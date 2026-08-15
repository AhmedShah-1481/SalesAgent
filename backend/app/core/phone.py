"""Phone / WhatsApp number normalization — Phase 9.

Inbound WhatsApp identifiers arrive as JIDs (``1234567890@s.whatsapp.net``), while contact numbers
we store may be written as ``+1 (234) 567-890`` etc. This reduces both to comparable digit strings
and matches them forgivingly (a locally-stored number often lacks the country code the JID carries).
"""
from __future__ import annotations


def normalize_phone(raw: str | None) -> str:
    """Reduce a phone/WhatsApp identifier to digits (drops JID suffix, +, spaces, 00 IDD prefix)."""
    if not raw:
        return ""
    # "1234567890@s.whatsapp.net" or "1234:5@..." -> "1234567890"
    head = raw.split("@", 1)[0].split(":", 1)[0]
    digits = "".join(ch for ch in head if ch.isdigit())
    if digits.startswith("00"):  # international dialing prefix -> drop
        digits = digits[2:]
    return digits


def phones_match(a: str | None, b: str | None) -> bool:
    """True if two numbers plausibly refer to the same line (tolerates a missing country code)."""
    na, nb = normalize_phone(a), normalize_phone(b)
    if len(na) < 7 or len(nb) < 7:  # too short to match confidently
        return False
    return na == nb or na.endswith(nb) or nb.endswith(na)
