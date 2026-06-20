import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from eth_account import Account

from core.config import get_settings
from core.logger import logger

settings = get_settings()


def _get_aes_key() -> bytes:
    key_hex = settings.wallet_encryption_key
    if not key_hex:
        raise RuntimeError("WALLET_ENCRYPTION_KEY non configurata")
    if len(key_hex) != 64:
        raise RuntimeError(
            "WALLET_ENCRYPTION_KEY deve essere una stringa hex di 64 caratteri (32 byte). "
            "Genera con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return bytes.fromhex(key_hex)


def genera_wallet() -> tuple[str, str]:
    """Genera un wallet Ethereum. Restituisce (address, encrypted_private_key)."""
    account = Account.create()
    address = account.address
    private_key = account.key.hex()
    encrypted = _cifra_chiave(private_key)
    return address, encrypted


def _cifra_chiave(private_key: str) -> str:
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, private_key.encode(), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode()


def _decifra_chiave(encrypted: str) -> str:
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    combined = base64.b64decode(encrypted)
    nonce = combined[:12]
    ciphertext = combined[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


def get_account_from_encrypted(encrypted_key: str):
    private_key = _decifra_chiave(encrypted_key)
    return Account.from_key(private_key)
