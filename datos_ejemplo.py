# -*- coding: utf-8 -*-
"""Banco de ejemplos coherentes de "Cargar ejemplo".

Cada entrada equivale a una muestra de laboratorio completa y verosímil que,
al calcularse, produce una de las clasificaciones SUCs posibles. Al pulsar
"Cargar ejemplo" se elige una al azar (con identificación también aleatoria),
o una del símbolo SUCs seleccionado, de modo que los datos numéricos y la
descripción de la muestra siempre coinciden con la clasificación que
generan.

REALISMO DEL TAMIZADO
---------------------
Los ejemplos no anesthesian los once tamices. En el laboratorio el tamizado
depende del material:

  * Arcillas y limos (CL, CH, ML, MH): no se monta la pila desde 3". Se
    pesa la muestra, se lavan los finos y solo se pesan N°4, N°10, N°40
    y N°200. Los tamices gruesos van EN BLANCO.
  * Arenas: tampoco hay nada mayor que 1", así que 3" a 1" quedan en blanco
    y el tamizado arranca en 3/4" o en N°4.
  * Gravas: se usa la pila completa, pero los tamices finos suelen quedar en
    blanco cuando el suelo es limpio (casi todo pasa el N°200 al fondo).

Un tamiz en blanco se anota con 100.0 de % que pasa en el perfil: su
retenido es cero y `_pesos` lo traduce a un peso en blanco, no a 0.0. Lo
mismo ocurre con un tamiz cuyo retenido cae por debajo de la resolución de
la balanza.

Los perfiles se afinaron numéricamente contra el motor real de la app
(`secciones.granulometria` + `motor.clasificacion`) para que cada fila dé
exactamente el símbolo que anuncia y una curva verosímil, sin saltos
improbables ni toda la fracción gruesa acumulada en un solo tamiz.
"""
import datetime
import math
import random

from secciones.granulometria import calcular_granulometria
from motor.clasificacion import clasificar

_RNG = random.Random()

#: Resolución de la balanza del ensayo (INV E-123 / ASTM D6913).
BALANZA = 0.1

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
# y los 11 pasos de % que pasa, de 3" a N°200. Los tamices que esa muestra
# NO tamiza se anotan con 100.0 (retenido cero -> peso en blanco).
BANCO = [
    # --- gravas limpias: pila completa, apenas finos en el N°200 ---------
    ("GW",   5.5, 3000, 30.0, 30.0, 16.0, False,
     [85.2, 84.4, 82.6, 76.1, 73.7, 67.2, 55.9, 35.8, 13.5, 7.0, 1.5]),
    ("GP",   5.5, 3000, 30.0, 27.0, 16.0, False,
     [92.7, 92.0, 84.7, 83.1, 72.6, 46.6, 44.0, 34.2, 4.0, 2.0, 1.2]),

    # --- arenas puras: nada mayor que 1" ---------------------------------
    ("SW",   8.0, 2000, 30.0, 32.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 77.5, 28.5, 3.0]),
    ("SP",   8.0, 2000, 30.0, 36.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 69.5, 59.0, 4.0]),

    # --- grava con finos: pila completa, D10 interpolable (F200 6-8 %) ----
    ("GW-GM", 8.5, 3000, 30.0, 28.0, 5.0, False,
     [87.1, 86.3, 83.6, 77.9, 71.5, 58.7, 50.8, 37.5, 13.0, 10.0, 7.0]),
    ("GW-GC", 8.5, 3000, 30.0, 31.0, 16.0, False,
     [91.8, 88.5, 79.0, 75.1, 71.3, 66.3, 61.1, 36.4, 12.0, 6.5, 6.0]),
    ("GP-GM", 8.5, 3000, 30.0, 29.0, 5.0, False,
     [86.7, 85.6, 84.9, 83.6, 75.4, 59.4, 56.6, 33.0, 9.0, 8.5, 8.0]),
    ("GP-GC", 8.5, 3000, 30.0, 33.0, 16.0, False,
     [85.0, 82.1, 74.2, 65.5, 59.0, 49.0, 36.3, 28.9, 7.5, 7.0, 6.5]),

    # --- arena con finos: 3" a 1" en blanco ------------------------------
    ("SW-SM", 10.0, 2000, 30.0, 27.0, 5.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 64.0, 11.5, 8.0]),
    ("SW-SC", 10.0, 2000, 30.0, 33.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 54.0, 10.5, 9.0]),
    ("SP-SM", 10.0, 2000, 30.0, 28.0, 5.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 78.5, 58.0, 9.0]),
    ("SP-SC", 10.0, 2000, 30.0, 35.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 76.0, 58.5, 9.5]),

    # --- grava con finos, 12 < F200 < 50 (ya no hay D10) -----------------
    ("GM",  13.0, 1500, 30.0, 34.0, 9.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 88.0, 70.0, 36.0, 31.4, 25.9, 22.0]),
    ("GC",  13.0, 1500, 30.0, 32.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 92.0, 80.0, 66.0, 38.0, 33.4, 27.9, 24.0]),
    ("GM",  16.0, 1500, 30.0, 36.0, None, True,
     [100.0, 100.0, 100.0, 100.0, 100.0, 88.0, 70.0, 36.0, 31.4, 25.9, 22.0]),

    # --- arena con finos, 12 < F200 < 50 ---------------------------------
    ("SM",  15.0, 1500, 30.0, 35.0, 9.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 94.0, 82.0, 63.0, 50.1, 34.9, 24.0]),
    ("SC",  15.0, 1500, 30.0, 33.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 95.0, 84.0, 63.5, 51.1, 36.5, 26.0]),
    ("SM",  18.0, 1500, 30.0, 38.0, None, True,
     [100.0, 100.0, 100.0, 100.0, 100.0, 94.0, 82.0, 63.0, 50.1, 34.9, 24.0]),

    # --- finos: 3" a 3/8" en blanco, solo N°4/N°10/N°40/N°200 ------------
    ("CL",  22.0, 1000, 30.0, 38.0, 16.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 72.7, 64.2, 58.0]),
    ("CH",  32.0, 1000, 30.0, 55.0, 26.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 74.1, 67.0, 62.0]),
    ("ML",  20.0, 1000, 30.0, 28.0, 5.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 74.7, 68.5, 64.0]),
    ("MH",  34.0, 1000, 30.0, 58.0, 20.0, False,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 72.1, 62.7, 56.0]),
    ("ML",  18.0, 1000, 30.0, 24.0, None, True,
     [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 75.4, 69.9, 66.0]),
]

