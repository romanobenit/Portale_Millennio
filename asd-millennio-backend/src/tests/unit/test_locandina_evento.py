from io import BytesIO

import pytest
from PIL import Image

from modules.eventi.locandina import LATO_MAX, prepara_locandina


def _immagine(formato: str, size=(718, 1024), mode="RGB", exif: bytes | None = None) -> bytes:
    buf = BytesIO()
    img = Image.new(mode, size, (200, 30, 30, 128) if mode == "RGBA" else (200, 30, 30))
    kwargs = {"exif": exif} if exif else {}
    img.save(buf, formato, **kwargs)
    return buf.getvalue()


def test_jpeg_resta_delle_stesse_dimensioni():
    jpeg, w, h = prepara_locandina(_immagine("JPEG"))
    assert (w, h) == (718, 1024)
    assert Image.open(BytesIO(jpeg)).format == "JPEG"


def test_png_trasparente_diventa_jpeg_su_fondo_bianco():
    jpeg, _, _ = prepara_locandina(_immagine("PNG", mode="RGBA"))
    assert Image.open(BytesIO(jpeg)).mode == "RGB"


def test_immagine_grande_ridotta():
    _, w, h = prepara_locandina(_immagine("PNG", size=(4000, 3000)))
    assert max(w, h) == LATO_MAX


def test_metadati_exif_rimossi():
    exif = Image.Exif()
    exif[0x010F] = "MarcaTelefono"  # Make
    jpeg, _, _ = prepara_locandina(_immagine("JPEG", exif=exif.tobytes()))
    assert not Image.open(BytesIO(jpeg)).getexif()


@pytest.mark.parametrize(
    "contenuto, messaggio",
    [
        (b"", "vuoto"),
        (b"%PDF-1.4 non un'immagine", "leggibile"),
        (_immagine("GIF"), "Formato"),
        (b"x" * (8 * 1024 * 1024 + 1), "troppo grande"),
    ],
)
def test_file_rifiutati(contenuto, messaggio):
    with pytest.raises(ValueError, match=messaggio):
        prepara_locandina(contenuto)
