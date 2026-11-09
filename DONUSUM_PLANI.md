# PySide6 Dönüşüm Planı — Encümen Kayıt + TKGM Parsel Sorgulama

> İnceleme tarihi: 09.11.2026  
> Depo: `fatihay16/is-Takip` — incelenen kaynak dalı: `main`  
> Belge dalı: `docs/pyside6-donusum-plani`  
> Kapsam dışı: `modern_tasarim.py`. Kullanıcının açıklaması gereği eski ve uygulanmamış ayrı bir denemedir; açılmadı, analiz edilmedi ve kullanılmadı.  
> Bu belge planlama/dokümantasyon güncellemesidir. Uygulama kaynak kodları, veritabanı dosyaları ve kullanıcı verileri değiştirilmedi.

## 1. Gerçek durumun doğrulanması

İnceleme anındaki Git blob kimlikleri ve dosya boyutları:

| Dosya | Blob SHA | Satır | Gerçek durum |
|---|---|---:|---|
| `encumen_kayit.py` | `d5129119de41d398f699ed744e632fa99e152078` | 3.453 | Tkinter ana uygulaması; PySide6 arayüz dönüşümü henüz yapılmamış. |
| `parsel_sorgu_modulu.py` | `7c8bb3a7505ea434abe8f563ee0b079e5a4a0592` | 2.137 | **PySide6 arayüzü zaten mevcut.** Bu dosyayı hâlâ Tkinter arayüzüymüş gibi yeniden dönüştürmek doğru değil. |
| `requirements.txt` | `574ec387c780f22d8afe854d04d52e69fb1827e8` | 4 | `requests>=2.31.0`, `openpyxl>=3.1.2`, `PySide6>=6.6,<7`. |
| `ENTEGRASYON.txt` | `607a8be57cb8bbd3445bfdaf56234a7ba0883f44` | 27 | TKGM/İş Takip davranışını ve mevcut kullanıcı akışlarını açıklıyor; bazı kurulum bilgileri requirements ile güncel değil. |

**Önemli düzeltme:** İlk taslakta TKGM modülü Tkinter ve requirements yalnız requests/openpyxl olarak tanımlanmıştı. Güncel `main` dalı yeniden okununca bunun artık doğru olmadığı görüldü: TKGM modülü PySide6'ya taşınmış ve PySide6 bağımlılığı requirements dosyasına eklenmiş. Bu belge mevcut gerçek duruma göre güncellendi.

## 2. Modül envanteri

### 2.1 Encümen / İş Takip — `encumen_kayit.py`

- İçe aktarımlar Tkinter/`ttk`; ana pencere `App` içinde `tk.Tk()` ile kuruluyor.
- Başlangıç: `init_db()`, ardından `App().root.mainloop()`.
- Ana arayüz sekmeleri: Kayıtlar, Grafikler, Fen Klasörü.
- Yardımcı pencereler/sınıflar: `Takvim`, `Form`, `Listeler`, `Silinenler`, `TopluGuncelle`, `RaporAyar`, `FenIslemDialog`, `ZincirDetay`, `PasifListe`, `TarihAraligi`, `ListeFiltreleri`, `AramaliCombobox`, `App`.
- Temel veri/iş mantığı: Türkçe sıralama ve arama, tarih/para biçimleme, bekleme günü, arşiv durumu, kayıt ekleme/düzenleme/silme/geri alma, 90 günlük son silinenler, filtreler/kayıtlı görünümler, toplu güncelleme.
- Rapor/çıktı: HTML rapor üretimi, grafikler, CSV içe/dışa aktarma.
- Dosya işlemleri: karar/makbuz dosya yollarını kaydetme ve açma, klasör indeksleme, yedek alma ve yedekten geri yükleme.
- Parsel/Fen: TKGM sonuçlarını okuma, pasif parsel uyarıları, hareket zinciri, Fen Klasörü eski/yeni/ara parsel kayıtları, elle düzenlenen Fen kayıtlarının kilitlenmesi.
- Önemli fonksiyonlar: `init_db`, `q`, `parsel_kontrol_oku`, `parsel_gosterim`, `parsel_otomatik_onay`, `fen_kayit_ekle`, `fen_kayit_guncelle`, `fen_senkronla`, `kayit_sil`, `kayit_geri`, `yedekle`, `App.load`, `App.parsel_sorgu_ac`, `App.parsel_sonuc_geldi`, `App.fen_*`.

