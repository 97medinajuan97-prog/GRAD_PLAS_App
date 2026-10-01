# -*- coding: utf-8 -*-
"""Zonas de filtro de los materiales, para la curva granulométrica.

Cada material tiene una franja de aceptación: dos límites de % que pasa, uno
inferior y otro superior, y el material está dentro de zona cuando su curva
queda entre los dos. Se proyecta sobre la curva como dos líneas paralelas al
eje, con la zona sombreada entre ellas.

Los valores se dan como (tamiz, % que pasa). Van por el NOMBRE del tamiz, no
por diámetro: "1 1/2"" y "1 1/2" son el mismo tamiz y los diameters son más
fáciles de equivocar al teclear.

    Afirmados   A-38, A-25
    Bases       BG-40, BG-27, BG-38, BG-25
    Subbases    SBG-50, SBG-38

Solo hay datos de BG-38 por ahora. Las demás graduaciones se inventarían, así
que no se dibuja nada para ellas: es preferible ver la curva limpia antes que
una zona que no dice la verdad.

`pasa_a_100` es el punto donde la línea llega al 100 %: la curva no empieza
por encima del primer tamiz con dato, así que la zona se cierra ahí en vez de
inventar un tramo horizontal.
"""

#: Graduación -> (línea inferior, línea superior). Cada línea es una lista de
#: pares (tamiz, % que pasa).
ZONAS_FILTRO = {
    "BG-38": (
        # inferior
        [("1 1/2\"", 100.0), ("1\"", 70.0), ("3/4\"", 60.0), ("3/8\"", 50.0),
         ("N° 4", 30.0), ("N° 10", 20.0), ("N° 40", 10.0), ("N° 200", 5.0)],
        # superior
        [("1\"", 100.0), ("3/4\"", 90.0), ("3/8\"", 75.0), ("N° 4", 60.0),
         ("N° 10", 45.0), ("N° 40", 30.0), ("N° 200", 15.0)],
    ),
}


def zona_de(graduacion):
    """(línea inferior, línea superior) de la graduación, o `None`.

    La comparación no distingue mayúsculas ni tildes: el código de graduación
    se teclea y puede llegar como "BG-38", "bg-38" o con espacios de más.
    """
    if not graduacion:
        return None
    clave = _normaliza(graduacion)
    for g, par in ZONAS_FILTRO.items():
        if _normaliza(g) == clave:
            return par
    return None


def _normaliza(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(t.split()).upper()


def puntos_de(linea, diametros):
    """Convierte `[(tamiz, % pasa)]` a `[(diametro, % pasa)]`.

    Un tamiz que no está en la serie vigente se descarta: son series distintas
    y el 1/2" no está en todas. Devuelve la lista de mayor a menor diámetro, que
    es como se dibuja la zona sobre el eje de la curva.
    """
    salida = []
    for tamiz, pasa in linea:
        d = diametros.get(tamiz)
        if d is None:
            continue
        salida.append((d, float(pasa)))
    return sorted(salida, key=lambda r: -r[0])