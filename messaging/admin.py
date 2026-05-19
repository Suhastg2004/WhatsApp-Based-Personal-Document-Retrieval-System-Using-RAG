from django.contrib import admin

from messaging.models import InboundMessage


@admin.register(InboundMessage)
class InboundMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "twilio_sid", "num_media", "created_at")
    search_fields = ("user__wa_id", "twilio_sid", "body")
    readonly_fields = ("created_at",)