### 2.2 TKGM Parsel Sorgulama — `parsel_sorgu_modulu.py`

- Arayüz PySide6: `QMainWindow`, `QDialog`, `QWidget`, `QTableView`, `QAbstractTableModel`, `Signal`, `QThread`, `QTimer` kullanılıyor.
- Ana sınıflar: `App(QMainWindow)`, `ParselModel(QAbstractTableModel)`, `Detay`, `HareketAyar`, `MahalleEslestir`, `AramaliKutu`, `DurumEtiketi`, `GrafikAlani`, `_Is(QThread)`.
- Sorgu motoru ve iş mantığı: `query_one`, `analiz_et`, `tkgm_gittigi_kayitlar`, `devam_parsellerini_zincirle`, `hareket_adresi`, `get_json`, `mahalle_id_bul`, mahalle eşleştirme ve sonuç özeti fonksiyonları.
- Kullanıcı özellikleri: elle parsel ekleme, il/ilçe/mahalle seçimi, açık iş listesinden aktarım, kapanmış iş parsellerini göster/gizle, günlük istek sayacı/limit, otomatik tekrar kontrol, seçili/toplu sorgu, durum/alan/nitelik/yeni parseller ve hareket detayları.
- Dosya/veri işlemleri: Excel şablonu, Excel içe/dışa aktarma; ayarlar ve idari liste önbelleği.
- İş parçacığı: `QThread` ve sinyallerle arka plan işlemleri; UI güncellemeleri sinyal-slot üzerinden. `threading.Event` sorguyu durdurma kontrolünde kullanılıyor.
- Önemli fonksiyonlar: `db`, `get_json`, `query_one`, `takip_sonuc_yaz`, `aktarim_hazirla`, `App.illeri_yukle`, `App.is_listesinden_aktar`, `App.start_queries`, `App.worker`, `App.takibe_yaz`, `App.import_excel`, `App.export_excel`, `App.load_saved`.

**Sonuç:** TKGM tarafında yapılacak iş sıfırdan UI dönüşümü değil; mevcut PySide6 uygulamasının işlevsel eşdeğerliğini, entegrasyonunu ve Qt ana uygulamasına geçişini doğrulayıp eksikleri kapatmaktır.

## 3. SQLite envanteri

### 3.1 Encümen DB — `imar_kayitlari.db`

Yol: `encumen_kayit.py` içindeki `BASE / imar_kayitlari.db`.

Kaynakta oluşturulan tablolar:
- `kayit`: iş kayıtları; sütunlar `KEYS` listesinden oluşturuluyor, ayrıca `durum_tarihi` ekleniyor.
- `ayar`: `ad` / `deger` ayarları.
- `liste`: tür/değer listeleri.
- `silinen`: silinen kayıtların 90 günlük geri alma arşivi.
- `gorunum`: kayıtlı filtre/görünümler.
- `parsel_kontrol`: TKGM sonuçları.
- `fen_islem`: Fen Klasörü işlem başlıkları.
- `fen_parsel`: işlem/parsel/rol ilişkileri; `fen_parsel_ix` indeksi.

### 3.2 TKGM DB — `parsel_kayitlari.db`

Yol: `parsel_sorgu_modulu.py` içindeki `APP_DIR / parsel_kayitlari.db`; `Sonuclar` klasörü de tanımlı.

Tablolar:
- `parcels`: il, ilçe, mahalle, ada/parsel, mahalle ID, alan, nitelik, koordinat, durum, açıklama ve hareket bilgileri.
- `ayar`: ayarlar.
- `sayac`: gün bazında sorgu sayacı.
- `liste_onbellek`: TKGM idari liste önbelleği.
- `is_parsel_bag`: bir iş kaydı ile bir veya daha fazla parsel arasındaki bağ.
- `mahalle_esleme`: İş Takip mahalle adı ile TKGM resmi mahalle/ID eşlemesi.

