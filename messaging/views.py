"""Twilio inbound WhatsApp webhook (form-encoded POST)."""
from __future__ import annotations

import logging

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.twiml.messaging_response import MessagingResponse

from core.models import WhatsAppUser
from messaging.models import InboundMessage
from messaging.services.dispatcher import handle_inbound
from messaging.services.twilio_client import download_media, validate_signature

logger = logging.getLogger(__name__)


def _twiml(reply_text: str) -> HttpResponse:
    response = MessagingResponse()
    # Twilio limits a single WhatsApp message to ~1600 chars.
    response.message(reply_text[:1500])
    return HttpResponse(str(response), content_type="application/xml")


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    if not validate_signature(request):
        logger.warning("Rejected unsigned Twilio webhook from %s", request.META.get("REMOTE_ADDR"))
        return HttpResponseForbidden("Invalid Twilio signature")

    from_id = request.POST.get("From", "").strip()
    body = request.POST.get("Body", "").strip()
    twilio_sid = request.POST.get("MessageSid", "").strip()
    profile_name = request.POST.get("ProfileName", "").strip()

    if not from_id:
        return _twiml("Sorry, I couldn't identify your WhatsApp number.")

    user, _ = WhatsAppUser.objects.get_or_create(
        wa_id=from_id,
        defaults={"display_name": profile_name},
    )
    if profile_name and user.display_name != profile_name:
        user.display_name = profile_name
        user.save(update_fields=["display_name", "last_seen_at"])

    media: list = []
    try:
        num_media = int(request.POST.get("NumMedia", "0") or "0")
    except ValueError:
        num_media = 0

    for i in range(num_media):
        url = request.POST.get(f"MediaUrl{i}")
        ctype = request.POST.get(f"MediaContentType{i}", "")
        if not url:
            continue
        try:
            media.append(download_media(url, ctype))
        except Exception:
            logger.exception("Failed to download media %s", url)

    inbound = InboundMessage.objects.create(
        user=user,
        twilio_sid=twilio_sid,
        body=body,
        num_media=num_media,
    )

    try:
        result = handle_inbound(user, body, media)
        inbound.reply = result.reply
        inbound.save(update_fields=["reply"])
        return _twiml(result.reply)
    except Exception as exc:
        logger.exception("Dispatch failed for %s", from_id)
        inbound.error = str(exc)[:500]
        inbound.save(update_fields=["error"])
        return _twiml("Something went wrong while processing your message. Please try again.")
