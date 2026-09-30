# -*- coding: utf-8 -*-
"""
SECCIÓN 1 · Humedad natural (INV E-122).

Distribución en dos columnas (sin títulos): a la izquierda el ingreso
(N° recipiente, Wc, W1, W2) y a la derecha los resultados (Ww, Ws, ω).
El peso seco del suelo (Ws = W2 − Wc) es el TOTAL que se usa en la
granulometría (Sección 3), por eso en granulometría no se pide el total:
allí aparece solo como "Peso antes de lavado (w1)".

  ω = (Ww / Ws) × 100
"""
import tkinter as tk

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, ToolTip,
                      FAM_UI, validar_tecla, ayuda_seccion)
from motor.calculo import fnum


def calcular_humedad(ht):
    """Fórmula pura (sin UI). ht: dict recip/hum/seco.

    Devuelve ω%, peso del agua (Ww), peso del suelo seco (Ws) y el W seco.
    `Ws` es el total que consume la granulometría como peso seco de la
    muestra, así que ambos ensayos quedan atados por este mismo valor."""
    recip = ht.get("recip")
    hum = ht.get("hum")
    seco = ht.get("seco")
    if any(x is None or x <= 0 for x in (recip, hum, seco)):
        return {"w": None, "w_agua": None, "w_suelo": None, "seco_usado": seco}
    w_agua = hum - seco
    w_suelo = seco - recip
    if w_suelo <= 0:
        return {"w": None, "w_agua": w_agua, "w_suelo": w_suelo, "seco_usado": seco}
    w = w_agua / w_suelo * 100
    return {"w": w, "w_agua": w_agua, "w_suelo": w_suelo, "seco_usado": seco}


def aviso_incoherencia(ht, res):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    recip, hum, seco = ht["recip"], ht["hum"], ht["seco"]
    if all(x is None for x in (recip, hum, seco)):
        return "", ""
    if any(x is None for x in (recip, hum, seco)):
        return "⚠ Datos incompletos", "Ingrese Wc, W1 y W2."
    if any(x <= 0 for x in (recip, hum, seco)):
        return "⚠ Datos incoherentes", "Los pesos deben ser mayores que cero."
    if hum <= seco:
        return "⚠ Datos incoherentes", "W1 debe ser mayor que W2."
    if seco <= recip:
        return "⚠ Datos incoherentes", "W2 debe ser mayor que Wc."
    w = res.get("w")
    if w is not None and not (0 <= w <= 100):
        return "⚠ Fuera de rango", "Humedad (ω) fuera de 0–100 %."
    return "", ""


