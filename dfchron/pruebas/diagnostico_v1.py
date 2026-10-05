#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: DIAGNOSTICO DE VALORES (no solo de presencia).
==================================================================

`inventario_eventos.py` cuenta CAMPOS. Este cuenta VALORES, que es donde
aparece lo que el campo presente no muestra: `seconds72` existe en las 57.215
lineas, pero en cuantas vale `-1`, que significa «DF no lo sabe»?

Eso decide si un evento se puede colocar en un instante o solo en un anio. Y
tambien resuelve una pregunta que la documentacion anterior afirmaba sin
comprobar: si `hfid` vale `0` de verdad no identifica a nadie.

Solo lectura. Determinista.
Uso:  python dfchron/pruebas/diagnostico_v1.py
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

from dfchron import chronicles_datos as cd   # noqa: E402

AUSENTES = ("", "-1", "-1.0")


def _v(campos, clave):
    return cd.valor_de(campos, clave, None)


def main():
    ruta = cd.ruta_de("historical_events")
    anios, segs = [], []
    anio_ausente = seg_ausente = 0
    tipo_ausente = collections.Counter()
    hfid_cero = collections.Counter()
    hf_died = {"n": 0, "seg_ausente": 0, "anio_ausente": 0, "hfid_cero": 0}

    figs = set()
    filas_figs, _ = cd.leer_jsonl("historical_figures", None)
    for f in filas_figs:
        figs.add(str(f.get("df_id")))

    muertes_sin_figura = 0
    filas, _ = cd.leer_jsonl("historical_events", None)
    for fila in filas:
        c = fila.get("campos") or {}
        t = str(_v(c, "type") or "")
        ya = _v(c, "year")
        sa = _v(c, "seconds72")
        faltan = []
        if str(ya).strip() in AUSENTES:
            anio_ausente += 1
            faltan.append("year")
        else:
            anios.append(int(ya))
        if str(sa).strip() in AUSENTES:
            seg_ausente += 1
            faltan.append("seconds72")
        else:
            segs.append(int(sa))
        if faltan:
            tipo_ausente[t + "(" + ",".join(faltan) + ")"] += 1
        if t == "hf died":
            hf_died["n"] += 1
            if str(sa).strip() in AUSENTES:
                hf_died["seg_ausente"] += 1
            if str(ya).strip() in AUSENTES:
                hf_died["anio_ausente"] += 1
            if str(_v(c, "hfid")).strip() in AUSENTES:
                hf_died["hfid_cero"] += 1
            if str(_v(c, "hfid")) not in figs:
                muertes_sin_figura += 1
        if str(_v(c, "hfid")).strip() == "0":
            hfid_cero[t] += 1

    print("=" * 78)
    print("DIAGNOSTICO DE VALORES :: historical_events")
    print("=" * 78)
    print("registros: %d   figuras: %d" % (len(filas), len(figs)))
    print()
    print("year       ausente/anulado: %d" % anio_ausente)
    if anios:
        print("             min: %d   max: %d" % (min(anios), max(anios)))
    print("seconds72  ausente/anulado: %d" % seg_ausente)
    if segs:
        print("             min: %d   max: %d" % (min(segs), max(segs)))
    print()
    print("tipos con algun temporal ausente (top 8):")
    for k, n in tipo_ausente.most_common(8):
        print("  %-46s %d" % (k[:46], n))
    print()
    print("hf died: %d registros" % hf_died["n"])
    print("   seconds72 ausente : %d" % hf_died["seg_ausente"])
    print("   year ausente      : %d" % hf_died["anio_ausente"])
    print("   hfid ausente/-1   : %d" % hf_died["hfid_cero"])
    print("   hfid sin figura en historical_figures: %d" % muertes_sin_figura)
    print()
    print("hfid == 0 por tipo (top 6):")
    for k, n in hfid_cero.most_common(6):
        print("  %-46s %d" % (k[:46], n))
    print("  TOTAL hfid==0: %d" % sum(hfid_cero.values()))

    # --- Tabla por tipo para los que se citan en `SEMANTICA_NO_DEMOSTRADA`.
    # Sin estos numeros, documentar «no lo emito porque...» seria repetir lo
    # que deduje de UN registro de ejemplo. Aqui se comprueba por tipo.
    tipos = [t for t in cd.MAPA_TIPOS] + [
        "change hf job", "change hf state", "add hf entity link",
        "add hf site link", "add hf hf link", "remove hf hf link",
        "hf simple battle event", "hf wounded", "hf abducted"]
    stats = dict((t, [0, 0, 0, 0]) for t in tipos)  # n, hfid, seg, hfid_cero
    for fila in filas:
        c = fila.get("campos") or {}
        t = str(_v(c, "type") or "")
        if t not in stats:
            continue
        s = stats[t]
        s[0] += 1
        if str(_v(c, "hfid")).strip() not in AUSENTES:
            s[1] += 1
        else:
            s[3] += 1
        if str(_v(c, "seconds72")).strip() not in AUSENTES:
            s[2] += 1
    print()
    print("%-26s %7s %7s %8s %7s" % ("TIPO", "N", "hfid", "seg72", "hfid=0"))
    print("-" * 78)
    for t in tipos:
        if t in stats:
            n, h, s, z = stats[t]
            print("%-26s %7d %7d %8d %7d" % (t[:26], n, h, s, z))
    return 0


if __name__ == "__main__":
    sys.exit(main())