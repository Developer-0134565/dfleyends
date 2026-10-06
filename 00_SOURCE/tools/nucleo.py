#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Núcleo de consulta
====================================

Capa de acceso a datos y API de consulta del archivo histórico.

DISEÑO
------
Reutiliza el `Indice` ya construido y validado en la Fase 2
(`validar_semantica.py`) en lugar de duplicar la lógica de carga e indexado.
Este módulo AÑADE: búsqueda, fichas estructuradas, cronología, relaciones
sociales, agrupaciones de conflicto DERIVED y exportación.

PRINCIPIOS
----------
* Los IDs de Dwarf Fortress se conservan tal cual (son cadenas en los JSONL).
* Cada resultado declara su `certainty`: FACT o DERIVED.
* Lo desconocido se marca UNKNOWN; nunca se inventa.
* Las 13.192 relaciones de legends_plus.xml NO se asocian a eventos ausentes.
* Los XML originales no se abren: solo se leen los JSONL procesados.

USO
---
    from nucleo import Archivo
    a = Archivo()
    print(a.buscar_figura("galka shafttop"))
    print(a.ficha_figura("712"))
"""
import os
import re
import sys
import json
import time
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402
from validar_semantica import (  # noqa: E402
    Indice, Consultas, cargar_jsonl, v, valido, como_int, sin_dato,
    coords_primeras, MERGED, PLUS, BASE,
    FACT, DERIVED, INTERPRETATION, UNKNOWN,
)

# Rutas centralizadas (antes: os.path.join(BASE, "00_SOURCE", "processed")).
PROC = rutas.PROCESSED_ROOT
VALID = rutas.VALIDATION_ROOT

# Límite temporal observado en los datos (verificado en Fase 2).
ANIO_MIN, ANIO_MAX = 1, 100


def normalizar(texto):
    """Minúsculas, sin acentos ni signos, para buscar."""
    if texto is None:
        return ""
    t = str(texto).lower().strip()
    t = (t.replace("á", "a").replace("é", "e").replace("í", "i")
          .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
          .replace("ü", "u").replace("'", "").replace("`", ""))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


class Archivo:
    """Archivo histórico consultable sobre los datos de Dwarf Fortress."""

    def __init__(self, verbose=False):
        t0 = time.perf_counter()
        self.indice = Indice().cargar()
        self.c = Consultas(self.indice)
        self.tiempo_carga = time.perf_counter() - t0

        self._rivers = cargar_jsonl("rivers", PLUS)
        self._landmasses = cargar_jsonl("landmasses", PLUS)
        self._peaks = cargar_jsonl("mountain_peaks", PLUS)
        self._wcs = cargar_jsonl("world_constructions", PLUS)

        # artefacto -> eventos que lo mencionan (FACT)
        self.ev_por_artefacto = collections.defaultdict(list)
        for eid, e in self.indice.eventos.items():
            aid = sin_dato(v(e, "artifact_id"))
            if aid is not None:
                self.ev_por_artefacto[str(aid)].append(eid)
        # artefacto -> creador, vía evento 'artifact created' (FACT)
        self.creador_artefacto = {}
        for eid, e in self.indice.eventos.items():
            if v(e, "type") == "artifact created":
                aid = sin_dato(v(e, "artifact_id"))
                hid = sin_dato(v(e, "hist_figure_id"))
                if aid is not None and hid is not None:
                    self.creador_artefacto[str(aid)] = str(hid)

        # Índice año -> [evento_id, ...]. DERIVED, construido una vez.
        # Auditía Extra (parte 13): convierte eventos_del_anio() de O(n) a
        # O(año). El orden usa el MISMO criterio que Indice.eventos_ordenados,
        # por lo que no altera el determinismo ni los resultados.
        self.eventos_por_anio = collections.defaultdict(list)
        for eid, ev in self.indice.eventos.items():
            self.eventos_por_anio[self.indice.anos(ev)].append(eid)

        # (x, y) -> sitios. DERIVED, construido una vez a partir de FACT.
        # Existe para responder "que hay en esta coordenada" sin recorrer los
        # 734 sitios en cada peticion. El indice es DERIVED; los valores que
        # indexa (coordenadas, nombre, tipo) son FACT.
        self.sitios_por_coordenada = collections.defaultdict(list)
        for sid, s in self.indice.sitios.items():
            for par in coords_primeras(v(s, "coords")):
                self.sitios_por_coordenada[par].append(sid)

        # (capa, x, y) -> [df_id, ...]. DERIVED.
        # Los rios no tienen <id>: su df_id ya es un hash DERIVED del nucleo.
        self.capas_por_coordenada = collections.defaultdict(list)
        for nombre, registros, campo in (
                ("world_constructions", self._wcs, "coords"),
                ("mountain_peaks", self._peaks, "coords"),
                ("landmasses", self._landmasses, "coord_1"),
                ("rivers", self._rivers, "path")):
            for r in registros:
                for par in coords_primeras(v(r, campo)):
                    self.capas_por_coordenada[(nombre, par[0], par[1])].append(
                        r.get("df_id"))
        for y in self.eventos_por_anio:
            self.eventos_por_anio[y] = self.indice.eventos_ordenados(
                self.eventos_por_anio[y])

        self._idx_busqueda = self._construir_indice_busqueda()
        if verbose:
            print(f"[Archivo] cargado en {self.tiempo_carga:.2f}s")

    def _construir_indice_busqueda(self):
        idx = {k: collections.defaultdict(set) for k in
               ("historical_figures", "entities", "sites", "artifacts",
                "historical_events")}
        fuentes = {
            "historical_figures": (self.indice.figuras, "name"),
            "entities": (self.indice.entidades, "name"),
            "sites": (self.indice.sitios, "name"),
            "artifacts": (self.indice.artefactos, "name"),
            "historical_events": (self.indice.eventos, "type"),
        }
        for tipo, (dic, campo) in fuentes.items():
            for did, rec in dic.items():
                tokens = set(normalizar(v(rec, campo)).split())
                tokens.add(normalizar(did))
                for t in tokens:
                    if t:
                        idx[tipo][t].add(did)
        return idx

    # ------------------------------------------------------------------ util
    def nombre_de(self, tipo, did):
        if did is None:
            return UNKNOWN
        dic = {"historical_figures": self.indice.figuras,
               "entities": self.indice.entidades,
               "sites": self.indice.sitios,
               "artifacts": self.indice.artefactos}.get(tipo, {})
        rec = dic.get(str(did))
        if rec is None:
            return UNKNOWN
        n = v(rec, "name")
        return n if valido(n) else UNKNOWN
# ------------------------------------------------------------- BUSQUEDA
    def buscar(self, texto, tipo=None, limite=50):
        """Búsqueda parcial por nombre o ID.

        Devuelve AMBIGUA si hay más de una coincidencia; nunca elige por su
        cuenta qué entidad es la correcta.
        """
        t = normalizar(texto)
        if not t:
            return {"consulta": texto, "consulta_ambigua": False,
                    "resultados": {}, "certainty": UNKNOWN,
                    "motivo": "consulta vacía"}
        tipos = [tipo] if tipo else list(self._idx_busqueda)
        out = {}
        totales = {}
        for tp in tipos:
            enc = set()
            for tok in t.split():
                enc |= self._idx_busqueda[tp].get(tok, set())
            if not enc:
                for clave, ids in self._idx_busqueda[tp].items():
                    if clave.startswith(t) or t.startswith(clave):
                        enc |= ids
            # El total se cuenta ANTES de truncar, para no ocultar informacion.
            ordenados = sorted(enc, key=lambda x: int(x) if x.isdigit() else 0)
            totales[tp] = len(ordenados)
            out[tp] = ordenados[:limite]
        return {"consulta": texto,
                "consulta_ambigua": any(v > 1 for v in totales.values()),
                "total_encontrados": totales,
                "total_devueltos": {k: len(v) for k, v in out.items()},
                "limite": limite,
                "truncado": any(totales[k] > len(out[k]) for k in out),
                "resultados": out, "certainty": FACT}

    def _buscar_tipo(self, texto, tipo, breve, limite=20):
        r = self.buscar(texto, tipo, limite)
        ids = r["resultados"].get(tipo, [])
        total = r["total_encontrados"].get(tipo, len(ids))
        ficha = {"historical_figures": self.ficha_figura,
                 "entities": self.ficha_entidad,
                 "sites": self.ficha_sitio,
                 "artifacts": self.ficha_artefacto}[tipo]
        return {"tipo": tipo, "consulta": texto,
                "consulta_ambigua": r["consulta_ambigua"], "ids": ids,
                "total_encontrados": total,
                "devueltos": len(ids),
                "truncado": total > len(ids),
                "limite": limite,
                "fichas": [ficha(i, breve=True) for i in ids], "certainty": FACT}

    def buscar_figura(self, texto, limite=20):
        return self._buscar_tipo(texto, "historical_figures", True, limite)

    def buscar_entidad(self, texto, limite=20):
        return self._buscar_tipo(texto, "entities", True, limite)

    def buscar_sitio(self, texto, limite=20):
        return self._buscar_tipo(texto, "sites", True, limite)

    def buscar_artefacto(self, texto, limite=20):
        return self._buscar_tipo(texto, "artifacts", True, limite)

    def buscar_evento(self, texto, limite=20):
        r = self.buscar(texto, "historical_events", limite)
        ids = r["resultados"].get("historical_events", [])
        total = r["total_encontrados"].get("historical_events", len(ids))
        return {"tipo": "historical_events", "consulta": texto,
                "consulta_ambigua": r["consulta_ambigua"], "ids": ids,
                "total_encontrados": total,
                "devueltos": len(ids),
                "truncado": total > len(ids),
                "limite": limite,
                "certainty": FACT}

    # ------------------------------------------------------------- FECHAS
    @staticmethod
    def _anio_seguro(valor):
        """Coerce a int. Devuelve None si no es un año numérico entero.

        Existe para que una consulta con un tipo equivocado NO rompa y
        devuelva UNKNOWN en lugar de lanzar una excepcion.
        """
        if valor is None or isinstance(valor, bool):
            return None
        if isinstance(valor, int):
            return valor
        if isinstance(valor, float):
            return int(valor) if valor.is_integer() else None
        try:
            s = str(valor).strip()
            return int(s) if s.lstrip("+-").isdigit() else None
        except (TypeError, ValueError):
            return None

    def eventos_del_anio(self, anio):
        y = self._anio_seguro(anio)
        if y is None:
            return {"certainty": UNKNOWN, "anio": anio,
                    "motivo": "el año no es un número entero válido"}
        if not (ANIO_MIN <= y <= ANIO_MAX):
            return {"certainty": UNKNOWN, "anio": y,
                    "motivo": f"fuera del rango de los datos ({ANIO_MIN}-{ANIO_MAX})"}
        ids = self.eventos_por_anio.get(y, [])
        filas = [self._evento_resumido(eid) for eid in ids]
        return {"anio": y, "total": len(filas), "eventos": filas,
                "certainty": FACT,
                "nota": "ordenado por (segundos72, evento_id)"}

    def eventos_entre_anios(self, anio_a, anio_b, limite=None):
        a = self._anio_seguro(anio_a)
        b = self._anio_seguro(anio_b)
        if a is None or b is None:
            return {"certainty": UNKNOWN, "desde": anio_a, "hasta": anio_b,
                    "motivo": "los años no son números enteros válidos"}
        a, b = sorted((a, b))
        # Union de los años del rango usando el índice: evita el barrido O(n).
        ids = []
        for y in range(a, b + 1):
            ids.extend(self.eventos_por_anio.get(y, []))
        ids = self.indice.eventos_ordenados(ids)
        filas = [self._evento_resumido(e) for e in ids]
        total = len(filas)
        devueltos = filas[:limite] if limite else filas
        return {"desde": a, "hasta": b, "total": total,
                "eventos": devueltos,
                "devueltos": len(devueltos),
                "truncado": total > len(devueltos),
                "certainty": FACT, "limite_temporal_datos": [ANIO_MIN, ANIO_MAX]}
# ---------------------------------------------------------------- FICHAS
    def ficha_figura(self, df_id, breve=False):
        """Ficha estructurada de una figura histórica."""
        f = self.indice.figuras.get(str(df_id))
        if f is None:
            return {"certainty": UNKNOWN, "tipo": "historical_figure",
                    "df_id": str(df_id), "motivo": "no existe esa figura"}
        base = self.c.ficha_figura(str(df_id))
        base["tipo"] = "historical_figure"
        base["identidad"] = self.identidad_de_figura(str(df_id))
        base["conflictos_registrados"] = len(f.get("conflictos", []))
        base["nacimiento"] = self._fecha_legible(base.get("nacimiento"))
        base["muerte"] = self._fecha_legible(base.get("muerte"))
        if not breve:
            base["acontecimientos"] = self.eventos_de_figura(str(df_id))
            base["cronologia"] = self.cronologia_figura(str(df_id))
            base["artefactos"] = self.artefactos_de_figura(str(df_id))
            base["relaciones_sociales"] = self.relaciones_de_figura(str(df_id))
            base["sitios_relacionados"] = sorted(
                {e["sitio_nombre"] for e in base["acontecimientos"]
                 if e["sitio_nombre"] != UNKNOWN})
            base["entidades_relacionadas"] = sorted(
                {e["entidad_nombre"] for e in base["acontecimientos"]
                 if e["entidad_nombre"] != UNKNOWN})
        return base

    @staticmethod
    def _fecha_legible(campo):
        """Añade certeza explícita a un campo de fecha.

        CRÍTICO (auditoría Extra, parte 4): un `death_year` ausente NO
        significa «sigue viva» ni «murió después del año 100». Significa
        que el dato NO CONSTA. Se marca UNKNOWN para que ninguna capa
        consumidora pueda interpretar la ausencia como negación.
        """
        if not isinstance(campo, dict):
            return {"certainty": UNKNOWN, "motivo": "campo no disponible"}
        anio = campo.get("año")
        if anio is None:
            return {"año": None, "segundos72": campo.get("segundos72"),
                    "certainty": UNKNOWN,
                    "motivo": ("el XML no registra esta fecha. NO significa "
                               "que la figura siga viva ni que muriera fuera "
                               "del rango de los datos."),
                    "interpretacion_prohibida": [
                        "sigue viva", "murió después del año 100",
                        "murió en una fecha desconocida pero anterior"]}
        return {"año": anio, "segundos72": campo.get("segundos72"),
                "certainty": FACT}

    def identidad_de_figura(self, df_id):
        """Identidad asociada (legends_plus) o UNKNOWN."""
        for ident in self.indice.identidades:
            if str(sin_dato(v(ident, "histfig_id")) or "") == str(df_id):
                return {"df_id": ident["df_id"], "nombre": v(ident, "name"),
                        "source": ident.get("source"), "certainty": FACT}
        return {"certainty": UNKNOWN, "motivo": "sin identidad asociada"}

    def eventos_de_figura(self, df_id, limite=None, con_total=False):
        """Eventos de una figura, ordenados.

        Con `con_total=True` devuelve además `total`, `devueltos` y
        `truncado`, para que un recorte nunca sea silencioso.
        """
        ids = self.indice.ev_por_hf.get(str(df_id), [])
        orden = self.indice.eventos_ordenados(
            [i for i in ids if i in self.indice.eventos])
        total = len(orden)
        if limite:
            orden = orden[:limite]
        filas = [self._evento_resumido(eid) for eid in orden]
        if con_total:
            return {"items": filas, "total": total, "devueltos": len(filas),
                    "truncado": total > len(filas), "certainty": FACT}
        return filas

    def cronologia_figura(self, df_id, limite=None):
        todos = self.indice.ev_por_hf.get(str(df_id), [])
        filas = self.eventos_de_figura(df_id, limite)
        anios = [f["año"] for f in filas if f["año"] is not None]
        return {"figura_id": str(df_id),
                "nombre": self.nombre_de("historical_figures", df_id),
                "total_eventos": len(todos),
                "devueltos": len(filas),
                "truncado": len(todos) > len(filas),
                "rango_anios": [min(anios), max(anios)] if anios else UNKNOWN,
                "linea_temporal": filas, "certainty": FACT,
                "limite_temporal_datos": [ANIO_MIN, ANIO_MAX]}

    def _evento_resumido(self, eid):
        e = self.indice.eventos[eid]
        sid, cid, hf = (sin_dato(v(e, "site_id")), sin_dato(v(e, "civ_id")),
                        sin_dato(v(e, "hfid")))
        return {
            "evento_id": eid, "año": self.indice.anos(e),
            "segundos72": sin_dato(v(e, "seconds72")),
            "tipo": v(e, "type"),
            "subtipo": v(e, "subtype") if valido(v(e, "subtype")) else None,
            "estado": v(e, "state") if valido(v(e, "state")) else None,
            "causa": v(e, "cause") if valido(v(e, "cause")) else None,
            "figura_id": hf, "figura_nombre": self.nombre_de("historical_figures", hf),
            "entidad_id": cid, "entidad_nombre": self.nombre_de("entities", cid),
            "sitio_id": sid, "sitio_nombre": self.nombre_de("sites", sid),
            "certainty": FACT,
        }

    # ------------------------------------------------------------ ESTADISTICAS
    def estadisticas(self):
        """Cifras REALES del dataset, calculadas desde el indice cargado.

        Ninguna cifra esta escrita a mano: todas salen de `self.indice`.
        La UI las muestra; no las inventa.
        """
        idx = self.indice
        anos_con_datos = sorted(y for y in self.eventos_por_anio
                                if y is not None)
        return {
            "figuras": len(idx.figuras),
            "entidades": len(idx.entidades),
            "sitios": len(idx.sitios),
            "eventos": len(idx.eventos),
            "artefactos": len(idx.artefactos),
            "relaciones": len(idx.relaciones),
            "rios": len(self._rivers),
            "masas_tierra": len(self._landmasses),
            "picos": len(self._peaks),
            "construcciones_mundo": len(self._wcs),
            "identidades": len(idx.identidades),
            "colecciones_eventos": len(idx.collections),
            "eras": len(idx.eras),
            "supplements": len(idx.supplements),
            "anio_min": min(anos_con_datos) if anos_con_datos else UNKNOWN,
            "anio_max": max(anos_con_datos) if anos_con_datos else UNKNOWN,
            "anos_con_eventos": len(anos_con_datos),
            "limite_temporal_datos": [ANIO_MIN, ANIO_MAX],
            "certainty": DERIVED,
            "nota": ("Conteos DERIVED: se cuentan registros del indice. Los "
                     "valores de cada registro son FACT."),
        }

    def tipos_evento(self):
        """Tipos de evento REALES presentes en el XML, con su recuento.

        Alimenta el desplegable 'Tipo' del explorador de eventos. No inventa
        tipos ni los traduce.
        """
        c = collections.Counter()
        for e in self.indice.eventos.values():
            t = v(e, "type")
            if valido(t):
                c[t] += 1
        return {"tipos": dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))),
                "total_tipos": len(c),
                "total_eventos": len(self.indice.eventos),
                "certainty": FACT,
                "nota": "cadenas literales del XML; sin traducir ni agrupar"}

    def ficha_evento(self, df_id):
        """Ficha completa de un evento, con participantes y contexto."""
        base = self.c.ficha_evento(str(df_id))
        if base.get("certainty") == UNKNOWN:
            return base
        base["tipo_registro"] = "historical_event"
        base["relaciones_adicionales"] = self.relaciones_adicionales_evento(
            str(df_id))
        return base

    def ficha_entidad(self, df_id, breve=False):
        e = self.indice.entidades.get(str(df_id))
        if e is None:
            return {"certainty": UNKNOWN, "tipo": "entity",
                    "df_id": str(df_id), "motivo": "no existe esa entidad"}
        base = self.c.ficha_entidad(str(df_id))
        base["tipo"] = "entity"
        if not breve:
            base["figuras"] = [self.ficha_figura(h, breve=True)
                               for h in self.indice.hf_por_entidad.get(str(df_id), [])]
            base["sitios"] = [{"df_id": s, "nombre": v(self.indice.sitios[s], "name"),
                               "tipo": v(self.indice.sitios[s], "type"),
                               "certainty": FACT}
                              for s in self.indice.ent_por_sitio.get(str(df_id), [])]
            base["acontecimientos"] = [
                self._evento_resumido(x) for x in self.indice.eventos_ordenados(
                    [y for y in self.indice.ev_por_entidad.get(str(df_id), [])
                     if y in self.indice.eventos])]
            base["artefactos"] = self.artefactos_de_entidad(str(df_id))
            base["cronologia"] = self.cronologia_entidad(str(df_id))
        return base

    def eventos_filtrados(self, anio=None, desde=None, hasta=None, tipo=None,
                          figura=None, sitio=None, entidad=None, limite=50,
                          offset=0):
        """Busqueda de eventos por año, tipo, figura, sitio o entidad.

        Devuelve SIEMPRE el total real de coincidencias, incluso si solo se
        devuelve una pagina: `truncado` dice si hay mas.
        """
        def anio_o_error(valor, etiqueta):
            """None = no filtrado. UNKNOWN = error de tipo."""
            if valor is None:
                return None
            y = self._anio_seguro(valor)
            if y is None:
                return UNKNOWN
            return y

        a = anio_o_error(anio, "anio")
        d = anio_o_error(desde, "desde")
        h = anio_o_error(hasta, "hasta")
        for etiqueta, valor in (("anio", a), ("desde", d), ("hasta", h)):
            if valor == UNKNOWN:
                return {"certainty": UNKNOWN, "eventos": [], "items": [],
                        "total_encontrados": 0, "devueltos": 0,
                        "truncado": False, "offset": 0, "limite": limite,
                        "motivo": f"'{etiqueta}' no es un año entero válido"}
        if a is not None:
            d = h = a
        if d is not None and h is not None and d > h:
            d, h = h, d

        # Candidatos: se parte del indice mas selectivo disponible.
        if figura is not None:
            base = [x for x in self.indice.ev_por_hf.get(str(figura), [])
                    if x in self.indice.eventos]
        elif sitio is not None:
            base = [x for x in self.indice.ev_por_sitio.get(str(sitio), [])
                    if x in self.indice.eventos]
        elif entidad is not None:
            base = [x for x in self.indice.ev_por_entidad.get(str(entidad), [])
                    if x in self.indice.eventos]
        elif d is not None or h is not None:
            base = []
            for y in range(d if d is not None else ANIO_MIN,
                           (h if h is not None else ANIO_MAX) + 1):
                base.extend(self.eventos_por_anio.get(y, []))
        else:
            base = list(self.indice.eventos)

        def pasa(eid):
            # El rango de años se revalida SIEMPRE: la base puede venir de un
            # índice por figura/sitio/entidad, que no lo restringe por año.
            if d is not None or h is not None:
                y = self.indice.anos(self.indice.eventos[eid])
                if y is None:
                    return False
                if d is not None and y < d:
                    return False
                if h is not None and y > h:
                    return False
            if tipo is None:
                return True
            return v(self.indice.eventos[eid], "type") == tipo

        sel = [eid for eid in base if pasa(eid)]
        sel = self.indice.eventos_ordenados(dict.fromkeys(sel))
        total = len(sel)
        off = max(0, int(offset or 0))
        pagina = sel[off:off + limite] if limite else sel[off:]
        return {
            "eventos": [self._evento_resumido(e) for e in pagina],
            "total_encontrados": total,
            "devueltos": len(pagina),
            "truncado": (off + len(pagina)) < total,
            "offset": off,
            "limite": limite,
            "filtros": {"anio": a, "desde": d, "hasta": h, "tipo": tipo,
                        "figura": figura, "sitio": sitio, "entidad": entidad},
            "certainty": FACT,
            "nota": "ordenado por (año, seconds72): el orden temporal validado",
        }

    def listar_registros(self, tipo_registro, limite=50, offset=0):
        """Listado paginado de un tipo de registro (para explorar sin buscar).

        `tipo_registro` ∈ historical_figures, entities, sites, artifacts.
        """
        tabla = {"historical_figures": (self.indice.figuras, self.ficha_figura),
                 "entities": (self.indice.entidades, self.ficha_entidad),
                 "sites": (self.indice.sitios, self.ficha_sitio),
                 "artifacts": (self.indice.artefactos, self.ficha_artefacto)}
        par = tabla.get(tipo_registro)
        if par is None:
            return {"certainty": UNKNOWN, "items": [], "total_encontrados": 0,
                    "devueltos": 0, "truncado": False, "offset": 0,
                    "limite": limite,
                    "motivo": f"tipo de registro desconocido: {tipo_registro!r}"}
        dic, ficha = par
        orden = sorted(dic, key=lambda x: int(x) if x.isdigit() else 0)
        total = len(orden)
        off = max(0, int(offset or 0))
        pagina = orden[off:off + limite] if limite else orden[off:]
        return {"items": [ficha(i, breve=True) for i in pagina],
                "total_encontrados": total,
                "devueltos": len(pagina),
                "truncado": (off + len(pagina)) < total,
                "offset": off, "limite": limite,
                "certainty": FACT}

    def eventos_de_artefacto(self, df_id, limite=None, con_total=False):
        """Eventos que mencionan un artefacto (campo artifact_id)."""
        ids = [i for i in self.ev_por_artefacto.get(str(df_id), [])
               if i in self.indice.eventos]
        orden = self.indice.eventos_ordenados(ids)
        total = len(orden)
        if limite:
            orden = orden[:limite]
        filas = [self._evento_resumido(eid) for eid in orden]
        if con_total:
            return {"items": filas, "total": total, "devueltos": len(filas),
                    "truncado": total > len(filas), "certainty": FACT}
        return filas

    def miembros_entidad(self, df_id):
        """Figuras que pertenecen a una entidad (FACT vía entity_link)."""
        ids = self.indice.hf_por_entidad.get(str(df_id), [])
        return {"entidad_id": str(df_id),
                "nombre": self.nombre_de("entities", df_id),
                "miembros": [{"df_id": h,
                              "nombre": v(self.indice.figuras[h], "name"),
                              "race": v(self.indice.figuras[h], "race"),
                              "eventos": len(self.indice.ev_por_hf.get(h, [])),
                              "certainty": FACT} for h in ids],
                "total": len(ids), "certainty": FACT,
                "enlace": "historical_figures.entity_link.entity_id"}

    def sitios_de_entidad(self, df_id):
        ids = self.indice.ent_por_sitio.get(str(df_id), [])
        return {"entidad_id": str(df_id), "sitios": [
            {"df_id": s, "nombre": v(self.indice.sitios[s], "name"),
             "tipo": v(self.indice.sitios[s], "type"),
             "coordenadas": coords_primeras(v(self.indice.sitios[s], "coords")) or UNKNOWN,
             "certainty": FACT} for s in ids],
            "total": len(ids), "certainty": FACT,
            "enlace": "sites.civ_id / sites.cur_owner_id"}

    def ficha_sitio(self, df_id, breve=False):
        """Ficha de sitio. `tipo` conserva el tipo real de Dwarf Fortress."""
        base = self.c.ficha_sitio(str(df_id))
        if base.get("certainty") == UNKNOWN:
            base["tipo_registro"] = "site"
            return base
        # NO se sobreescribe `tipo`: es el tipo del sitio en el XML (p.ej.
        # 'fortress'). `tipo_registro` identifica el tipo de registro.
        base["tipo_registro"] = "site"
        # AUSENCIA != NEGACIÓN (auditoría Extra, parte 19): 0 eventos
        # significa "no constan", no "ocurrieron cero eventos".
        if base.get("eventos") == 0:
            base["certainty_eventos"] = UNKNOWN
            base["nota_eventos"] = ("no constan eventos registrados para este "
                                    "sitio; esto NO significa que no ocurriera "
                                    "ninguno")
        if not breve:
            base["acontecimientos"] = self.eventos_de_sitio(str(df_id))
            base["figuras"] = [self.ficha_figura(h, breve=True)
                               for h in self.indice.hf_por_sitio.get(str(df_id), [])]
            base["artefactos"] = [
                {"df_id": a, "nombre": v(self.indice.artefactos[a], "name"),
                 "certainty": FACT}
                for a in self.indice.art_por_sitio.get(str(df_id), [])]
            base["historia"] = self.cronologia_sitio(str(df_id))
        return base

    def eventos_de_sitio(self, df_id, limite=None, con_total=False):
        """Eventos de un sitio, ordenados. Ver `eventos_de_figura`."""
        ids = [i for i in self.indice.ev_por_sitio.get(str(df_id), [])
               if i in self.indice.eventos]
        orden = self.indice.eventos_ordenados(ids)
        total = len(orden)
        if limite:
            orden = orden[:limite]
        filas = [self._evento_resumido(eid) for eid in orden]
        if con_total:
            return {"items": filas, "total": total, "devueltos": len(filas),
                    "truncado": total > len(filas), "certainty": FACT}
        return filas

    def cronologia_sitio(self, df_id, limite=None):
        todos = self.indice.ev_por_sitio.get(str(df_id), [])
        filas = self.eventos_de_sitio(df_id, limite)
        anios = [f["año"] for f in filas if f["año"] is not None]
        return {"sitio_id": str(df_id), "nombre": self.nombre_de("sites", df_id),
                "total_eventos": len(todos),
                "devueltos": len(filas),
                "truncado": len(todos) > len(filas),
                "rango_anios": [min(anios), max(anios)] if anios else UNKNOWN,
                "linea_temporal": filas, "certainty": FACT}
    def ficha_artefacto(self, df_id, breve=False):
        a = self.indice.artefactos.get(str(df_id))
        if a is None:
            return {"certainty": UNKNOWN, "tipo": "artifact",
                    "df_id": str(df_id), "motivo": "no existe ese artefacto"}
        base = self.c.ficha_artefacto(str(df_id))
        base["tipo"] = "artifact"
        # creador: vía evento 'artifact created' (FACT)
        cid = self.creador_artefacto.get(str(df_id))
        base["creador"] = {
            "figura_id": cid,
            "nombre": self.nombre_de("historical_figures", cid),
            "certainty": FACT if cid else UNKNOWN,
            "metodo": "historical_events(type='artifact created').hist_figure_id",
        }
        if not breve:
            base["propietarios"] = self.propietarios_artefacto(str(df_id))
            base["acontecimientos"] = [
                self._evento_resumido(e) for e in self.indice.eventos_ordenados(
                    [x for x in self.ev_por_artefacto.get(str(df_id), [])
                     if x in self.indice.eventos])]
            base["escrito"] = valido(v(a, "writing"))
            wc_id = sin_dato(v(a, "writing"))
            base["escrito_id"] = wc_id
        return base

    def propietarios_artefacto(self, df_id):
        """Propietario declarado (holder_hfid) y registro histórico."""
        a = self.indice.artefactos.get(str(df_id))
        if a is None:
            return {"certainty": UNKNOWN, "motivo": "artefacto inexistente"}
        h = sin_dato(v(a, "holder_hfid"))
        return {
            "propietario_actual_id": h,
            "propietario_actual_nombre": self.nombre_de("historical_figures", h),
            "eventos_que_lo_mencionan": len(self.ev_por_artefacto.get(str(df_id), [])),
            "certeza_enlace": FACT,
            "certainty": FACT if h else UNKNOWN,
        }

    def artefactos_de_figura(self, df_id):
        ids = self.indice.art_por_hf.get(str(df_id), [])
        return [{"df_id": a, "nombre": v(self.indice.artefactos[a], "name"),
                 "tipo": v(self.indice.artefactos[a], "item_type"),
                 "certainty": FACT} for a in ids]

    def artefactos_de_entidad(self, df_id):
        """Artefactos situados en sitios de la entidad (DERIVED por pertenencia)."""
        sitios = self.indice.ent_por_sitio.get(str(df_id), [])
        out = []
        for s in sitios:
            for a in self.indice.art_por_sitio.get(s, []):
                out.append({"df_id": a, "nombre": v(self.indice.artefactos[a], "name"),
                            "sitio_id": s, "certainty": DERIVED,
                            "metodo": "artefacto situado en un sitio de la entidad"})
        return out
# ------------------------------------------------------- RELACIONES SOCIALES
    def relaciones_de_figura(self, df_id, tipo=None, limite=None):
        """Relaciones sociales de legends_plus.xml.

        IMPORTANTE: su `event_id` apunta a eventos que NO existen en
        historical_events. No se asocian a ningún evento.
        """
        filas = []
        for rel in self.indice.rel_por_hf.get(str(df_id), []):
            tipo_rel = v(rel, "relationship")
            if tipo and tipo_rel != tipo:
                continue
            src = str(sin_dato(v(rel, "source_hf")) or "")
            tgt = str(sin_dato(v(rel, "target_hf")) or "")
            otro = tgt if src == str(df_id) else src
            existe = rel.get("event_existe_en_historical_events")
            filas.append({
                "tipo": tipo_rel, "año": sin_dato(v(rel, "year")),
                "figura_id": str(df_id),
                "otra_figura_id": otro,
                "otra_figura_nombre": self.nombre_de("historical_figures", otro),
                "evento_id": rel.get("event_id"),
                "evento_existe": existe,
                "certainty": FACT, "source": rel.get("source"),
                "nota": ("" if existe else
                         "el evento citado no existe en historical_events; "
                         "la relación se conserva sin evento asociado"),
            })
        filas.sort(key=lambda x: (x["año"] is None, x["año"] or 0,
                                  str(x["otra_figura_id"])))
        total = len(filas)
        devueltas = filas[:limite] if limite else filas
        return {"figura_id": str(df_id),
                "nombre": self.nombre_de("historical_figures", df_id),
                "relaciones": devueltas,
                "total": total,
                "devueltos": len(devueltas),
                "truncado": total > len(devueltas),
                "certainty": FACT,
                "nota_grafo": ("El grafo es DIRIGIDO: que A tenga relación con B "
                               "no implica la inversa. La ausencia del inverso "
                               "significa solo que no está registrado.")}

    def amigos(self, df_id):
        return self.relaciones_de_figura(df_id, tipo="childhood_friend")

    def amantes(self, df_id):
        return self.relaciones_de_figura(df_id, tipo="lover")

    def exparejas(self, df_id):
        return self.relaciones_de_figura(df_id, tipo="former_lover")

    def companeros_de_guerra(self, df_id):
        return self.relaciones_de_figura(df_id, tipo="war_buddy")

    def obsesiones(self, df_id):
        return self.relaciones_de_figura(df_id, tipo="jealous_obsession")

    def tipos_relacion_disponibles(self):
        """Todos los tipos presentes en el XML, sin filtrar."""
        c = collections.Counter(v(r, "relationship")
                                for r in self.indice.relaciones
                                if valido(v(r, "relationship")))
        return {"tipos": dict(c), "total_relaciones": len(self.indice.relaciones),
                "certainty": FACT,
                "nota": "tipos literales del XML; no se traducen ni reinterpretan"}

    def cronologia_entidad(self, df_id, limite=None):
        ids = [x for x in self.indice.ev_por_entidad.get(str(df_id), [])
               if x in self.indice.eventos]
        todas = [self._evento_resumido(e)
                 for e in self.indice.eventos_ordenados(ids)]
        filas = todas[:limite] if limite else todas
        anios = [f["año"] for f in todas if f["año"] is not None]
        return {"entidad_id": str(df_id),
                "nombre": self.nombre_de("entities", df_id),
                "total_eventos": len(todas),
                "devueltos": len(filas),
                "truncado": len(todas) > len(filas),
                "rango_anios": [min(anios), max(anios)] if anios else UNKNOWN,
                "linea_temporal": filas, "certainty": FACT}

    def participantes_evento(self, df_id):
        """Quién participó en un evento: figura principal, objetivo y grupos."""
        f = self.c.ficha_evento(str(df_id))
        if f.get("certainty") == UNKNOWN:
            return f
        p = f["participantes"]
        return {
            "evento_id": str(df_id), "tipo": f["tipo"], "subtipo": f["subtipo"],
            "año": f["año"],
            "figura_principal": {"id": p["hfid"],
                                 "nombre": self.nombre_de("historical_figures", p["hfid"])},
            "objetivo": {"id": p["objetivo_hfid"],
                         "nombre": self.nombre_de("historical_figures", p["objetivo_hfid"])},
            "grupo_1": {"id": p["grupo_1_hfid"],
                        "nombre": self.nombre_de("historical_figures", p["grupo_1_hfid"])},
            "grupo_2": {"id": p["grupo_2_hfid"],
                        "nombre": self.nombre_de("historical_figures", p["grupo_2_hfid"])},
            "entidad": f["entidad"], "sitio": f["sitio"], "certainty": FACT}

    def relaciones_adicionales_evento(self, df_id):
        """Relaciones de plus que citan este evento (normalmente ninguna)."""
        return {"evento_id": str(df_id),
                "relaciones": self.c.relaciones_de_evento(str(df_id)),
                "certainty": FACT,
                "nota": ("las 13.192 relaciones de plus citan eventos ausentes; "
                         "esta lista queda vacía para eventos presentes")}
# ------------------------------------------------- CONFLICTOS (DERIVED)
    # Regla EXPLICITA y REPRODUCIBLE para agrupar eventos de conflicto.
    # No crea guerras: crea AGRUPACIONES de eventos, marcadas DERIVED.
    SUBTIPOS_CONFLICTO = (
        "attacked", "ambushed", "confront", "surprised", "scuffle",
        "got into a brawl", "corner", "happen upon",
    )
    TIPOS_CONFLICTO = ("hf simple battle event",)
    CAUSAS_MUERTE_CONFLICTO = ("struck", "murdered", "shot", "exec generic",
                               "exec beheaded", "exec hacked to pieces")

    def conflictos(self, limite_eventos=6000, solo_documentados=True):
        """Agrupa eventos de batalla/ataque según subtipo.

        El agrupamiento es DERIVED. No se afirma que ninguna guerra haya
        ocurrido: solo se enumeran eventos que el XML tipifica como
        enfrentamiento.

        `eventos_de_enfrentamiento` es el TOTAL real del conjunto, no el
        número devuelto. Si se alcanza `limite_eventos`, `truncado` lo dice
        y `total_real` conserva la cifra completa.
        """
        filas = []
        total_real = 0
        for eid in self.indice.eventos_ordenados(list(self.indice.eventos)):
            e = self.indice.eventos[eid]
            t = v(e, "type")
            if t not in self.TIPOS_CONFLICTO:
                continue
            total_real += 1
            if len(filas) >= limite_eventos:
                continue
            st = v(e, "subtype") if valido(v(e, "subtype")) else None
            g1 = sin_dato(v(e, "group_1_hfid"))
            g2 = sin_dato(v(e, "group_2_hfid"))
            sid = sin_dato(v(e, "site_id"))
            filas.append({
                "evento_id": eid,
                "anio": self.indice.anos(e),
                "tipo": t, "subtipo": st,
                "clasificado_como_enfrentamiento": st in self.SUBTIPOS_CONFLICTO,
                "grupo_1_id": g1,
                "grupo_1_nombre": self.nombre_de("historical_figures", g1),
                "grupo_2_id": g2,
                "grupo_2_nombre": self.nombre_de("historical_figures", g2),
                "sitio_id": sid,
                "sitio_nombre": self.nombre_de("sites", sid),
                "certainty": FACT,
                "fuente": "legends.xml · historical_events",
            })
        por_subtipo = collections.Counter(f["subtipo"] for f in filas)
        return {
            "eventos_de_enfrentamiento": total_real,
            "eventos_devueltos": len(filas),
            "total_real": total_real,
            "truncado": total_real > len(filas),
            "por_subtipo": dict(por_subtipo),
            "por_subtipo_total": dict(self._subtipos_totales()),
            "regla": ("event.type == 'hf simple battle event'; "
                      "clasificado como enfrentamiento si subtype pertenece a "
                      + str(list(self.SUBTIPOS_CONFLICTO))),
            "certainty": DERIVED,
            "advertencia": ("esto NO demuestra guerras. El XML no contiene una "
                            "tabla de guerras; solo eventos tipificados."),
            "trazabilidad": ("cada elemento de 'eventos' conserva evento_id, "
                             "anio, sitio y grupos: la agrupacion es reproducible "
                             "y auditable evento a evento"),
            "eventos": filas,
        }

    def _subtipos_totales(self):
        """Recuento de subtipos sobre TODO el conjunto, sin limite."""
        c = collections.Counter()
        for e in self.indice.eventos.values():
            if v(e, "type") not in self.TIPOS_CONFLICTO:
                continue
            c[v(e, "subtype") if valido(v(e, "subtype")) else None] += 1
        return c
    def muertes_por_conflicto(self):
        """Eventos 'hf died' cuya causa es violently (FACT)."""
        filas = []
        for eid, e in self.indice.eventos.items():
            if v(e, "type") != "hf died":
                continue
            cc = v(e, "cause") if valido(v(e, "cause")) else None
            if cc in self.CAUSAS_MUERTE_CONFLICTO:
                hf = sin_dato(v(e, "hfid"))
                filas.append({"evento_id": eid, "año": self.indice.anos(e),
                              "causa": cc, "figura_id": hf,
                              "figura_nombre": self.nombre_de("historical_figures", hf),
                              "certainty": FACT})
        filas.sort(key=lambda x: (x["año"] or 0, x["evento_id"]))
        por_causa = collections.Counter(f["causa"] for f in filas)
        return {"total": len(filas), "por_causa": dict(por_causa),
                "certainty": FACT, "eventos": filas}

    # ------------------------------------------------------------ GEOGRAFIA
    def geografia(self):
        def resumen(rs, campo):
            return {"registros": len(rs),
                    "con_nombre": sum(1 for r in rs if valido(v(r, "name"))),
                    "ejemplos": [{"df_id": r["df_id"], "nombre": v(r, "name"),
                                  "coordenadas": v(r, campo)}
                                 for r in rs[:3]],
                    "certainty": FACT}
        return {
            "rivers": resumen(self._rivers, "path"),
            "landmasses": resumen(self._landmasses, "coord_1"),
            "mountain_peaks": resumen(self._peaks, "coords"),
            "world_constructions": resumen(self._wcs, "coords"),
            "nota_rivers": ("los ríos no tienen <id> en el XML: su record_id "
                            "es DERIVED (hash del contenido)"),
            "certainty": FACT}

    def listar_geografia(self, capa, limite=100, offset=0, con_coordenadas=True):
        """Listado paginado de una capa geografica.

        `capa` ∈ rivers, landmasses, mountain_peaks, world_constructions.
        Los rios NO tienen <id> en el XML: su `df_id` es un hash DERIVED.
        """
        capas = {"rivers": (self._rivers, "path"),
                 "landmasses": (self._landmasses, "coord_1"),
                 "mountain_peaks": (self._peaks, "coords"),
                 "world_constructions": (self._wcs, "coords")}
        par = capas.get(capa)
        if par is None:
            return {"certainty": UNKNOWN, "items": [], "total_encontrados": 0,
                    "devueltos": 0, "truncado": False, "offset": 0,
                    "limite": limite, "capa": capa,
                    "capas_disponibles": sorted(capas),
                    "motivo": f"capa geográfica desconocida: {capa!r}"}
        registros, campo = par
        total = len(registros)
        off = max(0, int(offset or 0))
        pagina = registros[off:off + limite] if limite else registros[off:]
        items = []
        for r in pagina:
            fila = {"df_id": r.get("df_id"),
                    "nombre": v(r, "name") if valido(v(r, "name")) else UNKNOWN,
                    "certainty": FACT}
            if capa != "rivers":
                fila["tipo"] = (v(r, "type") if valido(v(r, "type"))
                                else UNKNOWN)
            if con_coordenadas:
                fila["coordenadas"] = (coords_primeras(v(r, campo)) or UNKNOWN)
                fila["coordenadas_bruto"] = v(r, campo)
            items.append(fila)
        return {"items": items, "capa": capa,
                "total_encontrados": total, "devueltos": len(items),
                "truncado": (off + len(items)) < total,
                "offset": off, "limite": limite, "certainty": FACT,
                "nota_derivada": ("El df_id de los ríos es DERIVED (hash del "
                                  "contenido): el XML no les asigna <id>.")
                if capa == "rivers" else None}

    def construir_en_coordenada(self, x, y):
        """Construcciones cuya ruta pasa por (x,y). Enlace DERIVED."""
        out = []
        for wc in self._wcs:
            crds = coords_primeras(v(wc, "coords"))
            if (int(x), int(y)) in crds:
                out.append({"df_id": wc["df_id"], "nombre": v(wc, "name"),
                            "tipo": v(wc, "type"), "certainty": DERIVED,
                            "metodo": "coordenada exacta compartida"})
        return {"coordenada": [int(x), int(y)], "construcciones": out,
                "total": len(out), "certainty": DERIVED}
# ------------------------------------------------------ GEOGRAFÍA POR PUNTO
    # Semántica: son las "world coordinates" de Dwarf Fortress, un parche (x, y)
    # del mapa global. Los datos NO contienen Z en ningún campo, así que `z` se
    # devuelve siempre como None y su ausencia se declara como FACT, no como un
    # valor inventado.
    COORDENADAS = {
        "x": "columna en el mapa global del mundo (world coordinates)",
        "y": "fila en el mapa global del mundo (world coordinates)",
        "z": "NO EXISTE en los datos de Legends: se devuelve null",
        "metodo": "coordenada exacta compartida (x, y)",
        "distancia": "no se calcula ninguna: la coincidencia es exacta",
    }

    def _sitio_minimo(self, sid):
        """Ficha corta de un sitio, con su tipo REAL (nunca 'site')."""
        s = self.indice.sitios[sid]
        return {"df_id": sid,
                "nombre": v(s, "name") if valido(v(s, "name")) else UNKNOWN,
                "tipo": v(s, "type") if valido(v(s, "type")) else UNKNOWN,
                "coordenadas": [list(par) for par in
                                coords_primeras(v(s, "coords"))],
                "certainty": FACT}

    def _capas_en(self, xi, yi, nombres):
        """Registros de las capas indicadas que tocan exactamente (x, y)."""
        campos = {"world_constructions": "coords", "mountain_peaks": "coords",
                  "landmasses": "coord_1", "rivers": "path"}
        regs = {"world_constructions": self._wcs,
                "mountain_peaks": self._peaks,
                "landmasses": self._landmasses, "rivers": self._rivers}
        salida = {}
        for nombre in nombres:
            ids = self.capas_por_coordenada.get((nombre, xi, yi), [])
            items = []
            for r in regs[nombre]:
                if r.get("df_id") not in ids:
                    continue
                fila = {"df_id": r.get("df_id"),
                        "nombre": (v(r, "name") if valido(v(r, "name"))
                                   else UNKNOWN),
                        "certainty": FACT}
                if nombre != "rivers":
                    fila["tipo"] = (v(r, "type") if valido(v(r, "type"))
                                    else UNKNOWN)
                fila["coordenadas"] = [list(c) for c in
                                       coords_primeras(v(r, campos[nombre]))]
                items.append(fila)
            salida[nombre] = items
        return salida

    def geografia_en_coordenada(self, x, y):
        """Todo lo que el XML sitúa EXACTAMENTE en (x, y).

        Los sitios y las capas son FACT (posiciones leídas del XML). El hecho de
        que compartan ese parche es un enlace DERIVED: NO significa que estén
        relacionados entre sí.
        """
        xi, yi = int(x), int(y)
        sitios = [self._sitio_minimo(s) for s in
                  self.sitios_por_coordenada.get((xi, yi), [])]
        capas = self._capas_en(xi, yi, ("world_constructions", "mountain_peaks",
                                        "landmasses", "rivers"))
        return {"coordenada": {"x": xi, "y": yi, "z": None},
                "coordenadas": self.COORDENADAS,
                "sitios": sitios,
                "total_sitios": len(sitios),
                "capas": capas,
                "total_registros_capas": sum(len(c) for c in capas.values()),
                "certainty": FACT,
                "certainty_enlace": DERIVED,
                "motivo": None}

    def geografia_en_area(self, x, y, ancho=32, alto=32, incluir_capas=False):
        """Sitios dentro de un rectángulo. Para dibujar un viewport de mapa.

        `incluir_capas` está apagado a propósito: las 4 capas suman más de 2.500
        registros y ningún mapa los necesita para situar los sitios.
        """
        xi, yi, an, al = int(x), int(y), int(ancho), int(alto)
        if an <= 0 or al <= 0:
            return {"area": None, "certainty": UNKNOWN,
                    "motivo": "el area debe tener tamano positivo",
                    "sitios": [], "total_sitios": 0}
        area = {"x": xi, "y": yi, "ancho": an, "alto": al,
                "x_max": xi + an - 1, "y_max": yi + al - 1}
        out = []
        for dx in range(an):
            for dy in range(al):
                for sid in self.sitios_por_coordenada.get((xi + dx, yi + dy), ()):
                    out.append(self._sitio_minimo(sid))
        # Orden estable por coordenada y luego por id: dos llamadas iguales
        # deben devolver SIEMPRE la misma lista.
        out.sort(key=lambda s: (s["coordenadas"][0] if s["coordenadas"]
                                else [0, 0], s["df_id"]))
        res = {"area": area, "coordenadas": self.COORDENADAS,
               "sitios": out, "total_sitios": len(out), "certainty": FACT}
        if incluir_capas:
            campos = {"world_constructions": "coords",
                      "mountain_peaks": "coords", "landmasses": "coord_1"}
            regs = {"world_constructions": self._wcs,
                    "mountain_peaks": self._peaks, "landmasses": self._landmasses}
            capas = {}
            for nombre in campos:
                items = []
                for r in regs[nombre]:
                    crds = coords_primeras(v(r, campos[nombre]))
                    if not crds:
                        continue
                    if any(area["x"] <= cx <= area["x_max"] and
                           area["y"] <= cy <= area["y_max"] for cx, cy in crds):
                        items.append({"df_id": r.get("df_id"),
                                      "nombre": (v(r, "name")
                                                 if valido(v(r, "name"))
                                                 else UNKNOWN),
                                      "tipo": (v(r, "type")
                                               if valido(v(r, "type"))
                                               else UNKNOWN),
                                      "coordenadas": [list(c) for c in crds],
                                      "certainty": FACT})
                items.sort(key=lambda r: r["df_id"] or "")
                capas[nombre] = items
            res["capas"] = capas
        return res
# ------------------------------------------------------------ EXPORTACIÓN
    FUENTES = {
        "legends.xml": "Export original de Dwarf Fortress (CP437). Fuente primaria.",
        "legends_plus.xml": ("Export complementario de Dwarf Fortress (UTF-8). "
                             "Relaciones, geografía e identidades."),
    }

    def _envolver(self, datos, titulo):
        return {
            "titulo": titulo,
            "generado_por": "DF-Chronicles :: nucleo.Archivo",
            "certainty_global": datos.get("certainty", UNKNOWN),
            "fuentes": list(self.FUENTES),
            "aviso": ("Los valores proceden de los XML de Dwarf Fortress. "
                      "'UNKNOWN' significa que el dato no consta; no se inventa."),
            "datos": datos,
        }

    def exportar_json(self, datos, titulo, ruta=None):
        obj = self._envolver(datos, titulo)
        texto = json.dumps(obj, ensure_ascii=False, indent=1)
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto)
        return texto

    def exportar_markdown(self, datos, titulo, ruta=None):
        """Exporta una ficha o consulta como Markdown estructurado (sin prosa)."""
        L = [f"# {titulo}", ""]
        L.append(f"- **Certeza global:** {datos.get('certainty', UNKNOWN)}")
        L.append("- **Fuentes:** " + ", ".join(f"`{k}`" for k in self.FUENTES))
        L.append(f"- **Generado por:** DF-Chronicles · nucleo.Archivo")
        L.append("")
        L.append("> Los datos proceden de los exports XML de Dwarf Fortress.")
        L.append("> `UNKNOWN` significa que el dato no consta; no se inventa.")
        L.append("")

        def tabla(filas, cols, titulo_t, maximo=200):
            if not filas:
                return
            L.append(f"## {titulo_t}")
            if len(filas) > maximo:
                L.append(f"> **Tabla truncada:** se muestran {maximo} de "
                         f"{len(filas)} filas. Use la exportación JSON para el "
                         f"conjunto completo.")
            L.append("| " + " | ".join(cols) + " |")
            L.append("|" + "|".join(["---"] * len(cols)) + "|")
            for f in filas[:maximo]:
                L.append("| " + " | ".join(str(f.get(c, "")) for c in cols) + " |")
            L.append("")

        if datos.get("certainty") == UNKNOWN and datos.get("motivo"):
            L.append(f"**Sin datos:** {datos['motivo']}")
            L.append("")
            texto = "\n".join(L)
        else:
            ident = {k: v for k, v in datos.items()
                     if not isinstance(v, (list, dict))}
            L.append("## Ficha")
            for k, v in ident.items():
                L.append(f"- **{k}:** {v}")
            L.append("")
            if "eventos" in datos or "acontecimientos" in datos:
                tabla(datos.get("acontecimientos") or datos.get("eventos"),
                      ["año", "tipo", "subtipo", "figura_nombre", "sitio_nombre"],
                      "Acontecimientos")
            if "linea_temporal" in datos:
                tabla(datos["linea_temporal"],
                      ["año", "segundos72", "tipo", "sitio_nombre", "entidad_nombre"],
                      "Línea temporal")
            if "relaciones" in datos:
                tabla(datos["relaciones"],
                      ["tipo", "año", "otra_figura_nombre"], "Relaciones sociales")
            if "figuras" in datos and isinstance(datos["figuras"], list):
                tabla(datos["figuras"], ["df_id", "nombre", "race", "eventos"],
                      "Figuras")
            if "sitios" in datos and isinstance(datos["sitios"], list):
                tabla(datos["sitios"], ["df_id", "nombre", "tipo"], "Sitios")
            if "eventos_de_enfrentamiento" in datos:
                tabla(datos.get("eventos"), ["año", "subtipo", "grupo_1_nombre",
                                             "grupo_2_nombre", "sitio_nombre"],
                      "Eventos de enfrentamiento (DERIVED)")
            texto = "\n".join(L)
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto)
        return texto

    def exportar_historia_figura(self, df_id, formato="json", ruta=None):
        """Atajo: historia completa de una figura en JSON o Markdown."""
        datos = self.ficha_figura(str(df_id))
        titulo = f"Historia de {datos.get('nombre', df_id)} (df_id {df_id})"
        if formato == "json":
            return self.exportar_json(datos, titulo, ruta)
        return self.exportar_markdown(datos, titulo, ruta)


if __name__ == "__main__":
    a = Archivo(verbose=True)
    print(f"Figuras: {len(a.indice.figuras):,} | Eventos: {len(a.indice.eventos):,}")
    f = a.ficha_figura("712")
    print(f"\nFigura 712: {f['nombre']} ({f['race']})")
    print(f"  eventos={len(f['acontecimientos'])} relaciones={f['relaciones_sociales']['total']}")
