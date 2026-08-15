"""Phase 7 tests: response classification (§10) + 3-day follow-up (§11).

The classifier LLM, the follow-up drafter, and the send mechanism are injected/simulated, and the
follow-up clock takes an injected ``now``, so this runs on requirements-base.txt with no API keys
and no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph.nodes.follow_up import is_eligible, run_follow_ups
from app.graph.nodes.response_classification import apply_reply
from app.main import app
from app.memory.store import get_store
from app.schemas.contact import Contact
from app.schemas.conversation import Message, ReplyClassification
from app.schemas.email import EmailDraft, OutreachLog
from app.schemas.enums import PipelineStage, ResponseCategory
from app.schemas.lead import Lead
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


def _contacted_lead(**overrides) -> Lead:
    base = dict(
        id="acme",
        company_name="Acme Logistics",
        confidence=82.0,
        recommended_service="WhatsApp AI Chatbot",
        stage=PipelineStage.CONTACTED,
        contacts=[Contact(name="Jane Doe", role="Head of Support", email="jane@acme.com")],
        research=ResearchProfile(sources=["https://acme.com/news"]),
    )
    base.update(overrides)
    return Lead(**base)


# ── classification (§10) ─────────────────────────────────
def test_apply_reply_positive_moves_to_interested():
    lead = _contacted_lead()
    clf = _FakeRunnable(ReplyClassification(category=ResponseCategory.POSITIVE, reasoning="keen"))

    updated, result = apply_reply(lead, "Yes, let's talk!", classifier=clf, settings=get_settings())

    assert result.category is ResponseCategory.POSITIVE
    assert updated.stage is PipelineStage.INTERESTED
    assert updated.last_response_category is ResponseCategory.POSITIVE
    assert updated.messages[-1].role == "prospect"
    assert updated.messages[-1].category is ResponseCategory.POSITIVE


def test_apply_reply_not_interested_disqualifies():
    clf = _FakeRunnable(
        ReplyClassification(category=ResponseCategory.NOT_INTERESTED, reasoning="hard no")
    )
    updated, _ = apply_reply(
        _contacted_lead(), "No thanks", classifier=clf, settings=get_settings()
    )
    assert updated.stage is PipelineStage.NOT_INTERESTED


def test_apply_reply_not_now_keeps_stage_but_records_signal():
    clf = _FakeRunnable(ReplyClassification(category=ResponseCategory.NOT_NOW, reasoning="later"))
    updated, _ = apply_reply(
        _contacted_lead(), "Circle back in Q3", channel="whatsapp",
        classifier=clf, settings=get_settings(),
    )
    assert updated.stage is PipelineStage.CONTACTED  # soft defer — no forced transition
    assert updated.last_response_category is ResponseCategory.NOT_NOW
    assert updated.messages[-1].channel == "whatsapp"


# ── follow-up eligibility (§11) ──────────────────────────
def test_is_eligible_rules():
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    due = _contacted_lead(last_outreach_at=now - timedelta(days=4))

    assert is_eligible(due, s, force=False, now=now) is True

    recent = due.model_copy(update={"last_outreach_at": now - timedelta(days=1)})
    assert is_eligible(recent, s, force=False, now=now) is False  # 3-day wait not elapsed
    assert is_eligible(recent, s, force=True, now=now) is True  # force bypasses the wait

    maxed = due.model_copy(update={"follow_up_count": s.max_follow_ups})
    assert is_eligible(maxed, s, force=True, now=now) is False  # already followed up

    moved = due.model_copy(update={"stage": PipelineStage.INTERESTED})
    assert is_eligible(moved, s, force=True, now=now) is False  # only CONTACTED leads


# ── follow-up send (§11) ─────────────────────────────────
def test_run_follow_ups_sends_email_two_and_advances_clock():
    sent: list[str | None] = []

    def fake_send(to, subject, body, **_kw):
        sent.append(to)
        return {"status": "simulated"}

    now = datetime.now(tz=timezone.utc)
    lead = _contacted_lead(last_outreach_at=now - timedelta(days=4))
    drafter = _FakeRunnable(EmailDraft(subject="Still worth a chat?", body="Following up..."))

    updated, logs = run_follow_ups(
        [lead], "we sell chatbots", force=False,
        drafter=drafter, send_fn=fake_send, settings=get_settings(), now=now,
    )

    assert sent == ["jane@acme.com"]
    assert len(updated) == 1
    assert updated[0].follow_up_count == 1
    assert updated[0].last_outreach_at == now  # clock reset for any future follow-up
    assert any(m.role == "agent" for m in updated[0].messages)
    assert len(logs) == 1
    assert logs[0].message.startswith("[Follow-up #1]")
    assert logs[0].evidence == ["https://acme.com/news"]


def test_run_follow_ups_skips_a_lead_that_already_replied():
    now = datetime.now(tz=timezone.utc)
    replied = _contacted_lead(
        last_outreach_at=now - timedelta(days=5),
        messages=[Message(role="prospect", text="got it", timestamp=now - timedelta(days=2))],
    )
    updated, logs = run_follow_ups(
        [replied], force=True,  # even forced, a replied lead isn't awaiting a response
        drafter=_FakeRunnable(EmailDraft(subject="s", body="b")),
        send_fn=lambda *a, **k: {}, settings=get_settings(), now=now,
    )
    assert updated == [] and logs == []


# ── API ──────────────────────────────────────────────────
def test_reply_endpoint_404_for_unknown_lead():
    assert client.post("/leads/nope/reply", json={"text": "hi"}).status_code == 404


def test_reply_endpoint_classifies_and_persists(monkeypatch):
    from app.api.routers import leads as leads_router

    get_store().upsert_lead(
        Lead(id="acme", company_name="Acme", stage=PipelineStage.CONTACTED)
    )

    def fake_apply(lead, text, *, channel="email", settings=None):
        updated = lead.model_copy(
            update={
                "stage": PipelineStage.INTERESTED,
                "last_response_category": ResponseCategory.POSITIVE,
            }
        )
        return updated, ReplyClassification(category=ResponseCategory.POSITIVE, reasoning="keen")

    monkeypatch.setattr(leads_router, "apply_reply", fake_apply)

    r = client.post("/leads/acme/reply", json={"text": "Yes!", "channel": "email"})
    assert r.status_code == 200
    body = r.json()
    assert body["classification"]["category"] == "Positive/Interested"
    assert body["lead"]["stage"] == "Interested"
    assert client.get("/leads/acme").json()["stage"] == "Interested"


def test_follow_up_endpoint_requires_contacted_leads():
    assert client.post("/leads/follow-up").status_code == 400


def test_follow_up_endpoint_forces_and_logs(monkeypatch):
    from app.api.routers import leads as leads_router

    get_store().upsert_lead(
        Lead(
            id="acme",
            company_name="Acme",
            stage=PipelineStage.CONTACTED,
            contacts=[Contact(name="Jane", role="CEO", email="jane@acme.com")],
        )
    )
    monkeypatch.setattr(leads_router, "_company_knowledge_summary", lambda: "we sell bots")

    def fake_run(leads, knowledge, force=False, settings=None):
        updated = [lead.model_copy(update={"follow_up_count": 1}) for lead in leads]
        logs = [
            OutreachLog(company="Acme", contact_name="Jane", role="CEO",
                        message="[Follow-up #1] Subject: Hi")
        ]
        return updated, logs

    monkeypatch.setattr(leads_router, "run_follow_ups", fake_run)

    r = client.post("/leads/follow-up?force=true")
    assert r.status_code == 200
    body = r.json()
    assert body["followed_up"] == 1 and body["emails"] == 1
    assert body["eligible_pool"] == 1 and body["mode"] == "simulate"
    assert len(client.get("/outreach").json()) == 1
    assert client.get("/leads/acme").json()["follow_up_count"] == 1
