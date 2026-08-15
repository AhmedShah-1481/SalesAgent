"""Split documents into overlapping chunks for embedding (§1)."""
from __future__ import annotations

from langchain_core.documents import Document

from app.config import get_settings


def split(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # lazy

    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.rag_chunk_size,
        chunk_overlap=chunk_overlap or settings.rag_chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(documents)
