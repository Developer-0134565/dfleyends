#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Configuracion de la aplicacion
===============================================

Reexporta las rutas centralizadas y define los limites de la API.

`00_SOURCE/tools/rutas.py` es la fuente UNICA de verdad sobre rutas. Este
modulo solo le anade lo que necesita la aplicacion (limites, red) para que
`dfchron.servicio` y `dfchron.api` no dependan de `00_SOURCE/tools/`.

LIMITES
-------
Son deliberados. Sin ellos, un `?limit=999999999` intentaria materializar
57.215 eventos completos en memoria y en disco. Un limite NO oculta
informacion: la respuesta declara `total_encontrados` y `truncado`.
"""
import os
import sys

# El nucleo vive en 00_SOURCE/tools/. Se anade al sys.path para poder
# importarlo sin instalar nada.
TOOLS_ROOT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "00_SOURCE", "tools")
if TOOLS_ROOT not in sys.path:
    sys.path.insert(0, TOOLS_ROOT)

import rutas  # noqa: E402

PROJECT_ROOT = rutas.PROJECT_ROOT
DATA_ROOT = rutas.DATA_ROOT
TOOLS_ROOT = rutas.TOOLS_ROOT
ORIGINAL_DATA_ROOT = rutas.ORIGINAL_DATA_ROOT
PROCESSED_ROOT = rutas.PROCESSED_ROOT
MERGED_ROOT = rutas.MERGED_ROOT
VALIDATION_ROOT = rutas.VALIDATION_ROOT
EXPORT_ROOT = rutas.EXPORT_ROOT
WEB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# --- Limites de la API -------------------------------------------------------
LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 500          # tope duro de filas por peticion
LIMITE_EXPORTACION = 20000   # tope de filas en un export

# --- Red ---------------------------------------------------------------------
# 127.0.0.1 = solo local. Cambiarlo expondría el archivo a la red.
HOST_PUERTA_DEFECTO = "127.0.0.1"
PUERTO_DEFECTO = 877
# --- CORS ---------------------------------------------------------------------
# Esta API es de solo lectura y escucha en 127.0.0.1, pero la web local se
# sirve desde OTRO origen. El navegador exige CORS.
#
# NO se usa `Access-Control-Allow-Origin: *`: la lista es explicita y solo
# contiene origenes locales. Si algun dia se quisiera abrir a internet, esta
# lista es el sitio exacto que habria que revisar.
#
# PUERTOS INCLUIDOS
#   4321  `astro dev` (desarrollo con recarga)
#   4400  `dfchron/pruebas/servidor_estatico.py`, que sirve `dist/` como lo
#         haria el hosting, con el fallback a `404.html`. Es necesario para
#         auditar las rutas limpias (`/figures/712`) con el build real.
#
# Para cualquier otro puerto (por ejemplo si `astro dev` corre en otro):
#   DFCHRON_CORS_PUERTOS=5000,5001 python run.py
def _origenes_cors():
    puertos = ["4321", "4400"]
    extra = os.environ.get("DFCHRON_CORS_PUERTOS", "")
    puertos += [p.strip() for p in extra.split(",") if p.strip()]
    origenes = []
    for host in ("localhost", "127.0.0.1"):
        for puerto in puertos:
            origenes.append(f"http://{host}:{puerto}")
    return tuple(origenes)


ORIGENES_CORS = _origenes_cors()


def limite_seguro(valor, defecto=LIMITE_POR_DEFECTO, maximo=LIMITE_MAXIMO):
    """Coerce un limite pedido por el cliente a un entero dentro de rango.

    Un limite exagerado, negativo o de tipo raro NUNCA rompe la API: se
    recorta al maximo y la respuesta declara el recorte.
    """
    if valor is None or valor == "":
        return defecto
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return defecto
    if n <= 0:
        return defecto
    return min(n, maximo)


def offset_seguro(valor):
    """Offset de paginacion. Negativo o invalido -> 0."""
    if valor is None or valor == "":
        return 0
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return 0
    return max(0, n)


def resumen_rutas():
    """Informacion de arranque: se imprime al iniciar la aplicacion."""
    d = rutas.resumen()
    d["LIMITE_MAXIMO"] = LIMITE_MAXIMO
    d["HOST"] = HOST_PUERTA_DEFECTO
    return d
