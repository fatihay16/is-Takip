# -*- coding: utf-8 -*-
"""
Encümen İş Takip - PySide6 arayüzü, 2. AŞAMA pencereleri.

Bu dosya yalnızca PENCERELERİ içerir (Form, TopluGuncelle, Listeler, Silinenler, PasifListe, RaporAyar).
İş kuralları (kaydetme biçimleri, mükerrer kontrolü, toplu_uygula, kayit_geri, benzer_* vb.) eski
encumen_kayit.py içinden aynen çağrılır. Veritabanı yapısı değişmez.

Pencereler ana pencerenin (AnaPencere) şu yardımcılarını kullanır:
    app.liste_combo(tur), app.takvim_sec(parent, metin), app.dosya_sec_dialog(tur), app.undo_onceki / undo_ekle /
    undo_temizle, app.load / yenile_koru, app.bilgi / uyari / hata / sor, app.parsel_onay_kaldir
"""
import os
import sqlite3
import datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import encumen_kayit as ek


# ---------------------------------------------------------------- silme / geri getirme (eski numarayı koruyan sürüm)
def silinen_hazirla():
    """'silinen' tablosuna eski kayıt numarasını (eski_id) tutan sütunu ekler. Var olan satırlara ve eski programa dokunmaz:
    eski program sütun adlarını açıkça yazdığı için ek sütundan etkilenmez. Birden çok kez çağrılması zararsızdır."""
    if "eski_id" not in [r[1] for r in ek.q("PRAGMA table_info(silinen)")]:
        ek.q("ALTER TABLE silinen ADD COLUMN eski_id INTEGER")


def kayit_sil_idli(ids):
    """ek.kayit_sil ile aynı işi yapar (kaydı 'silinen' tablosuna kopyalayıp siler); ek olarak eski numarayı saklar.
    Hepsi tek işlemdir. Silme zamanını döndürür."""
    silinen_hazirla()
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c = ",".join(ek.KEYS)
    con = sqlite3.connect(ek.DB)
    try:
        with con:
            for i in ids:
                con.execute(f"INSERT INTO silinen (silinme,{c},durum_tarihi,eski_id) SELECT ?,{c},durum_tarihi,id FROM kayit WHERE id=?",
                            (zaman, i))
                con.execute("DELETE FROM kayit WHERE id=?", (i,))
    finally:
        con.close()
    return zaman


def kayit_geri_idli(sids):
    """'silinen' kayıtlarını geri getirir. Eski numarası biliniyorsa ve o numara boşsa kayıt AYNI numarayla döner
    (böylece TKGM parsel sonucu ve Fen Klasörü bağlantısı yerinde kalır). Numara bilinmiyorsa (eski satır) veya doluysa
    yeni numara alır; hiçbir kayıt ezilmez. Döndürür: [(eski_id, yeni_id, ayni_numara_mi), ...]"""
    silinen_hazirla()
    c = ",".join(ek.KEYS)
    sonuc = []
    con = sqlite3.connect(ek.DB)
    try:
        with con:
            for sid in sids:
                r = con.execute("SELECT eski_id FROM silinen WHERE sid=?", (sid,)).fetchone()
                if r is None:
                    continue
                eski = r[0]
                if eski is not None and con.execute("SELECT 1 FROM kayit WHERE id=?", (eski,)).fetchone() is None:
                    con.execute(f"INSERT INTO kayit (id,{c},durum_tarihi) SELECT ?,{c},durum_tarihi FROM silinen WHERE sid=?", (eski, sid))
                    sonuc.append((eski, eski, True))
                else:
                    cur = con.execute(f"INSERT INTO kayit ({c},durum_tarihi) SELECT {c},durum_tarihi FROM silinen WHERE sid=?", (sid,))
                    sonuc.append((eski, cur.lastrowid, False))
                con.execute("DELETE FROM silinen WHERE sid=?", (sid,))
    finally:
        con.close()
    return sonuc


def _dugme(metin, fonk, ad=""):
    b = QtWidgets.QPushButton(metin)
    if ad:
        b.setObjectName(ad)
    b.setAutoDefault(False)  # Enter tuşu yanlışlıkla kaydetmesin (eski programdaki gibi)
    b.setDefault(False)
    b.clicked.connect(lambda _=False, f=fonk: f())
    return b


