"""Health check — reports Django status and RAG service connectivity."""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from rag_client.client import get_rag_client


@api_view(["GET"])
def health_check(request):
    rag = get_rag_client().health()
    rag_ok = rag.get("status") == "ok"

    return Response({
        "django_status": "ok",
        "rag_status": "ok" if rag_ok else "unavailable",
        "rag_detail": rag,
        "overall": "ok" if rag_ok else "degraded",
    })
