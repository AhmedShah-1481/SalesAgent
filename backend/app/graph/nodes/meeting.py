"""Meeting & Admin Automation node (§12) — Phase 8.

Finalizes a meeting for an interested lead: picks a fixed time, provides a meeting link (real
Google Calendar/Meet when MEETING_MODE=create, else a simulated link + BOOKING_LINK), replies to
the prospect with the link + fixed time (§11), notifies the admin over WhatsApp (§12), and stores
the meeting with an LLM briefing. A separate reminder step notifies the admin ~30 minutes before
the meeting with that briefing (§12). The prospect email, the admin notifier, the briefing LLM, and
the calendar creator are all dependency-injected (and ``now`` is injectable), so this unit-tests
with no API keys, no Google/Gmail, and no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.graph.nodes.outreach import _select_contacts
from app.graph.state import PipelineState
from app.schemas.contact import Contact
from app.schemas.conversation import Message
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead
from app.schemas.meeting import AdminBriefing, Meeting


def pick_meeting_time(now: datetime, settings) -> datetime:
    """A fixed, finalized meeting time: ``meeting_lead_days`` out at ``meeting_hour`` UTC."""
    day = now + timedelta(days=settings.meeting_lead_days)
    return day.replace(hour=settings.meeting_hour, minute=0, second=0, microsecond=0)


def create_meeting_link(
    lead: Lead, when: datetime, *, contact: Contact | None = None, creator=None, settings=None
) -> str:
    """Real Meet link (MEETING_MODE=create) or a simulated one (default)."""
    settings = settings or get_settings()
    if settings.meeting_mode == "create":
        if creator is None:
            from app.services.calendar_client import create_calendar_event as creator
        result = creator(
            f"{lead.company_name} × our team — intro call",
            when,
            when + timedelta(minutes=settings.meeting_duration_minutes),
            [contact.email] if contact and contact.email else [],
            settings=settings,
        )
        return result.get("meeting_link") or settings.booking_link
    # simulate: prefer a configured booking link, else a clearly-simulated placeholder
    return settings.booking_link or f"https://meet.example.com/{lead.id}-{when:%Y%m%d%H%M}"


def _briefing_prompt(lead: Lead) -> str:
    dossier = lead.research.model_dump_json(indent=2) if lead.research else "{}"
    replies = [m.text for m in lead.messages if m.role == "prospect"]
    convo = "\n".join(f"- {t}" for t in replies) if replies else "(no replies yet)"
    svc = lead.recommended_service or "our services"
    rationale = lead.service_rationale or ""
    return (
        "Prepare a concise pre-meeting briefing for our sales rep about this prospect. Ground it "
        "ONLY in the research dossier and the conversation below — do not invent facts. Identify "
        "the customer's likely problem, restate the recommended service and why it fits, list any "
        "objections/questions they've raised, and give a few concrete discussion points.\n\n"
        f"Company: {lead.company_name}\nRecommended service: {svc}\nWhy it fits: {rationale}\n\n"
        f"Prospect replies so far:\n{convo}\n\nResearch dossier:\n{dossier}"
    )


def _format_briefing(b: AdminBriefing) -> str:
    objections = "; ".join(b.key_objections) if b.key_objections else "none noted"
    points = "; ".join(b.discussion_points) if b.discussion_points else "intro + discovery"
    return (
        f"Customer problem: {b.customer_problem}\n"
        f"Recommended service: {b.recommended_service}\n"
        f"Key objections/questions: {objections}\n"
        f"Discussion points: {points}"
    )


def build_briefing(lead: Lead, *, briefer=None, settings=None) -> str:
    """Generate the §12 admin briefing (four grounded elements) for a lead."""
    settings = settings or get_settings()
    if briefer is None:
        from app.llm.parsers import structured

        briefer = structured(AdminBriefing, model=settings.llm_model)
    result: AdminBriefing = briefer.invoke(_briefing_prompt(lead))
    return _format_briefing(result)


def _confirmation_email(lead: Lead, contact: Contact, meeting: Meeting) -> tuple[str, str]:
    when = meeting.scheduled_time
    when_str = when.strftime("%A, %d %b %Y at %H:%M UTC") if when else "a time to be confirmed"
    subject = f"Meeting confirmed — {lead.company_name} × our team"
    body = (
        f"Hi {contact.name or 'there'},\n\n"
        f"Great to connect! I've scheduled our meeting for {when_str}.\n"
        f"Join here: {meeting.meeting_link}\n\n"
        "If that time doesn't work, just reply and we'll find another slot. Talk soon!"
    )
    return subject, body


def _admin_message(meeting: Meeting, *, reminder: bool) -> str:
    when = meeting.scheduled_time
    when_str = when.strftime("%d %b %Y %H:%M UTC") if when else "TBD"
    head = "Reminder: meeting in ~30 minutes" if reminder else "Meeting finalized"
    return (
        f"{head}\n"
        f"Company: {meeting.company}\n"
        f"Contact: {meeting.contact_name or 'n/a'}\n"
        f"Time: {when_str}\n"
        f"Link: {meeting.meeting_link}\n\n"
        f"Briefing:\n{meeting.briefing or 'n/a'}"
    )


def finalize_meeting(
    lead: Lead,
    *,
    when: datetime | None = None,
    briefer=None,
    email_fn=None,
    admin_fn=None,
    creator=None,
    settings=None,
    now: datetime | None = None,
) -> tuple[Lead, Meeting, OutreachLog | None]:
    """Finalize a meeting: link + fixed time, prospect confirmation (§11), admin notify (§12)."""
    settings = settings or get_settings()
    now = now or datetime.now(tz=timezone.utc)
    if email_fn is None:
        from app.services.gmail_client import send_email as email_fn
    if admin_fn is None:
        from app.services.whatsapp_client import notify_admin as admin_fn

    targets = _select_contacts(lead, 1)
    contact = targets[0] if targets else None
    when = when or pick_meeting_time(now, settings)
    link = create_meeting_link(lead, when, contact=contact, creator=creator, settings=settings)
    briefing = build_briefing(lead, briefer=briefer, settings=settings)

    meeting = Meeting(
        lead_id=lead.id,
        company=lead.company_name,
        contact_name=contact.name if contact else None,
        scheduled_time=when,
        meeting_link=link,
        briefing=briefing,
        reminder_sent=False,
    )

    log: OutreachLog | None = None
    messages = list(lead.messages)
    if contact and contact.email:  # §11: reply with the meeting link + fixed time
        subject, body = _confirmation_email(lead, contact, meeting)
        email_fn(contact.email, subject, body, settings=settings)
        log = OutreachLog(
            company=lead.company_name,
            contact_name=contact.name,
            role=contact.role,
            lead_score=lead.confidence,
            recommended_service=lead.recommended_service,
            message=f"Subject: {subject}\n\n{body}",
            evidence=(lead.research.sources if lead.research else []),
            timestamp=now,
        )
        messages.append(
            Message(role="agent", channel="email", text=f"{subject}\n\n{body}", timestamp=now)
        )

    admin_fn(_admin_message(meeting, reminder=False), settings=settings)  # §12 notify on finalize

    updated = lead.model_copy(
        update={"stage": PipelineStage.MEETING_SCHEDULED, "messages": messages, "updated_at": now}
    )
    return updated, meeting, log


def is_reminder_due(meeting: Meeting, *, now: datetime, settings, force: bool = False) -> bool:
    """Whether the admin reminder for this meeting should fire (§12: ~30 min before)."""
    if meeting.reminder_sent or meeting.scheduled_time is None:
        return False
    if force:
        return True
    window = timedelta(minutes=settings.meeting_reminder_minutes)
    return meeting.scheduled_time - window <= now < meeting.scheduled_time


def send_meeting_reminder(meeting: Meeting, *, admin_fn=None, settings=None) -> Meeting:
    """Send the admin the 30-min briefing reminder; returns the meeting with reminder_sent=True."""
    settings = settings or get_settings()
    if admin_fn is None:
        from app.services.whatsapp_client import notify_admin as admin_fn
    admin_fn(_admin_message(meeting, reminder=True), settings=settings)
    return meeting.model_copy(update={"reminder_sent": True})


def run_reminders(
    meetings: list[Meeting],
    *,
    force: bool = False,
    admin_fn=None,
    settings=None,
    now: datetime | None = None,
) -> list[Meeting]:
    """Send reminders for every due meeting; returns only the meetings actually reminded."""
    settings = settings or get_settings()
    now = now or datetime.now(tz=timezone.utc)
    reminded: list[Meeting] = []
    for meeting in meetings:
        if not is_reminder_due(meeting, now=now, settings=settings, force=force):
            continue
        reminded.append(send_meeting_reminder(meeting, admin_fn=admin_fn, settings=settings))
    return reminded


def run(state: PipelineState) -> dict:
    # Graph-path adapter. Canonical drivers are POST /leads/{id}/schedule-meeting + the reminder
    # sweep over the store; a batch graph invoke has no finalized time to honour.
    return {}
