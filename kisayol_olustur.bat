@echo off
cd /d "%~dp0"
if not exist "dist\ImarUygulamalari.exe" (
  echo dist\ImarUygulamalari.exe bulunamadi. Once exe_yap.bat dosyasini calistirin.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Imar Uygulamalari.lnk'); $s.TargetPath='%CD%\dist\ImarUygulamalari.exe'; $s.WorkingDirectory='%CD%\dist'; $s.IconLocation='%CD%\dist\ImarUygulamalari.exe,0'; $s.Description='Imar Uygulamalari'; $s.Save()"
if errorlevel 1 (
  echo Kisayol olusturulamadi.
  pause
  exit /b 1
)
echo Masaustune "Imar Uygulamalari" kisayolu eklendi.
pause
