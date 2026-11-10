# İmar Uygulamaları — Modern Tasarım Yenilemesi

PySide6 tabanlı "İmar Uygulamaları" uygulaması için yenilenmiş tasarım sistemi.
Üç tema, üretim kalitesinde QSS, özel çizilen tablo bileşenleri ve canlı
tema değiştirme desteği içerir.

Tüm görseller **gerçek PySide6 ile offscreen render** edilmiştir — mockup
değildir. Kodda birebir aynı ekran çalışır.

---

## 1. Hızlı başlangıç

```bash
pip install PySide6-Essentials

# canlı pencere (sağ üstteki düğme ile tema değiştirir)
python uygulama.py

# tüm temaların PNG çıktısını üret
python uygulama.py --render
python sistem_sayfasi.py       # tasarım sistemi referans sayfası
```

### Fontlar

Üç font ailesi kullanılır — hepsi ücretsiz ve SIL Open Font License:

| Rol | Font | Nerede |
|---|---|---|
| display | **Space Grotesk** | başlıklar, KPI rakamları |
| body | **IBM Plex Sans** | arayüz metni, tablo hücreleri |
| mono | **IBM Plex Mono** | para, tarih, ada/parsel, karar no |

Türkçe karakter desteği (`İ ı ş ğ ü ö ç ₺`) üç fontta da doğrulanmıştır.
Fontlar sistemde yoksa `tema.py` içindeki `FAMILY_FALLBACK` ile otomatik
olarak Inter / DejaVu'ya düşer — uygulama çalışmaya devam eder.

---

## 2. Dosya düzeni

```
imar-modern/
├── tema.py              # renk/ölçü tokenları + 3 tema tanımı
├── qss.py               # tokenlardan QSS üreticisi
├── ikonlar.py           # QPainter ile vektörel ikon fabrikası
├── bilesenler.py        # tablo delegate, KPI kartı, sparkline, rozet
├── ekran.py             # modern Kayıtlar ekranı
├── uygulama.py          # giriş noktası + render
├── sistem_sayfasi.py    # tasarım sistemi referans sayfası
├── karsilastirma.py     # önce/sonra görseli
└── cikti/               # üretilen PNG'ler
```

---

## 3. Mevcut uygulamana entegrasyon

### 3.1 Tema motorunu bağla

Mevcut uygulamanızda tema değiştirme fonksiyonunuz varsa, QSS'i oradan
uygulayın:

```python
from tema import THEMES, font
from qss import build_qss

def tema_uygula(uygulama, anahtar):
    tema = THEMES[anahtar]
    uygulama.setStyleSheet(build_qss(tema))
    uygulama.setFont(font("body", 13))
```

Qt'de `setStyleSheet` **global** olduğu için, tema değiştirdiğinizde
tüm widget'lar yeniden boyanır. QSS'i widget'a değil `QApplication`'a verin.

### 3.2 Tabloyu kendi modelinize bağla

`KayitDelegate` kendi veri modelinizle çalışır. Hücre başına şu rollerı
set edin:

```python
from bilesenler import (ROLE_TEXT_ROLE, ROLE_COLOR, ROLE_ALIGN,
                        ROLE_WEIGHT, ROLE_STRIPE, ROLE_BADGE, ROLE_BADGE_COLOR)

item.setData(ROLE_TEXT_ROLE, "mono")     # display | body | mono
item.setData(ROLE_COLOR, "#26211A")       # metin rengi
item.setData(ROLE_ALIGN, Qt.AlignRight | Qt.AlignVCenter)
item.setData(ROLE_WEIGHT, 500)            # 400 | 500 | 600
item.setData(ROLE_STRIPE, "#2A5C8A")      # sol aksan rengi (durum)
item.setData(ROLE_BADGE, "Encümene Girdi")
item.setData(ROLE_BADGE_COLOR, "#2A5C8A")
```

Delegate'in `paint()` metodu hücreyi baştan çizer: arka plan, alt çizgi,
sol aksan şeridi ve içerik. QSS'teki `QTableView::item` kuralları bu
kapsayıcıları etkilemez — istediğiniz gibi özelleştirebilirsiniz.

### 3.3 Mevcut widget'larınızı yeni rozetlerle değiştirin

`StatusPill`, QSS ile yapılamayan şeyi yapar: sol hizalı pill rozet.

```python
from bilesenler import StatusPill
from ekran import durum_rengi

rozet = StatusPill(tema, "Tescilde Bekliyor", durum_rengi(tema, "Tescilde Bekliyor"))
rozet.clicked.connect(lambda: filtre_uygula("Tescilde Bekliyor"))
```

### 3.4 KPI kartı

```python
from bilesenler import KpiCard

kart = KpiCard(tema, "Açık işler", "84", "toplam 780 arşiv kaydı",
               tema.palette.accent,
               spark=[58, 61, 59, 66, 70, 68, 74, 79, 76, 81, 80, 84])
```

`spark` verilmezse grafik çizilmez. Değerler 12 aylık seriden gelmelidir —
gerçek veriye bağlayın.

