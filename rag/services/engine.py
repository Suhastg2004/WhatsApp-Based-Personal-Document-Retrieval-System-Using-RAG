"""RAG answer generation.

Two backends:
- groq: Calls Groq Cloud API with retrieved context (recommended).
- extractive: Returns the top chunk verbatim (no API key needed, fallback).

The system prompt is tuned for short WhatsApp replies from personal documents.
"""
from __future__ import annotations

import logging

from django.conf import settings

from rag.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a precise personal-document assistant. "
    "The user has uploaded personal documents (ID cards, bank passbooks, notes, etc.) "
    "and is asking questions about them via WhatsApp.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the provided context.\n"
    "2. Quote values (numbers, names, dates) exactly as they appear.\n"
    "3. If the answer is not in the context, say: \"I couldn't find that in your uploaded documents.\"\n"
    "4. Keep answers short (1-3 sentences), suitable for WhatsApp.\n"
    "5. Do NOT make up information or guess."
)


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"--- Document {i}: {c.source} (chunk {c.chunk_index}, score {c.score:.3f}) ---")
        parts.append(c.text)
        parts.append("")
    return "\n".join(parts)


def answer_question(question: str, chunks: list[RetrievedChunk]) -> str:
    """Generate an answer from retrieved chunks.

    Args:
        question: The user's natural language question.
        chunks: Retrieved chunks ranked by relevance (highest first).

    Returns:
        A text answer suitable for sending via WhatsApp.
    """
    if not chunks:
        return "I couldn't find anything related to that in your uploaded documents."

    selected = chunks[: settings.MAX_CONTEXT_CHUNKS]
    context = _build_context(selected)
    backend = (settings.GENERATION_BACKEND or "extractive").lower().strip()

    if backend == "groq" and settings.GROQ_API_KEY:
        try:
            return _groq_answer(question, context)
        except Exception as exc:
            logger.exception("Groq generation failed, falling back to extractive: %s", exc)

    return _extractive_answer(selected)


def _groq_answer(question: str, context: str) -> str:
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.1,
        max_tokens=500,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"},
        ],
    )
    content = completion.choices[0].message.content or ""
    return content.strip() or "No answer was generated."


def _extractive_answer(chunks: list[RetrievedChunk]) -> str:
    """Return the best matching chunk as-is."""
    top = chunks[0]
    snippet = top.text[:1200]
    return f"From {top.source}:\n{snippet}"
