# -*- coding: utf-8 -*-
"""
Encümen İş Takip - PySide6 arayüzü, 3. AŞAMA: Takvim, Grafikler sekmesi, Fen Klasörü sekmesi,
Fen işlemi penceresi (FenIslemDialog) ve parsel hareket listesi (ZincirDetay + zincir grafiği).

Bu dosya yalnızca ARAYÜZÜ ve ÇİZİMİ içerir. Hesaplamalar ve veritabanı işleri eski encumen_kayit.py içinden
aynen çağrılır (aylik_seri, zincir_modeli, fen_ara_sorgu, fen_kayit_ekle, fen_kayit_guncelle, fen_sil_kayit, fen_senkronla ...).
Veritabanı yapısı değişmez.

Ana pencereden (AnaPencere) şunlar kullanılır: app.ListeFiltreleriSinif, app.TarihAraligiSinif, app.AramaliComboSinif,
app.tum_kayitlar, app.bilgi / uyari / hata / sor, app.pasif_liste_ac, app.zincir_detay, app.takvim_sec
"""
import math
import calendar
import datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import encumen_kayit as ek


# ================================================================ ortak yardımcılar
def renk(ad):
    """Geçerli temadaki renk (ek.METIN gibi). Tema değişince ek içindeki değerler güncellenir."""
    return QtGui.QColor(getattr(ek, ad))


def yaz(p, x, y, metin, renk_kodu, boyut=9, kalin=False, hiza="w"):
    """Tk'deki create_text karşılığı: (x, y) noktasına dikey ortalı yazı. hiza: w=sola, e=sağa, c=ortala yaslı."""
    f = QtGui.QFont("Segoe UI")
    f.setPointSize(boyut)
    f.setBold(kalin)
    p.setFont(f)
    p.setPen(QtGui.QColor(renk_kodu))
    fm = p.fontMetrics()
    gen = fm.horizontalAdvance(metin)
    x0 = x if hiza == "w" else (x - gen if hiza == "e" else x - gen / 2)
    p.drawText(QtCore.QPointF(x0, y + fm.ascent() - fm.height() / 2), metin)


def _dugme(metin, fonk, ad=""):
    b = QtWidgets.QPushButton(metin)
    if ad:
        b.setObjectName(ad)
    b.setAutoDefault(False)
    b.setDefault(False)
    b.clicked.connect(lambda _=False, f=fonk: f())
    return b


