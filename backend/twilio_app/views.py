"""Twilio WhatsApp webhook view."""
from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.request_validator import RequestValidator

from twilio_app.dispatcher import dispatch

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def twilio_webhook(request):
    """Receive an inbound WhatsApp message from Twilio.

    Twilio sends form-encoded POST data with fields like:
      From, To, Body, ProfileName, NumMedia, MediaUrl0, MediaContentType0, MessageSid
    """
    if settings.TWILIO_VALIDATE_SIGNATURE:
        signature = request.headers.get("X-Twilio-Signature", "")
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        url = request.build_absolute_uri()
        params = request.POST.dict()
        if not validator.validate(url, params, signature):
            logger.warning("Invalid Twilio signature from %s", request.META.get("REMOTE_ADDR"))
            return HttpResponseForbidden("Invalid signature")

    try:
        form_data = request.POST.dict()
        dispatch(form_data)
    except Exception:
        logger.exception("Error processing Twilio webhook")

    # Empty TwiML response — we send replies via the REST API instead
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        content_type="application/xml",
        status=200,
    )
