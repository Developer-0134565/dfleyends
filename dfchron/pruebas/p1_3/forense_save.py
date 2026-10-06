# =============================================================================
# DF-Chronicles :: P1.3 -- HERRAMIENTA DE INVESTIGACION (NO PRODUCTIVA)
# -----------------------------------------------------------------------------
# FORENSICA DE CONTENEDOR DE SAVE (SOLO LECTURA)
#
# PROPOSITO
#   Responder con evidencia reproducible a las preguntas de la seccion B/12:
#     - Que cabecera tiene un save de DF?
#     - Dos saves byte a byte identicos producen el mismo hash?
#     - Que campos de "identidad" hay en el payload descomprimido?
#     - Que cambia entre dos saves del mismo mundo en momentos distintos?
#
# QUE HACE
#   Analiza el contenedor de save de DF (el mismo layout que usa el extractor
#   del proyecto) de forma ESTRICTAMENTE DE SOLO LECTURA:
#     u32 version | u32 flag | [ u32 comp_len | zlib(comp_len) -> 20000 B ]*
#   Ademas busca cadenas "u16 len + ASCII" tipicas de DF en el payload.
#
# GARANTIAS
#   - SOLO LECTURA. Abre los saves con 'rb' y jamas escribe en ellos.
#   - Nunca modifica, mueve ni renombra el fichero analizado.
#   - DETERMINISTA: el informe no contiene timestamps del reloj; el hash del
#     fichero SI se incluye (es contenido, no tiempo).
#   - No es producto.
#
# USO
#   python forense_save.py --save A --save B [--json salida.json]
#   python forense_save.py --save A --descodificar
# =============================================================================
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import zlib

VERSION_ETIQUETA = 3602
BLOQUE_DESCOMPRIMIDO = 20000


def sha256_fichero(ruta: str, chunk: int = 1 << 20) -> str:
    """SHA-256 en streaming. Solo lectura."""
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        while True:
            datos = fh.read(chunk)
            if not datos:
                break
            h.update(datos)
    return h.hexdigest()


def leer_cabecera(ruta: str) -> dict:
    """Lee SOLO los primeros bytes y el tamano. Sin descomprimir nada."""
    est = os.stat(ruta)
    with open(ruta, "rb") as fh:
        prefijo = fh.read(8)
    if len(prefijo) < 8:
        return {
            "ruta": ruta, "bytes": est.st_size, "legible": False,
            "motivo": "fichero mas corto que la cabecera minima (8 bytes)",
        }
    version, flag = struct.unpack("<II", prefijo)
    return {
        "ruta": ruta,
        "bytes": est.st_size,
        "legible": True,
        "version_etiqueta": version,
        "flag": flag,
        "es_version_conocida": version == VERSION_ETIQUETA,
        # mtime NO se usa como identidad: se registra solo como dato observado.
        "mtime_observado": est.st_mtime,
        "mtime_es_identidad": False,
    }


def recorrer_bloques(ruta: str):
    """Devuelve (indice, offset, comp_len, datos_o_None, error) por bloque."""
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    if len(crudo) < 8:
        return [], 0
    pos = 8
    bloques = []
    idx = 0
    while pos + 4 <= len(crudo):
        (clen,) = struct.unpack_from("<I", crudo, pos)
        pos += 4
        if clen == 0:
            break
        trozo = crudo[pos:pos + clen]
        pos += clen
        error = None
        datos = None
        try:
            datos = zlib.decompress(trozo)
        except Exception as exc:                       # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
        bloques.append((idx, pos - clen, clen, datos, error))
        idx += 1
    return bloques, len(crudo) - pos


def buscar_cadenas(payload: bytes, minimo: int = 3, limite: int = 400,
                   desde: int = 0):
    """Busca cadenas 'u16 len + ASCII imprimible' tipicas de DF.

    Solo devuelve lo observado. NO interpreta el significado del campo.
    `desde` acota el inicio del barrido: la metadata del save vive al final
    del payload, y barrer 208 MB byte a byte en Python es inviable.
    """
    hallados = []
    n = len(payload)
    for i in range(max(0, desde), n - 2, 1):
        (largo,) = struct.unpack_from("<H", payload, i)
        if largo < minimo or largo > 80 or i + 2 + largo > n:
            continue
        trozo = payload[i + 2: i + 2 + largo]
        if all(32 <= b < 127 for b in trozo):
            hallados.append({
                "offset": i, "len": largo,
                "texto": trozo.decode("ascii"),
            })
            if len(hallados) >= limite:
                break
    return hallados


