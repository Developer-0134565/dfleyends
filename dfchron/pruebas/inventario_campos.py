#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: INVENTARIO REAL DE CAMPOS.
============================================

Que hace
--------
Barre las 57.215 lineas de `historical_events.jsonl` y responde una sola
pregunta: ¿que nombres de campo EXISTEN de verdad?

Por que existe
--------------
Una version anterior de este proyecto busco los sujetos en `hf` y `figure`.
Esos campos NO EXISTEN. El real es `hfid`. Con los nombres correctos los tipos
utilizables pasaron de 11 a 78 de 90.

Ese fallo no se impidio con una suposicion mejor: se impidio BARRIENDO. Este
script es la forma de seguir barriendo, y su salida es la que alimenta el
vocabulario congelado de `clasificar_tipos.py`.

Este script NO decide que campo es sujeto ni que campo es tiempo: solo cuenta
nombres. La decision se toma leyendo los VALORES, en la clasificacion.

Uso:  python dfchron/pruebas/inventario_campos.py [--json SALIDA]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dfchron import chronicles_datos as cd   # noqa: E402

RUTA = cd.ruta_de("historical_events")

#: Sufijos que en DF identifican a una figura historica. Se usan para DETECTAR
#: campos de sujeto que el vocabulario anterior no conocia, no para afirmar que
#: lo sean: la confirmacion viene del valor, no del nombre.
SUFIJOS_HF = ("hfid", "hf_id")


def barrer():
    total = corruptas = 0
    campos = collections.Counter()
    por_tipo = collections.defaultdict(collections.Counter)
    for linea in open(RUTA, "r", encoding="utf-8"):
        linea = linea.strip()
        if not linea:
            continue
        total += 1
        try:
            reg = json.loads(linea)
        except ValueError:
            corruptas += 1
            continue
        c = reg.get("campos") or {}
        for k in c:
            campos[k] += 1
            por_tipo[str(cd.valor_de(c, "type", ""))][k] += 1
    return total, corruptas, campos, por_tipo


def main(argv=None):
    p = argparse.ArgumentParser(description="Inventario real de campos")
    p.add_argument("--json", default=None)
    a = p.parse_args(argv)

    total, corruptas, campos, por_tipo = barrer()
    hf = sorted(k for k in campos if k.endswith(SUFIJOS_HF))
    print("=" * 78)
    print("INVENTARIO REAL DE CAMPOS :: historical_events")
    print("=" * 78)
    print("lineas : %d   corruptas : %d" % (total, corruptas))
    print("campos distintos: %d" % len(campos))
    print()
    print("campos cuyo nombre acaba en hfid/hf_id (posibles sujetos):")
    for k in hf:
        print("  %-24s %7d registros" % (k, campos[k]))
    print()
    print("campos mas frecuentes:")
    for k, n in campos.most_common(24):
        print("  %-24s %7d" % (k, n))
    if a.json:
        doc = {"lineas": total, "corruptas": corruptas,
               "campos": dict(campos.most_common()),
               "campos_hfid": {k: campos[k] for k in hf},
               "campos_por_tipo": dict((t, dict(c)) for t, c in por_tipo.items())}
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        print("\n-> %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())