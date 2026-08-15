"""Load a company PDF (PyMuPDF) or pasted text into LangChain Documents (§1).

One Document per PDF page (with page number) so retrieved chunks can cite their page;
pasted text becomes a single Document. Splitting happens later in splitter.py.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

from langchain_core.documents import Document


def _normalize(text: str) -> str:
    # NFKC folds typographic ligatures (ﬁ->fi) and other compatibility chars that
    # PDF extraction emits, so retrieval isn't tripped up by non-ASCII look-alikes.
    return unicodedata.normalize("NFKC", text).strip()


def load_pdf(path: str) -> list[Document]:
    import pymupdf  # PyMuPDF — lazy import

    name = Path(path).name
    docs: list[Document] = []
    with pymupdf.open(path) as pdf:
        for index, page in enumerate(pdf):
            text = _normalize(page.get_text("text"))
            if text:
                docs.append(
                    Document(page_content=text, metadata={"source": name, "page": index + 1})
                )
    if not docs:
        raise ValueError(f"No extractable text found in PDF: {name}")
    return docs


def load_text(text: str, source: str = "pasted-text") -> list[Document]:
    cleaned = _normalize(text)
    if not cleaned:
        raise ValueError("Cannot ingest empty text.")
    return [Document(page_content=cleaned, metadata={"source": source, "page": None})]
