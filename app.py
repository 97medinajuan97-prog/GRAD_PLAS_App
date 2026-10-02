# -*- coding: utf-8 -*-
"""Ventana principal: panel izquierdo de ingreso (secciones) + panel derecho
con el reporte en vivo. Cada sección es un módulo independiente."""
import datetime
import json
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui_theme import (aplicar_estilo, ScrollableFrame, ACC, ACC_D,
                      BG,                       BORDE_HOJA, CARD, CREMA, MUT, SUP, TXT, FAM_UI,
                      VERSION, validar_tecla, ayuda_seccion, SelectDropdown,
                      habilitar_deshacer, ToolTip, FONDO_VISOR, BORDE)

from secciones.humedad import Humedad
from secciones.limites import Limites
from secciones.granulometria import Granulometria, serie_para
from motor.calculo import calcular as motor_calcular, fnum
from reporte.constantes import (NOMBRES_EXPLORACION, codigo_exploracion,
                                codigo_muestra, datos_exploracion,
                                prefijo_exploracion)
from datos_ejemplo import datos_ejemplo, SIMBOLOS
from rutas import carpeta_datos

#: Título de la ventana. Antes se escribía literal dos veces (título del `Tk`
#: y rótulo de la franja superior) y cualquier corrección había que replicarla
#: en ambos sitios, con el riesgo de que se desincronizaran.
TITULO = ("Granulometría · Límites de Atterberg · Humedad natural"
          " — INV E-123 · E-125 · E-126")

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("%s  ·  v%s" % (TITULO, VERSION))
        self.configure(bg=BG)
        self.minsize(1020, 620)
        aplicar_estilo(self)

        self.idvars = {k: tk.StringVar() for k in
                       ("proyecto", "sector", "ordenado", "sondeo", "muestra",
                        "fecha_toma", "fecha_ejecucion",
                        "prof_desde", "prof_hasta", "descripcion")}
        self._preview_after = None
        self._datos_actuales = None
        self._res_actuales = None
        #: True mientras `_sincronizar_alcance` está en marcha. Al cambiar de
        #: alcance se repuebla la lista de graduaciones, y eso dispara la traza
        #: de `sel_graduacion`. Sin este candado, esa traza refrescaría el
        #: reporte antes de que se haya cambiado la serie de tamices: la curva
        #: saldría de otra muestra y la graduación sería la nueva.
        self._sinc_seleccion = False

        self._build()

        # Ctrl+Z en todo el ingreso de datos. Va después de _build para que
        # existan ya todas las casillas.
        habilitar_deshacer(self)

        for v in self.idvars.values():
            v.trace_add("write", lambda *_: self._refresh())
        self._schedule_preview(200)

    # ---------------- construccion ----------------
    def _build(self):
        cab = tk.Frame(self, bg=ACC, padx=16, pady=8)
        cab.pack(fill="x")
        tk.Label(cab, text="%s  ·  v%s" % (TITULO, VERSION),
                 bg=ACC, fg="#ffffff", font=(FAM_UI, 12, "bold")).pack(anchor="center")

        split = tk.Frame(self, bg=BG)
        split.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.left_sc = ScrollableFrame(split)
        # El visualizador lleva barra horizontal abajo y sin franja vertical:
        # con el área de la hoja ocupando todo el ancho, esa franja tapaba lo
        # que hubiera detrás.
        self.right_sc = ScrollableFrame(split, horizontal=True,
                                        vertical_thumb=False, bg=FONDO_VISOR)
        # La barra de herramientas va FUERA del área que desplaza, como en un
        # lector de PDF. Dentro, el marco se ensancha con la hoja y la barra
        # se saldría de la ventana al ampliar.
        self.bar_r = tk.Frame(split, bg=FONDO_VISOR)

        def _ajustar_split(_e=None):
            tot = split.winfo_width()
            h = split.winfo_height()
            if tot < 40 or h < 24:
                return
            usable = tot - 6
            rw = int(round(usable * 0.618))
            lw = usable - rw
            # La barra toma la altura que pide su contenido. Con una altura fija
            # se quedaba más baja que el botón "Guardar PDF", que pide 39 px con
            # su relleno; Tk lo comprimía y el texto se recortaba entero.
            alto = max(30, self.bar_r.winfo_reqheight())
            self.left_sc.place(x=0, y=0, width=lw, height=h)
            self.bar_r.place(x=lw + 6, y=0, width=rw, height=alto)
            self.right_sc.place(x=lw + 6, y=alto + 4, width=rw,
                                height=max(40, h - alto - 4))

        split.bind("<Configure>", _ajustar_split)
        left = self.left_sc.inner()
        self.right = self.right_sc.inner()

        # ---- panel izquierdo: secciones independientes ----
        self._build_muestra(left)
        self._build_identidad(left)

        self.hum = Humedad(left)
        self.hum.pack(fill="x", pady=2)
        self.lim = Limites(left)
        self.lim.pack(fill="x", pady=2)
        self.grano = Granulometria(left)
        self.grano.pack(fill="x", pady=2)
        for sec in (self.hum, self.lim, self.grano):
            sec.bind_cambio(lambda *_: self._refresh())

        bot = ttk.Frame(left)
        bot.pack(fill="x", pady=(4, 2))
        tk.Label(bot, text="Ejemplo:", bg=BG, fg=MUT, font=(FAM_UI, 10),
                 pady=4).pack(side="left", padx=(4, 0))
        self.ejemplo_tipo = SelectDropdown(bot, ["Aleatorio"] + list(SIMBOLOS),
                                           inicial="Aleatorio", ancho=9)
        self.ejemplo_tipo.pack(side="left", padx=(0, 8))
        ttk.Button(bot, text="Cargar ejemplo", style="Ghost.TButton",
                   command=self._cargar_ejemplo).pack(side="left", padx=(0, 4))
        ttk.Button(bot, text="Limpiar", style="Ghost.TButton",
                   command=self._limpiar).pack(side="left", padx=(0, 4))

        # ---- panel derecho: barra fija + área del visualizador ----
        bar = ttk.Frame(self.bar_r, style="Visor.TFrame")
        bar.pack(fill="both", expand=True, padx=(8, 8), pady=2)
        ttk.Label(bar, text="Reporte en vivo", style="Visor.TLabel",
                  font=(FAM_UI, 11, "bold")).pack(side="left", padx=(0, 6))

        # Firmar: si está marcado, el reporte sale con las firmas escaneadas.
        # Desmarcado (que es como abre) el bloque sale con los nombres y el
        # espacio en blanco, que es lo que se necesita para una copia que se
        # firma a mano.
        self.firmar = tk.BooleanVar(value=False)
        # El botón va primero: la barra se arma con `side="right"`, así que lo
        # que se empaqueta primero queda más a la derecha. Empaquetando el
        # check antes, "Firmar" salía a la derecha de "Guardar PDF", al revés
        # de como se pidió.
        ttk.Button(bar, text="Guardar PDF", style="Accent.TButton",
                   command=self._pdf).pack(side="right", padx=2)
        chk = tk.Checkbutton(bar, text="Firmar", variable=self.firmar,
                             bg=FONDO_VISOR, fg=ACC, activebackground=FONDO_VISOR,
                             selectcolor=FONDO_VISOR, font=(FAM_UI, 9),
                             bd=0, highlightthickness=0, cursor="hand2")
        chk.pack(side="right", padx=(4, 6))
        ToolTip(chk, "Incluir las firmas escaneadas en el reporte.\n\n"
                     "Sin marcar, el bloque sale con los nombres y el espacio "
                     "en blanco para firmar a mano.")
        self._build_zoom(bar)
        # espacio elástico entre el rótulo y el grupo de la derecha, para que
        # el grupo quede siempre pegado al borde sin apretar el control
        tk.Frame(bar, bg=FONDO_VISOR).pack(side="left", fill="x", expand=True)

        # Área del visualizador: fondo oscuro y aire alrededor de la hoja, para
        # que el papel blanco quede flotando como en un lector de PDF.
        self.report_area = ttk.Frame(self.right, style="Visor.TFrame")
        self.report_area.pack(fill="both", expand=True)
        self._imgs = []

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1180, sw - 60)
        h = min(800, sh - 100)
        self.geometry("%dx%d+%d+%d" % (w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 3)))
        self.right_sc.bind_resize(lambda: self._schedule_preview())
        # la barra se coloca cuando ya se sabe la altura que pide su contenido
        self.after(80, _ajustar_split)

    # ---------------- zoom del reporte ----------------
    #: Rango del control: el 0 es el 100 % del tamaño real de la hoja, y se
    #: puede reducir a la mitad o ampliar al triple.
    ZOOM_MIN = -60
    ZOOM_MAX = 200
    #: aire entre el borde del área de visualización y la hoja
    PAD_HOJA = 12

    def _build_zoom(self, parent):
        """Ampliación del reporte: solo los dos botones y el porcentaje.

        El 0 es el 100 %: la hoja se dibuja a su tamaño real, convirtiendo los
        puntos del PDF a píxeles de pantalla según los DPI del equipo. El
        porcentaje es solo de lectura, se escribe al mover los botones.

        Se quitaron el deslizador y el botón «Encajar» porque con los botones ya
        se llega a cualquier tamaño, y el deslizador encima de la barra se comía
        el espacio. El porcentaje se queda porque sin él no se sabe a qué
        ampliación se está mirando la hoja.
        """
        self._zoom_val = 0.0
        lbl = tk.Label(parent, text="Zoom", bg=FONDO_VISOR, fg=MUT,
                       font=(FAM_UI, 9))
        lbl.pack(side="right", padx=(8, 4))
        self._zoom_pct_lbl = tk.Label(parent, text="100 %", bg=FONDO_VISOR,
                                      fg=ACC, font=(FAM_UI, 9), width=6,
                                      anchor="center")
        self._zoom_pct_lbl.pack(side="right", padx=(0, 8))

        # Los botones usan el fondo de la barra para no abrir huecos claros.
        mas = tk.Button(parent, text="+", font=(FAM_UI, 11, "bold"),
                        bg=FONDO_VISOR, fg=ACC, relief="flat", bd=0,
                        width=2, activebackground=CREMA, cursor="hand2",
                        command=lambda: self._zoom_paso(+10))
        mas.pack(side="right", padx=(0, 2))
        ToolTip(mas, "Aumentar la ampliación.")

        menos = tk.Button(parent, text="−", font=(FAM_UI, 11, "bold"),
                          bg=FONDO_VISOR, fg=ACC, relief="flat", bd=0,
                          width=2, activebackground=CREMA, cursor="hand2",
                          command=lambda: self._zoom_paso(-10))
        menos.pack(side="right")
        ToolTip(menos, "Reducir la ampliación.")

    def _factor_zoom(self):
        """Factor de escala para el 100 % real de la hoja.

        1 punto del PDF es 1/72 de pulgada. Multiplicando por los píxeles por
        pulgada de la pantalla, el 100 % sale al tamaño físico real. Un 150 %
        de DPI alto da 2.0, que es lo que quiere decir "150 %".
        """
        try:
            ppp = float(self.winfo_fpixels("1i"))       # píxeles por pulgada
        except (tk.TclError, ValueError):
            ppp = 96.0
        return (ppp / 72.0) * (1.0 + self._zoom_valor() / 100.0)

    def _zoom_valor(self):
        """Ampliación actual, con el 0 en el 100 %."""
        return self._zoom_val

    def _zoom_ir(self, valor):
        """Fija la ampliación a un valor absoluto (contexto del 0 = 100 %)."""
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return
        self._zoom_val = max(self.ZOOM_MIN, min(self.ZOOM_MAX, valor))
        self._zoom_pct_lbl.config(text="%d %%" % round(100.0 + self._zoom_val))
        self._schedule_preview(60)

    def _zoom_paso(self, salto):
        """Mueve la ampliación un tanto respecto a donde está (botones − y +)."""
        self._zoom_ir(self._zoom_valor() + salto)

    #: ancho en caracteres de los dos botones de Muestra. Se fijan los dos al
    #: mismo para que midan igual, ya que el texto más corto no los iguala.
    ANCHO_BTN = 17

    #: Tipo de muestra: para qué se toma. Es lo primero que pregunta el
    #: laboratorio, porque decide el alcance de los ensayos que se van a hacer.
    TIPO_SUELOS = "Suelos"
    TIPO_CC = "Control de calidad"
    TIPOS_MUESTRA = (TIPO_SUELOS, TIPO_CC)

    #: Dentro de control de calidad, la familia de ensayo. Afirmados, bases y
    #: subbases van separados porque cada familia tiene sus propias
    #: graduaciones (ver `GRADUACIONES`), y meterlos en una sola opción
    #: obligaría a elegir una graduación que no aplica al material.
    ALCANCE_AFIRMADO = "Afirmados"
    ALCANCE_BASE = "Bases"
    ALCANCE_SUBBASE = "Subbases"
    ALCANCE_ESTRUCTURAS = "Estructuras y drenajes"
    ALCANCE_PAVIMENTOS = "Pavimentos asfálticos"
    ALCANCES_CC = (ALCANCE_AFIRMADO, ALCANCE_BASE, ALCANCE_SUBBASE,
                   ALCANCE_ESTRUCTURAS, ALCANCE_PAVIMENTOS)

    #: Graduación de cada familia de granulares, según lo pedido para el control
    #: de calidad. Solo estos tres alcances tienen graduación; estructuras,
    #: drenajes y pavimentos asfálticos no la piden, así que el selector de
    #: graduación se esconde y el archivo guarda la cadena vacía.
    GRAD_AFIRMADO = ("A-38", "A-25")
    GRAD_BASE = ("BG-40", "BG-27", "BG-38", "BG-25")
    GRAD_SUBBASE = ("SBG-50", "SBG-38")
    GRADUACIONES = {ALCANCE_AFIRMADO: GRAD_AFIRMADO,
                    ALCANCE_BASE: GRAD_BASE,
                    ALCANCE_SUBBASE: GRAD_SUBBASE}

    def _build_muestra(self, parent):
        """Caja de la muestra: carpeta de trabajo, abrir y guardar.

        Va antes de la identificación porque es la acción de primer nivel:
        se entra por el archivo, no escribiendo los datos a mano.
        """
        f = ttk.LabelFrame(parent, text=" Muestra ",
                           style="Card.TLabelframe", padding=9,
                           labelanchor="n")
        f.pack(fill="x", pady=2)

        # --- acciones primero: son el uso principal de la sección ---
        # `expand` + `anchor` para que los dos botones queden centrados en la
        # caja, y el mismo `width` en ambos para que midan lo mismo: el texto
        # más corto no los dejaba iguales.
        fila = ttk.Frame(f, style="Card.TFrame")
        fila.pack(fill="x")
        # Un marco intermedio con `anchor="center"` es lo que centra de verdad:
        # con `expand` en los botones, `pack` reparte el sobrante entre las
        # zonas que ocupa cada uno, pero el botón sigue dibujándose a la
        # izquierda de su zona y los dos quedaban arrimados al borde.
        centro = ttk.Frame(fila, style="Card.TFrame")
        centro.pack(anchor="center")
        ttk.Button(centro, text="Abrir muestra", style="Accent.TButton",
                   width=self.ANCHO_BTN, command=self._abrir_muestra
                   ).pack(side="left", padx=(0, 8))
        ttk.Button(centro, text="Guardar muestra", style="Ghost.TButton",
                   width=self.ANCHO_BTN, command=self._guardar_muestra
                   ).pack(side="left")

        # --- carpeta de trabajo, debajo de los botones ---
        tk.Label(f, text="Directorio de trabajo", bg=CARD, fg=MUT,
                 font=(FAM_UI, 9), anchor="w").pack(fill="x", pady=(10, 2))
        caja = tk.Frame(f, bg=CARD, highlightbackground=BORDE,
                        highlightthickness=1)
        caja.pack(fill="x")
        self.v_dir = tk.StringVar(value=self._leer_dir())
        ent = tk.Entry(caja, textvariable=self.v_dir, bd=0, relief="flat",
                       highlightthickness=0, bg=CARD, fg=TXT, justify="left",
                       font=(FAM_UI, 9), insertbackground=TXT)
        ent.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 2))
        ent.bind("<FocusIn>", lambda ev, w=caja: w.config(
            highlightbackground=ACC, highlightthickness=1))
        ent.bind("<FocusOut>", lambda ev, w=caja: w.config(
            highlightbackground=BORDE, highlightthickness=1))
        ToolTip(ent, "Carpeta de trabajo. 'Guardar muestra' escribe aquí, "
                     "con el nombre que armen los datos de la muestra.")
        btn_dir = tk.Button(caja, text="📁", font=("Segoe UI Emoji", 9),
                            bg=CARD, fg=ACC, relief="flat", bd=0, padx=0,
                            pady=0, activebackground=CREMA, cursor="hand2",
                            command=self._elegir_dir)
        btn_dir.pack(side="right", padx=(2, 3))
        ToolTip(btn_dir, "Elegir la carpeta de trabajo.")

        # --- tipo de muestra y alcance ---
        # El tipo dice para qué va la muestra; el alcance, más abajo, solo tiene
        # sentido en control de calidad: son las tres familias de ensayo que se
        # manejan como control de calidad. En suelos se esconde porque no aplica.
        tk.Label(f, text="Tipo", bg=CARD, fg=MUT,
                 font=(FAM_UI, 9), anchor="w").pack(fill="x", pady=(10, 2))
        self.sel_tipo = SelectDropdown(f, list(self.TIPOS_MUESTRA),
                                       inicial=self.TIPO_SUELOS, ancho=22)
        self.sel_tipo.pack(fill="x")
        ToolTip(self.sel_tipo, "Suelos: caracterización del terreno. "
                               "Control de calidad: verificación de un "
                               "material puesto en obra.")

        self._caja_alcance = tk.Frame(f, bg=CARD)
        lbl_alc = tk.Label(self._caja_alcance, text="Alcance", bg=CARD, fg=MUT,
                           font=(FAM_UI, 9), anchor="w")
        lbl_alc.pack(fill="x", pady=(10, 2))
        self.sel_alcance = SelectDropdown(
            self._caja_alcance, list(self.ALCANCES_CC),
            inicial=self.ALCANCE_AFIRMADO, ancho=22)
        self.sel_alcance.pack(fill="x")
        ToolTip(self.sel_alcance, "Familia de ensayo dentro de control de "
                                  "calidad.")

        # La graduación depende del alcance: cada familia tiene las suyas y
        # estructuras, drenajes y pavimentos no tienen ninguna. Se deja la
        # lista completa de graduaciones en el desplegable y se limita con
        # `values`, en vez de crear un selector por familia.
        self._caja_graduacion = tk.Frame(f, bg=CARD)
        lbl_grad = tk.Label(self._caja_graduacion, text="Tipo de graduación",
                            bg=CARD, fg=MUT, font=(FAM_UI, 9), anchor="w")
        lbl_grad.pack(fill="x", pady=(10, 2))
        self.sel_graduacion = SelectDropdown(
            self._caja_graduacion, list(self.GRAD_AFIRMADO),
            inicial=self.GRAD_AFIRMADO[0], ancho=22)
        self.sel_graduacion.pack(fill="x")
        ToolTip(self.sel_graduacion, "Graduación exigida para el material "
                                     "de esta familia.")
