"""Elección automática de estrategia (walk-forward).

1. Se divide el histórico en dos tramos: entrenamiento y validación.
2. En el tramo de entrenamiento se busca la mejor configuración de cada estrategia.
3. Esa configuración se prueba en el tramo de validación, que no ha visto.
4. Solo se aceptan estrategias que ganen dinero y tengan Sharpe positivo en validación.
5. Si ninguna lo consigue, el bot se queda en liquidez (euros).
"""

from .backtest import backtest
from .datos import velas_por_dia
from .estrategias import ESTRATEGIAS, combinaciones, senal

MIN_OPERACIONES_ENTRENO = 4


def evaluar(df, cfg):
    vpd = velas_por_dia(cfg["timeframe"])
    n_val = min(int(cfg["dias_validacion"] * vpd), len(df) // 3)
    if n_val < 50:
        raise ValueError(f"Histórico insuficiente para evaluar ({len(df)} velas)")
    corte = len(df) - n_val
    coste = cfg["comision"] + cfg["deslizamiento"]
    vpa = vpd * 365
    close = df["close"]

    ranking = []
    for nombre in ESTRATEGIAS:
        mejor = None
        for params in combinaciones(nombre):
            pos = senal(nombre, params, df)
            m = backtest(close.iloc[:corte], pos.iloc[:corte], coste, vpa)
            if nombre != "mantener" and m["operaciones"] < MIN_OPERACIONES_ENTRENO:
                continue
            if mejor is None or m["sharpe"] > mejor[2]["sharpe"]:
                mejor = (params, pos, m)
        if mejor is None:
            continue
        params, pos, m_ent = mejor
        m_val = backtest(close.iloc[corte:], pos.iloc[corte:], coste, vpa)
        ranking.append({
            "estrategia": nombre,
            "params": params,
            "entreno": m_ent,
            "validacion": m_val,
            "valida": m_val["retorno"] > 0 and m_val["sharpe"] > 0,
        })
    ranking.sort(key=lambda r: r["validacion"]["sharpe"], reverse=True)
    return ranking


def decidir(ranking, actual, margen):
    """Devuelve la estrategia a usar (o None = quedarse en euros).

    Para no cambiar de estrategia por ruido, la actual se mantiene mientras
    siga siendo válida y la mejor no la supere por más de `margen` de Sharpe.
    """
    validas = [r for r in ranking if r["valida"]]
    if not validas:
        return None
    mejor = validas[0]
    if actual:
        for r in validas:
            if r["estrategia"] == actual["estrategia"]:
                if mejor["validacion"]["sharpe"] < r["validacion"]["sharpe"] + margen:
                    return r
                break
    return mejor
