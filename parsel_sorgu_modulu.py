# -*- coding: utf-8 -*-
"""İş Takip içine entegre edilmiş, orijinal Toplu Parsel Sorgulama v2 | TKGM

Her parsel için:
  * parsel AKTİF ise  -> alan ve nitelik gösterilir,
  * parsel PASİF ise  -> "pasife alınmıştır" ibaresi, işlem türü/tarihi ve oluşan YENİ parsellerin
                         tamamı (Parsel Sorgu'daki hareket listesi gibi) gösterilir.
Günlük istek sayacı vardır; üst sınıra gelince toplu sorgu durur. İl/ilçe/mahalle kimlikleri bir kez
çözülüp saklanır (eskiden her parsel için 3 ek istek atılıyordu).
"""
import os, sys, re, json, time, sqlite3, threading, unicodedata
from pathlib import Path
from datetime import datetime, date, timedelta
import math
from PySide6.QtCore import (Qt, QThread, Signal, QAbstractTableModel, QModelIndex, QStringListModel, QRectF, QPointF, QTimer)
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QFont, QPolygonF, QGuiApplication, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QPushButton, QCheckBox, QComboBox, QLineEdit, QGroupBox, QTableView, QTableWidget,
                               QTableWidgetItem, QHeaderView, QProgressBar, QSpinBox, QTabWidget, QPlainTextEdit,
                               QScrollArea, QMessageBox, QFileDialog, QAbstractItemView, QCompleter, QSizePolicy, QFrame)
try:
    import encumen_tema as _et  # ortak kurumsal görünüm (yoksa eski görünüm kullanılır)
except Exception:
    _et = None

import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

# exe olarak çalışırken veritabanı geçici klasöre değil, exe'nin yanına yazılsın
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "Sonuclar"
DB_PATH = APP_DIR / "parsel_kayitlari.db"
API = "https://cbsapi.tkgm.gov.tr/megsiswebapi.v3.1/api"
WEB = "https://parselsorgu.tkgm.gov.tr/"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Origin": "https://parselsorgu.tkgm.gov.tr",
    "Referer": WEB,
}
TIMEOUT = 25
VARSAYILAN_LIMIT = 90       # günlük istek üst sınırı (TKGM sınırı 100 olduğu için pay bırakıldı)
VARSAYILAN_YENILE_GUN = 3   # Aktif görünen parseller kaç günde bir yeniden kontrol edilsin
BEKLEME_SN = 1.2            # istekler arası bekleme
VARSAYILAN_IL = "Bursa"      # İş Takip aktarımında il/ilçe seçilmemişse kullanılır
VARSAYILAN_ILCE = "Mustafakemalpaşa"

YENI_SUTUNLAR = {"pasif_mesaj": "TEXT", "islem_turu": "TEXT", "islem_tarihi": "TEXT", "yeni_parseller": "TEXT",
                 "hareketler": "TEXT", "ham_parsel": "TEXT", "ham_hareket": "TEXT", "devam_parseller": "TEXT", "tkgm_mahalle": "TEXT"}
SUTUNLAR = ["il", "ilce", "mahalle", "ada", "parsel", "mahalle_id", "alan", "nitelik", "koordinatlar", "map_file",
            "status", "detail", "updated"] + list(YENI_SUTUNLAR)


class LimitHatasi(RuntimeError):
    pass


class ErisimHatasi(RuntimeError):
    pass


# ------------------------------------------------------------------ veritabanı
_SEMA_HAZIR = set()


def db():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.execute("PRAGMA synchronous=NORMAL")
    if str(DB_PATH) in _SEMA_HAZIR:
        return con
    con.execute("""CREATE TABLE IF NOT EXISTS parcels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        il TEXT, ilce TEXT, mahalle TEXT, ada TEXT, parsel TEXT,
        mahalle_id TEXT, alan TEXT, nitelik TEXT, koordinatlar TEXT,
        map_file TEXT, status TEXT, detail TEXT, updated TEXT,
        UNIQUE(il,ilce,mahalle,ada,parsel)
    )""")
    var = {r[1] for r in con.execute("PRAGMA table_info(parcels)")}
    for k, t in YENI_SUTUNLAR.items():  # eski veritabanını bozmadan yeni sütunları ekle
        if k not in var:
            con.execute(f"ALTER TABLE parcels ADD COLUMN {k} {t}")
    con.execute("CREATE TABLE IF NOT EXISTS ayar (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS sayac (gun TEXT PRIMARY KEY, adet INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS liste_onbellek (url TEXT PRIMARY KEY, veri TEXT)")
    # İş Takip bağlantısı: hangi iş kaydı hangi parselle ilişkili (bir parsel birden çok işe bağlı olabilir)
    con.execute("""CREATE TABLE IF NOT EXISTS is_parsel_bag (
        work_id INTEGER, il TEXT, ilce TEXT, mahalle TEXT, ada TEXT, parsel TEXT, kaynak_metin TEXT, aktarim TEXT,
        PRIMARY KEY (work_id, il, ilce, mahalle, ada, parsel))""")
    # İş Takip'teki mahalle adı -> TKGM resmi mahalle (bir kez seçilir, hatırlanır; İş Takip'teki ad değişmez)
    con.execute("""CREATE TABLE IF NOT EXISTS mahalle_esleme (
        il TEXT, ilce TEXT, kaynak_norm TEXT, tkgm_mahalle TEXT, mahalle_id TEXT,
        PRIMARY KEY (il, ilce, kaynak_norm))""")
    con.commit()
    _SEMA_HAZIR.add(str(DB_PATH))
    return con


def ayar_oku(k, varsayilan=""):
    con = db()
    r = con.execute("SELECT v FROM ayar WHERE k=?", (k,)).fetchone()
    con.close()
    return r[0] if r and r[0] is not None else varsayilan


def ayar_yaz(k, v):
    con = db()
    con.execute("INSERT OR REPLACE INTO ayar VALUES (?,?)", (k, str(v)))
    con.commit()
    con.close()


def limit_degeri():
    try:
        return max(int(ayar_oku("gunluk_limit", VARSAYILAN_LIMIT)), 1)
    except ValueError:
        return VARSAYILAN_LIMIT


def sayac_oku():
    con = db()
    r = con.execute("SELECT adet FROM sayac WHERE gun=?", (date.today().isoformat(),)).fetchone()
    con.close()
    return r[0] if r else 0


def sayac_artir():
    con = db()
    con.execute("INSERT INTO sayac VALUES (?,1) ON CONFLICT(gun) DO UPDATE SET adet=adet+1", (date.today().isoformat(),))
    con.commit()
    con.close()


# ------------------------------------------------------------------ servis istekleri
def get_json(url, say=True):
    """say=True: istek günlük sayaca işlenir ve üst sınırda LimitHatasi atılır."""
    if say:
        if sayac_oku() >= limit_degeri():
            raise LimitHatasi(f"Günlük üst sınıra ({limit_degeri()} istek) ulaşıldı. Yarın devam edin ya da sınırı artırın.")
        sayac_artir()
    r = requests.get(url, headers=HEADERS, timeout=(6, TIMEOUT))  # bağlanamazsa 6 sn'de vazgeç
    if r.status_code == 403:
        raise ErisimHatasi("TKGM erişimi 403 ile reddetti (erişim/limit kısıtı). Bir süre sonra yeniden deneyin.")
    if r.status_code == 429:
        raise ErisimHatasi("TKGM geçici istek sınırına ulaşıldı (429). Daha sonra tekrar deneyin.")
    r.raise_for_status()
    return r.json()


def get_json_onbellekli(url):
    """İl/ilçe/mahalle listeleri nadiren değişir: bir kez çekilip saklanır, sayaca işlenmez."""
    con = db()
    r = con.execute("SELECT veri FROM liste_onbellek WHERE url=?", (url,)).fetchone()
    con.close()
    if r:
        return json.loads(r[0])
    veri = get_json(url, say=False)
    con = db()
    con.execute("INSERT OR REPLACE INTO liste_onbellek VALUES (?,?)", (url, json.dumps(veri, ensure_ascii=False)))
    con.commit()
    con.close()
    return veri


def feature_items(data):
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        return [f.get("properties", {}) for f in data.get("features", [])]
    if isinstance(data, list):
        return data
    return []


def norm_ad(x):
    return " ".join(str(x or "").strip().casefold().replace("i̇", "i").split())


def find_id(items, name_keys, wanted):
    w = norm_ad(wanted)
    for item in items:
        name = next((item.get(k) for k in name_keys if item.get(k) not in (None, "")), "")
        if norm_ad(name) == w:
            return item.get("id") or item.get("mahalleKodu") or item.get("ilceKodu")
    matches = []
    for item in items:
        name = next((item.get(k) for k in name_keys if item.get(k) not in (None, "")), "")
        if w and (w in norm_ad(name) or norm_ad(name) in w):
            matches.append(item.get("id") or item.get("mahalleKodu") or item.get("ilceKodu"))
    if len(matches) == 1:
        return matches[0]
    raise RuntimeError(f"'{wanted}' idari birimi TKGM listesinde tekil olarak bulunamadı.")


def mahalle_id_bul(row):
    if row.get("mahalle_id"):
        return row["mahalle_id"]
    con = db()  # aynı il/ilçe/mahalle için daha önce çözülmüş kimlik varsa tekrar istek atma
    kayitlar = con.execute("SELECT il,ilce,mahalle,mahalle_id FROM parcels WHERE mahalle_id IS NOT NULL AND mahalle_id!=''").fetchall()
    con.close()
    hedef = (norm_ad(row["il"]), norm_ad(row["ilce"]), norm_ad(row["mahalle"]))
    for il, ilce, mah, mid in kayitlar:
        if (norm_ad(il), norm_ad(ilce), norm_ad(mah)) == hedef:
            return mid
    provinces = feature_items(get_json_onbellekli(f"{API}/idariYapi/ilListe"))
    il_id = find_id(provinces, ["text", "ad", "name", "ilAdi"], row["il"])
    districts = feature_items(get_json_onbellekli(f"{API}/idariYapi/ilceListe/{il_id}"))
    ilce_id = find_id(districts, ["text", "ilceAdi", "ad", "name"], row["ilce"])
    neighborhoods = feature_items(get_json_onbellekli(f"{API}/idariYapi/mahalleListe/{ilce_id}"))
    return find_id(neighborhoods, ["text", "mahalleAdi", "ad", "name"], row["mahalle"])


# ------------------------------------------------------------------ aktif / pasif / hareket çözümleme
_KATLA = str.maketrans("İıĞğÜüŞşÖöÇç", "IiGgUuSsOoCc")  # 1'e 1 harf eşleme: indeksler korunur


def katla(s):
    return str(s if s is not None else "").translate(_KATLA).lower()


NO_RE = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")
ISLEM_RE = re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+tarihli\s+(.+?)\s+islemi")
# TKGM'nin "02/10/2026 Tarihli İfrazen Taksim (Tsm)" biçimindeki metinlerinde 'işlemi' kelimesi yoktur.
ISLEM_RE_GENIS = re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+tarihli\s+(.+?)\s*(?:\([^)]*\))?\s*$")


def metinleri_topla(obj, cikti=None):
    cikti = [] if cikti is None else cikti
    if isinstance(obj, dict):
        for v in obj.values():
            metinleri_topla(v, cikti)
    elif isinstance(obj, list):
        for v in obj:
            metinleri_topla(v, cikti)
    elif isinstance(obj, str):
        cikti.append(obj)
    return cikti


def pasif_ibaresi(obj):
    """Yanıtın herhangi bir yerinde 'pasife alınmıştır' içeren metni bulur."""
    for s in metinleri_topla(obj):
        if "pasife alinmistir" in katla(s):
            return s.strip()
    return ""


def islem_ayikla(metin):
    """'20/10/2026 Tarihli Tevhit İşlemi (Tsm)' -> ('20.10.2026', 'Tevhit')"""
    k = katla(metin)
    m = ISLEM_RE.search(k)
    if not m:
        return "", ""
    tarih = re.sub(r"[/-]", ".", metin[m.start(1):m.end(1)])
    tur = metin[m.start(2):m.end(2)].strip()
    return tarih, tur[:1].upper() + tur[1:]


def islem_ayikla_genis(metin):
    """'20/10/2026 Tarihli İfrazen Taksim (Tsm)' -> ('20.10.2026', 'İfrazen Taksim')
    (metinde 'işlemi' kelimesi bulunmayan TKGM işlem tanımları için genişletilmiş çözümleme)."""
    tarih, tur = islem_ayikla(metin)
    if tarih:
        return tarih, tur
    m = ISLEM_RE_GENIS.search(katla(metin))
    if not m:
        return "", ""
    tarih = re.sub(r"[/-]", ".", metin[m.start(1):m.end(1)])
    tur = metin[m.start(2):m.end(2)].strip()
    return tarih, tur[:1].upper() + tur[1:]


def _durum_degeri(v):
    k = katla(v).strip()
    return "Aktif" if k == "aktif" else "Pasif" if k == "pasif" else None


