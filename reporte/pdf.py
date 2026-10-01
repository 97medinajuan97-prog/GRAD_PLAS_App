# -*- coding: utf-8 -*-
"""Reporte PDF del ensayo (tonos grises, fuente Segoe UI).

Layout definido por configuración: las secciones se ubican dentro del área
útil de la hoja carta (612x792 pt) menos márgenes (lateral 1" por lado,
superior/inferior 0.5"). Presentación actual:

  - cada sección ocupa todo el ancho disponible entre las márgenes,
  - separadas verticalmente entre sí por 5 pt,
  - cajas simples: borde negro, sin relleno,
  - las alturas de cada sección se toman de `SECTIONS` (porcentaje del
    área útil) y la pila completa queda centrada verticalmente.

El documento se emite en una sola página: las alturas de las secciones se
apilan y el sobrante queda entre el cuerpo y el bloque de firmas, de modo que
las firmas y el pie permanecen anclados al borde inferior.
"""

import os
from collections import namedtuple

# No se importa `secciones.granulometria` a propósito: ese módulo arrastra
# tkinter y el reporte se genera también sin interfaz (servidor, pruebas). El
# número de filas se comprueba contra los datos received al dibujar, en
# `_bloque_gr`.

_FONTS = {}

# ---- página (hoja carta, pt) ----
_PAGE_W, _PAGE_H = 612.0, 792.0          # letter 8.5" x 11"
_MARGEN_L = _MARGEN_R = 72.0             # 1 pulgada lateral
_MARGEN_S = _MARGEN_I = 36.0             # 0.5 pulgadas sup./inf.

GAP = 5.0                                # separación vertical entre recuadros

# ---- secciones: (nombre, descripción, x%, y%, ancho%, alto%) ----
# x/y/ancho de la tabla original; el alto (%) se respeta, la posición
# horizontal es siempre ancho completo y y se recalcula con `GAP`.
_ROWH_WL = 12.5                     # alto de fila de la tabla de pesos/límites
_ROWS_WL = 9                        # encabezado + 8 filas de datos
_SECT_H_WL = _ROWS_WL * _ROWH_WL     # alto exacto de la sección wl-wp-block

_GR_ROWH = _ROWH_WL                   # la tabla de granulometría usa el mismo alto de fila
# banda inferior de parámetros granulométricos (W1/W2, D60..D10, Cu/Cc, %):
_GR_BAND_GAP = 5.0                    # separación entre la tabla y la banda
_GR_BAND_VH = 13.0                    # altura de las filas de datos de la banda
_GR_BAND_PAD = 2.0                    # aire superior/inferior de la banda
_GR_BAND_H = 2 * _GR_BAND_VH + 2 * _GR_BAND_PAD

#: Aire extra entre la sección de granulometría y la curva.
#:
#: Con el GAP general de 5 pt, la banda de parámetros (W1/W2, Cu/Cc) y la tabla
#: de denominaciones de la curva (GRAVA | ARENA | LIMO Y ARCILLA) quedaban a
#: 10 pt, y se leían como un solo bloque de líneas. Subido a 12 seguían
#: pegadas; a 18 la curva se despega y las dos cajas se leen separadas.
_GR_CHART_GAP = 18.0


def _alturas_gr(res):
    """Alto de la sección de granulometría para esta muestra.

    La tabla tiene una fila por tamiz de la serie vigente, y la serie de
    control de calidad es más corta que la de suelos. El alto se calcula con
    la serie que trae el resultado, en vez de con un número fijo: con el fijo,
    una muestra de afirmados dejaría dos filas en blanco al pie de la tabla y
    la banda de resultados quedaría desalineada del resto de secciones.

    El sobrante que deja la tabla más corta no estira nada: la diagramación
    apila las secciones de arriba abajo y el espacio que queda va entre el
    cuerpo y el bloque de firmas (ver `_SECTIONS`).
    """
    filas = len(res.get("sieve") or ()) or 14
    band_top = filas * _GR_ROWH
    return band_top + _GR_BAND_GAP + _GR_BAND_H


_SECT_H_GR = 14 * _GR_ROWH + _GR_BAND_GAP + _GR_BAND_H   # referencia: serie de suelos

# altura fija de la sección de la curva granulométrica (pt): impuesta para
# garantizar que la banda de firmas (anclada al fondo) conserve su espacio.
_SECT_H_CHART = 172.0

SECTIONS = [
    ("page",                "Hoja carta completa (área útil)",                    0,  0, 100, 100),
    ("header",              "Logo + título | código / versión / página",           3,  2,  94,   6.25),
    ("project-info",        "Proyecto · fechas · descripción material",            3, 14,  94,   9),
    ("wl-wp-block",         "Tabla de pesos/límites + gráfica de fluidez (reservada)", 3, 27,  94,  18),
    ("granulometria-block", "Tabla granulometría + resultados/clasificación",      3, 45,  94,  27),
    ("grain-size-chart",    "Curva granulométrica semi-log",                       3, 72,  94,	26),
    ("firmas-block",        "Firmas de responsabilidad (encima del pie)",    3,  87,  94,   6),
    ("footer",              "Dirección / email",                                   3, 93,  94, 1.0),
]


#: Fuentes del reporte. Antes `_webfonts()` devolvía solo dos de las tres que
#: registraba: la itérica quedaba guardada en `_FONTS` pero era inalcanzable.
Fuentes = namedtuple("Fuentes", "fn fnb fni")


def _webfonts():
    """Resuelve (normal, negrita, itálica) y las cachea.

    Registra Segoe UI si está en la carpeta de fuentes de Windows, para poder
    dibujar `ω` y otros símbolos; si no, cae a las Helvetica de ReportLab.
    """
    if _FONTS:
        return Fuentes(_FONTS["fn"], _FONTS["fnb"], _FONTS["fni"])
    fn, fnb, fni = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
    try:
        from reportlab.lib import pdfmetrics
        from reportlab.lib.pdfencodings import WinAnsiEncoding  # noqa: F401
        from reportlab.pdfbase.ttfonts import TTFont
        fdir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts")
        fn_map = {"SegoeUI": "segoeui.ttf",
                  "SegoeUIB": "segoeuib.ttf",
                  "SegoeUII": "segoeuii.ttf"}
        base = "Helvetica"
        baseb = "Helvetica-Bold"
        basei = "Helvetica-Oblique"
        for tag, arch in fn_map.items():
            ya = os.path.join(fdir, arch)
            if os.path.isfile(ya):
                pdfmetrics.registerFont(TTFont(tag, ya))
                if tag == "SegoeUI":
                    fn = "SegoeUI"
                    base = "SegoeUI"
                elif tag == "SegoeUIB":
                    fnb = "SegoeUIB"
                    baseb = "SegoeUIB"
                else:
                    fni = "SegoeUII"
                    basei = "SegoeUII"
        if not base.startswith("Helvetica"):
            fn, fnb, fni = base, baseb, basei
    except Exception:
        fn, fnb, fni = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
    _FONTS.update(fn=fn, fnb=fnb, fni=fni)
    return Fuentes(fn, fnb, fni)


def _temp_prefix():
    """Prefijo de los archivos temporales, propio de cada copia instalada.

    El nombre incluye la carpeta del proyecto para que dos versiones de la
    app abiertas a la vez no se pisen el mismo archivo temporal: sin esto el
    preview de una versión se vería en la otra.
    """
    carpeta = os.path.basename(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return "gradplas_%s_" % carpeta


def san(s):
    for a, b in (("\u2265", ">="), ("\u2264", "<="), ("\u03a3", "Suma"),
                 ("\u2192", "->"), ("\u00b7", "*"), ("\u26a0", "[!]"),
                 ("\u2014", "-"), ("\u2013", "-"), ("\u00d7", "x"),
                 ("\u00b2", "^2"), ("\u00b1", "+/-"), ("\u2212", "-")):
        s = s.replace(a, b)
    return s


def _pos(xp, yp, wp, hp, ML, MB, CW, CH):
    """Convierte porcentajes (y desde arriba) a rect final (x, y, w, h) en pt."""
    x = ML + xp / 100.0 * CW
    y = MB + (100.0 - yp - hp) / 100.0 * CH
    w = wp / 100.0 * CW
    h = hp / 100.0 * CH
    return x, y, w, h


def _pilas(ML, MB, CW, CH, gap=GAP, alturas=None):
    """Apila las secciones a ancho completo con `gap` pt de separación.

    ANCLA FIJA (firmas + pie): las secciones de firmas (`firmas-block`) y
    pie de página (`PIE-block`/`footer`) se dibujan SIEMPRE en el mismo
    lugar, pegadas al fondo del área útil (el pie abajo y las firmas justo
    encima), con altura fija (su porcentaje de `SECTIONS`). No dependen del
    contenido: si cambian las demás secciones, el pie y las firmas jamás se
    desplazan.

    El resto de secciones (encabezado, datos de proyecto, wl-wp,
    granulometría y curva) apila en el espacio que queda ENCIMA de las
    firmas, repartido y centrado igual que antes. Devuelve
    [(nombre, desc, x, y, w, h), ...] en pt, ordenadas de arriba hacia
    abajo (y desde el borde inferior).
    """
    secs = [s for s in SECTIONS if s[0] != "page"]
    if alturas is None:
        hs = [hp / 100.0 * CH for _, _, _, _, _, hp in secs]
    else:
        hs = list(alturas)

    # bloques con ancla al fondo: los que la definición sitúa desde el 80 %
    # del alto hacia abajo (firmas-block 87 % y pie 93 %), en su orden.
    anclas, cuerpo = [], []
    for (nombre, desc, _, yp, _, hp), h in zip(secs, hs):
        (anclas if yp >= 80.0 else cuerpo).append((nombre, desc, hp, h))

    # Las secciones ancladas (firmas, pie) conservan su altura fija; el
    # reparto vertical real lo hace cada altura medida en `alturas`, así que
    # aquí no hace falta calcular ningún total.
    anchgap = 1.0                    # separación firmas <-> pie (ajustada)

    pilas = []
    # 1) firmas y pie anclados al borde inferior (pie abajo, firmas encima)
    yb = MB
    for nombre, desc, hp, _h in reversed(anclas):
        h_a = hp / 100.0 * CH
        pilas.append((nombre, desc, ML, yb, CW, h_a))
        yb += h_a + anchgap
    # 2) el resto de secciones apila desde el tope del área útil: la primera
    # sección (encabezado) queda pegada al margen superior, igual que el pie
    # respeta el margen inferior, de modo que los márgenes de la hoja quedan
    # visualmente simétricos. El sobrante, si lo hay, queda entre la última
    # sección del cuerpo y las firmas.
    tope = MB + CH
    offset = 0.0
    # El hueco va ANTES de cada sección, y se decide con el par (anterior,
    # esta). La primera sección va pegada al tope, sin hueco.
    #
    # Importa dónde se acumula: si el hueco se sumara después de colocar la
    # sección, estaría valorando el par (esta, siguiente) y el visible sería
    # el de la anterior, que es justo el que no se quiere cambiar.
    hueco_antes = 0.0
    for i, (nombre, desc, hp, h) in enumerate(cuerpo):
        if i:
            anterior = cuerpo[i - 1][0]
            hueco_antes = (_GR_CHART_GAP
                           if (anterior == "granulometria-block"
                               and nombre == "grain-size-chart") else gap)
        y = tope - offset - hueco_antes - h
        pilas.append((nombre, desc, ML, y, CW, h))
        offset += h + hueco_antes
    return pilas


# ---- header: bandas en fracciones del recuadro (derivadas de la tabla) ----
# x% de la grilla original: logo 3..33 (30/94), título 33..73 (40/94),
# código 73..97 (24/94); las 3 bandas ocupan todo el alto (12% == 100%).
_HEADER_BANDAS = (0.25, 0.55, 0.20)              # logo 25% | central 55% | código 20%
# filas de la código-tabla: 3 filas iguales (4/12 cada una).


def _dibujar_header(c, box, fn, fnb):
    """Replica la distribución del header: logo, título y código/versión/página.

    Fuente única en todo el header; solo la columna central va en negrilla."""
    from reportlab.lib import colors as rlcolors
    from reportlab.lib.utils import ImageReader
    C_DK = rlcolors.HexColor("#000000")

    LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "RAPITEST LOGO.png")
    SIZE = 8.0                                # fuente general del header
    SIZE_NIT = 6.5                            # NIT más pequeño que la empresa

    x, y, w, h = box
    fx = [0.0]
    for f in _HEADER_BANDAS:
        fx.append(fx[-1] + f)
    bandas = [("logo", 0), ("titulo", 1), ("codigo", 2)]

    for tag, i in bandas:
        bx = x + fx[i] * w
        bw = (fx[i + 1] - fx[i]) * w
        c.setLineWidth(0.5)
        c.setStrokeColor(C_DK)
        c.rect(bx, y, bw, h, stroke=1, fill=0)

        if tag == "logo":
            if os.path.isfile(LOGO):
                ir = ImageReader(LOGO)
                iw, ih = ir.getSize()
                PADX, PADY = 12.0, 8.0
                wimg = bw - 2.0 * PADX
                himg = wimg * ih / iw
                if himg > h - 2.0 * PADY:
                    himg = h - 2.0 * PADY
                    wimg = himg * iw / ih
                imgx = bx + (bw - wimg) / 2.0
                imgy = y + (h - himg) / 2.0
                c.drawImage(ir, imgx, imgy, wimg, himg, preserveAspectRatio=False)
            else:
                c.setFillColor(C_DK)
                c.setFont(fnb, SIZE)
                c.drawCentredString(bx + bw / 2.0, y + h / 2.0, "RAPITEST INGENIERÍA")

        elif tag == "titulo":
            midx = bx + bw / 2.0
            A, D = 0.728, 0.210              # ascensor/descensor por em (Segoe UI)

            # Los tres ensayos con su norma INV-E en dos renglones centrados.
            # El tamaño se ajusta hasta que el renglón más largo quepa en el
            # ancho de la banda.
            maxw = bw - 12.0
            renglones = ("HUMEDAD NATURAL \u2014 INV E-122  \u00b7  "
                         "GRANULOMETR\u00cdA \u2014 INV E-123",
                         "L\u00cdMITES DE ATTERBERG \u2014 INV E-125 / E-126")
            ENS_SIZE = 7.0
            while ENS_SIZE > 5.5 and max(c.stringWidth(r, fnb, ENS_SIZE)
                                         for r in renglones) > maxw:
                ENS_SIZE -= 0.5
            items = [("RAPITEST INGENIER\u00cdA LTDA.", SIZE),
                     ("NIT 830.052.363-2", SIZE_NIT),
                     None] + [(r, ENS_SIZE) for r in renglones]

            alto = sum(0.5 if it is None else it[1] * (A + D) for it in items)
            G = (h - alto) / (len(items) + 1)  # padding uniforme arriba/abajo/entre
            cursor = y + h - G                 # pila construida de arriba hacia abajo
            c.setFillColor(C_DK)
            for it in items:
                if it is None:
                    c.setLineWidth(0.5)        # divisor: mismo grosor que verticales
                    c.line(bx, cursor - 0.25, bx + bw, cursor - 0.25)
                    cursor -= 0.5 + G
                else:
                    txt, sz = it
                    c.setFont(fnb, sz)          # única columna en negrilla
                    c.drawCentredString(midx, cursor - sz * A, txt)
                    cursor -= sz * (A + D) + G

        elif tag == "codigo":
            ROW_H = h / 3.0                   # filas llenan exactamente la banda
            # El reporte se emite en una sola página, así que el total es 1.
            # Se interroga al canvas en vez de escribir "1 de 1" a mano: si
            # algún día el documento crece a varias páginas, el rótulo
            # seguirá siendo cierto en lugar de mentir.
            # OJO: "VERSIÓN" es la versión del FORMATO de laboratorio
            # (CÓDIGO F-LAB-001), no la versión de la aplicación.
            filas = [("CÓDIGO", "F-LAB-001"),
                     ("VERSIÓN", "1.0"),
                     ("PÁGINA", "%d de %d" % (c.getPageNumber(), 1))]
            c.setFont(fn, SIZE)               # misma fuente que columna central
            for j, (lb, val) in enumerate(filas):
                ry = y + h - (j + 1) * ROW_H
                c.setLineWidth(0.5)
                c.setStrokeColor(C_DK)
                c.rect(bx, ry, bw, ROW_H, stroke=1, fill=0)
                ty = ry + (ROW_H - SIZE) / 2.0
                c.setFillColor(C_DK)
                c.drawString(bx + 6, ty, lb)
                c.drawRightString(bx + bw - 6, ty, val)


