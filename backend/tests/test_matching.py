"""Phase 5 tests: service matching (§6) + decision-maker identification (§7).

The RAG grounding text, web search, and both LLM calls (matcher, extractor) are injected
fakes, so this runs on requirements-base.txt with no API keys and no network.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph.nodes.decision_makers import find_decision_makers
from app.graph.nodes.service_matching import match_service
from app.main import app
from app.memory.store import get_store
from app.schemas.contact import Contact
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.matching import DecisionMakerList, ServiceMatch
from app.schemas.research import ResearchProfile

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
def qualified_lead() -> Lead:
    return Lead(
        id="acme",
        company_name="Acme Logistics",
        domain="acme.com",
        stage=PipelineStage.QUALIFIED,
        confidence=82.0,
        explanation="High inbound WhatsApp volume; strong ICP fit.",
        research=ResearchProfile(problems_signals="Overwhelmed by WhatsApp customer inquiries"),
    )


# ── service matching core (§6) ───────────────────────────
def test_match_service_sets_grounded_recommendation(qualified_lead):
    matcher = _FakeRunnable(
        ServiceMatch(
            recommended_service="WhatsApp AI Chatbot",
            rationale="They are drowning in WhatsApp inquiries",
            alternatives=["Email automation"],
        )
    )
    out = match_service(qualified_lead, "We sell a WhatsApp AI Chatbot and Email automation.",
                        matcher=matcher, settings=get_settings())

    assert out.recommended_service == "WhatsApp AI Chatbot"
    assert out.service_rationale == "They are drowning in WhatsApp inquiries"
    assert out.stage is PipelineStage.QUALIFIED  # enrichment does not advance the stage


def test_match_service_none_when_no_fit(qualified_lead):
    matcher = _FakeRunnable(ServiceMatch(recommended_service=None, rationale="No offering fits"))
    out = match_service(qualified_lead, "", matcher=matcher, settings=get_settings())

    assert out.recommended_service is None
    assert out.service_rationale == "No offering fits"


# ── decision-maker identification core (§7) ──────────────
def test_find_decision_makers_extracts_and_caps(qualified_lead):
    def fake_search(query, max_results=5):
        return [{"title": "Team", "url": "https://acme.com/team", "content": "leadership"}]

    people = [
        Contact(name=f"Person {i}", role="VP Sales", relevance="owns support") for i in range(7)
    ]
    extractor = _FakeRunnable(DecisionMakerList(contacts=people))

    lead = qualified_lead.model_copy(update={"recommended_service": "WhatsApp AI Chatbot"})
    out = find_decision_makers(
        lead, search_fn=fake_search, extractor=extractor, settings=get_settings()
    )

    assert len(out.contacts) == get_settings().max_decision_makers  # capped at 5
    assert out.contacts[0].role == "VP Sales"
    assert out.stage is PipelineStage.QUALIFIED


def test_find_decision_makers_no_evidence_keeps_contacts_empty(qualified_lead):
    out = find_decision_makers(
        qualified_lead,
        search_fn=lambda q, max_results=5: [],
        # extractor is never invoked when there is no evidence
        extractor=_FakeRunnable(DecisionMakerList(contacts=[Contact(name="ghost")])),
        settings=get_settings(),
    )
    assert out.contacts == []


# ── API ──────────────────────────────────────────────────
def test_enrich_endpoint_requires_qualified_leads():
    assert client.post("/leads/enrich").status_code == 400


def test_enrich_endpoint_persists_service_and_contacts(monkeypatch):
    from app.api.routers import leads as leads_router

    store = get_store()
    store.set_icp(ICP(industry="logistics"))
    store.upsert_lead(Lead(id="acme", company_name="Acme", stage=PipelineStage.QUALIFIED))

    monkeypatch.setattr(
        leads_router, "_company_knowledge_summary", lambda: "We sell a WhatsApp bot."
    )
    monkeypatch.setattr(
        leads_router,
        "match_services",
        lambda leads, knowledge, settings=None: [
            lead.model_copy(update={"recommended_service": "WhatsApp AI Chatbot"}) for lead in leads
        ],
    )
    monkeypatch.setattr(
        leads_router,
        "find_decision_makers_for",
        lambda leads, icp, settings=None: [
            lead.model_copy(update={"contacts": [Contact(name="Jane Doe", role="CEO")]})
            for lead in leads
        ],
    )

    r = client.post("/leads/enrich")
    assert r.status_code == 200
    body = r.json()
    assert body["enriched"] == 1 and body["with_service"] == 1 and body["with_contacts"] == 1

    lead = client.get("/leads/acme").json()
    assert lead["recommended_service"] == "WhatsApp AI Chatbot"
    assert lead["contacts"][0]["name"] == "Jane Doe"
    assert lead["stage"] == "Qualified"  # still Qualified after enrichment
