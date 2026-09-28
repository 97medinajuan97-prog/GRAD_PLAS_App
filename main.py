# -*- coding: utf-8 -*-
"""Punto de entrada de la Calculadora GRAD-PLAS."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app import App  # noqa: E402


def main():
    App().mainloop()


if __name__ == "__main__":
    main()