# -*- coding: utf-8 -*-
"""Aşama 1: encumen_tema jeton/QSS testleri (PySide6 gerekmez)."""
import re, sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import encumen_tema as et

ESKI_ANAHTARLAR = {"BG", "METIN", "KART", "BASLIK", "SOLUK", "KIRMIZI", "VURGU", "VURGU_K", "KENAR", "SEC", "BHOV"}


def test_iki_tema_ayni_anahtarlar_ve_gecerli_renk():
    assert set(et.ACIK) == set(et.KOYU)
    assert ESKI_ANAHTARLAR <= set(et.ACIK)
    for t in (et.ACIK, et.KOYU):
        for k, v in t.items():
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", v), (k, v)
    for koyu in (False, True):
        assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in et.SERI[koyu])


def test_qss_uretimi_ve_eski_secicilerin_korunmasi():
    for koyu in (False, True):
        q = et.qss_yap(et.jetonlar(koyu))
        for secici in ("QFrame#bant", "QLabel#kartSayi", "QPushButton#vurgu", "QPushButton#tehlike", "QTableView",
                       "QHeaderView::section", "QTextEdit#detay", "QFrame#kart", "QLabel#bildirim", "QLabel#temaDugme"):
            assert secici in q, secici
        assert "{" not in q.replace("{", "", 0) or q.count("{") == q.count("}")


def test_birlestir_ek_anahtarlarini_korur():
    t = et.birlestir({"BG": "#000000", "ESKI_OZEL": "#123456"}, False)
    assert t["BG"] == et.ACIK["BG"] and t["ESKI_OZEL"] == "#123456"


def test_ek_renk_uygula_yalniz_var_olanlara_dokunur():
    ek = types.SimpleNamespace(METIN="x", KART="x", DURUM_UI={"a": 1}, FIELDS=["z"])
    et.ek_renk_uygula(ek, True)
    assert ek.METIN == et.KOYU["METIN"] and ek.KART == et.KOYU["KART"]
    assert not hasattr(ek, "VURGU")            # olmayan ad eklenmez
    assert ek.DURUM_UI == {"a": 1} and ek.FIELDS == ["z"]   # diğer her şey aynı


def test_qss_parantez_dengesi_ve_yeni_kurallar():
    for koyu in (False, True):
        q = et.qss_yap(et.jetonlar(koyu))
        assert q.count("{") == q.count("}")
        assert "'" not in q.split("QToolTip")[0]
        for secici in ("QPushButton", "QLineEdit", "QMenu", "QTabBar::tab:selected", "QScrollBar:vertical", "QGroupBox",
                       'QLabel#kartSayi[vurgu="mor"]', "QLabel#hap"):
            assert secici in q, secici
        assert "{t[" not in q   # biçimlendirilmemiş jeton kalmadı


def test_hap_renkleri_ve_turkce_buyuk_harf():
    z, y = et.hap_renkleri("#DDF3E7", False)
    assert z == "#DDF3E7" and y != z and int(y[1:3], 16) < int("DD", 16)     # açık temada yazı daha koyu
    z, y = et.hap_renkleri("#173C30", True)
    assert int(y[3:5], 16) > int("3C", 16)                                   # koyu temada yazı daha açık
    assert et.tr_buyuk("Parsel durumu") == "PARSEL DURUMU" and et.tr_buyuk("işlem") == "İŞLEM" and et.tr_buyuk("ıslak") == "ISLAK"


def test_yazi_sistemi_qss_ve_font_aileleri():
    assert et.FONT_AILELER[0] == "Segoe UI Variable" and "Segoe UI" in et.FONT_AILELER and et.MONO_AILELER[0] == "Consolas"
    q = et.qss_yap(et.ACIK)
    assert "font-size:22pt" in q and "font-size:16pt" in q and "font-size:9.5pt" in q
    baslik = q.split("QHeaderView::section {")[1].split("}")[0]
    assert "font-weight" not in baslik and "font-size" not in baslik     # başlık fontunu kod yönetir (ölçeklenir)


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn(); print("OK  ", ad)
