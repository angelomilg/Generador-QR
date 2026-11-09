"""Utilidades del sistema operativo."""

import logging
import os
import subprocess
import sys

log = logging.getLogger("bot")


def evitar_suspension():
    """Impide que el ordenador se suspenda mientras el bot está abierto.

    No cambia ninguna configuración del sistema: en cuanto cierras el bot,
    el ordenador vuelve a comportarse como siempre. (Cerrar la tapa de un
    portátil puede suspenderlo igualmente.)
    """
    try:
        if sys.platform.startswith("win"):
            import ctypes

            ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        elif sys.platform == "darwin":
            subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        else:
            return
        log.info("El ordenador no se suspenderá mientras el bot esté abierto.")
    except Exception as e:
        log.warning("No se pudo evitar la suspensión: %s", e)
