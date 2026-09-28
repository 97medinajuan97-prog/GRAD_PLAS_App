# -*- coding: utf-8 -*-
"""Constantes de configuración del reporte.

Datos editables del laboratorio que se usan en el pie de página de los
documentos generados. Edítelos aquí y se reflejarán en todos los reportes.
"""

#: Pie de página del reporte (una sola línea centrada, justo encima del
#: borde grueso inferior; el número de página se dibuja a la derecha).
#: Edítelos aquí y se reflejarán en todos los reportes.
PIE = (
    "Carrera 28 # 2\u00aa 08 Sogamoso Boyac\u00e1  \u00b7  Cel. 315 8468211 \u2013 310 871 6863  \u00b7  Tel (038) 775 06 30  \u00b7  Email. cgutierrezcarrerog@gmail.com",
)

#: Firmas de responsabilidad (bloque justo encima del pie de página).
#: Dos columnas separadas por una línea vertical delgada:
#:   * izquierda: firma escaneada (imagen) o nombre en cursiva;
#:   * derecha: firma en cursiva grande (rúbrica manuscrita).
#: Cada ítem: (lado, imagen, nombre, cargo, usar_cursiva).
#:   - lado: "izq" (firma escaneada de la imagen) o "der" (firma grande)
#:   - imagen: ruta PNG/JPG con la firma escaneada y fondo transparente;
#:             vacío "" para usar la fuente cursiva simulada en su lugar
#:   - usar_cursiva: True → el nombre se dibuja en letra cursiva grande
#:                   simulando la rúbrica manuscrita
FIRMAS = (
    ("izq", "", "Carlos H. Guti\u00e9rrez C.",
     "Ing. Control de Calidad", False),
    ("der", "", "Idauro Mu\u00f1oz", "Laboratorista", True),
)

#: Pie de página del reporte. Cada línea se centra en el pie, justo encima
#: del borde grueso inferior; el número de página se dibuja a la derecha.
#: Edítelos aquí y se reflejarán en todos los reportes.
PIE = (
    "Carrera 28 # 2\u00aa 08 Sogamoso Boyac\u00e1   \u00b7   "
    "Cel. 315 8468211 \u2013 310 871 6863 - Tel (038) 775 06 30   \u00b7   "
    "Email. cgutierrezcarrerog@gmail.com",
)

#: Firmas de responsabilidad (bloque justo encima del pie de página).
#: Dos columnas separadas por una línea vertical delgada:
#:   * izquierda: firma escaneada (imagen PNG con la firma escaneada) o
#:                nombre en letra cursiva;
#:   * derecha: firma en letra cursiva grande (simula la rúbrica manuscrita).
#: Cada entrada: (lado, imagen, nombre, cargo, usar_cursiva).
#:   - lado: "izq" (firma escaneada) o "der" (firma grande en cursiva)
#:   - imagen: ruta PNG/JPG con la firma escaneada y fondo transparente;
#:             vacío "" para usar la fuente cursiva simulada en su lugar
#:   - usar_cursiva: True → el nombre se dibuja en letra cursiva grande
#:                   simulando la rúbrica manuscrita
FIRMAS = (
    ("izq", "", "Carlos Hern\u00e1n Guti\u00e9rrez Carrero",
     "Ing. Control de Calidad", False),
    ("der", "", "Idauro Mu\u00f1oz", "Laboratorista", True),
)
