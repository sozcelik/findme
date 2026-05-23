"""
Lightweight credential encryption using Fernet (AES-128-CBC + HMAC).
In production, replace with Supabase Vault for proper secret isolation.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.encryption_key
        if not key:
            # Derive a stable key from the JWT secret if no dedicated key is configured
            raw = (settings.supabase_jwt_secret or "dev-insecure-key-change-me").encode()
            derived = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
            key = derived.decode()
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
