from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_url: str = "http://localhost:8000"
    node_env: str = "development"
    jwt_secret: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/millennio"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "millennio-asd"
    keycloak_client_id: str = "millennio-backend"
    keycloak_client_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # Blockchain
    polygon_rpc_url: str = ""
    polygon_chain_id: int = 80002
    contract_address_palasirio_nft: str = ""
    minter_private_key: str = ""

    # IPFS / Pinata
    pinata_api_key: str = ""
    pinata_secret_key: str = ""
    pinata_gateway_url: str = "https://gateway.pinata.cloud"

    # Wallet custodiale
    wallet_encryption_key: str = ""

    # Documenti sensibili (identità, prova tutela) — storage cifrato su volume privato
    documenti_storage_path: str = "/data/documenti"
    document_encryption_key: str = ""  # se vuota, usa wallet_encryption_key

    # Verifica tesseramento self-service
    tesseramento_verifica_giorni: int = 30  # giorni entro cui lo staff conferma (silenzio-assenso)

    # Email — Resend
    resend_api_key: str = ""
    email_from: str = "noreply@millennioasd.com"

    # Business logic
    fundraising_target_eur: int = 300000
    anno_sportivo_corrente: str = "2026-2027"
    tessera_scadenza_mese: int = 6
    tessera_scadenza_giorno: int = 30

    # Periodo di vendita slot Palasirio (inclusivo)
    calendario_inizio: str = "2027-01-01"
    calendario_fine: str = "2042-12-31"


@lru_cache
def get_settings() -> Settings:
    return Settings()