_LABEL_IDENT = {
    "proyecto": "Proyecto",
    "sector": "Sector",
    "ordenado": "Ordenado por",
    "muestra": "Muestra N°",
    "fecha_toma": "Fecha de toma",
    "fecha_ejecucion": "Fecha de ejecución",
    "sondeo": "Perforación N°",
    "profundidad": "Profundidad (m)",
    "descripcion": "Color",
    "tipo": "Tipo",
    "alcance": "Alcance",
    "graduacion": "Tipo de graduación",
}


def _normalizar(t):
    import re
    import unicodedata
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t).strip().lower()


def _id_campo(datos, ident, key):
    """Devuelve el valor del campo `key` desde `datos['ident']` (dict) o la
    lista `ident` con entradas 'Etiqueta: valor' (formato de `app._ident`)."""
    d = datos.get("ident") if isinstance(datos, dict) else None
    if isinstance(d, dict):
        v = d.get(key)
        if v not in (None, ""):
            return str(v)
    et = _LABEL_IDENT.get(key)
    if et:
        esc = _normalizar(et)
        for linea in ident or []:
            if ":" in str(linea):
                lb, _, val = str(linea).partition(":")
                if _normalizar(lb) == esc:
                    return val.strip()
    return ""


def _tipo_muestra(datos, ident):
    """(tipo, graduación) para el encabezado del reporte.

    El tipo siempre tiene valor ("Suelos" por defecto). La graduación solo se
    imprime en control de calidad, y solo en los alcances que la llevan
    (afirmados, bases y subbases); en suelos, estructuras y drenajes, y
    pavimentos asfálticos no aparece.

    Ambas van en caja alta, como las demás celdas de datos del encabezado: son
    valores fijos de una lista cerrada, y escribirlos como venían dejaría la fila
    mezclando "Control de calidad" con "A-38".
    """
    tipo = (_id_campo(datos, ident, "tipo") or "Suelos").strip()
    es_cc = (tipo.lower() != "suelos")
    graduacion = ((_id_campo(datos, ident, "graduacion") or "").strip()
                  if es_cc else "")
    return tipo.upper(), graduacion.upper()


def _graduacion_de(datos, ident):
    """Solo la graduación, sin el tipo. La zona de filtro la usa."""
    return _tipo_muestra(datos, ident)[1]


def _desc_material(datos, res, ident):
    """Descripción del material en el reporte.

    La parte descriptiva la compone sola la app a partir de la clasificación
    SUCs (`descripcion_sucs`): es la que caracteriza el suelo sin repetir
    porcentajes ni coeficientes. El campo que ingresa el usuario es el COLOR,
    que es lo único que el laboratorio observa y la clasificación no puede
    deducir, así que se añade al final:

        "Arcillas de plasticidad alta, de color café oscuro con vetas grises"

    Si no hay color, se imprime solo la descripción automática.

    Toda la línea va en mayúsculas, como las demás celdas de datos del
    encabezado. El texto es una ficha del material, no una frase de lectura
    corrida: en minúsculas mezclaba "Grava limosa no plástica, de color café
    claro" con etiquetas como "PROYECTO" o "DESCRIPCIÓN MATERIAL" en caja alta,
    y se veía como si el valor fuera de otra fuente.

    La capitalización va al final, sobre la cadena completa, y no sobre el
    `auto` de `descripcion_sucs`: si se hiciera antes de encadenar el color, el
    "De color %s" perdería su mayúscula inicial y quedaría "DE COLOR café".
    """
    from motor.clasificacion import descripcion_sucs
    color = (_id_campo(datos, ident, "descripcion") or "").strip()
    color = color.strip(" .;,")
    auto = descripcion_sucs(res) if isinstance(res, dict) else ""
    if color:
        # `descripcion_sucs` ya cierra con punto; se quita para poder encadenar
        # la coma sin dejar "areno-gravosas., de color ...".
        auto = auto.rstrip(" .;,")
        texto = ("%s, de color %s" % (auto, color) if auto
                 else "De color %s" % color)
    else:
        texto = auto
    return texto.upper()


def _profundidad(datos, ident):
    """Profundidad con formato '10.00 m a 10.60 m'.

    Desde la lista de `app._ident` ya llega formateada ('Profundidad (m): ...');
    desde `datos['ident']` (dict) se combina prof_desde/prof_hasta con la unidad.
    """
    if not (isinstance(datos, dict) and isinstance(datos.get("ident"), dict)):
        v = _id_campo(datos, ident, "profundidad")
        if v:
            return v
    ds = _id_campo(datos, ident, "prof_desde")
    hs = _id_campo(datos, ident, "prof_hasta")
    ds = "" if ds in (None, "", "N.A.") else ds
    hs = "" if hs in (None, "", "N.A.") else hs
    if ds and hs:
        return "%s - %s m" % (ds, hs)
    if ds:
        return "%s m" % ds
    return ""


def _clip(c, txt, font, size, maxw):
    """Trunca `txt` con elipsis para que quepa en `maxw`."""
    if maxw <= 0 or c.stringWidth(txt, font, size) <= maxw:
        return txt
    corte = txt
    while corte and c.stringWidth(corte + "\u2026", font, size) > maxw:
        corte = corte[:-1]
    return corte + "\u2026"


#: Máximo de renglones de los campos de texto largo de la identificación
#: (proyecto y descripción del material). Con más renglones la fila crece,
#: empuja las secciones de abajo y el encuadre deja de ser el mismo entre
#: muestras: un proyecto con un nombre largo descuadraba el reporte entero.
MAX_LINEAS_IDENT = 2


