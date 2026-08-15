"""Deep Company Research node (§4) — Phase 4.

For each promising (POTENTIAL) lead, gather grounded evidence — company profile, people,
news, funding, technology, and buying signals — from targeted web searches plus an
optional best-effort website fetch, then synthesize it into a structured `ResearchProfile`
(the LLM may only use the gathered text — no inventing facts). Promotes POTENTIAL ->
RESEARCHING. The core is dependency-injected (search_fn / scrape_fn / synthesizer) so it
unit-tests without live search, scraping, or LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.core.logging import get_logger
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.research import ResearchProfile

logger = get_logger(__name__)


def _research_queries(lead: Lead, limit: int) -> list[str]:
    name = lead.company_name
    site = f" {lead.domain}" if lead.domain else ""
    queries = [
        f"{name}{site} company overview what they do",
        f"{name} news recent announcements",
        f"{name} funding revenue growth employees",
        f"{name} technology stack tools integrations",
        f"{name} hiring challenges customer support operations",
    ]
    return queries[:limit]


def _synthesis_prompt(lead: Lead, icp: ICP, gathered: str) -> str:
    return (
        "You are a B2B sales researcher building a factual dossier on a prospect company. "
        "Use ONLY the evidence provided below — do not invent or assume facts. Leave a field "
        "null if the evidence does not cover it. Be concise and specific.\n\n"
        f"Prospect company: {lead.company_name}"
        + (f" ({lead.domain})" if lead.domain else "")
        + "\n"
        f"(Our ICP, for relevance: industry={icp.industry}, location={icp.location}, "
        f"size={icp.company_size}, focus={icp.special_targeting})\n\n"
        f"Evidence:\n{gathered}"
    )


def research_lead(
    lead: Lead,
    icp: ICP,
    *,
    search_fn=None,
    scrape_fn=None,
    synthesizer=None,
    settings=None,
) -> Lead:
    """Gather evidence + synthesize a ResearchProfile -> lead promoted to RESEARCHING."""
    settings = settings or get_settings()
    if search_fn is None:
        from app.services.search import search_web

        search_fn = search_web
    if synthesizer is None:
        from app.llm.parsers import structured

        synthesizer = structured(ResearchProfile, model=settings.llm_model_cheap)
    if scrape_fn is None and settings.enable_scraping:
        from app.services.scraper import scrape as scrape_fn

    # 1. gather search evidence across targeted queries (dedup by url)
    blocks: list[str] = []
    sources: list[str] = []
    seen: set[str] = set()
    for query in _research_queries(lead, settings.research_queries_per_lead):
        for r in search_fn(query, max_results=settings.research_results_per_query):
            url = r.get("url", "")
            if url and url in seen:
                continue
            seen.add(url)
            if url:
                sources.append(url)
            blocks.append(f"{r.get('title', '')} ({url})\n{r.get('content', '')}")

    # 2. optional best-effort website text
    if scrape_fn is not None and lead.domain:
        site_text = scrape_fn(lead.domain)
        if site_text:
            blocks.append(f"[Company website {lead.domain}]\n{site_text}")
            sources.append(lead.domain)

    now = datetime.now(tz=timezone.utc)
    if not blocks:
        # nothing found — still advance the stage with an empty dossier
        return lead.model_copy(
            update={
                "stage": PipelineStage.RESEARCHING,
                "research": ResearchProfile(),
                "updated_at": now,
            }
        )

    # 3. grounded synthesis into a structured dossier. A single lead's synthesis must
    #    never crash the whole batch (e.g. a transient LLM/provider error mid-demo), so
    #    degrade to an empty dossier — the lead still advances to RESEARCHING with its
    #    gathered sources and qualification can proceed on whatever evidence exists.
    try:
        profile: ResearchProfile = synthesizer.invoke(
            _synthesis_prompt(lead, icp, "\n\n".join(blocks))
        )
    except Exception:  # noqa: BLE001 - resilience: one lead must not fail the whole run
        logger.exception(
            "Research synthesis failed for %s; using empty dossier.", lead.company_name
        )
        profile = ResearchProfile()
    if not profile.sources:
        profile.sources = sources[:8]
    if not profile.website and lead.domain:
        profile.website = lead.domain

    return lead.model_copy(
        update={"stage": PipelineStage.RESEARCHING, "research": profile, "updated_at": now}
    )


def research_leads(leads: list[Lead], icp: ICP, *, settings=None, **kwargs) -> list[Lead]:
    """Research up to ``research_max_leads`` POTENTIAL leads (cost/latency cap)."""
    settings = settings or get_settings()
    return [research_lead(lead, icp, settings=settings, **kwargs) for lead in leads]


def run(state: PipelineState) -> dict:
    icp = state.get("icp")
    leads = [lead for lead in (state.get("leads") or []) if lead.stage is PipelineStage.POTENTIAL]
    if not icp or not leads:
        return {}
    researched = research_leads(leads[: get_settings().research_max_leads], icp)
    event = ActivityEvent(
        kind="deep_research",
        message=f"Deep-researched {len(researched)} potential leads.",
        stage=PipelineStage.RESEARCHING.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    # NOTE: full-graph batch mutation of `leads` needs an id-upsert reducer (P10); the
    # canonical Phase 4 driver is POST /leads/research operating on the store.
    return {"leads": researched, "activity": [event]}
