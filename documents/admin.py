from django.contrib import admin

from documents.models import Chunk, Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source", "status", "chunk_count", "created_at")
    list_filter = ("status", "file_type")
    search_fields = ("source", "title", "user__wa_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "user", "chunk_index", "created_at")
    search_fields = ("document__source", "user__wa_id", "text")
