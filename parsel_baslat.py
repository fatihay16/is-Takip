# -*- coding: utf-8 -*-
"""
Geçici köprü: TKGM Parsel Sorgu penceresini (parsel_sorgu_modulu.py, hâlâ Tkinter) AYRI bir süreçte açar.

Neden gerekli?
  Encümen penceresi PySide6'ya geçti. Tkinter penceresi ile Qt penceresi aynı süreçte birlikte çalışamaz.
  Bu dosya, parsel_sorgu_modulu.App'i eskisiyle AYNI parametrelerle (kaynak, takip_db) çağırır;
  parsel_sorgu_modulu.py'ye hiç dokunulmaz.

Sonuçlar nasıl Encümen'e ulaşır?
  parsel_sorgu_modulu, sonuçları zaten imar_kayitlari.db içindeki 'parsel_kontrol' tablosuna yazıyor.
  Encümen penceresi bu tabloyu izleyip listeyi kendiliğinden yeniler (eski 'sonuc_geri_cagir' işlevinin karşılığı).

TKGM modülü PySide6'ya çevrildiğinde bu dosya silinir.
Doğrudan çalıştırılmaz; encumen_qt.py tarafından başlatılır.
"""
import os
import sys
import json


def calistir(args):
    """args: [kaynak_json_yolu, takip_db_yolu]"""
    kaynak_yolu, takip_db = args[0], args[1]
    with open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = [tuple(x) for x in json.load(f)]  # [(iş_id, mahalle, ada_parsel), ...]
    try:
        os.remove(kaynak_yolu)
    except OSError:
        pass

    klasor = os.path.dirname(os.path.abspath(takip_db))
    if klasor not in sys.path:
        sys.path.insert(0, klasor)

    import tkinter as tk
    import parsel_sorgu_modulu

    # Eski programda pencere, Encümen'in Tk kök penceresine bağlı açılıyordu. Aynı çağrı biçimini korumak için
    # görünmez (şeffaf, 1x1 piksel) bir kök pencere kullanılır.
    kok = tk.Tk()
    kok.overrideredirect(True)
    kok.geometry("1x1+0+0")
    try:
        kok.attributes("-alpha", 0.0)
    except tk.TclError:
        pass

    pencere = parsel_sorgu_modulu.App(
        kok, kaynak=kaynak, takip_db=takip_db,
        sonuc_geri_cagir=lambda work_id, ozet: None,  # sonuç zaten veritabanına yazılıyor; Encümen tabloyu izliyor
    )

    def kapaninca(olay):
        if olay.widget is pencere:
            kok.after(100, kok.quit)

    pencere.bind("<Destroy>", kapaninca)
    kok.mainloop()
    try:
        kok.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    calistir(sys.argv[1:])
