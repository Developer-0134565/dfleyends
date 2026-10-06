#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: CORRER TODAS LAS SUITES
==========================================

Un unico comando para la REGRESION GLOBAL. Descubre `probar*.py` en los sitios
donde el proyecto ya los tiene y los ejecuta, informando por suite.

DESCUBRIMIENTO, NO HARDCODEO DE SUITES
---------------------------------------
Las suites se=colocan por convencion: `probar_*.py`. Si mañana aparece una suite
nueva en un sitio nuevo, se ejecuta sin tocar este fichero.

    python dfchron/pruebas/correr_todas.py            # todas
    python dfchron/pruebas/correr_todas.py api        # solo las que encajan

Por qué existe: el baseline documentado (32 suites / 1241 tests) estaba medido
a mano, y una regresion que solo se ve mirando la cuenta total no es una
regresion que se pueda capturar.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, "..", ".."))

#: Sitios donde el proyecto ya tiene suites. Se recorren en este orden, que es
#: el orden logico: nucleo -> aplicacion -> pruebas de frontera.
RUTAS_SUITES = (
    os.path.join(_RAIZ, "00_SOURCE", "tools"),
    os.path.join(_RAIZ, "dfchron", "pruebas"),
    os.path.join(_RAIZ, "dfchron", "pruebas", "p1_3"),
    os.path.join(_RAIZ, "API_WEB"),
    os.path.join(_RAIZ, "P1_FINAL"),
)


def descubrir():
    """Rutas absolutas de todas las suites, ordenadas para ser reproducibles."""
    suites = []
    for base in RUTAS_SUITES:
        if not os.path.isdir(base):
            continue
        for nombre in sorted(os.listdir(base)):
            if not nombre.startswith("probar") or not nombre.endswith(".py"):
                continue
            completa = os.path.join(base, nombre)
            if os.path.isfile(completa):
                suites.append(completa)
    return suites


def _cuenta(texto):
    """(tests, fallos, errores, saltados) de la salida de unittest.

    Se lee el resumen de `unittest`, que tiene una forma estable:
    `FAILED (failures=2, errors=1)` y `Ran 55 tests in 3.4s`. Se busca el
    ULTIMO resumen, porque durante la ejecucion tambien se imprimen lineas
    `FAIL: ...` que contienen las palabras buscadas.
    """
    numeros = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0}
    for linea in texto.splitlines():
        if "Ran " in linea and " test" in linea:
            for parte in linea.replace("(", " ").replace(")", " ").split():
                if parte.isdigit():
                    numeros["ran"] = int(parte)
                    break
        if linea.startswith("FAILED") or linea.startswith("OK ("):
            cuerpo = linea
            for clave in ("failures", "errors", "skipped"):
                marca = "%s=" % clave
                if marca in cuerpo:
                    bruto = cuerpo.split(marca, 1)[1].split(",")[0]
                    bruto = bruto.split(")")[0].strip()
                    try:
                        numeros[clave] = int(bruto)
                    except ValueError:
                        pass
    return numeros


def ejecutar(suite, verbose=False):
    """Ejecuta UNA suite en un subproceso. Nunca lanza."""
    ini = time.time()
    cmd = [sys.executable, suite]
    if not verbose:
        cmd.append("-q")
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=_RAIZ,
                       encoding="utf-8", errors="replace")
    salida = (p.stdout or "") + (p.stderr or "")
    n = _cuenta(salida)
    ok = p.returncode == 0
    return {"suite": os.path.relpath(suite, _RAIZ).replace("\\", "/"),
            "ok": ok, "tests": n["ran"], "fallos": n["failures"],
            "errores": n["errors"], "saltados": n["skipped"],
            "segundos": round(time.time() - ini, 1),
            "salida": salida if not ok else ""}


def main(argv):
    verbose = "--verbose" in argv
    filtros = [a for a in argv if not a.startswith("-")]
    suites = descubrir()
    if filtros:
        suites = [s for s in suites
                  if any(f.lower() in s.lower() for f in filtros)]
    if not suites:
        print("ninguna suite encontrada")
        return 1

    filas, salida_completa = [], []
    print("=" * 78)
    print("REGRESION GLOBAL :: %d suites" % len(suites))
    print("=" * 78)
    print("%-52s %6s %8s %7s" % ("SUITE", "TESTS", "ESTADO", "SEG"))
    print("-" * 78)
    total = fallos = saltados = 0
    for suite in suites:
        r = ejecutar(suite, verbose)
        filas.append(r)
        salida_completa.append(r)
        total += r["tests"]
        fallos += r["fallos"] + r["errores"]
        saltados += r["saltados"]
        estado = "OK" if r["ok"] else "FALLO"
        print("%-52s %6d %8s %7.1f"
              % (r["suite"][-52:], r["tests"], estado, r["segundos"]))

    print("-" * 78)
    print("TOTAL: %d suites · %d tests · %d fallos · %d saltados"
          % (len(filas), total, fallos, saltados))
    rotas = [r for r in filas if not r["ok"]]
    if rotas:
        print("\nSUITES CON FALLO: %d" % len(rotas))
        for r in rotas:
            print("\n" + "=" * 78)
            print(r["suite"])
            print("=" * 78)
            print(r["salida"][-4000:])
    print("\nREGRESION: %s" % ("OK" if not rotas else "CON FALLOS"))
    return 1 if rotas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))