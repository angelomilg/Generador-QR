"""Carga de la configuración.

Todos los valores tienen un valor por defecto razonable. Si quieres cambiar
algo, edita `config.json` (en la carpeta principal del bot). Las claves del
exchange, solo necesarias para el modo real, van en `claves.json`, que nunca
se sube a GitHub.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

POR_DEFECTO = {
    # "simulacion": opera con dinero ficticio usando precios reales (no necesita cuenta).
    # "real": opera con tu dinero. Necesita claves.json.
    "modo": "simulacion",
    "exchange": "binance",
    "par": "BTC/EUR",
    "timeframe": "1h",
    "capital_inicial": 100.0,
    # Costes que se asumen en simulación y en las pruebas con datos pasados.
    "comision": 0.001,
    "deslizamiento": 0.0005,
    # Evaluación de estrategias (walk-forward).
    "dias_historico": 180,
    "dias_validacion": 60,
    "reevaluar_cada_horas": 168,
    # Solo se cambia de estrategia si la nueva es claramente mejor (en Sharpe).
    "margen_cambio": 0.25,
    # Límites de riesgo: el bot no puede saltárselos.
    "stop_total_pct": 0.20,
    "stop_diario_pct": 0.05,
    # Comodidades.
    "evitar_suspension": True,
    "abrir_panel_al_iniciar": True,
    "telegram_token": "",
    "telegram_chat_id": "",
}


def cargar_config(ruta=None):
    ruta = Path(ruta) if ruta else RAIZ / "config.json"
    cfg = dict(POR_DEFECTO)
    if ruta.exists():
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        desconocidas = set(datos) - set(POR_DEFECTO) - {"_ayuda"}
        if desconocidas:
            raise ValueError(f"Opciones desconocidas en config.json: {sorted(desconocidas)}")
        cfg.update({k: v for k, v in datos.items() if k != "_ayuda"})
    if cfg["modo"] not in ("simulacion", "real"):
        raise ValueError('"modo" debe ser "simulacion" o "real"')
    return cfg


def cargar_claves(ruta=None):
    ruta = Path(ruta) if ruta else RAIZ / "claves.json"
    if not ruta.exists():
        raise FileNotFoundError(
            "Para el modo real necesitas el archivo claves.json con tu api_key y api_secret. "
            "Copia claves.ejemplo.json, renómbralo a claves.json y rellénalo."
        )
    with open(ruta, encoding="utf-8") as f:
        claves = json.load(f)
    if not claves.get("api_key") or not claves.get("api_secret"):
        raise ValueError("claves.json debe tener api_key y api_secret")
    return claves
