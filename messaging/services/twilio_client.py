"""Twilio helpers: download inbound media and validate signatures.

Replies are returned as TwiML by the webhook, so we don't need an outbound
client for the basic flow.
"""
from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from twilio.request_validator import RequestValidator

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    filename: str
    content: bytes
    content_type: str


def validate_signature(request) -> bool:
    """Return True if the request was signed by Twilio (or validation disabled)."""
    if not settings.TWILIO_VALIDATE_SIGNATURE:
        return True
    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_AUTH_TOKEN not set; rejecting webhook.")
        return False

    signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
    proto = request.META.get("HTTP_X_FORWARDED_PROTO") or ("https" if request.is_secure() else "http")
    host = request.get_host()
    url = f"{proto}://{host}{request.get_full_path()}"

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, request.POST.dict(), signature)


def download_media(media_url: str, content_type_hint: str = "") -> MediaItem:
    """Fetch a Twilio MediaUrl.

    Twilio media URLs return a 307 redirect to their CDN. The CDN URL
    has signed query params and doesn't need auth. Strategy:
    1. Hit the Twilio URL with auth but DON'T follow redirects.
    2. Get the CDN URL from the Location header.
    3. Download from the CDN URL (no auth needed).
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Step 1: Get the redirect
    resp = session.get(media_url, allow_redirects=False, timeout=30)

    if resp.status_code in (301, 302, 303, 307, 308):
        cdn_url = resp.headers.get("Location", "")
        if cdn_url:
            # Step 2: Download from CDN (no auth needed, URL is pre-signed)
            final_resp = requests.get(cdn_url, timeout=60)
            final_resp.raise_for_status()
        else:
            raise RuntimeError(f"Twilio returned {resp.status_code} but no Location header")
    elif resp.status_code == 200:
        final_resp = resp
    else:
        resp.raise_for_status()
        final_resp = resp  # won't reach here but keeps linter happy

    content_type = final_resp.headers.get("Content-Type", content_type_hint or "application/octet-stream")
    extension = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
    if extension == ".jpe":
        extension = ".jpg"

    name = urlparse(media_url).path.rsplit("/", 1)[-1] or "media"
    filename = f"{name}{extension}" if extension and not name.endswith(extension) else name
    return MediaItem(filename=filename, content=final_resp.content, content_type=content_type)
