from django.db import models

from core.models import WhatsAppUser


class InboundMessage(models.Model):
    """Audit log of every inbound WhatsApp message we processed."""

    user = models.ForeignKey(WhatsAppUser, related_name="inbound_messages", on_delete=models.CASCADE)
    twilio_sid = models.CharField(max_length=64, blank=True, default="")
    body = models.TextField(blank=True, default="")
    num_media = models.PositiveIntegerField(default=0)
    reply = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.wa_id} :: {self.twilio_sid or self.id}"
