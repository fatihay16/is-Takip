# -*- coding: utf-8 -*-
"""
Encümen İş Takip - PySide6 arayüzü (1. AŞAMA)

Çalıştırma:   python encumen_qt.py
Eski program: python encumen_kayit.py   (değişmedi, referans olarak durur)

Bu dosya yalnızca ARAYÜZÜ yapar. İş kuralları, hesaplamalar, SQLite tabloları, yedekleme, rapor ve
dosya mantığı encumen_kayit.py içinden aynen kullanılır (aşağıda `ek.` ile başlayan çağrılar).
Aynı veritabanı dosyası (imar_kayitlari.db) kullanılır; tablo yapısı değiştirilmez.

1. aşamada hazır olanlar : ana pencere, 3 sekme, özet kartları, arama, filtreler, tarih aralığı, kayıtlı filtreler,
                           kayıt tablosu (renkler, sıralama, çoklu seçim, hücre düzenleme), detay paneli,
                           tema, yazı boyutu, sütun gizleme, silme/geri alma, dosya açma, yedek, rapor, CSV,
                           TKGM (Parsel Sorgu) açma.
2. aşamada eklenenler   : Yeni kayıt / Formda düzenle / Satırı çoğalt, Toplu Güncelle, Listeler, Son silinenler,
                           Pasif Parseller, Rapor ayarları (encumen_qt_pencereler.py).
3. aşamada eklenenler   : Takvim, Grafikler sekmesi, Fen Klasörü sekmesi, Fen işlemi penceresi, parsel hareket listesi
                           (encumen_qt_sekmeler.py).
"""
import sys

# Köprü modu: TKGM penceresi (PySide6) bu dosyanın kendisi başka bir süreçte çağrılarak açılır (EXE'de de çalışsın diye).
# parsel_baslat.calistir Qt olay döngüsünü çalıştırır ve çıkış kodunu döndürür.
if __name__ == "__main__" and "--parsel-baslat" in sys.argv:
    import parsel_baslat
    sys.exit(parsel_baslat.calistir(sys.argv[sys.argv.index("--parsel-baslat") + 1:]) or 0)

import os
import re
import csv
import json
import sqlite3
import datetime
import tempfile
import calendar
import subprocess
import importlib.util

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import encumen_kayit as ek  # iş mantığı (Tkinter penceresi AÇILMAZ; yalnızca fonksiyonlar kullanılır)
import encumen_qt_sekmeler as sek  # 3. aşama: Takvim, Grafikler, Fen Klasörü, parsel hareket listesi
import encumen_qt_pencereler as pen  # 2. aşama pencereleri: Form, TopluGuncelle, Listeler, Silinenler, PasifListe, RaporAyar
import encumen_tema as et  # görünüm jetonları (renk/QSS); iş mantığı içermez
import v11_gorsel as v11g  # alternatif-tema tasarım katmanı; yalnızca görünüm
import v11_ikonlar as v11i  # tema renkli vektörel ikonlar

YAKINDA = "Bu pencere bir sonraki aşamada PySide6'ya taşınacak. Şimdilik eski programda (encumen_kayit.py) kullanılabilir."

MONO_YAZI = True    # karar no, tarih, alan (m²) sütunları eşit genişlikli fontla (Consolas); False: tüm tabloda tek font
KALIN_SUTUN = ("mahalle", "alinan_ucret", "ada_parsel")                   # yarı kalın
MONO_SUTUN = ("karar_no", "makbuz_no", "alan", "yuzolcum", "sira")       # + adında "tarih" geçen tüm sütunlar
_FONT_ONBELLEK = {}


def tablo_fontu(tur):
    """Tablo hücre yazı tipi (önbellekli). tur: 'yari' | 'mono'. Boyut ek.TABLO_PUNTO'ya göre ölçeklenir."""
    anahtar = (tur, ek.TABLO_PUNTO)
    if anahtar not in _FONT_ONBELLEK:
        _FONT_ONBELLEK[anahtar] = et.font_yap(ek.TABLO_PUNTO, yari=(tur == "yari"), mono=(tur == "mono"))
    return _FONT_ONBELLEK[anahtar]


def mono_sutun_mu(k):
    # Tarih sütunları da ana arayüz gibi Segoe UI kullanır; yalnızca sayısal/kimlik sütunları monospace kalır.
    return k in MONO_SUTUN


SATIR_BOYA = False  # True: eski görünüm (tüm satır durum rengiyle boyanır). False: yalnızca "onay" sütununda renkli hap.
SIRALANABILIR = set(ek.SHOWN) | {"bekleme", "parsel_durum", "parsel_yeni"}
DUZENLENEMEZ = {"sira", "karar_ok", "makbuz_ok", "bekleme", "parsel_durum", "parsel_yeni"}
ORTALI = {"sira", "karar_ok", "makbuz_ok", "bekleme"}
KOLON_AD = {"sira": "Sıra", "karar_ok": "Karar Dosyası", "makbuz_ok": "Makbuz Dosyası"}
VARSAYILAN_GENISLIK = {"sira": 50, "karar_ok": 100, "makbuz_ok": 100, "bekleme": 95, "parsel_durum": 190,
                       "parsel_yeni": 150, "aciklama": 170}
KOLON_NO = {k: i for i, k in enumerate(ek.TV_COLS)}


PARSEL_YEDEK_DESEN = re.compile(r"^parsel_kayitlari_\d{4}-\d{2}-\d{2}\.db$")


def yedekle_hepsi(ek_ad=""):
    """İki veritabanını birlikte yedekler: imar_kayitlari.db (eski ek.yedekle ile, aynen) ve parsel_kayitlari.db (TKGM).
    Döndürür: (imar_yedek_yolu, parsel_yedek_yolu | '', parsel_hata_metni). imar yedeği başarısızsa hata fırlatır;
    parsel yedeği başarısız olursa işlem durmaz, hata metni döner. Yedekler aynı klasöre yazılır; parsel yedeği de
    ek.YEDEK_SAKLA kadar saklanır."""
    yol = ek.yedekle(ek_ad)
    kaynak = os.path.join(ek.BASE, "parsel_kayitlari.db")
    if not os.path.exists(kaynak):
        return yol, "", ""
    try:
        kl = ek.yedek_klasor()
        ad = f"parsel_kayitlari_{datetime.date.today():%Y-%m-%d}.db" if not ek_ad else f"parsel_kayitlari_{ek_ad}.db"
        hedef = os.path.join(kl, ad)
        ek.db_kopyala(kaynak, hedef)
        for f in sorted(f for f in os.listdir(kl) if PARSEL_YEDEK_DESEN.match(f))[:-ek.YEDEK_SAKLA]:
            os.remove(os.path.join(kl, f))
        return yol, hedef, ""
    except Exception as ex:
        return yol, "", str(ex)


def ayar_yaz(ad, deger):
    ek.q("INSERT OR REPLACE INTO ayar VALUES (?,?)", (ad, deger))


def kolon_baslik(k):
    return KOLON_AD.get(k) or ek.LAB.get(k, k)


# ---------------------------------------------------------------- tema
TEMA_ANAHTAR = "acik"  # seçili tema (et.TEMALAR anahtarı)


def tema_ata(anahtar):
    """Seçili temayı belirler. ek.renk_ata ile temanın tabanı (açık/koyu) ek'e bildirilir; böylece durum renkleri,
    takvim ve eski modül renkleri tabana uygun kalır. Bilinmeyen anahtar 'acik' sayılır."""
    global TEMA_ANAHTAR
    TEMA_ANAHTAR = anahtar if anahtar in et.TEMALAR else "acik"
    ek.renk_ata(et.tema_koyu_mu(TEMA_ANAHTAR))


def tema():
    return et.birlestir(ek.TEMA_KOYU if ek.KOYU else ek.TEMA_ACIK, ek.KOYU, TEMA_ANAHTAR)


def palet_yap(t):
    return et.palet_yap(t)


def ok_ikon_yaz(ad, renk_kodu, yukari=False):
    """Açılır liste ve sayaç okları için küçük üçgen PNG'si üretir (QSS'teki kenarlık hilesi üçgen yerine gri kutu çiziyordu).
    Dosya geçici klasöre bir kez yazılır; yolu döndürür."""
    klasor = os.path.join(tempfile.gettempdir(), "encumen_ikon")
    os.makedirs(klasor, exist_ok=True)
    yol = os.path.join(klasor, f"{ad}_{renk_kodu.lstrip('#')}.png")
    if not os.path.exists(yol):
        pm = QtGui.QPixmap(12, 8)
        pm.fill(Qt.GlobalColor.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(renk_kodu))
        nokta = ([(1, 7), (11, 7), (6, 1)] if yukari else [(1, 1), (11, 1), (6, 7)])
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in nokta]))
        p.end()
        pm.save(yol, "PNG")
    return yol.replace("\\", "/")


def ok_ikon_qss(t):
    """Açılır liste (QComboBox) ve sayaç (QSpinBox) okları için tema rengine uygun üçgen resimler. Üretilemezse boş döner
    (o zaman temanın kendi oku kalır)."""
    try:
        asagi, yukari = ok_ikon_yaz("asagi", t["SOLUK"]), ok_ikon_yaz("yukari", t["SOLUK"], True)
    except Exception:
        return ""
    if not (os.path.exists(asagi) and os.path.exists(yukari)):
        return ""
    return f"""
QComboBox::down-arrow {{ image:url("{asagi}"); width:12px; height:8px; border:none; margin-right:8px; }}
QSpinBox::down-arrow {{ image:url("{asagi}"); width:12px; height:8px; border:none; }}
QSpinBox::up-arrow {{ image:url("{yukari}"); width:12px; height:8px; border:none; }}
"""


def qss_yap(t):
    return et.qss_yap(t) + ok_ikon_qss(t) + v11g.qss_ek(t)

def ikon_ata(anahtar, renk=None, boyut=18):
    """V1.1 ikonlarını mevcut tema paletine göre üretir."""
    t = tema()
    return v11i.ikon(anahtar, renk or t["SOLUK"], boyut)


def eylem_ikonu(eylem, anahtar, renk=None):
    eylem.setIcon(ikon_ata(anahtar, renk, 16))
    return eylem


