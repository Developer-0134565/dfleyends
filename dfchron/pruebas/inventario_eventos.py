#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: INVENTARIO COMPLETO de eventos.

Barre `merged/historical_events.jsonl` ENTERO (57.215 lineas, sin muestras) y
responde: ¿que tipos existen REALMENTE, cuantos hay, que campos traen, con que
procedencia, y si permiten derivar un evento de Chronicles?

REGLA
-----
Un tipo NO se declara usable por su NOMBRE. Se declara usable solo si sus
CAMPOS lo permiten: identificador del sujeto + tiempo.

Nombres de campo VERIFICADOS sobre el dataset, no supuestos:
    tiempo  -> year, seconds72
    sujeto  -> hfid, hfid_target, target_hfid, slayer_hfid, group_1_hfid,
                group_2_hfid, hist_figure_id, entity_id, site_id, item_id...

El primer intento uso "hf" y "figure", que NO EXISTEN: el campo se llama `hfid`.
Uso:  python dfchron/pruebas/inventario_eventos.py
"""
from __future__ import annotations

import collections
import json
import os
import sys

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dfchron import chronicles_datos as cd  # noqa: E402

RUTA = cd.ruta_de("historical_events")

TEMPORALES = ("year", "seconds72", "seconds", "tick")
IDENTIFICADORES = ("hfid", "hfid_target", "target_hfid", "slayer_hfid",
                   "group_1_hfid", "group_2_hfid", "hist_figure_id",
                   "entity_id", "site_id", "item_id", "structure_id",
                   "position_id", "civ_id", "site_civ_id", "occasion_id",
                   "schedule_id", "link")


def valor(campos, clave, defecto=None):
    v = (campos or {}).get(clave)
    return v.get("valor", defecto) if isinstance(v, dict) else (
        defecto if v is None else v)


def barrer():
    """Barrido TOTAL: cada linea se lee exactamente una vez."""
    total = corruptas = sin_campos = 0
    por_tipo = collections.Counter()
    campos_por_tipo = collections.defaultdict(collections.Counter)
    sin_ident = collections.Counter()
    cert = collections.defaultdict(collections.Counter)
    fuente = collections.defaultdict(collections.Counter)
    ejemplos = {}

    with open(RUTA, "r", encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            total += 1
            try:
                reg = json.loads(linea)
            except ValueError:
                corruptas += 1
                continue
            campos = reg.get("campos") or {}
            if not campos:
                sin_campos += 1
            tipo = str(valor(campos, "type", "(sin type)"))
            por_tipo[tipo] += 1
            cert[tipo][str(reg.get("certainty"))] += 1
            fuente[tipo][str(reg.get("source"))] += 1
            for k in campos:
                campos_por_tipo[tipo][k] += 1
            util = any(str(valor(campos, k, "")) not in ("", "-1", "-1.0")
                       for k in IDENTIFICADORES)
            if not util:
                sin_ident[tipo] += 1
            if tipo not in ejemplos:
                ejemplos[tipo] = {
                    "record_id": reg.get("record_id"),
                    "df_id": reg.get("df_id"),
                    "certainty": reg.get("certainty"),
                    "ejemplo": {k: valor(campos, k)
                                for k in sorted(campos)[:14]}}
    return {"total": total, "corruptas": corruptas, "sin_campos": sin_campos,
            "por_tipo": por_tipo, "campos_por_tipo": campos_por_tipo,
            "sin_ident": sin_ident, "cert": cert, "fuente": fuente,
            "ejemplos": ejemplos}


def evaluar(b):
    filas = []
    for tipo, n in b["por_tipo"].most_common():
        pres = b["campos_por_tipo"][tipo]
        t_tiempo = any(pres.get(c, 0) for c in TEMPORALES)
        n_ident = sum(1 for c in IDENTIFICADORES if pres.get(c, 0))
        if not t_tiempo:
            usable, motivo = "NO", "sin tiempo"
        elif n_ident == 0:
            usable, motivo = "NO", "sin sujeto identificable"
        else:
            usable, motivo = "SI", "tiempo + %d ids" % n_ident
        filas.append({
            "tipo": tipo, "n": n, "usable": usable, "motivo": motivo,
            "sin_identificador": b["sin_ident"][tipo],
            "certainty": dict(b["cert"][tipo].most_common(2)),
            "fuente": dict(b["fuente"][tipo].most_common(2)),
            "campos": [c for c, _ in
                       b["campos_por_tipo"][tipo].most_common(8)],
        })
    return filas


def main():
    b = barrer()
    filas = evaluar(b)
    print("=" * 76)
    print("BARRIDO COMPLETO: %s" % RUTA)
    print("=" * 76)
    print("lineas leidas   : %d" % b["total"])
    print("corruptas       : %d" % b["corruptas"])
    print("tipos distintos : %d" % len(b["por_tipo"]))
    print("tipos USABLES   : %d"
          % sum(1 for f in filas if f["usable"] == "SI"))
    print()
    print("%-40s %7s %7s %-24s" % ("TIPO", "N", "USABLE", "MOTIVO"))
    print("-" * 76)
    for f in filas[:24]:
        print("%-40s %7d %7s %-24s"
              % (f["tipo"][:40], f["n"], f["usable"], f["motivo"][:24]))
    if len(filas) > 24:
        print("... y %d tipos mas" % (len(filas) - 24))
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "_eventos_inventario.json")
    with open(salida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"ruta": RUTA, "total": b["total"],
                   "corruptas": b["corruptas"],
                   "tipos_distintos": len(b["por_tipo"]),
                   "tipos": filas, "ejemplos": b["ejemplos"]},
                  fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("\ninventario completo -> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())