from django.urls import path
from webhook import views

urlpatterns = [
    path("", views.webhook, name="webhook"),
]
