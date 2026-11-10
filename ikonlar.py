"""
Vektörel ikon fabrikası.

Tüm ikonlar QPainter ile çizilir — dış dosya/bağımlılık yoktur,
her ölçekte net görünür ve tema rengini devralır.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)

from tema import Theme, alpha

_CACHE: dict = {}


def _pixmap(size: int, theme: Theme, key: str, color: str) -> QPixmap:
    ck = (size, theme.key, key, color)
    if ck in _CACHE:
        return _CACHE[ck]

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    c = QColor(color)
    s = size
    k = s / 16.0  # 16px referansına ölçek

    pen = QPen(c)
    pen.setWidthF(1.6 * k)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if key == "search":
        p.drawEllipse(QRectF(3.4 * k, 3.4 * k, 8.0 * k, 8.0 * k))
        p.drawLine(QPointF(10.4 * k, 10.4 * k), QPointF(13.2 * k, 13.2 * k))

    elif key == "plus":
        p.drawLine(QPointF(8 * k, 3.6 * k), QPointF(8 * k, 12.4 * k))
        p.drawLine(QPointF(3.6 * k, 8 * k), QPointF(12.4 * k, 8 * k))

    elif key == "pencil":
        path = QPainterPath()
        path.moveTo(3.6 * k, 12.4 * k)
        path.lineTo(4.4 * k, 9.6 * k)
        path.lineTo(10.6 * k, 3.4 * k)
        path.lineTo(12.6 * k, 5.4 * k)
        path.lineTo(6.4 * k, 11.6 * k)
        path.closeSubpath()
        p.drawPath(path)

    elif key == "trash":
        p.drawLine(QPointF(3.2 * k, 4.6 * k), QPointF(12.8 * k, 4.6 * k))
        p.drawLine(QPointF(6.2 * k, 4.6 * k), QPointF(6.2 * k, 3.2 * k)
                   if False else QPointF(6.2 * k, 3.2 * k))
        p.drawLine(QPointF(6.2 * k, 4.6 * k), QPointF(6.2 * k, 2.9 * k))
        p.drawLine(QPointF(9.8 * k, 4.6 * k), QPointF(9.8 * k, 2.9 * k))
        p.drawLine(QPointF(6.2 * k, 2.9 * k), QPointF(9.8 * k, 2.9 * k))
        p.drawRoundedRect(QRectF(4.2 * k, 4.6 * k, 7.6 * k, 8.6 * k), 1.2 * k, 1.2 * k)
        p.drawLine(QPointF(6.7 * k, 6.8 * k), QPointF(6.7 * k, 11.1 * k))
        p.drawLine(QPointF(9.3 * k, 6.8 * k), QPointF(9.3 * k, 11.1 * k))

    elif key == "folder":
        p.drawPolyline(QPolygonF([
            QPointF(2.8 * k, 12.6 * k), QPointF(2.8 * k, 3.8 * k),
            QPointF(6.4 * k, 3.8 * k), QPointF(7.8 * k, 5.9 * k),
            QPointF(13.2 * k, 5.9 * k), QPointF(13.2 * k, 12.6 * k),
        ]))
        p.drawLine(QPointF(2.8 * k, 12.6 * k), QPointF(13.2 * k, 12.6 * k))

    elif key == "receipt":
        path = QPainterPath()
        path.moveTo(4.2 * k, 2.8 * k)
        path.lineTo(11.8 * k, 2.8 * k)
        path.lineTo(11.8 * k, 13.2 * k)
        path.lineTo(10.0 * k, 11.9 * k)
        path.lineTo(8.0 * k, 13.2 * k)
        path.lineTo(6.0 * k, 11.9 * k)
        path.lineTo(4.2 * k, 13.2 * k)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(6.2 * k, 5.8 * k), QPointF(9.8 * k, 5.8 * k))
        p.drawLine(QPointF(6.2 * k, 8.2 * k), QPointF(9.8 * k, 8.2 * k))

    elif key == "download":
        p.drawLine(QPointF(8 * k, 2.8 * k), QPointF(8 * k, 10.2 * k))
        p.drawPolyline(QPolygonF([QPointF(4.8 * k, 7.2 * k), QPointF(8 * k, 10.4 * k),
                                  QPointF(11.2 * k, 7.2 * k)]))
        p.drawLine(QPointF(3.4 * k, 13.2 * k), QPointF(12.6 * k, 13.2 * k))

    elif key == "database":
        p.drawEllipse(QRectF(3.4 * k, 2.6 * k, 9.2 * k, 3.2 * k))
        p.drawLine(QPointF(3.4 * k, 4.2 * k), QPointF(3.4 * k, 11.8 * k))
        p.drawLine(QPointF(12.6 * k, 4.2 * k), QPointF(12.6 * k, 11.8 * k))
        p.drawArc(QRectF(3.4 * k, 9.4 * k, 9.2 * k, 3.2 * k), 0, 180 * 16)

    elif key == "chart":
        p.drawLine(QPointF(2.8 * k, 13.2 * k), QPointF(13.2 * k, 13.2 * k))
        p.drawLine(QPointF(2.8 * k, 13.2 * k), QPointF(2.8 * k, 2.8 * k))
        p.drawRoundedRect(QRectF(4.8 * k, 8.0 * k, 2.0 * k, 5.2 * k), 0.6 * k, 0.6 * k)
        p.drawRoundedRect(QRectF(8.0 * k, 5.4 * k, 2.0 * k, 7.8 * k), 0.6 * k, 0.6 * k)
        p.drawRoundedRect(QRectF(11.2 * k, 3.4 * k, 2.0 * k, 9.8 * k), 0.6 * k, 0.6 * k)

    elif key == "filter":
        path = QPainterPath()
        path.moveTo(2.8 * k, 3.6 * k)
        path.lineTo(13.2 * k, 3.6 * k)
        path.lineTo(9.4 * k, 8.4 * k)
        path.lineTo(9.4 * k, 12.6 * k)
        path.lineTo(6.6 * k, 11.2 * k)
        path.lineTo(6.6 * k, 8.4 * k)
        path.closeSubpath()
        p.drawPath(path)

    elif key == "calendar":
        p.drawRoundedRect(QRectF(2.9 * k, 3.8 * k, 10.2 * k, 9.6 * k), 1.4 * k, 1.4 * k)
        p.drawLine(QPointF(2.9 * k, 6.8 * k), QPointF(13.1 * k, 6.8 * k))
        p.drawLine(QPointF(5.6 * k, 2.4 * k), QPointF(5.6 * k, 5.2 * k))
        p.drawLine(QPointF(10.4 * k, 2.4 * k), QPointF(10.4 * k, 5.2 * k))

    elif key == "check":
        p.drawPolyline(QPolygonF([QPointF(3.4 * k, 8.4 * k), QPointF(6.6 * k, 11.6 * k),
                                  QPointF(12.6 * k, 4.8 * k)]))

    elif key == "x":
        p.drawLine(QPointF(4.2 * k, 4.2 * k), QPointF(11.8 * k, 11.8 * k))
        p.drawLine(QPointF(11.8 * k, 4.2 * k), QPointF(4.2 * k, 11.8 * k))

    elif key == "clock":
        p.drawEllipse(QRectF(3.0 * k, 3.0 * k, 10.0 * k, 10.0 * k))
        p.drawPolyline(QPolygonF([QPointF(8 * k, 5.4 * k), QPointF(8 * k, 8.2 * k),
                                  QPointF(10.4 * k, 9.6 * k)]))

    elif key == "refresh":
        p.drawArc(QRectF(3.4 * k, 3.4 * k, 9.2 * k, 9.2 * k), 40 * 16, 280 * 16)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(11.0 * k, 1.9 * k), QPointF(13.4 * k, 4.4 * k),
                                  QPointF(10.0 * k, 4.9 * k)]))

    elif key == "more":
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        for cx in (4.2, 8.0, 11.8):
            p.drawEllipse(QRectF(cx * k - 1.1 * k, 6.9 * k, 2.2 * k, 2.2 * k))

    elif key == "bell":
        p.drawArc(QRectF(4.2 * k, 3.2 * k, 7.6 * k, 8.4 * k), 180 * 16, 180 * 16)
        p.drawLine(QPointF(2.9 * k, 11.4 * k), QPointF(13.1 * k, 11.4 * k))
        p.drawLine(QPointF(4.2 * k, 11.4 * k), QPointF(4.2 * k, 8.4 * k))
        p.drawLine(QPointF(11.8 * k, 11.4 * k), QPointF(11.8 * k, 8.4 * k))
        p.drawArc(QRectF(6.8 * k, 10.4 * k, 2.4 * k, 2.4 * k), 0, 180 * 16)

    elif key == "layers":
        path = QPainterPath()
        path.moveTo(8 * k, 2.6 * k)
        path.lineTo(13.4 * k, 5.6 * k)
        path.lineTo(8 * k, 8.6 * k)
        path.lineTo(2.6 * k, 5.6 * k)
        path.closeSubpath()
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(2.6 * k, 8.6 * k), QPointF(8 * k, 11.6 * k),
                                  QPointF(13.4 * k, 8.6 * k)]))
        p.drawPolyline(QPolygonF([QPointF(2.6 * k, 11.2 * k), QPointF(8 * k, 14.0 * k),
                                  QPointF(13.4 * k, 11.2 * k)]))

    elif key == "building":
        p.drawRect(QRectF(3.4 * k, 3.0 * k, 5.2 * k, 10.4 * k))
        p.drawRect(QRectF(8.6 * k, 6.6 * k, 4.0 * k, 6.8 * k))
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        for yy in (5.2, 7.4, 9.6):
            p.drawRect(QRectF(4.6 * k, yy * k, 1.5 * k, 1.2 * k))
            p.drawRect(QRectF(7.0 * k, yy * k, 1.0 * k, 1.2 * k))

    elif key == "sun":
        p.drawEllipse(QRectF(5.2 * k, 5.2 * k, 5.6 * k, 5.6 * k))
        for i in range(8):
            from math import cos, radians, sin
            a = radians(i * 45)
            p.drawLine(QPointF(8 * k + cos(a) * 4.4 * k, 8 * k + sin(a) * 4.4 * k),
                       QPointF(8 * k + cos(a) * 6.0 * k, 8 * k + sin(a) * 6.0 * k))

    elif key == "moon":
        path = QPainterPath()
        path.moveTo(11.6 * k, 9.6 * k)
        path.cubicTo(7.2 * k, 10.6 * k, 4.6 * k, 7.6 * k, 5.6 * k, 3.4 * k)
        path.cubicTo(2.0 * k, 4.6 * k, 1.6 * k, 9.8 * k, 4.8 * k, 12.2 * k)
        path.cubicTo(6.6 * k, 13.6 * k, 9.8 * k, 13.4 * k, 11.6 * k, 9.6 * k)
        path.closeSubpath()
        p.drawPath(path)

    elif key == "chevron-down":
        p.drawPolyline(QPolygonF([QPointF(4.4 * k, 6.4 * k), QPointF(8 * k, 10.0 * k),
                                  QPointF(11.6 * k, 6.4 * k)]))

    elif key == "chevron-right":
        p.drawPolyline(QPolygonF([QPointF(6.4 * k, 4.4 * k), QPointF(10.0 * k, 8 * k),
                                  QPointF(6.4 * k, 11.6 * k)]))

    elif key == "user":
        p.drawEllipse(QRectF(5.6 * k, 3.0 * k, 4.8 * k, 4.8 * k))
        path = QPainterPath()
        path.moveTo(2.9 * k, 13.2 * k)
        path.cubicTo(3.4 * k, 9.6 * k, 12.6 * k, 9.6 * k, 13.1 * k, 13.2 * k)
        p.drawPath(path)

    p.end()
    _CACHE[ck] = pm
    return pm


def icon(theme: Theme, key: str, size: int = 16,
         color: str | None = None) -> QIcon:
    """Tema renginde ikon döndürür."""
    c = color or theme.palette.text_muted
    ico = QIcon()
    pm = _pixmap(size, theme, key, c)
    ico.addPixmap(pm)
    return ico


def pixmap(theme: Theme, key: str, size: int = 16,
           color: str | None = None) -> QPixmap:
    return _pixmap(size, theme, key, color or theme.palette.text_muted)
