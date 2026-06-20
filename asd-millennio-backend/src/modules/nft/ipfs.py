import base64
import json

import httpx

from core.config import get_settings
from core.logger import logger

settings = get_settings()

PINATA_BASE = "https://api.pinata.cloud"


def _headers() -> dict:
    return {
        "pinata_api_key": settings.pinata_api_key,
        "pinata_secret_api_key": settings.pinata_secret_key,
    }


async def upload_json_to_ipfs(metadata: dict) -> str:
    """Carica JSON dei metadati NFT su IPFS tramite Pinata. Restituisce l'URI ipfs://..."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{PINATA_BASE}/pinning/pinJSONToIPFS",
            json={"pinataContent": metadata, "pinataMetadata": {"name": "palasirion-nft"}},
            headers=_headers(),
        )
        resp.raise_for_status()
        cid = resp.json()["IpfsHash"]
        return f"ipfs://{cid}"


async def upload_file_to_ipfs(content: str, filename: str) -> str:
    """Carica file testuale su IPFS tramite Pinata. Restituisce ipfs://..."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        files = {"file": (filename, content.encode("utf-8"), "text/calendar")}
        resp = await client.post(
            f"{PINATA_BASE}/pinning/pinFileToIPFS",
            files=files,
            headers=_headers(),
        )
        resp.raise_for_status()
        cid = resp.json()["IpfsHash"]
        return f"ipfs://{cid}"


def costruisci_metadati_nft(
    slots_count: int,
    data_primo_slot: str,
    fascia_prevalente: str,
    ore_totali: int,
    importo_eur: float,
    ical_content: str,
    ical_sha256: str,
    tessera_id: str,
) -> dict:
    ical_b64 = base64.b64encode(ical_content.encode("utf-8")).decode()
    return {
        "name": f"Diritto d'uso Palasirion — {slots_count} slot — ASD Millennio",
        "description": (
            "Questo token NON è uno strumento finanziario ai sensi della Direttiva MiFID II. "
            "Rappresenta esclusivamente il diritto d'uso del Palasirion per le fasce orarie "
            "specificate. Non garantisce rendimenti economici."
        ),
        "attributes": [
            {"trait_type": "Numero slot", "value": str(slots_count)},
            {"trait_type": "Data primo slot", "value": data_primo_slot},
            {"trait_type": "Fascia oraria", "value": fascia_prevalente},
            {"trait_type": "Ore totali", "value": str(ore_totali)},
            {"trait_type": "Valore pagato (€)", "value": str(importo_eur)},
        ],
        "ical_content": ical_b64,
        "ical_sha256": ical_sha256,
        "asd_member_id": tessera_id,
        "legal_disclaimer": (
            "Diritto d'uso personale e non trasferibile. "
            "Subordinato al mantenimento della qualità di socio attivo ASD Millennio."
        ),
    }
