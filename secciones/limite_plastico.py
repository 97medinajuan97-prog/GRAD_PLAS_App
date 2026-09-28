# -*- coding: utf-8 -*-
"""
SECCIÓN 2.2 · Límite plástico (INV E-126).

Promedio de las humedades w de los ensayos. El IP (= LL − LP) lo calcula el
motor usando el LL de la Sección 2.1, pero la sección sigue siendo
independiente. Misma presentación visual que la Sección 2.1 (dos columnas:
ingreso a la izquierda, resultados a la derecha con el LL/debajo), y admite
que la muestra sea "no plástica" deshabilitando el ingreso desde la app.
"""
import tkinter as tk
from tkinter import ttk

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, ayuda, ToolTip,
                      FAM_SERIF, validar_tecla)
from motor.calculo import fnum, _w


def calcular_lp(rows, LL=None):
    """rows: [{recip, hum, seco}, ...]. Devuelve w% por ensayo, LP e IP."""
    ws = []
    ok = []
    for row in rows:
        w = _w(row["recip"], row["hum"], row["seco"])
        ws.append(w)
        if w is not None:
            ok.append(w)
    LP = (sum(ok) / len(ok)) if ok else None
    IP = (LL - LP) if (LL is not None and LP is not None) else None
    return {"w": ws, "LP": LP, "IP": IP}


