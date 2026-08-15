"""Structured-output helpers built on LangChain's ``.with_structured_output(...)``.

Nodes pass a pydantic schema from app.schemas to get a validated object back from the
LLM. ``structured(Schema).invoke(prompt_str)`` yields a validated ``Schema`` instance.

Groq offers three ways to force a schema, and the choice matters on the Llama models:

* ``json_schema`` (Groq Structured Outputs) is NOT supported by ``llama-3.3-70b-versatile``
  / ``llama-3.1-8b-instant`` — Groq 400s "model does not support response format
  json_schema". Unusable here.
* ``function_calling`` (tool calling) usually works, but Llama *intermittently* emits the
  ``<function=Name>{...}`` payload as plain text, which Groq rejects with
  ``400 tool_use_failed`` — this is what broke live research.
* ``json_mode`` forces a JSON object via ``response_format`` (universally supported) and
  cannot hit ``tool_use_failed`` at all. Its one requirement is that the prompt describe
  the schema (and contain the word "json"), so we append PydanticOutputParser's format
  instructions to the prompt string.

So ``structured()`` uses json_mode as the PRIMARY path and layers function_calling — then
Gemini, if configured — behind it via ``.with_fallbacks``. The failure modes are
orthogonal, so a transient hiccup on one path is transparently recovered by the next.
"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda

from app.llm.provider import gemini_model, groq_model


def _json_mode_chain(llm, schema: type):
    """json_mode with the schema's format instructions appended to the prompt string."""
    instructions = PydanticOutputParser(pydantic_object=schema).get_format_instructions()
    augment = RunnableLambda(lambda prompt: f"{prompt}\n\n{instructions}")
    return augment | llm.with_structured_output(schema, method="json_mode")


def structured(schema: type, *, model: str | None = None, temperature: float = 0.0):
    """A runnable whose ``.invoke(prompt_str)`` returns a validated ``schema`` instance.

    Tries Groq json_mode first, then Groq function_calling, then Gemini (when a Google API
    key is set). Each fallback receives the original prompt string.

    Example:
        from app.schemas.discovery import CandidateExtraction
        out = structured(CandidateExtraction).invoke(prompt)  # -> CandidateExtraction
    """
    groq = groq_model(model=model, temperature=temperature)

    primary = _json_mode_chain(groq, schema)
    fallbacks = [groq.with_structured_output(schema, method="function_calling")]

    gemini = gemini_model(temperature=temperature)
    if gemini is not None:
        fallbacks.append(gemini.with_structured_output(schema))

    return primary.with_fallbacks(fallbacks)
