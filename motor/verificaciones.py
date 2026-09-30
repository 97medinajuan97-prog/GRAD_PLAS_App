# -*- coding: utf-8 -*-
"""11 verificaciones automáticas (mismas del formato validado).

Cada elemento es (nº, etiqueta, ok|None, mensaje). `ok` es True/False según
el resultado, o None cuando el ensayo no tiene datos suficientes para
evaluarlo: un `None` nunca debe presentarse como conforme.
"""


def verificaciones(data, res, g):
    """Devuelve lista de tuplas (nº, etiqueta, ok|None, mensaje)."""
    chk = []
    total = res.get("g_total")
    total_ret = g["sum_ret"] + g["fondo"] if g["fondo"] is not None else g["sum_ret"]
    chk.append((1, "Σ pesos ret. vs total declarado",
                None if total is None else abs(total_ret - total) <= 0.5,
                "Diferencia > 0.5 g" if (total is not None and abs(total_ret - total) > 0.5) else None))

    sieve = res["sieve"]
    pasas = [s["pasa"] for s in sieve]
    evaluable = any(p is not None for p in pasas)
    inc = next((i for i in range(len(pasas) - 1)
                if pasas[i] is not None and pasas[i + 1] is not None and pasas[i + 1] > pasas[i] + 0.1), None)
    chk.append((2, "%Pasa decreciente (sin aumentos)", None if not evaluable else inc is None,
                "Hay aumentos en %%Pasa (tamiz %s)" % sieve[inc + 1]["tamiz"] if inc is not None else None))

    chk.append((3, "LL ≥ LP (IP ≥ 0)",
                None if (res["LL"] is None or res["LP"] is None) else res["LL"] >= res["LP"],
                "LL < LP" if (res["LL"] is not None and res["LP"] is not None and res["LL"] < res["LP"]) else None))

    chk.append((4, "LL en rango [0,150] %",
                None if res["LL"] is None else 0 <= res["LL"] <= 150,
                "LL fuera de rango" if (res["LL"] is not None and not 0 <= res["LL"] <= 150) else None))

    chk.append((5, "w natural en rango [0,100] %",
                None if res["w_nat"] is None else 0 <= res["w_nat"] <= 100,
                "w fuera de rango" if (res["w_nat"] is not None and not 0 <= res["w_nat"] <= 100) else None))

    # Sin golpes ingresados el ensayo no se ha hecho: `all([])` daría True y
    # la app reportaría "OK" sobre una lista vacía. Sin datos -> None.
    golpes = [r["n"] for r in data["ll"] if r["n"] is not None]
    ok6 = None if not golpes else all(5 <= g0 <= 75 for g0 in golpes)
    chk.append((6, "N° golpes de LL entre 5 y 75", ok6,
                "Golpes fuera de rango" if ok6 is False else None))

    if res["D10"] is not None and res["D30"] is not None and res["D60"] is not None:
        ok7 = res["D10"] <= res["D30"] <= res["D60"]
        chk.append((7, "Orden D10 ≤ D30 ≤ D60", ok7,
                    "No se cumple D60≥D30≥D10" if not ok7 else None))
    else:
        chk.append((7, "Orden D10 ≤ D30 ≤ D60", None, None))

    if res["Cu"] is not None:
        chk.append((8, "Cu ≥ 1", res["Cu"] >= 1, "Cu < 1" if res["Cu"] < 1 else None))
    else:
        chk.append((8, "Cu ≥ 1", None, None))

    F200 = g["f200"]
    # Que el D10 sea o no interpolable depende del suelo, no de un error en
    # la captura: en un suelo fino el % que pasa el N°200 es alto por
    # definición y el D10 simplemente no existe. Marcarlo como "falló"
    # reprobaría un ensayo correcto, así que sin D10 no hay nada que
    # verificar y el estado es None.
    if F200 is not None and res["D10"] is not None:
        chk.append((9, "D10 obtenido por interpolación", True, None))
    else:
        chk.append((9, "D10 obtenido por interpolación", None,
                    "%Pasa N°200 ≥ 10% → el D10 no es interpolable"
                    if F200 is not None else None))

    pesos = [w for w in data["grano"]["pesos"] if w is not None]
    neg = [w for w in pesos if w < 0]
    chk.append((10, "Sin pesos negativos", None if not pesos else not neg,
                "Hay pesos negativos" if neg else None))

    # IP = 0 (LL == LP) deja IL e IC sin definición: no es un error de
    # captura, pero conviene que quede visible en lugar de un guion mudo.
    chk.append((11, "IP > 0 para definir IL e IC",
                True if res.get("ip_cero") else (None if res.get("IP") is None else res["IP"] > 0),
                "IP = 0 → IL e IC no definidos" if res.get("ip_cero") else None))
    return chk
