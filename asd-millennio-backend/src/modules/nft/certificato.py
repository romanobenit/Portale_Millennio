"""
Generatore del Certificato di sostegno Palasirio (PDF A4 verticale, celebrativo).

Prodotto automaticamente alla conferma del mint NFT e allegato all'email al socio.
Due pagine:
  1. Certificato: ringraziamenti, dati di autenticità on-chain (account Ethereum,
     ID NFT, contratto, transazione di conio, hash IPFS), QR di verifica, firma.
  2. Allegato A: elenco completo delle ore sostenute + totale.

Dipendenze: reportlab, qrcode[pil], Pillow (già usate da soci/pdf.py).
"""
import io
import os
from datetime import date

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from core.logger import logger

_LOGO_SVG = os.path.join(os.path.dirname(__file__), "assets", "logo_millennio.svg")
# Cache del logo vettoriale (Drawing reportlab) per larghezza: svg2rlg è lento.
_logo_cache: dict[float, object] = {}

ORO = colors.HexColor("#BA7517")
ORO_CHIARO = colors.HexColor("#EF9F27")
ORO_SCURO = colors.HexColor("#854F0B")
BLU_ASD = colors.HexColor("#1d4ed8")
GRIGIO = colors.HexColor("#6b7280")
GRIGIO_CHIARO = colors.HexColor("#9ca3af")
NERO = colors.HexColor("#111827")

FASCIA_LABEL = {"notte": "Notte", "mattina": "Mattina", "pomeriggio": "Pomeriggio"}
GIORNI_ABBR = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]

PAGE_W, PAGE_H = A4
CX = PAGE_W / 2


def _fmt_importo(importo: float) -> str:
    return f"€ {importo:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _fmt_data(d: date) -> str:
    return f"{GIORNI_ABBR[d.weekday()]} {d.strftime('%d/%m/%Y')}"


def _fmt_ora(ora: int) -> str:
    return f"{ora:02d}:00–{(ora + 1) % 24:02d}:00"


def _cornice(c: canvas.Canvas) -> None:
    """Cornice dorata a doppio filo con losanghe agli angoli — disegnata su ogni pagina."""
    m = 22
    c.setStrokeColor(ORO)
    c.setLineWidth(2)
    c.rect(m, m, PAGE_W - 2 * m, PAGE_H - 2 * m, fill=0, stroke=1)
    c.setStrokeColor(ORO_CHIARO)
    c.setLineWidth(0.5)
    c.rect(m + 6, m + 6, PAGE_W - 2 * (m + 6), PAGE_H - 2 * (m + 6), fill=0, stroke=1)
    c.setFillColor(ORO)
    for cx, cy in [(m, m), (PAGE_W - m, m), (m, PAGE_H - m), (PAGE_W - m, PAGE_H - m)]:
        c.saveState()
        c.translate(cx, cy)
        c.rotate(45)
        c.rect(-4, -4, 8, 8, fill=1, stroke=0)
        c.restoreState()


def _center(c: canvas.Canvas, text: str, y: float, font: str, size: float, color) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(CX, y, text)


def _carica_logo(target_w: float):
    """
    Carica il logo ASD Millennio (SVG) come Drawing reportlab, ritagliato al
    contenuto e scalato a `target_w` pt. Vettoriale (niente rasterizzazione).
    Ritorna None se svglib/il file non sono disponibili → fallback medaglione.
    """
    if target_w in _logo_cache:
        return _logo_cache[target_w]
    try:
        from reportlab.graphics.shapes import Drawing, Group
        from svglib.svglib import svg2rlg

        src = svg2rlg(_LOGO_SVG)
        x1, y1, x2, y2 = src.getBounds()
        cw, ch = (x2 - x1) or 1, (y2 - y1) or 1
        scale = target_w / cw
        g = Group(src)
        # mappa il bounding box del contenuto esattamente in [0..target_w] x [0..h]
        g.transform = (scale, 0, 0, scale, -x1 * scale, -y1 * scale)
        d = Drawing(cw * scale, ch * scale)
        d.add(g)
        _logo_cache[target_w] = d
        return d
    except Exception as e:  # noqa: BLE001 — fallback grazioso al medaglione "M"
        logger.warning("Logo Millennio non caricato (%s): uso il medaglione di fallback.", e)
        _logo_cache[target_w] = None
        return None


