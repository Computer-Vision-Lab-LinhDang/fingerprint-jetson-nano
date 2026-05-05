"""Payload encryption utilities for the Jetson Nano worker.

Compatible with Python 3.6+ (Jetson Nano).
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.

The shared secret key is read from:
  - Settings().encryption_key  (env var: WORKER_ENCRYPTION_KEY)
  - Falls back to WORKER_ENCRYPTION_KEY env var directly

Generate a key once and put it in BOTH .env files:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
import os

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Lazily initialize the Fernet cipher.

    Key priority:
    1. WORKER_ENCRYPTION_KEY env var (matches Settings prefix)
    2. ENCRYPTION_KEY env var (fallback)
    """
    global _fernet
    if _fernet is not None:
        return _fernet

    from cryptography.fernet import Fernet

    key = (
        os.environ.get("WORKER_ENCRYPTION_KEY", "")
        or os.environ.get("ENCRYPTION_KEY", "")
    ).strip()

    if not key:
        raise RuntimeError(
            "Encryption key not set. Add WORKER_ENCRYPTION_KEY to your .env file.\n"
            "Generate a key with:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    _fernet = Fernet(key.encode())
    logger.debug("Fernet cipher initialized.")
    return _fernet


def reset_fernet():
    # type: () -> None
    """Reset cached cipher (useful for testing or key rotation)."""
    global _fernet
    _fernet = None


def is_encryption_enabled():
    # type: () -> bool
    """Return True if WORKER_ENCRYPTION_KEY is configured."""
    key = (
        os.environ.get("WORKER_ENCRYPTION_KEY", "")
        or os.environ.get("ENCRYPTION_KEY", "")
    ).strip()
    return bool(key)


# ── Image encryption ──────────────────────────────────────────────────────────


def encrypt_image_bytes(image_bytes):
    # type: (bytes) -> str
    """Encrypt raw image bytes → encrypted base64 string for JSON transport.

    Args:
        image_bytes: Raw fingerprint image data (e.g. TIFF bytes).

    Returns:
        URL-safe base64 string containing the encrypted ciphertext.
        This string replaces the plain ``image_base64`` field in MQTT payloads.
    """
    fernet = _get_fernet()
    encrypted = fernet.encrypt(image_bytes)   # bytes, already base64url-safe
    result = encrypted.decode("utf-8")
    logger.debug(
        "encrypt_image_bytes: %d bytes → %d chars (encrypted)", len(image_bytes), len(result)
    )
    return result


def decrypt_image_bytes(encrypted_b64):
    # type: (str) -> bytes
    """Decrypt an encrypted base64 string back to raw image bytes.

    Args:
        encrypted_b64: The string produced by :func:`encrypt_image_bytes`.

    Returns:
        Original raw image bytes.

    Raises:
        cryptography.fernet.InvalidToken: If the token is tampered or the key is wrong.
    """
    fernet = _get_fernet()
    result = fernet.decrypt(encrypted_b64.encode("utf-8"))
    logger.debug(
        "decrypt_image_bytes: %d chars → %d bytes (decrypted)", len(encrypted_b64), len(result)
    )
    return result


# ── Generic field encryption ──────────────────────────────────────────────────


def encrypt_field(text):
    # type: (str) -> str
    """Encrypt a plain-text string (e.g. a JSON-serialised embedding vector).

    Args:
        text: Plain text to encrypt.

    Returns:
        Encrypted string safe for JSON transport.
    """
    fernet = _get_fernet()
    return fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_field(encrypted_text):
    # type: (str) -> str
    """Decrypt a field encrypted by :func:`encrypt_field`.

    Args:
        encrypted_text: Encrypted string.

    Returns:
        Original plain text.
    """
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
