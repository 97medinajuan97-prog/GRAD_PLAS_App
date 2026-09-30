# -*- coding: utf-8 -*-
"""
Tema visual y widgets compartidos de la app.

Cada seccion de ingreso/calculo hereda de `Seccion`, una tarjeta
independiente con su propio modelo de datos y formula.

`VERSION` identifica esta copia de la aplicación. No es la versión del
formato de laboratorio, que se imprime en el encabezado del PDF
(«CÓDIGO F-LAB-001 · VERSIÓN 1.0») y no depende de este número.
"""
import re
import tkinter as tk
from tkinter import ttk

VERSION = "2.0.0"

BG    = "#f3f4f6"
CARD  = "#ffffff"
ACC   = "#40464f"
ACC_D = "#333940"
SUP   = "#d7dade"
TXT   = "#20242a"
MUT   = "#6e7781"

#: Fondo del panel donde se ve el reporte. Más oscuro que BG a propósito: la
#: hoja es blanca y necesita un marco visible para no perderse en la ventana.
FONDO_VISOR = "#565d66"

# Fuente de la app. Antes se llamaba `FAM_UI`, nombre engañoso: Segoe UI
# es una sans serif; el nombre correcta es FAM_UI.
FAM_UI = "Segoe UI"


def validar_tecla(root, tipo="decimal"):
    """Registra una validación de teclado en `root`.

    Devuelve el comando Tcl para usar en `validatecommand` (con %P): solo se
    permiten caracteres que lleven a un formato numérico válido:
    decimal → 12.5, 12, ".5", "" ; entero → 12, "".
    """
    def _dec(P):
        if P == "":
            return True
        if P in (".", ","):
            return True
        return re.fullmatch(r"\d*[,.]\d*|\d+", P) is not None

    def _ent(P):
        return P == "" or P.isdigit()

    cmd = _ent if tipo == "entero" else _dec
    return root.register(cmd)


#: Pasos de deshacer que recuerda cada casilla de ingreso.
MAX_DESHACER = 100


def con_deshacer(w):
    """Habilita Ctrl+Z (deshacer) y Ctrl+Y / Ctrl+Mayús+Z (rehacer) en una
    casilla de entrada.

    Tk solo ofrece historial para `Text`, no para `Entry`, así que se lleva
    una pila de instantáneas a mano.

    Los pasos se AGRUPAN por entrada, no por tecla: escribir "600" es un solo
    paso y un Ctrl+Z lo borra entero. Se sigue escribiendo mientras el valor
    nuevo sea el anterior seguido de caracteres más; cualquier otra edición
    (borrar, corregir en medio, pegar) cierra el paso y abre uno nuevo.
    """
    pila = []            # valores a los que se puede volver
    redo = []            # valores a los que se puede rehacer
    grupo = [None]       # valor previo al paso de escritura en curso
    actual = [None]

    def _leer():
        try:
            return w.get()
        except tk.TclError:
            return ""

    def _escribir(txt):
        try:
            w.delete(0, "end")
            w.insert(0, txt)
        except tk.TclError:
            pass
        actual[0] = txt

    def _sigue_escribiendo(a, b):
        return len(b) > len(a) and b.startswith(a)

    def _push(*_):
        v = _leer()
        if actual[0] is None:
            actual[0] = v          # primera medición, no es un cambio
            return
        prev = actual[0]
        if v == prev:
            return
        if grupo[0] is None:
            grupo[0] = prev        # empieza un paso de escritura
        elif not _sigue_escribiendo(prev, v):
            pila.append(grupo[0])  # se cerró el paso: se archiva su origen
            del pila[:-MAX_DESHACER]
            grupo[0] = prev
            del redo[:]            # lo que se iba a rehacer ya no vale
        actual[0] = v

    def _deshacer(*_):
        destino = None
        if grupo[0] is not None and grupo[0] != actual[0]:
            destino = grupo[0]     # el paso de escritura que está en curso
        elif pila:
            destino = pila.pop()
        if destino is None:
            return "break"
        redo.append(actual[0])
        grupo[0] = None
        _escribir(destino)
        return "break"

    def _rehacer(*_):
        if not redo:
            return "break"
        grupo[0] = None
        _escribir(redo.pop())
        return "break"

    actual[0] = _leer()
    w.bind("<KeyRelease>", _push, add="+")
    for seq in ("<Control-z>", "<Control-Z>", "<Control-KeyPress-z>"):
        w.bind(seq, _deshacer, add="+")
    for seq in ("<Control-y>", "<Control-Y>",
                "<Control-Shift-Z>", "<Control-Shift-z>"):
        w.bind(seq, _rehacer, add="+")
    return w