def _partir(c, txt, font, size, maxw, maxlineas=8):
    """Envuelve `txt` por palabras hasta caber en `maxw` (p. ej. filas
    de texto largo). Devuelve la lista de líneas (acotada a `maxlineas`)."""
    palabras = (txt or "").split()
    if not palabras:
        return [""]
    lineas, actual = [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if not actual or c.stringWidth(prueba, font, size) <= maxw:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
            if len(lineas) >= maxlineas:
                break
    if actual and len(lineas) < maxlineas:
        lineas.append(actual)
    elif actual:
        lineas[-1] = _clip(c, actual, font, size, maxw)
    return lineas or [""]


#: Las dos filas de texto largo van acotadas a MAX_LINEAS_IDENT renglones. Las
#: de datos pareados (sector, fechas, tipo) no se envuelven.
_FILA_LARGA = (True, MAX_LINEAS_IDENT)


def _filas_ident(datos, res, ident):
    """Definición de las filas de la tabla de identificación.

    La usan las dos funciones de la sección: la que dibuja y la que mide. Si
    construyeran la lista por separado, agregar una fila en una y no en la otra
    descuadraría la tabla sin que nada avise.
    """
    proy = _id_campo(datos, ident, "proyecto")
    orden = _id_campo(datos, ident, "ordenado")
    sect = _id_campo(datos, ident, "sector")
    perf = _id_campo(datos, ident, "sondeo")
    mues = _id_campo(datos, ident, "muestra")
    f_toma = _id_campo(datos, ident, "fecha_toma")
    f_ejec = _id_campo(datos, ident, "fecha_ejecucion")
    prof = _profundidad(datos, ident)
    desc = _desc_material(datos, res, ident)
    tipo, graduacion = _tipo_muestra(datos, ident)

    # El alcance no se imprime: la graduación lo encarna ("BG-38" dice base y
    # no subbase), y el usuario pidió que en esa fila aparezca solo el tipo de
    # graduación. La fila se completa con el valor centrado en el ancho que
    # ocupaba el alcance, para que no quede un hueco a la derecha.
    celdas_grad = ([("label", "GRADACIÓN", "L2", "L3"),
                    ("centro", graduacion, "L3", 1.0)] if graduacion else [])
    filas = [
        # (es_larga, celdas); los rótulos de las columnas son nombres, no
        # números: las fracciones las pone quien dibuja, con la misma grilla.
        # `_FILA_LARGA` es (True, MAX_LINEAS_IDENT): el True dice que la fila
        # es de texto largo, y el número acota sus renglones.
        (_FILA_LARGA[0],
         [("label", "PROYECTO", 0, "L1"), ("texto", proy, "L1", 1.0)],
         _FILA_LARGA[1]),
        (_FILA_LARGA[0],
         [("label", "ORDENADO POR", 0, "L1"), ("texto", orden, "L1", 1.0)],
         _FILA_LARGA[1]),
        (False, [("label", "SECTOR", 0, "L1"), ("centro", sect, "L1", "L2"),
                 ("label", "MUESTRA", "L2", "L3"), ("centro", mues, "L3", 1.0)], 0),
        (False, [("label", "FECHA DE TOMA", 0, "L1"), ("centro", f_toma, "L1", "L2"),
                 ("label", "FECHA DE EJECUCIÓN", "L2", "L3"),
                 ("centro", f_ejec, "L3", 1.0)], 0),
        (False, [("label", "PERFORACIÓN", 0, "L1"), ("centro", perf, "L1", "L2"),
                 ("label", "PROFUNDIDAD", "L2", "L3"), ("centro", prof, "L3", 1.0)], 0),
        (False, [("label", "TIPO", 0, "L1"), ("centro", tipo, "L1", "L2")]
                 + celdas_grad, 0),
        (_FILA_LARGA[0],
         [("label", "DESCRIPCIÓN MATERIAL", 0, "L1"), ("desc", desc, "L1", 1.0)],
         _FILA_LARGA[1]),
    ]
    return filas


def _rohs_project_info(datos, res, ident):
    """Alturas (pt) de cada fila de identificación, en orden vertical.

    Las filas de texto largo crecen con las líneas envueltas; las pareadas
    tienen alto fijo. Las que existen dependen de los datos, y el alto sale de
    `_filas_ident`, la misma definición que usa el dibujo.
    """
    from reportlab.pdfgen import canvas as _canvas
    import tempfile
    fn = _webfonts().fn          # solo se mide con la fuente normal
    c = _canvas.Canvas(os.path.join(tempfile.gettempdir(),
                                    _temp_prefix() + "medicion.pdf"))
    L1, PAD = 0.234, 6.0
    SIZE, R0, LH = 8.0, 12.5, 10.0
    maxw = 468.0 * (1.0 - L1) - 2.0 * PAD

    def roh(larga, txto, tope):
        if not larga:
            return R0
        # `tope` es el máximo de renglones de la fila. Las de datos pareados no
        # lo fijan (0) y no se envuelven.
        n = max(1, len(_partir(c, txto or "", fn, SIZE, maxw,
                               maxlineas=tope or 8)))
        return max(R0, n * LH + 2.0)

    return [roh(larga, celdas[-1][1], tope)
            for larga, celdas, tope in _filas_ident(datos, res, ident)]


def _medir_project_info(datos, res, ident):
    """Alto (pt) total de la sección de identificación según su contenido."""
    return sum(_rohs_project_info(datos, res, ident))


def _alturas(datos, res, ident, CH):
    """Alturas (pt) de las secciones en el orden de `SECTIONS` (sin 'page')."""
    hs = []
    for s in SECTIONS:
        if s[0] == "page":
            continue
        if s[0] == "project-info":
            hs.append(_medir_project_info(datos, res, ident))
        elif s[0] == "wl-wp-block":
            hs.append(_SECT_H_WL)
        elif s[0] == "granulometria-block":
            hs.append(_alturas_gr(res))
        elif s[0] == "grain-size-chart":
            hs.append(_SECT_H_CHART)
        else:
            hs.append(s[5] / 100.0 * CH)
    return _repartir_chart(hs, CH)


def _repartir_chart(hs, CH):
    """Deja la separación de la curva como corresponde y le quita el alto.

    `_pilas` apila el cuerpo de arriba abajo y lo que sobra queda entre la
    última sección y las firmas. Ese sobrante se iba a un solo sitio y la
    separación extra entre granulometría y curva (`_GR_CHART_GAP`) nunca se
    veía: la curva conservaba su alto fijo y el hueco se quedaba igual.

    La curva se dibuja con un alto menor en la misma posición: su contenido
    (banda de denominaciones, marco, ejes y rótulos) se reparte dentro del alto
    que recibe, así que bajarlo lo acerca a las firmas, que es exactamente lo
    que hace falta para que el aire de arriba sea el pedido.
    """
    secs = [s for s in SECTIONS if s[0] != "page"]
    idx_ch = next(i for i, s in enumerate(secs) if s[0] == "grain-size-chart")
    anclas = sum(s[5] / 100.0 * CH for s in secs if s[3] >= 80.0)
    cuerpo = [i for i, s in enumerate(secs) if s[3] < 80.0]
    total = sum(hs[i] for i in cuerpo)
    n_gaps = len(cuerpo) - 1
    # hueco total disponible entre el tope del cuerpo y el bloque de firmas
    disponible = CH - anclas - 1.0
    sobrante = disponible - total - n_gaps * GAP
    if sobrante <= 0:
        return hs
    extra = _GR_CHART_GAP - GAP          # lo que hay que añadir al hueco
    if extra > sobrante:
        extra = sobrante                  # no hay espacio para tanto
    # el aire extra se lo queda la curva, que pierde ese alto
    hs[idx_ch] = max(80.0, hs[idx_ch] - extra)
    return hs


def _dibujar_project_info(c, box, fn, fnb, datos, res, ident):
    """Tabla de identificación con filas de texto adaptables a su contenido.

    - filas pareadas: alto fijo, datos ingresados centrados H+V;
    - filas de texto largo (Proyecto, Ordenado por, Descripción): el alto
      crece con las líneas envueltas y el texto va a la izquierda."""
    from reportlab.lib import colors as rlcolors
    C_DK = rlcolors.HexColor("#000000")
    SIZE = 8.0
    A, D = 0.728, 0.210
    PAD = 6.0
    LH = 10.0                      # alto de línea al envolver (8 pt)

    # grilla de columnas (misma para todas las filas: líneas alineadas)
    L1, L2, L3 = 0.234, 0.494, 0.70

    x, y, w, h = box
    maxw = w * (1.0 - L1) - 2.0 * PAD

    # Las filas vienen de `_filas_ident`, la misma definición que usa la
    # medición: así el dibujo y el alto no pueden separarse.
    filas = [(larga,
              [(tag, txt,
                {"L1": L1, "L2": L2, "L3": L3}[f0] if isinstance(f0, str) else f0,
                {"L1": L1, "L2": L2, "L3": L3}[f1] if isinstance(f1, str) else f1)
               for tag, txt, f0, f1 in celdas],
              tope)
             for larga, celdas, tope in _filas_ident(datos, res, ident)]

    # altos por fila (misma fuente que la medición de la sección)
    altos = _rohs_project_info(datos, res, ident)

    c.setFillColor(C_DK)
    ycur = y + h
    for (lag, celdas, tope), rowh in zip(filas, altos):
        top = ycur
        bot = top - rowh
        rmid = (top + bot) / 2.0

        # líneas envueltas para las celdas de texto largo, acotadas al máximo
        # de renglones de la fila (el mismo tope que usa la medición del alto)
        if lag:
            lineas = _partir(c, celdas[1][1] or "", fn, SIZE, maxw,
                             maxlineas=tope or 8)
            n = len(lineas)
            # baseline de la 1ª línea: centra la caja visual (diseño A/D)
            # del bloque de n líneas respecto al centro de la fila
            bas0 = rmid + ((n - 1) * LH + D * SIZE - A * SIZE) / 2.0
        else:
            lineas = []

        for tag, txt, f0, f1 in celdas:
            cx0 = x + f0 * w
            cx1 = x + f1 * w

            if tag == "label":
                c.setFont(fnb, SIZE)
                c.drawString(cx0 + PAD, ty_bas(rmid, A, D, SIZE), txt)
            elif tag == "texto":
                # texto largo: líneas envueltas, bloque visual centrado V
                for k, linea in enumerate(lineas):
                    c.setFont(fn, SIZE)
                    c.drawString(cx0 + PAD, bas0 - k * LH, linea)
            elif tag == "centro":
                c.setFont(fn, SIZE)
                c.drawCentredString((cx0 + cx1) / 2.0,
                                    ty_bas(rmid, A, D, SIZE), txt)
            elif tag == "desc":
                sucs = res.get("sucs") if isinstance(res, dict) else None
                px = cx0 + PAD
                for k, linea in enumerate(lineas):
                    _dib_desc_linea(c, linea, fn, fnb, SIZE, px,
                                    bas0 - k * LH, maxw, sucs)

        # separadores verticales internos de la fila
        c.setLineWidth(0.5)
        for tag, txt, f0, f1 in celdas[1:]:
            xx = x + f0 * w
            c.line(xx, bot, xx, top)

        ycur = bot

    # separadores horizontales entre filas (sin duplicar bordes)
    c.setLineWidth(0.5)
    yy = y + h
    for i in range(1, len(filas)):
        yy -= altos[i - 1]
        c.line(x, yy, x + w, yy)


def ty_bas(rmid, A, D, SIZE):
    """Baseline que centra el glifo (asc+desc) respecto a `rmid`."""
    return rmid - (A - D) / 2.0 * SIZE


def _dib_desc_linea(c, linea, fn, fnb, size, px, ty, maxw, sucs):
    """Dibuja una línea de la descripción del material.

    `sucs` se acepta por compatibilidad con llamadas antiguas, pero ya no se
    usa para nada: el texto que compone `descripcion_sucs` describe el suelo
    ("GRAVA LIMOSA NO PLÁSTICA, DE COLOR ...") y nunca incluye el símbolo, de
    modo que buscarlo aquí para ponerlo en negrilla no encontraba nada y toda la
    línea salía en la fuente normal. La negrilla la aporta la etiqueta
    "DESCRIPCIÓN MATERIAL" de la izquierda.
    """
    seg = [(linea, fn)]
    clave = (sucs or "").upper()
    if clave and clave in linea:
        pos = linea.rfind(clave)
        fin = pos + len(clave)
        if fin < len(linea) and linea[fin] == ")":
            fin += 1
        seg = [(linea[:pos], fn), (linea[pos:fin], fnb),
               (linea[fin:], fn)]
    for frag, font in seg:
        disp = _clip(c, frag, font, size, maxw)
        c.setFont(font, size)
        c.drawString(px, ty, disp)
        px += c.stringWidth(disp, font, size)
        maxw -= c.stringWidth(disp, font, size)
        if maxw <= 6:
            break


def _dib_wl_wp(c, box, fn, fnb, datos, res):
    """Bloque de límites de consistencia: tabla de pesos (LL/LP) a la
    izquierda y gráfica de fluidez (espacio reservado) a la derecha.

    # La tabla replica los casilleros de la planilla INV E-125/E-126 con
    # nombres técnicos subindicados y sus unidades (W_Recip (g), W_Agua (g),
    # Humedad (%)…). La tabla ocupa [0 … 55 %] del ancho del bloque, pegada
    # al borde izquierdo, y la zona de la curva de fluidez [55 … 100 %]
    # llega al borde derecho. Las columnas de datos (LL ×3, LP ×2 y ω)
    # tienen el mismo ancho; la columna de la izquierda (etiquetas) es
    # independiente y más angosta. El alto del bloque es exactamente la
    # suma de sus 9 filas (9 × 12.5 pt), las verticales se trazan en todas
    # las filas (incluida la última) y no hay fondos de color. La columna
    # ω muestra los datos del ensayo de humedad natural y la fila final la
    # humedad calculada de cada ensayo.
    """
    from reportlab.lib import colors as rlcolors
    C_DK = rlcolors.HexColor("#000000")
    C_MUT = rlcolors.HexColor("#6e7781")
    C_HEAD = rlcolors.HexColor("#e4e7eb")     # relleno del encabezado (gris claro)
    TAB_SIZE = 7.5                            # valores de las celdas
    TAB_SIZE_LABEL = 7.0                      # parte principal de las etiquetas
    SUB_SIZE = 5.0                            # tamaño de los subíndices
    UNIT_SIZE = 5.0                           # tamaño de las unidades "(g)"
    SUB_OFF = 1.35                            # descenso de los subíndices (pt)
    HDR_SIZE = 6.6                            # títulos (caben en la columna LP)
    A, D = 0.728, 0.210
    PADL = 2.0                                # sangría de etiquetas
    ROWH = 13.5                               # igual que en project-info (R0)

    x, y, w, h = box
    f_tab = (0.00, 0.55)                      # tabla hasta el borde izquierdo
    f_flow = (0.55, 1.00)                     # curva de fluidez hasta el derecho

    f_label = (0.00, 0.10)                    # columna de etiquetas (VARIABLE)
    # 6 columnas de datos del mismo ancho: 0.10..0.55 en partes de 0.075
    _cols = [0.10 + 0.075 * k for k in range(7)]
    f_ll = (_cols[0], _cols[1]), (_cols[1], _cols[2]), (_cols[2], _cols[3])
    f_lp = (_cols[3], _cols[4]), (_cols[4], _cols[5])
    f_hn = (_cols[5], _cols[6])               # columna de resultado ω / hum. natural

    ROWS = _ROWS_WL                           # encabezado + 8 filas de datos
    ROWH = _ROWH_WL
    top = y + h                               # alto de la sección = ROWS*ROWH

    # ---- datos: ingresados y calculados (nombres técnicos) ----
    ll = datos.get("ll") or []
    lp = datos.get("lp") or []
    hum = datos.get("hum") or {}
    np_ = bool(datos.get("ll_np"))

    def _v(rows, i, k):
        return rows[i].get(k) if i < len(rows) else None

    def _s(v, dec=2):
        return "" if v is None else ("%.*f" % (dec, v))

    def _ll(f, dec=2):
        return [""] * 3 if (np_ or not ll) else [
            _s(f(ll[i]), dec) if i < len(ll) else "" for i in range(3)]

    def _lp(f, dec=2):
        return [""] * 2 if (np_ or not lp) else [
            _s(f(lp[i]), dec) if i < len(lp) else "" for i in range(2)]

    def _rest(a, b):
        """a - b a prueba de valores incompletos (None)."""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a - b
        return None

    def _ws(v, dec=2):
        return "" if v is None else ("%.*f" % (dec, v))

    def _wseq(key, n):
        seq = res.get(key) or []
        return [_ws(seq[i], 2) if i < len(seq) else "" for i in range(n)]

    def _h(clave):
        """Valor ingresado del ensayo de humedad natural (columna ω) o ''."""
        v = hum.get(clave) if hum else None
        return "" if v is None else ("%.2f" % v)

    # Wc = recip (tara), W1 = hum (suelo húmedo + tara), W2 = seco (suelo seco
    # + tara); calculados: W_Agua = W1 - W2, W_Suelo = W2 - Wc. N°_Golpes = n,
    # N°_Recip = identificación del recipiente ingresada. La columna ω lleva
    # los datos del ensayo de humedad natural (id, Wc, W1, W2 y sus
    # resultados), y la fila Humedad (%) la humedad calculada de cada ensayo
    # (w = W_Agua / W_Suelo × 100, tomada del cálculo) en todas las columnas.
    filas = [
        # (principal, subíndice, unidad, LL ×3, LP ×2, ω)
        ("N°", "Recip", "",
         [ll[i].get("id", "") if i < len(ll) else "" for i in range(3)],
         [lp[i].get("id", "") if i < len(lp) else "" for i in range(2)],
         str(hum.get("id", "")) if hum else ""),
        ("W", "Recip", "g", _ll(lambda r: r["recip"]),
         _lp(lambda r: r["recip"]), _h("recip")),
        ("W", "Húmedo", "g", _ll(lambda r: r["hum"]),
         _lp(lambda r: r["hum"]), _h("hum")),
        ("W", "Seco", "g", _ll(lambda r: r["seco"]),
         _lp(lambda r: r["seco"]), _h("seco")),
        ("W", "Agua", "g", _ll(lambda r: _rest(r["hum"], r["seco"])),
         _lp(lambda r: _rest(r["hum"], r["seco"])), _ws(res.get("w_agua"))),
        ("W", "Suelo", "g", _ll(lambda r: _rest(r["seco"], r["recip"])),
         _lp(lambda r: _rest(r["seco"], r["recip"])), _ws(res.get("w_suelo"))),
        ("N°", "Golpes", "", _ll(lambda r: r["n"], 0), ["-", "-"], "-"),
        ("Humedad", "", "%", _wseq("ll_w", 3), _wseq("lp_w", 2),
         _ws(res.get("w_nat"))),
    ]

    # ---- encabezado: relleno gris claro ----
    c.setFillColor(C_HEAD)
    c.rect(x, top - ROWH, f_tab[1] * w, ROWH, stroke=0, fill=1)
    c.setFillColor(C_DK)

    # ---- líneas de la tabla ----
    c.setLineWidth(0.5)
    c.setStrokeColor(C_DK)
    # verticales: en el encabezado solo las de los extremos de cada título
    # (LÍMITE LÍQUIDO | LÍMITE PLÁSTICO | ω); en el cuerpo todas las
    # columnas, salvo en suelo no plástico donde LL y LP quedan fundidas
    # (un solo "NL" por campo) y solo se conservan sus bordes extremos.
    for i in range(1, ROWS + 1):              # i = fila (1 = encabezado)
        yt = top - (i - 1) * ROWH
        yb = yt - ROWH
        if i == 1 or np_:
            bounds = (0.10, 0.325, 0.475)
        else:
            bounds = _cols[:-1]
        for b in bounds:
            c.line(x + b * w, yb, x + b * w, yt)
    if np_:
        # sin plasticidad los campos LL y LP quedan fundidos ("No presenta"):
        # los separadores horizontales solo recorren la columna de etiquetas
        # y la de humedad natural (ω), salvo el que queda inmediatamente
        # debajo de los títulos LÍMITE LÍQUIDO / LÍMITE PLÁSTICO (se conserva).
        for i in range(1, ROWS):
            yy = top - i * ROWH
            if i == 1:
                c.line(x, yy, x + f_tab[1] * w, yy)
            else:
                c.line(x, yy, x + _cols[0] * w, yy)
                c.line(x + _cols[5] * w, yy, x + _cols[6] * w, yy)
    else:
        for i in range(1, ROWS):              # separadores entre filas
            c.line(x, top - i * ROWH, x + f_tab[1] * w, top - i * ROWH)
    # la divisoria tabla/curva (0.8 pt) se traza al final, sobre todos los
    # elementos, para que mantenga el grosor del borde exterior en toda su
    # longitud (incluida la fila de títulos ω / CURVA DE FLUIDEZ)

    # ---- textos ----
    c.setFillColor(C_DK)

    def ty_lab(rmid, sub):
        """Baseline principal que centra etiqueta (+ subíndice) en la fila."""
        if not sub:
            return ty_bas(rmid, A, D, TAB_SIZE_LABEL)
        return rmid - (A * TAB_SIZE_LABEL - SUB_OFF + D * SUB_SIZE) / 2.0

    # encabezado
    hmid = top - ROWH / 2.0
    c.setFont(fnb, HDR_SIZE)
    c.drawCentredString(x + (f_label[0] + f_label[1]) / 2.0 * w,
                        ty_bas(hmid, A, D, HDR_SIZE), "VARIABLE")
    c.drawCentredString(x + (f_ll[0][0] + f_ll[2][1]) / 2.0 * w,
                        ty_bas(hmid, A, D, HDR_SIZE), "LÍMITE LÍQUIDO")
    c.drawCentredString(x + (f_lp[0][0] + f_lp[1][1]) / 2.0 * w,
                        ty_bas(hmid, A, D, HDR_SIZE), "LÍMITE PLÁSTICO")
    c.drawCentredString(x + (f_hn[0] + f_hn[1]) / 2.0 * w,
                        ty_bas(hmid, A, D, HDR_SIZE), "ω")

    # cuerpo: etiqueta con subíndice y unidad + valores LL/LP/Hn
    for i, (main, sub, unidad, v3, v2, hn) in enumerate(filas, start=2):
        yt = top - (i - 1) * ROWH
        yb = yt - ROWH
        rmid = (yt + yb) / 2.0
        ty = ty_bas(rmid, A, D, TAB_SIZE)

        c.setFont(fnb, TAB_SIZE_LABEL)
        lx = x + f_label[0] * w + PADL
        bsub = ty_lab(rmid, sub)
        c.setFillColor(C_DK)
        c.drawString(lx, bsub, main)
        xx = lx + c.stringWidth(main, fnb, TAB_SIZE_LABEL)
        if sub:
            c.setFont(fnb, SUB_SIZE)
            c.drawString(xx + 0.7, bsub - SUB_OFF, sub)
            xx += 0.7 + c.stringWidth(sub, fnb, SUB_SIZE)
        if unidad:
            c.setFont(fnb, UNIT_SIZE)
            c.setFillColor(C_MUT)
            c.drawRightString(x + f_label[1] * w - PADL,
                              bsub - (SUB_OFF if sub else 0.6),
                              "(%s)" % unidad)

        c.setFont(fn, TAB_SIZE)
        c.setFillColor(C_DK)

        def pintar(a, b, txt):
            """Dibuja el valor centrado; el '-' (celda sin datos) en gris."""
            if not txt:
                return
            c.setFillColor(C_MUT if txt == "-" else C_DK)
            c.drawCentredString(x + (a + b) / 2.0 * w, ty,
                                _clip(c, txt, fn, TAB_SIZE, (b - a) * w - 1))

        if not np_:
            for (a, b), txt in zip(f_ll, v3):
                pintar(a, b, txt)
            for (a, b), txt in zip(f_lp, v2):
                pintar(a, b, txt)
        pintar(f_hn[0], f_hn[1], hn)

    # suelo no plástico: un "No presenta" centrado en cada campo (límite
    # líquido y límite plástico), cuyas columnas quedaron fundidas
    if np_:
        vmid = top - ((ROWS + 1) / 2.0) * ROWH   # centro de las filas de datos
        ty_nl = ty_bas(vmid, A, D, TAB_SIZE)
        c.setFont(fn, TAB_SIZE)
        c.setFillColor(C_DK)
        for a, b in ((_cols[0], _cols[3]), (_cols[3], _cols[5])):
            c.drawCentredString(x + (a + b) / 2.0 * w, ty_nl,
                                _clip(c, "No presenta", fn, TAB_SIZE,
                                      (b - a) * w - 1))

    # ---- gráfica de fluidez (Casagrande) ----
    import math
    # 5 pt de separación entre la tabla (límites + humedad) y la gráfica
    fx = x + f_flow[0] * w + 5.0
    fw = (f_flow[1] - f_flow[0]) * w - 5.0
    # título en una fila superior, de la misma forma que LÍMITE LÍQUIDO /
    # LÍMITE PLÁSTICO (relleno gris claro, negrilla centrada)
    c.setFillColor(C_HEAD)
    c.rect(fx, top - ROWH, fw, ROWH, stroke=0, fill=1)
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.5)
    c.line(fx, top - ROWH, fx + fw, top - ROWH)
    c.setFillColor(C_DK)
    c.setFont(fnb, HDR_SIZE)
    c.drawCentredString(fx + fw / 2.0,
                        ty_bas(top - ROWH / 2.0, A, D, HDR_SIZE),
                        "CURVA DE FLUIDEZ (w vs N)")

    # Plot semi-logarítmico: x = log10(nº de golpes) con rango 10..50, y = %
    # humedad lineal. El ancho se reparte según log10 (las marcas no quedan
    # equiespaciadas).
    RED = rlcolors.HexColor("#d32f2f")
    BRAND = rlcolors.HexColor("#014366")          # azul del logo RAPITEST
    C_GRID = rlcolors.HexColor("#c8cdd3")
    # La gráfica y sus rótulos aprovechan casi todo el espacio de la curva:
    # se recorta el aire de arriba y de la derecha para equilibrar el conjunto.
    pa_l = fx + 35.0             # margen izq.: rótulo vertical + valores del eje Y
    pa_r = fx + fw - 8.0
    pa_t = top - ROWH - 6.0
    pa_b = y + 18.0              # margen inf.: números X + rótulo "NÚMERO..."
    lx0, lx1 = math.log10(10.0), math.log10(50.0)

    def px(n):
        """Posición horizontal (pt) de n golpes, escala logarítmica 10..50."""
        return pa_l + (pa_r - pa_l) * (math.log10(n) - lx0) / (lx1 - lx0)

    def py(v, y_min, y_max):
        """Posición vertical (pt) del % de humedad, escala lineal."""
        return pa_t + (pa_b - pa_t) * (y_max - v) / (y_max - y_min)

    # pares (golpes → humedad) de los 3 ensayos del límite líquido
    pts = []
    llw = res.get("ll_w") or [None] * 3
    for i in range(3):
        n = ll[i].get("n") if i < len(ll) else None
        hv = llw[i] if i < len(llw) else None
        if isinstance(n, (int, float)) and isinstance(hv, (int, float)):
            pts.append((n, hv))

    # 1) grid y ejes
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.5)
    c.rect(pa_l, pa_b, pa_r - pa_l, pa_t - pa_b, stroke=1, fill=0)
    c.setLineWidth(0.35)
    c.setStrokeColor(C_GRID)
    for tg in (10, 20, 30, 40, 50):
        c.line(px(tg), pa_b, px(tg), pa_t)

    # rango Y con pasos "redondos" según los valores medidos (35..55 → 30..60)
    y_min = y_max = None
    y_ticks = []
    if pts:
        hs = [hv for _, hv in pts]
        lo, hi = min(hs), max(hs)
        rng = hi - lo if hi - lo > 1e-9 else max(abs(hi) * 0.2, 1.0)
        e = math.floor(math.log10(rng))
        step = None
        for s0 in (1, 2, 2.5, 5, 10):
            s = s0 * 10 ** e
            if rng / s <= 6.0:
                step = s
                break
        if step is None:
            step = 10 ** (e + 1)
        lo_v = math.floor(lo / step) * step
        hi_v = math.ceil(hi / step) * step
        if lo - lo_v < 0.15 * step:
            lo_v -= step
        if hi_v - hi < 0.15 * step:
            hi_v += step
        if hi_v - lo_v < step:
            hi_v = lo_v + step
        y_min, y_max = lo_v, hi_v
        v = y_min
        while v <= y_max + 1e-9:
            y_ticks.append(v)
            v += step
        c.setStrokeColor(C_GRID)
        c.setLineWidth(0.35)
        for v in y_ticks:
            yy = py(v, y_min, y_max)
            c.line(pa_l, yy, pa_r, yy)

    # 2) línea de tendencia (azul), recortada dentro del área del gráfico
    trend = None
    if len(pts) >= 2:
        Xs = [math.log10(n) for n, _ in pts]
        Ys = [hv for _, hv in pts]
        mx_, my_ = sum(Xs) / len(Xs), sum(Ys) / len(Ys)
        den = sum((x - mx_) ** 2 for x in Xs)
        if abs(den) > 1e-12:
            slope = sum((x - mx_) * (v - my_) for x, v in zip(Xs, Ys)) / den
            inter = my_ - slope * mx_
            trend = (slope, inter)
            x1, y1 = px(10.0), py(slope * lx0 + inter, y_min, y_max)
            x2, y2 = px(50.0), py(slope * lx1 + inter, y_min, y_max)

            def recortar(x1, y1, x2, y2):
                """Segmento recortado al rectángulo del plot (Liang-Barsky)."""
                dx, dy = x2 - x1, y2 - y1
                t0, t1 = 0.0, 1.0
                for p, q in ((-dx, x1 - pa_l), (dx, pa_r - x1),
                             (-dy, y1 - pa_b), (dy, pa_t - y1)):
                    if p == 0.0:
                        if q < 0:
                            return None
                        continue
                    t = q / p
                    if p < 0:
                        if t > t1:
                            return None
                        if t > t0:
                            t0 = t
                    else:
                        if t < t0:
                            return None
                        if t < t1:
                            t1 = t
                return (x1 + t0 * dx, y1 + t0 * dy,
                        x1 + t1 * dx, y1 + t1 * dy)

            seg = recortar(x1, y1, x2, y2)
            if seg:
                c.setStrokeColor(BRAND)
                c.setLineWidth(0.8)
                c.line(*seg)

    # 3) puntos de datos (los 3 ensayos): azul de marca con borde negro
    if pts:
        c.setFillColor(BRAND)
        c.setStrokeColor(C_DK)
        c.setLineWidth(0.6)
        for n, hv in pts:
            c.circle(px(n), py(hv, y_min, y_max), 1.9, stroke=1, fill=1)

    # 4) proyección en N = 25 (lectura del límite líquido): vertical desde el
    #    eje X y horizontal hasta el eje Y, punteadas en rojo
    if trend:
        slope, inter = trend
        y25 = slope * math.log10(25.0) + inter
        x25, y25p = px(25.0), py(y25, y_min, y_max)
        c.setStrokeColor(RED)
        c.setDash([2, 1.5], 0)
        c.setLineWidth(0.5)
        c.line(x25, pa_b, x25, y25p)
        c.line(x25, y25p, pa_l, y25p)
        c.setDash()

        # 5) marca "x" y valor de y25: centrado sobre la línea de rastreo, justo
        #    encima de ella (rojo)
        c.setLineWidth(0.7)
        rr = 2.0
        c.line(x25 - rr, y25p - rr, x25 + rr, y25p + rr)
        c.line(x25 - rr, y25p + rr, x25 + rr, y25p - rr)
        c.setFillColor(RED)
        c.setFont(fn, 5.0)
        c.drawCentredString((x25 + pa_l) / 2.0, y25p + 2.6, "%.1f" % y25)

    # 6) marcas del eje X (10, 20, 30, 40, 50) y rótulos de los ejes
    c.setFillColor(C_DK)
    c.setFont(fn, 5.0)
    for tg in (10, 20, 30, 40, 50):
        c.drawCentredString(px(tg), pa_b - 6.0, "%d" % tg)
    # el valor 25 con el mismo tamaño y color que el valor interpolado a 25 golpes
    c.setFillColor(RED)
    c.setFont(fn, 5.0)
    c.drawCentredString(px(25.0), pa_b - 6.0, "25")
    c.setFillColor(C_DK)
    c.setFont(fn, 6.0)
    c.drawCentredString((pa_l + pa_r) / 2.0, y + 5.5, "NÚMERO DE GOLPES")
    # valores del eje Y (escala "redonda" automática según los datos)
    c.setFont(fn, 5.0)
    for v in y_ticks:
        yy = py(v, y_min, y_max)
        c.drawRightString(pa_l - 3.5, yy - 1.7, "%g" % v)
    # rótulo vertical del eje Y: misma fuente (tamaño 6.0) que el rótulo
    # horizontal, y pegado al eje del lado izquierdo
    c.saveState()
    c.setFont(fn, 6.0)
    c.translate(fx + 16.0, (pa_t + pa_b) / 2.0)
    c.rotate(90)
    c.drawCentredString(0, 0, "HUMEDAD (%)")
    c.restoreState()

    if not pts:
        c.setFont(fn, TAB_SIZE if np_ else 6.0)
        c.setFillColor(C_DK if np_ else C_MUT)
        c.drawCentredString((pa_l + pa_r) / 2.0, (pa_t + pa_b) / 2.0,
                            "No presenta" if np_ else "Espacio reservado")

    # cierres: la tabla (límites + humedad) y la gráfica son cajas
    # independientes, cada una con su propio borde grueso (0.8 pt) y 5 pt de
    # separación entre ellas, sin ninguna línea/vínculo que las conecte.
    # Se trazan al final para que ningún elemento interno las interrumpa.
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.8)
    c.rect(x, y, f_tab[1] * w, h, stroke=1, fill=0)   # borde de la tabla
    c.rect(fx, y, fw, h, stroke=1, fill=0)            # borde de la gráfica