def _kolon_tablo(app, basliklar, genislikler):
    t = QtWidgets.QTableWidget(0, len(basliklar))
    t.setHorizontalHeaderLabels(basliklar)
    t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    t.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setShowGrid(False)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(round(ek.TABLO_PUNTO * 2.8))
    t.setFont(app.tablo.font())  # ana tablodaki yazı boyutu
    t.horizontalHeader().setStretchLastSection(True)
    for i, w in enumerate(genislikler):
        t.setColumnWidth(i, w)
    return t


# ---------------------------------------------------------------- Yeni kayıt / Formda düzenle / Satırı çoğalt
class Form(QtWidgets.QDialog):
    KOPYA = ("mahalle", "ada_parsel", "muellif")  # "Satırı çoğalt" ile yalnızca bunlar taşınır

    def __init__(self, app, rid=None, kopya=None):
        super().__init__(app)
        self.app, self.rid = app, rid
        self.setWindowTitle("Yeni kayıt (çoğaltılan satırdan)" if kopya else ("Kayıt" if rid else "Yeni kayıt"))
        self.setModal(True)
        kaynak = rid or kopya
        satir = ek.q(f"SELECT {','.join(ek.KEYS)} FROM kayit WHERE id=?", (kaynak,)) if kaynak else []
        row = satir[0] if satir else None
        self.w = {}
        g = QtWidgets.QGridLayout(self)
        g.setContentsMargins(14, 12, 14, 12)
        g.setVerticalSpacing(7)
        for i, (k, l, t) in enumerate(ek.FIELDS):
            et = QtWidgets.QLabel(l)
            et.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            g.addWidget(et, i, 0)
            deger = (row[i] or "") if row and (not kopya or k in self.KOPYA) else ""
            if t and t.startswith("liste:"):
                w = app.liste_combo(t[6:])
                w.setEditText(deger)
                w.setMinimumWidth(430)
            else:
                w = QtWidgets.QLineEdit(deger)
                w.setMinimumWidth(430)
            self.w[k] = w
            g.addWidget(w, i, 1)
            if t == "dosya":
                g.addWidget(_dugme("Seç", lambda k=k: self.pick(k)), i, 2)
            if k in ek.DATES:
                g.addWidget(_dugme("Takvim", lambda k=k: self.takvim(k)), i, 2)
            if k == "ada_parsel":  # '728/1-2-9-10' gibi yazımlar ayrı parseller olarak okunur; ipucu yalnızca çoklu parselde görünür
                self.ipucu = QtWidgets.QLabel(ek.parsel_ozeti(deger))
                self.ipucu.setWordWrap(True)
                self.ipucu.setMaximumWidth(320)
                g.addWidget(self.ipucu, i, 2)
                w.textChanged.connect(lambda m: self.ipucu.setText(ek.parsel_ozeti(m)))
        n = len(ek.FIELDS)
        g.addWidget(_dugme("Kaydet", self.save, "vurgu"), n, 1, alignment=Qt.AlignmentFlag.AlignLeft)

    def al(self, k):
        w = self.w[k]
        return (w.currentText() if isinstance(w, QtWidgets.QComboBox) else w.text()).strip()

    def koy(self, k, metin):
        w = self.w[k]
        if isinstance(w, QtWidgets.QComboBox):
            w.setEditText(metin)
        else:
            w.setText(metin)

    def pick(self, k):
        p = self.app.dosya_sec_dialog("karar" if k.startswith("karar") else "makbuz")
        if p:
            self.koy(k, p)

    def takvim(self, k):
        s = self.app.takvim_sec(self, self.al(k))
        if s is not None:
            self.koy(k, s)

    def save(self):
        vals = [self.al(k) for k in ek.KEYS]
        ui = ek.KEYS.index("alinan_ucret")
        vals[ui] = ek.para_bicim(vals[ui])
        for dk in ek.DATES:
            vals[ek.KEYS.index(dk)] = ek.tarih_bicim(vals[ek.KEYS.index(dk)])
        ii = ek.KEYS.index("islem")
        vals[ii] = ek.islem_kanon(vals[ii])
        uy = ek.mukerrer(dict(zip(ek.KEYS, vals)), self.rid)
        if uy and not self.app.sor("Olası mükerrer kayıt", uy + "\n\nYine de kaydedilsin mi?"):
            return
        oi = ek.KEYS.index("onay")
        try:
            if self.rid:
                self.app.undo_onceki("Kayıt düzenleme", [self.rid])
                eski = (ek.q("SELECT onay FROM kayit WHERE id=?", (self.rid,)) or [[""]])[0][0] or ""
                if vals[oi] != eski:
                    ek.q("UPDATE kayit SET durum_tarihi=? WHERE id=?", (ek.bugun_str(), self.rid))
                ek.q(f"UPDATE kayit SET {','.join(k + '=?' for k in ek.KEYS)} WHERE id=?", vals + [self.rid])
                hedef = self.rid
            else:
                ek.q(f"INSERT INTO kayit ({','.join(ek.KEYS)},durum_tarihi) VALUES ({','.join('?' * (len(ek.KEYS) + 1))})",
                     vals + [ek.bugun_str() if vals[oi] else ""])
                hedef = ek.q("SELECT MAX(id) FROM kayit")[0][0]
                self.app.undo_ekle("Yeni kayıt", [hedef])
            for k, t in ek.LISTE_ALAN.items():  # listede olmayan yeni değeri listeye ekle (düzeltilmiş değerle)
                v = vals[ek.KEYS.index(k)]
                if v:
                    ek.q("INSERT OR IGNORE INTO liste VALUES (?,?)", (t, v))
        except sqlite3.Error as ex:
            self.app.hata("Kayıt", f"Kayıt veritabanına yazılamadı:\n{ex}")
            return
        self.app.yenile_koru(hedef)  # liste ve özet kartları yenilenir, düzenlenen/yeni satır seçilir
        self.accept()


