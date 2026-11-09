#!/bin/bash
# Doble clic para arrancar el bot en Mac (o ejecútalo con ./iniciar_mac.command en Linux).
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "No se ha encontrado Python 3. Instálalo desde https://www.python.org/downloads/ y vuelve a abrir este archivo."
  read -r -p "Pulsa Intro para cerrar."
  exit 1
fi

if [ ! -f .venv/instalado.txt ]; then
  echo "Preparando el bot por primera vez. Tarda un par de minutos..."
  python3 -m venv .venv && .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt \
    && echo ok > .venv/instalado.txt || { echo "Error al preparar el bot."; rm -rf .venv; read -r -p "Pulsa Intro."; exit 1; }
fi

while true; do
  .venv/bin/python -m bot "$@"
  echo
  echo "El bot se ha cerrado. Se volverá a abrir en 60 segundos (pulsa Ctrl+C para evitarlo)."
  sleep 60
done