İki DB farklı amaçla kullanılır; birleştirilmemeli ve dosya adları/konumları gelişigüzel değiştirilmemelidir. `DATA_DIR = APP_DIR / "Sonuclar"` ve `map_file` alanları mevcut kodda tanımlı; ancak sorgu worker'ında harita PNG'sinin üretilmediği açıkça belirtiliyor. Bu alan/klasörlerin hâlen kullanılan bir akış olup olmadığı ayrıca doğrulanmadan silinmemeli.

## 4. Kritik TKGM ↔ Encümen entegrasyon sözleşmesi

### 4.1 Tablo ve yazma davranışı

İki kaynakta da `parsel_kontrol` DDL'si eşleşiyor:

`work_id INTEGER PRIMARY KEY, parsel_no TEXT, tkgm_mahalle TEXT, durum TEXT, alan TEXT, nitelik TEXT, islem_turu TEXT, islem_tarihi TEXT, yeni_parseller TEXT, nihai_aktifler TEXT, aciklama TEXT, son_kontrol TEXT, onay_bekliyor INTEGER DEFAULT 0, zincir TEXT`.

TKGM modülündeki `takip_sonuc_yaz(takip_db_yolu, work_id, row)`:
- Encümen DB yoluna ayrı SQLite bağlantısı açıyor.
- Gerekirse eski DB'ye `zincir` sütununu ekliyor.
- `work_id` üzerinden UPSERT yapıyor.
- `kayit` tablosundaki asıl iş kaydını değiştirmediğini docstring'de açıkça belirtiyor.
- Pasife yeni düşen sonuçta `onay_bekliyor=1`; zaten pasif olan kayıtta önceki onay değeri korunuyor; Pasif dışındaki sonuçlarda onay sıfırlanıyor.

### 4.2 Pencere açılışı ve callback

Encümen `App.parsel_sorgu_ac`:
1. Açık işlerden `(id, mahalle, ada_parsel)` listesini hazırlar.
2. `parsel_sorgu_modulu.App(s.root, kaynak=kaynak, takip_db=DB, sonuc_geri_cagir=s.parsel_sonuc_geldi)` çağrısını yapar.
3. TKGM `takip_db` üzerinden `parsel_kontrol` tablosuna yazar; callback Encümen tablosunun gecikmeli yenilenmesini sağlar.

TKGM modülünün `App` kurucusu `master`, `kaynak`, `takip_db`, `sonuc_geri_cagir` parametrelerini kabul ediyor. `sonuc_geri_cagir(work_id, ozet)` sözleşmesi korunmalı.

### 4.3 Fen Klasörü ve onay

- Encümen `parsel_kontrol_oku` ile sonuçları okuyor.
- `parsel_otomatik_onay`, iş durumu Tescillendi olduğunda bekleyen pasif-parsel uyarısını kaldırıyor.
- `fen_senkronla`, pasif sonuçlardan Fen Klasörü kayıtları üretiyor/güncelliyor; eski/yeni/ara parselleri, alan/nitelik ve zinciri kullanıyor.
- Elle düzenlenmiş/kilitlenmiş Fen kayıtları otomatik senkronizasyonda ezilmemeli; “TKGM sonucuna dön” akışı korunmalı.

### 4.4 Geçiş köprüsü ve doğrulanması gereken uyumsuzluk

TKGM dosyasında `_tk_koprusu(master)` fonksiyonu, TKGM Qt penceresi eski Tk tabanlı Encümen'den açıldığında `master.after(15, ... qapp.processEvents())` ile Qt olaylarını Tk döngüsünden işletiyor. Bu, **geçiş dönemi köprüsü** olarak yorumlanmalı; kalıcı mimari olmamalı.

Encümen'in mevcut `parsel_sorgu_ac` fonksiyonunda açık pencere kontrolü `p.winfo_exists()` ile yapılıyor. TKGM penceresi artık Qt `QMainWindow` olduğundan bu metot Qt penceresinde bulunmaz; tekrar açma akışı `AttributeError` üretebilir ve mevcut `except tk.TclError` bunu yakalamaz. Bu, gerçek kaynak kodundan görülen somut entegrasyon riskidir. Encümen Qt dönüşümünde pencere referansı/yaşam döngüsü `QWidget` API'siyle yönetilmeli; TKGM hesabı Encümen dosyasını değiştirmemelidir.

