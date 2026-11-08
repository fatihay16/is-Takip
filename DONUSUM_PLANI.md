# PySide6 Dönüşüm Planı — Encümen Kayıt + TKGM Parsel Sorgulama

> İnceleme tarihi: 08.11.2026  
> Depo: `fatihay16/is-Takip`  
> İncelenen dal: `main`  
> Kapsam dışı: `modern_tasarim.py` (kullanıcının açıklamasına göre eski, uygulanmamış ve ayrı bir deneme; açılmadı ve analiz edilmedi).  
> Bu belge planlama çıktısıdır. Uygulama kaynak kodlarında, veritabanlarında veya mevcut çalışma dosyalarında değişiklik yapılmamıştır.

## 1. İncelenen dosyalar ve doğrulama

| Dosya | İnceleme sonucu |
|---|---|
| `encumen_kayit.py` | 3.453 satır. Tkinter tabanlı ana Encümen/İş Takip uygulaması. `App` sınıfı, kayıt/form/filtre/rapor/yedek/Fen Klasörü ve TKGM bağlantısı. |
| `parsel_sorgu_modulu.py` | 1.865 satır. Tkinter `Toplevel` modülü. TKGM CBS sorgusu, hareket zinciri çözümleme, Excel içe/dışa aktarma, yerel parsel veritabanı ve İş Takip bağlantısı. |
| `requirements.txt` | Şu an yalnızca `requests>=2.31.0` ve `openpyxl>=3.1.2` içeriyor. PySide6 henüz listelenmiyor. |
| `ENTEGRASYON.txt` | Entegrasyon davranışını ve bazı performans/kurulum notlarını açıklıyor. Özellikle sonuçların İş Takip DB'sindeki `parsel_kontrol` tablosuna yazıldığını doğruluyor. |

Dosyaların Git blob kimlikleri (inceleme anındaki):
- `encumen_kayit.py`: `d5129119de41d398f699ed744e632fa99e152078`
- `parsel_sorgu_modulu.py`: `5e263c774dd4bf4ac10728d0ae4869e6ed1b99ef`
- `requirements.txt`: `9c8b396f7a2c879961abc6b8c315cf92328cb0f5`
- `ENTEGRASYON.txt`: `607a8be57cb8bbd3445bfdaf56234a7ba0883f44`

## 2. Mevcut uygulama envanteri

### 2.1 Encümen / İş Takip — `encumen_kayit.py`

- Başlangıç: `init_db()`, ardından `App().root.mainloop()`.
- Ana arayüz: `App` sınıfı; Kayıtlar, Grafikler ve Fen Klasörü sekmeleri.
- Form ve yardımcı pencereler: `Form`, `Listeler`, `Silinenler`, `TopluGuncelle`, `RaporAyar`, `FenIslemDialog`, `ZincirDetay`, `PasifListe`, `Takvim`.
- Veri/iş kuralları: Türkçe sıralama ve arama, tarih/para ayrıştırma, bekleme günü, arşiv durumları, kayıt filtreleri, toplu düzenleme, geri alma/son silinenler, CSV içe/dışa aktarma.
- Dosya işlemleri: karar ve makbuz dosyalarının yolunu kaydetme/açma, klasör indeksleme, yedek alma/geri yükleme.
- Raporlama: HTML rapor üretimi ve tarayıcıda açma; grafik çizimleri.
- Parsel/Fen işlevleri: TKGM sonuçlarını okuma, pasif parsel listesi, hareket zinciri, eski-yeni parsel ilişkileri, Fen Klasörü senkronizasyonu ve elle düzenlenmiş kayıtları kilitleme.
- Önemli fonksiyon grupları: `init_db`, `parsel_kontrol_oku`, `fen_kayit_ekle`, `fen_kayit_guncelle`, `fen_senkronla`, `kayit_sil`, `kayit_geri`, `yedekle`, `App.parsel_sorgu_ac`, `App.parsel_sonuc_geldi`, `App.fen_*`.

### 2.2 TKGM Parsel Sorgulama — `parsel_sorgu_modulu.py`

