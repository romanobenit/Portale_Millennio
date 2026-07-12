"""
Storage cifrato per documenti sensibili (identità, prova tutela).

I file NON sono mai serviti pubblicamente: vivono su un volume Docker privato,
cifrati a riposo con AES-256-GCM (stessa primitiva dei wallet custodiali), e
sono leggibili solo tramite endpoint autenticato (proprietario o staff).
GDPR: `elimina_documento` cancella il file dal disco (cancellazione effettiva).
"""
import os
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import get_settings
from core.logger import logger

settings = get_settings()

MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB per documento
MIME_CONSENTITI = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _get_key() -> bytes:
    key_hex = settings.document_encryption_key or settings.wallet_encryption_key
    if not key_hex:
        raise RuntimeError(
            "DOCUMENT_ENCRYPTION_KEY (o WALLET_ENCRYPTION_KEY) non configurata: "
            "impossibile cifrare i documenti."
        )
    if len(key_hex) != 64:
        raise RuntimeError(
            "La chiave di cifratura documenti deve essere hex di 64 caratteri (32 byte)."
        )
    return bytes.fromhex(key_hex)


def _abs_path(rel_path: str) -> str:
    # difesa da path traversal: consenti solo un nome file semplice dentro la base
    base = os.path.abspath(settings.documenti_storage_path)
    full = os.path.abspath(os.path.join(base, rel_path))
    if os.path.commonpath([base, full]) != base:
        raise ValueError("Percorso documento non valido")
    return full


def salva_documento(content: bytes, content_type: str) -> tuple[str, int]:
    """
    Cifra e salva un documento sul volume privato. Restituisce (rel_path, size_bytes).
    Solleva ValueError se il tipo/dimensione non sono ammessi.
    """
    if content_type not in MIME_CONSENTITI:
        raise ValueError(f"Tipo file non ammesso: {content_type}")
    if len(content) > MAX_DOC_BYTES:
        raise ValueError("File troppo grande (max 10 MB)")
    if not content:
        raise ValueError("File vuoto")

    os.makedirs(settings.documenti_storage_path, exist_ok=True)
    # nome file opaco: niente PII nel filesystem
    ts = datetime.now(timezone.utc).strftime("%Y%m")
    rel_path = f"{ts}_{uuid.uuid4().hex}.bin"

    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, content, None)

    with open(_abs_path(rel_path), "wb") as f:
        f.write(nonce + ciphertext)

    return rel_path, len(content)


def leggi_documento(rel_path: str) -> bytes:
    """Decifra e restituisce il contenuto del documento."""
    with open(_abs_path(rel_path), "rb") as f:
        blob = f.read()
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(blob[:12], blob[12:], None)


def elimina_documento(rel_path: str) -> None:
    """Cancella fisicamente il documento (GDPR Art. 17). Best-effort."""
    try:
        os.remove(_abs_path(rel_path))
    except FileNotFoundError:
        pass
    except Exception as e:  # noqa: BLE001
        logger.error("Errore cancellazione documento %s: %s", rel_path, e)
