from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/onboarding/", permanent=False)),
    path("webhook", include("webhook.urls")),
    path("webhook/whatsapp/", include("twilio_app.urls")),
    path("webhook/whatsapp", include("twilio_app.urls")),
    path("twilio/webhook", include("twilio_app.urls")),
    path("health", include("health.urls")),
    path("onboarding/", include("onboarding.urls")),
]
