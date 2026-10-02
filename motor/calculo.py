# -*- coding: utf-8 -*-
"""
Motor de cálculo: orquesta las secciones independientes.

`calcular(data)` reúne los datos de cada sección, obtiene su resultado de la
función de cálculo de esa sección y compone el resultado final (mismas claves
que el formato validado) + clasificación y verificaciones.
"""


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


def calcular(data):
    """Calcula todos los resultados. `data` tiene las claves:
    hum, ll, lp, grano (misma forma que `datos_ejemplo`)."""
    from secciones.humedad import calcular_humedad
    from secciones.limite_liquido import calcular_ll
    from secciones.limite_plastico import calcular_lp
    from secciones.granulometria import calcular_granulometria
    from motor.clasificacion import (clasificar, grupo_aashto, indice_grupo,
                                     aashto_faltantes)
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
    # IP = 0 (LL == LP) no es un dato ausente sino una división por cero:
    # IL e IC no están definidos. Se distingue del caso "sin datos" para no
    # perder el motivo, y `verificaciones` lo reporta.
    IL = IC = None
    res["ip_cero"] = False
    if (res["LL"] is not None and res["LP"] is not None
            and res["w_nat"] is not None and res["IP"] is not None):
        if res["IP"] == 0:
            res["ip_cero"] = True
        else:
            IL = (res["w_nat"] - res["LP"]) / res["IP"]
            IC = (res["LL"] - res["w_nat"]) / res["IP"]
    res["IL"] = IL
    res["IC"] = IC

    # ---- 3 · granulometría: el total es el peso seco del suelo (Ws) ----
    # (tomado de la humedad natural: Ws = W2 − Wc, sin contenedor)
    #
    # La serie de tamices depende del tipo de muestra: la de control de
    # calidad es más corta. Se lee del bloque `grano`, que es donde la interfaz
    # guarda los datos del ensayo.
    from secciones.granulometria import serie_para
    grano = data["grano"]
    serie = serie_para(grano.get("tipo"), grano.get("alcance"))
    res["serie"] = [t for t, _ in serie]
    w_suelo = hu["w_suelo"]
    # El total de la granulometria es el W1 de su propia tabla, que viene
    # puesto con el peso del suelo de la humedad natural pero se puede cambiar:
    # hay ensayos donde el material que se tamiza no es la misma porcion de la
    # que se leyo la humedad, y forzar el total de la humedad dejaria la curva
    # con porcentajes que no cuadran con los pesos de la tabla.
    #
    # Aqui no se decide cual de los dos manda: se devuelven los dos y cada
    # pantalla usa el que le corresponde. La granulometria escribe su W1 y el
    # motor solo lo usa si hay algo escrito.
    w_gramo = grano.get("w1")
    base = w_gramo if (w_gramo is not None and w_gramo > 0) else w_suelo
    g_total = base if (base is not None and base > 0) else None
    res["g_total"] = g_total
    #: El peso del suelo que sale de la humedad natural, para que la casilla
    #: W1 de la granulometria pueda mostrarlo como valor por defecto.
    res["w_suelo_humedad"] = w_suelo
    g = calcular_granulometria({"total": g_total, "pesos": grano["pesos"]},
                               serie)
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

    # ---- composición para presentar (pantalla y PDF deben coincidir) ----
    # Grava + Arena + Finos suman 100 % exactamente en aritmética real
    # (grava = 100 − F4, arena = F4 − F200, finos = F200). Al imprimirlas a
    # 1 decimal, redondear las tres por separado puede dar 99.9 o 100.1. Se
    # redondean Grava y Arena y se obtiene Finos por diferencia, de modo que
    # las tres celdas mostradas sumen siempre 100.0 %. Estas claves son las
    # que leen tanto el resumen de la interfaz como la tabla del PDF.
    gv, ar, fi = g["grava"], g["arena"], g["finos"]
    if gv is not None and ar is not None and fi is not None:
        res["g_grava_1d"] = round(gv, 1)
        res["g_arena_1d"] = round(ar, 1)
        res["g_finos_1d"] = round(100.0 - round(gv, 1) - round(ar, 1), 1)
    else:
        res["g_grava_1d"] = res["g_arena_1d"] = res["g_finos_1d"] = None

    # ---- clasificación ----
    Fn = g["f200"]
    LL2, PI2 = res["LL"], res["IP"]
    sucs, sucs_desc = clasificar(Fn, g["grava"], g["arena"], g["cu"], g["cc"],
                                 LL2, PI2, np_=res["ll_np"])
    res["sucs"] = sucs
    res["sucs_desc"] = sucs_desc
    # AASHTO M 145: en un suelo no plástico el índice de plasticidad se toma
    # como 0, no como "dato faltante". Sin esta sustitución un suelo NP
    # quedaría sin clasificar, cuando sí tiene grupo propio.
    ll_aa = 0.0 if res["ll_np"] else LL2
    pi_aa = 0.0 if res["ll_np"] else PI2
    gpo = grupo_aashto(g["f10"], g["f40"], Fn, ll_aa, pi_aa)
    res["grupo_aashto"] = gpo
    # El índice de grupo sí exige plasticidad medida, así que un suelo NP
    # no lo tiene: se informa solo el grupo, sin paréntesis.
    res["ig"] = indice_grupo(Fn, LL2, PI2)
    res["aashto"] = ("%s (%d)" % (gpo, res["ig"])) if (gpo and res["ig"] is not None) else (gpo or None)
    # La graduación viaja al resultado para que el reporte dibuje la zona de
    # filtro de la curva sin volver a preguntar a la interfaz. Viene en el bloque
    # `grano`, que es donde la app la deja junto al alcance.
    res["graduacion"] = (grano.get("graduacion") or "").strip()

    res["aashto_desc"] = None
    if gpo:
        from motor.clasificacion import DESC_AASHTO
        res["aashto_desc"] = DESC_AASHTO.get(gpo[:3])
    # Si no se pudo clasificar, se informa qué dato falta para que la interfaz
    # lo diga en vez de mostrar un guion mudo.
    res["aashto_faltan"] = [] if gpo else aashto_faltantes(
        g["f10"], g["f40"], Fn, ll_aa, pi_aa)
    # SUCs también puede quedar sin emitir por falta de datos; se anota por qué
    # para que la interfaz no muestre un guion mudo.
    if not res["sucs"]:
        res["sucs_faltan"] = ([] if Fn is None else
                              (["LL e IP"] if not res["ll_np"] else ["granulometría"]))
    else:
        res["sucs_faltan"] = []

    # ---- verificaciones ----
    res["checks"] = verificaciones(data, res, g)
    return res