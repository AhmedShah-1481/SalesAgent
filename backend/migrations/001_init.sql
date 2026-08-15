-- ==========================================================================
-- Supabase / Postgres schema for long-term memory (§13) + sales pipeline (§14).
-- Phase 10. Run once in the Supabase SQL editor (or `supabase db` / psql).
--
-- Design: each domain object is persisted losslessly as JSONB via Pydantic
-- `model_dump(mode="json")`, so the DB shape never has to chase the schema as it
-- grows each phase. Only fields the app queries on are promoted to real columns:
-- `leads.stage` (pipeline grouping) and the primary keys. See
-- backend/app/memory/supabase/{models.py,repository.py}.
-- ==========================================================================

-- Ideal Customer Profile — a singleton (id is always 'current').
create table if not exists icp (
    id          text primary key,
    data        jsonb       not null,
    updated_at  timestamptz not null default now()
);

-- Leads: the full pipeline. `stage` is denormalized from data->>'stage' so the
-- Kanban query (§14) can group/filter without deserializing every row.
create table if not exists leads (
    id          text primary key,
    stage       text        not null,
    data        jsonb       not null,
    updated_at  timestamptz not null default now()
);
create index if not exists leads_stage_idx on leads (stage);

-- Outreach log (§9): append-only record of every outreach action.
create table if not exists outreach_logs (
    id          bigint generated always as identity primary key,
    data        jsonb       not null,
    created_at  timestamptz not null default now()
);

-- Meetings (§12): one live meeting per lead (keyed by lead_id, or company as fallback).
create table if not exists meetings (
    lead_id     text primary key,
    data        jsonb       not null,
    updated_at  timestamptz not null default now()
);