def hareket_satirlari(obj):
    """Hareket listesindeki satırları (açıklama, durum, taşınmaz no) şekil gözetmeden bulur:
    'Aktif/Pasif' değeri ile '727/13' gibi bir numarası olan her kayıt bir satırdır (iç içe olsa da)."""
    satirlar, goruldu = [], set()

    def gez(x):
        if isinstance(x, dict):
            durum = no = None
            ack = ""
            ada = parsel = None
            for k, v in x.items():
                kk = katla(k)
                if isinstance(v, bool):
                    if "pasif" in kk and v:
                        durum = durum or "Pasif"
                    elif "aktif" in kk:
                        durum = durum or ("Aktif" if v else "Pasif")
                elif isinstance(v, str):
                    d = _durum_degeri(v)
                    if d and durum is None:
                        durum = d
                    elif NO_RE.match(v) and no is None:
                        no = re.sub(r"\s+", "", v)
                    elif "tarihli" in katla(v) and not ack:
                        ack = v.strip()
                    elif v.strip() in ("-", "–") and not ack:
                        ack = "-"
                if kk in ("ada", "adano") and isinstance(v, (int, str)) and str(v).strip().isdigit():
                    ada = str(v).strip()
                if kk in ("parsel", "parselno") and isinstance(v, (int, str)) and str(v).strip().isdigit():
                    parsel = str(v).strip()
            if no is None and ada and parsel:
                no = f"{ada}/{parsel}"
            if durum and no:
                anahtar = (no, durum, ack)
                if anahtar not in goruldu:
                    goruldu.add(anahtar)
                    satirlar.append({"aciklama": ack, "durum": durum, "no": no})
            for v in x.values():
                gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)

    gez(obj)
    return satirlar


def props_durum(props):
    """TKGM parsel cevabındaki durum alanını ve alternatif durum alanlarını çözer."""
    if not isinstance(props, dict):
        return None
    # TKGM Parsel Sorgu cevabında durum=0 pasif, durum=1 aktif.
    raw = props.get("durum")
    if raw is not None:
        deger = str(raw).strip()
        if deger == "0":
            return "Pasif"
        if deger == "1":
            return "Aktif"
        d = _durum_degeri(deger)
        if d:
            return d
    for k, v in props.items():
        kk = katla(k)
        if isinstance(v, bool):
            if "pasif" in kk and v:
                return "Pasif"
            if "aktif" in kk and not v:
                return "Pasif"
        elif isinstance(v, str) and ("durum" in kk or "aktif" in kk or "pasif" in kk or "statu" in kk):
            d = _durum_degeri(v)
            if d:
                return d
    return None


def _geojson_coz(raw):
    """TKGM iç içe GeoJSON alanını dict biçimine çevirir."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return {}
    return raw if isinstance(raw, dict) else {}


def tkgm_gittigi_kayitlar(props, ziyaret=None, derinlik=0):
    """İlk TKGM yanıtındaki tüm alt parselleri, ek API isteği yapmadan düz listeye açar."""
    ziyaret = ziyaret if ziyaret is not None else set()
    bulunan = []
    if derinlik >= 20 or not isinstance(props, dict):
        return bulunan
    raw = _geojson_coz(props.get("gittigiParselListe"))
    for feature in raw.get("features") or []:
        if not isinstance(feature, dict):
            continue
        p = feature.get("properties") or {}
        ada = str(p.get("adaNo") or "").strip()
        parsel = str(p.get("parselNo") or "").strip()
        if not ada or not parsel:
            continue
        no = f"{ada}/{parsel}"
        if no in ziyaret:
            continue
        ziyaret.add(no)
        durum = props_durum(p) or "Belirsiz"
        sebep = str(p.get("gittigiParselSebep") or props.get("gittigiParselSebep") or "").strip()
        alt_sonuc = analiz_et(ada, parsel, p, None) if durum == "Pasif" else None
        bulunan.append({
            "ada": ada, "parsel": parsel, "durum": durum,
            "alan": area_text(p.get("alan")) or "TKGM verisinde bulunamadı",
            "nitelik": str(p.get("nitelik") or "TKGM verisinde bulunamadı"),
            "koordinatlar": geometri_ozeti(feature.get("geometry") or ""),
            "geometry": feature.get("geometry") or {},
            "islem_turu": (alt_sonuc or {}).get("islem_turu") or islem_ayikla_genis(sebep)[1],
            "islem_tarihi": (alt_sonuc or {}).get("islem_tarihi") or islem_ayikla_genis(sebep)[0],
            "pasif_mesaj": sebep,
            "yeni_parseller": "; ".join(tkgm_gittigi_parseller(p)),
            "hareketler": json.dumps(
                [{"aciklama": sebep, "durum": durum, "no": no}] if sebep else [],
                ensure_ascii=False
            ),
            "ham_hareket": ""
        })
        bulunan.extend(tkgm_gittigi_kayitlar(p, ziyaret, derinlik + 1))
    return bulunan


def tkgm_gittigi_parseller(props):
    """İlk seviyedeki hedef parsel numaralarını döndürür."""
    raw = _geojson_coz((props or {}).get("gittigiParselListe"))
    sonuc = []
    for feature in raw.get("features") or []:
        p = (feature or {}).get("properties") or {}
        ada = str(p.get("adaNo") or "").strip()
        parsel = str(p.get("parselNo") or "").strip()
        if ada and parsel:
            no = f"{ada}/{parsel}"
            if no not in sonuc:
                sonuc.append(no)
    return sonuc


def zemin_id_bul(props):
    for k, v in (props or {}).items():
        kk = katla(k)
        if "zemin" in kk and "id" in kk and isinstance(v, (int, str)) and str(v).strip():
            return str(v).strip()
    return ""


def analiz_et(ada, parsel, props, hareket):
    """Parsel yanıtı (+ varsa hareket yanıtı) -> durum, ibare, işlem, yeni parseller, hareket satırları."""
    kendi = f"{str(ada).strip()}/{str(parsel).strip()}"
    kaynaklar = [props] + ([hareket] if hareket is not None else [])
    satirlar, ibare = [], ""
    # TKGM hareket bilgisi aynı parsel cevabının properties alanında geliyor.
    tkgm_durum = props_durum(props)
    sebep = str((props or {}).get("gittigiParselSebep") or "").strip()
    hedefler = _geojson_coz((props or {}).get("gittigiParselListe")).get("features") or []
    if tkgm_durum == "Pasif":
        ibare = sebep or "Bu taşınmaz pasif durumdadır."
        satirlar.append({"aciklama": ibare, "durum": "Pasif", "no": kendi})
        for feature in hedefler:
            p = (feature or {}).get("properties") or {}
            ada_alt = str(p.get("adaNo") or "").strip()
            parsel_alt = str(p.get("parselNo") or "").strip()
            if ada_alt and parsel_alt:
                no = f"{ada_alt}/{parsel_alt}"
                durum_alt = props_durum(p) or "Belirsiz"
                satir = {"aciklama": sebep, "durum": durum_alt, "no": no}
                if satir not in satirlar:
                    satirlar.append(satir)
    for v in kaynaklar:
        for s in hareket_satirlari(v):
            if s not in satirlar:
                satirlar.append(s)
        ibare = ibare or pasif_ibaresi(v)
    kendi_satir = next((s for s in satirlar if s["no"] == kendi), None)
    # Hareket tablosundaki parselin kendi satırı, genel durum alanından önceliklidir.
    durum = kendi_satir["durum"] if kendi_satir else tkgm_durum
    if durum is None and ibare:
        durum = "Pasif"
    tarih = tur = ""
    for metin in [ibare] + [s["aciklama"] for s in ([kendi_satir] if kendi_satir else []) + satirlar]:
        if metin and not tarih:
            tarih, tur = islem_ayikla_genis(metin)  # 'İfrazen Taksim (Tsm)' gibi 'işlemi' içermeyen tanımlar da çözülür
    if durum == "Pasif" and not ibare and tarih:
        ibare = f"Bu taşınmaz {tarih} Tarihli {tur} İşlemi ile pasife alınmıştır."
    yeni = []
    for s in satirlar:
        if s["durum"] == "Aktif" and s["no"] != kendi and s["no"] not in yeni:
            yeni.append(s["no"])
    return {"durum": durum, "ibare": ibare, "islem_tarihi": tarih, "islem_turu": tur, "yeni": yeni, "satirlar": satirlar}


def hareket_gecerli(h):
    if h is None:
        return False
    if isinstance(h, dict) and (h.get("Message") or h.get("message") or h.get("error")):
        return False
    return isinstance(h, (dict, list))


def hareket_adresi(sablon, row, props, mahalle_id):
    zemin = zemin_id_bul(props)
    if "{zemin_id}" in sablon and not zemin:
        raise RuntimeError("Hareket adresi {zemin_id} istiyor ama parsel yanıtında zemin kimliği bulunamadı.")
    degerler = {"mahalle_id": mahalle_id, "ada": row["ada"], "parsel": row["parsel"], "zemin_id": zemin,
                "il_id": (props or {}).get("ilId", ""), "ilce_id": (props or {}).get("ilceId", "")}
    for k, v in degerler.items():
        sablon = sablon.replace("{" + k + "}", str(v))
    return sablon


def geometri_ozeti(geom):
    coords = []
    raw = (geom or {}).get("coordinates") or []
    if (geom or {}).get("type") == "Polygon" and raw:
        coords = raw[0]
    elif (geom or {}).get("type") == "MultiPolygon" and raw and raw[0]:
        coords = raw[0][0]
    try:
        return "; ".join(f"{p[1]:.7f}, {p[0]:.7f}" for p in coords)
    except (TypeError, IndexError, ValueError):
        return ""


def area_text(v):
    return "" if v is None else str(v).strip()


def devam_parsellerini_zincirle(props):
    """Alt parsel zincirini ana TKGM yanıtının içindeki iç içe veriden çıkarır (ek istek yapmaz)."""
    return tkgm_gittigi_kayitlar(props), []


def query_one(row):
    """Bir parseli sorgular ve pasif hareket zincirini sonuna kadar takip eder."""
    mahalle_id = mahalle_id_bul(row)
    data = get_json(f"{API}/parsel/{mahalle_id}/{row['ada']}/{row['parsel']}")
    if isinstance(data, dict) and data.get("Message"):
        raise RuntimeError(str(data["Message"]))
    if not isinstance(data, dict) or data.get("type") != "Feature":
        raise RuntimeError("TKGM beklenmeyen yanıt döndürdü; parsel bulunamadı veya servis erişimi kısıtlı.")
    props = data.get("properties") or {}
    geom = data.get("geometry") or {}
    sonuc = analiz_et(row["ada"], row["parsel"], props, None)
    hareket, ham_h, hareket_hata = None, "", ""
    sablon = ayar_oku("hareket_url")
    if sablon:
        try:
            hareket = get_json(hareket_adresi(sablon, row, props, mahalle_id))
            ham_h = json.dumps(hareket, ensure_ascii=False)
            if not hareket_gecerli(hareket):
                hareket_hata = "Hareket servisi geçerli bir liste döndürmedi."
                hareket = None
            else:
                sonuc = analiz_et(row["ada"], row["parsel"], props, hareket)
        except (LimitHatasi, ErisimHatasi):
            raise
        except Exception as e:
            hareket_hata = f"Hareket servisi: {e}"
    ayrinti = []
    if sonuc["durum"] is None:
        sonuc["durum"] = "Belirsiz"
        ayrinti.append(hareket_hata or ("Aktif/pasif bilgisi servis yanıtında bulunamadı. "
                                         "'Hareket servisini ayarla' bölümünü kullanın."))
    elif hareket_hata:
        ayrinti.append(hareket_hata)
    ozet = {k: props.get(k) for k in ("ozet", "mevkii", "pafta", "zeminId", "zeminKmdurum") if props.get(k) not in (None, "")}
    ham = json.dumps({"properties": props, "geometri": (geom or {}).get("type") or None}, ensure_ascii=False)
    devam, devam_hatalari = [], []
    if sonuc["durum"] == "Pasif" and tkgm_gittigi_parseller(props):
        devam, devam_hatalari = devam_parsellerini_zincirle(props)
    if sonuc["durum"] == "Pasif" and not tkgm_gittigi_parseller(props) and not sonuc["yeni"]:
        ayrinti.append("Yeni parsel listesi alınamadı (TKGM yanıtında alt parsel listesi yok).")
    if devam_hatalari:
        ayrinti.append("Devam parselleri: " + "; ".join(devam_hatalari))
    row.update({
        "mahalle_id": str(mahalle_id), "alan": area_text(props.get("alan")) or "TKGM verisinde bulunamadı", "nitelik": str(props.get("nitelik") or "TKGM verisinde bulunamadı"),
        "koordinatlar": geometri_ozeti(geom), "geometry": geom, "status": sonuc["durum"],
        "pasif_mesaj": sonuc["ibare"], "islem_turu": sonuc["islem_turu"], "islem_tarihi": sonuc["islem_tarihi"],
        "yeni_parseller": "; ".join(dict.fromkeys(
            tkgm_gittigi_parseller(props) + sonuc["yeni"]
        )), "hareketler": json.dumps(sonuc["satirlar"], ensure_ascii=False),
        "ham_parsel": ham[:60000], "ham_hareket": ham_h[:60000],
        "devam_parseller": json.dumps([{k: v for k, v in d.items() if k != "geometry"} for d in devam], ensure_ascii=False),
        "detail": " ".join(ayrinti + ([" • ".join(f"{k}: {v}" for k, v in ozet.items())] if ozet else [])),
    })
    return row


def hareket_sablonu_yap(url, row):
    """F12'den kopyalanan adresteki mahalle kimliği/ada/parsel değerlerini {mahalle_id},{ada},{parsel} ile değiştirir."""
    from urllib.parse import urlsplit, urlunsplit
    p = urlsplit(url.strip())
    esle = {str(row.get("mahalle_id") or ""): "{mahalle_id}", str(row.get("ada") or ""): "{ada}", str(row.get("parsel") or ""): "{parsel}"}
    esle.pop("", None)
    parcalar = [esle.get(s, s) for s in p.path.split("/")]
    sorgu = "&".join(f"{kv.split('=')[0]}={esle.get(kv.split('=')[1], kv.split('=')[1])}" if "=" in kv else kv
                     for kv in p.query.split("&")) if p.query else ""
    return urlunsplit((p.scheme, p.netloc, "/".join(parcalar), sorgu, "")).replace("%7B", "{").replace("%7D", "}")


