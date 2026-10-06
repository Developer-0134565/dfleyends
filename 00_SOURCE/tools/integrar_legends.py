#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Integrador de los dos exports de Legends
=========================================================

Integra `legends.xml` (fuente primaria) y `legends_plus.xml` (complementaria)
en `00_SOURCE/processed/`, separando claramente el origen de cada dato.

REGLAS DE MERGE (verificadas contra los XML, sin inventar datos):
  * `legends.xml` es la fuente PRIMARIA. Sus campos nunca se pierden.
  * `legends_plus.xml` es COMPLEMENTARIA.
  * Un campo vacío en `legends_plus.xml` NUNCA pisa un valor de `legends.xml`.
  * Un valor de `legends.xml` NUNCA se descarta por no existir en plus.
  * Si ambos traen un campo con VALORES DIFERENTES y ambos no vacíos, se
    conservan los dos y se registra un CONFLICTO explícito.
  * Cada campo lleva `source` y `source_section`.

Sobre los 13.192 eventos:
  Los ids ausentes en `historical_events` NO se inventan ni se insertan.
  Los `historical_event_relationships` de plus se guardan como sección
  RELACIONADA aparte, con clave foránea al id de evento.
"""
import os
import sys
import json
import shutil
import hashlib
import collections
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402
from cargar_legends import cargar_legends, id_de_entrada, FACT, DERIVED  # noqa: E402

# Rutas centralizadas. NOTA: `verificar_reproducibilidad.py` reasigna estas
# variables de modulo para reconstruir el pipeline en un temporal; los nombres
# NO deben cambiar.
BASE = rutas.PROJECT_ROOT
SRC = rutas.DATA_ROOT
ORIG_DIR = rutas.ORIGINAL_DATA_ROOT
PROC = rutas.PROCESSED_ROOT
PROC_LEGENDS = rutas.LEGENDS_ROOT
PROC_PLUS = rutas.PLUS_ROOT
PROC_MERGED = rutas.MERGED_ROOT

# Rutas REALES de los originales (verificadas por inspección, no inventadas).
# Por defecto se usan las copias YA REGISTRADAS en original_data/: así el
# pipeline es reejecutable sin depender de descargas ni del directorio de la
# partida. `verificar_reproducibilidad.py` las sobrescribe con su temporal.
ORIG_LEGENDS = os.path.join(ORIG_DIR, "legends.xml")
ORIG_PLUS = os.path.join(ORIG_DIR, "legends_plus.xml")

SRC_LEGENDS = "legends.xml"
SRC_PLUS = "legends_plus.xml"

# Secciones que solo existen en legends.xml (fuente primaria). Se vuelcan en
# merged/ tal cual, sin mezclarlas con plus: plus las tiene vacías.
PRIMARIAS_SOLO = ("historical_events", "historical_event_collections",
                  "historical_eras")

COMPARTIDAS = ("regions", "underground_regions", "sites", "artifacts",
               "historical_figures", "entity_populations", "entities",
               "written_contents", "poetic_forms", "musical_forms",
               "dance_forms", "world_constructions")


def sha256_de(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def registrar_original(origen, destino_nombre):
    """Copia el original a original_data/ de forma idempotente.

    NO sobrescribe nunca: si ya existe, compara hashes y conserva la copia.
    """
    os.makedirs(ORIG_DIR, exist_ok=True)
    destino = os.path.join(ORIG_DIR, destino_nombre)
    h_origen = sha256_de(origen)
    est = {"origen": origen, "destino": destino, "sha256_origen": h_origen,
           "bytes": os.path.getsize(origen)}
    if not os.path.exists(destino):
        shutil.copy2(origen, destino)
        h_dest = sha256_de(destino)
        est.update(accion="copiado", sha256_destino=h_dest,
                   identique=(h_dest == h_origen))
        if not est["identique"]:
            raise RuntimeError(f"La copia de {destino_nombre} no coincide byte a byte")
    else:
        h_dest = sha256_de(destino)
        est.update(accion="ya existía (NO sobrescrito)", sha256_destino=h_dest,
                   identique=(h_dest == h_origen))
        if h_dest != h_origen:
            est["aviso"] = ("el original de origen cambió respecto a la copia "
                            "guardada; se conserva la copia existente")
    return est


def _vacio(v):
    return v is None or (isinstance(v, str) and v.strip() in ("", "unknown"))


def _campos(elemento, ruta=""):
    """Aplana un elemento a {ruta_punteada: texto}. Las hojas se guardan."""
    if len(elemento) == 0:
        return {ruta or elemento.tag: (elemento.text or "").strip()}
    out = {}
    for hijo in elemento:
        out.update(_campos(hijo, f"{ruta}.{hijo.tag}" if ruta else hijo.tag))
    return out


def _equivale_raw_legible(a, b):
    """¿Un token raws y su forma legible son el mismo valor?

    Ej.: 'COLOSSUS_BRONZE' -> 'colossus bronze' == 'bronze colossus'?  No siempre:
    el orden puede cambiar. Se comparan como CONJUNTO DE PALABRAS.
    Solo se usa para CLASIFICAR un conflicto ya existente; nunca para descartar
    ni para elegir un valor.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    pa = set(a.lower().replace("_", " ").split())
    pb = set(b.lower().replace("_", " ").split())
    return bool(pa) and pa == pb


