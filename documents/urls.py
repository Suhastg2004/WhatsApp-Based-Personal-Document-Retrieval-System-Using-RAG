from django.urls import path

from documents import views

urlpatterns = [
    path("documents/", views.documents_root, name="documents-root"),
    path("documents/<uuid:doc_id>/", views.document_detail, name="document-detail"),
]
