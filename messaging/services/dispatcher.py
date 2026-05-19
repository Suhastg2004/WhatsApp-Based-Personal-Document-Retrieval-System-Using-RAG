"""Decide what to do with an inbound WhatsApp message.

Behavior:
- Media attached -> ingest each media item as a Document.
- Text starting with '/' -> command (/help, /list, /delete <id>, /reset, /save <text>).
- Plain text -> RAG query, scoped to this user.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

from core.models import WhatsAppUser
from documents.models import Document
from documents.services.ingestion import ingest_bytes, ingest_text, is_supported_filename
from messaging.services.twilio_client import MediaItem
from rag.services.embedder import embed_query
from rag.services.engine import answer_question
from rag.services.vector_store import search_for_user

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "👋 Welcome! I'm your personal document assistant.\n\n"
    "• Send me a *PDF, image, or text* to remember it.\n"
    "• Then ask anything in plain English (e.g., \"What is my PAN number?\").\n\n"
    "Commands:\n"
    "  /help — show this help\n"
    "  /save <text> — save text as a document\n"
    "  /list — list your stored documents\n"
    "  /delete <id> — delete a document\n"
    "  /reset — delete all your documents"
)


@dataclass
class DispatchResult:
    reply: str


def handle_inbound(user: WhatsAppUser, body: str, media: list[MediaItem]) -> DispatchResult:
    body = (body or "").strip()

    if media:
        return _handle_media(user, media, body)

    if not body:
        return DispatchResult(reply=HELP_TEXT)

    if body.startswith("/"):
        return _handle_command(user, body)

    return _handle_question(user, body)


def _handle_media(user: WhatsAppUser, media: list[MediaItem], caption: str) -> DispatchResult:
    lines: list[str] = []
    for item in media:
        if not is_supported_filename(item.filename):
            lines.append(f"⚠️ {item.filename}: unsupported file type")
            continue
        result = ingest_bytes(user, item.filename, item.content)
        if result.status == Document.Status.READY:
            lines.append(f"✅ {result.source}: indexed {result.chunks_indexed} chunks")
        else:
            lines.append(f"❌ {result.source}: {result.error or 'failed'}")

    lines.append("\nNow ask me anything from these documents.")
    return DispatchResult(reply="\n".join(lines))


def _handle_command(user: WhatsAppUser, body: str) -> DispatchResult:
    parts = body.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/help", "/start"}:
        return DispatchResult(reply=HELP_TEXT)

    if cmd == "/save":
        if not arg:
            return DispatchResult(reply="Usage: /save <text to remember>")
        result = ingest_text(user, arg, source_label="saved_text")
        if result.error:
            return DispatchResult(reply=f"❌ Failed to save: {result.error}")
        return DispatchResult(reply=f"✅ Saved! Indexed {result.chunks_indexed} chunks.")

    if cmd == "/list":
        docs = list(Document.objects.filter(user=user).order_by("-created_at")[:20])
        if not docs:
            return DispatchResult(reply="You haven't uploaded any documents yet.")
        lines = ["📚 Your documents:"]
        for d in docs:
            lines.append(f"• {d.source} ({d.chunk_count} chunks) — id: {d.id}")
        lines.append("\nUse /delete <id> to remove one.")
        return DispatchResult(reply="\n".join(lines))

    if cmd == "/delete":
        if not arg:
            return DispatchResult(reply="Usage: /delete <document_id>")
        deleted, _ = Document.objects.filter(user=user, id=arg).delete()
        if deleted:
            return DispatchResult(reply=f"🗑️ Deleted document {arg}.")
        return DispatchResult(reply=f"No document with id {arg} found in your library.")

    if cmd == "/reset":
        count = Document.objects.filter(user=user).count()
        Document.objects.filter(user=user).delete()
        return DispatchResult(reply=f"🧹 Deleted all {count} documents.")

    return DispatchResult(reply=f"Unknown command: {cmd}\n\n{HELP_TEXT}")


def _handle_question(user: WhatsAppUser, question: str) -> DispatchResult:
    if not Document.objects.filter(user=user, status=Document.Status.READY).exists():
        return DispatchResult(
            reply="You haven't uploaded any documents yet. Send me a PDF or photo first."
        )

    vector = embed_query(question)
    matches = search_for_user(user.id, vector, settings.DEFAULT_TOP_K)
    answer = answer_question(question, matches)
    return DispatchResult(reply=answer)
