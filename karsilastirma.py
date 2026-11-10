"""
Önce / sonra karşılaştırma görseli üretir.
Sol: kullanıcının ekran görüntüsü (mevcut tasarım)
Sağ: yeni tasarımın render'ı
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QImage, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from qss import build_qss
from tema import THEMES, font


class Karsilastirma(QWidget):
    def __init__(self, eski_yol: str, yeni_yol: str, tema, parent=None):
        super().__init__(parent)
        self.eski = QPixmap(eski_yol)
        self.yeni = QPixmap(yeni_yol)
        self.tema = tema
        p = tema.palette
        self.setFixedSize(1760, 1010)
        self.setStyleSheet(f"#Karsilastirma {{ background: {p.canvas}; }}")
        self.setObjectName("Karsilastirma")

    def paintEvent(self, ev):
        p = self.tema.palette
        pr = QPainter(self)
        pr.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pr.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        W, H = self.width(), self.height()
        pad = 44
        gap = 34
        col_w = (W - pad * 2 - gap) // 2

        # başlık
        pr.setFont(font("display", 27, 600))
        pr.setPen(QPen(QColor(p.text)))
        pr.drawText(QRectF(pad, 40, W, 44), Qt.AlignmentFlag.AlignLeft |
                    Qt.AlignmentFlag.AlignVCenter,
                    "İmar Uygulamaları — mevcut tasarım ve modern yenileme")

        pr.setFont(font("body", 14))
        pr.setPen(QPen(QColor(p.text_muted)))
        pr.drawText(QRectF(pad, 84, W, 26), Qt.AlignmentFlag.AlignLeft |
                    Qt.AlignmentFlag.AlignVCenter,
                    "Aynı veri, aynı ekran akışı. Değişen şey: renk sistemi, tipografi, "
                    "hiyerarşi ve tablo okunabilirliği.")

        üst = 132

        # sol: eski
        self._etiket(pr, pad, üst, col_w, "MEVCUT", p.text_faint)
        self._gorsel(pr, self.eski, QRectF(pad, üst + 26, col_w, 760), p)

        # sağ: yeni
        x2 = pad + col_w + gap
        self._etiket(pr, x2, üst, col_w, "YENİ", p.accent)
        self._gorsel(pr, self.yeni, QRectF(x2, üst + 26, col_w, 760), p)

        # alt açıklama
        y = üst + 26 + 760 + 34
        pr.setFont(font("body", 13))
        pr.setPen(QPen(QColor(p.text_muted)))
        pr.drawText(QRectF(pad, y, col_w, 90),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
                    Qt.TextFlag.TextWordWrap,
                    "Kahverengi başlık, sıkışık filtre satırları, eşit ağırlıklı KPI "
                    "kartları ve 16 sütunlu tabloda kaybolan durum bilgisi.")
        pr.setPen(QPen(QColor(p.text)))
        pr.drawText(QRectF(x2, y, col_w, 90),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
                    Qt.TextFlag.TextWordWrap,
                    "Tek renk vurgusu, gruplanmış filtreler, sparkline'lı ölçüm kartları "
                    "ve durumu kodlayan sol aksan şeridi.")
        pr.end()

    def _etiket(self, pr: QPainter, x: int, y: int, w: int, metin: str, renk: str):
        f = font("body", 11, 700)
        pr.setFont(f)
        pr.setPen(QPen(QColor(renk)))
        pr.drawText(QRectF(x, y, w, 22), Qt.AlignmentFlag.AlignLeft |
                    Qt.AlignmentFlag.AlignVCenter, metin)

    def _gorsel(self, pr: QPainter, pm: QPixmap, hedef: QRectF, p):
        # çerçeve
        yol = QPainterPath()
        yol.addRoundedRect(hedef, 10, 10)
        pr.save()
        pr.setPen(Qt.NoPen)
        pr.setBrush(QColor(p.surface_sunken))
        pr.drawPath(yol)
        pr.restore()

        if pm.isNull():
            return

        # tam sığdırma (contain) — hiçbir şey kırpılmaz
        olcek = min(hedef.width() / pm.width(), hedef.height() / pm.height())
        w = pm.width() * olcek
        h = pm.height() * olcek
        x = hedef.x() + (hedef.width() - w) / 2
        y = hedef.y() + (hedef.height() - h) / 2
        alan = QRectF(x, y, w, h)

        pr.save()
        yol2 = QPainterPath()
        yol2.addRoundedRect(alan, 6, 6)
        pr.setClipPath(yol2)
        pr.drawPixmap(alan, pm, pm.rect())
        pr.restore()

        # çerçeve kenarı
        pr.save()
        pr.setPen(QPen(QColor(p.border_strong), 1))
        pr.setBrush(Qt.BrushStyle.NoBrush)
        yol3 = QPainterPath()
        yol3.addRoundedRect(hedef.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        pr.drawPath(yol3)
        pr.restore()


def uret(eski_yol: str, yeni_yol: str, cikti: str, tema_anahtar: str = "kadastro"):
    app = QApplication.instance() or QApplication(sys.argv)
    tema = THEMES[tema_anahtar]
    app.setStyleSheet(build_qss(tema))
    app.setFont(font("body", 13))

    w = Karsilastirma(eski_yol, yeni_yol, tema)
    w.show()
    app.processEvents()
    w.grab().save(cikti)
    print("yazıldı:", cikti)


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    kok = os.path.dirname(os.path.abspath(__file__))
    uret(
        "/workspace/attachments/42fe41ba53dee190/image.png",
        os.path.join(kok, "cikti", "imar-kadastro.png"),
        os.path.join(kok, "cikti", "karsilastirma.png"),
    )
