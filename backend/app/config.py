"""Application configuration — loaded from the repo-root .env via pydantic-settings.

Every external key from PROJECT_BRIEF.md lives here with a safe default so the app
boots even when keys are missing (individual features fail loudly only when used).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py -> backend/ -> repo root
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Prefer the root .env (single source of truth); fall back to backend/.env.
        env_file=(str(REPO_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────
    groq_api_key: str = ""
    google_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    # Gemini fallback model. Defaults to the "-latest" alias so it tracks the current
    # stable Flash and never 404s when a dated id (e.g. gemini-1.5-flash) is retired.
    gemini_model: str = "gemini-flash-latest"

    # ── Search ───────────────────────────────────────────
    tavily_api_key: str = ""
    serper_api_key: str = ""

    # ── Email (Gmail) ────────────────────────────────────
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_sender: str = ""
    email_mode: str = "simulate"  # "simulate" | "send"

    # ── Calendar ─────────────────────────────────────────
    google_calendar_credentials: str = ""

    # ── Supabase (long-term memory) ──────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    memory_backend: str = "auto"  # "auto" (supabase if keys set) | "memory" | "supabase"

    # ── WhatsApp microservice wiring ─────────────────────
    whatsapp_service_url: str = "http://localhost:3001"
    python_backend_url: str = "http://localhost:8000"
    whatsapp_port: int = 3001
    admin_whatsapp_number: str = ""

    # ── Runtime paths (relative to the backend/ working dir) ──
    chroma_persist_dir: str = "./data/chroma"
    checkpoint_db_path: str = "./data/checkpoints.sqlite"
    upload_dir: str = "./data/uploads"

    # ── RAG / company knowledge (Phase 2) ────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_collection: str = "company_knowledge"
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4

    # ── Lead discovery (Phase 3) ─────────────────────────
    discovery_search_provider: str = "auto"  # "auto" | "tavily" | "serper"
    discovery_max_candidates: int = 12  # cap on candidates fed to cheap filtering
    discovery_results_per_query: int = 8  # web results pulled per search query
    llm_model_cheap: str = "llama-3.1-8b-instant"  # cheap model for extraction/filtering

    # ── Deep research + qualification (Phase 4) ──────────
    research_max_leads: int = 5  # cap Potential leads deep-researched per run (cost/latency)
    research_queries_per_lead: int = 4  # targeted searches per company
    research_results_per_query: int = 4  # web results kept per research query
    enable_scraping: bool = True  # best-effort website fetch to enrich the dossier
    qualification_threshold: float = 60.0  # confidence >= threshold -> Qualified, else not

    # ── Service matching + decision-makers (Phase 5) ─────
    matching_max_leads: int = 5  # cap Qualified leads enriched per run (cost/latency)
    decision_maker_queries: int = 3  # targeted people-search queries per company
    decision_maker_results_per_query: int = 5  # web results kept per people query
    max_decision_makers: int = 5  # contacts kept per company

    # ── Personalized outreach + email (Phase 6) ──────────
    outreach_max_leads: int = 5  # cap Qualified leads contacted per run
    outreach_max_contacts_per_lead: int = 1  # emails per company (avoid spamming)
    booking_link: str = ""  # scheduling/booking URL included in outreach "when appropriate" (§9)

    # ── Response classification + follow-up (Phase 7) ────
    follow_up_wait_days: int = 3  # §11: Day 0 -> wait 3 days -> Email #2
    max_follow_ups: int = 1  # §11 shows a single automated second-touch email
    follow_up_sweep_minutes: int = 60  # how often the scheduler scans for due follow-ups

    # ── Meetings + admin reminder (Phase 8) ──────────────
    meeting_mode: str = "simulate"  # "simulate" | "create" (real Google Calendar/Meet)
    meeting_lead_days: int = 3  # default fixed meeting time this many days out
    meeting_hour: int = 15  # UTC hour of day for the fixed meeting time
    meeting_duration_minutes: int = 30  # meeting length (for the Calendar event)
    meeting_reminder_minutes: int = 30  # §12: remind the admin this long before the meeting
    reminder_sweep_minutes: int = 5  # how often the scheduler scans for due meeting reminders

    # ── App behaviour ────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        """Create runtime directories so first-run doesn't crash on missing paths."""
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
