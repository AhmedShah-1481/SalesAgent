"""Phase 10 tests: long-term memory (§13) + pipeline persistence (§14).

Two things are covered:
  1. get_store() backend selection — keyless boot yields the in-memory store.
  2. SupabaseStore round-trips — exercised against a tiny in-memory fake of the supabase-py
     fluent client, so the real serialization/query logic runs with no network and no keys.
The fake mimics the exact subset of the supabase-py API SupabaseStore uses:
``client.table(name).<op>().<filter>().execute().data``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.memory.store import InMemoryStore, get_store
from app.memory.supabase.repository import SupabaseStore
from app.schemas.contact import Contact
from app.schemas.email import OutreachLog
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP
from app.schemas.lead import Lead
from app.schemas.meeting import Meeting


# ── tiny fake of the supabase-py fluent client ───────────
class _FakeResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, table: _FakeTable, op: str, payload=None) -> None:
        self._t = table
        self._op = op
        self._payload = payload
        self._filters: list[tuple] = []

    def eq(self, col, val):
        self._filters.append(("==", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("!=", col, val))
        return self

    def gte(self, col, val):  # only used by clear() as a match-all; treat as no-op
        return self

    def order(self, col):  # fake preserves insertion order already
        return self

    def _match(self, row: dict) -> bool:
        for kind, col, val in self._filters:
            if kind == "==" and row.get(col) != val:
                return False
            if kind == "!=" and row.get(col) == val:
                return False
        return True

    def execute(self) -> _FakeResult:
        t = self._t
        if self._op == "select":
            return _FakeResult([dict(r) for r in t.rows if self._match(r)])
        if self._op in ("upsert", "insert"):
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            for item in items:
                row = dict(item)
                if self._op == "upsert":
                    existing = next((r for r in t.rows if r.get(t.pk) == row.get(t.pk)), None)
                    if existing is not None:
                        existing.update(row)
                        continue
                if t.pk not in row:  # append-only table with an identity pk
                    t.seq += 1
                    row[t.pk] = t.seq
                t.rows.append(row)
            return _FakeResult(items)
        if self._op == "delete":
            t.rows[:] = [r for r in t.rows if not self._match(r)]
            return _FakeResult([])
        return _FakeResult([])


class _FakeTable:
    def __init__(self, pk: str) -> None:
        self.rows: list[dict] = []
        self.pk = pk
        self.seq = 0

    def select(self, *_a):
        return _FakeQuery(self, "select")

    def upsert(self, payload):
        return _FakeQuery(self, "upsert", payload)

    def insert(self, payload):
        return _FakeQuery(self, "insert", payload)

    def delete(self):
        return _FakeQuery(self, "delete")


class _FakeSupabase:
    def __init__(self) -> None:
        self._tables = {
            "leads": _FakeTable("id"),
            "icp": _FakeTable("id"),
            "meetings": _FakeTable("lead_id"),
            "outreach_logs": _FakeTable("id"),
        }

    def table(self, name: str) -> _FakeTable:
        return self._tables[name]


@pytest.fixture
def store() -> SupabaseStore:
    return SupabaseStore(client=_FakeSupabase())


def _lead(**kw) -> Lead:
    base = dict(id="acme", company_name="Acme", stage=PipelineStage.QUALIFIED)
    base.update(kw)
    return Lead(**base)


# ── backend selection ────────────────────────────────────
def test_get_store_defaults_to_in_memory_without_keys():
    # The test env has no SUPABASE_* keys, so auto-selection must stay in-memory.
    assert isinstance(get_store(), InMemoryStore)


# ── ICP round-trip (§2/§13) ──────────────────────────────
def test_icp_round_trips_through_supabase(store: SupabaseStore):
    assert store.get_icp() is None
    icp = ICP(location="Berlin", industry="Logistics", company_size="50-200")
    store.set_icp(icp)
    loaded = store.get_icp()
    assert loaded is not None
    assert loaded.location == "Berlin" and loaded.industry == "Logistics"


# ── leads: upsert, get, replace, list-by-stage, pipeline ─
def test_lead_persist_and_stage_query(store: SupabaseStore):
    store.upsert_lead(_lead(id="a", company_name="Acme", stage=PipelineStage.QUALIFIED))
    store.upsert_lead(_lead(id="b", company_name="Beta", stage=PipelineStage.CONTACTED))
    assert store.get_lead("a").company_name == "Acme"
    assert store.get_lead("missing") is None

    qualified = store.list_leads(stage=PipelineStage.QUALIFIED)
    assert [lead.id for lead in qualified] == ["a"]
    assert len(store.list_leads()) == 2


def test_upsert_replaces_not_duplicates(store: SupabaseStore):
    store.upsert_lead(_lead(id="a", stage=PipelineStage.QUALIFIED))
    store.upsert_lead(_lead(id="a", stage=PipelineStage.CONTACTED))  # same id, new stage
    assert len(store.list_leads()) == 1
    assert store.get_lead("a").stage is PipelineStage.CONTACTED
    # stage column is kept in sync so the pipeline query reflects the move
    assert store.list_leads(stage=PipelineStage.QUALIFIED) == []


def test_pipeline_groups_every_stage(store: SupabaseStore):
    store.upsert_many(
        [
            _lead(id="a", stage=PipelineStage.QUALIFIED),
            _lead(id="b", stage=PipelineStage.QUALIFIED),
            _lead(id="c", stage=PipelineStage.MEETING_SCHEDULED),
        ]
    )
    board = store.pipeline()
    assert {stage.value for stage in PipelineStage} <= set(board)  # every stage present
    assert len(board[PipelineStage.QUALIFIED.value]) == 2
    assert len(board[PipelineStage.MEETING_SCHEDULED.value]) == 1
    assert board[PipelineStage.CONVERTED.value] == []


def test_get_lead_by_phone_matches_contact(store: SupabaseStore):
    store.upsert_lead(
        _lead(id="a", contacts=[Contact(name="Jane", role="CEO", phone="+1 555 123 4567")])
    )
    assert store.get_lead_by_phone("15551234567@s.whatsapp.net").id == "a"
    assert store.get_lead_by_phone("15559999999") is None


# ── outreach logs are append-only (§9) ───────────────────
def test_outreach_logs_append_and_list(store: SupabaseStore):
    store.add_outreach_logs([OutreachLog(company="Acme", message="hi")])
    store.add_outreach_logs([OutreachLog(company="Beta", message="hello")])
    logs = store.list_outreach_logs()
    assert [log.company for log in logs] == ["Acme", "Beta"]


# ── meetings (§12) ───────────────────────────────────────
def test_meeting_round_trip(store: SupabaseStore):
    when = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    store.upsert_meeting(
        Meeting(lead_id="a", company="Acme", scheduled_time=when, meeting_link="https://m/x")
    )
    got = store.get_meeting("a")
    assert got is not None and got.meeting_link == "https://m/x"
    assert got.scheduled_time == when
    assert [m.company for m in store.list_meetings()] == ["Acme"]


# ── durability semantics: a second store over the same DB sees the data ──
def test_state_survives_a_new_store_instance():
    db = _FakeSupabase()  # stands in for the shared Postgres
    first = SupabaseStore(client=db)
    first.upsert_lead(_lead(id="a", company_name="Acme", stage=PipelineStage.CONVERTED))
    first.set_icp(ICP(industry="Logistics"))

    second = SupabaseStore(client=db)  # e.g. after a process restart
    assert second.get_lead("a").company_name == "Acme"
    assert second.get_icp().industry == "Logistics"


def test_clear_wipes_all_tables(store: SupabaseStore):
    store.upsert_lead(_lead(id="a"))
    store.set_icp(ICP(industry="Logistics"))
    store.add_outreach_logs([OutreachLog(company="Acme")])
    store.upsert_meeting(Meeting(lead_id="a", company="Acme"))
    store.clear()
    assert store.list_leads() == []
    assert store.get_icp() is None
    assert store.list_outreach_logs() == []
    assert store.list_meetings() == []
