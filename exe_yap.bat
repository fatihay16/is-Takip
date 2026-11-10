@echo off
setlocal
cd /d "%~dp0"

set "DATA_BACKUP=%CD%\.exe_build_data"

echo ============================================
echo  Imar Uygulamalari - PySide6 EXE olusturuluyor
echo ============================================

rem Yeni arayuzun ve gerekli modullerin varligini kontrol et.
for %%F in (encumen_qt.py encumen_qt_pencereler.py encumen_qt_sekmeler.py encumen_tema.py v11_gorsel.py v11_ikonlar.py encumen_kayit.py parsel_baslat.py parsel_sorgu_modulu.py requirements.txt) do (
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
echo [1/5] Mevcut EXE verileri guvenceye aliniyor...
if not exist "%DATA_BACKUP%" mkdir "%DATA_BACKUP%"
rem EXE'nin yanindaki veritabani asil kullanilan veri olabilir. Once onu sakla.
if exist "dist\imar_kayitlari.db" copy /y "dist\imar_kayitlari.db" "%DATA_BACKUP%\imar_kayitlari.db" >nul
if exist "dist\parsel_kayitlari.db" copy /y "dist\parsel_kayitlari.db" "%DATA_BACKUP%\parsel_kayitlari.db" >nul
if exist "dist\Sonuclar" xcopy "dist\Sonuclar" "%DATA_BACKUP%\Sonuclar" /E /I /H /Y >nul
if exist "dist\yedekler" xcopy "dist\yedekler" "%DATA_BACKUP%\yedekler" /E /I /H /Y >nul

echo.
echo [2/5] Gerekli kutuphaneler kuruluyor...
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
echo [3/5] Eski derleme dosyalari temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ImarUygulamalari.spec del /q ImarUygulamalari.spec

echo.
echo [4/5] PySide6 ana programi paketleniyor...
set "PYI_ARGS=--noconfirm --clean --onefile --windowed --name ImarUygulamalari --distpath dist --workpath build --specpath . --paths . --hidden-import encumen_qt_pencereler --hidden-import encumen_qt_sekmeler --hidden-import encumen_tema --hidden-import v11_gorsel --hidden-import v11_ikonlar --hidden-import encumen_kayit --hidden-import parsel_baslat --hidden-import parsel_sorgu_modulu"

if exist encumen.ico (
    %PY% -m PyInstaller %PYI_ARGS% --icon "encumen.ico" --add-data "encumen.ico;." encumen_qt.py
) else (
    %PY% -m PyInstaller %PYI_ARGS% encumen_qt.py
)
if errorlevel 1 (
    echo.
    echo HATA: EXE olusturulamadi. Verileriniz .exe_build_data klasorunde korundu.
    pause
    exit /b 1
)

echo.
echo [5/5] Veriler geri yukleniyor...
rem Once mevcut EXE'den saklanan dosyalar; yoksa kaynak klasordeki dosyalar kullanilir.
if exist "%DATA_BACKUP%\imar_kayitlari.db" (
    copy /y "%DATA_BACKUP%\imar_kayitlari.db" "dist\imar_kayitlari.db" >nul
) else if exist "imar_kayitlari.db" (
    copy /y "imar_kayitlari.db" "dist\imar_kayitlari.db" >nul
)
if exist "%DATA_BACKUP%\parsel_kayitlari.db" (
    copy /y "%DATA_BACKUP%\parsel_kayitlari.db" "dist\parsel_kayitlari.db" >nul
) else if exist "parsel_kayitlari.db" (
    copy /y "parsel_kayitlari.db" "dist\parsel_kayitlari.db" >nul
)
if exist "%DATA_BACKUP%\Sonuclar" (
    xcopy "%DATA_BACKUP%\Sonuclar" "dist\Sonuclar" /E /I /H /Y >nul
) else if exist "Sonuclar" (
    xcopy "Sonuclar" "dist\Sonuclar" /E /I /H /Y >nul
)
if exist "%DATA_BACKUP%\yedekler" (
    xcopy "%DATA_BACKUP%\yedekler" "dist\yedekler" /E /I /H /Y >nul
) else if exist "yedekler" (
    xcopy "yedekler" "dist\yedekler" /E /I /H /Y >nul
)

if exist "%DATA_BACKUP%" rmdir /s /q "%DATA_BACKUP%"

echo.
echo ============================================
echo  BASARILI!
echo  EXE: dist\ImarUygulamalari.exe
echo ============================================
echo.
echo Masaustu kisayolu icin kisayol_olustur.bat dosyasini calistirin.
echo Veritabani ve yedekler dist klasorunde korunur.
echo Parsel Sorgu modulu de ayni EXE icinden ayri surecte acilir.
pause
endlocal
