# -*- coding: utf-8 -*-
"""
SECCIÓN 3 · Granulometría por tamizado (INV E-123).

Sección independiente: la curva completa (retenidos → % ret. → % acum. →
% pasa), los diámetros D60/D30/D10 (interpolación logarítmica), Cu, Cc,
% grava/arena/finos y tipo. De aquí salen los insumos para la clasificación.

El peso antes de lavado (w1) es el peso seco del suelo sin contenedor (Ws)
y lo toma la app de la Sección 1 (Humedad natural). El peso después de
lavado (w2) = w1 − retenido en el fondo.
"""
import math
import tkinter as tk
from tkinter import ttk

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, ToolTip,
                      FAM_SERIF, validar_tecla, ayuda_seccion)
from motor.calculo import fnum

SIEVES = [
    ('3"', 76.2), ('2 1/2"', 63.5), ('2"', 50.8), ('1 1/2"', 38.1),
    ('1"', 25.4), ('3/4"', 19.05), ('3/8"', 9.525),
    ('N° 4', 4.75), ('N° 10', 2.0), ('N° 40', 0.425),
    ('N° 200', 0.075), ('FONDO', 0.0),
]
DIAM = [d for _, d in SIEVES]


def calcular_granulometria(d):
    """d: {'total': texto|None, 'pesos': 11 pesos retenidos}. Curva completa.
    El fondo se calcula restando la suma del total (o se ignora si viene
    como 12º elemento 'auto')."""
    total = fnum(d.get("total"))
    pesos = list(d["pesos"])
    if len(pesos) > 11:
        pesos = pesos[:11]
    sumw = sum(w for w in pesos if w is not None)
    fondo = (total - sumw) if total is not None else None
    total_ef = total if total is not None else sumw

    F = []
    sieve = []
    cum = 0.0
    comb = list(pesos) + [fondo]
    for i, w in enumerate(comb):
        if w is not None:
            cum += w
        ret_p = (w / total_ef * 100) if (w is not None and total_ef) else None
        pasa = (100 - cum / total_ef * 100) if total_ef else None
        if i == len(comb) - 1 and fondo is not None and pasa is not None:
            pasa = 0.0
        if pasa is not None and abs(pasa) < 1e-9:
            pasa = 0.0
        F.append(pasa)
        sieve.append({
            "tamiz": SIEVES[i][0], "diam": DIAM[i], "w": w,
            "ret_p": ret_p,
            "acum_p": (cum / total_ef * 100) if total_ef else None,
            "pasa": pasa,
        })

    def interp(P):
        for k in range(len(F) - 1):
            a, b = F[k], F[k + 1]
            if a is None or b is None:
                continue
            if a >= P >= b:
                d1, d2 = DIAM[k], DIAM[k + 1]
                if d2 <= 0:
                    return None
                return math.pow(10, math.log10(d1) + (math.log10(d2) - math.log10(d1)) * (P - a) / (b - a))
        return None

    d60, d30, d10 = interp(60), interp(30), interp(10)
    cu = (d60 / d10) if (d60 is not None and d10 is not None and d10 > 0) else None
    cc = (d30 ** 2 / (d60 * d10)
          if (d60 and d30 is not None and d10 is not None and d60 * d10 > 0) else None)

    F4, F200 = F[7], F[10]
    grava = (100 - F4) if F4 is not None else None
    arena = (F4 - F200) if (F4 is not None and F200 is not None) else None
    tipo = ("GRANULAR" if F200 <= 35 else "FINO") if F200 is not None else None

    return {
        "fondo": fondo, "sum_ret": sumw, "sieve": sieve, "F": F,
        "d60": d60, "d30": d30, "d10": d10, "cu": cu, "cc": cc,
        "grava": grava, "arena": arena, "finos": F200, "tipo": tipo,
        "f4": F4, "f10": F[8], "f40": F[9], "f200": F200,
    }


def aviso_incoherencia(pesos, total):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    no = [p for p in pesos if p is not None]
    if not no:
        return "", ""
    if any(p < 0 for p in no):
        return "⚠ Datos incoherentes", "Los pesos retenidos no pueden ser negativos."
    if len(no) < len(pesos):
        return "⚠ Datos incompletos", "Falta el peso retenido de algún tamiz."
    s = sum(no)
    if total is not None and s > total:
        return "⚠ Datos incoherentes", ("La suma de retenidos (%.1f g) supera "
                                         "el peso total (%.1f g)." % (s, total))
    return "", ""


