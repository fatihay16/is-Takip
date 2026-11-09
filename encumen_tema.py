# -*- coding: utf-8 -*-
"""Encümen / TKGM ortak görünüm jetonları (lacivert-mavi-beyaz kurumsal tema, referans: Google AI Studio taslağı).

YALNIZCA görünüm: renkler, QSS ve palet üretir. İş mantığı, veritabanı ve ek.* işlevleri burada YOKTUR.
"""

ACIK = {
    "BG": "#EEF2F8", "KART": "#FFFFFF", "BASLIK": "#F4F6FA", "BHOV": "#E6ECF5",
    "METIN": "#1E293B", "SOLUK": "#7B8798", "KENAR": "#DDE3EC",
    "VURGU": "#1F5BFF", "VURGU_K": "#1448D6", "SEC": "#E3ECFF", "KIRMIZI": "#E11D48",
    "LACIVERT": "#1E3A8A", "LACIVERT_YAZI": "#DCE6FF", "LACIVERT_SOLUK": "#AFC3F2",
    "YESIL": "#0E9F6E", "YESIL_ZEMIN": "#DDF3E7", "TURUNCU": "#D97706", "TURUNCU_ZEMIN": "#FFEBCC",
    "KIRMIZI_ZEMIN": "#FBE0E0", "GRI": "#64748B", "GRI_ZEMIN": "#E8ECF2", "MAVI_ZEMIN": "#DCE9FB",
    "SAYI_MAVI": "#2563EB", "SAYI_YESIL": "#10A56B", "SAYI_KIRMIZI": "#F43F5E", "SAYI_TURUNCU": "#F59E0B",
    "SAYI_MOR": "#A855F7",
}
KOYU = {
    "BG": "#0B1220", "KART": "#141F33", "BASLIK": "#1A2840", "BHOV": "#22345A",
    "METIN": "#E6EDF7", "SOLUK": "#93A4BC", "KENAR": "#26364F",
    "VURGU": "#3B7BFF", "VURGU_K": "#5C93FF", "SEC": "#1F3866", "KIRMIZI": "#FF7B8F",
    "LACIVERT": "#172B63", "LACIVERT_YAZI": "#DCE6FF", "LACIVERT_SOLUK": "#9DB3E6",
    "YESIL": "#4CC38A", "YESIL_ZEMIN": "#173C30", "TURUNCU": "#F0B04A", "TURUNCU_ZEMIN": "#4A3817",
    "KIRMIZI_ZEMIN": "#4A2323", "GRI": "#9AA9BD", "GRI_ZEMIN": "#26364E", "MAVI_ZEMIN": "#1F3A63",
    "SAYI_MAVI": "#5B9BFF", "SAYI_YESIL": "#34D399", "SAYI_KIRMIZI": "#FB7185", "SAYI_TURUNCU": "#FBBF24",
    "SAYI_MOR": "#C084FC",
}
# grafik serisi: mavi ailesi (açık, koyu)
SERI = {
    False: ["#1F5BFF", "#3B82F6", "#60A5FA", "#1E3A8A", "#93C5FD", "#2563EB", "#1E40AF", "#7DA7E8"],
    True: ["#3B7BFF", "#6AA0F8", "#93C5FD", "#2F5FB3", "#BFDBFE", "#3B82F6", "#1E3A8A", "#7DA7E8"],
}

EK_RENK_ANAHTARLARI = ("BG", "KART", "BASLIK", "BHOV", "METIN", "SOLUK", "KENAR", "VURGU", "VURGU_K", "SEC", "KIRMIZI")


# ---- yazı sistemi
FONT_AILELER = ["Segoe UI Variable", "Segoe UI", "Arial"]   # Variable yoksa Segoe UI'ye düşer
MONO_AILELER = ["Consolas", "Courier New"]                  # karar no, tarih, alan (m²) gibi sayısal sütunlar


