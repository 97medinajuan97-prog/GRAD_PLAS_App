# -*- coding: utf-8 -*-
"""Banco de ejemplos coherentes de "Cargar ejemplo".

Cada entrada equivale a una muestra de laboratorio completa y realista que,
al calcularse, produce una de las clasificaciones SUCs posibles. Los perfiles
de pasa (%) son monótonos (sin pesos negativos) y grava+arena+finos suman
100 %. Al pulsar "Cargar ejemplo" se elige una al azar (con identificación
también aleatoria), o una del símbolo SUCs seleccionado, de modo que los
datos numéricos y la descripción de la muestra siempre coinciden con la
clasificación que generan.
"""
import datetime
import math
import random

from secciones.granulometria import calcular_granulometria
from motor.clasificacion import clasificar

_RNG = random.Random()

PROYECTOS = [
    "CARACTERIZACION BASE GRANULAR VIA SAN JUAN",
    "ESTUDIO GEOTECNICO PUENTE LA PAZ",
    "MEJORAMIENTO VIA EL CARMEN",
    "BANCO DE MATERIALES RIO NEGRO",
]
SECTORES = [
    "ACOPIO PLANTA", "PR-40+800 KM DER", "PR-25+300 KM IZQ",
    "FRENTE DE EXCAVACION N-1",
]
ORDENADO = [
    "GUSTAVO QUESADA", "LUIS PERDOMO ROMAN", "MARIA OSPINA VERGARA",
    "CARLOS BERNAL MORA",
]

# (símbolo, humedad natural % objetivo, Ws seco (g), Wc tara (g), LL, IP, NP)
# La granulometría se describe con 11 pasos (% que pasa) decrecientes:
# '3"' .. N° 4 .. N° 200. Suma grava+arena+finos = 100 %.
BANCO = [
    ("GW",   5.5, 3000, 30.0, 30.0, 16.0, False,
     [85.24, 84.37, 82.57, 76.07, 73.67, 67.18, 55.95, 35.78, 28.58, 9.59, 2.0]),
    ("GP",   5.5, 3000, 30.0, 27.0, 16.0, False,
     [92.66, 92.0, 84.73, 83.08, 72.59, 46.64, 44.01, 34.15, 27.45, 6.13, 2.0]),
    ("SW",   8.0, 2000, 30.0, 32.0, 16.0, False,
     [97.81, 97.64, 96.71, 94.69, 93.1, 88.04, 76.83, 71.75, 45.87, 16.68, 2.5]),
    ("SP",   8.0, 2000, 30.0, 36.0, 16.0, False,
     [97.02, 95.91, 92.13, 91.11, 86.32, 78.13, 74.82, 55.56, 48.86, 21.15, 2.5]),
    ("GW-GM", 8.5, 3000, 30.0, 28.0, 5.0, False,
     [87.1, 86.34, 83.56, 77.89, 71.47, 58.71, 50.82, 37.51, 32.02, 14.38, 8.0]),
    ("GW-GC", 8.5, 3000, 30.0, 31.0, 16.0, False,
     [91.84, 88.46, 79.04, 75.09, 71.35, 66.34, 61.09, 36.41, 31.86, 13.58, 8.0]),
    ("GP-GM", 8.5, 3000, 30.0, 29.0, 5.0, False,
     [86.71, 85.56, 84.91, 83.64, 75.36, 59.42, 56.61, 32.99, 26.97, 12.45, 8.0]),
    ("GP-GC", 8.5, 3000, 30.0, 33.0, 16.0, False,
     [84.98, 82.1, 74.23, 65.49, 59.02, 48.95, 36.28, 28.87, 25.82, 13.46, 8.0]),
    ("SW-SM", 10.0, 2000, 30.0, 27.0, 5.0, False,
     [94.97, 94.71, 90.87, 89.88, 88.62, 85.17, 74.16, 56.72, 43.87, 15.61, 8.0]),
    ("SW-SC", 10.0, 2000, 30.0, 33.0, 16.0, False,
     [96.53, 95.44, 93.6, 91.42, 87.63, 84.17, 79.68, 67.41, 47.51, 20.94, 8.0]),
    ("SP-SM", 10.0, 2000, 30.0, 28.0, 5.0, False,
     [97.45, 95.94, 93.62, 93.19, 90.41, 84.74, 82.08, 68.21, 54.61, 40.22, 8.0]),
    ("SP-SC", 10.0, 2000, 30.0, 35.0, 16.0, False,
     [91.72, 90.67, 89.79, 83.13, 76.35, 72.33, 70.87, 62.7, 55.91, 38.19, 8.0]),
    ("GM",  13.0, 1500, 30.0, 34.0, 9.0, False,
     [94.83, 93.99, 90.86, 89.12, 86.75, 75.96, 64.35, 33.53, 33.26, 26.84, 24.0]),
    ("GC",  13.0, 1500, 30.0, 32.0, 16.0, False,
     [94.04, 91.68, 87.12, 84.32, 68.97, 66.87, 51.71, 38.35, 37.37, 31.55, 24.0]),
    ("SM",  15.0, 1500, 30.0, 35.0, 9.0, False,
     [99.0, 98.57, 97.25, 95.43, 91.3, 89.23, 85.43, 71.05, 44.63, 29.53, 24.0]),
    ("SC",  15.0, 1500, 30.0, 33.0, 16.0, False,
     [97.66, 95.74, 93.67, 92.06, 88.73, 78.39, 77.06, 65.29, 59.97, 40.59, 24.0]),
    ("GM",  16.0, 1500, 30.0, 36.0, None, True,
     [94.83, 93.99, 90.86, 89.12, 86.75, 75.96, 64.35, 33.53, 33.26, 26.84, 24.0]),
    ("SM",  18.0, 1500, 30.0, 38.0, None, True,
     [99.0, 98.57, 97.25, 95.43, 91.3, 89.23, 85.43, 71.05, 44.63, 29.53, 24.0]),
    ("CL",  22.0, 1000, 30.0, 38.0, 16.0, False,
     [99.07, 98.84, 97.94, 97.6, 96.94, 94.66, 91.65, 90.8, 83.88, 68.36, 60.0]),
    ("CH",  32.0, 1000, 30.0, 55.0, 26.0, False,
     [99.5, 99.06, 98.35, 97.27, 96.91, 95.38, 94.32, 89.8, 79.63, 64.23, 60.0]),
    ("ML",  20.0, 1000, 30.0, 28.0, 5.0, False,
     [98.82, 98.46, 97.0, 94.78, 91.95, 84.18, 81.83, 76.2, 75.3, 67.45, 60.0]),
    ("MH",  34.0, 1000, 30.0, 58.0, 20.0, False,
     [98.48, 98.17, 96.6, 93.4, 90.48, 88.59, 85.54, 81.85, 80.22, 70.95, 60.0]),
    ("ML",  18.0, 1000, 30.0, 24.0, None, True,
     [98.82, 98.46, 97.0, 94.78, 91.95, 84.18, 81.83, 76.2, 75.3, 67.45, 60.0]),
]

