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

from ui_theme import (Seccion, TXT, MUT, CARD, ACC, SUP, AMBAR,
                      NEGRO, ToolTip, FAM_UI, validar_tecla, ayuda_seccion)
from motor.calculo import fnum

#: Diámetros nominales, en mm, de cada tamiz. Se guardan aparte para poder armar
#: listas por alcance sin repetir el texto de cada uno, y para renombrar (el
#: 1/2" de la base general es el 0.5" de la especificación de subbases).
_D = {'3"': 76.2, '2 1/2"': 63.5, '2"': 50.8, '1 1/2"': 38.1, '1"': 25.4,
      '3/4"': 19.05, '1/2"': 12.7, '3/8"': 9.525, 'N° 4': 4.75,
      'N° 10': 2.0, 'N° 40': 0.425, 'N° 200': 0.075, 'FONDO': 0.0}


def _serie(nombres):
    return [(n, _D[n]) for n in nombres]


#: Serie base, para suelos (INV E-123). El 1/2" (12.70 mm) está porque en la
#: curva de densidad es el salto de la grava gruesa a la arena gruesa y sin él
#: esa zona queda sin apoyo en la interpolación.
SIEVES_SUELOS = _serie([
    '3"', '2 1/2"', '2"', '1 1/2"', '1"', '3/4"', '1/2"', '3/8"',
    'N° 4', 'N° 10', 'N° 40', 'N° 200', 'FONDO',
])

#: Series de control de calidad. En todas se conservan los tamices más gruesos
#: que ya tiene la serie base y que caen por encima del primero de la
#: especificación, porque el material control los retiene y se necesitan para
#: que la curva no empiece a mitad. A partir de ahí va la lista de cada
#: familia.
#:
#:   Afirmados  desde 1 1/2":  1 1/2", 1", 3/4", 3/8", N°4, N°10, N°40, N°200
#:   Bases      desde 1 1/2":  1 1/2", 1", 3/4", 3/8", N°4, N°10, N°40, N°200
#:   Subbases   desde 2":      2", 1 1/2", 1", 1/2", 3/8", N°4, N°10, N°40, N°200
#:
#: Fíjate que affirmed y bases coinciden en tamices: la graduación es lo que las
#: distingue (A-38 contra BG-38), no la serie.
SIEVES_AFIRMADOS = _serie([
    '3"', '2 1/2"', '2"',
    '1 1/2"', '1"', '3/4"', '3/8"',
    'N° 4', 'N° 10', 'N° 40', 'N° 200', 'FONDO',
])
SIEVES_BASES = SIEVES_AFIRMADOS
SIEVES_SUBBASES = _serie([
    '3"', '2 1/2"',
    '2"', '1 1/2"', '1"', '1/2"', '3/8"',
    'N° 4', 'N° 10', 'N° 40', 'N° 200', 'FONDO',
])

#: Alcance de control de calidad -> serie de tamices. Los alcances que no
#: aparecen aquí (estructuras y drenajes, pavimentos asfálticos) no tienen
#: graduación ni serie propia: se usa la base, que es la del tamizado de suelo.
SERIES_CC = {
    "Afirmados": SIEVES_AFIRMADOS,
    "Bases": SIEVES_BASES,
    "Subbases": SIEVES_SUBBASES,
}

#: Serie por defecto: la de suelos. Es la que se usa cuando no se indica otro,
#: y la que lee un archivo de muestra sin alcance.
SIEVES = SIEVES_SUELOS
#: cantidad de tamices con peso retenido de la serie base. El FONDO va
#: aparte: se calcula restando el total menos la suma, no se escribe.
N_TAMICES = len(SIEVES) - 1


def serie_para(tipo=None, alcance=None):
    """Serie de tamices según el tipo de muestra y su alcance.

    Suelos y los alcances sin serie propia usan la base. Un archivo viejo, sin
    estas claves, también: no se fuerza a una serie de control de calidad a la
    que no se pertenece.
    """
    if (tipo or "").strip().lower() == "suelos":
        return SIEVES_SUELOS
    return SERIES_CC.get((alcance or "").strip(), SIEVES_SUELOS)


