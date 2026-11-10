"""
Tasarım sistemi referans sayfası — palet, tipografi ve bileşen örnekleri.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPainterPath,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

import ikonlar
from bilesenler import KpiCard, StatusPill
from ekran import DURUMLAR, durum_rengi
from qss import build_qss
from tema import THEMES, Theme, font


class Sayfa(QWidget):
    """Tek sayfalık tasarım sistemi referansı."""

    def __init__(self, tema: Theme, parent=None):
        super().__init__(parent)
        self.tema = tema
        p = tema.palette
        self.setFixedSize(1180, 1120)
        self.setObjectName("SistemSayfasi")
        # Sayfa kendi stilini objectName seçicisiyle alır; aksi hâlde
        # alt widget'ların (buton, tablo) uygulama stilini ezer.
        self.setStyleSheet(f"#SistemSayfasi {{ background: {p.canvas}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(14)

        # başlık
        bas = QVBoxLayout()
        bas.setSpacing(2)
        b1 = QLabel("İmar Uygulamaları — Tasarım Sistemi")
        b1.setFont(font("display", 25, 600))
        b1.setStyleSheet(f"color: {p.text};")
        bas.addWidget(b1)
        b2 = QLabel(f"«{tema.label}» teması · {tema.description}")
        b2.setFont(font("body", 13))
        b2.setStyleSheet(f"color: {p.text_muted};")
        bas.addWidget(b2)
        root.addLayout(bas)

        root.addWidget(self._bolum("Yüzey ve metin"))
        root.addWidget(self._yuzey_kartlari())

        root.addWidget(self._bolum("Vurgu ve durum renkleri"))
        root.addWidget(self._vurgu_kartlari())

        root.addWidget(self._bolum("Tipografi"))
        root.addWidget(self._tipografi_kartlari())

        root.addWidget(self._bolum("Bileşenler"))
        root.addWidget(self._bilesen_kartlari())

    def _bolum(self, baslik: str) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(22)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0)
        lbl = QLabel(baslik.upper())
        lbl.setFont(font("body", 11, 700))
        lbl.setStyleSheet(f"color: {p.text_faint}; letter-spacing: 1.2px;")
        lay.addWidget(lbl)
        ay = QFrame_ayrac(self)
        lay.addWidget(ay, 1)
        return w

    def _yuzey_kartlari(self) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(96)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        for ad, renk in (("canvas", p.canvas), ("surface", p.surface),
                         ("surface_alt", p.surface_alt),
                         ("surface_sunken", p.surface_sunken),
                         ("border", p.border),
                         ("text", p.text),
                         ("text_muted", p.text_muted),
                         ("text_faint", p.text_faint)):
            lay.addWidget(self._renk_kutu(ad, renk), 1)
        return w

    def _vurgu_kartlari(self) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(96)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        for ad, renk in (("accent", p.accent), ("success", p.success),
                         ("warning", p.warning), ("danger", p.danger),
                         ("info", p.info), ("neutral", p.neutral),
                         ("accent_soft", p.accent_soft),
                         ("danger_soft", p.danger_soft),
                         ("success_soft", p.success_soft)):
            lay.addWidget(self._renk_kutu(ad, renk), 1)
        return w

    def _renk_kutu(self, ad: str, renk: str) -> QWidget:
        p = self.tema.palette
        k = QWidget(self)
        k.setFixedHeight(96)
        v = QVBoxLayout(k)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        sw = QWidget(k)
        sw.setFixedHeight(56)
        sw.setStyleSheet(
            f"background: {renk}; border-radius: 8px;"
            f"border: 1px solid {p.border};")
        v.addWidget(sw)

        l1 = QLabel(ad)
        l1.setFont(font("mono", 10, 500))
        l1.setStyleSheet(f"color: {p.text_muted};")
        v.addWidget(l1)

        l2 = QLabel(renk.upper())
        l2.setFont(font("mono", 9, 400))
        l2.setStyleSheet(f"color: {p.text_faint};")
        v.addWidget(l2)
        return k

    def _tipografi_kartlari(self) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(168)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        satirlar = [
            ("display", "İmar Uygulamaları", 34, 600, "Başlık ve KPI rakamı — Space Grotesk"),
            ("body", "Encümen karar ve makbuz kayıtları", 15, 400, "Arayüz metni — IBM Plex Sans"),
            ("mono", "38.213 ₺ · 27.10.2026 · 116408", 15, 500, "Para, tarih, karara no — IBM Plex Mono"),
        ]
        for rol, metin, boyut, agir, aciklama in satirlar:
            sat = QWidget(w)
            h = QHBoxLayout(sat)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(16)

            l = QLabel(metin)
            l.setFont(font(rol, boyut, agir))
            l.setStyleSheet(f"color: {p.text};")
            h.addWidget(l)

            h.addStretch(1)

            a = QLabel(aciklama)
            a.setFont(font("body", 11))
            a.setStyleSheet(f"color: {p.text_faint};")
            h.addWidget(a)
            v.addWidget(sat)

        # ölçek
        ol = QWidget(w)
        ho = QHBoxLayout(ol)
        ho.setContentsMargins(0, 0, 0, 0)
        ho.setSpacing(18)
        for et, boyut in (("11", 11), ("12", 12), ("13", 13), ("15", 15),
                          ("17", 17), ("25", 25)):
            t = QLabel(f"{et}px")
            t.setFont(font("body", boyut, 500))
            t.setStyleSheet(f"color: {p.text_muted};")
            ho.addWidget(t)
        v.addWidget(ol)
        v.addStretch(1)
        return w

    def _bilesen_kartlari(self) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(412)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # butonlar
        s1 = QWidget(w)
        h1 = QHBoxLayout(s1)
        h1.setContentsMargins(0, 0, 0, 0)
        h1.setSpacing(8)
        h1.addWidget(QLabel("Butonlar:"))
        for ad, ikon, kind in (("Yeni", "plus", "Primary"),
                               ("Formda Düzenle", "pencil", ""),
                               ("Toplu Güncelle", "refresh", ""),
                               ("Sil", "trash", "Danger")):
            b = QPushButton(ad)
            if kind:
                b.setObjectName(kind)
            b.setIcon(ikonlar.icon(self.tema, ikon, 15,
                                   p.accent_text if kind == "Primary" else p.text))
            b.setIconSize(QSize(15, 15))
            h1.addWidget(b)
        h1.addStretch(1)
        v.addWidget(s1)

        # rozetler
        s2 = QWidget(w)
        h2 = QHBoxLayout(s2)
        h2.setContentsMargins(0, 0, 0, 0)
        h2.setSpacing(8)
        h2.addWidget(QLabel("Durum rozetleri:"))
        for ad, _ in DURUMLAR:
            h2.addWidget(StatusPill(self.tema, ad, durum_rengi(self.tema, ad)))
        h2.addStretch(1)
        v.addWidget(s2)

        # KPI
        s3 = QWidget(w)
        h3 = QHBoxLayout(s3)
        h3.setContentsMargins(0, 0, 0, 0)
        h3.setSpacing(12)
        h3.addWidget(KpiCard(self.tema, "Açık işler", "84",
                             "toplam 780 arşiv kaydı", p.accent,
                             [58, 61, 59, 66, 70, 68, 74, 79, 76, 81, 80, 84]))
        h3.addWidget(KpiCard(self.tema, "Geciken işler", "41",
                             "eşik 90 gün aşıldı", p.danger,
                             [22, 25, 24, 29, 33, 31, 36, 34, 38, 40, 39, 41]))
        h3.addWidget(KpiCard(self.tema, "Bu ay tahsil edilen harç", "38.213 ₺",
                             "geçen aya göre +%12", p.success,
                             [24, 19, 28, 31, 26, 33, 29, 36, 34, 41, 38, 38]))
        v.addWidget(s3)

        # tablo satır örneği
        s4 = QWidget(w)
        h4 = QVBoxLayout(s4)
        h4.setContentsMargins(0, 0, 0, 0)
        h4.setSpacing(6)
        h4.addWidget(QLabel("Tablo satırı — sol aksan şeridi durumu kodlar:"))
        h4.addWidget(self._tablo_ornegi())
        v.addWidget(s4)
        v.addStretch(1)
        return w

    def _tablo_ornegi(self) -> QWidget:
        p = self.tema.palette
        w = QWidget(self)
        w.setFixedHeight(210)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        for ad, token in DURUMLAR:
            renk = getattr(p, token)
            satir = QWidget(w)
            satir.setFixedHeight(24)
            h = QHBoxLayout(satir)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(12)

            bar = QWidget(satir)
            bar.setFixedWidth(3)
            bar.setStyleSheet(f"background: {renk};")
            h.addWidget(bar)

            adet = QLabel("BEHRAM")
            adet.setFixedWidth(76)
            adet.setFont(font("body", 12, 600))
            adet.setStyleSheet(f"color: {p.text};")
            h.addWidget(adet)

            ada = QLabel("1098-1128")
            ada.setFixedWidth(76)
            ada.setFont(font("mono", 12, 500))
            ada.setStyleSheet(f"color: {p.text};")
            h.addWidget(ada)

            ucret = QLabel("15.200,00 ₺")
            ucret.setFixedWidth(94)
            ucret.setFont(font("mono", 12, 500))
            ucret.setStyleSheet(f"color: {p.text};")
            h.addWidget(ucret)

            rozet = StatusPill(self.tema, ad, renk)
            h.addWidget(rozet, 0, Qt.AlignVCenter)

            h.addStretch(1)
            v.addWidget(satir)

        return w


class QFrame_ayrac(QWidget):
    """İnce yatay ayraç."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background: %s;" % _border_color(parent))

    def paintEvent(self, ev):
        pass


def _border_color(w) -> str:
    try:
        return w.tema.palette.border
    except Exception:
        return "#DDD"


# ---------------------------------------------------------------------------

def uret(cikti_dizini: str):
    os.makedirs(cikti_dizini, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)

    for anahtar in ("kadastro", "gece", "murekkep"):
        tema = THEMES[anahtar]
        app.setStyleSheet(build_qss(tema))
        app.setFont(font("body", 13))

        sayfa = Sayfa(tema)
        sayfa.show()
        app.processEvents()
        yol = os.path.join(cikti_dizini, f"sistem-{anahtar}.png")
        sayfa.grab().save(yol)
        print("yazıldı:", yol)
        sayfa.close()
        app.processEvents()


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    uret(os.path.join(os.path.dirname(__file__), "cikti"))
