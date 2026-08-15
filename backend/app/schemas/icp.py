"""Ideal Customer Profile (§3)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ICP(BaseModel):
    location: str | None = Field(None, description="Target location / region")
    industry: str | None = Field(None, description="Target industry or market")
    company_size: str | None = Field(None, description="Company size or qualification criteria")
    special_targeting: str | None = Field(
        None, description="Specific problem, use case, service, or customer type to target"
    )
    notes: str | None = None
