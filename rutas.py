# -*- coding: utf-8 -*-
"""Dónde están los archivos, según cómo se esté ejecutando la aplicación.

Hay dos carpetas distintas y confundirlas rompe cosas silenciosamente:

  * Los archivos que la app LEE (el logo del encabezado) viajan DENTRO del
    ejecutable. Empaquetado con PyInstaller, `__file__` deja de apuntar al
    proyecto y pasa a apuntar a una carpeta temporal que Windows borra al
    cerrar, así que buscar el logo por ahí lo deja sin encontrar.

  * Los archivos que la app ESCRIBE (la carpeta de trabajo recordada) tienen
    que vivir FUERA, junto al `.exe`, porque un temporal se borra al cerrar y
    el usuario perdería su carpeta en cada arranque. Esta es la razón de que el
    programa sea "portable": la configuración viaja con el programa.

Por eso son dos funciones y no una. Una sola no puede atender a las dos cosas:
el logo no se puede dejar fuera (viaja con el binario) y la configuración no
puede ir dentro (se perdería).

Cuando la aplicación se ejecuta desde Python, y no desde el ejecutable, las dos
carpetas coinciden con la del proyecto y todo funciona como siempre.
"""
import os
import sys


def es_empaquetada():
    """¿La aplicación está corriendo desde el ejecutable compilado?"""
    return bool(getattr(sys, "frozen", False))


def recurso(*partes):
    """Ruta de un archivo que la aplicación solo lee.

    Empaquetado, busca dentro del ejecutable; sin empaquetar, en la carpeta del
    proyecto, que es donde está este módulo.
    """
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *partes)


def carpeta_datos():
    """Carpeta donde la aplicación puede escribir y lo que hay ahí persiste.

    Empaquetado, es la carpeta del `.exe`: el programa se lleva su
    configuración a donde vaya. Sin empaquetar, la carpeta del proyecto, que es
    como se usaba antes.
    """
    if es_empaquetada():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def nombre_copia():
    """Nombre corto de esta copia instalada, para archivos temporales.

    Sirve para que dos copias de la aplicación abiertas a la vez no se pisen el
    mismo archivo temporal. Empaquetado es el nombre del `.exe`; sin
    empaquetar, el de la carpeta del proyecto.

    Ojo: empaquetado en un solo archivo, la carpeta temporal donde se
    descomprime cambia de nombre en cada arranque, así que no sirve para esto:
    dos arranques seguidos dejarían archivos temporales distintos acumulados y
    dos copias se pisarían sin embargo.
    """
    if es_empaquetada():
        return os.path.splitext(os.path.basename(sys.executable))[0]
    return os.path.basename(os.path.dirname(os.path.abspath(__file__)))