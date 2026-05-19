from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("onboarding.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("rag.urls")),
    path("webhook/", include("messaging.urls")),
]
