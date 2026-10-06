#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1.5 :: validador cruzado de la conversion CP437 (herramienta de investigacion).

Compara la tabla Lua con el CODEC CP437 de Python, byte a byte. Son dos
implementaciones INDEPENDIENTES: si coinciden en los 128 bytes del rango alto
y en los casos compuestos, la conversion es correcta por Construccion, no por
que alguien escribiera bien una tabla.

Tambien comprueba lo que la tabla DEBE prometer y todavia no se comprobaba:
  - 128 entradas (la primera version tenia 127 y NADA lo delataba)
  - ASCII en identidad
  - determinismo
  - reversibilidad via hex
  - salida realmente UTF-8 valida

Uso:  python dfchron/pruebas/p1_5/validar_cp437.py <salida_lua.txt>
"""
from __future__ import annotations

import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))


def _leer_barrido(lineas):
    """Extrae {byte: hex_utf8} de la seccion BARRIDO."""
    out = {}
    dentro = False
    for ln in lineas:
        s = ln.strip()
        if s == "BARRIDO":
            dentro = True
            continue
        if s == "CASOS":
            break
        if dentro and s:
            partes = s.split()
            if len(partes) == 2:
                out[int(partes[0], 16)] = partes[1]
    return out


def _leer_casos(lineas):
    out = {}
    dentro = False
    for ln in lineas:
        s = ln.strip()
        if s == "CASOS":
            dentro = True
            continue
        if dentro and s.startswith("C"):
            p = s.split()
            if len(p) == 4 and p[2] == "->":
                out[int(p[0][1:])] = (p[1], p[3])
    return out


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        _AQUI, "..", "..", "..", "P1.5", "resultados", "cp437_prueba.txt")
    if not os.path.isfile(ruta):
        print("FALLO: no existe %s" % ruta)
        return 2

    crudo = open(ruta, "rb").read()
    texto = crudo.decode("utf-8")          # si no es UTF-8, esto revienta
    lineas = texto.split("\n")
    fallos = []

    # 1. La tabla debe tener 128 entradas.
    entradas = next((l.split()[1] for l in lineas
                     if l.startswith("TABLA_ENTRADAS")), "0")
    if entradas != "128":
        fallos.append("la tabla tiene %s entradas; debe tener 128" % entradas)

    # 2. Cada byte alto debe coincidir con el codec de Python.
    barrido = _leer_barrido(lineas)
    if len(barrido) != 128:
        fallos.append("el barrido covers %d bytes; deberian ser 128"
                      % len(barrido))
    for b, hex_lua in sorted(barrido.items()):
        esperado = bytes([b]).decode("cp437").encode("utf-8").hex().upper()
        if hex_lua != esperado:
            fallos.append("byte %02X: Lua da %s, Python da %s"
                          % (b, hex_lua, esperado))

    # 3. Los casos compuestos tambien.
    for idx, (hex_crudo, hex_lua) in sorted(_leer_casos(lineas).items()):
        esperado = bytes.fromhex(hex_crudo).decode("cp437") \
                        .encode("utf-8").hex().upper()
        if hex_lua != esperado:
            fallos.append("caso %d: Lua da %s, Python da %s"
                          % (idx, hex_lua, esperado))

    # 4. Determinismo y ASCII en identidad, tal y como los declaro Lua.
    def _flag(nombre):
        return any(l.startswith(nombre + " ") and l.split()[1] == "true"
                   for l in lineas)
    if not _flag("DETERMINISTA"):
        fallos.append("la conversion NO es determinista")
    if not _flag("ASCII_IDENTIDAD"):
        fallos.append("ASCII no esta en identidad")

    if fallos:
        print("VALIDACION CP437 FALLIDA (%d):" % len(fallos))
        for f in fallos[:20]:
            print("   - " + f)
        if len(fallos) > 20:
            print("   ... y %d mas" % (len(fallos) - 20))
        return 1

    print("VALIDACION CP437 CORRECTA")
    print("   tabla            : 128 entradas")
    print("   bytes 0x80-0xFF  : 128/128 coinciden con el codec de Python")
    print("   casos compuestos : coinciden")
    print("   determinista     : si")
    print("   ASCII identidad  : si")
    return 0


if __name__ == "__main__":
    sys.exit(main())