## 5. PySide6 hedef mimarisi

### 5.1 Encümen tarafı (gerçek dönüşüm işi)

- İş kuralları, SQLite işlemleri, tarih/para/parsel hesapları ve rapor üretimi UI'dan ayrıştırılmalı; mümkün olduğunca mevcut fonksiyonlar korunup servis/repository katmanına taşınmalı.
- Kayıt tablosu için `QTableView + QAbstractTableModel`; sıralama/filtre için `QSortFilterProxyModel`.
- Form, takvim, listeler, toplu güncelleme, son silinenler, rapor ayarı, pasif parsel ve Fen Klasörü pencereleri Qt karşılıklarına taşınmalı.
- Grafikler, detay paneli, tema, yazı boyutu, sütun görünürlüğü, kayıtlı görünümler, kısayollar ve çoklu seçim korunmalı.
- HTML/CSV, dosya seçme/açma, ağ klasörü indeksleme ve yedek/geri yükleme davranışları korunmalı.

### 5.2 TKGM tarafı (mevcut PySide6 kodunu sağlamlaştırma)

- Var olan `QMainWindow`, `ParselModel`, `QThread` ve sinyal-slot yapısını temel al; sıfırdan yeniden yazma.
- Özellik/iş kuralı eşleştirme tablosu çıkar; mevcut Tk sürümünden taşınmış olduğu iddia edilen davranışların güncel kodda gerçekten bulunduğunu doğrula.
- Encümen Qt olduğunda TKGM penceresinin nasıl açılacağı için açık bir Qt entegrasyon API'si tanımla (Qt parent, pencere referansı, yaşam döngüsü, callback/sinyal). Eski Tk köprüsünü geçiş dönemi için koru; Encümen hesabının işi tamamlanmadan kaldırma.
- Sorgu motoru, TKGM API uçları, hareket zinciri, mahalle eşleştirme, limit/bekleme, Excel ve DB davranışlarını değiştirme.

### 5.3 Ortak arayüz ilkeleri

- Qt widget'larına yalnız GUI ana thread'inden erişilsin.
- Uzun ağ/dosya işleri worker-object + `QThread` veya `QThreadPool/QRunnable` ile çalışsın.
- Worker'lar ilerleme, durum, sonuç, hata ve tamamlandı sinyalleri yayınlasın; GUI yalnız sinyallerle güncellensin.
- Worker içinden widget değiştirme, Tk `after` çağrısını Qt worker'a taşıma veya `processEvents()` ile UI zorlamak yasak.
- İptal/durdurma, pencere kapanışı, timeout, limit ve bekleme kuralları güvenli olmalı.
- Ortak tema ve etkileşim ilkeleri tutarlı olsun; fakat iki modülün bağımsız test edilebilirliği korunsun.

### 5.4 Veritabanı erişim sözleşmesi

- Varsayılan DB yolları ve dosya adları korunmalı: `imar_kayitlari.db`, `parsel_kayitlari.db`.
- Mevcut şemalar, PK'ler, kolon adları ve migration davranışları korunmalı.
- Gerçek DB üzerinde ilk test/migration yapılmamalı; kopya DB ve sentetik veri kullanılmalı.
- Her yazma işlemi açık transaction/commit/rollback sınırına sahip olmalı; bağlantı timeout ve eşzamanlı yazma test edilmeli.
- `parsel_kontrol` DDL/UPSERT tek bir sözleşme olarak ele alınmalı; iki tarafta farklı kolon veya farklı `onay_bekliyor` mantığı oluşturulmamalı.
- `work_id`, Encümen `kayit.id` anlamını korumalı.
- WAL gibi SQLite ayarları ölçüm ve geri dönüş planı olmadan açılmamalı.

## 6. Bağımlılıklar ve paketleme

Güncel `requirements.txt` zaten `PySide6>=6.6,<7` içeriyor; ayrıca `requests` ve `openpyxl` korunmalı. Dolayısıyla PySide6'yı yeniden eklemek gerekmiyor. Python sürümü, EXE aracı ve paketleme betikleri bu incelemede tam doğrulanmadı; EXE aşamasından önce ayrıca incelenmeli.