def _dib_granulometria(c, box, fn, fnb, datos, res):
    """Bloque de granulometría: tabla completa de tamices al ~70 % del ancho
    y, a la derecha y separada por `GAP`, una sección de resultados
    (humedad natural, límites, índices y clasificación). Cada parte es una
    caja independiente con su propio borde grueso (0.8 pt) y sin vínculo
    entre ellas.

    La tabla replica la estética de límites/humedad: usa la misma altura de
    fila (_GR_ROWH), la grilla queda completa (verticales también en la fila
    de encabezado) y el alto de la sección se ajusta exacto al número de
    filas de la serie vigente (`_alturas_gr`). De esta forma todas las filas
    tienen la misma altura y la tabla no deja filas en blanco.
    La sección de resultados se dibuja con las mismas fuentes/tamaños de la
    tabla (TAB_SIZE 7.5 / TAB_SIZE_LABEL 7.0) y cada variable ocupa su propia
    fila."""
    from reportlab.lib import colors as rlcolors
    C_DK = rlcolors.HexColor("#000000")
    C_MUT = rlcolors.HexColor("#6e7781")
    C_HEAD = rlcolors.HexColor("#e4e7eb")     # relleno del encabezado
    A, D = 0.728, 0.210
    TAB_SIZE = 7.5                            # valores de las celdas de la tabla
    TAB_SIZE_LABEL = 7.0                      # etiquetas de la tabla (límites)
    SUB_SIZE = 5.0                            # unidades/abreviaturas pequeñas
    HDR_SIZE = 6.6                            # títulos del encabezado de bloque
    PADX = 3.0                                # aire horizontal de las celdas
    f_tab = 0.70                              # la tabla ocupa el 70 % del ancho
    # Encabezado + una fila por tamiz de la serie vigente. Con un número fijo
    # quedaban filas en blanco al pie de una muestra de control de calidad, que
    # tiene menos tamices, y la grilla se cerraba más abajo que el contenido.
    sieve = res.get("sieve") or []
    ROWS = len(sieve) + 1 if sieve else 14
    rh = _GR_ROWH                             # 12.5 pt, igual que límites
    NC = 6                                    # columnas de la tabla

    x, y, w, h = box
    top = y + h
    htab = ROWS * rh                         # alto de tabla + resultados
    y_tab = top - htab                       # borde inferior de tabla + resultados
    tw = f_tab * w
    rx = x + tw + GAP                         # borde izquierdo de resultados
    rw = w - tw - GAP
    cwest = tw / NC

    def fmt(v, dec=2):
        return "" if v is None else ("%.*f" % (dec, v))

    def fmt_g(v):
        return "" if v is None else "%g" % v

    def ty_cel(row_top, size):
        return ty_bas(row_top - rh / 2.0, A, D, size)

    # ---- tabla de granulometría (70 %) ----
    # fila de encabezado (banda gris clara)
    hedr = top - rh                          # filas a tope: sin aire interior
    c.setFillColor(C_HEAD)
    c.rect(x, hedr, tw, rh, stroke=0, fill=1)
    c.setFont(fnb, HDR_SIZE)
    c.setFillColor(C_DK)
    enc = ("TAMIZ", "\u00d8 (mm)", "PESO RET. (g)", "% RET.", "% ACUM.", "% PASA")
    ty_h = ty_bas(hedr + rh / 2.0, A, D, HDR_SIZE)   # centrado dentro de la banda
    for k, t in enumerate(enc):
        c.drawCentredString(x + (k + 0.5) * cwest, ty_h,
                            _clip(c, t, fnb, HDR_SIZE, cwest - PADX))

    # cuerpo: una fila por tamiz (+ fondo)
    c.setFont(fn, TAB_SIZE)
    for i, s in enumerate(sieve, start=1):
        yb = hedr - i * rh                   # borde inferior de la fila
        es_fondo = (s["diam"] or 0.0) <= 0.0      # la fila del fondo no pasa
        vals = (s["tamiz"],
                ("\u2014" if es_fondo else fmt_g(s["diam"])),
                fmt(s["w"]), fmt(s["ret_p"]), fmt(s["acum_p"]),
                ("\u2014" if es_fondo else fmt(s["pasa"])))
        c.setFillColor(C_DK)
        ty = ty_cel(yb + rh, TAB_SIZE)       # centro de la fila i
        c.drawCentredString(x + cwest / 2.0, ty,
                            _clip(c, vals[0], fn, TAB_SIZE, cwest - PADX))
        for k in range(1, NC):
            if vals[k]:
                c.drawCentredString(x + (k + 0.5) * cwest, ty,
                                    _clip(c, vals[k], fn, TAB_SIZE,
                                          cwest - PADX))

    # la grilla (separadores 0.5) se traza sobre el cuerpo completo.
    # verticales en TODAS las filas (incluida la de encabezado) y una línea
    # horizontal bajo el encabezado más una por cada fila de datos.
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.5)
    for k in range(1, NC):
        c.line(x + k * cwest, y_tab, x + k * cwest, top)
    c.line(x, hedr, x + tw, hedr)             # bajo el encabezado
    for i in range(1, ROWS - 1):
        c.line(x, hedr - i * rh, x + tw, hedr - i * rh)

    # ---- resultados (30 % restante) ----
    # "RESULTADOS" flotando encima (sin celda); debajo, tres tablas
    # independientes (humedad / límites / clasificación) separadas 5 px en
    # vertical, cada una con su borde y su subtítulo en banda gris. Los
    # valores van como campos fijos subrayados:  "LL: ____".
    TH = 11.0                                 # fila de subtítulo
    gapT = 5.0                                # separación vertical entre tablas
    NFILAS = 8                                # variables con resultado
    TZ = 14.0                                 # zona del título flotante
    VH = (htab - TZ - 3 * TH - 2 * gapT) / NFILAS  # reparte la altura de la tabla+resultados
    f_fld = 42.0                              # ancho fijo del campo subrayado
    campo_x = rx + rw - PADX - f_fld          # borde izquierdo del campo
    lw_lab = campo_x - rx - 2 * PADX - 4      # ancho disponible de la etiqueta

    c.setFont(fnb, 8.0)
    c.setFillColor(C_DK)
    c.drawCentredString(rx + rw / 2.0, top - 9.0, "RESULTADOS")

    fmt1 = lambda v: "\u2014" if v is None else "%.1f" % v   # 1 decimal (resultados)
    fmt2 = lambda v: "\u2014" if v is None else "%.2f" % v   # 2 decimales (banda)
    cur = top - TZ                          # debajo del título flotante
    boxes = []                                # cajas de cada sub-tabla
    t_top = None

    def subtitulo(txt):
        nonlocal cur
        c.setFillColor(C_HEAD)
        c.rect(rx, cur - TH, rw, TH, stroke=0, fill=1)
        c.setFont(fnb, 6.8)
        c.setFillColor(C_DK)
        c.drawCentredString(rx + rw / 2.0, ty_bas(cur - TH / 2.0, A, D, 6.8),
                            txt.upper())
        cur -= TH

    def fila(label, unidad, txt):
        nonlocal cur
        row_arm = cur - VH                    # borde inferior de la fila
        bas = ty_bas(cur - VH / 2.0, A, D, TAB_SIZE_LABEL)
        c.setFont(fnb, TAB_SIZE_LABEL)
        c.setFillColor(C_DK)
        c.drawString(rx + PADX, bas,
                     _clip(c, label + ":", fnb, TAB_SIZE_LABEL, lw_lab))
        if unidad:
            ux = rx + PADX + c.stringWidth(label + ":", fnb,
                                           TAB_SIZE_LABEL) + 1.5
            c.setFont(fnb, SUB_SIZE)
            c.setFillColor(C_MUT)
            c.drawString(ux, ty_bas(cur - VH / 2.0, A, D, SUB_SIZE) - 0.5,
                         "(%s)" % unidad)
        c.setStrokeColor(C_DK)
        c.setLineWidth(0.5)
        c.line(campo_x, row_arm + 1.5, campo_x + f_fld, row_arm + 1.5)  # subrayado
        c.setFont(fn, TAB_SIZE)
        c.setFillColor(C_MUT if txt in ("\u2014", "") else C_DK)
        c.drawCentredString(campo_x + f_fld / 2.0, row_arm + 6.0,
                            _clip(c, txt or "\u2014", fn, TAB_SIZE, f_fld))
        cur -= VH

    def abrir():
        nonlocal t_top
        t_top = cur

    def cerrar():
        nonlocal t_top
        boxes.append((t_top, cur))
        t_top = None

    abrir()
    subtitulo("Humedad natural")
    fila("w", "%", fmt1(res.get("w_nat")))
    cerrar()
    cur -= gapT

    abrir()
    subtitulo("L\u00edmites de consistencia")
    fila("LL", "%", fmt1(res.get("LL")))
    fila("LP", "%", fmt1(res.get("LP")))
    fila("IP", "%", fmt1(res.get("IP")))
    fila("Liquidez", "IL", fmt2(res.get("IL")))
    fila("Consistencia", "IC", fmt2(res.get("IC")))
    cerrar()
    cur -= gapT

    abrir()
    subtitulo("Clasificaci\u00f3n")
    fila("SUCs", None, res.get("sucs") or "\u2014")
    fila("AASHTO", None, res.get("aashto") or "\u2014")
    cerrar()

    # bordes por sub-tabla (0.8) sin separadores internos
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.8)
    for yt, yb in boxes:
        c.rect(rx, yb, rw, yt - yb, stroke=1, fill=0)

    # ---- banda inferior: parámetros granulométricos (ancho completo) ----
    # W1/W2 · D60/D30/D10 · Cu/Cc · % grava/arena/finos, con la misma
    # estética de "etiqueta: ____" de la columna de resultados. Sin subtítulo:
    # las dos filas de campos arrancan en el borde superior de la banda.
    band_top = y_tab - _GR_BAND_GAP
    band_bot = band_top - _GR_BAND_H
    cellw = w / 5.0
    f_fld_b = 42.0                            # ancho fijo del campo de la banda
    lw_lab_b = cellw - 2 * PADX - 4 - f_fld_b  # ancho disponible de la etiqueta

    c.setStrokeColor(C_DK)
    c.setLineWidth(0.8)
    c.rect(x, band_bot, w, _GR_BAND_H, stroke=1, fill=0)

    def campo_banda(label, unidad, valor, k, row_top):
        """Campo "label: ____ (unidad)" dentro de una celda de la banda."""
        rt = row_top
        rb = rt - _GR_BAND_VH
        cx = x + k * cellw
        fx = cx + cellw - PADX - f_fld_b
        bas = ty_bas(rt - _GR_BAND_VH / 2.0, A, D, TAB_SIZE_LABEL)
        c.setFont(fnb, TAB_SIZE_LABEL)
        c.setFillColor(C_DK)
        c.drawString(cx + PADX,
                     bas,
                     _clip(c, label + ":", fnb, TAB_SIZE_LABEL, lw_lab_b))
        if unidad:
            ux = cx + PADX + c.stringWidth(label + ":", fnb,
                                           TAB_SIZE_LABEL) + 1.5
            c.setFont(fnb, SUB_SIZE)
            c.setFillColor(C_MUT)
            c.drawString(ux, ty_bas(rt - _GR_BAND_VH / 2.0, A, D, SUB_SIZE) - 0.5,
                         "(%s)" % unidad)
        c.setStrokeColor(C_DK)
        c.setLineWidth(0.5)
        c.line(fx, rb + 1.5, fx + f_fld_b, rb + 1.5)
        c.setFont(fn, TAB_SIZE)
        c.setFillColor(C_MUT if valor in ("\u2014", "") else C_DK)
        c.drawCentredString(fx + f_fld_b / 2.0, rb + 6.0,
                            _clip(c, valor or "\u2014", fn, TAB_SIZE, f_fld_b))

    r1 = band_top - _GR_BAND_PAD
    g_tot = res.get("g_total")
    g_fon = res.get("fondo")
    w2 = (g_tot - g_fon) if (g_tot is not None and g_fon is not None) else None
    fila1 = (("W1", "g", fmt2(g_tot)), ("W2", "g", fmt2(w2)),
             ("D60", "mm", fmt2(res.get("D60"))),
             ("D30", "mm", fmt2(res.get("D30"))),
             ("D10", "mm", fmt2(res.get("D10"))))
    # Grava + Arena + Finos deben sumar 100 % en lo impreso. El motor ya
    # entrega estos tres valores redondeados a 1 decimal de forma coherente
    # (`g_grava_1d` / `g_arena_1d` / `g_finos_1d`, con Finos por diferencia),
    # y son las mismas claves que lee el resumen de la interfaz: pantalla y
    # papel no pueden diferir. El respaldo cubre datos que lleguen de otro
    # origen sin esas claves.
    gv, ar, fi = res.get("g_grava"), res.get("g_arena"), res.get("g_finos")
    gv_1d, ar_1d, fi_1d = (res.get("g_grava_1d"), res.get("g_arena_1d"),
                          res.get("g_finos_1d"))
    if None not in (gv_1d, ar_1d, fi_1d):
        c_grava, c_arena, c_finos = "%.1f" % gv_1d, "%.1f" % ar_1d, "%.1f" % fi_1d
    elif gv is not None and ar is not None:
        gv_r, ar_r = round(gv, 1), round(ar, 1)
        c_grava = "%.1f" % gv_r
        c_arena = "%.1f" % ar_r
        c_finos = "%.1f" % round(100.0 - gv_r - ar_r, 1)
    else:
        c_grava, c_arena, c_finos = fmt1(gv), fmt1(ar), fmt1(fi)
    campos = (("Cu", None, fmt2(res.get("Cu"))),
             ("Cc", None, fmt2(res.get("Cc"))),
             ("Grava", "%", c_grava),
             ("Arena", "%", c_arena),
             ("Finos", "%", c_finos))
    for k, cel in enumerate(fila1):
        campo_banda(*cel, k, r1)
    for k, cel in enumerate(campos):
        campo_banda(*cel, k, r1 - _GR_BAND_VH)

    # cierre: borde grueso de la tabla de granulometría
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.8)
    c.rect(x, y_tab, tw, htab, stroke=1, fill=0)     # borde de la tabla



