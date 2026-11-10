"""
İmar Uygulamaları — Modern Tema Sistemi
=======================================
PySide6 / Qt6 tabanlı masaüstü uygulaması için tasarım token sistemi,
QSS üreticisi ve tema yöneticisi.

Üç modern tema tanımlıdır:
  • kadastro  — Kâğıt zeminli, sıcak nötr, arşiv kağıdı hissi (varsayılan)
  • gece      — Derin lacivert, düşük parlaklık, gece vardiyası
  • mürekkep  — Yüksek kontrastlı mürekkep/kağıt, bürokratik arşiv

Tipografi rolleri:
  • display  → Space Grotesk  (başlıklar, KPI rakamları)
  • body     → IBM Plex Sans  (arayüz metni, tablo hücreleri)
  • mono     → IBM Plex Mono  (para, tarih, ada/parsel, karar no)

Türkçe karakter desteği tüm fontlarda doğrulanmıştır (İ ı ş ğ ü ö ç ₺).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from PySide6.QtGui import QColor, QFont, QFontDatabase


# ---------------------------------------------------------------------------
# Font rolleri
# ---------------------------------------------------------------------------

FONT_DISPLAY = "Space Grotesk"
FONT_BODY = "IBM Plex Sans"
FONT_MONO = "IBM Plex Mono"

FAMILY_FALLBACK = {
    FONT_DISPLAY: ["Space Grotesk", "Inter", "DejaVu Sans"],
    FONT_BODY: ["IBM Plex Sans", "Inter", "DejaVu Sans"],
    FONT_MONO: ["IBM Plex Mono", "DejaVu Sans Mono", "Courier"],
}


def _resolve_family(preferred: str) -> str:
    """Fontu mevcut değilse geriye doğru güvenli bir aileye düşürür."""
    available = set(QFontDatabase.families())
    for name in FAMILY_FALLBACK.get(preferred, [preferred]):
        if name in available:
            return name
    return preferred


def font(role: str = "body", size: int = 13, weight: int = 400,
         letter_spacing: float = 0.0) -> QFont:
    """Rol tabanlı font üretir. letter_spacing px cinsindendir."""
    family = {
        "display": FONT_DISPLAY,
        "body": FONT_BODY,
        "mono": FONT_MONO,
    }.get(role, FONT_BODY)

    f = QFont(_resolve_family(family))
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    if letter_spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return f


# ---------------------------------------------------------------------------
# Tema token modeli
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    """Bir temanın renk tokenları. Tümü hex string (#RRGGBB)."""

    # Yüzeyler
    canvas: str          # uygulama arka planı
    surface: str         # kart / panel yüzeyi
    surface_alt: str     # ikincil yüzey (tablo başlığı, footer)
    surface_hover: str   # satır hover
    surface_sunken: str  # içerik gömme alanı (tablo gövdesi)

    # Çizgiler
    border: str          # ince ayırıcı
    border_strong: str   # belirgin kenar / odak halkası
    grid: str            # tablo satır ayırıcısı

    # Metin
    text: str            # birincil metin
    text_muted: str      # ikincil metin
    text_faint: str      # üçüncül metin / etiket
    text_inverse: str    # koyu zemin üstünde

    # Aksiyon
    accent: str          # birincil vurgu
    accent_hover: str
    accent_press: str
    accent_text: str     # accent üstündeki metin
    accent_soft: str     # accent'in soluk tonu (chip zemin)

    # Durumlar (semantik)
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    info: str
    info_soft: str
    neutral: str
    neutral_soft: str

    # Özel durum renkleri (encümen akışı)
    stage_girdi: str      # Encümene girdi
    stage_yazildi: str    # Encümene yazıldı
    stage_tescil: str     # Tescilde bekliyor
    stage_odeme: str      # Ödeme bekleniyor
    stage_gorus: str      # Görüş soruldu
    stage_edildi: str     # Tescil edildi
    stage_aska: str       # Askıda kaldı
    stage_iptal: str      # İptal

    # Vurgu yardımcıları
    shadow: str           # rgba(...)
    overlay: str          # rgba(...)


@dataclass(frozen=True)
class Metrics:
    """Ölçü tokenları — px."""

    radius_sm: int = 4
    radius: int = 7
    radius_lg: int = 10
    radius_pill: int = 999

    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    space_xl: int = 24

    row_height: int = 30
    header_height: int = 38
    control_height: int = 30
    topbar_height: int = 56
    kpi_height: int = 84


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    description: str
    palette: Palette
    metrics: Metrics = field(default_factory=Metrics)
    density: str = "comfortable"   # comfortable | compact
    dark: bool = False


# ---------------------------------------------------------------------------
# Tema tanımları
# ---------------------------------------------------------------------------

KADASTRO = Theme(
    key="kadastro",
    label="Kadastro",
    description="Açık, sıcak nötr zemin. Arşiv kağıdı ve ölçüm çizgisi estetiği.",
    dark=False,
    palette=Palette(
        canvas="#EDE7DB",
        surface="#FBF8F1",
        surface_alt="#F3EEE3",
        surface_hover="#F7F2E8",
        surface_sunken="#F8F4EB",
        border="#DDD5C4",
        border_strong="#C1B7A2",
        grid="#E8E1D2",
        text="#26211A",
        text_muted="#6E6556",
        text_faint="#968C7B",
        text_inverse="#FBF8F1",
        accent="#1F5F5B",
        accent_hover="#194F4C",
        accent_press="#123F3C",
        accent_text="#FBFAF7",
        accent_soft="#DCE9E6",
        success="#2F6B4F",
        success_soft="#DDEBE3",
        warning="#9A6410",
        warning_soft="#F4E7CE",
        danger="#A33A2A",
        danger_soft="#F5E0DB",
        info="#2A5C8A",
        info_soft="#DEE8F2",
        neutral="#6B6459",
        neutral_soft="#E7E2D8",
        stage_girdi="#2A5C8A",
        stage_yazildi="#9A6410",
        stage_tescil="#2F6B4F",
        stage_odeme="#7A5AA8",
        stage_gorus="#1F5F5B",
        stage_edildi="#3A7D5C",
        stage_aska="#8A8274",
        stage_iptal="#A33A2A",
        shadow="rgba(35, 32, 25, 0.10)",
        overlay="rgba(35, 32, 25, 0.32)",
    ),
)

GECE = Theme(
    key="gece",
    label="Gece",
    description="Derin lacivert zemin. Uzun vardiya ve düşük ışıkta çalışma için.",
    dark=True,
    palette=Palette(
        canvas="#14181F",
        surface="#1B2029",
        surface_alt="#222833",
        surface_hover="#252C38",
        surface_sunken="#171B23",
        border="#2C3441",
        border_strong="#3D4757",
        grid="#262D38",
        text="#E8EBF0",
        text_muted="#9AA5B4",
        text_faint="#6E7987",
        text_inverse="#14181F",
        accent="#4ECDC4",
        accent_hover="#6FDDD5",
        accent_press="#3AB3AB",
        accent_text="#0E2A29",
        accent_soft="#1E3B3C",
        success="#54C08A",
        success_soft="#1D3A2E",
        warning="#D9A441",
        warning_soft="#3D3220",
        danger="#E2685C",
        danger_soft="#432523",
        info="#5B9DD9",
        info_soft="#1E3348",
        neutral="#9AA5B4",
        neutral_soft="#2A313C",
        stage_girdi="#5B9DD9",
        stage_yazildi="#D9A441",
        stage_tescil="#54C08A",
        stage_odeme="#A88CD4",
        stage_gorus="#4ECDC4",
        stage_edildi="#54C08A",
        stage_aska="#7E8794",
        stage_iptal="#E2685C",
        shadow="rgba(0, 0, 0, 0.45)",
        overlay="rgba(8, 10, 14, 0.60)",
    ),
)

MUREKKEP = Theme(
    key="murekkep",
    label="Mürekkep",
    description="Yüksek kontrastlı mürekkep/kağıt. Baskı ve raporlama odaklı.",
    dark=False,
    palette=Palette(
        canvas="#E4E6E4",
        surface="#FFFFFF",
        surface_alt="#F1F2F1",
        surface_hover="#EBECEB",
        surface_sunken="#FAFAF9",
        border="#CBCCC9",
        border_strong="#A3A5A1",
        grid="#E2E3E0",
        text="#111110",
        text_muted="#565854",
        text_faint="#868883",
        text_inverse="#FFFFFF",
        accent="#1C3F94",
        accent_hover="#16357E",
        accent_press="#102868",
        accent_text="#FFFFFF",
        accent_soft="#E1E7F7",
        success="#1F6B45",
        success_soft="#DCEBE2",
        warning="#8C5A08",
        warning_soft="#F3E6CB",
        danger="#96281C",
        danger_soft="#F3DED9",
        info="#1C3F94",
        info_soft="#E1E7F7",
        neutral="#5A564E",
        neutral_soft="#E6E3DC",
        stage_girdi="#1C3F94",
        stage_yazildi="#8C5A08",
        stage_tescil="#1F6B45",
        stage_odeme="#5B3E8C",
        stage_gorus="#0F5F5B",
        stage_edildi="#1F6B45",
        stage_aska="#6E695F",
        stage_iptal="#96281C",
        shadow="rgba(20, 19, 15, 0.12)",
        overlay="rgba(20, 19, 15, 0.35)",
    ),
)

THEMES: Dict[str, Theme] = {t.key: t for t in (KADASTRO, GECE, MUREKKEP)}
DEFAULT_THEME = KADASTRO


def get_theme(key: str) -> Theme:
    return THEMES.get(key, DEFAULT_THEME)


# ---------------------------------------------------------------------------
# Renk yardımcıları
# ---------------------------------------------------------------------------

def mix(hex_a: str, hex_b: str, ratio: float) -> str:
    """İki hex rengi oranla karıştırır. ratio=0 → a, 1 → b."""
    a, b = QColor(hex_a), QColor(hex_b)
    r = round(a.red() + (b.red() - a.red()) * ratio)
    g = round(a.green() + (b.green() - a.green()) * ratio)
    bl = round(a.blue() + (b.blue() - a.blue()) * ratio)
    return f"#{r:02X}{g:02X}{bl:02X}"


def alpha(hex_color: str, a: float) -> str:
    """Hex rengi rgba() biçimine çevirir."""
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {a:.2f})"
