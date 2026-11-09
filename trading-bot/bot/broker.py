"""Ejecución de órdenes: simulada (dinero ficticio) o real (exchange)."""

import logging

log = logging.getLogger("bot")


class BrokerSimulado:
    """Lleva un saldo ficticio y aplica comisión y deslizamiento a cada operación."""

    def __init__(self, estado, cfg):
        self.cfg = cfg
        if "simulado" not in estado:
            estado["simulado"] = {"quote": float(cfg["capital_inicial"]), "base": 0.0}
        self.s = estado["simulado"]

    def saldos(self):
        return self.s["quote"], self.s["base"]

    def precio_actual(self, precio_cierre):
        return precio_cierre

    def comprar_todo(self, precio):
        importe = self.s["quote"]
        if importe < 1:
            return None
        precio_ej = precio * (1 + self.cfg["deslizamiento"])
        cantidad = importe * (1 - self.cfg["comision"]) / precio_ej
        self.s["quote"] = 0.0
        self.s["base"] += cantidad
        return {"lado": "compra", "precio": precio_ej, "cantidad": cantidad, "importe": importe}

    def vender_todo(self, precio):
        cantidad = self.s["base"]
        if cantidad * precio < 1:
            return None
        precio_ej = precio * (1 - self.cfg["deslizamiento"])
        importe = cantidad * precio_ej * (1 - self.cfg["comision"])
        self.s["base"] = 0.0
        self.s["quote"] += importe
        return {"lado": "venta", "precio": precio_ej, "cantidad": cantidad, "importe": importe}


class BrokerReal:
    """Opera de verdad en el exchange con órdenes a mercado (solo contado)."""

    MARGEN_COMPRA = 0.99  # deja un 1 % libre para comisiones y movimientos de precio

    def __init__(self, ex, par):
        self.ex = ex
        self.par = par
        self.base, self.quote = par.split("/")
        self._mercado = None

    @property
    def mercado(self):
        if self._mercado is None:  # se carga al usarlo, así un corte de red al arrancar no tumba el bot
            self.ex.load_markets()
            self._mercado = self.ex.market(self.par)
        return self._mercado

    def saldos(self):
        b = self.ex.fetch_balance()
        quote = float((b.get(self.quote) or {}).get("free") or 0)
        base = float((b.get(self.base) or {}).get("free") or 0)
        return quote, base

    def precio_actual(self, precio_cierre):
        try:
            t = self.ex.fetch_ticker(self.par)
            return float(t.get("last") or precio_cierre)
        except Exception:
            return precio_cierre

    def _minimo(self, precio):
        lim = self.mercado.get("limits") or {}
        min_coste = (lim.get("cost") or {}).get("min") or 0
        min_cant = (lim.get("amount") or {}).get("min") or 0
        return max(float(min_coste), float(min_cant) * precio, 1.0)

    def _resumen(self, lado, orden, precio, cantidad):
        precio_ej = float(orden.get("average") or orden.get("price") or precio)
        cant = float(orden.get("filled") or cantidad)
        return {"lado": lado, "precio": precio_ej, "cantidad": cant, "importe": precio_ej * cant,
                "id_orden": orden.get("id")}

    def comprar_todo(self, precio):
        quote, _ = self.saldos()
        gasto = quote * self.MARGEN_COMPRA
        if gasto < self._minimo(precio):
            return None
        cantidad = float(self.ex.amount_to_precision(self.par, gasto / precio))
        log.info("Orden REAL de compra: %s %s", cantidad, self.par)
        orden = self.ex.create_order(self.par, "market", "buy", cantidad)
        return self._resumen("compra", orden, precio, cantidad)

    def vender_todo(self, precio):
        _, base = self.saldos()
        if base * precio < self._minimo(precio):
            return None
        cantidad = float(self.ex.amount_to_precision(self.par, base))
        log.info("Orden REAL de venta: %s %s", cantidad, self.par)
        orden = self.ex.create_order(self.par, "market", "sell", cantidad)
        return self._resumen("venta", orden, precio, cantidad)
