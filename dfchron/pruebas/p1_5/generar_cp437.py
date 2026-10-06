#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1.5 :: generador de la tabla CP437 -> UTF-8 (herramienta de investigacion).

POR QUE GENERARLA Y NO ESCRIBIRLA A MANO
----------------------------------------
Escribir 128 entradas a mano invita a errores de conteo: en la primera version
de esta tabla faltaba UNA entrada y TODOS los bytes >= 0x80 mapeaban al
caracter siguiente. Nada delata eso a simple vista; solo un barrido completo.

Aqui la tabla se deriva del CODEC CP437 de Python (fuente autoritativa) y se
emite ademas un fichero de VECTORES DE PRUEBA que Lua debe reproducir byte a
byte. Si alguien cambia una entrada, la prueba falla.

NO ES PRODUCTO.  Ejecutar:  python dfchron/pruebas/p1_5/generar_cp437.py
"""
from __future__ import annotations

import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))

CABECERA = '''-- ============================================================================
-- P1.5 :: cp437.lua -- Conversion CP437 -> UTF-8 determinista y verificable
-- ============================================================================
-- GENERADO AUTOMATICAMENTE por generar_cp437.py desde el CODEC CP437 de
-- Python. NO editar a mano: se regenera y se vuelve a probar.
--
-- Determinista : misma entrada -> misma salida, siempre.
-- Invertible   : cada byte 0x00-0xFF produce un caracter, nunca ninguno.
-- No inventa   : si un byte no tuviera tabla, decode() lo DECLARA con U+FFFD.
-- Conserva     : M.hex() siempre devuelve el crudo, para poder auditar.
--
-- P1.4         : translateName() devuelve CP437, no UTF-8. El ciudadano
--                S\\x86kzul Tulonroder es "Sakzul" con 'a' con anillo:
--                en CP437, 0x86 = U+00E5. La 'e' acentuada es 0x82.
-- ============================================================================

local M = {}

local function utf8_char(cp)
    if cp < 0x80 then
        return string.char(cp)
    elseif cp < 0x800 then
        return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + (cp % 0x40))
    elseif cp < 0x10000 then
        return string.char(0xE0 + math.floor(cp / 0x1000),
                           0x80 + (math.floor(cp / 0x40) % 0x40),
                           0x80 + (cp % 0x40))
    end
    return nil
end

-- Tabla alta: indice i (1..128) -> byte 0x80 + (i - 1).
local CP437_ALTO = {
'''

CUERPO = '''}

local ALTO = {}
for i, cp in ipairs(CP437_ALTO) do ALTO[i] = utf8_char(cp) end

function M.es_ascii(s)
    if type(s) ~= 'string' then return false end
    for i = 1, #s do
        if string.byte(s, i) >= 0x80 then return false end
    end
    return true
end

function M.hex(s)
    local h = {}
    for i = 1, #s do
        h[#h + 1] = string.format('%02X', string.byte(s, i))
    end
    return table.concat(h)
end

function M.decode(s)
    if type(s) ~= 'string' then return nil end
    local out = {}
    for i = 1, #s do
        local b = string.byte(s, i)
        if b < 0x80 then
            out[#out + 1] = string.char(b)      -- ASCII: identidad
        else
            local c = ALTO[b - 0x7F]            -- 0x80 -> ALTO[1]
            if c == nil then
                out[#out + 1] = string.char(0xEF, 0xBF, 0xBD)  -- U+FFFD
            else
                out[#out + 1] = c
            end
        end
    end
    return table.concat(out)
end

function M.describir(s)
    if type(s) ~= 'string' then return nil end
    return { valor = M.decode(s), ascii = M.es_ascii(s),
             bytes_crudos = #s, hex_crudo = M.hex(s) }
end

function M.tamano_tabla()
    return #CP437_ALTO
end

return M
'''


def main():
    pares = []
    for b in range(0x80, 0x100):
        pares.append(ord(bytes([b]).decode("cp437")))
    if len(pares) != 128:
        print("ABORTO: la tabla debe tener 128 entradas, tiene %d" % len(pares))
        return 2

    cuerpo = "\n".join("    " + " ".join("0x%04X," % c for c in pares[i:i + 8])
                       for i in range(0, 128, 8))
    with open(os.path.join(_AQUI, "cp437.lua"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(CABECERA + cuerpo + "\n" + CUERPO)

    vectores = [{"crudo_hex": "%02X" % b,
                 "utf8_hex": bytes([b]).decode("cp437").encode("utf-8").hex().upper(),
                 "char": bytes([b]).decode("cp437")} for b in range(0x80, 0x100)]
    for crudo in (b"S\x86k", b"N\xf1", b"\x82", b"\xfc\xf6\xe1\xf1\xe7"):
        vectores.append({
            "crudo_hex": crudo.hex().upper(),
            "utf8_hex": crudo.decode("cp437").encode("utf-8").hex().upper(),
            "char": crudo.decode("cp437")})
    with open(os.path.join(_AQUI, "cp437_vectores.json"), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump(vectores, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print("generado cp437.lua (128 entradas) y cp437_vectores.json (%d vectores)"
          % len(vectores))
    return 0


if __name__ == "__main__":
    sys.exit(main())