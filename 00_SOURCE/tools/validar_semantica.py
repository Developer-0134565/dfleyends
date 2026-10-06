#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Validador semántico
====================================

VALIDACIÓN, no generación. Este módulo NO crea crónicas, lore, rankings ni
interpretaciones. Solo comprueba, con datos reales, que la información
integrada permite responder de forma ESTRUCTURADA sobre el mundo.

Niveles de certeza usados:
    FACT         -> el valor aparece directamente en el XML
    DERIVED      -> relación o conteo calculado mecánicamente sobre FACT
    INTERPRETATION -> no se genera aquí
    UNKNOWN      -> no determinable con los datos disponibles

REGLAS ESTRICTAS:
  * Los XML originales no se abren para escritura. Este módulo lee ÚNICAMENTE
    los JSONL ya procesados en processed/.
  * `-1` es un valor centinela de Dwarf Fortress que significa "sin dato".
    Se trata como ausente, nunca como un id válido.
  * No se inventa ninguna posición, nombre ni relación.
  * Un dato que no exista se marca UNKNOWN; no se rellena por inferencia.
"""
import os
import sys
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402

# Rutas centralizadas: ningun modulo vuelve a escribir una ruta absoluta.
BASE = rutas.DATA_ROOT
PROC = rutas.PROCESSED_ROOT
MERGED = rutas.MERGED_ROOT
PLUS = rutas.PLUS_ROOT
VALID = rutas.VALIDATION_ROOT
MANIFEST = rutas.MANIFEST_PATH

SENTINELA = "-1"          # centinela de DF para "sin dato"
NO_DATA = {"-1", "", "unknown"}

FACT = "FACT"
DERIVED = "DERIVED"
INTERPRETATION = "INTERPRETATION"
UNKNOWN = "UNKNOWN"


# --------------------------------------------------------------------------
# Carga de datos procesados
# --------------------------------------------------------------------------
def cargar_jsonl(nombre, carpeta=MERGED):
    """Lee un JSONL. Devuelve lista de registros."""
    ruta = os.path.join(carpeta, nombre + ".jsonl")
    if not os.path.exists(ruta):
        return []
    out = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                out.append(json.loads(linea))
    return out


def v(reg, campo, default=None):
    """Valor de un campo, tolerando ambos formatos de 'campos'.

    merged/     -> {campo: {'valor':..., 'source':..., 'source_section':...}}
    from_*/     -> {campo: 'texto plano'}
    """
    c = reg.get("campos") or {}
    m = c.get(campo)
    if m is None:
        return default
    if isinstance(m, dict):
        return m.get("valor", default)
    return m


def valido(x):
    """¿Es un valor usable (no centinela, no vacío)?"""
    if x is None:
        return False
    s = str(x).strip()
    return s not in NO_DATA


def como_int(x):
    try:
        return int(str(x).strip())
    except (TypeError, ValueError):
        return None


def sin_dato(x):
    """Devuelve None si el valor es centinela o no numérico."""
    i = como_int(x)
    if i is None or i < 0:
        return None
    return i


def coords_primeras(texto):
    """'9,110' -> (9,110); 'a,b|c,d|' -> ((a,b),(c,d)); '-1,-1' -> None."""
    if not valido(texto):
        return []
    txt = str(texto)
    if txt in ("-1,-1", "-1"):
        return []
    pares = []
    for trozo in txt.split("|"):
        trozo = trozo.strip().strip(",")
        if not trozo or "," not in trozo:
            continue
        a, _, b = trozo.partition(",")
        ia, ib = como_int(a), como_int(b)
        if ia is not None and ib is not None and ia >= 0 and ib >= 0:
            pares.append((ia, ib))
    return pares
class Indice:
    """Índices de referencia cruzados sobre los datos procesados.

    Todos los índices se construyen mecánicamente a partir de FACT.
    Su existencia misma es DERIVED; los valores que indexan son FACT.
    """

    def __init__(self):
        self.figuras = {}
        self.entidades = {}
        self.sitios = {}
        self.eventos = {}
        self.artefactos = {}
        self.relaciones = []
        self.supplements = []
        self.collections = []
        self.eras = []
        self.identidades = []
        # índices inversos
        self.ev_por_hf = collections.defaultdict(list)
        self.ev_por_entidad = collections.defaultdict(list)
        self.ev_por_sitio = collections.defaultdict(list)
        self.hf_por_entidad = collections.defaultdict(list)
        self.hf_por_sitio = collections.defaultdict(list)
        self.ent_por_sitio = collections.defaultdict(list)
        self.art_por_hf = collections.defaultdict(list)
        self.art_por_sitio = collections.defaultdict(list)
        self.rel_por_hf = collections.defaultdict(list)
        self.rel_por_evento = collections.defaultdict(list)
        self.col_por_evento = collections.defaultdict(list)

    # ------------------------------------------------------------- carga
    def cargar(self):
        for r in cargar_jsonl("historical_figures"):
            self.figuras[r["df_id"]] = r
        for r in cargar_jsonl("entities"):
            self.entidades[r["df_id"]] = r
        for r in cargar_jsonl("sites"):
            self.sitios[r["df_id"]] = r
        for r in cargar_jsonl("historical_events"):
            self.eventos[r["df_id"]] = r
        for r in cargar_jsonl("artifacts"):
            self.artefactos[r["df_id"]] = r
        self.relaciones = cargar_jsonl("historical_event_relationships")
        self.supplements = cargar_jsonl("historical_event_relationship_supplements")
        self.collections = cargar_jsonl("historical_event_collections")
        self.eras = cargar_jsonl("historical_eras")
        self.identidades = cargar_jsonl("identities", PLUS)
        self._construir()
        return self

    # --------------------------------------------------------- índices
    # NOTA: todas las claves de índice se normalizan a TEXTO, porque
    # `df_id` en los JSONL es una cadena ("0", "1234"). Usar enteros aquí
    # rompería silenciosamente todas las referencias cruzadas.
    def _construir(self):
        # eventos -> hf / entidad / sitio
        for dfe, e in self.eventos.items():
            hfid = sin_dato(v(e, "hfid"))
            if hfid is not None:
                self.ev_por_hf[str(hfid)].append(dfe)
            cid = sin_dato(v(e, "civ_id"))
            if cid is not None:
                self.ev_por_entidad[str(cid)].append(dfe)
            sid = sin_dato(v(e, "site_id"))
            if sid is not None:
                self.ev_por_sitio[str(sid)].append(dfe)
            for g in ("group_1_hfid", "group_2_hfid", "target_hfid",
                      "hfid_target", "hist_figure_id", "group_hfid"):
                gid = sin_dato(v(e, g))
                if gid is not None:
                    self.ev_por_hf[str(gid)].append(dfe)

        # figuras -> entidad / sitio
        for dfh, f in self.figuras.items():
            el = sin_dato(v(f, "entity_link.entity_id"))
            if el is not None:
                self.hf_por_entidad[str(el)].append(dfh)
            sl = sin_dato(v(f, "site_link.site_id"))
            if sl is not None:
                self.hf_por_sitio[str(sl)].append(dfh)

        # sitios -> entidad / propietario
        for dfs, s in self.sitios.items():
            for campo in ("civ_id", "cur_owner_id"):
                cid = sin_dato(v(s, campo))
                if cid is not None:
                    self.ent_por_sitio[str(cid)].append(dfs)

        # artefactos -> figura / sitio
        for dfa, a in self.artefactos.items():
            h = sin_dato(v(a, "holder_hfid"))
            if h is not None:
                self.art_por_hf[str(h)].append(dfa)
            s = sin_dato(v(a, "site_id"))
            if s is not None:
                self.art_por_sitio[str(s)].append(dfa)

        # relaciones (plus) -> figuras / evento
        for rel in self.relaciones:
            ev = rel.get("event_id")
            if ev is not None:
                self.rel_por_evento[str(ev)].append(rel)
            for campo in ("source_hf", "target_hf"):
                h = sin_dato(v(rel, campo))
                if h is not None:
                    self.rel_por_hf[str(h)].append(rel)

        # collections -> evento
        for c in self.collections:
            ev = sin_dato(v(c, "event"))
            if ev is not None:
                self.col_por_evento[str(ev)].append(c)

    # -------------------------------------------------------------- años
    def anos(self, evento):
        """Año del evento, o None si no hay dato válido."""
        return sin_dato(v(evento, "year"))

    def eventos_ordenados(self, ids):
        return sorted(ids, key=lambda i: (self.anos(self.eventos[i]) or 0,
                                          como_int(v(self.eventos[i], "seconds72")) or 0))
class Consultas:
    """Consultas estructuradas sobre el índice. Solo FACT y DERIVED."""

    def __init__(self, indice):
        self.i = indice

    # ---- A: ¿Quién es esta figura? -------------------------------
    def ficha_figura(self, df_id):
        f = self.i.figuras.get(df_id)
        if f is None:
            return {"certainty": UNKNOWN, "motivo": "figura no encontrada"}
        ent = sin_dato(v(f, "entity_link.entity_id"))
        ent_rec = self.i.entidades.get(str(ent)) if ent is not None else None
        sit = sin_dato(v(f, "site_link.site_id"))
        sit_rec = self.i.sitios.get(str(sit)) if sit is not None else None
        return {
            "certainty": FACT,
            "df_id": df_id,
            "nombre": v(f, "name") if valido(v(f, "name")) else UNKNOWN,
            "race": v(f, "race") if valido(v(f, "race")) else UNKNOWN,
            "caste": v(f, "caste") if valido(v(f, "caste")) else UNKNOWN,
            "sexo": v(f, "sex") if valido(v(f, "sex")) else UNKNOWN,
            "nacimiento": {"año": sin_dato(v(f, "birth_year")),
                           "segundos72": sin_dato(v(f, "birth_seconds72"))},
            "muerte": {"año": sin_dato(v(f, "death_year")),
                       "segundos72": sin_dato(v(f, "death_seconds72"))},
            "entidad": {"df_id": ent,
                        "nombre": v(ent_rec, "name") if ent_rec else UNKNOWN,
                        "tipo": v(ent_rec, "type") if ent_rec else UNKNOWN},
            "sitio": {"df_id": sit,
                      "nombre": v(sit_rec, "name") if sit_rec else UNKNOWN},
            "relaciones_adicionales": self.relaciones_de(df_id),
            "enlaces": {"entidad": FACT, "sitio": FACT, "relaciones": FACT},
            "sources": f.get("sources", []),
        }

    def relaciones_de(self, df_hf):
        """Relaciones de legends_plus.xml que involucran a la figura."""
        out = []
        for rel in self.i.rel_por_hf.get(df_hf, []):
            src = sin_dato(v(rel, "source_hf"))
            tgt = sin_dato(v(rel, "target_hf"))
            otro = tgt if src == int(df_hf) else src
            out.append({
                "tipo": v(rel, "relationship"),
                "año": sin_dato(v(rel, "year")),
                "evento_id": rel.get("event_id"),
                "evento_presente": rel.get("event_existe_en_historical_events"),
                "otra_figura_id": otro,
                "otra_figura_nombre": (v(self.i.figuras[str(otro)], "name")
                                       if str(otro) in self.i.figuras else UNKNOWN),
                "certainty": FACT,
                "source": rel.get("source"),
            })
        return sorted(out, key=lambda x: (x["año"] is None, x["año"] or 0))

    # ---- B: ¿Qué acontecimientos conocemos de esta figura? ------
    def historia_figura(self, df_id, limite=None):
        ids = set(self.i.ev_por_hf.get(df_id, []))
        orden = self.i.eventos_ordenados([i for i in ids if i in self.i.eventos])
        if limite:
            orden = orden[:limite]
        ficha = self.ficha_figura(df_id)
        filas = []
        for eid in orden:
            e = self.i.eventos[eid]
            sid = sin_dato(v(e, "site_id"))
            s = self.i.sitios.get(str(sid)) if sid is not None else None
            cid = sin_dato(v(e, "civ_id"))
            ent = self.i.entidades.get(str(cid)) if cid is not None else None
            filas.append({
                "evento_id": eid,
                "año": self.i.anos(e),
                "segundos72": sin_dato(v(e, "seconds72")),
                "tipo": v(e, "type"),
                "subtipo": v(e, "subtype") if valido(v(e, "subtype")) else None,
                "estado": v(e, "state") if valido(v(e, "state")) else None,
                "causa": v(e, "cause") if valido(v(e, "cause")) else None,
                "sitio_id": sid,
                "sitio_nombre": v(s, "name") if s else UNKNOWN,
                "entidad_id": cid,
                "entidad_nombre": v(ent, "name") if ent else UNKNOWN,
                "certainty": FACT,
            })
        años = [f["año"] for f in filas if f["año"] is not None]
        return {
            "certainty": FACT,
            "figura": ficha,
            "total_eventos": len(ids),
            "eventos": filas,
            "lugares": sorted({f["sitio_nombre"] for f in filas
                               if f["sitio_nombre"] != UNKNOWN}),
            "entidades": sorted({f["entidad_nombre"] for f in filas
                                 if f["entidad_nombre"] != UNKNOWN}),
            "relaciones_adicionales": ficha["relaciones_adicionales"],
            "rango_anios": [min(años), max(años)] if años else UNKNOWN,
        }
# ---- C: ¿Qué ocurrió en este sitio? --------------------------
    def ficha_sitio(self, df_id):
        s = self.i.sitios.get(df_id)
        if s is None:
            return {"certainty": UNKNOWN, "motivo": "sitio no encontrado"}
        civ = sin_dato(v(s, "civ_id"))
        own = sin_dato(v(s, "cur_owner_id"))
        civ_r = self.i.entidades.get(str(civ)) if civ is not None else None
        own_r = self.i.entidades.get(str(own)) if own is not None else None
        crds = coords_primeras(v(s, "coords"))
        figs = self.i.hf_por_sitio.get(df_id, [])
        evs = [e for e in self.i.ev_por_sitio.get(df_id, []) if e in self.i.eventos]
        return {
            "certainty": FACT,
            "df_id": df_id,
            "nombre": v(s, "name") if valido(v(s, "name")) else UNKNOWN,
            "tipo": v(s, "type") if valido(v(s, "type")) else UNKNOWN,
            "coordenadas": crds if crds else UNKNOWN,
            "civilizacion": {"df_id": civ,
                             "nombre": v(civ_r, "name") if civ_r else UNKNOWN},
            "propietario_actual": {"df_id": own,
                                   "nombre": v(own_r, "name") if own_r else UNKNOWN},
            "figuras_asociadas": len(figs),
            "eventos": len(evs),
            "artefactos": len(self.i.art_por_sitio.get(df_id, [])),
            "construcciones": self.construcciones_en_sitio(crds),
            "sources": s.get("sources", []),
        }

    def construcciones_en_sitio(self, crds):
        """Construcciones de plus cuyas coordenadas tocan las del sitio.

        Enlace DERIVED por coincidencia exacta de la coordenada (x,y).
        """
        if not crds or crds == UNKNOWN:
            return []
        objetivo = set(crds)
        out = []
        for wc in cargar_jsonl("world_constructions", PLUS):
            cs = coords_primeras(v(wc, "coords"))
            comunes = objetivo & set(cs)
            if comunes:
                out.append({
                    "df_id": wc["df_id"], "nombre": v(wc, "name"),
                    "tipo": v(wc, "type"),
                    "coordenadas_comunes": sorted(comunes),
                    "certainty": DERIVED,
                    "metodo": "coincidencia exacta de coordenadas (x,y)",
                })
        return out

    # ---- D: ¿Qué acontecimientos ocurrieron entre dos fechas? ---
    def eventos_entre(self, anio_a, anio_b, limite=None):
        a, b = min(anio_a, anio_b), max(anio_a, anio_b)
        filas = []
        for eid, e in self.i.eventos.items():
            y = self.i.anos(e)
            if y is None or not (a <= y <= b):
                continue
            filas.append((y, como_int(v(e, "seconds72")) or 0, eid))
        filas.sort()
        total = len(filas)
        if limite:
            filas = filas[:limite]
        out = []
        for y, s, eid in filas:
            e = self.i.eventos[eid]
            out.append({
                "evento_id": eid, "año": y, "segundos72": s,
                "tipo": v(e, "type"),
                "subtipo": v(e, "subtype") if valido(v(e, "subtype")) else None,
                "hfid": sin_dato(v(e, "hfid")),
                "sitio_id": sin_dato(v(e, "site_id")),
                "entidad_id": sin_dato(v(e, "civ_id")),
                "certainty": FACT,
            })
        return {"certainty": FACT, "desde": a, "hasta": b,
                "total": total, "devueltos": len(out), "eventos": out}
# ---- E/F: participantes y relaciones de un evento ------------
    def ficha_evento(self, df_id):
        e = self.i.eventos.get(df_id)
        if e is None:
            return {"certainty": UNKNOWN, "motivo": "evento no encontrado"}
        hf = sin_dato(v(e, "hfid"))
        hf_r = self.i.figuras.get(str(hf)) if hf is not None else None
        tid = (sin_dato(v(e, "target_hfid")) or sin_dato(v(e, "hfid_target"))
               or sin_dato(v(e, "hist_figure_id")))
        cid = sin_dato(v(e, "civ_id"))
        ent_r = self.i.entidades.get(str(cid)) if cid is not None else None
        sid = sin_dato(v(e, "site_id"))
        s_r = self.i.sitios.get(str(sid)) if sid is not None else None
        return {
            "certainty": FACT, "df_id": df_id,
            "año": self.i.anos(e),
            "segundos72": sin_dato(v(e, "seconds72")),
            "tipo": v(e, "type"),
            "subtipo": v(e, "subtype") if valido(v(e, "subtype")) else None,
            "estado": v(e, "state") if valido(v(e, "state")) else None,
            "causa": v(e, "cause") if valido(v(e, "cause")) else None,
            "participantes": {
                "hfid": hf,
                "nombre": v(hf_r, "name") if hf_r else UNKNOWN,
                "objetivo_hfid": tid,
                "grupo_1_hfid": sin_dato(v(e, "group_1_hfid")),
                "grupo_2_hfid": sin_dato(v(e, "group_2_hfid")),
            },
            "entidad": {"df_id": cid,
                        "nombre": v(ent_r, "name") if ent_r else UNKNOWN,
                        "tipo": v(ent_r, "type") if ent_r else UNKNOWN},
            "sitio": {"df_id": sid, "nombre": v(s_r, "name") if s_r else UNKNOWN},
            "coordenadas": coords_primeras(v(e, "coords")) or UNKNOWN,
            "relaciones": self.relaciones_de_evento(df_id),
            "collections": self.collections_de_evento(df_id),
        }

    def relaciones_de_evento(self, df_id):
        out = []
        for rel in self.i.rel_por_evento.get(df_id, []):
            src = sin_dato(v(rel, "source_hf"))
            tgt = sin_dato(v(rel, "target_hf"))
            out.append({
                "tipo": v(rel, "relationship"),
                "año": sin_dato(v(rel, "year")),
                "source_hf": src, "target_hf": tgt,
                "source_nombre": (v(self.i.figuras[str(src)], "name")
                                  if str(src) in self.i.figuras else UNKNOWN),
                "target_nombre": (v(self.i.figuras[str(tgt)], "name")
                                  if str(tgt) in self.i.figuras else UNKNOWN),
                "certainty": FACT, "source": rel.get("source"),
            })
        return out

    def collections_de_evento(self, df_id):
        return [{"df_id": c["df_id"], "tipo": v(c, "type"),
                 "inicio": sin_dato(v(c, "start_year")),
                 "fin": sin_dato(v(c, "end_year")), "certainty": FACT}
                for c in self.i.col_por_evento.get(df_id, [])]
# ---- G: ¿Qué conocemos de esta entidad? ---------------------
    def ficha_entidad(self, df_id):
        e = self.i.entidades.get(df_id)
        if e is None:
            return {"certainty": UNKNOWN, "motivo": "entidad no encontrada"}
        evs = self.i.eventos_ordenados([x for x in
                                        self.i.ev_por_entidad.get(df_id, [])
                                        if x in self.i.eventos])
        return {
            "certainty": FACT, "df_id": df_id,
            "nombre": v(e, "name") if valido(v(e, "name")) else UNKNOWN,
            "tipo": v(e, "type") if valido(v(e, "type")) else UNKNOWN,
            "race": v(e, "race") if valido(v(e, "race")) else UNKNOWN,
            "figuras": len(self.i.hf_por_entidad.get(df_id, [])),
            "sitios": len(self.i.ent_por_sitio.get(df_id, [])),
            "eventos": len(evs),
            "posicion": (v(e, "entity_position.name")
                         if valido(v(e, "entity_position.name")) else UNKNOWN),
            "sources": e.get("sources", []),
        }

    def recursive_entidad(self, df_id):
        """Árbol de relaciones de una entidad. Enlace DERIVED, valores FACT."""
        evs = self.i.eventos_ordenados([x for x in
                                        self.i.ev_por_entidad.get(df_id, [])
                                        if x in self.i.eventos])
        return {
            "entidad": self.ficha_entidad(df_id),
            "figuras": [{"df_id": h, "nombre": v(self.i.figuras[h], "name"),
                         "eventos": len(self.i.ev_por_hf.get(h, [])),
                         "certainty": FACT}
                        for h in self.i.hf_por_entidad.get(df_id, [])[:25]],
            "total_figuras": len(self.i.hf_por_entidad.get(df_id, [])),
            "sitios": [{"df_id": s, "nombre": v(self.i.sitios[s], "name"),
                        "tipo": v(self.i.sitios[s], "type"), "certainty": FACT}
                       for s in self.i.ent_por_sitio.get(df_id, [])[:25]],
            "total_sitios": len(self.i.ent_por_sitio.get(df_id, [])),
            "eventos": [{"evento_id": e, "año": self.i.anos(self.i.eventos[e]),
                         "tipo": v(self.i.eventos[e], "type"), "certainty": FACT}
                        for e in evs[:25]],
            "total_eventos": len(evs),
        }

    # ---- H: ¿Qué sabemos de este artefacto? ---------------------
    def ficha_artefacto(self, df_id):
        a = self.i.artefactos.get(df_id)
        if a is None:
            return {"certainty": UNKNOWN, "motivo": "artefacto no encontrado"}
        h = sin_dato(v(a, "holder_hfid"))
        s = sin_dato(v(a, "site_id"))
        hr = self.i.figuras.get(str(h)) if h is not None else None
        sr = self.i.sitios.get(str(s)) if s is not None else None
        return {
            "certainty": FACT, "df_id": df_id,
            "nombre": v(a, "name") if valido(v(a, "name")) else UNKNOWN,
            "nombre_item": v(a, "item.name_string"),
            "tipo": v(a, "item_type") if valido(v(a, "item_type")) else UNKNOWN,
            "subtipo": v(a, "item_subtype") if valido(v(a, "item_subtype")) else None,
            "material": v(a, "mat") if valido(v(a, "mat")) else UNKNOWN,
            "es_escrito": valido(v(a, "writing")),
            "propietario_hfid": h,
            "propietario_nombre": v(hr, "name") if hr else UNKNOWN,
            "sitio_id": s,
            "sitio_nombre": v(sr, "name") if sr else UNKNOWN,
            "sources": a.get("sources", []),
        }
# ==========================================================================
# VALIDACIONES
# ==========================================================================

HUERFANO_LEGITIMO = "HUERFANO LEGITIMO"
REF_INCOMPLETA = "REFERENCIA INCOMPLETA"
REF_ROTA = "REFERENCIA ROTA"
DATOS_INSUFICIENTES = "DATOS INSUFICIENTES"


def validar_figuras(idx, cons):
    figs = idx.figuras
    total = len(figs)
    con_nombre = sum(1 for f in figs.values() if valido(v(f, "name")))
    sin_nombre = total - con_nombre
    con_race = sum(1 for f in figs.values() if valido(v(f, "race")))
    con_ent = sum(1 for f in figs.values()
                  if sin_dato(v(f, "entity_link.entity_id")) is not None)
    con_ev = sum(1 for k in figs if idx.ev_por_hf.get(k))
    multi_ev = sum(1 for k in figs if len(idx.ev_por_hf.get(k, [])) >= 2)
    con_rel = sum(1 for k in figs if idx.rel_por_hf.get(k))
    con_nombre_y_race = sum(
        1 for f in figs.values()
        if valido(v(f, "name")) and valido(v(f, "race")))
    # candidatas: nombre + entidad + >=2 eventos
    candidatas = [k for k, f in figs.items()
                  if valido(v(f, "name"))
                  and sin_dato(v(f, "entity_link.entity_id")) is not None
                  and len(idx.ev_por_hf.get(k, [])) >= 2]
    candidatas.sort(key=lambda k: (-len(idx.ev_por_hf.get(k, [])), k))
    return {
        "total": total, "con_nombre": con_nombre, "sin_nombre": sin_nombre,
        "con_race": con_race, "con_entidad": con_ent,
        "con_eventos": con_ev, "sin_eventos": total - con_ev,
        "con_multiples_eventos": multi_ev,
        "con_relaciones_plus": con_rel, "sin_relaciones_plus": total - con_rel,
        "con_nombre_y_race": con_nombre_y_race,
        "candidatas": candidatas,
    }


def validar_entidades(idx, cons):
    ent = idx.entidades
    total = len(ent)
    con_nombre = sum(1 for e in ent.values() if valido(v(e, "name")))
    con_figs = sum(1 for k in ent if idx.hf_por_entidad.get(k))
    con_sitios = sum(1 for k in ent if idx.ent_por_sitio.get(k))
    con_evs = sum(1 for k in ent if idx.ev_por_entidad.get(k))
    tipos = collections.Counter(v(e, "type") for e in ent.values()
                                if valido(v(e, "type")))
    # candidatas: tipo civilization + nombre + figuras + eventos
    cid_cands = [k for k, e in ent.items()
                 if v(e, "type") == "civilization" and valido(v(e, "name"))
                 and idx.hf_por_entidad.get(k) and idx.ev_por_entidad.get(k)]
    cid_cands.sort(key=lambda k: (-len(idx.ev_por_entidad.get(k, [])), k))
    return {
        "total": total, "con_nombre": con_nombre,
        "con_figuras": con_figs, "con_sitios": con_sitios,
        "con_eventos": con_evs, "tipos": dict(tipos),
        "civilizaciones": tipos.get("civilization", 0),
        "candidatas_civilizacion": cid_cands,
    }


def validar_sitios(idx, cons):
    sit = idx.sitios
    total = len(sit)
    con_nombre = sum(1 for s in sit.values() if valido(v(s, "name")))
    con_coords = sum(1 for s in sit.values()
                     if coords_primeras(v(s, "coords")))
    con_tipo = sum(1 for s in sit.values() if valido(v(s, "type")))
    con_civ = sum(1 for s in sit.values() if sin_dato(v(s, "civ_id")) is not None)
    con_figs = sum(1 for k in sit if idx.hf_por_sitio.get(k))
    con_evs = sum(1 for k in sit if idx.ev_por_sitio.get(k))
    con_arts = sum(1 for k in sit if idx.art_por_sitio.get(k))
    tipos = collections.Counter(v(s, "type") for s in sit.values()
                                if valido(v(s, "type")))
    cands = [k for k, s in sit.items()
             if valido(v(s, "name")) and coords_primeras(v(s, "coords"))
             and sin_dato(v(s, "civ_id")) is not None and idx.ev_por_sitio.get(k)]
    cands.sort(key=lambda k: (-len(idx.ev_por_sitio.get(k, [])), k))
    return {
        "total": total, "con_nombre": con_nombre, "con_coordenadas": con_coords,
        "con_tipo": con_tipo, "con_civilizacion": con_civ,
        "con_figuras": con_figs, "con_eventos": con_evs,
        "con_artefactos": con_arts,
        "tipos": dict(tipos), "candidatas": cands,
    }
def validar_eventos(idx, cons):
    ev = idx.eventos
    total = len(ev)
    con_anio = sum(1 for e in ev.values() if idx.anos(e) is not None)
    con_tipo = sum(1 for e in ev.values() if valido(v(e, "type")))
    con_hf = sum(1 for e in ev.values() if sin_dato(v(e, "hfid")) is not None)
    con_civ = sum(1 for e in ev.values() if sin_dato(v(e, "civ_id")) is not None)
    con_sitio = sum(1 for e in ev.values() if sin_dato(v(e, "site_id")) is not None)
    con_coords = sum(1 for e in ev.values() if coords_primeras(v(e, "coords")))
    con_col = sum(1 for eid in ev if idx.col_por_evento.get(eid))
    con_rel = sum(1 for eid in ev if idx.rel_por_evento.get(eid))
    tipos = collections.Counter(v(e, "type") for e in ev.values()
                                if valido(v(e, "type")))
    anos = [idx.anos(e) for e in ev.values() if idx.anos(e) is not None]
    cands = [k for k, e in ev.items()
             if idx.anos(e) is not None and sin_dato(v(e, "hfid")) is not None
             and (sin_dato(v(e, "site_id")) is not None
                  or sin_dato(v(e, "civ_id")) is not None)]
    cands.sort(key=lambda k: (idx.anos(ev[k]), k))
    return {
        "total": total, "con_anio": con_anio, "sin_anio": total - con_anio,
        "con_tipo": con_tipo, "con_hfid": con_hf, "con_civ_id": con_civ,
        "con_sitio_id": con_sitio, "con_coordenadas": con_coords,
        "con_collection": con_col, "con_relaciones": con_rel,
        "rango_anios": [min(anos), max(anos)] if anos else None,
        "tipos_distintos": len(tipos),
        "tipos": dict(tipos),
        "anos_1_a_100": collections.Counter(anos).most_common(),
        "candidatas": cands,
    }


def validar_relaciones(idx, cons):
    rels = idx.relaciones
    total = len(rels)
    a_presente = sum(1 for r in rels if r.get("event_existe_en_historical_events"))
    a_ausente = total - a_presente
    con_figuras = 0
    con_ent = 0
    con_sitio = 0
    otros = 0
    hf_validos = 0
    for r in rels:
        s = sin_dato(v(r, "source_hf"))
        t = sin_dato(v(r, "target_hf"))
        ok_s = s is not None and str(s) in idx.figuras
        ok_t = t is not None and str(t) in idx.figuras
        if ok_s and ok_t:
            hf_validos += 1
            con_figuras += 1
            continue
        if any(campo in r["campos"] for campo in
               ("civ_id", "entity_id", "site_id")):
            con_ent += 1
        else:
            otros += 1
    tipos = collections.Counter(v(r, "relationship") for r in rels
                                if valido(v(r, "relationship")))
    ids_ausentes = set()
    if rels:
        todos = set()
        for r in rels:
            e = r.get("event_id")
            if e is not None:
                todos.add(e)
        presentes = set(idx.eventos)
        ids_ausentes = {e for e in todos if e not in presentes}
    return {
        "total": total, "apuntan_a_evento_presente": a_presente,
        "apuntan_a_ids_ausentes": a_ausente,
        "ids_ausentes_distintos": len(ids_ausentes),
        "conectan_figuras_validas": hf_validos,
        "conectan_entidades": con_ent, "conectan_sitios": con_sitio,
        "otros": otros,
        "tipos": dict(tipos), "tipos_distintos": len(tipos),
    }


def validar_artefactos(idx, cons):
    art = idx.artefactos
    total = len(art)
    con_nombre = sum(1 for a in art.values() if valido(v(a, "name")))
    con_tipo = sum(1 for a in art.values() if valido(v(a, "item_type")))
    con_prop = sum(1 for a in art.values()
                   if sin_dato(v(a, "holder_hfid")) is not None)
    con_sitio = sum(1 for a in art.values()
                    if sin_dato(v(a, "site_id")) is not None)
    con_escrito = sum(1 for a in art.values() if valido(v(a, "writing")))
    cands = [k for k, a in art.items()
             if valido(v(a, "name")) and valido(v(a, "item_type"))
             and (sin_dato(v(a, "holder_hfid")) is not None
                  or sin_dato(v(a, "site_id")) is not None)]
    return {
        "total": total, "con_nombre": con_nombre, "con_tipo": con_tipo,
        "con_propietario": con_prop, "con_sitio": con_sitio,
        "con_escrito": con_escrito,
        "sin_propietario_ni_sitio": sum(
            1 for a in art.values()
            if sin_dato(v(a, "holder_hfid")) is None
            and sin_dato(v(a, "site_id")) is None),
        "candidatas": cands,
    }
def validar_geografia(cons):
    out = {}
    for sec, esperado in (("rivers", 2346), ("landmasses", 40),
                          ("mountain_peaks", 4), ("world_constructions", 122)):
        rs = cargar_jsonl(sec, PLUS)
        campo_coord = {"rivers": "path", "landmasses": "coord_1",
                       "mountain_peaks": "coords", "world_constructions": "coords"}[sec]
        tipos = collections.Counter(v(r, "type") for r in rs if valido(v(r, "type")))
        out[sec] = {
            "registros": len(rs), "esperado": esperado,
            "coincide": len(rs) == esperado,
            "con_id_df": sum(1 for r in rs if r.get("df_id")),
            "con_nombre": sum(1 for r in rs if valido(v(r, "name"))),
            "con_coordenadas": sum(1 for r in rs if valido(v(r, campo_coord))),
            "tipos": dict(tipos),
            "ejemplos": [{"df_id": r["df_id"], "nombre": v(r, "name"),
                          "coordenadas": (coords_primeras(v(r, campo_coord))
                                          or v(r, campo_coord))}
                         for r in rs[:3]],
        }
    return out


def validar_identidades(idx, cons):
    ids_ = idx.identidades
    total = len(ids_)
    con_histfig = resueltas = con_entity = 0
    for r in ids_:
        h = sin_dato(v(r, "histfig_id"))
        if h is not None:
            con_histfig += 1
            if str(h) in idx.figuras:
                resueltas += 1
        if sin_dato(v(r, "entity_id")) is not None:
            con_entity += 1
    # Figuras cuyo campo 'name' proviene de legends.xml y no de plus.
    # En merged/, 'campos.name.source' indica de qué fichero salió el valor.
    solo_xml = 0
    desde_xml = 0
    for k, f in idx.figuras.items():
        meta = (f.get("campos") or {}).get("name")
        if not meta:
            continue
        origen = meta.get("source") if isinstance(meta, dict) else None
        if origen == "legends.xml":
            desde_xml += 1
            if origen != "legends_plus.xml":
                solo_xml += 1
    return {"total": total, "con_histfig_id": con_histfig,
            "histfig_resuelto": resueltas,
            "histfig_no_resuelto": con_histfig - resueltas,
            "con_entity_id": con_entity,
            "figuras_nombre_desde_legends_xml": desde_xml,
            "figuras_con_nombre_solo_en_legends_xml": solo_xml}


def analizar_conflictos():
    """Estadísticas de los conflictos. NO se resuelven."""
    ruta = os.path.join(MERGED, "_manifiesto.json")
    with open(ruta, encoding="utf-8") as f:
        man = json.load(f)
    mg = man["merge"]
    por_campo = collections.Counter()
    ejemplos = collections.defaultdict(list)
    for c in mg.get("divergencias_detalle", []):
        clave = (c.get("campo"), c.get("tipo", "conflicto_real"))
        por_campo[clave] += 1
        if len(ejemplos[clave]) < 3:
            ejemplos[clave].append({
                "field": c.get("campo"),
                "source_legends": c.get("valor_legends_xml"),
                "source_plus": c.get("valor_legends_plus_xml"),
                "tipo": c.get("tipo"),
                "resolucion": "UNRESOLVED",
            })
    return {
        "divergencias_totales": mg.get("divergencias_totales"),
        "conflictos_reales": mg.get("conflictos_reales"),
        "notaciones_equivalentes": mg.get("notaciones_equivalentes"),
        "por_campo": {f"{k[0]} [{k[1]}]": n for k, n in por_campo.items()},
        "ejemplos": {f"{k[0]} [{k[1]}]": vs for k, vs in ejemplos.items()},
    }
def detectar_huerfanos(idx, cons):
    """Clasifica referencias ausentes. NO las trata como error."""
    cats = collections.Counter()
    detalles = collections.defaultdict(list)

    ev_hf_rota = ev_sitio_rota = ev_ent_rota = 0
    for eid, e in idx.eventos.items():
        h = sin_dato(v(e, "hfid"))
        if h is not None and str(h) not in idx.figuras:
            ev_hf_rota += 1
        s = sin_dato(v(e, "site_id"))
        if s is not None and str(s) not in idx.sitios:
            ev_sitio_rota += 1
        c = sin_dato(v(e, "civ_id"))
        if c is not None and str(c) not in idx.entidades:
            ev_ent_rota += 1
    cats["evento->figura rota"] = ev_hf_rota
    cats["evento->sitio rota"] = ev_sitio_rota
    cats["evento->entidad rota"] = ev_ent_rota
    if ev_hf_rota:
        detalles["evento->figura rota"].append(
            {"patron": "hfid sin figura correspondiente", "cantidad": ev_hf_rota})
    if ev_sitio_rota:
        detalles["evento->sitio rota"].append(
            {"patron": "site_id sin sitio correspondiente", "cantidad": ev_sitio_rota})
    if ev_ent_rota:
        detalles["evento->entidad rota"].append(
            {"patron": "civ_id sin entidad correspondiente", "cantidad": ev_ent_rota})

    rel_huerf = sum(1 for r in idx.relaciones
                    if not r.get("event_existe_en_historical_events"))
    cats[HUERFANO_LEGITIMO] = rel_huerf
    detalles[HUERFANO_LEGITIMO].append({
        "patron": "historical_event_relationship cuyo event_id no está en historical_events",
        "cantidad": rel_huerf,
        "explicacion": ("Dwarf Fortress exporta estos eventos en una tabla separada; "
                        "es el comportamiento normal, no un fallo")})

    sin_ev = sum(1 for k in idx.figuras if not idx.ev_por_hf.get(k))
    cats[DATOS_INSUFICIENTES] += sin_ev
    detalles[DATOS_INSUFICIENTES].append({
        "patron": "figura sin ningún evento asociado", "cantidad": sin_ev})

    sin_ent = sum(1 for k, f in idx.figuras.items()
                  if sin_dato(v(f, "entity_link.entity_id")) is None)
    cats[REF_INCOMPLETA] += sin_ent
    detalles[REF_INCOMPLETA].append({
        "patron": "figura sin entity_link (no consta su entidad)", "cantidad": sin_ent})

    ent_aisl = sum(1 for k in idx.entidades
                   if not idx.hf_por_entidad.get(k) and not idx.ev_por_entidad.get(k)
                   and not idx.ent_por_sitio.get(k))
    cats["entidad sin relaciones"] = ent_aisl
    detalles["entidad sin relaciones"].append(
        {"patron": "entidad sin figuras, eventos ni sitios", "cantidad": ent_aisl})

    sit_aisl = sum(1 for k in idx.sitios
                   if not idx.ev_por_sitio.get(k) and not idx.hf_por_sitio.get(k)
                   and not idx.art_por_sitio.get(k))
    cats["sitio sin referencias"] = sit_aisl
    detalles["sitio sin referencias"].append(
        {"patron": "sitio sin eventos, figuras ni artefactos", "cantidad": sit_aisl})

    art_huerf = sum(1 for a in idx.artefactos.values()
                    if sin_dato(v(a, "holder_hfid")) is None
                    and sin_dato(v(a, "site_id")) is None)
    cats["artefacto sin propietario ni sitio"] = art_huerf
    detalles["artefacto sin propietario ni sitio"].append(
        {"patron": "artefacto sin holder_hfid ni site_id", "cantidad": art_huerf})

    ev_sin_part = sum(1 for e in idx.eventos.values()
                      if sin_dato(v(e, "hfid")) is None
                      and sin_dato(v(e, "civ_id")) is None)
    cats["evento sin participantes"] = ev_sin_part
    detalles["evento sin participantes"].append(
        {"patron": "evento sin hfid ni civ_id", "cantidad": ev_sin_part})

    return {"categorias": dict(cats), "detalle": dict(detalles)}


def analizar_conflictos_de_guerras(idx):
    """Investiga cómo aparecen los conflictos. NO los clasifica como 'guerra'.

    Solo documenta event_type, subtipo, participantes y sitios reales.
    """
    ev = idx.eventos
    relevante = collections.Counter()
    sub = collections.Counter()
    muestras = {}
    palabras = ("battle", "war", "attack", "invasion", "conquest", "destroy",
                "raid", "siege", "kill", "died", "struck", "abduct")
    for eid, e in ev.items():
        t = (v(e, "type") or "").lower()
        st = (v(e, "subtype") or "").lower()
        c = (v(e, "cause") or "").lower()
        if any(p in t for p in palabras):
            relevante[t] += 1
            muestras.setdefault(t, []).append(eid)
        if t == "hf simple battle event" and st:
            sub[st] += 1
    total_bat = sum(sub.values())
    return {
        "event_types_relacionados": dict(relevante),
        "subtipos_battle": dict(sub),
        "total_eventos_battle": total_bat,
        "nota": ("El XML NO contiene una tabla 'wars'. Los conflictos aparecen como "
                 "eventos discretos con type/subtype; cualquier entidad WAR sería DERIVED."),
    }
def recorrer(idx, cons, f_ini):
    """Cadena FIGURA -> EVENTOS -> SITIOS -> ENTIDADES."""
    h = cons.historia_figura(f_ini, limite=25)
    sitios, entidades = set(), set()
    for e in h["eventos"]:
        if e["sitio_nombre"] != UNKNOWN:
            sitios.add(e["sitio_nombre"])
        if e["entidad_nombre"] != UNKNOWN:
            entidades.add(e["entidad_nombre"])
    return {
        "recorrido": "FIGURA -> EVENTOS -> SITIOS -> ENTIDADES",
        "desde_figura": f_ini,
        "nombre": h["figura"]["nombre"],
        "enlaces": [
            {"tipo": "figura->eventos", "certainty": FACT,
             "metodo": "campo hfid / group_*_hfid del evento"},
            {"tipo": "eventos->sitios", "certainty": FACT,
             "metodo": "campo site_id del evento"},
            {"tipo": "eventos->entidades", "certainty": FACT,
             "metodo": "campo civ_id del evento"}],
        "pasos": [
            {"paso": "eventos", "certainty": FACT,
             "total": h["total_eventos"], "rango_anios": h["rango_anios"]},
            {"paso": "sitios", "certainty": FACT, "valor": sorted(sitios)},
            {"paso": "entidades", "certainty": FACT, "valor": sorted(entidades)}],
    }


def generar_fixtures(idx, st):
    """Fixtures con IDs y datos REALES, para pruebas futuras."""
    os.makedirs(VALID, exist_ok=True)

    def volcar(nombre, obj):
        with open(os.path.join(VALID, nombre), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    figs = st["figuras"]["candidatas"][:12]
    volcar("figures_sample.json", {
        "certainty": FACT, "nota": "IDs y nombres reales de legends.xml",
        "figuras": [{"df_id": k, "nombre": v(idx.figuras[k], "name"),
                     "race": v(idx.figuras[k], "race"),
                     "eventos": len(idx.ev_por_hf.get(k, [])),
                     "relaciones_plus": len(idx.rel_por_hf.get(k, [])),
                     "certainty": FACT} for k in figs]})

    ents = st["entidades"]["candidatas_civilizacion"][:12]
    volcar("entities_sample.json", {
        "certainty": FACT,
        "entidades": [{"df_id": k, "nombre": v(idx.entidades[k], "name"),
                       "tipo": v(idx.entidades[k], "type"),
                       "figuras": len(idx.hf_por_entidad.get(k, [])),
                       "eventos": len(idx.ev_por_entidad.get(k, [])),
                       "certainty": FACT} for k in ents]})

    sits = st["sitios"]["candidatas"][:12]
    volcar("sites_sample.json", {
        "certainty": FACT,
        "sitios": [{"df_id": k, "nombre": v(idx.sitios[k], "name"),
                    "tipo": v(idx.sitios[k], "type"),
                    "coords": coords_primeras(v(idx.sitios[k], "coords")),
                    "civ_id": sin_dato(v(idx.sitios[k], "civ_id")),
                    "eventos": len(idx.ev_por_sitio.get(k, [])),
                    "certainty": FACT} for k in sits]})

    evs = st["eventos"]["candidatas"][:24]
    volcar("events_sample.json", {
        "certainty": FACT,
        "eventos": [{"df_id": k, "año": idx.anos(idx.eventos[k]),
                     "tipo": v(idx.eventos[k], "type"),
                     "subtipo": v(idx.eventos[k], "subtype"),
                     "hfid": sin_dato(v(idx.eventos[k], "hfid")),
                     "site_id": sin_dato(v(idx.eventos[k], "site_id")),
                     "civ_id": sin_dato(v(idx.eventos[k], "civ_id")),
                     "certainty": FACT} for k in evs]})

    arts = st["artefactos"]["candidatas"][:12]
    volcar("artifacts_sample.json", {
        "certainty": FACT,
        "artefactos": [{"df_id": k, "nombre": v(idx.artefactos[k], "name"),
                        "tipo": v(idx.artefactos[k], "item_type"),
                        "holder_hfid": sin_dato(v(idx.artefactos[k], "holder_hfid")),
                        "site_id": sin_dato(v(idx.artefactos[k], "site_id")),
                        "certainty": FACT} for k in arts]})

    rels = idx.relaciones[:12]
    volcar("relationship_sample.json", {
        "certainty": FACT,
        "relaciones": [{"event_id": r["event_id"],
                        "tipo": v(r, "relationship"),
                        "source_hf": sin_dato(v(r, "source_hf")),
                        "target_hf": sin_dato(v(r, "target_hf")),
                        "año": sin_dato(v(r, "year")),
                        "evento_presente": r["event_existe_en_historical_events"],
                        "certainty": FACT} for r in rels]})

    # cronología: conteos reales por año
    por_anio = st["eventos"]["anos_1_a_100"]
    por_anio = sorted(por_anio, key=lambda x: int(x[0]))
    volcar("timeline_sample.json", {
        "certainty": DERIVED,
        "rango_anios": st["eventos"]["rango_anios"],
        "eventos_por_año": [{"año": int(y), "eventos": n, "certainty": DERIVED}
                            for y, n in por_anio[:20]],
        "nota": "Conteos DERIVADOS a partir del campo year de cada evento (FACT)."})


def main():
    print("[1/5] Cargando datos procesados ...")
    idx = Indice().cargar()
    cons = Consultas(idx)
    print(f"      figuras={len(idx.figuras):,} entidades={len(idx.entidades):,} "
          f"sitios={len(idx.sitios):,} eventos={len(idx.eventos):,} "
          f"artefactos={len(idx.artefactos):,}")

    print("[2/5] Validaciones ...")
    st = {
        "figuras": validar_figuras(idx, cons),
        "entidades": validar_entidades(idx, cons),
        "sitios": validar_sitios(idx, cons),
        "eventos": validar_eventos(idx, cons),
        "relaciones": validar_relaciones(idx, cons),
        "artefactos": validar_artefactos(idx, cons),
        "geografia": validar_geografia(cons),
        "identidades": validar_identidades(idx, cons),
        "huerfanos": detectar_huerfanos(idx, cons),
        "conflictos": analizar_conflictos(),
        "conflictos_guerra": analizar_conflictos_de_guerras(idx),
    }

    print("[3/5] Ejemplos factuales ...")
    # La selección de candidatos es tolerante a listas vacías: si una sección
    # no alcanza los criterios, se documenta como DATOS INSUFICIENTES en vez de
    # inventar o abortar la validación.
    def primeros(lst, n=10):
        return [x for x in (lst or [])[:n]]

    st["ejemplos_figura"] = [cons.ficha_figura(k)
                             for k in primeros(st["figuras"]["candidatas"])]
    st["ejemplos_entidad"] = [cons.recursive_entidad(k)
                              for k in primeros(
                                  st["entidades"]["candidatas_civilizacion"])]
    st["ejemplos_sitio"] = [cons.ficha_sitio(k)
                            for k in primeros(st["sitios"]["candidatas"])]
    st["ejemplos_evento"] = [cons.ficha_evento(k)
                             for k in primeros(st["eventos"]["candidatas"], 20)]
    st["ejemplos_artefacto"] = [cons.ficha_artefacto(k)
                                for k in primeros(st["artefactos"]["candidatas"])]

    print("[4/5] Cronología y recorridos ...")
    rango = st["eventos"]["rango_anios"] or [1, 1]
    st["cronologia_rango"] = cons.eventos_entre(
        rango[0], min(rango[0] + 9, rango[1]), limite=40)
    cands = st["figuras"]["candidatas"]
    st["cronologia_historia"] = (cons.historia_figura(cands[0], limite=30)
                                 if cands else {"certainty": UNKNOWN,
                                                "motivo": "sin figuras que cumplan criterios"})
    st["recorridos"] = [recorrer(idx, cons, cands[i])
                        for i in range(min(3, len(cands)))]

    print("[5/5] Fixtures ...")
    generar_fixtures(idx, st)

    with open(os.path.join(VALID, "_estadisticas.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1, default=str)
    print(f"\n[OK] Estadísticas en {VALID}")
    return st


if __name__ == "__main__":
    main()
