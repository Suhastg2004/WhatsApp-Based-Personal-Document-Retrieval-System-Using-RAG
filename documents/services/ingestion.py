"""Ingestion pipeline: save -> parse -> chunk -> embed -> persist.

All operations are scoped to a single WhatsAppUser so data is isolated.
Supports two modes:
- ingest_bytes(): for files (PDF, image, DOCX, TXT)
- ingest_text(): for raw text messages sent via WhatsApp
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from core.models import WhatsAppUser
from documents.models import Chunk, Document
from documents.services.chunker import chunk_text
from documents.services.parser import SUPPORTED_EXTENSIONS, parse_file
from rag.services.embedder import embed_texts

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    document_id: str
    source: str
    chunks_indexed: int
    status: str
    error: str = ""


def is_supported_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def ingest_bytes(
    user: WhatsAppUser,
    filename: str,
    content: bytes,
) -> IngestResult:
    """Ingest a file: parse, chunk, embed, and store."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return IngestResult(
            document_id="",
            source=filename,
            chunks_indexed=0,
            status=Document.Status.FAILED,
            error=f"Unsupported file type: {suffix}",
        )

    document = Document.objects.create(
        user=user,
        title=Path(filename).stem,
        source=filename,
        file_type=suffix,
        status=Document.Status.PROCESSING,
    )
    document.file.save(filename, ContentFile(content), save=True)

    try:
        parsed = parse_file(Path(document.file.path))
        return _chunk_embed_store(user, document, parsed.text)
    except Exception as exc:
        logger.exception("Ingestion failed for %s", filename)
        document.status = Document.Status.FAILED
        document.error_message = str(exc)[:500]
        document.save(update_fields=["status", "error_message", "updated_at"])
        return IngestResult(
            document_id=str(document.id),
            source=filename,
            chunks_indexed=0,
            status=document.status,
            error=document.error_message,
        )


def ingest_text(
    user: WhatsAppUser,
    text: str,
    source_label: str = "text_message",
) -> IngestResult:
    """Ingest raw text (e.g. a WhatsApp text message the user wants stored)."""
    if not text or not text.strip():
        return IngestResult(
            document_id="",
            source=source_label,
            chunks_indexed=0,
            status=Document.Status.FAILED,
            error="Empty text provided.",
        )

    document = Document.objects.create(
        user=user,
        title=source_label,
        source=source_label,
        file_type=".txt",
        status=Document.Status.PROCESSING,
    )

    try:
        return _chunk_embed_store(user, document, text)
    except Exception as exc:
        logger.exception("Text ingestion failed")
        document.status = Document.Status.FAILED
        document.error_message = str(exc)[:500]
        document.save(update_fields=["status", "error_message", "updated_at"])
        return IngestResult(
            document_id=str(document.id),
            source=source_label,
            chunks_indexed=0,
            status=document.status,
            error=document.error_message,
        )


def _chunk_embed_store(
    user: WhatsAppUser,
    document: Document,
    text: str,
) -> IngestResult:
    """Shared logic: chunk text, embed, and persist to DB."""
    chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

    if not chunks:
        document.status = Document.Status.FAILED
        document.error_message = "No text could be extracted from the file."
        document.save(update_fields=["status", "error_message", "updated_at"])
        return IngestResult(
            document_id=str(document.id),
            source=document.source,
            chunks_indexed=0,
            status=document.status,
            error=document.error_message,
        )

    # Embed all chunks
    vectors = embed_texts(chunks)

    with transaction.atomic():
        Chunk.objects.bulk_create(
            [
                Chunk(
                    document=document,
                    user=user,
                    chunk_index=idx,
                    text=chunk,
                    vector=json.dumps(vector),
                    is_embedded=True,
                )
                for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False))
            ]
        )
        document.status = Document.Status.READY
        document.chunk_count = len(chunks)
        document.error_message = ""
        document.save(update_fields=["status", "chunk_count", "error_message", "updated_at"])

    logger.info(
        "Ingested %s for user %s: %d chunks embedded",
        document.source, user.wa_id, len(chunks),
    )

    return IngestResult(
        document_id=str(document.id),
        source=document.source,
        chunks_indexed=len(chunks),
        status=document.status,
    )