def _dibujar_zona_filtro(c, XLOG, YP, px0, px1, py0, py1, res, pts_curva):
    """Proyecta sobre la curva la zona de filtro del material.

    Son dos líneas de % que pasa, una por debajo de la especificación y otra
    por encima, y la franja sombreada entre ellas. Se dibuja por debajo de la
    curva: lo medido tiene que leerse por encima del límite, no al revés.

    `pts_curva` son las coordenadas ya proyectadas de la curva del ensayo.

    Ojo con el eje: XLOG devuelve x MÁS grande cuanto MÁS FINO es el tamiz
    (100 mm a la izquierda, 0.01 mm a la derecha). La zona se dibuja sobre su
    propio recorrido, del tamiz más grueso al más fino, y de ahí sale sola la
    forma: la línea superior arranca en un tamiz más fino que la inferior, así
    que el tramo que le falta se cierra con un horizontal al 100 %.

    Sin graduación, o con una graduación de la que no hay zona cargada, no se
    dibuja nada: una zona inventada sería peor que ninguna.
    """
    from reportlab.lib import colors as rlcolors
    from motor.zonas import zona_de, puntos_de
    if not isinstance(res, dict):
        return
    graduacion = res.get("graduacion") or ""
    par = zona_de(graduacion)
    if par is None:
        return
    sie = res.get("sieve") or []
    diametros = {s["tamiz"]: s["diam"] for s in sie if s.get("diam")}
    inf = puntos_de(par[0], diametros)
    sup = puntos_de(par[1], diametros)
    if len(inf) < 2 or len(sup) < 2:
        return

    # La línea superior no llega al tamiz más grueso de la inferior: ese
    # tramo se cierra al 100 %, que es donde las dos coinciden en un material
    # que cumple por arriba.
    d_max_sup = sup[0][0]
    sup = [(d, 100.0) for d, _p in inf if d > d_max_sup] + sup
    if len(sup) < 2:
        return

    CL_ZONA = rlcolors.HexColor("#B8860B")   # ocre de la zona de filtro

    def _proyecta(linea):
        # De mayor a menor diámetro, que es de izquierda a derecha en el eje.
        return [(XLOG(d), YP(p)) for d, p in linea]

    inf_p = _proyecta(inf)
    sup_p = _proyecta(sup)

    # franja entre las dos líneas
    c.saveState()
    c.setFillColor(CL_ZONA)
    c.setFillAlpha(0.16)
    p = c.beginPath()
    p.moveTo(inf_p[0][0], inf_p[0][1])
    for x, y in inf_p[1:]:
        p.lineTo(x, y)
    for x, y in reversed(sup_p):
        p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()

    # las dos líneas de límite
    c.saveState()
    c.setStrokeColor(CL_ZONA)
    c.setLineWidth(0.8)
    c.setDash([2.5, 2.0], 0)
    for linea in (inf_p, sup_p):
        p = c.beginPath()
        p.moveTo(linea[0][0], linea[0][1])
        for x, y in linea[1:]:
            p.lineTo(x, y)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def _dib_grain_size_chart(c, box, fn, fnb, res):
    """Curva granulom\u00e9trica de suelos (semilogar\u00edtmica).

    Replica el gr\u00e1fico de Excel de la imagen original: eje X log\u00a0base 10
    (100 \u2192 0.01 mm, invertido), etiquetas s\u00f3lo en las d\u00e9cadas, eje Y
    lineal 0\u2013100 con etiquetas a la derecha y t\u00edtulo rotado a la
    izquierda, cuadr\u00edcula fina (10 % y 1\u20269 \u00d7 10\u207f), l\u00edneas de l\u00edmite
    de tama\u00f1o en azul de la identidad (gruesas para divisiones principales
    y finas para las menores), curva de distribuci\u00f3n en el azul oscuro de la
    curva de fluidez con puntos circulares de marca, y encabezado
    clasificatorio de dos filas como una tabla (GRAVA | ARENA | LIMO Y
    ARCILLA sobre Gruesa | Fina | Gruesa | Media | Fina).
    El eje X se ancla en 75 mm (inicio de la curva) y 0.075 mm (fin)."""
    import math
    from reportlab.lib import colors as rlcolors

    # ---- zonas dentro de la caja ----
    # Aire interior uniforme: todos los componentes de la gráfica (banda de
    # tamaños, marco, ejes y rótulos) quedan separados del borde de la sección
    # por el mismo `PAD`, para que nada se pegue al recuadro exterior.
    PAD = 7.0                   # aire interior uniforme respecto a la sección
    PAD_B = 3.0                 # aire interior inferior (zona baja, comprimida)
    H_HDR = 20.0                # encabezado clasificatorio (tabla de dos filas)
    # Aire entre la banda del encabezado clasificatorio (GRAVA | ARENA | LIMO
    # Y ARCILLA, y sus Divisions Gruesa/Media/Fina) y el área de trazado. Sin
    # él, la banda toca el marco de la curva y ambas zonas se leen como una.
    SEP_HDR = 4.0
    IZQ = 16.0                  # columna del titulo Y rotado
    DER = 16.0                  # valores del eje Y (derecha, fuera del marco)
    INF = 18.0                  # etiquetas eje X (décadas, límites y título)
    # Separación entre el área trazada y los rótulos de abajo. Las etiquetas
    # de tamaños van pegadas al eje, como estaban.
    EIX_LBL = 6.0               # línea base de los rótulos de tamaños
    EIX_TIT = 12.0              # línea base del título del eje X
    x, y, w, h = box
    x0, y0, w0, h0 = x + PAD, y + PAD_B, w - 2.0 * PAD, h - PAD - PAD_B
    top = y0 + h0               # borde superior del contenido (inset del borde)
    px0 = x0 + IZQ
    py0 = y0 + INF                      # borde inferior del area de trazado (0 %)
    py1 = top - H_HDR - SEP_HDR         # borde superior del area de trazado (100 %)
    px1 = px0 + (w0 - IZQ - DER)
    pw = px1 - px0
    ph = py1 - py0

    CL_NEGRO = rlcolors.HexColor("#000000")
    CL_GRID = rlcolors.HexColor("#c8cdd3")
    CL_BRAND = rlcolors.HexColor("#014366")     # azul de la identidad RAPITEST
    CL_LIM = rlcolors.HexColor("#014366")       # l\u00edmites principales (grs/arena/finos)
    CL_LIM_MIN = rlcolors.HexColor("#8FABC8")   # l\u00edmites menores (divisiones de la arena)
    C_HEAD = rlcolors.HexColor("#e4e7eb")     # banda del encabezado (como tablas)
    C_MUT = rlcolors.HexColor("#6e7781")      # gris apagado (rotulos secundarios)

    A, D = 0.728, 0.210                  # ascensor/descensor por em (Segoe UI)

    def XLOG(d):
        # diametro d en [0.01, 100]; 100 a la izquierda, 0.01 a la derecha
        return px0 + pw * (2.0 - math.log10(max(d, 1e-6))) / 4.0

    def YP(p):
        # p %% que pasa, 0 abajo, 100 arriba
        return py0 + ph * p / 100.0

    # ---- datos de la curva ----
    # No se dibuja curva si no hay granulometría real que graficar. Lo que
    # cuenta son los tamices con peso efectivamente ingresado, y no los
    # puntos de la curva: los tamices vacíos aportan 0 al acumulado, así que
    # el %pasa siempre trae 11 valores y una curva "plana al 100 %" parecería
    # un ensayo verdadero con cero material. La fila FONDO se excluye por
    # tener diámetro 0 (su peso es el resto, no un tamizado). Antes, con
    # menos de 3 puntos se trazaba una curva de diseño de ejemplo; ese caso
    # además era inalcanzable, porque nunca se daban menos de 3 puntos.
    pts = []
    sie = res.get("sieve") if isinstance(res, dict) else None
    con_peso = 0
    if sie:
        con_peso = sum(1 for s in sie
                       if s.get("w") is not None and s.get("diam"))
        # La curva arranca en el tamiz INMEDIATAMENTE ANTERIOR al primero que
        # retiene. Los tamices de arriba están todos al 100 % y dibujarlos
        # extendía una línea plana que cruzaba de lado a lado la zona de los
        # tamaños de partícula, invadiendo el área de la grava gruesa y el
        # encabezado de la gráfica. Con este recorte la curva empieza justo
        # donde el material empieza a tamizarse.
        pesados = [i for i, s in enumerate(sie)
                  if s.get("w") is not None and s.get("diam")]
        ini = max(0, pesados[0] - 1) if pesados else 0
        raw = [(s.get("diam"), s.get("pasa")) for s in sie[ini:]]
        raw = [(d, p) for (d, p) in raw if d and d > 0.0 and p is not None]
        pts = list(sorted(raw, key=lambda r: -r[0]))
    sin_datos = con_peso == 0 or len(pts) < 3
    if sin_datos:
        pts = []
    pts = [(dd, pp) for (dd, pp) in pts if 0.075 <= dd <= 100.0]
    pts = [(XLOG(dd), YP(pp)) for (dd, pp) in pts]

    # ---- orden de capas: banda, cuadricula, limites, curva, puntos ----
    #    Empieza SEP_HDR por encima del marco, para que quede el aire
    #    que la separa del area de la curva.
    c.setFillColor(C_HEAD)
    c.rect(px0, py1 + SEP_HDR, pw, H_HDR, stroke=0, fill=1)
    # cuadricula horizontal cada 10 %
    c.setStrokeColor(CL_GRID)
    c.setLineWidth(0.35)
    for p in range(0, 101, 10):
        yy = YP(p)
        c.line(px0, yy, px1, yy)
    # 2) cuadricula vertical semilog: 1..9 x 10^n por decada (n de -2 a 1)
    for n in range(-2, 2):
        for k in range(1, 10):
            d = k * 10.0 ** n
            c.line(XLOG(d), py0, XLOG(d), py1)
    # 3) lineas de limite entre tamanos de grano. Divisiones principales
    #    (gravas/arenas y finos, y grava gruesa/fina) en azul identidad
    #    grueso; divisiones menores (arena gruesa/media/fina) en azul claro
    #    fino. Trazadas sobre la cuadricula, bajo la curva, en discontinuo
    #    para no competir con la curva ni con la cuadricula.
    c.setStrokeColor(CL_LIM)
    c.setLineWidth(0.75)
    c.setDash([3.0, 2.0], 0)
    for d in (4.75, 0.075):
        xx = XLOG(d)
        c.line(xx, py0, xx, py1)
    c.setStrokeColor(CL_LIM_MIN)
    c.setLineWidth(0.75)
    c.setDash([2.0, 2.0], 0)
    for d in (19.0, 2.0, 0.425):
        xx = XLOG(d)
        c.line(xx, py0, xx, py1)
    c.setDash()
    # 4) zona de filtro del material: dos líneas de % que pasa y la franja
    #    entre ellas. Va bajo la curva para que se vea cuál es el dato medido y
    #    cuál el límite de la especificación.
    _dibujar_zona_filtro(c, XLOG, YP, px0, px1, py0, py1, res, pts)

    # 5) curva negra (Catmull-Rom, sutil, con 2 puntos control por tramo)
    if len(pts) >= 2:
        def _seg(p0, p1, p2, p3):
            return ((p1[0], p1[1]),
                    (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0),
                    (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0),
                    (p2[0], p2[1]))
        path = c.beginPath()
        path.moveTo(pts[0][0], pts[0][1])
        for i in range(len(pts) - 1):
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else p2
            a, c1, c2, b = _seg(p0, p1, p2, p3)
            path.curveTo(c1[0], c1[1], c2[0], c2[1], b[0], b[1])
        c.setStrokeColor(CL_BRAND)
        c.setLineWidth(1.0)
        c.setLineJoin(1)
        c.setLineCap(1)
        c.drawPath(path, stroke=1, fill=0)
        c.setLineJoin(0); c.setLineCap(0)
    # 6) puntos de datos: círculo azul macizo, sin borde negro y más pequeño.
    #    El borde negro sobre un trazo ya fino lo engordaba y los marcadores
    #    parecían más pesados que la propia curva.
    c.setFillColor(CL_BRAND)
    c.setStrokeColor(CL_BRAND)
    c.setLineWidth(0.3)
    for (mx, my) in pts:
        c.circle(mx, my, 0.9, stroke=0, fill=1)
    # 6) marco negro del area de trazado
    c.setStrokeColor(CL_NEGRO)
    c.setLineWidth(0.5)
    c.rect(px0, py0, pw, ph, stroke=1, fill=0)
    # 7) sin datos suficientes: se rotula el area vacia. Se dibuja la
    # cuadricula y las lineas de limite, pero ninguna curva, para que la
    # hoja siga siendo presentable sin sugerir un resultado inexistente.
    if sin_datos:
        cxc, cyc = px0 + pw / 2.0, py0 + ph / 2.0
        c.setFillColor(C_MUT)
        c.setFont(fnb, 8.0)
        c.drawCentredString(cxc, cyc + 2.0, "SIN DATOS DE CURVA")
        c.setFont(fn, 6.0)
        c.drawCentredString(cxc, cyc - 8.0,
                            "ingrese los pesos retenidos de los tamices")

    # ---- eje X: marcas y etiquetas (décadas y límites en la misma fila) ----
    c.setStrokeColor(CL_NEGRO)
    c.setLineWidth(0.4)
    for label, d in (("100.00", 100.0), ("10.00", 10.0), ("1.00", 1.0),
                     ("0.10", 0.1), ("0.01", 0.01)):
        xx = XLOG(d)
        c.line(xx, py0, xx, py0 + 3.0)              # marca hacia afuera
    c.setFont(fn, 5.0)
    c.setFillColor(CL_NEGRO)
    for label, d in (("100.00", 100.0), ("10.00", 10.0), ("1.00", 1.0),
                     ("0.10", 0.1), ("0.01", 0.01)):
        c.drawCentredString(XLOG(d), py0 - EIX_LBL, label)
    # valores de división y subdivisión de tamaños de partícula sobre el eje,
    # a LA MISMA ALTURA que las décadas: cada uno con su color (identidad o
    # subdivisión) y su marca corta, en la posición de las líneas punteadas.
    c.setLineWidth(0.4)
    for d, color in ((75.0, CL_LIM), (19.0, CL_LIM_MIN), (4.75, CL_LIM),
                     (2.0, CL_LIM_MIN), (0.425, CL_LIM_MIN), (0.075, CL_LIM)):
        xx = XLOG(d)
        c.setStrokeColor(color)
        c.line(xx, py0, xx, py0 + 2.0)              # marca corta hacia afuera
        c.setFillColor(color)
        c.setFont(fnb, 4.5)
        c.drawCentredString(xx, py0 - EIX_LBL, "%.3g" % d)
    c.setFont(fn, 6.0)
    c.setFillColor(CL_NEGRO)
    c.drawCentredString(px0 + pw / 2.0, py0 - EIX_TIT,
                        "DI\u00c1METRO DE PART\u00cdCULAS (mm)")

    # ---- eje Y: marcas, etiquetas a la derecha y titulo rotado ----
    c.setStrokeColor(CL_NEGRO)
    c.setLineWidth(0.4)
    for p in range(0, 101, 10):
        c.line(px1, YP(p), px1 + 3.0, YP(p))        # marca hacia afuera
    c.setFont(fn, 5.0)
    c.setFillColor(CL_NEGRO)
    for p in range(0, 101, 10):
        c.drawRightString(px1 + 12.0, ty_bas(YP(p), A, D, 5.0), str(p))
    c.saveState()
    c.translate(px0 - 4.0, (py0 + py1) / 2.0)
    c.rotate(90)
    c.setFont(fn, 6.0)
    c.drawCentredString(0, 0, "% TOTAL QUE PASA")
    c.restoreState()

    # ---- encabezado clasificatorio (tabla de dos filas) ----
    # Fila 1: GRAVA | ARENA | LIMO Y ARCILLA (celdas de banda completa) y fila 2
    # con las subdivisiones Gruesa | Fina | Gruesa | Media | Fina, separadas por
    # un renglón horizontal que solo cruza las celdas de grava y arena (las
    # limos y arcillas no tienen subdivisión). Los textos se centran vertical y
    # horizontalmente en su celda con `ty_bas`. Los bordes laterales de la banda
    # y los separadores verticales se dibujan cerrando cada celda, desde
    # `yb` (el borde inferior de la banda, por encima del aire SEP_HDR) y no
    # desde `py1`, para que ninguna línea llegue hasta el marco de la curva.
    yMid = top - 0.5 * H_HDR            # separador horizontal fila1/fila2
    yb = py1 + SEP_HDR                   # borde INFERIOR de la banda de etiquetas
    c.setStrokeColor(CL_NEGRO)
    c.setLineWidth(0.5)
    # separador horizontal entre las dos filas (solo sobre grava y arena)
    c.line(px0, yMid, XLOG(0.075), yMid)
    # borde superior de la banda de etiquetas (tabla de tamaños de partícula)
    c.line(px0, top, px1, top)
    # borde INFERIOR de la banda: faltaba, y sin él la tabla de denominaciones
    # (GRAVA/ARENA/LIMO Y ARCILLA y sus subdivisiones) quedaba abierta por
    # abajo, como si las celdas no cerraran. Se cierra a lo largo de todo el
    # ancho, y las verticales internas nacen de ella.
    c.line(px0, yb, px1, yb)
    # laterales exteriores de la banda de etiquetas (plena altura)
    c.line(px0, yb, px0, top)
    c.line(px1, yb, px1, top)
    # verticales a plena altura: límites que separan fila1 (4.75 y 0.075)
    for lim in (4.75, 0.075):
        c.line(XLOG(lim), yb, XLOG(lim), top)
    # verticales solo en la fila inferior: subdivisiones de la arena y grava
    for lim in (19.0, 2.0, 0.425):
        c.line(XLOG(lim), yb, XLOG(lim), yMid)
    # textos fila 1 (negrilla, centrada en cada celda)
    c.setFillColor(CL_NEGRO)
    c.setFont(fnb, 5.2)
    c.drawCentredString((px0 + XLOG(4.75)) / 2.0, ty_bas(top - 5.5, A, D, 5.2), "GRAVA")
    c.drawCentredString((XLOG(4.75) + XLOG(0.075)) / 2.0, ty_bas(top - 5.5, A, D, 5.2), "ARENA")
    # LIMO Y ARCILLA: celda de banda completa (sin subdivisión), centrada
    c.drawCentredString((XLOG(0.075) + px1) / 2.0, ty_bas(top - 11.0, A, D, 5.2), "LIMO Y ARCILLA")
    # textos fila 2 (regular, centrada en cada celda)
    c.setFont(fn, 5.2)
    c.drawCentredString((px0 + XLOG(19.0)) / 2.0, ty_bas(top - 16.5, A, D, 5.2), "Gruesa")
    c.drawCentredString((XLOG(19.0) + XLOG(4.75)) / 2.0, ty_bas(top - 16.5, A, D, 5.2), "Fina")
    c.drawCentredString((XLOG(4.75) + XLOG(2.0)) / 2.0, ty_bas(top - 16.5, A, D, 5.2), "Gruesa")
    c.drawCentredString((XLOG(2.0) + XLOG(0.425)) / 2.0, ty_bas(top - 16.5, A, D, 5.2), "Media")
    c.drawCentredString((XLOG(0.425) + XLOG(0.075)) / 2.0, ty_bas(top - 16.5, A, D, 5.2), "Fina")

    # borde exterior de la sección dibujado al final para que su grosor
    # quede por encima de todos los elementos (0.8 pt, como el resto de cajas)
    c.setStrokeColor(CL_NEGRO)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h, stroke=1, fill=0)

    return