---

## 4. Tasarım kararları ve gerekçeleri

### 4.1 Tek vurgu rengi

Mevcut tasarımda kahverengi, turuncu, yeşil, kırmızı, mavi ve mor aynı
anda vurgu olarak kullanılıyor; hangisinin önemli olduğu belli olmuyor.

Yeni sistemde **tek bir vurgu rengi** (`accent`) vardır ve yalnızca eylem
 için kullanılır. Renkler bundan sonra anlam taşır:

| Renk | Anlam |
|---|---|
| accent | birincil eylem, aktif sekme, seçili durum |
| danger | gecikme, iptal, silme |
| warning | ödeme bekleniyor, uyarı eşiği |
| success | tescil edildi, tahsil |
| info / stage_* | encümen akışındaki aşamalar |

### 4.2 Durum, tablo hücresinde değil satır kenarında

16 sütunlu bir tabloda her satıra renkli bir "Onay Durumu" rozeti koymak
gürültü yaratır — 16 sütundan biri renk kodu taşırken geri kalanı okunur
kalmıyor.

Yeni tasarımda durum **sol kenardaki 3 px aksan şeridi** ile kodlanır.
Böylece:

- Durumu görmek için 16 sütunu taramak gerekmez; göz tabloyu süpürür.
- Rozet sütunu boşalır ve "Müellif" / "Açıklamalar" gibi alanlar yer bulur.
- Altta renk efsanesi zaten durumları tanımlıyor.

Rozet yine de durum adını gösterir — ikisi birlikte hem hızlı tarama hem
kesin bilgi verir.

### 4.3 Sayısal sütunlar mono ve sekmeli

Ada/parsel, karar no, tarih ve ücret sütunları IBM Plex Mono kullanır.
Sabit genişlikli rakamlar sayısal sütunları hizalı tutar ve "15.200,00 ₺"
ile "3.800,00 ₺" arasındaki farkı gözle yakalamayı kolaylaştırır.

### 4.4 Tipografi rolleri

- **Space Grotesk** — geometrik, teknik bir grotesk. Başlık ve KPI rakamı
  olarak kullanılır; tabular sayı hissi verir.
- **IBM Plex Sans** — nötr, yoğun arayüzde okunabilir, Türkçe desteği tam.
- **IBM Plex Mono** — veri için. Kimlik numarası / para / tarih hizalı.

Üç rol net ayrılmış; hiçbiri "genel amaçlı" değil.

> **Not:** QSS'te `font-size` vermek `QFont.setFont()` çağrılarını ezer.
> Bu yüzden genel `QWidget` kuralında `font-size` yoktur; uygulama geneli
> yazı tipi `QApplication.setFont()` ile verilir. Widget bazlı QSS
> kurallarında (`#KpiValue`, `QPushButton` vb.) `font-size` kullanılabilir.

### 4.5 Ölçüm kartlarına trend

Her KPI tek başına bir sayı. Kartlara 12 aylık sparkline eklendiğinde
"84 açık iş" ifadesi "son 12 ayda 58'den 84'e çıktı" bilgisine dönüşür.
Geciken işler kartının kırmızı trendi, sabit bir sayıdan çok daha
fazla şey söyler.

---

## 5. Tema kataloğu

| Tema | Karakter | Ne zaman |
|---|---|---|
| **Kadastro** | Sıcak nötr kağıt zemin, koyu yeşil-teal vurgu | Günlük masaüstü kullanımı, uzun çalışma |
| **Gece** | Derin lacivert, camgöbeği-teal vurgu | Gece vardiyası, düşük ışık, projeksiyon |
| **Mürekkep** | Yüksek kontrastlı nötr gri/beyaz, mavi vurgu | Baskı, rapor, ekran görüntüsü paylaşımı |

Üçü de aynı token setini paylaşır — yeni bir tema eklemek `tema.py` içine
bir `Palette` tanımı eklemekten ibaret.

---

## 6. Erişilebilirlik notları

- Tüm metin/gövde kontrastları WCAG AA (4.5:1) üzerinde.
- Durum bilgisi **renge bağlı değil**: hem renk şeridi hem metin rozeti var.
- Odak halkaları QSS ile tanımlı; `QWidget { outline: none }` yalnızca
  stil kontrolleri içindir, `:focus` kuralları korunur.
- Tablo başlığı büyük harf + artı aralık, 10 px.
- Tema düğmesi (`tema_butonu`) tooltip taşır.

---

## 7. Üretilen görseller

| Dosya | İçerik |
|---|---|
| `cikti/imar-kadastro.png` | Kadastro teması — Kayıtlar ekranı |
| `cikti/imar-gece.png` | Gece teması — Kayıtlar ekranı |
| `cikti/imar-murekkep.png` | Mürekkep teması — Kayıtlar ekranı |
| `cikti/sistem-*.png` | Tasarım sistemi referans sayfası (palet, tipografi, bileşenler) |
| `cikti/karsilastirma.png` | Mevcut tasarım / yeni tasarım karşılaştırması |