# Símbolos SUCs posibles, en orden de aparición (para el selector).
_SIMBOLOS = []
for _e in BANCO:
    if _e[0] not in _SIMBOLOS:
        _SIMBOLOS.append(_e[0])
SIMBOLOS = tuple(_SIMBOLOS)


def _pesos(p, Ws):
    """Convierte los pasos % (decrecientes) a pesos retenidos (g) por tamiz."""
    ret = []
    prev = 100.0
    for i in range(10):
        ret.append((prev - p[i]) / 100.0 * Ws)
        prev = p[i]
    ret.append((prev - p[10]) / 100.0 * Ws)
    return [round(w, 1) for w in ret]


def _composicion(p, Ws, LL, IP, np_):
    pesos = _pesos(p, Ws)
    g = calcular_granulometria({"total": Ws, "pesos": pesos})
    sucs, desc = clasificar(g["f200"], g["grava"], g["arena"], g["cu"],
                            g["cc"], LL, IP, np_=np_)
    return {
        "sucs": sucs, "desc": desc, "tipo": g["tipo"],
        "grava": g["grava"], "arena": g["arena"], "finos": g["f200"],
        "cu": g["cu"], "cc": g["cc"],
    }


# Variantes de (golpes, desfase) para el ensayo de límite líquido: cada LL del
# banco usa una combinación distinta, de modo que los 3 puntos NO quedan
# perfectamente alineados y la "figura" de puntos varía entre ejemplos.
_VARIANTES_LL = (
    ((14, 24, 40), (0.9, -1.1, 0.3)),
    ((16, 30, 45), (-0.8, 1.2, -0.4)),
    ((12, 22, 38), (1.3, -0.6, -0.9)),
    ((18, 28, 42), (-1.2, 0.7, 1.0)),
    ((15, 25, 35), (0.5, -0.9, 0.7)),
    ((20, 32, 48), (1.1, 0.4, -1.3)),
)


