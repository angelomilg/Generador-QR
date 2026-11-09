"""Genera el panel (estado/panel.html) que puedes abrir en el navegador."""

import html
from datetime import datetime, timezone

NOMBRES = {
    "mantener": "Comprar y mantener",
    "cruce_medias": "Cruce de medias",
    "rsi_reversion": "Reversión RSI",
    "bollinger": "Bandas de Bollinger",
    "ruptura": "Ruptura de canal",
}


def _e(x):
    return html.escape(str(x))


def _pct(x):
    return f"{x * 100:+.2f} %"


def _fecha(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone().strftime("%d/%m %H:%M")


def _grafico(historial, capital):
    if len(historial) < 2:
        return "<p class='nota'>El gráfico aparecerá cuando haya algo más de historial.</p>"
    ancho, alto, m = 800, 220, 8
    valores = [h[1] for h in historial]
    precio0 = historial[0][2]
    referencia = [capital * h[2] / precio0 for h in historial]
    lo = min(valores + referencia)
    hi = max(valores + referencia)
    if hi - lo < 1e-9:
        hi = lo + 1

    def linea(serie):
        n = len(serie) - 1
        pts = (
            f"{m + i * (ancho - 2 * m) / n:.1f},{alto - m - (v - lo) / (hi - lo) * (alto - 2 * m):.1f}"
            for i, v in enumerate(serie)
        )
        return " ".join(pts)

    return f"""
<svg viewBox="0 0 {ancho} {alto}" class="grafico" role="img" aria-label="Evolución del valor">
  <polyline points="{linea(referencia)}" class="ref"/>
  <polyline points="{linea(valores)}" class="bot"/>
</svg>
<p class="leyenda"><span class="c-bot"></span> Bot &nbsp; <span class="c-ref"></span> Si solo hubieras comprado y mantenido</p>"""


def generar_panel(ruta, estado, cfg, valor, precio):
    capital = estado["capital_inicial"]
    referencia = capital * precio / estado["precio_inicio"]
    activa = estado.get("estrategia")
    if estado.get("detenido"):
        situacion = "DETENIDO por el límite de pérdidas"
    elif estado.get("pausado_hoy"):
        situacion = "En pausa hasta mañana (límite diario)"
    else:
        situacion = "Funcionando"

    filas_ops = "".join(
        f"<tr><td>{_fecha(o['ts'])}</td><td>{_e(o['lado'])}</td><td>{o['precio']:,.2f}</td>"
        f"<td>{o['cantidad']:.6f}</td><td>{o['importe']:,.2f}</td><td>{_e(o.get('motivo', ''))}</td></tr>"
        for o in reversed(estado.get("operaciones", [])[-25:])
    ) or "<tr><td colspan='6' class='nota'>Todavía no hay operaciones.</td></tr>"

    filas_rank = "".join(
        f"<tr{' class=activa' if activa and r['estrategia'] == activa['estrategia'] else ''}>"
        f"<td>{_e(NOMBRES.get(r['estrategia'], r['estrategia']))}</td>"
        f"<td><code>{_e(r['params'])}</code></td>"
        f"<td>{_pct(r['validacion']['retorno'])}</td><td>{r['validacion']['sharpe']:.2f}</td>"
        f"<td>{_pct(r['validacion']['max_caida'])}</td><td>{r['validacion']['operaciones']}</td>"
        f"<td>{'sí' if r['valida'] else 'no'}</td></tr>"
        for r in estado.get("ranking", [])
    ) or "<tr><td colspan='7' class='nota'>Aún no se ha evaluado.</td></tr>"

    nombre_activa = NOMBRES.get(activa["estrategia"], activa["estrategia"]) if activa else "Ninguna (en euros)"
    ultima_eval = _fecha(estado["ultima_evaluacion"]) if estado.get("ultima_evaluacion") else "-"
    quote, base = estado.get("saldos", (0, 0))
    moneda_base, moneda_quote = cfg["par"].split("/")

    contenido = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Panel del bot</title>
<style>
:root {{ --fondo:#f7f7f5; --tarjeta:#fff; --texto:#1d1d1b; --suave:#6b6b66; --borde:#e3e3de;
  --bot:#2f6fdb; --ref:#a3a39c; --bien:#1f8a4c; --mal:#c23b30; --resalte:#eef3fd; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fondo:#151514; --tarjeta:#1f1f1d; --texto:#ecece8;
  --suave:#a0a09a; --borde:#33332f; --bot:#6d9cf0; --ref:#6b6b66; --bien:#4cc27d; --mal:#ef6b5f; --resalte:#1e2a40; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--fondo); color:var(--texto); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px 48px }}
h1 {{ font-size:22px; margin:0 0 4px }} h2 {{ font-size:16px; margin:32px 0 10px }}
.sub,.nota,.leyenda {{ color:var(--suave); font-size:13px }}
.tarjetas {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-top:20px }}
.t {{ background:var(--tarjeta); border:1px solid var(--borde); border-radius:10px; padding:12px 14px }}
.t b {{ display:block; font-size:20px; font-variant-numeric:tabular-nums }} .t span {{ color:var(--suave); font-size:13px }}
.pos {{ color:var(--bien) }} .neg {{ color:var(--mal) }}
.caja {{ background:var(--tarjeta); border:1px solid var(--borde); border-radius:10px; padding:12px; overflow-x:auto }}
.grafico {{ width:100%; height:auto; display:block }}
.grafico polyline {{ fill:none; stroke-width:2; vector-effect:non-scaling-stroke }}
.grafico .bot {{ stroke:var(--bot) }} .grafico .ref {{ stroke:var(--ref); stroke-dasharray:4 4 }}
.leyenda span {{ display:inline-block; width:14px; height:3px; vertical-align:middle }}
.c-bot {{ background:var(--bot) }} .c-ref {{ background:var(--ref) }}
table {{ width:100%; border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums }}
th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--borde); white-space:nowrap }}
th {{ color:var(--suave); font-weight:600 }} tr.activa {{ background:var(--resalte) }}
</style></head><body><main>
<h1>Panel del bot · {_e(cfg['par'])}</h1>
<div class="sub">Modo: <b>{'SIMULACIÓN (dinero ficticio)' if cfg['modo'] == 'simulacion' else 'REAL'}</b> ·
Exchange: {_e(cfg['exchange'])} · Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · Se recarga solo cada minuto</div>