def son_kontrol(r):
    try:
        return datetime.fromisoformat(r.get("updated") or "")
    except ValueError:
        return datetime.min


# ------------------------------------------------------------------ arayüz
# ------------------------------------------------------------------ İş Takip bağlantısı
def norm_mahalle(value):
    """Büyük/küçük harf, Türkçe harf (ı/İ/ş/ç/ğ/ö/ü), noktalama ve boşluk farklarını yok sayar; yalnızca TAM eşleşme için."""
    value = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).replace("ı", "i")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


_AYRAC = r"(?:\s*(?:[-,;+&]|\bve\b)\s*)"
_ADA_PARSEL_RE = re.compile(r"(?<!\d)(\d+)\s*/\s*(\d+(?:" + _AYRAC + r"\d+(?!\d|\s*/))*)", re.I)


def parselleri_coz(metin):
    """İş Takip'teki ada/parsel yazımından TÜM parselleri çıkarır (tire/virgül ayraçtır, aralık değildir):
    '728/1-2-9-10' -> 728 ada 1,2,9,10 | '727/2-3' -> 727 ada 2,3 | '3469-3511' -> ada yok (0): 3469, 3511."""
    metin = str(metin or "")
    out = []

    def ekle(ada, parsel):
        if (ada, parsel) not in out:
            out.append((ada, parsel))

    bulundu = False
    for m in _ADA_PARSEL_RE.finditer(metin):
        bulundu = True
        for pr in re.findall(r"\d+", m.group(2)):
            ekle(m.group(1), pr)
    if not bulundu:
        for pr in re.findall(r"\d+", metin):
            ekle("0", pr)
    return out


def ada_parsel_ayikla(deger):
    """Sorgulanacak İLK parsel ('hepsi': yazılı tüm parseller). Diğerleri sorgulanmaz; sonuçtan çıkarım yapılır."""
    liste = parselleri_coz(deger)
    if not liste:
        return None
    return {"ada": liste[0][0], "parsel": liste[0][1], "coklu": len(liste) > 1, "hepsi": liste}


def kaynak_normalle(kaynak):
    """İş Takip'ten gelen açık işleri {id, mahalle, ada_parsel} sözlüklerine çevirir (sözlük, tuple veya sqlite satırı olabilir)."""
    out = []
    for k in kaynak or []:
        try:
            d = dict(k) if isinstance(k, dict) else {"id": k[0], "mahalle": k[1], "ada_parsel": k[2]}
        except (IndexError, TypeError, KeyError):
            continue
        if d.get("id") is None:
            continue
        d["id"] = int(d["id"]) if str(d["id"]).strip().isdigit() else d["id"]
        out.append(d)
    return out


def mahalle_adi_ve_id(item):
    ad = next((str(item.get(k)).strip() for k in ("text", "mahalleAdi", "ad", "name") if item.get(k) not in (None, "")), "")
    kod = item.get("id") or item.get("mahalleKodu") or item.get("ilceKodu")
    return ad, (str(kod) if kod else "")


def mahalle_esle(kaynak_mahalle, mahalleler, hafiza=None):
    """('tamam', resmi_ad, mahalle_id) | ('belirsiz'|'yok', None, None). Parça eşleşmesi YOK: yanlış mahalleye sorgu atılmaz."""
    anahtar = norm_mahalle(kaynak_mahalle)
    if hafiza and anahtar in hafiza:
        ad, mid = hafiza[anahtar]
        return "tamam", ad, str(mid)
    bulunan = []
    for item in mahalleler:
        ad, kod = mahalle_adi_ve_id(item)
        if ad and kod and norm_mahalle(ad) == anahtar:
            bulunan.append((ad, kod))
    if len({k for _, k in bulunan}) == 1:
        return "tamam", bulunan[0][0], bulunan[0][1]
    return ("belirsiz" if bulunan else "yok"), None, None


def mahalle_listesi_getir(il, ilce):
    iller = feature_items(get_json_onbellekli(f"{API}/idariYapi/ilListe"))
    il_id = find_id(iller, ["text", "ad", "name", "ilAdi"], il)
    ilceler = feature_items(get_json_onbellekli(f"{API}/idariYapi/ilceListe/{il_id}"))
    ilce_id = find_id(ilceler, ["text", "ilceAdi", "ad", "name"], ilce)
    return feature_items(get_json_onbellekli(f"{API}/idariYapi/mahalleListe/{ilce_id}"))


def esleme_hafizasi(il, ilce):
    con = db()
    r = con.execute("SELECT kaynak_norm, tkgm_mahalle, mahalle_id FROM mahalle_esleme WHERE il=? AND ilce=?",
                    (norm_mahalle(il), norm_mahalle(ilce))).fetchall()
    con.close()
    return {k: (ad, mid) for k, ad, mid in r}


def esleme_kaydet(il, ilce, kaynak_mahalle, tkgm_mahalle, mahalle_id):
    con = db()
    con.execute("INSERT OR REPLACE INTO mahalle_esleme VALUES (?,?,?,?,?)",
                (norm_mahalle(il), norm_mahalle(ilce), norm_mahalle(kaynak_mahalle), tkgm_mahalle, str(mahalle_id)))
    con.commit()
    con.close()


def aktarim_hazirla(kaynak, il, ilce, mahalleler, hafiza=None):
    """Açık işleri parsel satırlarına çevirir (saf işlev). İş Takip'teki mahalle adı DEĞİŞTİRİLMEZ."""
    satirlar, eslesmeyen, hatali, coklu = [], {}, [], []
    for k in kaynak:
        wid = k["id"]
        mahalle = str(k.get("mahalle") or "").strip()
        ap = ada_parsel_ayikla(k.get("ada_parsel"))
        if not mahalle or not ap:
            hatali.append(f"#{wid}: mahalle veya ada/parsel okunamadı")
            continue
        durum, tkgm_ad, mid = mahalle_esle(mahalle, mahalleler, hafiza)
        if durum != "tamam":
            eslesmeyen.setdefault(mahalle, []).append(wid)
            continue
        if ap["coklu"]:
            coklu.append(f"#{wid} ({k.get('ada_parsel')})")
        satirlar.append({"work_id": wid, "il": il, "ilce": ilce, "mahalle": mahalle, "tkgm_mahalle": tkgm_ad,
                         "mahalle_id": mid, "ada": ap["ada"], "parsel": ap["parsel"],
                         "kaynak_metin": str(k.get("ada_parsel") or "")})
    return {"satirlar": satirlar, "eslesmeyen": eslesmeyen, "hatali": hatali, "coklu": coklu}


def satir_anahtari(r):
    return tuple(str(r.get(k, "")).strip() for k in ("il", "ilce", "mahalle", "ada", "parsel"))


def norm_anahtar(r):
    """Büyük/küçük harf ve Türkçe harf farkı olsa da aynı parseli aynı sayar (eski kayıtlar 'BURSA'/'atatürk' olabilir)."""
    return (norm_mahalle(r.get("il")), norm_mahalle(r.get("ilce")), norm_mahalle(r.get("mahalle")),
            str(r.get("ada", "")).strip(), str(r.get("parsel", "")).strip())