def font_yap(punto=10, kalin=False, yari=False, mono=False, aralik=0.0):
    """Tutarlı QFont üretir. kalin: Bold, yari: DemiBold (yarı kalın), mono: eşit genişlikli, aralik: harf aralığı (px)."""
    from PySide6 import QtGui
    f = QtGui.QFont()
    f.setFamilies(MONO_AILELER if mono else FONT_AILELER)
    f.setPointSizeF(float(punto))
    if kalin:
        f.setWeight(QtGui.QFont.Weight.Bold)
    elif yari:
        f.setWeight(QtGui.QFont.Weight.DemiBold)
    if aralik:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, aralik)
    return f


def jetonlar(koyu):
    return KOYU if koyu else ACIK


def birlestir(ek_tema, koyu):
    """ek'in kendi tema sözlüğü + yeni jetonlar (yeni jetonlar kazanır; ek'te olup burada olmayan anahtarlar korunur)."""
    t = dict(ek_tema or {})
    t.update(jetonlar(koyu))
    return t


def ek_renk_uygula(ek, koyu):
    """Sekmelerin doğrudan okuduğu ek.METIN/ek.KART... değişkenlerini yeni jetonlara çeker.
    Yalnızca ek'te ZATEN VAR OLAN renk adlarına dokunur; ek içindeki sözlük/işlev/ayar değişmez."""
    t = jetonlar(koyu)
    for k in EK_RENK_ANAHTARLARI:
        if hasattr(ek, k):
            setattr(ek, k, t[k])


def tr_buyuk(metin):
    """Türkçe büyük harf (i -> İ, ı -> I) — tablo başlıkları için."""
    return str(metin).replace("i", "İ").replace("ı", "I").upper()


def _rgb(hexkod):
    h = hexkod.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hap_renkleri(zemin_hex, koyu):
    """Durum hapı için (zemin, yazı) çifti. Zemin: mevcut durum rengi; yazı: aynı rengin koyulaştırılmış/açılmış tonu."""
    r, g, b = _rgb(zemin_hex)
    if koyu:
        yazi = tuple(int(c + (255 - c) * 0.78) for c in (r, g, b))
    else:
        yazi = tuple(int(c * 0.36) for c in (r, g, b))
    return zemin_hex, "#%02X%02X%02X" % yazi


