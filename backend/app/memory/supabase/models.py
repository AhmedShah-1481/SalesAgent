"""Supabase table layout for long-term memory — Phase 10.

Domain objects are stored losslessly as JSONB (Pydantic ``model_dump(mode="json")``)
rather than shredded across normalized columns, so the DB shape never has to chase the
Pydantic schema as it grows each phase. Only fields the store queries on are promoted to
real columns: ``leads.stage`` (pipeline grouping, §14) and the primary keys.

See ``backend/migrations/001_init.sql`` for the matching DDL.
"""
from __future__ import annotations

# Table names
LEADS_TABLE = "leads"
ICP_TABLE = "icp"
OUTREACH_LOGS_TABLE = "outreach_logs"
MEETINGS_TABLE = "meetings"

# The ICP is a singleton; it always occupies this row id.
ICP_SINGLETON_ID = "current"
