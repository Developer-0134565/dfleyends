#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-ejecuta los supervivientes contra la suite COMPLEMENTARIA.

En la primera pasada, M08 (NOT_VERIFIED 200->404) sobrevivio. Sospecha: la
prueba que comprueba los codigos HTTP (`test_cada_estado_conserva_su_codigo_http`)
vive en `probar_integracion_consulta.py`, no en `probar_api.py`. Si es asi, el
superviviente es un DEFECTO DE ASIGNACION del harness, no un hueco de cobertura.

Este script lo distingue, que es justo lo que hace falta antes de acusar a las
pruebas de nada.

Uso:  python P1_FINAL/revisar_supervivientes.py
"""
import io
import json
import os
import subprocess
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))
sys.path.insert(0, _AQUI)
import mutaciones as M  # noqa: E402

COMPLEMENTARIA = {"probar_api.py": M.INT, "probar_integracion_consulta.py": M.API}


def _b(r):
    with io.open(r, "rb") as fh:
        return fh.read()


def _w(r, d):
    with io.open(r, "wb") as fh:
        fh.write(d)


def main():
    with io.open(os.path.join(_AQUI, "MUTATION_TEST_RESULTS.json"),
                 encoding="utf-8") as fh:
        res = json.load(fh)["resultados"]
    surv = [r for r in res if r["estado"] == "SURVIVED"]
    print("Supervivientes a re-evaluar: %d" % len(surv))
    print()

    por_defecto = []
    for r in surv:
        mid, capa, ruta, buscar, poner, suite, nota = next(
            m for m in M.MUTACIONES if m[0] == r["id"])
        alt = COMPLEMENTARIA[suite]
        orig = _b(ruta)
        _w(ruta, orig.decode("utf-8").replace(buscar, poner, 1).encode("utf-8"))
        try:
            p = subprocess.run(
                [sys.executable,
                 os.path.join(_RAIZ, "dfchron", "pruebas", alt)],
                cwd=_RAIZ, capture_output=True, text=True, timeout=1200)
            det = p.returncode != 0
            cola = ""
            for l in ((p.stdout or "") + (p.stderr or "")).splitlines():
                if l.startswith(("FAILED", "FAIL:", "ERROR:")):
                    cola = l[:100]
                    break
        finally:
            _w(ruta, orig)
        veredicto = "KILLED (por la suite complementaria)" if det \
            else "SURVIVED en AMBAS suites = hueco real"
        if det:
            por_defecto.append(r["id"])
        print("[%s] %-20s %-32s %s" % (r["id"], r["capa"], suite, veredicto))
        if cola:
            print("        %s" % cola)

    print()
    print("Supervivientes debidos a ASIGNACION de suite: %s"
          % (", ".join(por_defecto) if por_defecto else "ninguno"))
    return 0


if __name__ == "__main__":
    sys.exit(main())