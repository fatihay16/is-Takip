# -*- coding: utf-8 -*-
"""
Geçici süreç köprüsü: PySide6 tabanlı TKGM Parsel Sorgu penceresini ayrı süreçte açar.

Encümen ve TKGM ayrı süreçlerde çalışır. Bu süreçte Tkinter kullanılmaz;
Qt kendi olay döngüsünü doğrudan çalıştırır. Böylece Tk/Qt ana döngülerinin
ve Python sonlandırma aşamasının çakışması önlenir.
"""
import os
import sys
import json


def calistir(args):
    """args: [kaynak_json_yolu, takip_db_yolu]"""
    if len(args) < 2:
        raise ValueError("Kaynak JSON yolu ve İş Takip veritabanı yolu gerekli.")

    kaynak_yolu, takip_db = args[0], args[1]
    with open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = [tuple(x) for x in json.load(f)]

    try:
        os.remove(kaynak_yolu)
    except OSError:
        pass

    klasor = os.path.dirname(os.path.abspath(takip_db))
    if klasor not in sys.path:
        sys.path.insert(0, klasor)

    from PySide6.QtWidgets import QApplication
    import parsel_sorgu_modulu

    # QApplication, TKGM penceresinden önce ve bu sürecin ana iş parçacığında oluşturulur.
    uygulama = QApplication.instance() or QApplication(sys.argv)
    uygulama.setQuitOnLastWindowClosed(True)

    pencere = parsel_sorgu_modulu.App(
        None,
        kaynak=kaynak,
        takip_db=takip_db,
        sonuc_geri_cagir=lambda work_id, ozet: None,
    )

    # App kendi içinde show() çağırıyor; Qt olay döngüsü pencere kapanana kadar sürer.
    return uygulama.exec()


if __name__ == "__main__":
    raise SystemExit(calistir(sys.argv[1:]))
