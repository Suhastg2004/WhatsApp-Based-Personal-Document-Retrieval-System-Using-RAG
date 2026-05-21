from django.db import models
from users.models import UserRecord


class DocumentMetadata(models.Model):
    """Tracks documents uploaded by a user and their RAG document IDs."""

    user = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="documents")
    rag_document_id = models.CharField(max_length=64, unique=True, db_index=True)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    chunk_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.rag_document_id})"
