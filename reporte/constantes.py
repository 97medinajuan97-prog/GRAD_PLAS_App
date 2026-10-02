# -*- coding: utf-8 -*-
"""Constantes de configuración del reporte.

Datos editables del laboratorio que se usan en el pie de página de los
documentos generados. Edítelos aquí y se reflejarán en todos los reportes.
"""


#: Pie de página del reporte. Cada línea se centra en el pie, justo encima
#: del borde grueso inferior; el número de página se dibuja a la derecha.
#: Edítelos aquí y se reflejarán en todos los reportes.
PIE = (
    "Carrera 28 # 2\u00aa 08 Sogamoso Boyac\u00e1   \u00b7   "
    "Cel. 318 5613325 \u2013 310 871 6863 - Tel (608) 775 06 30   \u00b7   "
    "Email. cgutierrezcarrerog@gmail.com",
)

#: Firmas de responsabilidad (bloque justo encima del pie de página).
#: Dos columnas separadas por una línea vertical delgada.
#:
#: Cada entrada dice, en este orden:
#:   - lado:      "izq" o "der". Reparte las dos mitades del bloque.
#:   - imagen:    firma preparada (PNG con el papel ya transparente y recortada
#:                al trazo). Vacío "" si esa firma no tiene imagen.
#:   - nombre:    de quién es, se imprime debajo de la línea.
#:   - cargo:     el puesto, se imprime justo bajo la línea.
#:
#: Las imágenes se preparando con `tools_preparar_firmas.py`, que convierte los
#: escaneos tal cual llegan (tinta sobre blanco, sin transparencia) en algo que
#: se pueda imprimir: sin el rectángulo blanco de fondo y recortado al trazo.
#:
#: La casilla "Firmar" de la aplicación decide si se dibujan o no. Sin ella
#: quedan los nombres y el espacio en blanco, que es lo que se necesita para
#: imprimir una copia que se va a firmar a mano.
#: `alto` es el alto maximo de la firma en puntos, medido con la base apoyada en
#: la linea. Sin la clave se usa `ALTO_FIRMA_BASE`, que es el tamaño con el que
#: se vinha viendo la firma del laboratorista: asi la firma que no se toca no
#: cambia de aspecto porque la otra haya crecido.
FIRMAS = (
    # La del ingeniero se veia muy reducida en el reporte, asi que va un 50 %
    # mas alta. Crece desde abajo, apoyada en la linea, no desde el centro.
    {"lado": "izq", "imagen": "firmas/firma_ing.png",
     "nombre": "Carlos Hernán Gutiérrez Carrero",
     "cargo": "Ing. Control de Calidad",
     "alto": 28.8},
    {"lado": "der", "imagen": "firmas/firma_laboratorista.png",
     "nombre": "Jaider Gallego",
     "cargo": "Laboratorista"},
)

#: Alto por defecto de una firma, en puntos. Es el que ya se venia usando.
ALTO_FIRMA_BASE = 19.2


# ------------------------------------------------------------- exploracion ---
#: Tipos de exploracion y como se escriben en el reporte.
#:
#: Cada uno lleva su prefijo, que es el codigo corto con el que se rotula el
#: numero de exploracion: una manual es `P-2`, una mecanica `PM-2` y un apique
#: `A-2`.
#:
#: El rotulo es la palabra que encabeza la fila del reporte. Manual y mecanica
#: comparten "PERFORACION": el codigo ya dice cual de las dos es, asi que
#: escribirlo dos veces en la misma linea solo ocupa espacio. El apique SI
#: conserva el suyo, porque un apique no es una perforacion: es otra exploracion
#: y en un informe de campo decir "PERFORACION" de un apique seria untrue.
#:
#: El orden es el que ve el usuario en el desplegable.
TIPOS_EXPLORACION = (
    {"nombre": "Perforaci\u00f3n manual",
     "prefijo": "P",
     "rotulo": "PERFORACI\u00d3N"},
    {"nombre": "Perforaci\u00f3n mec\u00e1nica",
     "prefijo": "PM",
     "rotulo": "PERFORACI\u00d3N"},
    {"nombre": "Apique",
     "prefijo": "A",
     "rotulo": "APIQUE"},
)