# ---------------------------------------------------------------- Toplu güncelle
class TopluGuncelle(QtWidgets.QDialog):
    ALANLAR = ["onay", "encumen_tarihi", "karar_no", "karar_tarihi", "muellif", "makbuz_tarihi", "aciklama"]

    def __init__(self, app, ids):
        super().__init__(app)
        self.app, self.ids = app, ids
        self.setWindowTitle(f"Toplu Güncelle ({len(ids)} kayıt)")
        self.setModal(True)
        self.sec, self.w = {}, {}
        tur = {f[0]: f[2] for f in ek.FIELDS}
        g = QtWidgets.QGridLayout(self)
        g.setContentsMargins(14, 12, 14, 12)
        g.setVerticalSpacing(7)
        bilgi = QtWidgets.QLabel(f"{len(ids)} kayıtta yalnızca işaretlediğiniz alanlar değiştirilir.\n"
                                 "(Değer yazınca kutu kendiliğinden işaretlenir; boş değerle işaretlerseniz alan temizlenir.)")
        g.addWidget(bilgi, 0, 0, 1, 3)
        for i, k in enumerate(self.ALANLAR, 1):
            cb = QtWidgets.QCheckBox(ek.LAB[k])
            self.sec[k] = cb
            g.addWidget(cb, i, 0)
            if tur[k] and tur[k].startswith("liste:"):
                w = app.liste_combo(tur[k][6:])
                w.setEditText("")
                w.lineEdit().textEdited.connect(lambda _, c=cb: c.setChecked(True))
                w.activated.connect(lambda _, c=cb: c.setChecked(True))
            else:
                w = QtWidgets.QLineEdit()
                w.textEdited.connect(lambda _, c=cb: c.setChecked(True))
            w.setMinimumWidth(300)
            self.w[k] = w
            g.addWidget(w, i, 1)
            if k in ek.DATES:
                g.addWidget(_dugme("Takvim", lambda k=k: self.takvim(k)), i, 2)
        g.addWidget(_dugme("Uygula", self.uygula, "vurgu"), len(self.ALANLAR) + 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)

    def al(self, k):
        w = self.w[k]
        return (w.currentText() if isinstance(w, QtWidgets.QComboBox) else w.text()).strip()

    def takvim(self, k):
        s = self.app.takvim_sec(self, self.al(k))
        if s is not None:
            self.w[k].setText(s)
            self.sec[k].setChecked(True)

    def uygula(self):
        sec = [k for k in self.ALANLAR if self.sec[k].isChecked()]
        if not sec:
            self.app.bilgi("Uyarı", "Değiştirilecek en az bir alanı işaretleyin.")
            return
        ozet = "\n".join(f"• {ek.LAB[k]}: {self.al(k) or '(boş bırakılacak)'}" for k in sec)
        if not self.app.sor("Toplu güncelle", f"{len(self.ids)} kayıtta şu değişiklikler yapılacak:\n\n{ozet}\n\nDevam edilsin mi?"):
            return
        try:
            self.app.undo_onceki(f"Toplu güncelleme ({len(self.ids)} kayıt)", self.ids)
            ek.toplu_uygula(self.ids, {k: self.al(k) for k in sec})
        except sqlite3.Error as ex:
            self.app.hata("Toplu güncelle", f"Güncelleme yapılamadı:\n{ex}")
            return
        self.app.load()
        self.app.sec_idler(self.ids)
        self.accept()
        self.app.bilgi("Tamam", f"{len(self.ids)} kayıt güncellendi.")


