"""Límites de riesgo. Se comprueban antes de cada decisión y no se pueden saltar."""


def revisar(estado, valor, cfg, hoy):
    """Devuelve None si todo está bien, o el motivo por el que no se debe estar invertido.

    - "total": se ha perdido más de stop_total_pct del capital inicial. El bot se detiene.
    - "diario": se ha perdido más de stop_diario_pct hoy. Se queda en euros hasta mañana.
    """
    if estado.get("dia") != hoy:
        estado["dia"] = hoy
        estado["valor_inicio_dia"] = valor
        estado["pausado_hoy"] = False

    if valor <= estado["capital_inicial"] * (1 - cfg["stop_total_pct"]):
        estado["detenido"] = True
        return "total"
    if estado.get("pausado_hoy") or valor <= estado["valor_inicio_dia"] * (1 - cfg["stop_diario_pct"]):
        estado["pausado_hoy"] = True
        return "diario"
    return None
