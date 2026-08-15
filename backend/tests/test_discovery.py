"""Phase 3 tests: ICP intake + staged discovery (search -> extract -> cheap filter).

No live search or LLM calls — the search function, extractor, and cheap-filter judge are
injected fakes, so this runs on requirements-base.txt with no API keys.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routers import icp as icp_router
from app.config import get_settings
from app.graph.nodes.cheap_filter import filter_candidates
from app.graph.nodes.discovery import discover_leads
from app.main import app
from app.memory.store import get_store
from app.schemas.discovery import (
    CandidateCompany,
    CandidateExtraction,
    FilterResponse,
    FilterVerdict,
)
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead

client = TestClient(app)


class _FakeRunnable:
    """Stands in for a `.with_structured_output(...)` runnable."""

    def __init__(self, result):
        self._result = result

    def invoke(self, _prompt):
        return self._result


@pytest.fixture(autouse=True)
def _clean_store():
    get_store().clear()
    yield
    get_store().clear()


@pytest.fixture
def icp() -> ICP:
    return ICP(location="Texas", industry="logistics", special_targeting="high call volume")


# ── discovery core ───────────────────────────────────────
def test_discover_leads_grounded_and_deduped(icp):
    def fake_search(query, max_results=8):
        return [
            {"title": "Acme Logistics", "url": "https://acme.com", "content": "3PL in Texas"},
            {"title": "Acme Logistics", "url": "https://acme.com/about", "content": "dup domain"},
        ]

    extractor = _FakeRunnable(
        CandidateExtraction(
            companies=[
                CandidateCompany(name="Acme Logistics", domain="acme.com", reason="3PL in TX"),
                CandidateCompany(name="Acme Logistics", domain="acme.com", reason="dup"),
                CandidateCompany(name="Lone Star Freight", domain="lonestar.io", reason="freight"),
            ]
        )
    )

    leads = discover_leads(icp, search_fn=fake_search, extractor=extractor, settings=get_settings())

    assert [lead.company_name for lead in leads] == ["Acme Logistics", "Lone Star Freight"]
    assert all(lead.stage is PipelineStage.DISCOVERED for lead in leads)
    assert leads[0].evidence == ["3PL in TX"]  # grounded reason carried as evidence


def test_discover_leads_empty_search_returns_nothing(icp):
    leads = discover_leads(
        icp, search_fn=lambda q, max_results=8: [], extractor=_FakeRunnable(None)
    )
    assert leads == []


# ── cheap filter core ────────────────────────────────────
def test_cheap_filter_keeps_drops_and_defaults_to_keep(icp):
    candidates = [
        Lead(id="acme", company_name="Acme Logistics", stage=PipelineStage.DISCOVERED),
        Lead(id="dir", company_name="Freight Directory", stage=PipelineStage.DISCOVERED),
        Lead(id="unrated", company_name="Mystery Co", stage=PipelineStage.DISCOVERED),
    ]
    judge = _FakeRunnable(
        FilterResponse(
            verdicts=[
                FilterVerdict(name="Acme Logistics", keep=True, reason="fits ICP"),
                FilterVerdict(name="Freight Directory", keep=False, reason="a directory"),
                # Mystery Co intentionally unrated -> must default to keep
            ]
        )
    )

    kept, dropped = filter_candidates(candidates, icp, judge=judge)

    kept_names = {lead.company_name for lead in kept}
    assert kept_names == {"Acme Logistics", "Mystery Co"}
    assert all(lead.stage is PipelineStage.POTENTIAL for lead in kept)
    assert [lead.company_name for lead in dropped] == ["Freight Directory"]
    assert "directory" in dropped[0].explanation.lower()


# ── store + API ──────────────────────────────────────────
def test_icp_roundtrip_and_empty_leads():
    assert client.get("/icp").json() is None
    r = client.post("/icp", json={"location": "Texas", "industry": "logistics"})
    assert r.status_code == 200
    assert r.json()["industry"] == "logistics"
    assert client.get("/icp").json()["location"] == "Texas"
    assert client.get("/leads").json() == []


def test_pipeline_has_every_stage_and_lead_404():
    stages = client.get("/pipeline").json()
    assert {"Discovered", "Potential", "Qualified", "Converted"} <= set(stages)
    assert client.get("/leads/nope").status_code == 404


def test_discover_endpoint_requires_icp():
    assert client.post("/icp/discover").status_code == 400


def test_discover_endpoint_persists_potential_leads(monkeypatch):
    lead = Lead(id="acme", company_name="Acme Logistics", stage=PipelineStage.DISCOVERED)

    monkeypatch.setattr(icp_router, "discover_leads", lambda icp, knowledge, settings=None: [lead])
    monkeypatch.setattr(
        icp_router,
        "filter_candidates",
        lambda cands, icp, settings=None: (
            [c.model_copy(update={"stage": PipelineStage.POTENTIAL}) for c in cands],
            [],
        ),
    )

    client.post("/icp", json={"location": "Texas", "industry": "logistics"})
    r = client.post("/icp/discover")
    assert r.status_code == 200
    body = r.json()
    assert body["discovered"] == 1 and body["kept"] == 1 and body["dropped"] == 0

    leads = client.get("/leads").json()
    assert len(leads) == 1 and leads[0]["stage"] == "Potential"
    assert client.get("/pipeline").json()["Potential"][0]["company_name"] == "Acme Logistics"
