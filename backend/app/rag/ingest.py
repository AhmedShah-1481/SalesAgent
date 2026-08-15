"""Ingestion + query orchestration for the company knowledge base (§1).

Pipeline: load (PDF/text) -> split -> embed -> persist in Chroma. Everything downstream
reads through query_knowledge / retriever so decisions stay grounded in these facts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

from app.config import get_settings
from app.rag.loader import load_pdf, load_text
from app.rag.retriever import retrieve
from app.rag.splitter import split
from app.rag.vectorstore import get_vectorstore
from app.schemas.knowledge import (
    IngestResult,
    KnowledgeChunk,
    KnowledgeStats,
    QueryResult,
)


def _ingest_docs(docs: list[Document], doc_type: str, source: str, store) -> IngestResult:
    chunks = split(docs)
    for chunk in chunks:  # stamp source so mixed-source collections stay attributable
        chunk.metadata.setdefault("source", source)
    store = store or get_vectorstore()
    if chunks:
        store.add_documents(chunks)
    return IngestResult(
        source=source,
        doc_type=doc_type,
        pages=len(docs),
        chunks=len(chunks),
        characters=sum(len(c.page_content) for c in chunks),
        ingested_at=datetime.now(tz=timezone.utc),
    )


def ingest_pdf(path: str, source: str | None = None, store=None) -> IngestResult:
    docs = load_pdf(path)
    return _ingest_docs(docs, doc_type="pdf", source=source or Path(path).name, store=store)


def ingest_text(text: str, source: str = "pasted-text", store=None) -> IngestResult:
    docs = load_text(text, source=source)
    return _ingest_docs(docs, doc_type="text", source=source, store=store)


def query_knowledge(query: str, k: int | None = None, store=None) -> QueryResult:
    hits = retrieve(query, k=k, store=store)
    chunks = [
        KnowledgeChunk(
            text=doc.page_content,
            source=doc.metadata.get("source"),
            page=doc.metadata.get("page"),
            score=round(float(score), 4),
        )
        for doc, score in hits
    ]
    return QueryResult(query=query, results=chunks)


def knowledge_stats(store=None) -> KnowledgeStats:
    settings = get_settings()
    store = store or get_vectorstore()
    data = store.get(include=["metadatas"])
    metadatas = data.get("metadatas") or []
    sources = sorted({m.get("source") for m in metadatas if m and m.get("source")})
    return KnowledgeStats(
        collection=settings.rag_collection,
        embedding_model=settings.embedding_model,
        total_chunks=len(data.get("ids") or []),
        sources=list(sources),
    )


def reset_knowledge(store=None) -> None:
    """Wipe the collection — used when a fresh company profile replaces the old one."""
    store = store or get_vectorstore()
    store.delete_collection()
