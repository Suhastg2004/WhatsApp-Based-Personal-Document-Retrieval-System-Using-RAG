"""HTTP client for the RAG FastAPI service (bot/app/, port 8001)."""
from __future__ import annotations

import logging
from io import BytesIO

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class RAGClient:
    """Communicates with the FastAPI RAG service via HTTP."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or settings.RAG_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.RAG_REQUEST_TIMEOUT

    def health(self) -> dict:
        """GET /health on the RAG service."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("RAG health check failed: %s", exc)
            return {"status": "unavailable", "error": str(exc)}

    def ingest_file(self, filename: str, file_bytes: bytes, content_type: str) -> dict:
        """POST /ingest/files with a single file as multipart upload.

        Returns: {"files_processed": int, "chunks_indexed": int, "document_ids": list[str]}
        """
        files = {"files": (filename, BytesIO(file_bytes), content_type)}
        resp = requests.post(
            f"{self.base_url}/ingest/files",
            files=files,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def query(self, question: str, top_k: int = 4) -> dict:
        """POST /query with a question.

        Returns: {"answer": str, "sources": list[dict]}
        """
        resp = requests.post(
            f"{self.base_url}/query",
            json={"question": question, "top_k": top_k},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


# Module-level singleton
_client: RAGClient | None = None


def get_rag_client() -> RAGClient:
    global _client
    if _client is None:
        _client = RAGClient()
    return _client
