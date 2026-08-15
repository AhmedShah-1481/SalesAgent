"""Phase 8 tests: meeting finalization + admin reminder (§12).

The briefing LLM, the prospect email, the admin notifier, and the calendar creator are all
injected/simulated, and the meeting clock takes an injected ``now``, so this runs on
requirements-base.txt with no API keys and no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph.nodes.meeting import (
    finalize_meeting,
    is_reminder_due,
    pick_meeting_time,
    run_reminders,
)
from app.main import app
from app.memory.store import get_store
from app.schemas.contact import Contact
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead
from app.schemas.meeting import AdminBriefing, Meeting
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


def _briefer() -> _FakeRunnable:
    return _FakeRunnable(
        AdminBriefing(
            customer_problem="slow manual support",
            recommended_service="WhatsApp AI Chatbot",
            key_objections=["price"],
            discussion_points=["live demo", "integration timeline"],
        )
    )


def _interested_lead(**overrides) -> Lead:
    base = dict(
        id="acme",
        company_name="Acme Logistics",
        confidence=82.0,
        recommended_service="WhatsApp AI Chatbot",
        stage=PipelineStage.INTERESTED,
        contacts=[Contact(name="Jane Doe", role="Head of Support", email="jane@acme.com")],
        research=ResearchProfile(sources=["https://acme.com/news"]),
    )
    base.update(overrides)
    return Lead(**base)


# ── meeting time (§12) ───────────────────────────────────
def test_pick_meeting_time_is_a_fixed_future_slot():
    now = datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc)
    when = pick_meeting_time(now, get_settings())
    assert when.hour == get_settings().meeting_hour
    assert when.minute == 0 and when.second == 0
    assert (when.date() - now.date()).days == get_settings().meeting_lead_days


# ── finalize meeting (§11 confirm + §12 notify) ──────────
def test_finalize_meeting_confirms_prospect_and_briefs_admin():
    now = datetime.now(tz=timezone.utc)
    emails: list[tuple[str, str]] = []
    admins: list[str] = []

    def fake_email(to, subject, body, **_kw):
        emails.append((to, subject))
        return {"status": "simulated"}

    def fake_admin(message, **_kw):
        admins.append(message)
        return {"status": "simulated"}

    updated, meeting, log = finalize_meeting(
        _interested_lead(),
        briefer=_briefer(), email_fn=fake_email, admin_fn=fake_admin,
        settings=get_settings(), now=now,
    )

    assert updated.stage is PipelineStage.MEETING_SCHEDULED
    assert meeting.scheduled_time == pick_meeting_time(now, get_settings())
    assert meeting.meeting_link  # simulated link set
    assert meeting.briefing and "slow manual support" in meeting.briefing
    assert meeting.reminder_sent is False
    assert emails and emails[0][0] == "jane@acme.com"  # §11 prospect confirmation
    assert admins and "Meeting finalized" in admins[0]  # §12 admin notified
    assert log is not None and log.message.startswith("Subject:")
    assert updated.messages[-1].role == "agent"  # confirmation recorded on the lead


def test_finalize_meeting_without_contact_email_still_schedules_and_notifies():
    now = datetime.now(tz=timezone.utc)
    admins: list[str] = []
    emails: list[str] = []
    lead = _interested_lead(contacts=[Contact(name="Jane Doe", role="Head of Support")])

    updated, meeting, log = finalize_meeting(
        lead,
        briefer=_briefer(),
        email_fn=lambda to, s, b, **_kw: emails.append(to),
        admin_fn=lambda m, **_kw: admins.append(m),
        settings=get_settings(), now=now,
    )

    assert emails == []  # no address -> no prospect email
    assert log is None
    assert admins  # admin still briefed
    assert updated.stage is PipelineStage.MEETING_SCHEDULED
    assert meeting.contact_name == "Jane Doe"


# ── reminder due logic (§12: ~30 min before) ─────────────
def test_is_reminder_due_rules():
    s = get_settings()
    now = datetime.now(tz=timezone.utc)

    soon = Meeting(lead_id="a", company="A", scheduled_time=now + timedelta(minutes=20))
    assert is_reminder_due(soon, now=now, settings=s) is True

    far = Meeting(lead_id="b", company="B", scheduled_time=now + timedelta(minutes=90))
    assert is_reminder_due(far, now=now, settings=s) is False
    assert is_reminder_due(far, now=now, settings=s, force=True) is True  # force bypasses window

    sent = Meeting(
        lead_id="c", company="C",
        scheduled_time=now + timedelta(minutes=20), reminder_sent=True,
    )
    assert is_reminder_due(sent, now=now, settings=s, force=True) is False  # already reminded

    unscheduled = Meeting(lead_id="d", company="D", scheduled_time=None)
    assert is_reminder_due(unscheduled, now=now, settings=s, force=True) is False

    past = Meeting(lead_id="e", company="E", scheduled_time=now - timedelta(minutes=5))
    assert is_reminder_due(past, now=now, settings=s) is False  # meeting already started


def test_run_reminders_fires_only_for_due_meetings():
    now = datetime.now(tz=timezone.utc)
    admins: list[str] = []
    due = Meeting(lead_id="a", company="A", scheduled_time=now + timedelta(minutes=10))
    not_due = Meeting(lead_id="b", company="B", scheduled_time=now + timedelta(hours=5))
    already = Meeting(
        lead_id="c", company="C",
        scheduled_time=now + timedelta(minutes=10), reminder_sent=True,
    )

    reminded = run_reminders(
        [due, not_due, already],
        admin_fn=lambda m, **_kw: admins.append(m), settings=get_settings(), now=now,
    )

    assert [m.lead_id for m in reminded] == ["a"]
    assert reminded[0].reminder_sent is True
    assert len(admins) == 1 and "~30 minutes" in admins[0]


# ── API ──────────────────────────────────────────────────
def test_schedule_meeting_404_for_unknown_lead():
    assert client.post("/leads/nope/schedule-meeting", json={}).status_code == 404


def test_schedule_meeting_persists_lead_meeting_and_log(monkeypatch):
    from app.api.routers import meetings as meetings_router

    get_store().upsert_lead(
        Lead(
            id="acme", company_name="Acme", stage=PipelineStage.INTERESTED,
            contacts=[Contact(name="Jane", role="CEO", email="jane@acme.com")],
        )
    )

    def fake_finalize(lead, *, when=None, settings=None, **_kw):
        meeting = Meeting(
            lead_id=lead.id, company=lead.company_name, contact_name="Jane",
            scheduled_time=datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
            meeting_link="https://meet.example.com/acme", briefing="Customer problem: x",
        )
        updated = lead.model_copy(update={"stage": PipelineStage.MEETING_SCHEDULED})
        log = OutreachLog(company="Acme", contact_name="Jane", role="CEO",
                          message="Subject: Meeting confirmed")
        return updated, meeting, log

    monkeypatch.setattr(meetings_router, "finalize_meeting", fake_finalize)

    r = client.post("/leads/acme/schedule-meeting", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["emailed"] is True
    assert body["lead"]["stage"] == "Meeting Scheduled"
    assert body["meeting"]["meeting_link"] == "https://meet.example.com/acme"
    # persisted across the store
    assert client.get("/leads/acme").json()["stage"] == "Meeting Scheduled"
    assert len(client.get("/meetings").json()) == 1
    assert len(client.get("/outreach").json()) == 1


def test_reminders_run_requires_meetings():
    assert client.post("/meetings/reminders/run").status_code == 400


def test_reminders_run_forces_and_marks_reminded():
    now = datetime.now(tz=timezone.utc)
    # notify_admin degrades to a log when no ADMIN_WHATSAPP_NUMBER is set — no network here.
    get_store().upsert_meeting(
        Meeting(
            lead_id="acme", company="Acme", contact_name="Jane",
            scheduled_time=now + timedelta(days=1),
            meeting_link="https://meet.example.com/acme", briefing="Customer problem: x",
        )
    )

    r = client.post("/meetings/reminders/run?force=true")
    assert r.status_code == 200
    body = r.json()
    assert body["reminded"] == 1 and body["pending"] == 0
    assert client.get("/meetings").json()[0]["reminder_sent"] is True