# Una graduación recuerda por familia. Al pasar por Afirmados y volver a
        # Bases, se recupera lo que se había escogido en Bases en vez de
        # volver a la primera de la lista.
        self._grad_por_familia = {}
        #: familia a la que pertenece la lista que hay en pantalla en este
        #: momento. Sin esto no se sabe en qué carpeta guardar el valor que
        #: se está dejando, y se acabaría guardando BG-27 como si fuera la
        #: graduación de Afirmados.
        self._familia_grad = ""

        # Los tres selectores alimentan el reporte, así que los tres tienen que
        # rehacer la vista previa. Antes solo se sincronizaba la lista de
        # graduaciones y la serie de tamices: el "reporte en vivo" se quedaba
        # congelado con los datos anteriores hasta que se escribiera en otro
        # campo. "Guardar PDF" sí salía bien, porque recalcula desde cero.
        #
        # `trace` en vez de un comando: si la variable cambia por cualquier vía
        # (elegir en el desplegable, cargar una muestra, restaurar un archivo)
        # pasa por aquí igual, y el selector no queda desincronizado con la
        # lista de alcances.
        self.sel_tipo.var.trace_add(
            "write", lambda *a: self._cambio_de_seleccion())
        self.sel_alcance.var.trace_add(
            "write", lambda *a: self._cambio_de_seleccion())
        self.sel_graduacion.var.trace_add(
            "write", lambda *a: self._cambio_de_seleccion())
        self._sincronizar_alcance()

        # Se guarda la referencia para poder insertar el alcance antes de la
        # ayuda cuando haya que mostrarlo: `pack` solo coloca al final.
        self._ayuda_muestra = ayuda_seccion(
            f,
            "Tipo: qué va a muestrear. Suelos es la caracterización del "
            "terreno; control de calidad, la verificación de un material "
            "puesto en obra.\n"
            "Alcance: solo en control de calidad, la familia de ensayo "
            "(afirmados, estructuras y drenajes, o pavimentos asfálticos). "
            "Se guarda con la muestra y aparece en el reporte.\n"
            "Carpeta de trabajo: donde se guardan las muestras.\n"
            "Abrir muestra: carga una muestra guardada en un archivo .json.\n"
            "Guardar muestra: guarda TODO el ingreso actual (identificación, "
            "humedad, límites y granulometría) en un archivo .json dentro de "
            "la carpeta de trabajo. El nombre se arma con los datos de la "
            "muestra: perforación, número de muestra y GRAD, por ejemplo "
            "PM1_M5_GRAD.json.\n"
            "El archivo es texto plano: se puede revisar, copiar o versionar.")

    def _sincronizar_alcance(self):
        """Muestra u oculta el selector de alcance según el tipo elegido.

        El alcance solo existe en control de calidad. En suelos se esconde la
        fila entera, no solo el desplegable, para que no quede la etiqueta
        "Alcance" colgando sin nada debajo.
        """
        es_cc = (self.sel_tipo.get() == self.TIPO_CC)
        # El estado de `pack` se lee con `winfo_manager()`, no con
        # `winfo_ismapped()`: este último devuelve 0 hasta que la ventana pasa
        # por un ciclo de dibujo completo, así que al cargar una muestra el
        # selector ya estaba empacado pero parecía no estarlo, y el siguiente
        # `pack` lo recolocaba al final de la caja, debajo del símbolo de ayuda.
        self._empacar(self._caja_alcance, es_cc)

        alcance = self.sel_alcance.get()
        graduaciones = self.GRADUACIONES.get(alcance)
        if graduaciones is not None and self._familia_grad != alcance:
            # La lista del desplegable cambia con el alcance: sin esto, tras
            # elegir Afirmados se seguirían ofreciendo las graduaciones de la
            # familia anterior.
            #
            # `self._familia_grad` es la familia a la que pertenece lo que hay
            # ahora en pantalla. Antes de cambiar la lista se guarda ese valor
            # en SU familia, para que al volver a ella se recupere lo que se
            # había escogido en ella y no la primera de la lista.
            if self._familia_grad:
                self._grad_por_familia[self._familia_grad] = \
                    self.sel_graduacion.get()
            elegido = self._grad_por_familia.get(alcance) or ""
            if elegido not in graduaciones:
                elegido = graduaciones[0]
            self.sel_graduacion._values = list(graduaciones)
            self.sel_graduacion.set(elegido)
            self._familia_grad = alcance
        self._empacar(self._caja_graduacion, es_cc and bool(graduaciones))

        # La tabla de granulometría sigue a la serie del alcance. Sin esto, una
        # muestra de afirmados se tamizaría con la serie de suelos: se
        # escribiría un peso en el 1/2" que no se tamizó, y ese peso sumaría al
        # total con un % retenido falso.
        #
        # La sección de granulometría todavía no existe en el primer llamado:
        # la caja de Muestra se construye antes que ella. Se comprueba, en vez
        # de confiar en el orden, porque el orden es justo lo que no conviene
        # hacer depender de un detalle así.
        grano = getattr(self, "grano", None)
        if grano is not None:
            grano.set_serie(serie_para(
                self.TIPO_CC if es_cc else self.TIPO_SUELOS, alcance))

    def _cambio_de_seleccion(self, *_):
        """Reface el reporte cuando se mueve el tipo, el alcance o la graduación.

        Los tres van al mismo sitio por dos caminos: los tres alimentan el
        bloque `ident` que lee el reporte, y el alcance además cambia la serie
        de tamices, con lo que también cambia la curva.

        Se pasa siempre por `_sincronizar_alcance`, incluso al cambiar solo la
        graduación. Es inocuo: si el alcance no ha cambiado, no repuebla la lista
        (el bloque está guardado por `self._familia_grad`) y `set_serie` sale
        temprano porque la serie es la misma. Así una graduación elegida a mano
        no la pisa nadie.

        El candado evita el refresco a destiempo: al cambiar de alcance se
        repuebla la lista de graduaciones, y eso dispara la traza de
        `sel_graduacion`. Sin candado, esa traza refrescaría antes de que se
        haya aplicado la serie nueva de tamices.
        """
        if self._sinc_seleccion:
            return
        self._sinc_seleccion = True
        try:
            self._sincronizar_alcance()
        finally:
            self._sinc_seleccion = False
        # En el primer llamado del build la sección de granulometría todavía no
        # existe, y `_datos` la usaría. Se comprueba en vez de confiar en el
        # orden, porque el orden es justo lo que no conviene hacer depender de
        # un detalle así. Igual que dentro de `_sincronizar_alcance`.
        if getattr(self, "grano", None) is not None:
            self._refresh()

    @staticmethod
    def _empacar(caja, visible):
        """Empaqueta o saca una caja, sin depender de si ya se ha pintado."""
        empacada = (caja.winfo_manager() != "")
        if visible and not empacada:
            caja.pack(fill="x")
        elif not visible and empacada:
            caja.pack_forget()

