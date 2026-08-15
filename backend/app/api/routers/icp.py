"""ICP intake + lead discovery endpoints (§2–3) — Phase 3.

- POST /icp          -> store the Ideal Customer Profile (asked of the user up front).
- POST /icp/discover -> run staged discovery (search -> grounded extraction -> cheap
                        filter) against the stored ICP, persist Potential leads, return them.
- GET  /icp          -> read back the current ICP.

Discovery is CPU/IO-bound (search + LLM), so it runs in a threadpool to keep the event
loop and SSE feed responsive — same pattern as the RAG layer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.graph.nodes.cheap_filter import filter_candidates
from app.graph.nodes.discovery import discover_leads
from app.memory.store import get_store
from app.schemas.activity import ActivityEvent
from app.schemas.discovery import DiscoveryResult
from app.schemas.enums import PipelineStage
from app.schemas.icp import ICP

router = APIRouter(prefix="/icp", tags=["icp"])
logger = get_logger(__name__)


def _company_knowledge_summary() -> str:
    """Best-effort 'what we sell' blurb from the RAG layer to sharpen search queries.

    Fully optional: returns "" if the ML/RAG deps or an indexed profile are absent, so
    discovery still works on a base-only install.
    """
    try:
        from app.rag.ingest import query_knowledge

        result = query_knowledge("our services, capabilities, and target customers", k=3)
        return "\n".join(c.text for c in result.results)[:1500]
    except Exception:  # ML deps missing, nothing indexed, etc. — grounding is optional here
        return ""


def _discover(icp: ICP, knowledge: str, settings) -> tuple[list, list]:
    candidates = discover_leads(icp, knowledge, settings=settings)
    kept, dropped = filter_candidates(candidates, icp, settings=settings)
    return candidates, kept, dropped


@router.post("", response_model=ICP)
async def submit_icp(icp: ICP) -> ICP:
    """Store the Ideal Customer Profile used throughout the pipeline (§2)."""
    get_store().set_icp(icp)
    event_bus.publish(
        ActivityEvent(
            kind="icp",
            message="Ideal Customer Profile saved.",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return icp


@router.get("", response_model=ICP | None)
async def get_icp() -> ICP | None:
    """Return the current ICP (null if none has been submitted yet)."""
    return get_store().get_icp()


@router.post("/discover", response_model=DiscoveryResult)
async def discover(icp: ICP | None = None) -> DiscoveryResult:
    """Run staged discovery against the stored ICP (or one supplied in the body)."""
    store = get_store()
    icp = icp or store.get_icp()
    if icp is None:
        raise HTTPException(status_code=400, detail="No ICP set — POST /icp first.")
    store.set_icp(icp)

    settings = get_settings()
    knowledge = await run_in_threadpool(_company_knowledge_summary)
    try:
        candidates, kept, dropped = await run_in_threadpool(_discover, icp, knowledge, settings)
    except RuntimeError as exc:  # e.g. no search provider configured
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # search/LLM failure
        logger.exception("Discovery failed")
        raise HTTPException(status_code=502, detail=f"Discovery failed: {exc}") from exc

    store.upsert_many(kept)
    event_bus.publish(
        ActivityEvent(
            kind="discovery",
            message=f"Discovery complete: {len(candidates)} found, {len(kept)} kept "
            f"as Potential, {len(dropped)} dropped.",
            stage=PipelineStage.POTENTIAL.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return DiscoveryResult(
        icp=icp,
        discovered=len(candidates),
        kept=len(kept),
        dropped=len(dropped),
        leads=kept,
    )