#: Nombres de la lista, en el orden en que se ofrecen.
NOMBRES_EXPLORACION = tuple(t["nombre"] for t in TIPOS_EXPLORACION)

#: Prefijo con el que se rotula cuando no se ha elegido tipo. Es el de la
#: perforacion mecanica, que es lo que se venia suponiendo siempre.
PREFIJO_EXPLORACION_POR_DEFECTO = "PM"

#: Rotulo de la fila cuando no se ha elegido tipo: el de siempre.
ROTULO_EXPLORACION_POR_DEFECTO = "PERFORACI\u00d3N"

#: Prefijos que ya se pueden haber tecleado en el campo. Se ordena de mas
#: largo a mas corto porque "PM-2" tiene que reconocerse como mecanica y no
#: como una manual a la que se le antepone otra P.
PREFIJOS_EXPLORACION = tuple(
    sorted((t["prefijo"] for t in TIPOS_EXPLORACION), key=len, reverse=True))


def _sin_tildes(t):
    """El texto sin tildes ni diacriticos, para poder compararlo."""
    import unicodedata
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c))


def _clave(t):
    """Clave de busqueda: sin tildes, sin espacios y en minusculas."""
    return _sin_tildes(t or "").strip().lower().replace(" ", "")


def datos_exploracion(nombre):
    """Los datos del tipo de exploracion `nombre`, o `None` si no hay ninguno.

    Busca sin distinguir mayusculas, minusculas, tildes ni espacios. El nombre
    viene de un archivo .json que pudo escribir otra version de la aplicacion,
    y comparar la cadena exacta haria que un "apique" en minuscula se quedara
    sin reconocer y saliera como "PERFORACION".
    """
    clave = _clave(nombre)
    if not clave:
        return None
    for t in TIPOS_EXPLORACION:
        if _clave(t["nombre"]) == clave:
            return t
    return None


def prefijo_exploracion(nombre):
    """Prefijo del tipo elegido, o el de por defecto si no hay ninguno."""
    d = datos_exploracion(nombre)
    return d["prefijo"] if d else PREFIJO_EXPLORACION_POR_DEFECTO


def rotulo_exploracion(nombre):
    """Palabra que encabeza la fila del reporte.

    Sin tipo elegido se queda la de siempre, "PERFORACION", para que las
    muestras guardadas antes de que existiera el campo sigan saliendo como
    hasta ahora en vez de que se les inventara un tipo.
    """
    d = datos_exploracion(nombre)
    return d["rotulo"] if d else ROTULO_EXPLORACION_POR_DEFECTO


def lleva_prefijo(valor, prefijos=None):
    """¿El valor ya viene con un prefijo puesto?

    El usuario teclea el numero pelado, pero puede que pegue o reescriba el
    codigo completo. Si ya lo trae, no se le antepone otro. Sin `prefijos`
    se miran los de exploracion.
    """
    v = (valor or "").strip().upper()
    if not v:
        return False
    for p in (PREFIJOS_EXPLORACION if prefijos is None else prefijos):
        if v == p or v.startswith(p + "-"):
            return True
    return False


def codigo_exploracion(valor, nombre_tipo):
    """'2' con perforación mecánica -> 'PM-2'.

    Sin tipo elegido el numero va SUELTO, sin anteponer nada: se eligio el
    rotulo de la fila y no el prefijo del numero, y poner 'PM' hardcodes el
    tipo en una muestra que no lo declaro. Es lo que hacia la aplicacion
    entera antes de que existiera el campo.
    """
    v = (valor or "").strip()
    if not v or lleva_prefijo(v):
        return v
    if datos_exploracion(nombre_tipo) is None:
        return v
    return "%s-%s" % (prefijo_exploracion(nombre_tipo), v)


#: Prefijo de la muestra.
PREFIJO_MUESTRA = "M"


def codigo_muestra(valor):
    """'5' -> 'M-5'. La muestra siempre lleva su prefijo."""
    v = (valor or "").strip()
    if not v or lleva_prefijo(v, (PREFIJO_MUESTRA,)):
        return v
    return "%s-%s" % (PREFIJO_MUESTRA, v)
