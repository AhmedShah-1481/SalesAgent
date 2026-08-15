"""Personalized Outreach node (§8) + email send/log (§9) — Phase 6.

For each QUALIFIED lead (already service-matched + given decision-makers in Phase 5), draft a
role-specific, evidence-grounded email per selected contact, attach a booking link when one is
configured, send it via Gmail or simulate it (EMAIL_MODE), and log the action with the §9 fields.
Promotes QUALIFIED -> CONTACTED and stamps ``last_outreach_at`` so the §11 follow-up clock starts.
The recipient address and booking link are set deterministically (not trusted to the LLM). Core is
dependency-injected (drafter / send_fn) so it unit-tests without an LLM call or network.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.contact import Contact
from app.schemas.conversation import Message
from app.schemas.email import EmailDraft, OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead


def _select_contacts(lead: Lead, limit: int) -> list[Contact]:
    """Prefer contacts we can actually email, preserving §7 relevance order within each group."""
    with_email = [c for c in lead.contacts if c.email]
    without_email = [c for c in lead.contacts if not c.email]
    return (with_email + without_email)[:limit]


def _draft_prompt(lead: Lead, contact: Contact, knowledge: str, booking_link: str) -> str:
    dossier = lead.research.model_dump_json(indent=2) if lead.research else "{}"
    role = contact.role or "decision-maker"
    svc = lead.recommended_service or "our services"
    sell = (
        f"\n\nWhat we offer (for accuracy, do not overstate):\n{knowledge.strip()}"
        if knowledge
        else ""
    )
    link = (
        "\n\nEnd with a clear call to action and include this booking link naturally: "
        f"{booking_link}"
        if booking_link
        else "\n\nEnd with a clear call to action (propose a short intro call)."
    )
    return (
        "Write a concise, personalized B2B outreach email (subject + body) from our sales team to "
        f"{contact.name or 'the contact'} ({role}) at {lead.company_name}. Ground EVERY claim only "
        "in the research dossier and our offerings below — do not invent facts about the prospect. "
        "Frame it for this person's role: a technical leader (CTO) cares about integration and "
        "technical fit; a sales or support leader cares about response time, productivity, and "
        f"revenue impact. Center the message on how '{svc}' addresses their likely problem. Keep "
        f"it under ~150 words, friendly and specific.{sell}{link}\n\n"
        f"Prospect research dossier:\n{dossier}"
    )


def draft_email(
    lead: Lead,
    contact: Contact,
    knowledge: str = "",
    *,
    booking_link: str = "",
    drafter=None,
    settings=None,
) -> EmailDraft:
    """Draft one role-specific email; recipient + booking link are set deterministically."""
    settings = settings or get_settings()
    if drafter is None:
        from app.llm.parsers import structured

        drafter = structured(EmailDraft, model=settings.llm_model)

    draft: EmailDraft = drafter.invoke(_draft_prompt(lead, contact, knowledge, booking_link))
    draft.to = contact.email  # never let the model invent a recipient
    if booking_link and not draft.meeting_link:
        draft.meeting_link = booking_link
    return draft


def _to_log(lead: Lead, contact: Contact, draft: EmailDraft, now: datetime) -> OutreachLog:
    body = draft.body
    if draft.meeting_link:
        body = f"{body}\n\nBooking link: {draft.meeting_link}"
    return OutreachLog(
        company=lead.company_name,
        contact_name=contact.name,
        role=contact.role,
        lead_score=lead.confidence,
        recommended_service=lead.recommended_service,
        message=f"Subject: {draft.subject}\n\n{body}",
        evidence=(lead.research.sources if lead.research else []),
        timestamp=now,
    )


def outreach_lead(
    lead: Lead,
    knowledge: str = "",
    *,
    drafter=None,
    send_fn=None,
    settings=None,
) -> tuple[Lead, list[OutreachLog]]:
    """Draft + send/simulate email(s) for a lead's top contact(s) -> CONTACTED + outreach logs."""
    settings = settings or get_settings()
    if send_fn is None:
        from app.services.gmail_client import send_email as send_fn

    targets = _select_contacts(lead, settings.outreach_max_contacts_per_lead)
    if not targets:
        return lead, []  # nobody to contact — leave the lead as-is

    now = datetime.now(tz=timezone.utc)
    logs: list[OutreachLog] = []
    sent_messages: list[Message] = []
    for contact in targets:
        draft = draft_email(
            lead, contact, knowledge,
            booking_link=settings.booking_link, drafter=drafter, settings=settings,
        )
        send_fn(draft.to, draft.subject, draft.body, settings=settings)
        logs.append(_to_log(lead, contact, draft, now))
        sent_messages.append(
            Message(
                role="agent", channel="email",
                text=f"{draft.subject}\n\n{draft.body}", timestamp=now,
            )
        )

    updated = lead.model_copy(
        update={
            "stage": PipelineStage.CONTACTED,
            "messages": [*lead.messages, *sent_messages],
            "last_outreach_at": now,  # starts the §11 3-day follow-up clock
            "updated_at": now,
        }
    )
    return updated, logs


def outreach_leads(
    leads: list[Lead], knowledge: str = "", *, settings=None, **kwargs
) -> tuple[list[Lead], list[OutreachLog]]:
    settings = settings or get_settings()
    updated: list[Lead] = []
    logs: list[OutreachLog] = []
    for lead in leads:
        lead_out, lead_logs = outreach_lead(lead, knowledge, settings=settings, **kwargs)
        updated.append(lead_out)
        logs.extend(lead_logs)
    return updated, logs


def run(state: PipelineState) -> dict:
    leads = [
        lead
        for lead in (state.get("leads") or [])
        if lead.stage is PipelineStage.QUALIFIED and lead.contacts
    ]
    if not leads:
        return {}
    updated, logs = outreach_leads(leads, state.get("company_knowledge", "") or "")
    event = ActivityEvent(
        kind="outreach",
        message=f"Outreach ({get_settings().email_mode}): {len(logs)} emails "
        f"across {len(updated)} leads.",
        stage=PipelineStage.CONTACTED.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    # NOTE: batch `leads` mutation needs an id-upsert reducer (P10); canonical driver is
    # POST /leads/outreach operating on the store.
    return {"leads": updated, "outreach_logs": logs, "activity": [event]}
