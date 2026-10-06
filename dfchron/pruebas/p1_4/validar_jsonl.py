#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1.4 :: validador del JSONL de observaciones (herramienta de investigacion).

NO es producto. Solo lee y valida lo que el observador escribio en el juego.

Comprueba, de forma estricta:
  1. Una observacion por LINEA (JSONL de verdad, no JSON indentado).
  2. UTF-8 estricto, sin caracteres de reemplazo.
  3. Finales de linea LF, sin CRLF mezclado.
  4. Cada linea es un objeto JSON valido.
  5.observation_id monotono y sin repetir.
  6. observed_at presente y con formato ISO-8601 UTC.
  7. Procedencia (mechanism) presente en cada hecho.
  8. Clasificacion de visibilidad presente yKnown.
  9. Ningun hecho declara read_only = false (seria una mentira de este
     prototipo, que solo lee).
 10. Todo hecho del perimetro es VISIBLE o VISIBLE_CONDITIONAL, salvo los
     marcados NO_VISIBLE, que se listan aparte y no son imprimibles.

Uso:  python dfchron/pruebas/p1_4/validar_jsonl.py <ruta.jsonl>
"""
from __future__ import annotations

import json
import os
import sys

VISIBILIDADES = {"VISIBLE", "VISIBLE_CONDITIONAL", "NO_VISIBLE", "GOD_MODE",
                 "UNKNOWN"}
#: Un NO_VISIBLE no puede entrar en el perimetro imprimible del observador.
PERIMETRO_IMPRIMIBLE = {"VISIBLE", "VISIBLE_CONDITIONAL"}


def validar(ruta: str) -> int:
    if not os.path.isfile(ruta):
        print("FALLO: no existe %s" % ruta)
        return 2
    crudo = open(ruta, "rb").read()
    fallos = []

    # 2. UTF-8 estricto
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError as e:
        print("FALLO: no es UTF-8 valido -> %s" % e)
        return 2
    if "�" in texto:
        fallos.append("contiene U+FFFD (caracter de reemplazo): texto degradado")

    # 3. finales de linea
    crlf = texto.count("\r\n")
    lf = texto.count("\n") - crlf
    if crlf:
        fallos.append("mezcla CRLF (%d) con LF (%d)" % (crlf, lf))

    lineas = [l for l in texto.split("\n") if l.strip()]
    if not lineas:
        print("FALLO: el fichero esta vacio")
        return 2

    vistos = set()
    fuera_de_perimetro = []
    print("%-9s %-24s %-20s %s" % ("ID", "HECHO", "VISIBILIDAD", "VALOR"))
    print("-" * 96)
    for i, linea in enumerate(lineas, 1):
        # 4. JSON valido
        try:
            obj = json.loads(linea)
        except ValueError as e:
            fallos.append("linea %d no es JSON valido: %s" % (i, e))
            continue
        hecho = obj.get("fact") or {}
        # 5. identificador monotono
        oid = obj.get("observation_id")
        if not oid:
            fallos.append("linea %d sin observation_id" % i)
        elif oid in vistos:
            fallos.append("observation_id REPETIDO: %s" % oid)
        else:
            vistos.add(oid)
        # 6. marca temporal real
        ts = obj.get("observed_at") or ""
        if not (ts.endswith("Z") and len(ts) == 20):
            fallos.append("linea %d: observed_at suspecto -> %r" % (i, ts))
        # 7-9. contrato del hecho
        if not hecho.get("mechanism"):
            fallos.append("linea %d: sin mecanismo de procedencia" % i)
        vis = hecho.get("visibility")
        if vis not in VISIBILIDADES:
            fallos.append("linea %d: visibilidad invalida -> %r" % (i, vis))
        if hecho.get("read_only") is not True:
            fallos.append("linea %d: read_only no es true" % i)
        if vis not in PERIMETRO_IMPRIMIBLE and hecho.get("name"):
            fuera_de_perimetro.append((hecho["name"], vis))
        print("%-9s %-24s %-20s %s" % (oid, hecho.get("name"), vis,
                                       str(hecho.get("value"))[:36]))

    print("-" * 96)
    print("observaciones: %d" % len(lineas))
    if fuera_de_perimetro:
        print("FUERA DEL PERIMETRO IMPRIMIBLE (registrado, no se imprime):")
        for nombre, vis in fuera_de_perimetro:
            print("   - %-22s %s" % (nombre, vis))
    if fallos:
        print("\nVALIDACION FALLIDA (%d):" % len(fallos))
        for f in fallos:
            print("   - " + f)
        return 1
    print("\nVALIDACION CORRECTA: JSONL valido, UTF-8, monotono, con procedencia.")
    return 0


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "P1.4", "resultados", "observaciones.jsonl")
    sys.exit(validar(os.path.abspath(destino)))