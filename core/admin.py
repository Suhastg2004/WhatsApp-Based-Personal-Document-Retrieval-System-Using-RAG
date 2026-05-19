from django.contrib import admin

from core.models import WhatsAppUser


@admin.register(WhatsAppUser)
class WhatsAppUserAdmin(admin.ModelAdmin):
    list_display = ("wa_id", "display_name", "is_active", "last_seen_at", "created_at")
    search_fields = ("wa_id", "display_name")
    list_filter = ("is_active",)
