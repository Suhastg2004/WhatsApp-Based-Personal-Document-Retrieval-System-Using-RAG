"""Send outbound WhatsApp messages via Twilio and download incoming media."""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1500  # Twilio WhatsApp limit per message


def _get_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _from_number() -> str:
    """Return the first configured Twilio sender number."""
    if not settings.TWILIO_WHATSAPP_NUMBERS:
        return ""
    return settings.TWILIO_WHATSAPP_NUMBERS[0]


def split_message(text: str) -> list[str]:
    """Split text into parts of at most MAX_MESSAGE_LENGTH characters."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    parts = []
    while text:
        parts.append(text[:MAX_MESSAGE_LENGTH])
        text = text[MAX_MESSAGE_LENGTH:]
    return parts


def send_text(to: str, body: str) -> None:
    """Send a text message via Twilio. `to` should be like 'whatsapp:+91...' or just '+91...' or '91...'."""
    # Normalize to E.164 format with whatsapp: prefix
    if not to.startswith("whatsapp:"):
        digits = to.lstrip("+")
        to = f"whatsapp:+{digits}"
    elif not to.startswith("whatsapp:+"):
        # Has whatsapp: but no + sign — fix it
        digits = to.replace("whatsapp:", "").lstrip("+")
        to = f"whatsapp:+{digits}"
    from_ = _from_number()
    if not from_:
        logger.error("No TWILIO_WHATSAPP_NUMBERS configured")
        return

    client = _get_client()
    for part in split_message(body):
        try:
            client.messages.create(from_=from_, to=to, body=part)
        except Exception as exc:
            logger.error("Failed to send Twilio message to %s: %s", to, exc)


def download_media(media_url: str) -> tuple[bytes, str] | None:
    """Download a media file from Twilio's hosted URL using basic auth.

    Returns: (file_bytes, content_type) or None on failure.
    """
    try:
        resp = requests.get(
            media_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=60,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return resp.content, content_type
    except Exception as exc:
        logger.error("Failed to download Twilio media %s: %s", media_url, exc)
        return None
