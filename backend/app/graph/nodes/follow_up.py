"""Follow-Up node (§11) — Phase 7.

Day 0 sends Email #1 (Phase 6 outreach). If a prospect hasn't replied after ``follow_up_wait_days``
(default 3), the Follow-Up Agent sends Email #2 — once (``max_follow_ups``). A lead is eligible when
it is still at CONTACTED, is awaiting a response (no reply since our last email), and hasn't
already used up its follow-ups. The scheduler sweeps for due leads on a timer; the endpoint can
force one immediately for the 90-second demo. Drafter / send_fn are injected so this unit-tests
offline, and ``now`` is injectable so eligibility is deterministic under test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.graph.nodes.outreach import _select_contacts
from app.graph.state import PipelineState
from app.schemas.contact import Contact
from app.schemas.conversation import Message
from app.schemas.email import EmailDraft, OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead


def _awaiting_response(lead: Lead) -> bool:
    """True if we've emailed and the prospect hasn't replied since (so a bump is warranted)."""
    if lead.last_outreach_at is None:
        return False
    last_reply = max(
        (m.timestamp for m in lead.messages if m.role == "prospect" and m.timestamp),
        default=None,
    )
    return last_reply is None or last_reply <= lead.last_outreach_at


def is_eligible(lead: Lead, settings, *, force: bool, now: datetime) -> bool:
    """Whether a lead is due for an automated follow-up (§11)."""
    if lead.stage is not PipelineStage.CONTACTED:
        return False
    if lead.follow_up_count >= settings.max_follow_ups:
        return False
    if not _awaiting_response(lead):
        return False
    if force:
        return True
    if lead.last_outreach_at is None:
        return False
    return now - lead.last_outreach_at >= timedelta(days=settings.follow_up_wait_days)


def _follow_up_prompt(lead: Lead, contact: Contact, knowledge: str) -> str:
    svc = lead.recommended_service or "our services"
    sell = f"\n\nWhat we offer:\n{knowledge.strip()}" if knowledge else ""
    return (
        "Write a short, polite SECOND-touch follow-up email (subject + body) to "
        f"{contact.name or 'the contact'} ({contact.role or 'decision-maker'}) at "
        f"{lead.company_name}. They didn't reply to our first email. Gently re-surface the value, "
        "don't guilt-trip, keep it under ~90 words, and end with a low-friction call to action. "
        f"Center it on how '{svc}' could help them. Ground every claim only in what we know — do "
        f"not invent facts.{sell}"
    )


def follow_up_lead(
    lead: Lead,
    knowledge: str = "",
    *,
    drafter=None,
    send_fn=None,
    settings=None,
    now: datetime | None = None,
) -> tuple[Lead, OutreachLog | None]:
    """Draft + send Email #2 to the lead's top contact; advances the follow-up clock."""
    settings = settings or get_settings()
    targets = _select_contacts(lead, 1)  # follow up the single best contact
    if not targets:
        return lead, None
    contact = targets[0]

    if drafter is None:
        from app.llm.parsers import structured

        drafter = structured(EmailDraft, model=settings.llm_model)
    if send_fn is None:
        from app.services.gmail_client import send_email as send_fn

    draft: EmailDraft = drafter.invoke(_follow_up_prompt(lead, contact, knowledge))
    draft.to = contact.email
    if settings.booking_link and not draft.meeting_link:
        draft.meeting_link = settings.booking_link

    now = now or datetime.now(tz=timezone.utc)
    send_fn(draft.to, draft.subject, draft.body, settings=settings)

    body = draft.body
    if draft.meeting_link:
        body = f"{body}\n\nBooking link: {draft.meeting_link}"
    log = OutreachLog(
        company=lead.company_name,
        contact_name=contact.name,
        role=contact.role,
        lead_score=lead.confidence,
        recommended_service=lead.recommended_service,
        message=f"[Follow-up #{lead.follow_up_count + 1}] Subject: {draft.subject}\n\n{body}",
        evidence=(lead.research.sources if lead.research else []),
        timestamp=now,
    )
    agent_msg = Message(
        role="agent", channel="email",
        text=f"{draft.subject}\n\n{draft.body}", timestamp=now,
    )
    updated = lead.model_copy(
        update={
            "follow_up_count": lead.follow_up_count + 1,
            "last_outreach_at": now,
            "messages": [*lead.messages, agent_msg],
            "updated_at": now,
        }
    )
    return updated, log


def run_follow_ups(
    leads: list[Lead],
    knowledge: str = "",
    *,
    force: bool = False,
    drafter=None,
    send_fn=None,
    settings=None,
    now: datetime | None = None,
) -> tuple[list[Lead], list[OutreachLog]]:
    """Send Email #2 to every eligible lead; returns only the leads followed up + their logs."""
    settings = settings or get_settings()
    now = now or datetime.now(tz=timezone.utc)
    updated: list[Lead] = []
    logs: list[OutreachLog] = []
    for lead in leads:
        if not is_eligible(lead, settings, force=force, now=now):
            continue
        lead_out, log = follow_up_lead(
            lead, knowledge, drafter=drafter, send_fn=send_fn, settings=settings, now=now
        )
        updated.append(lead_out)
        if log is not None:
            logs.append(log)
    return updated, logs


def run(state: PipelineState) -> dict:
    # Graph-path adapter. The canonical drivers are the APScheduler sweep + POST /leads/follow-up
    # over the store; a one-shot graph invoke has no 3-day clock to honour.
    return {}
