# -*- coding: utf-8 -*-
"""Receta de empaquetado de GRAD-PLAS para Windows.

Genera una CARPETA con el ejecutable y su interior, no un .exe suelto:

    dist/GRAD-PLAS/GRAD-PLAS.exe
    dist/GRAD-PLAS/_internal/...

Se eligiÃ³ la carpeta y no el archivo suelto por dos razones que se notan al
usarlo: arranca mucho mÃ¡s rÃ¡pido (no descomprime nada en cada apertura) y
Windows lo marca mucho menos como sospechoso.

Para recompilar:

    py -3 tools_generar_icono.py
    py -3 -m PyInstaller --noconfirm --clean GRAD-PLAS.spec

Que quede una carpeta `dist/GRAD-PLAS.zip` para repartir.
"""

# El logo viaja DENTRO del ejecutable: el reporte lo dibuja en el encabezado y
# si no lo encuentra sale sin Ã©l. La ruta la resuelve `rutas.recurso()`, que
# empaquetado apunta a `sys._MEIPASS`.
datas = [("RAPITEST LOGO.png", ".")]

# `fitz` es el nombre antiguo de PyMuPDF. La app lo importa con ese nombre,
# dentro de una funciÃ³n, asÃ­ que el anÃ¡lisis estÃ¡tico puede no engancharlo y
# acabarÃ­a faltando la vista previa en el ejecutable.
hiddenimports = ["fitz", "pymupdf"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # `collect_all` de reportlab y PyMuPDF se deja fuera a proposito: arrastra
    # mas de lo que la app usa (los filtros de imagen de MuPDF, los codigos de
    # barras de reportlab) y el ejecutable pasa de 70 MB a mucho mas sin que
    # cambie nada de lo que se ve.
    #
# Esta lista es lo que hace que la carpeta pese 80 MB en vez de 160. Sin
    # ella, PyInstaller se lleva pandas, numpy, lxml, jedi y black, que la
    # aplicacion no usa en absoluto: nada las importa. numpy le interesa a
    # PyMuPDF, pero como opcional, y el preview funciona sin el.
    #
    # PIL NO se puede quitar: reportlab lo importa sin condiciones en
    # `rl_accel`, que se carga al pintar cualquier color. Se excluyó y el
    # ejecutable se caía al generar el primer PDF. Eso lo comprueba
    # `prueba-empaquetado.spec`, que se compila con esta misma receta y falla
    # si falta algo de lo que la app usa de verdad.
    excludes=[
        "black", "jedi", "pandas", "pandas.libs", "lxml", "numpy",
        "numpy.libs", "charset_normalizer", "tzdata",
        "IPython", "pytest", "setuptools", "pip", "wheel",
        "unittest", "pydoc_data", "lib2to3", "distutils",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GRAD-PLAS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Sin consola: si algo falla lo avisa un cuadro de diÃ¡logo de la propia
    # aplicacion, y el usuario no ve una ventana negra detrÃ¡s.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GRAD-PLAS",
)
