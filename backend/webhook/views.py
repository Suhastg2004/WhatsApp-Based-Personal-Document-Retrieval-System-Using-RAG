"""Meta WhatsApp Cloud API webhook — verification and inbound message handling."""
from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from webhook.signature import validate_signature

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        return _handle_verify(request)
    return _handle_inbound(request)


def _handle_verify(request):
    """Meta webhook verification challenge (one-time setup).

    Meta sends: GET /webhook?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
    We return the challenge value if the verify_token matches.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return HttpResponse(challenge, content_type="text/plain", status=200)

    logger.warning("Webhook verification failed. Token mismatch.")
    return HttpResponseForbidden("Verification failed")


def _handle_inbound(request):
    """Process inbound webhook POST from Meta.

    Always returns 200 to prevent Meta from retrying.
    """
    # Signature validation
    if settings.META_VALIDATE_SIGNATURE:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not validate_signature(request.body, signature, settings.META_APP_SECRET):
            logger.warning("Invalid webhook signature from %s", request.META.get("REMOTE_ADDR"))
            return HttpResponseForbidden("Invalid signature")

    try:
        import json
        body = json.loads(request.body)
        _process_webhook_payload(body)
    except Exception:
        logger.exception("Error processing webhook payload")

    # Always return 200 to Meta
    return HttpResponse("EVENT_RECEIVED", status=200)


def _process_webhook_payload(body: dict) -> None:
    """Parse and dispatch the Meta webhook payload.

    Meta payload structure:
    {
      "object": "whatsapp_business_account",
      "entry": [{
        "changes": [{
          "value": {
            "messages": [{
              "from": "919876543210",
              "type": "text|document|image",
              "text": {"body": "..."},
              "document": {"id": "...", "filename": "...", "mime_type": "..."},
              "image": {"id": "...", "mime_type": "..."}
            }],
            "contacts": [{"profile": {"name": "..."}}]
          }
        }]
      }]
    }
    """
    from webhook.dispatcher import dispatch_message

    if body.get("object") != "whatsapp_business_account":
        return

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            # Get display name from contacts
            display_name = ""
            if contacts:
                display_name = contacts[0].get("profile", {}).get("name", "")

            for message in messages:
                sender = message.get("from", "")
                msg_type = message.get("type", "")
                msg_id = message.get("id", "")

                if not sender:
                    continue

                dispatch_message(
                    sender_phone=sender,
                    display_name=display_name,
                    message_type=msg_type,
                    message=message,
                    meta_message_id=msg_id,
                )
