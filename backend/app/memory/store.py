"""Lead + ICP + meeting store, with two interchangeable backends.

`get_store()` returns the durable Supabase-backed `SupabaseStore` when Supabase is
configured (long-term memory, §13), otherwise the process-local `InMemoryStore` below —
same graceful-degradation pattern as EMAIL_MODE/MEETING_MODE, so the app still boots and
the tests still run with no keys. Both classes expose the identical method surface, so the
HTTP layer (`/icp`, `/leads`, `/pipeline`, `/meetings`, `/outreach`) depends on `get_store()`
and never on the storage backend directly.

The in-memory store is deliberately non-durable (lost on restart); Supabase is what makes
the full pipeline (§14) persist. A lock guards the dicts since sync store calls run in
FastAPI's threadpool.
"""
from __future__ import annotations

import threading
from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.meeting import Meeting

if TYPE_CHECKING:
    from app.memory.supabase.repository import SupabaseStore

logger = get_logger(__name__)


class InMemoryStore:
    def __init__(self) -> None:
        self._icp: ICP | None = None
        self._leads: dict[str, Lead] = {}
        self._outreach_logs: list[OutreachLog] = []
        self._meetings: dict[str, Meeting] = {}  # keyed by lead_id (one live meeting per lead)
        self._lock = threading.Lock()

    # ── ICP (§2) ─────────────────────────────────────────
    def set_icp(self, icp: ICP) -> ICP:
        with self._lock:
            self._icp = icp
        return icp

    def get_icp(self) -> ICP | None:
        return self._icp

    # ── Leads ────────────────────────────────────────────
    def upsert_lead(self, lead: Lead) -> Lead:
        with self._lock:
            self._leads[lead.id] = lead
        return lead

    def upsert_many(self, leads: list[Lead]) -> list[Lead]:
        with self._lock:
            for lead in leads:
                self._leads[lead.id] = lead
        return leads

    def get_lead(self, lead_id: str) -> Lead | None:
        return self._leads.get(lead_id)

    def get_lead_by_phone(self, phone: str) -> Lead | None:
        """Find the lead with a contact whose number matches ``phone`` (§9 inbound WhatsApp)."""
        from app.core.phone import phones_match

        for lead in self._leads.values():
            if any(phones_match(c.phone, phone) for c in lead.contacts):
                return lead
        return None

    def list_leads(self, stage: PipelineStage | None = None) -> list[Lead]:
        leads = list(self._leads.values())
        if stage is not None:
            leads = [lead for lead in leads if lead.stage is stage]
        return leads

    def pipeline(self) -> dict[str, list[Lead]]:
        """Leads grouped by pipeline stage (every stage present, even if empty)."""
        grouped: dict[str, list[Lead]] = {stage.value: [] for stage in PipelineStage}
        for lead in self._leads.values():
            grouped[lead.stage.value].append(lead)
        return grouped

    # ── Outreach log (§9) ────────────────────────────────
    def add_outreach_logs(self, logs: list[OutreachLog]) -> None:
        with self._lock:
            self._outreach_logs.extend(logs)

    def list_outreach_logs(self) -> list[OutreachLog]:
        return list(self._outreach_logs)

    # ── Meetings (§12) ───────────────────────────────────
    def upsert_meeting(self, meeting: Meeting) -> Meeting:
        """Store the finalized meeting for a lead (one live meeting per lead_id)."""
        with self._lock:
            self._meetings[meeting.lead_id or meeting.company] = meeting
        return meeting

    def get_meeting(self, lead_id: str) -> Meeting | None:
        return self._meetings.get(lead_id)

    def list_meetings(self) -> list[Meeting]:
        return list(self._meetings.values())

    def clear(self) -> None:
        with self._lock:
            self._icp = None
            self._leads.clear()
            self._outreach_logs.clear()
            self._meetings.clear()


@lru_cache
def get_store() -> InMemoryStore | SupabaseStore:
    """Return the singleton store: Supabase when configured (§13), else in-memory.

    `MEMORY_BACKEND` forces the choice — "supabase" | "memory" | "auto" (default: use
    Supabase iff SUPABASE_URL and SUPABASE_KEY are both set). If Supabase is selected but
    fails to initialise, we log and fall back to the in-memory store so the app still boots.
    """
    settings = get_settings()
    backend = (settings.memory_backend or "auto").strip().lower()
    has_keys = bool(settings.supabase_url and settings.supabase_key)
    use_supabase = backend == "supabase" or (backend == "auto" and has_keys)

    if use_supabase:
        try:
            from app.memory.supabase.repository import SupabaseStore

            store = SupabaseStore()
            logger.info("Long-term memory: Supabase backend (§13).")
            return store
        except Exception:
            logger.warning(
                "Supabase memory selected but unavailable; using in-memory store.", exc_info=True
            )
    logger.info("Long-term memory: in-memory backend (non-durable — set SUPABASE_* to persist).")
    return InMemoryStore()
