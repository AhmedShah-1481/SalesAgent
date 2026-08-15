"""Long-term memory on Supabase/Postgres (§13) — Phase 10.

Persists ICP, leads, outreach logs, and meetings so the full sales pipeline (§14) survives
restarts — company history, contacts, emails, replies, objections, lead scores, follow-ups,
meetings, and final status all live inside the Pydantic models this store round-trips.

``SupabaseStore`` exposes exactly the same methods as ``InMemoryStore`` (see app.memory.store),
so ``get_store()`` swaps between them and the routers never change. Objects are stored as JSONB;
``leads.stage`` is denormalized to a column so the Kanban query groups without deserializing rows.

The supabase client is created lazily (client.get_supabase), so importing this module never
requires the ``supabase`` package or any keys — a test can inject a fake client instead.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.memory.supabase.models import (
    ICP_SINGLETON_ID,
    ICP_TABLE,
    LEADS_TABLE,
    MEETINGS_TABLE,
    OUTREACH_LOGS_TABLE,
)
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.meeting import Meeting

logger = get_logger(__name__)


class SupabaseStore:
    """Durable store backed by Supabase. Drop-in replacement for InMemoryStore."""

    def __init__(self, client=None) -> None:
        if client is None:
            from app.memory.supabase.client import get_supabase

            client = get_supabase()  # raises if unconfigured — get_store() handles the fallback
        self._client = client

    def _table(self, name: str):
        return self._client.table(name)

    # ── ICP (§2) ─────────────────────────────────────────
    def set_icp(self, icp: ICP) -> ICP:
        self._table(ICP_TABLE).upsert(
            {"id": ICP_SINGLETON_ID, "data": icp.model_dump(mode="json")}
        ).execute()
        return icp

    def get_icp(self) -> ICP | None:
        rows = self._table(ICP_TABLE).select("data").eq("id", ICP_SINGLETON_ID).execute().data
        return ICP(**rows[0]["data"]) if rows else None

    # ── Leads ────────────────────────────────────────────
    @staticmethod
    def _lead_row(lead: Lead) -> dict:
        return {"id": lead.id, "stage": lead.stage.value, "data": lead.model_dump(mode="json")}

    def upsert_lead(self, lead: Lead) -> Lead:
        self._table(LEADS_TABLE).upsert(self._lead_row(lead)).execute()
        return lead

    def upsert_many(self, leads: list[Lead]) -> list[Lead]:
        if leads:
            self._table(LEADS_TABLE).upsert([self._lead_row(lead) for lead in leads]).execute()
        return leads

    def get_lead(self, lead_id: str) -> Lead | None:
        rows = self._table(LEADS_TABLE).select("data").eq("id", lead_id).execute().data
        return Lead(**rows[0]["data"]) if rows else None

    def get_lead_by_phone(self, phone: str) -> Lead | None:
        """Find the lead with a contact whose number matches ``phone`` (§9 inbound WhatsApp)."""
        from app.core.phone import phones_match

        for lead in self.list_leads():
            if any(phones_match(c.phone, phone) for c in lead.contacts):
                return lead
        return None

    def list_leads(self, stage: PipelineStage | None = None) -> list[Lead]:
        query = self._table(LEADS_TABLE).select("data")
        if stage is not None:
            query = query.eq("stage", stage.value)
        rows = query.execute().data
        return [Lead(**row["data"]) for row in rows]

    def pipeline(self) -> dict[str, list[Lead]]:
        """Leads grouped by pipeline stage (every stage present, even if empty)."""
        grouped: dict[str, list[Lead]] = {stage.value: [] for stage in PipelineStage}
        for lead in self.list_leads():
            grouped[lead.stage.value].append(lead)
        return grouped

    # ── Outreach log (§9) — append-only ──────────────────
    def add_outreach_logs(self, logs: list[OutreachLog]) -> None:
        if logs:
            self._table(OUTREACH_LOGS_TABLE).insert(
                [{"data": log.model_dump(mode="json")} for log in logs]
            ).execute()

    def list_outreach_logs(self) -> list[OutreachLog]:
        rows = self._table(OUTREACH_LOGS_TABLE).select("data").order("id").execute().data
        return [OutreachLog(**row["data"]) for row in rows]

    # ── Meetings (§12) ───────────────────────────────────
    def upsert_meeting(self, meeting: Meeting) -> Meeting:
        """Store the finalized meeting for a lead (one live meeting per lead_id)."""
        key = meeting.lead_id or meeting.company
        self._table(MEETINGS_TABLE).upsert(
            {"lead_id": key, "data": meeting.model_dump(mode="json")}
        ).execute()
        return meeting

    def get_meeting(self, lead_id: str) -> Meeting | None:
        rows = self._table(MEETINGS_TABLE).select("data").eq("lead_id", lead_id).execute().data
        return Meeting(**rows[0]["data"]) if rows else None

    def list_meetings(self) -> list[Meeting]:
        rows = self._table(MEETINGS_TABLE).select("data").execute().data
        return [Meeting(**row["data"]) for row in rows]

    def clear(self) -> None:
        """Wipe every table — used by tests and a fresh-demo reset (Postgres requires a filter)."""
        self._table(LEADS_TABLE).delete().neq("id", "").execute()
        self._table(ICP_TABLE).delete().neq("id", "").execute()
        self._table(MEETINGS_TABLE).delete().neq("lead_id", "").execute()
        self._table(OUTREACH_LOGS_TABLE).delete().gte("id", 0).execute()
