from django.db import models


class WhatsAppUser(models.Model):
    """A WhatsApp end-user identified by their phone in 'whatsapp:+E164' form."""

    wa_id = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=128, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return self.wa_id
