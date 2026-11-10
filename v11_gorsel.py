# -*- coding: utf-8 -*-
"""İş Takip V1.1 — alternatif-tema tasarım dilinin mevcut uygulamaya uyarlanmış katmanı.

Bu modül yalnızca görünümü etkiler. Veritabanı, kayıt iş akışları, TKGM ve iş kuralları
encumen_qt.py / encumen_kayit.py içinde kalır. Alternatif dalın demo kayıtları kullanılmaz.
"""
from PySide6 import QtGui


def font_ata(app):
    """IBM Plex Sans varsa kullan; kurulu değilse Windows/Qt güvenli fontlarına düş."""
    f = QtGui.QFont()
    f.setFamilies(["IBM Plex Sans", "Segoe UI Variable", "Segoe UI", "Arial"])
    f.setPointSizeF(9.5)
    app.setFont(f)


def qss_ek(t):
    """Mevcut QSS'in üzerine alternatif-tema görsel dilini uygular.

    t, encumen_tema.py içindeki mevcut renk jetonlarıdır. Böylece eski yedi tema ve
    yeni üç tema aynı görünüm katmanıyla çalışır.
    """
    body = "'IBM Plex Sans', 'Segoe UI Variable', 'Segoe UI', Arial"
    display = "'Space Grotesk', 'Segoe UI', Arial"
    mono = "'IBM Plex Mono', Consolas, monospace"
    return f"""
/* V1.1 — tipografi ve yüzey dili */
QWidget {{ font-family: {body}; }}
QToolTip {{
    background: {t['KART']}; color: {t['METIN']};
    border: 1px solid {t['KENAR']}; border-radius: 5px;
    padding: 6px 9px; font-size: 9pt;
}}

/* Üst bant: ağır renk bloğu yerine sakin, modern başlık yüzeyi */
QFrame#bant {{
    background: {t['KART']};
    border-bottom: 1px solid {t['KENAR']};
}}
QFrame#bant QLabel {{ background: transparent; color: {t['METIN']}; }}
QLabel#bantBaslik {{
    color: {t['METIN']}; font-family: {display};
    font-size: 16pt; font-weight: 650; padding: 12px 0 12px 20px;
}}
QLabel#bantAlt {{ color: {t['SOLUK']}; padding-left: 12px; font-size: 9pt; }}
QLabel#bildirim {{ color: {t['TURUNCU']}; padding: 0 18px; }}
QLabel#temaDugme {{
    color: {t['VURGU']}; background: {t['SEC']};
    border: 1px solid {t['KENAR']}; border-radius: 8px;
    padding: 5px 12px; margin: 10px 16px 10px 4px; font-weight: 600;
}}
QLabel#temaDugme:hover {{ background: {t['BHOV']}; }}

/* KPI kartları: ince kenar, sol vurgu çizgisi, daha belirgin rakam */
QFrame#kart {{
    background: {t['KART']}; border: 1px solid {t['KENAR']};
    border-left: 3px solid {t['VURGU']}; border-radius: 9px;
}}
QFrame#kart[vurgu="yesil"] {{ border-left-color: {t['YESIL']}; }}
QFrame#kart[vurgu="kirmizi"] {{ border-left-color: {t['KIRMIZI']}; }}
QFrame#kart[vurgu="turuncu"] {{ border-left-color: {t['TURUNCU']}; }}
QFrame#kart[vurgu="mor"] {{ border-left-color: {t['SAYI_MOR']}; }}
QFrame#kart QLabel {{ background: transparent; }}
QLabel#kartSayi {{
    font-family: {display}; font-size: 24pt; font-weight: 650;
    color: {t['SAYI_MAVI']};
}}
QLabel#kartBaslik {{ color: {t['SOLUK']}; font-size: 9pt; font-weight: 500; }}

/* Eylemler ve giriş alanları */
QPushButton {{
    font-family: {body}; font-size: 9pt; font-weight: 550;
    border-radius: 7px; padding: 6px 12px;
}}
QPushButton#vurgu {{ border-radius: 7px; font-weight: 650; }}
QToolButton {{
    font-family: {body}; font-size: 9pt; font-weight: 550;
    border-radius: 7px; padding: 6px 11px;
}}
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {{
    font-family: {body}; font-size: 9pt; border-radius: 7px;
    padding: 5px 9px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus,
QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {t['VURGU']};
}}

/* Açılır listeler ve sağ tık menüsü aynı görsel ailede */
QComboBox QAbstractItemView, QCompleter QAbstractItemView {{
    background: {t['BASLIK']}; color: {t['METIN']};
    border: 1px solid {t['KENAR']}; border-radius: 8px;
    padding: 4px; outline: none;
    selection-background-color: {t['VURGU']}; selection-color: #FFFFFF;
}}
QComboBox QAbstractItemView::item, QCompleter QAbstractItemView::item {{
    background: {t['KART']}; color: {t['METIN']};
    padding: 6px 9px; margin: 2px; border-radius: 5px;
}}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected,
QCompleter QAbstractItemView::item:hover, QCompleter QAbstractItemView::item:selected {{
    background: {t['VURGU']}; color: #FFFFFF;
}}
QMenu {{
    background: {t['BASLIK']}; color: {t['METIN']};
    border: 1px solid {t['KENAR']}; border-radius: 8px;
    padding: 5px; font-family: {body}; font-size: 9pt;
}}
QMenu::item {{
    background: {t['KART']}; color: {t['METIN']};
    padding: 6px 26px 6px 10px; margin: 2px;
    border: 1px solid {t['KENAR']}; border-radius: 5px;
}}
QMenu::item:selected {{
    background: {t['VURGU']}; color: #FFFFFF;
    border-color: {t['VURGU']}; font-weight: 600;
}}
QMenu::separator {{ height: 1px; background: {t['KENAR']}; margin: 4px 7px; }}

/* Sekmeler, tablo ve detay alanı */
QTabBar::tab {{
    background: transparent; color: {t['SOLUK']};
    padding: 8px 17px; margin: 0 4px 0 0;
    border: 1px solid transparent; border-radius: 7px;
    font-family: {body}; font-weight: 600;
}}
QTabBar::tab:hover {{ background: {t['BHOV']}; color: {t['METIN']}; }}
QTabBar::tab:selected {{
    background: {t['SEC']}; color: {t['VURGU']};
    border-color: {t['KENAR']};
}}
QTableView, QTableWidget {{
    background: {t['KART']}; border: 1px solid {t['KENAR']};
    border-radius: 8px; gridline-color: {t['KENAR']};
    selection-background-color: {t['SEC']}; selection-color: {t['METIN']};
    font-family: {body};
}}
QTableView::item, QTableWidget::item {{
    padding: 3px 7px; border-bottom: 1px solid {t['KENAR']};
}}
QHeaderView::section {{
    background: {t['BASLIK']}; color: {t['SOLUK']};
    padding: 8px 7px; border: none;
    border-bottom: 1px solid {t['KENAR']};
    font-family: {body}; font-size: 8pt; font-weight: 700;
}}
QHeaderView::section:hover {{ background: {t['BHOV']}; color: {t['METIN']}; }}
QTextEdit#detay {{
    background: {t['KART']}; border: 1px solid {t['KENAR']};
    border-radius: 8px;
}}

/* Daha sakin kaydırma çubukları */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {t['KENAR']}; border-radius: 4px; min-height: 28px; min-width: 28px;
}}
QScrollBar::handle:hover {{ background: {t['SOLUK']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
