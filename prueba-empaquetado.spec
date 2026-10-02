# -*- coding: utf-8 -*-
"""Empaqueta la prueba de humo con la MISMA receta que GRAD-PLAS.

Se compila aparte, y con consola para poder leer el resultado. Lo que importa
es que comparta `excludes` y `datas` con GRAD-PLAS.spec: si la aplicaciÃ³n real
arranca con esto, arranca con aquello.

No se distribuye: solo sirve para comprobar el empaquetado.
"""

datas = [("RAPITEST LOGO.png", ".")]

hiddenimports = ["fitz", "pymupdf"]

excludes = [
    "black", "jedi", "pandas", "pandas.libs", "lxml", "numpy",
    "numpy.libs", "charset_normalizer", "tzdata",
    "IPython", "pytest", "setuptools", "pip", "wheel",
    "unittest", "pydoc_data", "lib2to3", "distutils",
]

a = Analysis(
    ["tools_prueba_empaquetado.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="prueba-empaquetado",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="prueba-empaquetado",
)
