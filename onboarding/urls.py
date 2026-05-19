from django.urls import path

from onboarding import views

urlpatterns = [
    path("", views.landing, name="onboarding-landing"),
    path("qr.png", views.qr_image, name="onboarding-qr"),
]
