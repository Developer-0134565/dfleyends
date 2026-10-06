#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1_FINAL :: corredor de regresion COMPLETA (herramienta, no producto).

Ejecuta TODAS las suites descubiertas y registra resultado, numero de pruebas,
SKIPS y XFAILS. No selecciona suites: las descubre todas y las ejecuta todas.

No es un segundo sistema de reporting: reutiliza unittest y solo recopila su
salida.

Uso:  python P1_FINAL/corredor.py [salida.json]
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))

EXCLUIDAS = {
    "dfchron/pruebas/probar_mutation_frontera.py":
        "harness de mutacion: muta ficheros de produccion, no es suite",
    "dfchron/pruebas/p1_4/validar_jsonl.py": "validador de datos",
    "dfchron/pruebas/p1_5/validar_cp437.py": "validador de datos",
    "dfchron/pruebas/p1_7/validar_mapa.py": "validador de datos",
    "P1_FINAL/corredor.py": "este mismo fichero",
}

RE_RAN = re.compile(r"^Ran (\d+) test", re.M)
RE_SKIP = re.compile(r"skipped=(\d+)")
RE_XFAIL = re.compile(r"expected failures=(\d+)")
RE_OK = re.compile(r"^OK", re.M)


def descubrir():
    halladas = set()
    for pat in ("dfchron/pruebas/**/*.py", "00_SOURCE/tools/probar_*.py"):
        for f in glob.glob(os.path.join(_RAIZ, pat), recursive=True):
            halladas.add(os.path.relpath(f, _RAIZ).replace(os.sep, "/"))
    excl = sorted(s for s in halladas if s in EXCLUIDAS)
    ejec = sorted(s for s in halladas
                  if s not in EXCLUIDAS
                  and os.path.basename(s) != "__init__.py")
    return ejec, excl


def ejecutar(rel):
    ruta = os.path.join(_RAIZ, rel.replace("/", os.sep))
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, ruta], cwd=_RAIZ,
                           capture_output=True, text=True, timeout=1800)
        salida = (p.stdout or "") + (p.stderr or "")
        rc = p.returncode
    except subprocess.TimeoutExpired:
        return {"suite": rel, "estado": "TIMEOUT", "tests": 0, "skipped": 0,
                "xfail": 0, "segundos": round(time.time() - t0, 2)}
    dur = round(time.time() - t0, 2)
    m = RE_RAN.search(salida)
    tests = int(m.group(1)) if m else 0
    s = RE_SKIP.search(salida)
    x = RE_XFAIL.search(salida)
    if rc != 0:
        estado = "FALLA"
    elif tests == 0:
        estado = "NO_SUITE"
    elif RE_OK.search(salida):
        estado = "OK"
    else:
        estado = "OK_SIN_TAG"
    lineas = salida.strip().splitlines()
    return {"suite": rel, "estado": estado, "tests": tests,
            "skipped": int(s.group(1)) if s else 0,
            "xfail": int(x.group(1)) if x else 0,
            "segundos": dur, "returncode": rc,
            "cola": lineas[-1][:160] if lineas else ""}


def main():
    ejec, excl = descubrir()
    print("Suites descubiertas : %d" % len(ejec))
    print("Suites excluidas    : %d" % len(excl))
    for e in excl:
        print("   - %s :: %s" % (e, EXCLUIDAS[e]))
    print()
    res = []
    for i, rel in enumerate(ejec, 1):
        r = ejecutar(rel)
        res.append(r)
        print("[%2d/%2d] %-46s %-11s %5d  %6.1fs"
              % (i, len(ejec), os.path.basename(rel), r["estado"],
                 r["tests"], r["segundos"]))
        sys.stdout.flush()

    ok = [r for r in res if r["estado"] == "OK"]
    fail = [r for r in res if r["estado"] == "FALLA"]
    otros = [r for r in res if r["estado"] not in ("OK", "FALLA")]
    print()
    print("=" * 62)
    print("suites OK        : %d" % len(ok))
    print("suites FALLA     : %d" % len(fail))
    print("otros estados    : %d" % len(otros))
    print("TOTAL PRUEBAS    : %d" % sum(r["tests"] for r in res))
    print("skipped          : %d" % sum(r["skipped"] for r in res))
    print("xfail            : %d" % sum(r["xfail"] for r in res))
    print("duracion (s)     : %.1f" % sum(r["segundos"] for r in res))
    if fail:
        print("\nEN FALLA:")
        for r in fail:
            print("   - %s :: %s" % (r["suite"], r["cola"]))
    if otros:
        print("\nREQUIEREN REVISION (no son suites verificables):")
        for r in otros:
            print("   - %-46s %s" % (os.path.basename(r["suite"]), r["estado"]))
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        _AQUI, "P1_FINAL_BASELINE.json")
    with open(destino, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"excluidas": excl, "resultados": res}, fh, indent=1,
                  ensure_ascii=False)
        fh.write("\n")
    print("\nbaseline -> %s" % destino)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())