"""FastAPI entrypoint — ``uvicorn app.main:app``.

Mounts routers, configures CORS, and creates runtime dirs on startup. The LangGraph
pipeline is compiled lazily via app.api.deps.get_graph(), so boot stays fast and does
not require any ML dependencies (torch/chroma live in requirements-ml.txt).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import activity, health, icp, knowledge, leads, meetings, whatsapp
from app.config import get_settings
from app.core.events import event_bus
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    settings.ensure_dirs()
    from app.memory.store import get_store

    get_store()  # log + validate the long-term memory backend early (§13)
    # Let background threads (APScheduler follow-up sweep) publish onto this loop's SSE feed.
    event_bus.bind_loop(asyncio.get_running_loop())
    try:  # best-effort — manual POST endpoints still work without the scheduler
        from app.scheduler.jobs import start_follow_up_sweeps, start_meeting_reminders

        start_follow_up_sweeps()
        start_meeting_reminders()
    except Exception:
        logger.warning(
            "Scheduler not started; use POST /leads/follow-up + /meetings/reminders/run.",
            exc_info=True,
        )
    logger.info(
        "Backend starting (phase 10 — long-term memory + pipeline). CORS: %s",
        settings.cors_origins_list,
    )
    yield
    try:
        from app.scheduler.jobs import get_scheduler

        get_scheduler().shutdown(wait=False)
    except Exception:
        pass
    logger.info("Backend shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AgentHack — Autonomous AI Sales Agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (health, knowledge, icp, leads, whatsapp, activity, meetings):
        app.include_router(module.router)
    return app


app = create_app()
