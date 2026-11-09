@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Trading bot

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto sinpython
%PY% --version >nul 2>nul
if errorlevel 1 goto sinpython

if not exist ".venv\instalado.txt" (
  echo Preparando el bot por primera vez. Tarda un par de minutos...
  %PY% -m venv .venv || goto error
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto error
  echo ok> ".venv\instalado.txt"
)

:arrancar
".venv\Scripts\python.exe" -m bot %*
echo.
echo El bot se ha cerrado. Se volverá a abrir en 60 segundos (cierra esta ventana para evitarlo).
timeout /t 60
goto arrancar

:sinpython
echo No se ha encontrado Python. Intentando instalarlo automáticamente...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo Si se ha instalado bien, cierra esta ventana y vuelve a hacer doble clic en INICIAR_WINDOWS.bat
echo Si no, descarga Python desde https://www.python.org/downloads/ y marca "Add python.exe to PATH".
pause
exit /b

:error
echo.
echo Ha ocurrido un error al preparar el bot. Revisa el mensaje de arriba.
rmdir /s /q .venv 2>nul
pause