def fusionar_registro(prim, sec, record_id):
    """Fusiona campos de dos fuentes. Devuelve (campos, conflictos)."""
    fusion, conflictos = {}, []
    sec_nombre = prim["_section"]
    plus_nombre = sec["_section"]

    for k, v in prim.items():
        if k.startswith("_"):
            continue
        val = {"valor": v, "source": SRC_LEGENDS, "source_section": sec_nombre}
        if _vacio(v):
            if k in sec and not _vacio(sec[k]):
                fusion[k] = {"valor": sec[k], "source": SRC_PLUS,
                             "source_section": plus_nombre}
            else:
                fusion[k] = val
        elif k not in sec or _vacio(sec[k]):
            fusion[k] = val
        elif sec[k] == v:
            val["tambien_en_plus"] = True
            fusion[k] = val
        else:
            val["conflicto"] = True
            fusion[k] = val
            entrada = {
                "campo": k, "record_id": record_id,
                "valor_legends_xml": v, "valor_legends_plus_xml": sec[k],
                "seccion_plus": plus_nombre,
            }
            if _equivale_raw_legible(v, sec[k]):
                # Mismo dato en dos notaciones (token raws vs nombre legible).
                entrada["tipo"] = "notacion_equivalente"
                entrada["certidumbre"] = DERIVED
                entrada["resolucion"] = (
                    "Mismo valor en dos notaciones; se conservan ambos. "
                    "legends.xml aporta el token raws original")
            else:
                entrada["tipo"] = "conflicto_real"
                entrada["certidumbre"] = FACT
                entrada["resolucion"] = (
                    "Valores distintos; se conservan ambos sin elegir")
            conflictos.append(entrada)
    for k, v in sec.items():
        if k.startswith("_") or k in fusion or _vacio(v):
            continue
        fusion[k] = {"valor": v, "source": SRC_PLUS, "source_section": plus_nombre}
    return fusion, conflictos
