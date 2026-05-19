from rest_framework import serializers

from documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id",
            "user",
            "title",
            "source",
            "file_type",
            "status",
            "chunk_count",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
