"""User registration and lookup."""
from users.models import UserRecord


def get_or_create_user(phone_number: str, display_name: str = "") -> UserRecord:
    """Get existing user or create a new one. Updates last_active and display_name."""
    user, created = UserRecord.objects.get_or_create(
        phone_number=phone_number,
        defaults={"display_name": display_name},
    )
    if not created:
        update_fields = ["last_active"]
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            update_fields.append("display_name")
        user.save(update_fields=update_fields)
    return user