def baglanti_kaydet(work_id, anahtar, kaynak_metin):
    """İş kaydını parselle ilişkilendirir; aynı işin eski (artık geçersiz) parsel bağlantısını kaldırır."""
    con = db()
    con.execute("DELETE FROM is_parsel_bag WHERE work_id=? AND NOT (il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?)",
                (work_id, *anahtar))
    con.execute("INSERT OR REPLACE INTO is_parsel_bag VALUES (?,?,?,?,?,?,?,?)",
                (work_id, *anahtar, kaynak_metin, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()


def baglantilari_oku():
    con = db()
    veri = con.execute("SELECT work_id, il, ilce, mahalle, ada, parsel FROM is_parsel_bag ORDER BY work_id").fetchall()
    con.close()
    out = {}
    for wid, *anahtar in veri:
        out.setdefault(tuple(anahtar), []).append(wid)
    return out


def son_aktif_listesi(row):
    """Zincir sonunda AKTİF görünen parseller (ara aşamada aktif olup sonra pasife düşenler çıkarılır)."""
    durumlar = {}
    try:
        for s in json.loads(row.get("hareketler") or "[]"):
            if s.get("no"):
                durumlar[str(s["no"]).strip()] = s.get("durum")
        for a in json.loads(row.get("devam_parseller") or "[]"):
            durumlar[f"{a.get('ada')}/{a.get('parsel')}"] = a.get("durum")
    except (TypeError, ValueError):
        pass
    kendi = f"{row.get('ada')}/{row.get('parsel')}"
    return sorted(no for no, d in durumlar.items() if d == "Aktif" and no != kendi)


def zincir_json(row):
    """Parsel hareket zinciri (kök parsel + alt parseller): İş Takip tarafında ağ isteği olmadan gösterilebilsin diye saklanır."""
    try:
        devam = json.loads(row.get("devam_parseller") or "[]")
    except (TypeError, ValueError):
        devam = []

    def yenilist(metin):
        return [x.strip() for x in str(metin or "").split(";") if x.strip()]

    kok = {"no": f"{row.get('ada')}/{row.get('parsel')}", "durum": row.get("status") or "", "alan": row.get("alan") or "",
           "nitelik": row.get("nitelik") or "", "islem_turu": row.get("islem_turu") or "",
           "islem_tarihi": row.get("islem_tarihi") or "", "aciklama": row.get("pasif_mesaj") or "",
           "yeni": yenilist(row.get("yeni_parseller"))}
    alt = [{"no": f"{d.get('ada')}/{d.get('parsel')}", "durum": d.get("durum") or "", "alan": d.get("alan") or "",
            "nitelik": d.get("nitelik") or "", "islem_turu": d.get("islem_turu") or "",
            "islem_tarihi": d.get("islem_tarihi") or "", "aciklama": d.get("pasif_mesaj") or "",
            "yeni": yenilist(d.get("yeni_parseller"))} for d in devam if isinstance(d, dict)]
    return json.dumps({"kok": kok, "devam": alt}, ensure_ascii=False)


def sonuc_ozeti(row):
    return {"parsel_no": f"{row.get('ada')}/{row.get('parsel')}", "tkgm_mahalle": row.get("tkgm_mahalle") or "",
            "durum": row.get("status") or "", "alan": row.get("alan") or "", "nitelik": row.get("nitelik") or "",
            "islem_turu": row.get("islem_turu") or "", "islem_tarihi": row.get("islem_tarihi") or "",
            "yeni_parseller": row.get("yeni_parseller") or "", "nihai_aktifler": "; ".join(son_aktif_listesi(row)),
            "aciklama": row.get("pasif_mesaj") or row.get("detail") or "", "zincir": zincir_json(row),
            "son_kontrol": row.get("updated") or datetime.now().isoformat(timespec="seconds")}


TAKIP_SONUC_DDL = """CREATE TABLE IF NOT EXISTS parsel_kontrol (
    work_id INTEGER PRIMARY KEY, parsel_no TEXT, tkgm_mahalle TEXT, durum TEXT, alan TEXT, nitelik TEXT,
    islem_turu TEXT, islem_tarihi TEXT, yeni_parseller TEXT, nihai_aktifler TEXT, aciklama TEXT,
    son_kontrol TEXT, onay_bekliyor INTEGER DEFAULT 0, zincir TEXT)"""


def takip_sonuc_yaz(takip_db_yolu, work_id, row):
    """Sorgu sonucunu İş Takip veritabanındaki 'parsel_kontrol' tablosuna işler (iş kaydına dokunmaz).
    onay_bekliyor=1: parsel PASİF'e yeni döndü, kullanıcı kontrol edip işi kapatmalı (İş Takip onaylayınca 0 yapar)."""
    o = sonuc_ozeti(row)
    con = sqlite3.connect(takip_db_yolu, timeout=15)
    try:
        con.execute(TAKIP_SONUC_DDL)
        if "zincir" not in [r[1] for r in con.execute("PRAGMA table_info(parsel_kontrol)")]:
            con.execute("ALTER TABLE parsel_kontrol ADD COLUMN zincir TEXT")  # eski veritabanı
        onceki = con.execute("SELECT durum, onay_bekliyor FROM parsel_kontrol WHERE work_id=?", (work_id,)).fetchone()
        if o["durum"] != "Pasif":
            onay = 0
        elif onceki and onceki[0] == "Pasif":
            onay = onceki[1] or 0
        else:
            onay = 1
        con.execute("""INSERT INTO parsel_kontrol (work_id, parsel_no, tkgm_mahalle, durum, alan, nitelik, islem_turu,
            islem_tarihi, yeni_parseller, nihai_aktifler, aciklama, son_kontrol, onay_bekliyor, zincir)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(work_id) DO UPDATE SET parsel_no=excluded.parsel_no, tkgm_mahalle=excluded.tkgm_mahalle,
            durum=excluded.durum, alan=excluded.alan, nitelik=excluded.nitelik, islem_turu=excluded.islem_turu,
            islem_tarihi=excluded.islem_tarihi, yeni_parseller=excluded.yeni_parseller,
            nihai_aktifler=excluded.nihai_aktifler, aciklama=excluded.aciklama, son_kontrol=excluded.son_kontrol,
            onay_bekliyor=excluded.onay_bekliyor, zincir=excluded.zincir""",
                    (work_id, o["parsel_no"], o["tkgm_mahalle"], o["durum"], o["alan"], o["nitelik"], o["islem_turu"],
                     o["islem_tarihi"], o["yeni_parseller"], o["nihai_aktifler"], o["aciklama"], o["son_kontrol"], onay, o["zincir"]))
        con.commit()
    finally:
        con.close()


RENKLER = {"Aktif": "#e3f4e8", "Pasif": "#fde9c9", "Belirsiz": "#fff6cc", "Hata": "#fde2e2"}
# (zemin, yazı) çiftleri: yazı rengi AÇIKÇA verilir, böylece hangi temada olursa olsun okunur
PALET_ACIK = {
    "satir": {"Aktif": "#FFF0A6", "Pasif": "#FFD0A3"},
    "mesaj": {"Aktif": ("#dff0d8", "#1f4d2b"), "Pasif": ("#fcf8e3", "#6b5a2a"), "Belirsiz": ("#fff6cc", "#4a4010"),
              "Hata": ("#f2dede", "#5a1f1f"), "Bekliyor": ("#eeeeee", "#333333")},
    "baslik": "#18334d", "alt": "#586575", "ust_bant": "#1E3A8A",
    "cv_bg": "#ffffff", "cv_yazi": "#111111", "cv_cizgi": "#777777",
    "cv_pasif": ("#d3d3d3", "#000000"), "cv_aktif": ("#7a9a3a", "#ffffff"), "cv_tahmin": ("#ececec", "#555555"),
    "pasif_satir_fg": "#999999",
}
PALET_KOYU = {
    "satir": {"Aktif": "#FFF0A6", "Pasif": "#FFD0A3"},
    "mesaj": {"Aktif": ("#1f3d2b", "#d7f0df"), "Pasif": ("#4a3a1c", "#fbe9c6"), "Belirsiz": ("#41401f", "#f3efc4"),
              "Hata": ("#4d2323", "#f9dcdc"), "Bekliyor": ("#2b3342", "#e5e7eb")},
    "baslik": "#e5e7eb", "alt": "#9ca3af", "ust_bant": "#172B63",
    "cv_bg": "#1f2430", "cv_yazi": "#e5e7eb", "cv_cizgi": "#9ca3af",
    "cv_pasif": ("#4b5563", "#f3f4f6"), "cv_aktif": ("#4d7c0f", "#ffffff"), "cv_tahmin": ("#2f3542", "#9ca3af"),
    "pasif_satir_fg": "#9ca3af",
}



# ------------------------------------------------------------------ PySide6 arayüzü
# Yukarıdaki motor/veritabanı/İş Takip işlevleri DEĞİŞTİRİLMEDİ; aşağısı yalnızca arayüz katmanıdır.
_ARKA_PLAN = set()         # çalışan QThread nesneleri (kapanışta yok edilmesinler)
_ACIK_PENCERELER = set()   # dışarıdan (ör. Tk tabanlı İş Takip) açılıp referansı bırakılan pencereler


def qapp_hazirla():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        if _et:
            app.setFont(_et.font_yap(10))
    return app


def _tk_koprusu(master):
    """Geçiş dönemi: pencere hâlâ Tkinter tabanlı İş Takip'ten açılırsa Qt olaylarını Tk döngüsünden işler."""
    if getattr(master, "_qt_pompa", False):
        return
    master._qt_pompa = True
    qapp = QApplication.instance()

    def pompa():
        try:
            qapp.processEvents()
            master.after(15, pompa)
        except Exception:
            pass
    master.after(15, pompa)


def koyu_mu(widget=None):
    """Uygulama paleti koyu mu? (koyu modda pencere koyu paletle açılır.)"""
    try:
        pal = widget.palette() if widget is not None else QGuiApplication.palette()
        return pal.color(QPalette.ColorRole.Window).lightness() < 115
    except Exception:
        return False


def _kutu(parent, ikon, baslik, metin, sorulu=False):
    kutu = QMessageBox(ikon, baslik, metin, QMessageBox.StandardButton.NoButton, parent)
    if sorulu:
        evet = kutu.addButton("Evet", QMessageBox.ButtonRole.YesRole)
        kutu.addButton("Hayır", QMessageBox.ButtonRole.NoRole)
        kutu.exec()
        return kutu.clickedButton() is evet
    kutu.addButton("Tamam", QMessageBox.ButtonRole.AcceptRole)
    kutu.exec()
    return True


def bilgi(parent, baslik, metin):
    _kutu(parent, QMessageBox.Icon.Information, baslik, metin)


def uyari(parent, baslik, metin):
    _kutu(parent, QMessageBox.Icon.Warning, baslik, metin)


def hata_kutusu(parent, baslik, metin):
    _kutu(parent, QMessageBox.Icon.Critical, baslik, metin)


def sor(parent, baslik, metin):
    return _kutu(parent, QMessageBox.Icon.Question, baslik, metin, sorulu=True)


def takip_temasi_koyu(takip_db):
    """İş Takip'te seçili temayı salt okunur okur: True=koyu, False=açık, None=bilinmiyor."""
    if not takip_db:
        return None
    try:
        con = sqlite3.connect(f"file:{Path(takip_db).as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            for r in con.execute("SELECT * FROM ayar"):
                if r and r[0] == "tema":
                    return str(r[1]) == "koyu"
        finally:
            con.close()
    except Exception:
        pass
    return None


class _Is(QThread):
    """Verilen işlevi arka planda çalıştırır; widget'lara yalnız sinyallerle dokunulur."""

    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        _ARKA_PLAN.add(self)
        self.finished.connect(lambda: _ARKA_PLAN.discard(self))

    def run(self):
        self.fn()


class Metin(QLineEdit):
    def get(self):
        return self.text()

    def set(self, v):
        self.setText(str(v))


class AramaliKutu(QComboBox):
    """Yazdıkça Türkçe harf duyarsız öneri listesi gösteren il/ilçe/mahalle kutusu."""
    secildi = Signal()

    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._tam = []
        self._model = QStringListModel(self)
        self._comp = QCompleter(self._model, self)
        self._comp.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.setCompleter(self._comp)
        self.lineEdit().textEdited.connect(self._yazildi)
        self.activated.connect(lambda _i: self.secildi.emit())
        self._comp.activated[str].connect(self._oneriden)

    def get(self):
        return self.currentText()

    def set(self, v):
        self.setEditText(str(v))

    def listeyi_ata(self, liste):
        """Seçenekleri değiştirir; yazılı metni ve ayar kaydını etkilemez."""
        metin = self.currentText()
        le = self.lineEdit()
        self.blockSignals(True)
        le.blockSignals(True)
        self.clear()
        self.addItems(list(liste))
        self.setEditText(metin)
        le.blockSignals(False)
        self.blockSignals(False)
        self._tam = list(liste)

    def _yazildi(self, yazilan):
        aranan = norm_ad(yazilan)
        eslesen = [ad for ad in self._tam if aranan in norm_ad(ad)] if aranan else []
        self._model.setStringList(eslesen[:8])
        if yazilan and eslesen:
            self._comp.complete()
        else:
            self._comp.popup().hide()

    def _oneriden(self, metin):
        self.setEditText(metin)
        self.secildi.emit()


class ParselModel(QAbstractTableModel):
    BASLIK = ["İl", "İlçe", "Mahalle", "Ada", "Parsel", "İş kayıt no", "Parsel durumu", "Alan (m²)", "Nitelik",
              "Yeni parseller", "Pasif işlemi", "Son kontrol"]
    GENISLIK = [80, 120, 110, 60, 60, 90, 100, 90, 120, 190, 170, 120]

    def __init__(self, pal):
        super().__init__()
        self.pal = pal
        self.satirlar = []   # (rows içindeki indeks, durum, [hücre değerleri])

    def yukle(self, satirlar):
        self.beginResetModel()
        self.satirlar = satirlar
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.satirlar)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.BASLIK)

    def headerData(self, bolum, yon, rol=Qt.ItemDataRole.DisplayRole):
        if rol == Qt.ItemDataRole.DisplayRole and yon == Qt.Orientation.Horizontal:
            return _et.tr_buyuk(self.BASLIK[bolum]) if _et else self.BASLIK[bolum]
        return None

    def data(self, index, rol=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        i, durum, deger = self.satirlar[index.row()]
        if rol == Qt.ItemDataRole.DisplayRole:
            return str(deger[index.column()])
        if rol == Qt.ItemDataRole.UserRole:
            return i
        if rol == Qt.ItemDataRole.FontRole and _et and index.column() in (3, 4, 7, 11):   # ada, parsel, alan, son kontrol
            return _et.font_yap(10, mono=True)
        # Aktif/pasif satır renkleri temadan bağımsızdır; yalnızca arka plan boyanır.
        renk = self.pal["satir"].get(durum)
        if renk and rol == Qt.ItemDataRole.BackgroundRole:
            return QBrush(QColor(renk))
        return None


class DurumEtiketi(QLabel):
    def __init__(self, metin=""):
        super().__init__(metin)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set(self, metin):
        self.setText(str(metin))
        self.setToolTip(str(metin))


def _tablo_yap(basliklar, genislikler, satirlar, soluk=None):
    """Salt okunur küçük tablo. satirlar: [(değerler, soluk_mu)]."""
    t = QTableWidget(len(satirlar), len(basliklar))
    t.setHorizontalHeaderLabels(basliklar)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    if _et:
        t.horizontalHeader().setFont(_et.font_yap(8.5, kalin=True))
    for j, w in enumerate(genislikler):
        t.setColumnWidth(j, w)
    for i, (degerler, soluk_mu) in enumerate(satirlar):
        for j, d in enumerate(degerler):
            oge = QTableWidgetItem("" if d is None else str(d))
            if soluk_mu and soluk:
                oge.setForeground(QBrush(QColor(soluk)))
            t.setItem(i, j, oge)
    return t


class GrafikAlani(QWidget):
    def __init__(self, detay):
        super().__init__()
        self.d = detay
        self.setMinimumSize(700, 480)

    def paintEvent(self, _olay):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(self.d.pal["cv_bg"]))
        self.d.grafik_ciz(p, max(self.width(), 700))
        p.end()


class Detay(QDialog):
    """Parsel Sorgu'daki 'hareket listesi' penceresi gibi: Özet / Tablo / Grafik / Ham veri."""

    def __init__(self, master, row, ilgili=None):
        super().__init__(master if isinstance(master, QWidget) else None)
        self.row = row
        self.pal = getattr(master, "pal", PALET_ACIK)
        self.ilgili = list(ilgili or [])  # aynı iş kaydında yazılı diğer parseller (sorgulanmamış)
        self.tahmin = self.birlesen_tahmin()
        self.setWindowTitle(f"{row['ada']} ada {row['parsel']} parsel hareket listesi")
        self.resize(900, 560)
        ana = QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)
        baslik = QLabel(f"{row['ada']} ada {row['parsel']} parsel hareket listesi")
        baslik.setStyleSheet(f"background:{self.pal['ust_bant']};color:white;font:15pt 'Segoe UI';padding:12px 16px;")
        ana.addWidget(baslik)
        self.nb = QTabWidget()
        ana.addWidget(self.nb, 1)
        self.ozet_tab, self.tablo_tab, self.grafik_tab, self.ham_tab, self.devam_tab = (QWidget() for _ in range(5))
        for f, ad in ((self.ozet_tab, "Özet"), (self.tablo_tab, "Hareket Tablosu"), (self.grafik_tab, "Grafik"),
                      (self.devam_tab, "Hareket Zinciri"), (self.ham_tab, "Ham veri")):
            self.nb.addTab(f, ad)
        self.satirlar = []
        self.devamlar = []
        try:
            self.satirlar = json.loads(row.get("hareketler") or "[]")
        except (TypeError, ValueError):
            pass
        try:
            self.devamlar = json.loads(row.get("devam_parseller") or "[]")
        except (TypeError, ValueError):
            pass
        self._ozet()
        self._tablo()
        self._grafik()
        self._devam()
        self._ham()

    def birlesen_tahmin(self):
        """Pasif parsel TEVHİT ile yeni parsele dönüştüyse, iş kaydında yazılı diğer parseller de aynı tevhide katılmış sayılır
        (örn. iş '727/2-3', sorgulanan 727/2 -> 727/13: 727/3 de 727/13'e birleşmiştir). Sorgulanmayan parseller '*' ile işaretlenir."""
        r = self.row
        yeni = [x.strip() for x in (r.get("yeni_parseller") or "").split(";") if x.strip()]
        kok = f"{r.get('ada')}/{r.get('parsel')}"
        if r.get("status") == "Pasif" and yeni and "tevhit" in katla(r.get("islem_turu")):
            return [n for n in self.ilgili if n != kok]
        return []

    def _ozet(self):
        r = self.row
        durum = r.get("status") or "Bekliyor"
        renk, yazi = self.pal["mesaj"].get(durum, self.pal["mesaj"]["Bekliyor"])
        if durum == "Pasif":
            metin = r.get("pasif_mesaj") or "Bu taşınmaz pasife alınmıştır."
        elif durum == "Aktif":
            metin = "Bu parsel AKTİF görünüyor."
        elif durum == "Belirsiz":
            metin = "Aktif/pasif durumu belirlenemedi.\n" + (r.get("detail") or "")
        else:
            metin = r.get("detail") or durum
        ly = QVBoxLayout(self.ozet_tab)
        ly.setContentsMargins(18, 18, 18, 12)
        mesaj = QLabel(metin)
        mesaj.setWordWrap(True)
        mesaj.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mesaj.setStyleSheet(f"background:{renk};color:{yazi};border:1px solid #888;padding:18px 16px;")
        ly.addWidget(mesaj)
        satirlar = [("Parsel", f"{r['mahalle']} / {r['ada']} ada {r['parsel']} parsel"),
                    ("Alan (m²)", r.get("alan") or "-"), ("Nitelik", r.get("nitelik") or "-")]
        if durum == "Pasif":
            satirlar.insert(1, ("İşlem", f"{r.get('islem_turu') or '-'}  ({r.get('islem_tarihi') or '-'})"))
            if self.tahmin:
                yeni_s = ", ".join(x.strip() for x in (r.get("yeni_parseller") or "").split(";") if x.strip())
                satirlar.insert(2, ("Birleşen parseller (iş kaydına göre)", f"{r['ada']}/{r['parsel']}, " + ", ".join(self.tahmin) + f"  →  {yeni_s}"))
            son_aktif = self.son_aktif_parseller()
            satirlar.append((f"Zincir sonundaki aktif parseller ({len(son_aktif)} adet)",
                             ",  ".join(son_aktif) if son_aktif else "Belirlenemedi"))
        izgara = QGridLayout()
        izgara.setContentsMargins(6, 8, 6, 0)
        for i, (k, v) in enumerate(satirlar):
            ak = QLabel(k + ":")
            ak.setStyleSheet("font-weight:bold;")
            av = QLabel(v)
            av.setWordWrap(True)
            av.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            izgara.addWidget(ak, i, 0, Qt.AlignmentFlag.AlignTop)
            izgara.addWidget(av, i, 1)
        izgara.setColumnStretch(1, 1)
        izgara.setColumnMinimumWidth(0, 260)
        ly.addLayout(izgara)
        if durum == "Pasif":
            n = QLabel("Not: Pasif parselin alan/niteliği son kayıtlı bilgidir.")
            n.setStyleSheet(f"color:{(getattr(master, 'tk', None) or {}).get('SOLUK', '#777')};")
            ly.addWidget(n)
        ly.addStretch(1)

    def tum_hareket_satirlari(self):
        """Kök ve ara parsellerin hareketlerini birleştirir; aynı parselde en güncel durumu tutar."""
        son = {}
        for satir in self.satirlar:
            no = str(satir.get("no") or "").strip()
            if no:
                son[no] = dict(satir)
        for parca in self.devamlar:
            try:
                alt_satirlar = json.loads(parca.get("hareketler") or "[]")
            except (TypeError, ValueError):
                alt_satirlar = []
            for satir in alt_satirlar:
                no = str(satir.get("no") or "").strip()
                if no:
                    son[no] = dict(satir)
            no = f"{parca.get('ada')}/{parca.get('parsel')}"
            if no not in son or parca.get("durum") in ("Aktif", "Pasif"):
                son[no] = {"no": no, "durum": parca.get("durum") or "Belirsiz",
                           "aciklama": parca.get("pasif_mesaj") or ""}
        return list(son.values())

    def son_aktif_parseller(self):
        """Ara aşamada aktif görünüp sonraki işlemde pasife düşenleri son listeden çıkarır."""
        durumlar = {}
        for satir in self.satirlar:
            no = str(satir.get("no") or "").strip()
            if no:
                durumlar[no] = satir.get("durum")
        for parca in self.devamlar:
            no = f"{parca.get('ada')}/{parca.get('parsel')}"
            durumlar[no] = parca.get("durum")
        return sorted(no for no, durum in durumlar.items() if durum == "Aktif"
                      and no != f"{self.row.get('ada')}/{self.row.get('parsel')}")

    def _tablo(self):
        hareketler = self.tum_hareket_satirlari()
        satirlar = [((s.get("aciklama") or "-", s.get("durum"), s.get("no")), s.get("durum") == "Pasif") for s in hareketler]
        satirlar += [(("İş kaydında yazılı; sorgulanmadı — tevhitle birleşmiş sayıldı", "Pasif*", no), True) for no in self.tahmin]
        ly = QVBoxLayout(self.tablo_tab)
        ly.addWidget(_tablo_yap(["Açıklama / İşlem", "Son Durum", "Taşınmaz No"], [380, 90, 120], satirlar, self.pal["pasif_satir_fg"]))
        if not hareketler:
            ly.addWidget(QLabel("Hareket kaydı alınamadı."), 0, Qt.AlignmentFlag.AlignHCenter)

    def _grafik(self):
        ly = QVBoxLayout(self.grafik_tab)
        ly.setContentsMargins(0, 0, 0, 0)
        kaydirma = QScrollArea()
        kaydirma.setWidgetResizable(True)
        kaydirma.setWidget(GrafikAlani(self))
        ly.addWidget(kaydirma)

    def grafik_ciz(self, p, w):
        kok = f"{self.row.get('ada')}/{self.row.get('parsel')}"
        cizgi = QColor(self.pal["cv_cizgi"])
        dugum_durum = {kok: self.row.get("status") or "Belirsiz"}
        kenarlar = []
        kok_yeniler = [x.strip() for x in (self.row.get("yeni_parseller") or "").split(";") if x.strip()]
        for yeni in kok_yeniler:
            kenarlar.append((kok, yeni))
            dugum_durum.setdefault(yeni, "Aktif")
        for no in self.tahmin:  # iş kaydında yazılı, sorgulanmamış parseller aynı yeni parsele birleşir
            dugum_durum[no] = "Pasif*"
            for yeni in kok_yeniler:
                kenarlar.append((no, yeni))
        for parca in self.devamlar:
            no = f"{parca.get('ada')}/{parca.get('parsel')}"
            dugum_durum[no] = parca.get("durum") or "Belirsiz"
            for yeni in (parca.get("yeni_parseller") or "").split(";"):
                yeni = yeni.strip()
                if yeni:
                    kenarlar.append((no, yeni))
                    dugum_durum.setdefault(yeni, "Aktif")
        if not kenarlar:
            p.setPen(cizgi)
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRectF(0, 88, w, 24), Qt.AlignmentFlag.AlignCenter, "Parsel hareket zinciri bulunamadı")
            return

        seviyeler = {kok: 0, **{n: 0 for n in self.tahmin}}
        for _ in range(20):
            degisti = False
            for kaynak, hedef in kenarlar:
                if kaynak in seviyeler and hedef not in seviyeler:
                    seviyeler[hedef] = seviyeler[kaynak] + 1
                    degisti = True
            if not degisti:
                break
        for no in dugum_durum:
            seviyeler.setdefault(no, 1)
        max_seviye = max(seviyeler.values()) if seviyeler else 1
        y_adim = max(85, min(125, 360 / max(max_seviye, 1)))
        konum = {}
        for seviye in range(max_seviye + 1):
            grup = [n for n, d in seviyeler.items() if d == seviye]
            for i, no in enumerate(grup):
                konum[no] = (w * (i + 1) / (len(grup) + 1), 55 + seviye * y_adim)
        kalem = QPen(cizgi)
        kalem.setWidth(2)
        for kaynak, hedef in kenarlar:
            if kaynak in konum and hedef in konum:
                x1, y1 = konum[kaynak]
                x2, y2 = konum[hedef]
                y1 += 18
                y2 -= 18
                p.setPen(kalem)
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                a = math.atan2(y2 - y1, x2 - x1)
                ok = QPolygonF([QPointF(x2, y2),
                                QPointF(x2 - 10 * math.cos(a - 0.4), y2 - 10 * math.sin(a - 0.4)),
                                QPointF(x2 - 10 * math.cos(a + 0.4), y2 - 10 * math.sin(a + 0.4))])
                p.setBrush(QBrush(cizgi))
                p.drawPolygon(ok)
        p.setFont(QFont("Segoe UI", 10))
        for no, (x, y) in konum.items():
            durum = dugum_durum.get(no, "Belirsiz")
            if durum == "Pasif":
                dolgu, yazi = self.pal["cv_pasif"]
            elif durum == "Pasif*":
                dolgu, yazi = self.pal["cv_tahmin"]
            elif durum == "Aktif":
                dolgu, yazi = self.pal["cv_aktif"]
            else:
                dolgu, yazi = "#fff1bf", "#000000"
            kutu_kalem = QPen(cizgi)
            if durum == "Pasif*":
                kutu_kalem.setStyle(Qt.PenStyle.DashLine)
            p.setPen(kutu_kalem)
            p.setBrush(QBrush(QColor(dolgu)))
            kutu = QRectF(x - 48, y - 17, 96, 34)
            p.drawRect(kutu)
            p.setPen(QColor(yazi))
            p.drawText(kutu, Qt.AlignmentFlag.AlignCenter, no + ("*" if durum == "Pasif*" else ""))
        if self.tahmin:
            p.setPen(cizgi)
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(0, 55 + max_seviye * y_adim + 36, w, 24), Qt.AlignmentFlag.AlignCenter,
                       "* iş kaydında yazılı, sorgulanmadı; tevhitle birleşmiş sayıldı")

    def _devam(self):
        """Zincirdeki alt parselleri (pasif ara + aktif son) kendi TKGM alan/nitelik ve işlem bilgileriyle gösterir."""
        try:
            devam = json.loads(self.row.get("devam_parseller") or "[]")
        except (TypeError, ValueError):
            devam = []
        satirlar = [((p.get("ada"), p.get("parsel"), p.get("durum"), p.get("alan"), p.get("nitelik"),
                      p.get("islem_turu") or "-", p.get("islem_tarihi") or "-"), p.get("durum") == "Pasif") for p in devam]
        ly = QVBoxLayout(self.devam_tab)
        ly.addWidget(_tablo_yap(["Ada", "Parsel", "Durum", "Alan (m²)", "Nitelik", "İşlem Türü", "İşlem Tarihi"],
                                [70, 80, 80, 110, 190, 140, 100], satirlar, self.pal["pasif_satir_fg"]))
        if not devam:
            ly.addWidget(QLabel("Parsel hareket zinciri bilgisi bulunamadı."), 0, Qt.AlignmentFlag.AlignHCenter)

    def _ham(self):
        parca = []
        for ad, v in (("PARSEL YANITI", self.row.get("ham_parsel")), ("HAREKET YANITI", self.row.get("ham_hareket"))):
            try:
                parca.append(f"=== {ad} ===\n" + (json.dumps(json.loads(v), ensure_ascii=False, indent=2) if v else "(yok)"))
            except ValueError:
                parca.append(f"=== {ad} ===\n{v}")
        self.ham_metin = "\n\n".join(parca)
        ly = QVBoxLayout(self.ham_tab)
        t = QPlainTextEdit()
        t.setReadOnly(True)
        t.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        t.setFont(QFont("Consolas", 9))
        t.setStyleSheet(f"background:{self.pal['cv_bg']};color:{self.pal['cv_yazi']};")
        t.setPlainText(self.ham_metin)
        ly.addWidget(t)
        b = QPushButton("Panoya kopyala")
        b.clicked.connect(self.kopyala)
        ly.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)

    def kopyala(self):
        QGuiApplication.clipboard().setText(self.ham_metin)


