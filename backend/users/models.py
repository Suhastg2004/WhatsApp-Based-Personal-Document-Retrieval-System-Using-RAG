from django.db import models


class UserRecord(models.Model):
    """A WhatsApp user identified by phone number."""

    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_active"]

    def __str__(self) -> str:
        return self.phone_number