def _filas_ll(LL):
    if LL is None:
        return []
    golpes, desfase = _VARIANTES_LL[int(abs(float(LL or 0))) % len(_VARIANTES_LL)]
    filas = []
    for j, n in enumerate(golpes, 1):
        w = LL + 3.5 * math.log(25.0 / n) + desfase[j - 1]
        filas.append({"id": "LL-%d" % j, "n": n, "recip": 30.0,
                      "hum": round(130.0 + w, 1), "seco": 130.0})
    return filas


def _filas_lp(LL, IP):
    if LL is None or IP is None:
        return []
    LP = LL - IP
    return [{"id": "LP-%d" % (i + 1), "recip": 25.0,
             "hum": round(65.0 + (LP + d) / 100.0 * 40.0, 1),
             "seco": 65.0}
            for i, d in enumerate((1.5, -1.5))]


def _fecha(base, det):
    d = base + datetime.timedelta(days=det)
    return "%d/%d/%d" % (d.month, d.day, d.year)


def _descripcion(comp, ll_np):
    s = comp
    tipo = s["tipo"] or "SUELO"
    txto = "Suelo %s" % tipo.lower()
    nomb = s["desc"] or s["sucs"] or "sin clasificar"
    if s["sucs"] and "-" in s["sucs"]:
        nomb = "símbolo doble " + s["sucs"]
    txto += ": %s (%s)." % (nomb, s["sucs"])
    if tipo == "GRANULAR" and s["finos"] is not None:
        txto += " %d%% grava, %d%% arena, %d%% finos; Cu=%.1f, Cc=%.2f." % (
            round(s["grava"]), round(s["arena"]), round(s["finos"]),
            s["cu"] or 0.0, s["cc"] or 0.0)
    if tipo == "FINO":
        txto += " %d%% pasa el tamiz N° 200." % round(s["finos"])
    if ll_np:
        txto += " Material no plástico (NP)."
    return txto


def _construir(entrada):
    sucs, w_nat, Ws, recip, LL, IP, np_, p = entrada
    pesos = _pesos(p, Ws)
    comp = _composicion(p, Ws, LL, IP, np_)

    hum_rec = _RNG.uniform(25.0, 35.0)
    base = datetime.date(2026, 1, 20)
    desde = _RNG.randint(1, 25) * 0.5
    hasta = desde + _RNG.uniform(0.5, 2.0)

    id_ = {
        "proyecto": _RNG.choice(PROYECTOS),
        "sector": _RNG.choice(SECTORES),
        "ordenado": _RNG.choice(ORDENADO),
        "sondeo": "S-%d" % _RNG.randint(1, 12),
        "muestra": str(_RNG.randint(1, 3)),
        "fecha_toma": _fecha(base, _RNG.randint(0, 40)),
        "fecha_ejecucion": _fecha(base, _RNG.randint(45, 80)),
        "prof_desde": "%.2f" % desde,
        "prof_hasta": "%.2f" % hasta,
        "descripcion": _descripcion(comp, np_),
    }

    return {
        "ll_np": np_,
        "hum": {"id": "A-1",
                "recip": round(hum_rec, 1),
                "hum": round(Ws + recip + w_nat / 100.0 * Ws, 1),
                "seco": Ws + recip},
        "ll": _filas_ll(LL),
        "lp": _filas_lp(LL, IP),
        "grano": {"total": None, "pesos": pesos},
        "ident": id_,
    }


def datos_ejemplo(solo=None):
    """Devuelve una muestra de ejemplo aleatoria del banco.

    Con `solo` se acota al símbolo SUCs indicado (p. ej. "CL", "SC", "GW-GM").
    """
    pool = [e for e in BANCO if solo is None or e[0] == solo]
    if not pool:
        pool = BANCO
    return _construir(_RNG.choice(pool))


def sembrar(indice):
    """Devuelve el i-ésimo ejemplo del banco (para las pruebas)."""
    return _construir(BANCO[indice % len(BANCO)])