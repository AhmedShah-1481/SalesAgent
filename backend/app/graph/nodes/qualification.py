"""Lead Qualification & Confidence Score node (§5) — Phase 4.

Scores each researched company against the ICP and our own offering: a 0-100 confidence
with a written explanation grounded in the §5 factors (ICP fit, problem fit, service fit,
buying signals, company size, location, evidence quality). Leads at/above the configured
threshold become QUALIFIED; the rest become NOT_QUALIFIED — the system deliberately says
"no" (goal is the best leads, not the most contacts). Core is dependency-injected.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.activity import ActivityEvent
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.research import QualificationResult


def _qualification_prompt(lead: Lead, icp: ICP, knowledge: str) -> str:
    dossier = lead.research.model_dump_json(indent=2) if lead.research else "{}"
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
    sell = f"\n\nWhat WE sell (for service-fit):\n{knowledge.strip()}" if knowledge else ""
    return (
        "You qualify a researched prospect for a B2B sales team. Output a confidence score "
        "from 0 to 100 and a concise explanation. Base every judgment ONLY on the dossier and "
        "ICP below — do not invent facts; weak/absent evidence should LOWER confidence. The "
        "explanation must reference ICP fit, problem fit, service fit, buying signals, company "
        "size, location, and evidence quality. Fill the breakdown sub-scores (0-100) for each.\n\n"
        f"Ideal Customer Profile:\n{icp_lines}{sell}\n\n"
        f"Prospect: {lead.company_name}"
        + (f" ({lead.domain})" if lead.domain else "")
        + "\n\n"
        f"Research dossier:\n{dossier}"
    )


def qualify_lead(
    lead: Lead,
    icp: ICP,
    knowledge: str = "",
    *,
    scorer=None,
    settings=None,
) -> Lead:
    """Score a researched lead -> QUALIFIED or NOT_QUALIFIED with a written explanation."""
    settings = settings or get_settings()
    if scorer is None:
        from app.llm.parsers import structured

        scorer = structured(QualificationResult, model=settings.llm_model)

    result: QualificationResult = scorer.invoke(_qualification_prompt(lead, icp, knowledge))
    stage = (
        PipelineStage.QUALIFIED
        if result.confidence >= settings.qualification_threshold
        else PipelineStage.NOT_QUALIFIED
    )
    return lead.model_copy(
        update={
            "stage": stage,
            "confidence": result.confidence,
            "explanation": result.explanation,
            "score_breakdown": result.breakdown,
            "updated_at": datetime.now(tz=timezone.utc),
        }
    )


def qualify_leads(leads: list[Lead], icp: ICP, knowledge: str = "", *, settings=None, **kwargs):
    settings = settings or get_settings()
    return [qualify_lead(lead, icp, knowledge, settings=settings, **kwargs) for lead in leads]


def run(state: PipelineState) -> dict:
    icp = state.get("icp")
    leads = [lead for lead in (state.get("leads") or []) if lead.stage is PipelineStage.RESEARCHING]
    if not icp or not leads:
        return {}
    qualified = qualify_leads(leads, icp, state.get("company_knowledge", "") or "")
    kept = sum(1 for lead in qualified if lead.stage is PipelineStage.QUALIFIED)
    event = ActivityEvent(
        kind="qualification",
        message=f"Qualified {kept}/{len(qualified)} researched leads "
        f"(threshold {get_settings().qualification_threshold:.0f}%).",
        stage=PipelineStage.QUALIFIED.value,
        timestamp=datetime.now(tz=timezone.utc),
    )
    return {"leads": qualified, "activity": [event]}
