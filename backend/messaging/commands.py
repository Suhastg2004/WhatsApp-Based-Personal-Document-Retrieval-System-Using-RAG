"""Command router for slash commands."""
from __future__ import annotations

from documents.services import delete_document, list_documents, reset_user
from users.models import UserRecord

HELP_TEXT = (
    "👋 Welcome! I'm your personal document assistant.\n\n"
    "• Send me a *PDF, image, or document* to remember it.\n"
    "• Then ask anything in plain English.\n\n"
    "Commands:\n"
    "  /help — show this help\n"
    "  /list — list your stored documents\n"
    "  /delete <id> — delete a document\n"
    "  /reset — delete all your documents"
)


def route_command(user: UserRecord, text: str) -> str | None:
    """If text is a slash command, handle it and return response. Otherwise return None."""
    if not text.startswith("/"):
        return None

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/help", "/start"):
        return HELP_TEXT

    if cmd == "/list":
        return list_documents(user)

    if cmd == "/delete":
        if not arg:
            return "Usage: /delete <document_id>"
        return delete_document(user, arg)

    if cmd == "/reset":
        return reset_user(user)

    if cmd == "/save":
        return "✅ Your data is saved automatically. No action needed!"

    return f"Unknown command: {cmd}\nType /help to see available commands."
