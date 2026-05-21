"""Document ingestion, querying, and management — per-user isolation layer."""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

from documents.models import DocumentMetadata
from rag_client.client import get_rag_client
from users.models import UserRecord

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "txt", "tif", "tiff", "webp", "md"}


def is_supported_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in SUPPORTED_EXTENSIONS


def get_supported_formats_message() -> str:
    return "Supported formats: PDF, PNG, JPG, DOCX, TXT"


def prefix_filename(phone_number: str, filename: str) -> str:
    """Prefix filename with user phone for namespace isolation."""
    return f"{phone_number}_{filename}"


def ingest_for_user(user: UserRecord, filename: str, file_bytes: bytes, content_type: str) -> str:
    """Ingest a file for a user via the RAG service.

    Returns a confirmation or error message for the user.
    """
    if not is_supported_file(filename):
        return f"⚠️ Unsupported file type. {get_supported_formats_message()}"

    prefixed = prefix_filename(user.phone_number, filename)
    client = get_rag_client()

    try:
        result = client.ingest_file(prefixed, file_bytes, content_type)
    except Exception as exc:
        logger.exception("RAG ingestion failed for user %s, file %s", user.phone_number, filename)
        return f"❌ Failed to process {filename}: {exc}"

    # Store document metadata
    doc_ids = result.get("document_ids", [])
    chunks = result.get("chunks_indexed", 0)

    for doc_id in doc_ids:
        DocumentMetadata.objects.create(
            user=user,
            rag_document_id=doc_id,
            original_filename=filename,
            file_type=Path(filename).suffix.lower().lstrip("."),
            chunk_count=chunks,
        )

    return f"✅ {filename}: indexed {chunks} chunks. Ask me anything about it!"


def query_for_user(user: UserRecord, question: str) -> str:
    """Query the RAG service, filtering results to this user's documents only.

    Returns the answer text.
    """
    # Check if user has any documents
    user_doc_ids = set(
        DocumentMetadata.objects.filter(user=user, is_deleted=False)
        .values_list("rag_document_id", flat=True)
    )

    if not user_doc_ids:
        return "You haven't uploaded any documents yet. Send me a PDF, image, or text file first!"

    client = get_rag_client()
    top_k = settings.DEFAULT_TOP_K

    try:
        # Request more results to account for filtering
        result = client.query(question, top_k=top_k * 3)
    except Exception as exc:
        logger.exception("RAG query failed for user %s", user.phone_number)
        return "⚠️ Service temporarily unavailable. Please try again later."

    answer = result.get("answer", "")
    sources = result.get("sources", [])

    # Filter sources to only this user's documents
    user_sources = [s for s in sources if s.get("document_id") in user_doc_ids]

    if not user_sources:
        return "I couldn't find anything related to that in your documents."

    # If the answer was generated from the user's docs, use it directly
    # Otherwise return extractive from filtered sources
    top_source_ids = {s.get("document_id") for s in sources[:top_k]}
    if top_source_ids.issubset(user_doc_ids):
        return answer

    # Fallback: return top matching chunk from user's docs
    top_chunk = user_sources[0]
    return f"From {top_chunk.get('source', 'your document')}:\n{top_chunk.get('text', '')[:1200]}"


def list_documents(user: UserRecord) -> str:
    """List user's documents."""
    docs = DocumentMetadata.objects.filter(user=user, is_deleted=False).order_by("-uploaded_at")[:20]
    if not docs:
        return "You haven't uploaded any documents yet."

    lines = ["📚 Your documents:"]
    for d in docs:
        lines.append(f"• {d.original_filename} ({d.chunk_count} chunks) — id: {d.rag_document_id[:8]}")
    lines.append("\nUse /delete <id> to remove one.")
    return "\n".join(lines)


def delete_document(user: UserRecord, doc_identifier: str) -> str:
    """Soft-delete a document by its ID prefix."""
    doc = DocumentMetadata.objects.filter(
        user=user,
        is_deleted=False,
        rag_document_id__startswith=doc_identifier,
    ).first()

    if not doc:
        return f"No document found with id starting with '{doc_identifier}'."

    doc.is_deleted = True
    doc.save(update_fields=["is_deleted"])
    return f"🗑️ Deleted {doc.original_filename}."


def reset_user(user: UserRecord) -> str:
    """Soft-delete all user's documents."""
    count = DocumentMetadata.objects.filter(user=user, is_deleted=False).update(is_deleted=True)
    return f"🧹 Deleted all {count} documents."
