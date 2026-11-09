"""Descarga de velas (precios) del exchange."""

import pandas as pd

TF_MS = {
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def tf_ms(timeframe):
    if timeframe not in TF_MS:
        raise ValueError(f"timeframe no soportado: {timeframe}. Usa uno de {list(TF_MS)}")
    return TF_MS[timeframe]


def velas_por_dia(timeframe):
    return 86_400_000 / tf_ms(timeframe)


def crear_exchange(cfg, claves=None):
    import ccxt

    clase = getattr(ccxt, cfg["exchange"], None)
    if clase is None:
        raise ValueError(f"Exchange desconocido: {cfg['exchange']}")
    opciones = {"enableRateLimit": True}
    if claves:
        opciones["apiKey"] = claves["api_key"]
        opciones["secret"] = claves["api_secret"]
        if claves.get("password"):
            opciones["password"] = claves["password"]
    return clase(opciones)


def descargar_velas(ex, par, timeframe, n_velas):
    """Devuelve las últimas `n_velas` velas CERRADAS como DataFrame.

    La vela que aún está en curso se descarta para no decidir con datos
    que todavía pueden cambiar.
    """
    paso = tf_ms(timeframe)
    ahora = ex.milliseconds()
    desde = ahora - (n_velas + 2) * paso
    filas = []
    while desde < ahora:
        lote = ex.fetch_ohlcv(par, timeframe, since=desde, limit=1000)
        if not lote:
            break
        filas.extend(lote)
        siguiente = lote[-1][0] + paso
        if siguiente <= desde:
            break
        desde = siguiente

    if not filas:
        raise RuntimeError(f"El exchange no ha devuelto velas para {par}")
    df = pd.DataFrame(filas, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("ts").sort_values("ts")
    df = df[df["ts"] + paso <= ahora]
    df.index = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.tail(n_velas).astype({c: float for c in ["open", "high", "low", "close", "volume"]})
