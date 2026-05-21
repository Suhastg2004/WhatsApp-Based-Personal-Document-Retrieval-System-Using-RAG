"""HMAC-SHA256 signature validation for Meta webhook payloads."""
import hashlib
import hmac


def validate_signature(payload_body: bytes, signature_header: str, app_secret: str) -> bool:
    """Validate the X-Hub-Signature-256 header from Meta.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of X-Hub-Signature-256 header (format: "sha256=<hex>").
        app_secret: The Meta app secret used as HMAC key.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = signature_header[7:]  # strip "sha256=" prefix
    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected_sig)
