# -*- coding: utf-8 -*-
"""
SECCIÓN 2 · Límites de consistencia (INV E-125 / E-126).

Integra el límite líquido (Sección 2.1: 3 ensayos de la copa de Casagrande)
y el límite plástico (Sección 2.2: 2 ensayos) en una sola tarjeta. Al final,
LL, LP e IP se muestran en la misma fila. Un check permite declarar la
muestra sin plasticidad (NP): deshabilita el ingreso y reporta NP.
"""
import tkinter as tk

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, ToolTip,
                      FAM_UI, validar_tecla, ayuda_seccion)
from motor.calculo import fnum
from secciones.limite_liquido import aviso_incoherencia as aviso_ll
from secciones.limite_plastico import aviso_incoherencia as aviso_lp


class Limites(Seccion):
    titulo = " 2 · Límites de consistencia "

    Sig = {
        "id": "Número de identificación del recipiente (tara) de cada ensayo, p. ej. A-1.",
        "n": "N° de golpes del ensayo (copa de Casagrande).",
        "recip": "Wc = peso del recipiente (tara), en gramos.",
        "hum": "W1 = peso del recipiente + suelo húmedo, en gramos.",
        "seco": "W2 = peso del recipiente + suelo seco, en gramos.",
        "w": "w = humedad calculada de cada ensayo = (W1 − W2) / (W2 − Wc) × 100.",
        "LL": "LL = límite líquido: humedad del suelo en su límite de consistencia líquido (interpolación a 25 golpes).",
        "LP": "LP = límite plástico: promedio de las humedades w de los ensayos.",
        "IP": "IP = índice de plasticidad = LL − LP.",
    }

    #: texto completo del '?' de la sección (todas las variables a la vez)
    SIG_FULL = "\n".join(
        "· %s: %s" % (k.upper() if len(k) <= 2 else k, v)
        for k, v in Sig.items())

    def __init__(self, master):
        super().__init__(master)
        self._val_ent = validar_tecla(self.winfo_toplevel(), "entero")
        self._val_dec = validar_tecla(self.winfo_toplevel(), "decimal")

        self.v_np = tk.BooleanVar(value=False)
        self.registrar(self.v_np)
        self.v_ll = tk.StringVar()
        self.v_lp = tk.StringVar()
        self.v_ip = tk.StringVar()
        self.v_ll.set("—")
        self.v_lp.set("—")
        self.v_ip.set("—")

        self.ll_v = [[tk.StringVar() for _ in range(5)] for _ in range(3)]
        self.ll_w = [tk.StringVar() for _ in range(3)]
        self.lp_v = [[tk.StringVar() for _ in range(4)] for _ in range(2)]
        self.lp_w = [tk.StringVar() for _ in range(2)]
        for v in self.ll_w + self.lp_w:
            v.set("—")
        for i in range(3):
            self.registrar(*self.ll_v[i])
        for i in range(2):
            self.registrar(*self.lp_v[i])

        cb = tk.Checkbutton(self, text="Suelo no plástico (NP)",
                            variable=self.v_np, command=self._toggle_np,
                            bg=CARD, fg=TXT, activebackground=CARD,
                            font=(FAM_UI, 9), selectcolor="#ffffff",
                            highlightthickness=0, cursor="hand2")
        cb.grid(row=0, column=0, sticky="w", pady=(0, 4))
        ToolTip(cb, "Suelo sin límites de consistencia: no presenta "
                    "plasticidad y se reporta como NP (no plástico).")

        self._build_cuerpo()
        self._bind_navegacion()
        self.v_np.trace_add("write", lambda *_: self._aplicar_np())

        self.aviso_lbl = tk.Label(self, text="", foreground="#a0432e",
                                  bg=CARD, font=(FAM_UI, 9, "bold"))
        self.aviso_lbl.grid(row=3, column=0, sticky="e", padx=2, pady=(6, 0))
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._aplicar_np()
        self._ayuda = ayuda_seccion(self, self.SIG_FULL)

    # ---------------- cuerpo: 2.1 líquido (arriba) + 2.2 plástico (abajo) ----
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        cuerpo.grid(row=1, column=0, sticky="ew")

        for texto in ("Límite líquido", "Límite plástico"):
            tk.Label(cuerpo, text=texto, bg=CARD, fg=ACC,
                     font=(FAM_UI, 9, "bold")).pack(anchor="w",
                                                       pady=(0, 2))
            if texto == "Límite líquido":
                ll = tk.Frame(cuerpo, bg=CARD)
                ll.pack(fill="x")
                self._tabla_ll(ll)
            else:
                lp = tk.Frame(cuerpo, bg=CARD)
                lp.pack(fill="x")
                self._tabla_lp(lp)
            sep = tk.Frame(cuerpo, bg=SUP, height=1)
            sep.pack(fill="x", pady=(6, 8))

        self._build_resultados()

    def _tabla_ll(self, parent):
        keys = ("id", "n", "recip", "hum", "seco")
        self._inputs = []
        for c, clave in enumerate(keys):
            texto = "N° recip" if clave == "id" else self._sigla(clave)
            self._col_cabecera(parent, c, texto, self.Sig[clave], negra=True,
                               unidad=None if clave in ("n", "id")
                               else self._unidad(clave))
            parent.columnconfigure(c, weight=1)
        self._col_cabecera(parent, 5, "w", self.Sig["w"], negra=True,
                           unidad="%")
        for i in range(3):
            fila = []
            for c, clave in enumerate(keys):
                if clave == "id":
                    frm, num = self.caja(parent, self.ll_v[i][c], "",
                                         ancho=6, tipo="texto")
                elif clave == "n":
                    frm, num = self.caja(parent, self.ll_v[i][c], "",
                                         ancho=6, tipo="entero")
                else:
                    frm, num = self.caja(parent, self.ll_v[i][c],
                                         self._unidad(clave), ancho=7)
                frm.grid(row=i + 1, column=c, sticky="ew", padx=2, pady=2)
                fila.append(num)
            frm, num = self.caja(parent, self.ll_w[i], "%", editable=False)
            frm.grid(row=i + 1, column=5, sticky="ew", padx=2, pady=2)
            self._inputs.append(fila)

    def _tabla_lp(self, parent):
        keys = ("id", "recip", "hum", "seco")
        self._inputs = []
        for c, clave in enumerate(keys):
            texto = "N° recip" if clave == "id" else self._sigla(clave)
            self._col_cabecera(parent, c, texto, self.Sig[clave], negra=True,
                               unidad=None if clave == "id"
                               else self._unidad(clave))
            parent.columnconfigure(c, weight=1)
        self._col_cabecera(parent, 4, "w", self.Sig["w"], negra=True,
                           unidad="%")
        for i in range(2):
            fila = []
            for c, clave in enumerate(keys):
                if clave == "id":
                    frm, num = self.caja(parent, self.lp_v[i][c], "",
                                         ancho=6, tipo="texto")
                else:
                    frm, num = self.caja(parent, self.lp_v[i][c],
                                         self._unidad(clave))
                frm.grid(row=i + 1, column=c, sticky="ew", padx=2, pady=2)
                fila.append(num)
            frm, num = self.caja(parent, self.lp_w[i], "%", editable=False)
            frm.grid(row=i + 1, column=4, sticky="ew", padx=2, pady=2)
            self._inputs.append(fila)

    def _sigla(self, clave):
        return {"n": "N°", "recip": "Wc", "hum": "W1", "seco": "W2"}[clave]

    def _unidad(self, clave):
        return "" if clave == "n" else "g"

    def _col_cabecera(self, parent, c, texto, sig, negra=False, unidad=None):
        cel = tk.Frame(parent, bg=CARD)
        cel.grid(row=0, column=c, sticky="ew", pady=(0, 2))
        lbl = tk.Frame(cel, bg=CARD)
        lbl.pack()
        tk.Label(lbl, text=texto, font=(FAM_UI, 10),
                 fg=TXT if negra else MUT, bg=CARD).pack(side="left")
        if unidad:
            tk.Label(lbl, text=" (%s)" % unidad, font=(FAM_UI, 10),
                     fg=MUT, bg=CARD).pack(side="left")

    # ---------------- fila final: LL | LP | IP en la misma fila -------------
    def _build_resultados(self):
        fila = tk.Frame(self, bg=CARD)
        fila.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._celda_res(fila, self.v_ll, "LL", self.Sig["LL"], "%")
        self._celda_res(fila, self.v_lp, "LP", self.Sig["LP"], "%")
        self._celda_res(fila, self.v_ip, "IP", self.Sig["IP"], "%")

    def _celda_res(self, parent, var, simbolo, sig, unidad):
        fr = tk.Frame(parent, bg=CARD)
        fr.pack(side="left", padx=(0, 16))
        tk.Label(fr, text=simbolo, font=(FAM_UI, 10), fg=TXT,
                 bg=CARD).pack(side="left")
        tk.Label(fr, text=" (%s)" % unidad, font=(FAM_UI, 10), fg=MUT,
                 bg=CARD).pack(side="left")
        frm, num = self.caja(fr, var, "", editable=False)
        frm.pack(side="left", pady=(2, 0))

    # ---------------- muestra sin plasticidad ----------------
    def _toggle_np(self):
        self._aplicar_np()

    def _aplicar_np(self):
        estado = "disabled" if self.v_np.get() else "normal"
        for fila in self._inputs:
            for num in fila:
                num.config(state=estado)

    def sin_plasticidad(self):
        return self.v_np.get()

    # ---------------- casillas y teclado ----------------
    def caja(self, parent, var, unidad="", editable=True, ancho=7,
             tipo="decimal"):
        """Caja de valor: fondo blanco, valor centrado; la unidad va en la
        etiqueta de la variable (como en las cajas de resultado de la
        granulometría). Las cajas de ingreso solo aceptan números
        (validación); tipo="texto" admite cualquier identificación
        (N° recipiente)."""
        bg = "#ffffff"
        frm = tk.Frame(parent, bg=bg, highlightbackground=SUP, highlightthickness=1)
        usar_val = editable and tipo != "texto"
        valcmd = (self._val_ent if tipo == "entero" else self._val_dec, "%P")
        num = tk.Entry(frm, textvariable=var, bd=0, relief="flat",
                       highlightthickness=0, bg=bg, fg=TXT, insertbackground=TXT,
                       disabledbackground=bg, readonlybackground=bg,
                       justify="center", font=(FAM_UI, 10), width=ancho,
                       state="normal" if editable else "readonly",
                       validate="key" if usar_val else "none",
                       validatecommand=valcmd if usar_val else None)
        num.pack(side="left", fill="x", expand=True, ipady=2, padx=(5, 2))
        if editable:
            num.bind("<FocusIn>", lambda ev, f=frm, n=num: (
                f.config(highlightbackground=ACC, highlightthickness=1),
                self._seleccionar(n)))
            num.bind("<FocusOut>", lambda ev, f=frm: (
                f.config(highlightbackground=SUP, highlightthickness=1),
                self._formatear_entrada(num, var, tipo)))
            num.bind("<Button-1>", lambda ev, n=num: self._seleccionar(n))
        return frm, num

    def _formatear_entrada(self, num, var, tipo="decimal"):
        if tipo == "texto":
            return
        v = fnum(var.get())
        if v is not None:
            var.set("%.2f" % v)

    def _bind_navegacion(self):
        """Celda de ingreso unificada: filas 0-2 del líquido (4 columnas) y
        3-4 del plástico (3 columnas). Enter avanza fila a fila con vuelta."""
        for r, fila in enumerate(self._inputs):
            for c, num in enumerate(fila):
                num.bind("<Left>", lambda ev, r=r, c=c: self._nav(r, c, 0, -1))
                num.bind("<Right>", lambda ev, r=r, c=c: self._nav(r, c, 0, +1))
                num.bind("<Up>", lambda ev, r=r, c=c: self._nav(r, c, -1, 0))
                num.bind("<Down>", lambda ev, r=r, c=c: self._nav(r, c, +1, 0))
                num.bind("<Return>", lambda ev, r=r, c=c: self._return(r, c))

    def _ncols(self, r):
        return 5 if r < 3 else 4

    def _nav(self, r, c, dr, dc):
        nr = max(0, min(r + dr, 4))
        nc = max(0, min(c + dc, self._ncols(nr) - 1))
        num = self._inputs[nr][nc]
        num.focus_set()
        self._seleccionar(num)

    def _return(self, r, c):
        if c + 1 < self._ncols(r):
            nr, nc = r, c + 1
        elif r < 4:
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
        ll = []
        for i in range(3):
            ll.append({"id": self.ll_v[i][0].get().strip(),
                       "n": fnum(self.ll_v[i][1].get()),
                       "recip": fnum(self.ll_v[i][2].get()),
                       "hum": fnum(self.ll_v[i][3].get()),
                       "seco": fnum(self.ll_v[i][4].get())})
        lp = []
        for i in range(2):
            lp.append({"id": self.lp_v[i][0].get().strip(),
                       "recip": fnum(self.lp_v[i][1].get()),
                       "hum": fnum(self.lp_v[i][2].get()),
                       "seco": fnum(self.lp_v[i][3].get())})
        return {"ll": ll, "lp": lp}

    def mostrar(self, res):
        np_ = bool(res.get("ll_np"))
        for i in range(3):
            w = None if np_ else res["ll_w"][i]
            self.ll_w[i].set("—" if w is None else "%.2f" % w)
        for i in range(2):
            w = None if np_ else res["lp_w"][i]
            self.lp_w[i].set("—" if w is None else "%.2f" % w)
        for var, key in ((self.v_ll, "LL"), (self.v_lp, "LP"), (self.v_ip, "IP")):
            if np_:
                var.set("NP")
            else:
                v = res.get(key)
                var.set("—" if v is None else "%.2f" % v)
        if np_:
            self.aviso_lbl.config(text="")
            self._aviso_tip.set_text("")
            return
        data = self.leer()
        corto, detalle = aviso_ll(data["ll"])
        if not corto:
            corto, detalle = aviso_lp(data["lp"])
        self.aviso_lbl.config(text=corto)
        self._aviso_tip.set_text(detalle)

    def cargar(self, ejemplo):
        np_ = bool(ejemplo.get("ll_np", False))
        self.v_np.set(np_)
        for i in range(3):
            for c in range(5):
                self.ll_v[i][c].set("")
        for i in range(2):
            for c in range(4):
                self.lp_v[i][c].set("")
        if not np_:
            for i, row in enumerate(ejemplo["ll"]):
                self.ll_v[i][0].set(row.get("id") or "")
                vals = [row["n"], row["recip"], row["hum"], row["seco"]]
                for c in range(4):
                    self.ll_v[i][c + 1].set("" if vals[c] is None
                                            else str(vals[c]))
            for i, row in enumerate(ejemplo["lp"]):
                self.lp_v[i][0].set(row.get("id") or "")
                vals = [row["recip"], row["hum"], row["seco"]]
                for c in range(3):
                    self.lp_v[i][c + 1].set("" if vals[c] is None
                                            else str(vals[c]))
        self._aplicar_np()

    def limpiar(self):
        self.v_np.set(False)
        for i in range(3):
            for c in range(5):
                self.ll_v[i][c].set("")
        for i in range(2):
            for c in range(4):
                self.lp_v[i][c].set("")
        for v in self.ll_w + self.lp_w:
            v.set("—")
        self.v_ll.set("—")
        self.v_lp.set("—")
        self.v_ip.set("—")
        self.aviso_lbl.config(text="")
        self._aviso_tip.set_text("")
        self._aplicar_np()