`ENTEGRASYON.txt` kurulum notunda requirements içeriğini “requests, openpyxl” diye özetliyor; bu bilgi artık eksik, çünkü güncel requirements PySide6 da içeriyor. Belge güncellemesi ayrı ve kontrollü bir dokümantasyon işi olarak ele alınabilir. `exe_yap.bat`, `kisayol_olustur.bat`, `encumen.ico` dosyalarının içerikleri bu görevde açılmadı; `ENTEGRASYON.txt` bunların değişmediğini söylüyor, ancak paketleme davranışları doğrulanmış sayılmaz.

## 7. İki hesaba görev dağılımı ve branch sınırları

İki hesap aynı dosyayı eşzamanlı düzenlememeli. Her hesap kendi branch'inde çalışmalı; doğrudan `main` dalına commit/merge yapılmamalı.

### Hesap 1 — Encümen'in Tkinter → PySide6 dönüşümü

- Branch: `feature/pyside6-encumen`
- Kapsam: yalnız `encumen_kayit.py` ve Encümen'e ait yeni Qt UI/core/test dosyaları.
- `parsel_sorgu_modulu.py` dosyasına dokunma.
- TKGM sorgu motorunu yeniden yazma.
- `parsel_kontrol` DDL/kolonları/UPSERT ve `sonuc_geri_cagir(work_id, ozet)` sözleşmesini değiştirme.
- TKGM Qt penceresini QWidget/QMainWindow yaşam döngüsüyle aç; mevcut `winfo_exists()` kontrolünü Qt uyumlu hale getir.
- Fen Klasörü kilit/geri dön davranışını, pasif onay geçişlerini ve tüm Encümen özelliklerini koru.

### Hesap 2 — Mevcut TKGM PySide6 dönüşümünü doğrulama ve tamamlama

- Branch: `feature/pyside6-parsel-review`
- Kapsam: yalnız `parsel_sorgu_modulu.py` ve TKGM'ye ait yeni test/dokümantasyon dosyaları.
- **Bu modül zaten PySide6 olduğundan sıfırdan dönüşüm yapma.** Mevcut UI'nın tüm özelliklerini ve önceki iş akışlarını doğrula; gerçek eksikleri yalnız bu modülde düzelt.
- Encümen Qt ana penceresinin kullanacağı parent/sinyal/callback/pencere yaşam döngüsü sözleşmesini dokümante et.
- Mevcut Tk ana uygulamasıyla geçiş uyumluluğunu koru; `_tk_koprusu` kaldırılacaksa ancak entegrasyon branch'inde ve Encümen Qt ana penceresi hazır olduğunda karar verilsin.
- `encumen_kayit.py` dosyasına dokunma; `parsel_kontrol` sözleşmesini değiştirme.

### Her iki hesap için ortak yasaklar

- `modern_tasarim.py` dosyasını açma, analiz etme, import etme veya kullanma.
- Diğer hesabın sahip olduğu dosyalara müdahale etme.
- `main` dalına doğrudan commit/push/merge yapma.
- Gerçek kullanıcı DB'sini açma, değiştirme veya migration çalıştırma.
- Özellik kaldırma, iş kuralı değiştirme veya şema değişikliği yapma.
- Her aşamada değişen dosyaları, test sonuçlarını ve bilinen eksikleri raporla.

## 8. Aşamalar ve birleştirme