class HareketAyar(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Hareket servisini ayarla")
        self.resize(760, 470)
        yardim = ("Pasif parselin hareket listesini (yeni parselleri) getiren servis adresi bir kez tanımlanır.\n\n"
                  "1) Tarayıcıda parselsorgu.tkgm.gov.tr açın, F12 tuşuna basın, 'Ağ / Network' sekmesinde 'Fetch/XHR' seçin.\n"
                  "2) Pasif bir parseli sorgulayıp 'Parsel hareketlerini göster' bağlantısına tıklayın.\n"
                  "3) Listede yeni beliren isteğe tıklayın, 'Request URL' adresini kopyalayıp aşağıya yapıştırın.\n"
                  "4) Bu programda o parselin satırını seçip 'Örnek adresi şablona çevir'e basın, sonra Kaydet.\n"
                  "   (Adresteki mahalle kimliği, ada ve parsel değerleri {mahalle_id} {ada} {parsel} ile değiştirilir.)")
        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 14, 16, 14)
        y = QLabel(yardim)
        y.setWordWrap(True)
        ly.addWidget(y)
        self.var = QLineEdit(ayar_oku("hareket_url"))
        ly.addWidget(self.var)
        satir = QHBoxLayout()
        satir.addStretch(1)
        for ad, fn in (("Örnek adresi şablona çevir", self.cevir), ("Kaydet", self.kaydet),
                       ("Temizle (servisi kapat)", lambda: self.var.setText(""))):
            b = QPushButton(ad)
            b.clicked.connect(fn)
            satir.addWidget(b)
        satir.addStretch(1)
        ly.addLayout(satir)
        o = QLabel("Şablon örneği:  https://.../api/.../{mahalle_id}/{ada}/{parsel}")
        o.setStyleSheet(f"color:{(getattr(app, 'tk', None) or {}).get('SOLUK', '#666')};")
        ly.addWidget(o)
        ly.addStretch(1)

    def cevir(self):
        sec = self.app.secili_indeksler()
        if not sec:
            bilgi(self, "Bilgi", "Önce ana listede örnek parselin satırını seçin.")
            return
        self.var.setText(hareket_sablonu_yap(self.var.text(), self.app.rows[sec[0]]))

    def kaydet(self):
        ayar_yaz("hareket_url", self.var.text().strip())
        bilgi(self, "Kaydedildi", "Hareket servisi ayarı kaydedildi.")
        self.accept()