# ================================================================ Takvim (gün / yıl / ay seçimli)
class TakvimAlan(QtWidgets.QWidget):
    def __init__(self, tk):
        super().__init__()
        self.tk = tk
        self.setMouseTracking(True)
        self.setFixedSize(7 * tk.CW, tk.UST + 6 * tk.CH)
        self.hucre = []
        self.hover = None

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), renk("KART"))
        p.setPen(renk("KENAR"))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        self.hucre = []
        t = self.tk
        if t.mod == "gun":
            self._gun(p)
        elif t.mod == "yil":
            self._izgara(p, [(y, str(y)) for y in range(t.yil_bas, t.yil_bas + 12)], "yil",
                         lambda y: y == t.yil, lambda y: y == t.bugun.year)
        else:
            self._izgara(p, [(i + 1, ad) for i, ad in enumerate(t.KISA)], "ay",
                         lambda m: m == t.ay, lambda m: t.yil == t.bugun.year and m == t.bugun.month)

    def _daire(self, p, cx, cy, r):
        p.drawEllipse(QtCore.QPointF(cx, cy), r, r)

    def _kutu(self, p, cx, cy):
        p.drawRect(QtCore.QRectF(cx - 30, cy - 17, 60, 34))

    def _gun(self, p):
        t = self.tk
        for c, g in enumerate(t.GUNLER):
            yaz(p, c * t.CW + t.CW / 2, t.UST / 2, g, ek.SOLUK, 9, True, "c")
        for r, hafta in enumerate(calendar.monthcalendar(t.yil, t.ay)):
            for c, g in enumerate(hafta):
                if not g:
                    continue
                cx, cy = c * t.CW + t.CW / 2, t.UST + r * t.CH + t.CH / 2
                secili = (t.yil, t.ay, g) == t.secili
                bugun = (t.yil, t.ay, g) == (t.bugun.year, t.bugun.month, t.bugun.day)
                if self.hover and self.hover[0] == "gun" and self.hover[1] == g and not secili:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(renk("TAKV1"))
                    self._daire(p, cx, cy, 14)
                if secili:
                    p.setPen(renk("VURGU"))
                    p.setBrush(renk("VURGU"))
                    self._daire(p, cx, cy, 14)
                if bugun:
                    p.setPen(QtGui.QPen(QtGui.QColor(t.BUGUN), 2))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    self._daire(p, cx, cy, 16 if secili else 15)
                yaz(p, cx, cy, str(g), "#ffffff" if secili else ek.METIN, 10, bugun, "c")
                self.hucre.append((cx - t.CW / 2, cy - t.CH / 2, cx + t.CW / 2, cy + t.CH / 2, ("gun", g, secili)))

    def _izgara(self, p, adlar, tur, secili_mi, bugun_mu):
        t = self.tk
        w, h = 7 * t.CW / 4, (t.UST + 6 * t.CH) / 3
        for i, (deger, ad) in enumerate(adlar):
            r, c = divmod(i, 4)
            cx, cy = c * w + w / 2, r * h + h / 2
            sec = secili_mi(deger)
            if self.hover and self.hover[0] == tur and self.hover[1] == deger and not sec:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(renk("TAKV2"))
                self._kutu(p, cx, cy)
            if sec:
                p.setPen(renk("VURGU"))
                p.setBrush(renk("VURGU"))
                self._kutu(p, cx, cy)
            if bugun_mu(deger):
                p.setPen(QtGui.QPen(QtGui.QColor(t.BUGUN), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                self._kutu(p, cx, cy)
            yaz(p, cx, cy, ad, "#ffffff" if sec else ek.METIN, 10, False, "c")
            self.hucre.append((c * w, r * h, c * w + w, r * h + h, (tur, deger, sec)))

    def bul(self, x, y):
        for x0, y0, x1, y1, a in self.hucre:
            if x0 <= x < x1 and y0 <= y < y1:
                return a
        return None

    def mouseMoveEvent(self, e):
        a = self.bul(e.position().x(), e.position().y())
        self.setCursor(Qt.CursorShape.PointingHandCursor if a else Qt.CursorShape.ArrowCursor)
        yeni = (a[0], a[1]) if a else None
        if yeni != self.hover:
            self.hover = yeni
            self.update()

    def leaveEvent(self, e):
        self.hover = None
        self.update()

    def mousePressEvent(self, e):
        a = self.bul(e.position().x(), e.position().y())
        if not a:
            return
        t = self.tk
        if a[0] == "gun":
            t.sec(a[1], t.ay, t.yil)
        elif a[0] == "yil":
            t.yil, t.mod = a[1], "ay"
            t.ciz()
        else:
            t.ay, t.mod = a[1], "gun"
            t.ciz()


class Takvim(QtWidgets.QDialog):
    """Gün / yıl / ay seçimli takvim. Başlığa (örn. "Ekim 2026") tıklayınca yıl, sonra ay seçilir.
    Bugün turuncu halkayla, seçili gün mavi daireyle gösterilir.
    Sonuç: self.sonuc  (None = iptal, '' = temizle, 'gg.aa.yyyy' = seçilen tarih; ayraç ayrac ile verilir)."""
    AYLAR = "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split()
    KISA = "Oca Şub Mar Nis May Haz Tem Ağu Eyl Eki Kas Ara".split()
    GUNLER = "Pzt Sal Çar Per Cum Cmt Paz".split()
    CW, CH, UST = 42, 36, 28
    BUGUN = "#f59e0b"

    def __init__(self, parent, deger="", ayrac="."):
        super().__init__(parent)
        self.setWindowTitle("Tarih Seç")
        self.setModal(True)
        self.ayrac, self.sonuc = ayrac, None
        self.bugun = datetime.date.today()
        d = ek.tarih_oku(deger)
        if d:
            self.yil, self.ay, self.secili = d.year, d.month, (d.year, d.month, d.day)
        else:
            self.yil, self.ay, self.secili = self.bugun.year, self.bugun.month, None
        self.mod, self.yil_bas = "gun", self.yil - 5
        v = QtWidgets.QVBoxLayout(self)
        h = QtWidgets.QHBoxLayout()
        self.dugme = []
        for i in range(5):
            b = QtWidgets.QPushButton()
            b.setAutoDefault(False)
            b.clicked.connect(lambda _=False, i=i: self._tikla(i))
            self.dugme.append(b)
            h.addWidget(b, 1 if i == 2 else 0)
            if i != 2:
                b.setFixedWidth(38)
        v.addLayout(h)
        self.alan = TakvimAlan(self)
        v.addWidget(self.alan, alignment=Qt.AlignmentFlag.AlignHCenter)
        alt = QtWidgets.QHBoxLayout()
        alt.addStretch(1)
        for ad, f in (("Bugün", lambda: self.sec(self.bugun.day, self.bugun.month, self.bugun.year)),
                      ("Temizle", self._temizle), ("İptal", self.reject)):
            alt.addWidget(_dugme(ad, f))
        alt.addStretch(1)
        v.addLayout(alt)
        self.ciz()

    def _tikla(self, i):
        t = self._tanim[i]
        if t:
            t[1]()

    def kay(self, dy, dm):
        a = self.ay - 1 + dm + 12 * dy
        self.yil += a // 12
        self.ay = a % 12 + 1
        self.ciz()

    def yil_ac(self):
        self.mod, self.yil_bas = "yil", self.yil - 5
        self.ciz()

    def gun_ac(self):
        self.mod = "gun"
        self.ciz()

    def yil_kay(self, d):
        self.yil_bas += d
        self.ciz()

    def yil_deg(self, d):
        self.yil += d
        self.ciz()

    def sec(self, g, a, y):
        self.sonuc = f"{g:02d}{self.ayrac}{a:02d}{self.ayrac}{y}"
        self.accept()

    def _temizle(self):
        self.sonuc = ""
        self.accept()

    def ciz(self):
        if self.mod == "gun":
            self._tanim = [("«", lambda: self.kay(-1, 0)), ("‹", lambda: self.kay(0, -1)),
                           (f"{self.AYLAR[self.ay - 1]} {self.yil}  ▾", self.yil_ac),
                           ("›", lambda: self.kay(0, 1)), ("»", lambda: self.kay(1, 0))]
        elif self.mod == "yil":
            self._tanim = [None, ("‹", lambda: self.yil_kay(-12)), (f"{self.yil_bas} – {self.yil_bas + 11}", self.gun_ac),
                           ("›", lambda: self.yil_kay(12)), None]
        else:
            self._tanim = [None, ("‹", lambda: self.yil_deg(-1)), (f"{self.yil}  ▾", self.yil_ac),
                           ("›", lambda: self.yil_deg(1)), None]
        for b, t in zip(self.dugme, self._tanim):
            b.setVisible(bool(t))
            b.setText(t[0] if t else "")
        self.alan.hover = None
        self.alan.update()


def takvim_sec(ust, metin="", ayrac="."):
    """None: iptal, '': temizle, 'gg.aa.yyyy': seçilen tarih."""
    dlg = Takvim(ust, metin, ayrac)
    dlg.exec()
    return dlg.sonuc


# ================================================================ grafik çizimleri (QPainter)
class GrafikKutu(QtWidgets.QWidget):
    """Çizimi dışarıdan verilen fonksiyonla yapan kutu: ciz(painter, genişlik, yükseklik)."""

    def __init__(self, ciz, min_yukseklik=150):
        super().__init__()
        self.ciz = ciz
        self.setMinimumSize(220, min_yukseklik)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), renk("KART"))
        p.setPen(renk("KENAR"))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        self.ciz(p, self.width(), self.height())


