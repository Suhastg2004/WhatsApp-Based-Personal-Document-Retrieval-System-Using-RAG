from django.urls import path

from messaging import views

urlpatterns = [
    path("whatsapp/", views.whatsapp_webhook, name="whatsapp-webhook"),
]
