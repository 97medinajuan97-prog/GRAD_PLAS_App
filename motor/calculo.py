# -*- coding: utf-8 -*-
"""
Motor de cálculo: orquesta las secciones independientes.

`calcular(data)` reúne los datos de cada sección, obtiene su resultado de la
función de cálculo de esa sección y compone el resultado final (mismas claves
que el formato validado) + clasificación y verificaciones.
"""
import math


def fnum(s):
    """Convierte a float (mismo comportamiento que Excel: vacío = None)."""
    if s is None:
        return None
    t = str(s).strip().replace(",", ".")
    if t == "":
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _w(recip, hum, seco):
    """w% = (húmedo − seco) / (seco − recipiente) × 100."""
    if recip is None or hum is None or seco is None:
        return None
    if seco - recip <= 0:
        return None
    return (hum - seco) / (seco - recip) * 100


def fstr(v, dec=2):
    return "" if v is None else ("%.*f" % (dec, v))


def calcular(data):
    """Calcula todos los resultados. `data` tiene las claves:
    hum, ll, lp, grano (misma forma que `datos_ejemplo`)."""
    from secciones.humedad import calcular_humedad
    from secciones.limite_liquido import calcular_ll
    from secciones.limite_plastico import calcular_lp
    from secciones.granulometria import calcular_granulometria
    from motor.clasificacion import clasificar, grupo_aashto, indice_grupo
    from motor.verificaciones import verificaciones

    res = {}

    # ---- 1 · humedad natural: W seco se ingresa aquí y es el total de grano --
    hum = data["hum"]
    hu = calcular_humedad(hum)
    res["w_nat"] = hu["w"]
    res["w_agua"] = hu["w_agua"]
    res["w_suelo"] = hu["w_suelo"]
    res["w_seco_usado"] = hu["seco_usado"]

    # ---- 2.1 · limite liquido ----
    res["ll_np"] = bool(data.get("ll_np"))
    if res["ll_np"]:
        res["ll_w"] = [None, None, None]
        res["LL"] = None
    else:
        ll = calcular_ll(data["ll"])
        res["ll_w"] = (ll["w"] + [None] * 3)[:3]
        res["LL"] = ll["LL"]

    # ---- 2.2 · limite plastico ----
    lp = calcular_lp(data["lp"])
    res["lp_w"] = (lp["w"] + [None] * 2)[:2]
    res["LP"] = lp["LP"]
    if res["ll_np"]:
        res["lp_w"] = [None, None]
        res["LP"] = None
        res["IP"] = None
    else:
        res["IP"] = (res["LL"] - res["LP"]) if (res["LL"] is not None and res["LP"] is not None) else None

    # ---- índices de liquidez (IL) y consistencia (IC) según w natural ----
    IL = IC = None
    if (res["LL"] is not None and res["LP"] is not None
            and res["w_nat"] is not None and res["IP"]):
        IL = (res["w_nat"] - res["LP"]) / res["IP"]
        IC = (res["LL"] - res["w_nat"]) / res["IP"]
    res["IL"] = IL
    res["IC"] = IC

    # ---- 3 · granulometría: el total es el peso seco del suelo (Ws) ----
    # (tomado de la humedad natural: Ws = W2 − Wc, sin contenedor)
    w_suelo = hu["w_suelo"]
    g_total = w_suelo if (w_suelo is not None and w_suelo > 0) else None
    res["g_total"] = g_total
    g = calcular_granulometria({"total": g_total, "pesos": data["grano"]["pesos"]})
    res["fondo"] = g["fondo"]
    res["sum_ret"] = g["sum_ret"]
    res["sieve"] = g["sieve"]
    res["D60"] = g["d60"]
    res["D30"] = g["d30"]
    res["D10"] = g["d10"]
    res["Cu"] = g["cu"]
    res["Cc"] = g["cc"]
    res["g_grava"] = g["grava"]
    res["g_arena"] = g["arena"]
    res["g_finos"] = g["finos"]
    res["tipo"] = g["tipo"]

    # ---- clasificación ----
    Fn = g["f200"]
    LL2, PI2 = res["LL"], res["IP"]
    sucs, sucs_desc = clasificar(Fn, g["grava"], g["arena"], g["cu"], g["cc"],
                                 LL2, PI2, np_=res["ll_np"])
    res["sucs"] = sucs
    res["sucs_desc"] = sucs_desc
    gpo = grupo_aashto(g["f10"], g["f40"], Fn, LL2, PI2) if Fn is not None else None
    res["grupo_aashto"] = gpo
    res["ig"] = indice_grupo(Fn, LL2, PI2) if (Fn is not None and LL2 is not None and PI2 is not None) else None
    res["aashto"] = ("%s (%d)" % (gpo, res["ig"])) if (gpo and res["ig"] is not None) else (gpo or None)
    res["aashto_desc"] = None
    if gpo:
        from motor.clasificacion import DESC_AASHTO
        res["aashto_desc"] = DESC_AASHTO.get(gpo[:3])

    # ---- verificaciones ----
    res["checks"] = verificaciones(data, res, g)
    return res