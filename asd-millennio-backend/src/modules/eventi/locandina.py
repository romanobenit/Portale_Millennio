"""
Preparazione della locandina di un evento.

L'immagine caricata dalla dirigenza viene sempre riaperta e ricompressa in JPEG:
così si accettano solo immagini vere (niente file travestiti), si tolgono i metadati
EXIF (posizione GPS, dispositivo) e si limita la dimensione servita al pubblico.
"""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXEL = 40_000_000      # oltre: rifiutata prima di decodificarla (decompression bomb)
LATO_MAX = 1600
FORMATI = {"JPEG", "PNG", "WEBP"}


def prepara_locandina(contenuto: bytes) -> tuple[bytes, int, int]:
    """Restituisce (jpeg, larghezza, altezza). ValueError con un messaggio per l'utente."""
    if not contenuto:
        raise ValueError("File vuoto")
    if len(contenuto) > MAX_BYTES:
        raise ValueError("File troppo grande (max 8 MB)")
    try:
        with Image.open(BytesIO(contenuto)) as originale:
            if originale.format not in FORMATI:
                raise ValueError("Formato non ammesso: usa un'immagine JPG, PNG o WebP")
            if originale.width * originale.height > MAX_PIXEL:
                raise ValueError("Immagine troppo grande")
            img = ImageOps.exif_transpose(originale)   # foto da telefono: rispetta l'orientamento
            img.thumbnail((LATO_MAX, LATO_MAX))
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                sfondo = Image.new("RGB", img.size, "white")
                sfondo.paste(img, mask=img.getchannel("A"))
                img = sfondo
            elif img.mode != "RGB":
                img = img.convert("RGB")
            out = BytesIO()
            img.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError("Il file non è un'immagine leggibile") from exc
    return out.getvalue(), img.width, img.height
