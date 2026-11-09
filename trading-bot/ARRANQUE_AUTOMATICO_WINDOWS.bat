@echo off
chcp 65001 >nul
set "DESTINO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Trading bot.bat"
if exist "%DESTINO%" (
  del "%DESTINO%"
  echo Arranque automático DESACTIVADO. El bot ya no se abrirá al encender el ordenador.
) else (
  > "%DESTINO%" echo @echo off
  >> "%DESTINO%" echo start "Trading bot" /min "%~dp0INICIAR_WINDOWS.bat"
  echo Arranque automático ACTIVADO. El bot se abrirá solo al iniciar sesión en Windows.
  echo Vuelve a ejecutar este archivo si quieres desactivarlo.
)
pause