def _entradas(w):
    """Recorre el árbol de widgets y devuelve todas las casillas de entrada."""
    for c in w.winfo_children():
        if isinstance(c, (tk.Entry, ttk.Entry)):
            yield c
        for x in _entradas(c):
            yield x


def habilitar_deshacer(root):
    """Activa Ctrl+Z / Ctrl+Y en todas las casillas de ingreso de la ventana.

    Se hace un solo recorrido del árbol en lugar de tocar cada fábrica de
    entradas, para que ningún campo nuevo quede sin deshacer por olvido. Es
    idempotente: una casilla que ya tiene el enlace no se vuelve a tocar.
    """
    n = 0
    for w in _entradas(root):
        if not w.bind("<Control-z>"):
            con_deshacer(w)
            n += 1
    return n


def aplicar_estilo(root):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    s.configure(".", font=("Segoe UI", 10))
    s.configure("TFrame", background=BG)
    s.configure("TLabel", background=BG, foreground=TXT)
    # Fondo del visualizador del reporte: un gris claramente más oscuro que
    # el de la app, para que la hoja blanca se despegue como en un lector de
    # PDF y no se mezcle con el resto de la ventana.
    s.configure("Visor.TFrame", background=FONDO_VISOR)
    s.configure("Visor.TLabel", background=FONDO_VISOR, foreground="#d8dce2")
    s.configure("Card.TLabelframe", background=CARD, bordercolor=SUP,
                relief="solid", borderwidth=1, padding=6)
    s.configure("Card.TLabelframe.Label", background=CARD, foreground=ACC,
                font=("Segoe UI", 10, "bold"))
    s.configure("TEntry", fieldbackground="#ffffff", bordercolor=SUP,
                insertcolor=TXT, padding=4,
                font=(FAM_UI, 10))
    s.map("TEntry", bordercolor=[("focus", ACC)])
    s.configure("Accent.TButton", background=ACC, foreground="#ffffff",
                padding=[14, 8], font=("Segoe UI", 10, "bold"), bordercolor=ACC)
    s.map("Accent.TButton", background=[("active", ACC_D), ("pressed", ACC_D)],
          foreground=[("active", "#ffffff")])
    s.configure("Ghost.TButton", background="#e5e9f4", foreground=TXT,
                padding=[10, 3], font=("Segoe UI", 10), bordercolor="#d8deeb")
    s.map("Ghost.TButton", background=[("active", "#d6dded")])
    s.configure("Ejemplo.TCombobox", fieldbackground="#ffffff",
                background="#ffffff", foreground=TXT, arrowcolor=ACC,
                bordercolor=SUP, lightcolor=BG, darkcolor=BG, relief="flat",
                padding=[6, 5], insertcolor=TXT, selectbackground="#ffffff",
                selectforeground=TXT, font=(FAM_UI, 10))
    s.map("Ejemplo.TCombobox",
          fieldbackground=[("readonly", "#ffffff"), ("focus", "#ffffff")],
          foreground=[("readonly", TXT)],
          bordercolor=[("focus", ACC)],
          lightcolor=[("focus", BG)], darkcolor=[("focus", BG)])
    root.option_add("*TCombobox*Listbox.background", "#ffffff")
    root.option_add("*TCombobox*Listbox.foreground", TXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#dfe6f2")
    root.option_add("*TCombobox*Listbox.selectForeground", TXT)
    root.option_add("*TCombobox*Listbox.font", (FAM_UI, 10))
    s.configure("Key.TLabel", background=CARD, foreground=MUT,
                font=(FAM_UI, 9))
    s.configure("Val.TLabel", background=CARD, foreground=TXT,
                font=(FAM_UI, 10))
    s.configure("Res.TLabel", background=CARD, foreground=TXT,
                font=(FAM_UI, 12, "bold"))
    s.configure("Nota.TLabel", background=CARD, foreground=MUT,
                font=(FAM_UI, 8))
    s.configure("Res.TEntry", fieldbackground="#ffffff", bordercolor=ACC,
                borderwidth=1, padding=5, insertcolor=TXT,
                font=(FAM_UI, 12, "bold"))
    s.map("Res.TEntry", bordercolor=[("focus", ACC_D)])


class _ThumbScroll(tk.Canvas):
    """Deslizador fino y moderno: asa redondeada que se resalta al pasar el mouse.

    Se oculta solo cuando el contenido cabe en la vista."""
    ANCHO = 14

    def __init__(self, master, command):
        super().__init__(master, width=self.ANCHO, bg=BG, highlightthickness=0,
                         bd=0, cursor="hand2")
        self._cmd = command
        self._first = 0.0
        self._last = 1.0
        self._dragging = False
        self._arrastre = 0.0
        self._hover = False
        self.bind("<Configure>", self._dibujar)
        self.bind("<Button-1>", self._clic)
        self.bind("<B1-Motion>", self._mover)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Enter>", lambda e: (setattr(self, "_hover", True), self._dibujar()))
        self.bind("<Leave>", lambda e: (setattr(self, "_hover", False), self._dibujar()))

    def set(self, first, last):
        self._first = float(first)
        self._last = float(last)
        self._dibujar()

    def _rango(self):
        h = self.winfo_height()
        if h < 24:
            return None
        total = self._last - self._first
        if total <= 0.0001 or total >= 1.0:
            return None
        y0 = self._first * h
        y1 = self._last * h
        if y1 - y0 < 32:
            y1 = y0 + 32
            if y1 > h - 2:
                y0 = max(2, h - 34)
                y1 = h - 2
        return max(2, y0), min(h - 2, y1)

    def _dibujar(self, *_):
        self.delete("all")
        r = self._rango()
        if r is None:
            return
        y0, y1 = r
        color = "#374151" if self._hover else "#6b7280"
        cx = self.ANCHO // 2
        self.create_line(cx, 0, cx, self.winfo_height(), fill="#dde1e6", width=4)
        self.create_line(cx, y0 + 5, cx, y1 - 5, fill=color, width=8,
                         capstyle="round")

    def _clic(self, e):
        r = self._rango()
        if r is None:
            return
        y0, y1 = r
        if e.y < y0:
            self._cmd("scroll", -1, "pages")
        elif e.y > y1:
            self._cmd("scroll", 1, "pages")
        else:
            self._dragging = True
            self._arrastre = e.y - y0

    def _mover(self, e):
        if not self._dragging:
            return
        h = self.winfo_height()
        if h <= 0:
            return
        frac = (e.y - self._arrastre) / h
        self._cmd("moveto", max(0.0, min(1.0, frac)))

    def _soltar(self, _):
        self._dragging = False
        self._dibujar()


class ScrollableFrame(ttk.Frame):
    """Marca de contenido con scroll vertical (deslizador fino).

    Con `horizontal=True` añade además barra horizontal y deja de forzar el
    ancho del contenido, que es lo que permite ampliar un documento y
    recorrerlo de lado a lado. Es lo que necesita el visualizador del
    reporte: al ampliar, la hoja es más ancha que el panel.
    """

    def __init__(self, master, horizontal=False, bg=None, **kw):
        super().__init__(master, **kw)
        self._horizontal = horizontal
        self._bg = bg or BG
        self._canvas = tk.Canvas(self, bg=self._bg, highlightthickness=0,
                                 bd=0)
        self._vsb = _ThumbScroll(self, self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._vsb.pack(side="right", fill="y")
        self._hsb = None
        if horizontal:
            self._hsb = ttk.Scrollbar(self, orient="horizontal",
                                      command=self._canvas.xview)
            self._hsb.pack(side="bottom", fill="x")
            self._canvas.configure(xscrollcommand=self._hsb.set)
        self._inner = ttk.Frame(self._canvas, style="Visor.TFrame")
        self._win = self._canvas.create_window((0, 0), window=self._inner,
                                               anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        if horizontal:
            # con barra horizontal el contenido conserva su ancho propio
            self._inner.bind("<Configure>",
                             lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
            self._canvas.bind("<Configure>", self._ajustar_h)
        else:
            self._canvas.bind("<Configure>",
                              lambda e: self._canvas.itemconfigure(self._win, width=e.width))
        self._canvas.bind("<Enter>", lambda e: self._canvas.bind_all("<MouseWheel>", self._onwheel))
        self._canvas.bind("<Leave>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

    def _ajustar_h(self, e):
        """Al ampliar, la barra horizontal sigue al ancho del contenido."""
        self._canvas.itemconfigure(self._win, width=e.width)
        if self._hsb is not None:
            self._hsb.set(0, 1)
        self._canvas.xview_moveto(0.0)

    def _onwheel(self, e):
        self._canvas.yview_scroll(int(-e.delta / 120), "units")

    def inner(self):
        return self._inner

    def canvas_width(self):
        w = self._canvas.winfo_width()
        return w if w and w > 20 else 560

    def canvas_height(self):
        h = self._canvas.winfo_height()
        return h if h and h > 20 else 700

    def bind_resize(self, cb):
        self._canvas.bind("<Configure>", lambda e: cb())


class ToolTip:
    """Tooltip flotante simple (globos de ayuda)."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", lambda _: self.mostrar())
        widget.bind("<Leave>", lambda _: self.ocultar())

    def mostrar(self):
        self.ocultar()
        w = tk.Toplevel(self.widget)
        w.wm_overrideredirect(True)
        w.wm_attributes("-topmost", True)
        w.geometry("+%d+%d" % (self.widget.winfo_pointerx() + 14,
                               self.widget.winfo_pointery() + 12))
        tk.Label(w, text=self.text, justify="left", bg="#2b3138", fg="#f5f6f7",
                 font=(FAM_UI, 10), padx=8, pady=5, wraplength=260).pack()
        self.tip = w
        w.bind("<Button-1>", lambda _: self.ocultar())

    def ocultar(self):
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None

    def set_text(self, text):
        self.text = text


def ayuda(parent, texto):
    """Símbolo de ayuda discreto: '?' en gris claro."""
    lbl = tk.Label(parent, text="?", font=(FAM_UI, 10),
                   fg="#a9b1b9", bg=CARD, cursor="question_arrow")
    ToolTip(lbl, texto)
    return lbl


def ayuda_seccion(card, texto):
    """Un único símbolo de ayuda por tarjeta, en la fila del título, a la derecha."""
    lbl = tk.Label(card, text="?", font=(FAM_UI, 11, "bold"),
                   fg="#8a929c", bg=CARD, cursor="question_arrow")
    ToolTip(lbl, texto)
    lbl.place(relx=1.0, x=-6, y=-26, anchor="ne")
    return lbl


class SelectDropdown(ttk.Frame):
    """Selector abatible con la misma apariencia de la app y el deslizador fino.

    Sustituye al ttk.Combobox: entrada de solo lectura con flecha, y una
    lista desplegable con el _ThumbScroll de la app como slider."""

    def __init__(self, master, values, inicial=None, ancho=9):
        super().__init__(master, style="TFrame")
        self._values = list(values)
        self._pop = None
        self._funcid = None
        self.var = tk.StringVar(value=inicial if inicial is not None
                                else (values[0] if values else ""))

        frm = tk.Frame(self, bg="#ffffff", highlightbackground=SUP,
                       highlightthickness=1)
        frm.pack(fill="both", expand=True)
        e = tk.Entry(frm, textvariable=self.var, bd=0, relief="flat",
                     highlightthickness=0, bg="#ffffff", fg=TXT,
                     readonlybackground="#ffffff", disabledforeground=TXT,
                     insertbackground=TXT, font=(FAM_UI, 10), width=ancho,
                     state="readonly")
        e.pack(side="left", fill="x", expand=True, ipady=4, padx=(6, 0))
        self.entry = e
        flecha = tk.Label(frm, text="▾", bg="#ffffff", fg=ACC,
                          font=(FAM_UI, 8), cursor="hand2")
        flecha.pack(side="right", padx=(0, 6))
        self._flecha = flecha
        for wdg in (frm, e, flecha):
            wdg.bind("<Button-1>", lambda ev: self._toggle())

    # ---------------- api similar a un Combobox ----------------
    def get(self):
        return self.var.get()

    def set(self, valor):
        self.var.set(valor)

    @property
    def values(self):
        return self._values

    # ---------------- popup con listbox + deslizador fino ----------------
    def _toggle(self):
        if self._pop is not None:
            self._cerrar()
        else:
            self._abrir()

    def _abrir(self):
        top = tk.Toplevel(self.winfo_toplevel())
        top.wm_overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=SUP)
        cont = tk.Frame(top, bg="#ffffff", bd=0, highlightthickness=1,
                        highlightbackground=SUP)
        cont.pack(fill="both", expand=True)

        lb = tk.Listbox(cont, bd=0, relief="flat", bg="#ffffff", fg=TXT,
                        font=(FAM_UI, 10), highlightthickness=0,
                        selectbackground="#dfe6f2", selectforeground=TXT,
                        activestyle="none", exportselection=False,
                        width=max(9, max((len(v) for v in self._values),
                                         default=9) + 2))
        for v in self._values:
            lb.insert("end", v)
        lb.pack(side="left", fill="both", expand=True)
        thumb = _ThumbScroll(cont, lb.yview)
        thumb.pack(side="right", fill="y")
        lb.configure(yscrollcommand=thumb.set)
        lb.configure(height=max(2, min(len(self._values), 8)))

        try:
            sel = max(0, self._values.index(self.var.get()))
        except ValueError:
            sel = 0
        lb.selection_set(sel)
        lb.activate(sel)
        lb.see(sel)

        def cerrar():
            self._pop = None
            self._unbind_fuera()
            try:
                top.destroy()
            except tk.TclError:
                pass

        def elegir(_ev=None):
            cur = lb.curselection()
            if cur:
                self.var.set(lb.get(cur[0]))
            cerrar()

        self._pop = top
        lb.bind("<Double-1>", elegir)
        lb.bind("<ButtonRelease-1>", elegir)
        lb.bind("<Return>", elegir)
        lb.bind("<Escape>", lambda ev: cerrar())
        top.bind("<Escape>", lambda ev: cerrar())

        root = self.winfo_toplevel()
        self._funcid = root.bind("<Button-1>", self._click_fuera, add="+")

        top.update_idletasks()
        pw = max(top.winfo_reqwidth(), self.winfo_width())
        ph = top.winfo_reqheight()
        x = self.winfo_rootx()
        arriba = self.winfo_rooty() - ph - 2
        y = arriba if arriba >= 0 else self.winfo_rooty() + self.winfo_height() + 2
        top.geometry("%dx%d+%d+%d" % (pw, ph, x, y))
        lb.focus_set()

    def _click_fuera(self, _e=None):
        if self._pop is not None:
            self._cerrar()
        return None

    def _cerrar(self):
        if self._pop is not None:
            try:
                self._pop.destroy()
            except tk.TclError:
                pass
            self._pop = None
        self._unbind_fuera()

    def _unbind_fuera(self):
        if self._funcid is not None:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._funcid)
            except tk.TclError:
                pass
            self._funcid = None


class Seccion(ttk.LabelFrame):
    """Tarjeta independiente de ingreso + calculo.

    Una seccion: crea su UI, registra sus variables de texto, lee sus datos,
    calcula su ensayo, muestra resultados y puede cargar/limpiar. No conoce a
    las demas secciones (las dependencias se resuelven desde `app`).
    """

    titulo = ""
    ancho_entrada = 9

    def __init__(self, master):
        super().__init__(master, text=self.titulo, style="Card.TLabelframe",
                         padding=9, labelanchor="n")
        self._vars = []

    # -- hook para entradas: registrar variables y rotulos de salida ----
    def registrar(self, *var):
        for v in var:
            self._vars.append(v)

    # -- interfaz comun ----
    def bind_cambio(self, cb):
        for v in self._vars:
            v.trace_add("write", cb)

    def limpiar(self):
        for v in self._vars:
            v.set("")

    def mostrar_aviso(self, corto, detalle=""):
        """Muestra el aviso de la sección, o lo saca de la rejilla si no hay
        nada que decir.

        Un `Label` con texto vacío sigue reservando su línea, y esa franja
        quedaba como aire bajo la última fila de ingreso en las secciones con
        aviso, al contrario que en la de información de la muestra.
        """
        if not hasattr(self, "aviso_lbl"):
            return
        self.aviso_lbl.config(text=corto or "")
        tip = getattr(self, "_aviso_tip", None)
        if tip is not None:
            tip.set_text(detalle or "")
        if corto:
            self.aviso_lbl.grid()
        else:
            self.aviso_lbl.grid_remove()

    def cargar(self, ejemplo):
        raise NotImplementedError

    def leer(self):
        raise NotImplementedError

    def mostrar(self, res):
        """Pinta resultados en vivo dentro de la tarjeta."""
        raise NotImplementedError