class MahalleEslestir(QDialog):
    """İş Takip'teki mahalle adı TKGM listesinde birebir bulunamazsa, TKGM'deki resmi adı bir kez seçtirir (hatırlanır).
    Kullanım: d = MahalleEslestir(master, adlar, tkgm_adlar); d.exec(); d.sonuc"""

    def __init__(self, master, adlar, tkgm_adlar):
        super().__init__(master if isinstance(master, QWidget) else None)
        self.setWindowTitle("Mahalle eşleştir")
        self.setModal(True)
        self.sonuc, self.vars = {}, {}
        ly = QVBoxLayout(self)
        ly.setContentsMargins(14, 12, 14, 12)
        a = QLabel("İş Takip'teki şu mahalle adları TKGM listesinde birebir bulunamadı. Doğru TKGM mahallesini seçin; seçim "
                   "hatırlanır, İş Takip'teki mahalle adı DEĞİŞMEZ. Emin olmadıklarınızı '(atla)' bırakın.")
        a.setWordWrap(True)
        a.setMinimumWidth(600)
        ly.addWidget(a)
        izgara = QGridLayout()
        for i, ad in enumerate(adlar):
            izgara.addWidget(QLabel(ad), i, 0)
            c = QComboBox()
            c.addItems(["(atla)"] + list(tkgm_adlar))
            c.setMinimumWidth(300)
            izgara.addWidget(c, i, 1)
            self.vars[ad] = c
        ly.addLayout(izgara)
        b = QPushButton("Tamam")
        b.clicked.connect(self._tamam)
        ly.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)

    def _tamam(self):
        self.sonuc = {ad: c.currentText() for ad, c in self.vars.items() if c.currentText() != "(atla)"}
        self.accept()