def n_tamices_de(serie):
    """Cuántos tamices con peso se digitan en una serie (sin el FONDO)."""
    return len(serie) - 1


def nombres_de(serie):
    """Nombres de tamiz de una serie, venga como [(nombre, mm)] o como [nombre]."""
    return [(s[0] if isinstance(s, (tuple, list)) else s) for s in serie]


#: posición del 1/2" dentro de la serie base. La necesitan quienes leen un
#: archivo de muestra de la versión anterior, que no tenía ese tamiz: el hueco
#: va aquí, no al final, o los pesos siguientes se corren una fila y el 3/8"
#: aparecería como si fuera el 1/2", falseando media curva.
POS_1_2 = next(i for i, (t, _) in enumerate(SIEVES) if t == '1/2"')


def indices_de(serie):
    """Índices de los tamices que definen fracciones y grupos, por nombre.

    Se buscan por nombre y no por número de posición. Con posición fija, al
    agregar el 1/2" %pasa N°4 quedó leyendo el 3/8" y %pasa N°200 el N°40, y
    con ellos la grava, la arena, los finos, el tipo de suelo y las
    clasificaciones SUCs y AASHTO. Con series de distinta longitud, el error
    sería aún más fácil de cometer.

    Los cuatro tamices que definen fracción y grupo están en todas las series:
    si alguna vez faltara en una, se avisa al importar en vez de leer otra fila.
    """
    faltan = [t for t in ("N° 4", "N° 10", "N° 40", "N° 200")
              if not any(n == t for n, _ in serie)]
    if faltan:
        raise ValueError("La serie de tamices no tiene %s, que definen la "
                         "grava, la arena, los finos y la clasificación."
                         % ", ".join(faltan))
    idx = [next(i for i, (n, _) in enumerate(serie) if n == t)
           for t in ("N° 4", "N° 10", "N° 40", "N° 200")]
    return {"n4": idx[0], "n10": idx[1], "n40": idx[2], "n200": idx[3]}


_I_BASE = indices_de(SIEVES)


def calcular_granulometria(d, serie=None):
    """d: {'total': texto|None, 'pesos': pesos retenidos}.

    `serie` es la lista de tamices que aplica (ver `serie_para`). Sin ella se
    usa la de suelos, que es la base general.

    Los pesos se normalizan al número de tamices de la serie: si vienen cortos,
    como cuando se carga un archivo .json de otra versión, se rellena con None
    en vez de acortar la curva, porque si no el fondo quedaría corrido una fila
    y los % saldrían mal. El fondo se calcula restando la suma del total; no se
    escribe.
    """
    serie = serie or SIEVES_SUELOS
    n = n_tamices_de(serie)
    idx = indices_de(serie)
    diam = [d0 for _, d0 in serie]
    total = fnum(d.get("total"))
    pesos = list(d["pesos"])[:n]
    pesos += [None] * (n - len(pesos))
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
            "tamiz": serie[i][0], "diam": diam[i], "w": w,
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
                d1, d2 = diam[k], diam[k + 1]
                if d2 <= 0:
                    return None
                return math.pow(10, math.log10(d1) + (math.log10(d2) - math.log10(d1)) * (P - a) / (b - a))
        return None

    d60, d30, d10 = interp(60), interp(30), interp(10)
    cu = (d60 / d10) if (d60 is not None and d10 is not None and d10 > 0) else None
    cc = (d30 ** 2 / (d60 * d10)
          if (d60 and d30 is not None and d10 is not None and d60 * d10 > 0) else None)

    # Por nombre, no por posición: ver `indices_de`.
    F4, F200 = F[idx["n4"]], F[idx["n200"]]
    grava = (100 - F4) if F4 is not None else None
    arena = (F4 - F200) if (F4 is not None and F200 is not None) else None
    tipo = ("GRANULAR" if F200 <= 35 else "FINO") if F200 is not None else None

    return {
        "fondo": fondo, "sum_ret": sumw, "sieve": sieve, "F": F,
        "d60": d60, "d30": d30, "d10": d10, "cu": cu, "cc": cc,
        "grava": grava, "arena": arena, "finos": F200, "tipo": tipo,
        "f4": F4, "f10": F[idx["n10"]], "f40": F[idx["n40"]], "f200": F200,
    }


