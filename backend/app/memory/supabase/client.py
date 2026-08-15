"""Supabase client factory — Phase 10. Import is lazy so the app boots without keys."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_supabase():
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Supabase not configured (SUPABASE_URL / SUPABASE_KEY).")
    from supabase import create_client  # lazy import

    return create_client(settings.supabase_url, settings.supabase_key)
