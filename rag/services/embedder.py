"""Embedding service using SentenceTransformers.

Lazy-loads the model on first call (downloads ~90MB on first run).
Thread-safe via a lock. Once loaded, subsequent calls are fast.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None


class EmbedderUnavailable(RuntimeError):
    """Raised when the embedding model cannot be loaded."""


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL_NAME)
            _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info("Embedding model loaded successfully.")
    return _model


def is_available() -> bool:
    """Check if the embedder can be loaded."""
    try:
        _get_model()
        return True
    except Exception:
        return False


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of normalized float vectors."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Embed a single query string. Returns a normalized float vector."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