def analizar(ruta: str, decodificar: bool = False,
            ventana: int = 8 << 20) -> dict:
    """Analiza un save. SOLO LECTURA."""
    info = leer_cabecera(ruta)
    if not info.get("legible"):
        return info

    info["sha256"] = sha256_fichero(ruta)
    bloques, trailing = recorrer_bloques(ruta)
    ok = [b for b in bloques if b[4] is None]

    info["bloques_total"] = len(bloques)
    info["bloques_ok"] = len(ok)
    info["bloques_error"] = len(bloques) - len(ok)
    info["bytes_descomprimidos"] = sum(len(b[3]) for b in ok)
    info["bytes_restantes"] = trailing
    info["tamano_bloques_esperado"] = BLOQUE_DESCOMPRIMIDO
    info["bloques_con_tamano_estandar"] = sum(
        1 for b in ok if len(b[3]) == BLOQUE_DESCOMPRIMIDO)

    if decodificar and ok:
        # Solo se conserva en memoria; no se escribe ningun .bin.
        payload = b"".join(b[3] for b in ok)
        desde = max(0, len(payload) - ventana)
        info["cadenas_desde_offset"] = desde
        info["cadenas_identidad_muestra"] = buscar_cadenas(
            payload, limite=80, desde=desde)
    return info


def comparar(a: str, b: str) -> dict:
    """Compara dos saves en las dimensiones que importan para P1.3."""
    ia, ib = analizar(a), analizar(b)
    filas = []
    for k in ("bytes", "sha256", "version_etiqueta", "flag",
              "bloques_total", "bytes_descomprimidos"):
        va, vb = ia.get(k), ib.get(k)
        filas.append({"campo": k, "a": va, "b": vb, "igual": va == vb})
    return {
        "a": a,
        "b": b,
        "filas": filas,
        "copia_byte_a_byte": ia.get("sha256") == ib.get("sha256"),
        "hash_responde_identidad_de_mundo": False,
        "nota": (
            "Un sha256 igual demuestra que los BYTES son iguales. "
            "No demuestra identidad de mundo ante el juego: dos ficheros "
            "identicos cargados como saves distintos son indistinguibles "
            "para cualquier prueba de contenido, y no hemos podido "
            "demostrar ningun UUID de save en DF."),
    }



def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Forensica de contenedor de save DF (P1.3, solo lectura)")
    p.add_argument("--save", action="append", default=[],
                   help="ruta de un save (repetible)")
    p.add_argument("--descodificar", action="store_true",
                   help="busca cadenas de identidad en el payload (cola)")
    p.add_argument("--ventana", type=int, default=8 << 20,
                   help="bytes finales del payload a barrer con --descodificar")
    p.add_argument("--json", default=None, help="salida JSON")
    args = p.parse_args(argv)

    if len(args.save) < 1:
        print("ERROR: indica al menos un --save")
        return 2
    for ruta in args.save:
        if not os.path.isfile(ruta):
            print(f"ERROR: no existe el fichero: {ruta}")
            return 2

    informe = {
        "herramienta": "forense_save",
        "tipo": "HERRAMIENTA DE INVESTIGACION (no productiva)",
        "garantias": {
            "solo_lectura": True,
            "determinista": True,
            "modifica_originales": False,
            "es_producto": False,
        },
        "saves": [analizar(r, args.descodificar, args.ventana)
                  for r in args.save],
    }
    if len(args.save) == 2:
        informe["comparacion"] = comparar(args.save[0], args.save[1])

    print("=" * 74)
    print("P1.3 :: FORENSICA DE CONTENEDOR DE SAVE (solo lectura)")
    print("=" * 74)
    for s in informe["saves"]:
        print(f"\n-- {os.path.basename(s['ruta'])}")
        if not s.get("legible"):
            print(f"   ILEGIBLE: {s.get('motivo')}")
            continue
        print(f"   bytes            : {s['bytes']:,}")
        print(f"   sha256           : {s['sha256']}")
        print(f"   version_etiqueta : {s['version_etiqueta']}")
        print(f"   flag             : {s['flag']}")
        print(f"   bloques          : {s['bloques_total']} "
              f"(ok {s['bloques_ok']} / error {s['bloques_error']})")
        print(f"   descomprimido    : {s['bytes_descomprimidos']:,}")
        print(f"   bytes restantes  : {s['bytes_restantes']}")
        if "cadenas_identidad_muestra" in s:
            print("   cadenas identidad (muestra):")
            for c in s["cadenas_identidad_muestra"][:20]:
                print(f"      @{c['offset']:>12,}  {c['texto']!r}")
    if "comparacion" in informe:
        print("\n-- COMPARACION")
        for f in informe["comparacion"]["filas"]:
            print(f"   {f['campo']:22s} "
                  f"{'IGUAL' if f['igual'] else 'DISTINTO'}")
        print(f"   copia byte a byte: "
              f"{informe['comparacion']['copia_byte_a_byte']}")

    if args.json:
        texto = json.dumps(informe, indent=2, sort_keys=True, ensure_ascii=False)
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
        print(f"\ninforme escrito en: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