def _dibujar_pie(c, box, fn, fnb):
    """Pie de página fijo de los reportes.

    Línea horizontal gruesa en el borde superior (todo el ancho útil), tres
    renglones centrados con los datos del laboratorio (constante `PIE` de
    `reporte.constantes`) y el número de página a la derecha, alineado al
    centro del pie, en fuente más grande y sin negrita. Hoy el reporte se
    emite en una sola página; el rótulo se arma con `getPageNumber()` para
    que siga siendo correcto si algún día el documento crece."""
    from reportlab.lib import colors as rlcolors
    from reporte.constantes import PIE

    C_DK = rlcolors.HexColor("#000000")
    x, y, w, h = box
    top = 36.0  # 0.5 pulgadas del borde inferior

    # borde superior del pie: línea gruesa a todo el ancho útil
    c.setStrokeColor(C_DK)
    c.setLineWidth(0.5)
    c.line(x, top, x + w, top)

    # tres renglones centrados con los datos del laboratorio
    from reportlab.pdfbase.pdfmetrics import stringWidth as _sw_pie
    c.setFont(fn, 8.0)
    c.setFillColor(C_DK)
    bas = top - 8.5
    for linea in PIE:
        ancho_pie = _sw_pie(linea, fn, 8.0)
        if ancho_pie > w:
            c.setFont(fn, 8.0 * w / ancho_pie)
        c.drawCentredString(x + w / 2.0, bas, linea)
        c.setFont(fn, 8.0)
        bas -= 10.0


