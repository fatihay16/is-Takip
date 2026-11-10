@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Imar Uygulamalari - PySide6 EXE olusturuluyor
echo ============================================

rem Yeni arayuzun ve gerekli modullerin varligini kontrol et.
for %%F in (encumen_qt.py encumen_qt_pencereler.py encumen_qt_sekmeler.py encumen_tema.py encumen_kayit.py parsel_baslat.py parsel_sorgu_modulu.py requirements.txt) do (
    if not exist "%%F" (
        echo HATA: %%F bulunamadi. Proje dosyalari eksik.
        pause
        exit /b 1
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PY=python"
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        echo HATA: Python bulunamadi. Python 3 kurup PATH'e ekleyin.
        pause
        exit /b 1
    )
    set "PY=py"
)

%PY% --version
if errorlevel 1 (
    echo HATA: Python baslatilamadi.
    pause
    exit /b 1
)

echo.
echo [1/4] Gerekli kutuphaneler kuruluyor...
%PY% -m pip install --upgrade pip
if errorlevel 1 (
    echo HATA: pip guncellenemedi.
    pause
    exit /b 1
)
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo HATA: requirements.txt kutuphaneleri kurulamadi.
    pause
    exit /b 1
)
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo HATA: PyInstaller kurulamadi.
    pause
    exit /b 1
)

echo.
echo [2/4] Eski derleme klasorleri temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ImarUygulamalari.spec del /q ImarUygulamalari.spec

echo.
echo [3/4] PySide6 ana programi paketleniyor...
set "PYI_ARGS=--noconfirm --clean --onefile --windowed --name ImarUygulamalari --distpath dist --workpath build --specpath . --paths . --hidden-import encumen_qt_pencereler --hidden-import encumen_qt_sekmeler --hidden-import encumen_tema --hidden-import encumen_kayit --hidden-import parsel_baslat --hidden-import parsel_sorgu_modulu"

if exist encumen.ico (
    %PY% -m PyInstaller %PYI_ARGS% --icon "encumen.ico" --add-data "encumen.ico;." encumen_qt.py
) else (
    %PY% -m PyInstaller %PYI_ARGS% encumen_qt.py
)
if errorlevel 1 (
    echo.
    echo HATA: EXE olusturulamadi. Yukaridaki hata mesajlarini kontrol edin.
    pause
    exit /b 1
)

echo.
echo [4/4] Varsa mevcut veritabani ve sonuc dosyalari korunarak kopyalaniyor...
if exist "imar_kayitlari.db" if not exist "dist\imar_kayitlari.db" copy /y "imar_kayitlari.db" "dist\imar_kayitlari.db" >nul
if exist "parsel_kayitlari.db" if not exist "dist\parsel_kayitlari.db" copy /y "parsel_kayitlari.db" "dist\parsel_kayitlari.db" >nul
if exist "Sonuclar" if not exist "dist\Sonuclar" xcopy "Sonuclar" "dist\Sonuclar" /E /I /H /Y >nul

echo.
echo ============================================
echo  BASARILI!
echo  EXE: dist\ImarUygulamalari.exe
echo ============================================
echo.
echo Masaustu kisayolu icin kisayol_olustur.bat dosyasini calistirin.
echo Veritabani dosyalari EXE'nin bulundugu dist klasorunde tutulur.
echo Parsel Sorgu modulu de ayni EXE icinden ayri surecte acilir.
pause
endlocal
