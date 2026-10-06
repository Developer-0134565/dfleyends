#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Configuracion central de rutas
=============================================

Fuente UNICA de verdad sobre donde vive cada carpeta.

POR QUE EXISTE
--------------
Antes, cada modulo repetia la misma ruta absoluta
`C:\\Users\\Missingn0\\Documents\\Dwarf Fortress\\DF-Chronicles`. Eso hacia que
mover el proyecto, o ejecutarlo desde otra carpeta, breakara el nucleo. Este
modulo resuelve las rutas RELATIVAS a la ubicacion del propio fichero, de modo
que el proyecto funciona desde cualquier sitio.

COMO SE RESUELVE
----------------
1. Si existe `DFCHRON_ROOT`, se usa como raiz.
2. Si no, se sube desde este fichero buscando la carpeta que contiene
   `00_SOURCE` (raiz del proyecto) o `original_data` (raiz de datos, caso del
   temporal de `verificar_reproducibilidad.py`).
3. Si no se encuentra nada, se usa la carpeta padre de `tools/`.

NINGUN modulo debe escribir una ruta absoluta nueva. Debe importar de aqui.

GARANTIA DE SOLO LECTURA
------------------------
`RUTAS_SOLO_LECTURA` define las carpetas que la aplicacion jamas puede
escribir: `original_data/`, `processed/` y `validation/`.
"""
import os

# Carpeta que contiene ESTE fichero (00_SOURCE/tools/ o su copia temporal).
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


def _subir_desde(inicio, nombres, maximo=6):
    """Sube directorios buscando el primero que contenga TODOS `nombres`."""
    d = inicio
    for _ in range(maximo):
        if all(os.path.isdir(os.path.join(d, n)) for n in nombres):
            return d
        padre = os.path.dirname(d)
        if padre == d:            # raiz del sistema: no se puede mas subir
            break
        d = padre
    return None


def _resolver_raiz():
    """Raiz de datos: la carpeta que contiene tools/ y original_data/."""
    override = os.environ.get("DFCHRON_ROOT", "").strip()
    if override:
        cand = os.path.abspath(override)
        # Se admite tanto la raiz del proyecto como la propia carpeta 00_SOURCE.
        if os.path.isdir(os.path.join(cand, "00_SOURCE")):
            cand = os.path.join(cand, "00_SOURCE")
        return cand
    # Desde tools/ se sube hasta encontrar la raiz de datos.
    cand = _subir_desde(TOOLS_DIR, ("tools", "original_data"))
    if cand:
        return cand
    cand = _subir_desde(TOOLS_DIR, ("00_SOURCE",))
    if cand:
        return os.path.join(cand, "00_SOURCE")
    return os.path.dirname(TOOLS_DIR)


DATA_ROOT = _resolver_raiz()

# Raiz del proyecto: el padre de 00_SOURCE (contiene 08_DATABASE, README.md...).
PROJECT_ROOT = os.environ.get(
    "DFCHRON_PROJECT_ROOT", "").strip() or os.path.dirname(DATA_ROOT)

TOOLS_ROOT = os.path.join(DATA_ROOT, "tools")
ORIGINAL_DATA_ROOT = os.path.join(DATA_ROOT, "original_data")
PROCESSED_ROOT = os.path.join(DATA_ROOT, "processed")
MERGED_ROOT = os.path.join(PROCESSED_ROOT, "merged")
PLUS_ROOT = os.path.join(PROCESSED_ROOT, "from_legends_plus")
LEGENDS_ROOT = os.path.join(PROCESSED_ROOT, "from_legends_xml")
VALIDATION_ROOT = os.path.join(PROCESSED_ROOT, "validation")
MANIFEST_PATH = os.path.join(DATA_ROOT, "dataset_manifest.json")

# Exports FUERA de processed/: un export nunca puede contaminar el dataset.
EXPORT_ROOT = os.environ.get(
    "DFCHRON_EXPORT_ROOT", "").strip() or os.path.join(DATA_ROOT, "exports")

# Carpetas que NUNCA admiten escritura por parte de la aplicacion.


def normalizar(ruta):
    """Ruta absoluta y comparable (resuelve mayusculas y barras distintas)."""
    return os.path.normcase(os.path.abspath(ruta))


def es_ruta_protegida(ruta):
    """¿La ruta cae dentro de original_data/, processed/ o validation/?

    Se usa para ABORTAR cualquier escritura sospechosa ANTES de que ocurra.
    """
    destino = normalizar(ruta)
    for protegida in RUTAS_SOLO_LECTURA:
        p = normalizar(protegida)
        if destino == p or destino.startswith(p + os.sep):
            return True
    return False


def ruta_de_exportacion(nombre):
    """Resuelve un nombre de exportacion dentro de EXPORT_ROOT.

    ABORTA si el nombre intenta salir de EXPORT_ROOT (path traversal) o si
    apunta a una carpeta protegida. Devuelve la ruta absoluta segura.
    """
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("nombre de exportacion vacio")
    limpio = os.path.basename(nombre.strip())
    if limpio in ("", ".", "..") or os.sep in limpio or "/" in limpio:
        raise ValueError(f"nombre de exportacion no valido: {nombre!r}")
    destino = os.path.join(EXPORT_ROOT, limpio)
    if normalizar(os.path.dirname(destino)) != normalizar(EXPORT_ROOT):
        raise ValueError("la exportacion se sale de EXPORT_ROOT")
    if es_ruta_protegida(destino):
        raise ValueError("destino protegido: no se escribe en datos originales")
    return destino


def resumen():
    """Rutas activas. Se imprime al arrancar DF-Chronicles."""
    return {
        "PROJECT_ROOT": PROJECT_ROOT,
        "DATA_ROOT": DATA_ROOT,
        "TOOLS_ROOT": TOOLS_ROOT,
        "ORIGINAL_DATA_ROOT": ORIGINAL_DATA_ROOT,
        "PROCESSED_ROOT": PROCESSED_ROOT,
        "MERGED_ROOT": MERGED_ROOT,
        "VALIDATION_ROOT": VALIDATION_ROOT,
        "EXPORT_ROOT": EXPORT_ROOT,
        "origen": ("DFCHRON_ROOT" if os.environ.get("DFCHRON_ROOT")
                   else "ubicacion del proyecto"),
        "existe_dataset": os.path.isdir(MERGED_ROOT),
    }


def asegurar_export_root():
    """Crea EXPORT_ROOT si hace falta. Nunca toca rutas protegidas."""
    if es_ruta_protegida(EXPORT_ROOT):
        raise RuntimeError(
            f"EXPORT_ROOT cae en una ruta protegida: {EXPORT_ROOT}")
    os.makedirs(EXPORT_ROOT, exist_ok=True)
    return EXPORT_ROOT


if __name__ == "__main__":
    import json
    print(json.dumps(resumen(), ensure_ascii=False, indent=2))

RUTAS_SOLO_LECTURA = (ORIGINAL_DATA_ROOT, PROCESSED_ROOT, VALIDATION_ROOT)