1. **Sözleşmeyi dondur:** DB yolları/şemaları, `parsel_kontrol` alanları, onay mantığı, callback ve Qt pencere API'si.
2. **Encümen dönüşümü:** Hesap 1 iş mantığını koruyarak UI'yı Qt'ye taşısın.
3. **TKGM doğrulaması:** Hesap 2 mevcut PySide6 UI'nın özellik eşitliğini, worker/iptal/kapanış davranışını ve entegrasyon API'sini test etsin.
4. **Tekil testler:** Her branch geçici DB ve mock TKGM yanıtlarıyla kendi testlerini çalıştırsın.
5. **Entegrasyon dalı:** İki branch `integration/pyside6` dalına alınsın; ana dal doğrudan hedef olmasın.
6. **Qt-Qt bağlantısı:** TKGM penceresi Qt parent ile açılıp kapansın; callback veya Qt sinyaliyle Encümen yenilensin; eski Tk köprüsü yalnız artık kullanılmadığı kanıtlanınca kaldırılmalı.
7. **Regresyon ve paketleme:** Aşağıdaki testler geçmeden canlı DB/EXE dağıtımı yapılmasın.
8. **Canlı geçiş:** Önce yedek; ilk açılış kopya DB'de doğrulanmış migration ile; eski sürüm ve DB yedeği geri dönüş için saklanmalı.

## 9. Zorunlu test listesi

- Eski DB kopyasında kayıt sayısı, ID, kolon ve listeler değişmiyor.
- Şema yükseltmesi yalnız gerekli kolonları ekliyor; veri kaybı yok.
- Encümen kayıt ekle/düzenle/sil/geri al, 90 günlük arşiv, filtreler, kayıtlı görünümler, Türkçe arama/sıralama.
- Tarih/para hesapları, bekleme günleri, arşiv ve durum geçişleri.
- Karar/makbuz dosya yolları; ağ paylaşımı yokken ve dosya taşındığında davranış.
- HTML rapor, grafik, CSV/Excel akışları, yedek ve geri yükleme.
- TKGM manuel giriş, iş listesinden aktarım, mahalle eşleştirme, Excel içe/dışa aktarma.
- TKGM aktif/pasif/belirsiz/hata, timeout, limit ve hareket servisi hatası.
- Günlük istek limiti, istek aralığı, aktif parsel tekrar kontrol süresi ve kapalı işlerin sorgulanmaması.
- Pasif parsel hareket zinciri, ara pasifler ve nihai aktif parseller.
- `is_parsel_bag` çoklu iş/parsel ilişkileri.
- `parsel_kontrol` UPSERT: ilk pasif sonuç onay=1; pasif kalırken önceki onay korunur; pasif dışı sonuçta onay=0.
- Encümen'in TKGM sonucunu okuyup Fen Klasörü'ne senkronlaması; elle kilitli kayıt ezilmemesi; “TKGM sonucuna dön”.
- TKGM penceresinin Encümen'den art arda açılma/öne getirilme/kapatılma senaryosu; mevcut `winfo_exists()` Qt uyumsuzluğu giderilmiş olmalı.
- Qt worker'ı sürerken pencere kapatma/iptal; UI donmaması ve thread kapanışında çökme olmaması.
- TKGM'nin bağımsız Qt açılışı ve Qt Encümen içinden açılışı.
- Windows temiz ortamında requirements kurulumu ve EXE paketlemesi.

## 10. Çözülmesi gereken riskler

1. **Mevcut Qt/Tk hibrit bağlantısı:** TKGM Qt penceresi şu an Tk `after` köprüsüne sahip. Encümen Qt'ye geçince bu ara katmanın nasıl kaldırılacağı planlanmalı.
2. **Pencere yaşam döngüsü hatası:** Encümen'deki `winfo_exists()` Qt penceresinde bulunmuyor; tekrar açma akışı düzeltilmeli.
3. **SQLite eşzamanlı yazma:** İki DB ve özellikle ortak `parsel_kontrol` yazımı eşzamanlılık altında test edilmeli.
4. **Worker güvenliği:** Worker'dan widget erişimi ve pencere kapanışında thread yaşam döngüsü kontrol edilmeli.
5. **TKGM dış servisi:** Canlı servis değişebilir; otomatik testler kayıtlı JSON/mock yanıtlarla çalışmalı.
6. **Paketleme:** Python/EXE aracı sürümü, ikon, göreli yollar ve yazma izinleri ayrıca doğrulanmalı.
7. **Doküman uyumsuzluğu:** `ENTEGRASYON.txt` requirements özetinde PySide6'dan söz etmiyor; kurulum notu güncellenmeli.
8. **Harita/çıktı artıkları:** `DATA_DIR` ve `map_file` tanımları mevcut, ancak sorgu worker'ı harita PNG üretmediğini belirtiyor; kullanılmayan alan/klasör olduğu kanıtlanmadan kaldırılmamalı.