class Humedad(Seccion):
    titulo = " 1 · Humedad natural "

    #: (símbolo, unidad, significado) de cada casilla
    D = {
        "id": ("N°", "", "Número o identificación del recipiente (tara), p. ej. A-1."),
        "recip": ("Wc", "g", "Wc = peso del recipiente (tara), en gramos."),
        "hum": ("W1", "g", "W1 = peso del recipiente + suelo húmedo, en gramos."),
        "seco": ("W2", "g", "W2 = peso del recipiente + suelo seco, en gramos. "
                             "De aquí sale el peso seco del suelo (Ws = W2 − Wc)."),
        "agua": ("Ww", "g", "Ww = peso del agua = W1 − W2, en gramos."),
        "suelo": ("Ws", "g", "Ws = peso del suelo seco = W2 − Wc, en gramos."),
        "res": ("ω", "%", "ω = humedad natural del suelo = (Ww / Ws) × 100."),
    }

    #: texto completo del '?' de la sección (todas las variables a la vez)
    SIG_FULL = "\n".join(
        "· %s (%s): %s" % (s, u, t) for s, u, t in D.values())

    #: Disposición del ingreso: dos filas de dos casillas.
    #: Los resultados (Ww, Ws y ω) ya no se muestran aquí; se leen en el
    #: reporte, junto a la granulometría que se apoya en el peso seco.
    FILAS = (
        ("id", "recip"),
        ("hum", "seco"),
    )

    def __init__(self, master):
        super().__init__(master)
        self._val_dec = validar_tecla(self.winfo_toplevel(), "decimal")

        self.v_id = tk.StringVar()
        self.v_recip = tk.StringVar()
        self.v_hum = tk.StringVar()
        self.v_seco = tk.StringVar()
        self.registrar(self.v_id, self.v_recip, self.v_hum, self.v_seco)

        self._inputs = []
        self._build_cuerpo()
        self._bind_navegacion()

        self.aviso_lbl = tk.Label(self, text="", foreground="#a0432e",
                                  bg=CARD, font=(FAM_UI, 9, "bold"))
        self.aviso_lbl.grid(row=2, column=0, sticky="e",
                            padx=2, pady=(4, 0))
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._ayuda = ayuda_seccion(self, self.SIG_FULL)

    # ---------------- ingreso en dos filas de dos casillas ----------------
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        cuerpo.grid(row=1, column=0, sticky="ew")
        for c in range(2):
            cuerpo.columnconfigure(c, weight=1, uniform="hum")
        for f, grupo in enumerate(self.FILAS):
            for c, clave in enumerate(grupo):
                self._celda(cuerpo, f, c, clave)

    def _celda(self, parent, fila, col, clave):
        """Casilla con su rótulo a la izquierda, en una rejilla 2x2."""
        simbolo, unidad, _sig = self.D[clave]
        marco = tk.Frame(parent, bg=CARD)
        marco.grid(row=fila, column=col, sticky="ew", padx=(0, 12),
                   pady=2)
        marco.columnconfigure(1, weight=1)
        lbl = tk.Frame(marco, bg=CARD)
        lbl.grid(row=0, column=0, sticky="w", padx=(0, 6))
        tk.Label(lbl, text=simbolo, font=(FAM_UI, 10), fg=TXT,
                 bg=CARD).pack(side="left")
        if unidad:
            tk.Label(lbl, text=" (%s)" % unidad, font=(FAM_UI, 10),
                     fg=MUT, bg=CARD).pack(side="left")
        editable = clave in ("id", "recip", "hum", "seco")
        frm, num = self.caja(marco, getattr(self, "v_" + clave), unidad,
                             editable=editable,
                             tipo="decimal" if clave != "id" else "texto")
        frm.grid(row=0, column=1, sticky="ew")
        if editable:
            self._inputs.append(num)

    # ---------------- casillas y teclado ----------------
    def caja(self, parent, var, unidad="", editable=True, tipo="decimal"):
        """Caja de valor: fondo blanco y valor centrado. La unidad va en la
        etiqueta de la variable (como en las cajas de resultado de la
        granulometría). Las cajas numéricas solo aceptan números
        (validación)."""
        bg = "#ffffff"
        frm = tk.Frame(parent, bg=bg, highlightbackground=SUP, highlightthickness=1)
        num = tk.Entry(frm, textvariable=var, bd=0, relief="flat",
                       highlightthickness=0, bg=bg, fg=TXT, insertbackground=TXT,
                       disabledbackground=bg, readonlybackground=bg,
                       justify="center",
                       font=(FAM_UI, 10), width=7,
                       state="normal" if editable else "readonly",
                       validate="key" if editable and tipo != "texto" else "none",
                       validatecommand=(self._val_dec, "%P")
                       if editable and tipo != "texto" else None)
        num.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 2))
        if editable:
            num.bind("<FocusIn>", lambda ev, f=frm, n=num: (
                f.config(highlightbackground=ACC, highlightthickness=1),
                self._seleccionar(n)))
            num.bind("<FocusOut>", lambda ev, f=frm, t=tipo: (
                f.config(highlightbackground=SUP, highlightthickness=1),
                self._formatear_entrada(num, var) if t != "texto" else None))
            num.bind("<Button-1>", lambda ev, n=num: self._seleccionar(n))
        return frm, num

    def _formatear_entrada(self, num, var):
        """Al salir de la casilla, el valor queda con 2 decimales fijos."""
        v = fnum(var.get())
        if v is not None:
            var.set("%.2f" % v)

    def _bind_navegacion(self):
        """↑/↓ y Enter se mueven solo entre las celdas de ingreso."""
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
        """Enter: baja a la siguiente celda (vuelve al inicio al terminar)."""
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
        return {"id": self.v_id.get().strip(),
                "recip": fnum(self.v_recip.get()),
                "hum": fnum(self.v_hum.get()),
                "seco": fnum(self.v_seco.get())}

    def mostrar(self, res):
        # Los resultados (Ww, Ws, ω) no se muestran en la sección: se leen
        # en el reporte. Aquí solo queda el aviso de coherencia del ingreso.
        corto, detalle = aviso_incoherencia(self.leer(), res)
        self.aviso_lbl.config(text=corto)
        self._aviso_tip.set_text(detalle)

    def cargar(self, ejemplo):
        h = ejemplo["hum"]
        self.v_id.set(h.get("id", ""))
        self.v_recip.set("" if h["recip"] is None else str(h["recip"]))
        self.v_hum.set("" if h["hum"] is None else str(h["hum"]))
        self.v_seco.set("" if h["seco"] is None else str(h["seco"]))

    def limpiar(self):
        for v in (self.v_recip, self.v_hum, self.v_seco):
            v.set("")
        self.v_id.set("")
        self.aviso_lbl.config(text="")
        self._aviso_tip.set_text("")
