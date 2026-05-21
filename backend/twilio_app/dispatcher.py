"""Dispatch parsed Twilio webhook messages to the correct handler."""
from __future__ import annotations

import logging
from pathlib import Path

from documents.services import ingest_for_user, query_for_user
from messaging.commands import route_command
from messaging.services import log_inbound, log_outbound
from twilio_app.sender import download_media, send_text
from users.services import get_or_create_user

logger = logging.getLogger(__name__)

MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/tiff": "tiff",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


def _normalize_phone(twilio_from: str) -> str:
    """Strip 'whatsapp:' prefix and leading '+' from a Twilio sender."""
    return twilio_from.replace("whatsapp:", "").lstrip("+")


def dispatch(form_data: dict) -> None:
    """Process an inbound Twilio WhatsApp webhook payload."""
    sender = form_data.get("From", "")
    profile_name = form_data.get("ProfileName", "")
    body = (form_data.get("Body", "") or "").strip()
    num_media = int(form_data.get("NumMedia", "0") or 0)
    message_sid = form_data.get("MessageSid", "")

    if not sender:
        return

    phone = _normalize_phone(sender)
    user = get_or_create_user(phone, profile_name)

    if num_media > 0:
        _handle_media(user, form_data, num_media, message_sid)
    elif body:
        _handle_text(user, body, message_sid)


def _handle_text(user, body: str, message_sid: str) -> None:
    log_inbound(user, "text", body, message_sid)

    response = route_command(user, body)
    if response is None:
        response = query_for_user(user, body)

    send_text(user.phone_number, response)
    log_outbound(user, response)


def _handle_media(user, form_data: dict, num_media: int, message_sid: str) -> None:
    """Handle one or more media attachments."""
    body = (form_data.get("Body", "") or "").strip()
    log_inbound(user, "document", f"[media x{num_media}] {body}", message_sid)

    replies: list[str] = []
    for i in range(num_media):
        media_url = form_data.get(f"MediaUrl{i}")
        content_type = form_data.get(f"MediaContentType{i}", "application/octet-stream")
        if not media_url:
            continue

        result = download_media(media_url)
        if result is None:
            replies.append("❌ Could not download your file. Please try again.")
            continue

        file_bytes, _ = result
        ext = MIME_EXT.get(content_type, "bin")
        filename = f"upload_{message_sid[:8]}_{i}.{ext}"

        reply = ingest_for_user(user, filename, file_bytes, content_type)
        replies.append(reply)

    full_reply = "\n\n".join(replies) if replies else "❌ No media received."
    send_text(user.phone_number, full_reply)
    log_outbound(user, full_reply)
