"""
QSS üreticisi — tema tokenlarından Qt Style Sheet üretir.
"""

from __future__ import annotations

from tema import (FONT_BODY, FONT_DISPLAY, FONT_MONO, Theme, _resolve_family,
                  alpha)


def build_qss(t: Theme) -> str:
    p = t.palette
    m = t.metrics

    body = _resolve_family(FONT_BODY)
    display = _resolve_family(FONT_DISPLAY)
    mono = _resolve_family(FONT_MONO)

    return f"""
/* ============ Temel ============ */
/* font-size bilinçli olarak burada verilmez: QSS font özellikleri
   QFont.setFont() çağrılarını ezer. Uygulama geneli yazı tipi
   QApplication.setFont() ile verilir. */
QWidget {{
    background: {p.canvas};
    color: {p.text};
    font-family: "{body}";
    outline: none;
}}

QToolTip {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {m.radius_sm}px;
    padding: 6px 9px;
    font-family: "{body}";
    font-size: 12px;
}}

QLabel {{
    background: transparent;
}}

/* ============ Üst çubuk ============ */
#TopBar {{
    background: {p.surface};
    border-bottom: 1px solid {p.border};
}}

#AppTitle {{
    font-family: "{display}";
    font-size: 17px;
    font-weight: 600;
    color: {p.text};
    letter-spacing: 0.2px;
}}

#AppSubtitle {{
    font-family: "{body}";
    font-size: 12px;
    color: {p.text_faint};
}}

#UserChip {{
    font-family: "{body}";
    font-size: 12px;
    font-weight: 500;
    color: {p.text_muted};
    background: {p.surface_alt};
    border: 1px solid {p.border};
    border-radius: {m.radius_pill}px;
    padding: 4px 12px 4px 10px;
}}

/* ============ Sekmeler ============ */
QTabWidget::pane {{
    border: none;
    background: transparent;
    top: -1px;
}}

QTabBar {{
    background: {p.surface};
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background: transparent;
    color: {p.text_muted};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 4px;
    margin-right: 26px;
    font-family: "{body}";
    font-size: 13px;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    color: {p.text};
}}

QTabBar::tab:selected {{
    color: {p.accent};
    border-bottom: 2px solid {p.accent};
}}

/* ============ KPI kartları ============ */
#KpiCard {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {m.radius_lg}px;
}}

#KpiLabel {{
    font-family: "{body}";
    font-size: 11px;
    font-weight: 500;
    color: {p.text_faint};
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}

#KpiValue {{
    font-family: "{display}";
    font-size: 30px;
    font-weight: 600;
    color: {p.text};
}}

#KpiNote {{
    font-family: "{body}";
    font-size: 11px;
    color: {p.text_faint};
}}

#KpiAccent {{
    background: transparent;
}}

#KpiSpark {{
    background: transparent;
}}

/* ============ Toolbar ============ */
#Toolbar {{
    background: {p.surface};
    border-bottom: 1px solid {p.border};
}}

#ToolbarInner {{
    background: transparent;
}}

#FilterBar {{
    background: {p.surface_alt};
    border-bottom: 1px solid {p.border};
}}

#SectionLabel {{
    font-family: "{body}";
    font-size: 11px;
    font-weight: 600;
    color: {p.text_faint};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

#Divider {{
    background: {p.border};
    max-height: 20px;
}}

/* ============ Butonlar ============ */
QPushButton {{
    font-family: "{body}";
    font-size: 12px;
    font-weight: 500;
    color: {p.text};
    background: {p.surface};
    border: 1px solid {p.border_strong};
    border-radius: {m.radius}px;
    padding: 6px 13px;
    min-height: {m.control_height - 12}px;
}}

QPushButton:hover {{
    background: {p.surface_hover};
    border-color: {p.text_faint};
}}

QPushButton:pressed {{
    background: {p.surface_alt};
}}

QPushButton:disabled {{
    color: {p.text_faint};
    border-color: {p.border};
    background: {p.surface_alt};
}}

QPushButton#Primary {{
    background: {p.accent};
    color: {p.accent_text};
    border: 1px solid {p.accent};
    font-weight: 600;
}}

QPushButton#Primary:hover {{
    background: {p.accent_hover};
    border-color: {p.accent_hover};
}}

QPushButton#Primary:pressed {{
    background: {p.accent_press};
    border-color: {p.accent_press};
}}

QPushButton#Danger {{
    color: {p.danger};
    border-color: {alpha(p.danger, 0.45)};
    background: transparent;
}}

QPushButton#Danger:hover {{
    background: {p.danger_soft};
    border-color: {p.danger};
}}

QPushButton#Ghost {{
    background: transparent;
    border-color: transparent;
    color: {p.text_muted};
    padding: 6px 9px;
}}

QPushButton#Ghost:hover {{
    background: {p.surface_hover};
    color: {p.text};
}}

QPushButton#Ghost:checked {{
    background: {p.accent_soft};
    color: {p.accent};
}}

/* ============ Giriş alanları ============ */
QLineEdit, QComboBox, QSpinBox, QDateEdit {{
    font-family: "{body}";
    font-size: 12px;
    color: {p.text};
    background: {p.surface};
    border: 1px solid {p.border_strong};
    border-radius: {m.radius}px;
    padding: 5px 10px;
    min-height: {m.control_height - 12}px;
    selection-background-color: {p.accent};
    selection-color: {p.accent_text};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {p.accent};
    background: {p.surface};
}}

QLineEdit::placeholder {{
    color: {p.text_faint};
}}

QLineEdit#Search {{
    padding-left: 30px;
    background: {p.surface_sunken};
    border-color: {p.border};
}}

QLineEdit#Search:focus {{
    background: {p.surface};
    border-color: {p.accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.text_faint};
    width: 0;
    height: 0;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background: {p.surface};
    border: 1px solid {p.border_strong};
    border-radius: {m.radius}px;
    padding: 4px;
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    min-height: 24px;
    padding: 3px 8px;
    border-radius: {m.radius_sm}px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    border: none;
    background: transparent;
}}

/* ============ Onay kutusu ============ */
QCheckBox {{
    font-family: "{body}";
    font-size: 12px;
    color: {p.text_muted};
    spacing: 7px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {p.border_strong};
    border-radius: {m.radius_sm}px;
    background: {p.surface};
}}

QCheckBox::indicator:hover {{
    border-color: {p.accent};
}}

QCheckBox::indicator:checked {{
    background: {p.accent};
    border-color: {p.accent};
    image: none;
}}

/* ============ Radyo / segment ============ */
QRadioButton {{
    font-family: "{body}";
    font-size: 12px;
    color: {p.text_muted};
    spacing: 7px;
    background: transparent;
}}

QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    background: {p.surface};
}}

QRadioButton::indicator:checked {{
    border: 4px solid {p.accent};
    background: {p.surface};
}}

/* ============ Tablo ============ */
QTableView {{
    background: {p.surface};
    alternate-background-color: {p.surface};
    gridline-color: {p.grid};
    border: none;
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
    font-family: "{body}";
    font-size: 12px;
}}

QTableView::item {{
    padding: 0px 8px;
    border: none;
    border-bottom: 1px solid {p.grid};
    color: {p.text};
}}

QTableView::item:selected {{
    background: {p.accent_soft};
    color: {p.text};
}}

QTableView::item:hover {{
    background: {p.surface_hover};
}}

QHeaderView {{
    background: {p.surface_alt};
    border: none;
}}

QHeaderView::section {{
    background: {p.surface_alt};
    color: {p.text_faint};
    border: none;
    border-bottom: 1px solid {p.border};
    border-right: 1px solid {p.grid};
    padding: 0px 8px;
    font-family: "{body}";
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QHeaderView::section:hover {{
    background: {p.surface_hover};
    color: {p.text_muted};
}}

QTableCornerButton::section {{
    background: {p.surface_alt};
    border: none;
    border-bottom: 1px solid {p.border};
}}

/* ============ Kaydırma çubuğu ============ */
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {p.border_strong};
    border-radius: 5px;
    min-height: 32px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p.text_faint};
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {p.border_strong};
    border-radius: 5px;
    min-width: 32px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {p.text_faint};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
    border: none;
    background: none;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}

/* ============ Durum çubuğu ============ */
QStatusBar {{
    background: {p.surface};
    color: {p.text_muted};
    border-top: 1px solid {p.border};
    font-family: "{body}";
    font-size: 11px;
}}

QStatusBar::item {{
    border: none;
}}

/* ============ Ayırıcı / boş alan ============ */
QSplitter::handle {{
    background: {p.border};
}}

#StatusHint {{
    color: {p.text_faint};
    font-size: 11px;
}}

#StatusCount {{
    color: {p.text};
    font-weight: 600;
}}

#StatusMoney {{
    font-family: "{mono}";
    color: {p.text};
    font-weight: 600;
}}

/* ============ Menü ============ */
QMenu {{
    background: {p.surface};
    border: 1px solid {p.border_strong};
    border-radius: {m.radius}px;
    padding: 5px;
}}

QMenu::item {{
    padding: 6px 26px 6px 12px;
    border-radius: {m.radius_sm}px;
    color: {p.text};
    font-size: 12px;
}}

QMenu::item:selected {{
    background: {p.accent_soft};
    color: {p.text};
}}

QMenu::separator {{
    height: 1px;
    background: {p.border};
    margin: 4px 8px;
}}
"""
