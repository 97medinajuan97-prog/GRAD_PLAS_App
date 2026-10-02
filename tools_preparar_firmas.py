# -*- coding: utf-8 -*-
"""Prepara las firmas escaneadas para el bloque de firmas del reporte.

Las dos firmas llegan como tinta negra sobre fondo blanco y sin canal de
transparencia. Si se dibujan tal cual, el rectángulo blanco tapa la línea de
firma y cualquier línea de la retícula que pase por debajo, y además el ancho
del recuadro es el del papel, no el del trazo: la firma saldría diminuta
dentro de un cuadro enorme.

Aquí se hace lo que hace falta para que se vean como una firma y no como una
foto:

  * el blanco se vuelve transparente, usando la luminancia como canal alfa
    (tinta negra opaca, papel invisible);
  * se recorta el borde vacío, para que la firma ocupe justo la caja que se le
    da en el reporte.

Los originales NO se tocan: se leen y se escriben copias ya tratadas en la
carpeta `firmas/`, que es la que usa el reporte. Así se puede volver a preparar
si llega un escaneo mejor.

    py -3 tools_preparar_firmas.py
"""
import os

from PIL import Image

ORIGENES = (
    ("firma_ing.png", "firmas/firma_ing.png"),
    ("firma_laboratorista.jfif", "firmas/firma_laboratorista.png"),
)

#: Cuánto se considera "papel". Un blanco puro (255) es totalmente
#: transparente; el negro (0) es totalmente opaco. Lo de en medio, gris, es la
#: sombra del bolígrafo o un trazo fino, y tiene que quedar a medio camino.
BLANCO = 245
MARGEN = 6          # px de aire que se dejan alrededor del trazo


def preparar(origen, destino):
    img = Image.open(origen).convert("L")          # luminancia
    # Alfa: 0 en el papel, 255 en la tinta.
    alfa = img.point(lambda v: 0 if v >= BLANCO
                      else int(255 * (BLANCO - v) / BLANCO))
    # Recorte al rectángulo que realmente tiene tinta, con un margen de aire.
    caja = alfa.getbbox()
    if caja is None:
        raise SystemExit("%s está en blanco: no hay firma que colocar." % origen)
    x0, y0, x1, y1 = caja
    x0 = max(0, x0 - MARGEN)
    y0 = max(0, y0 - MARGEN)
    x1 = min(alfa.width, x1 + MARGEN)
    y1 = min(alfa.height, y1 + MARGEN)
    firma = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    firma.putalpha(alfa.crop((x0, y0, x1, y1)))
    carpeta = os.path.dirname(destino)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    firma.save(destino, format="PNG")
    return img.size, firma.size


def main():
    faltan = [o for o, _ in ORIGENES if not os.path.isfile(o)]
    if faltan:
        raise SystemExit(
            "No se encontraron los escaneos originales: %s\n"
            "Colocalos en la carpeta del proyecto y vuelve a intentarlo."
            % ", ".join(faltan))
    for origen, destino in ORIGENES:
        antes, despues = preparar(origen, destino)
        print("  %-28s %sx%s  ->  %-34s %sx%s  (%.0f KB)" % (
            origen, antes[0], antes[1], destino, despues[0], despues[1],
            os.path.getsize(destino) / 1024.0))


if __name__ == "__main__":
    main()