# ---------------- carpeta de trabajo ----------------
#: Archivo donde se recuerda la carpeta elegida entre sesiones. Va en la
    #: carpeta donde vive la aplicación: empaquetada, junto al `.exe`, para que
    #: la configuración viaje con el programa y no se pierda al cerrar. Sin
    #: empaquetar, en la carpeta del proyecto.
    _CONF = os.path.join(carpeta_datos(), "grad_plas_config.json")

    def _leer_dir(self):
        """Carpeta de trabajo recordada; si no hay, el Escritorio."""
        try:
            with open(self._CONF, encoding="utf-8") as fh:
                d = str(json.load(fh).get("directorio", "")).strip()
            if d and os.path.isdir(d):
                return d
        except Exception:
            pass            # sin configuración, o ilegible: se usa el defecto
        return os.path.expanduser("~/Desktop")

    def _recordar_dir(self, path):
        try:
            with open(self._CONF, "w", encoding="utf-8") as fh:
                json.dump({"directorio": path}, fh, ensure_ascii=False,
                          indent=1)
        except OSError:
            pass          # si no se puede escribir, la app sigue igual

    def _elegir_dir(self):
        d = filedialog.askdirectory(title="Carpeta de trabajo de las muestras",
                                    initialdir=self.v_dir.get() or None)
        if d:
            self.v_dir.set(d)
            self._recordar_dir(d)

    def _dir_trabajo(self):
        d = self.v_dir.get().strip()
        return d if d else os.path.expanduser("~/Desktop")

    def _nombre_base(self, ident):
        """Nombre sin extensión, a partir de los datos de la muestra.

        Se arma con lo que identifica una muestra en el reporte: la exploración
        y la muestra, más el tipo de ensayo y, en control de calidad, la
        graduación.

            Exploración 1, Muestra 3, grad. BG-38  ->  PM-1_M-3_GRAD_BG-38
            Exploración 2, Muestra 5, suelos        ->  A-2_M-5_GRAD

        El prefijo de la exploración sale del tipo elegido (P, PM o A), y si no
        se eligió ninguno se usa PM, que es lo que se suponía siempre. Los
        códigos van con guion, igual que en el reporte, para que el nombre del
        archivo se lea como la hoja.

        La graduación solo se añade en control de calidad; en suelos no existe
        y se omite esa parte en vez de inventar una. Si falta el número de
        exploración o el de muestra, se omite esa parte y el resto sigue igual.
        """
        def limpio(v):
            return re.sub(r"[^0-9A-Za-z_-]+", "", (v or "").strip().upper())

        prefijo = prefijo_exploracion(ident.get("exploracion"))
        sondeo = limpio(ident.get("sondeo"))
        muestra = limpio(ident.get("muestra"))
        partes = []
        if sondeo:
            partes.append("%s-%s" % (prefijo, sondeo))
        if muestra:
            partes.append("M-%s" % muestra)
        partes.append("GRAD")
        graduacion = limpio(ident.get("graduacion"))
        if graduacion:
            partes.append(graduacion)
        return "_".join(partes)

    def _nombre_muestra(self, ident):
        return self._nombre_base(ident) + ".json"

    def _tipo_alcance(self):
        """(tipo, alcance, graduación) elegidos.

        El alcance y la graduación solo tienen valor en control de calidad, y la
        graduación solo en las tres familias que la tienen: en suelos, en
        estructuras y drenajes y en pavimentos asfálticos se devuelven vacías,
        que es lo que viaja al archivo y al reporte.
        """
        tipo = self.sel_tipo.get() or self.TIPO_SUELOS
        if tipo != self.TIPO_CC:
            return tipo, "", ""
        alcance = self.sel_alcance.get() or ""
        if alcance not in self.GRADUACIONES:
            return tipo, alcance, ""
        return tipo, alcance, (self.sel_graduacion.get() or "")

    def _guardar_muestra(self):
        """Guarda la muestra. Abre el diálogo de Windows para elegir dónde.

        El nombre sugerido es el que arma la muestra, y el usuario puede
        conservarlo o cambiarlo, igual que la carpeta. El diálogo abre en la
        carpeta de trabajo y avisa él mismo si el archivo ya existe, así que no
        hace falta una pregunta aparte.
        """
        datos = self._datos()
        ident = self._ident_dict()
        tipo, alcance, graduacion = self._tipo_alcance()
        ident["tipo"] = tipo
        # Se guardan aunque estén vacíos: así el archivo declara que es una
        # muestra de suelos sin graduación, en vez de no decir nada.
        ident["alcance"] = alcance
        ident["graduacion"] = graduacion
        d = self._dir_trabajo()
        if not os.path.isdir(d):
            messagebox.showerror(
                "Guardar muestra",
                "La carpeta de trabajo no existe:\n%s\n\nElíjala de nuevo con "
                "el botón de carpeta." % d)
            return
        path = filedialog.asksaveasfilename(
            title="Guardar muestra",
            initialdir=d,
            initialfile=self._nombre_muestra(ident),
            defaultextension=".json",
            filetypes=[("Muestra GRAD-PLAS", "*.json"),
                       ("Todos los archivos", "*.*")],
            confirmoverwrite=True)
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"formato": "GRAD-PLAS muestra", "version": 1,
                           "ident": ident, "datos": datos},
                          fh, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("Guardar muestra",
                                 "No se pudo escribir el archivo:\n%s" % e)
            return
        messagebox.showinfo("Guardar muestra", "Muestra guardada:\n%s" % path)

    def _build_identidad(self, parent):
        f = ttk.LabelFrame(parent, text=" Información de la muestra ",
                           style="Card.TLabelframe", padding=9, labelanchor="n")
        f.pack(fill="x", pady=2)
        f.columnconfigure(1, weight=1)
        self._val_ent = validar_tecla(self, "entero")
        self._v_txt = self.register(self._val_txt)
        self._v_nombre = self.register(self._val_nombre)
        self._v_alfanum = self.register(self._val_alfanum)
        self._v_fecha = self.register(self._val_fecha)
        self._v_prof = self.register(self._val_prof)

        # orden: de lo más general (proyecto) a lo más específico de la muestra
        #
        # El tipo de exploración va entre "Ordenado por" y el número de
        # exploración porque es lo que explica ese número: un 2 puede ser una
        # perforación o un apique, y son cosas distintas. El rótulo del campo
        # se llama "Exploración N°" y no "Perforación N°" por lo mismo.
        campos = [
            ("proyecto", "Proyecto", "txt", False),
            ("sector", "Sector", "txt", False),
            ("ordenado", "Ordenado por", "nombre", False),
            ("exploracion", "Tipo de exploración", "exploracion", False),
            ("sondeo", "Exploración N°", "alfanum", False),
            ("muestra", "Muestra N°", "entero", False),
            ("fecha_toma", "Fecha de toma", "fecha", True),
            ("fecha_ejecucion", "Fecha de ejecución", "fecha", True),
        ]
        self.ident_ents = []
        self._casillas_ident = []
        for i, (k, lab, tip, cal) in enumerate(campos):
            tk.Label(f, text=lab, bg=CARD, fg=TXT,
                     font=(FAM_UI, 10)).grid(row=i, column=0,
                                                 sticky="e", padx=(2, 6), pady=2)
            if tip == "exploracion":
                self._fila_exploracion(f, i)
                continue
            frm = tk.Frame(f, bg=CARD, highlightbackground=SUP,
                           highlightthickness=1)
            frm.grid(row=i, column=1, padx=3, pady=2, sticky="ew")
            e = self._entry_ident(frm, self.idvars[k], tip,
                                  width=17 if k == "sondeo" else 22)
            e.pack(side="left", fill="x", expand=True, ipady=2, padx=5)
            if cal:
                cal_btn = tk.Button(frm, text="📅", font=("Segoe UI Emoji", 8),
                                    bg=CARD, fg=ACC, relief="flat", bd=0,
                                    padx=0, pady=0,
                                    activebackground=SUP, cursor="hand2")
                cal_btn.pack(side="right", padx=(2, 4))
                cal_btn.config(
                    command=lambda v=self.idvars[k], b=cal_btn:
                        self._abrir_calendario(v, b))
            e.bind("<Down>", lambda ev, idx=i: self._ident_mov(idx, +1))
            e.bind("<Return>", lambda ev, idx=i: self._ident_mov(idx, +1, True))
            e.bind("<Up>", lambda ev, idx=i: self._ident_mov(idx, -1))
            e.bind("<KeyRelease>", self._a_mayusculas, add="+")
            self.ident_ents.append(e)
            self._casillas_ident.append((self.idvars[k], e))


        # ---------------- profundidad: rango "6.00 m a 5.60 m" ----------------
        i = len(campos)
        tk.Label(f, text="Profundidad (m)", bg=CARD, fg=TXT,
                 font=(FAM_UI, 10)).grid(row=i, column=0,
                                            sticky="e", padx=(2, 6), pady=2)
        pfrm = tk.Frame(f, bg=CARD)
        pfrm.grid(row=i, column=1, padx=3, pady=2, sticky="ew")
        f1 = tk.Frame(pfrm, bg=CARD, highlightbackground=SUP,
                      highlightthickness=1)
        f1.pack(side="left", fill="both", expand=True)
        d1 = self._entry_ident(f1, self.idvars["prof_desde"], "prof", width=8)
        d1.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 0))
        tk.Label(f1, text="m", bg=CARD, fg=MUT, font=(FAM_UI, 8),
                 padx=2).pack(side="right")
        tk.Label(pfrm, text="a", bg=CARD, fg=TXT, font=(FAM_UI, 10)
                 ).pack(side="left", padx=(6, 6))
        f2 = tk.Frame(pfrm, bg=CARD, highlightbackground=SUP,
                      highlightthickness=1)
        f2.pack(side="left", fill="both", expand=True)
        d2 = self._entry_ident(f2, self.idvars["prof_hasta"], "prof", width=8)
        d2.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 0))
        tk.Label(f2, text="m", bg=CARD, fg=MUT, font=(FAM_UI, 8),
                 padx=2).pack(side="right")
        base = len(self.ident_ents)
        for clave, wdg in (("prof_desde", d1), ("prof_hasta", d2)):
            idx = base + (0 if clave == "prof_desde" else 1)
            wdg.bind("<Down>", lambda ev, i=idx: self._ident_mov(i, +1))
            wdg.bind("<Return>", lambda ev, i=idx: self._ident_mov(i, +1, True))
            wdg.bind("<Up>", lambda ev, i=idx: self._ident_mov(i, -1))
            wdg.bind("<KeyRelease>", self._a_mayusculas, add="+")
            self.ident_ents.append(wdg)
            self._casillas_ident.append((self.idvars[clave], wdg))

        # ---------------- color del material (texto corto) ----------------
        # La descripción del material la compone sola el reporte a partir de
        # la clasificación SUCs, así que aquí solo se registra el color, que
        # es lo único que el laboratorio observa y la app no puede deducir.
        i += 1
        tk.Label(f, text="Color", bg=CARD, fg=TXT,
                 font=(FAM_UI, 10)).grid(row=i, column=0, sticky="ne",
                                            padx=(2, 6), pady=2)
        dfrm = tk.Frame(f, bg=CARD, highlightbackground=SUP, highlightthickness=1)
        dfrm.grid(row=i, column=1, padx=3, pady=2, sticky="ew")
        self.ident_desc = tk.Text(dfrm, bd=0, relief="flat",
                                  highlightthickness=0, bg=CARD, fg=TXT,
                                  insertbackground=TXT, font=(FAM_UI, 10),
                                  height=1, wrap="word", undo=True)
        self.ident_desc.pack(fill="x", padx=5, pady=2)
        self.ident_desc.bind("<FocusIn>", lambda ev, fw=dfrm: fw.config(
            highlightbackground=ACC, highlightthickness=1))
        self.ident_desc.bind("<FocusOut>", lambda ev, fw=dfrm: fw.config(
            highlightbackground=SUP, highlightthickness=1))
        # El color es el último campo del recorrido: Enter y Tab dan la vuelta
        # al primer campo, y la flecha arriba vuelve al campo anterior.
        # izquierda/derecha se dejan para mover el cursor al editar el texto.
        self.ident_desc.bind("<Return>", lambda ev: (
            self._ident_foco_primero(), "break"))
        self.ident_desc.bind("<Tab>", lambda ev: (
            self._ident_foco_primero(), "break"))
        self.ident_desc.bind("<Up>", lambda ev: (
            self._ident_foco_ultimo(), "break"))
        self.ident_desc.bind("<Down>", lambda ev: (
            self._ident_foco_primero(), "break"))
        self.ident_desc.bind("<KeyRelease>", lambda ev: (self._a_mayusculas(),
                                                         self._ajustar_desc(),
                                                         self._refresh()))
        self.ident_desc.bind("<Configure>", self._ajustar_desc)

        ayuda_seccion(f, "\n".join((
            "Proyecto: nombre del proyecto o contrato.",
            "Sector: ubicación de la muestra dentro del proyecto.",
            "Ordenado por: técnico que solicitó el ensayo.",
            "Perforación N°: sondeo o apique del que proviene la muestra."
            "Muestra N°: número de la muestra ensayada.",
            "Fecha de toma / Fecha de ejecución: cuándo se tomó y se ensayó, "
            "en formato DD/MM/AAAA. También se puede elegir con el calendario.",
            "Profundidad (m): rango de profundidad del muestreo (a): inicio, "
            "b): fin. Permite N.A. (no aplica).",
            "Color: color del suelo tal como se observa en campo, por ejemplo "
            "'café oscuro con vetas grises'. El reporte lo añade al final de "
            "la descripción que se deriva de la clasificación SUCs, de modo "
            "que el texto completo queda como 'Arcillas de plasticidad alta, "
            "de color café oscuro con vetas grises'. Si se deja vacío, se "
            "imprime solo la descripción automática.")))

    def _fila_exploracion(self, f, fila):
        """Fila del desplegable de tipo de exploración.

        Va con el resto de campos de identificación y por eso entra en la
        navegación con las flechas: si no, el <Abajo> de "Ordenado por" se
        saltaría esta fila para irse a "Exploración N°".

        Empieza vacía a propósito. Sin tipo elegido el reporte pone el rótulo
        de siempre y el número suelto, que es como salen las muestras
        guardadas antes de que existiera el campo, en vez de suponer una
        perforación mecánica que el usuario nunca dijo.
        """
        self.sel_exploracion = SelectDropdown(
            f, list(NOMBRES_EXPLORACION), inicial="", ancho=22)
        self.sel_exploracion.grid(row=fila, column=1, padx=3, pady=2,
                                  sticky="ew")
        ToolTip(self.sel_exploracion,
                "Decide cómo se rotula la exploración en el reporte y el "
                "prefijo de su número: P, PM o A.")
        ent = self.sel_exploracion.entry
        for seq, signo in (("<Down>", +1), ("<Return>", +1), ("<Up>", -1)):
            ent.bind(seq, lambda ev, idx=fila, d=signo, s=seq:
                     self._ident_mov(idx, d, s == "<Return>"))
        # El reporte lee el rótulo y el prefijo de aquí, así que el cambio tiene
        # que rehacerlo igual que cualquier otro dato de identificación.
        self.sel_exploracion.var.trace_add(
            "write", lambda *a: self._refresh())

    def _entry_ident(self, parent, var, tip, width=22):
        """Crea un campo de entrada validado según el tipo de dato."""
        e = tk.Entry(parent, textvariable=var, bd=0, relief="flat",
                     highlightthickness=0, bg=CARD, fg=TXT,
                     insertbackground=TXT, font=(FAM_UI, 10), width=width,
                     validate="key",
                     validatecommand=(self._cmd_ident(tip), "%P"))
        e.bind("<FocusIn>", lambda ev, fw=parent: fw.config(
            highlightbackground=ACC, highlightthickness=1))
        e.bind("<FocusOut>", lambda ev, tip=tip, v=var: (
            self._ident_focusout(parent), self._fmt_ident(v, tip)))
        e.bind("<Button-1>", lambda ev, w=e: w.config(
            insertwidth=2, insertbackground=TXT))
        return e

    def _ident_focusout(self, parent):
        parent.config(highlightbackground=SUP, highlightthickness=1)

    def _a_mayusculas(self, *_):
        """Fuerza mayúsculas en todo el texto de identificación.

        El reporte reproduce estos textos tal cual, así que convertirlos al
        escribir evita que en el PDF aparezca una línea en minúscula o
        combinada junto a las demás, que van todas en mayúscula. El cursor
        se lleva al final porque, al reescribir la variable, Tk lo deja
        donde estaba y el texto parecería saltarse caracteres.
        """
        for var, wdg in self._casillas_ident:
            v = var.get()
            if v and v != v.upper():
                var.set(v.upper())
                try:
                    wdg.icursor("end")
                except tk.TclError:
                    pass
        txt = self.ident_desc.get("1.0", "end-1c")
        may = txt.upper()
        if may != txt:
            pos = self.ident_desc.index("insert")
            self.ident_desc.delete("1.0", "end-1c")
            self.ident_desc.insert("1.0", may)
            self.ident_desc.mark_set("insert", pos)
            # el cambio de caja no debe llenar el historial de deshacer
            self.ident_desc.edit_reset()

    def _ajustar_desc(self, *_):
        """Ajusta la altura de la descripción al contenido, creciendo hacia abajo."""
        try:
            res = self.ident_desc.count("1.0", "end-1c", "displaylines")
            if res is None:
                n = 1
            elif isinstance(res, (tuple, list)):
                n = int(res[0]) if res else 1
            else:
                n = int(res)
            n = max(1, n)
        except (tk.TclError, AttributeError, ValueError):
            texto = self.ident_desc.get("1.0", "end-1c")
            n = max(1, texto.count("\n") + 1 if texto else 1)
        self.ident_desc.configure(height=min(n, 24))

    # ---------------- validación por tipo de dato ----------------
    def _cmd_ident(self, tip):
        return {"txt": self._v_txt, "nombre": self._v_nombre,
                "alfanum": self._v_alfanum, "entero": self._val_ent,
                "fecha": self._v_fecha, "prof": self._v_prof}[tip]

    def _val_txt(self, P):
        """Texto corto: cualquier carácter imprimible."""
        return P == "" or P.isprintable()

    def _val_nombre(self, P):
        """Nombre propio: letras, espacios y . - , y también números.

        Se aceptan números porque en la orden de trabajo cabe tanto el nombre
        de quien solicita el ensayo como su cédula, un lote o un número de
        contrato, y anotar "4547392" no es un nombre pero sí un dato válido del
        mismo campo.
        """
        if P == "":
            return True
        return re.fullmatch(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9 .'\-]+", P) is not None

    def _val_alfanum(self, P):
        """Texto alfanumérico (permite N.A.)."""
        return P == "" or re.fullmatch(r"[A-Za-z0-9 .\-/_()]+", P) is not None

    def _val_fecha(self, P):
        """Fecha DD/MM/AAAA: solo dígitos y / o -"""
        return P == "" or all(c.isdigit() or c in "/-" for c in P)

    def _val_prof(self, P):
        """Profundidad: decimal (permite , o .) o literal N.A."""
        if P == "":
            return True
        if P.upper() in ("N", "N.", "N.A", "N.A."):
            return True
        return re.fullmatch(r"\d*[,.]\d*|\d+", P) is not None

    # ---------------- formateo al salir del campo ----------------
    def _fmt_ident(self, var, tip):
        v = var.get().strip()
        if tip == "fecha":
            var.set(self._fmt_fecha(v))
        elif tip == "prof":
            var.set(self._fmt_prof(v))
        elif tip in ("txt", "nombre", "alfanum") and v:
            var.set(v.upper())

    def _fmt_fecha(self, v):
        if not v:
            return ""
        v = v.replace("-", "/")
        parts = v.split("/")
        if len(parts) == 3 and parts[2].isdigit() and len(parts[2]) >= 4:
            try:
                return "%d/%d/%s" % (int(parts[0]), int(parts[1]), parts[2][:4])
            except ValueError:
                return v
        return v

    def _fmt_prof(self, v):
        if not v:
            return ""
        if v.upper() in ("N.A.", "N.A", "NA"):
            return "N.A."
        n = fnum(v)
        if n is not None:
            return "%.2f" % n
        return v

    # ---------------- calendario desplegable para fechas ----------------
    def _abrir_calendario(self, var, wdg):
        top = tk.Toplevel(self)
        top.title("Fecha")
        top.resizable(False, False)
        top.configure(bg=CARD)
        top.attributes("-topmost", True)
        top.bind("<Escape>", lambda e: top.destroy())

        hoy = datetime.date.today()

        def fecha_actual():
            v = self._fmt_fecha(var.get().strip())
            try:
                d, m, y = v.split("/")
                return datetime.date(int(y), int(m), int(d))
            except Exception:
                return None

        base = fecha_actual() or hoy
        anio = tk.IntVar(value=base.year)
        mes = tk.IntVar(value=base.month)

        cab = tk.Frame(top, bg=CARD)
        cab.pack(fill="x", padx=6, pady=(6, 2))
        tk.Button(cab, text="◀", bg=CARD, fg=TXT, relief="flat",
                  activebackground=SUP, font=(FAM_UI, 9, "bold"),
                  command=lambda: self._cal_mover(anio, mes, -1, pintar)
                  ).pack(side="left", padx=2)
        titulo = tk.Label(cab, text="", bg=CARD, fg=ACC,
                          font=(FAM_UI, 10, "bold"))
        titulo.pack(side="left", expand=True)
        tk.Button(cab, text="▶", bg=CARD, fg=TXT, relief="flat",
                  activebackground=SUP, font=(FAM_UI, 9, "bold"),
                  command=lambda: self._cal_mover(anio, mes, +1, pintar)
                  ).pack(side="left", padx=2)

        sem = tk.Frame(top, bg=CARD)
        sem.pack(fill="x", padx=6)
        for d in ("L", "M", "M", "J", "V", "S", "D"):
            tk.Label(sem, text=d, bg=CARD, fg=MUT, width=2,
                     font=(FAM_UI, 8)).pack(side="left", expand=True)

        dias = tk.Frame(top, bg=CARD)
        dias.pack(fill="x", padx=6, pady=(1, 3))
        celdas = []
        for fi in range(6):
            for cj in range(7):
                b = tk.Button(dias, text="", bg=CARD, fg=TXT, relief="flat",
                              activebackground=SUP, width=2,
                              font=(FAM_UI, 8))
                b.grid(row=fi, column=cj, sticky="nsew", padx=0, pady=1)
                celdas.append(b)

        def seleccionar(d):
            var.set("%02d/%02d/%d" % (d.day, d.month, d.year))
            top.destroy()

        def pintar():
            y, m = anio.get(), mes.get()
            titulo.config(text="%s %d" % (MESES[m - 1], y))
            primero = datetime.date(y, m, 1)
            inicio = primero.weekday()
            fin = datetime.date(y + (1 if m == 12 else 0),
                                (1 if m == 12 else m + 1), 1)
            dim = (fin - primero).days
            sel = fecha_actual()
            for i, b in enumerate(celdas):
                dia = i - inicio + 1
                if 1 <= dia <= dim:
                    d = datetime.date(y, m, dia)
                    fg = ACC_D if sel == d else (ACC if d == hoy else TXT)
                    b.config(text=str(dia), state="normal", foreground=fg,
                             command=lambda d=d: seleccionar(d))
                else:
                    b.config(text="", state="disabled", command=None)

        pie = tk.Frame(top, bg=CARD)
        pie.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(pie, text="Hoy  %s" % hoy.strftime("%d/%m/%Y"), bg=ACC,
                  fg="#ffffff", activebackground=ACC_D, relief="flat",
                  font=(FAM_UI, 9, "bold"),
                  command=lambda: seleccionar(hoy)).pack(fill="x", ipady=1)

        pintar()
        try:
            top.geometry("+%d+%d" % (wdg.winfo_rootx(),
                                     wdg.winfo_rooty() + wdg.winfo_height() + 4))
        except Exception:
            pass
        top.after(1, top.grab_set)
        top.focus_set()

    def _cal_mover(self, anio, mes, delta, pintar):
        m = mes.get() + delta
        y = anio.get()
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        mes.set(m)
        anio.set(y)
        pintar()

    # ---------------- navegación entre campos ----------------
    def _ident_mov(self, idx, d, wrap=False):
        """Desplaza el foco entre los campos de identificación.

        El color va después del último campo y es un Text, no un Entry, así
        que llegar al final del último Entry salta siempre al color. La vuelta
        al primer campo se hace desde el propio color, no desde el campo
        anterior: antes el Enter de la profundidad daba la vuelta y se saltaba
        el color.
        """
        n = len(self.ident_ents)
        if d > 0:
            if idx >= n - 1:
                self._ident_foco_txt()
                return
            ni = idx + 1
        else:
            ni = max(idx - 1, 0)
        e = self.ident_ents[ni]
        e.focus_set()
        self._ident_sel(e)

    def _ident_foco_txt(self):
        """Foco en el campo de color, con el texto seleccionado."""
        self.ident_desc.focus_set()
        self._ident_sel_txt()

    def _ident_foco_primero(self):
        """Vuelta al primer campo (fin del recorrido del formulario)."""
        e = self.ident_ents[0]
        e.focus_set()
        self._ident_sel(e)

    def _ident_foco_ultimo(self):
        """Vuelta al último Entry, que es justo antes del color."""
        e = self.ident_ents[-1]
        e.focus_set()
        self._ident_sel(e)

    def _ident_sel(self, w):
        """Estilo Excel: borde resaltado y sin cursor titilando."""
        w.config(insertwidth=2, insertbackground=w.cget("bg"))
        try:
            w.selection_range(0, "end")
            w.icursor("end")
        except tk.TclError:
            pass

    def _ident_sel_txt(self):
        try:
            self.ident_desc.tag_add("sel", "1.0", "end-1c")
            self.ident_desc.mark_set("insert", "end-1c")
        except tk.TclError:
            pass

    # ---------------- datos ----------------
    def _cargar_ejemplo(self):
        solo = None if self.ejemplo_tipo.get() == "Aleatorio" \
            else self.ejemplo_tipo.get()
        d = datos_ejemplo(solo=solo)
        for sec in (self.hum, self.lim, self.grano):
            sec.cargar(d)
        ident = d.get("ident", {})
        for k in self.idvars:
            if k in ident:
                self.idvars[k].set(ident[k])
        # El tipo de exploración no está en `idvars`: es un desplegable, no un
        # campo de texto. Si el ejemplo no trae ninguno, se deja como esté.
        if "exploracion" in ident:
            self.sel_exploracion.set(ident["exploracion"])
        self.ident_desc.delete("1.0", "end")
        self.ident_desc.insert("1.0", ident.get("descripcion", ""))
        self._ajustar_desc()

    def _limpiar(self):
        for sec in (self.hum, self.lim, self.grano):
            sec.limpiar()
        for v in self.idvars.values():
            v.set("")
        self.ident_desc.delete("1.0", "end")
        self._ajustar_desc()

    def _datos(self):
        """Datos del ensayo, con la serie de tamices que corresponde.

        `tipo` y `alcance` viajan en el bloque de granulometría, y no solo en la
        identificación: el motor elige la serie de tamices con ellos. Si
        faltaran, el cálculo usaría la serie de suelos para una muestra de
        afirmados, y la curva saldría con tamices que no se tamizaron.

        La identificación también se incluye en el diccionario, porque el
        reporte la lee de ahí (`_id_campo`) y sin ella el tipo salía siempre
        como suelos: el PDF solo recibía la lista de rótulos, que no lleva
        tipo, alcance ni graduación.
        """
        lim = self.lim.leer()
        tipo, alcance, grad = self._tipo_alcance()
        grano = self.grano.leer()
        grano["tipo"] = tipo
        grano["alcance"] = alcance
        grano["graduacion"] = grad
        ident = self._ident_dict()
        return {"hum": self.hum.leer(), "ll": lim["ll"],
                "ll_np": self.lim.sin_plasticidad(), "lp": lim["lp"],
                "grano": grano, "ident": ident}

    def _ident_dict(self):
        """Identificación como diccionario (no como lista de rótulos).

        Incluye el tipo de muestra y, en control de calidad, el alcance, para
        que el reporte pueda imprimirlos sin volver a preguntar a la interfaz.

        El tipo de exploración viaja tal cual se eligió, sin anteponerle el
        prefijo al número: el prefijo depende del rótulo de la fila, y el código
        completo lo compone el reporte. Si se compusiera en los dos lados, un
        archivo guardado con un tipo y abierto con otro se vería distinto en la
        hoja y en su nombre.
        """
        d = {k: v.get().strip() for k, v in self.idvars.items()}
        d["descripcion"] = self.ident_desc.get("1.0", "end-1c").strip()
        d["tipo"], d["alcance"], d["graduacion"] = self._tipo_alcance()
        d["exploracion"] = self.sel_exploracion.get().strip()
        return d

    # ---------------- muestra: archivo de la muestra ----------------
    #: Claves de un archivo de muestra y su tipo, para validar al cargar.
    _CLAVES_MUESTRA = {
        "hum": dict, "ll": list, "lp": list, "ll_np": bool,
        "grano": dict, "ident": dict,
    }

    def _aplicar_muestra(self, datos, ident):
        """Vuelca una muestra en la interfaz (datos + identificación).

        El tipo y el alcance se ponen ANTES de cargar la granulometría: ellos
        deciden la serie de tamices, así que la sección tiene que saber cuál
        aplica antes de recibir los pesos. Al revés, una muestra de afirmados se
        volcaría sobre la serie de suelos y el peso del 3/8" caería en la fila
        del 1/2".
        """
        for k, v in self.idvars.items():
            v.set("" if ident.get(k) is None else str(ident[k]))
        self.ident_desc.delete("1.0", "end")
        self.ident_desc.insert("1.0", ident.get("descripcion") or "")
        self._ajustar_desc()
        # El tipo va antes del alcance: al poner "Control de calidad" la traza
        # muestra el selector de alcance, y la del alcance fija la serie de
        # tamices de la sección de granulometría.
        tipo = ident.get("tipo") or self.TIPO_SUELOS
        if tipo not in self.TIPOS_MUESTRA:
            tipo = self.TIPO_SUELOS
        self.sel_tipo.set(tipo)
        alcance = ident.get("alcance") or ""
        if alcance not in self.ALCANCES_CC:
            alcance = ""
        self.sel_alcance.set(alcance or self.ALCANCE_AFIRMADO)
        # El tipo de exploración se pone después del alcance, pero antes de la
        # graduación: es un dato independiente de ambos y solo hay que
        # descartar un valor que no exista en la lista.
        #
        # Las muestras guardadas antes de que existiera el campo no lo tienen,
        # y eso está bien: se abren con el desplegable vacío y el reporte las
        # sigue mostrando como "PERFORACIÓN", que es como se veían.
        tipo_exp = ident.get("exploracion") or ""
        if datos_exploracion(tipo_exp) is None:
            tipo_exp = ""
        self.sel_exploracion.set(tipo_exp)
        # La graduación se lee después de poner el alcance: la traza del
        # alcance ya deja la lista con los valores de esa familia, y solo
        # entonces tiene sentido restaurar el valor que traía el archivo.
        graduacion = ident.get("graduacion") or ""
        if graduacion not in self.sel_graduacion.values:
            graduacion = ""
        if graduacion:
            self.sel_graduacion.set(graduacion)
            # Se apunta como elegida para esta familia, para que al pasar por
            # otra y volver no se pierda.
            self._grad_por_familia[self._familia_grad] = graduacion
        # Ahora sí: la serie de tamices ya es la del archivo, y los pesos se
        # reencuadran por nombre al cargarlos.
        for sec in (self.hum, self.lim, self.grano):
            sec.cargar(datos)
        self._refresh()

    def _abrir_muestra(self):
        """Carga una muestra desde un archivo .json."""
        ruta = self._dir_trabajo()
        if not os.path.isdir(ruta):
            ruta = os.path.expanduser("~/Desktop")
        path = filedialog.askopenfilename(
            title="Abrir muestra", filetypes=[("Muestra GRAD-PLAS", "*.json"),
                                              ("Todos los archivos", "*.*")],
            initialdir=ruta)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as e:
            messagebox.showerror(
                "Abrir muestra",
                "No se pudo leer el archivo:\n%s\n\nDebe ser un archivo de "
                "muestra guardado por esta aplicación (.json)." % e)
            return
        if not isinstance(doc, dict) or "datos" not in doc:
            messagebox.showerror(
                "Abrir muestra",
                "El archivo no parece una muestra de esta aplicación.\n"
                "Falta la sección 'datos'.")
            return
        datos, ident = doc["datos"], doc.get("ident", {})
        faltan = [k for k, t in self._CLAVES_MUESTRA.items()
                  if k != "ident" and not isinstance(datos.get(k), t)]
        if faltan or not isinstance(ident, dict):
            messagebox.showerror(
                "Abrir muestra",
                "El archivo está incompleto o dañado.\nFalta o no corresponde: "
                "%s." % ", ".join(faltan + (["ident"] if faltan else [])))
            return
        # Las filas de los ensayos pueden venir de un archivo más antiguo o
        # editado a mano: se recorta al número de casillas que hay en pantalla.
        for k, n in (("ll", 3), ("lp", 2)):
            filas = datos[k]
            datos[k] = filas[:n] + [{} for _ in range(max(0, n - len(filas)))]
        self._aplicar_muestra(datos, ident)
        messagebox.showinfo("Abrir muestra", "Muestra cargada:\n%s" % path)

    def _ident(self):
        out = []
        for k, lab in [("proyecto", "Proyecto"), ("sector", "Sector"),
                       ("ordenado", "Ordenado por"),
                       ("muestra", "Muestra N°"),
                       ("fecha_toma", "Fecha de toma"),
                       ("fecha_ejecucion", "Fecha de ejecución")]:
            v = self.idvars[k].get().strip()
            if k == "muestra":
                v = codigo_muestra(v)
            if v:
                out.append("%s: %s" % (lab, v))
        tipo_exp = self.sel_exploracion.get().strip()
        if tipo_exp:
            out.append("Tipo de exploración: %s" % tipo_exp)
        v = codigo_exploracion(self.idvars["sondeo"].get(), tipo_exp)
        if v:
            out.append("Exploración N°: %s" % v)
        desde = self.idvars["prof_desde"].get().strip()
        hasta = self.idvars["prof_hasta"].get().strip()
        vals = [x for x in (desde, hasta) if x]
        if len(vals) == 2 and all(x == "N.A." for x in vals):
            out.append("Profundidad (m): N.A.")
        elif len(vals) == 2:
            out.append("Profundidad (m): %s - %s m" % (desde, hasta))
        elif len(vals) == 1:
            if vals[0] == "N.A.":
                out.append("Profundidad (m): N.A.")
            else:
                out.append("Profundidad (m): %s m" % vals[0])
        color = self.ident_desc.get("1.0", "end").strip()
        if color:
            out.append("Color: %s" % color)
        return out

    # ---------------- actualizacion en vivo ----------------
    def _refresh(self, *_):
        datos = self._datos()
        self._datos_actuales = datos
        self._res_actuales = motor_calcular(datos)
        res = self._res_actuales
        self.hum.mostrar(res)
        self.lim.mostrar(res)
        self.grano.mostrar(res)
        self._schedule_preview()

    def _schedule_preview(self, ms=350):
        if self._preview_after is not None:
            self.after_cancel(self._preview_after)
        self._preview_after = self.after(ms, self._render_preview)

    def _zoom_preview(self, _page=None):
        """Factor de escala de la vista, tomado del control de zoom."""
        return self._factor_zoom()

    def _render_preview(self):
        self._preview_after = None
        if self._datos_actuales is None:
            return
        try:
            import fitz
        except ImportError:
            self._show_preview_msg("Para ver el reporte en vivo, instala PyMuPDF:\n  pip install pymupdf")
            return
        try:
            from reporte.pdf import preview_pdf
            pdf = preview_pdf(self._datos_actuales, self._res_actuales,
                         self._ident(), firmar=self.firmar.get())
            doc = fitz.open(pdf)
            z = self._zoom_preview()
            imgs = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(z, z))
                png = pix.tobytes("png")
                img = tk.PhotoImage(data=png)
                imgs.append(img)
            doc.close()
        except Exception as e:
            self._show_preview_msg("No se pudo generar el reporte:\n%s" % e)
            return

        for w in self.report_area.winfo_children():
            w.destroy()
        self._imgs = imgs
        for img in imgs:
            # aire alrededor de la hoja, para que no quede pegada al borde.
            # Con `expand=True` la hoja queda centrada en el panel: pegada al
            # borde izquierdo se veía descuadrada al abrir la app.
            #
            # El desplazamiento del visor no hay que guardarlo ni devolverlo
            # después: al destruir y recrear las etiquetas dentro de la MISMA
            # llamada, el bucle de eventos no llega a ver el área vacía y Tk
            # conserva la posición de lectura. Si algún día se rehiciera el
            # visor en dos vueltas del bucle, eso dejaría de ser cierto.
            lab = tk.Label(self.report_area, image=img, bg=FONDO_VISOR,
                           highlightthickness=1, highlightbackground=BORDE_HOJA)
            lab.pack(side="top", expand=True,
                     padx=self.PAD_HOJA, pady=self.PAD_HOJA)

    def _show_preview_msg(self, text):
        for w in self.report_area.winfo_children():
            w.destroy()
        ttk.Label(self.report_area, text=text, foreground=MUT,
                  font=(FAM_UI, 9), justify="left").pack(anchor="w", pady=8)

    # ---------------- guardar PDF ----------------
    def _pdf(self):
        try:
            # Sonda de disponibilidad: no se usa el módulo, solo se comprueba
            # que esté instalado para poder avisar con un mensaje claro.
            import reportlab  # noqa: F401
        except ImportError:
            messagebox.showerror("Guardar PDF",
                                 "No se encontró reportlab.\nInstala con:  pip install reportlab")
            return
        from reporte.pdf import report_pdf
        datos = self._datos()
        res = motor_calcular(datos)
        ident = self._ident_dict()
        d = self._dir_trabajo()
        if not os.path.isdir(d):
            messagebox.showerror(
                "Guardar PDF",
                "La carpeta de trabajo no existe:\n%s\n\nElíjala de nuevo con "
                "el botón de carpeta." % d)
            return
        # El PDF va con el nombre del archivo de muestra y solo cambia la
        # extensión: PM-1_M-3_GRAD_BG-38.json deja su reporte en
        # PM-1_M-3_GRAD_BG-38.pdf, al lado. Así los dos archivos se reconocen
        # como el par que son. Se abre el diálogo de Windows para que el
        # usuario pueda cambiar el nombre o la carpeta, como en la muestra.
        path = filedialog.asksaveasfilename(
            title="Guardar PDF",
            initialdir=d,
            initialfile=self._nombre_base(ident) + ".pdf",
            defaultextension=".pdf",
            filetypes=[("Reporte PDF", "*.pdf"),
                       ("Todos los archivos", "*.*")],
            confirmoverwrite=True)
        if not path:
            return
        try:
            # Se pasa el diccionario de identificación, no la lista de
            # rótulos: `self._ident()` no lleva tipo, alcance ni graduación, y
            # sin ellos el reporte salía siempre como "Suelos" y sin
            # graduación, aunque en pantalla se hubiera elegido control de
            # calidad.
            report_pdf(datos, res, ident, path, firmar=self.firmar.get())
        except Exception as e:
            messagebox.showerror("Guardar PDF", "Error al generar el PDF:\n%s" % e)
            return
        messagebox.showinfo("Guardar PDF", "Reporte guardado:\n%s" % path)
        try:
            os.startfile(path)
        except Exception:
            pass