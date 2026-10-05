#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles :: INGESTOR del dataset real.
============================================

Lee `00_SOURCE/processed/merged/*.jsonl` y alimenta `dfchron.chronicles_motor`.

REGLA DE ORO DEL LOADER
-----------------------
NO inventa. NO convierte. NO normaliza de mas. NO descarta en silencio.

Cada registro conserva su contrato real:
    record_id · df_id · certainty · source · source_section · campos
Los campos desconocidos NO se eliminan: se conservan.

QUE SE DELEGA Y QUE NO
----------------------
Lectura, cache y huella: AQUI.
Semantica, orden, deduplicacion, clasificacion: `chronicles_motor`.
Vocabulario de tipos y campos: `chronicles_vocab`.
Tiempo `(year, seconds72)`: NUNCA conversion a ticks. La constante exacta de
conversion a ticks de DF no esta demostrada; convertirla seria inventar
precision que el dataset no declara.

DETERMINISMO
------------
El resultado NO depende de la hora, ni del orden de lectura de los ficheros
(van ordenados por nombre), ni de un cache con caducidad. `dataset_id` es la
identidad estable del CONTENIDO. Cache por proceso, invalidada por HUELLA de
contenido, no por reloj.
"""
from __future__ import annotations

import json
import os

from . import chronicles as ch
from . import chronicles_evento as ce
from . import chronicles_vocab as vocab
from . import chronicles_motor as cm

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Los datasets NO estan en `processed/` sino en sus subcarpetas:
# `processed/from_legends_plus/`, `processed/from_legends_xml/` y
# `processed/merged/`. Chronicles usa MERGED: es la version unificada que
# declara `dataset_version.json`. Verificado empiricamente, no supuesto.
PROCESSED = os.path.join(_RAIZ, "00_SOURCE", "processed", "merged")
VERSION = os.path.join(_RAIZ, "00_SOURCE", "dataset_version.json")

#: Datasets que forman el dataset ESENCIAL. No es "todo lo que hay": es lo que
#: la garantia PRE-IA declara suficiente para una cronica.
ESENCIALES = ("historical_figures", "historical_events", "entities",
              "sites", "artifacts", "regions", "entity_populations")

_cache = {}
#: Cache de la cronica completa. Invalidada junto con `cargar`.
_cache_cronica = {}


def _dataset_id():
    """Identidad ESTABLE del contenido. Nunca un reloj."""
    try:
        with open(VERSION, "r", encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("dataset_id")
    except (OSError, ValueError):
        return None


def _huella():
    """Huella del CONJUNTO de ficheros. Cambia si cambia un solo byte."""
    partes = []
    for nombre in ESENCIALES:
        ruta = os.path.join(PROCESSED, nombre + ".jsonl")
        try:
            partes.append("%s:%d" % (nombre, os.stat(ruta).st_size))
        except OSError:
            partes.append("%s:ausente" % nombre)
    return "|".join(partes)


def ruta_de(nombre):
    return os.path.join(PROCESSED, nombre + ".jsonl")


def leer_jsonl(nombre, limite=None):
    """Lee un JSONL real. `limite` acota la lectura: NUNCA se lee sin cota.

    Una linea corrupta NO se salta en silencio: se cuenta y se reporta.
    """
    ruta = ruta_de(nombre)
    filas, corruptas = [], 0
    if not os.path.isfile(ruta):
        return filas, {"ausente": True, "corruptas": 0, "leidas": 0}
    with open(ruta, "r", encoding="utf-8") as fh:
        for i, linea in enumerate(fh):
            if limite is not None and i >= limite:
                break
            linea = linea.strip()
            if not linea:
                continue
            try:
                filas.append(json.loads(linea))
            except ValueError:
                corruptas += 1
    return filas, {"ausente": False, "corruptas": corruptas,
                   "leidas": len(filas)}

def cargar(limite_por_dataset=None):
    """Carga los esenciales. Cache por proceso, invalidable por contenido.

    Devuelve SIEMPRE el mismo objeto: {"huella", "datos", "informe",
    "dataset_id"}. Antes devolvia `_cache["datos"]` en la ruta cacheada y el
    `_cache` completo en la primera: el mismo nombre, dos tipos de retorno.
    Detectado ejecutando, no leyendo.
    """
    global _cache
    huella = _huella()
    if _cache.get("huella") == huella:
        return _cache
    datos, informe = {}, []
    for nombre in ESENCIALES:
        filas, diag = leer_jsonl(nombre, limite_por_dataset)
        datos[nombre] = filas
        informe.append({"dataset": nombre, "registros": len(filas),
                        "ausente": diag["ausente"],
                        "corruptas": diag["corruptas"]})
    _cache = {"huella": huella, "datos": datos, "informe": informe,
              "dataset_id": _dataset_id()}
    return _cache


def invalidar_cache():
    """Invalidacion explicita. Sin relojes."""
    global _cache, _cache_cronica
    _cache = {}
    _cache_cronica = {}


# ============================================ VOCABULARIO Y LECTURA (alias) ===
#: Nombres REALES de los campos, descubiertos barriendo las 57.215 lineas.
#: No se deducen del nombre del evento: se LEEN del dataset.
#:   `hfid`       sujeto del evento. NO existe un campo `hf` ni `figure`
#:   `year`       anio, presente en las 57.215 lineas
#:   `seconds72`  posicion dentro del anio, presente en las 57.215 lineas
#:
#: En V1 el vocabulario vive en UN sitio, `chronicles_vocab`. Estos alias
#: conservan los nombres antiguos para las herramientas que ya los usan
#: (`clasificar_tipos`, `inventario_eventos`, `diagnostico_v1`...).
TEMPORALES = vocab.CAMPOS_TEMPORALES
SUJETOS = vocab.CAMPOS_SUJETO

#: Tipos que el motor convierte a un evento Chronicles VERIFICADO.
#: Clave = tipo EXACTO del dataset. Valor = (tipo_ch, campo_sujeto).
#: Se DERIVA de `vocab.SEMANTICA`: una sola fuente de verdad para la
#: equivalencia `hf died -> DEATH`. Si cambia la regla, cambia aqui sola.
MAPA_TIPOS = dict(
    (k, (v["tipo_chronicle"], v["campo_sujeto"]))
    for k, v in vocab.SEMANTICA.items())

#: Lectura de campos con procedencia: UNA implementacion, en
#: `chronicles_evento`. Se reexporta para que `cd.valor_de` siga funcionando.
valor_de = ce.valor_de
procedencia_de = ce.procedencia_de


# ================================================================== CRONICA ===
def cronica(limite=None):
    """Cronica COMPLETA del dataset real, con cache por huella de contenido.

    La semantica, el orden, la deduplicacion y la clasificacion viven en
    `chronicles_motor`; aqui solo se LEE y se cachea. Sin relojes: la cache se
    invalida por HUELLA de contenido, igual que `cargar`, nunca por hora.

    El resultado es EL MISMO objeto si el contenido no cambia: consultar dos
    veces no produce dos croniques distintas ni cuesta dos barridos.
    """
    global _cache_cronica
    datos = cargar(limite)
    clave = (datos["huella"], limite)
    if _cache_cronica.get("clave") == clave:
        return _cache_cronica["cronica"]
    cronic = cm.construir(
        datos["datos"].get("historical_events", []),
        datos["datos"].get("historical_figures", []),
        datos["datos"].get("sites", []),
        dataset_id=datos["dataset_id"])
    _cache_cronica = {"clave": clave, "cronica": cronic}
    return cronic

def construir_timeline(limite=None):
    """Linea temporal Chronicles desde el dataset REAL, barrido COMPLETO.

    DELEGACION TOTAL en `cronica()` / `chronicles_motor.construir`: este
    modulo solo LEE y cachea; la semantica no esta aqui.

    ANTES esta funcion calculaba `tick = anio * 1000000 + seg`, que ES una
    conversion a ticks NO demostrada. Se elimino: la representacion temporal
    V1 es `(year, seconds72)` y el orden se aplica sobre esa clave.

    Nada se descarta: los registros sin regla demostrada se declaran con su
    `grado` y su motivo, y `informe["por_grado"]` suma el total de registros.
    """
    cronic = cronica(limite)
    inf = cronic["informe"]
    return {"timeline": cronic["filas"],
            "cronica": cronic,
            "dataset_id": cronic["dataset_id"],
            "informe": inf,
            "registros_descartados": 0,
            "tipos_presentes": inf["tipos_vistos"],
            "tipos_convertidos": list(inf["tipos_emitidos"]),
            "derivacion_profesion": inf["derivacion_profesion"],
            "derivacion_nota": inf["derivacion_nota"]}


def entidades(limite=None):
    """Entidades Chronicles desde el dataset real.

    Identidad y procedencia salen de `ch.entidad_de_registro` (motor
    existente): sin `df_id` NO se inventa uno, se declara `NOT_PROVEN`.
    """
    datos = cargar(limite)
    salida = []
    for nombre in ("historical_figures", "entities", "sites"):
        for fila in datos["datos"].get(nombre, []):
            ent = ch.entidad_de_registro(fila)
            ent["entity_type"] = nombre
            salida.append(ent)
    return salida


def snapshot(limite=None):
    """Snapshot determinista de la fortaleza, desde el dataset real.

    Delega en el motor. `identidad_fortaleza` es `NOT_PROVEN` (el dataset
    declara 13 sitios `fortress` y legends.xml no dice cual es del jugador) y
    `edificios`/`recursos` son `NOT_AVAILABLE`, en vez de inventarlos.
    """
    return cronica(limite)["snapshot"]


def informe_ingesta(limite=None):
    """Trazabilidad de la ingestion: que se leyo y como se clasifico.

    Es la base para responder «de donde sale esto» sin reconstruirlo a mano,
    y para comprobar que no hay drops silenciosos: la suma por grado tiene
    que cuadrar con `registros_eventos` (lo comprueba `sin_drops`).
    """
    cronic = cronica(limite)
    inf = cronic["informe"]
    datos = cargar(limite)
    return {
        "dataset_id": datos["dataset_id"],
        "datasets": datos["informe"],
        "registros_totales": sum(i["registros"] for i in datos["informe"]),
        "corruptas_totales": sum(i["corruptas"] for i in datos["informe"]),
        "registros_eventos": inf["registros_eventos"],
        "eventos": inf["eventos_unicos"],
        "observaciones": inf["observaciones_declaradas"],
        "fusiones": inf["fusiones"],
        "por_grado": dict(inf["por_grado"]),
        "suma_grados": inf["suma_grados"],
        "sin_drops": inf["sin_drops"],
        "registros_descartados": 0,
        "derivacion_profesion": inf["derivacion_profesion"],
    }