- Ana pencere: `App(tk.Toplevel)`. Ana uygulamadan `master`, `kaynak`, `takip_db`, `sonuc_geri_cagir` parametreleriyle açılabiliyor; bağımsız açılışta kendi Tk kök penceresini oluşturuyor.
- TKGM servis kökü: `https://cbsapi.tkgm.gov.tr/megsiswebapi.v3.1/api`; Parsel Sorgu web adresi ve HTTP başlıkları da tanımlı.
- Sorgu motoru: `query_one`, `analiz_et`, `tkgm_gittigi_kayitlar`, `devam_parsellerini_zincirle`, `hareket_adresi`, `get_json`, mahalle/il/ilçe kimlik eşleştirme fonksiyonları.
- Pencere özellikleri: elle parsel ekleme, il/ilçe/mahalle seçimi, açık iş listesinden aktarım, kapanan işlerin parsellerini gizleme/gösterme, günlük istek sayacı/limit, otomatik tekrar kontrol, seçili/toplu sorgu, durum/alan/nitelik/yeni parseller ve hareket ayrıntısı.
- Dosya/veri işlemleri: Excel şablonu oluşturma, Excel içe/dışa aktarma; yerel ayarlar ve TKGM liste önbelleği.
- İş parçacığı kullanımı: idari listeler, iş listesinden aktarım ve sorgu çalıştırma arka plan thread'lerinde. UI güncellemeleri `after(...)` ile ana Tk döngüsüne yönlendiriliyor.
- Ana sınıf ve fonksiyonlar: `App`, `Detay`, `HareketAyar`, `MahalleEslestir`, `db`, `query_one`, `takip_sonuc_yaz`, `aktarim_hazirla`, `start_queries`, `worker`, `export_excel`, `import_excel`.

## 3. Veritabanı envanteri ve kritik ayrım

### 3.1 Encümen ana veritabanı

Dosya yolu: `encumen_kayit.py` içinde `BASE / imar_kayitlari.db`.

Kaynakta oluşturulan/kullanılan tablolar:
- `kayit`: Encümen iş kayıtları; `FIELDS/KEYS` içindeki alanlar ve sonradan eklenen `durum_tarihi`.
- `ayar`: uygulama ayarları.
- `liste`: mahalle, işlem, müellif ve onay listeleri.
- `silinen`: 90 günlük geri alma arşivi.
- `gorunum`: kayıtlı filtre/görünüm ayarları.
- `parsel_kontrol`: TKGM sonucunun iş ID'sine göre saklandığı entegrasyon tablosu.
- `fen_islem`, `fen_parsel`: Fen Klasörü işlem ve eski/yeni/ara parsel ilişkileri.

