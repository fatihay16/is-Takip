# -*- coding: utf-8 -*-
"""parsel_sorgu_modulu.py için sözleşme testleri: motor, DB şeması, parsel_kontrol UPSERT ve onay geçişleri.
GEÇİCİ veritabanı kullanır; gerçek imar_kayitlari.db / parsel_kayitlari.db'ye DOKUNMAZ.
Çalıştırma:  python -m pytest tests -q    (ya da)   python tests/test_parsel_sozlesme.py
PySide6 kurulu değilse yalnızca motor testleri için sahte (stub) bir PySide6 yerleştirilir; arayüz testleri atlanır.
"""
import os, sys, sqlite3, tempfile, types, importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PySide6  # noqa: F401
    GERCEK_QT = True
except ImportError:
    GERCEK_QT = False

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

psm = importlib.import_module("parsel_sorgu_modulu")


def gecici_ortam():
    d = Path(tempfile.mkdtemp())
    psm.DB_PATH = d / "parsel_kayitlari.db"
    psm._SEMA_HAZIR.clear()
    return d


def row(durum, **kw):
    r = {"il": "Bursa", "ilce": "Mustafakemalpaşa", "mahalle": "Atatürk", "tkgm_mahalle": "ATATÜRK", "ada": "727", "parsel": "2",
         "status": durum, "alan": "100", "nitelik": "Arsa", "islem_turu": "Tevhit", "islem_tarihi": "01.01.2026",
         "yeni_parseller": "727/13", "pasif_mesaj": "", "detail": "", "hareketler": "[]", "devam_parseller": "[]"}
    r.update(kw)
    return r


def test_parsel_db_semasi():
    gecici_ortam()
    con = psm.db()
    tablolar = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"parcels", "ayar", "sayac", "liste_onbellek", "is_parsel_bag", "mahalle_esleme"} <= tablolar
    kolonlar = {r[1] for r in con.execute("PRAGMA table_info(parcels)")}
    assert set(psm.SUTUNLAR) <= kolonlar
    con.close()


def test_parsel_kontrol_kolonlari_ve_onay_gecisi():
    d = gecici_ortam()
    takip = str(d / "imar_kayitlari.db")
    sc = sqlite3.connect(takip)
    sc.execute("CREATE TABLE kayit (id INTEGER PRIMARY KEY, mahalle TEXT)")
    sc.execute("INSERT INTO kayit VALUES (7, 'Atatürk')")
    sc.commit()
    sc.close()

    def oku():
        c = sqlite3.connect(takip)
        r = c.execute("SELECT durum, onay_bekliyor, parsel_no, nihai_aktifler FROM parsel_kontrol WHERE work_id=7").fetchone()
        c.close()
        return r

    psm.takip_sonuc_yaz(takip, 7, row("Aktif"))
    assert oku()[:2] == ("Aktif", 0)
    psm.takip_sonuc_yaz(takip, 7, row("Pasif"))            # ilk kez pasif -> onay=1
    assert oku()[:3] == ("Pasif", 1, "727/2")
    psm.takip_sonuc_yaz(takip, 7, row("Pasif"))            # pasif kalıyor -> mevcut onay korunur
    assert oku()[1] == 1
    c = sqlite3.connect(takip); c.execute("UPDATE parsel_kontrol SET onay_bekliyor=0 WHERE work_id=7"); c.commit(); c.close()
    psm.takip_sonuc_yaz(takip, 7, row("Pasif"))            # İş Takip onayladı (0) -> pasif kalınca 0 kalır
    assert oku()[1] == 0
    psm.takip_sonuc_yaz(takip, 7, row("Belirsiz"))         # aktif/belirsiz -> 0
    assert oku()[:2] == ("Belirsiz", 0)

    c = sqlite3.connect(takip)
    kol = [r[1] for r in c.execute("PRAGMA table_info(parsel_kontrol)")]
    assert kol == ["work_id", "parsel_no", "tkgm_mahalle", "durum", "alan", "nitelik", "islem_turu", "islem_tarihi",
                   "yeni_parseller", "nihai_aktifler", "aciklama", "son_kontrol", "onay_bekliyor", "zincir"]
    assert c.execute("SELECT mahalle FROM kayit WHERE id=7").fetchone()[0] == "Atatürk"   # iş kaydına dokunulmadı
    c.close()


