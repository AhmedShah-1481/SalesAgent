"""Discovery/cheap-filter LLM I/O + API response models (§2–3) — Phase 3.

The *Candidate*/*Filter* models are the schemas the LLM is forced to fill via
``.with_structured_output(...)`` (grounded extraction from real search snippets,
then a cheap keep/drop triage). ``DiscoveryResult`` is what the HTTP endpoint returns.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.icp import ICP
from app.schemas.lead import Lead


# ── LLM extraction: pull real company names out of search snippets ──
class CandidateCompany(BaseModel):
    name: str = Field(description="Company name exactly as it appears in the results")
    domain: str | None = Field(None, description="Primary website domain if present, e.g. acme.com")
    reason: str | None = Field(None, description="One line: why this looks like an ICP match")


class CandidateExtraction(BaseModel):
    companies: list[CandidateCompany] = Field(default_factory=list)


# ── LLM cheap filter: keep/drop each candidate against the ICP ──
class FilterVerdict(BaseModel):
    name: str = Field(description="Candidate company name being judged")
    keep: bool = Field(description="True to keep for deep research, False to eliminate")
    reason: str = Field(description="Short justification for the keep/drop decision")


class FilterResponse(BaseModel):
    verdicts: list[FilterVerdict] = Field(default_factory=list)


# ── API response for POST /icp/discover ──
class DiscoveryResult(BaseModel):
    icp: ICP
    discovered: int = Field(description="Raw candidates found by search")
    kept: int = Field(description="Candidates surviving cheap filtering (Potential leads)")
    dropped: int = Field(description="Candidates eliminated as obviously irrelevant")
    leads: list[Lead] = Field(default_factory=list)
