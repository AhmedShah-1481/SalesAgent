"""Decision-Maker Identification node (§7) — Phase 5.

For each QUALIFIED company, find the people worth contacting — CEO/Founder/Co-Founder, CTO,
CFO, COO, VP/Head of Sales, Head of Support, or whichever role is most relevant to the
recommended service — from targeted web searches, then extract them (grounded, no invented
people) prioritized by the service being sold. Enriches the lead's `contacts` in place
(stage unchanged). The core is dependency-injected (search_fn / extractor) so it unit-tests
without live search or an LLM call. Emails are captured only when present in the evidence
(§8 uses them "when available").
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.matching import DecisionMakerList


def _people_queries(lead: Lead, limit: int) -> list[str]:
    name = lead.company_name
    queries = [
        f"{name} leadership team CEO founder executives",
        f"{name} VP sales head of sales head of support contact",
        f"{name} CTO CFO COO management team LinkedIn",
    ]
    if lead.recommended_service:
        # bias the search toward whoever owns the problem the service solves
        queries.insert(1, f"{name} decision maker for {lead.recommended_service}")
    return queries[:limit]


def _extract_prompt(lead: Lead, gathered: str) -> str:
    svc = lead.recommended_service or "the recommended service"
    return (
        "Extract the real decision-makers at the prospect company from the evidence below. Use "
        "ONLY people actually named in the evidence — do NOT invent names, titles, or emails. "
        "Prefer CEO/Founder/Co-Founder, CTO, CFO, COO, VP/Head of Sales, Head of Support, or the "
        f"roles most relevant to selling '{svc}'. Order the list most-relevant first. Include "
        "email/LinkedIn only if present in the evidence; otherwise leave them null. For each "
        "person set 'relevance' to why they matter for this service.\n\n"
        f"Prospect: {lead.company_name}"
        + (f" ({lead.domain})" if lead.domain else "")
        + f"\n\nEvidence:\n{gathered}"
    )


def find_decision_makers(
    lead: Lead,
    icp: ICP | None = None,
    *,
    search_fn=None,
    extractor=None,
    settings=None,
) -> Lead:
    """Search + grounded-extract decision-makers for a qualified lead (stage unchanged)."""
    settings = settings or get_settings()
    if search_fn is None:
        from app.services.search import search_web

        search_fn = search_web
    if extractor is None:
        from app.llm.parsers import structured

        extractor = structured(DecisionMakerList, model=settings.llm_model_cheap)

    blocks: list[str] = []
    seen: set[str] = set()
    for query in _people_queries(lead, settings.decision_maker_queries):
        for r in search_fn(query, max_results=settings.decision_maker_results_per_query):
            url = r.get("url", "")
            if url and url in seen:
                continue
            seen.add(url)
            blocks.append(f"{r.get('title', '')} ({url})\n{r.get('content', '')}")

    now = datetime.now(tz=timezone.utc)
    if not blocks:
        # no evidence — leave contacts as-is rather than invent people
        return lead.model_copy(update={"updated_at": now})

    result: DecisionMakerList = extractor.invoke(_extract_prompt(lead, "\n\n".join(blocks)))
    contacts = result.contacts[: settings.max_decision_makers]
    return lead.model_copy(update={"contacts": contacts, "updated_at": now})


def find_decision_makers_for(
    leads: list[Lead], icp: ICP | None = None, *, settings=None, **kwargs
) -> list[Lead]:
    settings = settings or get_settings()
    return [find_decision_makers(lead, icp, settings=settings, **kwargs) for lead in leads]


def run(state: PipelineState) -> dict:
    icp = state.get("icp")
    leads = [lead for lead in (state.get("leads") or []) if lead.stage is PipelineStage.QUALIFIED]
    if not leads:
        return {}
    enriched = find_decision_makers_for(leads, icp)
    total = sum(len(lead.contacts) for lead in enriched)
    event = ActivityEvent(
        kind="decision_makers",
        message=f"Identified {total} decision-makers across {len(enriched)} qualified leads.",
        stage=PipelineStage.QUALIFIED.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    # NOTE: batch `leads` mutation needs an id-upsert reducer (P10); canonical driver is
    # POST /leads/enrich operating on the store.
    return {"leads": enriched, "activity": [event]}
