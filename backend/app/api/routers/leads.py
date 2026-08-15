"""Leads + pipeline endpoints (§14–15 reads) + deep research/qualification trigger (§4–5).

Reads serve whatever is in the in-memory store; POST /leads/research runs deep research +
qualification over the current POTENTIAL leads. Phase 10 swaps the store for Supabase
behind the same shapes, so these handlers stay unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.graph.nodes.decision_makers import find_decision_makers_for
from app.graph.nodes.deep_research import research_leads
from app.graph.nodes.follow_up import run_follow_ups
from app.graph.nodes.outreach import outreach_leads
from app.graph.nodes.qualification import qualify_leads
from app.graph.nodes.response_classification import apply_reply
from app.graph.nodes.service_matching import match_services
from app.memory.store import get_store
from app.schemas.activity import ActivityEvent
from app.schemas.conversation import ReplyClassification
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead

router = APIRouter(tags=["leads"])
logger = get_logger(__name__)


class ResearchRunResult(BaseModel):
    """Response for POST /leads/research."""

    researched: int = Field(description="Potential leads deep-researched this run")
    qualified: int
    not_qualified: int
    skipped: int = Field(0, description="Potential leads left unprocessed by the per-run cap")
    leads: list[Lead] = Field(default_factory=list)


class EnrichmentRunResult(BaseModel):
    """Response for POST /leads/enrich (service matching §6 + decision-makers §7)."""

    enriched: int = Field(description="Qualified leads enriched this run")
    with_service: int = Field(description="Leads that got a recommended service")
    with_contacts: int = Field(description="Leads that got at least one decision-maker")
    skipped: int = Field(0, description="Qualified leads left unprocessed by the per-run cap")
    leads: list[Lead] = Field(default_factory=list)


class OutreachRunResult(BaseModel):
    """Response for POST /leads/outreach (personalized outreach §8 + email/log §9)."""

    contacted: int = Field(description="Leads moved to Contacted this run")
    emails: int = Field(description="Emails drafted + sent/simulated")
    skipped: int = Field(0, description="Qualified leads not contacted (no contacts, or over cap)")
    mode: str = Field(description="Email mode used: 'simulate' or 'send'")
    logs: list[OutreachLog] = Field(default_factory=list)
    leads: list[Lead] = Field(default_factory=list)


class IncomingReply(BaseModel):
    """Body for POST /leads/{id}/reply — an inbound prospect message from any channel."""

    text: str = Field(min_length=1, description="The prospect's reply text")
    channel: str = Field("email", description="Channel it arrived on: 'email' or 'whatsapp'")


class ReplyResult(BaseModel):
    """Response for POST /leads/{id}/reply (classification + updated lead)."""

    classification: ReplyClassification
    lead: Lead


class FollowUpRunResult(BaseModel):
    """Response for POST /leads/follow-up (§11 second-touch sweep)."""

    followed_up: int = Field(description="Leads that received Email #2 this run")
    emails: int = Field(description="Follow-up emails sent/simulated")
    eligible_pool: int = Field(description="Contacted leads considered this run")
    mode: str = Field(description="Email mode used: 'simulate' or 'send'")
    logs: list[OutreachLog] = Field(default_factory=list)
    leads: list[Lead] = Field(default_factory=list)


@router.get("/leads", response_model=list[Lead])
def list_leads() -> list[Lead]:
    return get_store().list_leads()


@router.get("/leads/{lead_id}", response_model=Lead)
def get_lead(lead_id: str) -> Lead:
    lead = get_store().get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"No lead with id '{lead_id}'.")
    return lead


@router.get("/pipeline", response_model=dict[str, list[Lead]])
def get_pipeline() -> dict[str, list[Lead]]:
    """Leads grouped by PipelineStage for the Kanban board (every stage present)."""
    return get_store().pipeline()


def _company_knowledge_summary() -> str:
    """Best-effort 'what we sell' context for service-fit scoring; "" if RAG unavailable."""
    try:
        from app.rag.ingest import query_knowledge

        hits = query_knowledge("our services and capabilities", k=3).results
        return "\n".join(c.text for c in hits)[:1500]
    except Exception:
        return ""


def _research_and_qualify(leads: list[Lead], icp, knowledge: str, settings) -> list[Lead]:
    researched = research_leads(leads, icp, settings=settings)
    return qualify_leads(researched, icp, knowledge, settings=settings)


@router.post("/leads/research", response_model=ResearchRunResult)
async def research_and_qualify_leads() -> ResearchRunResult:
    """Deep-research + qualify the current POTENTIAL leads (§4–5), capped per run."""
    store = get_store()
    icp = store.get_icp()
    if icp is None:
        raise HTTPException(
            status_code=400, detail="No ICP set — POST /icp then /icp/discover first."
        )

    potential = store.list_leads(stage=PipelineStage.POTENTIAL)
    if not potential:
        raise HTTPException(
            status_code=400, detail="No Potential leads to research — run /icp/discover."
        )

    settings = get_settings()
    batch = potential[: settings.research_max_leads]
    skipped = len(potential) - len(batch)
    if skipped:
        logger.info("Research capped at %d leads; %d left as Potential.", len(batch), skipped)

    knowledge = await run_in_threadpool(_company_knowledge_summary)
    try:
        processed = await run_in_threadpool(_research_and_qualify, batch, icp, knowledge, settings)
    except RuntimeError as exc:  # e.g. no search provider configured
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Research/qualification failed")
        raise HTTPException(status_code=502, detail=f"Research failed: {exc}") from exc

    store.upsert_many(processed)
    qualified = sum(1 for lead in processed if lead.stage is PipelineStage.QUALIFIED)
    event_bus.publish(
        ActivityEvent(
            kind="qualification",
            message=f"Researched {len(processed)} leads: {qualified} Qualified, "
            f"{len(processed) - qualified} Not Qualified.",
            stage=PipelineStage.QUALIFIED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return ResearchRunResult(
        researched=len(processed),
        qualified=qualified,
        not_qualified=len(processed) - qualified,
        skipped=skipped,
        leads=processed,
    )


def _match_and_identify(leads: list[Lead], icp, knowledge: str, settings) -> list[Lead]:
    matched = match_services(leads, knowledge, settings=settings)
    return find_decision_makers_for(matched, icp, settings=settings)


@router.post("/leads/enrich", response_model=EnrichmentRunResult)
async def enrich_qualified_leads() -> EnrichmentRunResult:
    """Service-match (§6) + identify decision-makers (§7) for current QUALIFIED leads, capped."""
    store = get_store()
    icp = store.get_icp()  # optional here — people-search doesn't require it

    qualified = store.list_leads(stage=PipelineStage.QUALIFIED)
    if not qualified:
        raise HTTPException(
            status_code=400, detail="No Qualified leads to enrich — run /leads/research first."
        )

    settings = get_settings()
    batch = qualified[: settings.matching_max_leads]
    skipped = len(qualified) - len(batch)
    if skipped:
        logger.info("Enrichment capped at %d leads; %d left as Qualified.", len(batch), skipped)

    # RAG-grounded "what we sell" so service matching can't invent offerings (§6)
    knowledge = await run_in_threadpool(_company_knowledge_summary)
    try:
        processed = await run_in_threadpool(_match_and_identify, batch, icp, knowledge, settings)
    except RuntimeError as exc:  # e.g. no search provider configured (decision-maker search)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Service matching / decision-maker ID failed")
        raise HTTPException(status_code=502, detail=f"Enrichment failed: {exc}") from exc

    store.upsert_many(processed)
    with_service = sum(1 for lead in processed if lead.recommended_service)
    with_contacts = sum(1 for lead in processed if lead.contacts)
    event_bus.publish(
        ActivityEvent(
            kind="enrichment",
            message=f"Enriched {len(processed)} qualified leads: {with_service} matched to a "
            f"service, {with_contacts} with decision-makers.",
            stage=PipelineStage.QUALIFIED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return EnrichmentRunResult(
        enriched=len(processed),
        with_service=with_service,
        with_contacts=with_contacts,
        skipped=skipped,
        leads=processed,
    )


@router.get("/outreach", response_model=list[OutreachLog])
def list_outreach() -> list[OutreachLog]:
    """Every logged outreach action (§9) — company, contact, role, score, service, message, ..."""
    return get_store().list_outreach_logs()


def _run_outreach(
    leads: list[Lead], knowledge: str, settings
) -> tuple[list[Lead], list[OutreachLog]]:
    return outreach_leads(leads, knowledge, settings=settings)


@router.post("/leads/outreach", response_model=OutreachRunResult)
async def run_outreach() -> OutreachRunResult:
    """Draft + send/simulate personalized outreach for QUALIFIED leads with contacts (§8–9)."""
    store = get_store()
    qualified = store.list_leads(stage=PipelineStage.QUALIFIED)
    if not qualified:
        raise HTTPException(
            status_code=400, detail="No Qualified leads to contact — run /leads/enrich first."
        )

    settings = get_settings()
    ready = [lead for lead in qualified if lead.contacts]  # need someone to email
    batch = ready[: settings.outreach_max_leads]
    skipped = len(qualified) - len(batch)
    if skipped:
        logger.info("Outreach on %d leads; %d Qualified left (no contacts or over cap).",
                    len(batch), skipped)

    knowledge = await run_in_threadpool(_company_knowledge_summary)
    try:
        updated, logs = await run_in_threadpool(_run_outreach, batch, knowledge, settings)
    except RuntimeError as exc:  # e.g. EMAIL_MODE=send without Gmail creds/libs
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Outreach failed")
        raise HTTPException(status_code=502, detail=f"Outreach failed: {exc}") from exc

    store.upsert_many(updated)
    store.add_outreach_logs(logs)
    contacted = sum(1 for lead in updated if lead.stage is PipelineStage.CONTACTED)
    event_bus.publish(
        ActivityEvent(
            kind="outreach",
            message=f"Outreach ({settings.email_mode}): {len(logs)} emails to {contacted} leads.",
            stage=PipelineStage.CONTACTED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return OutreachRunResult(
        contacted=contacted,
        emails=len(logs),
        skipped=skipped,
        mode=settings.email_mode,
        logs=logs,
        leads=updated,
    )


def _classify_and_apply(lead: Lead, text: str, channel: str, settings):
    return apply_reply(lead, text, channel=channel, settings=settings)


@router.post("/leads/{lead_id}/reply", response_model=ReplyResult)
async def record_reply(lead_id: str, reply: IncomingReply) -> ReplyResult:
    """Classify an inbound prospect reply (§10) and advance the lead's stage accordingly.

    Canonical inbound sink: the WhatsApp webhook (Phase 9) and any email polling funnel their
    messages here, so every channel shares one classifier and one stage-transition table.
    """
    store = get_store()
    lead = store.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"No lead with id '{lead_id}'.")

    settings = get_settings()
    try:
        updated, classification = await run_in_threadpool(
            _classify_and_apply, lead, reply.text, reply.channel, settings
        )
    except RuntimeError as exc:  # e.g. no LLM provider configured
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Reply classification failed")
        raise HTTPException(status_code=502, detail=f"Classification failed: {exc}") from exc

    store.upsert_lead(updated)
    event_bus.publish(
        ActivityEvent(
            kind="reply",
            message=f"{updated.company_name} replied — '{classification.category.value}' "
            f"-> {updated.stage.value}.",
            stage=updated.stage.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return ReplyResult(classification=classification, lead=updated)


def _run_follow_ups(leads: list[Lead], knowledge: str, force: bool, settings):
    return run_follow_ups(leads, knowledge, force=force, settings=settings)


@router.post("/leads/follow-up", response_model=FollowUpRunResult)
async def run_follow_up(force: bool = False) -> FollowUpRunResult:
    """Send Email #2 to CONTACTED leads still awaiting a reply (§11).

    Honours the 3-day wait by default; pass ``?force=true`` to bypass it (for the 90-sec demo).
    """
    store = get_store()
    contacted = store.list_leads(stage=PipelineStage.CONTACTED)
    if not contacted:
        raise HTTPException(
            status_code=400, detail="No Contacted leads to follow up — run /leads/outreach first."
        )

    settings = get_settings()
    knowledge = await run_in_threadpool(_company_knowledge_summary)
    try:
        updated, logs = await run_in_threadpool(
            _run_follow_ups, contacted, knowledge, force, settings
        )
    except RuntimeError as exc:  # e.g. EMAIL_MODE=send without Gmail creds/libs
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Follow-up run failed")
        raise HTTPException(status_code=502, detail=f"Follow-up failed: {exc}") from exc

    store.upsert_many(updated)
    store.add_outreach_logs(logs)
    if logs:
        event_bus.publish(
            ActivityEvent(
                kind="follow_up",
                message=f"Follow-up ({settings.email_mode}): {len(logs)} second-touch emails "
                f"to {len(updated)} leads.",
                stage=PipelineStage.CONTACTED.value,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
    return FollowUpRunResult(
        followed_up=len(updated),
        emails=len(logs),
        eligible_pool=len(contacted),
        mode=settings.email_mode,
        logs=logs,
        leads=updated,
    )
