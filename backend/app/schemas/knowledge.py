"""Schemas for the Company Knowledge / RAG layer (§1).

These back the /knowledge endpoints: ingest a company PDF or pasted text, report what
is indexed, and return grounded retrieval results that downstream nodes will cite.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TextIngestRequest(BaseModel):
    """Pasted company description (the text alternative to a PDF upload, §1)."""

    text: str = Field(min_length=1, description="Raw company description to index")
    source: str = Field("pasted-text", description="Label stored on every chunk")


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int | None = Field(None, ge=1, le=20, description="How many chunks to return")


class IngestResult(BaseModel):
    """Summary of a single ingestion pass."""

    source: str
    doc_type: str = Field(description='"pdf" or "text"')
    pages: int = Field(description="Source documents seen (PDF pages, or 1 for text)")
    chunks: int = Field(description="Chunks written to the vector store")
    characters: int
    ingested_at: datetime


class KnowledgeChunk(BaseModel):
    """One retrieved chunk with its provenance and relevance."""

    text: str
    source: str | None = None
    page: int | None = None
    score: float | None = Field(None, description="Relevance 0-1 (cosine); higher is closer")


class QueryResult(BaseModel):
    query: str
    results: list[KnowledgeChunk] = Field(default_factory=list)


class KnowledgeStats(BaseModel):
    """What the knowledge base currently holds — powers the /knowledge view."""

    collection: str
    embedding_model: str
    total_chunks: int
    sources: list[str] = Field(default_factory=list)
