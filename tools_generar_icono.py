# -*- coding: utf-8 -*-
"""Convierte icon.png en icon.ico para el icono del ejecutable.

Windows no usa el .png tal cual: el icono de un .exe es un .ico, y conviene
que tenga varias resoluciones porque Windows elige segun el tamano de la icono,
la barra de tareas o el explorador de archivos.

El png es rectangular (1224x1285) y un icono se supone cuadrado, asi que se
recorta centrado, sin estirar: estirar deformaria el dibujo.

Solo hace falta al compilar el ejecutable. Pillow es una herramienta de
empaquetado y NO hace falta para usar el programa.
"""
import os

from PIL import Image

ORIGEN = "icon.png"
DESTINO = "icon.ico"
TAMANOS = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
           (128, 128), (256, 256)]


def cuadrado(img):
    """Recorta centrado a un cuadrado, sin deformar."""
    w, h = img.size
    if w == h:
        return img
    lado = min(w, h)
    izquierda = (w - lado) // 2
    arriba = (h - lado) // 2
    return img.crop((izquierda, arriba, izquierda + lado, arriba + lado))


def main():
    if not os.path.isfile(ORIGEN):
        raise SystemExit("No se encontro %s en la carpeta del proyecto."
                         % ORIGEN)
    img = Image.open(ORIGEN)
    # El logo esta sobre fondo blanco; sin alfa, Windows lo pondria sobre un
    # rectangulo opaco y en el explorador se veria un cuadro blanco.
    img = cuadrado(img).convert("RGBA")
    fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    fondo.alpha_composite(img)
    fondo.save(DESTINO, format="ICO", sizes=TAMANOS)
    print("  %s -> %s  (%d resoluciones, %.0f KB)" % (
        ORIGEN, DESTINO, len(TAMANOS),
        os.path.getsize(DESTINO) / 1024.0))


if __name__ == "__main__":
    main()