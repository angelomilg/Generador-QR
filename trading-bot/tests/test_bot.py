import numpy as np
import pandas as pd
import pytest

from bot.backtest import backtest
from bot.broker import BrokerSimulado
from bot.config import POR_DEFECTO
from bot.datos import descargar_velas
from bot.estrategias import ESTRATEGIAS, combinaciones, senal
from bot.motor import Bot
from bot.riesgo import revisar
from bot.selector import decidir, evaluar

HORA = 3_600_000


class ExchangeFalso:
    """Imita la parte de ccxt que usa el bot, con un paseo aleatorio de precios."""

    def __init__(self, n=6000, tendencia=0.0002, semilla=1, ahora=1_700_000_000_000 + 30 * 60_000):
        rng = np.random.default_rng(semilla)
        self.ahora = ahora
        inicio = (ahora // HORA - n) * HORA
        self.ts = inicio + np.arange(n + 1) * HORA  # la última vela está aún abierta
        cierre = 30_000 * np.exp(np.cumsum(rng.normal(tendencia, 0.01, n + 1)))
        self.velas = [[int(t), c, c * 1.005, c * 0.995, c, 1.0] for t, c in zip(self.ts, cierre)]

    def milliseconds(self):
        return self.ahora

    def fetch_ohlcv(self, par, tf, since=None, limit=1000):
        return [v for v in self.velas if v[0] >= since][:limit]


def cfg(**cambios):
    c = dict(POR_DEFECTO, abrir_panel_al_iniciar=False, evitar_suspension=False)
    c.update(cambios)
    return c


def test_descarga_pagina_y_quita_vela_abierta():
    ex = ExchangeFalso()
    df = descargar_velas(ex, "BTC/EUR", "1h", 2500)
    assert len(df) == 2500
    assert df["ts"].iloc[-1] + HORA <= ex.ahora
    assert df["ts"].diff().dropna().eq(HORA).all()


def test_backtest_mantener_y_costes():
    close = pd.Series([100.0, 110.0, 121.0])
    m = backtest(close, pd.Series([1.0, 1.0, 1.0]), coste=0.0, velas_por_anio=8760)
    # La posición decidida en la vela 0 se aplica desde la vela 1.
    assert m["retorno"] == pytest.approx(0.21)
    m2 = backtest(close, pd.Series([1.0, 1.0, 1.0]), coste=0.01, velas_por_anio=8760)
    assert m2["retorno"] < m["retorno"]
    assert m2["operaciones"] == 1


def test_backtest_no_mira_al_futuro():
    # Una estrategia que "sabe" que la siguiente vela sube solo lo aprovecharía mirando al futuro.
    close = pd.Series([100.0, 50.0, 100.0, 50.0, 100.0])
    trampa = pd.Series([0.0, 0.0, 1.0, 0.0, 1.0])  # marca justo las velas que suben
    m = backtest(close, trampa, coste=0.0, velas_por_anio=8760)
    assert m["retorno"] <= 0


def test_estrategias_devuelven_0_o_1():
    df = descargar_velas(ExchangeFalso(), "BTC/EUR", "1h", 1000)
    for nombre in ESTRATEGIAS:
        for p in combinaciones(nombre):
            s = senal(nombre, p, df)
            assert len(s) == len(df)
            assert set(s.unique()) <= {0.0, 1.0}


def test_selector_en_tendencia_bajista_no_compra_a_ciegas():
    ex = ExchangeFalso(tendencia=-0.0006, semilla=3)
    df = descargar_velas(ex, "BTC/EUR", "1h", 4320)
    ranking = evaluar(df, cfg())
    mantener = next(r for r in ranking if r["estrategia"] == "mantener")
    assert not mantener["valida"]
    elegida = decidir(ranking, None, 0.25)
    assert elegida is None or elegida["estrategia"] != "mantener"


def test_decidir_tiene_histeresis():
    def r(nombre, sharpe):
        return {"estrategia": nombre, "params": {}, "validacion": {"sharpe": sharpe}, "valida": True}

    ranking = [r("ruptura", 1.2), r("bollinger", 1.1)]
    assert decidir(ranking, {"estrategia": "bollinger"}, 0.25)["estrategia"] == "bollinger"
    ranking = [r("ruptura", 2.0), r("bollinger", 1.1)]
    assert decidir(ranking, {"estrategia": "bollinger"}, 0.25)["estrategia"] == "ruptura"
    assert decidir([dict(r("x", -1), valida=False)], None, 0.25) is None


def test_broker_simulado_cobra_costes():
    estado = {}
    b = BrokerSimulado(estado, cfg())
    b.comprar_todo(100.0)
    b.vender_todo(100.0)
    quote, base = b.saldos()
    assert base == 0
    assert 99.6 < quote < 99.8  # 2 comisiones de 0,1 % + 2 deslizamientos de 0,05 %
    assert b.vender_todo(100.0) is None


def test_limites_de_riesgo():
    c = cfg()
    e = {"capital_inicial": 100.0}
    assert revisar(e, 100.0, c, "2026-01-01") is None
    assert revisar(e, 94.0, c, "2026-01-01") == "diario"
    assert revisar(e, 99.0, c, "2026-01-01") == "diario"  # sigue en pausa ese día
    assert revisar(e, 99.0, c, "2026-01-02") is None
    assert revisar(e, 79.0, c, "2026-01-03") == "total"
    assert e["detenido"]


def test_ciclos_completos_en_simulacion(tmp_path):
    ex = ExchangeFalso(tendencia=0.0004, semilla=7)
    bot = Bot(cfg(), ex, tmp_path)
    for _ in range(30):
        bot.ciclo()
        ex.ahora += HORA
        ex.velas.append([ex.velas[-1][0] + HORA] + ex.velas[-1][1:])
    e = bot.estado
    assert e["capital_inicial"] == 100.0
    assert len(e["historial"]) == 30
    assert e["ranking"]
    assert (tmp_path / "panel.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    # El estado se recupera tras reiniciar.
    bot2 = Bot(cfg(), ex, tmp_path)
    assert bot2.estado["historial"] == e["historial"]
    assert bot2.broker.saldos() == bot.broker.saldos()
