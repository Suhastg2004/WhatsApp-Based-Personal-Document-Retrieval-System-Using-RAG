import uuid

from django.db import models

from core.models import WhatsAppUser


def _upload_to(instance: "Document", filename: str) -> str:
    return f"uploads/{instance.user.wa_id}/{instance.id}_{filename}"


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(WhatsAppUser, related_name="documents", on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=255, help_text="Original filename")
    file_type = models.CharField(max_length=16, blank=True, default="")
    file = models.FileField(upload_to=_upload_to, blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    chunk_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self) -> str:
        return f"{self.source} ({self.id})"


class Chunk(models.Model):
    """A retrievable text chunk with its embedding stored as JSON."""

    document = models.ForeignKey(Document, related_name="chunks", on_delete=models.CASCADE)
    user = models.ForeignKey(WhatsAppUser, related_name="chunks", on_delete=models.CASCADE)
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    vector = models.TextField(blank=True, default="", help_text="JSON-encoded float vector")
    is_embedded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        indexes = [models.Index(fields=["user"])]
        unique_together = ("document", "chunk_index")

    def __str__(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"
