#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: P1.3 -- PRUEBAS DE LAS HERRAMIENTAS DE INVESTIGACION

    python dfchron/pruebas/p1_3/probar_p1_3.py

Cubre lo exigido en la seccion 35: entradas validas y ausentes, datos corruptos,
ficheros identicos y duplicados, diferencias de metadata, determinismo, y que
las herramientas NO modifiquen los originales.

HERRAMIENTA DE INVESTIGACION. No forma parte del producto.
"""
from __future__ import annotations

import hashlib
import os
import struct
import sys
import tempfile
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

import experimentos_p1_3 as exp          # noqa: E402
import forense_save as fs                # noqa: E402
import inventario_exportador as inv      # noqa: E402

FALLOS = []
PUNTOS = 0


def comprobar(nombre, condicion, detalle=""):
    global PUNTOS
    PUNTOS += 1
    if condicion:
        print("  OK    " + nombre)
    else:
        print("  FALLA " + nombre + " " + str(detalle))
        FALLOS.append(nombre)


def hacer_contenedor(version=fs.VERSION_ETIQUETA, flag=1, bloques=3):
    """Contenedor de save sintetico y valido."""
    out = bytearray(struct.pack("<II", version, flag))
    for i in range(bloques):
        cuerpo = bytes([i % 251]) * fs.BLOQUE_DESCOMPRIMIDO
        comp = zlib.compress(cuerpo, 6)
        out += struct.pack("<I", len(comp)) + comp
    return bytes(out)


def sha_de(ruta):
    with open(ruta, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def claves(d):
    return sorted(d.keys()) if isinstance(d, dict) else type(d).__name__


print("=" * 70)
print("P1.3 :: PRUEBAS DE HERRAMIENTAS DE INVESTIGACION")
print("=" * 70)

TMP = tempfile.mkdtemp(prefix="p1_3_pruebas_")

# --- [1] forense_save :: entradas validas -----------------------------------
print("\n[1] forense_save :: entradas validas")
bueno = os.path.join(TMP, "bueno.sav")
with open(bueno, "wb") as fh:
    fh.write(hacer_contenedor())
info = fs.analizar(bueno)
comprobar("contenedor valido es legible", info.get("legible") is True)
comprobar("detecta la version esperada",
          info.get("version_etiqueta") == fs.VERSION_ETIQUETA, claves(info))
comprobar("no quedan bytes sin procesar", info.get("bytes_restantes") == 0)
comprobar("todos los bloques decodifican", info.get("bloques_error") == 0)
comprobar("sha256 presente y de 64 hex", len(info.get("sha256", "")) == 64)
comprobar("mtime marcado como NO identidad",
          info.get("mtime_es_identidad") is False)

# --- [2] identicos y duplicados ---------------------------------------------
print("\n[2] forense_save :: identicos y duplicados")
copia = os.path.join(TMP, "copia.sav")
with open(copia, "wb") as fh:
    fh.write(hacer_contenedor())
cmp_id = fs.comparar(bueno, copia)
comprobar("copia byte a byte detectada",
          cmp_id.get("copia_byte_a_byte") is True)
filas = {r["campo"]: r for r in cmp_id.get("filas", [])}
comprobar("el hash no distingue el original de la copia",
          filas.get("sha256", {}).get("igual") is True)
comprobar("el hash NO se declara identidad de mundo",
          cmp_id.get("hash_responde_identidad_de_mundo") is False)

# --- [3] diferencias de metadata --------------------------------------------
print("\n[3] forense_save :: diferencias de metadata")
v9999 = os.path.join(TMP, "v9999.sav")
with open(v9999, "wb") as fh:
    fh.write(hacer_contenedor(version=9999))
iv = fs.analizar(v9999)
comprobar("version distinta marcada como NO conocida",
          iv.get("es_version_conocida") is False)
comprobar("el valor de version leido difiere",
          iv.get("version_etiqueta") == 9999)
f7 = os.path.join(TMP, "flag7.sav")
with open(f7, "wb") as fh:
    fh.write(hacer_contenedor(flag=7))
comprobar("flag distinto se lee correctamente",
          fs.analizar(f7).get("flag") == 7)
comprobar("save con otra version NO es copia byte a byte",
          fs.comparar(bueno, v9999).get("copia_byte_a_byte") is False)

# --- [4] datos corruptos -----------------------------------------------------
print("\n[4] forense_save :: datos corruptos")
vacio = os.path.join(TMP, "vacio.sav")
open(vacio, "wb").close()
ivac = fs.analizar(vacio)
comprobar("fichero vacio -> ilegible sin excepcion",
          ivac.get("legible") is False)
comprobar("fichero vacio informa del motivo", "motivo" in ivac)

corto = os.path.join(TMP, "corto.sav")
with open(corto, "wb") as fh:
    fh.write(b"\x01\x02\x03")
comprobar("cabecera truncada -> ilegible",
          fs.analizar(corto).get("legible") is False)

crudo = bytearray(hacer_contenedor())
crudo[10:40] = b"\x00" * 30
corrupto = os.path.join(TMP, "corrupto.sav")
with open(corrupto, "wb") as fh:
    fh.write(bytes(crudo))
ic = fs.analizar(corrupto)
comprobar("zlib corrupto -> se contabiliza el error",
          ic.get("bloques_error", 0) >= 1, claves(ic))
comprobar("zlib corrupto -> la herramienta no revienta", "sha256" in ic)

truncado = os.path.join(TMP, "truncado.sav")
with open(truncado, "wb") as fh:
    fh.write(hacer_contenedor()[:50])
comprobar("fichero truncado se analiza sin excepcion",
          "bloques_total" in fs.analizar(truncado))

# --- [5] entradas ausentes ----------------------------------------------------
print("\n[5] forense_save :: entradas ausentes")
comprobar("ruta inexistente -> codigo de error",
          fs.main(["--save", os.path.join(TMP, "no_existe.sav")]) == 2)
comprobar("sin argumentos -> codigo de error de uso", fs.main([]) == 2)

# --- [6] determinismo ---------------------------------------------------------
print("\n[6] forense_save :: determinismo")
comprobar("dos analisis identicos coinciden",
          fs.analizar(bueno) == fs.analizar(bueno))
a = os.path.join(TMP, "a.json")
b = os.path.join(TMP, "b.json")
fs.main(["--save", bueno, "--json", a])
fs.main(["--save", bueno, "--json", b])
comprobar("JSON byte a byte identico entre ejecuciones",
          sha_de(a) == sha_de(b))

# --- [7] no modifica los originales -------------------------------------------
print("\n[7] forense_save :: no modifica los originales")
antes = sha_de(bueno)
fs.analizar(bueno)
fs.analizar(bueno, decodificar=True)
fs.comparar(bueno, copia)
comprobar("el hash del original no cambia tras analizarlo",
          sha_de(bueno) == antes)
comprobar("no se crea ningun .bin derivado",
          not any(f.endswith(".bin") for f in os.listdir(TMP)))

# --- [8] inventario_exportador :: analisis estatico ---------------------------
print("\n[8] inventario_exportador :: analisis estatico")
RAIZ_DFHACK = os.path.abspath(
    os.path.join(AQUI, "..", "..", "..", "..", "DFHack", "hack"))
hay = os.path.isdir(RAIZ_DFHACK)
comprobar("la instalacion de DFHack esta disponible", hay, RAIZ_DFHACK)
comprobar("raiz DFHack inexistente -> codigo de error",
          inv.main(["--raiz", os.path.join(TMP, "no_existe")]) == 2)

if hay:
    informe = inv.construir_informe(RAIZ_DFHACK)
    nombres = informe["analisis"].get("ficheros_analizados", [])
    comprobar("se localiza exportlegends.lua", "exportlegends.lua" in nombres,
              nombres)
    comprobar("no falta ningun objetivo declarado",
              informe["analisis"].get("faltantes") == [],
              informe["analisis"].get("faltantes"))

    fichas = {}
    for ficha in informe["analisis"].get("detalle", []):
        fichas[ficha.get("fichero")] = ficha

    comprobar("hay una ficha por fichero analizado",
              len(fichas) == len(nombres),
              "{} fichas vs {} nombres".format(len(fichas), len(nombres)))

    el = fichas.get("exportlegends.lua", {})
    resumen = el.get("resumen", {})
    comprobar("exportlegends cede el control con script.sleep",
              resumen.get("cesion_script_sleep", 0) >= 1, resumen)
    comprobar("exportlegends NO usa with_suspend",
              "cesion_with_suspend" not in resumen)
    comprobar("exportlegends captura cur_savegame.save_dir",
              resumen.get("identidad_save_dir", 0) >= 1)
    comprobar("exportlegends NO muta memoria de DF",
              el.get("escritura_memoria_df") is False)
    comprobar("open-legends SI muta memoria de DF",
              fichas.get("open-legends.lua", {}).get(
                  "escritura_memoria_df") is True)

    comprobar("el informe se declara herramienta de investigacion",
              str(informe.get("tipo", "")).startswith("HERRAMIENTA DE INV"))
    comprobar("el informe declara no ser producto",
              informe.get("garantias", {}).get("es_producto") is False)
    comprobar("el analisis es determinista",
              inv.construir_informe(RAIZ_DFHACK) == informe)

    # --- [9] los comentarios no cuentan como cesiones ----------------------
    print("\n[9] inventario_exportador :: comentarios ignorados")
    con_comentario = os.path.join(TMP, "comentado.lua")
    with open(con_comentario, "w", encoding="utf-8") as fh:
        fh.write("-- comentario con script.sleep(1,'frames')\n")
        fh.write("local x = 1\n")
    r = inv.analizar_fichero(con_comentario)
    comprobar("un comentario NO cuenta como cesion",
              "cesion_script_sleep" not in r.get("resumen", {}))
    comprobar("el fichero se analiza igualmente", r.get("lineas") == 2)

# --- [10] experimentos :: no inventa resultados ------------------------------
print("\n[10] experimentos_p1_3 :: honestidad del banco")
banco = exp.estado_banco()
exps = banco.get("experimentos", [])
comprobar("se declaran los 12 experimentos", len(exps) == 12, len(exps))
comprobar("ningun experimento tiene resultado inventado",
          all(e.get("resultado") is None for e in exps))
comprobar("cada experimento tiene procedimiento",
          all(e.get("procedimiento") for e in exps))
comprobar("cada experimento declara su criterio de PASE y de FALLA",
          all(e.get("pase") and e.get("falla_si") for e in exps))
comprobar("cada experimento declara que mide",
          all(e.get("medir") for e in exps))
comprobar("sin DF nada se declara EJECUTADO",
          all(e.get("estado") != "EJECUTADO" for e in exps),
          [e.get("estado") for e in exps])
comprobar("el banco declara que no inventa resultados",
          banco.get("garantias", {}).get("no_inventa_resultados") is True)
comprobar("el banco declara que no escribe en saves",
          banco.get("garantias", {}).get("no_escribe_en_saves") is True)
comprobar("E7 queda enlazado con la evidencia E007",
          any(e.get("id") == "E7" and "P1.3-E007" in str(e.get("nota", ""))
              for e in exps))
comprobar("experimento inexistente -> error",
          "error" in exp.estado_banco("E99"))

# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("RESULTADO: {}/{} comprobaciones correctas".format(
    PUNTOS - len(FALLOS), PUNTOS))
if FALLOS:
    print("FALLOS:")
    for f in FALLOS:
        print("  - " + str(f))
    sys.exit(1)
print("Todas las comprobaciones de las herramientas P1.3 han pasado.")
sys.exit(0)
