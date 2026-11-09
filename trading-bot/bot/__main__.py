"""Punto de entrada: `python -m bot`."""

import argparse
import logging
import sys
import webbrowser
from logging.handlers import RotatingFileHandler

from .config import RAIZ, cargar_claves, cargar_config
from .datos import crear_exchange, descargar_velas, velas_por_dia
from .informe import NOMBRES
from .selector import decidir, evaluar
from .sistema import evitar_suspension

CARPETA_ESTADO = RAIZ / "estado"


def configurar_registro():
    CARPETA_ESTADO.mkdir(exist_ok=True)
    formato = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    log = logging.getLogger("bot")
    log.setLevel(logging.INFO)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)
    archivo = RotatingFileHandler(CARPETA_ESTADO / "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    archivo.setFormatter(formato)
    log.addHandler(consola)
    log.addHandler(archivo)
    return log


def solo_backtest(cfg, ex):
    n = int(cfg["dias_historico"] * velas_por_dia(cfg["timeframe"]))
    df = descargar_velas(ex, cfg["par"], cfg["timeframe"], n)
    ranking = evaluar(df, cfg)
    print(f"\n{len(df)} velas de {cfg['par']} ({cfg['timeframe']}). Validación: últimos {cfg['dias_validacion']} días.\n")
    print(f"{'Estrategia':<22}{'Retorno':>10}{'Sharpe':>9}{'Caída máx':>11}{'Ops':>6}  Válida  Parámetros")
    for r in ranking:
        v = r["validacion"]
        print(f"{NOMBRES[r['estrategia']]:<22}{v['retorno']*100:>9.2f}%{v['sharpe']:>9.2f}{v['max_caida']*100:>10.2f}%"
              f"{v['operaciones']:>6}  {'sí' if r['valida'] else 'no':<6}  {r['params']}")
    elegida = decidir(ranking, None, cfg["margen_cambio"])
    print("\nEstrategia que usaría ahora:", f"{NOMBRES[elegida['estrategia']]} {elegida['params']}" if elegida
          else "ninguna (se quedaría en euros)")


def main():
    parser = argparse.ArgumentParser(description="Trading bot con selección automática de estrategia")
    parser.add_argument("--backtest", action="store_true", help="solo evalúa las estrategias y muestra los resultados")
    parser.add_argument("--una-vez", action="store_true", help="ejecuta un único ciclo y termina")
    args = parser.parse_args()

    log = configurar_registro()
    cfg = cargar_config()
    claves = cargar_claves() if cfg["modo"] == "real" else None
    ex = crear_exchange(cfg, claves)

    if args.backtest:
        solo_backtest(cfg, ex)
        return

    from .motor import Bot

    log.info("=" * 60)
    log.info("Bot iniciado | modo %s | %s en %s | velas de %s",
             cfg["modo"].upper(), cfg["par"], cfg["exchange"], cfg["timeframe"])
    if cfg["modo"] == "real":
        log.warning("MODO REAL: el bot opera con tu dinero. Usará TODO el saldo de %s de la cuenta.",
                    cfg["par"].split("/")[1])
    log.info("Panel: %s", CARPETA_ESTADO / "panel.html")
    log.info("Para pararlo, cierra esta ventana o pulsa Ctrl+C.")
    log.info("=" * 60)

    if cfg["evitar_suspension"] and not args.una_vez:
        evitar_suspension()

    bot = Bot(cfg, ex, CARPETA_ESTADO)
    if args.una_vez:
        bot.ciclo()
        return
    abrir_panel = None
    if cfg["abrir_panel_al_iniciar"]:
        def abrir_panel():
            webbrowser.open((CARPETA_ESTADO / "panel.html").as_uri())
    bot.bucle(tras_primer_ciclo=abrir_panel)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot detenido por el usuario.")