def test_eski_parsel_kontrol_zincir_kolonu_eklenir():
    d = gecici_ortam()
    takip = str(d / "eski.db")
    c = sqlite3.connect(takip)
    c.execute("""CREATE TABLE parsel_kontrol (work_id INTEGER PRIMARY KEY, parsel_no TEXT, tkgm_mahalle TEXT, durum TEXT,
        alan TEXT, nitelik TEXT, islem_turu TEXT, islem_tarihi TEXT, yeni_parseller TEXT, nihai_aktifler TEXT, aciklama TEXT,
        son_kontrol TEXT, onay_bekliyor INTEGER DEFAULT 0)""")
    c.commit(); c.close()
    psm.takip_sonuc_yaz(takip, 1, row("Aktif"))
    c = sqlite3.connect(takip)
    assert "zincir" in [r[1] for r in c.execute("PRAGMA table_info(parsel_kontrol)")]
    c.close()


def test_parsel_cozumleme_ve_aktarim():
    assert psm.parselleri_coz("728/1-2-9-10") == [("728", "1"), ("728", "2"), ("728", "9"), ("728", "10")]
    assert psm.parselleri_coz("3469-3511") == [("0", "3469"), ("0", "3511")]
    mahalleler = [{"text": "ATATÜRK", "id": "123"}]
    s = psm.aktarim_hazirla([{"id": 5, "mahalle": "Atatürk", "ada_parsel": "727/2-3"},
                             {"id": 6, "mahalle": "Yokmahalle", "ada_parsel": "1/1"}], "Bursa", "Mustafakemalpaşa", mahalleler)
    assert len(s["satirlar"]) == 1 and s["satirlar"][0]["work_id"] == 5 and s["satirlar"][0]["parsel"] == "2"
    assert s["eslesmeyen"] == {"Yokmahalle": [6]} and s["coklu"]


def test_sayac_ve_limit():
    gecici_ortam()
    assert psm.sayac_oku() == 0
    psm.sayac_artir(); psm.sayac_artir()
    assert psm.sayac_oku() == 2
    psm.ayar_yaz("gunluk_limit", 2)
    try:
        psm.get_json("http://gecersiz.invalid/")      # sınır dolu: ağ isteği atılmadan LimitHatasi
        assert False
    except psm.LimitHatasi:
        pass


def test_son_aktif_ve_zincir_json():
    r = row("Pasif", hareketler='[{"no":"727/13","durum":"Pasif"},{"no":"727/14","durum":"Aktif"}]',
            devam_parseller='[{"ada":"727","parsel":"13","durum":"Pasif","yeni_parseller":"727/15"},{"ada":"727","parsel":"15","durum":"Aktif"}]')
    assert psm.son_aktif_listesi(r) == ["727/14", "727/15"]
    assert '"kok"' in psm.zincir_json(r)


# ---------------------------------------------------------------- arayüz (yalnız gerçek PySide6 varsa)
def _qt_gerekli():
    if not GERCEK_QT:
        print("ATLANDI: PySide6 kurulu değil (arayüz testi)")
        return False
    return True


def test_arayuz_aciliyor_ve_kaynak_baglanti():
    if not _qt_gerekli():
        return
    gecici_ortam()
    d = Path(psm.DB_PATH).parent
    app = psm.qapp_hazirla()
    geri = []
    w = psm.App(None, kaynak=[(1, "Atatürk", "727/2")], takip_db=str(d / "t.db"), sonuc_geri_cagir=lambda i, o: geri.append(i))
    assert w.model.rowCount() == 0
    w.rows.append(row("Bekliyor")); w.refresh()
    assert w.model.rowCount() == 1
    w.tree.selectRow(0)
    assert w.secili_indeksler() == [0]
    w.close()


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn()
            print("OK  ", ad)
