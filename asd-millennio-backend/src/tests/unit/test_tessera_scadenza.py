from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from tasks.tessera_scadenza import gia_rinnovata


def _t(sport, scadenza):
    return SimpleNamespace(id=uuid4(), sport=sport, data_scadenza=scadenza)


def test_rinnovata_stessa_categoria_anno_successivo():
    vecchia = _t("volley", date(2027, 6, 30))
    nuova = _t("volley", date(2028, 6, 30))
    assert gia_rinnovata(vecchia, [vecchia, nuova])


def test_non_rinnovata_se_rinnovo_di_altra_categoria():
    vecchia = _t("volley", date(2027, 6, 30))
    altra = _t("badminton", date(2028, 6, 30))
    assert not gia_rinnovata(vecchia, [vecchia, altra])


def test_non_rinnovata_senza_altre_tessere():
    vecchia = _t("pickleball", date(2027, 6, 30))
    assert not gia_rinnovata(vecchia, [vecchia])