class Granulometria(Seccion):
    titulo = " 3 · Granulometría por tamizado "

    #: significado de cada variable (todas en un único '?' de la sección)
    SIG = {
        "w1": "w1 = peso antes de lavado: peso seco del suelo sin contenedor "
              "(Ws = W2 − Wc), tomado de la Sección 1 (Humedad natural).",
        "w2": "w2 = peso después de lavado: w1 − retenido en el fondo "
              "(lo que queda sobre los tamices tras lavar los finos < N° 200).",
        "tamiz": "Apertura nominal de cada tamiz, en mm.",
        "preto": "Peso del suelo retenido sobre cada tamiz, en gramos. "
                 "El del fondo se calcula automáticamente.",
        "retp": "% Retenido = 100 × peso ret. / W1.",
        "acum": "% Acumulado = suma de los retenidos sobre los tamices anteriores.",
        "pasa": "% Pasa = 100 − % acumulado (lo que atraviesa cada tamiz).",
        "d60": "D60 = diámetro para el 60 % del material que pasa (mm).",
        "d30": "D30 = diámetro para el 30 % del material que pasa (mm).",
        "d10": "D10 = diámetro para el 10 % del material que pasa (mm).",
        "cu": "Cu = D60 / D10 (coeficiente de uniformidad).",
        "cc": "Cc = D30² / (D60·D10) (coeficiente de curvatura).",
        "g": "Grava = 100 − %pasa N°4 · Arena = %pasa N°4 − %pasa N°200 · "
             "Finos = %pasa N°200. Su suma debe ser 100 %.",
        "sucs": "Clasificación SUCs (ASTM D-2487): según el % que pasa N° 200, "
                "el % de grava/arena y la plasticidad (LL y IP de la Sección 2).",
    }
    SIG_FULL = "\n".join("%s\n%s" % (k.upper() if k in (
        "w1", "w2") else ("· " + k), v) for k, v in (
        ("w1", SIG["w1"]), ("w2", SIG["w2"]), ("preto", SIG["preto"]),
        ("retp", SIG["retp"]), ("acum", SIG["acum"]), ("pasa", SIG["pasa"]),
        ("d60", SIG["d60"]), ("d30", SIG["d30"]), ("d10", SIG["d10"]),
        ("cu", SIG["cu"]), ("cc", SIG["cc"]), ("g", SIG["g"]),
        ("sucs", SIG["sucs"])))

    def __init__(self, master):
        super().__init__(master)
        self._val_dec = validar_tecla(self.winfo_toplevel(), "decimal")
        self.v_w1 = tk.StringVar()
        self.v_w2l = tk.StringVar()
        self.v_fondo = tk.StringVar()
        self.v_fondo.set("auto")
        self.peso_vars = [tk.StringVar() for _ in SIEVES[:-1]]
        self.registrar(*self.peso_vars)
        self.v_res = [[tk.StringVar() for _ in range(3)] for _ in range(12)]
        self.v_d60, self.v_d30, self.v_d10 = (tk.StringVar() for _ in range(3))
        self.v_cu, self.v_cc = tk.StringVar(), tk.StringVar()
        self.v_grava, self.v_arena, self.v_finos = (tk.StringVar() for _ in range(3))

        self._build_pesos()
        self._build_cuerpo()
        self._build_resumen()
        self._bind_navegacion()

        self.aviso_lbl = tk.Label(self, text="", foreground="#a0432e",
                                  bg=CARD, font=(FAM_SERIF, 9, "bold"))
        self.aviso_lbl.grid(row=6, column=0, sticky="e", padx=2, pady=(6, 0))
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._ayuda = ayuda_seccion(self, self.SIG_FULL)

    # ---------------- pesos: antes y después de lavado (W1 / W2) ----------------
    def _build_pesos(self):
        fila = tk.Frame(self, bg=CARD)
        fila.grid(row=0, column=0, sticky="w", pady=(0, 10))
        tk.Label(fila, text="W1",
                 font=(FAM_SERIF, 10), fg=TXT, bg=CARD).pack(side="left")
        tk.Label(fila, text=" (g)",
                 font=(FAM_SERIF, 10), fg=MUT, bg=CARD).pack(side="left")
        frm, num = self.caja(fila, self.v_w1, editable=False)
        frm.pack(side="left", padx=(10, 0))
        tk.Label(fila, text="W2",
                 font=(FAM_SERIF, 10), fg=TXT, bg=CARD).pack(side="left",
                                                             padx=(22, 0))
        tk.Label(fila, text=" (g)",
                 font=(FAM_SERIF, 10), fg=MUT, bg=CARD).pack(side="left")
        frm2, num2 = self.caja(fila, self.v_w2l, editable=False)
        frm2.pack(side="left", padx=(10, 0))

    # ---------------- tabla: ingreso (izquierda) | resultados (derecha) ----
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        cuerpo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        tabla = tk.Frame(cuerpo, bg=CARD)
        tabla.pack(side="left", fill="both", expand=True)
        self._build_tabla(tabla)

    def _cabecera(self, parent, col, texto, negra=False, unidad=None):
        cel = tk.Frame(parent, bg=CARD)
        cel.grid(row=0, column=col, sticky="ew", pady=(0, 2))
        lbl = tk.Frame(cel, bg=CARD)
        lbl.pack()
        tk.Label(lbl, text=texto, font=(FAM_SERIF, 10),
                 fg=TXT if negra else MUT, bg=CARD).pack(side="left")
        if unidad:
            tk.Label(lbl, text=" (%s)" % unidad, font=(FAM_SERIF, 10),
                     fg=MUT, bg=CARD).pack(side="left")

    def _build_tabla(self, tabla):
        for c, (texto, uni) in enumerate((
                ("Tamiz", None), ("\u00d8", "mm"), ("Peso ret.", "g"),
                ("% Ret.", None), ("% Acum.", None), ("% Pasa", None))):
            self._cabecera(tabla, c, texto, negra=True, unidad=uni)
            tabla.columnconfigure(c, weight=1, uniform="granos")
        self._inputs = []
        for i, (tam, d) in enumerate(SIEVES):
            r = i + 1
            tk.Label(tabla, text=tam, bg=CARD, fg=TXT,
                     font=(FAM_SERIF, 10)).grid(row=r, column=0, sticky="w",
                                                padx=2, pady=2)
            tk.Label(tabla, text="%g" % d, bg=CARD, fg=TXT,
                     font=(FAM_SERIF, 10)).grid(row=r, column=1, sticky="w",
                                                padx=2, pady=2)
            if tam == "FONDO":
                frm, num = self.caja(tabla, self.v_fondo, editable=False)
                frm.grid(row=r, column=2, sticky="ew", padx=2, pady=2)
                self._fondo_num = num
            else:
                frm, num = self.caja(tabla, self.peso_vars[i], editable=True)
                frm.grid(row=r, column=2, sticky="ew", padx=2, pady=2)
                self._inputs.append(num)
            for c in range(3):
                frm, num = self.caja(tabla, self.v_res[i][c],
                                     editable=False, ancho=8)
                frm.grid(row=r, column=3 + c, sticky="ew", padx=2, pady=2)

    # ---------------- resumen: D60/D30/D10, Cu/Cc, grava/arena/finos --------
    def _build_resumen(self):
        sep = tk.Frame(self, bg=SUP, height=1)
        sep.grid(row=2, column=0, sticky="ew", pady=(8, 6))

        tab = tk.Frame(self, bg=CARD)
        tab.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        for c in range(3):
            tab.columnconfigure(c, weight=1, uniform="gresum")

        def celda(fila_r, col, simbolo, var, unidad=""):
            cel = tk.Frame(tab, bg=CARD)
            cel.grid(row=fila_r, column=col, sticky="ew", padx=(0, 14),
                     pady=(0, 2) if fila_r < 2 else (0, 0))
            cel.columnconfigure(0, minsize=80)
            cel.columnconfigure(1, weight=1)
            lbl = tk.Frame(cel, bg=CARD)
            lbl.grid(row=0, column=0, sticky="w")
            tk.Label(lbl, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                     bg=CARD).pack(side="left")
            if unidad:
                tk.Label(lbl, text=" (%s)" % unidad, font=(FAM_SERIF, 10),
                         fg=MUT, bg=CARD).pack(side="left")
            if var is not None:
                frm, num = self.caja(cel, var, editable=False)
                frm.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        for c, (sim, var, uni) in enumerate((
                ("D60", self.v_d60, "mm"), ("D30", self.v_d30, "mm"),
                ("D10", self.v_d10, "mm"))):
            celda(0, c, sim, var, uni)
        for c, (sim, var, uni) in enumerate((("Cu", self.v_cu, ""),
                                             ("Cc", self.v_cc, ""))):
            celda(1, c, sim, var, uni)
        for c, (sim, var, uni) in enumerate((
                ("Grava", self.v_grava, "%"), ("Arena", self.v_arena, "%"),
                ("Finos", self.v_finos, "%"))):
            celda(2, c, sim, var, uni)

        fila = tk.Frame(self, bg=CARD)
        fila.grid(row=4, column=0, sticky="w", pady=(4, 0))
        tk.Label(fila, text="Clase:", bg=CARD, fg=TXT,
                 font=(FAM_SERIF, 10)).pack(side="left")
        self.tipo_lbl = tk.Label(fila, text="—", bg=CARD, fg=TXT,
                                 font=(FAM_SERIF, 10))
        self.tipo_lbl.pack(side="left", padx=(2, 16))
        tk.Label(fila, text="SUCs:", bg=CARD, fg=TXT,
                 font=(FAM_SERIF, 10)).pack(side="left")
        self.sucs_lbl = tk.Label(fila, text="—", bg=CARD, fg=TXT,
                                 font=(FAM_SERIF, 10, "bold"))
        self.sucs_lbl.pack(side="left", padx=(2, 0))

        self.sucs_desc = tk.Label(self, text="", bg=CARD, fg=MUT,
                                  font=(FAM_SERIF, 9), anchor="w",
                                  justify="left", wraplength=390)
        self.sucs_desc.grid(row=5, column=0, sticky="ew", padx=2, pady=(2, 0))

    def _celda_res(self, parent, var, simbolo, unidad):
        fr = tk.Frame(parent, bg=CARD)
        fr.pack(side="left", padx=(0, 14))
        tk.Label(fr, text=simbolo, font=(FAM_SERIF, 10), fg=MUT,
                 bg=CARD).pack(side="left")
        frm, num = self.caja(fr, var, unidad, editable=False)
        frm.pack(side="left", padx=(6, 0))
        return num

    # ---------------- casillas y teclado ----------------
    def caja(self, parent, var, unidad="", editable=True, ancho=7):
        """Caja de valor: fondo blanco, valor a la derecha sin unidades
        (la unidad va en la etiqueta de la variable). El borde mantiene siempre
        el mismo grosor (no se desplaza al enfocar).
        Al recibir foco se selecciona el contenido y el cursor queda oculto."""
        bg = "#ffffff"
        frm = tk.Frame(parent, bg=bg, highlightbackground=SUP, highlightthickness=1)
        num = tk.Entry(frm, textvariable=var, bd=0, relief="flat",
                       highlightthickness=0, bg=bg, fg=TXT,
                       disabledbackground=bg, disabledforeground=TXT,
                       readonlybackground=bg, insertbackground=TXT,
                       justify="center", font=(FAM_SERIF, 10), width=ancho,
                       state="normal" if editable else "readonly",
                       validate="key" if editable else "none",
                       validatecommand=(self._val_dec, "%P") if editable else None)
        num.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 2))
        if editable:
            num.bind("<FocusIn>", lambda ev, f=frm, n=num: (
                f.config(highlightbackground=ACC, highlightthickness=1),
                self._seleccionar(n)))
            num.bind("<FocusOut>", lambda ev, f=frm: (
                f.config(highlightbackground=SUP, highlightthickness=1),
                self._formatear_entrada(num, var)))
            num.bind("<Button-1>", lambda ev, n=num: self._seleccionar(n))
        return frm, num

    def _formatear_entrada(self, num, var):
        """Al salir de la casilla, el valor queda con 2 decimales fijos."""
        v = fnum(var.get())
        if v is not None:
            var.set("%.2f" % v)

    def _bind_navegacion(self):
        """↓ y Enter bajan entre los pesos de los tamices; ↑ sube.
        El desplazamiento es solo entre las celdas de ingreso."""
        n = len(self._inputs)
        for i, num in enumerate(self._inputs):
            num.bind("<Up>", lambda ev, i=i: self._nav(i, -1))
            num.bind("<Down>", lambda ev, i=i: self._nav(i, +1))
            num.bind("<Return>", lambda ev, i=i: self._enter(i))

    def _nav(self, i, dr):
        ni = max(0, min(i + dr, len(self._inputs) - 1))
        num = self._inputs[ni]
        num.focus_set()
        self._seleccionar(num)

    def _enter(self, i):
        """Enter: baja al siguiente tamiz (vuelve al 3\" al terminar)."""
        num = self._inputs[(i + 1) % len(self._inputs)]
        num.focus_set()
        self._seleccionar(num)

    def _seleccionar(self, wdg):
        """Estilo Excel: borde resaltado y sin cursor titilando. Al escribir
        el contenido se reemplaza (la celda viene seleccionada)."""
        wdg.config(insertwidth=2, insertbackground=wdg.cget("bg"))
        try:
            wdg.selection_range(0, "end")
            wdg.icursor("end")
        except tk.TclError:
            pass

    # ----------------------------------------------------------------
    def leer(self):
        pesos = []
        for v in self.peso_vars:
            pesos.append(fnum(v.get()))
        return {"total": None, "pesos": pesos}

    def calcular(self):  # requisito de la base
        return calcular_granulometria(self.leer())

    def mostrar(self, res):
        gt = res.get("g_total")
        self.v_w1.set("—" if gt is None else "%.2f" % gt)
        f = res.get("fondo")
        w2 = (gt - f) if (gt is not None and f is not None) else None
        self.v_w2l.set("—" if w2 is None else "%.2f" % w2)
        for i, s in enumerate(res["sieve"]):
            for c, key in ((0, "ret_p"), (1, "acum_p"), (2, "pasa")):
                v = s[key]
                self.v_res[i][c].set("—" if v is None else "%.2f" % v)
        if f is None:
            self.v_fondo.set("auto")
            self._fondo_num.config(fg=MUT)
        else:
            self.v_fondo.set("%.2f" % f)
            self._fondo_num.config(fg=TXT)

        for var, key in ((self.v_d60, "D60"), (self.v_d30, "D30"),
                         (self.v_d10, "D10")):
            v = res.get(key)
            var.set("—" if v is None else "%.2f" % v)
        for var, key in ((self.v_cu, "Cu"), (self.v_cc, "Cc")):
            v = res.get(key)
            var.set("—" if v is None else "%.2f" % v)
        for var, key in ((self.v_grava, "g_grava"), (self.v_arena, "g_arena"),
                         (self.v_finos, "g_finos")):
            v = res.get(key)
            var.set("—" if v is None else "%.2f" % v)

        tipo = res.get("tipo")
        if tipo:
            self.tipo_lbl.config(text=tipo, foreground=TXT)
        else:
            self.tipo_lbl.config(text="—", foreground=MUT)

        sucs = res.get("sucs")
        sucs_db = res.get("sucs_desc")
        if sucs:
            self.sucs_lbl.config(text=sucs, foreground=TXT)
        else:
            self.sucs_lbl.config(text="—", foreground=MUT)
        self.sucs_desc.config(text=sucs_db or "")

        corto, detalle = aviso_incoherencia(self.leer()["pesos"], gt)
        if not corto:
            ga, ar, fi = res.get("g_grava"), res.get("g_arena"), res.get("g_finos")
            if None not in (ga, ar, fi) and abs(ga + ar + fi - 100.0) > 0.65:
                corto = "⚠ Grava+Arena+Finos ≠ 100 %"
                detalle = ("La suma de %grava ({:.1f}) + %arena ({:.1f}) + "
                           "%finos ({:.1f}) debe dar 100 %.".format(ga, ar, fi))
        self.aviso_lbl.config(text=corto)
        self._aviso_tip.set_text(detalle)

    def cargar(self, ejemplo):
        g = ejemplo["grano"]
        for i, v in enumerate(self.peso_vars):
            v.set("" if g["pesos"][i] is None else str(g["pesos"][i]))

    def limpiar(self):
        super().limpiar()
        self.v_w1.set("—")
        self.v_w2l.set("—")
        self.v_fondo.set("auto")
        self._fondo_num.config(fg=MUT)
        for row in self.v_res:
            for v in row:
                v.set("—")
        for v in (self.v_d60, self.v_d30, self.v_d10, self.v_cu, self.v_cc,
                  self.v_grava, self.v_arena, self.v_finos):
            v.set("—")
        self.tipo_lbl.config(text="—", foreground=MUT)
        self.sucs_lbl.config(text="—", foreground=MUT)
        self.sucs_desc.config(text="")
        self.aviso_lbl.config(text="")
        self._aviso_tip.set_text("")