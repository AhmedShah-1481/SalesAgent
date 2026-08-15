"""LLM provider factory — Groq primary, Gemini fallback.

Provider is swappable behind these functions. Imports are lazy so the app boots even
if a provider package or key is missing; failures surface only when a node calls the model.

Concrete models (``groq_model`` / ``gemini_model``) are exposed separately from the
fallback-wrapped ``get_chat_model`` because structured output must be applied to each
CONCRETE model *before* they are combined — ``RunnableWithFallbacks`` has no
``.with_structured_output`` (see app.llm.parsers).
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings


@lru_cache
def groq_model(model: str | None = None, temperature: float = 0.2):
    """A concrete Groq chat model (no fallback wrapper)."""
    settings = get_settings()

    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model or settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )


@lru_cache
def gemini_model(temperature: float = 0.2):
    """A concrete Gemini chat model, or ``None`` if unavailable.

    Returns ``None`` when no Google API key is configured, or when the optional
    ``langchain-google-genai`` package isn't installed — the Gemini fallback simply
    stays inactive rather than breaking callers (same graceful-degradation pattern as
    EMAIL_MODE / MEETING_MODE / the memory backend).
    """
    settings = get_settings()
    if not settings.google_api_key:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        return None

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


@lru_cache
def get_chat_model(model: str | None = None, temperature: float = 0.2):
    """A ChatModel for plain (non-structured) text calls: Groq primary + Gemini fallback.

    For structured output use ``app.llm.parsers.structured()`` instead — it applies the
    schema to each concrete model before combining, which this wrapper cannot do.
    """
    primary = groq_model(model=model, temperature=temperature)
    fallback = gemini_model(temperature=temperature)
    if fallback is not None:
        return primary.with_fallbacks([fallback])
    return primary
