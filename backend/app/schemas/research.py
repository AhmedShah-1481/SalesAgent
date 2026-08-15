"""Deep research (§4) + qualification (§5) models — Phase 4.

`ResearchProfile` is the grounded dossier synthesized from web evidence (one field per §4
facet). `QualificationResult` is what the scoring LLM returns; `ScoreBreakdown` lives here
(not in lead.py) so both Lead and the qualifier can use it without an import cycle.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Sub-scores (0-100) backing the headline confidence % — the §5 factors."""

    icp_fit: float | None = None
    problem_fit: float | None = None
    service_fit: float | None = None
    buying_signals: float | None = None
    company_size: float | None = None
    location: float | None = None
    evidence_quality: float | None = None


class ResearchProfile(BaseModel):
    """Grounded research dossier for a company (§4). Fields are null when unknown."""

    website: str | None = None
    profile_summary: str | None = Field(None, description="Company profile / what they do")
    employees_departments: str | None = Field(None, description="Employees & key departments")
    news: str | None = Field(None, description="News & recent events")
    funding_growth: str | None = Field(None, description="Funding & growth signals")
    technologies: str | None = Field(None, description="Technology / tools / integrations in use")
    problems_signals: str | None = Field(None, description="Business problems / buying signals")
    other_evidence: str | None = Field(None, description="Any other qualification evidence")
    sources: list[str] = Field(default_factory=list, description="Source URLs the dossier draws on")


class QualificationResult(BaseModel):
    """LLM qualification verdict for one researched company (§5)."""

    confidence: float = Field(ge=0, le=100, description="Lead confidence percentage, 0-100")
    explanation: str = Field(
        description="Written rationale referencing ICP fit, problem/service fit, buying "
        "signals, company size, location, and evidence quality"
    )
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
