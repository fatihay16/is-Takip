import os, sys, re, csv, json, time, base64, calendar, datetime, sqlite3, subprocess, tempfile, webbrowser, pathlib
from html import escape as hesc
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import modern_tasarim

BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
DB = os.path.join(BASE, "imar_kayitlari.db")
EXT = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff")

# (alan, başlık, tür)  tür: None=düz kutu, "liste:x"=açılır liste, "dosya"=dosya seç
FIELDS = [
    ("mahalle", "Mahalle", "liste:mahalle"), ("ada_parsel", "Ada/Parsel", None),
    ("islem", "İşlem", "liste:islem"), ("encumen_tarihi", "Encümen Tarih", None),
    ("karar_no", "Karar No", None), ("karar_tarihi", "Tarih", None),
    ("alinan_ucret", "Alınan Ücret", None), ("aciklama", "Açıklamalar", None),
    ("muellif", "Müellif", "liste:muellif"), ("onay", "Onay Durumu", "liste:onay"),
    ("makbuz_tarihi", "Ödeme Makbuz Tarih", None), ("makbuz_no", "Makbuz No (Sayı)", None),
    ("karar_dosya", "Karar Dosyası (dosya yolu)", "dosya"),
    ("makbuz_dosya", "Makbuz Dosyası (dosya yolu)", "dosya"),
]
KEYS = [f[0] for f in FIELDS]
LAB = {f[0]: f[1] for f in FIELDS}
LAB["bekleme"] = "Bekleme (gün)"
LAB["parsel_durum"] = "Parsel durumu"
LAB["parsel_yeni"] = "Yeni parseller"
SHOWN = [k for k in KEYS if not k.endswith("_dosya")]
TV_COLS = ["sira"] + SHOWN + ["karar_ok", "makbuz_ok", "bekleme", "parsel_durum", "parsel_yeni"]
DURUM_RENK = {"Tescilde Bekliyor": "#d4f0d4", "Ödeme Bekleniyor": "#fff2b8", "Encümene Girdi": "#d3e5ff",
              "Encümene Yazıldı": "#ffdcb8", "Görüş Soruldu": "#e8d6f5",
              "Tescillendi": "#bfe9e4", "Askıda Kaldı": "#e5e7eb", "İptal": "#fecaca"}
GORUNUMLER = ["Aktif işler", "Tümü (arşiv dahil)", "Sadece arşiv (Tescillendi/Askıda/İptal)"]
BAZI_GORUNUM = {  # hazır kayıtlı filtreler
    "Ödeme bekleyenler": {"lf": {"onay": "Ödeme Bekleniyor"}},
    "Bu ay encümen": {"gorunum": GORUNUMLER[1], "alan": "Encümen Tarih", "preset": "Bu ay"},
    "Geciken işler": {"gecik": True},
    "Dosyası eksik olanlar": {"eksik": True},
}

HDR = {"mahalle": "mahalle", "ada/parsel": "ada_parsel", "işlem": "islem", "encümen tarih": "encumen_tarihi",
       "karar no": "karar_no", "tarih": "karar_tarihi", "alınan ücret": "alinan_ucret", "açıklamalar": "aciklama",
       "müellif": "muellif", "onay durumu": "onay", "ödeme makbuz tarih": "makbuz_tarihi", "sayı": "makbuz_no",
       "karar dosyası (dosya yolu)": "karar_dosya", "makbuz dosyası (dosya yolu)": "makbuz_dosya"}
LT = {"mahalle": "Mahalle", "muellif": "Müellif", "islem": "İşlem", "onay": "Onay Durumu"}
SEED = {
    "mahalle": "ALİSEYDİ ALPAĞUT ATATÜRK ÇAKALLAR ÇARDAKBELEN ÇELTİKÇİ ÇİVİLİÇAM ÇÖRDÜK DEMİRDERE DERECİK DEREKADI "
               "DOĞANALAN DURUMTAY FEVZİDEDE FINDICAK HACIAHMET HAMİDİYEKÖY IŞIKLAR KARAOĞLAN KARAPINAR KAVAKLI "
               "KAYABAŞI KAZANPINAR KİLLİK KÖMÜRCÜKADI KÖREKEM KÖSEHOROZ KOSOVA KOŞUBOĞAZI MELİK MURADİYESARNIÇ "
               "OCAKLI ORMANKADI PAŞALAR ŞAPÇI SARIMUSTAFALAR SELİMİYE ŞEVKETİYE SİNCANSARNIÇ SÖĞÜTALAN SÜNLÜK "
               "TAŞPINAR TEPECİK ÜÇBEYLİ VIRACA YALINTAŞ YAMANLI YENİCE YEŞİLOVA YONCAAĞAÇ YUMURCAKLI BEHRAM "
               "GÜLLÜCE GÜVEÇDERE".split(),
    "muellif": ["Hüsamettin", "Serkan Abi", "Serhat", "Adnan Abi", "Doruk Harita", "Proses Harita", "Ufuk Ay",
                "Ramazan AKILLI", "Sebahattin GÖKÇE", "Hazine", "1611/785 Lihkab", "1607/733 Lihkab",
                "1611/572 Lihkab", "1611/1018 Lihkab", "1607/555 Lihkab"],
    "islem": ["ifraz", "tevhit", "tevhit-ifraz", "imar uygulaması", "yola terk", "ihdas", "ihdas-tevhit",
              "ifraz(mahkeme)", "tevhit-yola terk-ifraz"],
    "onay": ["Görüş Soruldu", "Ödeme Bekleniyor", "Encümene Girdi", "Encümene Yazıldı", "Tescilde Bekliyor"],
}


def tr_lower(s):
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


TR_ABC = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"


def tr_sira(s):
    """Türkçe alfabe sırası: ... C < Ç < D ... G < Ğ < H < I < İ ... S < Ş < T ... U < Ü < V"""
    return tuple(1000 + TR_ABC.index(c) if c in TR_ABC else ord(c) for c in tr_lower(s))


def temiz(s):
    return (s or "").replace("\u200b", "").strip()


def para_oku(x):
    """TRY / TL / ₺ ile yazılmış, Türkçe (9.500,00) veya İngilizce (9,500.00) biçimli tutarı sayıya çevirir."""
    x = re.sub(r"try|tl|₺|\s", "", (x or "").replace("\u200b", ""), flags=re.I)
    if not x or x in ("-", "–", "—"):
        return None
    if "," in x and "." in x:
        x = x.replace(".", "").replace(",", ".") if x.rfind(",") > x.rfind(".") else x.replace(",", "")
    elif "," in x:
        p = x.split(",")
        x = x.replace(",", "") if (len(p) > 2 or len(p[-1]) == 3) else x.replace(",", ".")
    elif "." in x:
        p = x.split(".")
        if len(p) > 2 or len(p[-1]) == 3:
            x = x.replace(".", "")
    try:
        return float(x)
    except ValueError:
        return None


def para(x):
    return para_oku(x) or 0.0


def para_yaz(v, n=2):
    return f"{v:,.{n}f}".replace(",", "_").replace(".", ",").replace("_", ".") + " ₺"


def para_bicim(x):
    x = temiz(x)
    v = para_oku(x)
    return x if v is None else para_yaz(v)


def q(sql, args=()):
    con = sqlite3.connect(DB)
    try:
        with con:
            return con.execute(sql, args).fetchall()
    finally:
        con.close()


