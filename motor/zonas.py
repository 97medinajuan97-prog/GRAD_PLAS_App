# -*- coding: utf-8 -*-
"""Zonas de filtro de los materiales, para la curva granulométrica.

Cada material tiene una franja de aceptación: dos límites de % que pasa, uno
inferior y otro superior, y el material está dentro de zona cuando su curva
queda entre los dos. Se proyecta sobre la curva como dos líneas punteadas con
la franja sombreada entre ellas.

Los valores van con la notación de la especificación (1.5", 0.5"), no con la
de la serie de tamices de la app (1 1/2", 1/2"), porque así se pueden comparar
de un vistazo con el documento del laboratorio. `_ALIAS` traduce una en otra al
buscar el diámetro, y `_validar` revisa al importar que todos los puntos
resuelvan: un nombre mal escrito que no se encontrara dejaría una zona a medio
dibujar, que es peor que ninguna.
"""

#: Traducción de la notación de la especificación a la de la serie de tamices.
_ALIAS = {
    '1.5"': '1 1/2"',
    '0.5"': '1/2"',
    'No.4': 'N° 4',
    'No.10': 'N° 10',
    'No.40': 'N° 40',
    'No.200': 'N° 200',
}


def _p(*pares):
    """[(tamiz, % pasa)] en la notación de la especificación."""
    return list(pares)


#: Graduación -> (línea inferior, línea superior).
ZONAS_FILTRO = {
    # --- afirmados -----------------------------------------------------
    "A-38": (
        _p(("1.5\"", 100), ("3/4\"", 80), ("3/8\"", 60), ("No.4", 40),
            ("No.10", 30), ("No.40", 13), ("No.200", 9)),
        _p(("3/4\"", 100), ("3/8\"", 85), ("No.4", 65), ("No.10", 50),
            ("No.40", 30), ("No.200", 18)),
    ),
    "A-25": (
        _p(("1\"", 100), ("3/4\"", 90), ("3/8\"", 65), ("No.4", 45),
            ("No.10", 35), ("No.40", 15), ("No.200", 10)),
        _p(("3/4\"", 100), ("3/8\"", 90), ("No.4", 70), ("No.10", 55),
            ("No.40", 35), ("No.200", 20)),
    ),

    # --- subbases ------------------------------------------------------
    "SBG-50": (
        _p(("2\"", 100), ("1.5\"", 70), ("1\"", 60), ("0.5\"", 45),
            ("3/8\"", 40), ("No.4", 25), ("No.10", 15), ("No.40", 6),
            ("No.200", 2)),
        _p(("1.5\"", 95), ("1\"", 90), ("0.5\"", 75), ("3/8\"", 70),
            ("No.4", 55), ("No.10", 40), ("No.40", 25), ("No.200", 15)),
    ),
    "SBG-38": (
        _p(("1.5\"", 100), ("1\"", 75), ("0.5\"", 55), ("3/8\"", 45),
            ("No.4", 30), ("No.10", 20), ("No.40", 8), ("No.200", 2)),
        _p(("1\"", 95), ("0.5\"", 85), ("3/8\"", 75), ("No.4", 60),
            ("No.10", 45), ("No.40", 30), ("No.200", 15)),
    ),

    # --- bases ---------------------------------------------------------
    "BG-40": (
        _p(("1.5\"", 100), ("1\"", 75), ("3/4\"", 65), ("3/8\"", 45),
            ("No.4", 30), ("No.10", 15), ("No.40", 7), ("No.200", 0)),
        _p(("1\"", 100), ("3/4\"", 90), ("3/8\"", 68), ("No.4", 50),
            ("No.10", 32), ("No.40", 20), ("No.200", 9)),
    ),
    "BG-27": (
        _p(("1\"", 100), ("3/4\"", 75), ("3/8\"", 52), ("No.4", 35),
            ("No.10", 20), ("No.40", 8), ("No.200", 0)),
        _p(("3/4\"", 100), ("3/8\"", 78), ("No.4", 59), ("No.10", 40),
            ("No.40", 22), ("No.200", 9)),
    ),
    "BG-38": (
        _p(("1.5\"", 100), ("1\"", 70), ("3/4\"", 60), ("3/8\"", 45),
            ("No.4", 30), ("No.10", 20), ("No.40", 10), ("No.200", 5)),
        _p(("1\"", 100), ("3/4\"", 90), ("3/8\"", 75), ("No.4", 60),
            ("No.10", 45), ("No.40", 30), ("No.200", 15)),
    ),
    "BG-25": (
        _p(("1\"", 100), ("3/4\"", 70), ("3/8\"", 50), ("No.4", 35),
            ("No.10", 20), ("No.40", 10), ("No.200", 5)),
        _p(("3/4\"", 100), ("3/8\"", 80), ("No.4", 65), ("No.10", 45),
            ("No.40", 30), ("No.200", 15)),
    ),
}


def _validar():
    """Revisa que todo tamiz de las zonas exista en alguna serie de la app.

    Solo importa el nombre: los diámetros se buscan en la serie que tenga la
    muestra. Un nombre que no exista en ninguna serie es un error de escritura
    en los datos, y se avisa al importar en vez de dejar una zona a medias.
    """
    from secciones.granulometria import SIEVES_SUELOS, SERIES_CC
    nombres = {n for n, _ in SIEVES_SUELOS}
    for serie in SERIES_CC.values():
        nombres |= {n for n, _ in serie}
    faltan = set()
    for g, (inf, sup) in ZONAS_FILTRO.items():
        for tamiz, _p in list(inf) + list(sup):
            if _ALIAS.get(tamiz, tamiz) not in nombres:
                faltan.add("%s (%s)" % (tamiz, g))
    if faltan:
        raise ValueError(
            "Zonas de filtro con tamices que no existen: %s. Revisa la "
            "notación o el alias en motor/zonas.py." % ", ".join(sorted(faltan)))
    return True


def _normaliza(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(t.split()).upper()


def zona_de(graduacion):
    """(línea inferior, línea superior) de la graduación, o `None`.

    La comparación no distingue mayúsculas, minúsculas, tildes ni espacios: el
    código de graduación se teclea y puede llegar como "BG-38", "bg 38" o con
    espacios de más.
    """
    if not graduacion:
        return None
    clave = _normaliza(graduacion)
    for g, par in ZONAS_FILTRO.items():
        if _normaliza(g) == clave:
            return par
    return None


def puntos_de(linea, diametros):
    """Convierte `[(tamiz, % pasa)]` a `[(diametro, % pasa)]`.

    `diametros` viene de la serie vigente, que cambia según el alcance: el 0.5"
    de las subbases es el 1/2" de la app y no está en las series de afirmados.
    Un tamiz que no está en esa serie se descarta (esa serie no lo tamiza), pero
    `_validar` ya se encarga de que el nombre exista en alguna.

    Devuelve la lista de mayor a menor diámetro, que es como se dibuja la zona
    sobre el eje de la curva.
    """
    salida = []
    for tamiz, pasa in linea:
        clave = _ALIAS.get(tamiz, tamiz)
        d = diametros.get(clave)
        if d is None:
            continue
        salida.append((d, float(pasa)))
    return sorted(salida, key=lambda r: -r[0])


_validar()