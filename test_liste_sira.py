# -*- coding: utf-8 -*-
"""Seçim listelerinde özel sıra: saf mantık + ek.liste sarmalayıcısı (sahte encumen_kayit / PySide6 ile)."""
import json, sys, types, importlib
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

AYAR = {}
def _q(sql, par=()):
    if sql.startswith("INSERT OR REPLACE INTO ayar"):
        AYAR[par[0]] = par[1]
    return []

fake_ek = MagicMock()
fake_ek.liste = lambda tur: {"islem": ["ifraz", "tevhit", "imar uygulaması", "yola terk"]}.get(tur, [])
fake_ek.ayar = lambda k: AYAR.get(k, "")
fake_ek.q = _q
sys.modules["encumen_kayit"] = fake_ek
try:
    import PySide6  # noqa: F401
except ImportError:
    class _Meta(type):
        def __getattr__(cls, ad):
            return _Meta(ad, (object,), {"__init__": lambda s, *a, **k: None})
    class _Modul(types.ModuleType):
        def __getattr__(self, ad):
            if ad.startswith("__"):
                raise AttributeError(ad)
            return _Meta(ad, (object,), {"__init__": lambda s, *a, **k: None})
    for ad in ("PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"):
        sys.modules[ad] = _Modul(ad)

pen = importlib.import_module("encumen_qt_pencereler")


def test_liste_tasi_tek_ve_blok_ve_sinir():
    l = ["a", "b", "c", "d"]
    assert pen.liste_tasi(l, ["c"], -1) == ["a", "c", "b", "d"]
    assert pen.liste_tasi(l, ["b"], 1) == ["a", "c", "b", "d"]
    assert pen.liste_tasi(l, ["b", "c"], -1) == ["b", "c", "a", "d"]      # blok birlikte
    assert pen.liste_tasi(l, ["b", "c"], 1) == ["a", "d", "b", "c"]
    assert pen.liste_tasi(l, ["a"], -1) == l and pen.liste_tasi(l, ["d"], 1) == l   # sınırda durur
    assert pen.liste_tasi(l, ["a", "c"], -1) == ["a", "c", "b", "d"]      # üstteki seçim sınırda, diğeri ilerler
    assert l == ["a", "b", "c", "d"]                                      # girdi değişmez


def test_sira_uygula_yeniler_sonda():
    assert pen.sira_uygula(["a", "b", "c"], []) == ["a", "b", "c"]
    assert pen.sira_uygula(["a", "b", "c", "yeni"], ["c", "a", "b"]) == ["c", "a", "b", "yeni"]
    assert pen.sira_uygula(["a", "c"], ["c", "silinmis", "a"]) == ["c", "a"]


def test_ek_liste_sarmalayicisi_ve_sifirlama():
    assert fake_ek.liste("islem")[0] == "ifraz"                           # sıra yokken özgün sıra
    pen._sira_yaz("islem", ["yola terk", "ifraz", "tevhit", "imar uygulaması"])
    assert json.loads(AYAR["liste_sira_islem"])[0] == "yola terk"
    assert fake_ek.liste("islem") == ["yola terk", "ifraz", "tevhit", "imar uygulaması"]
    pen._sira_yaz("islem", [])                                            # sıfırla
    assert fake_ek.liste("islem") == ["ifraz", "tevhit", "imar uygulaması", "yola terk"]
    AYAR["liste_sira_islem"] = "bozuk{json"                               # bozuk ayar: varsayılan sıra, hata yok
    assert fake_ek.liste("islem")[0] == "ifraz"


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn(); print("OK  ", ad)
