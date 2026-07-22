"""Crypto tests."""
import pytest
from utils.crypto_utils import CryptoManager


def test_encrypt_decrypt():
    """Test encryption and decryption."""
    manager = CryptoManager("test-master-key-32-chars-long!!!")
    plaintext = "my-secret-api-key-12345"
    encrypted = manager.encrypt(plaintext)
    decrypted = manager.decrypt(encrypted)
    assert decrypted == plaintext


def test_different_salts():
    """Test that each encryption uses different salt."""
    manager = CryptoManager("test-master-key-32-chars-long!!!")
    plaintext = "same-text"
    encrypted1 = manager.encrypt(plaintext)
    encrypted2 = manager.encrypt(plaintext)
    assert encrypted1 != encrypted2
    assert manager.decrypt(encrypted1) == plaintext
    assert manager.decrypt(encrypted2) == plaintext


def test_invalid_key():
    """Test decryption with wrong key fails."""
    manager1 = CryptoManager("test-master-key-32-chars-long!!!")
    manager2 = CryptoManager("wrong-master-key-32-chars-long!!")
    encrypted = manager1.encrypt("secret")
    with pytest.raises(Exception):
        manager2.decrypt(encrypted)
