# -*- coding: utf-8 -*-
"""
Cálculo del límite líquido (INV E-125).

La interfaz de esta sección vive en `secciones/limites.py`, que agrupa LL y
LP en una sola tarjeta. Aquí queda solo la fórmula: cada ensayo aporta su
humedad y el LL se obtiene por la recta de flujo a N = 25 golpes.
"""
import math

from motor.calculo import _w


def calcular_ll(rows):
    """rows: [{n, recip, hum, seco}, ...]. Devuelve w% por ensayo y LL."""
    ws = []
    pts = []
    for row in rows:
        w = _w(row["recip"], row["hum"], row["seco"])
        ws.append(w)
        n = row["n"]
        if n and n > 0 and w is not None:
            pts.append((math.log(n), w))
    if len(pts) >= 2:
        n = len(pts)
        mx = sum(x for x, _ in pts) / n
        my = sum(y for _, y in pts) / n
        den = sum(x * x for x, _ in pts) - n * mx * mx
        if abs(den) > 1e-12:
            m = (sum(x * y for x, y in pts) - n * mx * my) / den
            b = my - m * mx
            LL = b + m * math.log(25)
        else:
            LL = None
    else:
        LL = None
    return {"w": ws, "LL": LL}


def aviso_incoherencia(rows):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    keys = ("recip", "hum", "seco")
    llenas = [r for r in rows if all(r[k] is not None for k in keys)]
    tiene = any(r[k] is not None for r in rows for k in keys)
    if not tiene:
        return "", ""
    if not llenas or any(r["n"] is None for r in llenas):
        return "⚠ Datos incompletos", "Complete golpes, Wc, W1 y W2 de cada ensayo."
    for i, r in enumerate(llenas, 1):
        if any(r[k] <= 0 for k in keys) or r["n"] <= 0:
            return "⚠ Datos incoherentes", "Ensayo #%d: los valores deben ser mayores que cero." % i
        if r["hum"] <= r["seco"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W1 debe ser mayor que W2." % i
        if r["seco"] <= r["recip"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W2 debe ser mayor que Wc." % i
    return "", ""