def dikey_bar(p, w, h, baslik, aylar, deger, fmt, bar_renk):
    if w < 140 or h < 110:
        return
    yaz(p, 12, 16, baslik, ek.METIN, 11, True)
    sol, sag, ust, alt = 52, 14, 40, 44
    gw, gh = w - sol - sag, h - ust - alt
    ust_sinir = ek.guzel_ust(max(deger) if deger else 0)
    for i in range(5):  # yatay kılavuz çizgileri ve eksen değerleri
        y = ust + gh * (1 - i / 4)
        p.setPen(renk("KENAR"))
        p.drawLine(QtCore.QPointF(sol, y), QtCore.QPointF(w - sag, y))
        yaz(p, sol - 6, y, fmt(ust_sinir * i / 4), ek.SOLUK, 8, False, "e")
    n = max(len(deger), 1)
    bw = gw / n
    cubuk = bw * 0.62
    bugun = datetime.date.today()
    for i, (a, v) in enumerate(zip(aylar, deger)):
        x0 = sol + i * bw + (bw - cubuk) / 2
        y0 = ust + gh * (1 - v / ust_sinir)
        if v > 0:
            p.fillRect(QtCore.QRectF(x0, y0, cubuk, ust + gh - y0), QtGui.QColor(bar_renk))
            if bw >= 34:
                yaz(p, x0 + cubuk / 2, y0 - 8, fmt(v), ek.SOLUK, 8, False, "c")
        if bw >= 34 or i % 2 == 0 or i == n - 1:
            bu_ay = a == (bugun.year, bugun.month)
            yaz(p, x0 + cubuk / 2, ust + gh + 12, Takvim.KISA[a[1] - 1], "#f59e0b" if bu_ay else ek.METIN, 8, bu_ay, "c")
            if i == 0 or a[1] == 1:
                yaz(p, x0 + cubuk / 2, ust + gh + 27, str(a[0]), ek.SOLUK, 8, False, "c")
    p.setPen(renk("SOLUK"))
    p.drawLine(QtCore.QPointF(sol, ust + gh), QtCore.QPointF(w - sag, ust + gh))


def yatay_bar(p, w, h, baslik, veri, fmt, sol=140, maks=20):
    if w < 80 or h < 60:
        return
    yaz(p, 12, 16, baslik, ek.METIN, 11, True)
    if not veri:
        yaz(p, w / 2, h / 2, "Veri yok", "#888888", 9, False, "c")
        return
    mx = max(v for _, v in veri) or 1
    sag, ust = 95, 32
    bh = min(28, (h - ust - 8) / len(veri))
    for i, (ad, v) in enumerate(veri):
        y = ust + i * bh
        uz = max((w - sol - sag) * v / mx, 1)
        yaz(p, sol - 6, y + bh / 2, ad[:maks], ek.METIN, 9, False, "e")
        p.fillRect(QtCore.QRectF(sol, y + 2, uz, bh - 4), QtGui.QColor(ek.RENK[0]))
        yaz(p, sol + uz + 5, y + bh / 2, fmt(v), ek.SOLUK, 9)


def pasta(p, w, h, baslik, veri):
    if w < 80 or h < 80:
        return
    yaz(p, 12, 16, baslik, ek.METIN, 11, True)
    if not veri:
        yaz(p, w / 2, h / 2, "Veri yok", "#888888", 9, False, "c")
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
    kutu = QtCore.QRectF(cx - r, y0, 2 * r, 2 * r)
    p.setPen(QtGui.QColor("white"))
    if len(veri) == 1:
        p.setBrush(QtGui.QColor(ek.RENK[0]))
        p.drawEllipse(kutu)
    else:
        bas = 90.0
        for i, (_, v) in enumerate(veri):
            ext = -360 * v / toplam
            p.setBrush(QtGui.QColor(ek.RENK[i % len(ek.RENK)]))
            p.drawPie(kutu, int(bas * 16), int(ext * 16))
            bas += ext
    lx, ly = (cx + r + 30, 44) if yan else (20, y0 + 2 * r + 16)
    for i, (ad, v) in enumerate(veri):
        y = ly + i * 20
        p.fillRect(QtCore.QRectF(lx, y, 12, 12), QtGui.QColor(ek.RENK[i % len(ek.RENK)]))
        yaz(p, lx + 20, y + 6, f"{ad[:22]}: {v} iş (%{100 * v / toplam:.0f})", ek.METIN, 9)


