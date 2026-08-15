"""Cheap Filtering node (§3) — Phase 3.

Eliminates obviously irrelevant candidates BEFORE expensive deep research (§4) runs on
them. One cheap batched LLM call triages every candidate against the ICP; survivors are
promoted DISCOVERED -> POTENTIAL. Intentionally lenient — deep research does the real
qualification (§5), so this only drops the clearly-wrong (wrong industry/location,
directories, vendors, non-prospects). Core is dependency-injected for unit testing.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.discovery import FilterResponse
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead


def _filter_prompt(icp: ICP, candidates: list[Lead]) -> str:
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
    listed = "\n".join(
        f"- {lead.company_name}"
        + (f" ({lead.domain})" if lead.domain else "")
        + (f" — {lead.evidence[0]}" if lead.evidence else "")
        for lead in candidates
    )
    return (
        "You are cheaply triaging candidate companies for a B2B sales pipeline BEFORE any "
        "expensive research. Return a keep/drop verdict for EVERY company by exact name.\n"
        "Drop only the clearly-wrong: wrong industry or location vs the ICP, directories / "
        "listicles / marketplaces, the seller's own vendors, or entries that are not real "
        "prospect companies. When unsure, KEEP — deep research will qualify them later.\n\n"
        f"Ideal Customer Profile:\n{icp_lines}\n\n"
        f"Candidates:\n{listed}"
    )


def filter_candidates(
    candidates: list[Lead],
    icp: ICP,
    *,
    judge=None,
    settings=None,
) -> tuple[list[Lead], list[Lead]]:
    """Triage candidates -> (kept as POTENTIAL, dropped). Unknown verdicts default to keep."""
    if not candidates:
        return [], []
    settings = settings or get_settings()
    if judge is None:
        from app.llm.parsers import structured

        judge = structured(FilterResponse, model=settings.llm_model_cheap)

    response: FilterResponse = judge.invoke(_filter_prompt(icp, candidates))
    verdicts = {v.name.strip().lower(): v for v in response.verdicts}

    now = datetime.now(tz=timezone.utc)
    kept: list[Lead] = []
    dropped: list[Lead] = []
    for lead in candidates:
        verdict = verdicts.get(lead.company_name.strip().lower())
        # Absent verdict -> keep (never silently drop something the LLM forgot to rate).
        if verdict is None or verdict.keep:
            kept.append(
                lead.model_copy(
                    update={
                        "stage": PipelineStage.POTENTIAL,
                        "explanation": verdict.reason if verdict else None,
                        "updated_at": now,
                    }
                )
            )
        else:
            dropped.append(
                lead.model_copy(
                    update={
                        "explanation": f"Cheap filter dropped: {verdict.reason}",
                        "updated_at": now,
                    }
                )
            )
    return kept, dropped


def run(state: PipelineState) -> dict:
    candidates = state.get("candidates") or []
    icp = state.get("icp")
    if not candidates or not icp:
        return {}
    kept, dropped = filter_candidates(candidates, icp)
    event = ActivityEvent(
        kind="cheap_filter",
        message=f"Cheap filter kept {len(kept)} and dropped {len(dropped)} of "
        f"{len(candidates)} candidates.",
        stage=PipelineStage.POTENTIAL.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    return {"leads": kept, "activity": [event]}
