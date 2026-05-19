"""Per-user vector search over chunks stored in SQLite.

Vectors are stored as JSON in `Chunk.vector`. Cosine similarity is computed
in NumPy. This is fast enough for personal-scale data (hundreds to low
thousands of chunks per user).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from documents.models import Chunk


@dataclass
class RetrievedChunk:
    document_id: str
    source: str
    chunk_index: int
    text: str
    score: float


def search_for_user(user_id: int, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
    """Find the top_k most relevant chunks for a user given a query vector.

    Only searches chunks where is_embedded=True (have valid vectors).
    Results are sorted by cosine similarity, highest first.
    """
    if not query_vector:
        return []

    query = np.asarray(query_vector, dtype=np.float32)
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        return []

    rows = (
        Chunk.objects.filter(user_id=user_id, is_embedded=True)
        .values_list("document__id", "document__source", "chunk_index", "text", "vector")
    )

    if not rows.exists():
        return []

    scored: list[RetrievedChunk] = []
    for doc_id, source, chunk_index, text, vector_json in rows.iterator():
        try:
            vec = np.asarray(json.loads(vector_json), dtype=np.float32)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        vec_norm = float(np.linalg.norm(vec))
        if vec_norm == 0.0:
            continue
        score = float(np.dot(query, vec) / (vec_norm * query_norm))
        scored.append(
            RetrievedChunk(
                document_id=str(doc_id),
                source=source,
                chunk_index=int(chunk_index),
                text=text,
                score=score,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]
