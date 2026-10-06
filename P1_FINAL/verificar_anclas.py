#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que TODAS las anclas de mutacion existen antes de mutar nada.

Un patron inexistente daria NOT_APPLICABLE y pareceria un resultado valido.
Esto lo delata antes de tocar produccion.

Uso:  python P1_FINAL/verificar_anclas.py
"""
import io
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))

import mutaciones as M  # noqa: E402

# LEE EN BYTES, igual que hace el harness. Leer en modo texto traduce CRLF a LF
# y daria un FALSO POSITIVO: el ancla pareceria existir y en realidad no.
FUENTES = {M.SVC: open(M.SVC, "rb").read().decode("utf-8"),
           M.ADA: open(M.ADA, "rb").read().decode("utf-8"),
           M.SER: open(M.SER, "rb").read().decode("utf-8")}


def main():
    print("Anclas de mutacion: %d" % len(M.MUTACIONES))
    faltan = 0
    for mut in M.MUTACIONES:
        mid, capa, ruta, buscar = mut[0], mut[1], mut[2], mut[3]
        suite, nota = mut[5], mut[6]
        ok = buscar in FUENTES[ruta]
        if not ok:
            faltan += 1
        print("  %-4s %-24s %-32s %s" % (mid, capa, suite,
                                         "OK" if ok else "*** NO EXISTE ***"))
    print("\nanclas inexistentes: %d" % faltan)
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())