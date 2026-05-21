from django.urls import path
from onboarding import views

urlpatterns = [
    path("", views.qr_page, name="onboarding-qr"),
]