`parsel_kontrol` alanları (iki dosyadaki DDL'de eşleşiyor):
`work_id` (PK), `parsel_no`, `tkgm_mahalle`, `durum`, `alan`, `nitelik`, `islem_turu`, `islem_tarihi`, `yeni_parseller`, `nihai_aktifler`, `aciklama`, `son_kontrol`, `onay_bekliyor`, `zincir`.

### 3.2 Parsel modülünün kendi veritabanı

Dosya yolu: `parsel_sorgu_modulu.py` içinde `APP_DIR / parsel_kayitlari.db`; ek çıktı klasörü `APP_DIR / Sonuclar`.

Tablolar:
- `parcels`: il/ilçe/mahalle/ada/parsel, mahalle ID, alan, nitelik, koordinatlar, durum, açıklama ve hareket alanları.
- `ayar`: kullanıcı seçimleri, günlük limit ve hareket servisi ayarları.
- `sayac`: gün bazında istek sayacı.
- `liste_onbellek`: TKGM idari liste yanıtları.
- `is_parsel_bag`: İş Takip kayıt ID'si ile parsel arasındaki çoktan-çoğa bağlantı.
- `mahalle_esleme`: İş Takip mahalle adı ile TKGM resmi mahalle/ID eşlemesi.

**Bu iki DB aynı dosya değildir.** Parsel modülü kendi sonuçlarını önce `parsel_kayitlari.db` içinde tutar; İş Takip entegrasyonu için ayrıca `takip_db=imar_kayitlari.db` yolu verilir. İki DB'nin rolü karıştırılmamalı.

### 3.3 Doğrulanmış entegrasyon sözleşmesi

1. Encümen, açık işlerden `(id, mahalle, ada_parsel)` kaynak listesini hazırlar.
2. `App.parsel_sorgu_ac`, `parsel_sorgu_modulu.App(..., kaynak=kaynak, takip_db=DB, sonuc_geri_cagir=...)` çağrısıyla TKGM penceresini açar.
3. Parsel modülü sorgu sonucunu `takip_sonuc_yaz(takip_db_yolu, work_id, row)` ile ana DB'deki `parsel_kontrol` tablosuna UPSERT eder.
4. Sonuç yazma işlemi `kayit` tablosundaki iş verisini değiştirmez.
5. `onay_bekliyor` davranışı önemlidir: pasife yeni düşen parsel için uyarı oluşturulur; zaten pasif olan kayıtta mevcut onay durumu korunur; aktif/belirsiz sonuçta uyarı sıfırlanır.
6. Encümen tarafı `parsel_kontrol_oku` ile sonuçları okur; `fen_senkronla` pasif sonuçlardan Fen Klasörü kayıtlarını üretir/günceller. Elle düzenlenen/kilitli Fen kayıtlarının otomatik ezilmemesi gerekir.
7. `sonuc_geri_cagir(work_id, ozet)` UI yenileme bildirimi olarak kullanılır.

**Bu sözleşme dönüşüm boyunca sabit kalmalı.** Tablo/kolon adları, PK, UPSERT alanları, `work_id` anlamı, onay geçiş mantığı ve callback anlamı değiştirilemez; değişiklik gerekirse önce ortak entegrasyon tasarımı ve veri geçiş testi yapılmalıdır.

## 4. PySide6 hedef mimarisi

### 4.1 Önerilen yapı

İlk aşamada mevcut iş mantığını taşımadan yeniden yazmak yerine UI ile iş mantığını ayırın:

- `core/`: mevcut iş kuralları, veri erişimi, TKGM sorgu/analiz, rapor ve yedekleme fonksiyonları.
- `ui/`: PySide6 pencereleri, diyaloglar, modeller, delegate'ler ve stiller.
- `services/`: arka plan görevleri ve iki modül arasındaki uygulama servis sözleşmesi.
- `tests/`: geçici kopya veritabanlarıyla otomatik testler.
- Mevcut iki kaynak dosya ilk geçişte referans/karşılaştırma olarak korunmalı; taşınan mantık birebir test edilmeden eski uygulama kodu silinmemeli.

Ortak başlatıcı/ana pencere kararı iki UI modülünün iskeleti görülmeden kesinleştirilmemeli. Öneri: Encümen ana pencere; TKGM pencere hem bağımsız çalıştırılabilir hem Encümen içinden açılabilir bir `QDialog` veya `QMainWindow` olsun.

### 4.2 UI dönüşüm ilkeleri

- Encümen: ana kayıt tablosu için `QTableView` + `QAbstractTableModel`; sıralama/filtreleme için `QSortFilterProxyModel`. Satır renklendirme, sütun gizleme, çoklu seçim, detay paneli, kayıt/form pencereleri ve Grafik/Fen Klasörü sekmeleri korunmalı.
- TKGM: parsel listesi için model/view; durum renkleri, çoklu seçim, ilerleme çubuğu, sayaç, filtre/gizleme ve detay/hareket görünümü korunmalı.
- Tema, yazı boyutu, sütun görünürlüğü, pencere/kolon durumu ve kullanıcı tercihleri mevcut ayar anahtarlarıyla uyumlu saklanmalı.
- Dosya seçme/açma, Excel/CSV, HTML rapor, yedek/geri yükleme ve ikon davranışları için mevcut kullanıcı akışı korunmalı.
- İşlevsel eşdeğerlik sağlanmadan görsel sadeleştirme veya özellik kaldırma yapılmamalı.

### 4.3 Sinyal-slot ve iş parçacığı

- Qt widget'larına yalnız GUI ana thread'inden erişilsin.
- Ağ sorguları, toplu Excel işlemleri, büyük veri yüklemeleri ve dosya indeksleme için `QThread` + worker-object veya `QThreadPool/QRunnable` kullanılsın.
- Worker; ilerleme, durum, sonuç, hata ve tamamlandı sinyallerini yayınlasın. UI bu sinyalleri queued connection ile alsın.
- Worker içinden doğrudan widget değiştirmek, `QApplication.processEvents()` ile UI zorlamak veya Tkinter `after` yaklaşımını taşımak yasak.
- İptal/durdurma, günlük limit, istekler arası bekleme, timeout ve hata sınıfları (limit/erişim/diğer) aynı davranışı korusun.
- Pencere kapanırken worker'lar kontrollü durdurulsun; arka plan işlemi sürerken uygulamanın kapanması veri kaybı yaratmamalı.

### 4.4 Veritabanı erişim sözleşmesi

- Var olan DB dosya adları ve konumları varsayılan olarak değiştirilmeyecek: `imar_kayitlari.db`, `parsel_kayitlari.db`.
- Şema yükseltmeleri mevcut `CREATE TABLE IF NOT EXISTS` / kontrollü `ALTER TABLE` davranışını korumalı; yeni migration yalnızca açıkça gerekli ve geriye uyumluysa eklenmeli.
- İlk PySide6 açılışı canlı kullanıcı DB'sinde değil, kopya DB üzerinde test edilmeli.
- Bağlantılar kısa ömürlü ve işlem sınırları belirgin olmalı; her yazma `commit`/rollback güvenliğiyle yapılmalı. Eşzamanlı erişimde timeout ve SQLite kilitlenme davranışı test edilmeli.
- `parsel_kontrol` yazımı için tek bir ortak servis/repository fonksiyonu tercih edilmeli; iki tarafta farklı DDL veya farklı UPSERT mantığı kopyalanmamalı.
- `work_id` integer kimliği Encümen `kayit.id` ile eşleşmeye devam etmeli.
- WAL modu gibi performans ayarları canlı DB'de ölçüm ve yedek/geri dönüş planı olmadan etkinleştirilmemeli.

## 5. Bağımlılıklar ve paketleme

Mevcut `requirements.txt`:
- `requests>=2.31.0`
- `openpyxl>=3.1.2`

PySide6 henüz ekli değil. Dönüşüm tamamlandığında `PySide6` sabitlenmiş/uyumlu bir sürüm aralığıyla eklenmeli; kesin sürüm mevcut Python sürümü ve EXE paketleme aracı doğrulandıktan sonra seçilmeli. `requests` ve `openpyxl` korunmalı. Şu anki kaynaklarda Pillow import'u görünmüyor; yalnızca bu nedenle Pillow eklenmemeli. Kullanılmayan bağımlılıklar kanıt olmadan silinmemeli.

Python sürümü, PyInstaller/Nuitka kullanımı, `exe_yap.bat`, `kisayol_olustur.bat`, `encumen.ico` içerikleri bu görevde ayrıntılı incelenmedi; paketleme öncesi ayrıca doğrulanmalı. ENTEGRASYON.txt bu dosyaların değişmediğini söylüyor, fakat içeriklerinin güncel projeyle uyumu henüz doğrulanmış değil.

## 6. İki hesaba görev dağılımı

İki hesap ayrı branch'lerde çalışmalı; aynı dosyalara eşzamanlı yazmamalı.

### Hesap 1 — Encümen PySide6

- Branch: `feature/pyside6-encumen`
- Sahip olduğu kapsam: yalnız `encumen_kayit.py` dönüşümü ve kendisine ait yeni Encümen UI/core/test dosyaları.
- `parsel_sorgu_modulu.py` üzerinde değişiklik yapmayacak.
- TKGM sorgu motorunu yeniden yazmayacak; entegrasyonun karşı tarafını sabit sözleşmeye göre çağıracak.
- `parsel_kontrol` DDL/UPSERT alanlarını ve `sonuc_geri_cagir` imzasını değiştirmeyecek.
- Teslim: Encümen PySide6 arayüzü, işlev eşleştirme tablosu, testler, değişen dosya listesi, çalıştırma yönergesi.

### Hesap 2 — TKGM Parsel PySide6

- Branch: `feature/pyside6-parsel`
- Sahip olduğu kapsam: yalnız `parsel_sorgu_modulu.py` dönüşümü ve kendisine ait yeni TKGM UI/core/worker/test dosyaları.
- `encumen_kayit.py` üzerinde değişiklik yapmayacak.
- TKGM API uç noktalarını, sorgu başına istek sayısını, hareket zinciri çözümünü, mahalle eşlemesini, günlük limit ve bekleme kurallarını değiştirmeyecek.
- `takip_db` yolunu, `takip_sonuc_yaz` davranışını ve `sonuc_geri_cagir(work_id, ozet)` sözleşmesini koruyacak.
- Teslim: TKGM PySide6 penceresi, bağımsız/entegre çalışma testi, testler, değişen dosya listesi, çalıştırma yönergesi.

### Her iki hesap için ortak yasaklar

- `modern_tasarim.py` dosyasını açma, analiz etme, içe aktarma veya kullanma.
- Diğer hesabın sahip olduğu kaynak dosyaya müdahale etme.
- Ana dala doğrudan commit/push/merge yapma.
- Gerçek kullanıcı veritabanını açma, değiştirme veya migration çalıştırma.
- Mevcut özellikleri sessizce kaldırma veya iş mantığını “daha iyi” olduğu varsayımıyla değiştirme.
- Bir modülün henüz tamamlanmamış diğer modülün UI sınıflarına doğrudan bağımlı olmasını sağlama.
- Her görev sonunda test çıktısı, değişen dosya listesi ve bilinen eksikleri raporla.

## 7. Aşamalı uygulama ve birleştirme

1. **Ortak sözleşmeyi dondur:** DB yolları/tabloları, `parsel_kontrol` alanları, callback ve hata/sonuç sözleşmesi.
2. **İş mantığı/UI ayrımı:** her hesap kendi modülünde önce mevcut fonksiyonları UI bağımlılığından ayırıp test edilebilir hale getirsin.
3. **Encümen UI:** kayıt tablosu, filtreler, formlar, detaylar, grafikler, Fen Klasörü, rapor, yedek, dosya ve CSV akışları.
4. **TKGM UI:** konum seçimi, iş aktarımı, parsel listesi, sorgu worker'ı, ilerleme/sayaç, detay/hareket zinciri, Excel akışları.
5. **Tekil modül testleri:** her modül kendi branch'inde sentetik/geçici DB ile test edilsin.
6. **Entegrasyon branch'i:** iki branch, ana dala değil, ayrı bir `integration/pyside6` branch'ine sırayla birleştirilsin. Çakışmalar ve ortak sözleşme burada çözülsün.
7. **Regresyon testi:** aşağıdaki senaryolar geçmeden canlı DB'ye geçilmesin.
8. **Paketleme:** temiz Windows ortamında kurulum/EXE, dosya yolları, ikon, yedek ve güncelleme davranışı doğrulansın.
9. **Canlı geçiş:** kullanıcı önce yedek alsın; ilk açılış öncesi otomatik migration kopya DB'de doğrulanmış olsun. Geri dönüş için eski EXE ve DB yedeği saklansın.

## 8. Zorunlu test kontrol listesi

- Eski DB kopyasıyla açılış: kayıt sayısı, ID'ler, alanlar ve listeler aynı.
- Yeni şema ekleme: yalnız beklenen kolonlar ekleniyor; mevcut veri değişmiyor.
- Kayıt ekleme/düzenleme/silme/geri alma/90 günlük son silinenler.
- Türkçe arama/sıralama, tarih ve para biçimleri, filtreler, toplu işlem.
- Karar/makbuz dosyası yolları; erişilemeyen ağ klasörü ve taşınmış dosya davranışı.
- Rapor, Excel/CSV içe/dışa aktarma, yedek/geri yükleme.
- Parsel modülünde manuel giriş, Excel içe/dışa aktarma, idari liste önbelleği ve mahalle eşlemesi.
- TKGM aktif, pasif, belirsiz, erişim hatası, limit hatası, zaman aşımı ve hareket servisi hatası.
- Günlük istek sayacı, bekleme aralığı, aktif parsel yenileme süresi ve kapanmış işlerin sorgulanmaması.
- Pasif parselin tüm devam/aktif parselleri ve hareket zinciri.
- İş listesinden aktarım: tek parselin birden çok işe bağlanması ve birden çok parselin eşleşmesi.
- `parsel_kontrol` UPSERT: ilk pasif sonuçta onay=1; pasif kalırken mevcut onay korunur; aktif/belirsiz sonuçta onay=0.
- Encümen'in TKGM sonucunu okuması, Fen Klasörü'ne senkronlaması, elle kilitli kaydı ezmemesi ve “TKGM sonucuna dön” davranışı.
- Ağ/DB yavaşken UI donmaması; worker tamamlanmadan pencere kapanışının güvenli olması.
- Bağımsız TKGM açılışı ve Encümen içinden açılışı.

## 9. Açık riskler / doğrulanması gerekenler

1. **Aynı fiziksel DB dosyasına eşzamanlı yazma:** iki uygulama aynı anda çalışırsa SQLite kilitlenmesi/yarım kalmış işlem riski test edilmeli.
2. **İşlem thread'leri:** TKGM sorgusu ve sonuç yazımı arka planda; UI callback'leri Qt sinyalleriyle ana thread'e alınmalı.
3. **Bağımsız ve entegre çalışma:** TKGM modülü kendi DB'sini ve opsiyonel İş Takip DB'sini kullanıyor. İki modun da korunması gerekiyor.
4. **Dosya yolu ve EXE:** `BASE/APP_DIR` davranışı EXE, kaynak kod, ağ klasörü ve yazma izni senaryolarında doğrulanmalı.
5. **Dış TKGM servisi:** API yanıt şeması ve hareket servisi değişebilir; canlı servis olmadan testler mock/fikstür kullanmalı, gerçek servis testi ayrıca yapılmalı.
6. **Sürüm/paketleme:** Python ve EXE aracı sürümleri bu inceleme kapsamındaki dosyalardan kesinleşmiyor.
7. **UI kapsamı büyük:** Encümen tarafında çok sayıda yardımcı pencere ve özel etkileşim var; yalnız ana tabloyu taşımak tamamlanmış dönüşüm sayılmaz.
8. **İki branch entegrasyonu:** her iki uygulama da ortak başlatıcı veya ortak veri servisinde değişiklik isterse bu kısım önceden atanmalı; aynı dosyayı iki hesap düzenlememeli.

## 10. Hesaplara verilecek hazır görev metinleri

### Hesap 1'e gönderilecek metin

> Bu görevde yalnız Encümen/İş Takip uygulamasını PySide6'ya dönüştür. Kaynak: `encumen_kayit.py`. Önce `DONUSUM_PLANI.md` belgesini oku ve Encümen bölümünü uygula. `modern_tasarim.py` eski ve uygulanmamış ayrı bir çalışmadır; kesinlikle açma, analiz etme veya kullanma. TKGM modülü `parsel_sorgu_modulu.py` başka hesap tarafından geliştirilecek; bu dosyaya dokunma. TKGM entegrasyon sözleşmesini koru: `imar_kayitlari.db` içindeki `parsel_kontrol` tablosu, kolonlar, `work_id`, onay geçiş mantığı ve `sonuc_geri_cagir(work_id, ozet)` imzası değişmeyecek. İş kurallarını, hesaplamaları, kayıtları, filtreleri, Fen Klasörü, grafik, rapor, dosya, CSV, yedek ve geri yükleme özelliklerini eksiksiz koru. Gerçek DB'yi kullanma; test için kopya DB üret. Sadece `feature/pyside6-encumen` branch'inde çalış. TKGM dosyasını, ana dalı veya diğer hesabın dosyalarını değiştirme. Önce analiz ve dönüşüm adımlarını küçük commit'lerle yap; her aşamada test et. Sonunda değişen dosyaları, test sonuçlarını, eksikleri ve çalıştırma talimatını bildir. Özellik kaldırma veya şema değiştirme yapma.

### Hesap 2'ye gönderilecek metin

> Bu görevde yalnız TKGM Parsel Sorgulama modülünü PySide6'ya dönüştür. Kaynak: `parsel_sorgu_modulu.py`. Önce `DONUSUM_PLANI.md` belgesini oku ve TKGM bölümünü uygula. `modern_tasarim.py` eski ve uygulanmamış ayrı bir çalışmadır; kesinlikle açma, analiz etme veya kullanma. Encümen ana uygulaması `encumen_kayit.py` başka hesap tarafından geliştirilecek; bu dosyaya dokunma. TKGM sorgu motorunu, API uç noktalarını, hareket zincirini, mahalle eşlemesini, istek sayacı/limiti, bekleme aralığını, Excel akışlarını ve yerel `parsel_kayitlari.db` verisini koru. Entegrasyon sözleşmesi değişmeyecek: `takip_db` parametresiyle verilen `imar_kayitlari.db` dosyasındaki `parsel_kontrol` tablosuna aynı kolonlarla UPSERT yap; `onay_bekliyor` mantığını ve `sonuc_geri_cagir(work_id, ozet)` callback'ini koru. Modül hem bağımsız hem Encümen içinden açılabilir olmalı. Gerçek DB'yi kullanma; test için kopya DB üret. Sadece `feature/pyside6-parsel` branch'inde çalış. Encümen dosyasını, ana dalı veya diğer hesabın dosyalarını değiştirme. Sonunda değişen dosyaları, test sonuçlarını, eksikleri ve çalıştırma talimatını bildir. Özellik kaldırma veya şema değiştirme yapma.

---

**İnceleme sınırı:** Kaynak kodları statik olarak okundu; uygulamalar çalıştırılmadı, TKGM'ye canlı istek atılmadı, DB dosyası açılmadı ve test verisi üretilmedi. Bu nedenle davranışa ilişkin doğrulamalar kaynak kodundaki tanımlar ve entegrasyon notlarıyla sınırlıdır.
