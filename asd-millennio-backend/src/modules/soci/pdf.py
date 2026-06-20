"""
Generatore PDF tessera associativa ASD Millennio.

Produce un documento A5 con:
- Intestazione ASD Millennio
- Dati anagrafici e della tessera
- QR code che punta all'endpoint pubblico di verifica (RFC-M01-002)

Dipendenze: reportlab, qrcode[pil], Pillow
"""
import io
from datetime import date

import qrcode
import qrcode.image.pil
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SPORT_LABEL: dict[str, str] = {
    "volley": "Pallavolo",
    "badminton": "Badminton",
    "kung_fu": "Kung Fu",
    "pickleball": "Pickleball",
}

BLU_ASD = colors.HexColor("#1d4ed8")
GRIGIO = colors.HexColor("#6b7280")
GRIGIO_CHIARO = colors.HexColor("#f9fafb")


def _qr_image(url: str, size_mm: float) -> Image:
    qr = qrcode.QRCode(box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_mm * mm, height=size_mm * mm)


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
    Genera il PDF della tessera. Restituisce bytes pronti per la risposta HTTP
    o per il salvataggio su disco.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "AsdTitle",
        parent=styles["Normal"],
        fontSize=17,
        fontName="Helvetica-Bold",
        textColor=BLU_ASD,
        spaceAfter=1 * mm,
    )
    subtitle_style = ParagraphStyle(
        "AsdSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=GRIGIO,
        spaceAfter=4 * mm,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=GRIGIO,
        leading=10,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        leading=13,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#9ca3af"),
        leading=9,
    )

    def riga(label: str, valore: str) -> list:
        return [Paragraph(label, label_style), Paragraph(valore or "—", value_style)]

    story = []

    story.append(Paragraph("ASD MILLENNIO", title_style))
    story.append(Paragraph("TESSERA ASSOCIATIVA SPORTIVA", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLU_ASD, spaceAfter=4 * mm))

    dati = Table(
        [
            riga("COGNOME E NOME", f"{cognome.upper()}  {nome}"),
            riga("NUMERO TESSERA", numero_tessera),
            riga("SPORT", SPORT_LABEL.get(sport, sport.upper())),
            riga("ANNO SPORTIVO", anno_sportivo or "—"),
            riga("DATA EMISSIONE", str(data_emissione) if data_emissione else "—"),
            riga("SCADENZA", str(data_scadenza) if data_scadenza else "—"),
        ],
        colWidths=[28 * mm, 62 * mm],
    )
    dati.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRIGIO_CHIARO, colors.white]),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )

    qr_img = _qr_image(verifica_url, 34)

    layout = Table(
        [[dati, qr_img]],
        colWidths=[92 * mm, 36 * mm],
    )
    layout.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(layout)
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=3 * mm))
    story.append(
        Paragraph(
            "Scansiona il QR code per verificare la validità della tessera. "
            "Tessera personale e non trasferibile. "
            "Documento emesso da ASD Millennio — millennioasd.com",
            footer_style,
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf.read()
