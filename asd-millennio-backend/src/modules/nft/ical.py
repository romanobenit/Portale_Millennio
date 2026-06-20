import hashlib
import uuid
from datetime import datetime, timedelta

from models.slot_calendario import SlotCalendario


def genera_ical_content(
    slots: list[SlotCalendario],
    token_id: int,
    tessera_id: str,
    contract_address: str,
    ore_per_slot: dict[str, list[int]] | None = None,
) -> str:
    """
    Genera file iCal con un VEVENT per ogni ora acquistata (non per fascia).
    ore_per_slot: {slot_id_str: [8, 9, 10, ...]} — se None usa tutte le ore della fascia.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ASD Millennio//Palasirion//IT",
    ]

    for slot in slots:
        fascia = slot.fascia
        slot_ore = (
            ore_per_slot.get(str(slot.id)) if ore_per_slot else None
        )
        if slot_ore is None:
            h_inizio = slot.ora_inizio.hour
            slot_ore = list(range(h_inizio, h_inizio + slot.ore_totali))

        for ora in sorted(slot_ore):
            uid = f"{uuid.uuid4()}@millennioasd.com"
            dt_inizio = datetime(
                slot.data.year, slot.data.month, slot.data.day, ora, 0, 0
            )
            dt_fine = dt_inizio + timedelta(hours=1)
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{dt_inizio.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{dt_fine.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:Diritto d'uso Palasirion — {fascia} — ASD Millennio",
                f"DESCRIPTION:Token ID: {token_id} | Socio: {tessera_id} | "
                f"Verifica: polygonscan.com/token/{contract_address}/{token_id}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def calcola_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
