from django.urls import path

from rag import views

urlpatterns = [
    path("query/", views.query, name="rag-query"),
    path("ingest/text/", views.ingest_text_view, name="rag-ingest-text"),
    path("rag/status/", views.rag_status, name="rag-status"),
]
