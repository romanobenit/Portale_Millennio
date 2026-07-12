"""
Invio email transazionali NFT tramite Resend (REST API via httpx).

Nessuna dipendenza extra: si usa l'HTTP API di Resend. Se RESEND_API_KEY non è
configurata, la funzione è un no-op che logga un warning (non blocca il mint).
"""
import base64

import httpx

from core.config import get_settings
from core.logger import logger

settings = get_settings()

RESEND_ENDPOINT = "https://api.resend.com/emails"


def _template_html(
    nome: str, token_id: int, ore_totali: int, importo: str, polygonscan_url: str
) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#111827">
  <h2 style="color:#1d4ed8;margin:0 0 4px">Grazie per il tuo sostegno, {nome}</h2>
  <p style="color:#6b7280;margin:0 0 16px">ASD Millennio — Raccolta fondi Palasirio</p>
  <p style="line-height:1.6">Il tuo contributo è stato registrato on-chain come NFT. In allegato trovi
  il <strong>certificato di sostegno</strong> (PDF) e il file <strong>iCal</strong> con le ore acquistate.</p>
  <table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
    <tr><td style="padding:6px 0;color:#6b7280">ID NFT</td><td style="padding:6px 0;text-align:right">#{token_id}</td></tr>
    <tr><td style="padding:6px 0;color:#6b7280">Ore sostenute</td><td style="padding:6px 0;text-align:right">{ore_totali}</td></tr>
    <tr><td style="padding:6px 0;color:#6b7280">Importo versato</td><td style="padding:6px 0;text-align:right">{importo}</td></tr>
  </table>
  <p style="margin:16px 0"><a href="{polygonscan_url}" style="color:#1d4ed8">Verifica l'NFT su Polygonscan &rarr;</a></p>
  <p style="font-size:12px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px;line-height:1.5">
    Questo token NON è uno strumento finanziario ai sensi della Direttiva MiFID II. Rappresenta esclusivamente
    il diritto d'uso del Palasirio per le fasce orarie specificate ed è personale e non trasferibile.
  </p>
</div>"""


async def invia_certificato_email(
    *,
    to: str,
    nome: str,
    token_id: int,
    ore_totali: int,
    importo: str,
    polygonscan_url: str,
    pdf_bytes: bytes,
    ical_content: str | None = None,
) -> bool:
    """
    Invia l'email con il certificato PDF (e l'iCal) in allegato.
    Restituisce True se inviata, False se saltata/fallita (mai solleva).
    """
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY non configurata: email certificato non inviata (token %s → %s).",
            token_id, to,
        )
        return False

    attachments = [{
        "filename": f"certificato-palasirio-nft-{token_id}.pdf",
        "content": base64.b64encode(pdf_bytes).decode(),
    }]
    if ical_content:
        attachments.append({
            "filename": f"palasirio-nft-{token_id}.ics",
            "content": base64.b64encode(ical_content.encode("utf-8")).decode(),
        })

    payload = {
        "from": settings.email_from,
        "to": [to],
        "subject": f"Grazie per il tuo sostegno — Certificato Palasirio NFT #{token_id}",
        "html": _template_html(nome, token_id, ore_totali, importo, polygonscan_url),
        "attachments": attachments,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
        if resp.status_code >= 300:
            logger.error(
                "Invio email certificato fallito (token %s): HTTP %s %s",
                token_id, resp.status_code, resp.text[:300],
            )
            return False
        logger.info("Email certificato inviata a %s (token %s).", to, token_id)
        return True
    except Exception as e:  # noqa: BLE001 — l'email non deve mai far fallire il mint
        logger.error("Errore invio email certificato (token %s): %s", token_id, e)
        return False