def aviso_incoherencia(rows):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    keys = ("recip", "hum", "seco")
    llenas = [r for r in rows if all(r[k] is not None for k in keys)]
    tiene = any(r[k] is not None for r in rows for k in keys)
    if not tiene:
        return "", ""
    if not llenas:
        return "⚠ Datos incompletos", "Complete Wc, W1 y W2 de cada ensayo."
    for i, r in enumerate(llenas, 1):
        if any(r[k] <= 0 for k in keys):
            return "⚠ Datos incoherentes", "Ensayo #%d: los valores deben ser mayores que cero." % i
        if r["hum"] <= r["seco"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W1 debe ser mayor que W2." % i
        if r["seco"] <= r["recip"]:
            return "⚠ Datos incoherentes", "Ensayo #%d: W2 debe ser mayor que Wc." % i
    return "", ""


class LimitePlastico(Seccion):
    titulo = " 2.2 · Límite plástico "

    #: (símbolo, unidad, significado) de cada casilla
    D = {
        "recip": ("Wc", "g", "Wc = peso del recipiente (tara), en gramos."),
        "hum": ("W1", "g", "W1 = peso del recipiente + suelo húmedo, en gramos."),
        "seco": ("W2", "g", "W2 = peso del recipiente + suelo seco, en gramos."),
        "w": ("w", "%", "w = humedad calculada de cada ensayo = (W1 − W2) / (W2 − Wc) × 100."),
        "LP": ("LP", "%", "LP = límite plástico: promedio de las humedades w de los ensayos."),
        "IP": ("IP", "%", "IP = índice de plasticidad = LL − LP."),
    }

    def __init__(self, master):
        super().__init__(master)
        self._val_dec = validar_tecla(self.winfo_toplevel(), "decimal")
        self.v_lp = tk.StringVar()
        self.v_ip = tk.StringVar()
        self.rows_v = []
        self.v_w = [tk.StringVar() for _ in range(2)]
        self._entradas = []

        self._build_cuerpo()
        self._bind_navegacion()

        self.aviso_lbl = ttk.Label(self, text="", foreground="#a0432e",
                                   font=(FAM_SERIF, 9, "bold"))
        self.aviso_lbl.grid(row=2, column=0, sticky="e", padx=2, pady=(6, 0))
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._np = False

    # ---------------- ingreso (izquierda) + humedades (derecha) ----------------
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        cuerpo.grid(row=1, column=0, sticky="ew")
        self._inputs = [[None] * 3 for _ in range(2)]

        ing = tk.Frame(cuerpo, bg=CARD)
        ing.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self._build_ingreso(ing)

        res = tk.Frame(cuerpo, bg=CARD)
        res.pack(side="left", fill="y")
        self._build_resultados(res)

    def _build_ingreso(self, ing):
        keys = ("recip", "hum", "seco")
        for c, clave in enumerate(keys, 1):
            simbolo, unidad, sig = self.D[clave]
            cel = tk.Frame(ing, bg=CARD)
            cel.grid(row=0, column=c, sticky="w", pady=(0, 2))
            tk.Label(cel, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                     bg=CARD).pack(side="left")
            ayuda(cel, sig).pack(side="left", padx=(10, 0))
            ing.columnconfigure(c, weight=1)
        self.rows_v = []
        for i in range(2):
            tk.Label(ing, text="#%d" % (i + 1), fg=MUT, bg=CARD,
                     font=(FAM_SERIF, 8)).grid(row=i + 1, column=0, sticky="e",
                                               padx=(0, 4))
            vars_ = [tk.StringVar() for _ in range(3)]
            self.rows_v.append(vars_)
            for c, clave in enumerate(keys, 1):
                frm, num = self.caja(ing, vars_[c - 1], self.D[clave][1])
                frm.grid(row=i + 1, column=c, sticky="ew", padx=2, pady=3)
                self._inputs[i][c - 1] = num
                self._entradas.append(num)
            self.registrar(*vars_)

    def _build_resultados(self, res):
        simbolo, unidad, sig = self.D["w"]
        cel = tk.Frame(res, bg=CARD)
        cel.grid(row=0, column=0, sticky="w", pady=(0, 2))
        tk.Label(cel, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                 bg=CARD).pack(side="left")
        ayuda(cel, sig).pack(side="left", padx=(10, 0))
        res.columnconfigure(0, weight=1)
        for i in range(2):
            frm, num = self.caja(res, self.v_w[i], "%", editable=False)
            frm.grid(row=i + 1, column=0, sticky="ew", padx=2, pady=3)

        sep = tk.Frame(res, bg=SUP, height=1)
        sep.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        for r, clave in ((4, "LP"), (5, "IP")):
            cel = tk.Frame(res, bg=CARD)
            cel.grid(row=r, column=0, sticky="ew", pady=(0, 2))
            simbolo, unidad, sig = self.D[clave]
            cab = tk.Frame(cel, bg=CARD)
            cab.pack(fill="x")
            tk.Label(cab, text=simbolo, font=(FAM_SERIF, 10), fg=TXT,
                     bg=CARD).pack(side="left")
            ayuda(cab, sig).pack(side="left", padx=(10, 0))
            var = self.v_lp if clave == "LP" else self.v_ip
            frm, num = self.caja(cel, var, "%", editable=False)
            frm.pack(fill="x", pady=(2, 0))

    # ---------------- casillas y teclado ----------------
    def caja(self, parent, var, unidad="", editable=True, ancho=8):
        """Caja de valor: fondo blanco, valor centrado, unidad a la derecha.
        Las cajas de ingreso solo aceptan números (validación de teclado)."""
        bg = "#ffffff"
        borde = SUP
        frm = tk.Frame(parent, bg=bg, highlightbackground=borde, highlightthickness=1)
        num = tk.Entry(frm, textvariable=var, bd=0, relief="flat",
                       highlightthickness=0, bg=bg, fg=TXT, insertbackground=TXT,
                       justify="center", font=(FAM_SERIF, 10), width=ancho,
                       state="normal" if editable else "readonly",
                       validate="key" if editable else "none",
                       validatecommand=(self._val_dec, "%P") if editable else None)
        num.pack(side="left", fill="x", expand=True, ipady=3, padx=(5, 2))
        if unidad:
            tk.Label(frm, text=unidad, bg=bg, fg=MUT,
                     font=(FAM_SERIF, 8)).pack(side="right", padx=(0, 5))
        if editable:
            num.bind("<FocusIn>", lambda ev, f=frm: f.config(
                highlightbackground=ACC, highlightthickness=1))
            num.bind("<FocusOut>", lambda ev, f=frm: (
                f.config(highlightbackground=borde, highlightthickness=1),
                self._formatear_entrada(num, var)))
            num.bind("<Button-1>", lambda ev, n=num: n.config(
                insertwidth=2, insertbackground=TXT))
        return frm, num

    def _formatear_entrada(self, num, var):
        """Al salir de la casilla, el valor queda con 1 decimal."""
        v = fnum(var.get())
        if v is not None:
            var.set("%.1f" % v)

    def _bind_navegacion(self):
        """↑/↓ entre ensayos, ←/→ entre columnas (solo celdas de ingreso);
        Enter = siguiente celda."""
        for r in range(2):
            for c in range(3):
                num = self._inputs[r][c]
                num.bind("<Left>", lambda ev, r=r, c=c: self._nav(r, c, 0, -1))
                num.bind("<Right>", lambda ev, r=r, c=c: self._nav(r, c, 0, +1))
                num.bind("<Up>", lambda ev, r=r, c=c: self._nav(r, c, -1, 0))
                num.bind("<Down>", lambda ev, r=r, c=c: self._nav(r, c, +1, 0))
                num.bind("<Return>", lambda ev, r=r, c=c: self._return(r, c))

    def _nav(self, r, c, dr, dc):
        """Mueve el foco dentro de la cuadrícula de ingreso (2×3)."""
        r2 = max(0, min(r + dr, 1))
        c2 = max(0, min(c + dc, 2))
        num = self._inputs[r2][c2]
        num.focus_set()
        self._seleccionar(num)

    def _return(self, r, c):
        """Enter: avanza fila por fila (con vuelta al inicio)."""
        if c < 2:
            nr, nc = r, c + 1
        elif r < 1:
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

    # ---------------- muestra no plástica ----------------
    def anular_np(self, activo):
        """Con muestra no plástica se deshabilita el ingreso de datos."""
        self._np = bool(activo)
        for e in self._entradas:
            if activo:
                e.config(state="disabled")
            else:
                e.config(state="normal")

    # ----------------------------------------------------------------
    def leer(self):
        keys = ("recip", "hum", "seco")
        out = []
        for vars_ in self.rows_v:
            out.append({keys[k]: fnum(vars_[k].get()) for k in range(3)})
        return out

    def calcular(self):  # requisito de la base
        return calcular_lp(self.leer())

    def mostrar(self, res):
        if res.get("ll_np"):
            for v in self.v_w:
                v.set("—")
            self.v_lp.set("NP")
            self.v_ip.set("NP")
            self.aviso_lbl.config(text="")
            self._aviso_tip.set_text("")
            return
        for i in range(2):
            w = res["lp_w"][i]
            self.v_w[i].set("—" if w is None else "%.1f" % w)
        v = res["LP"]
        self.v_lp.set("—" if v is None else "%.1f" % v)
        v = res["IP"]
        self.v_ip.set("—" if v is None else "%.1f" % v)
        corto, detalle = aviso_incoherencia(self.leer())
        self.aviso_lbl.config(text=corto)
        self._aviso_tip.set_text(detalle)

    def cargar(self, ejemplo):
        for i, row in enumerate(ejemplo["lp"]):
            vals = [row["recip"], row["hum"], row["seco"]]
            for c in range(3):
                self.rows_v[i][c].set("" if vals[c] is None else str(vals[c]))

    def limpiar(self):
        for vars_ in self.rows_v:
            for v in vars_:
                v.set("")
        for v in self.v_w:
            v.set("—")
        self.v_lp.set("—")
        self.v_ip.set("—")
        self.aviso_lbl.config(text="")
        self._aviso_tip.set_text("")