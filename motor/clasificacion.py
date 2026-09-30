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


_PLASTICIDAD = {"L": "baja", "H": "alta", "M": "media"}
_LIMPIOS = {"GW", "GP", "SW", "SP"}
# calificativos de cada fracción, en (singular, plural) y por género
_ADJ = {
    "arena": {True: ("arenoza", "arenosas"), False: ("arenoso", "arenosos")},
    "grava": {True: ("gravosa", "gravosas"), False: ("gravoso", "gravosos")},
}
# clave (femenino, plural) -> "no plástico" concordado
_NO_PLASTICO = {
    (True, True): "no plásticas", (False, True): "no plásticos",
    (True, False): "no plástica", (False, False): "no plástico",
}


def _adj(frac, fem, plural):
    """Calificativo de `frac` concordando en género y número."""
    return _ADJ[frac][fem][1 if plural else 0]


def _no_plastico(fem, plural):
    """'no plástico' concordando con el sustantivo al que acompaña."""
    return _NO_PLASTICO[(fem, plural)]


def _conj(partes):
    """Une enumeraciones: 'a', 'a y b', 'a, b y c'.

    Un complemento con preposición se coma antes que conjugar ('a, con b'),
    porque 'a y con b' no es una enumeración natural en español.
    """
    if len(partes) <= 1:
        return "".join(partes)
    penult = ", ".join(partes[:-1])
    ultimo = partes[-1]
    if ultimo.startswith("con "):
        return penult + ", " + ultimo
    if len(partes) == 2:
        return partes[0] + " y " + ultimo
    return penult + " y " + ultimo


def _calificativos(gra, are, fem, plural):
    """Calificativos de grava y arena de un suelo nombrado por su fracción fina.

    Allí ambas fracciones pueden ser el rasgo definitorio, de modo que las
    representativas van como adjetivo ('areno-gravosas') y las demás se
    degradan a 'con algo de ...'.
    """
    mods = []
    gr = gra is not None and gra >= 15
    ar = are is not None and are >= 15
    if gr and ar:
        mods.append("areno-" + _adj("grava", fem, plural))
    elif gr:
        mods.append(_adj("grava", fem, plural))
    elif ar:
        mods.append(_adj("arena", fem, plural))
    if gra is not None and 5 <= gra < 15:
        mods.append("con algo de gravas")
    if are is not None and 5 <= are < 15:
        mods.append("con algo de arena")
    return mods


def _complemento(otro, frac, fem, plural):
    """Calificativos de la fracción restante en un suelo granular.

    El nombre del suelo ya enuncia la fracción dominante, así que la otra solo
    aparece como adjetivo cuando es representativa, o como 'con algo de ...'.
    """
    if otro is None or otro < 5:
        return []
    if otro >= 15:
        return [_adj(frac, fem, plural)]
    return ["con algo de %s" % ("arena" if frac == "arena" else "gravas")]


def descripcion_sucs(res):
    """Frase que describe el material a partir del símbolo SUCs y su textura.

    Nombra el tipo de suelo, su plasticidad y las fracciones de arena y grava
    presentes, sin repetir porcentajes ni coeficientes: esos datos ya figuran
    en las tablas de resultados.
    """
    sucs = (res.get("sucs") or "").strip()
    if not sucs:
        return ""
    gra, are = res.get("g_grava"), res.get("g_arena")
    np_ = bool(res.get("ll_np"))

    # -- suelo granular limpio (GW/GP/SW/SP): grava o arena + gradación --
    if sucs in _LIMPIOS:
        g = (sucs[0] == "G")
        mods = ["bien graduada" if sucs[1] == "W" else "mal graduada", "limpia"]
        if np_:
            mods.append(_no_plastico(True, False))
        resto = _complemento(are if g else gra, "arena" if g else "grava",
                             True, False)
        return _frase("Grava" if g else "Arena", mods + resto)

    # -- símbolo doble (5 <= %pasa N°200 <= 12): grado + fracción con finos --
    if "-" in sucs:
        grado, resto = sucs.split("-", 1)
        g = (resto[0] == "G")
        finos = "limosos no plásticos" if (resto[1] == "M" and np_) \
            else ("limosos" if resto[1] == "M" else "arcillosos")
        mods = ["bien graduada" if grado[1] == "W" else "mal graduada"]
        comp = _complemento(are if g else gra, "arena" if g else "grava",
                            True, False)
        return _frase("Grava" if g else "Arena",
                      mods + comp + ["con finos " + finos])

    base, letra = sucs[0], sucs[1]

    # -- fracción fina (CL/CH/ML/MH): plasticidad según la línea A --
    if letra in "LH":
        fem = (base == "C")
        mods = ([_no_plastico(fem, True)] if np_
                else ["de plasticidad " + _PLASTICIDAD[letra]])
        return _frase("Arcillas" if fem else "Limos",
                      mods + _calificativos(gra, are, fem, True))

    # -- suelo granular con finos (12 < %pasa N°200 < 50): SM/SC/GM/GC --
    g = (base == "G")
    calif = "limosa" if letra == "M" else "arcillosa"
    if np_ and letra == "M":
        calif += " " + _no_plastico(True, False)
    comp = _complemento(are if g else gra, "arena" if g else "grava",
                        True, False)
    return _frase("Grava" if g else "Arena", [calif] + comp)


def _frase(head, mods):
    """Sustantivo del suelo seguido de sus calificativos, con punto final."""
    return (head + " " + _conj(mods)).rstrip() + "."


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