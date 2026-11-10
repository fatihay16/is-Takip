"""
Uygulama giriş noktası + offscreen render.

Kullanım:
    python uygulama.py                 → normal pencere (tema düğmesiyle geçiş)
    python uygulama.py --render        → üç temanın PNG çıktısını üretir
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from ekran import KayitlarEkrani
from qss import build_qss
from tema import GECE, KADASTRO, MUREKKEP, THEMES, Theme, font


class ImarUygulamasi(QMainWindow):
    def __init__(self, theme: Theme = KADASTRO):
        super().__init__()
        self.tema = theme
        self.setWindowTitle("İmar Uygulamaları")
        self.resize(1680, 1000)

        self.ekran = KayitlarEkrani(theme, self)
        self.ekran.tema_degisti.connect(self.tema_degistir)
        self.setCentralWidget(self.ekran)
        self._uygula(theme)

    def _uygula(self, theme: Theme):
        self.tema = theme
        app = QApplication.instance()
        app.setStyleSheet(build_qss(theme))
        app.setFont(font("body", 13))

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(theme.palette.canvas))
        pal.setColor(QPalette.ColorRole.Base, QColor(theme.palette.surface))
        pal.setColor(QPalette.ColorRole.Text, QColor(theme.palette.text))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(theme.palette.text))
        self.setPalette(pal)

        # ekranı yeniden kur
        yeni = KayitlarEkrani(theme, self)
        yeni.tema_degisti.connect(self.tema_degistir)
        self.setCentralWidget(yeni)
        self.ekran = yeni
        self.ekran.show()

    def tema_degistir(self, key: str):
        self._uygula(THEMES.get(key, self.tema))


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_ciktilari(cikti_dizini: str, genislik: int = 1680, yukseklik: int = 1000):
    os.makedirs(cikti_dizini, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)

    for anahtar, etiket in (("kadastro", "kadastro"), ("gece", "gece"), ("murekkep", "murekkep")):
        tema = THEMES[anahtar]
        app.setStyleSheet(build_qss(tema))
        app.setFont(font("body", 13))

        pencere = ImarUygulamasi(tema)
        pencere.resize(genislik, yukseklik)
        pencere.show()
        app.processEvents()

        yol = os.path.join(cikti_dizini, f"imar-{etiket}.png")
        pencere.grab().save(yol)
        print("yazıldı:", yol)

        pencere.close()
        app.processEvents()


if __name__ == "__main__":
    if "--render" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        render_ciktilari(os.path.join(os.path.dirname(__file__), "cikti"))
    else:
        app = QApplication(sys.argv)
        app.setStyleSheet(build_qss(KADASTRO))
        w = ImarUygulamasi(KADASTRO)
        w.show()
        sys.exit(app.exec())
