"""Bucle principal del bot."""

import json
import logging
import math
import time
from datetime import datetime, timezone

from . import riesgo
from .avisos import avisar
from .broker import BrokerReal, BrokerSimulado
from .datos import descargar_velas, tf_ms, velas_por_dia
from .estrategias import VELAS_CALENTAMIENTO, senal
from .informe import NOMBRES, generar_panel
from .selector import decidir, evaluar

log = logging.getLogger("bot")

MAX_HISTORIAL = 24 * 365
MAX_OPERACIONES = 1000


class Bot:
    def __init__(self, cfg, ex, carpeta_estado):
        self.cfg = cfg
        self.ex = ex
        self.carpeta = carpeta_estado
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.ruta_estado = self.carpeta / "estado.json"
        self.ruta_panel = self.carpeta / "panel.html"
        self.estado = self._cargar()
        if self.estado.get("modo") not in (None, cfg["modo"]):
            raise RuntimeError(
                f"El estado guardado es del modo '{self.estado['modo']}' y ahora estás en '{cfg['modo']}'. "
                f"Para empezar de cero, borra la carpeta {self.carpeta}."
            )
        self.estado["modo"] = cfg["modo"]
        if cfg["modo"] == "real":
            self.broker = BrokerReal(ex, cfg["par"])
        else:
            self.broker = BrokerSimulado(self.estado, cfg)

    # --- estado persistente -------------------------------------------------
    def _cargar(self):
        if self.ruta_estado.exists():
            return json.loads(self.ruta_estado.read_text(encoding="utf-8"))
        return {}

    def guardar(self):
        tmp = self.ruta_estado.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.estado, indent=1), encoding="utf-8")
        tmp.replace(self.ruta_estado)

    # --- evaluación de estrategias -----------------------------------------
    def toca_reevaluar(self, ahora_ms):
        ultima = self.estado.get("ultima_evaluacion")
        return ultima is None or ahora_ms - ultima >= self.cfg["reevaluar_cada_horas"] * 3_600_000

    def reevaluar(self):
        n = int(self.cfg["dias_historico"] * velas_por_dia(self.cfg["timeframe"]))
        log.info("Evaluando estrategias con %d velas de histórico...", n)
        df = descargar_velas(self.ex, self.cfg["par"], self.cfg["timeframe"], n)
        ranking = evaluar(df, self.cfg)
        anterior = self.estado.get("estrategia")
        elegida = decidir(ranking, anterior, self.cfg["margen_cambio"])
        self.estado["ranking"] = ranking
        self.estado["estrategia"] = (
            {"estrategia": elegida["estrategia"], "params": elegida["params"]} if elegida else None
        )
        self.estado["ultima_evaluacion"] = self.ex.milliseconds()

        def nombre(e):
            return f"{NOMBRES[e['estrategia']]} {e['params']}" if e else "ninguna (quedarse en euros)"

        if anterior != self.estado["estrategia"]:
            avisar(self.cfg, f"Cambio de estrategia: {nombre(anterior)} -> {nombre(self.estado['estrategia'])}")
        else:
            log.info("Se mantiene la estrategia: %s", nombre(anterior))

    # --- un ciclo (una vela) -----------------------------------------------
    def ciclo(self):
        ahora_ms = self.ex.milliseconds()
        if self.toca_reevaluar(ahora_ms):
            self.reevaluar()

        df = descargar_velas(self.ex, self.cfg["par"], self.cfg["timeframe"], VELAS_CALENTAMIENTO)
        precio = self.broker.precio_actual(float(df["close"].iloc[-1]))
        quote, base = self.broker.saldos()
        valor = quote + base * precio

        if "capital_inicial" not in self.estado:
            self.estado["capital_inicial"] = valor
            self.estado["precio_inicio"] = precio
            if valor < 1:
                raise RuntimeError("No hay saldo con el que operar.")

        hoy = datetime.fromtimestamp(ahora_ms / 1000, tz=timezone.utc).date().isoformat()
        motivo_riesgo = None if self.estado.get("detenido") else riesgo.revisar(self.estado, valor, self.cfg, hoy)

        activa = self.estado.get("estrategia")
        if self.estado.get("detenido"):
            objetivo, motivo = 0.0, "límite de pérdida total"
        elif motivo_riesgo == "diario":
            objetivo, motivo = 0.0, "límite de pérdida diaria"
        elif activa is None:
            objetivo, motivo = 0.0, "sin estrategia válida"
        else:
            objetivo = float(senal(activa["estrategia"], activa["params"], df).iloc[-1])
            motivo = NOMBRES[activa["estrategia"]]

        operacion = None
        if objetivo >= 0.5:
            operacion = self.broker.comprar_todo(precio)
        else:
            operacion = self.broker.vender_todo(precio)

        if operacion:
            operacion.update(ts=ahora_ms, motivo=motivo)
            self.estado.setdefault("operaciones", []).append(operacion)
            self.estado["operaciones"] = self.estado["operaciones"][-MAX_OPERACIONES:]
            quote, base = self.broker.saldos()
            valor = quote + base * precio
            avisar(self.cfg, f"{operacion['lado'].upper()} {operacion['cantidad']:.6f} a {operacion['precio']:,.2f} "
                             f"({motivo}). Valor: {valor:,.2f}")

        if motivo_riesgo == "total" and not self.estado.get("aviso_detenido"):
            self.estado["aviso_detenido"] = True
            avisar(self.cfg, f"LÍMITE DE PÉRDIDA TOTAL alcanzado (valor {valor:,.2f}). El bot se ha detenido "
                             f"y está en euros. Revisa qué ha pasado antes de reiniciarlo.")
        elif motivo_riesgo == "diario" and operacion:
            avisar(self.cfg, "Límite de pérdida diaria alcanzado: en euros hasta mañana.")

        self.estado["saldos"] = [quote, base]
        self.estado.setdefault("historial", []).append([ahora_ms, valor, precio])
        self.estado["historial"] = self.estado["historial"][-MAX_HISTORIAL:]
        self.guardar()
        generar_panel(self.ruta_panel, self.estado, self.cfg, valor, precio)
        log.info("Precio %.2f | valor %.2f (%+.2f %%) | objetivo %s | %s",
                 precio, valor, (valor / self.estado["capital_inicial"] - 1) * 100,
                 "invertido" if objetivo >= 0.5 else "en euros", motivo)

    # --- bucle infinito ------------------------------------------------------
    def bucle(self, tras_primer_ciclo=None):
        import ccxt

        paso = tf_ms(self.cfg["timeframe"])
        while True:
            espera_error = None
            try:
                self.ciclo()
                if tras_primer_ciclo:
                    tras_primer_ciclo()
                    tras_primer_ciclo = None
            except ccxt.NetworkError as e:
                log.warning("Problema de conexión (%s). Reintento en 1 minuto.", e)
                espera_error = 60
            except ccxt.AuthenticationError as e:
                avisar(self.cfg, f"Error de autenticación con el exchange: {e}. Revisa claves.json.")
                raise
            except Exception as e:
                log.exception("Error inesperado")
                avisar(self.cfg, f"Error inesperado: {e}. Reintento en 5 minutos.")
                espera_error = 300

            if espera_error:
                time.sleep(espera_error)
                continue
            # Esperar al cierre de la siguiente vela (+20 s para que el exchange la publique).
            ahora = time.time() * 1000
            siguiente = (math.floor(ahora / paso) + 1) * paso + 20_000
            while time.time() * 1000 < siguiente:
                time.sleep(min(60, max(1, (siguiente - time.time() * 1000) / 1000)))
