"""Phase 9 tests: inbound WhatsApp webhook (§9/§10) + phone matching.

The Node microservice and Baileys aren't exercised here (no JS harness); this covers the Python
seam — number normalization, lead lookup by phone, and the /whatsapp-incoming classifier funnel.
The classifier is monkeypatched, so this runs with no API keys and no network.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.phone import normalize_phone, phones_match
from app.main import app
from app.memory.store import get_store
from app.schemas.contact import Contact
from app.schemas.conversation import ReplyClassification
from app.schemas.enums import PipelineStage, ResponseCategory
from app.schemas.lead import Lead

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store():
    get_store().clear()
    yield
    get_store().clear()


# ── phone normalization / matching ───────────────────────
def test_normalize_phone_strips_jid_and_punctuation():
    assert normalize_phone("15551234567@s.whatsapp.net") == "15551234567"
    assert normalize_phone("+1 (555) 123-4567") == "15551234567"
    assert normalize_phone("0044 20 7946 0000") == "442079460000"  # 00 IDD prefix dropped
    assert normalize_phone(None) == ""


def test_phones_match_tolerates_missing_country_code():
    assert phones_match("+1 555 123 4567", "15551234567@s.whatsapp.net") is True
    assert phones_match("5551234567", "15551234567") is True  # stored local vs JID w/ country code
    assert phones_match("5551234567", "5559999999") is False
    assert phones_match("123", "123") is False  # too short to match confidently


# ── store lookup ─────────────────────────────────────────
def test_get_lead_by_phone_finds_matching_contact():
    store = get_store()
    store.upsert_lead(
        Lead(
            id="acme", company_name="Acme", stage=PipelineStage.CONTACTED,
            contacts=[Contact(name="Jane", role="CEO", phone="+1 555 123 4567")],
        )
    )
    assert store.get_lead_by_phone("15551234567@s.whatsapp.net").id == "acme"
    assert store.get_lead_by_phone("15559999999") is None


# ── webhook (§9/§10) ─────────────────────────────────────
def test_incoming_empty_message_is_ignored():
    r = client.post("/whatsapp-incoming", json={"phone": "15551234567", "text": "   "})
    assert r.status_code == 200 and r.json()["status"] == "ignored"


def test_incoming_unmatched_number_is_acknowledged_not_classified():
    r = client.post(
        "/whatsapp-incoming",
        json={"from": "15550000000@s.whatsapp.net", "text": "who is this?", "pushName": "Bob"},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "received" and body["matched"] is False


def test_incoming_from_admin_is_flagged_not_classified(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_whatsapp_number", "15557778888")
    r = client.post(
        "/whatsapp-incoming", json={"phone": "15557778888", "text": "ack, thanks"}
    )
    body = r.json()
    assert r.status_code == 200
    assert body["matched"] is False and body["admin"] is True


def test_incoming_matched_lead_is_classified_and_persisted(monkeypatch):
    from app.api.routers import whatsapp as whatsapp_router

    get_store().upsert_lead(
        Lead(
            id="acme", company_name="Acme", stage=PipelineStage.CONTACTED,
            contacts=[Contact(name="Jane", role="CEO", phone="+1 555 123 4567")],
        )
    )

    captured = {}

    def fake_apply(lead, text, *, channel="email", settings=None):
        captured["channel"] = channel
        updated = lead.model_copy(
            update={
                "stage": PipelineStage.INTERESTED,
                "last_response_category": ResponseCategory.POSITIVE,
            }
        )
        return updated, ReplyClassification(category=ResponseCategory.POSITIVE, reasoning="keen")

    monkeypatch.setattr(whatsapp_router, "apply_reply", fake_apply)

    r = client.post(
        "/whatsapp-incoming",
        json={"from": "15551234567@s.whatsapp.net", "text": "Yes, let's chat!"},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "classified" and body["matched"] is True
    assert body["lead_id"] == "acme"
    assert body["category"] == "Positive/Interested"
    assert body["stage"] == "Interested"
    assert captured["channel"] == "whatsapp"  # funneled through the same sink as email, tagged WA
    assert client.get("/leads/acme").json()["stage"] == "Interested"
