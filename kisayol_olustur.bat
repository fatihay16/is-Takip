@echo off
setlocal
cd /d "%~dp0"

set "APP_EXE=%CD%\dist\ImarUygulamalari.exe"
if not exist "%APP_EXE%" (
    echo HATA: dist\ImarUygulamalari.exe bulunamadi.
    echo Once exe_yap.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo Masaustu kisayolu olusturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $exe=$env:APP_EXE; $desktop=[Environment]::GetFolderPath('Desktop'); $lnk=Join-Path $desktop 'Imar Uygulamalari.lnk'; $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath=$exe; $s.WorkingDirectory=[IO.Path]::GetDirectoryName($exe); $s.IconLocation=$exe + ',0'; $s.Description='Imar Uygulamalari'; $s.Save(); if (!(Test-Path -LiteralPath $lnk)) { throw 'Kisayol dosyasi olusturulamadi.' }"
if errorlevel 1 (
    echo HATA: Masaustu kisayolu olusturulamadi.
    pause
    exit /b 1
)

echo Tamam. Masaustune "Imar Uygulamalari" kisayolu eklendi.
pause
endlocal