def _medaglione(c: canvas.Canvas, cx: float, cy: float, r: float, glyph: str, size: float) -> None:
    c.setStrokeColor(ORO)
    c.setLineWidth(2)
    c.circle(cx, cy, r, fill=0, stroke=1)
    c.setFont("Times-Bold", size)
    c.setFillColor(ORO)
    c.drawCentredString(cx, cy - size * 0.34, glyph)


def _qr_image(url: str) -> ImageReader:
    qr = qrcode.QRCode(box_size=4, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _riga_blockchain(c: canvas.Canvas, x: float, y: float, label: str, value: str) -> float:
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIGIO)
    c.drawString(x, y, label)
    c.setFont("Courier", 8.3)
    c.setFillColor(NERO)
    c.drawString(x, y - 11, value)
    return y - 26


def _pagina_certificato(c: canvas.Canvas, ctx: dict) -> None:
    from reportlab.graphics import renderPDF

    _cornice(c)

    logo = _carica_logo(150)
    if logo is not None:
        # logo vettoriale centrato in alto (marchio "a picchi" ASD Millennio)
        c.saveState()
        renderPDF.draw(logo, c, CX - logo.width / 2, PAGE_H - 96)
        c.restoreState()
    else:
        _medaglione(c, CX, PAGE_H - 92, 24, "M", 28)
    _center(c, "ASD MILLENNIO", PAGE_H - 116, "Helvetica", 9, GRIGIO)

    c.setStrokeColor(ORO)
    c.setLineWidth(0.5)
    c.line(CX - 70, PAGE_H - 150, CX - 18, PAGE_H - 150)
    c.line(CX + 18, PAGE_H - 150, CX + 70, PAGE_H - 150)
    c.setFillColor(ORO)
    c.setFont("Times-Bold", 13)
    c.drawCentredString(CX, PAGE_H - 155, "✦")

    _center(c, "Certificato di sostegno", PAGE_H - 192, "Times-Bold", 30, NERO)
    _center(c, "Raccolta fondi Palasirio — diritto d'uso registrato come NFT",
            PAGE_H - 210, "Helvetica", 10, GRIGIO)

    _center(c, "Con sincera gratitudine, l'ASD Millennio conferisce a",
            PAGE_H - 250, "Helvetica", 11, NERO)
    _center(c, f"{ctx['nome']} {ctx['cognome']}", PAGE_H - 280, "Times-Bold", 24, NERO)
    _center(c, "questo attestato per aver sostenuto l'associazione e l'impianto Palasirio.",
            PAGE_H - 304, "Helvetica", 10, GRIGIO)
    if ctx.get("tessera_sostenitore"):
        _center(c, f"Socio sostenitore · tessera {ctx['tessera_sostenitore']}",
                PAGE_H - 320, "Helvetica", 10, GRIGIO)

    box_x, box_w = 70, PAGE_W - 140
    box_top, box_bottom = PAGE_H - 350, PAGE_H - 500
    c.setStrokeColor(ORO_CHIARO)
    c.setLineWidth(0.5)
    c.rect(box_x, box_bottom, box_w, box_top - box_bottom, fill=0, stroke=1)
    c.setFont("Helvetica", 9)
    c.setFillColor(ORO_SCURO)
    c.drawCentredString(CX, box_top - 18, "AUTENTICITÀ ON-CHAIN · POLYGON")

    y = box_top - 40
    tx = ctx.get("mint_tx_hash") or "—"
    y = _riga_blockchain(c, box_x + 16, y, "Account Ethereum", ctx["wallet_address"])
    y = _riga_blockchain(c, box_x + 16, y, "ID NFT · contratto",
                         f"#{ctx['token_id']} · {ctx['contract_address']}")
    y = _riga_blockchain(c, box_x + 16, y, "Transazione di conio", tx)
    y = _riga_blockchain(c, box_x + 16, y, "Metadati IPFS", ctx["ipfs_uri"])

    qr_size = 70
    c.drawImage(ctx["qr"], box_x + box_w - qr_size - 16, box_bottom + 16,
                qr_size, qr_size, mask="auto")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIGIO)
    c.drawCentredString(box_x + box_w - qr_size / 2 - 16, box_bottom + 6, "Polygonscan")

    _medaglione(c, box_x + 26, PAGE_H - 552, 22, "★", 18)
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIGIO)
    c.drawString(box_x + 4, PAGE_H - 590, f"Palasirio, {ctx['data_emissione']}")

    sig_cx = PAGE_W - 140
    c.setFont("Times-Italic", 14)
    c.setFillColor(NERO)
    c.drawCentredString(sig_cx, PAGE_H - 560, "Il Presidente")
    c.setStrokeColor(ORO)
    c.setLineWidth(0.5)
    c.line(sig_cx - 65, PAGE_H - 572, sig_cx + 65, PAGE_H - 572)
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIGIO)
    c.drawCentredString(sig_cx, PAGE_H - 585, "ASD Millennio")

    _center(c, "Token personale e non trasferibile · non è uno strumento finanziario (Direttiva MiFID II).",
            PAGE_H - 640, "Helvetica", 8.5, GRIGIO_CHIARO)
    _center(c, "Il dettaglio delle ore sostenute è riportato nell'Allegato A.",
            PAGE_H - 654, "Helvetica", 8.5, GRIGIO_CHIARO)


