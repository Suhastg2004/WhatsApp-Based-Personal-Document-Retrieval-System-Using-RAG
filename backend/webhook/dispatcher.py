"""Dispatch parsed webhook messages to the appropriate handler."""
from __future__ import annotations

import logging

from documents.services import ingest_for_user, query_for_user
from messaging.commands import route_command
from messaging.sender import download_media, send_text
from messaging.services import log_inbound, log_outbound
from users.services import get_or_create_user

logger = logging.getLogger(__name__)


def dispatch_message(
    sender_phone: str,
    display_name: str,
    message_type: str,
    message: dict,
    meta_message_id: str,
) -> None:
    """Route an inbound message to the correct handler.

    This is called from webhook/views.py after payload parsing.
    """
    # Register / update user
    user = get_or_create_user(sender_phone, display_name)

    if message_type == "text":
        _handle_text(user, message, meta_message_id)
    elif message_type in ("document", "image"):
        _handle_media(user, message_type, message, meta_message_id)
    else:
        logger.info("Ignoring unsupported message type '%s' from %s", message_type, sender_phone)


def _handle_text(user, message: dict, meta_message_id: str) -> None:
    """Handle a text message — command or query."""
    text = message.get("text", {}).get("body", "").strip()
    if not text:
        return

    # Log inbound
    log_inbound(user, "text", text, meta_message_id)

    # Try command routing first
    response = route_command(user, text)
    if response is None:
        # Not a command — treat as a RAG query
        response = query_for_user(user, text)

    # Send reply
    send_text(user.phone_number, response)
    log_outbound(user, response)


def _handle_media(user, message_type: str, message: dict, meta_message_id: str) -> None:
    """Handle a document or image upload — download and ingest."""
    media_info = message.get(message_type, {})
    media_id = media_info.get("id")
    mime_type = media_info.get("mime_type", "application/octet-stream")
    filename = media_info.get("filename", "")

    if not media_id:
        logger.warning("No media_id in %s message from %s", message_type, user.phone_number)
        return

    # For images without a filename, generate one from mime type
    if not filename:
        ext = _mime_to_ext(mime_type)
        filename = f"image.{ext}" if message_type == "image" else f"file.{ext}"

    # Log inbound
    log_inbound(user, message_type, f"[{message_type}: {filename}]", meta_message_id)

    # Download media from Meta
    result = download_media(media_id)
    if result is None:
        reply = "❌ Could not download your file. Please try again."
        send_text(user.phone_number, reply)
        log_outbound(user, reply)
        return

    file_bytes, content_type = result

    # Ingest via RAG service
    reply = ingest_for_user(user, filename, file_bytes, content_type)
    send_text(user.phone_number, reply)
    log_outbound(user, reply)


def _mime_to_ext(mime_type: str) -> str:
    """Convert a MIME type to a file extension."""
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/tiff": "tiff",
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
    }
    return mapping.get(mime_type, "bin")