def _dibujar_firmas(c, box, fn, fnb):
    """Bloque de firmas de responsabilidad justo encima del pie.

    Dos columnas separadas por una linea vertical delgada:
      * izquierda: la firma manuscrita real se escribe a mano en el
        espacio en blanco; bajo una linea delgada se imprimen el cargo
        y el nombre del responsable.
      * derecha: igual estructura con el espacio en blanco.
    Config: reporte.constantes.FIRMAS = (lado, imagen, nombre, cargo).
    """
    from reportlab.lib import colors as _c
    try:
        from reporte.constantes import FIRMAS
    except Exception:
        FIRMAS = ()
    x, y, w, h = box
    midx = x + w / 2.0

    # linea vertical delgada que separa las dos columnas
    c.saveState()
    c.setStrokeColor(_c.HexColor("#b9bfc7"))
    c.setLineWidth(0.4)
    c.line(midx, y, midx, y + h)

    half = w / 2.0
    for it in FIRMAS:
        if len(it) == 5:
            lado, imagen, nombre, cargo, _u = it
        elif len(it) == 4:
            lado, imagen, nombre, cargo = it
        else:
            nombre, cargo, imagen = it
            lado = "izq"
        cx = x if (lado or "").lower().startswith("izq") else midx
        cw = half
        cxx = cx + cw / 2.0
        # espacio en BLANCO reservado para la firma manuscrita (sin nombre)
        # linea delgada bajo el espacio de la firma
        lw = cw * 0.46
        # zona en BLANCO sobre la linea para la firma manuscrita (22 pt)
        liny = y + h - 22.0
        base_cargo = liny - 9.0
        base_nombre = base_cargo - 9.5
        c.setStrokeColor(_c.HexColor("#2a3542"))
        c.setLineWidth(0.6)
        c.line(cxx - lw / 2.0, liny, cxx + lw / 2.0, liny)
        if lado == "izq":
            c.setFont(fn, 8.3)
            c.setFillColor(_c.HexColor("#000000"))
            c.drawCentredString(cxx, base_cargo, cargo)
            c.setFont(fn, 7.6)
            c.setFillColor(_c.HexColor("#000000"))
            c.drawCentredString(cxx, base_nombre, nombre)
        else:
            c.setFont(fn, 8.0)
            c.setFillColor(_c.HexColor("#000000"))
            c.drawCentredString(cxx, base_cargo, cargo)
    c.restoreState()

