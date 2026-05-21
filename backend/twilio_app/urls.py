from django.urls import path
from twilio_app import views

urlpatterns = [
    path("", views.twilio_webhook, name="twilio-webhook"),
]