<div class="tarjetas">
  <div class="t"><span>Valor actual</span><b>{valor:,.2f} {_e(moneda_quote)}</b></div>
  <div class="t"><span>Resultado del bot</span><b class="{'pos' if valor >= capital else 'neg'}">{_pct(valor / capital - 1)}</b></div>
  <div class="t"><span>Comprar y mantener</span><b class="{'pos' if referencia >= capital else 'neg'}">{_pct(referencia / capital - 1)}</b></div>
  <div class="t"><span>Estado</span><b style="font-size:15px">{_e(situacion)}</b></div>
  <div class="t"><span>Estrategia activa</span><b style="font-size:15px">{_e(nombre_activa)}</b></div>
  <div class="t"><span>Saldos</span><b style="font-size:15px">{quote:,.2f} {_e(moneda_quote)} · {base:.6f} {_e(moneda_base)}</b></div>
</div>

<h2>Evolución</h2>
<div class="caja">{_grafico(estado.get('historial', []), capital)}</div>

<h2>Últimas operaciones</h2>
<div class="caja"><table><tr><th>Fecha</th><th>Tipo</th><th>Precio</th><th>Cantidad</th><th>Importe</th><th>Motivo</th></tr>{filas_ops}</table></div>

<h2>Última evaluación de estrategias ({ultima_eval})</h2>
<p class="nota">Resultados en el tramo de validación: los últimos {cfg['dias_validacion']} días, que la estrategia no vio al ajustarse.
Solo se usan las marcadas como válidas (ganan dinero y tienen Sharpe positivo). Se reevalúa cada {cfg['reevaluar_cada_horas']} horas.</p>
<div class="caja"><table><tr><th>Estrategia</th><th>Parámetros</th><th>Retorno</th><th>Sharpe</th><th>Caída máx.</th><th>Operaciones</th><th>Válida</th></tr>{filas_rank}</table></div>
</main></body></html>"""
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(contenido, encoding="utf-8")
    tmp.replace(ruta)