class GrafiklerSekmesi(QtWidgets.QWidget):
    """Grafikler sekmesi: yalnızca bu sayfadaki filtreler grafikleri etkiler (ana tablodaki filtrelerden bağımsız)."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.gdata = {"harc": [], "tek": [], "mahalle": [], "muellif": [], "aylik": ([], [], [])}
        self.trend_rows = []
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(6, 8, 6, 4)
        f1 = QtWidgets.QHBoxLayout()
        self.glf = app.ListeFiltreleriSinif(f1, self.guncelle)
        f1.addWidget(_dugme("Filtreleri Temizle", self.temizle))
        f1.addStretch(1)
        v.addLayout(f1)
        self.gta = app.TarihAraligiSinif(self.guncelle)
        v.addWidget(self.gta)
        ac = QtWidgets.QLabel("Bu sayfadaki filtreler yalnızca grafikleri etkiler. Varsayılan olarak tüm işler "
                              "(Tescillendi, Askıda Kaldı ve İptal dahil) hesaba katılır.")
        ac.setWordWrap(True)
        v.addWidget(ac)
        self.gnb = QtWidgets.QTabWidget()
        v.addWidget(self.gnb, 1)

        genel = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(genel)
        tl = lambda x: ek.para_yaz(x, 0)
        self.c1 = GrafikKutu(lambda p, w, h: yatay_bar(p, w, h, "Müellife göre toplam harç", self.gdata["harc"], tl))
        self.c4 = GrafikKutu(lambda p, w, h: yatay_bar(p, w, h, "En yüksek tekil harçlar (ilk 10)", self.gdata["tek"], tl, sol=270, maks=42))
        self.c2 = GrafikKutu(lambda p, w, h: yatay_bar(p, w, h, "Mahalle bazlı iş sayısı (ilk 12)", self.gdata["mahalle"], lambda x: str(x)))
        self.c3 = GrafikKutu(lambda p, w, h: pasta(p, w, h, "Müellife göre iş sayısı", self.gdata["muellif"]))
        g.addWidget(self.c1, 0, 0)
        g.addWidget(self.c4, 0, 1)
        g.addWidget(self.c2, 1, 0)
        g.addWidget(self.c3, 1, 1)
        self.gnb.addTab(genel, "Genel")

        trend = QtWidgets.QWidget()
        tv = QtWidgets.QVBoxLayout(trend)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(QtWidgets.QLabel("Dönem:"))
        self.donem = QtWidgets.QComboBox()
        self.donem.addItems(list(ek.DONEMLER))
        self.donem.activated.connect(lambda _: self.trend_degisti())
        h.addWidget(self.donem)
        h.addWidget(QtWidgets.QLabel("Müellif, mahalle, işlem ve durum filtreleri uygulanır; tarih aralığı yerine bu dönem kullanılır."))
        h.addStretch(1)
        tv.addLayout(h)
        satir = QtWidgets.QHBoxLayout()

        def sayi(x):
            return str(int(x)) if x == int(x) else f"{x:.1f}"
        self.c5 = GrafikKutu(lambda p, w, h: dikey_bar(p, w, h, "Aylık iş sayısı (encümen tarihine göre)",
                                                      self.gdata["aylik"][0], self.gdata["aylik"][1], sayi, ek.VURGU))
        self.c6 = GrafikKutu(lambda p, w, h: dikey_bar(p, w, h, "Aylık tahsil edilen harç (makbuz tarihine göre, B = bin ₺)",
                                                      self.gdata["aylik"][0], self.gdata["aylik"][2], ek.kisa_para, "#10b981"))
        satir.addWidget(self.c5)
        satir.addWidget(self.c6)
        tv.addLayout(satir, 1)
        self.gnb.addTab(trend, "Aylık trend")

    def kutular(self):
        return (self.c1, self.c2, self.c3, self.c4, self.c5, self.c6)

    def ciz_hepsi(self):
        for c in self.kutular():
            c.update()

    def temizle(self):
        self.glf.temizle()
        self.gta.temizle()
        self.guncelle()

    def guncelle(self, tum=None):
        if tum is None:
            tum = self.app.tum_kayitlar()
        harc, mah, mue, tek, trend = {}, {}, {}, [], []
        for _, d in tum:
            if self.glf.uygun(d):
                trend.append(d)
            if not (self.glf.uygun(d) and self.gta.uygun(d)):
                continue
            m = d["muellif"] or "(Belirtilmemiş)"
            u = ek.para(d["alinan_ucret"])
            harc[m] = harc.get(m, 0) + u
            mue[m] = mue.get(m, 0) + 1
            if d["mahalle"]:
                mah[d["mahalle"]] = mah.get(d["mahalle"], 0) + 1
            if u > 0:
                tek.append((f"{m} · {d['mahalle']} {d['ada_parsel']}".strip(), u))
        sirali = lambda x: sorted(x.items(), key=lambda t: (-t[1], ek.tr_sira(t[0])))
        self.gdata = {"harc": [t for t in sirali(harc) if t[1] > 0][:12],
                      "tek": sorted(tek, key=lambda t: (-t[1], ek.tr_sira(t[0])))[:10],
                      "mahalle": sirali(mah)[:12], "muellif": sirali(mue), "aylik": ([], [], [])}
        self.trend_rows = trend
        self.trend_hesapla()
        self.ciz_hepsi()

    def trend_hesapla(self):
        self.gdata["aylik"] = ek.aylik_seri(self.trend_rows, self.donem.currentText() or ek.DONEMLER[0], datetime.date.today())

    def trend_degisti(self):
        self.trend_hesapla()
        self.ciz_hepsi()


# ================================================================ parsel zinciri (eski -> yeni) grafiği
def zincir_ciz(p, w, dugum, kenar, vurgu="", y0=40):
    """encumen_kayit.zincir_grafik_ciz'in QPainter karşılığı (yerleşim algoritması aynıdır)."""
    w = max(w, 560)
    if not dugum:
        yaz(p, w / 2, 90, "Grafik için parsel bilgisi yok", ek.SOLUK, 9, False, "c")
        return
    gelen = {n: [] for n in dugum}
    for a, b in kenar:
        if a in gelen and b in gelen:
            gelen[b].append(a)
    seviye = {n: 0 for n in dugum if not gelen[n]}
    for _ in range(len(dugum) + 1):  # en uzun yola göre seviye
        degisti = False
        for a, b in kenar:
            if a in seviye and b in dugum and seviye.get(b, -1) < seviye[a] + 1 and seviye[a] < len(dugum):
                seviye[b] = seviye[a] + 1
                degisti = True
        if not degisti:
            break
    for n in dugum:
        seviye.setdefault(n, 0)
    satirlar = {}
    for n in dugum:
        satirlar.setdefault(seviye[n], []).append(n)
    konum = {}
    for sv, liste_ in satirlar.items():
        for i, n in enumerate(liste_):
            konum[n] = (w * (i + 1) / (len(liste_) + 1), y0 + sv * 70)
    kalem = QtGui.QPen(renk("SOLUK"), 2)
    for a, b in kenar:
        if a in konum and b in konum:
            (x1, y1), (x2, y2) = konum[a], konum[b]
            bx, by, sx, sy = x1, y1 + 16, x2, y2 - 16
            p.setPen(kalem)
            p.drawLine(QtCore.QPointF(bx, by), QtCore.QPointF(sx, sy))
            aci = math.atan2(sy - by, sx - bx)  # ok başı
            ok = QtGui.QPolygonF([QtCore.QPointF(sx, sy),
                                  QtCore.QPointF(sx - 10 * math.cos(aci - 0.4), sy - 10 * math.sin(aci - 0.4)),
                                  QtCore.QPointF(sx - 10 * math.cos(aci + 0.4), sy - 10 * math.sin(aci + 0.4))])
            p.setBrush(renk("SOLUK"))
            p.drawPolygon(ok)
    for n, (x, y) in konum.items():
        d = dugum[n]
        dolgu, yazi = (ek.KENAR, ek.METIN) if d == "Pasif" else ("#4d7c0f", "#ffffff") if d == "Aktif" else (ek.KART, ek.SOLUK)
        secili = n == vurgu
        kalem2 = QtGui.QPen(renk("VURGU") if secili else renk("SOLUK"), 3 if secili else 1)
        if d == "Pasif*":
            kalem2.setStyle(Qt.PenStyle.DashLine)
        p.setPen(kalem2)
        p.setBrush(QtGui.QColor(dolgu))
        p.drawRect(QtCore.QRectF(x - 46, y - 16, 92, 32))
        yaz(p, x, y, ek.no_etiket(n) + ("*" if d == "Pasif*" else ""), yazi, 10, False, "c")
    if "Pasif*" in dugum.values():
        yaz(p, w / 2, y0 + (max(seviye.values()) + 1) * 70 - 10,
            "* iş kaydında yazılı, sorgulanmadı; tevhitle birleşmiş sayıldı", ek.SOLUK, 9, False, "c")


