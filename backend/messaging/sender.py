"""Send outbound messages via Meta WhatsApp Cloud API and download media."""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com"
MAX_MESSAGE_LENGTH = 4096


def send_text(to: str, body: str) -> None:
    """Send a text message to a WhatsApp user. Splits if > 4096 chars."""
    parts = split_message(body)
    for part in parts:
        _send_single_message(to, part)


def split_message(text: str) -> list[str]:
    """Split text into parts of at most MAX_MESSAGE_LENGTH characters."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    parts = []
    while text:
        parts.append(text[:MAX_MESSAGE_LENGTH])
        text = text[MAX_MESSAGE_LENGTH:]
    return parts


def _send_single_message(to: str, body: str) -> dict | None:
    """POST a single text message to Meta Cloud API."""
    url = f"{META_GRAPH_URL}/{settings.META_API_VERSION}/{settings.META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to send message to %s: %s", to, exc)
        return None


def download_media(media_id: str) -> tuple[bytes, str] | None:
    """Download media from Meta using the media ID.

    Steps:
    1. GET /v21.0/<media_id> to get the download URL
    2. GET the download URL to fetch the file bytes

    Returns: (file_bytes, content_type) or None on failure.
    """
    headers = {"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"}

    try:
        # Step 1: Get media URL
        url_resp = requests.get(
            f"{META_GRAPH_URL}/{settings.META_API_VERSION}/{media_id}",
            headers=headers,
            timeout=10,
        )
        url_resp.raise_for_status()
        media_url = url_resp.json().get("url")
        if not media_url:
            logger.error("No URL in media response for %s", media_id)
            return None

        # Step 2: Download the file
        file_resp = requests.get(media_url, headers=headers, timeout=60)
        file_resp.raise_for_status()
        content_type = file_resp.headers.get("Content-Type", "application/octet-stream")
        return file_resp.content, content_type

    except Exception as exc:
        logger.error("Failed to download media %s: %s", media_id, exc)
        return None
