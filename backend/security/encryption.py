"""Data encryption for sensitive fields (API keys, tokens, PII)."""

from cryptography.fernet import Fernet

from backend.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet cipher from encryption key."""
    key = settings.encryption_key
    if not key:
        raise ValueError("ENCRYPTION_KEY must be set in environment")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_data(data: str) -> str:
    """Encrypt a string value."""
    fernet = _get_fernet()
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt an encrypted string value."""
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_data.encode()).decode()
