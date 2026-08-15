"""Company Knowledge / RAG endpoints (§1) — Phase 2.

Ingest a company PDF *or* pasted text, inspect what is indexed, run a grounded query,
and reset the base when a new company profile replaces the old one. CPU-bound embedding
work is pushed to a threadpool so the event loop (and the SSE feed) stays responsive.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.events import event_bus
from app.rag.ingest import (
    ingest_pdf,
    ingest_text,
    knowledge_stats,
    query_knowledge,
    reset_knowledge,
)
from app.schemas.activity import ActivityEvent
from app.schemas.knowledge import (
    IngestResult,
    KnowledgeStats,
    QueryRequest,
    QueryResult,
    TextIngestRequest,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _announce(result: IngestResult) -> None:
    event_bus.publish(
        ActivityEvent(
            kind="knowledge",
            message=f"Indexed company knowledge from '{result.source}' "
            f"({result.chunks} chunks, {result.pages} page(s)).",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


@router.post("/upload", response_model=IngestResult)
async def upload_company_doc(file: UploadFile = File(...)) -> IngestResult:
    """Ingest a company PDF into the RAG knowledge layer."""
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are supported here; "
                            "use POST /knowledge/text for pasted descriptions.")
    dest = Path(get_settings().upload_dir) / filename
    dest.write_bytes(await file.read())
    try:
        result = await run_in_threadpool(ingest_pdf, str(dest), filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _announce(result)
    return result


@router.post("/text", response_model=IngestResult)
async def ingest_company_text(payload: TextIngestRequest) -> IngestResult:
    """Ingest a pasted company description (the text alternative to a PDF, §1)."""
    try:
        result = await run_in_threadpool(ingest_text, payload.text, payload.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _announce(result)
    return result


@router.post("/query", response_model=QueryResult)
async def query_company_knowledge(payload: QueryRequest) -> QueryResult:
    """Return the top-k grounded chunks for a query (inspect what the agent will cite)."""
    return await run_in_threadpool(query_knowledge, payload.query, payload.k)


@router.get("", response_model=KnowledgeStats)
async def get_company_knowledge() -> KnowledgeStats:
    """Report what is currently indexed (collection, sources, chunk count)."""
    return await run_in_threadpool(knowledge_stats)


@router.delete("", status_code=200)
async def clear_company_knowledge() -> dict:
    """Wipe the knowledge base so a fresh company profile can be ingested."""
    await run_in_threadpool(reset_knowledge)
    event_bus.publish(
        ActivityEvent(
            kind="knowledge",
            message="Company knowledge base cleared.",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return {"status": "cleared"}