class ZincirGrafik(QtWidgets.QWidget):
    """Seçili parsel zincirini çizen küçük bileşen. Fen Klasörü sekmesi ve hareket listesi penceresi kullanır."""

    def __init__(self, yukseklik=0):
        super().__init__()
        self.durum = None  # (başlık, dugum, kenar, vurgu, y0) | bos metin
        self.bos = ""
        if yukseklik:
            self.setFixedHeight(yukseklik)
        else:
            self.setMinimumHeight(200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

    def goster(self, dugum, kenar, vurgu="", baslik="", y0=40):
        self.durum = (baslik, dugum, kenar, vurgu, y0)
        self.update()

    def bos_goster(self, metin):
        self.durum = None
        self.bos = metin
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), renk("KART"))
        p.setPen(renk("KENAR"))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        if self.durum is None:
            if self.bos:
                yaz(p, max(self.width(), 600) / 2, 100, self.bos, ek.SOLUK, 9, False, "c")
            return
        baslik, dugum, kenar, vurgu, y0 = self.durum
        if baslik:
            yaz(p, 12, 14, baslik, ek.METIN, 10, True)
        zincir_ciz(p, self.width(), dugum, kenar, vurgu, y0)


# ================================================================ parsel hareket listesi (Özet / Tablo / Grafik)
class ZincirDetay(QtWidgets.QDialog):
    """Parsel Sorgu'daki 'hareket listesi' gibi Özet / Tablo / Grafik. Veriler İş Takip veritabanından gelir (ağ isteği yok)."""

    def __init__(self, app, k):
        super().__init__(app)
        self.app, self.k = app, k
        self.z = ek.zincir_coz(k.get("zincir"))
        ilk = f"{k['eski'][0][0]}/{k['eski'][0][1]}" if k.get("eski") else ""
        self.no = (self.z["kok"]["no"] if self.z else "") or k.get("parsel_no") or ilk
        self.setWindowTitle(f"{ek.no_etiket(self.no)} parsel hareket listesi")
        self.resize(900, 560)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        bant = QtWidgets.QLabel(f"{ek.no_etiket(self.no)} parsel hareket listesi  ·  {k.get('mahalle') or ''}")
        bant.setStyleSheet(f"background:{ek.VURGU_K}; color:#ffffff; font-size:14pt; padding:11px 16px;")
        v.addWidget(bant)
        nb = QtWidgets.QTabWidget()
        v.addWidget(nb, 1)
        nb.addTab(self._ozet(), "Özet")
        nb.addTab(self._tablo(), "Tablo")
        g = QtWidgets.QWidget()
        gv = QtWidgets.QVBoxLayout(g)
        gv.setContentsMargins(0, 0, 0, 0)
        self.graf = ZincirGrafik()
        gv.addWidget(self.graf)
        nb.addTab(g, "Grafik")
        dugum, kenar = ek.zincir_modeli(self.z, k.get("eski", []), k.get("yeni", []))
        self.graf.goster(dugum, kenar, self.no)

    def _liste(self, anahtar):
        return ", ".join(ek.parsel_etiket(a, p) for a, p in self.k.get(anahtar, [])) or "–"

    def _ozet(self):
        k = self.k
        f = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(f)
        v.setContentsMargins(18, 18, 18, 10)
        mesaj = k.get("aciklama") or ("Bu taşınmaz pasife alınmıştır." if k.get("durum") == "Pasif" else "Bu parsel aktif görünüyor.")
        m = QtWidgets.QLabel(mesaj)
        m.setWordWrap(True)
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        m.setStyleSheet(f"background:{ek.KART}; border:1px solid {ek.KENAR}; padding:16px;")
        v.addWidget(m)
        yeni_say = len(k.get("yeni", []))
        satir = [("Mahalle", k.get("mahalle") or "–"), ("Sorgulanan parsel", ek.no_etiket(self.no) or "–"),
                 ("Alan (m²) / Nitelik", f"{k.get('alan') or '–'} / {k.get('nitelik') or '–'}"),
                 ("İşlem", f"{k.get('tur') or '–'}  ({k.get('tarih') or '–'})"),
                 ("Eski parseller (iş kaydı + sorgu)", self._liste("eski")),
                 (f"Yeni (aktif) parseller ({yeni_say} adet)", self._liste("yeni")),
                 ("Kaynak", (k.get("kaynak") or "–") + (f"  ·  iş #{k['work_id']}" if k.get("work_id") else ""))]
        g = QtWidgets.QGridLayout()
        g.setContentsMargins(6, 10, 6, 0)
        for i, (ad, deger) in enumerate(satir):
            a = QtWidgets.QLabel(ad + ":")
            a.setStyleSheet("font-weight:bold;")
            d = QtWidgets.QLabel(deger)
            d.setWordWrap(True)
            d.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            g.addWidget(a, i, 0, Qt.AlignmentFlag.AlignTop)
            g.addWidget(d, i, 1)
        g.setColumnStretch(1, 1)
        g.setColumnMinimumWidth(0, 250)
        v.addLayout(g)
        v.addStretch(1)
        return f

    def _tablo(self):
        basl = [("Parsel", 110), ("Durum", 80), ("Alan (m²)", 90), ("Nitelik", 110), ("İşlem türü", 130), ("İşlem tarihi", 100),
                ("Açıklama", 260)]
        t = QtWidgets.QTableWidget(0, len(basl))
        t.setHorizontalHeaderLabels([a for a, _ in basl])
        for i, (_, w) in enumerate(basl):
            t.setColumnWidth(i, w)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        t.setShowGrid(False)

        def ekle(vals, soluk=False):
            n = t.rowCount()
            t.insertRow(n)
            for c, x in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(str(x))
                if soluk:
                    it.setForeground(QtGui.QBrush(renk("SOLUK")))
                t.setItem(n, c, it)
        var = set()
        if self.z:
            for p in [self.z["kok"]] + list(self.z.get("devam", [])):
                ekle((ek.no_etiket(p["no"]), p.get("durum") or "–", p.get("alan") or "–", p.get("nitelik") or "–",
                      p.get("islem_turu") or "–", p.get("islem_tarihi") or "–", p.get("aciklama") or "–"),
                     (p.get("durum") or "") in ("Pasif", "Pasif*"))
                var.add(p["no"])
            if "tevhit" in ek.tr_lower(self.z["kok"].get("islem_turu")):
                for a, pr in self.k.get("eski", []):
                    if f"{a}/{pr}" not in var:
                        ekle((f"{ek.parsel_etiket(a, pr)}*", "Pasif*", "–", "–", "–", "–",
                              "İş kaydında yazılı; sorgulanmadı, tevhitle birleşmiş sayıldı"), True)
        else:
            for a, pr in self.k.get("eski", []):
                ekle((ek.parsel_etiket(a, pr), "Pasif", "–", "–", self.k.get("tur") or "–", self.k.get("tarih") or "–", "–"), True)
            for a, pr in self.k.get("yeni", []):
                ekle((ek.parsel_etiket(a, pr), "Aktif", "–", "–", "–", "–", "–"))
        return t


