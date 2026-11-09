"""Estrategias candidatas.

Cada estrategia recibe las velas y devuelve, para cada vela, la posición que
quiere tener tras su cierre: 1 = invertido, 0 = en liquidez (euros).
Solo compra al contado: sin apalancamiento ni posiciones cortas.
Todos los indicadores usan solo datos pasados (sin mirar al futuro).
"""

import itertools

import numpy as np
import pandas as pd


def _con_memoria(entrar, salir, index):
    """Entra cuando `entrar` es cierto y se queda dentro hasta que `salir` lo sea."""
    s = pd.Series(np.nan, index=index)
    s[salir.fillna(False).to_numpy()] = 0.0
    s[entrar.fillna(False).to_numpy()] = 1.0
    return s.ffill().fillna(0.0)


def _rsi(close, periodo):
    d = close.diff()
    subidas = d.clip(lower=0).ewm(alpha=1 / periodo, adjust=False).mean()
    bajadas = (-d.clip(upper=0)).ewm(alpha=1 / periodo, adjust=False).mean()
    rs = subidas / bajadas.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0)


def mantener(df):
    """Referencia: comprar y mantener."""
    return pd.Series(1.0, index=df.index)


def cruce_medias(df, rapida, lenta):
    """Tendencia: dentro mientras la media rápida esté por encima de la lenta."""
    c = df["close"]
    return (c.rolling(rapida).mean() > c.rolling(lenta).mean()).astype(float)


def rsi_reversion(df, periodo, bajo, alto):
    """Reversión: compra cuando el RSI está muy bajo y vende cuando se recupera."""
    rsi = _rsi(df["close"], periodo)
    return _con_memoria(rsi < bajo, rsi > alto, df.index)


def bollinger(df, ventana, k):
    """Reversión: compra bajo la banda inferior y vende al volver a la media."""
    c = df["close"]
    media = c.rolling(ventana).mean()
    desv = c.rolling(ventana).std()
    return _con_memoria(c < media - k * desv, c > media, df.index)


def ruptura(df, entrada, salida):
    """Tendencia (Donchian): compra al superar el máximo de N velas y vende al perder el mínimo de M."""
    c = df["close"]
    maximo = df["high"].rolling(entrada).max().shift(1)
    minimo = df["low"].rolling(salida).min().shift(1)
    return _con_memoria(c > maximo, c < minimo, df.index)


ESTRATEGIAS = {
    "mantener": (mantener, {}),
    "cruce_medias": (cruce_medias, {"rapida": [10, 20, 50], "lenta": [50, 100, 200]}),
    "rsi_reversion": (rsi_reversion, {"periodo": [7, 14], "bajo": [25, 30, 35], "alto": [55, 65, 75]}),
    "bollinger": (bollinger, {"ventana": [20, 50], "k": [1.5, 2.0, 2.5]}),
    "ruptura": (ruptura, {"entrada": [20, 55, 100], "salida": [10, 20, 50]}),
}

# Velas mínimas para que cualquier indicador esté "caliente".
VELAS_CALENTAMIENTO = 400


def combinaciones(nombre):
    _, rejilla = ESTRATEGIAS[nombre]
    claves = list(rejilla)
    for valores in itertools.product(*rejilla.values()):
        p = dict(zip(claves, valores))
        if nombre == "cruce_medias" and p["rapida"] >= p["lenta"]:
            continue
        if nombre == "ruptura" and p["salida"] >= p["entrada"]:
            continue
        yield p


def senal(nombre, params, df):
    return ESTRATEGIAS[nombre][0](df, **params)
