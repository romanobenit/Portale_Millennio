"""
Alert scadenza certificato medico, via Resend (stesso pattern di modules/nft/email.py).
"""
import httpx

from core.config import get_settings
from core.logger import logger

settings = get_settings()

RESEND_ENDPOINT = "https://api.resend.com/emails"


def _template_html(nome: str, giorni_mancanti: int, scadenza: str, numero_tessera: str, nome_tesserato: str | None) -> str:
    riferimento = f" di <strong>{nome_tesserato}</strong>" if nome_tesserato else ""
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#111827">
  <h2 style="color:#b45309;margin:0 0 4px">Il certificato medico{riferimento} sta per scadere</h2>
  <p style="color:#6b7280;margin:0 0 16px">ASD Millennio — Tessera {numero_tessera}</p>
  <p style="line-height:1.6">Ciao {nome},<br>
  il certificato di idoneità sportiva{riferimento} scade tra <strong>{giorni_mancanti} giorni</strong>
  (il {scadenza}). Ricordati di rinnovarlo e caricare il nuovo certificato dall'area soci.</p>
  <p style="font-size:12px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px;line-height:1.5">
    Questo è un promemoria automatico, non serve rispondere a questa email.
  </p>
</div>"""


async def invia_alert_certificato_medico(
    *,
    to: str,
    nome: str,
    giorni_mancanti: int,
    scadenza: str,
    numero_tessera: str,
    nome_tesserato: str | None = None,
) -> bool:
    """Restituisce True se inviata, False se saltata/fallita (mai solleva — non deve bloccare il task)."""
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY non configurata: alert certificato medico non inviato (%s, tessera %s).",
            to, numero_tessera,
        )
        return False

    payload = {
        "from": settings.email_from,
        "to": [to],
        "subject": f"Certificato medico{' di ' + nome_tesserato if nome_tesserato else ''} in scadenza tra {giorni_mancanti} giorni",
        "html": _template_html(nome, giorni_mancanti, scadenza, numero_tessera, nome_tesserato),
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
                "Invio alert certificato medico fallito (%s, tessera %s): HTTP %s %s",
                to, numero_tessera, resp.status_code, resp.text[:300],
            )
            return False
        logger.info("Alert certificato medico inviato a %s (tessera %s, %s giorni).", to, numero_tessera, giorni_mancanti)
        return True
    except Exception as e:  # noqa: BLE001 — l'email non deve mai far fallire il task
        logger.error("Errore invio alert certificato medico (%s, tessera %s): %s", to, numero_tessera, e)
        return False