class App(QMainWindow):
    _durum_sig = Signal(str)
    _ilerleme_sig = Signal(int)
    _yenile_sig = Signal()
    _sayac_sig = Signal()
    _geri_sig = Signal(object, object)
    _bitti_sig = Signal(str, str)
    _iller_sig = Signal(str)
    _aktarim_sig = Signal(object, str, str, object, str, bool)

    def __init__(self, master=None, kaynak=None, takip_db=None, sonuc_geri_cagir=None):
        t0 = time.perf_counter()
        qapp_hazirla()
        super().__init__(master if isinstance(master, QWidget) else None)
        if master is not None and not isinstance(master, QWidget) and hasattr(master, "after"):
            _tk_koprusu(master)  # eski Tk tabanlı İş Takip içinden açılma (geçiş dönemi)
        self.kaynak = kaynak_normalle(kaynak)  # İş Takip'teki AÇIK işler
        self.takip_db = str(takip_db) if takip_db else ""  # sonuçların yazılacağı İş Takip veritabanı (isteğe bağlı)
        self.sonuc_geri_cagir = sonuc_geri_cagir          # f(work_id, sonuc_sozlugu): İş Takip arayüzünü yenilemek için (isteğe bağlı)
        self.acik_idler = {k["id"] for k in self.kaynak} if kaynak is not None else None
        self.baglar = {}
        self.setWindowTitle("Toplu Parsel Sorgulama | TKGM")
        self.resize(1280, 780)
        self.setMinimumSize(1050, 650)
        self.rows = []
        self.busy = False
        self._aktarim_suruyor = False
        self._kapaniyor = False
        self._durdur = threading.Event()
        self.gizli_sayi = 0
        self._detaylar = []
        tk_koyu = takip_temasi_koyu(self.takip_db)
        self.koyu = koyu_mu(self) if tk_koyu is None else tk_koyu
        self.pal = PALET_KOYU if self.koyu else PALET_ACIK
        self.tk = _et.jetonlar(self.koyu) if _et else None
        if self.tk:  # yalnızca bu pencere (ve alt pencereleri) boyanır; uygulamanın geri kalanına dokunulmaz
            self.setPalette(_et.palet_yap(self.tk))
            self.setStyleSheet(_et.qss_yap(self.tk))
        self._ui()
        self._durum_sig.connect(lambda t: self.status.set(t))
        self._ilerleme_sig.connect(self.progress.setValue)
        self._yenile_sig.connect(self.refresh)
        self._sayac_sig.connect(self.sayac_goster)
        self._geri_sig.connect(self._geri_cagir_ui)
        self._bitti_sig.connect(self._sorgu_bitti)
        self._iller_sig.connect(self._illeri_yukle_ui)
        self._aktarim_sig.connect(self._aktarim_tamam)
        self.load_saved()
        self.sayac_goster()
        for alan, kutu in self.vars.items():
            kutu_metin = kutu.lineEdit() if isinstance(kutu, QComboBox) else kutu
            kutu_metin.textChanged.connect(lambda _t, k=alan, v=kutu: ayar_yaz("secim_" + k, v.get()))
        QTimer.singleShot(50, self.illeri_yukle)
        if self.kaynak:  # açık işler ARKA PLANDA parsel listesine işlenir; pencere beklemeden açılır
            QTimer.singleShot(100, lambda: self.is_listesinden_aktar(sessiz=True))
        self.status.set(f"Pencere {time.perf_counter() - t0:.1f} sn'de açıldı."
                        + (" Açık işler arka planda aktarılıyor..." if self.kaynak else ""))
        _ACIK_PENCERELER.add(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.destroyed.connect(lambda _o=None, s=self: _ACIK_PENCERELER.discard(s))
        self.show()

    def _ui(self):
        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QVBoxLayout(merkez)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)
        band = QFrame()
        band.setObjectName("bant")
        band.setStyleSheet(f"QFrame#bant{{background:{self.pal['ust_bant']};}}")
        bl = QVBoxLayout(band)
        bl.setContentsMargins(22, 12, 22, 12)
        bl.setSpacing(2)
        baslik = QLabel("Toplu Parsel Sorgulama | TKGM")
        baslik.setStyleSheet("font-size:16pt;font-weight:600;color:white;background:transparent;")
        alt = QLabel("Aktif parselde alan ve nitelik, pasif parselde pasife alınma ibaresi ve oluşan yeni parseller gösterilir. "
                     "Satıra çift tıklayınca hareket listesi açılır.")
        alt.setStyleSheet("color:#C9D6F5;background:transparent;")
        alt.setWordWrap(True)
        bl.addWidget(baslik)
        bl.addWidget(alt)
        ana.addWidget(band)
        icerik = QWidget()
        ana.addWidget(icerik, 1)
        ana = QVBoxLayout(icerik)
        ana.setContentsMargins(18, 14, 18, 8)
        ana.setSpacing(10)

        bar = QHBoxLayout()
        bar.addWidget(self.btn("Excel şablonu oluştur", self.template))
        bar.addWidget(self.btn("Excel içe aktar", self.import_excel))
        bar.addWidget(self.vurgu(self.btn("İş listesinden aktar", self.is_listesinden_aktar)))
        bar.addWidget(self.btn("Sonuçları İş Takip'e yaz", self.tum_sonuclari_takibe_yaz))
        self.kapalilari_goster = QCheckBox("Kapanan işlerin parsellerini de göster")
        self.kapalilari_goster.toggled.connect(lambda _v: self.refresh())
        bar.addWidget(self.kapalilari_goster)
        bar.addWidget(self.btn("Seçili satırı sil", self.delete_selected))
        bar.addWidget(self.btn("Listeyi temizle", self.clear_rows))
        bar.addWidget(self.btn("Hareket servisini ayarla", lambda: HareketAyar(self).exec()))
        bar.addStretch(1)
        bar.addWidget(self.btn("Excel'e aktar", self.export_excel))
        ana.addLayout(bar)

        form = QGroupBox("Elle parsel ekle")
        izgara = QGridLayout(form)
        self.vars = {}
        for i, (etiket, key) in enumerate((("İl", "il"), ("İlçe", "ilce"), ("Mahalle", "mahalle"), ("Ada", "ada"), ("Parsel", "parsel"))):
            _e = QLabel(etiket)
            _e.setStyleSheet(f"color:{self.tk['SOLUK']};font-size:8.5pt;" if self.tk else "")
            izgara.addWidget(_e, 0, i)
            if key in ("il", "ilce", "mahalle"):
                w = AramaliKutu()
                if key == "il":
                    w.secildi.connect(lambda: self.il_secildi())
                elif key == "ilce":
                    w.secildi.connect(lambda: self.ilce_secildi())
                setattr(self, key + "_combo", w)
            else:
                w = Metin()
            self.vars[key] = w
            izgara.addWidget(w, 1, i)
            izgara.setColumnStretch(i, 1)
        izgara.addWidget(self.vurgu(self.btn("Listeye ekle", self.add_manual)), 1, 5)
        izgara.addWidget(self.btn("Mahalle listesini yenile", self.mahalleleri_yenile), 1, 6)
        ana.addWidget(form)

        self.model = ParselModel(self.pal)
        self.tree = QTableView()
        self.tree.setModel(self.model)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.verticalHeader().setVisible(False)
        self.tree.verticalHeader().setDefaultSectionSize(28)
        self.tree.setWordWrap(False)
        bs = self.tree.horizontalHeader()
        bs.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for j, w in enumerate(ParselModel.GENISLIK):
            self.tree.setColumnWidth(j, w)
        if _et:
            bs.setFont(_et.font_yap(8.5, kalin=True, aralik=0.5))
        self.tree.doubleClicked.connect(lambda _i: self.detay_ac())
        ana.addWidget(self.tree, 1)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        ana.addWidget(self.progress)
        alt_bar = QHBoxLayout()
        self.status = DurumEtiketi("Hazır. Excel şablonundaki sütunlar: İl, İlçe, Mahalle, Ada, Parsel.")
        alt_bar.addWidget(self.status, 1)
        alt_bar.addSpacing(14)
        alt_bar.addWidget(QLabel("Günlük üst sınır:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setKeyboardTracking(False)
        self.limit_spin.setValue(limit_degeri())
        self.limit_spin.valueChanged.connect(lambda _v: self.limit_degisti())
        alt_bar.addWidget(self.limit_spin)
        self.sayac_etiket = QLabel()
        self.sayac_etiket.setStyleSheet("color:#18334d;font-weight:bold;" if (not self.koyu and not self.tk) else "font-weight:bold;")
        alt_bar.addSpacing(14)
        alt_bar.addWidget(self.sayac_etiket)
        alt_bar.addWidget(self.btn("Seçili satırları sorgula", lambda: self.start_queries(secili=True)))
        alt_bar.addWidget(self.vurgu(self.btn("Bekleyenleri sorgula", self.start_queries)))
        ana.addLayout(alt_bar)

    @staticmethod
    def vurgu(b):
        b.setObjectName("vurgu")
        return b

    def btn(self, parent_veya_metin, metin_veya_komut, komut=None):
        """btn(metin, komut) biçiminde de çağrılabilir (eski btn(parent, metin, komut) imzası korunur)."""
        if komut is None:
            metin, komut = parent_veya_metin, metin_veya_komut
        else:
            metin = metin_veya_komut
        b = QPushButton(metin)
        b.clicked.connect(lambda _c=False: komut())
        return b

    def secili_indeksler(self):
        sm = self.tree.selectionModel()
        if sm is None:
            return []
        return sorted(ix.data(Qt.ItemDataRole.UserRole) for ix in sm.selectedRows())

    def closeEvent(self, olay):
        self._kapaniyor = True
        self._durdur.set()  # çalışan sorgu güvenle durur (bekleme süresi beklenmez)
        for th in list(_ARKA_PLAN):
            th.wait(8000)
        super().closeEvent(olay)

    @staticmethod
    def liste_adlari(veri):
        alanlar = ("text", "ad", "name", "ilAdi", "ilceAdi", "mahalleAdi")
        sonuc = []
        for item in feature_items(veri):
            if isinstance(item, dict):
                ad = next((str(item[k]).strip() for k in alanlar if item.get(k) not in (None, "")), "")
                if ad and ad not in sonuc:
                    sonuc.append(ad)
        return sorted(sonuc, key=norm_ad)

    def idari_liste(self, tur, ust_id=None):
        if tur == "il":
            url = API + "/idariYapi/ilListe"
        elif tur == "ilce":
            url = API + "/idariYapi/ilceListe/" + str(ust_id)
        else:
            url = API + "/idariYapi/mahalleListe/" + str(ust_id)
        return get_json_onbellekli(url)

    def _arka_plan(self, fn):
        th = _Is(fn)
        th.start()
        return th

    def illeri_yukle(self):
        """İl/ilçe/mahalle listelerini ARKA PLANDA önbelleğe alır (ağ yavaşsa pencere donmaz), sonra arayüzü doldurur."""
        def isci():
            hata = ""
            try:
                iller = get_json_onbellekli(API + "/idariYapi/ilListe")
                il, ilce = ayar_oku("secim_il"), ayar_oku("secim_ilce")
                if il:
                    il_id = find_id(feature_items(iller), ["text", "ad", "name", "ilAdi"], il)
                    ilceler = get_json_onbellekli(f"{API}/idariYapi/ilceListe/{il_id}")
                    if ilce:
                        ilce_id = find_id(feature_items(ilceler), ["text", "ilceAdi", "ad", "name"], ilce)
                        get_json_onbellekli(f"{API}/idariYapi/mahalleListe/{ilce_id}")
            except Exception as e:
                hata = str(e)
            if not self._kapaniyor:
                self._iller_sig.emit(hata)
        self._arka_plan(isci)

    def _illeri_yukle_ui(self, hata=""):
        if hata:  # ağda sorun varsa arayüz iş parçacığında tekrar ağ isteği ATILMAZ
            self.status.set("Konum listeleri alınamadı (TKGM yanıt vermiyor olabilir): " + hata[:110])
            return
        try:
            iller = self.idari_liste("il")
            self.il_combo.listeyi_ata(self.liste_adlari(iller))
            kayitli_il = ayar_oku("secim_il")
            kayitli_ilce = ayar_oku("secim_ilce")
            kayitli_mahalle = ayar_oku("secim_mahalle")
            if kayitli_il in self.il_combo._tam:
                self.vars["il"].set(kayitli_il)
                self.il_secildi(restore=True, ilce=kayitli_ilce, mahalle=kayitli_mahalle)
        except Exception as e:
            self.status.set("İl listesi alınamadı: " + str(e))

    def il_secildi(self, _event=None, restore=False, ilce="", mahalle=""):
        try:
            iller = self.idari_liste("il")
            il_id = find_id(feature_items(iller), ["text", "ad", "name", "ilAdi"], self.vars["il"].get())
            ilceler = self.idari_liste("ilce", il_id)
            self.ilce_combo.listeyi_ata(self.liste_adlari(ilceler))
            self.mahalle_combo.listeyi_ata([])
            if restore:
                if ilce in self.ilce_combo._tam:
                    self.vars["ilce"].set(ilce)
                    self.mahalleleri_yenile(restore_mahalle=mahalle)
            else:
                self.vars["ilce"].set("")
                self.vars["mahalle"].set("")
        except Exception as e:
            hata_kutusu(self, "İlçe listesi alınamadı", str(e))

    def ilce_secildi(self, _event=None):
        self.mahalleleri_yenile()

    def mahalleleri_yenile(self, restore_mahalle=""):
        try:
            iller = self.idari_liste("il")
            il_id = find_id(feature_items(iller), ["text", "ad", "name", "ilAdi"], self.vars["il"].get())
            ilceler = self.idari_liste("ilce", il_id)
            ilce_id = find_id(feature_items(ilceler), ["text", "ilceAdi", "ad", "name"], self.vars["ilce"].get())
            mahalleler = self.idari_liste("mahalle", ilce_id)
            self.mahalle_combo.listeyi_ata(self.liste_adlari(mahalleler))
            if restore_mahalle in self.mahalle_combo._tam:
                self.vars["mahalle"].set(restore_mahalle)
            self.status.set(str(len(self.mahalle_combo._tam)) + " mahalle listelendi.")
        except Exception as e:
            hata_kutusu(self, "Mahalle listesi alınamadı", str(e))

    # ---- sayaç / limit
    def limit_degisti(self):
        v = max(1, min(int(self.limit_spin.value()), 100))
        self.limit_spin.blockSignals(True)
        self.limit_spin.setValue(v)
        self.limit_spin.blockSignals(False)
        ayar_yaz("gunluk_limit", v)
        self.sayac_goster()

    def sayac_goster(self):
        self.sayac_etiket.setText(f"Bugün: {sayac_oku()} / {limit_degeri()} istek")

    # ---- liste işlemleri
    def is_listesinden_aktar(self, sessiz=False, bekle=False):
        """İş Takip'teki AÇIK işleri parsel listesine aktarır ve her satırı iş kayıt numarasıyla ilişkilendirir.
        Ağ ve hazırlık işi arka planda yapılır (pencere donmaz); veritabanına tek işlemde yazılır. bekle=True: aynı iş parçacığında çalıştırır."""
        if not self.kaynak:
            if not sessiz:
                bilgi(self, "İş listesinden aktar", "Aktarılacak açık iş kaydı bulunamadı.")
            return
        if getattr(self, "_aktarim_suruyor", False):
            return
        self._aktarim_suruyor = True
        il = self.vars["il"].get().strip() or ayar_oku("secim_il") or VARSAYILAN_IL
        ilce = self.vars["ilce"].get().strip() or ayar_oku("secim_ilce") or VARSAYILAN_ILCE
        self.status.set("Açık işler parsel listesine aktarılıyor...")
        kaynak = list(self.kaynak)

        def isci():
            hata, sonuc, mahalleler = "", None, []
            try:
                mahalleler = mahalle_listesi_getir(il, ilce)
                sonuc = aktarim_hazirla(kaynak, il, ilce, mahalleler, esleme_hafizasi(il, ilce))
            except Exception as e:
                hata = str(e)
            if not self._kapaniyor:
                self._aktarim_sig.emit(sonuc, il, ilce, mahalleler, hata, sessiz)

        if bekle:
            isci()
        else:
            self._arka_plan(isci)

    def _aktarim_tamam(self, sonuc, il, ilce, mahalleler, hata, sessiz):
        """(Arayüz iş parçacığı) hazırlanan aktarımı uygular."""
        self._aktarim_suruyor = False
        if hata:
            self.status.set("İş aktarımı yapılamadı: TKGM mahalle listesi alınamadı - " + hata[:120])
            if not sessiz:
                hata_kutusu(self, "TKGM listesi alınamadı", hata)
            return
        if sonuc["eslesmeyen"] and not sessiz:
            secilen = self.mahalle_eslestir_sor(sorted(sonuc["eslesmeyen"]), mahalleler)
            if secilen:
                for ad, (tkgm_ad, mid) in secilen.items():
                    esleme_kaydet(il, ilce, ad, tkgm_ad, mid)
                sonuc = aktarim_hazirla(self.kaynak, il, ilce, mahalleler, esleme_hafizasi(il, ilce))
        mevcut = {norm_anahtar(r): r for r in self.rows}  # tek geçişte dizinlenir (eskiden her iş için tüm liste taranıyordu)
        yeni_satirlar, guncellenen, baglar = [], [], []
        for s in sonuc["satirlar"]:
            satir = {k: s[k] for k in ("il", "ilce", "mahalle", "tkgm_mahalle", "mahalle_id", "ada", "parsel")}
            satir.update({"status": "Bekliyor", "detail": f"İş Takip kaydı #{s['work_id']} üzerinden aktarıldı."})
            hedef = mevcut.get(norm_anahtar(satir))
            if hedef is None:
                self.rows.append(satir)
                mevcut[norm_anahtar(satir)] = satir
                yeni_satirlar.append(satir)
                hedef = satir
            elif not hedef.get("mahalle_id") or not hedef.get("tkgm_mahalle"):
                hedef["mahalle_id"] = hedef.get("mahalle_id") or satir["mahalle_id"]
                hedef["tkgm_mahalle"] = hedef.get("tkgm_mahalle") or satir["tkgm_mahalle"]
                guncellenen.append(hedef)
            baglar.append((s["work_id"], satir_anahtari(hedef), s["kaynak_metin"]))
        zaman = datetime.now().isoformat(timespec="seconds")
        yer = ",".join("?" * len(SUTUNLAR))
        guncelle_sql = ",".join(f"{k}=excluded.{k}" for k in SUTUNLAR[5:])
        con = db()
        try:
            with con:  # TEK işlem: yüzlerce ayrı kayıt/fsync yerine bir kez
                for r in yeni_satirlar:
                    r["updated"] = zaman
                    con.execute(f"INSERT INTO parcels({','.join(SUTUNLAR)}) VALUES({yer}) ON CONFLICT(il,ilce,mahalle,ada,parsel) "
                                f"DO UPDATE SET {guncelle_sql}", [r.get(k) for k in SUTUNLAR])
                for r in guncellenen:
                    con.execute("UPDATE parcels SET mahalle_id=?, tkgm_mahalle=? WHERE il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?",
                                (r["mahalle_id"], r["tkgm_mahalle"], *satir_anahtari(r)))
                for wid, anahtar, metin in baglar:
                    con.execute("DELETE FROM is_parsel_bag WHERE work_id=? AND NOT (il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?)",
                                (wid, *anahtar))
                    con.execute("INSERT OR REPLACE INTO is_parsel_bag VALUES (?,?,?,?,?,?,?,?)", (wid, *anahtar, metin, zaman))
        finally:
            con.close()
        self.baglar = baglantilari_oku()
        self.refresh()
        mesaj = [f"İş Takip'teki açık iş: {len(self.kaynak)}",
                 f"İş numarasıyla bağlanan: {len(sonuc['satirlar'])} (yeni parsel satırı: {len(yeni_satirlar)})"]
        if self.gizli_sayi:
            mesaj.append(f"Bağlı işi kapanmış parsel: {self.gizli_sayi} (listede gizli, sorgulanmaz, limit harcanmaz)")
        if sonuc["coklu"]:
            mesaj.append("Birden fazla parsel yazılı olduğu için yalnızca İLK parsel sorgulanacak: " + ", ".join(sonuc["coklu"][:12])
                         + (" ..." if len(sonuc["coklu"]) > 12 else ""))
        if sonuc["eslesmeyen"]:
            mesaj.append("TKGM'de mahalle eşleşmeyen işler (eklenmedi): " + "; ".join(
                f"{ad} ({', '.join('#' + str(i) for i in ids[:5])})" for ad, ids in sorted(sonuc["eslesmeyen"].items())))
        if sonuc["hatali"]:
            mesaj.append("Okunamayan kayıtlar: " + "; ".join(sonuc["hatali"][:10]))
        self.status.set("İş listesinden aktarım: " + " | ".join(mesaj[:2]) + (
            " | Eşleşmeyen mahalle var: 'İş listesinden aktar' ile eşleştirin." if sonuc["eslesmeyen"] and sessiz else ""))
        if not sessiz:
            bilgi(self, "İş listesinden aktarım", "\n\n".join(mesaj))

    def mahalle_eslestir_sor(self, adlar, mahalleler):
        """{kaynak_mahalle: (tkgm_ad, mahalle_id)} döndürür."""
        harita = {}
        for item in mahalleler:
            ad, kod = mahalle_adi_ve_id(item)
            if ad and kod:
                harita[ad] = kod
        d = MahalleEslestir(self, adlar, sorted(harita, key=norm_ad))
        d.exec()
        return {k: (v, harita[v]) for k, v in d.sonuc.items() if v in harita}

    def _geri_cagir_ui(self, wid, ozet):
        """(Arayüz iş parçacığı) İş Takip'e sonuç bildirimi."""
        if self.sonuc_geri_cagir:
            try:
                self.sonuc_geri_cagir(wid, ozet)
            except Exception as e:
                self.status.set(f"İş Takip bildirimi başarısız (#{wid}): {e}")

    def takibe_yaz(self, row):
        """Sorgu sonucunu bu parsele bağlı her İş Takip kaydına yazar (iş kaydının kendisi değiştirilmez)."""
        for wid in self.baglar.get(satir_anahtari(row), []):
            try:
                if self.takip_db:
                    takip_sonuc_yaz(self.takip_db, wid, row)
                if self.sonuc_geri_cagir:
                    self._geri_sig.emit(wid, sonuc_ozeti(row))  # arayüz iş parçacığında çalışsın
            except Exception as e:
                self._durum_sig.emit(f"İş Takip'e yazılamadı (#{wid}): {e}")

    def tum_sonuclari_takibe_yaz(self):
        if not (self.takip_db or self.sonuc_geri_cagir):
            bilgi(self, "İş Takip bağlantısı", "Bu pencere İş Takip veritabanına bağlı açılmamış (takip_db verilmemiş).")
            return
        n = 0
        for r in self.rows:
            if (r.get("status") in ("Aktif", "Pasif", "Belirsiz")) and self.baglar.get(satir_anahtari(r)):
                self.takibe_yaz(r)
                n += len(self.baglar[satir_anahtari(r)])
        self.status.set(f"{n} iş kaydının parsel sonucu İş Takip'e yazıldı.")
        bilgi(self, "İş Takip bağlantısı", f"{n} iş kaydının parsel sonucu İş Takip'e yazıldı.")

    def add_manual(self):
        row = {k: v.get().strip() for k, v in self.vars.items()}
        if not all(row.values()):
            uyari(self, "Eksik bilgi", "İl, ilçe, mahalle, ada ve parsel alanlarının tamamını doldurun.")
            return
        self.add_row(row)
        # Parsel eklenince il/ilçe/mahalle sabit kalsın; yalnız ada ve parsel temizlensin.
        self.vars["ada"].set("")
        self.vars["parsel"].set("")

    def add_row(self, row):
        key = tuple(str(row.get(k, "")).strip() for k in ("il", "ilce", "mahalle", "ada", "parsel"))
        if any(tuple(str(x.get(k, "")).strip() for k in ("il", "ilce", "mahalle", "ada", "parsel")) == key for x in self.rows):
            return
        row.setdefault("status", "Bekliyor")
        self.rows.append(row)
        self.refresh()
        self.save_row(row)

    def kapali_mi(self, r):
        """Bağlı TÜM işleri kapanmış (tescillendi/askıda/iptal) parsel: sorgu listesinde gerek yok."""
        ids = self.baglar.get(satir_anahtari(r))
        return bool(ids) and self.acik_idler is not None and not any(i in self.acik_idler for i in ids)

    def gorunen_satirlar(self):
        return [r for r in self.rows if self.kapalilari_goster.isChecked() or not self.kapali_mi(r)]

    def refresh(self):
        goster = self.kapalilari_goster.isChecked()
        gizli = 0
        satirlar = []
        for i, r in enumerate(list(self.rows)):
            if not goster and self.kapali_mi(r):
                gizli += 1
                continue
            st = r.get("status") or "Bekliyor"
            islem = f"{r.get('islem_turu') or ''} {r.get('islem_tarihi') or ''}".strip()
            kontrol = (r.get("updated") or "")[:16].replace("T", " ")
            satirlar.append((i, st, [
                r.get("il", ""), r.get("ilce", ""), r.get("mahalle", ""), r.get("ada", ""), r.get("parsel", ""),
                ", ".join(f"#{k}" for k in self.baglar.get(satir_anahtari(r), [])), st,
                r.get("alan", "") or "", r.get("nitelik", "") or "", (r.get("yeni_parseller") or "").replace("; ", ", "), islem, kontrol]))
        self.model.yukle(satirlar)
        self.gizli_sayi = gizli

    def ilgili_parseller(self, row):
        """Bu parsele bağlı iş kayıtlarında yazılı TÜM parseller (sorgulanan hariç): '727/2-3' -> ['727/3']."""
        kok = f"{row.get('ada')}/{row.get('parsel')}"
        con = db()
        metinler = [r[0] for r in con.execute(
            "SELECT kaynak_metin FROM is_parsel_bag WHERE il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?",
            satir_anahtari(row))]
        con.close()
        out = []
        for metin in metinler:
            for ada, parsel in parselleri_coz(metin):
                no = f"{ada}/{parsel}"
                if no != kok and no not in out:
                    out.append(no)
        return out

    def detay_ac(self):
        sec = self.secili_indeksler()
        if sec:
            row = self.rows[sec[0]]
            d = Detay(self, row, self.ilgili_parseller(row))
            d.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self._detaylar.append(d)
            d.destroyed.connect(lambda _o=None, x=d: self._detaylar.remove(x) if x in self._detaylar else None)
            d.show()

    def template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel şablonu", "Parsel_Sorgu_Sablonu.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Parsel Listesi"
        ws.append(["İl", "İlçe", "Mahalle", "Ada", "Parsel"])
        ws.append(["Bursa", "Mustafakemalpaşa", "Atatürk", "727", "2"])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="244766")
        for col, w in zip("ABCDE", [22, 25, 28, 14, 14]):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        wb.save(path)
        bilgi(self, "Tamamlandı", "Excel şablonu oluşturuldu.")

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel içe aktar", "", "Excel (*.xlsx *.xlsm)")
        if not path:
            return
        try:
            ws = load_workbook(path, data_only=True).active
            headers = [str(c.value or "").strip().casefold() for c in ws[1]]
            aliases = {"il": ["il", "şehir", "sehir"], "ilce": ["ilçe", "ilce"], "mahalle": ["mahalle", "köy", "koy"],
                       "ada": ["ada", "ada no", "ada no."], "parsel": ["parsel", "parsel no", "parsel no."]}
            idx = {}
            for k, names in aliases.items():
                for j, h in enumerate(headers):
                    if h in names:
                        idx[k] = j
                        break
            if len(idx) != 5:
                raise ValueError("İlk satırda İl, İlçe, Mahalle, Ada ve Parsel sütunları bulunmalı.")
            count = 0
            for vals in ws.iter_rows(min_row=2, values_only=True):
                row = {k: str(vals[j]).strip() if j < len(vals) and vals[j] is not None else "" for k, j in idx.items()}
                if all(row.values()):
                    before = len(self.rows)
                    self.add_row(row)
                    count += len(self.rows) - before
            self.status.set(f"{count} yeni parsel eklendi.")
        except Exception as e:
            hata_kutusu(self, "Excel okunamadı", str(e))

    def delete_selected(self):
        selected = self.secili_indeksler()
        if not selected:
            return
        for i in sorted(selected, reverse=True):
            r = self.rows.pop(i)
            con = db()
            con.execute("DELETE FROM parcels WHERE il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?",
                        (r["il"], r["ilce"], r["mahalle"], r["ada"], r["parsel"]))
            con.execute("DELETE FROM is_parsel_bag WHERE il=? AND ilce=? AND mahalle=? AND ada=? AND parsel=?",
                        (r["il"], r["ilce"], r["mahalle"], r["ada"], r["parsel"]))
            con.commit()
            con.close()
        self.baglar = baglantilari_oku()
        self.refresh()

    def clear_rows(self):
        if self.busy:
            return
        if sor(self, "Onay", "Ekrandaki liste temizlensin mi? Kayıtlı sonuç veritabanı korunur."):
            self.rows = []
            self.refresh()

    # ---- veritabanı
    def save_row(self, r):
        con = db()
        r["updated"] = datetime.now().isoformat(timespec="seconds")
        deger = [r.get(k) for k in SUTUNLAR]
        yer = ",".join("?" * len(SUTUNLAR))
        guncelle = ",".join(f"{k}=excluded.{k}" for k in SUTUNLAR[5:])
        con.execute(f"INSERT INTO parcels({','.join(SUTUNLAR)}) VALUES({yer}) ON CONFLICT(il,ilce,mahalle,ada,parsel) DO UPDATE SET {guncelle}", deger)
        con.commit()
        con.close()

    def load_saved(self):
        self.baglar = baglantilari_oku()
        con = db()
        veri = con.execute(f"SELECT {','.join(SUTUNLAR)} FROM parcels ORDER BY id").fetchall()
        con.close()
        for x in veri:
            r = dict(zip(SUTUNLAR, x))
            if r.get("status") in (None, "", "Başarılı"):  # eski sürümde pasif/aktif ayrımı yoktu: yeniden sorgulanmalı
                r["status"] = "Bekliyor"
            self.rows.append(r)
        self.refresh()

    # ---- sorgulama
    def bekleyenler(self):
        sinir = datetime.now() - timedelta(days=VARSAYILAN_YENILE_GUN)
        out = []
        for r in self.rows:
            ids = self.baglar.get(satir_anahtari(r), [])
            if ids and self.acik_idler is not None and not any(i in self.acik_idler for i in ids):
                continue  # bağlı tüm işler kapanmış (tescillendi/askıda/iptal): günlük limit boşa harcanmasın
            st = r.get("status") or "Bekliyor"
            if st in ("Bekliyor", "Hata", "Belirsiz") or (st == "Aktif" and son_kontrol(r) < sinir):
                out.append(r)  # Pasif olanlar tekrar sorgulanmaz (işlem tamamlanmış)
        return out

    def start_queries(self, secili=False):
        if self.busy:
            return
        if secili:
            pending = [self.rows[i] for i in self.secili_indeksler()]
        else:
            pending = self.bekleyenler()
        if not pending:
            bilgi(self, "Bilgi", "Sorgulanacak parsel yok. (Pasif olanlar ve yakın zamanda kontrol edilen aktif parseller atlanır; "
                                 "belirli satırları sorgulamak için seçip 'Seçili satırları sorgula'ya basın.)")
            return
        kalan = max(limit_degeri() - sayac_oku(), 0)
        if kalan <= 0:
            uyari(self, "Günlük sınır", "Bugünkü istek üst sınırına ulaşıldı. Yarın devam edin ya da sınırı artırın.")
            return
        if not sor(self, "Toplu sorgu", f"{len(pending)} parsel sorgulanacak (bugün kalan istek hakkı: {kalan}). "
                                        "İstekler arası bekleme uygulanır. Başlatılsın mı?"):
            return
        self.busy = True
        self._durdur.clear()
        self.progress.setMaximum(len(pending))
        self.progress.setValue(0)
        self._arka_plan(lambda: self.worker(pending))

    def worker(self, pending):
        sayim = {"Aktif": 0, "Pasif": 0, "Belirsiz": 0, "Hata": 0}
        durdu = ""
        for n, row in enumerate(pending, 1):
            if self._durdur.is_set():
                durdu = "Pencere kapatıldı."
                break
            try:
                self._durum_sig.emit(f"Sorgulanıyor: {row['mahalle']} {row['ada']}/{row['parsel']}")
                query_one(row)
                row.pop("geometry", None)
                # Harita PNG dosyası üretilmez veya diske kaydedilmez.
                sayim[row["status"]] = sayim.get(row["status"], 0) + 1
            except (LimitHatasi, ErisimHatasi) as e:
                durdu = str(e)
                row["detail"] = durdu
                self.save_row(row)
                break
            except Exception as e:
                row["status"] = "Hata"
                row["detail"] = str(e)
                sayim["Hata"] += 1
            self.save_row(row)
            self.takibe_yaz(row)
            self._yenile_sig.emit()
            self._sayac_sig.emit()
            self._ilerleme_sig.emit(n)
            self._durdur.wait(BEKLEME_SN)
        self.busy = False
        ozet = f"Aktif: {sayim['Aktif']} | Pasif: {sayim['Pasif']} | Belirsiz: {sayim['Belirsiz']} | Hatalı: {sayim['Hata']}"
        self._bitti_sig.emit(durdu, ozet)

    def _sorgu_bitti(self, durdu, ozet):
        self.refresh()
        self.sayac_goster()
        self.status.set(("Durduruldu: " + durdu + "  " if durdu else "Tamamlandı. ") + ozet)
        if not self._kapaniyor:
            bilgi(self, "Sorgu bitti", ("DURDURULDU: " + durdu + "\n\n" if durdu else "") + ozet)

    def export_excel(self):
        if not self.rows:
            bilgi(self, "Bilgi", "Aktarılacak kayıt yok.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excel'e aktar", "Parsel_Sorgu_Sonuclari.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Sorgu Sonuçları"
        ws.append(["İl", "İlçe", "Mahalle", "Ada", "Parsel", "Parsel durumu", "Alan (m²)", "Nitelik", "Pasif ibaresi", "İşlem türü",
                   "İşlem tarihi", "Yeni parseller", "Son kontrol", "Açıklama", "Koordinatlar (Enlem, Boylam)"])
        for r in self.gorunen_satirlar():
            ws.append([r.get("il"), r.get("ilce"), r.get("mahalle"), r.get("ada"), r.get("parsel"), r.get("status"), r.get("alan"),
                       r.get("nitelik"), r.get("pasif_mesaj"), r.get("islem_turu"), r.get("islem_tarihi"),
                       (r.get("yeni_parseller") or "").replace("; ", ", "), (r.get("updated") or "").replace("T", " "),
                       r.get("detail"), r.get("koordinatlar")])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="244766")
            c.alignment = Alignment(wrap_text=True)
        for i, w in enumerate([14, 20, 20, 10, 10, 14, 12, 16, 50, 12, 13, 24, 17, 50, 40], 1):
            ws.column_dimensions[chr(64 + i)].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        devam_ws = wb.create_sheet("Parsel Hareket Zinciri")
        devam_ws.append(["Kaynak İl", "Kaynak İlçe", "Kaynak Mahalle", "Başlangıç Ada", "Başlangıç Parsel", "İşlem Türü", "İşlem Tarihi", "Alt Ada", "Alt Parsel", "Durum", "Alan (m²)", "Nitelik", "Koordinatlar (Enlem, Boylam)"])
        for kaynak in self.gorunen_satirlar():
            try:
                altlar = json.loads(kaynak.get("devam_parseller") or "[]")
            except (TypeError, ValueError):
                altlar = []
            for alt in altlar:
                devam_ws.append([kaynak.get("il"), kaynak.get("ilce"), kaynak.get("mahalle"), kaynak.get("ada"), kaynak.get("parsel"),
                                 kaynak.get("islem_turu"), kaynak.get("islem_tarihi"), alt.get("ada"), alt.get("parsel"), alt.get("durum"),
                                 alt.get("alan"), alt.get("nitelik"), alt.get("koordinatlar")])
        for c in devam_ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="244766")
            c.alignment = Alignment(wrap_text=True)
        for i, w in enumerate([14, 20, 20, 10, 10, 14, 13, 10, 10, 12, 12, 22, 42], 1):
            devam_ws.column_dimensions[chr(64 + i)].width = w
        devam_ws.freeze_panes = "A2"
        devam_ws.auto_filter.ref = devam_ws.dimensions
        wb.save(path)
        bilgi(self, "Tamamlandı", "Excel sonuç dosyası oluşturuldu. Parsel hareket zinciri (pasif ara ve aktif son parseller) ayrı sayfaya eklendi.")


if __name__ == "__main__":
    qapp = qapp_hazirla()
    pencere = App()
    kod = qapp.exec()
    for _th in list(_ARKA_PLAN):
        _th.wait(30000)
    sys.exit(kod)
