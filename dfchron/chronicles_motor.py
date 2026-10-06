#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: CONSTRUCTOR DE CRONICA.
============================================

Pasa de REGISTROS CRUDOS a la CRONICA COMPLETA: filas ordenadas, figuras con
estado, snapshot, informe de ingestion.

`chronicles_datos` LEE el dataset real (IO, cache, huella). Este modulo no
toca ficheros: recibe registros por parametro. Eso lo permite usar con
FIXTURES deterministas pequenas, que es lo que hace posible un test
end-to-end de verdad sin depender de 57.215 lineas.

NO DESCARTA NADA
----------------
`informe["por_grado"]` cuenta TODOS los registros de entrada; la suma tiene
que cuadrar con el total. Cada registro sale como evento (con `event_id`) o
como observacion declarada (con `record_id` y `grado`). Si alguna rama
empezara a descartar en silencio, la prueba de drops lo delataria porque la
suma dejaria de cuadrar.

AUSENCIA DE DECESO NO ES DECESO
-------------------------------
Una figura sin evento `DEATH` NO se marca como muerta: se declara
`NOT_AVAILABLE` con su motivo. Es la diferencia entre «murio» y «no he
encontrado su muerte».
"""
from __future__ import annotations

from . import chronicles as ch
from . import chronicles_evento as ce
from . import chronicles_vocab as vocab

DEATH = "DEATH"


# ==================================================================== FIGURAS ===
def _indice_decesos(eventos):
    """`hfid -> [event_id]` de los eventos DEATH. Orden determinista."""
    idx = {}
    for e in eventos:
        if e.get("event_type") == DEATH:
            idx.setdefault(e["hfid"], []).append(e["event_id"])
    for k in idx:
        idx[k] = sorted(idx[k])
    return idx


def _indice_eventos(eventos):
    """`hfid -> [fila]`, para la cobertura temporal de cada figura."""
    idx = {}
    for e in eventos:
        h = e.get("hfid")
        if h:
            idx.setdefault(h, []).append(e)
    return idx


def _estado_de_figura(hfid, decesos, cobertura_eventos):
    """Estado y cobertura temporal de UNA figura.

    - Con `DEATH`: `AVAILABLE` con la certidumbre DEL EVENTO (no la nuestra).
    - Sin `DEATH`: `NOT_AVAILABLE` con motivo. **No se escribe «vivo»**: eso
      afirmaria algo que nadie observo.

    La cobertura es un min/max sobre los eventos de la figura: `DERIVED`,
    nunca `FACT`.
    """
    if hfid and hfid in decesos:
        estado = {"valor": "DEATH", "status": "AVAILABLE", "certainty": None,
                  "evidence": decesos[hfid],
                  "motivo": "evento DEATH observado en Chronicles"}
    else:
        estado = {"valor": None, "status": "NOT_AVAILABLE",
                  "certainty": vocab.NOT_AVAILABLE, "evidence": [],
                  "motivo": "sin evento DEATH en Chronicles: la ausencia de "
                            "evidencia NO es evidencia de ausencia; no se "
                            "declara viva ni muerta"}

    props = cobertura_eventos.get(hfid) or []
    if not props:
        cobertura = {"status": "NOT_AVAILABLE",
                     "certainty": vocab.NOT_AVAILABLE,
                     "motivo": "esta figura no tiene eventos en Chronicles"}
    else:
        ordenados = sorted(props, key=ce.clave_de_orden)
        primero, ultimo = ordenados[0], ordenados[-1]
        cobertura = {
            "status": "AVAILABLE", "certainty": vocab.DERIVED,
            "desde": dict(primero.get("time") or {}),
            "hasta": dict(ultimo.get("time") or {}),
            "motivo": "min/max sobre los eventos Chronicles de la figura; "
                      "DERIVED porque es un calculo nuestro, no un hecho "
                      "declarado por el dataset",
        }
    return estado, cobertura


def _fecha_de_figura(campos, anio_campo, seg_campo):
    """`(valor, status)` de birth/death del REGISTRO de la figura.

    `-1` es «DF no lo sabe». Se refleja `NOT_AVAILABLE`: no se convierte en 0
    ni en un anio inventado.
    """
    a = ce.valor_de(campos, anio_campo)
    s = ce.valor_de(campos, seg_campo)
    ausente = (a is None or str(a).strip() in vocab.VALORES_AUSENTES)
    if ausente:
        return {"year": None, "seconds72": None, "status": "NOT_AVAILABLE",
                "certainty": vocab.NOT_AVAILABLE,
                "motivo": "el registro no declara este anio (-1 = no lo se)"}
    seg = None
    if s is not None and str(s).strip() not in vocab.VALORES_AUSENTES:
        seg = ce._entero(s)
        if seg is not None and seg < 0:
            seg = None
    return {"year": ce._entero(a), "seconds72": seg,
            "status": ("AVAILABLE" if seg is not None else "PARTIAL"),
            "certainty": None, "motivo": None}


def construir_figuras(registros_figuras, decesos=None, cobertura=None):
    """Figuras Chronicles desde registros crudos. Orden determinista.

    Reutiliza `ch.entidad_de_registro` (motor existente) para identidad y
    procedencia base: NO se reimplementa esa decision en otro sitio.
    """
    decesos = decesos if decesos is not None else {}
    cobertura = cobertura if cobertura is not None else {}
    salida = []
    for reg in registros_figuras:
        ent = ch.entidad_de_registro(reg)
        campos = reg.get("campos") or {}
        hfid = ent["entity_id"]
        estado, cob = _estado_de_figura(hfid, decesos, cobertura)
        salida.append({
            "hfid": hfid,
            "entity_id": ent["entity_id"],
            "identity_status": ent["identity_status"],
            "identity_note": ent["identity_note"],
            "nombre": ent["display_name"],
            "certainty": ent["certainty"],
            "estado": estado,
            "nacimiento": _fecha_de_figura(campos, "birth_year",
                                           "birth_seconds72"),
            "fallecimiento_registro": _fecha_de_figura(
                campos, "death_year", "death_seconds72"),
            "cobertura_temporal": cob,
            "provenance": ent["provenance"],
        })

    def _k(f):
        h = f.get("hfid")
        if h is not None and str(h).isdigit():
            return (0, int(h), "")
        return (1, 0, str(h))

    return sorted(salida, key=_k)

# ================================================================= CONSTRUCCION
def construir(registros_eventos, registros_figuras=(), registros_sitios=(),
              dataset_id=None):
    """Registros crudos -> CRONICA completa. Determinista y completa.

    Devuelve claves estables:
        filas          ordenadas (year, seconds72, identificador), deduplicadas
        eventos        filas con `event_id` (semantica demostrada)
        observaciones  filas sin `event_id` (NOT_PROVEN / UNSUPPORTED)
        figuras        figuras con estado derivado de la evidencia
        informe        recuento por grado: los numeros CUADRAN o es un bug
        snapshot       lo que la cronica puede demostrar de la fortaleza
    """
    crudas = [ce.fila_de_registro(r) for r in registros_eventos]

    # Informe SOBRE LAS CRUDAS: asi un drop silencioso romperia la suma.
    por_grado = dict((g, 0) for g in vocab.GRADOS)
    tipos = {}
    for f in crudas:
        g = f.get("grado")
        por_grado[g] = por_grado.get(g, 0) + 1
        tipos[f.get("type_raw")] = {"grado": g,
                                    "tipo_chronicle": f.get("event_type")}
    emitidos_crudos = sum(1 for f in crudas if f.get("event_id"))

    filas, fusiones = ce.deduplicar(crudas)
    eventos = [f for f in filas if f.get("event_id")]
    observaciones = [f for f in filas if not f.get("event_id")]

    decesos = _indice_decesos(eventos)
    cobertura = _indice_eventos(eventos)
    figuras = construir_figuras(registros_figuras, decesos, cobertura)

    informe = {
        "registros_eventos": len(crudas),
        "por_grado": por_grado,
        "suma_grados": sum(por_grado.values()),
        "eventos_emitidos": emitidos_crudos,
        "fusiones": fusiones,
        "eventos_unicos": len(eventos),
        "observaciones_declaradas": len(observaciones),
        "tipos_vistos": len(tipos),
        "tipos_emitidos": sorted(t for t in tipos
                                 if tipos[t]["tipo_chronicle"]),
        "sin_drops": sum(por_grado.values()) == len(crudas),
        "derivacion_profesion": vocab.NOT_AVAILABLE,
        "derivacion_nota": ("el dataset no entrega estados por tick: derivar "
                            "PROFESSION_CHANGE seria inventarlo"),
    }

    snapshot = construir_snapshot(eventos, observaciones, figuras,
                                  registros_sitios, informe, dataset_id)
    return {"dataset_id": dataset_id, "filas": filas, "eventos": eventos,
            "observaciones": observaciones, "figuras": figuras,
            "informe": informe, "snapshot": snapshot,
            "contrato": vocab.contrato()}


# =================================================================== SNAPSHOT ==
def construir_snapshot(eventos, observaciones, figuras, registros_sitios,
                       informe, dataset_id):
    """Lo que Chronicles PUEDE demostrar de la fortaleza. Ni un dato mas."""
    anios = [f["time"]["year"] for f in (list(eventos) + list(observaciones))
             if (f.get("time") or {}).get("year") is not None]
    con_deceso = sum(1 for f in figuras
                     if (f.get("estado") or {}).get("status") == "AVAILABLE")

    fortalezas = []
    for reg in registros_sitios:
        campos = reg.get("campos") or {}
        if str(ce.valor_de(campos, "type", "")) != "fortress":
            continue
        fortalezas.append({
            "site_id": reg.get("df_id"),
            "nombre": ce.valor_de(campos, "name"),
            "coords": ce.valor_de(campos, "coords"),
            "tipo": "fortress",
            "certainty": reg.get("certainty"),
            "provenance": {"record_id": reg.get("record_id"),
                           "source": reg.get("source"),
                           "source_section": reg.get("source_section")},
        })

    def _ks(f):
        s = str(f["site_id"])
        return (0, int(s), "") if s.isdigit() else (1, 0, s)

    fortalezas.sort(key=_ks)

    if anios:
        periodo = {"desde_year": min(anios), "hasta_year": max(anios),
                   "certainty": vocab.DERIVED,
                   "motivo": "min/max del campo `year` sobre los eventos de "
                             "Chronicles. NO es ticks: la constante de "
                             "conversion a ticks no esta demostrada"}
    else:
        periodo = {"desde_year": None, "hasta_year": None,
                   "certainty": vocab.NOT_AVAILABLE,
                   "motivo": "ningun evento con year utilizable"}

    return {
        "dataset_id": dataset_id,
        "identidad_fortaleza": {
            "status": vocab.NOT_PROVEN,
            "motivo": "el dataset declara %d sitios de tipo `fortress`, pero "
                      "legends.xml NO declara cual es la fortaleza del "
                      "jugador: elegir uno seria inventarlo"
                      % len(fortalezas),
        },
        "fortalezas_conocidas": fortalezas,
        "figuras": {"total": len(figuras), "con_deceso": con_deceso,
                    "certainty": vocab.DERIVED,
                    "motivo": "recuento sobre las figuras de Chronicles y "
                              "sus eventos DEATH"},
        "eventos": {"eventos": len(eventos),
                    "observaciones": len(observaciones),
                    "registros": informe["registros_eventos"],
                    "fusiones": informe["fusiones"],
                    "por_grado": dict(informe["por_grado"]),
                    "certainty": vocab.DERIVED},
        "periodo": periodo,
        "edificios": vocab.NOT_AVAILABLE,
        "edificios_nota": "Chronicles V1 no demostro una fuente fiable",
        "recursos": vocab.NOT_AVAILABLE,
        "recursos_nota": "Chronicles V1 no demostro una fuente fiable",
        "certainty": vocab.DERIVED,
        "nota": "snapshot de lo CONOCIDO por Chronicles, no del mundo completo",
    }

# ==================================================================== CONSULTA ==
def consultar(cronica, limite, offset=0, hfid=None, tipo=None, tipo_raw=None,
              year=None, desde=None, hasta=None, grado=None):
    """Filtro + orden obligatorio + paginacion, sobre la cronica.

    `(desde, hasta)` son pares `(year, seconds72)` inclusivos. La lista sale
    SIEMPRE ordenada por `year`, `seconds72`, identificador, asi que el corte
    de pagina es estable e independiente del orden del JSONL de origen.
    """
    filtradas = ce.filtrar(cronica.get("filas") or (),
                           hfid=hfid, tipo=tipo, tipo_raw=tipo_raw,
                           year=year, desde=desde, hasta=hasta, grado=grado)
    pagina, total, truncado = ce.paginar(filtradas, limite, offset)
    return {"filas": pagina, "total": total, "devueltos": len(pagina),
            "truncado": truncado, "limit": limite, "offset": offset}


def detalle_evento(cronica, event_id):
    """UN evento por su `event_id`. `None` si no existe (no se inventa)."""
    for e in cronica.get("eventos") or ():
        if e.get("event_id") == event_id:
            return e
    return None


def detalle_observacion(cronica, record_id):
    """UNA observacion por su `record_id`. `None` si no existe."""
    for o in cronica.get("observaciones") or ():
        if o.get("record_id") == record_id:
            return o
    return None


def detalle_figura(cronica, hfid):
    """UNA figura por su `hfid`. `None` si no existe (no se inventa)."""
    objetivo = str(hfid)
    for f in cronica.get("figuras") or ():
        if f.get("hfid") is not None and str(f["hfid"]) == objetivo:
            return f
    return None


def eventos_de_figura(cronica, hfid):
    """Todas las filas referidas a UNA figura. Orden cronologico obligatorio."""
    return ce.filtrar(cronica.get("filas") or (), hfid=str(hfid))