def report_pdf(datos, res, ident, path):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors as rlcolors
    from reportlab.pdfgen import canvas as _canvas

    f = _webfonts()
    fn, fnb = f.fn, f.fnb

    C_DK  = rlcolors.HexColor("#000000")
    C_MUT = rlcolors.HexColor("#6e7781")

    W, H = letter
    ML, MR = _MARGEN_L, _MARGEN_R
    MT, MB = _MARGEN_S, _MARGEN_I
    CW = W - ML - MR
    CH = H - MT - MB

    c = _canvas.Canvas(path, pagesize=letter)
    c.setTitle("GRAD-PLAS · Reporte de resultados")
    c.setAuthor("GRAD-PLAS")

    for nombre, desc, x, y, w, h in _pilas(ML, MB, CW, CH,
                                           alturas=_alturas(datos, res, ident, CH)):
        if nombre == "wl-wp-block":
            # tabla y gráfica son dos cajas independientes; cada una dibuja
            # su propio borde (0.8 pt) dentro de _dib_wl_wp
            _dib_wl_wp(c, (x, y, w, h), fn, fnb, datos, res)
            continue
        if nombre == "granulometria-block":
            # tabla (70 %) + resultados (30 %) son dos cajas independientes;
            # su propio borde (0.8 pt) lo dibuja _dib_granulometria
            _dib_granulometria(c, (x, y, w, h), fn, fnb, datos, res)
            continue
        if nombre == "grain-size-chart":
            _dib_grain_size_chart(c, (x, y, w, h), fn, fnb, res)
            continue
        if nombre == "firmas-block":
            _dibujar_firmas(c, (x, y, w, h), fn, fnb)
            continue
        if nombre == "PIE-block" or nombre == "footer":
            # pie de página fijo: línea gruesa + datos del laboratorio
            # (constante `PIE`) + número de página a la derecha
            _dibujar_pie(c, (x, y, w, h), fn, fnb)
            continue
        # caja simple: borde negro, sin relleno
        c.setLineWidth(0.8)
        c.setStrokeColor(C_DK)
        c.rect(x, y, w, h, stroke=1, fill=0)
        if nombre == "header":
            _dibujar_header(c, (x, y, w, h), fn, fnb)
            continue
        if nombre == "project-info":
            _dibujar_project_info(c, (x, y, w, h), fn, fnb, datos, res, ident)
            continue
        # identificación
        c.setFillColor(C_DK)
        c.setFont(fnb, 8)
        c.drawString(x + 6, y + h - 13, nombre)
        c.setFillColor(C_MUT)
        c.setFont(fn, 7.5)
        c.drawString(x + 6, y + h - 24, desc)
        c.setFont(fn, 6.5)
        c.drawString(x + w - 6, y + 4, "%.0f x %.0f pt" % (w, h))

    c.showPage()
    c.save()


def preview_pdf(datos, res, ident):
    """Genera el PDF de vista previa en el directorio temporal."""
    import tempfile
    pdf = os.path.join(tempfile.gettempdir(), _temp_prefix() + "preview.pdf")
    report_pdf(datos, res, ident, pdf)
    return pdf