def aviso_incoherencia(pesos, total):
    """Advertencia corta + detalle: datos incompletos o incoherentes."""
    no = [p for p in pesos if p is not None]
    if not no:
        return "", ""
    if any(p < 0 for p in no):
        return "⚠ Datos incoherentes", "Los pesos retenidos no pueden ser negativos."
    # Un tamiz en blanco NO es por sí solo un error. En INV E-123 el tamizado
    # arranca donde el material lo exige: una arcilla no se monta desde 3",
    # se lavan los finos y solo se pesan N°4, N°10, N°40 y N°200. Los
    # tamices en blanco por encima del primero pesado son lo normal.
    # Lo sospechoso es un hueco ENTRE dos tamices ya pesados: ahí sí faltó
    # anotar algo.
    idx = [i for i, p in enumerate(pesos) if p is not None]
    huecos = [i for i in range(idx[0], idx[-1] + 1) if pesos[i] is None]
    if huecos:
        nombres = ", ".join(SIEVES[i][0] for i in huecos)
        return "⚠ Datos incompletos", ("Falta el peso retenido de %s: hay un "
                                       "hueco entre tamices ya pesados." % nombres)
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
        #: True cuando el usuario ha escrito un W1 propio. Mientras no lo haga,
        #: la casilla se llena sola con el peso del suelo de la humedad natural.
        #: En cuanto escribe, su valor manda sobre el de la humedad: corregir la
        #: humedad despues ya no cambia esta casilla, porque el total de la
        #: granulometria es suyo. Borrarlo devuelve el control a la humedad.
        self._w1_propio = False
        #: True mientras el cursor este en la casilla W1, para que
        #: `mostrar` no la reescriba mientras se escribe.
        self._w1_enfocado = False
        #: Serie de tamices vigente. Arranca con la de suelos y la cambia la
        #: app según el tipo de muestra y su alcance (`set_serie`).
        self._serie = list(SIEVES_SUELOS)
        self._n = n_tamices_de(self._serie)
        #: Un variable por tamiz y tres de resultados, con la serie más ancha
        #: (suelos, 12 tamices). Las series de control de calidad tienen menos,
        #: y las que sobran quedan en "" para no perder lo ya escrito al
        #: cambiar de alcance y volver.
        self.peso_vars = [tk.StringVar() for _ in range(N_TAMICES)]
        self.registrar(*self.peso_vars)
        self.v_res = [[tk.StringVar() for _ in range(3)]
                      for _ in range(len(SIEVES_SUELOS))]

        self._build_pesos()
        self._build_cuerpo()
        self._bind_navegacion()

        # Chip de aviso: ambar de la paleta con texto negro encima
        # (10.1:1). Antes era un rojo oscuro sobre blanco; el ambar se ve
        # desde lejos y avisa sin gritar.
        self.aviso_lbl = tk.Label(self, text="", foreground=NEGRO,
                                  bg=AMBAR, font=(FAM_UI, 9, "bold"),
                                  padx=6, pady=1)
        self.aviso_lbl.grid(row=2, column=0, sticky="e", padx=2, pady=(6, 0))
        # sin texto no se muestra: el chip vacio era un cuadro ambar suelto
        self.aviso_lbl.grid_remove()
        self._aviso_tip = ToolTip(self.aviso_lbl, "")

        self.columnconfigure(0, weight=1)
        self._ayuda = ayuda_seccion(self, self.SIG_FULL)

    # ---------------- pesos: antes y después de lavado (W1 / W2) ----------------
    def _build_pesos(self):
        fila = tk.Frame(self, bg=CARD)
        fila.grid(row=0, column=0, sticky="w", pady=(0, 10))
        tk.Label(fila, text="W1",
                 font=(FAM_UI, 10), fg=TXT, bg=CARD).pack(side="left")
        tk.Label(fila, text=" (g)",
                 font=(FAM_UI, 10), fg=MUT, bg=CARD).pack(side="left")
        frm, num = self.caja(fila, self.v_w1, editable=True)
        frm.pack(side="left", padx=(10, 0))
        num.bind("<KeyRelease>", self._al_tocar_w1, add="+")
        num.bind("<FocusOut>", self._al_salir_w1, add="+")
        num.bind("<FocusIn>", self._entrar_w1, add="+")
        #: Marca de "este valor lo escribio el usuario". Sin ella, un W1 que no
        #: cuadra con los pesos parece un error de la aplicacion, cuando es un
        #: valor introducido a proposito.
        self._lbl_w1 = tk.Label(fila, text="", font=(FAM_UI, 9), fg=ACC,
                                bg=CARD)
        self._lbl_w1.pack(side="left", padx=(5, 0))
        ToolTip(num, "Peso del suelo que se tamiza.\n\nViene con el peso del "
                     "suelo de la humedad natural. Se puede cambiar si el "
                     "material tamizado no es esa misma porción.\n\nBorralo "
                     "para volver al valor de la humedad.")
        tk.Label(fila, text="W2",
                 font=(FAM_UI, 10), fg=TXT, bg=CARD).pack(side="left",
                                                             padx=(22, 0))
        tk.Label(fila, text=" (g)",
                 font=(FAM_UI, 10), fg=MUT, bg=CARD).pack(side="left")
        frm2, num2 = self.caja(fila, self.v_w2l, editable=False)
        frm2.pack(side="left", padx=(10, 0))

    # ---------------- tabla: ingreso (izquierda) | resultados (derecha) ----
    def _build_cuerpo(self):
        cuerpo = tk.Frame(self, bg=CARD)
        # sin aire extra debajo: el aviso ya aporta su espacio cuando hay
        # algo que avisar, y si no, la sección termina en la última fila
        cuerpo.grid(row=1, column=0, sticky="ew")
        tabla = tk.Frame(cuerpo, bg=CARD)
        tabla.pack(side="left", fill="both", expand=True)
        self._build_tabla(tabla)

    def _cabecera(self, parent, col, texto, negra=False, unidad=None):
        cel = tk.Frame(parent, bg=CARD)
        cel.grid(row=0, column=col, sticky="ew", pady=(0, 2))
        lbl = tk.Frame(cel, bg=CARD)
        lbl.pack()
        tk.Label(lbl, text=texto, font=(FAM_UI, 10),
                 fg=TXT if negra else MUT, bg=CARD).pack(side="left")
        if unidad:
            tk.Label(lbl, text=" (%s)" % unidad, font=(FAM_UI, 10),
                     fg=MUT, bg=CARD).pack(side="left")

    def _build_tabla(self, tabla):
        for c, (texto, uni) in enumerate((
                ("Tamiz", None), ("Ø", "mm"), ("Peso ret.", "g"),
                ("% Ret.", None), ("% Acum.", None), ("% Pasa", None))):
            self._cabecera(tabla, c, texto, negra=True, unidad=uni)
            tabla.columnconfigure(c, weight=1, uniform="granos")
        #: Entries de peso, en el orden de las filas, para la navegación con
        #: ↑↓ y Enter. Se guardan aparte de `_inputs_visibles` porque el
        #: recorrido es sobre las casillas de la serie vigente.
        self._entradas_peso = []
        #: Piezas de cada fila (etiquetas y cajas), para poderlas mostrar u
        #: ocultar juntas al cambiar de serie.
        self._piezas_fila = {}
        #: Entry de peso de cada fila de la serie base, por posición, para
        #: reconstruir la navegación cuando cambia la serie.
        self._peso_entry = {}
        for i, (tam, d) in enumerate(SIEVES_SUELOS):
            r = i + 1
            lbl = tk.Label(tabla, text=tam, bg=CARD, fg=TXT,
                           font=(FAM_UI, 10))
            lbl.grid(row=r, column=0, sticky="w", padx=2, pady=2)
            lbl_d = tk.Label(tabla, text="%g" % d, bg=CARD, fg=TXT,
                             font=(FAM_UI, 10))
            lbl_d.grid(row=r, column=1, sticky="w", padx=2, pady=2)
            if tam == "FONDO":
                frm, num = self.caja(tabla, self.v_fondo, editable=False)
                self._fondo_num = num
                frm.grid(row=r, column=2, sticky="ew", padx=2, pady=2)
                piezas = [lbl, lbl_d, frm]
            else:
                frm, num = self.caja(tabla, self.peso_vars[i], editable=True)
                self._entradas_peso.append(num)
                self._peso_entry[i] = num
                frm.grid(row=r, column=2, sticky="ew", padx=2, pady=2)
                piezas = [lbl, lbl_d, frm]
            for c in range(3):
                frm_res, _ = self.caja(tabla, self.v_res[i][c],
                                       editable=False, ancho=8)
                frm_res.grid(row=r, column=3 + c, sticky="ew", padx=2, pady=2)
                piezas.append(frm_res)
            self._piezas_fila[i] = piezas
        self._inputs = list(self._entradas_peso[:self._n])

    # ---------------- serie de tamices ----------------
    def set_serie(self, serie):
        """Cambia la serie de tamices de la tabla.

        La serie de una muestra de control de calidad tiene menos tamices: a
        afirmados y a bases les falta el 1/2". Las filas que sobran se ocultan
        con `grid_remove` y no se destruyen, así los valores escritos quedan en
        sus variables y al volver a suelos se recuperan.
        """
        serie = list(serie)
        if serie == self._serie:
            return
        self._serie = serie
        self._n = n_tamices_de(serie)
        # Las filas se muestran por NOMBRE de tamiz, no por posición. Las
        # series no tienen la misma lista: a afirmados y a bases les falta el
        # 1/2", y a subbases el 3/4". Con posición, la fila del 1/2" se
        # corresponde con el 3/8" de la otra serie y se mostraría el tamiz
        # equivocado.
        en_serie = {n for n, _ in serie}
        self._entradas_peso = []
        for i, (nombre, _d) in enumerate(SIEVES_SUELOS):
            piezas = self._piezas_fila[i]
            if nombre in en_serie:
                for p in piezas:
                    p.grid()
                if nombre != "FONDO":
                    self._entradas_peso.append(self._peso_entry[i])
            else:
                for p in piezas:
                    p.grid_remove()
        # La navegación con ↑↓ y Enter recorre solo las filas visibles.
        self._inputs = list(self._entradas_peso[:self._n])
        self._bind_navegacion()
        # Los resultados mostrados eran de la serie anterior: se limpian, y lo
        # mismo el fondo, que se recalcula con la serie nueva.
        for fila in self.v_res:
            for col in fila:
                col.set("")
        self.v_fondo.set("auto")
        self._fondo_num.config(fg=MUT)

    def serie(self):
        """Serie de tamices vigente."""
        return self._serie

    def n_tamices(self):
        """Cuántos tamices con peso se digitan en la serie vigente."""
        return self._n

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
                       justify="center", font=(FAM_UI, 10), width=ancho,
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
        """Pesos de los tamices de la serie vigente.

        Los valores de las filas ocultas (las que no están en la serie de
        control de calidad) no se devuelven: si se leyeran, el peso del tamiz
        que no se tamizó se sumaría al total y el fondo saldría mal. Se
        guardan en sus variables para recuperarlos al volver a soils.
        """
        # POR NOMBRE, no por posición.
        #
        # `peso_vars` está en el orden de la serie base (suelos), que tiene una
        # fila más que las series de control de calidad. Leyéndolo por posición,
        # en afirmados el 1/2" (oculto y vacío) se leía como el 3/8", el 3/8"
        # como el N° 4, y así hasta el final, con el N° 200 sin leer nunca: de
        # ahí el corrido en el reporte, el fondo mal calculado (la masa del
        # N° 200 se iba al fondo) y el aviso de "datos incompletos" por el hueco
        # del 1/2".
        # `SIEVES_SUELOS` incluye el FONDO, que no tiene casilla de peso: se recorre
        # sin la última fila, que es justo donde acaba `peso_vars`.
        valor = {nombre: fnum(self.peso_vars[i].get())
                 for i, (nombre, _d) in enumerate(SIEVES_SUELOS[:-1])}
        pesos = [valor.get(nombre) for nombre, _d in self._serie[:-1]]
        # El W1 solo se manda si el usuario puso uno propio. Si la casilla esta
        # con el valor automatico de la humedad, se manda vacio para que el
        # motor use el de la humedad y no dos veces el mismo numero.
        w1 = fnum(self.v_w1.get()) if self._w1_propio else None
        return {"total": None, "pesos": pesos, "w1": w1,
                "serie": [nombre for nombre, _d in self._serie[:-1]]}

    def mostrar(self, res):
        gt = res.get("g_total")
        # Mientras el cursor esté en la casilla, NO se reescribe: se está
        # escribiendo y cualquier valor puesto por el programa se comería lo
        # que el usuario teclea. Al salir de la casilla se vuelve a rellenar.
        if not self._w1_enfocado:
            self.v_w1.set("—" if gt is None else "%.2f" % gt)
        self._marcar_w1()
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

        corto, detalle = aviso_incoherencia(self.leer()["pesos"], gt)
        if not corto:
            # Se avisa sobre los valores mostrados (los redondeados), que son
            # los que suman 100 % por construcción: el aviso debe describir lo
            # que el usuario ve, no magnitudes intermedias.
            ga, ar, fi = (res.get("g_grava_1d"), res.get("g_arena_1d"),
                          res.get("g_finos_1d"))
            if None not in (ga, ar, fi) and abs(ga + ar + fi - 100.0) > 0.05:
                corto = "⚠ Grava+Arena+Finos ≠ 100 %"
                detalle = ("La suma de %grava ({:.1f}) + %arena ({:.1f}) + "
                           "%finos ({:.1f}) debe dar 100 %.".format(ga, ar, fi))
        self.mostrar_aviso(corto, detalle)

    def cargar(self, ejemplo):
        """Vuelca los pesos de un archivo o un ejemplo en la serie vigente.

        Los pesos SIEMPRE se reencuadran por nombre de tamiz, nunca por
        posición. `peso_vars` está en el orden de la serie base (suelos), que
        tiene una fila más que las series de control de calidad: copiarlas por
        posición dejaba el peso del 3/8" en la casilla del 1/2" (que está
        oculta) y corría todos los siguientes. Al guardar y volver a abrir una
        muestra de bases, los retenidos no volvían a su casilla.

        Un archivo sin la clave `serie` (uno viejo) se interpreta con la serie
        vigente, que es lo correcto: se guardó con los tamices que se están
        viendo en pantalla.
        """
        g = ejemplo["grano"]
        pesos = list(g.get("pesos") or [])
        serie_origen = list(g.get("serie") or [n for n, _ in self._serie])
        self._set_pesos_por_nombre(pesos, serie_origen)
        # Un archivo viejo no trae el campo W1: se devuelve el control a la
        # humedad, que es como se veían las muestras de antes de que la casilla
        # fuera editable.
        w1 = g.get("w1")
        if w1 is not None:
            self._w1_propio = True
            self.v_w1.set("%.2f" % float(w1))
        else:
            self._w1_propio = False
            self.v_w1.set("")
        self._w1_enfocado = False
        self._marcar_w1()

    def w1_propio(self):
        """¿El usuario escribió un W1 propio en vez de usar el de la humedad?"""
        return self._w1_propio

    def _entrar_w1(self, *_):
        """El cursor entró en la casilla W1: a partir de aquí no se reescribe."""
        self._w1_enfocado = True

    def _al_salir_w1(self, *_):
        """El cursor salió: ya no se está escribiendo, se puede refrescar."""
        self._w1_enfocado = False
        self._al_tocar_w1()

    def _al_tocar_w1(self, *_):
        """El usuario escribió en la casilla W1.

        Se escucha en el CONTROL y no en la variable, y a propósito. W1 es una
        salida que se rellena sola con el total, así que si la variable
        estuviera conectada al refresco, cada vez que `mostrar` la rellenara
        se volvería a refrescar, y de ahí otra vez, sin fin. Además no se
        podría distinguir un relleno de una edición. En el control solo llegan
        pulsaciones de teclado: lo escribe la persona o no lo escribe.

        Vaciar la casilla devuelve el control a la humedad en el acto, sin
        esperar a que el cursor salga: es lo que promete la ayuda, y dejar la
        casilla en blanco hasta el siguiente clic se lee como un fallo.
        """
        vacio = not self.v_w1.get().strip()
        self._w1_propio = not vacio
        if vacio:
            self._w1_enfocado = False
        self._marcar_w1()
        self.pedir_refresco()

    def _marcar_w1(self):
        """Muestra o quita la marca de valor propio."""
        self._lbl_w1.config(text="propio" if self._w1_propio else "")

    def peso_var_de(self, nombre):
        """Variable de un tamiz por su nombre.

        `peso_vars` está en el orden de la serie base y las filas en pantalla
        van en el de la serie vigente: son índices distintos. Cualquier código
        que necesite la casilla de un tamiz pasa por aquí en vez de adivinar
        la posición.
        """
        for i, (n, _d) in enumerate(SIEVES_SUELOS):
            if n == nombre and i < len(self.peso_vars):
                return self.peso_vars[i]
        raise KeyError("El tamiz %r no está en la serie base." % nombre)

    def _set_pesos_por_nombre(self, pesos, serie_origen):
        """Reencuadra los pesos a la serie vigente, casillas por nombre.

        Un tamiz que está en una serie y no en la otra no es cero: si no se
        tamizó, el material que se habría retenido en él pasó al tamiz
        siguiente más fino que sí está en la serie. Así que su peso se suma al
        de ese tamiz.

        Por ejemplo, al pasar una curva de suelos (que tiene el 1/2") a la
        serie de afirmados (que no), el retenido del 1/2" va al 3/8", que es el
        siguiente. Si en vez de sumar se descartara, el total de la muestra
        bajaría y el fondo artificially absorbería esa masa.
        """
        valor = {nombre: (pesos[i] if i < len(pesos) else None)
                 for i, nombre in enumerate(nombres_de(serie_origen))}
        # De mayor a menor, para poder correr el peso al tamiz más fino que sí
        # está en la serie vigente.
        en_vigente = {n for n, _ in self._serie}
        for nombre, v in valor.items():
            if v is None or nombre in en_vigente or nombre == "FONDO":
                continue
            # Por diámetro: el orden de los nombres ('1"' antes que '3/4"') no sirve para
            # comparar tamanos, así que se busca el siguiente más fino de la
            # serie vigente.
            destino = self._siguiente_mas_fino(nombre)
            if destino is None:
                continue
            previo = valor.get(destino) or 0.0
            valor[destino] = round(previo + v, 1)
        # Se escribe POR NOMBRE, con `peso_var_de`. Escribir con
        # `peso_vars[i]` usando el índice de la serie vigente ponía el 3/8" en
        # la casilla del 1/2" (que está oculta) y corría todos los
        # siguientes: al guardar y reabrir, los retenidos no volvían a su
        # casilla.
        for nombre, _d in self._serie[:-1]:
            v = valor.get(nombre)
            self.peso_var_de(nombre).set("" if v is None else str(v))

    def _siguiente_mas_fino(self, nombre):
        """Primer tamiz de la serie vigente más fino que `nombre`."""
        diam = dict(self._serie)
        if nombre not in diam:
            return None
        d0 = diam[nombre]
        candidatos = [(d, n) for n, d in self._serie
                      if n != "FONDO" and d < d0]
        return min(candidatos)[1] if candidatos else None

    def limpiar(self):
        super().limpiar()
        # Al limpiar se vuelve al valor de la humedad: un W1 propio era de este
        # ensayo y no tiene sentido arrastrarlo al siguiente.
        self._w1_propio = False
        self.v_w1.set("")
        self._marcar_w1()
        self.v_w2l.set("—")
        self.v_fondo.set("auto")
        self._fondo_num.config(fg=MUT)
        for row in self.v_res:
            for v in row:
                v.set("—")
        self.mostrar_aviso("")