def init_db():
    q(f"CREATE TABLE IF NOT EXISTS kayit (id INTEGER PRIMARY KEY AUTOINCREMENT, {', '.join(k + ' TEXT' for k in KEYS)})")
    q("CREATE TABLE IF NOT EXISTS ayar (ad TEXT PRIMARY KEY, deger TEXT)")
    q("CREATE TABLE IF NOT EXISTS liste (tur TEXT, deger TEXT, PRIMARY KEY (tur, deger))")
    if "durum_tarihi" not in [r[1] for r in q("PRAGMA table_info(kayit)")]:
        q("ALTER TABLE kayit ADD COLUMN durum_tarihi TEXT")  # durumun en son değiştiği tarih (bekleme süresi için)
    q(f"CREATE TABLE IF NOT EXISTS silinen (sid INTEGER PRIMARY KEY AUTOINCREMENT, silinme TEXT, "
      f"{', '.join(k + ' TEXT' for k in KEYS)}, durum_tarihi TEXT)")
    q("DELETE FROM silinen WHERE silinme < ?", ((datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"),))
    q("CREATE TABLE IF NOT EXISTS gorunum (ad TEXT PRIMARY KEY, veri TEXT)")
    q(PARSEL_KONTROL_DDL)  # Parsel Sorgu modülünün sonuçları buraya yazar (iş kaydına dokunmaz)
    for ddl in FEN_DDL:  # Fen Klasörü: parsel işlemleri (tevhit/ifraz) eski -> yeni
        q(ddl)
    for tur, vals in SEED.items():
        if not q("SELECT 1 FROM liste WHERE tur=?", (tur,)):
            for v in vals:
                q("INSERT OR IGNORE INTO liste VALUES (?,?)", (tur, v))
    if not q("SELECT 1 FROM ayar WHERE ad='onay_v2'"):
        for v in ("Tescillendi", "Askıda Kaldı", "İptal"):
            q("INSERT OR IGNORE INTO liste VALUES ('onay',?)", (v,))
        q("INSERT OR REPLACE INTO ayar VALUES ('onay_v2','1')")


def liste(tur):
    return sorted((r[0] for r in q("SELECT deger FROM liste WHERE tur=?", (tur,))), key=tr_sira)


def ayar(ad):
    r = q("SELECT deger FROM ayar WHERE ad=?", (ad,))
    return r[0][0] if r else ""


def open_file(p):
    if os.name == "nt":
        os.startfile(p)
    else:
        subprocess.Popen(["xdg-open", p])


def find_file(folder, no):
    if folder and no:
        for e in EXT:
            for n in (no, no.replace("/", "-")):
                p = os.path.join(folder, n + e)
                if os.path.exists(p):
                    return p
    return None


DATES = {"encumen_tarihi": ".", "karar_tarihi": ".", "makbuz_tarihi": "."}
LISTE_ALAN = {"mahalle": "mahalle", "islem": "islem", "muellif": "muellif", "onay": "onay"}
TARIH_ALANLARI = {"Encümen Tarih": "encumen_tarihi", "Tarih": "karar_tarihi", "Ödeme Makbuz Tarih": "makbuz_tarihi"}


def bugun_str():
    return datetime.date.today().strftime("%d.%m.%Y")


def bekleme_gun(d, bugun):
    """Açık işlerde (arşiv durumları ve boş durum hariç) durumun başlangıcından bu yana geçen gün."""
    if not d["onay"] or arsiv_mi(d["onay"]):
        return ""
    for k in ("durum_tarihi", "makbuz_tarihi", "karar_tarihi", "encumen_tarihi"):
        t = tarih_oku(d.get(k, ""))
        if t:
            return str(max((bugun - t).days, 0))
    return ""


def arsiv_mi(onay):
    return tr_lower((onay or "").strip()).startswith(("tescillendi", "askıda", "iptal"))


def tarih_oku(v):
    try:
        g, a, y = [int(x) for x in re.split(r"[./-]", (v or "").strip())[:3]]
        return datetime.date(y + 2000 if y < 100 else y, a, g)
    except ValueError:
        return None


def tarih_bicim(v):
    """13/10/2026, 13.10.2026, 9.5.23 ... -> 13.10.2026 (anlaşılamayan metne dokunmaz)."""
    v = temiz(v)
    t = tarih_oku(v)
    return t.strftime("%d.%m.%Y") if t else v


def sort_key(k, v):
    v = v.strip()
    if k == "bekleme":
        return (0, int(v) if v.isdigit() else 0, "")
    if k in DATES:
        try:
            t = tarih_oku(v)
            if not t:
                raise ValueError
            return (0, t.toordinal(), "")
        except ValueError:
            return (1, 0, tr_sira(v))
    if k == "alinan_ucret":
        return (0, para(v), "")
    if k in ("karar_no", "makbuz_no", "ada_parsel"):
        m = re.match(r"\d+", v)
        return (0, int(m.group()), tr_sira(v)) if m else (1, 0, tr_sira(v))
    return (0, 0, tr_sira(v))


PARSEL_KONTROL_DDL = """CREATE TABLE IF NOT EXISTS parsel_kontrol (
    work_id INTEGER PRIMARY KEY, parsel_no TEXT, tkgm_mahalle TEXT, durum TEXT, alan TEXT, nitelik TEXT,
    islem_turu TEXT, islem_tarihi TEXT, yeni_parseller TEXT, nihai_aktifler TEXT, aciklama TEXT,
    son_kontrol TEXT, onay_bekliyor INTEGER DEFAULT 0)"""


def parsel_kontrol_oku():
    """{iş_id: sonuç} — Parsel Sorgu'nun bu işe yazdığı en son TKGM sonucu."""
    try:
        satirlar = q("SELECT work_id, durum, islem_turu, islem_tarihi, yeni_parseller, nihai_aktifler, aciklama, alan, nitelik, "
                     "parsel_no, tkgm_mahalle, son_kontrol, onay_bekliyor FROM parsel_kontrol")
    except sqlite3.Error:
        return {}
    kol = ("durum", "islem_turu", "islem_tarihi", "yeni", "nihai", "aciklama", "alan", "nitelik", "parsel_no", "tkgm_mahalle",
           "son_kontrol", "onay")
    return {r[0]: dict(zip(kol, [x if x is not None else "" for x in r[1:]])) for r in satirlar}


def parsel_gosterim(p):
    """Tablo hücreleri: 'Pasif · Tevhit 20.10.2026' (⚠ = onay bekliyor), 'Aktif · 568,54 m²' ve yeni parseller."""
    if not p:
        return {"parsel_durum": "", "parsel_yeni": "", "parsel_onay": ""}
    durum = p["durum"] or ""
    onay = bool(p["onay"]) and durum == "Pasif"
    if durum == "Pasif":
        ek = " ".join(x for x in (p["islem_turu"], p["islem_tarihi"]) if x)
        metin = ("⚠ " if onay else "") + "Pasif" + (f" · {ek}" if ek else "")
    elif durum == "Aktif":
        metin = "Aktif" + (f" · {p['alan']} m²" if p["alan"] else "")
    else:
        metin = durum
    yeni = (p["nihai"] or p["yeni"] or "").replace("; ", ", ")
    return {"parsel_durum": metin, "parsel_yeni": yeni, "parsel_onay": "1" if onay else ""}


_AYRAC = r"(?:\s*(?:[-,;+&]|\bve\b)\s*)"
_ADA_PARSEL_RE = re.compile(r"(?<!\d)(\d+)\s*/\s*(\d+(?:" + _AYRAC + r"\d+(?!\d|\s*/))*)", re.I)


def parselleri_coz(metin):
    """İş kaydındaki ada/parsel yazımından TÜM parselleri çıkarır (tire/virgül ayraçtır, aralık değildir):
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


def parsel_etiket(ada, parsel):
    return str(parsel) if str(ada) in ("0", "") else f"{ada}/{parsel}"


def parsel_ozeti(metin):
    """Formda küçük ipucu: birden çok parsel algılandıysa nasıl okunduğunu gösterir (tek parselde boş: sessiz)."""
    liste = parselleri_coz(metin)
    if len(liste) < 2:
        return ""
    gruplar = {}
    for ada, pr in liste:
        gruplar.setdefault(ada, []).append(pr)
    return "Algılanan: " + "  |  ".join((f"{ada} ada: " if ada != "0" else "ada yok: ") + ", ".join(ps) for ada, ps in gruplar.items())


def parsel_otomatik_onay(pk):
    """İş 'Tescillendi' olduysa bekleyen pasif-parsel uyarısı doğrudan onaylanmış sayılır."""
    bekleyen = [w for w, p in pk.items() if p.get("onay")]
    if not bekleyen:
        return 0
    yer = ",".join("?" * len(bekleyen))
    n = 0
    for i, o in q(f"SELECT id, onay FROM kayit WHERE id IN ({yer})", bekleyen):
        if tr_lower((o or "").strip()).startswith("tescillendi"):
            q("UPDATE parsel_kontrol SET onay_bekliyor=0 WHERE work_id=?", (i,))
            pk[i]["onay"] = 0
            n += 1
    return n


FEN_DDL = [
    """CREATE TABLE IF NOT EXISTS fen_islem (
        id INTEGER PRIMARY KEY AUTOINCREMENT, work_id INTEGER, mahalle TEXT, islem_turu TEXT, islem_tarihi TEXT,
        kaynak TEXT, aciklama TEXT, imza TEXT, olusturma TEXT)""",
    "CREATE TABLE IF NOT EXISTS fen_parsel (islem_id INTEGER, ada TEXT, parsel TEXT, rol TEXT)",
    "CREATE INDEX IF NOT EXISTS fen_parsel_ix ON fen_parsel (ada, parsel)",
]


def fen_kayit_ekle(mahalle, tur, tarih, eski, yeni, kaynak, work_id=None, aciklama="", imza=""):
    con = sqlite3.connect(DB)
    try:
        with con:
            iid = con.execute("INSERT INTO fen_islem (work_id, mahalle, islem_turu, islem_tarihi, kaynak, aciklama, imza, olusturma) "
                              "VALUES (?,?,?,?,?,?,?,?)", (work_id, mahalle, tur, tarih, kaynak, aciklama, imza,
                                                           datetime.datetime.now().isoformat(timespec="seconds"))).lastrowid
            for rol, liste_ in (("eski", eski), ("yeni", yeni)):
                for ada, pr in liste_:
                    con.execute("INSERT INTO fen_parsel VALUES (?,?,?,?)", (iid, ada, pr, rol))
    finally:
        con.close()
    return iid


def fen_sil_kayit(iid):
    q("DELETE FROM fen_parsel WHERE islem_id=?", (iid,))
    q("DELETE FROM fen_islem WHERE id=?", (iid,))


def fen_senkronla():
    """TKGM'den gelen PASİF sonuçları Fen Klasörü'ne işler: eski = iş kaydındaki tüm parseller, yeni = TKGM'deki aktif parseller.
    Değişmeyen kayıtlar yeniden yazılmaz (imza karşılaştırması). Elle eklenen kayıtlara dokunulmaz."""
    pk = parsel_kontrol_oku()
    isler = {i: (mh, ap) for i, mh, ap in q("SELECT id, mahalle, ada_parsel FROM kayit")}
    mevcut = {w: (iid, imza) for iid, w, imza in q("SELECT id, work_id, imza FROM fen_islem WHERE kaynak='TKGM'")}
    n = 0
    for wid in list(mevcut):
        if wid not in pk or pk[wid]["durum"] != "Pasif" or wid not in isler:  # sonuç artık geçerli değil / iş silindi
            fen_sil_kayit(mevcut.pop(wid)[0])
            n += 1
    for wid, p in pk.items():
        if p["durum"] != "Pasif" or wid not in isler:
            continue
        mah, ap = isler[wid]
        eski = parselleri_coz(ap)
        for x in parselleri_coz(p["parsel_no"]):
            if x not in eski:
                eski.append(x)
        yeni_metin = p["nihai"] or p["yeni"]
        yeni = parselleri_coz(yeni_metin)
        if not (yeni or p["islem_turu"] or p["islem_tarihi"]):
            continue
        imza = json.dumps([mah, ap, p["islem_turu"], p["islem_tarihi"], yeni_metin], ensure_ascii=False)
        if wid in mevcut and mevcut[wid][1] == imza:
            continue
        if wid in mevcut:
            fen_sil_kayit(mevcut[wid][0])
        fen_kayit_ekle(mah, p["islem_turu"] or "", p["islem_tarihi"] or "", eski, yeni, "TKGM", wid, p["aciklama"] or "", imza)
        n += 1
    return n


def fen_ara_sorgu(mahalle, ada, parsel):
    """Mahalle/ada/parsel ile arar; parsel ESKİ ya da YENİ olarak geçen tüm fen işlemlerini ('rol' ile) döndürür.
    Ada boşsa ada gözetmez ('0' = adasız parsel). Mahalle boşsa tüm mahalleler."""
    mahalle, ada, parsel = (mahalle or "").strip(), (ada or "").strip(), (parsel or "").strip()
    if not (mahalle or ada or parsel):
        return []
    if ada or parsel:
        kosul, arg = [], []
        if ada:
            kosul.append("ada=?")
            arg.append(ada)
        if parsel:
            kosul.append("parsel=?")
            arg.append(parsel)
        vurgu = q("SELECT DISTINCT islem_id, rol FROM fen_parsel WHERE " + " AND ".join(kosul), arg)
    else:
        vurgu = [(r[0], "") for r in q("SELECT id FROM fen_islem")]
    out = []
    for iid, rol in vurgu:
        i = q("SELECT id, mahalle, islem_turu, islem_tarihi, kaynak, work_id, aciklama FROM fen_islem WHERE id=?", (iid,))
        if not i:
            continue
        i = i[0]
        if mahalle and tr_lower(mahalle) not in tr_lower(i[1] or ""):
            continue
        satirlar = q("SELECT ada, parsel, rol FROM fen_parsel WHERE islem_id=? ORDER BY rowid", (iid,))
        out.append({"id": i[0], "mahalle": i[1] or "", "tur": i[2] or "", "tarih": i[3] or "", "kaynak": i[4] or "",
                    "work_id": i[5], "aciklama": i[6] or "", "rol": rol,
                    "eski": [(a, p) for a, p, r in satirlar if r == "eski"], "yeni": [(a, p) for a, p, r in satirlar if r == "yeni"]})
    out.sort(key=lambda r: (tarih_oku(r["tarih"]) or datetime.date.min, r["id"]), reverse=True)
    return out


class Takvim(tk.Toplevel):
    """Gün / yıl / ay seçimli takvim. Başlığa (örn. "Ekim 2026") tıklayınca yıl, sonra ay seçilir.
    Bugün turuncu halkayla, seçili gün mavi daireyle gösterilir."""
    AYLAR = "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split()
    KISA = "Oca Şub Mar Nis May Haz Tem Ağu Eyl Eki Kas Ara".split()
    GUNLER = "Pzt Sal Çar Per Cum Cmt Paz".split()
    CW, CH, UST = 42, 36, 28  # gün hücresi genişliği, yüksekliği, hafta günü satırının yüksekliği
    BUGUN = "#f59e0b"

    def __init__(s, parent, deger, ayrac, sonuc, x=None, y=None):
        super().__init__(parent)
        s.title("Tarih Seç")
        modern_tasarim.tema_uygula(s, KOYU)
        s.resizable(False, False)
        s.ayrac, s.sonuc = ayrac, sonuc
        s.bugun = datetime.date.today()
        d = tarih_oku(deger)
        if d:
            s.yil, s.ay, s.secili = d.year, d.month, (d.year, d.month, d.day)
        else:
            s.yil, s.ay, s.secili = s.bugun.year, s.bugun.month, None
        s.mod, s.yil_bas, s.hucre = "gun", s.yil - 5, []
        s.hf = ttk.Frame(s)
        s.hf.pack(fill="x", padx=8, pady=(8, 2))
        s.cv = tk.Canvas(s, width=7 * s.CW, height=s.UST + 6 * s.CH, bg=KART, highlightthickness=1,
                         highlightbackground=KENAR)
        s.cv.pack(padx=8, pady=4)
        s.cv.bind("<Button-1>", s._tikla)
        s.cv.bind("<Motion>", s._hover)
        s.cv.bind("<Leave>", lambda e: s.cv.delete("hov"))
        alt = ttk.Frame(s)
        alt.pack(pady=(4, 10))
        ttk.Button(alt, text="Bugün", style="Accent.TButton", command=lambda: s.sec(s.bugun.day, s.bugun.month, s.bugun.year)).pack(side="left", padx=4)
        ttk.Button(alt, text="Temizle", command=lambda: (s.sonuc(""), s.destroy())).pack(side="left", padx=4)
        ttk.Button(alt, text="İptal", command=s.destroy).pack(side="left", padx=4)
        s.bind("<Escape>", lambda e: s.destroy())
        s.ciz()
        if x is not None:
            s.geometry(f"+{x}+{y}")
        s.transient(parent)
        s.grab_set()

    # ---- gezinme
    def kay(s, dy, dm):
        a = s.ay - 1 + dm + 12 * dy
        s.yil += a // 12
        s.ay = a % 12 + 1
        s.ciz()

    def yil_ac(s):
        s.mod, s.yil_bas = "yil", s.yil - 5
        s.ciz()

    def gun_ac(s):
        s.mod = "gun"
        s.ciz()

    def yil_kay(s, d):
        s.yil_bas += d
        s.ciz()

    def yil_deg(s, d):
        s.yil += d
        s.ciz()

    def sec(s, g, a, y):
        s.sonuc(f"{g:02d}{s.ayrac}{a:02d}{s.ayrac}{y}")
        s.destroy()

    # ---- çizim
    def baslik(s, sol, metin, sag, tikla):
        for t, k in sol:
            ttk.Button(s.hf, text=t, width=3, command=k).pack(side="left", padx=1)
        for t, k in reversed(sag):
            ttk.Button(s.hf, text=t, width=3, command=k).pack(side="right", padx=1)
        ttk.Button(s.hf, text=metin, command=tikla).pack(side="left", fill="x", expand=True, padx=4)

    def daire(s, cx, cy, r, **kw):
        return s.cv.create_oval(cx - r, cy - r, cx + r, cy + r, **kw)

    def kutu(s, cx, cy, **kw):
        return s.cv.create_rectangle(cx - 30, cy - 17, cx + 30, cy + 17, **kw)

    def ciz(s):
        s.cv.delete("all")
        s.hucre = []
        for w in s.hf.winfo_children():
            w.destroy()
        if s.mod == "gun":
            s.baslik([("«", lambda: s.kay(-1, 0)), ("‹", lambda: s.kay(0, -1))], f"{s.AYLAR[s.ay - 1]} {s.yil}  ▾",
                     [("›", lambda: s.kay(0, 1)), ("»", lambda: s.kay(1, 0))], s.yil_ac)
            s.ciz_gun()
        elif s.mod == "yil":
            s.baslik([("‹", lambda: s.yil_kay(-12))], f"{s.yil_bas} – {s.yil_bas + 11}", [("›", lambda: s.yil_kay(12))], s.gun_ac)
            s.ciz_yil()
        else:
            s.baslik([("‹", lambda: s.yil_deg(-1))], f"{s.yil}  ▾", [("›", lambda: s.yil_deg(1))], s.yil_ac)
            s.ciz_ay()

    def ciz_gun(s):
        for c, g in enumerate(s.GUNLER):
            s.cv.create_text(c * s.CW + s.CW / 2, s.UST / 2, text=g, fill=SOLUK, font=("Segoe UI", 9, "bold"))
        for r, hafta in enumerate(calendar.monthcalendar(s.yil, s.ay)):
            for c, g in enumerate(hafta):
                if not g:
                    continue
                cx, cy = c * s.CW + s.CW / 2, s.UST + r * s.CH + s.CH / 2
                secili = (s.yil, s.ay, g) == s.secili
                bugun = (s.yil, s.ay, g) == (s.bugun.year, s.bugun.month, s.bugun.day)
                if secili:
                    s.daire(cx, cy, 14, fill=VURGU, outline=VURGU)
                if bugun:
                    s.daire(cx, cy, 16 if secili else 15, outline=s.BUGUN, width=2)
                s.cv.create_text(cx, cy, text=str(g), fill="white" if secili else METIN,
                                 font=("Segoe UI", 10, "bold") if bugun else FONT)
                s.hucre.append((cx - s.CW / 2, cy - s.CH / 2, cx + s.CW / 2, cy + s.CH / 2, ("gun", g, cx, cy, secili)))

    def ciz_izgara(s, adlar, tur, secili_mi, bugun_mu):
        w, h = 7 * s.CW / 4, (s.UST + 6 * s.CH) / 3
        for i, (deger, ad) in enumerate(adlar):
            r, c = divmod(i, 4)
            cx, cy = c * w + w / 2, r * h + h / 2
            sec = secili_mi(deger)
            if sec:
                s.kutu(cx, cy, fill=VURGU, outline=VURGU)
            if bugun_mu(deger):
                s.kutu(cx, cy, outline=s.BUGUN, width=2)
            s.cv.create_text(cx, cy, text=ad, fill="white" if sec else METIN, font=FONT)
            s.hucre.append((c * w, r * h, c * w + w, r * h + h, (tur, deger, cx, cy, sec)))

    def ciz_yil(s):
        s.ciz_izgara([(y, str(y)) for y in range(s.yil_bas, s.yil_bas + 12)], "yil",
                     lambda y: y == s.yil, lambda y: y == s.bugun.year)

    def ciz_ay(s):
        s.ciz_izgara([(i + 1, ad) for i, ad in enumerate(s.KISA)], "ay",
                     lambda m: m == s.ay, lambda m: s.yil == s.bugun.year and m == s.bugun.month)

    # ---- fare
    def bul(s, e):
        for x0, y0, x1, y1, a in s.hucre:
            if x0 <= e.x < x1 and y0 <= e.y < y1:
                return a
        return None

    def _hover(s, e):
        s.cv.delete("hov")
        a = s.bul(e)
        s.cv.configure(cursor="hand2" if a else "")
        if a and not a[4]:
            if a[0] == "gun":
                s.daire(a[2], a[3], 14, fill=TAKV1, outline="", tags="hov")
            else:
                s.kutu(a[2], a[3], fill=TAKV2, outline="", tags="hov")
            s.cv.tag_lower("hov")

    def _tikla(s, e):
        a = s.bul(e)
        if not a:
            return
        if a[0] == "gun":
            s.sec(a[1], s.ay, s.yil)
        elif a[0] == "yil":
            s.yil, s.mod = a[1], "ay"
            s.ciz()
        else:
            s.ay, s.mod = a[1], "gun"
            s.ciz()


class Form(tk.Toplevel):
    KOPYA = ("mahalle", "ada_parsel", "muellif")  # "Satırı çoğalt" ile yalnızca bunlar taşınır

    def __init__(s, app, rid=None, kopya=None):
        super().__init__(app.root)
        s.app, s.rid, s.v = app, rid, {}
        koyu = s.app.koyu_var.get()
        modern_tasarim.tema_uygula(s, koyu)
        baslik = "Yeni Kayıt (Çoğaltılan Satırdan)" if kopya else ("Kayıt Düzenle" if rid else "Yeni İmar & Encümen Kaydı")
        s.title(baslik)
        modern_tasarim.pencere_merkeze_yerlestir(s, 760, 680)
        s.minsize(660, 560)
        modern_tasarim.ozel_baslik(s, baslik, koyu, "T.C. Mustafakemalpaşa Belediyesi• İmar Kayıt Formu")

        govde = ttk.Frame(s, padding=(18, 14))
        govde.pack(fill="both", expand=True)

        kaynak = rid or kopya
        row = q(f"SELECT {','.join(KEYS)} FROM kayit WHERE id=?", (kaynak,))[0] if kaynak else None
        for i, (k, l, t) in enumerate(FIELDS):
            ttk.Label(govde, text=l).grid(row=i, column=0, sticky="e", padx=(6, 10), pady=3)
            s.v[k] = tk.StringVar(value=(row[i] or "") if row and (not kopya or k in s.KOPYA) else "")
            if t and t.startswith("liste:"):
                AramaliCombobox(govde, (lambda tur=t[6:]: liste(tur)), textvariable=s.v[k], width=46).grid(row=i, column=1, sticky="w", pady=3)
            else:
                ttk.Entry(govde, textvariable=s.v[k], width=48).grid(row=i, column=1, sticky="w", pady=3)
            if t == "dosya":
                ttk.Button(govde, text="Dosya Seç", command=lambda k=k: s.pick(k)).grid(row=i, column=2, padx=6, sticky="w")
            if k in DATES:
                ttk.Button(govde, text="Takvim", command=lambda k=k: Takvim(s, s.v[k].get(), DATES[k], s.v[k].set)).grid(row=i, column=2, padx=6, sticky="w")
            if k == "ada_parsel":  # '728/1-2-9-10' gibi yazımlar arka planda ayrı parseller olarak okunur; ipucu yalnızca çoklu parselde görünür
                s.ap_ipucu = ttk.Label(govde, text=parsel_ozeti(s.v[k].get()), foreground=SOLUK, wraplength=250, justify="left")
                s.ap_ipucu.grid(row=i, column=2, sticky="w", padx=6)
                s.v[k].trace_add("write", lambda *a: s.ap_ipucu.config(text=parsel_ozeti(s.v["ada_parsel"].get())))

        alt_bar = ttk.Frame(s, padding=(18, 10))
        alt_bar.pack(fill="x", side="bottom")
        ttk.Button(alt_bar, text="Kaydet", command=s.save, style="Accent.TButton").pack(side="right", padx=6)
        ttk.Button(alt_bar, text="İptal", command=s.destroy).pack(side="right", padx=6)

    def pick(s, k):
        p = dosya_sec_dialog("karar" if k.startswith("karar") else "makbuz")
        if p:
            s.v[k].set(p)

    def save(s):
        vals = [s.v[k].get().strip() for k in KEYS]
        ui = KEYS.index("alinan_ucret")
        vals[ui] = para_bicim(vals[ui])
        for dk in DATES:
            vals[KEYS.index(dk)] = tarih_bicim(vals[KEYS.index(dk)])
        ii = KEYS.index("islem")
        vals[ii] = islem_kanon(vals[ii])
        uy = mukerrer(dict(zip(KEYS, vals)), s.rid)
        if uy and not messagebox.askyesno("Olası mükerrer kayıt", uy + "\n\nYine de kaydedilsin mi?"):
            return
        oi = KEYS.index("onay")
        if s.rid:
            s.app.undo_onceki("Kayıt düzenleme", [s.rid])
            eski = q("SELECT onay FROM kayit WHERE id=?", (s.rid,))[0][0] or ""
            if vals[oi] != eski:
                q("UPDATE kayit SET durum_tarihi=? WHERE id=?", (bugun_str(), s.rid))
            q(f"UPDATE kayit SET {','.join(k + '=?' for k in KEYS)} WHERE id=?", vals + [s.rid])
        else:
            q(f"INSERT INTO kayit ({','.join(KEYS)},durum_tarihi) VALUES ({','.join('?' * (len(KEYS) + 1))})",
              vals + [bugun_str() if vals[oi] else ""])
            s.app.undo_ekle("Yeni kayıt", [q("SELECT MAX(id) FROM kayit")[0][0]])
        for k, t in LISTE_ALAN.items():  # listede olmayan yeni değeri listeye ekle
            v = vals[KEYS.index(k)]  # düzeltilmiş (normalize) değer: yinelenen adlar listeye girmesin
            if v:
                q("INSERT OR IGNORE INTO liste VALUES (?,?)", (t, v))
        s.app.load()
        s.destroy()


class Listeler(tk.Toplevel):
    def __init__(s, app):
        super().__init__(app.root)
        s.app = app
        koyu = s.app.koyu_var.get()
        pal = modern_tasarim.tema_uygula(s, koyu)
        s.title("Seçim Listeleri")
        modern_tasarim.pencere_merkeze_yerlestir(s, 580, 640)
        s.minsize(480, 520)
        modern_tasarim.ozel_baslik(s, "Seçim Listeleri Yönetimi", koyu, "Mahalle, Müellif, İşlem ve Onay Listesi")

        govde = ttk.Frame(s, padding=(18, 14))
        govde.pack(fill="both", expand=True)

        ust = ttk.Frame(govde)
        ust.pack(fill="x", pady=(0, 8))
        ttk.Label(ust, text="Liste Türü:", font=(modern_tasarim.font_ailesi(), 9, "bold")).pack(side="left", padx=(0, 8))
        s.cb = ttk.Combobox(ust, state="readonly", values=list(LT.values()), width=24)
        s.cb.current(0)
        s.cb.pack(side="left")
        s.cb.bind("<<ComboboxSelected>>", lambda e: s.yenile())

        lb_frame = ttk.Frame(govde)
        lb_frame.pack(fill="both", expand=True, pady=4)
        s.lb = tk.Listbox(lb_frame, width=40, height=14, relief="flat", highlightthickness=1,
                          highlightbackground=pal["kenar"], bg=pal["kart"], fg=pal["metin"],
                          selectbackground=pal["vurgu"], selectforeground="#FFFFFF")
        lb_sb = ttk.Scrollbar(lb_frame, orient="vertical", command=s.lb.yview)
        s.lb.configure(yscrollcommand=lb_sb.set)
        lb_sb.pack(side="right", fill="y")
        s.lb.pack(side="left", fill="both", expand=True)

        giris_f = ttk.Frame(govde)
        giris_f.pack(fill="x", pady=(8, 4))
        s.e = tk.StringVar()
        ttk.Entry(giris_f, textvariable=s.e, width=32).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(giris_f, text="Ekle", command=s.ekle, style="Accent.TButton").pack(side="left")

        btn_f = ttk.Frame(govde)
        btn_f.pack(fill="x", pady=6)
        ttk.Button(btn_f, text="Seçileni Sil", command=s.sil, style="Danger.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(btn_f, text="Toplu Ekle", command=s.toplu).pack(side="left", padx=6)
        ttk.Button(btn_f, text="Benzer Adları Birleştir", command=s.birlestir).pack(side="right")
        s.yenile()

    def kod(s):
        return [k for k, v in LT.items() if v == s.cb.get()][0]

    def yenile(s):
        s.lb.delete(0, "end")
        for v in liste(s.kod()):
            s.lb.insert("end", v)

    def ekle(s):
        if s.e.get().strip():
            q("INSERT OR IGNORE INTO liste VALUES (?,?)", (s.kod(), s.e.get().strip()))
            s.e.set("")
            s.yenile()

    def birlestir(s):
        tur = s.kod()  # liste türü adı, kayıt tablosundaki sütun adıyla aynı (mahalle, muellif, islem, onay)
        g = benzer_gruplar(tur, tur, tur == "islem")
        if not g:
            messagebox.showinfo("Birleştir", "Birleştirilecek benzer ad bulunamadı.")
            return
        if messagebox.askyesno("Benzer adları birleştir", "Şu adlar tek yazıma çevrilecek, kayıtlar da güncellenecek:\n\n"
                               + benzer_ozet(g) + "\n\nDevam edilsin mi?"):
            benzer_uygula(tur, tur, g)
            s.yenile()
            s.app.undo_temizle()
            s.app.load()
            messagebox.showinfo("Tamam", f"{len(g)} grup birleştirildi.")

    def sil(s):
        for i in s.lb.curselection():
            q("DELETE FROM liste WHERE tur=? AND deger=?", (s.kod(), s.lb.get(i)))
        s.yenile()

    def toplu(s):
        w = tk.Toplevel(s)
        koyu = s.app.koyu_var.get()
        pal = modern_tasarim.tema_uygula(w, koyu)
        w.title("Toplu Değer Ekle")
        modern_tasarim.pencere_merkeze_yerlestir(w, 480, 440)
        modern_tasarim.ozel_baslik(w, "Toplu Liste Değeri Ekle", koyu, "Her satıra bir değer yapıştırın")
        govde = ttk.Frame(w, padding=14)
        govde.pack(fill="both", expand=True)
        t = tk.Text(govde, width=40, height=14, bg=pal["kart"], fg=pal["metin"],
                    highlightthickness=1, highlightbackground=pal["kenar"], relief="flat")
        t.pack(fill="both", expand=True, pady=(0, 10))

        def tamam():
            for satir in t.get("1.0", "end").splitlines():
                if satir.strip():
                    q("INSERT OR IGNORE INTO liste VALUES (?,?)", (s.kod(), satir.strip()))
            w.destroy()
            s.yenile()
        alt = ttk.Frame(govde)
        alt.pack(fill="x")
        ttk.Button(alt, text="Listeye Ekle", command=tamam, style="Accent.TButton").pack(side="right", padx=4)
        ttk.Button(alt, text="İptal", command=w.destroy).pack(side="right")


YEDEK_DESEN = re.compile(r"^imar_kayitlari_\d{4}-\d{2}-\d{2}\.db$")
YEDEK_SAKLA = 30


def yedek_klasor():
    return ayar("yedek_klasor") or os.path.join(BASE, "yedekler")


def db_kopyala(kaynak, hedef):
    a, b = sqlite3.connect(kaynak), sqlite3.connect(hedef)
    try:
        a.backup(b)
    finally:
        a.close()
        b.close()


def yedekle(ek=""):
    kl = yedek_klasor()
    os.makedirs(kl, exist_ok=True)
    ad = f"imar_kayitlari_{datetime.date.today():%Y-%m-%d}.db" if not ek else f"imar_kayitlari_{ek}.db"
    yol = os.path.join(kl, ad)
    db_kopyala(DB, yol)
    eski = sorted(f for f in os.listdir(kl) if YEDEK_DESEN.match(f))
    for f in eski[:-YEDEK_SAKLA]:
        os.remove(os.path.join(kl, f))
    return yol


def oto_esles(metin, degerler):
    """Yazılan harflerle eşleşen seçenekler: önce başlayanlar, sonra içinde geçenler (Türkçe harf duyarlı)."""
    n = tr_lower(metin.strip())
    if not n:
        return []
    bas, ic = [], []
    for v in degerler:
        if v == "(Tümü)":
            continue
        k = tr_lower(v)
        (bas if k.startswith(n) else ic if n in k else []).append(v)
    return bas + ic


class AramaliCombobox(ttk.Combobox):
    """Yazdıkça eşleşenleri gösterir. Aşağı/Yukarı ile gezilir, Enter veya tıklama seçer, Esc kapatır."""
    TUS_ATLA = {"Up", "Down", "Return", "KP_Enter", "Escape", "Tab", "ISO_Left_Tab", "Left", "Right", "Home", "End",
                "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock", "Prior", "Next"}

    def __init__(s, master, kaynak, degis=None, tumu=False, **kw):
        super().__init__(master, **kw)
        s.kaynak, s.degis, s.tumu = kaynak, degis, tumu
        s.lb, s._gid = None, None
        s.enter_cb = s.esc_cb = None
        s["values"] = kaynak()
        s.bind("<KeyRelease>", s._tus, add="+")
        s.bind("<Down>", s._asagi)
        s.bind("<Up>", s._yukari)
        s.bind("<Return>", s._enter)
        s.bind("<KP_Enter>", s._enter)
        s.bind("<Escape>", s._esc)
        s.bind("<FocusIn>", s._odak_gir, add="+")
        s.bind("<FocusOut>", s._odak_cik, add="+")
        s.bind("<ButtonRelease-1>", s._tikla_alan, add="+")
        s.bind("<Destroy>", s._yok, add="+")

    def _gorunur(s):
        return s.lb is not None and s.lb.winfo_exists() and s.lb.winfo_ismapped()

    def _gizle(s):
        if s.lb is not None and s.lb.winfo_exists():
            s.lb.place_forget()

    def _goster(s, items, secili=0):
        top = s.winfo_toplevel()
        if s.lb is None or not s.lb.winfo_exists():
            s.lb = tk.Listbox(top, activestyle="none", exportselection=False, takefocus=0, relief="solid", bd=1,
                              highlightthickness=0, selectbackground=VURGU, selectforeground="white", bg=KART, fg=METIN)
            s.lb.bind("<ButtonRelease-1>", s._tikla)
        s.lb.delete(0, "end")
        for v in items:
            s.lb.insert("end", v)
        s.lb.configure(height=min(len(items), 8))
        s.update_idletasks()
        s.lb.place(x=s.winfo_rootx() - top.winfo_rootx(), y=s.winfo_rooty() - top.winfo_rooty() + s.winfo_height(),
                   width=max(s.winfo_width(), 170))
        s.lb.lift()
        if secili is not None and items:
            s.lb.selection_clear(0, "end")
            s.lb.selection_set(secili)
            s.lb.see(secili)

    def tum_goster(s):
        items = [v for v in s.kaynak() if v != "(Tümü)"]
        if items:
            s._goster(items, items.index(s.get()) if s.get() in items else None)

    def _tus(s, e):
        if e.keysym in s.TUS_ATLA:
            return
        if s.degis:  # filtre kutusunda yazdıkça listeyi canlı süz
            if s._gid:
                s.after_cancel(s._gid)
            s._gid = s.after(300, s._degis_cagir)
        m = oto_esles(s.get(), s.kaynak())
        if not m or (len(m) == 1 and tr_lower(m[0]) == tr_lower(s.get().strip())):
            s._gizle()
        else:
            s._goster(m)

    def _degis_cagir(s):
        s._gid = None
        try:
            s.degis()
        except tk.TclError:
            pass

    def _hareket(s, d):
        cur = s.lb.curselection()
        n = max(0, min((cur[0] if cur else -1) + d, s.lb.size() - 1))
        s.lb.selection_clear(0, "end")
        s.lb.selection_set(n)
        s.lb.see(n)

    def _asagi(s, e):
        if s._gorunur():
            s._hareket(1)
            return "break"

    def _yukari(s, e):
        if s._gorunur():
            s._hareket(-1)
            return "break"

    def _sec(s, v):
        s.set(v)
        s._gizle()
        s.icursor("end")
        s.event_generate("<<ComboboxSelected>>")

    def _enter(s, e):
        if s._gorunur():
            cur = s.lb.curselection()
            s._sec(s.lb.get(cur[0] if cur else 0))
            return "break"
        if s.enter_cb:
            s.enter_cb(e)
            return "break"

    def _esc(s, e):
        if s._gorunur():
            s._gizle()
            return "break"
        if s.esc_cb:
            s.esc_cb(e)
            return "break"

    def _tikla(s, e):
        i = s.lb.nearest(e.y)
        if 0 <= i < s.lb.size():
            s._sec(s.lb.get(i))
            s.focus_set()

    def _tikla_alan(s, e):
        if s.tumu and s.get() == "(Tümü)":
            s.select_range(0, "end")

    def _odak_gir(s, e):
        if s.tumu and s.get() == "(Tümü)":
            s.after(1, lambda: s.select_range(0, "end"))

    def _odak_cik(s, e):
        s.after(200, s._odak_kontrol)

    def _odak_kontrol(s):
        try:
            f = s.focus_get()
        except Exception:
            f = None
        if f is not s.lb:
            s._gizle()
            if s.tumu and not s.get().strip():
                s.set("(Tümü)")

    def _yok(s, e):
        if e.widget is s:
            if s._gid:
                s.after_cancel(s._gid)
            try:
                s.lb.destroy()
            except Exception:
                pass


def ad_temizle(v):
    v = re.sub(r"[\u2010-\u2015\u2212]", "-", (v or "").replace("\u00a0", " ").replace("\u200b", ""))
    v = re.sub(r"\s*-\s*", "-", v)
    return re.sub(r"\s+", " ", v).strip()


def ad_anahtar(v, siki):
    k = tr_lower(ad_temizle(v))
    if siki:  # boşluk, tire ve Türkçe harf farkını yok say (tevhit-ifraz = tevhit - ifraz = Tevhit İfraz)
        k = re.sub(r"[\s\-_.]", "", k).translate(str.maketrans("ığüşöç", "igusoc"))
    return k


def benzer_gruplar(tur, kolon, siki):
    kul = {}
    for (v,) in q(f"SELECT {kolon} FROM kayit"):
        if v:
            kul[v] = kul.get(v, 0) + 1
    for v in liste(tur):
        kul.setdefault(v, 0)
    gruplar = {}
    for v, n in kul.items():
        gruplar.setdefault(ad_anahtar(v, siki), []).append((v, n))
    sonuc = []
    for uyeler in gruplar.values():
        formlar = {}
        for v, n in uyeler:
            formlar[ad_temizle(v)] = formlar.get(ad_temizle(v), 0) + n
        rep_ = max(formlar, key=lambda f: (formlar[f], "-" in f, f == tr_lower(f), -len(f)))
        eski = sorted(v for v, _ in uyeler if v != rep_)
        if eski:
            sonuc.append((rep_, eski, sum(n for _, n in uyeler)))
    return sorted(sonuc, key=lambda g: tr_sira(g[0]))


def benzer_uygula(tur, kolon, gruplar):
    con = sqlite3.connect(DB)
    try:
        with con:
            for rep_, eski, _ in gruplar:
                for v in eski:
                    con.execute(f"UPDATE kayit SET {kolon}=? WHERE {kolon}=?", (rep_, v))
                    con.execute("DELETE FROM liste WHERE tur=? AND deger=?", (tur, v))
                con.execute("INSERT OR IGNORE INTO liste VALUES (?,?)", (tur, rep_))
    finally:
        con.close()


def benzer_ozet(gruplar, en_fazla=15):
    sat = ["• " + "  |  ".join(f"“{x}”" for x in eski) + f"  →  “{r}”" for r, eski, _ in gruplar[:en_fazla]]
    if len(gruplar) > en_fazla:
        sat.append(f"... ve {len(gruplar) - en_fazla} grup daha")
    return "\n".join(sat)


def islem_kanon(v):
    """Yeni yazılan işlem adı listedeki benzeriyle aynıysa listedeki yazımı kullanır (yinelenmeyi önler)."""
    v = ad_temizle(v)
    if v:
        k = ad_anahtar(v, True)
        adaylar = [x for x in liste("islem") if ad_anahtar(x, True) == k]
        if adaylar:
            return min(adaylar, key=lambda x: (x != ad_temizle(x), x))  # temiz yazımı tercih et
    return v


def dosya_sec_dialog(tur):
    """Karar ve makbuz (dekont) için ayrı ayrı son seçilen klasörü hatırlar. Dosyayı yüklemez, yolunu döndürür."""
    ad = "Karar" if tur == "karar" else "Makbuz (dekont)"
    ayr = {"title": f"{ad} dosyasını seçin (PDF veya resim)",
           "filetypes": [("PDF ve resimler", "*.pdf *.jpg *.jpeg *.png *.tif *.tiff"), ("Tüm dosyalar", "*.*")]}
    for k in (f"son_{tur}_klasoru", f"{tur}_klasor"):
        d = ayar(k)
        if d and os.path.isdir(d):
            ayr["initialdir"] = d
            break
    p = filedialog.askopenfilename(**ayr)
    if not p:
        return ""
    p = os.path.normpath(p)
    q("INSERT OR REPLACE INTO ayar VALUES (?,?)", (f"son_{tur}_klasoru", os.path.dirname(p)))
    return p


def kayit_sil(ids):
    """Kayıtları silmeden önce 'silinen' tablosuna kopyalar (90 gün saklanır)."""
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c = ",".join(KEYS)
    con = sqlite3.connect(DB)
    try:
        with con:
            for i in ids:
                con.execute(f"INSERT INTO silinen (silinme,{c},durum_tarihi) SELECT ?,{c},durum_tarihi FROM kayit WHERE id=?",
                            (zaman, i))
                con.execute("DELETE FROM kayit WHERE id=?", (i,))
    finally:
        con.close()
    return zaman


def kayit_snapshot(ids):
    """Değişiklikten önce kayıtların tam kopyasını alır (geri al için). Kayıt yoksa None."""
    cols = ["id"] + KEYS + ["durum_tarihi"]
    out = {}
    for i in ids:
        r = q(f"SELECT {','.join(cols)} FROM kayit WHERE id=?", (i,))
        out[i] = dict(zip(cols, r[0])) if r else None
    return out


def undo_uygula(e):
    cols = ["id"] + KEYS + ["durum_tarihi"]
    con = sqlite3.connect(DB)
    try:
        with con:
            for i, r in e["onceki"].items():
                if r is None:  # işlemden önce yoktu (yeni eklenen kayıt): sil
                    con.execute("DELETE FROM kayit WHERE id=?", (i,))
                else:
                    con.execute(f"INSERT OR REPLACE INTO kayit ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                                [r[c] for c in cols])
            if e.get("silinme"):  # silmeyi geri alınca çöp kutusundaki kopyaları da kaldır
                con.execute("DELETE FROM silinen WHERE silinme=?", (e["silinme"],))
    finally:
        con.close()


def kayit_geri(sids):
    c = ",".join(KEYS)
    con = sqlite3.connect(DB)
    try:
        with con:
            for i in sids:
                con.execute(f"INSERT INTO kayit ({c},durum_tarihi) SELECT {c},durum_tarihi FROM silinen WHERE sid=?", (i,))
                con.execute("DELETE FROM silinen WHERE sid=?", (i,))
    finally:
        con.close()


class Silinenler(tk.Toplevel):
    SUTUN = [("silinme", "Silinme"), ("mahalle", "Mahalle"), ("ada_parsel", "Ada/Parsel"), ("islem", "İşlem"),
             ("karar_no", "Karar No"), ("muellif", "Müellif"), ("onay", "Durum"), ("alinan_ucret", "Alınan Ücret")]

    def __init__(s, app):
        super().__init__(app.root)
        s.app = app
        koyu = s.app.koyu_var.get()
        modern_tasarim.tema_uygula(s, koyu)
        s.title("Son Silinenler (Geri Dönüşüm Kutusu)")
        modern_tasarim.pencere_merkeze_yerlestir(s, 1040, 580)
        s.minsize(820, 440)
        modern_tasarim.ozel_baslik(s, "Geri Dönüşüm Kutusu • Silinen Kayıtlar", koyu, "Silinen kayıtlar 90 gün boyunca saklanır")

        govde = ttk.Frame(s, padding=(14, 10))
        govde.pack(fill="both", expand=True)

        kap = ttk.Frame(govde)
        kap.pack(fill="both", expand=True, pady=(0, 8))
        s.tv = ttk.Treeview(kap, columns=[k for k, _ in s.SUTUN], show="headings", selectmode="extended")
        sb = ttk.Scrollbar(kap, orient="vertical", command=s.tv.yview)
        s.tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        s.tv.pack(side="left", fill="both", expand=True)

        for k, ad in s.SUTUN:
            s.tv.heading(k, text=ad)
            s.tv.column(k, width=140 if k == "silinme" else 110)

        alt = ttk.Frame(govde)
        alt.pack(fill="x")
        ttk.Button(alt, text="Geri Getir", style="Accent.TButton", command=s.geri).pack(side="left")
        ttk.Button(alt, text="Kalıcı Sil", style="Danger.TButton", command=s.kalici).pack(side="left", padx=8)
        ttk.Label(alt, text="Ctrl / Shift ile birden çok satır seçebilirsiniz.", style="Sub.TLabel").pack(side="left", padx=10)
        ttk.Button(alt, text="Kapat", command=s.destroy).pack(side="right")
        s.yenile()

    def yenile(s):
        s.tv.delete(*s.tv.get_children())
        for r in q(f"SELECT sid,{','.join(k for k, _ in s.SUTUN)} FROM silinen ORDER BY sid DESC"):
            v = [x or "" for x in r[1:]]
            try:
                v[0] = datetime.datetime.strptime(v[0], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            except ValueError:
                pass
            s.tv.insert("", "end", iid=str(r[0]), values=v)

    def secili(s):
        ids = [int(x) for x in s.tv.selection()]
        if not ids:
            messagebox.showinfo("Uyarı", "Önce bir veya daha fazla satır seçin.")
        return ids

    def geri(s):
        ids = s.secili()
        if ids:
            kayit_geri(ids)
            s.yenile()
            s.app.undo_temizle()
            s.app.load()
            messagebox.showinfo("Tamam", f"{len(ids)} kayıt geri getirildi.")

    def kalici(s):
        ids = s.secili()
        if ids and messagebox.askyesno("Kalıcı sil", f"{len(ids)} kayıt kalıcı olarak silinecek. Emin misiniz?"):
            for i in ids:
                q("DELETE FROM silinen WHERE sid=?", (i,))
            s.yenile()


def toplu_uygula(ids, degerler):
    for i in ids:
        for k, v in degerler.items():
            if k in DATES:
                v = tarih_bicim(v)
            if k == "onay":
                eski = q("SELECT onay FROM kayit WHERE id=?", (i,))[0][0] or ""
                if eski != v:
                    q("UPDATE kayit SET durum_tarihi=? WHERE id=?", (bugun_str(), i))
            q(f"UPDATE kayit SET {k}=? WHERE id=?", (v, i))
    for k, v in degerler.items():
        if k in LISTE_ALAN and v:
            q("INSERT OR IGNORE INTO liste VALUES (?,?)", (LISTE_ALAN[k], v))
    return len(ids)


class TopluGuncelle(tk.Toplevel):
    ALANLAR = ["onay", "encumen_tarihi", "karar_no", "karar_tarihi", "muellif", "makbuz_tarihi", "aciklama"]

    def __init__(s, app, ids):
        super().__init__(app.root)
        s.app, s.ids = app, ids
        koyu = s.app.koyu_var.get()
        modern_tasarim.tema_uygula(s, koyu)
        s.title(f"Toplu Güncelle ({len(ids)} kayıt)")
        modern_tasarim.pencere_merkeze_yerlestir(s, 720, 560)
        s.minsize(620, 480)
        modern_tasarim.ozel_baslik(s, f"Toplu Güncelleme • {len(ids)} Kayıt Seçili", koyu, "Seçili kayıtlarda yalnızca işaretlenen alanlar güncellenir")

        s.sec, s.var = {}, {}
        tur = {f[0]: f[2] for f in FIELDS}

        govde = ttk.Frame(s, padding=(18, 12))
        govde.pack(fill="both", expand=True)

        bilgi = ttk.Label(govde, text=f"{len(ids)} kayıtta yalnızca işaretlediğiniz alanlar değiştirilir.\n"
                                     "(Değer yazınca kutu kendiliğinden işaretlenir; boş bırakıp işaretlerseniz alan temizlenir.)",
                          style="Sub.TLabel", wraplength=660)
        bilgi.grid(row=0, column=0, columnspan=3, padx=4, pady=(0, 10), sticky="w")

        for i, k in enumerate(s.ALANLAR, 1):
            s.sec[k] = tk.BooleanVar(value=False)
            s.var[k] = tk.StringVar()
            ttk.Checkbutton(govde, text=LAB[k], variable=s.sec[k]).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            if tur[k] and tur[k].startswith("liste:"):
                w = AramaliCombobox(govde, (lambda t2=tur[k][6:]: liste(t2)), textvariable=s.var[k], width=32)
            else:
                w = ttk.Entry(govde, textvariable=s.var[k], width=35)
            w.grid(row=i, column=1, padx=6, pady=4, sticky="w")
            s.var[k].trace_add("write", lambda *a, k=k: s.sec[k].set(True))
            if k in DATES:
                ttk.Button(govde, text="Takvim", command=lambda k=k: Takvim(s, s.var[k].get(), DATES[k], s.var[k].set)
                           ).grid(row=i, column=2, padx=6, sticky="w")

        alt_bar = ttk.Frame(s, padding=(18, 10))
        alt_bar.pack(fill="x", side="bottom")
        ttk.Button(alt_bar, text="Değişiklikleri Uygula", style="Accent.TButton", command=s.uygula).pack(side="right", padx=6)
        ttk.Button(alt_bar, text="İptal", command=s.destroy).pack(side="right")

    def uygula(s):
        sec = [k for k in s.ALANLAR if s.sec[k].get()]
        if not sec:
            messagebox.showinfo("Uyarı", "Değiştirilecek en az bir alanı işaretleyin.")
            return
        ozet = "\n".join(f"• {LAB[k]}: {s.var[k].get().strip() or '(boş bırakılacak)'}" for k in sec)
        if not messagebox.askyesno("Toplu güncelle", f"{len(s.ids)} kayıtta şu değişiklikler yapılacak:\n\n{ozet}\n\nDevam edilsin mi?"):
            return
        s.app.undo_onceki(f"Toplu güncelleme ({len(s.ids)} kayıt)", s.ids)
        toplu_uygula(s.ids, {k: s.var[k].get().strip() for k in sec})
        s.app.load()
        s.app.tv.selection_set([str(i) for i in s.ids if s.app.tv.exists(str(i))])
        s.destroy()
        messagebox.showinfo("Tamam", f"{len(s.ids)} kayıt güncellendi.")


class RaporAyar(tk.Toplevel):
    """Raporların üstündeki kurum başlığı / logo ve altındaki imza alanı ayarları."""
    ALANLAR = [("kurum", "Kurum adı"), ("birim", "Birim adı"), ("hazirlayan", "Hazırlayan (ad soyad)"),
               ("hazirlayan_unvan", "Hazırlayan unvanı"), ("onaylayan", "Onaylayan (ad soyad)"),
               ("onaylayan_unvan", "Onaylayan unvanı")]

    def __init__(s, app):
        super().__init__(app.root)
        is_dark = app.koyu_var.get() if hasattr(app, "koyu_var") else KOYU
        modern_tasarim.tema_uygula(s, is_dark)
        s.title("Rapor başlığı ve imza ayarları")
        modern_tasarim.pencere_merkeze_yerlestir(s, 720, 540)
        s.minsize(620, 460)
        modern_tasarim.ozel_baslik(s, "Rapor Başlığı ve İmza Ayarları", is_dark, "Resmi çıktı ve raporlarda yer alacak kurum bilgileri")

        govde = ttk.Frame(s, padding=(18, 14))
        govde.pack(fill="both", expand=True)

        s.v = {}
        for i, (k, ad) in enumerate(s.ALANLAR):
            ttk.Label(govde, text=ad).grid(row=i, column=0, sticky="e", padx=(6, 10), pady=4)
            s.v[k] = tk.StringVar(value=ayar("rapor_" + k))
            ttk.Entry(govde, textvariable=s.v[k], width=48).grid(row=i, column=1, columnspan=2, sticky="w", pady=4)
        n = len(s.ALANLAR)
        ttk.Label(govde, text="Logo (isteğe bağlı)").grid(row=n, column=0, sticky="e", padx=(6, 10), pady=4)
        s.v["logo"] = tk.StringVar(value=ayar("rapor_logo"))
        ttk.Entry(govde, textvariable=s.v["logo"], width=38).grid(row=n, column=1, sticky="w", pady=4)
        ttk.Button(govde, text="Dosya Seç", command=s.logo_sec).grid(row=n, column=2, sticky="w", padx=6)
        s.imza = tk.BooleanVar(value=ayar("rapor_imza") != "0")
        ttk.Checkbutton(govde, text="Raporun altına imza alanı ekle (Hazırlayan / Onaylayan)", variable=s.imza).grid(
            row=n + 1, column=1, columnspan=2, sticky="w", pady=(8, 4))

        alt = ttk.Frame(s, padding=(18, 10))
        alt.pack(fill="x", side="bottom")
        ttk.Button(alt, text="Kaydet", style="Accent.TButton", command=s.kaydet).pack(side="right", padx=6)
        ttk.Button(alt, text="Örnek Önizleme", command=s.onizle).pack(side="right", padx=6)
        ttk.Button(alt, text="Kapat", command=s.destroy).pack(side="left")

    def logo_sec(s):
        p = filedialog.askopenfilename(title="Logo seçin (PNG veya JPG)", filetypes=[("Resim", "*.png *.jpg *.jpeg")])
        if p:
            s.v["logo"].set(os.path.normpath(p))

    def kaydet(s, kapat=True):
        for k, v in s.v.items():
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("rapor_" + k, v.get().strip()))
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("rapor_imza", "1" if s.imza.get() else "0"))
        if kapat:
            s.destroy()

    def onizle(s):
        s.kaydet(kapat=False)
        rapor_ac(rapor_sayfasi("Örnek Rapor", "Önizleme — ayarlarınız bu şekilde görünür", "<p>Rapor içeriği burada yer alır.</p>"))


class FenIslemDialog(tk.Toplevel):
    """Elle fen işlemi: eski ve yeni parseller kendi yazım biçiminizle girilir (örn. 728/1-2-9-10 -> 728/13)."""
    TURLER = ["Tevhit", "İfraz", "Tevhit-İfraz", "Yola terk", "İhdas", "İhdas-Tevhit", "Diğer"]

    def __init__(s, app):
        super().__init__(app.root)
        s.app = app
        is_dark = s.app.koyu_var.get() if hasattr(s.app, "koyu_var") else KOYU
        modern_tasarim.tema_uygula(s, is_dark)
        s.title("Fen işlemi ekle")
        modern_tasarim.pencere_merkeze_yerlestir(s, 700, 540)
        s.minsize(600, 480)
        modern_tasarim.ozel_baslik(s, "Yeni Fen İşlemi Tanımla", is_dark, "Parsel Dönüşüm, Tevhit, İfraz ve Değişiklik Kaydı")

        govde = ttk.Frame(s, padding=(18, 14))
        govde.pack(fill="both", expand=True)

        s.v = {k: tk.StringVar() for k in ("mahalle", "tur", "tarih", "eski", "yeni", "not")}
        ttk.Label(govde, text="Mahalle").grid(row=0, column=0, sticky="e", padx=(6, 10), pady=5)
        AramaliCombobox(govde, lambda: liste("mahalle"), textvariable=s.v["mahalle"], width=34).grid(row=0, column=1, sticky="w")
        ttk.Label(govde, text="İşlem türü").grid(row=1, column=0, sticky="e", padx=(6, 10), pady=5)
        ttk.Combobox(govde, textvariable=s.v["tur"], values=s.TURLER, width=34).grid(row=1, column=1, sticky="w")
        ttk.Label(govde, text="İşlem tarihi").grid(row=2, column=0, sticky="e", padx=(6, 10), pady=5)
        ttk.Entry(govde, textvariable=s.v["tarih"], width=36).grid(row=2, column=1, sticky="w")
        ttk.Button(govde, text="Takvim", command=lambda: Takvim(s, s.v["tarih"].get(), ".", s.v["tarih"].set)).grid(row=2, column=2, padx=6)
        s.ipucu = {}
        for r, (k, ad) in enumerate((("eski", "Eski parseller"), ("yeni", "Yeni parseller")), 3):
            ttk.Label(govde, text=ad).grid(row=r * 2 - 2, column=0, sticky="e", padx=(6, 10), pady=(5, 0))
            ttk.Entry(govde, textvariable=s.v[k], width=36).grid(row=r * 2 - 2, column=1, sticky="w", pady=(5, 0))
            s.ipucu[k] = ttk.Label(govde, text="", foreground=SOLUK)
            s.ipucu[k].grid(row=r * 2 - 1, column=1, sticky="w")
            s.v[k].trace_add("write", lambda *a, k=k: s.ipucu[k].config(text=s.oku(k)))
        ttk.Label(govde, text="Açıklama").grid(row=7, column=0, sticky="e", padx=(6, 10), pady=5)
        ttk.Entry(govde, textvariable=s.v["not"], width=36).grid(row=7, column=1, sticky="w")

        alt = ttk.Frame(s, padding=(18, 10))
        alt.pack(fill="x", side="bottom")
        ttk.Button(alt, text="Kaydet", style="Accent.TButton", command=s.kaydet).pack(side="right", padx=6)
        ttk.Button(alt, text="İptal", command=s.destroy).pack(side="right")

    def oku(s, k):
        o = parsel_ozeti(s.v[k].get())
        return o or ("" if not parselleri_coz(s.v[k].get()) else "Algılanan: " + ", ".join(parsel_etiket(a, p) for a, p in parselleri_coz(s.v[k].get())))

    def kaydet(s):
        mah = s.v["mahalle"].get().strip()
        eski, yeni = parselleri_coz(s.v["eski"].get()), parselleri_coz(s.v["yeni"].get())
        if not mah or not (eski or yeni):
            messagebox.showwarning("Eksik bilgi", "Mahalle ile eski ve/veya yeni parsel yazılmalı.", parent=s)
            return
        fen_kayit_ekle(mah, s.v["tur"].get().strip(), tarih_bicim(s.v["tarih"].get()), eski, yeni, "Elle", None, s.v["not"].get().strip())
        q("INSERT OR IGNORE INTO liste VALUES ('mahalle',?)", (mah,))
        if any(s.app.fen_son):
            s.app.fen_ara()
        s.destroy()


class TarihAraligi:
    def __init__(s, parent, degis):
        s.degis = degis
        s.f = ttk.Frame(parent)
        s.f.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(s.f, text="Tarih aralığı:").pack(side="left", padx=(8, 2))
        s.alan = ttk.Combobox(s.f, state="readonly", width=18, values=list(TARIH_ALANLARI))
        s.alan.set("Encümen Tarih")
        s.alan.pack(side="left")
        s.alan.bind("<<ComboboxSelected>>", lambda e: s.degis())
        s.bas, s.bit = tk.StringVar(), tk.StringVar()
        s.preset = ""
        for ad, var in (("Başlangıç", s.bas), ("Bitiş", s.bit)):
            ttk.Label(s.f, text=ad + ":").pack(side="left", padx=(8, 2))
            en = ttk.Entry(s.f, textvariable=var, width=11, state="readonly")
            en.pack(side="left")
            en.bind("<Button-1>", lambda ev, var=var: Takvim(s.f.winfo_toplevel(), var.get(), ".",
                                                              lambda v: (var.set(v), setattr(s, "preset", ""), s.degis()), ev.x_root, ev.y_root))
        s.hz = ttk.Combobox(s.f, state="readonly", width=14,
                            values=["Bu ay", "Geçen ay", "Son 30 gün", "Bu yıl", "Aralığı temizle"])
        s.hz.pack(side="left", padx=10)
        s.hz.set("Hızlı seç")
        s.hz.bind("<<ComboboxSelected>>", lambda e: s.hizli(s.hz.get()))

    def hizli(s, secim):
        s.preset = secim if secim in ("Bu ay", "Geçen ay", "Son 30 gün", "Bu yıl") else ""
        bg = datetime.date.today()
        if secim == "Bu ay":
            b, e = bg.replace(day=1), bg.replace(day=calendar.monthrange(bg.year, bg.month)[1])
        elif secim == "Geçen ay":
            e = bg.replace(day=1) - datetime.timedelta(days=1)
            b = e.replace(day=1)
        elif secim == "Son 30 gün":
            b, e = bg - datetime.timedelta(days=30), bg
        elif secim == "Bu yıl":
            b, e = bg.replace(month=1, day=1), bg.replace(month=12, day=31)
        else:
            b = e = None
        s.bas.set(b.strftime("%d.%m.%Y") if b else "")
        s.bit.set(e.strftime("%d.%m.%Y") if e else "")
        s.hz.set("Hızlı seç")
        s.degis()

    def temizle(s):
        s.preset = ""
        s.bas.set("")
        s.bit.set("")

    def uygun(s, d):
        b, e = tarih_oku(s.bas.get()), tarih_oku(s.bit.get())
        if b or e:
            t = tarih_oku(d[TARIH_ALANLARI[s.alan.get()]])
            if not t or (b and t < b) or (e and t > e):
                return False
        return True


class ListeFiltreleri:
    ALANLAR = [("islem", "İşlem"), ("muellif", "Müellif"), ("mahalle", "Mahalle"), ("onay", "Durum")]

    def __init__(s, parent, degis):
        s.cb, s.vals = {}, {}
        for k, ad in s.ALANLAR:
            ttk.Label(parent, text=ad + ":").pack(side="left", padx=(8, 2))
            cb = AramaliCombobox(parent, (lambda k=k: ["(Tümü)"] + liste(LISTE_ALAN[k])), degis=degis, tumu=True, width=18)
            cb.set("(Tümü)")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: degis())
            s.cb[k] = cb

    def yenile(s):
        for k, cb in s.cb.items():
            v = liste(LISTE_ALAN[k])
            s.vals[k] = set(v)
            cb["values"] = ["(Tümü)"] + v

    def temizle(s):
        for cb in s.cb.values():
            cb.set("(Tümü)")

    def aktif(s, k):
        return s.cb[k].get().strip() not in ("", "(Tümü)")

    def uygun(s, d):
        """Listeden seçilen değer birebir eşleşir; elle yazılan kısmi metin 'içinde geçen' olarak aranır."""
        for k, cb in s.cb.items():
            v = cb.get().strip()
            if v in ("", "(Tümü)"):
                continue
            if v in s.vals.get(k, ()):
                if d[k] != v:
                    return False
            elif tr_lower(v) not in tr_lower(d[k]):
                return False
        return True


RAPOR_CSS = """
@page { size: A4 landscape; margin: 12mm; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #111; margin: 16px; }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 14px; margin: 18px 0 6px; page-break-after: avoid; }
.alt { color: #555; font-size: 11px; margin-bottom: 12px; }
.soluk { color: #777; font-weight: normal; }
table { border-collapse: collapse; width: 100%; font-size: 10.5px; }
table.dar { width: auto; min-width: 420px; }
th { background: #e8edf6; text-align: left; border: 1px solid #b8c0cf; padding: 4px 6px; }
td { border: 1px solid #cdd3dd; padding: 3px 6px; vertical-align: top; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
tfoot td { font-weight: bold; background: #f1f3f7; }
.sag { text-align: right; white-space: nowrap; }
.yazdir { position: fixed; top: 10px; right: 14px; padding: 8px 14px; background: #2563eb; color: #fff;
          border: 0; border-radius: 6px; font-size: 13px; cursor: pointer; }
.kurum { display: flex; align-items: center; gap: 14px; border-bottom: 2px solid #333; padding-bottom: 8px; margin-bottom: 12px; }
.logo { height: 58px; }
.k1 { font-weight: 700; font-size: 15px; }
.k2 { font-size: 12px; color: #444; }
.imza { display: flex; justify-content: space-around; gap: 40px; margin-top: 38px; page-break-inside: avoid; }
.imza > div { min-width: 230px; text-align: center; font-size: 12px; }
.imza .cizgi { border-top: 1px solid #333; margin-top: 52px; padding-top: 4px; }
@media print { .yazdir { display: none; } body { margin: 0; } }
"""
RAPOR_KOLON = [("mahalle", "Mahalle"), ("ada_parsel", "Ada/Parsel"), ("islem", "İşlem"),
               ("encumen_tarihi", "Encümen Tarih"), ("karar_no", "Karar No"), ("karar_tarihi", "Tarih"),
               ("alinan_ucret", "Alınan Ücret"), ("muellif", "Müellif"), ("onay", "Durum"),
               ("makbuz_tarihi", "Makbuz Tarih"), ("makbuz_no", "Makbuz No"), ("bekleme", "Bekleme (gün)"),
               ("parsel_durum", "Parsel durumu"), ("aciklama", "Açıklama")]


RAPOR_ANAHTAR = ("kurum", "birim", "logo", "hazirlayan", "hazirlayan_unvan", "onaylayan", "onaylayan_unvan", "imza")


def rapor_logo_html(yol):
    try:
        if yol and os.path.isfile(yol) and os.path.getsize(yol) < 2_000_000:
            mime = "image/png" if yol.lower().endswith(".png") else "image/jpeg"
            with open(yol, "rb") as f:
                return f"<img class='logo' src='data:{mime};base64,{base64.b64encode(f.read()).decode()}'>"
    except OSError:
        pass
    return ""


def rapor_ust():
    a = {k: ayar("rapor_" + k) for k in RAPOR_ANAHTAR}
    logo = rapor_logo_html(a["logo"])
    if not (a["kurum"] or a["birim"] or logo):
        return ""
    return ("<div class='kurum'>" + logo + "<div><div class='k1'>" + hesc(a["kurum"]) + "</div><div class='k2'>"
            + hesc(a["birim"]) + "</div></div></div>")


def rapor_alt():
    a = {k: ayar("rapor_" + k) for k in RAPOR_ANAHTAR}
    if a["imza"] == "0":
        return ""
    kutu = lambda baslik, ad, unvan: (f"<div><b>{baslik}</b><div class='cizgi'>{hesc(ad) or '&nbsp;'}"
                                       f"<br>{hesc(unvan) or '&nbsp;'}</div></div>")
    return ("<div class='imza'>" + kutu("Hazırlayan", a["hazirlayan"], a["hazirlayan_unvan"])
            + kutu("Onaylayan", a["onaylayan"], a["onaylayan_unvan"]) + "</div>")


def rapor_sayfasi(baslik, alt, govde):
    return ("<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>" + hesc(baslik) + "</title><style>"
            + RAPOR_CSS + "</style></head><body><button class='yazdir' onclick='window.print()'>Yazdır / PDF olarak kaydet</button>"
            + rapor_ust() + "<h1>" + hesc(baslik) + "</h1><div class='alt'>" + hesc(alt) + "</div>" + govde + rapor_alt() + "</body></html>")


def rapor_ac(html_metin):
    yol = os.path.join(tempfile.gettempdir(), f"imar_rapor_{datetime.datetime.now():%Y%m%d_%H%M%S}.html")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(html_metin)
    webbrowser.open(pathlib.Path(yol).as_uri())
    return yol


def liste_html(satirlar):
    bas = "<tr><th>Sıra</th>" + "".join(f"<th>{hesc(ad)}</th>" for _, ad in RAPOR_KOLON) + "</tr>"
    govde, toplam = [], 0.0
    for n, d in enumerate(satirlar, 1):
        toplam += para(d["alinan_ucret"])
        renk = DURUM_RENK.get(d["onay"])
        stil = f" style='background:{renk}'" if renk else ""
        hucre = "".join(f"<td{' class=sag' if k == 'alinan_ucret' else ''}>{hesc(d[k])}</td>" for k, _ in RAPOR_KOLON)
        govde.append(f"<tr{stil}><td>{n}</td>{hucre}</tr>")
    fi = [k for k, _ in RAPOR_KOLON].index("alinan_ucret")
    alt = (f"<tr><td colspan='{fi + 1}' class='sag'>Toplam ({len(satirlar)} kayıt)</td>"
           f"<td class='sag'>{para_yaz(toplam)}</td><td colspan='{len(RAPOR_KOLON) - fi - 1}'></td></tr>")
    return "<table><thead>" + bas + "</thead><tbody>" + "".join(govde) + "</tbody><tfoot>" + alt + "</tfoot></table>"


def muellif_html(satirlar):
    dk = ["mahalle", "ada_parsel", "islem", "encumen_tarihi", "karar_no", "makbuz_tarihi", "makbuz_no", "onay", "alinan_ucret"]
    grup = {}
    for d in satirlar:
        grup.setdefault(d["muellif"] or "(Belirtilmemiş)", []).append(d)
    top = {m: sum(para(x["alinan_ucret"]) for x in l) for m, l in grup.items()}
    sira = sorted(grup, key=lambda m: (-top[m], tr_sira(m)))
    o = ["<h2>Özet</h2><table class='dar'><thead><tr><th>Müellif</th><th>İş sayısı</th><th>Toplam harç</th></tr></thead><tbody>"]
    for m in sira:
        o.append(f"<tr><td>{hesc(m)}</td><td class='sag'>{len(grup[m])}</td><td class='sag'>{para_yaz(top[m])}</td></tr>")
    o.append(f"</tbody><tfoot><tr><td>Genel toplam</td><td class='sag'>{len(satirlar)}</td>"
             f"<td class='sag'>{para_yaz(sum(top.values()))}</td></tr></tfoot></table>")
    for m in sira:
        satir = []
        for n, d in enumerate(grup[m], 1):
            satir.append(f"<tr><td>{n}</td>" + "".join(
                f"<td{' class=sag' if k == 'alinan_ucret' else ''}>{hesc(d[k])}</td>" for k in dk) + "</tr>")
        bas = "<tr><th>Sıra</th>" + "".join(f"<th>{hesc(LAB[k])}</th>" for k in dk) + "</tr>"
        o.append(f"<h2>{hesc(m)} <span class='soluk'>({len(grup[m])} iş)</span></h2><table><thead>{bas}</thead><tbody>"
                 + "".join(satir) + f"</tbody><tfoot><tr><td colspan='{len(dk)}' class='sag'>{hesc(m)} toplamı</td>"
                 f"<td class='sag'>{para_yaz(top[m])}</td></tr></tfoot></table>")
    return "".join(o)


_DOSYA_CACHE = {}
DOSYA_TTL = 30  # sn


def dosya_cache_temizle():
    _DOSYA_CACHE.clear()


def _listele(dizin):
    z = time.time()
    e = _DOSYA_CACHE.get(dizin)
    if e and z - e[0] < DOSYA_TTL:
        return e[1]
    try:
        v = os.listdir(dizin)
    except OSError:
        v = None  # klasör ulaşılamıyor
    _DOSYA_CACHE[dizin] = (z, v)
    return v


def dosya_indeksi(klasor):
    if not klasor:
        return set()  # otomatik klasör tanımlı değil: numaraya göre eşleşme yok
    v = _listele(klasor)
    return None if v is None else {os.path.splitext(f)[0].lower() for f in v if f.lower().endswith(EXT)}


def dizin_dosyalari(dizin, onbellek):
    if dizin not in onbellek:
        v = _listele(dizin)
        onbellek[dizin] = None if v is None else {f.lower() for f in v}
    return onbellek[dizin]


def dosya_isaret(tur, d, idx, onbellek=None):
    no, dosya = d[tur + "_no"], d[tur + "_dosya"]
    if not no and not dosya:
        return ""
    if dosya:  # elle seçilen yol: klasör başına tek kez listelenir (ağ yavaşlığına karşı)
        lst = dizin_dosyalari(os.path.dirname(dosya), {} if onbellek is None else onbellek)
        if lst is None:
            return "?"
        if os.path.basename(dosya).lower() in lst:
            return "✓"
    if idx is None:
        return "?" if no else "✗"
    if no and (no.lower() in idx or no.replace("/", "-").lower() in idx):
        return "✓"
    return "✗"


def mukerrer(d, rid):
    if not d["mahalle"] and not d["ada_parsel"] and not d["makbuz_no"]:
        return ""
    for r in q(f"SELECT id,{','.join(KEYS)} FROM kayit"):
        if r[0] == rid:
            continue
        o = dict(zip(KEYS, [x or "" for x in r[1:]]))
        tanim = f"{o['mahalle']} {o['ada_parsel']} - {o['islem']}"
        if d["makbuz_no"] and tr_lower(o["makbuz_no"].strip()) == tr_lower(d["makbuz_no"]):
            return f"Makbuz no {d['makbuz_no']} başka bir kayıtta da var:\n{tanim}"
        if d["mahalle"] and all(tr_lower(o[k].strip()) == tr_lower(d[k]) for k in ("mahalle", "ada_parsel", "islem")) \
                and o["encumen_tarihi"].strip() == d["encumen_tarihi"]:
            return (f"Aynı mahalle, ada/parsel, işlem ve encümen tarihiyle bir kayıt zaten var:\n{tanim}"
                    f" (Karar No: {o['karar_no'] or '-'})")
    return ""


TEMA_ACIK = {
    "BG": "#F1F5F9", "KART": "#FFFFFF", "VURGU": "#2563EB", "VURGU_K": "#1D4ED8", "METIN": "#0F172A",
    "SOLUK": "#64748B", "KENAR": "#CBD5E1", "BASLIK": "#E2E8F0", "HOV": "#DBEAFE", "BAS": "#BFDBFE",
    "SEC": "#BFDBFE", "SB": "#CBD5E1", "SBH": "#94A3B8", "TEHL": "#FEE2E2", "KIRMIZI": "#DC2626",
    "BHOV": "#DBEAFE", "TAKV1": "#DBEAFE", "TAKV2": "#EFF6FF",
    "FEN_ESKI": "#B45309", "FEN_YENI": "#15803D"
}
TEMA_KOYU = {
    "BG": "#0B1120", "KART": "#1E293B", "VURGU": "#3B82F6", "VURGU_K": "#2563EB", "METIN": "#F8FAFC",
    "SOLUK": "#94A3B8", "KENAR": "#334155", "BASLIK": "#334155", "HOV": "#1E293B", "BAS": "#1E3A8A",
    "SEC": "#1E3A8A", "SB": "#475569", "SBH": "#64748B", "TEHL": "#451A1A", "KIRMIZI": "#EF4444",
    "BHOV": "#334155", "TAKV1": "#1E3A8A", "TAKV2": "#243B6B",
    "FEN_ESKI": "#FBBF24", "FEN_YENI": "#4ADE80"
}
# Ekrandaki durum renkleri (raporlar/yazdırma her zaman açık DURUM_RENK'i kullanır)
DURUM_UI_ACIK = dict(DURUM_RENK)
DURUM_UI_KOYU = {"Tescilde Bekliyor": "#1d4a2e", "Ödeme Bekleniyor": "#5a4a12", "Encümene Girdi": "#1e3a6b",
                 "Encümene Yazıldı": "#5c3a17", "Görüş Soruldu": "#432a5e", "Tescillendi": "#14504a",
                 "Askıda Kaldı": "#3a3f4a", "İptal": "#5e2424"}
DURUM_UI = dict(DURUM_RENK)
KOYU, TABLO_PUNTO = False, 10
SUTUN_AD = {"karar_ok": "Karar Dosyası", "makbuz_ok": "Makbuz Dosyası", "parsel_durum": "Parsel durumu (TKGM)",
           "parsel_yeni": "Yeni parseller (TKGM)"}
FONT = ("Segoe UI", 10)


def renk_ata(koyu):
    """Renk adlarını (BG, KART, METIN, ...) açık/koyu palete göre modül düzeyinde günceller."""
    globals().update(TEMA_KOYU if koyu else TEMA_ACIK)
    globals()["KOYU"] = bool(koyu)
    DURUM_UI.update(DURUM_UI_KOYU if koyu else DURUM_UI_ACIK)


def punto_ata(n):
    global TABLO_PUNTO
    TABLO_PUNTO = max(8, min(20, int(n)))


renk_ata(False)
RENK = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#64748b"]


def tema_kur(root):
    modern_tasarim.tema_uygula(root, KOYU)


KART_RENK = {"acik": "mavi", "encumen": "yesil", "gecik": "kirmizi", "harc": "turuncu", "parsel": "mor"}


DONEMLER = ["Son 12 ay", "Son 24 ay", "Bu yıl", "Geçen yıl"]


def aylik_seri(satirlar, donem, bugun):
    """Aylık iş sayısı (encümen tarihine göre) ve tahsil edilen harç (ödeme makbuz tarihine göre)."""
    if donem in ("Bu yıl", "Geçen yıl"):
        yil = bugun.year - (1 if donem == "Geçen yıl" else 0)
        aylar = [(yil, m) for m in range(1, 13)]
    else:
        aylar, y, m = [], bugun.year, bugun.month
        for _ in range(24 if donem == "Son 24 ay" else 12):
            aylar.append((y, m))
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        aylar.reverse()
    idx = {a: i for i, a in enumerate(aylar)}
    isl, harc = [0] * len(aylar), [0.0] * len(aylar)
    for d in satirlar:
        t = tarih_oku(d["encumen_tarihi"])
        if t and (t.year, t.month) in idx:
            isl[idx[(t.year, t.month)]] += 1
        t = tarih_oku(d["makbuz_tarihi"])
        if t and (t.year, t.month) in idx:
            harc[idx[(t.year, t.month)]] += para(d["alinan_ucret"])
    return aylar, isl, harc


def kisa_para(v):
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}".replace(".", ",") + " Mn"
    if v >= 1000:
        return f"{v / 1000:.0f} B"
    return f"{v:.0f}"


def guzel_ust(mx):
    """Eksen üst sınırı için yuvarlak bir sayı (1, 2, 2,5, 5 x 10^n)."""
    if mx <= 0:
        return 1
    us = 10 ** (len(str(int(mx))) - 1) if mx >= 1 else 1
    for k in (1, 2, 2.5, 5, 10):
        if k * us >= mx:
            return k * us
    return 10 * us


def dikey_bar(c, baslik, aylar, deger, fmt, renk):
    c.delete("all")
    w, h = c.winfo_width(), c.winfo_height()
    if w < 140 or h < 110:
        return
    c.create_text(12, 16, anchor="w", text=baslik, font=("Segoe UI", 11, "bold"), fill=METIN)
    sol, sag, ust, alt = 52, 14, 40, 44
    gw, gh = w - sol - sag, h - ust - alt
    ust_sinir = guzel_ust(max(deger) if deger else 0)
    for i in range(5):  # yatay kılavuz çizgileri ve eksen değerleri
        y = ust + gh * (1 - i / 4)
        c.create_line(sol, y, w - sag, y, fill=KENAR)
        c.create_text(sol - 6, y, anchor="e", text=fmt(ust_sinir * i / 4), fill=SOLUK, font=("Segoe UI", 8))
    n = max(len(deger), 1)
    bw = gw / n
    cubuk = bw * 0.62
    bugun = datetime.date.today()
    for i, (a, v) in enumerate(zip(aylar, deger)):
        x0 = sol + i * bw + (bw - cubuk) / 2
        y0 = ust + gh * (1 - v / ust_sinir)
        if v > 0:
            c.create_rectangle(x0, y0, x0 + cubuk, ust + gh, fill=renk, outline="")
            if bw >= 34:
                c.create_text(x0 + cubuk / 2, y0 - 8, text=fmt(v), fill=SOLUK, font=("Segoe UI", 8))
        if bw >= 34 or i % 2 == 0 or i == n - 1:
            ad = Takvim.KISA[a[1] - 1]
            bu_ay = a == (bugun.year, bugun.month)
            c.create_text(x0 + cubuk / 2, ust + gh + 12, text=ad, font=("Segoe UI", 8, "bold" if bu_ay else "normal"),
                          fill="#f59e0b" if bu_ay else METIN)
            if i == 0 or a[1] == 1:
                c.create_text(x0 + cubuk / 2, ust + gh + 27, text=str(a[0]), fill=SOLUK, font=("Segoe UI", 8))
    c.create_line(sol, ust + gh, w - sag, ust + gh, fill=SOLUK)


def yatay_bar(c, baslik, veri, fmt, sol=140, maks=20):
    c.delete("all")
    w, h = c.winfo_width(), c.winfo_height()
    if w < 80 or h < 60:
        return
    c.create_text(12, 16, anchor="w", text=baslik, font=("Segoe UI", 11, "bold"), fill=METIN)
    if not veri:
        c.create_text(w / 2, h / 2, text="Veri yok", fill="#888")
        return
    mx = max(v for _, v in veri) or 1
    sag, ust = 95, 32
    bh = min(28, (h - ust - 8) / len(veri))
    for i, (ad, v) in enumerate(veri):
        y = ust + i * bh
        uz = max((w - sol - sag) * v / mx, 1)
        c.create_text(sol - 6, y + bh / 2, anchor="e", text=ad[:maks], fill=METIN)
        c.create_rectangle(sol, y + 2, sol + uz, y + bh - 2, fill=RENK[0], width=0)
        c.create_text(sol + uz + 5, y + bh / 2, anchor="w", text=fmt(v), fill=SOLUK)


def pasta(c, baslik, veri):
    c.delete("all")
    w, h = c.winfo_width(), c.winfo_height()
    if w < 80 or h < 80:
        return
    c.create_text(12, 16, anchor="w", text=baslik, font=("Segoe UI", 11, "bold"), fill=METIN)
    if not veri:
        c.create_text(w / 2, h / 2, text="Veri yok", fill="#888")
        return
    if len(veri) > 8:
        veri = veri[:8] + [("Diğer", sum(v for _, v in veri[8:]))]
    toplam = sum(v for _, v in veri) or 1
    yan = w > h * 1.15  # geniş alanda pasta solda, açıklama sağda
    if yan:
        r = max(20, min((h - 56) / 2, w * 0.3))
        cx, y0 = 24 + r, 40
    else:
        r = max(20, min((w - 40) / 2, (h - 60 - len(veri) * 20) / 2))
        cx, y0 = w / 2, 36
    kutu = (cx - r, y0, cx + r, y0 + 2 * r)
    if len(veri) == 1:
        c.create_oval(*kutu, fill=RENK[0], outline="white")
    else:
        bas = 90
        for i, (_, v) in enumerate(veri):
            ext = -360 * v / toplam
            c.create_arc(*kutu, start=bas, extent=ext, fill=RENK[i % len(RENK)], outline="white")
            bas += ext
    lx, ly = (cx + r + 30, 44) if yan else (20, y0 + 2 * r + 16)
    for i, (ad, v) in enumerate(veri):
        y = ly + i * 20
        c.create_rectangle(lx, y, lx + 12, y + 12, fill=RENK[i % len(RENK)], width=0)
        c.create_text(lx + 20, y + 6, anchor="w", text=f"{ad[:22]}: {v} iş (%{100 * v / toplam:.0f})", fill=METIN)


class App:
    def __init__(s):
        s.root = tk.Tk()
        s.root.title("İmar Uygulamaları - Encümen Karar ve Makbuz Kayıtları")
        modern_tasarim.pencere_merkeze_yerlestir(s.root, 1420, 780)
        s.edit, s.son, s.siralama = None, None, None
        s.gizli = 0
        s.gecik_say = 0
        s.undo = []
        s.pk = {}
        renk_ata(ayar("tema") == "koyu")
        try:
            punto_ata(int(ayar("yazi_boyut") or 10))
        except ValueError:
            pass
        s.koyu_var = tk.BooleanVar(value=KOYU)
        s.rozet_var = tk.BooleanVar(value=ayar("rozet") != "0")
        s._rz_hucre, s._rz_cizgi, s._rz_hdr, s._rid = [], [], 34, None
        s.detay_var = tk.BooleanVar(value=False)
        s.detay_acik = False
        s.sutun_var = {k: tk.BooleanVar(value=True) for k in TV_COLS[1:]}
        s.sutun_goster = list(TV_COLS)
        tema_kur(s.root)
        modern_tasarim.tema_uygula(s.root, KOYU)
        s.simge_koy()
        s.root.minsize(1000, 560)
      
        s.baslik_cubuk = modern_tasarim.ozel_baslik(
            s.root,
            "İMAR UYGULAMALARI  |  ENCÜMEN KARAR VE MAKBUZ KAYITLARI",
            KOYU,
            kurumsal_alt="T.C. Mustafakemalpaşa Belediyesi• İmar ve Şehircilik Müdürlüğü • Encümen Kayıt Sistemi"
        )

        bnd = tk.Frame(s.root, bg=BG)
        bnd.pack(fill="x")

        s.tema_dugme = tk.Label(
        bnd,
        text=s.tema_yazi(),
        bg=BG,
        fg=METIN,
        padx=14,
        pady=9,
        cursor="hand2",
        font=("Segoe UI", 9, "bold")
        )
        s.tema_dugme.pack(side="right")
        s.tema_dugme.bind(
        "<Button-1>",
        lambda e: s.tema_degistir()
        )

        s.bildirim = tk.Label(
        bnd,
        text="",
        bg=BG,
        fg="#D97706",
        padx=18
        )
        s.bildirim.pack(side="right")

        s.nb = ttk.Notebook(s.root)
        s.nb.pack(fill="both", expand=True, padx=10, pady=(8, 10))
        sek = ttk.Frame(s.nb)
        s.gsek = ttk.Frame(s.nb)
        s.fsek = ttk.Frame(s.nb)
        s.nb.add(sek, text="Kayıtlar")
        s.nb.add(s.gsek, text="Grafikler")
        s.nb.add(s.fsek, text="Fen Klasörü")
        s.nb.bind("<<NotebookTabChanged>>", lambda e: s.ciz_hepsi())
        s.nb.bind("<<NotebookTabChanged>>", lambda e: s.fen_sekmesi_acildi(), add="+")
        s.kartlar = {}
        kf = ttk.Frame(sek)
        kf.pack(fill="x", padx=6, pady=(8, 2))
        for i, (anahtar, baslik) in enumerate([("acik", "Açık işler"), ("encumen", "Bu ay encümen"),
                                               ("gecik", "Geciken işler"), ("harc", "Bu ay tahsil edilen harç"),
                                               ("parsel", "Pasif parsel — onay bekliyor")]):
            kf.columnconfigure(i, weight=1, uniform="k")
            c = tk.Frame(kf, bg=KART, highlightthickness=1, highlightbackground=KENAR, cursor="hand2")
            c.grid(row=0, column=i, sticky="nsew", padx=4)
            sayi = tk.Label(c, text="–", bg=KART, fg=modern_tasarim.stat_renk(KART_RENK[anahtar], KOYU),
                            font=("Segoe UI", 22, "bold"), anchor="w")
            sayi.pack(fill="x", padx=16, pady=(12, 0))
            tk.Label(c, text=baslik, bg=KART, fg=SOLUK, font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=16, pady=(0, 12))
            for w in [c] + c.winfo_children():
                w.bind("<Button-1>", lambda e, a=anahtar: s.kart_tikla(a))
            s.kartlar[anahtar] = sayi
        top = ttk.Frame(sek)
        top.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(top, text="🔍 Ara:").pack(side="left")
        s.ara = tk.StringVar()
        s.ara.trace_add("write", lambda *a: s.load_gecikmeli())
        s.ara_kutu = ttk.Entry(top, textvariable=s.ara, width=24)
        s.ara_kutu.pack(side="left", padx=4)
        s.ara_kutu.bind("<Escape>", lambda e: s.ara.set(""))
        for t, c in [("+ Yeni Kayıt", s.yeni), ("Formda Düzenle", s.duzenle), ("Toplu Güncelle", s.toplu), ("Sil", s.sil),
                     ("Kararı Aç", lambda: s.ac("karar")), ("Makbuzu Aç", lambda: s.ac("makbuz"))]:
            ttk.Button(top, text=t, command=c, style="Accent.TButton" if t == "+ Yeni Kayıt" else (
                "Danger.TButton" if t == "Sil" else "TButton")).pack(side="left", padx=3)
        ym = tk.Menu(top, tearoff=0)
        ym.add_command(label="Şimdi yedekle", command=s.yedek_simdi)
        ym.add_command(label="Yedek klasörünü seç", command=s.yedek_klasoru_sec)
        ym.add_command(label="Yedekten geri yükle", command=s.yedek_geri_yukle)
        ttk.Menubutton(top, text="Yedek", menu=ym).pack(side="left", padx=2)
        vm = tk.Menu(top, tearoff=0)
        vm.add_command(label="Son işlemi geri al (Ctrl+Z)", command=s.geri_al)
        vm.add_separator()
        vm.add_command(label="Parsel Sorgu (TKGM)...", command=s.parsel_sorgu_ac)
        vm.add_command(label="Listeler (mahalle, müellif, işlem, durum)...", command=lambda: Listeler(s))
        vm.add_command(label="CSV Al (Google E-Tablo'dan)...", command=s.csv_al)
        vm.add_command(label="CSV Aktar (tüm kayıtlar)...", command=s.csv_aktar)
        vm.add_command(label="Dosya klasörleri (isteğe bağlı)...", command=s.klasorler)
        vm.add_separator()
        vm.add_command(label="Son silinenler (geri getir)...", command=lambda: Silinenler(s))
        ttk.Menubutton(top, text="Veri", menu=vm).pack(side="left", padx=2)
        rm = tk.Menu(top, tearoff=0)
        rm.add_command(label="Görünen liste (yazdır / PDF)", command=s.rapor_liste)
        rm.add_command(label="Müellife göre harç dökümü (yazdır / PDF)", command=s.rapor_muellif)
        rm.add_command(label="Görünen listeyi Excel'e aktar (CSV)", command=s.excel_aktar)
        rm.add_separator()
        rm.add_command(label="Rapor başlığı ve imza ayarları...", command=lambda: RaporAyar(s))
        ttk.Menubutton(top, text="Rapor", menu=rm).pack(side="left", padx=2)
        em = tk.Menu(top, tearoff=0)
        em.add_checkbutton(label="Koyu tema", variable=s.koyu_var, command=s.tema_degistir)
        em.add_checkbutton(label="Modern rozet ve satır çizgileri", variable=s.rozet_var, command=s.rozet_degistir)
        em.add_checkbutton(label="Detay paneli (F3)", variable=s.detay_var, command=s.detay_ac_kapa)
        em.add_separator()
        em.add_command(label="Yazıyı büyüt (Ctrl + tekerlek yukarı  /  Ctrl +)", command=lambda: s.yazi_boyut(1))
        em.add_command(label="Yazıyı küçült (Ctrl + tekerlek aşağı  /  Ctrl -)", command=lambda: s.yazi_boyut(-1))
        em.add_command(label="Varsayılan yazı boyutu (Ctrl 0)", command=lambda: s.yazi_boyut(None))
        em.add_separator()
        sm = tk.Menu(em, tearoff=0)
        for k in TV_COLS[1:]:
            sm.add_checkbutton(label=SUTUN_AD.get(k) or LAB.get(k, k), variable=s.sutun_var[k], command=s.sutun_uygula)
        em.add_cascade(label="Sütunları göster / gizle", menu=sm)
        ttk.Menubutton(top, text="Ekran", menu=em).pack(side="left", padx=2)
        f2 = ttk.Frame(sek)
        f2.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(f2, text="Görünüm:").pack(side="left", padx=(8, 2))
        s.gorunum = ttk.Combobox(f2, state="readonly", width=34, values=GORUNUMLER)
        s.gorunum.set(GORUNUMLER[0])
        s.gorunum.pack(side="left")
        s.gorunum.bind("<<ComboboxSelected>>", lambda e: s.load())
        s.lf = ListeFiltreleri(f2, s.load)
        ttk.Button(f2, text="Filtreleri Temizle", command=s.fil_temizle).pack(side="left", padx=10)
        s.eksik = tk.BooleanVar(value=False)
        ttk.Checkbutton(f2, text="Dosyası eksik olanlar (✗)", variable=s.eksik, command=s.load).pack(side="left", padx=6)
        s.parsel_f = tk.BooleanVar(value=False)
        ttk.Checkbutton(f2, text="Pasif parsel (onay bekliyor)", variable=s.parsel_f, command=s.load).pack(side="left", padx=6)
        s.ta = TarihAraligi(sek, s.load)
        s.gecik = tk.BooleanVar(value=False)
        s.esik_var = tk.StringVar(value=ayar("gecikme_gun") or "30")
        ttk.Checkbutton(s.ta.f, text="Geciken işler", variable=s.gecik, command=s.load).pack(side="left", padx=(16, 4))
        ttk.Label(s.ta.f, text="Eşik (gün):").pack(side="left")
        sp = ttk.Spinbox(s.ta.f, from_=1, to=365, width=5, textvariable=s.esik_var, command=s.esik_degisti)
        sp.pack(side="left", padx=4)
        sp.bind("<Return>", lambda e: s.esik_degisti())
        sp.bind("<FocusOut>", lambda e: s.esik_degisti())
        s.gm = tk.Menu(s.ta.f, tearoff=0, postcommand=s.gm_doldur)
        ttk.Menubutton(s.ta.f, text="Kayıtlı filtreler", menu=s.gm).pack(side="right", padx=6)
        ttk.Button(s.ta.f, text="Parsel Sorgu", command=s.parsel_sorgu_ac).pack(side="right", padx=6)
        kap = ttk.Frame(sek)
        kap.pack(fill="both", expand=True, padx=6)
        s.tv = ttk.Treeview(kap, columns=TV_COLS, show="headings", selectmode="extended")
        sb = ttk.Scrollbar(kap, orient="vertical", command=s.tv.yview)
        s.tv.configure(yscrollcommand=lambda a, b: (sb.set(a, b), s.rozet_planla()))
        s.sb = sb
        sb.pack(side="right", fill="y")
        s.tv.pack(side="left", fill="both", expand=True)
        s.detay_kur(kap)
        for k in SHOWN:
            s.tv.heading(k, text=LAB[k], command=lambda k=k: s.sirala(k))
            s.tv.column(k, width=170 if k == "aciklama" else 105)
        s.tv.heading("sira", text="Sıra", command=s.sira_sifirla)
        s.tv.column("sira", width=50, minwidth=40, anchor="center", stretch=False)
        for k, ad in (("karar_ok", "Karar Dosyası"), ("makbuz_ok", "Makbuz Dosyası")):
            s.tv.heading(k, text=ad)
            s.tv.column(k, width=100, anchor="center")
        s.tv.heading("bekleme", text=LAB["bekleme"], command=lambda: s.sirala("bekleme"))
        s.tv.column("bekleme", width=95, anchor="center")
        for k, g in (("parsel_durum", 190), ("parsel_yeni", 150)):
            s.tv.heading(k, text=LAB[k], command=lambda k=k: s.sirala(k))
            s.tv.column(k, width=g, anchor="w")
        s.tv.tag_configure("gec", foreground=KIRMIZI)
        s.tv.tag_configure("pas", foreground=KIRMIZI)
        s.durum_tag_ayarla()
        s.durum = ttk.Label(sek, style="Footer.TLabel")
        s.durum.pack(fill="x", padx=6, pady=(6, 2))
        lg = ttk.Frame(sek)
        lg.pack(anchor="w", padx=8, pady=(0, 4))
        ttk.Label(lg, text="Renkler:").pack(side="left")
        for ad, r in DURUM_UI.items():
            tk.Label(lg, text=ad, bg=r, fg=METIN, padx=6).pack(side="left", padx=2)
        ttk.Label(lg, text="    Dosya:  ✓ var   ✗ yok   ? klasöre ulaşılamıyor").pack(side="left")
        s.grafik_kur()
        s.fen_kur()
        s.tv.bind("<Button-1>", s.tikla)
        s.tv.bind("<Double-1>", s.cift)
        s.tv.bind("<Button-3>", s.sag)
        s.tv.bind("<MouseWheel>", lambda e: s.edit_kapat())
        s.tv.bind("<Control-MouseWheel>", lambda e: (s.yazi_boyut(1 if e.delta > 0 else -1), "break")[1])
        s.tv.bind("<Control-Button-4>", lambda e: (s.yazi_boyut(1), "break")[1])
        s.tv.bind("<Control-Button-5>", lambda e: (s.yazi_boyut(-1), "break")[1])
        s.tv.bind("<<TreeviewSelect>>", lambda e: s.detay_guncelle())
        for ks in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            s.root.bind(ks, lambda e: s.yazi_boyut(1))
        for ks in ("<Control-minus>", "<Control-KP_Subtract>"):
            s.root.bind(ks, lambda e: s.yazi_boyut(-1))
        s.root.bind("<Control-Key-0>", lambda e: s.yazi_boyut(None))
        s.root.bind("<F3>", lambda e: (s.detay_var.set(not s.detay_var.get()), s.detay_ac_kapa()))
        s.tv.bind("<F2>", lambda e: s.f2())
        s.tv.bind("<Configure>", lambda e: s.rozet_planla(), add="+")
        s.tv.bind("<ButtonRelease-1>", lambda e: s.rozet_planla(), add="+")
        s.tv.bind("<<TreeviewSelect>>", lambda e: s.rozet_planla(), add="+")
        s.nb.bind("<<NotebookTabChanged>>", lambda e: s.rozet_planla(), add="+")
        s.menu = tk.Menu(s.root, tearoff=0)
        for t, c in [("Bu hücreyi düzenle (F2)", s.f2), ("Satırı formda düzenle", s.duzenle),
                     ("Seçili satırları toplu güncelle...", s.toplu),
                     ("Satırı çoğalt (aynı parsele yeni işlem)", s.cogalt),
                     ("Hücreyi / seçili satırları kopyala (Ctrl+C)", s.kopyala),
                     ("Parsel sonucunu onayla (uyarıyı kaldır)", s.parsel_onayla),
                     ("Kararı aç", lambda: s.ac("karar")), ("Makbuzu aç", lambda: s.ac("makbuz")),
                     ("Karar dosyasını seç / değiştir...", lambda: s.dosya_sec("karar")),
                     ("Makbuz dosyasını seç / değiştir...", lambda: s.dosya_sec("makbuz")),
                     ("Satırı sil", s.sil)]:
            s.menu.add_command(label=t, command=c)
        s.root.protocol("WM_DELETE_WINDOW", s.kapat)
        s.root.bind("<Control-f>", lambda e: (s.nb.select(0), s.ara_kutu.focus_set(), s.ara_kutu.select_range(0, "end")))
        s.root.bind("<Control-n>", lambda e: s.yeni())
        s.root.bind("<Control-z>", lambda e: s.geri_al())
        s.root.bind("<Control-Z>", lambda e: s.geri_al())
        s.root.bind("<F5>", lambda e: (dosya_cache_temizle(), s.load()))
        s.tv.bind("<Delete>", lambda e: s.sil())
        s.tv.bind("<Control-c>", lambda e: s.kopyala())
        s.ayar_yukle()
        s.load()
        s.root.after(500, s.acilis)

    # ---------- liste / filtre / sıralama ----------
    def fil_yenile(s):
        s.lf.yenile()
        s.glf.yenile()

    def filtre_sifirla(s):
        s.lf.temizle()
        s.ta.temizle()
        s.gorunum.set(GORUNUMLER[0])
        s.eksik.set(False)
        s.gecik.set(False)
        s.parsel_f.set(False)
        s.ara.set("")

    def fil_temizle(s):
        s.filtre_sifirla()
        s.load()

    def uygun(s, d, gorunum=True):
        if not s.lf.uygun(d) or not s.ta.uygun(d):
            return False
        g = s.gorunum.get()
        if gorunum and not s.lf.aktif("onay"):  # Durum seçilmişse o seçim geçerli
            if g == GORUNUMLER[0] and arsiv_mi(d["onay"]):
                return False
            if g == GORUNUMLER[2] and not arsiv_mi(d["onay"]):
                return False
        if s.eksik.get() and "✗" not in (d["karar_ok"], d["makbuz_ok"]):
            return False
        if s.gecik.get() and not s.geciken(d):
            return False
        if s.parsel_f.get() and not d.get("parsel_onay"):
            return False
        n = tr_lower(s.ara.get().strip())
        return not n or n in tr_lower(" ".join(d[k] for k in KEYS))

    def sira_sifirla(s):
        s.siralama = None
        s.load()

    def tum_kayitlar(s):
        idx = {tur: dosya_indeksi(ayar(tur + "_klasor")) for tur in ("karar", "makbuz")}
        sonuc, onb, bugun = [], {}, datetime.date.today()
        s.pk = pk = parsel_kontrol_oku()
        oto = parsel_otomatik_onay(pk)
        if oto:
            s.bildir(f"{oto} pasif parsel uyarısı onaylandı (iş 'Tescillendi' olduğu için)")
        for r in q(f"SELECT id,{','.join(KEYS)},durum_tarihi FROM kayit ORDER BY id"):
            d = dict(zip(KEYS, [x or "" for x in r[1:-1]]))
            d["durum_tarihi"] = r[-1] or ""
            d["bekleme"] = bekleme_gun(d, bugun)
            d.update(parsel_gosterim(pk.get(r[0])))
            d["karar_ok"] = dosya_isaret("karar", d, idx["karar"], onb)
            d["makbuz_ok"] = dosya_isaret("makbuz", d, idx["makbuz"], onb)
            sonuc.append((r[0], d))
        return sonuc

    def load(s):
        s.edit_kapat()
        s.fil_yenile()
        tum = s.tum_kayitlar()
        rows = [r for r in tum if s.uygun(r[1])]
        s.gecik_say = sum(1 for _, d in rows if s.geciken(d))
        s.gizli = 0
        if s.gorunum.get() == GORUNUMLER[0] and not s.lf.aktif("onay"):
            s.gizli = sum(1 for _, d in tum if arsiv_mi(d["onay"]) and s.uygun(d, False))
        if s.siralama:
            k, ters = s.siralama
            dolu = [r for r in rows if r[1][k]]
            bos = [r for r in rows if not r[1][k]]
            dolu.sort(key=lambda r: sort_key(k, r[1][k]), reverse=ters)
            rows = dolu + bos
        s.tv.delete(*s.tv.get_children())
        for n, (i, d) in enumerate(rows, 1):
            s.tv.insert("", "end", iid=str(i), values=[n] + [d[k] for k in SHOWN] + [d["karar_ok"], d["makbuz_ok"], d["bekleme"], d["parsel_durum"], d["parsel_yeni"]],
                         tags=s.etiket(d["onay"]) + (("gec",) if s.geciken(d) else ()) + (("pas",) if d["parsel_onay"] else ()))
        for k in SHOWN + ["bekleme", "parsel_durum", "parsel_yeni"]:
            ok = ""
            if s.siralama and s.siralama[0] == k:
                ok = " ▼" if s.siralama[1] else " ▲"
            s.tv.heading(k, text=LAB[k] + ok)
        s.durum_guncelle()
        s.grafik_guncelle(tum)
        s.kart_guncelle(tum)
        try:
            fen_senkronla()  # yeni TKGM sonuçları Fen Klasörü'ne işlenir
        except Exception:
            pass

    # ---------- grafikler ----------
    def grafik_kur(s):
        f1 = ttk.Frame(s.gsek)
        f1.pack(fill="x", padx=6, pady=(8, 2))
        s.glf = ListeFiltreleri(f1, s.grafik_guncelle)
        ttk.Button(f1, text="Filtreleri Temizle", command=s.g_temizle).pack(side="left", padx=10)
        s.gta = TarihAraligi(s.gsek, s.grafik_guncelle)
        ttk.Label(s.gsek, foreground=SOLUK, text="Bu sayfadaki filtreler yalnızca grafikleri etkiler. "
                  "Varsayılan olarak tüm işler (Tescillendi, Askıda Kaldı ve İptal dahil) hesaba katılır.").pack(anchor="w", padx=14)
        s.gnb = ttk.Notebook(s.gsek)
        s.gnb.pack(fill="both", expand=True, padx=8, pady=4)
        s.gnb.bind("<<NotebookTabChanged>>", lambda e: s.ciz_hepsi())
        kap = ttk.Frame(s.gnb)
        s.gnb.add(kap, text="Genel")
        tr = ttk.Frame(s.gnb)
        s.gnb.add(tr, text="Aylık trend")
        ust = ttk.Frame(tr)
        ust.pack(fill="x", padx=6, pady=(8, 2))
        ttk.Label(ust, text="Dönem:").pack(side="left", padx=(6, 4))
        s.donem = ttk.Combobox(ust, state="readonly", width=14, values=DONEMLER)
        s.donem.set(DONEMLER[0])
        s.donem.pack(side="left")
        s.donem.bind("<<ComboboxSelected>>", lambda e: s.trend_degisti())
        ttk.Label(ust, foreground=SOLUK, text="Müellif, mahalle, işlem ve durum filtreleri uygulanır; tarih aralığı yerine bu dönem kullanılır."
                  ).pack(side="left", padx=14)
        tk_ = ttk.Frame(tr)
        tk_.pack(fill="both", expand=True, padx=2, pady=4)
        for i in (0, 1):
            tk_.columnconfigure(i, weight=1, uniform="t")
        tk_.rowconfigure(0, weight=1)
        s.c5 = tk.Canvas(tk_, bg=KART, highlightthickness=1, highlightbackground=KENAR)
        s.c6 = tk.Canvas(tk_, bg=KART, highlightthickness=1, highlightbackground=KENAR)
        s.c5.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        s.c6.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        s.g_trend_rows = []
        for i in (0, 1):
            kap.columnconfigure(i, weight=1, uniform="a")
            kap.rowconfigure(i, weight=1, uniform="b")
        mk = lambda: tk.Canvas(kap, bg=KART, highlightthickness=1, highlightbackground=KENAR)
        s.c1, s.c4, s.c2, s.c3 = mk(), mk(), mk(), mk()
        s.c1.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        s.c4.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        s.c2.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
        s.c3.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)
        s.gdata = {"harc": [], "tek": [], "mahalle": [], "muellif": [], "aylik": ([], [], [])}
        for c in (s.c1, s.c2, s.c3, s.c4, s.c5, s.c6):
            c.bind("<Configure>", lambda e: s.ciz_hepsi())

    def g_temizle(s):
        s.glf.temizle()
        s.gta.temizle()
        s.grafik_guncelle()

    def grafik_guncelle(s, tum=None):
        if tum is None:
            tum = s.tum_kayitlar()
        harc, mah, mue, tek = {}, {}, {}, []
        trend = []
        for _, d in tum:
            if s.glf.uygun(d):
                trend.append(d)
            if not (s.glf.uygun(d) and s.gta.uygun(d)):
                continue
            m = d["muellif"] or "(Belirtilmemiş)"
            u = para(d["alinan_ucret"])
            harc[m] = harc.get(m, 0) + u
            mue[m] = mue.get(m, 0) + 1
            if d["mahalle"]:
                mah[d["mahalle"]] = mah.get(d["mahalle"], 0) + 1
            if u > 0:
                tek.append((f"{m} · {d['mahalle']} {d['ada_parsel']}".strip(), u))
        sirali = lambda x: sorted(x.items(), key=lambda t: (-t[1], tr_sira(t[0])))
        s.gdata = {"harc": [t for t in sirali(harc) if t[1] > 0][:12],
                   "tek": sorted(tek, key=lambda t: (-t[1], tr_sira(t[0])))[:10],
                   "mahalle": sirali(mah)[:12], "muellif": sirali(mue), "aylik": ([], [], [])}
        s.g_trend_rows = trend
        s.trend_hesapla()
        s.ciz_hepsi()

    def trend_hesapla(s):
        s.gdata["aylik"] = aylik_seri(s.g_trend_rows, s.donem.get() or DONEMLER[0], datetime.date.today())

    def trend_degisti(s):
        s.trend_hesapla()
        s.ciz_hepsi()

    def ciz_hepsi(s):
        tl = lambda v: para_yaz(v, 0)
        yatay_bar(s.c1, "Müellife göre toplam harç", s.gdata["harc"], tl)
        yatay_bar(s.c4, "En yüksek tekil harçlar (ilk 10)", s.gdata["tek"], tl, sol=270, maks=42)
        yatay_bar(s.c2, "Mahalle bazlı iş sayısı (ilk 12)", s.gdata["mahalle"], lambda v: str(v))
        pasta(s.c3, "Müellife göre iş sayısı", s.gdata["muellif"])
        aylar, isl, harc = s.gdata["aylik"]
        dikey_bar(s.c5, "Aylık iş sayısı (encümen tarihine göre)", aylar, isl, lambda v: str(int(v)) if v == int(v) else f"{v:.1f}", VURGU)
        dikey_bar(s.c6, "Aylık tahsil edilen harç (makbuz tarihine göre, B = bin ₺)", aylar, harc, kisa_para, "#10b981")

    def durum_guncelle(s):
        ch = s.tv.get_children()
        toplam = sum(para(s.tv.set(i, "alinan_ucret")) for i in ch)
        gz = f"    ·  {s.gizli} arşiv iş gizli (Görünüm: Tümü ile görürsünüz)" if s.gizli else ""
        gc = f"    ·  ⚠ {s.gecik_say} geciken iş" if s.gecik_say else ""
        s.durum.config(text=f"{len(ch)} kayıt    Toplam Alınan Ücret: {para_yaz(toplam)}{gz}{gc}    "
                            "(Çift tıkla: hücre düzenle · Ctrl/Shift ile çoklu seçim → Toplu Güncelle · başlığa tıkla: sırala)")
        s.rozet_planla()

    def sirala(s, k):
        if s.siralama and s.siralama[0] == k:
            s.siralama = (k, not s.siralama[1])
        else:
            s.siralama = (k, False)
        s.load()

    # ---------- hücre düzenleme ----------
    def edit_kapat(s):
        w, s.edit = s.edit, None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def hucre_yer(s, e):
        if s.tv.identify_region(e.x, e.y) != "cell":
            return None
        satir = s.tv.identify_row(e.y)
        try:
            k = s.sutun_goster[int(s.tv.identify_column(e.x)[1:]) - 1]
        except (ValueError, IndexError):
            return None
        return (satir, k) if satir else None

    def tikla(s, e):
        s.edit_kapat()
        h = s.hucre_yer(e)
        if h:
            s.son = h

    def sag(s, e):
        h = s.hucre_yer(e)
        if h:
            s.son = h
            if h[0] not in s.tv.selection():
                s.tv.selection_set(h[0])
            s.menu.tk_popup(e.x_root, e.y_root)

    def cift(s, e):
        h = s.hucre_yer(e)
        if not h:
            return
        s.son = h
        s.tv.selection_set(h[0])
        if h[1] in ("karar_no", "karar_ok"):
            s.ac("karar")
        elif h[1] in ("makbuz_no", "makbuz_ok"):
            s.ac("makbuz")
        else:
            s.root.after(50, lambda: s.hucre(*h))

    def f2(s):
        if s.son and s.tv.exists(s.son[0]):
            s.hucre(*s.son)
        else:
            messagebox.showinfo("Uyarı", "Önce bir hücreye tıklayın.")

    def hucre(s, iid, k):
        s.edit_kapat()
        if k in ("sira", "karar_ok", "makbuz_ok", "bekleme", "parsel_durum", "parsel_yeni"):
            return
        b = s.tv.bbox(iid, k)
        if not b:
            return
        x, y, w, h = b
        deger = s.tv.set(iid, k)
        if k in DATES:
            Takvim(s.root, deger, DATES[k], lambda v: s.kaydet(iid, k, v),
                   s.tv.winfo_rootx() + x, s.tv.winfo_rooty() + y + h)
            return
        t = LISTE_ALAN.get(k)
        if t:
            wd = AramaliCombobox(s.tv, lambda t=t: liste(t))
            wd.set(deger)
            wd.bind("<<ComboboxSelected>>", lambda e: s.kaydet(iid, k, wd.get()))
        else:
            wd = ttk.Entry(s.tv)
            wd.insert(0, deger)
            wd.select_range(0, "end")
            wd.bind("<FocusOut>", lambda e: s.kaydet(iid, k, wd.get()) if s.edit is wd else None)
        if t:
            wd.enter_cb = lambda e: s.kaydet(iid, k, wd.get())
            wd.esc_cb = lambda e: s.edit_kapat()
        else:
            wd.bind("<Return>", lambda e: s.kaydet(iid, k, wd.get()))
            wd.bind("<Escape>", lambda e: s.edit_kapat())
        wd.place(x=x, y=y, width=max(w, 150) if t else w, height=h)
        wd.focus_force()
        s.edit = wd
        if t:
            wd.select_range(0, "end")
            wd.after(80, wd.tum_goster)  # tüm seçenekler görünür; yazdıkça daralır

    def kaydet(s, iid, k, v):
        v = para_bicim(v) if k == "alinan_ucret" else (tarih_bicim(v) if k in DATES else (islem_kanon(v) if k == "islem" else v.strip()))
        if (q(f"SELECT {k} FROM kayit WHERE id=?", (int(iid),))[0][0] or "") == v:  # değişmediyse dokunma
            s.edit_kapat()
            return
        s.undo_onceki("Hücre düzenleme: " + LAB.get(k, k), [int(iid)])
        if k == "onay":
            eski = q("SELECT onay FROM kayit WHERE id=?", (int(iid),))[0][0] or ""
            if eski != v:
                q("UPDATE kayit SET durum_tarihi=? WHERE id=?", (bugun_str(), int(iid)))
        q(f"UPDATE kayit SET {k}=? WHERE id=?", (v, int(iid)))
        s.edit_kapat()
        if s.tv.exists(iid):
            s.tv.set(iid, k, v)
            if k == "onay":
                s.tv.item(iid, tags=s.etiket(v))
            if k in ("karar_no", "makbuz_no"):
                tur = k[:-3]
                r = q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (int(iid),))[0]
                s.tv.set(iid, tur + "_ok", dosya_isaret(tur, {tur + "_no": r[0] or "", tur + "_dosya": r[1] or ""},
                                                        dosya_indeksi(ayar(tur + "_klasor"))))
        t = LISTE_ALAN.get(k)
        if t and v:
            q("INSERT OR IGNORE INTO liste VALUES (?,?)", (t, v))
            s.fil_yenile()
        s.durum_guncelle()
        s.grafik_guncelle()
        if k == "onay":
            s.yenile_koru(int(iid))
        else:
            s.kart_guncelle(s.tum_kayitlar())

    # ---------- görünüm: tema, yazı boyutu, detay paneli, sütunlar, simge ----------
    def simge_koy(s):
        for d in (BASE, getattr(sys, "_MEIPASS", BASE)):
            yol = os.path.join(d, "encumen.ico")
            if os.path.exists(yol):
                try:
                    s.root.iconbitmap(yol)
                except tk.TclError:
                    pass
                return

    def tema_yazi(s):
        return "◐  Açık tema" if KOYU else "◐  Koyu tema"

    def _yeniden_boya(s, w, esle):
        if getattr(w, "_modern_baslik", False):  # başlık şeridini modern_tasarim.baslik_yenile boyar
            return
        OPS = ("bg", "fg", "background", "foreground", "activebackground", "activeforeground", "highlightbackground",
               "highlightcolor", "selectbackground", "selectforeground", "insertbackground", "disabledforeground",
               "selectcolor")
        if not isinstance(w, ttk.Widget):  # ttk görünümü stillerden gelir; klasik tk bileşenleri tek tek boyanır
            for op in OPS:
                try:
                    cur = str(w.cget(op))
                except tk.TclError:
                    continue
                if cur in esle:
                    try:
                        w.configure(**{op: esle[cur]})
                    except tk.TclError:
                        pass
        for c in w.winfo_children():
            s._yeniden_boya(c, esle)

    def tema_degistir(s):
        s.edit_kapat()
        eski, eski_d = dict(TEMA_KOYU if KOYU else TEMA_ACIK), dict(DURUM_UI)
        renk_ata(not KOYU)
        yeni = TEMA_KOYU if KOYU else TEMA_ACIK
        esle = {eski[k]: yeni[k] for k in eski}
        esle.update({eski_d[k]: DURUM_UI[k] for k in eski_d})
        tema_kur(s.root)
        modern_tasarim.tema_uygula(s.root, KOYU)
        s._yeniden_boya(s.root, esle)
        modern_tasarim.baslik_yenile(s.baslik_cubuk, KOYU)
        s.kart_renk_uygula()
        s.tv.tag_configure("gec", foreground=KIRMIZI)
        s.tv.tag_configure("pas", foreground=KIRMIZI)
        s.durum_tag_ayarla()
        s.fen_tv.tag_configure("eski", foreground=FEN_ESKI)
        s.fen_tv.tag_configure("yeni", foreground=FEN_YENI)
        s.koyu_var.set(KOYU)
        s.rozet_planla()
        s.tema_dugme.config(text=s.tema_yazi())
        s.detay_renk()
        s.ciz_hepsi()
        s.fen_grafik_ciz()
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("tema", "koyu" if KOYU else "acik"))

    def yazi_boyut(s, d):
        s.edit_kapat()
        n = 10 if d is None else max(8, min(20, TABLO_PUNTO + d))
        if n == TABLO_PUNTO:
            return
        punto_ata(n)
        st = ttk.Style()
        st.configure("Treeview", font=("Segoe UI", n), rowheight=round(n * 2.8))
        st.configure("Treeview.Heading", font=("Segoe UI", max(9, n), "bold"))
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("yazi_boyut", str(n)))
        s.bildir(f"Tablo yazı boyutu: {n}", 1500)
        s.rozet_planla()

    def sutun_uygula(s, kaydet=True):
        s.edit_kapat()
        gor = ["sira"] + [k for k in TV_COLS[1:] if s.sutun_var[k].get()]
        if len(gor) == 1:  # hiç sütun kalmasın
            for v in s.sutun_var.values():
                v.set(True)
            gor = list(TV_COLS)
        s.sutun_goster = gor
        s.tv.configure(displaycolumns=gor)
        if kaydet:
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)",
              ("gizli_sutun", json.dumps([k for k in TV_COLS[1:] if not s.sutun_var[k].get()])))

    def detay_kur(s, kap):
        s.dp = ttk.Frame(kap, width=320)
        s.dp.pack_propagate(False)
        ttk.Label(s.dp, text="Kayıt ayrıntısı", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 4))
        alt = ttk.Frame(s.dp)
        alt.pack(side="bottom", fill="x", pady=8)
        ttk.Button(alt, text="Kararı Aç", command=lambda: s.ac("karar")).pack(side="left", padx=(10, 4))
        ttk.Button(alt, text="Makbuzu Aç", command=lambda: s.ac("makbuz")).pack(side="left", padx=4)
        s.dt = tk.Text(s.dp, wrap="word", width=30, height=10, relief="flat", bd=0, highlightthickness=1,
                       padx=10, pady=8, cursor="arrow", state="disabled")
        s.dt.pack(fill="both", expand=True, padx=(10, 6))
        s.detay_renk()

    def detay_renk(s):
        s.dt.configure(bg=KART, fg=METIN, highlightbackground=KENAR, highlightcolor=KENAR)
        s.dt.tag_configure("e", foreground=SOLUK, font=("Segoe UI", 9, "bold"))
        s.dt.tag_configure("d", foreground=METIN, font=("Segoe UI", 11))
        s.dt.tag_configure("soluk", foreground=SOLUK, font=("Segoe UI", 10))

    def detay_ac_kapa(s, kaydet=True):
        s.detay_acik = bool(s.detay_var.get())
        if s.detay_acik:
            s.dp.pack(side="right", fill="y", padx=(6, 0), after=s.sb)
            s.detay_guncelle()
        else:
            s.dp.pack_forget()
        if kaydet:
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("detay", "1" if s.detay_acik else "0"))

    def detay_guncelle(s):
        if not s.detay_acik:
            return
        sec, t = s.tv.selection(), s.dt
        t.configure(state="normal")
        t.delete("1.0", "end")
        if not sec:
            t.insert("end", "Ayrıntısını görmek için tablodan bir satır seçin.", "soluk")
        elif len(sec) > 1:
            t.insert("end", f"{len(sec)} kayıt seçili.\n\nBirlikte değiştirmek için «Toplu Güncelle»yi kullanabilirsiniz.", "soluk")
        else:
            iid = sec[0]
            for k in SHOWN:
                t.insert("end", LAB[k] + "\n", "e")
                t.insert("end", str(s.tv.set(iid, k) or "–") + "\n\n", "d")
            for k, ad in (("karar_ok", "Karar dosyası"), ("makbuz_ok", "Makbuz dosyası"), ("bekleme", "Bekleme (gün)")):
                t.insert("end", ad + "\n", "e")
                t.insert("end", str(s.tv.set(iid, k) or "–") + "\n\n", "d")
            pk = s.pk.get(int(iid))
            if pk:
                for ad, v in (("Parsel durumu (TKGM)", s.tv.set(iid, "parsel_durum")), ("Sorgulanan parsel", pk["parsel_no"]),
                              ("Alan / nitelik", f"{pk['alan'] or '–'} m² · {pk['nitelik'] or '–'}"),
                              ("Yeni (aktif) parseller", s.tv.set(iid, "parsel_yeni")), ("TKGM açıklaması", pk["aciklama"]),
                              ("Son parsel kontrolü", (pk["son_kontrol"] or "").replace("T", " ")[:16])):
                    t.insert("end", ad + "\n", "e")
                    t.insert("end", str(v or "–") + "\n\n", "d")
        t.configure(state="disabled")

    # ---------- Modern görünüm katmanı (yalnızca görsel; veriye dokunmaz) ----------
    ROZET_SUTUN = ("onay", "alinan_ucret", "karar_ok", "makbuz_ok", "parsel_durum")

    def durum_tag_ayarla(s):
        """Rozet açıkken satır zemini sade kalır, durum rengi rozette görünür."""
        for i, r in enumerate(DURUM_UI.values()):
            s.tv.tag_configure(f"d{i}", background=KART if s.rozet_var.get() else r)

    def rozet_degistir(s):
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("rozet", "1" if s.rozet_var.get() else "0"))
        s.durum_tag_ayarla()
        s.rozet_planla()

    def rozet_planla(s):
        if getattr(s, "_rid", None) is None:
            s._rid = s.root.after(25, s.rozet_ciz)

    def rozet_gizle(s, ilk_hucre=0, ilk_cizgi=0):
        for f, _ in s._rz_hucre[ilk_hucre:]:
            f.place_forget()
        for c in s._rz_cizgi[ilk_cizgi:]:
            c.place_forget()

    def rozet_ciz(s):
        s._rid = None
        try:
            s._rozet_ciz()
        except Exception:
            try:
                s.rozet_gizle()
            except Exception:
                pass

    def _rz_ilet(s, w):
        """Rozetlerin üstüne yapılan tıklama/tekerlek olaylarını tabloya iletir."""
        def yap(ad):
            def f(e):
                kw = dict(x=e.x_root - s.tv.winfo_rootx(), y=e.y_root - s.tv.winfo_rooty(), state=e.state, time=e.time)
                if ad.endswith("MouseWheel"):
                    kw["delta"] = e.delta
                s.tv.event_generate(ad, **kw)
                return "break"
            return f
        for ad in ("<Button-1>", "<ButtonRelease-1>", "<Button-3>", "<MouseWheel>", "<Control-MouseWheel>"):
            w.bind(ad, yap(ad))

    def _rz_hucre_al(s, no):
        while len(s._rz_hucre) <= no:
            f = tk.Frame(s.tv, bd=0, highlightthickness=0)
            l = tk.Label(f, bd=0)
            s._rz_ilet(f)
            s._rz_ilet(l)
            s._rz_hucre.append((f, l))
        return s._rz_hucre[no]

    def _rozet_ciz(s):
        tv = s.tv
        if not s.rozet_var.get() or not tv.winfo_ismapped():
            s.rozet_gizle()
            return
        cocuk = tv.get_children()
        n = len(cocuk)
        if not n:
            s.rozet_gizle()
            return
        try:
            rh = int(ttk.Style().lookup("Treeview", "rowheight") or 28)
        except ValueError:
            rh = 28
        yuk = tv.winfo_height()
        ilk = max(0, int(tv.yview()[0] * n) - 1)
        son = min(n, ilk + yuk // max(16, rh) + 4)
        if tv.yview()[0] == 0:
            b0 = tv.bbox(cocuk[0])
            if b0:
                s._rz_hdr = b0[1]
        sec = set(tv.selection())
        font = ("Segoe UI", TABLO_PUNTO)
        fkalin = ("Segoe UI", TABLO_PUNTO, "bold")
        yesil = modern_tasarim.stat_renk("yesil", KOYU)
        kirmizi = modern_tasarim.stat_renk("kirmizi", KOYU)
        amber = modern_tasarim.stat_renk("turuncu", KOYU)
        hn = cn = 0
        for iid in cocuk[ilk:son]:
            b = tv.bbox(iid)
            if not b or b[1] < s._rz_hdr - 2 or b[1] + b[3] > yuk + 1:
                continue
            zemin = SEC if iid in sec else KART
            while len(s._rz_cizgi) <= cn:
                s._rz_cizgi.append(tk.Frame(tv, height=1, bd=0, highlightthickness=0))
            c = s._rz_cizgi[cn]
            c.configure(bg=KENAR)
            c.place(x=0, y=b[1] + b[3] - 1, relwidth=1, height=1)
            cn += 1
            for kol in s.ROZET_SUTUN:
                cb = tv.bbox(iid, kol)
                if not cb:
                    continue
                v = tv.set(iid, kol)
                if not v:
                    continue
                f, l = s._rz_hucre_al(hn)
                hn += 1
                f.configure(bg=zemin)
                l.pack_forget()
                if kol == "onay":
                    l.configure(text=v, bg=DURUM_UI.get(v, BASLIK), fg=METIN, font=("Segoe UI", max(8, TABLO_PUNTO - 1), "bold"), padx=8, pady=1)
                    l.pack(side="left", padx=6)
                else:
                    if kol == "alinan_ucret":
                        fg, ft, an = yesil, fkalin, "w"
                    elif kol in ("karar_ok", "makbuz_ok"):
                        fg, ft, an = (yesil if "✓" in v else kirmizi if "✗" in v else amber), fkalin, "center"
                    else:
                        dv = v.strip().lower()
                        fg = kirmizi if dv.startswith("pasif") else yesil if dv.startswith("aktif") else METIN
                        ft, an = fkalin, "w"
                    l.configure(text=v, bg=zemin, fg=fg, font=ft, anchor=an, padx=6, pady=0)
                    l.pack(fill="both", expand=True)
                f.place(x=cb[0], y=cb[1], width=cb[2], height=cb[3] - 1)
        s.rozet_gizle(hn, cn)

    def etiket(s, v):
        return ("d%d" % list(DURUM_RENK).index(v),) if v in DURUM_RENK else ()

    def load_gecikmeli(s, ms=250):
        if getattr(s, "_yid", None):
            s.root.after_cancel(s._yid)
        s._yid = s.root.after(ms, s._yuk)

    def _yuk(s):
        s._yid = None
        s.load()

    # ---------- özet kartları, kayıtlı filtreler, geri al ----------
    def bildir(s, metin, ms=4000):
        s.bildirim.config(text=metin)
        if getattr(s, "_bid", None):
            s.root.after_cancel(s._bid)
        s._bid = s.root.after(ms, lambda: s.bildirim.config(text=""))

    def kart_guncelle(s, tum):
        bg = datetime.date.today()
        acik = encumen = gecik = parsel = 0
        harc = 0.0
        for _, d in tum:
            if not arsiv_mi(d["onay"]):
                acik += 1
            t = tarih_oku(d["encumen_tarihi"])
            if t and (t.year, t.month) == (bg.year, bg.month):
                encumen += 1
            if s.geciken(d):
                gecik += 1
            if d.get("parsel_onay"):
                parsel += 1
            t = tarih_oku(d["makbuz_tarihi"])
            if t and (t.year, t.month) == (bg.year, bg.month):
                harc += para(d["alinan_ucret"])
        s.kartlar["acik"].config(text=str(acik))
        s.kartlar["encumen"].config(text=str(encumen))
        s.kartlar["gecik"].config(text=str(gecik))
        s.kartlar["harc"].config(text=para_yaz(harc, 0))
        s.kartlar["parsel"].config(text=str(parsel))
        s.kart_renk_uygula()

    def kart_renk_uygula(s):
        """Sayaç rakamlarını kendi renginde gösterir (açık/koyu temaya uyumlu)."""
        for a, lbl in s.kartlar.items():
            lbl.config(fg=modern_tasarim.stat_renk(KART_RENK[a], KOYU))

    def kart_tikla(s, a):
        s.filtre_sifirla()
        if a in ("encumen", "harc"):
            s.gorunum.set(GORUNUMLER[1])
            s.ta.alan.set("Encümen Tarih" if a == "encumen" else "Ödeme Makbuz Tarih")
            s.ta.hizli("Bu ay")  # listeyi de yeniler
        else:
            if a == "gecik":
                s.gecik.set(True)
            elif a == "parsel":
                s.parsel_f.set(True)
            s.load()

    def gorunum_al(s):
        return {"gorunum": s.gorunum.get(), "lf": {k: cb.get() for k, cb in s.lf.cb.items()}, "alan": s.ta.alan.get(),
                "bas": s.ta.bas.get(), "bit": s.ta.bit.get(), "preset": s.ta.preset, "ara": s.ara.get(),
                "eksik": bool(s.eksik.get()), "gecik": bool(s.gecik.get()),
                "siralama": list(s.siralama) if s.siralama else None}

    def gorunum_uygula(s, v):
        s.filtre_sifirla()
        if v.get("gorunum") in GORUNUMLER:
            s.gorunum.set(v["gorunum"])
        for k, val in v.get("lf", {}).items():
            if k in s.lf.cb:
                s.lf.cb[k].set(val)
        if v.get("alan") in TARIH_ALANLARI:
            s.ta.alan.set(v["alan"])
        s.ara.set(v.get("ara", ""))
        s.eksik.set(bool(v.get("eksik")))
        s.gecik.set(bool(v.get("gecik")))
        sr = v.get("siralama")
        s.siralama = tuple(sr) if sr else None
        if v.get("preset"):
            s.ta.hizli(v["preset"])  # "Bu ay" gibi göreli aralıklar her seferinde güncel hesaplanır; listeyi de yeniler
        else:
            s.ta.bas.set(v.get("bas", ""))
            s.ta.bit.set(v.get("bit", ""))
            s.load()

    def gm_doldur(s):
        m = s.gm
        m.delete(0, "end")
        m.add_command(label="Geçerli filtreyi kaydet...", command=s.gorunum_kaydet)
        m.add_separator()
        for ad, v in BAZI_GORUNUM.items():
            m.add_command(label=ad, command=lambda v=v: s.gorunum_uygula(v))
        kayitli = sorted(q("SELECT ad, veri FROM gorunum"), key=lambda r: tr_sira(r[0]))
        if kayitli:
            m.add_separator()
            for ad, veri in kayitli:
                m.add_command(label=ad, command=lambda veri=veri: s.gorunum_uygula(json.loads(veri)))
            sm = tk.Menu(m, tearoff=0)
            for ad, _ in kayitli:
                sm.add_command(label=ad, command=lambda ad=ad: s.gorunum_sil(ad))
            m.add_cascade(label="Kayıtlı filtreyi sil", menu=sm)

    def gorunum_kaydet(s):
        ad = simpledialog.askstring("Filtreyi kaydet", "Bu filtre kombinasyonuna bir ad verin:", parent=s.root)
        if not ad or not ad.strip():
            return
        ad = ad.strip()
        if q("SELECT 1 FROM gorunum WHERE ad=?", (ad,)) and not messagebox.askyesno(
                "Kayıtlı filtre", f"“{ad}” adlı filtre zaten var. Üzerine yazılsın mı?"):
            return
        q("INSERT OR REPLACE INTO gorunum VALUES (?,?)", (ad, json.dumps(s.gorunum_al(), ensure_ascii=False)))
        s.bildir(f"Filtre kaydedildi: {ad}")

    def gorunum_sil(s, ad):
        if messagebox.askyesno("Kayıtlı filtreyi sil", f"“{ad}” silinsin mi?"):
            q("DELETE FROM gorunum WHERE ad=?", (ad,))
            s.bildir(f"Filtre silindi: {ad}")

    def undo_push(s, ad, onceki, silinme=None):
        s.undo.append({"ad": ad, "onceki": onceki, "silinme": silinme})
        del s.undo[:-50]

    def undo_onceki(s, ad, ids):
        s.undo_push(ad, kayit_snapshot(ids))

    def undo_ekle(s, ad, yeni_ids):
        s.undo_push(ad, {i: None for i in yeni_ids})

    def undo_temizle(s):
        s.undo.clear()

    def geri_al(s):
        if not s.undo:
            s.bildir("Geri alınacak işlem yok")
            return "break"
        e = s.undo.pop()
        undo_uygula(e)
        s.yenile_koru()
        s.bildir("Geri alındı: " + e["ad"])
        return "break"

    # ---------- Fen Klasörü ----------
    def fen_kur(s):
        s.fen_kayit, s.fen_son = {}, ("", "", "")
        ust = ttk.Frame(s.fsek)
        ust.pack(fill="x", padx=12, pady=(14, 4))
        ttk.Label(ust, text="Mahalle:").pack(side="left")
        s.fen_mah = AramaliCombobox(ust, lambda: liste("mahalle"), width=24)
        s.fen_mah.pack(side="left", padx=(4, 12))
        s.fen_mah.enter_cb = lambda e: s.fen_ara()
        s.fen_ada, s.fen_par = tk.StringVar(), tk.StringVar()
        ttk.Label(ust, text="Ada:").pack(side="left")
        e1 = ttk.Entry(ust, textvariable=s.fen_ada, width=8)
        e1.pack(side="left", padx=(4, 12))
        ttk.Label(ust, text="Parsel:").pack(side="left")
        e2 = ttk.Entry(ust, textvariable=s.fen_par, width=8)
        e2.pack(side="left", padx=(4, 12))
        for w in (e1, e2):
            w.bind("<Return>", lambda e: s.fen_ara())
        ttk.Button(ust, text="Ara", style="Accent.TButton", command=s.fen_ara).pack(side="left", padx=4)
        ttk.Button(ust, text="Temizle", command=s.fen_temizle).pack(side="left", padx=4)
        ttk.Button(ust, text="Fen işlemi ekle...", command=lambda: FenIslemDialog(s)).pack(side="right", padx=4)
        ttk.Button(ust, text="Seçileni sil", command=s.fen_sil).pack(side="right", padx=4)
        ttk.Label(s.fsek, foreground=SOLUK, text="Eski ya da yeni parsel numarasını yazın; ikisinde de ararım. Adası olmayan parseller için ada 0 "
                  "(boş bırakırsanız tüm adalarda aranır). Mahalle boşsa tüm mahalleler taranır. Kayıtlar, Parsel Sorgu sonuçlarından "
                  "otomatik oluşur; elle de eklenebilir.", wraplength=1100, justify="left").pack(anchor="w", padx=14)
        kap = ttk.Frame(s.fsek)
        kap.pack(fill="both", expand=True, padx=12, pady=(8, 2))
        cols = ("eslesme", "mahalle", "tur", "tarih", "eski", "yeni", "kaynak", "is")
        s.fen_tv = ttk.Treeview(kap, columns=cols, show="headings", selectmode="browse", height=9)
        for c, ad, w in (("eslesme", "Eşleşme", 110), ("mahalle", "Mahalle", 130), ("tur", "İşlem", 100), ("tarih", "Tarih", 95),
                         ("eski", "Eski parseller", 230), ("yeni", "Yeni parseller", 200), ("kaynak", "Kaynak", 70), ("is", "İş kayıt no", 80)):
            s.fen_tv.heading(c, text=ad)
            s.fen_tv.column(c, width=w, anchor="w")
        s.fen_tv.tag_configure("eski", foreground=FEN_ESKI)
        s.fen_tv.tag_configure("yeni", foreground=FEN_YENI)
        sb = ttk.Scrollbar(kap, orient="vertical", command=s.fen_tv.yview)
        s.fen_tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        s.fen_tv.pack(side="left", fill="both", expand=True)
        s.fen_tv.bind("<<TreeviewSelect>>", lambda e: s.fen_grafik_ciz())
        s.fen_say = ttk.Label(s.fsek, text="", foreground=SOLUK)
        s.fen_say.pack(anchor="w", padx=14, pady=(2, 2))
        s.fen_cv = tk.Canvas(s.fsek, bg=KART, height=210, highlightthickness=1, highlightbackground=KENAR)
        s.fen_cv.pack(fill="x", padx=12, pady=(0, 12))
        s.fen_cv.bind("<Configure>", lambda e: s.fen_grafik_ciz())
        s.fen_grafik_ciz()

    def fen_sekmesi_acildi(s):
        try:
            if s.nb.select() == str(s.fsek) and any(s.fen_son):
                s.fen_ara()  # başka yerden gelen yeni sonuçları göster
        except (tk.TclError, AttributeError):
            pass

    def fen_temizle(s):
        s.fen_mah.set("")
        s.fen_ada.set("")
        s.fen_par.set("")
        s.fen_ara()

    def fen_ara(s):
        mah, ada, par = s.fen_mah.get().strip(), s.fen_ada.get().strip(), s.fen_par.get().strip()
        s.fen_son = (mah, ada, par)
        for i in s.fen_tv.get_children():
            s.fen_tv.delete(i)
        s.fen_kayit = {}
        if not (mah or ada or par):
            s.fen_say.config(text="Arama için mahalle, ada veya parsel yazın.")
            s.fen_grafik_ciz()
            return
        sonuc = fen_ara_sorgu(mah, ada, par)
        for n, r in enumerate(sonuc):
            iid = str(n)
            s.fen_kayit[iid] = r
            eslesme = {"eski": "Eski parsel", "yeni": "Yeni parsel"}.get(r["rol"], "—")
            s.fen_tv.insert("", "end", iid=iid, tags=(r["rol"],) if r["rol"] else (), values=(
                eslesme, r["mahalle"], r["tur"] or "–", r["tarih"] or "–",
                ", ".join(parsel_etiket(a, p) for a, p in r["eski"]) or "–",
                ", ".join(parsel_etiket(a, p) for a, p in r["yeni"]) or "–", r["kaynak"],
                f"#{r['work_id']}" if r["work_id"] else ""))
        s.fen_say.config(text=f"{len(sonuc)} kayıt bulundu" if sonuc else "Kayıt bulunamadı")
        if sonuc:
            s.fen_tv.selection_set("0")
        s.fen_grafik_ciz()

    def fen_sil(s):
        sec = s.fen_tv.selection()
        if not sec or sec[0] not in s.fen_kayit:
            messagebox.showinfo("Uyarı", "Önce silinecek kaydı seçin.")
            return
        r = s.fen_kayit[sec[0]]
        if r["kaynak"] == "TKGM":
            messagebox.showinfo("Fen Klasörü", "Bu kayıt Parsel Sorgu sonucundan otomatik oluşturulur; silinemez. "
                                "Sonuç değişirse kendiliğinden güncellenir.")
            return
        if messagebox.askyesno("Sil", "Seçili fen işlemi silinsin mi?"):
            fen_sil_kayit(r["id"])
            s.fen_ara()

    def fen_grafik_ciz(s):
        cv = s.fen_cv
        cv.delete("all")
        w = max(cv.winfo_width(), 600)
        sec = s.fen_tv.selection()
        if not sec or sec[0] not in s.fen_kayit:
            cv.create_text(w / 2, 100, text="Bir sonuç seçince eski → yeni parsel grafiği burada görünür", fill=SOLUK)
            return
        r = s.fen_kayit[sec[0]]
        eski = [parsel_etiket(a, p) for a, p in r["eski"]]
        yeni = [parsel_etiket(a, p) for a, p in r["yeni"]]
        aranan = parsel_etiket(s.fen_son[1], s.fen_son[2]) if s.fen_son[2] else ""
        cv.create_text(12, 14, anchor="w", font=("Segoe UI", 10, "bold"), fill=METIN,
                       text=f"{r['tur'] or 'İşlem'} · {r['tarih'] or '–'} · {r['mahalle']}")
        iki = bool(eski and yeni)
        yer = lambda liste_, y: {no: (w * (i + 1) / (len(liste_) + 1), y) for i, no in enumerate(liste_)}
        ke, ky = yer(eski, 70 if iki else 110), yer(yeni, 160 if iki else 110)
        if iki:
            for ex, ey in ke.values():
                for yx, yy in ky.values():
                    cv.create_line(ex, ey + 16, ex, 115, yx, 115, yx, yy - 16, fill=SOLUK, width=2)
        for gruplar, dolgu, yazi in ((ke, KENAR, METIN), (ky, "#4d7c0f", "#ffffff")):
            for no, (x, y) in gruplar.items():
                secili = no == aranan
                cv.create_rectangle(x - 46, y - 16, x + 46, y + 16, fill=dolgu, outline=VURGU if secili else SOLUK, width=3 if secili else 1)
                cv.create_text(x, y, text=no, fill=yazi, font=("Segoe UI", 10, "bold" if secili else "normal"))
        if r.get("aciklama"):
            cv.create_text(w / 2, 198, fill=SOLUK, font=("Segoe UI", 9), text=r["aciklama"][:150])

    # ---------- Parsel Sorgu (TKGM) bağlantısı ----------
    def parsel_sorgu_ac(s):
        """İş Takip'teki AÇIK işleri parsel sorgu penceresine aktarır; sonuçlar 'parsel_kontrol' tablosuna yazılır."""
        try:
            import parsel_sorgu_modulu
        except ImportError as e:
            messagebox.showerror("Parsel Sorgu", "Parsel Sorgu modülü yüklenemedi.\n\nparsel_sorgu_modulu.py bu programla aynı klasörde "
                                 "olmalı ve 'pip install requests openpyxl pillow' ile kütüphaneler kurulu olmalı.\n\nAyrıntı: " + str(e))
            return
        p = getattr(s, "_parsel_pencere", None)
        try:
            if p is not None and p.winfo_exists():
                p.lift()
                p.focus_force()
                return
        except tk.TclError:
            pass
        kaynak = [(i, d["mahalle"], d["ada_parsel"]) for i, d in s.tum_kayitlar()
                  if not arsiv_mi(d["onay"]) and d["mahalle"] and d["ada_parsel"]]
        s._parsel_pencere = parsel_sorgu_modulu.App(s.root, kaynak=kaynak, takip_db=DB, sonuc_geri_cagir=s.parsel_sonuc_geldi)

    def parsel_sonuc_geldi(s, work_id, ozet):
        s.load_gecikmeli(700)  # birçok sonuç art arda gelir: tabloyu tek seferde yenile

    def parsel_onayla(s):
        """Pasif parsel uyarısını kaldırır (işin durumuna dokunmaz)."""
        ids = s.sel_ids()
        if not ids:
            messagebox.showinfo("Uyarı", "Önce satır(lar)ı seçin.")
            return
        n = 0
        for i in ids:
            if (s.pk.get(i) or {}).get("onay"):
                q("UPDATE parsel_kontrol SET onay_bekliyor=0 WHERE work_id=?", (i,))
                n += 1
        s.load()
        s.bildir(f"{n} kayıt için parsel uyarısı kaldırıldı" if n else "Seçili kayıtlarda onay bekleyen parsel uyarısı yok")

    # ---------- pencere, kopyalama, çoğaltma ----------
    def ayar_kaydet(s):
        zoom = s.root.state() == "zoomed"
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("pencere_durum", "zoomed" if zoom else "normal"))
        if not zoom:
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("pencere", s.root.geometry()))
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)",
          ("sutunlar", json.dumps({c: int(s.tv.column(c, "width")) for c in TV_COLS})))

    def ayar_yukle(s):
        try:
            m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", ayar("pencere"))
            if m:
                w, h, x, y = map(int, m.groups())
                sw, sh = s.root.winfo_screenwidth(), s.root.winfo_screenheight()
                w, h = min(w, sw), min(h, sh)
                x, y = min(max(x, 0), max(sw - w, 0)), min(max(y, 0), max(sh - h - 40, 0))
                s.root.geometry(f"{w}x{h}+{x}+{y}")
            for c, w in json.loads(ayar("sutunlar") or "{}").items():
                if c in TV_COLS and isinstance(w, int) and 20 <= w <= 900:
                    s.tv.column(c, width=w)
        except Exception:
            pass
        try:
            gizli = json.loads(ayar("gizli_sutun") or "[]")
            for k, v in s.sutun_var.items():
                v.set(k not in gizli)
            s.sutun_uygula(kaydet=False)
        except Exception:
            pass
        try:
            s.detay_var.set(ayar("detay") == "1")
            s.detay_ac_kapa(kaydet=False)
        except Exception:
            pass
        try:
            if ayar("pencere_durum") == "zoomed":
                s.root.state("zoomed")
        except Exception:
            pass

    def kopyala(s):
        ids = s.sel_ids()
        if not ids:
            return "break"
        tum = dict(s.tum_kayitlar())
        if len(ids) == 1 and s.son and s.son[0] == str(ids[0]):
            k = s.son[1]
            metin = tum[ids[0]].get(k)
            if metin is None:
                metin = str(s.tv.set(str(ids[0]), k))
        else:  # birden çok satır: Excel'e yapıştırılabilir (sekmeyle ayrılmış)
            sira = [int(i) for i in s.tv.get_children() if int(i) in ids]
            metin = "\n".join("\t".join(tum[i][k] for k in SHOWN) for i in sira if i in tum)
        s.root.clipboard_clear()
        s.root.clipboard_append(metin)
        return "break"

    def cogalt(s):
        i = s.sec()
        if i:
            Form(s, kopya=i)

    # ---------- gecikme / toplu işlem / rapor ----------
    def esik(s):
        try:
            return max(int(s.esik_var.get()), 0)
        except (ValueError, tk.TclError):
            return 30

    def esik_degisti(s):
        q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("gecikme_gun", str(s.esik())))
        s.load()

    def geciken(s, d):
        b = d.get("bekleme")
        return bool(b) and int(b) > s.esik()

    def sel_ids(s):
        return [int(x) for x in s.tv.selection()]

    def yenile_koru(s, iid=None):
        y = s.tv.yview()[0]
        s.load()
        s.tv.yview_moveto(y)
        if iid and s.tv.exists(str(iid)):
            s.tv.selection_set(str(iid))

    def toplu(s):
        ids = s.sel_ids()
        if not ids:
            messagebox.showinfo("Uyarı", "Önce satırları seçin (Ctrl veya Shift tuşuyla birden çok satır seçebilirsiniz).")
            return
        TopluGuncelle(s, ids)

    def gorunen(s):
        tum = dict(s.tum_kayitlar())
        return [tum[int(i)] for i in s.tv.get_children() if int(i) in tum]

    def filtre_ozeti(s):
        p = ["Görünüm: " + s.gorunum.get()]
        for k, ad in ListeFiltreleri.ALANLAR:
            if s.lf.aktif(k):
                p.append(f"{ad}: {s.lf.cb[k].get()}")
        b, e = s.ta.bas.get(), s.ta.bit.get()
        if b or e:
            p.append(f"{s.ta.alan.get()}: {b or '...'} - {e or '...'}")
        if s.ara.get().strip():
            p.append(f"Arama: {s.ara.get().strip()}")
        if s.eksik.get():
            p.append("Dosyası eksik olanlar")
        if s.gecik.get():
            p.append(f"Geciken işler (>{s.esik()} gün)")
        return " | ".join(p) + "   —   Düzenlenme: " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    def rapor_liste(s):
        sat = s.gorunen()
        if not sat:
            messagebox.showinfo("Rapor", "Listede kayıt yok.")
            return
        rapor_ac(rapor_sayfasi("İmar Uygulamaları - Kayıt Listesi", s.filtre_ozeti(), liste_html(sat)))

    def rapor_muellif(s):
        sat = s.gorunen()
        if not sat:
            messagebox.showinfo("Rapor", "Listede kayıt yok.")
            return
        rapor_ac(rapor_sayfasi("Müellife Göre Harç Dökümü", s.filtre_ozeti(), muellif_html(sat)))

    def excel_aktar(s):
        sat = s.gorunen()
        if not sat:
            messagebox.showinfo("Rapor", "Listede kayıt yok.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Excel'de açılır (CSV)", "*.csv")])
        if p:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Sıra"] + [LAB[k] for k in SHOWN] + [LAB["bekleme"], LAB["parsel_durum"], LAB["parsel_yeni"]])
                for n, d in enumerate(sat, 1):
                    w.writerow([n] + [d[k] for k in SHOWN] + [d["bekleme"], d["parsel_durum"], d["parsel_yeni"]])
            messagebox.showinfo("Tamam", f"{len(sat)} kayıt aktarıldı:\n{p}")

    # ---------- yedek ----------
    def acilis(s):
        s.acilis_yedek()
        if not ayar("ucret_bicim_v1"):  # eski kayıtlardaki ücretleri bir kez tek biçime çevir
            n = 0
            for i, u in q("SELECT id, alinan_ucret FROM kayit"):
                yeni = para_bicim(u or "")
                if yeni != (u or ""):
                    q("UPDATE kayit SET alinan_ucret=? WHERE id=?", (yeni, i))
                    n += 1
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("ucret_bicim_v1", "1"))
            if n:
                s.load()
                messagebox.showinfo("Ücret biçimi", f"{n} kaydın alınan ücreti tek biçime (9.500,00 ₺) çevrildi.")
        if not ayar("tarih_bicim_v1"):  # eski kayıtlardaki tarihleri bir kez tek biçime çevir
            n = bozuk = 0
            sut = list(DATES) + ["durum_tarihi"]
            for r in q(f"SELECT id,{','.join(sut)} FROM kayit"):
                eski = [x or "" for x in r[1:]]
                yeni = [tarih_bicim(x) for x in eski]
                bozuk += sum(1 for x in yeni if x and not tarih_oku(x))
                if yeni != eski:
                    q(f"UPDATE kayit SET {','.join(k + '=?' for k in sut)} WHERE id=?", yeni + [r[0]])
                    n += 1
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("tarih_bicim_v1", "1"))
            if n or bozuk:
                s.load()
                msg = f"{n} kaydın tarihleri tek biçime (13.10.2026) çevrildi."
                if bozuk:
                    msg += f"\n\n{bozuk} tarih anlaşılamadığı için olduğu gibi bırakıldı; tabloda gözle kontrol etmenizi öneririm."
                messagebox.showinfo("Tarih biçimi", msg)
        if not ayar("islem_birlestir_v1"):  # yinelenen işlem adlarını (tevhit-ifraz / tevhit - ifraz gibi) bir kez birleştir
            g = benzer_gruplar("islem", "islem", True)
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("islem_birlestir_v1", "1"))
            if g:
                benzer_uygula("islem", "islem", g)
                s.load()
                messagebox.showinfo("İşlem adları", "Yinelenen işlem adları birleştirildi, kayıtlar güncellendi:\n\n" + benzer_ozet(g))

    def acilis_yedek(s):
        kl = yedek_klasor()
        bugun = os.path.join(kl, f"imar_kayitlari_{datetime.date.today():%Y-%m-%d}.db")
        if not os.path.exists(bugun):
            try:
                yedekle()
            except Exception as ex:
                messagebox.showwarning("Yedek alınamadı", f"Otomatik yedek alınamadı:\n{ex}\n\nYedek klasörünü Yedek menüsünden değiştirebilirsiniz.")

    def kapat(s):
        s.edit_kapat()
        try:
            s.ayar_kaydet()
        except Exception:
            pass
        try:
            yedekle()
        except Exception:
            pass
        s.root.destroy()

    def yedek_simdi(s):
        try:
            messagebox.showinfo("Yedek", "Yedek alındı:\n" + yedekle())
        except Exception as ex:
            messagebox.showerror("Hata", f"Yedek alınamadı:\n{ex}")

    def yedek_klasoru_sec(s):
        p = filedialog.askdirectory(title="Yedek klasörü (örn. ağdaki bir klasör)", initialdir=yedek_klasor())
        if p:
            q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("yedek_klasor", p))
            messagebox.showinfo("Yedek", "Yedek klasörü ayarlandı:\n" + p)

    def yedek_geri_yukle(s):
        kl = yedek_klasor()
        p = filedialog.askopenfilename(title="Geri yüklenecek yedeği seçin", initialdir=kl if os.path.isdir(kl) else BASE,
                                       filetypes=[("Veritabanı", "*.db")])
        if not p:
            return
        try:
            sqlite3.connect(p).execute("SELECT COUNT(*) FROM kayit").fetchone()
        except Exception:
            messagebox.showerror("Hata", "Seçilen dosya geçerli bir kayıt yedeği değil.")
            return
        if not messagebox.askyesno("Geri yükle", "Şu anki kayıtların yerine seçtiğiniz yedek yüklenecek.\n"
                                   "(Mevcut hâliniz önce ayrı bir dosya olarak saklanır.) Devam edilsin mi?"):
            return
        try:
            yedekle("geri_yukleme_oncesi_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            db_kopyala(p, DB)
            init_db()
            s.undo_temizle()
            s.load()
            messagebox.showinfo("Tamam", "Yedek geri yüklendi.")
        except Exception as ex:
            messagebox.showerror("Hata", f"Geri yükleme başarısız:\n{ex}")

    # ---------- satır işlemleri ----------
    def sec(s):
        x = s.tv.selection()
        if not x:
            messagebox.showinfo("Uyarı", "Önce bir satır seçin.")
        elif len(x) > 1:
            messagebox.showinfo("Uyarı", "Bu işlem için tek bir satır seçin.")
            return None
        return int(x[0]) if x else None

    def yeni(s): Form(s)

    def duzenle(s):
        i = s.sec()
        if i: Form(s, i)

    def sil(s):
        ids = s.sel_ids()
        if not ids:
            messagebox.showinfo("Uyarı", "Önce silinecek satır(lar)ı seçin.")
            return
        msg = ("Kayıt silinsin mi?" if len(ids) == 1 else f"{len(ids)} kayıt silinsin mi?") + \
            "\n\n(Veri > Son silinenler bölümünden 90 gün içinde geri getirebilirsiniz.)"
        if messagebox.askyesno("Sil", msg):
            snap = kayit_snapshot(ids)
            zaman = kayit_sil(ids)
            s.undo_push(f"Silme ({len(ids)} kayıt)", snap, zaman)
            s.load()

    def ok_yenile(s, iid, tur):
        if s.tv.exists(str(iid)):
            r = q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (int(iid),))[0]
            s.tv.set(str(iid), tur + "_ok", dosya_isaret(tur, {tur + "_no": r[0] or "", tur + "_dosya": r[1] or ""},
                                                          dosya_indeksi(ayar(tur + "_klasor"))))

    def dosya_sec(s, tur, i=None):
        """Dosyayı yüklemez; yalnızca seçilen dosyanın yolunu kayda işler."""
        i = i or s.sec()
        if not i:
            return None
        ad = "Karar" if tur == "karar" else "Makbuz"
        p = dosya_sec_dialog(tur)
        if not p:
            return None
        s.undo_onceki("Dosya yolu seçimi", [i])
        q(f"UPDATE kayit SET {tur}_dosya=? WHERE id=?", (p, i))
        dosya_cache_temizle()
        s.ok_yenile(i, tur)
        return p

    def ac(s, tur):
        i = s.sec()
        if not i:
            return
        ad = "Karar" if tur == "karar" else "Makbuz"
        no, dosya = q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (i,))[0]
        no, dosya = no or "", dosya or ""
        p = dosya if dosya and os.path.exists(dosya) else find_file(ayar(tur + "_klasor"), no)
        if p:
            open_file(p)
            return
        if dosya:
            mesaj = f"Kayıtlı dosya bulunamadı (taşınmış, silinmiş veya ağa ulaşılamıyor olabilir):\n{dosya}\n\nYeni dosya seçmek ister misiniz?"
        else:
            mesaj = f"Bu kayıt için {ad.lower()} dosyası tanımlı değil.\n\nŞimdi bir dosya seçmek ister misiniz? (Dosya yüklenmez, sadece yolu kaydedilir.)"
        if messagebox.askyesno(f"{ad} dosyası", mesaj):
            yeni = s.dosya_sec(tur, i)
            if yeni:
                open_file(yeni)

    def klasorler(s):
        for tur, ad in [("karar", "Karar dosyalarının klasörü"), ("makbuz", "Makbuz dosyalarının klasörü")]:
            messagebox.showinfo("Klasör (isteğe bağlı)", ad + " seçilecek.\nBu ayar yalnızca dosya yolu elle seçilmemiş kayıtlar için, dosya adı karar/makbuz numarasıyla (ör. 599.pdf) eşleşirse kullanılır.")
            p = filedialog.askdirectory(title=ad)
            if p:
                q("INSERT OR REPLACE INTO ayar VALUES (?,?)", (tur + "_klasor", p))
        dosya_cache_temizle()
        s.load()

    def csv_al(s):
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        idx = {}
        for i, h in enumerate(rows[0] if rows else []):
            k = HDR.get(tr_lower(temiz(h)))
            if k and k not in idx:
                idx[k] = i
        if "mahalle" not in idx:
            messagebox.showerror("Hata", "Başlık satırı bulunamadı (MAHALLE sütunu yok).")
            return
        if q("SELECT 1 FROM kayit LIMIT 1") and messagebox.askyesno(
                "CSV Al", "Mevcut kayıtlar silinip dosyadaki kayıtlar yeniden yüklensin mi?\n(Hayır: mevcut kayıtlara eklenir)"):
            kayit_sil([r[0] for r in q("SELECT id FROM kayit")])
        n = 0
        for r in rows[1:]:
            d = {k: (temiz(r[i]) if i < len(r) else "") for k, i in idx.items()}
            if d.get("alinan_ucret"):
                d["alinan_ucret"] = para_bicim(d["alinan_ucret"])
            for dk in DATES:
                if d.get(dk):
                    d[dk] = tarih_bicim(d[dk])
            if not any(d.values()):
                continue
            q(f"INSERT INTO kayit ({','.join(d)}) VALUES ({','.join('?' * len(d))})", list(d.values()))
            for tur in LT:
                if d.get(tur):
                    q("INSERT OR IGNORE INTO liste VALUES (?,?)", (tur, d[tur]))
            n += 1
        g = benzer_gruplar("islem", "islem", True)
        if g:
            benzer_uygula("islem", "islem", g)
        s.undo_temizle()
        s.load()
        messagebox.showinfo("Tamam", f"{n} kayıt aktarıldı." + (f"\n{len(g)} yinelenen işlem adı birleştirildi." if g else ""))

    def csv_aktar(s):
        p = filedialog.asksaveasfilename(defaultextension=".csv")
        if p:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([LAB[k] for k in KEYS])
                w.writerows(q(f"SELECT {','.join(KEYS)} FROM kayit ORDER BY id"))


if __name__ == "__main__":
    init_db()
    App().root.mainloop()
