"""QR code onboarding page — generates a WhatsApp click-to-chat QR code.

Prefers Twilio sandbox (free, anyone can join) when configured;
falls back to Meta WhatsApp Cloud number otherwise.
"""
from __future__ import annotations

import base64
import io
import re

import qrcode
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


def _twilio_phone() -> str:
    """Return the Twilio sandbox phone number digits (e.g. '14155238886')."""
    if not settings.TWILIO_WHATSAPP_NUMBERS:
        return ""
    raw = settings.TWILIO_WHATSAPP_NUMBERS[0]  # 'whatsapp:+14155238886'
    return re.sub(r"\D", "", raw)


def qr_page(request):
    """Serve the onboarding page with a QR code linking to WhatsApp."""
    twilio_number = _twilio_phone()
    is_twilio = bool(twilio_number)

    if is_twilio:
        join_code = settings.TWILIO_SANDBOX_JOIN_CODE or "join your-code"
        # Pre-fill the join message so user just taps Send
        wa_url = f"https://wa.me/{twilio_number}?text={join_code.replace(' ', '%20')}"
        phone_display = f"+{twilio_number}"
        provider = "Twilio Sandbox"
        instructions = (
            f"1. Tap the button below to open WhatsApp\n"
            f"2. Send the pre-filled message: \"{join_code}\"\n"
            f"3. Wait for confirmation, then start chatting!"
        )
    else:
        phone_number = settings.META_PHONE_NUMBER_ID
        wa_url = f"https://wa.me/{phone_number}"
        phone_display = f"+{phone_number}"
        provider = "WhatsApp Cloud API"
        instructions = "Tap the button or scan the QR code to start chatting."

    # Generate QR code as base64 PNG
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(wa_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    html = render_to_string("onboarding/qr.html", {
        "qr_base64": qr_base64,
        "phone_display": phone_display,
        "wa_url": wa_url,
        "provider": provider,
        "instructions": instructions,
    })
    return HttpResponse(html)
