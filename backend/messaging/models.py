from django.db import models
from users.models import UserRecord


class MessageLog(models.Model):
    """Audit log for all inbound and outbound WhatsApp messages."""

    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    ]

    user = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="messages")
    direction = models.CharField(max_length=8, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=20)
    content_summary = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    meta_message_id = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.direction} {self.message_type} → {self.user.phone_number}"
