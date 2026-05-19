"""Choose which Twilio WhatsApp number to advertise on the QR page.

Round-robins across configured numbers using a hash of the day so a single
viewer sees a stable number, but the load distributes over time.
"""
from __future__ import annotations

import hashlib
from datetime import date
from urllib.parse import quote_plus

from django.conf import settings


def _strip_prefix(wa_number: str) -> str:
    return wa_number.replace("whatsapp:", "").strip().lstrip("+")


def pick_number() -> str | None:
    numbers = settings.TWILIO_WHATSAPP_NUMBERS
    if not numbers:
        return None
    if len(numbers) == 1:
        return numbers[0]
    today = date.today().isoformat()
    digest = hashlib.sha256(today.encode("utf-8")).digest()
    idx = digest[0] % len(numbers)
    return numbers[idx]


def build_wa_link(prefilled_text: str = "") -> tuple[str, str]:
    """Return (display_number, wa_link) for the picked Twilio number."""
    chosen = pick_number()
    if not chosen:
        return "", ""
    display = _strip_prefix(chosen)
    text = quote_plus(prefilled_text) if prefilled_text else ""
    link = f"https://wa.me/{display}"
    if text:
        link = f"{link}?text={text}"
    return display, link
