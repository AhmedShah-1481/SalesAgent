"""Service Matching node (§6) — Phase 5.

For each QUALIFIED prospect, pick which of the company's OWN products/services best fits,
grounded in the RAG knowledge base — §6 forbids inventing services, so the matcher may only
choose from the offerings text passed in. Enriches the lead in place (sets recommended_service
+ service_rationale) WITHOUT changing its QUALIFIED stage; outreach (§8) is the next pipeline
transition. The core is dependency-injected (matcher) so it unit-tests without an LLM call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead
from app.schemas.matching import ServiceMatch


def _match_prompt(lead: Lead, knowledge: str) -> str:
    dossier = lead.research.model_dump_json(indent=2) if lead.research else "{}"
    offerings = knowledge.strip() or "(no services provided)"
    return (
        "You match a qualified B2B prospect to ONE of OUR OWN services. You may ONLY choose "
        "from the services described in 'Our offerings' below — never invent a service. If none "
        "genuinely fit, return null for recommended_service and explain why. Ground the rationale "
        "in the prospect's specific problems / buying signals (e.g. high WhatsApp inquiry volume "
        "-> WhatsApp AI chatbot). List any other documented services that could also fit.\n\n"
        f"Our offerings (from our knowledge base):\n{offerings}\n\n"
        f"Prospect: {lead.company_name}"
        + (f" ({lead.domain})" if lead.domain else "")
        + "\n"
        + (f"Qualification rationale: {lead.explanation}\n" if lead.explanation else "")
        + f"\nResearch dossier:\n{dossier}"
    )


def match_service(lead: Lead, knowledge: str = "", *, matcher=None, settings=None) -> Lead:
    """Recommend one grounded service for a qualified lead (stage unchanged)."""
    settings = settings or get_settings()
    if matcher is None:
        from app.llm.parsers import structured

        matcher = structured(ServiceMatch, model=settings.llm_model)

    result: ServiceMatch = matcher.invoke(_match_prompt(lead, knowledge))
    return lead.model_copy(
        update={
            "recommended_service": result.recommended_service,
            "service_rationale": result.rationale,
            "updated_at": datetime.now(tz=timezone.utc),
        }
    )


def match_services(
    leads: list[Lead], knowledge: str = "", *, settings=None, **kwargs
) -> list[Lead]:
    settings = settings or get_settings()
    return [match_service(lead, knowledge, settings=settings, **kwargs) for lead in leads]


def run(state: PipelineState) -> dict:
    leads = [lead for lead in (state.get("leads") or []) if lead.stage is PipelineStage.QUALIFIED]
    if not leads:
        return {}
    matched = match_services(leads, state.get("company_knowledge", "") or "")
    named = sum(1 for lead in matched if lead.recommended_service)
    event = ActivityEvent(
        kind="service_matching",
        message=f"Matched a service for {named}/{len(matched)} qualified leads.",
        stage=PipelineStage.QUALIFIED.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    # NOTE: full-graph batch mutation of `leads` needs an id-upsert reducer (P10); the
    # canonical Phase 5 driver is POST /leads/enrich operating on the store.
    return {"leads": matched, "activity": [event]}
