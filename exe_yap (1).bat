@echo off
cd /d "%~dp0"
echo ============================================
echo  Imar Uygulamalari - EXE olusturuluyor
echo ============================================
where python >nul 2>nul && (set PY=python) || (set PY=py)
%PY% --version
if errorlevel 1 (
  echo Python bulunamadi. Once python.org adresinden Python kurun.
  pause
  exit /b 1
)
set ICON=
if exist encumen.ico set ICON=--icon encumen.ico --add-data "encumen.ico;."
if exist requirements.txt %PY% -m pip install -r requirements.txt
%PY% -m pip install --upgrade pyinstaller
if not exist parsel_sorgu_modulu.py echo UYARI: parsel_sorgu_modulu.py bulunamadi, Parsel Sorgu exe'ye eklenmeyecek.
%PY% -m PyInstaller --noconfirm --onefile --windowed --name ImarUygulamalari %ICON% --hidden-import parsel_sorgu_modulu encumen_kayit.py
if errorlevel 1 (
  echo.
  echo HATA: exe olusturulamadi. Yukaridaki mesajlari kontrol edin.
  pause
  exit /b 1
)
echo.
echo ============================================
echo  Bitti.  Program:  dist\ImarUygulamalari.exe
echo ============================================
echo Eski verilerinizi kullanmak icin imar_kayitlari.db dosyasini
echo exe'nin yanina (dist klasorune) kopyalayin.
echo Masaustu kisayolu icin kisayol_olustur.bat dosyasini calistirin.
echo (Parsel Sorgu icin parsel_sorgu_modulu.py bu klasorde olmalidir.)
pause
