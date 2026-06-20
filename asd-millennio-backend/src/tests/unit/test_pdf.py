"""Unit tests for PDF tessera generation (Sprint 2)."""
from datetime import date

import pytest


def test_genera_tessera_pdf_returns_bytes():
    from modules.soci.pdf import genera_tessera_pdf

    pdf_bytes = genera_tessera_pdf(
        numero_tessera="VOL-2026-00001",
        sport="volley",
        stato="attiva",
        data_emissione=date(2026, 9, 1),
        data_scadenza=date(2027, 6, 30),
        anno_sportivo="2026-2027",
        nome="Mario",
        cognome="Rossi",
        verifica_url="https://millennioasd.com/api/v1/tessere/abc/verifica",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_genera_tessera_pdf_header_pdf():
    """Il file deve iniziare con il magic byte %PDF."""
    from modules.soci.pdf import genera_tessera_pdf

    pdf_bytes = genera_tessera_pdf(
        numero_tessera="BDM-2026-00007",
        sport="badminton",
        stato="attiva",
        data_emissione=date(2026, 10, 1),
        data_scadenza=date(2027, 6, 30),
        anno_sportivo="2026-2027",
        nome="Anna",
        cognome="Verdi",
        verifica_url="https://millennioasd.com/api/v1/tessere/xyz/verifica",
    )

    assert pdf_bytes[:4] == b"%PDF"


def test_genera_tessera_pdf_sport_diversi():
    """PDF deve essere generato correttamente per tutti e 4 gli sport."""
    from modules.soci.pdf import genera_tessera_pdf

    for sport in ["volley", "badminton", "kung_fu", "pickleball"]:
        pdf_bytes = genera_tessera_pdf(
            numero_tessera=f"{sport[:3].upper()}-2026-00001",
            sport=sport,
            stato="attiva",
            data_emissione=date(2026, 9, 1),
            data_scadenza=date(2027, 6, 30),
            anno_sportivo="2026-2027",
            nome="Test",
            cognome="User",
            verifica_url="https://millennioasd.com/api/v1/tessere/test/verifica",
        )
        assert pdf_bytes[:4] == b"%PDF", f"PDF non valido per sport={sport}"
