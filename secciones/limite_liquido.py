# -*- coding: utf-8 -*-
"""
SECCIÓN 2.1 · Límite líquido (INV E-125).

Dos columnas: a la izquierda el ingreso de los 3 ensayos (N° golpes, Wc, W1, W2)
y a la derecha las humedades calculadas. El LL se muestra debajo, en una fila
horizontal. Un check permite declarar la muestra sin plasticidad.
"""
import math
import tkinter as tk
from tkinter import ttk

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, ayuda, ToolTip,
                      FAM_SERIF, validar_tecla)
from motor.calculo import fnum, _w


def calcular_ll(rows):
    """rows: [{n, recip, hum, seco}, ...]. Devuelve w% por ensayo y LL."""
    ws = []
    pts = []
    for row in rows:
        w = _w(row["recip"], row["hum"], row["seco"])
        ws.append(w)
        n = row["n"]
        if n and n > 0 and w is not None:
            pts.append((math.log(n), w))
    if len(pts) >= 2:
        n = len(pts)
        mx = sum(x for x, _ in pts) / n
        my = sum(y for _, y in pts) / n
        den = sum(x * x for x, _ in pts) - n * mx * mx
        if abs(den) > 1e-12:
            m = (sum(x * y for x, y in pts) - n * mx * my) / den
            b = my - m * mx
            LL = b + m * math.log(25)
        else:
            LL = None
    else:
        LL = None
    return {"w": ws, "LL": LL}


