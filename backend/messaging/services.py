"""Message logging utilities."""
from __future__ import annotations

import logging

from messaging.models import MessageLog
from users.models import UserRecord

logger = logging.getLogger(__name__)


def log_inbound(
    user: UserRecord,
    message_type: str,
    content_summary: str,
    meta_message_id: str | None = None,
) -> MessageLog:
    """Record an inbound message in the audit log."""
    return MessageLog.objects.create(
        user=user,
        direction="inbound",
        message_type=message_type,
        content_summary=content_summary[:500],  # truncate for storage
        meta_message_id=meta_message_id,
    )


def log_outbound(
    user: UserRecord,
    content_summary: str,
    meta_message_id: str | None = None,
) -> MessageLog:
    """Record an outbound message in the audit log."""
    return MessageLog.objects.create(
        user=user,
        direction="outbound",
        message_type="text",
        content_summary=content_summary[:500],  # truncate for storage
        meta_message_id=meta_message_id,
    )
