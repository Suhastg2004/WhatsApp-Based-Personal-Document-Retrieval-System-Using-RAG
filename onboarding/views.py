from io import BytesIO

import qrcode
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from onboarding.services import build_wa_link


def _join_text() -> str:
    return settings.TWILIO_SANDBOX_JOIN_CODE or "hi"


def landing(request):
    display_number, wa_link = build_wa_link(_join_text())
    return render(
        request,
        "onboarding/landing.html",
        {
            "display_number": display_number,
            "wa_link": wa_link,
            "join_code": settings.TWILIO_SANDBOX_JOIN_CODE,
            "qr_url": request.build_absolute_uri("/qr.png"),
        },
    )


def qr_image(request):
    _, wa_link = build_wa_link(_join_text())
    img = qrcode.make(wa_link or "https://wa.me/")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")
