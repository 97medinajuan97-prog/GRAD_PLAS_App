# -*- coding: utf-8 -*-
"""Clasificación de suelos: SUCs (ASTM D-2487) y AASHTO (INV E-102)."""

DESC_SUCS = {
    "GW": "Grava bien graduada, limpia", "GP": "Grava mal graduada, limpia",
    "SW": "Arena bien graduada, limpia", "SP": "Arena mal graduada, limpia",
    "GM": "Grava limosa", "GC": "Grava arcillosa",
    "SM": "Arena limosa", "SC": "Arena arcillosa",
    "CL": "Arcilla inorgánica de baja plasticidad",
    "CH": "Arcilla inorgánica de alta plasticidad",
    "ML": "Limo inorgánico de baja plasticidad",
    "MH": "Limo inorgánico de alta plasticidad",
}
DESC_AASHTO = {
    "A-1": "Grava y arena bien graduadas (piedra, grava, arena)",
    "A-2": "Grava y arena arcillosa o limosa",
    "A-3": "Arena fina",
    "A-4": "Suelo limoso",
    "A-5": "Suelo limoso",
    "A-6": "Suelo arcilloso",
    "A-7": "Suelo arcilloso",
}


def clasificar(Fn, Gp, An, CU, CC, LL2, PI2, np_=False):
    """SUCs según %pasa N°200 (Fn), %grava (Gp), %arena (An) y plasticidad.

    `np_` indica muestra no plástica (LL/IP indeterminados, NP): sus finos se
    asumen no plásticos, por lo que la letra de plasticidad es "M" (limo).
    """
    plastic = (not np_) and (LL2 is not None) and (PI2 is not None)
    if plastic:
        Alinea = 0.73 * (LL2 - 20)
        letra = "C" if (PI2 > Alinea and PI2 >= 4) else "M"
    else:
        letra = "M"
    base = ("G" if Gp >= An else "S") if (Gp is not None and An is not None) else None
    grado = None
    if base is not None and CU is not None and CC is not None:
        if base == "G":
            grado = "GW" if (CU >= 4 and 1 <= CC <= 3) else "GP"
        else:
            grado = "SW" if (CU >= 6 and 1 <= CC <= 3) else "SP"
    if Fn is None:
        sucs = None
    elif Fn < 5:
        sucs = grado
    elif Fn <= 12:
        sucs = (grado + "-" + base + letra) if (grado and base and letra) else None
    elif Fn < 50:
        sucs = (base + letra) if (base and letra) else None
    else:
        seg = "H" if (LL2 is not None and LL2 >= 50) else "L"
        sucs = (letra + seg) if letra else None
    desc = None
    if sucs:
        desc = ("Suelo granular con finos (símbolo doble)"
                if "-" in sucs else DESC_SUCS.get(sucs))
    return sucs, desc


def grupo_aashto(F10, F40, F200, LL, PI):
    """Grupo AASHTO según %pasa N°10, N°40, N°200 y plasticidad."""
    if F200 <= 35:
        if (F10 is None or F10 <= 50) and (F40 is None or F40 <= 30) and (F200 is None or F200 <= 15) and (PI is None or PI <= 6):
            return "A-1-a"
        if (F40 is None or F40 <= 50) and (F200 is None or F200 <= 25) and (PI is None or PI <= 6):
            return "A-1-b"
        if (F40 is None or F40 >= 51) and (F200 is None or F200 <= 10) and (PI is None or PI <= 0):
            return "A-3"
        if (LL is None or LL <= 40) and (PI is None or PI <= 10):
            return "A-2-4"
        if LL is not None and LL > 40 and (PI is None or PI <= 10):
            return "A-2-5"
        if (LL is None or LL <= 40) and PI is not None and PI > 10:
            return "A-2-6"
        return "A-2-7"
    if (LL is None or LL <= 40) and (PI is None or PI <= 10):
        return "A-4"
    if LL is not None and LL > 40 and (PI is None or PI <= 10):
        return "A-5"
    if (LL is None or LL <= 40) and PI is not None and PI > 10:
        return "A-6"
    if PI is not None and LL is not None and PI <= LL - 30:
        return "A-7-5"
    return "A-7-6"


def indice_grupo(F200, LL, PI):
    """Índice de grupo (AASHTO): IG = 0.2a + 0.005ac + 0.01bd."""
    a = max(0, min(40, F200 - 35))
    b = max(0, min(40, F200 - 15))
    c = 0 if PI <= 10 else max(0, min(20, LL - 40))
    d = max(0, min(20, PI - 10))
    return max(0, round(0.2 * a + 0.005 * a * c + 0.01 * b * d))