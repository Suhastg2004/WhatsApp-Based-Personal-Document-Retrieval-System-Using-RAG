"""RAG API endpoints.

POST /api/query/         — Ask a question against a user's documents
POST /api/ingest/text/   — Ingest raw text for a user
GET  /api/rag/status/    — Check if the RAG layer (embedder + generation) is ready
"""
from dataclasses import asdict

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import WhatsAppUser
from documents.services.ingestion import ingest_text
from rag.serializers import IngestTextRequestSerializer, QueryRequestSerializer, QueryResponseSerializer
from rag.services.embedder import embed_query, is_available as embedder_available
from rag.services.engine import answer_question
from rag.services.vector_store import search_for_user


@api_view(["POST"])
def query(request):
    """Ask a question. Embeds the question, searches user's chunks, generates answer."""
    serializer = QueryRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    user, _ = WhatsAppUser.objects.get_or_create(wa_id=payload["wa_id"])
    top_k = payload.get("top_k") or settings.DEFAULT_TOP_K

    vector = embed_query(payload["question"])
    matches = search_for_user(user.id, vector, top_k)
    answer = answer_question(payload["question"], matches)

    response = QueryResponseSerializer(
        {"answer": answer, "sources": [asdict(m) for m in matches]}
    )
    return Response(response.data)


@api_view(["POST"])
def ingest_text_view(request):
    """Ingest raw text (not a file) for a user. Useful for WhatsApp text messages."""
    serializer = IngestTextRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    user, _ = WhatsAppUser.objects.get_or_create(wa_id=payload["wa_id"])
    result = ingest_text(user, payload["text"], payload.get("source_label", "text_message"))

    if result.error:
        return Response(
            {"document_id": result.document_id, "source": result.source, "error": result.error},
            status=status.HTTP_400_BAD_REQUEST,
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


@api_view(["GET"])
def rag_status(request):
    """Health check for the RAG layer."""
    emb_ok = embedder_available()
    groq_configured = bool(settings.GROQ_API_KEY)
    backend = settings.GENERATION_BACKEND

    return Response({
        "embedder_ready": emb_ok,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "generation_backend": backend,
        "groq_configured": groq_configured,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "status": "ready" if emb_ok else "embedder_not_loaded",
    })