# ---------------------------------------------------------------- Seçim listeleri
class Listeler(QtWidgets.QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Seçim Listeleri")
        self.setModal(True)
        self.resize(420, 560)
        v = QtWidgets.QVBoxLayout(self)
        self.cb = QtWidgets.QComboBox()
        self.cb.addItems(list(ek.LT.values()))
        self.cb.activated.connect(lambda _: self.yenile())
        v.addWidget(self.cb)
        self.lb = QtWidgets.QListWidget()
        self.lb.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        v.addWidget(self.lb, 1)
        h = QtWidgets.QHBoxLayout()
        self.e = QtWidgets.QLineEdit()
        self.e.returnPressed.connect(self.ekle)
        h.addWidget(self.e, 1)
        h.addWidget(_dugme("Ekle", self.ekle))
        v.addLayout(h)
        h2 = QtWidgets.QHBoxLayout()
        h2.addWidget(_dugme("Seçileni Düzenle", self.duzenle))
        h2.addWidget(_dugme("Seçileni Sil", self.sil))
        h2.addWidget(_dugme("Toplu Ekle", self.toplu))
        v.addLayout(h2)
        v.addWidget(_dugme("Benzer adları birleştir", self.birlestir))
        self.yenile()

    def kod(self):
        return list(ek.LT)[self.cb.currentIndex()]

    def yenile(self):
        self.lb.clear()
        for v in ek.liste(self.kod()):
            self.lb.addItem(v)

    def secili(self):
        return [i.text() for i in self.lb.selectedItems()]

    def kullanim(self, tur, v):
        return ek.q(f"SELECT COUNT(*) FROM kayit WHERE {tur}=?", (v,))[0][0]  # liste türü adı = kayıt sütun adı

    def ekle(self):
        m = self.e.text().strip()
        if m:
            ek.q("INSERT OR IGNORE INTO liste VALUES (?,?)", (self.kod(), m))
            self.e.clear()
            self.yenile()

    def duzenle(self):
        tur, sec = self.kod(), self.secili()
        if len(sec) != 1:
            self.app.bilgi("Uyarı", "Düzenlemek için listeden tek bir değer seçin.")
            return
        eski = sec[0]
        if tur == "onay" and eski in ek.DURUM_RENK:
            self.app.bilgi("Düzenlenemez", f"“{eski}” programın renk, arşiv ve gecikme kurallarında kullanılan hazır bir durumdur; "
                           "adı değiştirilemez.")
            return
        yeni, tamam = QtWidgets.QInputDialog.getText(self, "Değeri düzenle", f"“{eski}” için yeni ad:", text=eski)
        yeni = ek.ad_temizle(yeni) if tamam else ""
        if not yeni or yeni == eski:
            return
        if tur == "onay" and yeni in ek.DURUM_RENK:
            self.app.bilgi("Düzenlenemez", f"“{yeni}” hazır bir durum adıdır; başka bir ad seçin.")
            return
        n = self.kullanim(tur, eski)
        varsa = yeni in ek.liste(tur)
        msg = f"“{eski}” → “{yeni}” olarak değiştirilecek."
        if n:
            msg += f"\n\n{n} kayıttaki değer de güncellenecek."
        if varsa:
            msg += f"\n\n“{yeni}” zaten listede var; iki değer birleşecek."
        if not self.app.sor("Değeri düzenle", msg + "\n\nDevam edilsin mi?"):
            return
        con = sqlite3.connect(ek.DB)
        try:
            with con:  # hepsi tek işlem: yarıda kalırsa hiçbiri uygulanmaz
                con.execute(f"UPDATE kayit SET {tur}=? WHERE {tur}=?", (yeni, eski))
                con.execute("DELETE FROM liste WHERE tur=? AND deger=?", (tur, eski))
                con.execute("INSERT OR IGNORE INTO liste VALUES (?,?)", (tur, yeni))
        except sqlite3.Error as ex:
            self.app.hata("Hata", f"Değer değiştirilemedi:\n{ex}")
            return
        finally:
            con.close()
        self.yenile()
        self.app.undo_temizle()
        self.app.load()

    def sil(self):
        tur, sec = self.kod(), self.secili()
        if not sec:
            self.app.bilgi("Uyarı", "Önce silinecek değer(ler)i seçin.")
            return
        if not self.app.sor("Seçileni sil", f"{len(sec)} değer seçim listesinden silinecek. Devam edilsin mi?"):
            return
        kullanilan = [(v, self.kullanim(tur, v)) for v in sec]
        kullanilan = [(v, n) for v, n in kullanilan if n]
        silinecek = list(sec)
        if kullanilan:
            liste = "\n".join(f"• {v}  ({n} kayıtta)" for v, n in kullanilan[:12])
            if not self.app.sor("Kayıtlarda kullanılan değerler",
                                "Şu değerler kayıtlarda kullanılıyor:\n\n" + liste +
                                "\n\nKayıtlar değerini korur ama bu değerler seçim listesinden kalkar. "
                                "Bunlar da listeden silinsin mi?\n(Hayır: yalnızca kullanılmayanlar silinir.)"):
                silinecek = [v for v in sec if v not in dict(kullanilan)]
        for v in silinecek:
            ek.q("DELETE FROM liste WHERE tur=? AND deger=?", (tur, v))
        self.yenile()

    def toplu(self):
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Her satıra bir değer yapıştırın")
        v = QtWidgets.QVBoxLayout(d)
        t = QtWidgets.QPlainTextEdit()
        t.setMinimumSize(360, 320)
        v.addWidget(t)

        def tamam():
            for satir in t.toPlainText().splitlines():
                if satir.strip():
                    ek.q("INSERT OR IGNORE INTO liste VALUES (?,?)", (self.kod(), satir.strip()))
            d.accept()
            self.yenile()
        v.addWidget(_dugme("Ekle", tamam))
        d.exec()

    def birlestir(self):
        tur = self.kod()  # liste türü adı, kayıt tablosundaki sütun adıyla aynı
        g = ek.benzer_gruplar(tur, tur, tur == "islem")
        if not g:
            self.app.bilgi("Birleştir", "Birleştirilecek benzer ad bulunamadı.")
            return
        if self.app.sor("Benzer adları birleştir", "Şu adlar tek yazıma çevrilecek, kayıtlar da güncellenecek:\n\n"
                        + ek.benzer_ozet(g) + "\n\nDevam edilsin mi?"):
            ek.benzer_uygula(tur, tur, g)
            self.yenile()
            self.app.undo_temizle()
            self.app.load()
            self.app.bilgi("Tamam", f"{len(g)} grup birleştirildi.")


# ---------------------------------------------------------------- Son silinenler
class Silinenler(QtWidgets.QDialog):
    SUTUN = [("silinme", "Silinme"), ("mahalle", "Mahalle"), ("ada_parsel", "Ada/Parsel"), ("islem", "İşlem"),
             ("karar_no", "Karar No"), ("muellif", "Müellif"), ("onay", "Durum"), ("alinan_ucret", "Alınan Ücret")]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        silinen_hazirla()
        self.setWindowTitle("Son Silinenler (90 gün saklanır)")
        self.setModal(True)
        self.resize(960, 480)
        v = QtWidgets.QVBoxLayout(self)
        self.tv = _kolon_tablo(app, [ad for _, ad in self.SUTUN], [140] + [115] * 7)
        v.addWidget(self.tv, 1)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(_dugme("Geri Getir", self.geri, "vurgu"))
        h.addWidget(_dugme("Kalıcı Sil", self.kalici, "tehlike"))
        h.addWidget(QtWidgets.QLabel("Ctrl/Shift ile birden çok satır seçebilirsiniz."))
        h.addStretch(1)
        v.addLayout(h)
        self.yenile()

    def yenile(self):
        self.tv.setRowCount(0)
        for r in ek.q(f"SELECT sid,{','.join(k for k, _ in self.SUTUN)} FROM silinen ORDER BY sid DESC"):
            vals = [x or "" for x in r[1:]]
            try:
                vals[0] = datetime.datetime.strptime(vals[0], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            except ValueError:
                pass
            n = self.tv.rowCount()
            self.tv.insertRow(n)
            for c, x in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(str(x))
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r[0])
                self.tv.setItem(n, c, it)

    def secili(self):
        sat = sorted({i.row() for i in self.tv.selectionModel().selectedRows()})
        ids = [self.tv.item(s, 0).data(Qt.ItemDataRole.UserRole) for s in sat]
        if not ids:
            self.app.bilgi("Uyarı", "Önce bir veya daha fazla satır seçin.")
        return ids

    def geri(self):
        ids = self.secili()
        if ids:
            try:
                sonuc = kayit_geri_idli(ids)
            except sqlite3.Error as ex:
                self.app.hata("Geri getir", f"Kayıtlar geri getirilemedi:\n{ex}")
                return
            self.yenile()
            self.app.undo_temizle()  # eski programdaki gibi: geri getirme sonrası Ctrl+Z geçmişi sıfırlanır
            self.app.load()
            ayni = sum(1 for _, _, a in sonuc if a)
            msg = f"{len(sonuc)} kayıt geri getirildi."
            if ayni:
                msg += f"\n{ayni} kayıt eski numarasıyla döndü (TKGM parsel sonucu ve Fen Klasörü bağlantısı korundu)."
            if len(sonuc) - ayni:
                msg += (f"\n{len(sonuc) - ayni} kayıt yeni numara aldı (eski numarası bilinmiyordu: bu kayıtlar önceki sürümde silinmiş); "
                        "bu işlerin TKGM sonucu için Parsel Sorgu'yu yeniden çalıştırın.")
            self.app.bilgi("Tamam", msg)

    def kalici(self):
        ids = self.secili()
        if ids and self.app.sor("Kalıcı sil", f"{len(ids)} kayıt kalıcı olarak silinecek. Emin misiniz?"):
            for i in ids:
                ek.q("DELETE FROM silinen WHERE sid=?", (i,))
            self.yenile()


# ---------------------------------------------------------------- Pasif parseller
class PasifListe(QtWidgets.QDialog):
    """Pasife düşen parsellerin listesi: alan, nitelik, yeni parseller, işlem. Çift tık: parsel hareket özeti."""
    BASLIK = [("Onay", 90), ("Mahalle", 130), ("Sorgulanan parsel", 120), ("Alan (m²)", 90), ("Nitelik", 120),
              ("Yeni (aktif) parseller", 220), ("İşlem", 170), ("İş no", 60), ("İş durumu", 130), ("Son kontrol", 120)]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.kayitlar = {}
        self.setWindowTitle("Pasif Parseller")
        self.setModal(True)
        self.resize(1280, 560)
        v = QtWidgets.QVBoxLayout(self)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(QtWidgets.QLabel("Ara:"))
        self.ara = QtWidgets.QLineEdit()
        self.ara.setMinimumWidth(190)
        self.ara.textChanged.connect(lambda _: self.yukle())
        h.addWidget(self.ara)
        self.sadece = QtWidgets.QCheckBox("Yalnız onay bekleyenler")
        self.sadece.toggled.connect(lambda _: self.yukle())
        h.addWidget(self.sadece)
        h.addWidget(_dugme("Seçili parseli onayla", self.onayla))
        h.addWidget(_dugme("Yenile", self.yukle))
        h.addStretch(1)
        self.say = QtWidgets.QLabel("")
        h.addWidget(self.say)
        v.addLayout(h)
        ac = QtWidgets.QLabel("Parsel Sorgu'da pasif çıkan parseller. Satıra çift tıklayınca parselin hareket özeti açılır. "
                              "İş 'Tescillendi' yapılınca onay uyarısı kendiliğinden kalkar; kayıt burada ve Fen Klasörü'nde durur.")
        ac.setWordWrap(True)
        v.addWidget(ac)
        self.tv = _kolon_tablo(app, [a for a, _ in self.BASLIK], [w for _, w in self.BASLIK])
        self.tv.doubleClicked.connect(lambda _: self.detay())
        v.addWidget(self.tv, 1)
        self.yukle()

    def yukle(self):
        pk = ek.parsel_kontrol_oku()
        isler = {i: (mh, ap, on) for i, mh, ap, on in ek.q("SELECT id, mahalle, ada_parsel, onay FROM kayit")}
        aranan = ek.tr_lower(self.ara.text().strip())
        satirlar = []
        for wid, p in pk.items():
            if p["durum"] != "Pasif" or (self.sadece.isChecked() and not p["onay"]):
                continue
            mh, ap, jonay = isler.get(wid, ("", "", ""))
            yeni_metin = p["nihai"] or p["yeni"] or ""
            if aranan and aranan not in ek.tr_lower(" ".join([mh or "", ap or "", p["parsel_no"] or "", yeni_metin, p["nitelik"] or ""])):
                continue
            satirlar.append((ek.tarih_oku(p["islem_tarihi"]) or datetime.date.min, wid, p, mh, ap, jonay, yeni_metin))
        satirlar.sort(key=lambda x: (x[0], x[1]), reverse=True)
        self.tv.setRowCount(0)
        self.kayitlar = {}
        for _, wid, p, mh, ap, jonay, yeni_metin in satirlar:
            eski = ek.parselleri_coz(ap)
            for x in ek.parselleri_coz(p["parsel_no"]):
                if x not in eski:
                    eski.append(x)
            self.kayitlar[wid] = {"mahalle": mh or "", "tur": p["islem_turu"], "tarih": p["islem_tarihi"], "aciklama": p["aciklama"],
                                  "alan": p["alan"], "nitelik": p["nitelik"], "eski": eski, "yeni": ek.parselleri_coz(yeni_metin),
                                  "parsel_no": p["parsel_no"]}
            vals = ["⚠ Bekliyor" if p["onay"] else "Onaylandı", mh or "(iş silinmiş)", ek.no_etiket(p["parsel_no"]), p["alan"] or "–",
                    p["nitelik"] or "–", yeni_metin.replace("; ", ", ") or "–",
                    f"{p['islem_turu']} {p['islem_tarihi']}".strip() or "–", f"#{wid}", jonay or "–",
                    (p["son_kontrol"] or "").replace("T", " ")[:16]]
            n = self.tv.rowCount()
            self.tv.insertRow(n)
            for c, x in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(str(x))
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, wid)
                if p["onay"]:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(ek.KIRMIZI)))
                self.tv.setItem(n, c, it)
        bek = sum(1 for _, _, p, *_ in satirlar if p["onay"])
        self.say.setText(f"{len(satirlar)} pasif parsel · {bek} onay bekliyor")

    def secili(self):
        sat = sorted({i.row() for i in self.tv.selectionModel().selectedRows()})
        return [self.tv.item(s, 0).data(Qt.ItemDataRole.UserRole) for s in sat]

    def onayla(self):
        sec = self.secili()
        if not sec:
            self.app.bilgi("Uyarı", "Önce satır(lar)ı seçin.")
            return
        n = self.app.parsel_onay_kaldir(sec)  # eski mekanizma: onay_bekliyor=0, iş durumuna dokunmaz
        self.yukle()
        self.say.setText(f"{n} kayıt onaylandı")

    def detay(self):
        sec = self.secili()
        if not sec or sec[0] not in self.kayitlar:
            return
        k = self.kayitlar[sec[0]]

        def et(liste):
            return ", ".join(ek.parsel_etiket(a, p) for a, p in liste) or "–"
        metin = [f"Mahalle: {k['mahalle'] or '–'}", f"Sorgulanan parsel: {ek.no_etiket(k['parsel_no']) or '–'}",
                 f"Alan / nitelik: {k['alan'] or '–'} m² · {k['nitelik'] or '–'}",
                 f"İşlem: {(k['tur'] or '') + ' ' + (k['tarih'] or '')}".rstrip(),
                 f"Eski parseller: {et(k['eski'])}", f"Yeni (aktif) parseller: {et(k['yeni'])}",
                 f"TKGM açıklaması: {k['aciklama'] or '–'}", "",
                 "(Hareket zincirinin grafiği Grafikler/Fen Klasörü aşamasında PySide6'ya taşınacak; eski programda görülebilir.)"]
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Parsel hareket özeti")
        v = QtWidgets.QVBoxLayout(d)
        t = QtWidgets.QPlainTextEdit("\n".join(metin))
        t.setReadOnly(True)
        t.setMinimumSize(560, 300)
        v.addWidget(t)
        d.exec()


