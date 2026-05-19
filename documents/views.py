from pathlib import Path

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import WhatsAppUser
from documents.models import Document
from documents.serializers import DocumentSerializer
from documents.services.ingestion import ingest_bytes, is_supported_filename


def _get_or_create_user(wa_id: str) -> WhatsAppUser:
    user, _ = WhatsAppUser.objects.get_or_create(wa_id=wa_id)
    return user


@api_view(["GET", "POST"])
def documents_root(request):
    """List documents for a user, or upload one for testing without WhatsApp.

    GET  ?wa_id=whatsapp:+91...
    POST multipart: wa_id=..., file=<binary>
    """
    if request.method == "GET":
        wa_id = request.query_params.get("wa_id")
        if not wa_id:
            return Response({"detail": "wa_id query param is required"}, status=400)
        user = _get_or_create_user(wa_id)
        qs = Document.objects.filter(user=user)
        return Response(DocumentSerializer(qs, many=True).data)

    wa_id = request.data.get("wa_id")
    upload = request.FILES.get("file")
    if not wa_id or not upload:
        return Response({"detail": "wa_id and file are required"}, status=400)
    if not is_supported_filename(upload.name):
        return Response(
            {"detail": f"Unsupported file type: {Path(upload.name).suffix}"},
            status=400,
        )

    user = _get_or_create_user(wa_id)
    result = ingest_bytes(user, upload.name, upload.read())
    if result.status == Document.Status.FAILED:
        return Response(
            {
                "document_id": result.document_id,
                "source": result.source,
                "status": result.status,
                "error": result.error,
            },
            status=status.HTTP_400_BAD_REQUEST if not result.document_id else status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response(
        {
            "document_id": result.document_id,
            "source": result.source,
            "chunks_indexed": result.chunks_indexed,
            "status": result.status,
        },
        status=201,
    )


@api_view(["DELETE"])
def document_detail(request, doc_id):
    wa_id = request.query_params.get("wa_id") or request.data.get("wa_id")
    if not wa_id:
        return Response({"detail": "wa_id is required"}, status=400)
    user = _get_or_create_user(wa_id)
    doc = get_object_or_404(Document, id=doc_id, user=user)
    doc.delete()
    return Response(status=204)
