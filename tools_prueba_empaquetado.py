# -*- coding: utf-8 -*-
"""Prueba de humo del ejecutable empaquetado.

Este guion NO se usa desde la aplicación: se empaqueta aparte, con la misma
receta y los mismos `excludes` que GRAD-PLAS, para comprobar que dentro del
paquete siguen funcionando las tres cosas que de verdad importan:

  1. que se encuentre el logo del encabezado (va dentro del ejecutable);
  2. que reportlab genere un PDF con el, sin PIL;
  3. que PyMuPDF lo abra y lo rasterice, sin numpy, que es lo que hace la
     vista previa.

Si esto pasa, la aplicación empaquetada arranca y dibuja: usa exactamente las
mismas librerías. Se ejecuta con consola para poder leer el resultado.
"""
import os
import sys
import tempfile

fallos = []


def chequear(ok, nombre, detalle=""):
    print("  %-56s %s%s" % (nombre, "OK" if ok else "FALLA",
                            "" if ok else "  <- " + str(detalle)))
    if not ok:
        fallos.append(nombre)
    return ok


print("  --- dentro del ejecutable ---")
print("  python: %s" % sys.version.split()[0])
print("  congelada: %s" % bool(getattr(sys, "frozen", False)))

import rutas
chequear(rutas.es_empaquetada(),
         "la aplicacion se detecta como empaquetada")
chequear(rutas.carpeta_datos().lower() == os.path.dirname(
    os.path.abspath(sys.executable)).lower(),
    "la carpeta de datos es la del ejecutable", rutas.carpeta_datos())
print("      ejecutable en : %s" % sys.executable)
print("      datos en      : %s" % rutas.carpeta_datos())
print("      copia         : %s" % rutas.nombre_copia())

logo = rutas.recurso("RAPITEST LOGO.png")
chequear(os.path.isfile(logo), "el logo se encuentra DENTRO del paquete", logo)
print("      logo          : %s" % logo)

# ---- reportlab: PDF completo, con logo y zona de filtro ----
print()
print("  --- reporte ---")
try:
    import fitz
    print("  PyMuPDF importado sin numpy: %s" % fitz.__doc__.strip().splitlines()[0]
          if fitz.__doc__ else "ok")
except Exception as e:
    chequear(False, "PyMuPDF se importa", repr(e))
    fitz = None

from motor.calculo import calcular
from reporte.pdf import report_pdf, _webfonts
from datos_ejemplo import datos_ejemplo

datos = datos_ejemplo(solo="BG")
ident = dict(datos["ident"])
ident["tipo"] = "Control de calidad"
ident["alcance"] = "Bases"
ident["graduacion"] = "BG-38"
ident["exploracion"] = "Apique"
ident["sondeo"] = "2"
ident["muestra"] = "5"
datos["ident"] = ident
res = calcular(datos)

salida = os.path.join(tempfile.gettempdir(), "prueba_empaquetado.pdf")
report_pdf(datos, res, ident, salida)
chequear(os.path.isfile(salida) and os.path.getsize(salida) > 5000,
         "reportlab genera el PDF", "%d bytes" % (
             os.path.getsize(salida) if os.path.isfile(salida) else 0))

if fitz is not None:
    doc = fitz.open(salida)
    texto = doc[0].get_text()
    paginas = doc.page_count
    # La vista previa rasteriza: es exactamente este paso.
    pix = doc[0].get_pixmap()
    png = pix.tobytes("png")
    doc.close()
    chequear(paginas == 1, "el reporte sale en una pagina", paginas)
    chequear(len(png) > 5000, "PyMuPDF rasteriza la pagina (vista previa)",
             "%d bytes de png" % len(png))
    plano = " ".join(texto.split())
    chequear("APIQUE" in plano, "el rotulo sale APIQUE")
    chequear("A-2" in plano, "el codigo de exploracion sale A-2")
    chequear("M-5" in plano, "la muestra sale M-5")
    chequear("BG-38" in plano, "la graduacion sale en el reporte")

    # El logo tiene que estar dibujado: si PIL faltara y el logo no se
    # pudiera leer, el encabezado saldría sin él, en silencio.
    imagenes = 0
    doc = fitz.open(salida)
    for p in doc:
        for img in p.get_images(full=True):
            imagenes += 1
    doc.close()
    chequear(imagenes >= 1, "el logo esta dibujado en el encabezado",
             "imagenes=%d" % imagenes)

    fn = _webfonts()
    chequear(bool(fn.fn), "las fuentes resuelven", fn.fn)

# ---- configuracion: se escribe junto al ejecutable y se relee ----
print()
print("  --- configuracion ---")
from app import App
conf = App._CONF
chequear(os.path.dirname(conf).lower() == rutas.carpeta_datos().lower(),
         "la configuracion va junto al ejecutable", conf)
import json
try:
    with open(conf, "w", encoding="utf-8") as fh:
        json.dump({"directorio": tempfile.gettempdir()}, fh)
    with open(conf, encoding="utf-8") as fh:
        leido = json.load(fh).get("directorio")
    chequear(leido == tempfile.gettempdir(),
             "se escribe y se relee (la carpeta recordada)", leido)
    os.remove(conf)
except Exception as e:
    chequear(False, "la configuracion se escribe y se relee", repr(e))

print()
print("  FALLOS:", fallos if fallos else "ninguno")
sys.exit(1 if fallos else 0)