def qss_yap(t):
    """Tüm uygulama için ortak görünüm (buton, giriş, liste, menü, sekme, kaydırma, kart, tablo, diyalog)."""
    return f"""
QToolTip {{ background:{t['KART']}; color:{t['METIN']}; border:1px solid {t['KENAR']}; padding:4px 6px; }}

/* ---- başlık bandı */
QFrame#bant {{ background:{t['LACIVERT']}; }}
QFrame#bant QLabel {{ background:transparent; color:{t['LACIVERT_YAZI']}; }}
QLabel#bantBaslik {{ color:white; font-size:16pt; font-weight:600; padding:12px 0px 12px 20px; }}
QLabel#bantAlt {{ color:{t['LACIVERT_SOLUK']}; padding-left:12px; font-size:9pt; }}
QLabel#bildirim {{ color:#fbbf24; padding:0px 18px; }}
QLabel#temaDugme {{ color:white; background:rgba(255,255,255,38); border-radius:8px; padding:5px 12px; margin:10px 16px 10px 4px; }}
QLabel#temaDugme:hover {{ background:rgba(255,255,255,70); }}

/* ---- özet kartları */
QFrame#kart {{ background:{t['KART']}; border:1px solid {t['KENAR']}; border-radius:12px; }}
QFrame#kart QLabel {{ background:transparent; }}
QLabel#kartSayi {{ font-size:22pt; font-weight:bold; color:{t['SAYI_MAVI']}; }}
QLabel#kartSayi[vurgu="mavi"] {{ color:{t['SAYI_MAVI']}; }}
QLabel#kartSayi[vurgu="yesil"] {{ color:{t['SAYI_YESIL']}; }}
QLabel#kartSayi[vurgu="kirmizi"] {{ color:{t['SAYI_KIRMIZI']}; }}
QLabel#kartSayi[vurgu="turuncu"] {{ color:{t['SAYI_TURUNCU']}; }}
QLabel#kartSayi[vurgu="mor"] {{ color:{t['SAYI_MOR']}; }}
QLabel#kartBaslik {{ color:{t['SOLUK']}; font-size:9pt; }}

/* ---- butonlar */
QPushButton {{ background:{t['KART']}; color:{t['METIN']}; border:1px solid {t['KENAR']}; border-radius:8px; padding:6px 14px; font-size:9.5pt; font-weight:600; }}
QPushButton:hover {{ background:{t['BHOV']}; }}
QPushButton:pressed {{ background:{t['SEC']}; }}
QPushButton:disabled {{ color:{t['SOLUK']}; background:{t['BASLIK']}; }}
QPushButton::menu-indicator {{ subcontrol-position:right center; subcontrol-origin:padding; right:6px; }}
QPushButton#vurgu {{ background:{t['VURGU']}; color:white; border:1px solid {t['VURGU']}; font-weight:bold; }}
QPushButton#vurgu:hover {{ background:{t['VURGU_K']}; border:1px solid {t['VURGU_K']}; }}
QPushButton#vurgu:disabled {{ background:{t['BASLIK']}; color:{t['SOLUK']}; border:1px solid {t['KENAR']}; }}
QPushButton#tehlike {{ color:{t['KIRMIZI']}; }}

/* ---- giriş alanları */
QLineEdit, QSpinBox, QDateEdit, QComboBox, QTextEdit, QPlainTextEdit {{
    background:{t['KART']}; color:{t['METIN']}; border:1px solid {t['KENAR']}; border-radius:8px; padding:5px 8px;
    selection-background-color:{t['VURGU']}; selection-color:white; }}
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border:1px solid {t['VURGU']}; }}
QLineEdit:disabled, QComboBox:disabled {{ background:{t['BASLIK']}; color:{t['SOLUK']}; }}
QComboBox QAbstractItemView, QCompleter QAbstractItemView {{ background:{t['KART']}; color:{t['METIN']}; border:1px solid {t['KENAR']};
    selection-background-color:{t['SEC']}; selection-color:{t['METIN']}; padding:2px; }}
QTableView QLineEdit {{ border-radius:0px; padding:0px 4px; border:1px solid {t['VURGU']}; }}
QComboBox QLineEdit {{ border:none; background:transparent; padding:0px; }}
QComboBox::drop-down {{ border:none; width:24px; }}
QComboBox::down-arrow {{ image:none; width:0px; height:0px; border-left:5px solid transparent; border-right:5px solid transparent;
    border-top:6px solid {t['SOLUK']}; margin-right:8px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width:20px; border:none; background:transparent; subcontrol-origin:border; }}
QSpinBox::up-button {{ subcontrol-position:top right; }}
QSpinBox::down-button {{ subcontrol-position:bottom right; }}
QSpinBox::up-arrow {{ image:none; width:0px; height:0px; border-left:4px solid transparent; border-right:4px solid transparent;
    border-bottom:5px solid {t['SOLUK']}; }}
QSpinBox::down-arrow {{ image:none; width:0px; height:0px; border-left:4px solid transparent; border-right:4px solid transparent;
    border-top:5px solid {t['SOLUK']}; }}
QCheckBox {{ spacing:7px; }}
QCheckBox::indicator {{ width:16px; height:16px; border:1px solid {t['SOLUK']}; border-radius:4px; background:{t['KART']}; }}
QCheckBox::indicator:hover {{ border:1px solid {t['VURGU']}; }}
QCheckBox::indicator:checked {{ background:{t['VURGU']}; border:1px solid {t['VURGU']}; }}
QCheckBox:disabled {{ color:{t['SOLUK']}; }}
QGroupBox {{ background:{t['KART']}; border:1px solid {t['KENAR']}; border-radius:10px; margin-top:14px; padding:10px; }}
QGroupBox::title {{ subcontrol-origin:margin; left:14px; padding:0px 6px; color:{t['VURGU']}; font-weight:bold; }}

/* ---- menü */
QMenu {{ background:{t['KART']}; color:{t['METIN']}; border:1px solid {t['KENAR']}; padding:6px; }}
QMenu::item {{ padding:6px 26px 6px 14px; border-radius:6px; }}
QMenu::item:selected {{ background:{t['SEC']}; color:{t['METIN']}; }}
QMenu::item:disabled {{ color:{t['SOLUK']}; }}
QMenu::separator {{ height:1px; background:{t['KENAR']}; margin:5px 8px; }}

/* ---- sekmeler (hap biçimli) */
QTabWidget::pane {{ border:none; top:4px; }}
QTabBar {{ qproperty-drawBase:0; }}
QTabBar::tab {{ background:transparent; color:{t['SOLUK']}; padding:8px 18px; margin:0px 4px 0px 0px; border-radius:8px; font-weight:600; }}
QTabBar::tab:hover {{ background:{t['BHOV']}; color:{t['METIN']}; }}
QTabBar::tab:selected {{ background:{t['VURGU']}; color:white; }}

/* ---- tablo */
QTableView, QTableWidget {{ background:{t['KART']}; border:1px solid {t['KENAR']}; border-radius:10px; gridline-color:{t['KENAR']};
              selection-background-color:{t['SEC']}; selection-color:{t['METIN']}; }}
QTableView::item {{ padding:3px 6px; border-bottom:1px solid {t['KENAR']}; }}
QHeaderView {{ background:transparent; }}
QHeaderView::section {{ background:{t['BASLIK']}; color:{t['SOLUK']}; padding:10px 8px; border:none; border-bottom:1px solid {t['KENAR']}; }}
QHeaderView::section:hover {{ background:{t['BHOV']}; }}
QTableCornerButton::section {{ background:{t['BASLIK']}; border:none; }}
QTextEdit#detay {{ background:{t['KART']}; border:1px solid {t['KENAR']}; border-radius:10px; }}

/* ---- kaydırma çubukları */
QScrollBar:vertical {{ background:transparent; width:11px; margin:2px; }}
QScrollBar:horizontal {{ background:transparent; height:11px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{t['KENAR']}; border-radius:4px; min-height:30px; }}
QScrollBar::handle:horizontal {{ background:{t['KENAR']}; border-radius:4px; min-width:30px; }}
QScrollBar::handle:hover {{ background:{t['SOLUK']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width:0px; height:0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}

QSplitter::handle {{ background:transparent; }}
QProgressBar {{ background:{t['KENAR']}; border:none; border-radius:5px; }}
QProgressBar::chunk {{ background:{t['VURGU']}; border-radius:5px; }}
QLabel#hap {{ border-radius:9px; padding:2px 10px; font-weight:bold; }}
"""


def palet_yap(t):
    from PySide6 import QtGui  # tembel import: modül PySide6 olmadan da (jeton/QSS testi için) yüklenebilir
    p = QtGui.QPalette()
    R = QtGui.QPalette.ColorRole
    G = QtGui.QPalette.ColorGroup
    for rol, anahtar in ((R.Window, "BG"), (R.WindowText, "METIN"), (R.Base, "KART"), (R.AlternateBase, "BASLIK"),
                         (R.Text, "METIN"), (R.Button, "KART"), (R.ButtonText, "METIN"), (R.ToolTipBase, "KART"),
                         (R.ToolTipText, "METIN"), (R.PlaceholderText, "SOLUK"), (R.BrightText, "KIRMIZI")):
        p.setColor(rol, QtGui.QColor(t[anahtar]))
    p.setColor(R.Highlight, QtGui.QColor(t["VURGU"]))
    p.setColor(R.HighlightedText, QtGui.QColor("white"))
    for rol in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(G.Disabled, rol, QtGui.QColor(t["SOLUK"]))
    return p