# ---------------------------------------------------------------- Rapor ayarları
class RaporAyar(QtWidgets.QDialog):
    """Raporların üstündeki kurum başlığı / logo ve altındaki imza alanı ayarları."""
    ALANLAR = [("kurum", "Kurum adı"), ("birim", "Birim adı"), ("hazirlayan", "Hazırlayan (ad soyad)"),
               ("hazirlayan_unvan", "Hazırlayan unvanı"), ("onaylayan", "Onaylayan (ad soyad)"),
               ("onaylayan_unvan", "Onaylayan unvanı")]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Rapor başlığı ve imza ayarları")
        self.setModal(True)
        g = QtWidgets.QGridLayout(self)
        g.setContentsMargins(14, 12, 14, 12)
        g.setVerticalSpacing(7)
        self.v = {}
        for i, (k, ad) in enumerate(self.ALANLAR):
            et = QtWidgets.QLabel(ad)
            et.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            g.addWidget(et, i, 0)
            self.v[k] = QtWidgets.QLineEdit(ek.ayar("rapor_" + k))
            self.v[k].setMinimumWidth(380)
            g.addWidget(self.v[k], i, 1, 1, 2)
        n = len(self.ALANLAR)
        et = QtWidgets.QLabel("Logo (isteğe bağlı)")
        et.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        g.addWidget(et, n, 0)
        self.v["logo"] = QtWidgets.QLineEdit(ek.ayar("rapor_logo"))
        g.addWidget(self.v["logo"], n, 1)
        g.addWidget(_dugme("Seç", self.logo_sec), n, 2)
        self.imza = QtWidgets.QCheckBox("Raporun altına imza alanı ekle (Hazırlayan / Onaylayan)")
        self.imza.setChecked(ek.ayar("rapor_imza") != "0")
        g.addWidget(self.imza, n + 1, 1, 1, 2)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(_dugme("Kaydet", self.kaydet, "vurgu"))
        h.addWidget(_dugme("Önizleme", self.onizle))
        h.addStretch(1)
        g.addLayout(h, n + 2, 1, 1, 2)

    def logo_sec(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Logo seçin (PNG veya JPG)", "", "Resim (*.png *.jpg *.jpeg)")
        if p:
            self.v["logo"].setText(os.path.normpath(p))

    def kaydet(self, kapat=True):
        for k, w in self.v.items():
            ek.q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("rapor_" + k, w.text().strip()))
        ek.q("INSERT OR REPLACE INTO ayar VALUES (?,?)", ("rapor_imza", "1" if self.imza.isChecked() else "0"))
        if kapat:
            self.accept()

    def onizle(self):
        self.kaydet(kapat=False)
        ek.rapor_ac(ek.rapor_sayfasi("Örnek Rapor", "Önizleme — ayarlarınız bu şekilde görünür",
                                     "<p>Rapor içeriği burada yer alır.</p>"))
