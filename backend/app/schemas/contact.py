"""Decision-maker / contact (§7)."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class Contact(BaseModel):
    name: str | None = None
    role: str | None = Field(
        None, description="e.g. CEO, Founder, CTO, CFO, COO, VP Sales, Head of Support"
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        None, description="Phone / WhatsApp number when known (§18) — enables reply mapping"
    )
    linkedin: str | None = None
    relevance: str | None = Field(
        None, description="Why this person is relevant to the recommended service"
    )
