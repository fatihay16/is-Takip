"""
Özel çizilen tablo delegate'i ve yeniden kullanılabilir widget'lar.

Buradaki bileşenler Qt Style Sheet'in yapamadığını yapar:
  • Satır kenarlarındaki durum çubuğu (sol aksan)
  • Yuvarlatılmış durum rozetleri (pill)
  • Hizalı, sekmeli rakamlı sütunlar
  • Sparkline KPI grafiği
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QModelIndex, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPainterPath,
                           QPen)
from PySide6.QtWidgets import (QStyledItemDelegate, QWidget, QSizePolicy,
                               QStyleOptionViewItem)

from tema import Theme, alpha, mix


# ---------------------------------------------------------------------------
# Rol sabitleri
# ---------------------------------------------------------------------------

ROLE_ACCENT = Qt.UserRole + 1        # hücre aksan rengi (hex)
ROLE_TEXT_ROLE = Qt.UserRole + 2    # 'display' | 'body' | 'mono'
ROLE_ALIGN = Qt.UserRole + 3        # Qt.AlignmentFlag
ROLE_BADGE = Qt.UserRole + 4        # rozet metni (varsa pill çizilir)
ROLE_BADGE_COLOR = Qt.UserRole + 5  # rozet rengi
ROLE_STRIPE = Qt.UserRole + 6       # sol aksan çubuğu rengi
ROLE_TREND = Qt.UserRole + 7       # trend yönü: -1 düşüş, 0, +1 artış
ROLE_TREND_VALUE = Qt.UserRole + 8  # trend metni


def _qcolor(value: str, fallback: str = "#888888") -> QColor:
    c = QColor(value)
    return c if c.isValid() else QColor(fallback)


class KayitDelegate(QStyledItemDelegate):
    """Tablo hücrelerini özel çizer: sol aksan, rozet, mono hizalama."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        p = theme.palette
        self._stripe_w = 3

    # -- yardımcılar --------------------------------------------------------

    def _cell_rect(self, opt: QStyleOptionViewItem) -> QRect:
        return opt.rect

    def _draw_stripe(self, painter: QPainter, rect: QRect, color: Optional[str]):
        if not color:
            return
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(_qcolor(color))
        painter.drawRect(QRect(rect.left(), rect.top(), self._stripe_w, rect.height()))
        painter.restore()

    def _draw_badge(self, painter: QPainter, rect: QRect, text: str,
                    color_hex: str) -> None:
        """Sola hizalı pill rozet çizer."""
        p = self.theme.palette
        fg = _qcolor(color_hex, p.text)
        bg = QColor(fg)
        bg.setAlpha(28)

        f = QFont(self.theme_font("body"))
        f.setPixelSize(11)
        f.setWeight(QFont.Weight.DemiBold)
        fm = QFontMetrics(f)

        tw = fm.horizontalAdvance(text)
        pad_h = 9
        dot = 5
        gap = 6
        w = tw + pad_h * 2 + dot + gap
        h = 19

        x = rect.left() + 12
        y = rect.center().y() - h // 2
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), h / 2, h / 2)
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawPath(path)
        painter.restore()

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(fg)
        painter.drawEllipse(QRect(x + pad_h, rect.center().y() - dot // 2, dot, dot))
        painter.restore()

        painter.save()
        painter.setFont(f)
        painter.setPen(QPen(fg.darker(115)))
        painter.drawText(QRect(x + pad_h + dot + gap, y, tw + 2, h),
                         Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def theme_font(self, role: str) -> QFont:
        from tema import font
        return font(role, 12)

    # -- çizim --------------------------------------------------------------

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        p = self.theme.palette
        rect = self._cell_rect(opt)

        # arka plan
        from PySide6.QtWidgets import QStyle
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        hovered = bool(opt.state & QStyle.StateFlag.State_MouseOver)

        if selected:
            bg = QColor(p.accent_soft)
        elif hovered:
            bg = QColor(p.surface_hover)
        else:
            bg = QColor(p.surface)

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRect(rect)
        painter.restore()

        # alt çizgi
        painter.save()
        pen = QPen(_qcolor(p.grid))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(rect.left(), rect.bottom(),
                         rect.right(), rect.bottom())
        painter.restore()

        # sol aksan çubuğu (durum) — yalnızca ilk sütunda
        stripe = index.data(ROLE_STRIPE)
        if index.column() == 0:
            self._draw_stripe(painter, rect, stripe)

        # içerik
        text = index.data(Qt.DisplayRole)
        if text is None:
            text = ""

        badge = index.data(ROLE_BADGE)
        if badge:
            self._draw_badge(painter, rect, str(badge),
                             index.data(ROLE_BADGE_COLOR) or p.text_muted)
            return

        role = index.data(ROLE_TEXT_ROLE) or "body"
        f = self.theme_font(role)
        weight = index.data(ROLE_WEIGHT) if index.data(ROLE_WEIGHT) else 400
        f.setWeight(QFont.Weight(weight))

        color_hex = index.data(ROLE_COLOR) or p.text
        painter.save()
        painter.setFont(f)
        painter.setPen(QPen(_qcolor(color_hex, p.text)))

        align = index.data(ROLE_ALIGN)
        if align is None:
            align = Qt.AlignLeft | Qt.AlignVCenter

        pad_l = 8 + (self._stripe_w if (stripe and index.column() == 0) else 0)
        text_rect = QRect(rect.left() + pad_l, rect.top(),
                          max(0, rect.width() - pad_l - 8), rect.height())

        if role == "mono":
            painter.drawText(text_rect, align, str(text))
        else:
            painter.drawText(text_rect, align, str(text))
        painter.restore()

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width(), self.theme.metrics.row_height)


ROLE_WEIGHT = Qt.UserRole + 9
ROLE_COLOR = Qt.UserRole + 10


# ---------------------------------------------------------------------------
# Sparkline (KPI trend grafiği)
# ---------------------------------------------------------------------------

class Sparkline(QWidget):
    """KPI kartının sağ alt köşesindeki minik trend çizgisi."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.values: Sequence[float] = []
        self.color: str = theme.palette.accent
        self.setMinimumSize(64, 26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, values: Sequence[float], color: Optional[str] = None):
        self.values = list(values)
        if color:
            self.color = color
        self.update()

    def paintEvent(self, ev):
        if len(self.values) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        lo, hi = min(self.values), max(self.values)
        span = (hi - lo) or 1.0

        pad = 3
        step = (w - pad * 2) / (len(self.values) - 1)

        pts = []
        for i, v in enumerate(self.values):
            x = pad + i * step
            y = h - pad - ((v - lo) / span) * (h - pad * 2)
            pts.append(QPoint(int(x), int(y)))

        # dolgu
        fill = QPainterPath()
        fill.moveTo(pts[0].x(), h)
        for pt in pts:
            fill.lineTo(pt.x(), pt.y())
        fill.lineTo(pts[-1].x(), h)
        fill.closeSubpath()

        col = _qcolor(self.color, self.theme.palette.accent)
        grad = QColor(col)
        grad.setAlpha(46)
        painter.fillPath(fill, grad)

        # çizgi
        line = QPainterPath()
        line.moveTo(pts[0])
        for pt in pts[1:]:
            line.lineTo(pt)
        pen = QPen(col, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(line)

        # uç nokta
        painter.setBrush(col)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(pts[-1], 2.4, 2.4)
        painter.end()


# ---------------------------------------------------------------------------
# Durum rozeti (tablo dışı, açıklama satırları vb.)
# ---------------------------------------------------------------------------

class StatusPill(QWidget):
    """Küçük durum rozeti. Metin + renkli nokta."""

    clicked = Signal()

    def __init__(self, theme: Theme, text: str = "", color: Optional[str] = None,
                 parent=None):
        super().__init__(parent)
        self.theme = theme
        self.text = text
        self.color = color or theme.palette.text_muted
        f = QFont(theme_font_body(theme))
        f.setPixelSize(11)
        f.setWeight(QFont.Weight.DemiBold)
        self.setFont(f)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._genislik()

    def _genislik(self):
        fm = QFontMetrics(self.font())
        self.setFixedWidth(fm.horizontalAdvance(self.text) + 26)

    def set_status(self, text: str, color: str):
        self.text = text
        self.color = color
        self._genislik()
        self.update()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        return QSize(fm.horizontalAdvance(self.text) + 26, 22)

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.rect().adjusted(0, 0, -1, -1)

        fg = _qcolor(self.color, self.theme.palette.text_muted)
        bg = QColor(fg)
        bg.setAlpha(28)

        path = QPainterPath()
        path.addRoundedRect(QRectF(r), r.height() / 2, r.height() / 2)
        painter.fillPath(path, bg)

        painter.setPen(Qt.NoPen)
        painter.setBrush(fg)
        painter.drawEllipse(QRect(r.left() + 9, r.center().y() - 3, 6, 6))

        painter.setPen(QPen(fg.darker(112)))
        painter.setFont(self.font())
        painter.drawText(r.adjusted(22, 0, -9, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, self.text)
        painter.end()

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)


def theme_font_body(theme: Theme, size: int = 11, weight: int = 500) -> QFont:
    from tema import font
    return font("body", size, weight)


# ---------------------------------------------------------------------------
# KPI kartı
# ---------------------------------------------------------------------------

class KpiCard(QWidget):
    """Etiket + büyük değer + not + trend çizgisi içeren ölçüm kartı."""

    def __init__(self, theme: Theme, title: str, value: str,
                 note: str = "", accent: Optional[str] = None,
                 spark: Optional[Sequence[float]] = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.accent = accent or theme.palette.accent
        self.spark_values = list(spark or [])
        self.setFixedHeight(theme.metrics.kpi_height)
        self.setObjectName("KpiCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build(title, value, note)

    def _build(self, title: str, value: str, note: str):
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 11, 14, 11)
        outer.setSpacing(12)

        # sol aksan çubuğu
        bar = QWidget(self)
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background: {self.accent}; border-radius: 1px;")
        outer.addWidget(bar, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        lbl = QLabel(title, self)
        lbl.setObjectName("KpiLabel")
        col.addWidget(lbl)

        val = QLabel(value, self)
        val.setObjectName("KpiValue")
        val.setFont(_display_font(self.theme, 29, 600))
        col.addWidget(val)

        self.note_label = QLabel(note, self)
        self.note_label.setObjectName("KpiNote")
        col.addWidget(self.note_label)
        col.addStretch(1)

        outer.addLayout(col, 1)

        # sağ: trend grafiği
        self.spark = Sparkline(self.theme, self)
        self.spark.set_values(self.spark_values, self.accent)
        self.spark.setFixedWidth(86)
        self.spark.setFixedHeight(34)
        outer.addWidget(self.spark, 0, Qt.AlignVCenter)

    def update_spark(self, values: Sequence[float], color: Optional[str] = None):
        self.spark_values = list(values)
        self.spark.set_values(self.spark_values, color or self.accent)


def _display_font(theme: Theme, size: int, weight: int) -> QFont:
    from tema import font
    return font("display", size, weight)