# ---------------------------------------------------------------- tablo modeli
class KayitModel(QtCore.QAbstractTableModel):
    """Tabloda görünen satırlar. Süzme ve sıralama pencerede (eski program gibi) yapılır; model hazır listeyi gösterir."""

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.rows = []  # [(iş_id, d), ...]

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(ek.TV_COLS)

    def veri_ata(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def satir_bul(self, iid):
        for n, (i, _) in enumerate(self.rows):
            if i == iid:
                return n
        return -1

    def flags(self, index):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.isValid() and ek.TV_COLS[index.column()] not in DUZENLENEMEZ:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def data(self, index, rol=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        i, d = self.rows[index.row()]
        k = ek.TV_COLS[index.column()]
        if rol in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if k == "sira":
                return index.row() + 1
            v = d.get(k, "")
            return "" if v is None else str(v)
        if rol == Qt.ItemDataRole.BackgroundRole:
            if not SATIR_BOYA:
                return None
            r = ek.DURUM_UI.get(d.get("onay", ""))
            return QtGui.QBrush(QtGui.QColor(r)) if r else None
        if rol == Qt.ItemDataRole.ForegroundRole:
            if self.pencere.geciken(d) or d.get("parsel_onay"):
                return QtGui.QBrush(QtGui.QColor(ek.KIRMIZI))
            if not SATIR_BOYA:
                if k == "ada_parsel":
                    return QtGui.QBrush(QtGui.QColor(tema()["VURGU"]))
                if k == "alinan_ucret":
                    return QtGui.QBrush(QtGui.QColor(tema()["YESIL"]))
            return None
        if rol == Qt.ItemDataRole.FontRole and not SATIR_BOYA:
            if k in KALIN_SUTUN:
                return tablo_fontu("yari")
            if MONO_YAZI and mono_sutun_mu(k):
                return tablo_fontu("mono")
            return None
        if rol == Qt.ItemDataRole.TextAlignmentRole:
            return int((Qt.AlignmentFlag.AlignCenter if k in ORTALI
                        else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
        return None

    def headerData(self, bolum, yon, rol=Qt.ItemDataRole.DisplayRole):
        if yon != Qt.Orientation.Horizontal or rol != Qt.ItemDataRole.DisplayRole:
            return None
        k = ek.TV_COLS[bolum]
        ok = ""
        sr = self.pencere.siralama
        if sr and sr[0] == k:
            ok = " ▼" if sr[1] else " ▲"
        return et.tr_buyuk(kolon_baslik(k)) + ok


RENKLI_ALAN = ("islem", "muellif")   # hücre listesinde yazıları renkli gösterilecek alanlar (durum listesi her zaman hap biçimli)


def liste_rengi(metin):
    """Liste değerine kalıcı (her açılışta aynı) bir vurgu rengi verir; kırmızı 'geciken' anlamına geldiği için kullanılmaz."""
    import zlib
    t = tema()
    renkler = [t[k] for k in ("SAYI_MAVI", "SAYI_YESIL", "SAYI_TURUNCU", "SAYI_MOR", "VURGU") if t.get(k)] or [t["VURGU"]]
    return renkler[zlib.crc32(str(metin).encode("utf-8")) % len(renkler)]


class RenkliListeDelegate(QtWidgets.QStyledItemDelegate):
    """Hücre listesi (tamamlayıcı açılır liste) öğelerini renkli çizer: durumlar tablodaki gibi hap, diğerleri renkli yazı."""

    def __init__(self, parent, durum):
        super().__init__(parent)
        self.durum = durum

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QtCore.QSize(s.width() + 24, max(s.height(), QtGui.QFontMetrics(option.font).height() + 10))

    def paint(self, p, option, index):
        metin = index.data(Qt.ItemDataRole.DisplayRole)
        if not metin:
            return super().paint(p, option, index)
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        stil = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        stil.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, p, opt.widget)  # seçim/üzerine gelme zemini
        f = QtGui.QFont(option.font)
        p.save()
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.durum:
            zemin, yazi = et.hap_renkleri(ek.DURUM_UI.get(metin) or tema()["GRI_ZEMIN"], ek.KOYU)
            f.setBold(True)
            f.setPointSizeF(max(7.5, f.pointSizeF() - 1))
            fm = QtGui.QFontMetrics(f)
            h = fm.height() + 6
            genislik = min(fm.horizontalAdvance(metin) + 22, option.rect.width() - 10)
            r = QtCore.QRectF(option.rect.x() + 6, option.rect.center().y() - h / 2, genislik, h)
            p.setFont(f)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(zemin))
            p.drawRoundedRect(r, h / 2, h / 2)
            p.setPen(QtGui.QColor(yazi))
            p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), fm.elidedText(metin, Qt.TextElideMode.ElideRight, int(r.width() - 12)))
        else:
            f.setWeight(QtGui.QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(QtGui.QColor(liste_rengi(metin)))
            r = option.rect.adjusted(10, 0, -6, 0)
            p.drawText(r, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                       QtGui.QFontMetrics(f).elidedText(metin, Qt.TextElideMode.ElideRight, r.width()))
        p.restore()


class ListeEditor(QtWidgets.QLineEdit):
    """Tablo hücresinde liste seçimi: kutuya tıklayınca / ▾ simgesine basınca TÜM liste açılır, yazdıkça daralır
    (içinde geçen aranır). Seçilen değer hemen kaydedilir; yeni bir değer yazıp Enter'a basarak da kaydedilebilir."""

    def __init__(self, parent, degerler, bitir, alan=""):
        super().__init__(parent)
        c = QtWidgets.QCompleter(degerler, self)
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        c.setFilterMode(Qt.MatchFlag.MatchContains)
        c.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        c.setMaxVisibleItems(15)
        c.setPopup(QtWidgets.QListView())
        c.popup().setStyleSheet(et.tamamlayici_popup_qss(tema()))
        durum = any(d in ek.DURUM_UI for d in degerler)   # durum listesi (Tescilde bekliyor...) tablodaki gibi hap görünür
        if durum or alan in RENKLI_ALAN:
            c.popup().setItemDelegate(RenkliListeDelegate(c.popup(), durum))
        self.setCompleter(c)
        c.activated.connect(lambda *_: QtCore.QTimer.singleShot(0, bitir))
        ok = self.addAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowDown),
                            QtWidgets.QLineEdit.ActionPosition.TrailingPosition)
        ok.triggered.connect(self.hepsini_goster)

    def hepsini_goster(self):
        c = self.completer()
        if c is not None:
            c.setCompletionPrefix("")
            c.complete()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if not self.text():
            QtCore.QTimer.singleShot(0, self.hepsini_goster)


class ListeKutu(ListeEditor):
    """Form, Toplu Güncelle ve Fen işlemi penceresindeki seçim kutusu. Tablo hücresinde çalışan liste düzenleyicisiyle aynı
    yapıdadır (kutuya tıklayınca ya da ▾ ile TÜM liste açılır, yazdıkça daralır; listede olmayan yeni değer de yazılabilir).
    Pencereler QComboBox gibi kullanabilsin diye currentText / setEditText / lineEdit / activated sunar."""
    activated = QtCore.Signal(int)

    def __init__(self, degerler):
        super().__init__(None, degerler, lambda: self.activated.emit(0))

    def currentText(self):
        return self.text()

    def setEditText(self, metin):
        self.setText(metin)

    def lineEdit(self):
        return self

    def mousePressEvent(self, e):
        QtWidgets.QLineEdit.mousePressEvent(self, e)
        QtCore.QTimer.singleShot(0, self.hepsini_goster)  # her tıklamada liste açılır

    def keyPressEvent(self, e):
        c = self.completer()
        if e.key() == Qt.Key.Key_Down and c is not None and not c.popup().isVisible():
            self.hepsini_goster()
            return
        super().keyPressEvent(e)


class HucreDelegate(QtWidgets.QStyledItemDelegate):
    """Hücreye çift tıklayınca / F2 ile yerinde düzenleme. Kaydetme işini pencere.kaydet yapar."""

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.aktif = None

    def createEditor(self, parent, option, index):
        k = ek.TV_COLS[index.column()]
        if k in DUZENLENEMEZ:
            return None
        t = ek.LISTE_ALAN.get(k)
        if t:
            ed = ListeEditor(parent, ek.liste(t), lambda: self._bitir(ed), alan=k)
            QtCore.QTimer.singleShot(0, ed.hepsini_goster)  # düzenleme başlar başlamaz liste açılır
        else:
            ed = QtWidgets.QLineEdit(parent)
        self.aktif = ed
        ed.destroyed.connect(lambda *_: setattr(self, "aktif", None) if self.aktif is ed else None)
        return ed

    def paint(self, p, option, index):
        k = ek.TV_COLS[index.column()]
        metin = index.data(Qt.ItemDataRole.DisplayRole)
        if SATIR_BOYA or k != "onay" or not metin:
            return super().paint(p, option, index)
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        stil = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        stil.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, p, opt.widget)
        t = tema()
        zemin, yazi = et.hap_renkleri(ek.DURUM_UI.get(metin) or t["GRI_ZEMIN"], ek.KOYU)
        f = QtGui.QFont(option.font)
        f.setBold(True)
        f.setPointSizeF(max(7.5, f.pointSizeF() - 1))
        fm = QtGui.QFontMetrics(f)
        h = fm.height() + 6
        genislik = min(fm.horizontalAdvance(metin) + 22, option.rect.width() - 10)
        r = QtCore.QRectF(option.rect.x() + 6, option.rect.center().y() - h / 2, genislik, h)
        p.save()
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setFont(f)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(zemin))
        p.drawRoundedRect(r, h / 2, h / 2)
        p.setPen(QtGui.QColor(yazi))
        p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), fm.elidedText(metin, Qt.TextElideMode.ElideRight, int(r.width() - 12)))
        p.restore()

    def _bitir(self, w):
        try:
            self.commitData.emit(w)
            self.closeEditor.emit(w)
        except RuntimeError:
            pass

    def setEditorData(self, editor, index):
        metin = index.data(Qt.ItemDataRole.EditRole) or ""
        editor.setText(metin)
        editor.selectAll()

    def setModelData(self, editor, model, index):
        metin = editor.text()
        iid = model.rows[index.row()][0]
        k = ek.TV_COLS[index.column()]
        QtCore.QTimer.singleShot(0, lambda: self.pencere.kaydet(iid, k, metin))  # düzenleyici kapandıktan sonra kaydet

    def updateEditorGeometry(self, editor, option, index):
        r = option.rect
        if isinstance(editor, ListeEditor):
            r = QtCore.QRect(r.x(), r.y(), max(r.width(), 170), r.height())
        editor.setGeometry(r)


# ---------------------------------------------------------------- küçük bileşenler
class TakvimDialog(QtWidgets.QDialog):
    """Geçici basit tarih seçici (Takvim penceresi 2. aşamada taşınacak). sonuc: None=iptal, ''=temizle, 'gg.aa.yyyy'."""

    def __init__(self, parent, baslangic=""):
        super().__init__(parent)
        self.setWindowTitle("Tarih seç")
        self.sonuc = None
        v = QtWidgets.QVBoxLayout(self)
        self.tk = QtWidgets.QCalendarWidget()
        self.tk.setGridVisible(True)
        t = ek.tarih_oku(baslangic)
        if t:
            self.tk.setSelectedDate(QtCore.QDate(t.year, t.month, t.day))
        self.tk.activated.connect(lambda *_: self._tamam())
        v.addWidget(self.tk)
        h = QtWidgets.QHBoxLayout()
        for ad, f in (("Tamam", self._tamam), ("Temizle", self._temizle), ("İptal", self.reject)):
            b = QtWidgets.QPushButton(ad)
            b.clicked.connect(f)
            h.addWidget(b)
        v.addLayout(h)

    def _tamam(self):
        self.sonuc = self.tk.selectedDate().toString("dd.MM.yyyy")
        self.accept()

    def _temizle(self):
        self.sonuc = ""
        self.accept()


class AkisDuzeni(QtWidgets.QLayout):
    """Sığmayan öğeleri alt satıra saran düzen (dar/yarım ekranda filtre kutularının üst üste binmesini önler).
    QHBoxLayout yerine kullanılır; addStretch/addSpacing çağrıları zararsızdır (yok sayılır)."""

    def __init__(self, parent=None, bosluk=8):
        super().__init__(parent)
        self._ogeler = []
        self._bosluk = bosluk
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._ogeler.append(item)

    def addStretch(self, *_):
        pass

    def addSpacing(self, *_):
        pass

    def count(self):
        return len(self._ogeler)

    def itemAt(self, i):
        return self._ogeler[i] if 0 <= i < len(self._ogeler) else None

    def takeAt(self, i):
        return self._ogeler.pop(i) if 0 <= i < len(self._ogeler) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, genislik):
        return self._yerlestir(QtCore.QRect(0, 0, genislik, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._yerlestir(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QtCore.QSize()
        for o in self._ogeler:
            s = s.expandedTo(o.minimumSize())
        m = self.contentsMargins()
        return s + QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())

    def _yerlestir(self, rect, sadece_olc):
        m = self.contentsMargins()
        e = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, satir_h = e.x(), e.y(), 0
        for o in self._ogeler:
            if o.isEmpty():
                continue
            b = o.sizeHint()
            sonraki = x + b.width()
            if sonraki > e.right() + 1 and satir_h > 0:   # sığmıyor: alt satıra geç
                x, y, satir_h = e.x(), y + satir_h + self._bosluk, 0
                sonraki = x + b.width()
            if not sadece_olc:
                o.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), b))
            x = sonraki + self._bosluk
            satir_h = max(satir_h, b.height())
        return y + satir_h - rect.y() + m.bottom()


def cift(*widgetlar, bosluk=6):
    """Etiket + kutu gibi birbirinden ayrılmaması gereken öğeleri tek parça yapar (alt satıra birlikte geçerler)."""
    k = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(k)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(bosluk)
    for w in widgetlar:
        h.addWidget(w)
    return k


class TarihKutu(QtWidgets.QLineEdit):
    tiklandi = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFixedWidth(100)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.tiklandi.emit()


