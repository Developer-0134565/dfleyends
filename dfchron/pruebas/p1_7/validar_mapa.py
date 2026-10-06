#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1.7 :: validador adversarial del JSONL cartografico (herramienta, no producto).

Infracciones que la Fase F exige detectar:
  [1] Emision de un tile NO visible como conocimiento del jugador
  [2] Coordenadas ausentes o no enteras
  [3] Nombre de tiletype sin su numero (valor inventado)
  [4] Perdida de procedencia (metodo, version, read_only)
  [5] Visibilidad ausente o incoherente con el dominio
  [6] Linea que no es JSON valido, o sin observation_id
  [7] observation_id duplicado
  [8] Codificacion no UTF-8 / U+FFFD
  [9] API de escritura citada, o changed/constructed != 0
  [10] JSONL mal formado (CRLF, vacio)

Uso:  python dfchron/pruebas/p1_7/validar_mapa.py [ruta.jsonl]
"""
from __future__ import annotations

import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))

#: APIs de escritura PROHIBIDAS: si se citan como metodo, se esta escribiendo.
APIS_ESCRITURA = ("set_tiletype", "construct", "spawnFlow", "addItemSpatter",
                  "addMaterialSpatter", "setTileAquifer", "removeTileAquifer",
                  "setTileAssignment", "resetTileAssignment")

VISIBILIDADES = {"VISIBLE", "VISIBLE_CONDITIONAL", "NOT_VISIBLE", "UNKNOWN"}


def validar(ruta):
    if not os.path.isfile(ruta):
        print("FALLO: no existe %s" % ruta)
        return 2
    crudo = open(ruta, "rb").read()
    fallos = []
    try:                                            # [8]
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError as e:
        print("FALLO [8]: no es UTF-8 valido -> %s" % e)
        return 1
    if "\ufffd" in texto:
        fallos.append("[8] contiene U+FFFD: sustitucion silenciosa")
    if "\r\n" in texto:                             # [10]
        fallos.append("[10] mezcla CRLF")
    lineas = [l for l in texto.split("\n") if l.strip()]
    if not lineas:
        print("FALLO: fichero vacio")
        return 2

    vistos, n_conoc, n_diag, resumen = set(), 0, 0, None

    for i, linea in enumerate(lineas, 1):
        try:
            o = json.loads(linea)                   # [6]
        except ValueError as e:
            fallos.append("[6] linea %d no es JSON: %s" % (i, e))
            continue
        if o.get("evento") == "RESUMEN":
            resumen = o
            continue

        oid = o.get("observation_id")               # [7]
        if not oid:
            fallos.append("[6] linea %d sin observation_id" % i)
        elif oid in vistos:
            fallos.append("[7] observation_id DUPLICADO: %s" % oid)
        else:
            vistos.add(oid)

        vis = o.get("visibilidad")                  # [5]
        if vis not in VISIBILIDADES:
            fallos.append("[5] linea %d visibilidad invalida: %r" % (i, vis))

        for k in ("x", "y", "z"):                    # [2]
            if not isinstance(o.get(k), int):
                fallos.append("[2] linea %d coordenada %s no entera" % (i, k))

        prov = o.get("provenance")                  # [4]
        if not isinstance(prov, dict) or not prov.get("metodo"):
            fallos.append("[4] linea %d: procedencia ausente" % i)
        else:
            for mala in APIS_ESCRITURA:             # [9]
                if mala in prov["metodo"]:
                    fallos.append("[9] linea %d cita API de escritura %r"
                                  % (i, mala))
            if prov.get("read_only") is not True:
                fallos.append("[4] linea %d read_only no es true" % i)
            if not prov.get("dfhack_version"):
                fallos.append("[4] linea %d sin version de DFHack" % i)

        dominio = o.get("domain")
        if dominio == "tile":
            n_conoc += 1
            if vis != "VISIBLE":                    # [1] FUGA
                fallos.append("[1] FUGA linea %d: tile %r como conocimiento"
                              % (i, vis))
            if o.get("visible_para_jugador") is not True:
                fallos.append("[1] FUGA linea %d: visible no es true" % i)
            if "tiletype_nombre" in o and o.get("tiletype_num") is None:
                fallos.append("[3] linea %d: nombre sin numero" % i)   # [3]
        if dominio == "tile_NO_VISIBLE":
            n_diag += 1
            if vis != "NOT_VISIBLE":
                fallos.append("[5] linea %d dominio NO_VISIBLE con %r"
                              % (i, vis))
            if not o.get("aviso"):
                fallos.append("[1] linea %d: canal diagnostico sin aviso" % i)

    if resumen is None:
        fallos.append("falta el registro RESUMEN")
    else:                                            # [9bis]
        for k in ("changed", "constructed"):
            if resumen.get(k) not in (0, None):
                fallos.append("[9] RESUMEN %s=%r" % (k, resumen.get(k)))
        if resumen.get("solo_lectura_ok") is not True:
            fallos.append("[9] RESUMEN solo_lectura_ok no es true")
        if resumen.get("paused_final") is not True:
            fallos.append("RESUMEN: partida no pausada al final")

    print("=" * 62)
    print("P1.7 :: VALIDACION ADVERSARIAL")
    print("=" * 62)
    print("lineas            : %d" % len(lineas))
    print("como conocimiento : %d" % n_conoc)
    print("como diagnostico  : %d" % n_diag)
    if resumen:
        print("scanned/changed   : %s / %s" % (resumen.get("scanned"),
                                               resumen.get("changed")))
    print()
    if fallos:
        print("FALLOS (%d):" % len(fallos))
        for f in fallos[:25]:
            print("   - " + f)
        return 1
    print("VALIDACION CORRECTA")
    print("  sin fuga de tiles NO visibles")
    print("  coordenadas enteras, procedencia completa, read_only=true")
    print("  sin APIs de escritura; changed=0")
    print("  observation_id unicos; UTF-8; una observacion por linea")
    return 0
if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        _AQUI, "..", "..", "..", "P1.7", "mapa.jsonl")
    sys.exit(validar(os.path.abspath(destino)))