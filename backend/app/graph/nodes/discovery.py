"""Lead Discovery node (§3) — Phase 3.

Staged, not brute-force: build search queries from the ICP, pull real web results
(Tavily -> Serper), then have a *cheap* LLM extract the companies actually named in those
results (grounded — it must not invent companies). Emits DISCOVERED candidates for the
cheap-filter stage to triage. The core ``discover_leads`` is pure and dependency-injected
so it is unit-testable without live search/LLM calls.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.discovery import CandidateExtraction
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead


def _build_queries(icp: ICP, knowledge: str = "") -> list[str]:
    industry = icp.industry or "companies"
    where = f" in {icp.location}" if icp.location else ""
    base = f"{industry}{where}".strip()

    queries = [f"list of {base}"]
    if icp.special_targeting:
        queries.append(f"{base} {icp.special_targeting}")
    if icp.company_size:
        queries.append(f"{base} {icp.company_size}")
    if knowledge and icp.special_targeting:
        queries.append(f"{industry}{where} that need {icp.special_targeting}")
    # de-dup while preserving order, keep it lean (each query is a paid search call)
    seen: set[str] = set()
    return [q for q in queries if not (q in seen or seen.add(q))][:3]


def _slug(name: str, domain: str | None) -> str:
    basis = (domain or name).lower()
    basis = re.sub(r"^https?://", "", basis).split("/")[0]
    slug = re.sub(r"[^a-z0-9]+", "-", basis).strip("-")
    return slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "lead"


def _format_results(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')} ({r.get('url', '')})\n{r.get('content', '')}")
    return "\n\n".join(lines)


def _extraction_prompt(icp: ICP, results: list[dict], knowledge: str) -> str:
    icp_lines = "\n".join(
        f"- {label}: {value}"
        for label, value in (
            ("Location", icp.location),
            ("Industry / market", icp.industry),
            ("Company size / criteria", icp.company_size),
            ("Special targeting", icp.special_targeting),
        )
        if value
    ) or "- (no constraints given)"
    sell = f"\n\nWhat WE sell (for relevance only):\n{knowledge.strip()}" if knowledge else ""
    return (
        "You extract real prospect companies from web search results for a B2B sales team.\n"
        "Return ONLY companies that are actually named in the results below — never invent "
        "or guess companies. Exclude directories, listicles, marketplaces, news outlets, and "
        "the search team's own vendors; we want prospective CUSTOMER companies.\n\n"
        f"Ideal Customer Profile:\n{icp_lines}{sell}\n\n"
        f"Search results:\n{_format_results(results)}"
    )


def discover_leads(
    icp: ICP,
    knowledge: str = "",
    *,
    search_fn=None,
    extractor=None,
    settings=None,
) -> list[Lead]:
    """Search + grounded extraction -> DISCOVERED candidate leads (no filtering yet)."""
    settings = settings or get_settings()
    if search_fn is None:
        from app.services.search import search_web

        search_fn = search_web
    if extractor is None:
        from app.llm.parsers import structured

        extractor = structured(CandidateExtraction, model=settings.llm_model_cheap)

    # 1. gather real search results across a few ICP-derived queries (dedup by url)
    results: list[dict] = []
    seen_urls: set[str] = set()
    for query in _build_queries(icp, knowledge):
        for r in search_fn(query, max_results=settings.discovery_results_per_query):
            url = r.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(r)
    if not results:
        return []

    # 2. grounded extraction of company names from those results
    extraction: CandidateExtraction = extractor.invoke(_extraction_prompt(icp, results, knowledge))

    # 3. materialize DISCOVERED leads, de-duplicated by stable id, capped
    now = datetime.now(tz=timezone.utc)
    leads: dict[str, Lead] = {}
    for c in extraction.companies:
        if not c.name or not c.name.strip():
            continue
        lead_id = _slug(c.name, c.domain)
        if lead_id in leads:
            continue
        leads[lead_id] = Lead(
            id=lead_id,
            company_name=c.name.strip(),
            domain=c.domain,
            stage=PipelineStage.DISCOVERED,
            evidence=[c.reason] if c.reason else [],
            created_at=now,
            updated_at=now,
        )
        if len(leads) >= settings.discovery_max_candidates:
            break
    return list(leads.values())


def run(state: PipelineState) -> dict:
    icp = state.get("icp")
    if not icp:
        return {}
    candidates = discover_leads(icp, state.get("company_knowledge", "") or "")
    event = ActivityEvent(
        kind="discovery",
        message=f"Discovered {len(candidates)} candidate companies from the ICP.",
        stage=PipelineStage.DISCOVERED.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    return {"candidates": candidates, "activity": [event]}
