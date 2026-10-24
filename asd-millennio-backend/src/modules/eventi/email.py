"""Email transazionali degli eventi campo, via Resend (stesso pattern di modules/soci/email.py)."""
import html

import httpx

from core.config import get_settings
from core.logger import logger

settings = get_settings()

RESEND_ENDPOINT = "https://api.resend.com/emails"

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def descrivi_evento(evento) -> str:
    giorno = GIORNI[evento.data.weekday()]
    titolo = f"{evento.titolo} — " if evento.titolo else ""
    sport = " / ".join(s.replace("_", " ").title() for s in evento.sport)
    return (
        f"{titolo}{sport}, {giorno} {evento.data.strftime('%d/%m/%Y')} "
        f"dalle {evento.ora_inizio.strftime('%H:%M')} alle {evento.ora_fine.strftime('%H:%M')}"
    )


def _layout(titolo: str, corpo: str) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#111827">
  <h2 style="color:#1d4ed8;margin:0 0 12px">{titolo}</h2>
  {corpo}
  <p style="font-size:12px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px;line-height:1.5">
    ASD Millennio — Palasirio. Email automatica, non serve rispondere.
  </p>
</div>"""


async def _invia(to: str, subject: str, body_html: str) -> bool:
    """True se inviata, False se saltata/fallita. Mai solleva: un'email non deve bloccare la richiesta."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY non configurata: email '%s' non inviata.", subject)
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                json={"from": settings.email_from, "to": [to], "subject": subject, "html": body_html},
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
        if resp.status_code >= 300:
            logger.error("Resend ha risposto %s per l'email '%s'", resp.status_code, subject)
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Invio email '%s' fallito: %s", subject, e)
        return False


async def invia_posto_libero(*, to: str, nome: str, evento) -> bool:
    desc = html.escape(descrivi_evento(evento))
    link = f"{settings.app_url}/dashboard/prenotazioni"
    corpo = (
        f'<p style="line-height:1.6">Ciao {html.escape(nome)},<br>'
        f"si è liberato un posto per l'evento <strong>{desc}</strong>, per cui eri in lista d'attesa.</p>"
        f'<p style="line-height:1.6">Il posto va a chi conferma per primo: '
        f'<a href="{link}" style="color:#1d4ed8">prenota ora dall\'area soci</a>.</p>'
    )
    return await _invia(to, "Si è liberato un posto al Palasirio", _layout("Posto disponibile", corpo))


async def invia_evento_annullato(*, to: str, nome: str, evento, rimborso: bool, in_credito: bool = False) -> bool:
    desc = html.escape(descrivi_evento(evento))
    if in_credito:
        nota = "L'importo pagato col credito ti è stato restituito sul credito della tua area soci."
    elif rimborso:
        nota = "Riceverai il rimborso dell'importo pagato online sullo stesso metodo di pagamento."
    else:
        nota = "Non è dovuto alcun pagamento."
    corpo = (
        f'<p style="line-height:1.6">Ciao {html.escape(nome)},<br>'
        f"l'evento <strong>{desc}</strong> è stato annullato dalla dirigenza.</p>"
        f'<p style="line-height:1.6">{nota}</p>'
    )
    return await _invia(to, "Evento al Palasirio annullato", _layout("Evento annullato", corpo))