def aviso_incoherencia(rows):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    keys = ("recip", "hum", "seco")
    llenas = [r for r in rows if all(r[k] is not None for k in keys)]
    tiene = any(r[k] is not None for r in rows for k in keys)
    if not tiene:
        return "", ""
    if not llenas or any(r["n"] is None for r in llenas):
        return "⚠ Datos incompletos", "Complete golpes, Wc, W1 y W2 de cada ensayo."
    for i, r in enumerate(llenas, 1):
        if any(r[k] <= 0 for k in keys) or r["n"] <= 0:
            return "⚠ Datos incoherentes", "Ensayo #%d: los valores deben ser mayores que cero." % i
        if r["hum"] <= r["seco"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W1 debe ser mayor que W2." % i
        if r["seco"] <= r["recip"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W2 debe ser mayor que Wc." % i
    return "", ""


class LimiteLiquido(Seccion):
    titulo = " 2.1 · Límite líquido "

    #: (símbolo, unidad, significado) de cada casilla
    D = {
        "n": ("N°", "", "N° de golpes del ensayo (copa de Casagrande)."),
        "recip": ("Wc", "g", "Wc = peso del recipiente (tara), en gramos."),
        "hum": ("W1", "g", "W1 = peso del recipiente + suelo húmedo, en gramos."),
        "seco": ("W2", "g", "W2 = peso del recipiente + suelo seco, en gramos."),
        "w": ("w", "%", "w = humedad calculada de cada ensayo = (W1 − W2) / (W2 − Wc) × 100."),
        "LL": ("LL", "%", "LL = límite líquido: humedad del suelo en su límite de consistencia líquido."),
    }

    def __init__(self, master):
        super().__init__(master)

        self.v_np = tk.BooleanVar(value=False)
        self.registrar(self.v_np)
        self.v_ll = tk.StringVar()
        self.rows_v = []
        self.v_w = [tk.StringVar() for _ in range(3)]

        cb = tk.Checkbutton(self, text="Suelo no plástico (NP)",
                            variable=self.v_np, command=self._toggle_np,
                            bg=CARD, fg=TXT, activebackground=CARD,
                            font=(FAM_SERIF, 9), selectcolor="#ffffff",
                            highlightthickness=0, cursor="hand2")
        cb.grid(row=0, column=0, sticky="w", pady=(0, 4))
        ToolTip(cb, "Suelo sin límites de consistencia: no presenta "
                    "plasticidad y se reporta como NP (no plástico).")

        self._build_cuerpo()
        self._bind_navegacion()

        self.aviso_lbl = ttk.Label(self, text="", foreground="#a0432e",
                                   font=(FAM_SERIF, 9, "bold"))
        self.aviso_lbl.grid(row=2, column=0, sticky="e", padx=2, pady=(6, 0))
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._aplicar_np()

    def _validaciones(self):
        """Comandos de validación de teclado para las casillas de ingreso."""
        if not hasattr(self, "_val_dec"):
            root = self.winfo_toplevel()
            self._val_ent = validar_tecla(root, "entero")
            self._val_dec = validar_tecla(root, "decimal")

    # ---------------- ingreso (izquierda) + humedades (derecha) ----------------
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        cuerpo.grid(row=1, column=0, sticky="ew")
        self._inputs = [[None] * 4 for _ in range(3)]

        ing = tk.Frame(cuerpo, bg=CARD)
        ing.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self._build_ingreso(ing)

        res = tk.Frame(cuerpo, bg=CARD)
        res.pack(side="left", fill="y")
        self._build_resultados(res)

    def _build_ingreso(self, ing):
        self._validaciones()
        keys = ("n", "recip", "hum", "seco")
        for c, clave in enumerate(keys, 1):
            simbolo, unidad, sig = self.D[clave]
            cel = tk.Frame(ing, bg=CARD)
            cel.grid(row=0, column=c, sticky="w", pady=(0, 2))
            tk.Label(cel, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                     bg=CARD).pack(side="left")
            ayuda(cel, sig).pack(side="left", padx=(10, 0))
            ing.columnconfigure(c, weight=1)
        self.rows_v = []
        for i in range(3):
            tk.Label(ing, text="#%d" % (i + 1), fg=MUT, bg=CARD,
                     font=(FAM_SERIF, 8)).grid(row=i + 1, column=0, sticky="e",
                                               padx=(0, 4))
            vars_ = [tk.StringVar() for _ in range(4)]
            self.rows_v.append(vars_)
            for c, clave in enumerate(keys, 1):
                frm, num = self.caja(ing, vars_[c - 1], self.D[clave][1],
                                     ancho=6 if clave == "n" else 8,
                                     tipo="entero" if clave == "n" else "decimal")
                frm.grid(row=i + 1, column=c, sticky="ew", padx=2, pady=3)
                self._inputs[i][c - 1] = num
            self.registrar(*vars_)

    def _build_resultados(self, res):
        simbolo, unidad, sig = self.D["w"]
        cel = tk.Frame(res, bg=CARD)
        cel.grid(row=0, column=0, sticky="w", pady=(0, 2))
        tk.Label(cel, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                 bg=CARD).pack(side="left")
        ayuda(cel, sig).pack(side="left", padx=(10, 0))
        res.columnconfigure(0, weight=1)
        for i in range(3):
            frm, num = self.caja(res, self.v_w[i], "%", editable=False)
            frm.grid(row=i + 1, column=0, sticky="ew", padx=2, pady=3)

        sep = tk.Frame(res, bg=SUP, height=1)
        sep.grid(row=4, column=0, sticky="ew", pady=(8, 4))
        llcel = tk.Frame(res, bg=CARD)
        llcel.grid(row=5, column=0, sticky="ew")
        simbolo, unidad, sig = self.D["LL"]
        cab = tk.Frame(llcel, bg=CARD)
        cab.pack(fill="x")
        tk.Label(cab, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                 bg=CARD).pack(side="left")
        ayuda(cab, sig).pack(side="left", padx=(10, 0))
        frm, num = self.caja(llcel, self.v_ll, "%", editable=False)
        frm.pack(fill="x", pady=(2, 0))

    # ---------------- muestra sin plasticidad ----------------
    def _toggle_np(self):
        self._aplicar_np()

    def _aplicar_np(self):
        """Con el check activo se deshabilitan las casillas de ingreso."""
        estado = "disabled" if self.v_np.get() else "normal"
        for r in range(3):
            for c in range(4):
                self._inputs[r][c].config(state=estado)

    def sin_plasticidad(self):
        return self.v_np.get()

    # ---------------- casillas y teclado ----------------
    def caja(self, parent, var, unidad="", editable=True, principal=False,
             ancho=8, tipo="decimal"):
        """Caja de valor: fondo blanco, valor centrado, unidad a la derecha.
        Las cajas de ingreso solo aceptan números (validación de teclado)."""
        bg = "#ffffff"
        borde = ACC if principal else SUP
        frm = tk.Frame(parent, bg=bg, highlightbackground=borde, highlightthickness=1)
        fuente = (FAM_SERIF, 12 if principal else 10, "bold" if principal else "normal")
        valcmd = (self._val_ent if tipo == "entero" else self._val_dec, "%P")
        num = tk.Entry(frm, textvariable=var, bd=0, relief="flat",
                       highlightthickness=0, bg=bg, fg=TXT, insertbackground=TXT,
                       justify="center", font=fuente, width=ancho,
                       state="normal" if editable else "readonly",
                       validate="key" if editable else "none",
                       validatecommand=valcmd if editable else None)
        num.pack(side="left", fill="x", expand=True, ipady=3, padx=(5, 2))
        if unidad:
            tk.Label(frm, text=unidad, bg=bg, fg=MUT,
                     font=(FAM_SERIF, 8)).pack(side="right", padx=(0, 5))
        if editable:
            num.bind("<FocusIn>", lambda ev, f=frm: f.config(
                highlightbackground=ACC, highlightthickness=1))
            num.bind("<FocusOut>", lambda ev, f=frm: (
                f.config(highlightbackground=borde, highlightthickness=1),
                self._formatear_entrada(num, var, tipo)))
            num.bind("<Button-1>", lambda ev, n=num: n.config(
                insertwidth=2, insertbackground=TXT))
        return frm, num

    def _formatear_entrada(self, num, var, tipo="decimal"):
        """Al salir de la casilla se formatea (una/dos cifras), sin revalidar."""
        v = fnum(var.get())
        if v is not None:
            var.set("%.0f" % v if tipo == "entero" else "%.1f" % v)

    def _bind_navegacion(self):
        """↑/↓ entre ensayos, ←/→ entre columnas (solo celdas de ingreso);
        Enter = siguiente celda."""
        for r in range(3):
            for c in range(4):
                num = self._inputs[r][c]
                num.bind("<Left>", lambda ev, r=r, c=c: self._nav(r, c, 0, -1))
                num.bind("<Right>", lambda ev, r=r, c=c: self._nav(r, c, 0, +1))
                num.bind("<Up>", lambda ev, r=r, c=c: self._nav(r, c, -1, 0))
                num.bind("<Down>", lambda ev, r=r, c=c: self._nav(r, c, +1, 0))
                num.bind("<Return>", lambda ev, r=r, c=c: self._return(r, c))

    def _nav(self, r, c, dr, dc):
        """Mueve el foco dentro de la cuadrícula de ingreso (3×4)."""
        r2 = max(0, min(r + dr, 2))
        c2 = max(0, min(c + dc, 3))
        num = self._inputs[r2][c2]
        num.focus_set()
        self._seleccionar(num)

    def _return(self, r, c):
        """Enter: avanza fila por fila (con vuelta al inicio)."""
        if c < 3:
            nr, nc = r, c + 1
        elif r < 2:
            nr, nc = r + 1, 0
        else:
            nr, nc = 0, 0
        num = self._inputs[nr][nc]
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
        keys = ("n", "recip", "hum", "seco")
        out = []
        for vars_ in self.rows_v:
            out.append({keys[k]: fnum(vars_[k].get()) for k in range(4)})
        return out

    def calcular(self):  # requisito de la base
        return calcular_ll(self.leer())

    def mostrar(self, res):
        if self.v_np.get():
            for v in self.v_w:
                v.set("—")
            self.v_ll.set("NP")
            self.aviso_lbl.config(text="")
            self._aviso_tip.set_text("")
            return
        for i in range(3):
            w = res["ll_w"][i]
            self.v_w[i].set("—" if w is None else "%.1f" % w)
        v = res["LL"]
        self.v_ll.set("—" if v is None else "%.1f" % v)
        corto, detalle = aviso_incoherencia(self.leer())
        self.aviso_lbl.config(text=corto)
        self._aviso_tip.set_text(detalle)

    def cargar(self, ejemplo):
        self.v_np.set(False)
        self._aplicar_np()
        for i, row in enumerate(ejemplo["ll"]):
            vals = [row["n"], row["recip"], row["hum"], row["seco"]]
            for c in range(4):
                self.rows_v[i][c].set("" if vals[c] is None else str(vals[c]))

    def limpiar(self):
        self.v_np.set(False)
        self._aplicar_np()
        for vars_ in self.rows_v:
            for v in vars_:
                v.set("")
        for v in self.v_w:
            v.set("—")
        self.v_ll.set("—")
        self.aviso_lbl.config(text="")
        self._aviso_tip.set_text("")