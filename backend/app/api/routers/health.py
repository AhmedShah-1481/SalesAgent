"""Health + root endpoints (REAL — used by the Phase 1 smoke test)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "phase": "1-scaffolding"}


@router.get("/")
def root() -> dict:
    return {
        "name": "AgentHack — Autonomous AI Sales Agent API",
        "docs": "/docs",
        "health": "/health",
    }