def _pagina_allegato(c: canvas.Canvas, ctx: dict) -> None:
    _cornice(c)

    _center(c, "Allegato A", PAGE_H - 96, "Helvetica", 10, ORO_SCURO)
    _center(c, "Dettaglio delle ore sostenute", PAGE_H - 124, "Times-Bold", 22, NERO)
    _center(c, f"Relativo al certificato NFT #{ctx['token_id']}"
               + (f" · tessera {ctx['tessera_sostenitore']}" if ctx.get("tessera_sostenitore") else ""),
            PAGE_H - 142, "Helvetica", 10, GRIGIO)

    left, right = 80, PAGE_W - 80
    y = PAGE_H - 180
    c.setStrokeColor(ORO_CHIARO)
    c.setLineWidth(0.5)
    c.line(left, y, right, y)

    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ORO_SCURO)
    c.drawString(left, y, "Data")
    c.drawString(left + 200, y, "Fascia")
    c.drawRightString(right, y, "Ora")
    y -= 6
    c.setStrokeColor(ORO_CHIARO)
    c.line(left, y, right, y)

    c.setFont("Helvetica", 10)
    for ora in ctx["ore"]:
        y -= 22
        c.setFillColor(NERO)
        c.drawString(left, y, _fmt_data(ora["data"]))
        c.drawString(left + 200, y, FASCIA_LABEL.get(ora["fascia"], ora["fascia"]))
        c.drawRightString(right, y, _fmt_ora(ora["ora"]))
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.4)
        c.line(left, y - 7, right, y - 7)

    y -= 34
    c.setFillColor(colors.HexColor("#E6F1FB"))
    c.rect(left, y - 6, right - left, 30, fill=1, stroke=0)
    c.setFont("Helvetica", 11)
    c.setFillColor(BLU_ASD)
    c.drawString(left + 12, y + 5, "Totale ore sostenute")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right - 12, y + 5,
                      f"{ctx['ore_totali']} ore · {_fmt_importo(ctx['importo_eur'])}")

    _center(c, "Importo effettivamente versato (pricing dinamico). Ogni ora corrisponde a un evento",
            96, "Helvetica", 8.5, GRIGIO_CHIARO)
    _center(c, "nel file iCal incluso nei metadati IPFS del token.",
            84, "Helvetica", 8.5, GRIGIO_CHIARO)


def genera_certificato_pdf(
    *,
    nome: str,
    cognome: str,
    tessera_sostenitore: str | None,
    token_id: int,
    contract_address: str,
    wallet_address: str,
    mint_tx_hash: str | None,
    ipfs_uri: str,
    ore: list[dict],
    importo_eur: float,
    data_emissione: date,
    polygonscan_base: str,
) -> bytes:
    """
    Genera il certificato PDF. `ore` è una lista di dict ordinati
    {"data": date, "fascia": str, "ora": int}. Restituisce i byte del PDF.
    """
    qr_url = f"{polygonscan_base.rstrip('/')}/token/{contract_address}?a={token_id}"
    ctx = {
        "nome": nome,
        "cognome": cognome,
        "tessera_sostenitore": tessera_sostenitore,
        "token_id": token_id,
        "contract_address": contract_address,
        "wallet_address": wallet_address,
        "mint_tx_hash": mint_tx_hash,
        "ipfs_uri": ipfs_uri,
        "ore": ore,
        "ore_totali": len(ore),
        "importo_eur": float(importo_eur),
        "data_emissione": data_emissione.strftime("%d/%m/%Y"),
        "qr": _qr_image(qr_url),
    }

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Certificato di sostegno Palasirio — NFT #{token_id}")
    _pagina_certificato(c, ctx)
    c.showPage()
    _pagina_allegato(c, ctx)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
