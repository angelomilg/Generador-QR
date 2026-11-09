"""Simulación de una estrategia sobre datos pasados, con costes incluidos."""

import numpy as np


def backtest(close, posicion, coste, velas_por_anio):
    """Mide cómo habría ido una serie de posiciones.

    La posición decidida al cierre de la vela t se aplica a la variación de
    precio de la vela t+1 (de ahí el shift), así nunca se usa información
    que no se tenía en el momento de decidir.
    `coste` es la comisión + deslizamiento por operación (p. ej. 0.0015).
    """
    rend = close.pct_change().fillna(0.0)
    p = posicion.shift(1).fillna(0.0)
    cambios = p.diff().abs()
    cambios.iloc[0] = p.iloc[0]
    neto = p * rend - cambios * coste
    curva = (1 + neto).cumprod()
    std = neto.std()
    return {
        "retorno": float(curva.iloc[-1] - 1),
        "max_caida": float((curva / curva.cummax() - 1).min()),
        "sharpe": float(neto.mean() / std * np.sqrt(velas_por_anio)) if std > 0 else 0.0,
        "operaciones": int((cambios > 0).sum()),
        "exposicion": float(p.mean()),
    }
