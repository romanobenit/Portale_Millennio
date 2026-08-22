"""
Generatore PDF tessera associativa ASD Millennio.

Produce una card in formato standard carta di credito **ISO/IEC 7810 ID-1 (CR80)**
— 85,60 × 53,98 mm, orientamento orizzontale — con:
- Intestazione ASD Millennio (banda blu)
- Dati anagrafici e della tessera
- QR code che punta all'endpoint pubblico di verifica (RFC-M01-002)

Dipendenze: reportlab, qrcode[pil], Pillow
"""
import io
import os
from datetime import date

import qrcode
import qrcode.image.pil
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

SPORT_LABEL: dict[str, str] = {
    "volley": "Pallavolo",
    "badminton": "Badminton",
    "kung_fu": "Kung Fu",
    "pickleball": "Pickleball",
    "sostenitore": "Socio Sostenitore",
}

BLU_ASD = colors.HexColor("#1d4ed8")
ROSSO_ASD = colors.HexColor("#dc070a")
GRIGIO = colors.HexColor("#6b7280")
GRIGIO_TESTO = colors.HexColor("#111827")
GRIGIO_TENUE = colors.HexColor("#9ca3af")

# ISO/IEC 7810 ID-1 (CR80) — dimensioni standard carta di credito
CARD_W = 85.60 * mm
CARD_H = 53.98 * mm

# Logo ASD Millennio (marchio "a picchi") — asset condiviso col certificato NFT
_LOGO_SVG = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "nft", "assets", "logo_millennio.svg")
)
_logo_cache: dict[tuple, object] = {}


def _recolora(node, color) -> None:
    """Forza il colore (fill/stroke) su tutte le forme del Drawing — logo monocromatico."""
    for e in getattr(node, "contents", []):
        if getattr(e, "fillColor", None) is not None:
            e.fillColor = color
        if getattr(e, "strokeColor", None) is not None:
            e.strokeColor = color
        _recolora(e, color)


def _carica_logo(target_w: float, color):
    """
    Carica il logo (SVG) come Drawing reportlab, ricolorato in tinta unita e scalato
    a `target_w` pt. Vettoriale. Ritorna None se svglib/il file non sono disponibili.
    """
    key = (round(target_w, 2), color.hexval() if hasattr(color, "hexval") else str(color))
    if key in _logo_cache:
        return _logo_cache[key]
    try:
        from reportlab.graphics.shapes import Drawing, Group
        from svglib.svglib import svg2rlg

        src = svg2rlg(_LOGO_SVG)
        _recolora(src, color)
        x1, y1, x2, y2 = src.getBounds()
        cw, ch = (x2 - x1) or 1, (y2 - y1) or 1
        scale = target_w / cw
        g = Group(src)
        g.transform = (scale, 0, 0, scale, -x1 * scale, -y1 * scale)
        d = Drawing(cw * scale, ch * scale)
        d.add(g)
        _logo_cache[key] = d
        return d
    except Exception:  # noqa: BLE001 — assenza logo non deve rompere l'emissione tessera
        _logo_cache[key] = None
        return None


def _qr_reader(url: str) -> ImageReader:
    qr = qrcode.QRCode(box_size=6, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def genera_tessera_pdf(
    numero_tessera: str,
    sport: str,
    stato: str,
    data_emissione: date | None,
    data_scadenza: date | None,
    anno_sportivo: str | None,
    nome: str,
    cognome: str,
    verifica_url: str,
) -> bytes:
    """
    Genera il PDF della tessera in formato carta di credito (CR80).
    Restituisce bytes pronti per la risposta HTTP o per il salvataggio su disco.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CARD_W, CARD_H))

    def top(yy_mm: float) -> float:
        """Converte una coordinata 'mm dall'alto' nel sistema reportlab (origine in basso)."""
        return CARD_H - yy_mm * mm

    # ── bordo card arrotondato ──────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.7)
    c.roundRect(0.5 * mm, 0.5 * mm, CARD_W - 1 * mm, CARD_H - 1 * mm, 2.5 * mm, stroke=1, fill=0)

    # ── banda intestazione blu ──────────────────────────────────────────────
    band_h = 11.5 * mm
    c.setFillColor(BLU_ASD)
    c.roundRect(0.5 * mm, CARD_H - 0.5 * mm - band_h, CARD_W - 1 * mm, band_h, 2.5 * mm, stroke=0, fill=1)
    # copre gli angoli arrotondati in basso della banda per uno stacco netto
    c.rect(0.5 * mm, CARD_H - 0.5 * mm - band_h, CARD_W - 1 * mm, band_h / 2, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4 * mm, top(6.4), "ASD MILLENNIO")
    c.setFont("Helvetica", 5.3)
    c.drawString(4 * mm, top(9.7), "TESSERA ASSOCIATIVA SPORTIVA")

    # logo (marchio "a picchi") ROSSO su chip bianco (badge), a destra nella banda blu
    logo = _carica_logo(23 * mm, ROSSO_ASD)
    if logo is not None:
        band_cy = CARD_H - 0.5 * mm - band_h / 2
        pad_x, pad_y = 3 * mm, 2.2 * mm
        chip_w = logo.width + 2 * pad_x
        chip_h = logo.height + 2 * pad_y
        chip_x = CARD_W - 4 * mm - chip_w
        chip_y = band_cy - chip_h / 2
        c.saveState()
        c.setFillColor(colors.white)
        c.roundRect(chip_x, chip_y, chip_w, chip_h, 1.6 * mm, stroke=0, fill=1)
        renderPDF.draw(logo, c, chip_x + pad_x, chip_y + pad_y)
        c.restoreState()

    # ── QR code (in alto a destra, sotto la banda) ──────────────────────────
    qr_size = 17 * mm
    qr_x = CARD_W - 4 * mm - qr_size
    qr_y = top(14.5) - qr_size
    c.drawImage(_qr_reader(verifica_url), qr_x, qr_y, qr_size, qr_size)
    c.setFillColor(GRIGIO)
    c.setFont("Helvetica", 4.6)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 3 * mm, "Verifica validità")

    # ── dati tessera (colonna sinistra) ─────────────────────────────────────
    fields = [
        ("COGNOME E NOME", f"{cognome.upper()} {nome}"),
        ("N° TESSERA", numero_tessera),
        ("SPORT", SPORT_LABEL.get(sport, sport.upper())),
        ("ANNO SPORTIVO", anno_sportivo or "—"),
        ("SCADENZA", str(data_scadenza) if data_scadenza else "—"),
    ]
    yy = 16.8
    for label, valore in fields:
        c.setFillColor(GRIGIO)
        c.setFont("Helvetica", 5)
        c.drawString(4 * mm, top(yy), label)
        c.setFillColor(GRIGIO_TESTO)
        c.setFont("Helvetica-Bold", 7.8)
        c.drawString(4 * mm, top(yy + 3.4), valore or "—")
        yy += 6.6

    # ── footer ──────────────────────────────────────────────────────────────
    c.setFillColor(GRIGIO_TENUE)
    c.setFont("Helvetica", 4.5)
    c.drawString(
        4 * mm, top(52.3),
        "Personale e non trasferibile · Documento emesso da ASD Millennio — millennioasd.com",
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