class AramaliCombo(QtWidgets.QComboBox):
    """Yazdıkça daralan açılır liste (eski AramaliCombobox'ın karşılığı)."""

    def __init__(self, degis, genislik=18):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        c = self.completer()
        c.setFilterMode(Qt.MatchFlag.MatchContains)
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        c.setPopup(QtWidgets.QListView())
        c.popup().setStyleSheet(et.tamamlayici_popup_qss(tema()))
        self.setMinimumWidth(genislik * 9)
        self._degis = degis
        self._zaman = QtCore.QTimer(self)
        self._zaman.setSingleShot(True)
        self._zaman.setInterval(300)
        self._zaman.timeout.connect(self._degis)
        self.lineEdit().textEdited.connect(lambda _: self._zaman.start())
        self.lineEdit().returnPressed.connect(self._hemen)
        self.activated.connect(lambda _: self._hemen())

    def _hemen(self):
        self._zaman.stop()
        QtCore.QTimer.singleShot(0, self._degis)  # seçim işlemi bitince filtrele (açık liste ortasında yenileme yapılmaz)


class TarihAraligi(QtWidgets.QWidget):
    def __init__(self, degis):
        super().__init__()
        self.degis = degis
        self.preset = ""
        self.duzen = AkisDuzeni(self)
        self.duzen.setContentsMargins(6, 0, 6, 6)
        self.alan = QtWidgets.QComboBox()
        self.alan.addItems(list(ek.TARIH_ALANLARI))
        self.alan.setCurrentText("Encümen Tarih")
        self.alan.activated.connect(lambda _: self.degis())
        self.duzen.addWidget(cift(QtWidgets.QLabel("Tarih aralığı:"), self.alan))
        self.kutu = {}
        for ad in ("Başlangıç", "Bitiş"):
            kt = TarihKutu()
            kt.tiklandi.connect(lambda ad=ad: self._sec(ad))
            self.kutu[ad] = kt
            self.duzen.addWidget(cift(QtWidgets.QLabel(ad + ":"), kt))
        self.hz = QtWidgets.QComboBox()
        self.hz.addItems(["Bu ay", "Geçen ay", "Son 30 gün", "Bu yıl", "Aralığı temizle"])
        self.hz.setPlaceholderText("Hızlı seç")
        self.hz.setCurrentIndex(-1)
        self.hz.activated.connect(lambda _: self.hizli(self.hz.currentText()))
        self.duzen.addWidget(self.hz)

    @property
    def bas(self):
        return self.kutu["Başlangıç"].text()

    @property
    def bit(self):
        return self.kutu["Bitiş"].text()

    def ayarla(self, bas, bit):
        self.kutu["Başlangıç"].setText(bas)
        self.kutu["Bitiş"].setText(bit)

    def _sec(self, ad):
        kt = self.kutu[ad]
        sonuc = sek.takvim_sec(self.window(), kt.text())
        if sonuc is not None:
            kt.setText(sonuc)
            self.preset = ""
            self.degis()

    def hizli(self, secim):
        self.preset = secim if secim in ("Bu ay", "Geçen ay", "Son 30 gün", "Bu yıl") else ""
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
        self.ayarla(b.strftime("%d.%m.%Y") if b else "", e.strftime("%d.%m.%Y") if e else "")
        self.hz.setCurrentIndex(-1)
        self.degis()

    def temizle(self):
        self.preset = ""
        self.ayarla("", "")

    def uygun(self, d):
        b, e = ek.tarih_oku(self.bas), ek.tarih_oku(self.bit)
        if b or e:
            t = ek.tarih_oku(d[ek.TARIH_ALANLARI[self.alan.currentText()]])
            if not t or (b and t < b) or (e and t > e):
                return False
        return True


class ListeFiltreleri:
    ALANLAR = [("islem", "İşlem"), ("muellif", "Müellif"), ("mahalle", "Mahalle"), ("onay", "Durum")]

    def __init__(self, duzen, degis):
        self.cb, self.vals = {}, {}
        for k, ad in self.ALANLAR:
            cb = AramaliCombo(degis)
            cb.addItem("(Tümü)")
            cb.setEditText("(Tümü)")
            duzen.addWidget(cift(QtWidgets.QLabel(ad + ":"), cb))
            self.cb[k] = cb

    def yenile(self):
        for k, cb in self.cb.items():
            v = ek.liste(ek.LISTE_ALAN[k])
            self.vals[k] = set(v)
            yeni = ["(Tümü)"] + v
            if [cb.itemText(i) for i in range(cb.count())] == yeni or cb.view().isVisible():
                continue  # değişmediyse veya liste şu an açıksa dokunma (açık liste kapanmasın)
            metin = cb.currentText()
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(["(Tümü)"] + v)
            cb.setEditText(metin)
            cb.blockSignals(False)

    def temizle(self):
        for cb in self.cb.values():
            cb.setEditText("(Tümü)")

    def aktif(self, k):
        return self.cb[k].currentText().strip() not in ("", "(Tümü)")

    def uygun(self, d):
        """Listeden seçilen değer birebir eşleşir; elle yazılan kısmi metin 'içinde geçen' olarak aranır."""
        for k, cb in self.cb.items():
            v = cb.currentText().strip()
            if v in ("", "(Tümü)"):
                continue
            if v in self.vals.get(k, ()):
                if d[k] != v:
                    return False
            elif ek.tr_lower(v) not in ek.tr_lower(d[k]):
                return False
        return True


