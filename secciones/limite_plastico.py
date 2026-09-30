# -*- coding: utf-8 -*-
"""
Cálculo del límite plástico (INV E-126).

La interfaz de esta sección vive en `secciones/limites.py`, que agrupa LL y
LP en una sola tarjeta. Aquí queda solo la fórmula: el LP es el promedio de
las humedades de los ensayos. El IP (LL − LP) lo calcula el motor, porque
depende del LL y no de este módulo.
"""
from motor.calculo import _w


def calcular_lp(rows):
    """rows: [{recip, hum, seco}, ...]. Devuelve w% por ensayo y el LP."""
    ws = []
    ok = []
    for row in rows:
        w = _w(row["recip"], row["hum"], row["seco"])
        ws.append(w)
        if w is not None:
            ok.append(w)
    LP = (sum(ok) / len(ok)) if ok else None
    return {"w": ws, "LP": LP}


def aviso_incoherencia(rows):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    keys = ("recip", "hum", "seco")
    llenas = [r for r in rows if all(r[k] is not None for k in keys)]
    tiene = any(r[k] is not None for r in rows for k in keys)
    if not tiene:
        return "", ""
    if not llenas:
        return "⚠ Datos incompletos", "Complete Wc, W1 y W2 de cada ensayo."
    for i, r in enumerate(llenas, 1):
        if any(r[k] <= 0 for k in keys):
            return "⚠ Datos incoherentes", "Ensayo #%d: los valores deben ser mayores que cero." % i
        if r["hum"] <= r["seco"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W1 debe ser mayor que W2." % i
        if r["seco"] <= r["recip"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W2 debe ser mayor que Wc." % i
    return "", ""


