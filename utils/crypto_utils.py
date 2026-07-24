"""
V10 NEXUS Swarm — Cryptography Utilities
=========================================
PBKDF2HMAC с случайной солью для каждого шифрования.
Соль хранится вместе с зашифрованными данными (prepended).
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoManager:
    """Manages encryption/decryption of API keys with random per-key salt."""

    def __init__(self, master_key: str):
        """
        Args:
            master_key: Hex-encoded master key (64 chars = 32 bytes)
        """
        if not master_key or len(master_key) < 32:
            raise ValueError("MASTER_KEY must be at least 32 characters")
        self._master_key = master_key.encode("utf-8")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key + random salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,  # OWASP recommendation 2023
        )
        return base64.urlsafe_b64encode(kdf.derive(self._master_key))

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with random salt.
        Format: base64(salt + ciphertext)
        """
        salt = os.urandom(16)  # 128-bit random salt
        key = self._derive_key(salt)
        f = Fernet(key)
        ciphertext = f.encrypt(plaintext.encode("utf-8"))
        # Prepend salt to ciphertext for storage
        combined = salt + ciphertext
        return base64.urlsafe_b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt data. Extracts salt from beginning of data.
        """
        combined = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
        salt = combined[:16]
        ciphertext = combined[16:]
        key = self._derive_key(salt)
        f = Fernet(key)
        return f.decrypt(ciphertext).decode("utf-8")

    def hash_api_key(self, api_key: str) -> str:
        """Create a non-reversible hash for logging/display (not for storage)."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]


# Singleton instance (initialized in app factory)
_crypto_manager: CryptoManager | None = None


def init_crypto_manager(master_key: str) -> None:
    """Initialize global crypto manager."""
    global _crypto_manager
    _crypto_manager = CryptoManager(master_key)


def get_crypto_manager() -> CryptoManager:
    """Get initialized crypto manager."""
    if _crypto_manager is None:
        raise RuntimeError(
            "CryptoManager not initialized. Call init_crypto_manager() first."
        )
    return _crypto_manager