def _escribir_jsonl(ruta, filas):
    with open(ruta, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def _volcar(entradas, seccion, origen):
    filas = []
    for el in entradas:
        rid, dfid, cert = id_de_entrada(el, seccion)
        campos = _campos(el)
        campos.pop("id", None)
        filas.append({
            "record_id": rid, "df_id": dfid, "certainty": cert,
            "source": origen, "source_section": seccion, "campos": campos,
        })
    return filas


def integrar():
    ahora = datetime.now(timezone.utc).isoformat()

    print("[1/7] Registrando originales en original_data/ ...")
    reg = {
        "legends.xml": registrar_original(ORIG_LEGENDS, "legends.xml"),
        "legends_plus.xml": registrar_original(ORIG_PLUS, "legends_plus.xml"),
    }
    for n, e in reg.items():
        print(f"      {n}: {e['accion']} | idéntico={e['identique']}")

    print("[2/7] Cargando XML (codificación autodetectada) ...")
    rl, rp = cargar_legends(ORIG_LEGENDS), cargar_legends(ORIG_PLUS)
    info_l, info_p = rl.resumen(), rp.resumen()
    print(f"      legends.xml      -> {info_l['codificacion_detectada']} "
          f"| {info_l['total_entradas']:,} entradas")
    print(f"      legends_plus.xml -> {info_p['codificacion_detectada']} "
          f"| {info_p['total_entradas']:,} entradas")
    if rl.error or rp.error:
        raise RuntimeError(f"Error de parseo: {rl.error or rp.error}")
    if info_l["raiz"] != "df_world" or info_p["raiz"] != "df_world":
        raise RuntimeError("Se esperaba raíz <df_world> en ambos archivos")
    sec_l, sec_p = rl.secciones(), rp.secciones()

    print("[3/7] Volcando processed/from_legends_xml/ ...")
    os.makedirs(PROC_LEGENDS, exist_ok=True)
    conteo_l = {}
    for sec, ents in sec_l.items():
        filas = _volcar(ents, sec, SRC_LEGENDS)
        _escribir_jsonl(os.path.join(PROC_LEGENDS, f"{sec}.jsonl"), filas)
        conteo_l[sec] = len(filas)

    print("[4/7] Volcando processed/from_legends_plus/ ...")
    os.makedirs(PROC_PLUS, exist_ok=True)
    conteo_p = {}
    for sec, ents in sec_p.items():
        filas = _volcar(ents, sec, SRC_PLUS)
        _escribir_jsonl(os.path.join(PROC_PLUS, f"{sec}.jsonl"), filas)
        conteo_p[sec] = len(filas)

    print("[5/7] Fusionando en processed/merged/ ...")
    os.makedirs(PROC_MERGED, exist_ok=True)
    conflictos_total = []
    resumen_merge = {}
    n_fusionados = n_solo_prim = n_solo_sec = 0

    # Secciones exclusivas de legends.xml: se copian tal cual a merged/.
    for sec in PRIMARIAS_SOLO:
        filas = []
        for el in sec_l.get(sec, []):
            rid, dfid, cert = id_de_entrada(el, sec)
            campos = _campos(el)
            campos.pop("id", None)
            filas.append({
                "record_id": rid, "df_id": dfid, "certainty": cert,
                "source": SRC_LEGENDS, "source_section": sec,
                "sources": [SRC_LEGENDS], "en_legends_xml": True,
                "en_legends_plus": False,
                "campos": {k: {"valor": v, "source": SRC_LEGENDS,
                               "source_section": sec} for k, v in campos.items()},
                "conflictos": [],
            })
            n_solo_prim += 1
        _escribir_jsonl(os.path.join(PROC_MERGED, f"{sec}.jsonl"), filas)
        resumen_merge[sec] = {"total": len(filas), "conflictos": 0,
                              "nota": "exclusiva de legends.xml; plus la tiene vacía"}

    for sec in sorted(set(sec_l) & set(COMPARTIDAS)):
        idx_p = {}
        for el in sec_p.get(sec, []):
            _, dfid, _ = id_de_entrada(el, sec)
            if dfid is not None:
                idx_p[dfid] = el
        ids_l = {id_de_entrada(e, sec)[1] for e in sec_l[sec]}

        filas, n_conf = [], 0
        for el in sec_l[sec]:
            rid, dfid, _ = id_de_entrada(el, sec)
            prim = _campos(el)
            prim["_section"] = sec
            prim.pop("id", None)
            otro = idx_p.get(dfid) if dfid is not None else None
            if otro is None:
                n_solo_prim += 1
                campos = {k: {"valor": v, "source": SRC_LEGENDS,
                              "source_section": sec}
                          for k, v in prim.items() if not k.startswith("_")}
                filas.append({
                    "record_id": rid, "df_id": dfid, "certainty": FACT,
                    "source": SRC_LEGENDS, "source_section": sec,
                    "sources": [SRC_LEGENDS], "en_legends_xml": True,
                    "en_legends_plus": False, "campos": campos, "conflictos": []})
                continue
            sp = _campos(otro)
            sp["_section"] = sec
            sp.pop("id", None)
            campos, conf = fusionar_registro(prim, sp, rid)
            n_conf += len(conf)
            conflictos_total.extend(conf)
            n_fusionados += 1
            filas.append({
                "record_id": rid, "df_id": dfid, "certainty": FACT,
                "source": SRC_LEGENDS, "source_section": sec,
                "sources": [SRC_LEGENDS, SRC_PLUS], "en_legends_xml": True,
                "en_legends_plus": True, "campos": campos, "conflictos": conf})

        for el in sec_p.get(sec, []):
            rid, dfid, _ = id_de_entrada(el, sec)
            if dfid is not None and dfid not in ids_l:
                n_solo_sec += 1
                c = _campos(el)
                c.pop("id", None)
                campos = {k: {"valor": v, "source": SRC_PLUS, "source_section": sec}
                          for k, v in c.items() if not _vacio(v)}
                filas.append({
                    "record_id": rid, "df_id": dfid, "certainty": FACT,
                    "source": SRC_PLUS, "source_section": sec,
                    "sources": [SRC_PLUS], "en_legends_xml": False,
                    "en_legends_plus": True, "campos": campos, "conflictos": []})

        _escribir_jsonl(os.path.join(PROC_MERGED, f"{sec}.jsonl"), filas)
        resumen_merge[sec] = {"total": len(filas), "conflictos": n_conf}
# ---- eventos: los 13.192 ids ausentes NO se materializan -------------
    print("[6/7] Estructura de relaciones (SIN inventar eventos) ...")
    eventos = sec_l.get("historical_events", [])
    ids_evento = {e.findtext("id") for e in eventos if e.findtext("id")}
    nums = sorted(int(x) for x in ids_evento)
    ausentes = set(range(nums[0], nums[-1] + 1)) - set(nums)

    filas_rel, enlazadas, sueltas = [], 0, 0
    for i, el in enumerate(sec_p.get("historical_event_relationships", [])):
        ev = el.findtext("event")
        existe = ev in ids_evento if ev else False
        enlazadas += existe
        sueltas += not existe
        filas_rel.append({
            "record_id": f"her:{ev}:{i}", "event_id": ev,
            "event_existe_en_historical_events": existe, "certainty": FACT,
            "source": SRC_PLUS, "source_section": "historical_event_relationships",
            "campos": {k: {"valor": v, "source": SRC_PLUS,
                           "source_section": "historical_event_relationships"}
                       for k, v in _campos(el).items()}})
    _escribir_jsonl(os.path.join(PROC_MERGED, "historical_event_relationships.jsonl"),
                    filas_rel)

    filas_sup = []
    for i, el in enumerate(sec_p.get("historical_event_relationship_supplements", [])):
        ev = el.findtext("event")
        filas_sup.append({
            "record_id": f"sup:{ev}:{i}", "event_id": ev,
            "event_existe_en_historical_events": ev in ids_evento if ev else False,
            "certainty": FACT, "source": SRC_PLUS,
            "source_section": "historical_event_relationship_supplements",
            "campos": {k: {"valor": v, "source": SRC_PLUS,
                           "source_section": "historical_event_relationship_supplements"}
                       for k, v in _campos(el).items()}})
    _escribir_jsonl(os.path.join(PROC_MERGED,
                                 "historical_event_relationship_supplements.jsonl"),
                    filas_sup)

    # Índice evento -> relaciones -> figuras (consulta posterior)
    idx = collections.defaultdict(lambda: {"relaciones": [], "figuras": set(),
                                           "supplements": 0})
    for f in filas_rel:
        e = idx[f["event_id"]]
        e["relaciones"].append({
            "tipo": f["campos"].get("relationship", {}).get("valor"),
            "source_hf": f["campos"].get("source_hf", {}).get("valor"),
            "target_hf": f["campos"].get("target_hf", {}).get("valor"),
            "year": f["campos"].get("year", {}).get("valor"),
            "source": SRC_PLUS})
        for k in ("source_hf", "target_hf"):
            v = f["campos"].get(k, {}).get("valor")
            if v is not None:
                e["figuras"].add(v)
    for f in filas_sup:
        idx[f["event_id"]]["supplements"] += 1

    with open(os.path.join(PROC_MERGED, "indice_evento_relaciones.json"), "w",
              encoding="utf-8") as f:
        json.dump({
            "certainty": DERIVED,
            "nota": ("Índice derivado por cruce de claves; los registros base "
                     "permanecen FACT en historical_event_relationships.jsonl"),
            "generado": ahora,
            "eventos_con_relaciones": len(idx),
            "entradas": {k: {"relaciones": v["relaciones"],
                             "figuras_implicadas": sorted(v["figuras"]),
                             "supplements": v["supplements"]}
                         for k, v in sorted(idx.items(),
                                            key=lambda x: (x[0] is None, x[0]))},
        }, f, ensure_ascii=False, indent=1)

    print(f"      relationships: {len(filas_rel):,} | enlazadas: {enlazadas} "
          f"| sin evento en historical_events: {sueltas}")
    print(f"      supplements: {len(filas_sup):,} | índice: {len(idx):,} eventos")

    print("[7/7] Escribiendo manifiesto ...")
    manifiesto = {
        "generado": ahora,
        "certainties": {
            "FACT": "valor presente directamente en el XML de origen",
            "DERIVED": "valor calculado a partir de los XML (p.ej. índices)",
            "INTERPRETATION": "no se genera en esta fase",
            "UNKNOWN": "no determinado",
        },
        "originales": reg,
        "lectura": {"legends.xml": info_l, "legends_plus.xml": info_p},
        "entradas_por_seccion": {"legends.xml": conteo_l, "legends_plus.xml": conteo_p},
        "merge": {
            "resumen_por_seccion": resumen_merge,
            "registros_fusionados": n_fusionados,
            "solo_en_legends_xml": n_solo_prim,
            "solo_en_legends_plus_xml": n_solo_sec,
            "divergencias_totales": len(conflictos_total),
            "divergencias_por_tipo": dict(collections.Counter(
                c.get("tipo", "conflicto_real") for c in conflictos_total)),
            "conflictos_reales": sum(
                1 for c in conflictos_total if c.get("tipo") == "conflicto_real"),
            "notaciones_equivalentes": sum(
                1 for c in conflictos_total
                if c.get("tipo") == "notacion_equivalente"),
            "nota": ("Ambas categorías conservan los dos valores y registran su "
                     "procedencia; ninguna se resuelve en silencio."),
            "divergencias_por_campo": dict(collections.Counter(
                f"{c.get('campo')} [{c.get('tipo', 'conflicto_real')}]"
                for c in conflictos_total)),
            "divergencias_detalle": conflictos_total[:500],
        },
        "eventos": {
            "historical_events": len(eventos),
            "ids_ausentes_en_historical_events": len(ausentes),
            "historical_event_relationships": len(filas_rel),
            "relationships_enlazadas": enlazadas,
            "relationships_sin_evento_en_historical_events": sueltas,
            "supplements": len(filas_sup),
            "politica": ("Los ids ausentes NO se materializan como eventos; los "
                         "relationships se conservan como sección relacionada."),
        },
        "salidas": {"from_legends_xml": PROC_LEGENDS, "from_legends_plus": PROC_PLUS,
                    "merged": PROC_MERGED},
    }
    with open(os.path.join(PROC_MERGED, "_manifiesto.json"), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=1)
    return manifiesto


if __name__ == "__main__":
    m = integrar()
    mg = m["merge"]
    print("\n[OK] Integración completada.")
    print(f"     Divergencias totales : {mg['divergencias_totales']}")
    print(f"       - notación equivalente: {mg['notaciones_equivalentes']}")
    print(f"       - conflicto real       : {mg['conflictos_reales']}")
    print(f"     Manifiesto: {os.path.join(PROC_MERGED, '_manifiesto.json')}")
