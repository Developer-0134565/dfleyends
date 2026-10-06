#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Actualizacion manual de datos
================================================

Reconstruye los datos que consume la API a partir de los XML de Legends, SIN
tocar jamas la version que esta en uso hasta que la nueva ha superado todas las
comprobaciones.

POR QUE NO SE GENERA DIRECTAMENTE
---------------------------------
`integrar_legends.py` escribe sobre `processed/` mientras trabaja. Si se ejecuta
en contra, la version valida queda a medias cuando algo falla, y la API se
queda sin datos. Aqui se genera primero en un staging y solo se activa al final.

COMO SE GARANTIZA QUE NO SE ROMPE NADA
--------------------------------------
1. La generacion ocurre en `00_SOURCE/work/staging-<sello>/`, un arbol COMPLETO
   (original_data + tools + processed). Se usa el mismo truco ya probado por
   `verificar_reproducibilidad.py`: al copiar `tools/` al staging junto a
   `original_data/`, `rutas.py` resuelve el staging como raiz y el pipeline
   entero escribe ahi sin tocar el dataset real.
2. Antes de generar se comprueban las entradas y se hashean.
3. Se valida el staging. Si algo falla, el staging se borra y no se toca nada.
4. Al activar, la version actual se mueve a `backups/` y entra la nueva. Si el
   segundo movimiento falla, se RESTAURA la anterior.
5. `original_data/` solo se lee: `registrar_original()` nunca sobrescribe.

USO
---
    python 00_SOURCE/tools/actualizar_datos.py estado
    python 00_SOURCE/tools/actualizar_datos.py actualizar
    python 00_SOURCE/tools/actualizar_datos.py actualizar --sin-activar
    python 00_SOURCE/tools/actualizar_datos.py recuperar
    python 00_SOURCE/tools/actualizar_datos.py historial