# ================================================================ Fen işlemi ekle / düzenle
class FenIslemDialog(QtWidgets.QDialog):
    """Fen işlemi ekle / düzenle: eski ve yeni parseller kendi yazım biçiminizle girilir (örn. 728/1-2-9-10 -> 728/13)."""
    TURLER = ["Tevhit", "İfraz", "Tevhit-İfraz", "Yola terk", "İhdas", "İhdas-Tevhit", "Diğer"]

    def __init__(self, app, kayit=None):
        super().__init__(app)
        self.app, self.kayit = app, kayit
        self.setWindowTitle("Fen işlemini düzenle" if kayit else "Fen işlemi ekle")
        self.setModal(True)
        g = QtWidgets.QGridLayout(self)
        g.setContentsMargins(14, 12, 14, 12)
        g.setVerticalSpacing(6)

        def etiket(metin, satir):
            e = QtWidgets.QLabel(metin)
            e.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            g.addWidget(e, satir, 0)
        etiket("Mahalle", 0)
        self.mahalle = app.liste_combo("mahalle")
        self.mahalle.setMinimumWidth(330)
        g.addWidget(self.mahalle, 0, 1)
        etiket("İşlem türü", 1)
        self.tur = QtWidgets.QComboBox()
        self.tur.setEditable(True)
        self.tur.addItems(self.TURLER)
        self.tur.setEditText("")
        g.addWidget(self.tur, 1, 1)
        etiket("İşlem tarihi", 2)
        self.tarih = QtWidgets.QLineEdit()
        g.addWidget(self.tarih, 2, 1)
        g.addWidget(_dugme("Takvim", self.takvim), 2, 2)
        self.alan, self.ipucu = {}, {}
        for r, (k, ad) in enumerate((("eski", "Eski parseller"), ("yeni", "Yeni parseller")), 3):
            etiket(ad, r * 2 - 2)
            e = QtWidgets.QLineEdit()
            self.alan[k] = e
            g.addWidget(e, r * 2 - 2, 1)
            self.ipucu[k] = QtWidgets.QLabel("")
            self.ipucu[k].setWordWrap(True)
            g.addWidget(self.ipucu[k], r * 2 - 1, 1)
            e.textChanged.connect(lambda _, k=k: self.ipucu[k].setText(self.oku(k)))
        etiket("Açıklama", 7)
        self.aciklama = QtWidgets.QLineEdit()
        g.addWidget(self.aciklama, 7, 1)
        g.addWidget(_dugme("Kaydet", self.kaydet, "vurgu"), 8, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        if kayit:
            self.mahalle.setEditText(kayit["mahalle"])
            self.tur.setEditText(kayit["tur"])
            self.tarih.setText(kayit["tarih"])
            self.alan["eski"].setText(", ".join(ek.parsel_etiket(a, p) for a, p in kayit["eski"]))
            self.alan["yeni"].setText(", ".join(ek.parsel_etiket(a, p) for a, p in kayit["yeni"]))
            self.aciklama.setText(kayit["aciklama"])
            if kayit["kaynak"] == "TKGM":
                n = QtWidgets.QLabel("Bu kayıt Parsel Sorgu sonucundan oluşmuştu. Elle kaydederseniz bundan sonra otomatik "
                                     "güncellenmez ('TKGM sonucuna dön' ile geri alabilirsiniz).")
                n.setWordWrap(True)
                n.setMaximumWidth(460)
                g.addWidget(n, 9, 0, 1, 3)

    def takvim(self):
        s = takvim_sec(self, self.tarih.text())
        if s is not None:
            self.tarih.setText(s)

    def oku(self, k):
        metin = self.alan[k].text()
        liste_ = ek.parselleri_coz(metin)
        return ek.parsel_ozeti(metin) or ("Algılanan: " + ", ".join(ek.parsel_etiket(a, p) for a, p in liste_) if liste_ else "")

    def kaydet(self):
        mah = self.mahalle.currentText().strip()
        eski, yeni = ek.parselleri_coz(self.alan["eski"].text()), ek.parselleri_coz(self.alan["yeni"].text())
        if not mah or not (eski or yeni):
            self.app.uyari("Eksik bilgi", "Mahalle ile eski ve/veya yeni parsel yazılmalı.")
            return
        tur, tarih, aciklama = self.tur.currentText().strip(), ek.tarih_bicim(self.tarih.text()), self.aciklama.text().strip()
        if self.kayit:
            ek.fen_kayit_guncelle(self.kayit["id"], mah, tur, tarih, eski, yeni, aciklama,
                                  kilit=1 if self.kayit["kaynak"] == "TKGM" else None)
        else:
            ek.fen_kayit_ekle(mah, tur, tarih, eski, yeni, "Elle", None, aciklama)
        ek.q("INSERT OR IGNORE INTO liste VALUES ('mahalle',?)", (mah,))
        if any(self.app.fen.son):
            self.app.fen.ara()
        self.accept()


# ================================================================ Fen Klasörü sekmesi
class FenSekmesi(QtWidgets.QWidget):
    BASLIK = [("Eşleşme", 105), ("Mahalle", 120), ("İşlem", 95), ("Tarih", 90), ("Eski parseller", 210), ("Yeni parseller", 190),
              ("Alan (m²)", 80), ("Kaynak", 65), ("İş no", 65)]
    ESLESME = {"eski": "Eski parsel", "yeni": "Yeni parsel", "ara": "Ara parsel"}

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.kayit = {}  # satır no -> fen kaydı
        self.son = ("", "", "")
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 14, 12, 8)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(QtWidgets.QLabel("Mahalle:"))
        self.mah = app.AramaliComboSinif(lambda: None, 24)
        self.mah.addItems(ek.liste("mahalle"))
        self.mah.setEditText("")
        self.mah.lineEdit().returnPressed.connect(self.ara)
        ust.addWidget(self.mah)
        self.ada, self.par = QtWidgets.QLineEdit(), QtWidgets.QLineEdit()
        for ad, e in (("Ada:", self.ada), ("Parsel:", self.par)):
            ust.addWidget(QtWidgets.QLabel(ad))
            e.setFixedWidth(80)
            e.returnPressed.connect(self.ara)
            ust.addWidget(e)
        ust.addWidget(_dugme("Ara", self.ara, "vurgu"))
        ust.addWidget(_dugme("Temizle", self.temizle))
        ust.addStretch(1)
        v.addLayout(ust)
        ey = QtWidgets.QHBoxLayout()
        ey.addWidget(_dugme("Fen işlemi ekle...", self.ekle))
        ey.addWidget(_dugme("Düzenle... (eski/yeni parsel)", self.duzenle))
        ey.addWidget(_dugme("Hareket listesi (çift tık)", self.detay))
        ey.addWidget(_dugme("Seçileni sil", self.sil))
        ey.addWidget(_dugme("TKGM sonucuna dön", self.tkgm_donus))
        ey.addStretch(1)
        ey.addWidget(_dugme("Pasif Parseller (liste)", app.pasif_liste_ac))
        v.addLayout(ey)
        bilgi = QtWidgets.QLabel("Eski ya da yeni parsel numarasını yazın; ikisinde de ararım. Adası olmayan parseller için ada 0 "
                                 "(boş bırakırsanız tüm adalarda aranır). Mahalle boşsa tüm mahalleler taranır. Kayıtlar Parsel Sorgu "
                                 "sonuçlarından otomatik oluşur; Düzenle ile eski/yeni parselleri elle düzeltebilirsiniz "
                                 "(TKGM*: elle düzenlenmiş).")
        bilgi.setWordWrap(True)
        v.addWidget(bilgi)
        self.tv = QtWidgets.QTableWidget(0, len(self.BASLIK))
        self.tv.setHorizontalHeaderLabels([a for a, _ in self.BASLIK])
        for i, (_, w) in enumerate(self.BASLIK):
            self.tv.setColumnWidth(i, w)
        self.tv.horizontalHeader().setStretchLastSection(True)
        self.tv.verticalHeader().setVisible(False)
        self.tv.verticalHeader().setDefaultSectionSize(round(ek.TABLO_PUNTO * 2.8))
        self.tv.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tv.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tv.setShowGrid(False)
        self.tv.setMinimumHeight(180)
        self.tv.itemSelectionChanged.connect(self.grafik_ciz)
        self.tv.doubleClicked.connect(lambda _: self.detay())
        v.addWidget(self.tv, 1)
        self.say = QtWidgets.QLabel("")
        v.addWidget(self.say)
        self.graf = ZincirGrafik(270)
        v.addWidget(self.graf)
        self.grafik_ciz()

    # ---- seçim ve arama
    def secili(self):
        sat = self.tv.selectionModel().selectedRows()
        return self.kayit.get(sat[0].row()) if sat else None

    def mah_doldur(self):
        """Mahalle listesini güncel tutar (yazılı metin korunur)."""
        metin = self.mah.currentText()
        self.mah.blockSignals(True)
        self.mah.clear()
        self.mah.addItems(ek.liste("mahalle"))
        self.mah.setEditText(metin)
        self.mah.blockSignals(False)

    def sekme_acildi(self):
        self.mah_doldur()
        if any(self.son):
            self.ara()  # başka yerden gelen yeni sonuçları göster

    def tema_degisti(self):
        if any(self.son):
            self.ara()
        else:
            self.grafik_ciz()

    def temizle(self):
        self.mah.setEditText("")
        self.ada.clear()
        self.par.clear()
        self.ara()

    def ara(self):
        mah, ada, par = self.mah.currentText().strip(), self.ada.text().strip(), self.par.text().strip()
        self.son = (mah, ada, par)
        self.tv.setRowCount(0)
        self.kayit = {}
        if not (mah or ada or par):
            self.say.setText("Arama için mahalle, ada veya parsel yazın.")
            self.grafik_ciz()
            return
        sonuc = ek.fen_ara_sorgu(mah, ada, par)
        for n, r in enumerate(sonuc):
            self.kayit[n] = r
            vals = [self.ESLESME.get(r["rol"], "—"), r["mahalle"], r["tur"] or "–", r["tarih"] or "–",
                    ", ".join(ek.parsel_etiket(a, p) for a, p in r["eski"]) or "–",
                    ", ".join(ek.parsel_etiket(a, p) for a, p in r["yeni"]) or "–", r["alan"] or "–",
                    r["kaynak"] + ("*" if r["kilit"] else ""), f"#{r['work_id']}" if r["work_id"] else ""]
            self.tv.insertRow(n)
            for c, x in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(str(x))
                if r["rol"] in ("eski", "ara"):
                    it.setForeground(QtGui.QBrush(renk("FEN_ESKI")))
                elif r["rol"] == "yeni":
                    it.setForeground(QtGui.QBrush(renk("FEN_YENI")))
                self.tv.setItem(n, c, it)
        self.say.setText(f"{len(sonuc)} kayıt bulundu" if sonuc else "Kayıt bulunamadı")
        if sonuc:
            self.tv.selectRow(0)
        self.grafik_ciz()

    def grafik_ciz(self):
        r = self.secili()
        if not r:
            self.graf.bos_goster("Bir sonuç seçince eski → yeni parsel grafiği burada görünür")
            return
        dugum, kenar = ek.zincir_modeli(ek.zincir_coz(r.get("zincir")), r["eski"], r["yeni"])
        aranan = f"{self.son[1] or '0'}/{self.son[2]}" if self.son[2] else ""
        self.graf.goster(dugum, kenar, aranan, f"{r['tur'] or 'İşlem'} · {r['tarih'] or '–'} · {r['mahalle']}", y0=62)

    # ---- işlemler
    def ekle(self):
        FenIslemDialog(self.app).exec()

    def duzenle(self):
        r = self.secili()
        if not r:
            self.app.bilgi("Uyarı", "Önce düzenlenecek kaydı seçin.")
            return
        FenIslemDialog(self.app, r).exec()

    def detay(self):
        r = self.secili()
        if not r:
            self.app.bilgi("Uyarı", "Önce bir kayıt seçin.")
            return
        self.app.zincir_detay(dict(r, durum="Pasif", parsel_no=""))

    def tkgm_donus(self):
        r = self.secili()
        if not r:
            self.app.bilgi("Uyarı", "Önce bir kayıt seçin.")
            return
        if r["kaynak"] != "TKGM" or not r["kilit"]:
            self.app.bilgi("Fen Klasörü", "Bu kayıt elle düzenlenmiş bir TKGM kaydı değil.")
            return
        if self.app.sor("TKGM sonucuna dön", "Elle yaptığınız değişiklikler silinecek, kayıt Parsel Sorgu sonucuna göre yeniden "
                        "oluşturulacak. Devam edilsin mi?"):
            ek.q("UPDATE fen_islem SET kilit=0, imza='' WHERE id=?", (r["id"],))
            ek.fen_senkronla()
            self.ara()

    def sil(self):
        r = self.secili()
        if not r:
            self.app.bilgi("Uyarı", "Önce silinecek kaydı seçin.")
            return
        if r["kaynak"] == "TKGM":
            self.app.bilgi("Fen Klasörü", "Bu kayıt Parsel Sorgu sonucundan otomatik oluşturulur; silinemez. "
                           "Yanlışsa 'Düzenle' ile eski/yeni parselleri düzeltebilirsiniz.")
            return
        if self.app.sor("Sil", "Seçili fen işlemi silinsin mi?"):
            ek.fen_sil_kayit(r["id"])
            self.ara()
