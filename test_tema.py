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


# ---------------------------------------------------------------- ek temalar (Okyanus, Zümrüt, Kum, Bordo, Grafit)
def _lum(hexkod):
    r, g, b = (v / 255 for v in et._rgb(hexkod))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _kontrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_tema_kayit_defteri():
    assert list(et.TEMALAR)[:2] == ["acik", "koyu"] and len(et.TEMALAR) == 7
    assert {"okyanus", "zumrut", "kum", "bordo", "grafit"} <= set(et.TEMALAR)
    for k, (ad, koyu, jeton) in et.TEMALAR.items():
        assert ad and isinstance(koyu, bool)
        assert set(jeton) == set(et.ACIK), k              # her temada aynı anahtarlar (eksik jeton QSS'i bozar)
        assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in jeton.values()), k
    assert et.tema_koyu_mu("grafit") and et.tema_koyu_mu("koyu") and not et.tema_koyu_mu("bordo")
    assert et.tema_adi("okyanus") == "Okyanus" and et.tema_adi("yok") == "Açık"
    assert et.sonraki_tema("grafit") == "acik" and et.sonraki_tema("acik") == "koyu" and et.sonraki_tema("yok") == "acik"


def test_jeton_secimi_geriye_uyumlu():
    assert et.jetonlar(False) is et.ACIK and et.jetonlar(True) is et.KOYU          # eski çağrı biçimi aynen çalışır
    assert et.jetonlar(False, "bordo") is et.BORDO and et.jetonlar(True, "yok") is et.KOYU
    assert et.birlestir({"ESKI": "#111111"}, False, "kum")["BG"] == et.KUM["BG"]
    assert et.birlestir({"ESKI": "#111111"}, False)["BG"] == et.ACIK["BG"]
    ek = types.SimpleNamespace(METIN="x", KART="x")
    et.ek_renk_uygula(ek, False, "okyanus")
    assert ek.METIN == et.OKYANUS["METIN"] and ek.KART == et.OKYANUS["KART"]


def test_tum_temalarda_okunaklilik_kontrasti():
    for k, (ad, koyu, t) in et.TEMALAR.items():
        assert _kontrast(t["METIN"], t["KART"]) >= 7, (k, "metin/kart")
        assert _kontrast(t["METIN"], t["BG"]) >= 7, (k, "metin/zemin")
        assert _kontrast(t["SOLUK"], t["KART"]) >= 3.5, (k, "soluk/kart")
        if k not in ("acik", "koyu"):   # mevcut Açık/Koyu temalara dokunulmadı (Koyu'da beyaz yazı/vurgu = 3,8); eşik yeni temalar içindir
            assert _kontrast("#FFFFFF", t["VURGU"]) >= 4.2, (k, "beyaz yazı/vurgu düğmesi")
        assert _kontrast(t["LACIVERT_YAZI"], t["LACIVERT"]) >= 7, (k, "bant yazısı")
        assert _kontrast(t["KIRMIZI"], t["KART"]) >= 3.5, (k, "kırmızı yazı/kart")


def test_tum_temalarda_qss_uretilir():
    for k, (ad, koyu, t) in et.TEMALAR.items():
        q = et.qss_yap(t)
        assert q.count("{") == q.count("}") and "{t[" not in q and t["VURGU"] in q, k
        assert et.tamamlayici_popup_qss(t).count("{") == et.tamamlayici_popup_qss(t).count("}")


def test_durum_hapi_tum_durum_renklerinde_okunur():
    # durum renkleri açık/koyu tabana göre ek içinden gelir; hap yazısı zeminle aynı renk ailesinde ve okunaklı olmalı
    for koyu, zeminler in ((False, ["#d4f0d4", "#fff2b8", "#d3e5ff", "#ffdcb8", "#e8d6f5", "#bfe9e4", "#e5e7eb", "#fecaca"]),
                           (True, ["#173C30", "#4A3817", "#1F3A63", "#4A2323", "#26364E"])):
        for z in zeminler:
            zemin, yazi = et.hap_renkleri(z, koyu)
            assert zemin == z and _kontrast(yazi, zemin) >= 3.5, (koyu, z, yazi)


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn(); print("OK  ", ad)