REINICIO DE LA API
------------------
`dfchron/servicio.py` guarda el `Archivo` en un singleton (`_ARCHIVO`), asi que
la API mantiene en memoria la version con la que arranco. Tras activar datos
nuevos hay que REINICIAR `python run.py` para servirlos. No es un defecto: leer
57.215 eventos cuesta ~2,5 s y hacerlo en cada peticion no es viable.
"""
import os
import sys
import json
import time
import shutil
import hashlib
import argparse
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402
import identidad_mundo  # noqa: E402

DATA_ROOT = rutas.DATA_ROOT
TOOLS_ROOT = rutas.TOOLS_ROOT
ORIGINAL_DATA_ROOT = rutas.ORIGINAL_DATA_ROOT
PROCESSED_ROOT = rutas.PROCESSED_ROOT
MERGED_ROOT = rutas.MERGED_ROOT

# --- Directorios del sistema de actualizacion -------------------------------
# Todos fuera de `processed/`: la version activa nunca seMezcla con el trabajo.
WORK_ROOT = os.path.join(DATA_ROOT, "work")
BACKUPS_ROOT = os.path.join(DATA_ROOT, "backups")
VERSION_PATH = os.path.join(DATA_ROOT, "dataset_version.json")

ENTRADAS = ("legends.xml", "legends_plus.xml")

# Secciones que merged/ debe tener para considerarse utilizable.
SECCIONES_MINIMAS = ("historical_figures", "entities", "sites",
                     "historical_events", "artifacts")

# Hook SOLO para pruebas: aborta en una etapa concreta.
# `DFCHRON_FALLO_EN=integrar` -> la etapa 3 falla.
VAR_FALLO = "DFCHRON_FALLO_EN"

ANCHO = 74


# =============================================================================
# Utilidades
# =============================================================================
def sello():
    """Marca temporal ordenable: 20261003-015500."""
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def ahora_iso():
    """ISO con milisegundos: dos actualizaciones seguidas en el mismo segundo
    deben quedar distinguibles."""
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def sha256_de(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def calcular_dataset_id(salidas):
    """Identificador estable del dataset a partir de {fichero: sha256}.

    Se deriva del CONTENIDO, no de un reloj, por dos razones:

      * determinista: el mismo contenido produce siempre el mismo id, así que
        dos actualizaciones que no cambian nada no parecen "mundos nuevos";
      * sensible: si cambia un solo byte, cambia el id.

    Es lo que permite responder "¿qué dataset está sirviendo la API?"
    comparando dos cadenas, sin releer los 58 MB de eventos.

    La fórmula se duplica a propósito en `dfchron/servicio.py` para que la API
    pueda derivar el id de un registro antiguo que aún no tenga el campo.
    `probar_refresh_cycle.py` comprueba que las dos dan el mismo valor.
    """
    try:
        texto = json.dumps(salidas, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":"))
    except (TypeError, ValueError):
        return None
    return "v1-" + hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def cabecera(titulo):
    print()
    print("=" * ANCHO)
    print(titulo)
    print("=" * ANCHO)


def etapa(n, total, texto):
    print(f"\n[{n}/{total}] {texto}")


def info(mensaje):
    print(f"      {mensaje}")


def ok(mensaje):
    print(f"   OK  {mensaje}")


def fallo(mensaje):
    print(f"  FALLO  {mensaje}")


class ErrorActualizacion(Exception):
    """Fallo en una etapa. Siempre significa: NO se toca la version activa."""


def _puede_fallar(nombre_etapa):
    """¿El hook de pruebas pide fallar aquí? Usado solo por la suite de pruebas."""
    objetivo = os.environ.get(VAR_FALLO, "").strip()
    if objetivo and objetivo == nombre_etapa:
        raise ErrorActualizacion(
            f"fallo simulado en la etapa '{nombre_etapa}' (hook {VAR_FALLO})")


def humano(n):
    return f"{n:,}".replace(",", ".")


# =============================================================================
# Etapa 1 - Entradas
# =============================================================================
def comprobar_entradas(origenes=None):
    """Comprueba que los XML existen, son legibles y no estan vacios.

    `origenes` permite probar con otro directorio (fixtures de prueba).
    Devuelve {nombre: {ruta, bytes, sha256}}.
    """
    base = origenes or ORIGINAL_DATA_ROOT
    info_base = {}
    for nombre in ENTRADAS:
        ruta = os.path.join(base, nombre)
        if not os.path.exists(ruta):
            raise ErrorActualizacion(
                f"falta el fichero de entrada {nombre} en {base}")
        if not os.path.isfile(ruta):
            raise ErrorActualizacion(f"{nombre} no es un fichero")
        try:
            tamano = os.path.getsize(ruta)
            with open(ruta, "rb") as f:
                f.read(1)
        except OSError as exc:
            raise ErrorActualizacion(f"no se puede leer {nombre}: {exc}") from exc
        if tamano == 0:
            raise ErrorActualizacion(f"{nombre} está vacío (0 bytes)")
        info_base[nombre] = {"ruta": ruta, "bytes": tamano,
                             "sha256": sha256_de(ruta)}
    return info_base
# =============================================================================
# Etapa 2 - Staging
# =============================================================================
def _copiar_arbol(origen, destino):
    shutil.copytree(origen, destino,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                "work", "backups"))


def preparar_staging(destino, entradas, raiz_proyecto):
    """Crea un arbol COMPLETO y aislado para generar los datos ahi.

        <destino>/original_data/   <- copias de los XML de entrada
        <destino>/tools/           <- copia de las herramientas
        <destino>/processed/       <- lo generara la integracion

    Al tener `tools/` y `original_data/` juntos, `rutas.py` resuelve `<destino>`
    como raiz y TODO el pipeline escribe dentro. El dataset real es intocable.
    """
    # ABSOLUTAS a proposito: la integracion se ejecuta en un subproceso con
    # `cwd` en el staging, asi que una ruta relativa se resolveria desde alli y
    # apuntaria al sitio equivocado.
    destino = os.path.abspath(destino)
    if os.path.exists(destino):
        shutil.rmtree(destino, ignore_errors=True)
    os.makedirs(destino, exist_ok=True)

    odir = os.path.join(destino, "original_data")
    os.makedirs(odir, exist_ok=True)
    for nombre, meta in entradas.items():
        shutil.copy2(meta["ruta"], os.path.join(odir, nombre))

    tdir = os.path.join(destino, "tools")
    _copiar_arbol(TOOLS_ROOT, tdir)

    with open(os.path.join(destino, "_staging.json"), "w", encoding="utf-8") as f:
        json.dump({"raiz_proyecto": raiz_proyecto,
                   "creado": ahora_iso(),
                   "entradas": {k: v["sha256"] for k, v in entradas.items()}},
                  f, ensure_ascii=False, indent=1)
    return {"raiz": destino, "tools": tdir, "original_data": odir,
            "processed": os.path.join(destino, "processed")}


# =============================================================================
# Etapa 3 - Extraccion + integracion
# =============================================================================
_CODIGO_RUNNER = """import sys, json
sys.path.insert(0, {tdir!r})
import integrar_legends as IL
IL.SRC = {raiz!r}
IL.ORIG_DIR = {odir!r}
IL.PROC = {proc!r}
IL.PROC_LEGENDS = {proc_legends!r}
IL.PROC_PLUS = {proc_plus!r}
IL.PROC_MERGED = {proc_merged!r}
IL.ORIG_LEGENDS = {orig_legends!r}
IL.ORIG_PLUS = {orig_plus!r}
m = IL.integrar()
mg = m['merge']
print('RESULTADO_JSON ' + json.dumps({{
    'divergencias': mg['divergencias_totales'],
    'conflictos': mg['conflictos_reales'],
    'fusionados': mg['registros_fusionados'],
    'generado': m['generado'],
    'lectura': {{k: {{'codificacion': v['codificacion_detectada'],
                     'entradas': v['total_entradas'],
                     'sha256': v['sha256']}}
               for k, v in m['lectura'].items()}},
}}))
"""


def generar(staging):
    """Ejecuta `integrar_legends.integrar()` DENTRO del staging.

    Va en un subproceso: si la integracion revienta, este proceso sigue vivo y
    puede limpiar sin dejar nada a medias.

    El runner reasigna las variables de modulo de `integrar_legends`, igual que
    hace `verificar_reproducibilidad.py`. Los nombres de esas variables no se
    tocan en ese modulo por ese motivo.
    """
    _puede_fallar("integrar")
    import subprocess

    tdir = staging["tools"]
    proc = staging["processed"]
    odir = staging["original_data"]
    runner = os.path.join(tdir, "_runner_actualizacion.py")
    codigo = _CODIGO_RUNNER.format(
        tdir=tdir, raiz=staging["raiz"], odir=odir, proc=proc,
        proc_legends=os.path.join(proc, "from_legends_xml"),
        proc_plus=os.path.join(proc, "from_legends_plus"),
        proc_merged=os.path.join(proc, "merged"),
        orig_legends=os.path.join(odir, "legends.xml"),
        orig_plus=os.path.join(odir, "legends_plus.xml"))
    with open(runner, "w", encoding="utf-8") as f:
        f.write(codigo)

    info(f"integrando en {proc}")
    p = subprocess.run([sys.executable, os.path.basename(runner)], cwd=tdir,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        raise ErrorActualizacion(
            "la integracion fallo:\n" + (p.stderr or p.stdout or "")[-900:])

    resumen = {}
    for linea in (p.stdout or "").splitlines():
        if linea.startswith("RESULTADO_JSON "):
            resumen = json.loads(linea[len("RESULTADO_JSON "):])
    merged = os.path.join(proc, "merged")
    if not os.path.isdir(merged):
        raise ErrorActualizacion("la integracion no produjo processed/merged/")
    return {"resumen": resumen, "salida": p.stdout, "merged": merged}
# =============================================================================
# Etapa 4 - Validacion del staging
# =============================================================================
_CODIGO_HUMO = """import sys, json
sys.path.insert(0, {tdir!r})
import rutas
rutas.DATA_ROOT = {raiz!r}
rutas.PROCESSED_ROOT = {proc!r}
rutas.MERGED_ROOT = {merged!r}
import validar_semantica as VS
VS.MERGED = {merged!r}
VS.PLUS = {plus!r}
VS.PROC = {proc!r}
from nucleo import Archivo
a = Archivo()
e = a.estadisticas()
print('RESULTADO_JSON ' + json.dumps({{
    'figuras': len(a.indice.figuras),
    'entidades': len(a.indice.entidades),
    'sitios': len(a.indice.sitios),
    'eventos': len(a.indice.eventos),
    'artefactos': len(a.indice.artefactos),
    'anios': [e.get('anio_min'), e.get('anio_max')],
}}, default=str))
"""


def validar_estructura(merged):
    """Los JSONL existen, son JSONL de verdad y tienen contenido."""
    problemas = []
    for sec in SECCIONES_MINIMAS:
        ruta = os.path.join(merged, f"{sec}.jsonl")
        if not os.path.isfile(ruta):
            problemas.append(f"falta {sec}.jsonl")
            continue
        n = 0
        with open(ruta, encoding="utf-8") as f:
            for i, linea in enumerate(f, 1):
                if not linea.strip():
                    continue
                n += 1
                try:
                    json.loads(linea)
                except json.JSONDecodeError as exc:
                    problemas.append(f"{sec}.jsonl linea {i} no es JSON: {exc}")
                    break
        if n == 0:
            problemas.append(f"{sec}.jsonl esta vacio")
    return problemas


def validar_nucleo(staging):
    """Carga el staging con el nucleo REAL y comprueba que sirve datos.

    Es la comprobacion de que la API podrá servirlo. Va en subproceso, con
    `rutas` y `validar_semantica` apuntando al staging.
    """
    import subprocess
    _puede_fallar("validar")
    tdir = staging["tools"]
    proc = staging["processed"]
    merged = os.path.join(proc, "merged")
    runner = os.path.join(tdir, "_humo_actualizacion.py")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(_CODIGO_HUMO.format(tdir=tdir, raiz=staging["raiz"], proc=proc,
                                    merged=merged,
                                    plus=os.path.join(proc, "from_legends_plus")))
    p = subprocess.run([sys.executable, os.path.basename(runner)], cwd=tdir,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        raise ErrorActualizacion(
            "el nucleo no pudo cargar el staging:\n"
            + (p.stderr or p.stdout or "")[-900:])
    for linea in (p.stdout or "").splitlines():
        if linea.startswith("RESULTADO_JSON "):
            return json.loads(linea[len("RESULTADO_JSON "):])
    raise ErrorActualizacion("el nucleo no devolvio el resumen esperado")
# =============================================================================
# Etapa 5 - Manifiesto de hashes de salida
# =============================================================================
SECCIONES_MANIFIESTO = (
    "historical_figures", "entities", "sites", "historical_events",
    "artifacts", "historical_event_relationships",
    "historical_event_relationship_supplements",
    "historical_event_collections", "historical_eras", "regions",
    "underground_regions", "entity_populations", "written_contents",
    "poetic_forms", "musical_forms", "dance_forms", "world_constructions",
)


def manifiesto_hashes(merged):
    """SHA-256 y nº de lineas de cada JSONL -> `merged/_hashes.json`.

    Permite saber mas tarde si la version activa es la que se genero, sin
    recalcular nada ni depender del contenido.
    """
    salida = {}
    for sec in SECCIONES_MANIFIESTO:
        ruta = os.path.join(merged, f"{sec}.jsonl")
        if not os.path.isfile(ruta):
            continue
        h = hashlib.sha256()
        n = 0
        with open(ruta, "rb") as f:
            for linea in f:
                if linea.strip():
                    n += 1
                h.update(linea)
        salida[sec] = {"lineas": n, "sha256": h.hexdigest(),
                       "bytes": os.path.getsize(ruta)}
    if not salida:
        raise ErrorActualizacion("no se genero ningun JSONL: nada que activar")
    doc = {"generado": ahora_iso(), "secciones": salida}
    with open(os.path.join(merged, "_hashes.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc


def verificar_hashes(merged, manifiesto=None):
    """Recalcula los hashes y los compara con el manifiesto.

    Sin manifiesto, se genera. Si algo no cuadra es un fallo: alguien toco los
    ficheros o la generacion se interrumpio a medias.
    """
    ruta_m = os.path.join(merged, "_hashes.json")
    if manifiesto is None:
        if os.path.isfile(ruta_m):
            with open(ruta_m, encoding="utf-8") as f:
                try:
                    manifiesto = json.load(f)
                except json.JSONDecodeError as exc:
                    raise ErrorActualizacion(
                        f"_hashes.json ilegible: {exc}") from exc
        else:
            manifiesto = manifiesto_hashes(merged)
    secciones = manifiesto.get("secciones") or {}
    if not secciones:
        raise ErrorActualizacion("el manifiesto no declara ninguna seccion")

    discrepancias = []
    for sec, esperado in secciones.items():
        ruta = os.path.join(merged, f"{sec}.jsonl")
        if not os.path.isfile(ruta):
            discrepancias.append(f"{sec}.jsonl no existe")
            continue
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            for linea in f:
                h.update(linea)
        if h.hexdigest() != esperado.get("sha256"):
            discrepancias.append(f"{sec}.jsonl no coincide con el manifiesto")
    for sec in SECCIONES_MANIFIESTO:
        ruta = os.path.join(merged, f"{sec}.jsonl")
        if os.path.isfile(ruta) and sec not in secciones:
            discrepancias.append(f"{sec}.jsonl no figura en el manifiesto")
    if discrepancias:
        raise ErrorActualizacion("los hashes no cuadran:\n        - "
                                 + "\n        - ".join(discrepancias))
    return manifiesto
# =============================================================================
# Etapa 6 - Activacion (backup + intercambio con reversion)
# =============================================================================
def listar_backups(backups_root=None):
    """Backups existentes, del mas reciente al mas antiguo."""
    root = backups_root or BACKUPS_ROOT
    if not os.path.isdir(root):
        return []
    salida = []
    for n in sorted(os.listdir(root), reverse=True):
        d = os.path.join(root, n)
        if os.path.isdir(d):
            salida.append((n, d))
    return salida


def leer_version(raiz_datos=None):
    """Registro de la version activa, o None si todavia no existe."""
    ruta = os.path.join(raiz_datos or DATA_ROOT, "dataset_version.json")
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def escribir_version(doc, raiz_datos=None):
    """Registro de la version activa. Se escribe AL FINAL, tras activar."""
    ruta = os.path.join(raiz_datos or DATA_ROOT, "dataset_version.json")
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def _ruta_backup_libre(backups_root=None):
    root = backups_root or BACKUPS_ROOT
    base = os.path.join(root, f"merged-{sello()}")
    if not os.path.exists(base):
        return base
    n = 2
    while os.path.exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def activar(merged_nuevo, destino_merged=MERGED_ROOT, backups_root=None):
    """Pone el staging en produccion conservando la version anterior.

    1. La version actual se mueve a `backups/merged-<sello>/`.
    2. La nueva entra en su lugar.
    3. Si (2) falla, se restaura (1) y se aborta.

    Los dos movimientos son `rename` dentro del mismo volumen: rapidos. Si aun
    asi se interrumpe justo entre ambos, la version anterior sigue en
    `backups/` y `recuperar()` la devuelve.
    """
    _puede_fallar("activar")
    root = backups_root or BACKUPS_ROOT
    os.makedirs(os.path.dirname(destino_merged), exist_ok=True)
    respaldo = None
    if os.path.isdir(destino_merged):
        os.makedirs(root, exist_ok=True)
        respaldo = _ruta_backup_libre(root)
        os.rename(destino_merged, respaldo)
        info(f"version anterior guardada en {respaldo}")

    try:
        os.rename(merged_nuevo, destino_merged)
    except OSError as exc:
        if respaldo and os.path.isdir(respaldo):
            try:
                os.rename(respaldo, destino_merged)
                info("version anterior restaurada automaticamente")
            except OSError:
                pass
        raise ErrorActualizacion(
            f"no se pudo activar la nueva version ({exc}); "
            f"la anterior esta en {respaldo}") from exc
    return respaldo


def recuperar(destino_merged=MERGED_ROOT, indice=0, backups_root=None):
    """Devuelve una version anterior. `indice` 0 = la mas reciente.

    Guarda la version que sustituye en un backup nuevo: recuperar tambien es
    reversible.
    """
    root = backups_root or BACKUPS_ROOT
    backups = listar_backups(root)
    if not backups:
        raise ErrorActualizacion("no hay ninguna copia anterior en backups/")
    if indice >= len(backups):
        raise ErrorActualizacion(
            f"solo hay {len(backups)} copias; indice {indice} no existe")

    nombre, ruta = backups[indice]
    actual_a_guardar = None
    if os.path.isdir(destino_merged):
        os.makedirs(root, exist_ok=True)
        actual_a_guardar = _ruta_backup_libre(root)
        os.rename(destino_merged, actual_a_guardar)
    try:
        os.rename(ruta, destino_merged)
    except OSError as exc:
        if actual_a_guardar and os.path.isdir(actual_a_guardar):
            os.rename(actual_a_guardar, destino_merged)
        raise ErrorActualizacion(f"no se pudo recuperar: {exc}") from exc
    return {"recuperada": nombre, "apartada": actual_a_guardar}
# =============================================================================
# Orquestador
# =============================================================================
def actualizar(origenes=None, raiz_proyecto=None, activar_nuevo=True,
               dejar_staging=False, raiz_datos=None, merged_destino=None,
               work_root=None, backups_root=None):
    """Flujo completo. Devuelve el registro de version, o lanza ErrorActualizacion.

    La garantia central: `merged_destino` NO se toca hasta que la version nueva
    ha generado, validado y tiene sus hashes comprobados.
    """
    raiz_proyecto = raiz_proyecto or rutas.PROJECT_ROOT
    raiz_datos = os.path.abspath(raiz_datos or DATA_ROOT)
    destino_merged = os.path.abspath(merged_destino) if merged_destino \
        else os.path.join(raiz_datos, "processed", "merged")
    staging_padre = os.path.abspath(work_root or WORK_ROOT)
    backups = os.path.abspath(backups_root or BACKUPS_ROOT)

    total = 8
    cabecera("ACTUALIZACION MANUAL DE DATOS")
    info(f"raiz de datos : {raiz_datos}")
    info(f"version activa: {destino_merged}")

    t0 = time.time()

    # --- 1. Entradas -------------------------------------------------------
    etapa(1, total, "Comprobando ficheros de entrada")
    _puede_fallar("entradas")
    entradas = comprobar_entradas(origenes)
    for nombre, meta in entradas.items():
        info(f"{nombre:<20} {humano(meta['bytes'])} B  sha256 {meta['sha256'][:16]}…")

    # --- 2. Staging --------------------------------------------------------
    etapa(2, total, "Preparando el area de trabajo")
    _puede_fallar("preparar")
    os.makedirs(staging_padre, exist_ok=True)
    staging_dir = os.path.join(staging_padre, f"staging-{sello()}")
    staging = preparar_staging(staging_dir, entradas, raiz_proyecto)
    info(f"staging: {staging_dir}")

    try:
        # --- 3. Extraccion + integracion -----------------------------------
        etapa(3, total, "Extrayendo e integrando Legends")
        gen = generar(staging)
        r = gen["resumen"]
        for nombre, det in (r.get("lectura") or {}).items():
            info(f"{nombre}: {det.get('codificacion')}, "
                 f"{humano(det.get('entradas', 0))} entradas")
        info(f"divergencias entre fuentes: {humano(r.get('divergencias', 0))}")

        # --- 4. Validacion -------------------------------------------------
        etapa(4, total, "Validando la version generada")
        problemas = validar_estructura(gen["merged"])
        if problemas:
            raise ErrorActualizacion("estructura invalida:\n        - "
                                     + "\n        - ".join(problemas))
        ok("todos los JSONL son validos y tienen contenido")

        humo = validar_nucleo(staging)
        info(f"el nucleo carga el staging: {humano(humo['figuras'])} figuras, "
             f"{humano(humo['eventos'])} eventos")

        # --- 5. Manifiesto -------------------------------------------------
        etapa(5, total, "Generando manifiesto de hashes")
        _puede_fallar("manifiesto")
        manifiesto = manifiesto_hashes(gen["merged"])
        info(f"{len(manifiesto['secciones'])} secciones hasheadas -> _hashes.json")
        verificar_hashes(gen["merged"], manifiesto)
        ok("los hashes coinciden con el manifiesto")

        # --- 6. Activacion -------------------------------------------------
        if not activar_nuevo:
            etapa(6, total, "Version generada; activacion OMITIDA")
            info("la version activa NO se ha tocado")
            info(f"version preparada en: {gen['merged']}")
            return {"activado": False, "merged_nuevo": gen["merged"],
                    "entradas": entradas, "resumen": r, "conteos": humo,
                    "manifiesto": manifiesto}

        etapa(6, total, "Activando la nueva version")
        respaldo = activar(gen["merged"], destino_merged, backups)

        # --- 7. Comprobacion posterior -------------------------------------
        etapa(7, total, "Comprobando la version activa")
        try:
            _puede_fallar("verificar")
            verificar_hashes(destino_merged, manifiesto)
        except Exception as exc:
            # La version nueva YA esta en su sitio. Si no cuadra, se revierte:
            # la version valida debe seguir siendo la activa.
            revertido = False
            if respaldo and os.path.isdir(respaldo):
                try:
                    averiada = _ruta_backup_libre(backups)
                    os.rename(destino_merged, averiada)
                    os.rename(respaldo, destino_merged)
                    revertido = True
                except OSError:
                    pass
            raise ErrorActualizacion(
                f"la version activa no supera la comprobacion ({exc}); "
                + ("se ha revertido a la version anterior"
                   if revertido else
                   f"la version anterior esta en {respaldo}")) from exc
        ok("la version activa coincide con el manifiesto recien generado")

        # --- 8. Registro ----------------------------------------------------
        etapa(8, total, "Registrando la version")
        version_anterior = leer_version(raiz_datos)
        registro = {
            "actualizada": ahora_iso(),
            # Identificador estable del dataset. Se DERIVA de las huellas reales
            # de las salidas, no de un reloj: dos ejecuciones sobre el mismo
            # contenido dan el mismo id, y si cambia un byte cambia el id.
            # Es lo que permite saber "que mundo esta sirviendo la API".
            "dataset_id": calcular_dataset_id(manifiesto["secciones"]),
            "entradas": {k: {"sha256": v["sha256"], "bytes": v["bytes"],
                             "origen": v["ruta"]} for k, v in entradas.items()},
            "salidas": manifiesto["secciones"],
            "conteos": humo,
            "merge": r,
            "backup_de_la_version_anterior": respaldo,
            "version_anterior": (version_anterior or {}).get("actualizada"),
        }
        # Identidad del MUNDO (P1.1). Se anade al final y es puramente aditiva:
        # `dataset_id` se calcula arriba desde `manifiesto["secciones"]` y NO
        # depende de esta clave, asi que el identificador del dataset no cambia.
        # No es identidad del ESTADO: esa sigue sin resolverse (ver P1, §20).
        identidad_mundo.anadir_a_registro(
            registro,
            identidad_mundo.desde_export(
                (entradas.get("legends_plus.xml") or {}).get("ruta")))
        escribir_version(registro, raiz_datos)

        info(f"datos actualizados en {time.time() - t0:.1f}s")
        # El staging ya cumplio su funcion: `merged` salio de ahi y el resto son
        # copias de trabajo. Se borra para no dejar basura (las copias que
        # importan estan en `backups/`).
        shutil.rmtree(staging_dir, ignore_errors=True)
        return {"activado": True, "merged_nuevo": destino_merged,
                "backup": respaldo, "entradas": entradas, "resumen": r,
                "conteos": humo, "manifiesto": manifiesto, "registro": registro,
                "dataset_id": registro["dataset_id"]}

    except Exception:
        # Cualquier fallo: el staging se borra y la version activa no se toca.
        if dejar_staging:
            print(f"   staging conservado para depurar: {staging_dir}")
        else:
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise
# =============================================================================
# Interfaz de linea de comandos
# =============================================================================
def cmd_estado(raiz_datos=None):
    """Muestra el estado de los datos: fecha, hashes de entrada y conteos."""
    raiz = raiz_datos or DATA_ROOT
    merged = os.path.join(raiz, "processed", "merged")
    cabecera("ESTADO DE LOS DATOS")
    info(f"raiz de datos : {raiz}")
    info(f"version activa: {merged}")

    version = leer_version(raiz)
    print("\n  Ultima actualizacion")
    if not version:
        info("todavia no hay registro (se genero con integrar_legends.py)")
    else:
        ok(f"actualizada: {version.get('actualizada')}")
        anterior = version.get("version_anterior")
        if anterior:
            info(f"version anterior: {anterior}")
        for nombre, meta in (version.get("entradas") or {}).items():
            info(f"entrada {nombre:<18} sha256 {meta['sha256'][:32]}...")

        # Identidad del MUNDO (P1.1). Es informacion, no una garantia: por
        # diseño se imprime aunque falte, con el motivo de la ausencia.
        mundo = version.get("mundo") or {}
        if mundo:
            print("\n  Identidad del mundo (NO es identidad del estado)")
            info(f"world_name   : {mundo.get('world_name')}")
            info(f"world_folder : {mundo.get('world_folder')}")
            for clave in ("world_name", "world_folder"):
                por_que = mundo.get(f"{clave}_ausente_porque")
                if por_que:
                    info(f"  {clave} ausente: {por_que}")

    print("\n  Ficheros de entrada ahora mismo")
    for nombre in ENTRADAS:
        ruta = os.path.join(raiz, "original_data", nombre)
        if os.path.isfile(ruta):
            info(f"{nombre:<20} {humano(os.path.getsize(ruta))} B  "
                 f"sha256 {sha256_de(ruta)[:32]}...")
        else:
            fallo(f"{nombre} no existe")

    print("\n  Conteos de la version activa")
    if not os.path.isdir(merged):
        fallo("no hay dataset: ejecuta 'actualizar'")
        return 1
    conteos = {}
    for sec in ("historical_figures", "entities", "sites", "historical_events",
                "artifacts", "historical_event_relationships"):
        ruta = os.path.join(merged, f"{sec}.jsonl")
        if not os.path.isfile(ruta):
            conteos[sec] = 0
            continue
        n = 0
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    n += 1
        conteos[sec] = n
    for sec, n in conteos.items():
        info(f"{sec:<38} {humano(n)}")

    print("\n  Manifiesto de hashes")
    verificar_hashes(merged)
    ok("la version activa coincide con _hashes.json")

    print("\n  Copias de seguridad")
    backups = listar_backups(os.path.join(raiz, "backups"))
    if not backups:
        info("ninguna")
    for nombre, _ in backups:
        info(nombre)
    return 0


def cmd_historial(raiz_datos=None):
    raiz = raiz_datos or DATA_ROOT
    cabecera("HISTORIAL DE ACTUALIZACIONES")
    version = leer_version(raiz)
    if version:
        ok(f"version activa: {version.get('actualizada')}")
        for nombre, meta in (version.get("entradas") or {}).items():
            info(f"{nombre:<20} {meta['sha256'][:40]}...")
    else:
        info("sin registro de version")
    print()
    backups = listar_backups(os.path.join(raiz, "backups"))
    if not backups:
        info("sin copias de seguridad")
        return 0
    for i, (nombre, ruta) in enumerate(backups):
        n = len([f for f in os.listdir(ruta) if f.endswith(".jsonl")])
        info(f"[{i}] {nombre}  ({n} secciones)")
    return 0
def cmd_recuperar(args):
    raiz = getattr(args, "raiz_datos", None) or DATA_ROOT
    merged = os.path.join(raiz, "processed", "merged")
    cabecera("RECUPERANDO UNA COPIA ANTERIOR")
    r = recuperar(merged, args.indice, os.path.join(raiz, "backups"))
    ok(f"restaurada la copia: {r['recuperada']}")
    if r["apartada"]:
        info(f"la version sustituida queda en: {r['apartada']}")
    verificar_hashes(merged)
    print("\n  Reinicia la API para servir estos datos:  python run.py")
    return 0


def cmd_actualizar(args):
    raiz = getattr(args, "raiz_datos", None) or DATA_ROOT
    merged = os.path.join(raiz, "processed", "merged")
    origenes = args.originales or os.path.join(raiz, "original_data")
    try:
        r = actualizar(
            origenes=origenes,
            raiz_proyecto=getattr(args, "raiz_proyecto", None),
            activar_nuevo=not args.sin_activar,
            dejar_staging=args.dejar_staging,
            raiz_datos=raiz,
            merged_destino=merged,
            work_root=os.path.join(raiz, "work"),
            backups_root=os.path.join(raiz, "backups"),
        )
    except ErrorActualizacion as exc:
        print()
        fallo(str(exc))
        print()
        info("La version activa NO se ha modificado.")
        print()
        cabecera("ACTUALIZACION CANCELADA")
        return 1

    print()
    cabecera("ACTUALIZACION CORRECTA")
    if r["activado"]:
        ok("la nueva version esta activa")
        if r.get("dataset_id"):
            ok(f"dataset activo: {r['dataset_id']}")
        if r.get("backup"):
            info(f"respaldo de la anterior: {r['backup']}")
        print()
        # El dataset ya esta en disco. Lo que falta es que un proceso de API
        # que ya estaba en marcha deje de servir el anterior. Se dice
        # exactamente eso, con el comando, en lugar de un "reinicia la API".
        cabecera("SIGUIENTE PASO")
        info("Si la API esta ABAJO, terminada y vuelve a arrancar:  python run.py")
        info("Si la API esta EN MARCHA, sigue sirviendo el dataset ANTERIOR:")
        info("  cierrala (Ctrl+C) y arranca de nuevo:  python run.py")
        print()
        info("La web avisara del cambio al recargar. No hace falta nada mas.")
    else:
        ok("version generada y validada, pero NO activada")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="actualizar_datos.py",
        description="Actualizacion manual de los datos de DF Legends.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  python 00_SOURCE/tools/actualizar_datos.py estado
  python 00_SOURCE/tools/actualizar_datos.py actualizar
  python 00_SOURCE/tools/actualizar_datos.py actualizar --sin-activar
  python 00_SOURCE/tools/actualizar_datos.py recuperar --indice 0
  python 00_SOURCE/tools/actualizar_datos.py historial
""")
    sub = ap.add_subparsers(dest="orden", required=True)

    def comun(p):
        p.add_argument("--raiz-datos", dest="raiz_datos", default=None,
                       help=argparse.SUPPRESS)
        return p

    comun(sub.add_parser("estado", help="estado actual de los datos"))
    comun(sub.add_parser("historial", help="versiones y copias disponibles"))
    p_act = comun(sub.add_parser("actualizar", help="generar y activar datos"))
    p_act.add_argument("--sin-activar", action="store_true",
                       help="genera y valida, pero no cambia la version activa")
    p_act.add_argument("--originales", default=None,
                       help="carpeta con legends.xml y legends_plus.xml")
    p_act.add_argument("--raiz-proyecto", dest="raiz_proyecto", default=None,
                       help=argparse.SUPPRESS)
    p_act.add_argument("--dejar-staging", action="store_true",
                       help="no borra el staging al fallar (para depurar)")
    p_rec = comun(sub.add_parser("recuperar", help="volver a una copia anterior"))
    p_rec.add_argument("--indice", type=int, default=0,
                       help="0 = la copia mas reciente")

    args = ap.parse_args(argv)
    if args.orden == "estado":
        return cmd_estado(args.raiz_datos)
    if args.orden == "historial":
        return cmd_historial(args.raiz_datos)
    if args.orden == "recuperar":
        return cmd_recuperar(args)
    return cmd_actualizar(args)


if __name__ == "__main__":
    sys.exit(main())