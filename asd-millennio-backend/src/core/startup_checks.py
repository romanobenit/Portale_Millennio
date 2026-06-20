"""
Validazione configurazione all'avvio.
Verifica solo PRESENZA e FORMATO delle variabili — mai codificare frammenti di valori reali.
"""
import re
import sys

from core.config import get_settings
from core.logger import logger

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ETH_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
_POLY_CHAIN_IDS = {80002, 137}


def validate_production_config() -> None:
    """Chiamata durante il lifespan all'avvio. Termina il processo se la config è incompleta."""
    s = get_settings()
    if s.node_env != "production":
        return

    errors: list[str] = []

    if not s.database_url or "postgresql" not in s.database_url:
        errors.append("DATABASE_URL mancante o non valido (deve iniziare con postgresql+asyncpg://)")

    if not s.stripe_secret_key or not s.stripe_secret_key.startswith("sk_"):
        errors.append("STRIPE_SECRET_KEY mancante o non valido (deve iniziare con sk_)")

    if not s.stripe_webhook_secret or len(s.stripe_webhook_secret) < 32:
        errors.append("STRIPE_WEBHOOK_SECRET mancante o troppo corto")

    if not s.wallet_encryption_key or not _HEX64.match(s.wallet_encryption_key):
        errors.append("WALLET_ENCRYPTION_KEY deve essere una stringa hex di 64 caratteri (32 byte)")

    if not s.contract_address_palasirion_nft or not _ETH_ADDR.match(s.contract_address_palasirion_nft):
        errors.append("CONTRACT_ADDRESS_PALASIRION_NFT deve essere un indirizzo Ethereum valido (0x...)")

    if not s.polygon_rpc_url or not s.polygon_rpc_url.startswith("https://"):
        errors.append("POLYGON_RPC_URL deve essere un endpoint HTTPS")

    if s.polygon_chain_id not in _POLY_CHAIN_IDS:
        errors.append(f"POLYGON_CHAIN_ID deve essere 80002 (Amoy) o 137 (mainnet), trovato: {s.polygon_chain_id}")

    # removeprefix("0x") rimuove solo il prefisso "0x" se presente (Python 3.9+).
    # lstrip("0x") rimuoverebbe qualsiasi combinazione di '0' e 'x' iniziali — bug.
    if not s.minter_private_key or not _HEX64.match(s.minter_private_key.removeprefix("0x")):
        errors.append("MINTER_PRIVATE_KEY mancante o non valido (64 hex chars, con o senza prefisso 0x)")

    if not s.pinata_api_key or not s.pinata_secret_key:
        errors.append("PINATA_API_KEY / PINATA_SECRET_KEY mancanti")

    if not s.resend_api_key:
        errors.append("RESEND_API_KEY mancante")

    if not s.keycloak_client_secret:
        errors.append("KEYCLOAK_CLIENT_SECRET mancante")

    if s.jwt_secret in ("change-me-in-production", "", None):
        errors.append("JWT_SECRET non configurato — usare un segreto forte in produzione")

    if errors:
        for e in errors:
            logger.critical("AVVIO BLOCCATO — CONFIG INVALIDA: %s", e)
        sys.exit(1)

    logger.info("Validazione configurazione produzione: OK (12 variabili verificate)")
