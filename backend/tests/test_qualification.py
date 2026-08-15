"""Phase 4 tests: deep research (§4) + qualification/confidence score (§5).

Search, website scrape, dossier synthesis, and scoring are all injected fakes, so this
runs on requirements-base.txt with no API keys and no network.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph.nodes.deep_research import research_lead
from app.graph.nodes.qualification import qualify_lead
from app.main import app
from app.memory.store import get_store
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.research import QualificationResult, ResearchProfile, ScoreBreakdown

client = TestClient(app)


class _FakeRunnable:
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


# ── deep research core ───────────────────────────────────
def test_research_lead_builds_grounded_dossier(icp):
    lead = Lead(id="acme", company_name="Acme Logistics", domain="acme.com",
                stage=PipelineStage.POTENTIAL)

    def fake_search(query, max_results=4):
        return [
            {"title": "Acme", "url": "https://acme.com/news", "content": "Raised $10M Series A"}
        ]

    profile = ResearchProfile(profile_summary="Regional 3PL", funding_growth="$10M Series A")
    out = research_lead(
        lead, icp,
        search_fn=fake_search,
        scrape_fn=lambda _url: "",
        synthesizer=_FakeRunnable(profile),
        settings=get_settings(),
    )

    assert out.stage is PipelineStage.RESEARCHING
    assert out.research.funding_growth == "$10M Series A"
    assert out.research.sources  # backfilled from search URLs when synthesizer left it empty
    assert out.research.website == "acme.com"  # backfilled from the lead domain


def test_research_lead_no_evidence_still_advances(icp):
    lead = Lead(id="x", company_name="Nobody Co", stage=PipelineStage.POTENTIAL)
    out = research_lead(
        lead, icp,
        search_fn=lambda q, max_results=4: [],
        scrape_fn=lambda _url: "",
        synthesizer=_FakeRunnable(None),  # never invoked — no evidence gathered
        settings=get_settings(),
    )
    assert out.stage is PipelineStage.RESEARCHING
    assert out.research == ResearchProfile()


# ── qualification core ───────────────────────────────────
def test_qualify_lead_above_threshold_is_qualified(icp):
    lead = Lead(id="acme", company_name="Acme", stage=PipelineStage.RESEARCHING,
                research=ResearchProfile(profile_summary="3PL"))
    scorer = _FakeRunnable(
        QualificationResult(confidence=85, explanation="strong ICP + service fit",
                            breakdown=ScoreBreakdown(icp_fit=90, service_fit=80))
    )
    out = qualify_lead(
        lead, icp, "we sell WhatsApp automation", scorer=scorer, settings=get_settings()
    )

    assert out.stage is PipelineStage.QUALIFIED
    assert out.confidence == 85
    assert out.explanation == "strong ICP + service fit"
    assert out.score_breakdown.icp_fit == 90


def test_qualify_lead_below_threshold_is_not_qualified(icp):
    lead = Lead(id="meh", company_name="Meh Inc", stage=PipelineStage.RESEARCHING,
                research=ResearchProfile())
    scorer = _FakeRunnable(QualificationResult(confidence=30, explanation="weak evidence"))
    out = qualify_lead(lead, icp, scorer=scorer, settings=get_settings())

    assert out.stage is PipelineStage.NOT_QUALIFIED
    assert out.confidence == 30


# ── API ──────────────────────────────────────────────────
def test_research_endpoint_guards():
    assert client.post("/leads/research").status_code == 400  # no ICP
    client.post("/icp", json={"industry": "logistics"})
    assert client.post("/leads/research").status_code == 400  # ICP but no Potential leads


def test_research_endpoint_persists_and_scores(monkeypatch):
    from app.api.routers import leads as leads_router

    store = get_store()
    store.set_icp(ICP(industry="logistics"))
    store.upsert_lead(Lead(id="acme", company_name="Acme", stage=PipelineStage.POTENTIAL))

    monkeypatch.setattr(
        leads_router,
        "research_leads",
        lambda leads, icp, settings=None: [
            lead.model_copy(update={"stage": PipelineStage.RESEARCHING}) for lead in leads
        ],
    )
    monkeypatch.setattr(
        leads_router,
        "qualify_leads",
        lambda leads, icp, knowledge, settings=None: [
            lead.model_copy(
                update={"stage": PipelineStage.QUALIFIED, "confidence": 88.0, "explanation": "fits"}
            )
            for lead in leads
        ],
    )

    r = client.post("/leads/research")
    assert r.status_code == 200
    body = r.json()
    assert body["researched"] == 1 and body["qualified"] == 1 and body["not_qualified"] == 0

    lead = client.get("/leads/acme").json()
    assert lead["stage"] == "Qualified" and lead["confidence"] == 88.0
    assert client.get("/pipeline").json()["Qualified"][0]["id"] == "acme"