class Kart(QtWidgets.QFrame):
    def __init__(self, baslik, tikla, vurgu="mavi"):
        super().__init__()
        self.setObjectName("kart")
        self.setProperty("vurgu", vurgu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tikla = tikla
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(18, 12, 18, 12)
        v.setSpacing(2)
        self.sayi = QtWidgets.QLabel("–")
        self.sayi.setObjectName("kartSayi")
        self.sayi.setProperty("vurgu", vurgu)
        b = QtWidgets.QLabel(baslik)
        b.setObjectName("kartBaslik")
        b.setWordWrap(True)   # dar pencerede kart başlığı alt satıra geçer, kartlar üst üste binmez
        v.addWidget(self.sayi)
        v.addWidget(b)

    def mousePressEvent(self, e):
        self._tikla()

    def yaz(self, metin, kirmizi=False):
        self.sayi.setText(metin)
        self.sayi.setStyleSheet(f"color:{ek.KIRMIZI};" if kirmizi else "")


class TiklaEtiket(QtWidgets.QLabel):
    tiklandi = QtCore.Signal()

    def mousePressEvent(self, e):
        self.tiklandi.emit()


class AraKutu(QtWidgets.QLineEdit):
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.clear()
        else:
            super().keyPressEvent(e)


# ---------------------------------------------------------------- ana pencere
class AnaPencere(QtWidgets.QMainWindow):
    # 3. aşama sekmeleri bu bileşenleri ana pencereden alır (tekrar yazılmasın diye)
    ListeFiltreleriSinif = ListeFiltreleri
    TarihAraligiSinif = TarihAraligi
    AramaliComboSinif = AramaliCombo

    def __init__(self):
        super().__init__()
        self.setWindowTitle("İmar Uygulamaları - Encümen Karar ve Makbuz Kayıtları")
        self.resize(1420, 780)
        self.setMinimumSize(820, 560)
        self.son = None
        self.siralama = None
        self.gizli = 0
        self.gecik_say = 0
        self.undo = []
        self.pk = {}
        self._sessiz = False
        self._buyut = False
        self._parsel_proc = None
        self._parsel_imza = None
        self._parsel_log = ""
        self._gen = {k: VARSAYILAN_GENISLIK.get(k, 105) for k in ek.TV_COLS}
        self._gen_yukleniyor = False

        kayitli = ek.ayar("tema_adi")  # kayıtlı tema varsa koru; yeni kurulum Kadastro ile başlar
        tema_ata(kayitli if kayitli in et.TEMALAR else ("koyu" if ek.ayar("tema") == "koyu" else "kadastro"))
        try:
            ek.punto_ata(int(ek.ayar("yazi_boyut") or 10))
        except ValueError:
            pass

        for d in (ek.BASE, getattr(sys, "_MEIPASS", ek.BASE)):
            yol = os.path.join(d, "encumen.ico")
            if os.path.exists(yol):
                self.setWindowIcon(QtGui.QIcon(yol))
                break

        self._yuk_zaman = QtCore.QTimer(self)
        self._yuk_zaman.setSingleShot(True)
        self._yuk_zaman.timeout.connect(self.load)
        self._bildir_zaman = QtCore.QTimer(self)
        self._bildir_zaman.setSingleShot(True)
        self._bildir_zaman.timeout.connect(lambda: self.bildirim.setText(""))
        self._esik_zaman = QtCore.QTimer(self)
        self._esik_zaman.setSingleShot(True)
        self._esik_zaman.setInterval(400)
        self._esik_zaman.timeout.connect(self.esik_degisti)
        self._parsel_zaman = QtCore.QTimer(self)
        self._parsel_zaman.setInterval(3000)
        self._parsel_zaman.timeout.connect(self._parsel_izle)

        self._kur()
        self._kisayollar()
        self.tema_uygula()
        self.ayar_yukle()
        self.load()
        QtCore.QTimer.singleShot(500, self.acilis)

    # ------------------------------------------------ arayüz kurulumu
    def _eylem(self, menu, metin, fonk=None, aktif=True, kutulu=None):
        a = QtGui.QAction(metin if aktif else metin + "   (sonraki aşama)", self)
        # Alternatif temadaki çizgi ikonları; menü metninin anlamına göre eşleştirilir.
        ikon_esleme = (
            (("yedek",), "database"), (("parsel sorgu", "ara"), "search"),
            (("pasif parsel", "katman", "toplu"), "layers"),
            (("liste", "klasör", "dosyayı aç", "kararı aç"), "folder"),
            (("makbuz", "rapor", "yazdır", "pdf"), "receipt"),
            (("csv", "aktar", "indir"), "download"),
            (("sil", "çöp"), "trash"), (("düzenle", "değiştir"), "pencil"),
            (("yenile", "geri al", "geri getir"), "refresh"),
            (("tarih", "takvim"), "calendar"), (("tema", "görünüm", "ekran"), "sun"),
        )
        alt = metin.casefold()
        for kelimeler, anahtar in ikon_esleme:
            if any(k in alt for k in kelimeler):
                a.setIcon(ikon_ata(anahtar, boyut=16))
                a.setProperty("_v11_ikon", anahtar)
                break
        if kutulu is not None:
            a.setCheckable(True)
            a.setChecked(kutulu)
        if aktif and fonk is not None:
            if kutulu is not None:
                a.toggled.connect(lambda _=False, f=fonk: f())
            else:
                a.triggered.connect(lambda _=False, f=fonk: f())
        if not aktif:
            a.setEnabled(False)
            a.setToolTip(YAKINDA)
        menu.addAction(a)
        return a

    def _menu_dugme(self, metin, menu, ikon_adi=None):
        b = QtWidgets.QToolButton()
        b.setText(metin)
        if ikon_adi:
            b.setIcon(ikon_ata(ikon_adi))
            b.setProperty("_v11_ikon", ikon_adi)
            b.setIconSize(QtCore.QSize(17, 17))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        b.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        b.setMenu(menu)
        return b

    def _dugme(self, metin, fonk, ad="", aktif=True, ikon_adi=None):
        b = QtWidgets.QPushButton(metin)
        if ikon_adi:
            b.setIcon(ikon_ata(ikon_adi))
            b.setProperty("_v11_ikon", ikon_adi)
            b.setIconSize(QtCore.QSize(17, 17))
        if ad:
            b.setObjectName(ad)
        if aktif:
            b.clicked.connect(lambda _=False, f=fonk: f())
        else:
            b.setEnabled(False)
            b.setToolTip(YAKINDA)
        return b

    def _kur(self):
        merkez = QtWidgets.QWidget()
        self.setCentralWidget(merkez)
        ana = QtWidgets.QVBoxLayout(merkez)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        # --- üst bant
        bant = QtWidgets.QFrame()
        bant.setObjectName("bant")
        bh = QtWidgets.QHBoxLayout(bant)
        bh.setContentsMargins(0, 0, 0, 0)
        l1 = QtWidgets.QLabel("İmar Uygulamaları")
        l1.setObjectName("bantBaslik")
        l2 = QtWidgets.QLabel("Encümen karar ve makbuz kayıtları")
        l2.setObjectName("bantAlt")
        self.bildirim = QtWidgets.QLabel("")
        self.bildirim.setObjectName("bildirim")
        self.tema_dugme = TiklaEtiket()
        self.tema_dugme.setObjectName("temaDugme")
        self.tema_dugme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tema_dugme.tiklandi.connect(self.tema_degistir)
        bh.addWidget(l1)
        bh.addWidget(l2)
        bh.addStretch(1)
        bh.addWidget(self.bildirim)
        bh.addWidget(self.tema_dugme)
        ana.addWidget(bant)

        # --- sekmeler
        self.nb = QtWidgets.QTabWidget()
        kap = QtWidgets.QWidget()
        kap.setContentsMargins(0, 0, 0, 0)
        ana.addWidget(self.nb, 1)
        self.nb.addTab(kap, ikon_ata("building", boyut=17), "Kayıtlar")
        self.grafikler = sek.GrafiklerSekmesi(self)
        self.fen = sek.FenSekmesi(self)
        self.nb.addTab(self.grafikler, ikon_ata("chart", boyut=17), "Grafikler")
        self.nb.addTab(self.fen, ikon_ata("folder", boyut=17), "Fen Klasörü")
        self.nb.currentChanged.connect(self._sekme_degisti)

        ana_duzen = QtWidgets.QVBoxLayout(kap)
        ana_duzen.setContentsMargins(16, 14, 16, 8)
        ana_duzen.setSpacing(10)

        # --- özet kartları
        kr = QtWidgets.QHBoxLayout()
        self.kartlar = {}
        kr.setSpacing(12)
        for anahtar, baslik, vurgu in (("acik", "Açık işler", "mavi"), ("encumen", "Bu ay encümen", "yesil"),
                                       ("gecik", "Geciken işler", "kirmizi"), ("harc", "Bu ay tahsil edilen harç", "turuncu"),
                                       ("parsel", "Pasif parsel — onay bekliyor", "mor")):
            kt = Kart(baslik, lambda a=anahtar: self.kart_tikla(a), vurgu)
            kr.addWidget(kt, 1)
            self.kartlar[anahtar] = kt
        ana_duzen.addLayout(kr)

        # --- arama + düğmeler + menüler
        ust = AkisDuzeni(bosluk=11)
        self.ara = AraKutu()
        self.ara.setMinimumWidth(230)
        self.ara.setClearButtonEnabled(True)
        self.ara_ikon_eylem = self.ara.addAction(ikon_ata("search", boyut=16), QtWidgets.QLineEdit.ActionPosition.LeadingPosition)
        self.ara.setPlaceholderText("Kayıtlarda ara...")
        self.ara.textChanged.connect(lambda _: self.load_gecikmeli())
        ust.addWidget(cift(QtWidgets.QLabel("Ara:"), self.ara))
        ust.addWidget(self._dugme("Yeni", self.yeni, "vurgu", ikon_adi="plus"))
        ust.addWidget(self._dugme("Formda Düzenle", self.duzenle, ikon_adi="pencil"))
        ust.addWidget(self._dugme("Toplu Güncelle", self.toplu, ikon_adi="layers"))
        ust.addWidget(self._dugme("Sil", self.sil, "tehlike", ikon_adi="trash"))
        ust.addWidget(self._dugme("Kararı Aç", lambda: self.ac("karar"), ikon_adi="folder"))
        ust.addWidget(self._dugme("Makbuzu Aç", lambda: self.ac("makbuz"), ikon_adi="receipt"))

        ym = QtWidgets.QMenu(self)
        self._eylem(ym, "Şimdi yedekle", self.yedek_simdi)
        self._eylem(ym, "Yedek klasörünü seç", self.yedek_klasoru_sec)
        self._eylem(ym, "Yedekten geri yükle", self.yedek_geri_yukle)
        ust.addWidget(self._menu_dugme("Yedek", ym, "database"))

        vm = QtWidgets.QMenu(self)
        self._eylem(vm, "Son işlemi geri al (Ctrl+Z)", self.geri_al)
        vm.addSeparator()
        self._eylem(vm, "Parsel Sorgu (TKGM)...", self.parsel_sorgu_ac)
        self._eylem(vm, "Pasif Parseller (liste)...", self.pasif_liste_ac)
        self._eylem(vm, "Listeler (mahalle, müellif, işlem, durum)...", self.listeler_ac)
        self._eylem(vm, "CSV Al (Google E-Tablo'dan)...", self.csv_al)
        self._eylem(vm, "CSV Aktar (tüm kayıtlar)...", self.csv_aktar)
        self._eylem(vm, "Dosya klasörleri (isteğe bağlı)...", self.klasorler)
        vm.addSeparator()
        self._eylem(vm, "Son silinenler (geri getir)...", self.silinenler_ac)
        ust.addWidget(self._menu_dugme("Veri", vm, "layers"))

        rm = QtWidgets.QMenu(self)
        self._eylem(rm, "Görünen liste (yazdır / PDF)", self.rapor_liste)
        self._eylem(rm, "Müellife göre harç dökümü (yazdır / PDF)", self.rapor_muellif)
        self._eylem(rm, "Görünen listeyi Excel'e aktar (CSV)", self.excel_aktar)
        rm.addSeparator()
        self._eylem(rm, "Rapor başlığı ve imza ayarları...", self.rapor_ayar_ac)
        ust.addWidget(self._menu_dugme("Rapor", rm, "receipt"))

        em = QtWidgets.QMenu(self)
        tm = em.addMenu("Tema")
        self.tema_grup = QtGui.QActionGroup(self)
        self.tema_grup.setExclusive(True)
        self.tema_eylem = {}
        for k in et.tema_anahtarlari():
            a = QtGui.QAction(et.tema_adi(k), self)
            a.setCheckable(True)
            self.tema_grup.addAction(a)
            a.triggered.connect(lambda _=False, k=k: self.tema_sec(k))
            tm.addAction(a)
            self.tema_eylem[k] = a
        self.detay_eylem = self._eylem(em, "Detay paneli (F3)", self.detay_ac_kapa, kutulu=False)
        em.addSeparator()
        self._eylem(em, "Yazıyı büyüt (Ctrl + tekerlek yukarı  /  Ctrl +)", lambda: self.yazi_boyut(1))
        self._eylem(em, "Yazıyı küçült (Ctrl + tekerlek aşağı  /  Ctrl -)", lambda: self.yazi_boyut(-1))
        self._eylem(em, "Varsayılan yazı boyutu (Ctrl 0)", lambda: self.yazi_boyut(None))
        em.addSeparator()
        sm = em.addMenu("Sütunları göster / gizle")
        self.sutun_eylem = {}
        for k in ek.TV_COLS[1:]:
            self.sutun_eylem[k] = self._eylem(sm, ek.SUTUN_AD.get(k) or ek.LAB.get(k, k), self.sutun_uygula, kutulu=True)
        ust.addWidget(self._menu_dugme("Ekran", em, "sun"))
        ust.addStretch(1)
        ana_duzen.addLayout(ust)

        # --- görünüm + liste filtreleri
        f2 = AkisDuzeni(bosluk=11)
        self.gorunum = QtWidgets.QComboBox()
        self.gorunum.addItems(ek.GORUNUMLER)
        self.gorunum.setMinimumWidth(230)
        self.gorunum.activated.connect(lambda _: self.degis())
        f2.addWidget(cift(QtWidgets.QLabel("Görünüm:"), self.gorunum))
        self.lf = ListeFiltreleri(f2, self.degis)
        f2.addWidget(self._dugme("Filtreleri Temizle", self.fil_temizle, ikon_adi="filter"))
        self.eksik = QtWidgets.QCheckBox("Dosyası eksik olanlar (✗)")
        self.eksik.toggled.connect(lambda _: self.degis())
        f2.addWidget(self.eksik)
        self.parsel_f = QtWidgets.QCheckBox("Pasif parsel (onay bekliyor)")
        self.parsel_f.toggled.connect(lambda _: self.degis())
        f2.addWidget(self.parsel_f)
        f2.addStretch(1)
        ana_duzen.addLayout(f2)

        # --- tarih aralığı + gecikme + kayıtlı filtreler
        self.ta = TarihAraligi(self.degis)
        self.gecik = QtWidgets.QCheckBox("Geciken işler")
        self.gecik.toggled.connect(lambda _: self.degis())
        self.esik_kutu = QtWidgets.QSpinBox()
        self.esik_kutu.setRange(1, 365)
        self.esik_kutu.setKeyboardTracking(False)
        try:
            self.esik_kutu.setValue(int(ek.ayar("gecikme_gun") or 30))
        except ValueError:
            self.esik_kutu.setValue(30)
        self.esik_kutu.valueChanged.connect(lambda _: self._esik_zaman.start())
        self.ta.duzen.addWidget(cift(self.gecik, QtWidgets.QLabel("Eşik (gün):"), self.esik_kutu, bosluk=8))
        self.gm = QtWidgets.QMenu(self)
        self.gm.aboutToShow.connect(self.gm_doldur)
        self.ta.duzen.addWidget(self._menu_dugme("Kayıtlı filtreler", self.gm, "filter"))
        self.ta.duzen.addWidget(self._dugme("Parsel Sorgu", self.parsel_sorgu_ac, ikon_adi="search"))
        self.ta.duzen.addWidget(self._dugme("Pasif Parseller", self.pasif_liste_ac, ikon_adi="layers"))
        ana_duzen.addWidget(self.ta)

        # --- tablo + detay paneli
        self.model = KayitModel(self)
        self.tablo = QtWidgets.QTableView()
        self.tablo.setModel(self.model)
        self.delegate = HucreDelegate(self)
        self.tablo.setItemDelegate(self.delegate)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tablo.setShowGrid(False)
        self.tablo.setWordWrap(False)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tablo.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        hdr = self.tablo.horizontalHeader()
        hdr.setSectionsClickable(True)
        hdr.setSectionsMovable(False)
        hdr.setStretchLastSection(False)
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for k, i in KOLON_NO.items():
            self.tablo.setColumnWidth(i, self._gen[k])
        hdr.sectionResized.connect(self._kolon_boyut)
        hdr.sectionClicked.connect(self.baslik_tikla)
        self.tablo.pressed.connect(self._basildi)
        self.tablo.doubleClicked.connect(self.cift)
        self.tablo.selectionModel().selectionChanged.connect(lambda *_: self.detay_guncelle())
        self.tablo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tablo.customContextMenuRequested.connect(self.sag)
        self.tablo.viewport().installEventFilter(self)

        self.menu = QtWidgets.QMenu(self)
        self._eylem(self.menu, "Bu hücreyi düzenle (F2)", self.f2)
        self._eylem(self.menu, "Satırı formda düzenle", self.duzenle)
        self._eylem(self.menu, "Seçili satırları toplu güncelle...", self.toplu)
        self._eylem(self.menu, "Satırı çoğalt (aynı parsele yeni işlem)", self.cogalt)
        self._eylem(self.menu, "Hücreyi / seçili satırları kopyala (Ctrl+C)", self.kopyala)
        self._eylem(self.menu, "Parsel sonucunu onayla (uyarıyı kaldır)", self.parsel_onayla)
        self._eylem(self.menu, "Kararı aç", lambda: self.ac("karar"))
        self._eylem(self.menu, "Makbuzu aç", lambda: self.ac("makbuz"))
        self._eylem(self.menu, "Karar dosyasını seç / değiştir...", lambda: self.dosya_sec("karar"))
        self._eylem(self.menu, "Makbuz dosyasını seç / değiştir...", lambda: self.dosya_sec("makbuz"))
        self._eylem(self.menu, "Satırı sil", self.sil)

        self.detay = QtWidgets.QTextEdit()
        self.detay.setObjectName("detay")
        self.detay.setReadOnly(True)
        self.detay.setMinimumWidth(260)
        self.bolme = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        self.bolme.addWidget(self.tablo)
        self.bolme.addWidget(self.detay)
        self.bolme.setStretchFactor(0, 1)
        self.bolme.setStretchFactor(1, 0)
        self.bolme.setSizes([1000, 320])
        self.bolme.setChildrenCollapsible(False)
        self.detay.setVisible(False)
        self.detay_acik = False
        ana_duzen.addWidget(self.bolme, 1)

        # --- durum satırı + renk açıklaması
        self.durum_etiket = QtWidgets.QLabel()
        ana_duzen.addWidget(self.durum_etiket)
        lg = QtWidgets.QHBoxLayout()
        lg.addWidget(QtWidgets.QLabel("Renkler:"))
        self.lejant = {}
        for ad in ek.DURUM_RENK:
            e = QtWidgets.QLabel(ad)
            e.setObjectName("hap")
            self.lejant[ad] = e
            lg.addWidget(e)
        lg.addWidget(QtWidgets.QLabel("      Dosya:  ✓ var   ✗ yok   ? klasöre ulaşılamıyor"))
        lg.addStretch(1)
        ana_duzen.addLayout(lg)

        self.tablo_yazi_uygula()

    def _kisayollar(self):
        def ks(tus, fonk, baglam=Qt.ShortcutContext.WindowShortcut, ust=None):
            s = QtGui.QShortcut(QtGui.QKeySequence(tus), ust or self)
            s.setContext(baglam)
            s.activated.connect(fonk)
            return s
        ks("Ctrl+F", lambda: (self.nb.setCurrentIndex(0), self.ara.setFocus(), self.ara.selectAll()))
        ks("Ctrl+Z", self.geri_al)
        ks("Ctrl+N", self.yeni)
        ks("F5", lambda: (ek.dosya_cache_temizle(), self.load()))
        ks("F3", lambda: self.detay_eylem.setChecked(not self.detay_eylem.isChecked()))
        for t in ("Ctrl++", "Ctrl+="):
            ks(t, lambda: self.yazi_boyut(1))
        ks("Ctrl+-", lambda: self.yazi_boyut(-1))
        ks("Ctrl+0", lambda: self.yazi_boyut(None))
        ks("F2", self.f2, Qt.ShortcutContext.WidgetShortcut, self.tablo)
        ks("Delete", self.sil, Qt.ShortcutContext.WidgetShortcut, self.tablo)
        ks("Ctrl+C", self.kopyala, Qt.ShortcutContext.WidgetShortcut, self.tablo)

    def eventFilter(self, nesne, olay):
        if nesne is self.tablo.viewport() and olay.type() == QtCore.QEvent.Type.Wheel:
            if olay.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.yazi_boyut(1 if olay.angleDelta().y() > 0 else -1)
                return True
        return super().eventFilter(nesne, olay)

    def _sekme_degisti(self, i):
        if i == 1:
            self.grafikler.ciz_hepsi()
        elif i == 2:
            self.fen.sekme_acildi()

    # ------------------------------------------------ tema ve yazı
    def tema_uygula(self):
        et.ek_renk_uygula(ek, ek.KOYU, TEMA_ANAHTAR)  # sekmelerin okuduğu ek.METIN/KART/VURGU... yeni jetonlara çekilir
        t = tema()
        app = QtWidgets.QApplication.instance()
        app.setPalette(palet_yap(t))
        app.setStyleSheet(qss_yap(t))
        v11g.font_ata(app)
        # Tema değişince mevcut ikonları da yeni metin rengine göre yeniden çiz.
        for w in self.findChildren(QtWidgets.QAbstractButton):
            anahtar = w.property("_v11_ikon")
            if anahtar:
                w.setIcon(ikon_ata(anahtar))
        for a in self.findChildren(QtGui.QAction):
            anahtar = a.property("_v11_ikon")
            if anahtar:
                a.setIcon(ikon_ata(anahtar, boyut=16))
        self.nb.setTabIcon(0, ikon_ata("building", boyut=17))
        self.nb.setTabIcon(1, ikon_ata("chart", boyut=17))
        self.nb.setTabIcon(2, ikon_ata("folder", boyut=17))
        self.ara_ikon_eylem.setIcon(ikon_ata("search", boyut=16))
        self.tema_dugme.setText("◐  " + et.tema_adi(TEMA_ANAHTAR))  # tıklayınca sıradaki temaya geçer
        self.tema_dugme.setToolTip("Temayı değiştir (Ekran > Tema ile doğrudan seçebilirsiniz)")
        for k, a in self.tema_eylem.items():
            a.blockSignals(True)
            a.setChecked(k == TEMA_ANAHTAR)
            a.blockSignals(False)
        for ad, e in self.lejant.items():
            zemin, yazi = et.hap_renkleri(ek.DURUM_UI[ad], ek.KOYU)
            e.setStyleSheet(f"background:{zemin}; color:{yazi};")
        self.tablo_yazi_uygula()
        self.model.layoutChanged.emit()
        self.detay_guncelle()
        self.grafikler.ciz_hepsi()
        self.fen.tema_degisti()

    def tema_degistir(self):
        """Bant düğmesi: sıradaki temaya geçer."""
        self.tema_sec(et.sonraki_tema(TEMA_ANAHTAR))

    def tema_sec(self, anahtar):
        self.edit_kapat()
        tema_ata(anahtar)
        ayar_yaz("tema_adi", TEMA_ANAHTAR)
        ayar_yaz("tema", "koyu" if ek.KOYU else "acik")  # eski program açık/koyu ayarını okumaya devam eder
        self.tema_uygula()
        self.kart_guncelle(self.tum_kayitlar())  # kart sayılarının kırmızı rengi temaya göre yenilenir

    def tablo_yazi_uygula(self):
        n = ek.TABLO_PUNTO
        self.tablo.setFont(et.font_yap(n))
        self.tablo.horizontalHeader().setFont(et.font_yap(max(8.5, round(n * 0.85, 1)), kalin=True, aralik=0.5))
        self.tablo.verticalHeader().setDefaultSectionSize(round(n * 2.8))

    def yazi_boyut(self, d):
        self.edit_kapat()
        n = 10 if d is None else max(8, min(20, ek.TABLO_PUNTO + d))
        if n == ek.TABLO_PUNTO:
            return
        ek.punto_ata(n)
        self.tablo_yazi_uygula()
        ayar_yaz("yazi_boyut", str(n))
        self.bildir(f"Tablo yazı boyutu: {n}", 1500)

    def bildir(self, metin, ms=4000):
        self.bildirim.setText(metin)
        self._bildir_zaman.start(ms)

    # ------------------------------------------------ sütunlar, detay paneli, pencere ayarları
    def _kolon_boyut(self, i, eski, yeni):
        if self._gen_yukleniyor or yeni <= 0 or self.tablo.isColumnHidden(i):
            return
        self._gen[ek.TV_COLS[i]] = int(yeni)

    def sutun_uygula(self, kaydet=True):
        self.edit_kapat()
        gor = [k for k in ek.TV_COLS[1:] if self.sutun_eylem[k].isChecked()]
        if not gor:  # hiç sütun kalmasın
            for a in self.sutun_eylem.values():
                a.blockSignals(True)
                a.setChecked(True)
                a.blockSignals(False)
            gor = list(ek.TV_COLS[1:])
        self._gen_yukleniyor = True
        for k, i in KOLON_NO.items():
            self.tablo.setColumnHidden(i, k != "sira" and k not in gor)
            if not self.tablo.isColumnHidden(i):
                self.tablo.setColumnWidth(i, self._gen[k])
        self._gen_yukleniyor = False
        if kaydet:
            ayar_yaz("gizli_sutun", json.dumps([k for k in ek.TV_COLS[1:] if not self.sutun_eylem[k].isChecked()]))

    def detay_ac_kapa(self, kaydet=True):
        self.detay_acik = self.detay_eylem.isChecked()
        self.detay.setVisible(self.detay_acik)
        if self.detay_acik:
            self.bolme.setSizes([max(self.bolme.width() - 320, 400), 320])
            self.detay_guncelle()
        if kaydet:
            ayar_yaz("detay", "1" if self.detay_acik else "0")

    def detay_guncelle(self):
        if not getattr(self, "detay_acik", False):
            return
        t = tema()
        e = f"color:{t['SOLUK']};font-weight:bold;font-size:9pt"
        dd = "font-size:11pt;margin-bottom:10px"
        sec = self.secili_satirlar()
        h = []
        if not sec:
            h.append(f"<span style='color:{t['SOLUK']}'>Ayrıntısını görmek için tablodan bir satır seçin.</span>")
        elif len(sec) > 1:
            h.append(f"<span style='color:{t['SOLUK']}'>{len(sec)} kayıt seçili.<br><br>"
                     "Birlikte değiştirmek için «Toplu Güncelle»yi kullanabilirsiniz.</span>")
        else:
            iid, d = sec[0]

            def alan(ad, v):
                h.append(f"<div style='{e}'>{ek.hesc(ad)}</div><div style='{dd}'>{ek.hesc(str(v or '–'))}</div>")
            for k in ek.SHOWN:
                alan(ek.LAB[k], d[k])
            for k, ad in (("karar_ok", "Karar dosyası"), ("makbuz_ok", "Makbuz dosyası"), ("bekleme", "Bekleme (gün)")):
                alan(ad, d[k])
            pk = self.pk.get(iid)
            if pk:
                for ad, v in (("Parsel durumu (TKGM)", d["parsel_durum"]), ("Sorgulanan parsel", pk["parsel_no"]),
                              ("Alan / nitelik", f"{pk['alan'] or '–'} m² · {pk['nitelik'] or '–'}"),
                              ("Yeni (aktif) parseller", d["parsel_yeni"]), ("TKGM açıklaması", pk["aciklama"]),
                              ("Son parsel kontrolü", (pk["son_kontrol"] or "").replace("T", " ")[:16])):
                    alan(ad, v)
        self.detay.setHtml("".join(h))

    def ayar_kaydet(self):
        zoom = self.isMaximized()
        ayar_yaz("pencere_durum", "zoomed" if zoom else "normal")
        if not zoom:
            g = self.geometry()
            ayar_yaz("pencere", f"{g.width()}x{g.height()}+{g.x()}+{g.y()}")
        ayar_yaz("sutunlar", json.dumps({c: int(self._gen[c]) for c in ek.TV_COLS}))

    def ayar_yukle(self):
        try:
            m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", ek.ayar("pencere"))
            if m:
                w, h, x, y = map(int, m.groups())
                ekran = QtGui.QGuiApplication.primaryScreen().geometry()
                sw, sh = ekran.width(), ekran.height()
                w, h = min(w, sw), min(h, sh)
                x, y = min(max(x, 0), max(sw - w, 0)), min(max(y, 0), max(sh - h - 40, 0))
                self.setGeometry(x, y, w, h)
            for c, w in json.loads(ek.ayar("sutunlar") or "{}").items():
                if c in self._gen and isinstance(w, int) and 20 <= w <= 900:
                    self._gen[c] = w
        except Exception:
            pass
        try:
            gizli = json.loads(ek.ayar("gizli_sutun") or "[]")
            for k, a in self.sutun_eylem.items():
                a.blockSignals(True)
                a.setChecked(k not in gizli)
                a.blockSignals(False)
        except Exception:
            pass
        self.sutun_uygula(kaydet=False)
        try:
            self.detay_eylem.blockSignals(True)
            self.detay_eylem.setChecked(ek.ayar("detay") == "1")
            self.detay_eylem.blockSignals(False)
            self.detay_ac_kapa(kaydet=False)
        except Exception:
            pass
        try:
            self._buyut = ek.ayar("pencere_durum") == "zoomed"
        except Exception:
            pass

    def closeEvent(self, e):
        self.edit_kapat()
        try:
            self.ayar_kaydet()
        except Exception:
            pass
        try:
            yedekle_hepsi()
        except Exception:
            pass
        e.accept()

    # ------------------------------------------------ liste / filtre / sıralama
    def degis(self):
        if not self._sessiz:
            self.load()

    def load_gecikmeli(self, ms=250):
        if not self._sessiz:
            self._yuk_zaman.start(ms)

    def fil_yenile(self):
        self.lf.yenile()
        self.grafikler.glf.yenile()

    def filtre_sifirla(self):
        self._sessiz = True
        try:
            self.lf.temizle()
            self.ta.temizle()
            self.gorunum.setCurrentText(ek.GORUNUMLER[0])
            self.eksik.setChecked(False)
            self.gecik.setChecked(False)
            self.parsel_f.setChecked(False)
            self.ara.setText("")
        finally:
            self._sessiz = False

    def fil_temizle(self):
        self.filtre_sifirla()
        self.load()

    def esik(self):
        return max(self.esik_kutu.value(), 0)

    def esik_degisti(self):
        ayar_yaz("gecikme_gun", str(self.esik()))
        self.load()

    def geciken(self, d):
        b = d.get("bekleme")
        return bool(b) and int(b) > self.esik()

    def uygun(self, d, gorunum=True):
        if not self.lf.uygun(d) or not self.ta.uygun(d):
            return False
        g = self.gorunum.currentText()
        if gorunum and not self.lf.aktif("onay"):  # Durum seçilmişse o seçim geçerli
            if g == ek.GORUNUMLER[0] and ek.arsiv_mi(d["onay"]):
                return False
            if g == ek.GORUNUMLER[2] and not ek.arsiv_mi(d["onay"]):
                return False
        if self.eksik.isChecked() and "✗" not in (d["karar_ok"], d["makbuz_ok"]):
            return False
        if self.gecik.isChecked() and not self.geciken(d):
            return False
        if self.parsel_f.isChecked() and not d.get("parsel_onay"):
            return False
        n = ek.tr_lower(self.ara.text().strip())
        return not n or n in ek.tr_lower(" ".join(d[k] for k in ek.KEYS))

    def tum_kayitlar(self):
        idx = {tur: ek.dosya_indeksi(ek.ayar(tur + "_klasor")) for tur in ("karar", "makbuz")}
        sonuc, onb, bugun = [], {}, datetime.date.today()
        self.pk = pk = ek.parsel_kontrol_oku()
        oto = ek.parsel_otomatik_onay(pk)
        if oto:
            self.bildir(f"{oto} pasif parsel uyarısı onaylandı (iş 'Tescillendi' olduğu için)")
        for r in ek.q(f"SELECT id,{','.join(ek.KEYS)},durum_tarihi FROM kayit ORDER BY id"):
            d = dict(zip(ek.KEYS, [x or "" for x in r[1:-1]]))
            d["durum_tarihi"] = r[-1] or ""
            d["bekleme"] = ek.bekleme_gun(d, bugun)
            d.update(ek.parsel_gosterim(pk.get(r[0])))
            d["karar_ok"] = ek.dosya_isaret("karar", d, idx["karar"], onb)
            d["makbuz_ok"] = ek.dosya_isaret("makbuz", d, idx["makbuz"], onb)
            sonuc.append((r[0], d))
        return sonuc

    def load(self):
        self.edit_kapat()
        self.fil_yenile()
        tum = self.tum_kayitlar()
        rows = [r for r in tum if self.uygun(r[1])]
        self.gecik_say = sum(1 for _, d in rows if self.geciken(d))
        self.gizli = 0
        if self.gorunum.currentText() == ek.GORUNUMLER[0] and not self.lf.aktif("onay"):
            self.gizli = sum(1 for _, d in tum if ek.arsiv_mi(d["onay"]) and self.uygun(d, False))
        if self.siralama:
            k, ters = self.siralama
            dolu = [r for r in rows if r[1][k]]
            bos = [r for r in rows if not r[1][k]]
            dolu.sort(key=lambda r: ek.sort_key(k, r[1][k]), reverse=ters)
            rows = dolu + bos
        self.model.veri_ata(rows)
        self.model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(ek.TV_COLS) - 1)
        self.durum_guncelle()
        self.kart_guncelle(tum)
        self.detay_guncelle()
        self.grafikler.guncelle(tum)
        try:
            ek.fen_senkronla()  # yeni TKGM sonuçları Fen Klasörü'ne işlenir
        except Exception:
            pass
        if self.nb.currentIndex() == 2:
            self.fen.sekme_acildi()

    def yenile_koru(self, iid=None):
        kay = self.tablo.verticalScrollBar().value()
        self.load()
        self.tablo.verticalScrollBar().setValue(kay)
        if iid:
            r = self.model.satir_bul(iid)
            if r >= 0:
                self.tablo.selectRow(r)

    def durum_guncelle(self):
        toplam = sum(ek.para(d["alinan_ucret"]) for _, d in self.model.rows)
        gz = f"    ·  {self.gizli} arşiv iş gizli (Görünüm: Tümü ile görürsünüz)" if self.gizli else ""
        gc = f"    ·  ⚠ {self.gecik_say} geciken iş" if self.gecik_say else ""
        self.durum_etiket.setText(f"{len(self.model.rows)} kayıt    Toplam Alınan Ücret: {ek.para_yaz(toplam)}{gz}{gc}    "
                                  "(Çift tıkla: hücre düzenle · Ctrl/Shift ile çoklu seçim → Toplu Güncelle · başlığa tıkla: sırala)")

    def baslik_tikla(self, i):
        k = ek.TV_COLS[i]
        if k == "sira":
            self.siralama = None
            self.load()
        elif k in SIRALANABILIR:
            if self.siralama and self.siralama[0] == k:
                self.siralama = (k, not self.siralama[1])
            else:
                self.siralama = (k, False)
            self.load()

    def kart_guncelle(self, tum):
        bg = datetime.date.today()
        acik = encumen = gecik = parsel = 0
        harc = 0.0
        for _, d in tum:
            if not ek.arsiv_mi(d["onay"]):
                acik += 1
            t = ek.tarih_oku(d["encumen_tarihi"])
            if t and (t.year, t.month) == (bg.year, bg.month):
                encumen += 1
            if self.geciken(d):
                gecik += 1
            if d.get("parsel_onay"):
                parsel += 1
            t = ek.tarih_oku(d["makbuz_tarihi"])
            if t and (t.year, t.month) == (bg.year, bg.month):
                harc += ek.para(d["alinan_ucret"])
        self.kartlar["acik"].yaz(str(acik))
        self.kartlar["encumen"].yaz(str(encumen))
        self.kartlar["gecik"].yaz(str(gecik), bool(gecik))
        self.kartlar["harc"].yaz(ek.para_yaz(harc, 0))
        self.kartlar["parsel"].yaz(str(parsel), bool(parsel))

    def kart_tikla(self, a):
        self.filtre_sifirla()
        if a in ("encumen", "harc"):
            self._sessiz = True
            self.gorunum.setCurrentText(ek.GORUNUMLER[1])
            self.ta.alan.setCurrentText("Encümen Tarih" if a == "encumen" else "Ödeme Makbuz Tarih")
            self._sessiz = False
            self.ta.hizli("Bu ay")  # listeyi de yeniler
        else:
            self._sessiz = True
            if a == "gecik":
                self.gecik.setChecked(True)
            elif a == "parsel":
                self.parsel_f.setChecked(True)
            self._sessiz = False
            self.load()

    # ------------------------------------------------ kayıtlı filtreler
    def gorunum_al(self):
        return {"gorunum": self.gorunum.currentText(), "lf": {k: cb.currentText() for k, cb in self.lf.cb.items()},
                "alan": self.ta.alan.currentText(), "bas": self.ta.bas, "bit": self.ta.bit, "preset": self.ta.preset,
                "ara": self.ara.text(), "eksik": bool(self.eksik.isChecked()), "gecik": bool(self.gecik.isChecked()),
                "siralama": list(self.siralama) if self.siralama else None}

    def gorunum_uygula(self, v):
        self.filtre_sifirla()
        self._sessiz = True
        try:
            if v.get("gorunum") in ek.GORUNUMLER:
                self.gorunum.setCurrentText(v["gorunum"])
            for k, val in v.get("lf", {}).items():
                if k in self.lf.cb:
                    self.lf.cb[k].setEditText(val)
            if v.get("alan") in ek.TARIH_ALANLARI:
                self.ta.alan.setCurrentText(v["alan"])
            self.ara.setText(v.get("ara", ""))
            self.eksik.setChecked(bool(v.get("eksik")))
            self.gecik.setChecked(bool(v.get("gecik")))
            sr = v.get("siralama")
            self.siralama = tuple(sr) if sr else None
        finally:
            self._sessiz = False
        if v.get("preset"):
            self.ta.hizli(v["preset"])  # "Bu ay" gibi göreli aralıklar her seferinde güncel hesaplanır; listeyi de yeniler
        else:
            self.ta.ayarla(v.get("bas", ""), v.get("bit", ""))
            self.load()

    def gm_doldur(self):
        m = self.gm
        m.clear()
        self._eylem(m, "Geçerli filtreyi kaydet...", self.gorunum_kaydet)
        m.addSeparator()
        for ad, v in ek.BAZI_GORUNUM.items():
            self._eylem(m, ad, lambda v=v: self.gorunum_uygula(v))
        kayitli = sorted(ek.q("SELECT ad, veri FROM gorunum"), key=lambda r: ek.tr_sira(r[0]))
        if kayitli:
            m.addSeparator()
            for ad, veri in kayitli:
                self._eylem(m, ad, lambda veri=veri: self.gorunum_uygula(json.loads(veri)))
            sm = m.addMenu("Kayıtlı filtreyi sil")
            for ad, _ in kayitli:
                self._eylem(sm, ad, lambda ad=ad: self.gorunum_sil(ad))

    def gorunum_kaydet(self):
        ad, tamam = QtWidgets.QInputDialog.getText(self, "Filtreyi kaydet", "Bu filtre kombinasyonuna bir ad verin:")
        if not tamam or not ad.strip():
            return
        ad = ad.strip()
        if ek.q("SELECT 1 FROM gorunum WHERE ad=?", (ad,)) and not self.sor("Kayıtlı filtre", f"“{ad}” adlı filtre zaten var. Üzerine yazılsın mı?"):
            return
        ek.q("INSERT OR REPLACE INTO gorunum VALUES (?,?)", (ad, json.dumps(self.gorunum_al(), ensure_ascii=False)))
        self.bildir(f"Filtre kaydedildi: {ad}")

    def gorunum_sil(self, ad):
        if self.sor("Kayıtlı filtreyi sil", f"“{ad}” silinsin mi?"):
            ek.q("DELETE FROM gorunum WHERE ad=?", (ad,))
            self.bildir(f"Filtre silindi: {ad}")

    # ------------------------------------------------ mesaj kutuları
    def bilgi(self, baslik, metin):
        QtWidgets.QMessageBox.information(self, baslik, metin)

    def uyari(self, baslik, metin):
        QtWidgets.QMessageBox.warning(self, baslik, metin)

    def hata(self, baslik, metin):
        QtWidgets.QMessageBox.critical(self, baslik, metin)

    def sor(self, baslik, metin):
        B = QtWidgets.QMessageBox.StandardButton
        return QtWidgets.QMessageBox.question(self, baslik, metin, B.Yes | B.No, B.No) == B.Yes

    # ------------------------------------------------ geri alma
    def undo_push(self, ad, onceki, silinme=None):
        self.undo.append({"ad": ad, "onceki": onceki, "silinme": silinme})
        del self.undo[:-50]

    def undo_onceki(self, ad, ids):
        self.undo_push(ad, ek.kayit_snapshot(ids))

    def undo_ekle(self, ad, yeni_ids):
        self.undo_push(ad, {i: None for i in yeni_ids})

    def undo_temizle(self):
        self.undo.clear()

    def geri_al(self):
        if not self.undo:
            self.bildir("Geri alınacak işlem yok")
            return
        e = self.undo.pop()
        ek.undo_uygula(e)
        self.yenile_koru()
        self.bildir("Geri alındı: " + e["ad"])

    # ------------------------------------------------ seçim, hücre düzenleme
    def secili_satirlar(self):
        sat = sorted({i.row() for i in self.tablo.selectionModel().selectedRows()})
        return [self.model.rows[r] for r in sat if r < len(self.model.rows)]

    def sel_ids(self):
        return [i for i, _ in self.secili_satirlar()]

    def sec(self):
        x = self.sel_ids()
        if not x:
            self.bilgi("Uyarı", "Önce bir satır seçin.")
            return None
        if len(x) > 1:
            self.bilgi("Uyarı", "Bu işlem için tek bir satır seçin.")
            return None
        return x[0]

    def _basildi(self, index):
        self.edit_kapat()
        if index.isValid():
            self.son = (self.model.rows[index.row()][0], ek.TV_COLS[index.column()])

    def sag(self, poz):
        index = self.tablo.indexAt(poz)
        if not index.isValid():
            return
        self.son = (self.model.rows[index.row()][0], ek.TV_COLS[index.column()])
        if not self.tablo.selectionModel().isRowSelected(index.row(), QtCore.QModelIndex()):
            self.tablo.selectRow(index.row())
        self.menu.exec(self.tablo.viewport().mapToGlobal(poz))

    def cift(self, index):
        if not index.isValid():
            return
        iid, k = self.model.rows[index.row()][0], ek.TV_COLS[index.column()]
        self.son = (iid, k)
        self.tablo.selectRow(index.row())
        if k in ("karar_no", "karar_ok"):
            self.ac("karar")
        elif k in ("makbuz_no", "makbuz_ok"):
            self.ac("makbuz")
        else:
            QtCore.QTimer.singleShot(50, lambda: self.hucre(iid, k))

    def f2(self):
        if self.son and self.model.satir_bul(self.son[0]) >= 0:
            self.hucre(*self.son)
        else:
            self.bilgi("Uyarı", "Önce bir hücreye tıklayın.")

    def edit_kapat(self):
        w = self.delegate.aktif if hasattr(self, "delegate") else None
        if w is not None:
            self.delegate.aktif = None
            try:
                self.delegate.closeEditor.emit(w, QtWidgets.QAbstractItemDelegate.EndEditHint.RevertModelCache)
            except RuntimeError:
                pass

    def hucre(self, iid, k):
        self.edit_kapat()
        if k in DUZENLENEMEZ:
            return
        r = self.model.satir_bul(iid)
        if r < 0:
            return
        if k in ek.DATES:  # tarih hücreleri takvimle düzenlenir (eski programdaki gibi)
            s = sek.takvim_sec(self, self.model.rows[r][1].get(k, ""), ek.DATES[k])
            if s is not None:
                self.kaydet(iid, k, s)
            return
        index = self.model.index(r, KOLON_NO[k])
        self.tablo.setCurrentIndex(index)
        self.tablo.edit(index)

    def kaydet(self, iid, k, v):
        iid = int(iid)
        v = (ek.para_bicim(v) if k == "alinan_ucret" else
             (ek.tarih_bicim(v) if k in ek.DATES else (ek.islem_kanon(v) if k == "islem" else v.strip())))
        if (ek.q(f"SELECT {k} FROM kayit WHERE id=?", (iid,))[0][0] or "") == v:  # değişmediyse dokunma
            return
        self.undo_onceki("Hücre düzenleme: " + ek.LAB.get(k, k), [iid])
        if k == "onay":
            eski = ek.q("SELECT onay FROM kayit WHERE id=?", (iid,))[0][0] or ""
            if eski != v:
                ek.q("UPDATE kayit SET durum_tarihi=? WHERE id=?", (ek.bugun_str(), iid))
        ek.q(f"UPDATE kayit SET {k}=? WHERE id=?", (v, iid))
        r = self.model.satir_bul(iid)
        if r >= 0:
            d = self.model.rows[r][1]
            d[k] = v
            if k in ("karar_no", "makbuz_no"):
                tur = k[:-3]
                x = ek.q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (iid,))[0]
                d[tur + "_ok"] = ek.dosya_isaret(tur, {tur + "_no": x[0] or "", tur + "_dosya": x[1] or ""},
                                                 ek.dosya_indeksi(ek.ayar(tur + "_klasor")))
            self.model.dataChanged.emit(self.model.index(r, 0), self.model.index(r, len(ek.TV_COLS) - 1))
        t = ek.LISTE_ALAN.get(k)
        if t and v:
            ek.q("INSERT OR IGNORE INTO liste VALUES (?,?)", (t, v))
            self.fil_yenile()
        self.durum_guncelle()
        if k == "onay":
            self.yenile_koru(iid)
        else:
            self.kart_guncelle(self.tum_kayitlar())
            self.detay_guncelle()

    # ------------------------------------------------ 2. aşama pencereleri
    def liste_combo(self, tur):
        """Formlardaki seçim kutusu (tıklayınca liste açılır, yazdıkça daralır). Değerler 'liste' tablosundan gelir."""
        return ListeKutu(ek.liste(tur))

    def takvim_sec(self, ust, metin=""):
        """None: iptal, '': temizle, 'gg.aa.yyyy': seçilen tarih."""
        return sek.takvim_sec(ust, metin)

    def zincir_detay(self, k):
        """Parsel hareket listesi penceresi (Özet / Tablo / Grafik)."""
        sek.ZincirDetay(self, k).exec()

    def sec_idler(self, idler):
        self.tablo.clearSelection()
        for i in idler:
            r = self.model.satir_bul(i)
            if r >= 0:
                self.tablo.selectionModel().select(
                    self.model.index(r, 0), QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows)

    def yeni(self):
        self.edit_kapat()
        pen.Form(self).exec()

    def duzenle(self):
        i = self.sec()
        if i:
            pen.Form(self, i).exec()

    def cogalt(self):
        """Seçili satırdan yeni kayıt: yalnızca mahalle, ada/parsel ve müellif taşınır; diğer alanlar boş gelir."""
        i = self.sec()
        if i:
            pen.Form(self, kopya=i).exec()

    def toplu(self):
        ids = self.sel_ids()
        if not ids:
            self.bilgi("Uyarı", "Önce satırları seçin (Ctrl veya Shift tuşuyla birden çok satır seçebilirsiniz).")
            return
        pen.TopluGuncelle(self, ids).exec()

    def listeler_ac(self):
        pen.Listeler(self).exec()

    def silinenler_ac(self):
        pen.Silinenler(self).exec()

    def pasif_liste_ac(self):
        pen.PasifListe(self).exec()

    def rapor_ayar_ac(self):
        pen.RaporAyar(self).exec()

    def kopyala(self):
        sec = self.secili_satirlar()
        if not sec:
            return
        if len(sec) == 1 and self.son and self.son[0] == sec[0][0]:
            k = self.son[1]
            d = sec[0][1]
            metin = d.get(k)
            if metin is None:
                metin = str(self.model.data(self.model.index(self.model.satir_bul(sec[0][0]), KOLON_NO[k])) or "")
            metin = str(metin)
        else:  # birden çok satır: Excel'e yapıştırılabilir (sekmeyle ayrılmış)
            metin = "\n".join("\t".join(d[k] for k in ek.SHOWN) for _, d in sec)
        QtWidgets.QApplication.clipboard().setText(metin)

    # ------------------------------------------------ satır işlemleri
    def sil(self):
        ids = self.sel_ids()
        if not ids:
            self.bilgi("Uyarı", "Önce silinecek satır(lar)ı seçin.")
            return
        msg = ("Kayıt silinsin mi?" if len(ids) == 1 else f"{len(ids)} kayıt silinsin mi?") + \
            "\n\n(Veri > Son silinenler bölümünden 90 gün içinde geri getirebilirsiniz.)"
        if self.sor("Sil", msg):
            snap = ek.kayit_snapshot(ids)
            zaman = pen.kayit_sil_idli(ids)  # eski numarayı da saklar (geri getirmede TKGM bağlantısı korunur)
            self.undo_push(f"Silme ({len(ids)} kayıt)", snap, zaman)
            self.load()

    def parsel_onay_kaldir(self, ids):
        n = 0
        for i in ids:
            if (self.pk.get(i) or {}).get("onay"):
                ek.q("UPDATE parsel_kontrol SET onay_bekliyor=0 WHERE work_id=?", (i,))
                n += 1
        self.load()
        return n

    def parsel_onayla(self):
        """Pasif parsel uyarısını kaldırır (işin durumuna dokunmaz)."""
        ids = self.sel_ids()
        if not ids:
            self.bilgi("Uyarı", "Önce satır(lar)ı seçin.")
            return
        n = self.parsel_onay_kaldir(ids)
        self.bildir(f"{n} kayıt için parsel uyarısı kaldırıldı" if n else "Seçili kayıtlarda onay bekleyen parsel uyarısı yok")

    def ok_yenile(self, iid, tur):
        r = self.model.satir_bul(iid)
        if r >= 0:
            x = ek.q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (iid,))[0]
            self.model.rows[r][1][tur + "_ok"] = ek.dosya_isaret(
                tur, {tur + "_no": x[0] or "", tur + "_dosya": x[1] or ""}, ek.dosya_indeksi(ek.ayar(tur + "_klasor")))
            self.model.dataChanged.emit(self.model.index(r, 0), self.model.index(r, len(ek.TV_COLS) - 1))

    def dosya_sec_dialog(self, tur):
        """Karar ve makbuz için ayrı ayrı son seçilen klasörü hatırlar. Dosyayı yüklemez, yolunu döndürür."""
        ad = "Karar" if tur == "karar" else "Makbuz (dekont)"
        baslangic = ""
        for k in (f"son_{tur}_klasoru", f"{tur}_klasor"):
            d = ek.ayar(k)
            if d and os.path.isdir(d):
                baslangic = d
                break
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, f"{ad} dosyasını seçin (PDF veya resim)", baslangic,
            "PDF ve resimler (*.pdf *.jpg *.jpeg *.png *.tif *.tiff);;Tüm dosyalar (*.*)")
        if not p:
            return ""
        p = os.path.normpath(p)
        ayar_yaz(f"son_{tur}_klasoru", os.path.dirname(p))
        return p

    def dosya_sec(self, tur, i=None):
        """Dosyayı yüklemez; yalnızca seçilen dosyanın yolunu kayda işler."""
        i = i or self.sec()
        if not i:
            return None
        p = self.dosya_sec_dialog(tur)
        if not p:
            return None
        self.undo_onceki("Dosya yolu seçimi", [i])
        ek.q(f"UPDATE kayit SET {tur}_dosya=? WHERE id=?", (p, i))
        ek.dosya_cache_temizle()
        self.ok_yenile(i, tur)
        return p

    def ac(self, tur):
        i = self.sec()
        if not i:
            return
        ad = "Karar" if tur == "karar" else "Makbuz"
        no, dosya = ek.q(f"SELECT {tur}_no,{tur}_dosya FROM kayit WHERE id=?", (i,))[0]
        no, dosya = no or "", dosya or ""
        p = dosya if dosya and os.path.exists(dosya) else ek.find_file(ek.ayar(tur + "_klasor"), no)
        if p:
            ek.open_file(p)
            return
        if dosya:
            mesaj = f"Kayıtlı dosya bulunamadı (taşınmış, silinmiş veya ağa ulaşılamıyor olabilir):\n{dosya}\n\nYeni dosya seçmek ister misiniz?"
        else:
            mesaj = (f"Bu kayıt için {ad.lower()} dosyası tanımlı değil.\n\nŞimdi bir dosya seçmek ister misiniz? "
                     "(Dosya yüklenmez, sadece yolu kaydedilir.)")
        if self.sor(f"{ad} dosyası", mesaj):
            yeni = self.dosya_sec(tur, i)
            if yeni:
                ek.open_file(yeni)

    def klasorler(self):
        for tur, ad in [("karar", "Karar dosyalarının klasörü"), ("makbuz", "Makbuz dosyalarının klasörü")]:
            self.bilgi("Klasör (isteğe bağlı)", ad + " seçilecek.\nBu ayar yalnızca dosya yolu elle seçilmemiş kayıtlar için, "
                       "dosya adı karar/makbuz numarasıyla (ör. 599.pdf) eşleşirse kullanılır.")
            p = QtWidgets.QFileDialog.getExistingDirectory(self, ad)
            if p:
                ayar_yaz(tur + "_klasor", p)
        ek.dosya_cache_temizle()
        self.load()

    # ------------------------------------------------ rapor, CSV
    def gorunen(self):
        tum = dict(self.tum_kayitlar())
        return [tum[i] for i, _ in self.model.rows if i in tum]

    def filtre_ozeti(self):
        p = ["Görünüm: " + self.gorunum.currentText()]
        for k, ad in ListeFiltreleri.ALANLAR:
            if self.lf.aktif(k):
                p.append(f"{ad}: {self.lf.cb[k].currentText()}")
        b, e = self.ta.bas, self.ta.bit
        if b or e:
            p.append(f"{self.ta.alan.currentText()}: {b or '...'} - {e or '...'}")
        if self.ara.text().strip():
            p.append(f"Arama: {self.ara.text().strip()}")
        if self.eksik.isChecked():
            p.append("Dosyası eksik olanlar")
        if self.gecik.isChecked():
            p.append(f"Geciken işler (>{self.esik()} gün)")
        return " | ".join(p) + "   —   Düzenlenme: " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    def rapor_liste(self):
        sat = self.gorunen()
        if not sat:
            self.bilgi("Rapor", "Listede kayıt yok.")
            return
        ek.rapor_ac(ek.rapor_sayfasi("İmar Uygulamaları - Kayıt Listesi", self.filtre_ozeti(), ek.liste_html(sat)))

    def rapor_muellif(self):
        sat = self.gorunen()
        if not sat:
            self.bilgi("Rapor", "Listede kayıt yok.")
            return
        ek.rapor_ac(ek.rapor_sayfasi("Müellife Göre Harç Dökümü", self.filtre_ozeti(), ek.muellif_html(sat)))

    def excel_aktar(self):
        sat = self.gorunen()
        if not sat:
            self.bilgi("Rapor", "Listede kayıt yok.")
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Excel'e aktar", "", "Excel'de açılır (CSV) (*.csv)")
        if p:
            if not p.lower().endswith(".csv"):
                p += ".csv"
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Sıra"] + [ek.LAB[k] for k in ek.SHOWN] + [ek.LAB["bekleme"], ek.LAB["parsel_durum"], ek.LAB["parsel_yeni"]])
                for n, d in enumerate(sat, 1):
                    w.writerow([n] + [d[k] for k in ek.SHOWN] + [d["bekleme"], d["parsel_durum"], d["parsel_yeni"]])
            self.bilgi("Tamam", f"{len(sat)} kayıt aktarıldı:\n{p}")

    def csv_aktar(self):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV Aktar", "", "CSV (*.csv)")
        if p:
            if not p.lower().endswith(".csv"):
                p += ".csv"
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([ek.LAB[k] for k in ek.KEYS])
                w.writerows(ek.q(f"SELECT {','.join(ek.KEYS)} FROM kayit ORDER BY id"))

    def csv_al(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV Al", "", "CSV (*.csv)")
        if not p:
            return
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        idx = {}
        for i, h in enumerate(rows[0] if rows else []):
            k = ek.HDR.get(ek.tr_lower(ek.temiz(h)))
            if k and k not in idx:
                idx[k] = i
        if "mahalle" not in idx:
            self.hata("Hata", "Başlık satırı bulunamadı (MAHALLE sütunu yok).")
            return
        if ek.q("SELECT 1 FROM kayit LIMIT 1") and self.sor(
                "CSV Al", "Mevcut kayıtlar silinip dosyadaki kayıtlar yeniden yüklensin mi?\n(Hayır: mevcut kayıtlara eklenir)"):
            pen.kayit_sil_idli([r[0] for r in ek.q("SELECT id FROM kayit")])
        n = 0
        for r in rows[1:]:
            d = {k: (ek.temiz(r[i]) if i < len(r) else "") for k, i in idx.items()}
            if d.get("alinan_ucret"):
                d["alinan_ucret"] = ek.para_bicim(d["alinan_ucret"])
            for dk in ek.DATES:
                if d.get(dk):
                    d[dk] = ek.tarih_bicim(d[dk])
            if not any(d.values()):
                continue
            ek.q(f"INSERT INTO kayit ({','.join(d)}) VALUES ({','.join('?' * len(d))})", list(d.values()))
            for tur in ek.LT:
                if d.get(tur):
                    ek.q("INSERT OR IGNORE INTO liste VALUES (?,?)", (tur, d[tur]))
            n += 1
        g = ek.benzer_gruplar("islem", "islem", True)
        if g:
            ek.benzer_uygula("islem", "islem", g)
        self.undo_temizle()
        self.load()
        self.bilgi("Tamam", f"{n} kayıt aktarıldı." + (f"\n{len(g)} yinelenen işlem adı birleştirildi." if g else ""))

    # ------------------------------------------------ yedek
    def acilis(self):
        self.acilis_yedek()
        if not ek.ayar("ucret_bicim_v1"):  # eski kayıtlardaki ücretleri bir kez tek biçime çevir
            n = 0
            for i, u in ek.q("SELECT id, alinan_ucret FROM kayit"):
                yeni = ek.para_bicim(u or "")
                if yeni != (u or ""):
                    ek.q("UPDATE kayit SET alinan_ucret=? WHERE id=?", (yeni, i))
                    n += 1
            ayar_yaz("ucret_bicim_v1", "1")
            if n:
                self.load()
                self.bilgi("Ücret biçimi", f"{n} kaydın alınan ücreti tek biçime (9.500,00 ₺) çevrildi.")
        if not ek.ayar("tarih_bicim_v1"):  # eski kayıtlardaki tarihleri bir kez tek biçime çevir
            n = bozuk = 0
            sut = list(ek.DATES) + ["durum_tarihi"]
            for r in ek.q(f"SELECT id,{','.join(sut)} FROM kayit"):
                eski = [x or "" for x in r[1:]]
                yeni = [ek.tarih_bicim(x) for x in eski]
                bozuk += sum(1 for x in yeni if x and not ek.tarih_oku(x))
                if yeni != eski:
                    ek.q(f"UPDATE kayit SET {','.join(k + '=?' for k in sut)} WHERE id=?", yeni + [r[0]])
                    n += 1
            ayar_yaz("tarih_bicim_v1", "1")
            if n or bozuk:
                self.load()
                msg = f"{n} kaydın tarihleri tek biçime (13.10.2026) çevrildi."
                if bozuk:
                    msg += f"\n\n{bozuk} tarih anlaşılamadığı için olduğu gibi bırakıldı; tabloda gözle kontrol etmenizi öneririm."
                self.bilgi("Tarih biçimi", msg)
        if not ek.ayar("islem_birlestir_v1"):  # yinelenen işlem adlarını bir kez birleştir
            g = ek.benzer_gruplar("islem", "islem", True)
            ayar_yaz("islem_birlestir_v1", "1")
            if g:
                ek.benzer_uygula("islem", "islem", g)
                self.load()
                self.bilgi("İşlem adları", "Yinelenen işlem adları birleştirildi, kayıtlar güncellendi:\n\n" + ek.benzer_ozet(g))

    def acilis_yedek(self):
        kl = ek.yedek_klasor()
        bugun = os.path.join(kl, f"imar_kayitlari_{datetime.date.today():%Y-%m-%d}.db")
        bugun_parsel = os.path.join(kl, f"parsel_kayitlari_{datetime.date.today():%Y-%m-%d}.db")
        parsel_var = os.path.exists(os.path.join(ek.BASE, "parsel_kayitlari.db"))
        if not os.path.exists(bugun) or (parsel_var and not os.path.exists(bugun_parsel)):
            try:
                _, _, phata = yedekle_hepsi()
                if phata:
                    self.uyari("Parsel yedeği alınamadı", f"parsel_kayitlari.db yedeği alınamadı:\n{phata}")
            except Exception as ex:
                self.uyari("Yedek alınamadı", f"Otomatik yedek alınamadı:\n{ex}\n\nYedek klasörünü Yedek menüsünden değiştirebilirsiniz.")

    def yedek_simdi(self):
        try:
            yol, pyol, phata = yedekle_hepsi()
            msg = "Yedek alındı:\n" + yol
            if pyol:
                msg += "\n" + pyol
            if phata:
                msg += f"\n\nUyarı: parsel_kayitlari.db yedeği alınamadı:\n{phata}"
            self.bilgi("Yedek", msg)
        except Exception as ex:
            self.hata("Hata", f"Yedek alınamadı:\n{ex}")

    def yedek_klasoru_sec(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Yedek klasörü (örn. ağdaki bir klasör)", ek.yedek_klasor())
        if p:
            ayar_yaz("yedek_klasor", p)
            self.bilgi("Yedek", "Yedek klasörü ayarlandı:\n" + p)

    def yedek_geri_yukle(self):
        kl = ek.yedek_klasor()
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Geri yüklenecek yedeği seçin", kl if os.path.isdir(kl) else ek.BASE,
                                                     "Veritabanı (*.db)")
        if not p:
            return
        try:
            c = sqlite3.connect(p)
            try:
                c.execute("SELECT COUNT(*) FROM kayit").fetchone()
            finally:
                c.close()
        except Exception:
            self.hata("Hata", "Seçilen dosya geçerli bir kayıt yedeği değil.")
            return
        if not self.sor("Geri yükle", "Şu anki kayıtların yerine seçtiğiniz yedek yüklenecek.\n"
                        "(Mevcut hâliniz önce ayrı bir dosya olarak saklanır.) Devam edilsin mi?"):
            return
        try:
            yedekle_hepsi("geri_yukleme_oncesi_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            ek.db_kopyala(p, ek.DB)
            ek.init_db()
            pen.silinen_hazirla()
            self.undo_temizle()
            self.load()
            self.bilgi("Tamam", "Yedek geri yüklendi.")
        except Exception as ex:
            self.hata("Hata", f"Geri yükleme başarısız:\n{ex}")

    # ------------------------------------------------ TKGM (Parsel Sorgu) köprüsü
    def parsel_sorgu_ac(self):
        """İş Takip'teki AÇIK işleri parsel sorgu penceresine aktarır; sonuçlar 'parsel_kontrol' tablosuna yazılır.
        Parsel Sorgu penceresi (PySide6) ayrı bir süreçte açılır (parsel_baslat.py)."""
        for modul in ("parsel_sorgu_modulu", "requests", "openpyxl"):
            if importlib.util.find_spec(modul) is None:
                self.hata("Parsel Sorgu", "Parsel Sorgu modülü yüklenemedi.\n\nparsel_sorgu_modulu.py bu programla aynı klasörde "
                          "olmalı ve 'pip install requests openpyxl' ile kütüphaneler kurulu olmalı.\n\nAyrıntı: “" + modul + "” bulunamadı.")
                return
        p = self._parsel_proc
        if p is not None and p.poll() is None:
            self.bildir("Parsel Sorgu penceresi zaten açık (görev çubuğuna bakın)", 5000)
            return
        # Hafif sorgu: tum_kayitlar() kullanılmaz (ağ klasörlerindeki dosyaları taramaz, bu yüzden pencere donmaz)
        kaynak = [(i, mh, ap) for i, mh, ap, onay in ek.q("SELECT id, mahalle, ada_parsel, onay FROM kayit")
                  if not ek.arsiv_mi(onay) and (mh or "").strip() and (ap or "").strip()]
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump(kaynak, f, ensure_ascii=False)
                kaynak_yolu = f.name
            self._parsel_log = os.path.join(tempfile.gettempdir(), "parsel_baslat.log")
            log = open(self._parsel_log, "w", encoding="utf-8")
            if getattr(sys, "frozen", False):
                komut = [sys.executable, "--parsel-baslat", kaynak_yolu, ek.DB]
            else:
                komut = [sys.executable, os.path.abspath(__file__), "--parsel-baslat", kaynak_yolu, ek.DB]
            try:
                self._parsel_proc = subprocess.Popen(komut, cwd=ek.BASE, stdout=log, stderr=log)
            finally:
                log.close()
        except Exception as ex:
            self.hata("Parsel Sorgu", f"Parsel Sorgu penceresi başlatılamadı:\n{ex}")
            return
        self._parsel_imza = self._parsel_imza_al()
        self._parsel_zaman.start()
        self.bildir("Parsel Sorgu açılıyor...", 3000)

    def _parsel_imza_al(self):
        try:
            return ek.q("SELECT COUNT(*), COALESCE(MAX(son_kontrol),''), COALESCE(SUM(onay_bekliyor),0) FROM parsel_kontrol")[0]
        except sqlite3.Error:
            return None

    def _parsel_izle(self):
        """Parsel Sorgu sonuç yazdıkça tabloyu yeniler (eski 'sonuc_geri_cagir' karşılığı)."""
        imza = self._parsel_imza_al()
        if imza != self._parsel_imza:
            self._parsel_imza = imza
            self.load_gecikmeli(700)  # birçok sonuç art arda gelir: tabloyu tek seferde yenile
        p = self._parsel_proc
        if p is not None and p.poll() is not None:
            self._parsel_zaman.stop()
            self.load_gecikmeli(300)
            if p.returncode != 0:
                ayr = ""
                try:
                    with open(self._parsel_log, encoding="utf-8", errors="replace") as f:
                        ayr = f.read()[-1500:]
                except OSError:
                    pass
                self.uyari("Parsel Sorgu", "Parsel Sorgu penceresi beklenmedik şekilde kapandı veya açılamadı.\n\n"
                           f"Ayrıntı ({self._parsel_log}):\n{ayr}")
            self._parsel_proc = None


def main():
    ek.init_db()
    pen.silinen_hazirla()  # 'silinen' tablosuna eski_id sütunu (yoksa) eklenir; var olan veriye dokunulmaz
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(et.font_yap(10))
    pencere = AnaPencere()
    if pencere._buyut:
        pencere.showMaximized()
    else:
        pencere.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