# Símbolos SUCs posibles, en orden de aparición (para el selector).
_SIMBOLOS = []
for _e in BANCO:
    if _e[0] not in _SIMBOLOS:
        _SIMBOLOS.append(_e[0])
SIMBOLOS = tuple(_SIMBOLOS)


def _pesos(p, Ws):
    """Convierte los pasos % que pasa en pesos retenidos (g) por tamiz.

    Un tamiz que no retiene nada se deja EN BLANCO, no como 0.0: así se ve en
    el reporte igual que en el laboratorio, donde el tamiz vacío no se
    anota. Pasa en dos casos:

      * la muestra no tiene nada de ese tamaño (una arcilla no se tamiza
        desde 3"; el perfil de esa fila trae 100.0 en esos tamices);
      * el retenido cae por debajo de la resolución de la balanza.
    """
    ret, prev = [], 100.0
    for paso in p:
        ret.append((prev - paso) / 100.0 * Ws)
        prev = paso
    salida = []
    for w in ret:
        v = round(w, 1)
        salida.append(None if v < BALANZA / 2.0 else v)
    return salida


def _composicion(p, Ws, LL, IP, np_):
    pesos = _pesos(p, Ws)
    g = calcular_granulometria({"total": Ws, "pesos": pesos})
    sucs, _desc = clasificar(g["f200"], g["grava"], g["arena"], g["cu"],
                             g["cc"], LL, IP, np_=np_)
    # `_desc` no se propaga: la descripción del material se arma aparte con
    # `descripcion_sucs` (ver `_descripcion`), que es la que llega al PDF.
    return {
        "sucs": sucs, "tipo": g["tipo"],
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
    return "%02d/%02d/%d" % (d.day, d.month, d.year)


def _descripcion(comp, ll_np):
    from motor.clasificacion import descripcion_sucs
    return descripcion_sucs({
        "sucs": comp["sucs"], "g_grava": comp["grava"],
        "g_arena": comp["arena"], "ll_np": ll_np,
    })


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