# -*- coding: utf-8 -*-
"""V1.1 için dış dosya gerektirmeyen, tema renkli vektörel ikonlar."""
from PySide6 import QtCore, QtGui

_CACHE = {}


def ikon(anahtar, renk="#64748B", boyut=18):
    imza = (anahtar, renk, boyut)
    if imza in _CACHE:
        return _CACHE[imza]
    pm = QtGui.QPixmap(boyut, boyut)
    pm.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    c = QtGui.QColor(renk)
    pen = QtGui.QPen(c, max(1.45, boyut / 11))
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    s = boyut / 18.0
    P = QtCore.QPointF
    R = QtCore.QRectF
    if anahtar == "search":
        p.drawEllipse(R(3*s, 3*s, 8*s, 8*s)); p.drawLine(P(10*s,10*s),P(15*s,15*s))
    elif anahtar == "plus":
        p.drawLine(P(9*s,3*s),P(9*s,15*s)); p.drawLine(P(3*s,9*s),P(15*s,9*s))
    elif anahtar == "pencil":
        path=QtGui.QPainterPath(); path.moveTo(4*s,13*s); path.lineTo(5*s,9*s); path.lineTo(12*s,2.5*s); path.lineTo(15.5*s,6*s); path.lineTo(8.5*s,13*s); path.closeSubpath(); p.drawPath(path); p.drawLine(P(4*s,13*s),P(8.5*s,13*s))
    elif anahtar == "trash":
        p.drawLine(P(3*s,5*s),P(15*s,5*s)); p.drawLine(P(7*s,3*s),P(11*s,3*s)); p.drawRoundedRect(R(5*s,5*s,8*s,10*s),1.2*s,1.2*s); p.drawLine(P(8*s,7*s),P(8*s,13*s)); p.drawLine(P(10*s,7*s),P(10*s,13*s))
    elif anahtar == "folder":
        path=QtGui.QPainterPath(); path.moveTo(2.5*s,5*s); path.lineTo(7*s,5*s); path.lineTo(8.5*s,7*s); path.lineTo(15.5*s,7*s); path.lineTo(14.5*s,15*s); path.lineTo(3*s,15*s); path.closeSubpath(); p.drawPath(path)
    elif anahtar == "receipt":
        path=QtGui.QPainterPath(); path.moveTo(4*s,2.5*s); path.lineTo(14*s,2.5*s); path.lineTo(14*s,15.5*s); path.lineTo(11.5*s,14*s); path.lineTo(9*s,15.5*s); path.lineTo(6.5*s,14*s); path.lineTo(4*s,15.5*s); path.closeSubpath(); p.drawPath(path); p.drawLine(P(6.5*s,6*s),P(11.5*s,6*s)); p.drawLine(P(6.5*s,9*s),P(11.5*s,9*s))
    elif anahtar == "database":
        p.drawEllipse(R(3*s,2.5*s,12*s,5*s)); p.drawLine(P(3*s,5*s),P(3*s,13*s)); p.drawLine(P(15*s,5*s),P(15*s,13*s)); p.drawArc(R(3*s,10.5*s,12*s,5*s),180*16,180*16)
    elif anahtar == "layers":
        p.drawPolyline(QtGui.QPolygonF([P(9*s,2*s),P(16*s,6*s),P(9*s,10*s),P(2*s,6*s),P(9*s,2*s)])); p.drawPolyline(QtGui.QPolygonF([P(2*s,9*s),P(9*s,13*s),P(16*s,9*s)])); p.drawPolyline(QtGui.QPolygonF([P(2*s,12*s),P(9*s,16*s),P(16*s,12*s)]))
    elif anahtar == "chart":
        p.drawLine(P(3*s,15*s),P(3*s,3*s)); p.drawLine(P(3*s,15*s),P(16*s,15*s)); p.drawRoundedRect(R(5*s,9*s,2.5*s,6*s),.5*s,.5*s); p.drawRoundedRect(R(9*s,6*s,2.5*s,9*s),.5*s,.5*s); p.drawRoundedRect(R(13*s,3*s,2.5*s,12*s),.5*s,.5*s)
    elif anahtar == "filter":
        path=QtGui.QPainterPath(); path.moveTo(2*s,3*s); path.lineTo(16*s,3*s); path.lineTo(10.5*s,9*s); path.lineTo(10.5*s,15*s); path.lineTo(7.5*s,13*s); path.lineTo(7.5*s,9*s); path.closeSubpath(); p.drawPath(path)
    elif anahtar == "building":
        p.drawRect(R(3*s,2*s,7*s,14*s)); p.drawRect(R(10*s,7*s,5*s,9*s))
        for x in (5,8):
            for y in (5,8,11): p.drawRect(R(x*s,y*s,1.2*s,1.2*s))
    elif anahtar == "sun":
        p.drawEllipse(R(6*s,6*s,6*s,6*s))
        import math
        for i in range(8):
            a=math.radians(i*45); p.drawLine(P(9*s+math.cos(a)*5*s,9*s+math.sin(a)*5*s),P(9*s+math.cos(a)*7*s,9*s+math.sin(a)*7*s))
    elif anahtar == "moon":
        path=QtGui.QPainterPath(); path.moveTo(12*s,3*s); path.cubicTo(7*s,3*s,4*s,7*s,5*s,12*s); path.cubicTo(8*s,16*s,14*s,13*s,15*s,9*s); path.cubicTo(12*s,11*s,9*s,8*s,12*s,3*s); p.drawPath(path)
    p.end()
    ico=QtGui.QIcon(pm)
    _CACHE[imza]=ico
    return ico