## 11. Hesaplara verilecek hazır görev talimatları

### Hesap 1'e gönderilecek metin

> Yalnız Encümen/İş Takip uygulamasının Tkinter → PySide6 dönüşümünü yap. Kaynak dosya `encumen_kayit.py`; önce `DONUSUM_PLANI.md` belgesini oku. `modern_tasarim.py` eski ve uygulanmamış ayrı bir denemedir; kesinlikle açma, analiz etme veya kullanma. TKGM modülü `parsel_sorgu_modulu.py` zaten PySide6 arayüzüne sahip ve başka hesap tarafından denetlenecek; bu dosyaya dokunma. Encümen'in iş kurallarını, tarih/para/parsel hesaplarını, kayıt/filtre/rapor/grafik/Fen Klasörü/dosya/CSV/yedek özelliklerini eksiksiz koru. Gerçek DB'yi kullanma; yalnız kopya DB ile test et. `imar_kayitlari.db` şemasını ve `parsel_kontrol` tablosunun kolonlarını değiştirme. TKGM'nin `takip_db`, `work_id`, `onay_bekliyor` ve `sonuc_geri_cagir(work_id, ozet)` sözleşmesini koru. Önemli: mevcut `parsel_sorgu_ac` içinde Qt penceresine `winfo_exists()` çağrısı yapılıyor; bunu Qt pencere yaşam döngüsüne uygun şekilde düzelt. TKGM penceresini QWidget/QMainWindow parent ile açabilecek biçimde entegre et; TKGM kaynak dosyasını değiştirme. Yalnız `feature/pyside6-encumen` branch'inde çalış. Ana dala commit/merge yapma. Sonunda değişen dosyaları, testleri, eksikleri ve çalıştırma talimatını bildir.

### Hesap 2'ye gönderilecek metin

> Yalnız TKGM Parsel Sorgulama modülünün mevcut PySide6 uygulamasını denetle ve eksiklerini tamamla. Kaynak dosya `parsel_sorgu_modulu.py`; önce `DONUSUM_PLANI.md` belgesini oku. **Bu dosya zaten PySide6'ya dönüştürülmüş durumda; sıfırdan Tkinter→Qt dönüşümü yapma ve mevcut çalışan yapıyı gereksiz yere yeniden yazma.** `modern_tasarim.py` eski ve uygulanmamış ayrı bir denemedir; kesinlikle açma, analiz etme veya kullanma. Encümen ana uygulaması `encumen_kayit.py` başka hesap tarafından Qt'ye dönüştürülecek; bu dosyaya dokunma. Mevcut TKGM sorgu motorunu, API uçlarını, hareket zincirini, mahalle eşleştirmesini, günlük limit/bekleme, Excel akışlarını ve `parsel_kayitlari.db` verisini koru. `takip_db` ile verilen `imar_kayitlari.db` içindeki `parsel_kontrol` UPSERT alanlarını ve `onay_bekliyor` geçiş mantığını değiştirme. `sonuc_geri_cagir(work_id, ozet)` callback sözleşmesini koru. Qt Encümen'in kullanacağı pencere parent, callback/sinyal ve pencere yaşam döngüsü API'sini netleştir; eski Tk ana uygulamasıyla geçiş köprüsünü, Encümen dönüşümü tamamlanmadan bozma. Worker thread'lerinin GUI'ye yalnız sinyallerle eriştiğini, iptal ve kapanış davranışını test et. Yalnız `feature/pyside6-parsel-review` branch'inde çalış. Ana dala commit/merge yapma. Sonunda doğruladığın özellikleri, değiştirdiğin dosyaları, test sonuçlarını ve eksikleri bildir.

---

**İnceleme sınırı:** Kaynak dosyalar GitHub `main` dalından statik olarak okundu. Uygulamalar çalıştırılmadı, canlı TKGM isteği yapılmadı, gerçek SQLite DB açılmadı veya değiştirilmedi. Çalışma zamanı davranışları ve paketleme testleri sonraki aşamada yapılmalıdır.
