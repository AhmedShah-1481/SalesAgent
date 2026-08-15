"""Phase 6 tests: personalized outreach (§8) + email send/log (§9).

The email drafter (LLM), the send mechanism, and RAG grounding are injected/simulated, so this
runs on requirements-base.txt with no API keys, no Gmail, and no network.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph.nodes.outreach import draft_email, outreach_lead
from app.main import app
from app.memory.store import get_store
from app.schemas.contact import Contact
from app.schemas.email import EmailDraft, OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead
from app.schemas.research import ResearchProfile
from app.services.gmail_client import send_email

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
        recommended_service="WhatsApp AI Chatbot",
        contacts=[Contact(name="Jane Doe", role="Head of Support", email="jane@acme.com")],
        research=ResearchProfile(sources=["https://acme.com/news"]),
    )


# ── drafting (§8) ────────────────────────────────────────
def test_draft_email_sets_recipient_and_booking_link(qualified_lead):
    contact = qualified_lead.contacts[0]
    drafter = _FakeRunnable(EmailDraft(subject="Cut your WhatsApp backlog", body="Hi Jane, ..."))

    draft = draft_email(
        qualified_lead, contact, "We sell a WhatsApp AI Chatbot.",
        booking_link="https://book.me/demo", drafter=drafter, settings=get_settings(),
    )

    assert draft.to == "jane@acme.com"  # recipient forced from the contact, not the LLM
    assert draft.meeting_link == "https://book.me/demo"
    assert draft.subject == "Cut your WhatsApp backlog"


# ── outreach + logging (§9) ──────────────────────────────
def test_outreach_lead_contacts_and_logs(qualified_lead):
    sent: list[str | None] = []

    def fake_send(to, subject, body, **_kw):
        sent.append(to)
        return {"status": "simulated", "to": to}

    drafter = _FakeRunnable(EmailDraft(subject="Hi", body="Grounded body."))
    updated, logs = outreach_lead(
        qualified_lead, "our services", drafter=drafter, send_fn=fake_send, settings=get_settings()
    )

    assert updated.stage is PipelineStage.CONTACTED
    assert sent == ["jane@acme.com"]
    assert len(logs) == 1
    log = logs[0]
    assert log.company == "Acme Logistics"
    assert log.role == "Head of Support"
    assert log.recommended_service == "WhatsApp AI Chatbot"
    assert log.lead_score == 82.0
    assert log.evidence == ["https://acme.com/news"]  # §9 evidence trail
    assert log.message.startswith("Subject: Hi")
    assert log.timestamp is not None


def test_outreach_lead_no_contacts_is_noop():
    lead = Lead(id="x", company_name="No Contacts Inc", stage=PipelineStage.QUALIFIED)
    updated, logs = outreach_lead(
        lead,
        drafter=_FakeRunnable(EmailDraft()),
        send_fn=lambda *a, **k: {},
        settings=get_settings(),
    )
    assert updated.stage is PipelineStage.QUALIFIED  # cannot contact -> unchanged
    assert logs == []


def test_outreach_prefers_a_contact_with_an_email(qualified_lead):
    # top-priority contact has no email; the emailed one should be chosen (cap = 1)
    lead = qualified_lead.model_copy(
        update={
            "contacts": [
                Contact(name="No Email CEO", role="CEO"),
                Contact(name="Jane Doe", role="Head of Support", email="jane@acme.com"),
            ]
        }
    )
    _, logs = outreach_lead(
        lead, drafter=_FakeRunnable(EmailDraft(subject="Hi", body="b")),
        send_fn=lambda *a, **k: {}, settings=get_settings(),
    )
    assert len(logs) == 1
    assert logs[0].contact_name == "Jane Doe"


# ── gmail client simulate mode (no network) ──────────────
def test_send_email_simulate_returns_without_network():
    result = send_email("jane@acme.com", "Subject", "Body", settings=get_settings())
    assert result["status"] == "simulated"  # EMAIL_MODE defaults to simulate


# ── API ──────────────────────────────────────────────────
def test_outreach_endpoint_requires_qualified_leads():
    assert client.post("/leads/outreach").status_code == 400


def test_outreach_endpoint_persists_and_logs(monkeypatch):
    from app.api.routers import leads as leads_router

    store = get_store()
    store.upsert_lead(
        Lead(
            id="acme",
            company_name="Acme",
            stage=PipelineStage.QUALIFIED,
            contacts=[Contact(name="Jane", role="CEO", email="jane@acme.com")],
        )
    )

    monkeypatch.setattr(leads_router, "_company_knowledge_summary", lambda: "We sell a bot.")

    def fake_outreach(leads, knowledge, settings=None):
        updated = [lead.model_copy(update={"stage": PipelineStage.CONTACTED}) for lead in leads]
        logs = [OutreachLog(company="Acme", contact_name="Jane", role="CEO", message="Subject: Hi")]
        return updated, logs

    monkeypatch.setattr(leads_router, "outreach_leads", fake_outreach)

    r = client.post("/leads/outreach")
    assert r.status_code == 200
    body = r.json()
    assert body["contacted"] == 1 and body["emails"] == 1 and body["mode"] == "simulate"

    assert len(client.get("/outreach").json()) == 1
    assert client.get("/leads/acme").json()["stage"] == "Contacted"
