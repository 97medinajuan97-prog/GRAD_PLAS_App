# -*- coding: utf-8 -*-
"""Ventana principal: panel izquierdo de ingreso (secciones) + panel derecho
con el reporte en vivo. Cada sección es un módulo independiente."""
import datetime
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui_theme import (aplicar_estilo, ScrollableFrame, ACC, ACC_D, BG,
                      CARD, MUT, SUP, TXT, FAM_UI, VERSION, validar_tecla,
                      ayuda_seccion, SelectDropdown)
from secciones.humedad import Humedad
from secciones.limites import Limites
from secciones.granulometria import Granulometria
from motor.calculo import calcular as motor_calcular, fnum
from datos_ejemplo import datos_ejemplo, SIMBOLOS

#: Título de la ventana. Antes se escribía literal dos veces (título del
#: `Tk` y rótulo de la franja superior) y cualquier corrección había que
#: replicarla en ambos sitios, con el riesgo de que se desincronizaran.
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

        self._build()

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
        self.right_sc = ScrollableFrame(split)

        def _ajustar_split(_e=None):
            tot = split.winfo_width()
            h = split.winfo_height()
            if tot < 40 or h < 24:
                return
            usable = tot - 6
            rw = int(round(usable * 0.618))
            lw = usable - rw
            self.left_sc.place(x=0, y=0, width=lw, height=h)
            self.right_sc.place(x=lw + 6, y=0, width=rw, height=h)

        split.bind("<Configure>", _ajustar_split)
        left = self.left_sc.inner()
        self.right = self.right_sc.inner()

        # ---- panel izquierdo: secciones independientes ----
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

        # ---- panel derecho: reporte en vivo ----
        bar = ttk.Frame(self.right)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="Reporte en vivo", style="TLabel",
                  font=(FAM_UI, 11, "bold")).pack(side="left")
        ttk.Button(bar, text="Guardar PDF", style="Accent.TButton",
                   command=self._pdf).pack(side="right", padx=2)
        ttk.Label(self.right, text="Edita los datos a la izquierda y este reporte se actualiza solo.",
                  foreground="#6e7781", font=(FAM_UI, 8)).pack(anchor="w", pady=(0, 4))
        self.report_area = ttk.Frame(self.right)
        self.report_area.pack(fill="both", expand=True)
        self._imgs = []

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1180, sw - 60)
        h = min(800, sh - 100)
        self.geometry("%dx%d+%d+%d" % (w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 3)))
        self.right_sc.bind_resize(lambda: self._schedule_preview())

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
        campos = [
            ("proyecto", "Proyecto", "txt", False),
            ("sector", "Sector", "txt", False),
            ("ordenado", "Ordenado por", "nombre", False),
            ("sondeo", "Perforación N°", "alfanum", False),
            ("muestra", "Muestra N°", "entero", False),
            ("fecha_toma", "Fecha de toma", "fecha", True),
            ("fecha_ejecucion", "Fecha de ejecución", "fecha", True),
        ]
        self.ident_ents = []
        for i, (k, lab, tip, cal) in enumerate(campos):
            tk.Label(f, text=lab, bg=CARD, fg=TXT,
                     font=(FAM_UI, 10)).grid(row=i, column=0,
                                                sticky="e", padx=(2, 6), pady=2)
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
            self.ident_ents.append(e)

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
        for rel, wdg in ((0, d1), (1, d2)):
            idx = base + rel
            wdg.bind("<Down>", lambda ev, i=idx: self._ident_mov(i, +1))
            wdg.bind("<Return>", lambda ev, i=idx: self._ident_mov(i, +1, True))
            wdg.bind("<Up>", lambda ev, i=idx: self._ident_mov(i, -1))
            self.ident_ents.append(wdg)

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
        self.ident_desc.bind("<Return>", lambda ev: (
            self._ident_mov(len(self.ident_ents) - 1, +1, True), "break"))
        self.ident_desc.bind("<KeyRelease>", lambda ev: (self._ajustar_desc(),
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
        """Nombre propio: solo letras (con acentos), espacios y . -"""
        return P == "" or re.fullmatch(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü .'-]+", P) is not None

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
        """Desplaza el foco entre los campos de identificación."""
        n = len(self.ident_ents)
        if d > 0:
            if idx >= n - 1:
                if wrap:
                    self.ident_ents[0].focus_set()
                    self._ident_sel(self.ident_ents[0])
                else:
                    self.ident_desc.focus_set()
                    self._ident_sel_txt()
                return
            ni = idx + 1
        else:
            ni = max(idx - 1, 0)
        e = self.ident_ents[ni]
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
            self.ident_desc.tag_add("sel", "1.0", "end")
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
        lim = self.lim.leer()
        return {"hum": self.hum.leer(), "ll": lim["ll"],
                "ll_np": self.lim.sin_plasticidad(), "lp": lim["lp"],
                "grano": self.grano.leer()}

    def _ident(self):
        out = []
        for k, lab in [("proyecto", "Proyecto"), ("sector", "Sector"),
                       ("ordenado", "Ordenado por"), ("muestra", "Muestra N°"),
                       ("fecha_toma", "Fecha de toma"),
                       ("fecha_ejecucion", "Fecha de ejecución")]:
            v = self.idvars[k].get().strip()
            if v:
                out.append("%s: %s" % (lab, v))
        v = self.idvars["sondeo"].get().strip()
        if v:
            out.append("Perforación N°: %s" % v)
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
            pdf = preview_pdf(self._datos_actuales, self._res_actuales, self._ident())
            doc = fitz.open(pdf)
            width = self.right_sc.canvas_width()
            imgs = []
            for page in doc:
                z = width / page.rect.width
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
            lab = tk.Label(self.report_area, image=img, bg="#ffffff",
                           highlightthickness=1, highlightbackground="#d7dade")
            lab.pack(side="top", pady=2)

    def _show_preview_msg(self, text):
        for w in self.report_area.winfo_children():
            w.destroy()
        ttk.Label(self.report_area, text=text, foreground="#6e7781",
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
        nombre = "GRAD-PLAS_reporte_%s.pdf" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Guardar reporte PDF", defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile=nombre,
            initialdir=os.path.expanduser("~/Desktop"))
        if not path:
            return
        try:
            report_pdf(datos, res, self._ident(), path)
        except Exception as e:
            messagebox.showerror("Guardar PDF", "Error al generar el PDF:\n%s" % e)
            return
        messagebox.showinfo("Guardar PDF", "Reporte guardado:\n%s" % path)
        try:
            os.startfile(path)
        except Exception:
            pass