"""
Modernize edilmiş "Kayıtlar" ekranı.

Ekran yapısı:
  Üst çubuk  → uygulama kimliği + tema düğmesi + kullanıcı
  Sekmeler  → Kayıtlar / Grafikler / Fen Klasörü
  KPI şerit → 5 ölçüm kartı (aksan + sparkline)
  Araç çubuğu→ arama + birincil eylemler + sağda filtre özeti
  Filtre    → tek satırda gruplandırılmış filtreler
  Tablo     → sol aksan şeridi + durum rozetleri + sekmeli rakamlar
  Durum çubuğu → özet + dosya göstergesi + efsane
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QPushButton, QSizePolicy,
                               QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import ikonlar
from bilesenler import (ROLE_ACCENT, ROLE_ALIGN, ROLE_BADGE, ROLE_BADGE_COLOR,
                        ROLE_COLOR, ROLE_STRIPE, ROLE_TEXT_ROLE, ROLE_WEIGHT,
                        KayitDelegate, KpiCard, StatusPill)
from tema import Theme, alpha, font, mix


# ---------------------------------------------------------------------------
# Durum tanımları — encümen akışı
# ---------------------------------------------------------------------------

DURUMLAR = [
    ("Encümene Girdi",   "stage_girdi"),
    ("Encümene Yazıldı", "stage_yazildi"),
    ("Ödeme Bekleniyor", "stage_odeme"),
    ("Tescilde Bekliyor","stage_tescil"),
    ("Görüş Soruldu",    "stage_gorus"),
    ("Tescil Edildi",    "stage_edildi"),
    ("Askıda Kaldı",     "stage_aska"),
    ("İptal",            "stage_iptal"),
]


def durum_rengi(theme: Theme, ad: str) -> str:
    p = theme.palette
    for name, token in DURUMLAR:
        if name == ad:
            return getattr(p, token)
    return p.text_muted


# ---------------------------------------------------------------------------
# Örnek veri — ekran görüntüsündeki kayıtlara sadık
# ---------------------------------------------------------------------------

KAYITLAR = [
    # mahalle, ada/parsel, işlem, encümen tarihi, karar no, tarih, ücret, açıklama, müellif, durum, ödeme makbuz, makbuz no, karar dosya, makbuz dosya, bekleme
    ("BEHRAM",        "957",          "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Hüsmettin", "Encümene Girdi",    "20.10.2026", "116408", "✗", "✓", "6"),
    ("GÜVECDERE",     "127/3",        "ifraz",        "27.10.2026", "626",   "",       "3.800,00 ₺",  "",                    "Hüsmettin", "Encümene Girdi",    "14.10.2026", "116104", "✓", "✓", "11"),
    ("KÖREKEM",       "286-487",      "tevhit-ifraz", "",           "",     "",       "11.400,00 ₺", "",                    "Hüsmettin", "Encümene Girdi",    "09.10.2026", "115031", "✗", "✓", "6"),
    ("PASALAR",       "155/38-39",    "tevhit-ifraz", "",           "",     "",       "11.400,00 ₺", "",                    "Hüsmettin", "Encümene Girdi",    "16.10.2026", "115266", "✗", "✓", "6"),
    ("ÜÇBEYLİ",       "616",          "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Hüsmettin", "Encümene Girdi",    "19.10.2026", "114666", "✗", "✓", "6"),
    ("BEHRAM",        "1098-1128",    "tevhit-ifraz", "",           "",     "",       "15.200,00 ₺", "",                    "Serkan Abi","Encümene Girdi",    "27.10.2026", "116689", "✓", "✓", "7"),
    ("KOSUBOĞAZI",    "1465",         "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Serkan Abi","Encümene Girdi",    "27.10.2026", "114870", "✓", "✓", "7"),
    ("MURADİYE/YAŞ…", "101/26",       "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Serkan Abi","Encümene Girdi",    "27.10.2026", "114871", "✓", "✓", "7"),
    ("BOSTANDERE",    "118/5",        "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Serkan Abi","Encümene Girdi",    "28.10.2026", "114914", "✓", "✓", "7"),
    ("KAVAKLI",       "165/1",        "yola terk",    "",           "",     "",       "—",          "",                    "Serkan Abi","Encümene Girdi",    "",           "",       "",   "",   "7"),
    ("KOSOVA",        "120/2",        "ifraz",        "",           "",     "",       "7.600,00 ₺",  "",                    "Hüsmettin", "Encümene Yazıldı",  "02.11.2026", "115816", "✓", "✓", "8"),
    ("MURADİYE/…",    "138/3",        "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Hüsmettin", "Encümene Yazıldı",  "22.10.2026", "116582", "✗", "✓", "8"),
    ("ATARİYE",       "124/12-13-14", "tevhit-yola terk","",        "",     "",       "3.840,97 ₺",  "",                    "Serhat",    "Encümene Yazıldı",  "28.10.2026", "115670", "✓", "✓", "11"),
    ("SÖĞÜTALAN",     "0/561",        "ifraz",        "",           "",     "",       "5.700,00 ₺",  "",                    "Serhat",    "Encümene Yazıldı",  "02.11.2026", "115881", "✓", "✓", "7"),
    ("SUNLUK",        "158/3",        "ifraz",        "",           "",     "",       "5.700,00 ₺",  "",                    "Hüsmettin", "Encümene Yazıldı",  "10.11.2026", "117221", "✓", "✓", "0"),
    ("DEMİRELİ",      "894",          "ifraz",        "",           "",     "",       "5.700,00 ₺",  "",                    "Hüsmettin", "Encümene Yazıldı",  "10.11.2026", "117222", "✓", "✓", "0"),
    ("MURADİYE/…",    "138/20",       "ifraz",        "",           "",     "",       "5.700,00 ₺",  "",                    "Serkan Abi","Encümene Yazıldı",  "09.11.2026", "B-6359","✓", "✓", "0"),
    ("ATATÜRK",       "748/20-21",    "tevhit",       "",           "",     "",       "3.922,61 ₺",  "",                    "1611/1018 Lih…","Encümene Yazıldı","10.11.2026","117194","✓", "✓", "0"),
    ("ATATÜRK",       "748/22-23",    "tevhit",       "",           "",     "",       "3.889,99 ₺",  "",                    "1611/1018 Lih…","Encümene Yazıldı","10.11.2026","117195","✓", "✓", "0"),
    ("ALİSEYDİ",      "384-406",      "imar uygulaması","13.01.2026","",    "26.01.2026","9.500,00 ₺","",                    "Hüsmettin", "Tescilde Bekliyor", "",           "",       "",   "",   "288"),
    ("KAVAKLI",       "165/2",        "ifraz",        "",           "",     "",       "3.800,00 ₺",  "",                    "Serkan Abi","Ödeme Bekleniyor",  "28.10.2026", "117240", "✓", "✗", "12"),
    ("YENİMAHALLE",   "402",          "ifraz",        "",           "",     "",       "5.700,00 ₺",  "",                    "Serhat",    "Görüş Soruldu",     "",           "",       "",   "",   "19"),
    ("ÇAMLIK",        "88/4-5",       "tevhit-ifraz", "",           "",     "",       "15.200,00 ₺", "",                    "Serkan Abi","Askıda Kaldı",      "22.10.2026", "115988", "✓", "✓", "23"),
]

KPI_SPARK = {
    "Açık işler": [58, 61, 59, 66, 70, 68, 74, 79, 76, 81, 80, 84],
    "Geciken işler": [22, 25, 24, 29, 33, 31, 36, 34, 38, 40, 39, 41],
    "Bu ay tahsil edilen harç": [24, 19, 28, 31, 26, 33, 29, 36, 34, 41, 38, 38],
}


# ---------------------------------------------------------------------------
# Yardımcı widget'lar
# ---------------------------------------------------------------------------

class IkonluButon(QPushButton):
    """Metin + vektörel ikon taşıyan buton."""

    def __init__(self, theme: Theme, text: str, icon_key: str = "",
                 kind: str = "", parent=None):
        super().__init__(text, parent)
        p = theme.palette
        if kind:
            self.setObjectName(kind)
        if icon_key:
            self.setIcon(ikonlar.icon(theme, icon_key, 15))
            self.setIconSize(QSize(15, 15))
        if kind == "Primary":
            self.setIcon(ikonlar.icon(theme, icon_key, 15, p.accent_text) if icon_key else ikonlar.icon(theme, "plus", 15, p.accent_text))
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class AramaKutusu(QLineEdit):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.setObjectName("Search")
        self.setPlaceholderText("Kayıtlarda ara…")
        self.setClearButtonEnabled(False)
        self.setMinimumWidth(240)


class BolumEtiketi(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SectionLabel")


class Ayirici(QFrame):
    def __init__(self, vertical: bool = True, parent=None):
        super().__init__(parent)
        if vertical:
            self.setFixedWidth(1)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setFixedHeight(1)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: %s;" % theme_border(self))


_theme_ref = None


def theme_border(theme: Theme | None = None) -> str:
    t = theme or _theme_ref
    return t.palette.border if t else "#DDD"


# ---------------------------------------------------------------------------
# Ana ekran
# ---------------------------------------------------------------------------

class KayitlarEkrani(QWidget):
    """Modernize edilmiş Kayıtlar sekmesi."""

    tema_degisti = Signal(str)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        global _theme_ref
        _theme_ref = theme
        self.setObjectName("KayitlarEkrani")
        self._build()

    # -- kurulum ------------------------------------------------------------

    def _build(self):
        t = self.theme
        p = t.palette

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._ust_cubuk())

        ic = QWidget(self)
        ic.setObjectName("IcAlan")
        ic_layout = QVBoxLayout(ic)
        ic_layout.setContentsMargins(0, 0, 0, 0)
        ic_layout.setSpacing(0)

        ic_layout.addWidget(self._kpi_seridi())
        ic_layout.addWidget(self._arac_cubugu())
        ic_layout.addWidget(self._filtre_seridi())

        split = QSplitter(Qt.Orientation.Vertical, ic)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(1)
        split.setStyleSheet(f"QSplitter::handle {{ background: {p.border}; }}")

        self.tablo = self._tablo()
        split.addWidget(self.tablo)

        self.durum_cubugu = self._durum_cubugu()
        split.addWidget(self.durum_cubugu)
        split.setSizes([760, 46])

        ic_layout.addWidget(split, 1)
        ic_layout.addWidget(self._efsane_seridi())
        root.addWidget(ic, 1)

    # -- üst çubuk ----------------------------------------------------------

    def _ust_cubuk(self) -> QWidget:
        t = self.theme
        p = t.palette

        bar = QWidget(self)
        bar.setObjectName("TopBar")
        bar.setFixedHeight(t.metrics.topbar_height)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 14, 0)
        lay.setSpacing(12)

        # marka
        mark = QLabel(bar)
        mark.setFixedSize(30, 30)
        mark.setPixmap(self._marka_pixmap())
        lay.addWidget(mark)

        # kimlik
        kim = QVBoxLayout()
        kim.setContentsMargins(0, 0, 0, 0)
        kim.setSpacing(0)

        baslik = QLabel("İmar Uygulamaları", bar)
        baslik.setObjectName("AppTitle")
        baslik.setFont(font("display", 17, 600))
        baslik.setMinimumWidth(172)
        baslik.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        kim.addWidget(baslik)

        alt = QLabel("Encümen karar ve makbuz kayıtları", bar)
        alt.setObjectName("AppSubtitle")
        alt.setFixedWidth(196)
        alt.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        kim.addWidget(alt)

        lay.addLayout(kim)
        lay.addSpacing(8)

        ayirici = QFrame(bar)
        ayirici.setFixedWidth(1)
        ayirici.setStyleSheet(f"background: {p.border};")
        lay.addWidget(ayirici)

        # sekmeler
        self.tab_butonlari = []
        for ad, ikon_key in (("Kayıtlar", "layers"),
                             ("Grafikler", "chart"),
                             ("Fen Klasörü", "folder")):
            b = QPushButton(ad, bar)
            b.setObjectName("Ghost")
            b.setCheckable(True)
            b.setChecked(ad == "Kayıtlar")
            b.setIcon(ikonlar.icon(t, ikon_key, 15, p.accent if ad == "Kayıtlar" else p.text_muted))
            b.setIconSize(QSize(15, 15))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(self._sekme_qss())
            b.clicked.connect(lambda _=False, x=ad: self._sekme_degisti(x))
            self.tab_butonlari.append(b)
            lay.addWidget(b)

        lay.addStretch(1)

        # sağ: tema düğmesi + kullanıcı
        self.tema_butonu = QPushButton(bar)
        self.tema_butonu.setObjectName("Ghost")
        self.tema_butonu.setIcon(ikonlar.icon(t, "sun" if not t.dark else "moon", 16, p.text_muted))
        self.tema_butonu.setIconSize(QSize(16, 16))
        self.tema_butonu.setToolTip("Temayı değiştir")
        self.tema_butonu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tema_butonu.clicked.connect(self._tema_degistir)
        lay.addWidget(self.tema_butonu)

        user = QLabel("◦  Kum", bar)
        user.setObjectName("UserChip")
        lay.addWidget(user)

        return bar

    def _sekme_qss(self) -> str:
        p = self.theme.palette
        return f"""
        QPushButton#Ghost {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: {self.theme.metrics.radius}px;
            color: {p.text_muted};
            font-size: 13px;
            font-weight: 500;
            padding: 7px 11px;
        }}
        QPushButton#Ghost:hover {{
            background: {p.surface_hover};
            color: {p.text};
        }}
        QPushButton#Ghost:checked {{
            background: {p.accent_soft};
            color: {p.accent};
            border-color: {alpha(p.accent, 0.35)};
        }}
        """

    def _marka_pixmap(self):
        """Uygulama işareti — ölçüm/plan temalı soyut geometri."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPainterPath

        t = self.theme
        p = t.palette
        pm = QPixmap(30, 30)
        pm.fill(Qt.GlobalColor.transparent)
        pr = QPainter(pm)
        pr.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # yuvarlatılmış koyu zemin
        bg = QPainterPath()
        bg.addRoundedRect(QRectF(0, 0, 30, 30), 8, 8)
        pr.fillPath(bg, QColor(p.accent))

        # parsel çizgileri
        pr.setPen(QPen(QColor(p.accent_text), 1.4))
        pr.drawLine(8, 8, 8, 22)
        pr.drawLine(8, 15, 22, 15)
        pr.drawLine(15, 8, 15, 22)

        # vurgulu parsel
        pr.setBrush(QColor(p.accent_text))
        pr.setPen(Qt.PenStyle.NoPen)
        pr.drawRect(QRectF(8.5, 8.5, 5.5, 5.5))
        pr.end()
        return pm

    def _sekme_degisti(self, ad: str):
        for b, ad2 in zip(self.tab_butonlari, ("Kayıtlar", "Grafikler", "Fen Klasörü")):
            b.setChecked(ad == ad2)
            p = self.theme.palette
            b.setIcon(ikonlar.icon(self.theme,
                                   {"Kayıtlar": "layers", "Grafikler": "chart", "Fen Klasörü": "folder"}[ad2],
                                   15, p.accent if ad == ad2 else p.text_muted))

    # -- KPI şeridi ---------------------------------------------------------

    def _kpi_seridi(self) -> QWidget:
        t = self.theme
        p = t.palette

        wrap = QWidget(self)
        wrap.setObjectName("KpiSerit")
        wrap.setStyleSheet(f"background: {p.canvas};")

        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        kartlar = [
            ("Açık işler", "84", "toplam 780 arşiv kaydı", p.text, "accent"),
            ("Bu ay encümen", "0", "son toplantı 28.10.2026", p.text_faint, "muted"),
            ("Geciken işler", "41", "eşik 90 gün aşıldı", p.danger, "danger"),
            ("Bu ay tahsil edilen harç", "38.213 ₺", "geçen aya göre +%12", p.success, "success"),
            ("Pasif parsel — onay bekliyor", "0", "kayıp yok", p.text_faint, "muted"),
        ]

        for baslik, deger, alt_not, renk, tip in kartlar:
            aksan = {
                "accent": p.accent,
                "danger": p.danger,
                "success": p.success,
                "muted": p.border_strong,
            }[tip]

            spark = KPI_SPARK.get(baslik)
            kart = KpiCard(t, baslik, deger, alt_not, aksan, spark, wrap)
            lay.addWidget(kart, 1)

        return wrap

    # -- araç çubuğu --------------------------------------------------------

    def _arac_cubugu(self) -> QWidget:
        t = self.theme
        p = t.palette

        bar = QWidget(self)
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(50)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 9, 16, 9)
        lay.setSpacing(8)

        self.arama = AramaKutusu(t, bar)
        lay.addWidget(self.arama)

        lay.addWidget(self._ikon_buton(t, "Yeni", "plus", "Primary"))
        lay.addWidget(self._ikon_buton(t, "Formda Düzenle", "pencil"))
        lay.addWidget(self._ikon_buton(t, "Toplu Güncelle", "refresh"))
        lay.addWidget(self._ikon_buton(t, "Sil", "trash", "Danger"))

        ay = QFrame(bar)
        ay.setFixedWidth(1)
        ay.setStyleSheet(f"background: {p.border};")
        lay.addWidget(ay)

        lay.addWidget(self._ikon_buton(t, "Kararı Aç", "building"))
        lay.addWidget(self._ikon_buton(t, "Makbuzu Aç", "receipt"))

        lay.addStretch(1)

        for ikon_key, ipucu in (("download", "Yedekle"), ("database", "Veri yönetimi"),
                                ("chart", "Rapor"), ("more", "Ekran")):
            b = QPushButton(bar)
            b.setObjectName("Ghost")
            b.setIcon(ikonlar.icon(t, ikon_key, 16, p.text_muted))
            b.setIconSize(QSize(16, 16))
            b.setToolTip(ipucu)
            b.setFixedWidth(30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b)

        return bar

    def _ikon_buton(self, t: Theme, text: str, ikon_key: str,
                    kind: str = "") -> QPushButton:
        p = t.palette
        b = QPushButton(text, self)
        if kind:
            b.setObjectName(kind)
        renk = p.accent_text if kind == "Primary" else p.text
        b.setIcon(ikonlar.icon(t, ikon_key, 15, renk))
        b.setIconSize(QSize(15, 15))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    # -- filtre şeridi ------------------------------------------------------

    def _filtre_seridi(self) -> QWidget:
        t = self.theme
        p = t.palette

        bar = QWidget(self)
        bar.setObjectName("FilterBar")
        bar.setFixedHeight(46)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(7)

        self.filtre_combo: dict = {}

        def grup(baslik, degerler, varsayilan=None):
            lay.addWidget(BolumEtiketi(baslik, bar))
            cb = QComboBox(bar)
            cb.addItems(degerler)
            if varsayilan is not None:
                cb.setCurrentText(varsayilan)
            cb.setMinimumWidth(112)
            lay.addWidget(cb)
            self.filtre_combo[baslik] = cb
            return cb

        grup("Görünüm", ["Aktif işler", "Tümü", "Geciken işler", "Arşiv"], "Aktif işler")
        grup("İşlem", ["(Tümü)", "ifraz", "tevhit", "tevhit-ifraz", "yola terk"])
        grup("Müellif", ["(Tümü)", "Hüsmettin", "Serkan Abi", "Serhat"])
        grup("Mahalle", ["(Tümü)", "BEHRAM", "GÜVECDERE", "KAVAKLI", "SÖĞÜTALAN"])
        grup("Durum", ["(Tümü)"] + [d[0] for d in DURUMLAR])

        ay = QFrame(bar)
        ay.setFixedWidth(1)
        ay.setStyleSheet(f"background: {p.border};")
        lay.addWidget(ay)

        cb_geciken = QCheckBox("Geciken işler", bar)
        cb_geciken.setFont(font("body", 12, 500))
        lay.addWidget(cb_geciken)

        cb_eksik = QCheckBox("Dosyası eksik olanlar", bar)
        lay.addWidget(cb_eksik)

        cb_pasif = QCheckBox("Pasif parsel", bar)
        lay.addWidget(cb_pasif)

        lay.addStretch(1)

        temizle = QPushButton("Filtreleri temizle", bar)
        temizle.setObjectName("Ghost")
        temizle.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(temizle)

        return bar

    # -- tablo --------------------------------------------------------------

    def _tablo(self) -> QTableWidget:
        t = self.theme
        p = t.palette

        tablo = QTableWidget(0, 16, self)
        tablo.setObjectName("KayitTablosu")
        tablo.setShowGrid(False)
        tablo.setAlternatingRowColors(False)
        tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tablo.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tablo.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                              QAbstractItemView.EditTrigger.EditKeyPressed)
        tablo.setSortingEnabled(False)
        tablo.setWordWrap(False)
        tablo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        basliklar = [
            "Sıra", "Mahalle", "Ada / Parsel", "İşlem", "Encümen\nTarihi",
            "Karar No", "Tarih", "Alınan Ücret", "Açıklamalar", "Müellif",
            "Onay Durumu", "Ödeme Makbuz", "Makbuz No", "Karar\nDosyası",
            "Makbuz\nDosyası", "Bekleme\n(Gün)",
        ]
        tablo.setHorizontalHeaderLabels(basliklar)

        hh = tablo.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setFixedHeight(46)

        genislikler = [40, 124, 106, 112, 86, 74, 84, 104, 132, 112, 152, 94, 80, 70, 72, 74]
        for i, g in enumerate(genislikler):
            tablo.setColumnWidth(i, g)

        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(15, QHeaderView.ResizeMode.Fixed)

        tablo.setItemDelegate(KayitDelegate(t, tablo))
        tablo.verticalHeader().setVisible(False)
        tablo.verticalHeader().setDefaultSectionSize(t.metrics.row_height)
        tablo.setShowGrid(False)

        self._tabloyu_doldur(tablo)

        return tablo

    def _tabloyu_doldur(self, tablo: QTableWidget):
        t = self.theme
        p = t.palette
        tablo.setRowCount(len(KAYITLAR))

        for r, kayit in enumerate(KAYITLAR):
            (mahalle, ada, islem, enc_tarih, karar_no, tarih, ucret, aciklama,
             muellif, durum, odeme, makbuz_no, karar_dosya, makbuz_dosya,
             bekleme) = kayit

            bekleme_int = int(bekleme) if bekleme.isdigit() else 0
            gecikmis = bekleme_int > 90

            veriler = [
                (str(r + 1), "mono", p.text_faint, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 400),
                (mahalle, "body", p.text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 600),
                (ada, "mono", p.text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 500),
                (islem, "body", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (enc_tarih, "mono", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (karar_no, "mono", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (tarih, "mono", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (ucret, "mono", p.text, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 500),
                (aciklama, "body", p.text_faint, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (muellif, "body", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                ("", "body", p.text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (odeme, "mono", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (makbuz_no, "mono", p.text_muted, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 400),
                (karar_dosya, "body", p.text, Qt.AlignmentFlag.AlignCenter, 500),
                (makbuz_dosya, "body", p.text, Qt.AlignmentFlag.AlignCenter, 500),
                (bekleme, "mono", p.danger if gecikmis else p.text_muted,
                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 600 if gecikmis else 400),
            ]

            for c, (metin, rol, renk, hiza, agirlik) in enumerate(veriler):
                it = QTableWidgetItem(metin)
                it.setData(ROLE_TEXT_ROLE, rol)
                it.setData(ROLE_COLOR, renk)
                it.setData(ROLE_ALIGN, hiza)
                it.setData(ROLE_WEIGHT, agirlik)
                it.setData(ROLE_STRIPE, durum_rengi(t, durum))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                tablo.setItem(r, c, it)

            # durum rozeti
            it = tablo.item(r, 10)
            if it is None:
                it = QTableWidgetItem("")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                tablo.setItem(r, 10, it)
            it.setData(ROLE_BADGE, durum)
            it.setData(ROLE_BADGE_COLOR, durum_rengi(t, durum))

        tablo.resizeRowsToContents()

    # -- durum çubuğu -------------------------------------------------------

    def _durum_cubugu(self) -> QWidget:
        t = self.theme
        p = t.palette

        bar = QWidget(self)
        bar.setObjectName("DurumCubugu")
        bar.setFixedHeight(38)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(9)

        kayit = QLabel("84 kayıt", bar)
        kayit.setObjectName("StatusCount")
        lay.addWidget(kayit)

        para = QLabel("Toplam alınan ücret  501.232,32 ₺", bar)
        para.setObjectName("StatusMoney")
        lay.addWidget(para)

        nokta = QLabel("•", bar)
        nokta.setStyleSheet(f"color: {p.text_faint};")
        lay.addWidget(nokta)

        gizli = QLabel("780 arşiv işi gizli", bar)
        gizli.setObjectName("StatusHint")
        lay.addWidget(gizli)

        ay = QFrame(bar)
        ay.setFixedWidth(1)
        ay.setStyleSheet(f"background: {p.border};")
        lay.addWidget(ay)

        # geciken uyarı rozeti
        geciken = QLabel("41 geciken iş", bar)
        geciken.setFont(font("body", 11, 600))
        geciken.setStyleSheet(
            f"color: {p.danger}; background: {p.danger_soft};"
            f"border-radius: 10px; padding: 3px 9px;")
        lay.addWidget(geciken)

        ay2 = QFrame(bar)
        ay2.setFixedWidth(1)
        ay2.setStyleSheet(f"background: {p.border};")
        lay.addWidget(ay2)

        # dosya göstergesi
        dosya = QLabel("Dosya:   ✓ var      ✗ yok      ? klasöre ulaşılamıyor", bar)
        dosya.setFont(font("body", 11, 500))
        dosya.setStyleSheet(f"color: {p.text_faint};")
        lay.addWidget(dosya)

        lay.addStretch(1)

        return bar

    def _efsane_seridi(self) -> QWidget:
        """Durum renkleri efsanesi — tablonun altında ince bir şerit."""
        t = self.theme
        p = t.palette

        bar = QWidget(self)
        bar.setObjectName("EfsaneSeridi")
        bar.setFixedHeight(30)
        bar.setStyleSheet(f"background: {p.surface_alt};")

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        bas = QLabel("Renkler", bar)
        bas.setObjectName("StatusHint")
        lay.addWidget(bas)

        for ad, token in DURUMLAR:
            renk = getattr(p, token)
            ch = QLabel(ad, bar)
            ch.setFont(font("body", 10, 500))
            ch.setStyleSheet(f"color: {p.text_muted};")
            lay.addWidget(ch)
            dot = QLabel("●", bar)
            dot.setStyleSheet(f"color: {renk}; font-size: 8px;")
            dot.setFixedWidth(9)
            lay.addWidget(dot)

        lay.addStretch(1)
        return bar

    # -- tema değişimi ------------------------------------------------------

    def _tema_degistir(self):
        from tema import THEMES
        anahtarlar = list(THEMES.keys())
        i = anahtarlar.index(self.theme.key)
        sonraki = anahtarlar[(i + 1) % len(anahtarlar)]
        self.tema_degisti.emit(sonraki)


# ---------------------------------------------------------------------------
# Yardımcı
# ---------------------------------------------------------------------------

from PySide6.QtGui import QPixmap  # noqa: E402
