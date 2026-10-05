#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles :: motor de cronica (v1) - DETERMINISTA, sin IA.
=================================================================

QUE ES
-----
Convierte los registros del dataset DF Chronicles en una cronologia navegable:
entidades, eventos y linea temporal. **No inventa nada.**

REGLA DE ORO DEL MOTOR
----------------------
    NO DATA  ->  NO CLAIM
    AUSENCIA  !=  NEGACION

Un personaje que no aparece en un tick **no ha muerto**: sencillamente no se ha
observado. El motor nunca fabrica un DEATH por ausencia.

LOS CINCO CONCEPTOS, SEPARADOS
-------------------------------
    OBSERVATION  lo que se recibio de una fuente, en un momento
    ENTITY       algo persistente dentro del conocimiento disponible
    STATE        como conocemos una entidad en un tick concreto
    EVENT        un cambio demostrable (OBSERVED o DERIVED)
    TIMELINE     eventos ordenados de forma estable

CONTRATO DE ENTRADA (el real del dataset, no uno inventado)
------------------------------------------------------------
Cada linea de `00_SOURCE/processed/*.jsonl` trae:
    record_id, df_id, certainty, source, source_section, campos

DETERMINISMO
------------
Misma entrada -> misma salida. Sin reloj, sin azar, sin estado global mutable,
sin depender del orden de llegada de los JSONL. El identificador de evento se
DERIVA de su contenido: nunca es aleatorio.
"""
from __future__ import annotations

import hashlib

OBSERVED = "OBSERVED"
DERIVED = "DERIVED"

BIRTH = "BIRTH"
DEATH = "DEATH"
ARRIVAL = "ARRIVAL"
DEPARTURE = "DEPARTURE"
CONSTRUCTION = "CONSTRUCTION"
DESTRUCTION = "DESTRUCTION"
COMBAT = "COMBAT"
MIGRATION = "MIGRATION"
PROFESSION_CHANGED = "PROFESSION_CHANGE"

#: Tipos que el motor PUEDE emitir. No se crean otros.
PERMITIDOS = frozenset((BIRTH, DEATH, ARRIVAL, DEPARTURE,
                        CONSTRUCTION, DESTRUCTION, COMBAT, MIGRATION,
                        PROFESSION_CHANGED))


# ================================================================= IDENTIDAD
def id_de_evento(tipo, entidad, tick, evidencia):
    """Identificador DETERMINISTA, derivado del contenido.

    Dos ejecuciones con la misma entrada producen el mismo ID; nunca un UUID
    aleatorio.
    """
    semilla = "|".join((str(tipo), str(entidad), str(tick),
                        ",".join(sorted(str(e) for e in (evidencia or ())))))
    return "ev_" + hashlib.sha256(semilla.encode("utf-8")).hexdigest()[:20]


def identidad_de_entidad(tipo, df_id):
    """Identidad de entidad y estatus de identidad.

    Sin `df_id` NO se inventa uno: se declara `NOT_PROVEN` y la entidad queda
    identificada por su `record_id`, que es de REGISTRO, no del mundo.
    """
    if df_id is None or str(df_id).strip() == "":
        return {"entity_id": None, "identity_status": "NOT_PROVEN",
                "nota": "sin df_id: la identidad de mundo NO esta demostrada"}
    return {"entity_id": str(df_id), "identity_status": "DEMONSTRATED",
            "nota": None}


# ================================================================== ENTIDADES
def entidad_de_registro(registro):
    """Construye una ENTIDAD desde un registro real del dataset."""
    campos = registro.get("campos") or {}
    tipo = registro.get("source_section") or "desconocido"
    ident = identidad_de_entidad(tipo, registro.get("df_id"))
    nombre = (campos.get("name") or campos.get("nombre")
              or campos.get("name_singular"))
    return {
        "entity_type": tipo,
        "entity_id": ident["entity_id"],
        "identity_status": ident["identity_status"],
        "identity_note": ident["nota"],
        "display_name": nombre,
        "certainty": registro.get("certainty"),
        "provenance": {
            "record_id": registro.get("record_id"),
            "source": registro.get("source"),
            "source_section": registro.get("source_section"),
        },
    }
# ==================================================================== EVENTOS
def evento_observado(tipo, entidad, tick, evidencia, certainty, resumen):
    """Evento leido LITERALMENTE del dataset. `origin = OBSERVED`.

    Se usa SOLO si el dataset contiene el evento. El motor no lo inventa.
    """
    if tipo not in PERMITIDOS:
        raise ValueError("tipo de evento no permitido: %r" % (tipo,))
    return {
        "event_id": id_de_evento(tipo, entidad, tick, evidencia),
        "event_type": tipo, "tick": tick, "subject": entidad,
        "origin": OBSERVED, "certainty": certainty, "summary": resumen,
        "evidence": list(evidencia or ()),
    }


def evento_derivado_profesion(entidad, tick_anterior, tick_actual,
                               prof_anterior, prof_actual, evidencia):
    """Evento DERIVED por COMPARACION de dos observaciones.

    Solo se emite si hay procedencia, ambos estados son conocidos y difieren.
    NO se emite si falta cualquiera de esas condiciones.
    """
    if not evidencia:
        return None
    if prof_anterior is None or prof_actual is None:
        return None
    if str(prof_anterior) == str(prof_actual):
        return None
    return {
        "event_id": id_de_evento(PROFESSION_CHANGED, entidad, tick_actual,
                                 evidencia),
        "event_type": PROFESSION_CHANGED, "tick": tick_actual,
        "subject": entidad, "origin": DERIVED, "certainty": "DERIVED",
        "summary": {"de": prof_anterior, "a": prof_actual,
                    "tick_anterior": tick_anterior},
        "evidence": list(evidencia),
    }


# =================================================================== TIMELINE
#: Orden ESTABLE, documentado. No accidental.
ORDEN_CLAVES = ("tick", "event_type", "entity_id", "event_id")


def _clave_orden(ev):
    """Clave de orden. Un evento SIN tick va al principio: no se sabe cuando."""
    t = ev.get("tick")
    return (-1 if t is None else t, str(ev.get("event_type") or ""),
            str(ev.get("subject") or ""), str(ev.get("event_id") or ""))


def ordenar(eventos):
    """Ordena de forma ESTABLE. No depende del orden de llegada."""
    return sorted(eventos, key=_clave_orden)


def deduplicar(eventos):
    """Idempotencia por `event_id`, que es determinista.

    Procesar dos veces el mismo dataset produce el MISMO conjunto logico.
    """
    vistos, salida = set(), []
    for ev in ordenar(eventos):
        eid = ev.get("event_id")
        if eid in vistos:
            continue
        vistos.add(eid)
        salida.append(ev)
    return salida


def construir_timeline(eventos):
    """Pipeline completo: deduplicar -> ordenar. Determinista e idempotente."""
    return deduplicar(eventos)


def timeline_de_entidad(timeline, entidad):
    return [e for e in timeline if e.get("subject") == entidad]


def filtrar_por_tipo(timeline, tipo):
    return [e for e in timeline if e.get("event_type") == tipo]


def filtrar_por_rango(timeline, tick_ini, tick_fin):
    """Rango temporal INCLUSIVO.

    Un evento SIN tick NO entra: no se sabe cuando ocurrio, y una cronologia
    no puede inventar su posicion.
    """
    salida = []
    for e in timeline:
        t = e.get("tick")
        if t is None:
            continue
        if tick_ini is not None and t < tick_ini:
            continue
        if tick_fin is not None and t > tick_fin:
            continue
        salida.append(e)
    return salida


# ============================================================ ESTADO HISTORICO
def estado_en_tick(estados, entidad, tick):
    """¿Que sabiamos de `entidad` en `tick`?

    **NO interpola.** Sin observacion en ese tick devuelve `NOT_AVAILABLE`:
    rellenar el hueco seria inventar.
    """
    aplicables = [e for e in estados
                  if e.get("entidad") == entidad and e.get("tick") == tick]
    if not aplicables:
        return {"entidad": entidad, "tick": tick, "estado": None,
                "certainty": None, "status": "NOT_AVAILABLE",
                "evidence": [], "nota": "sin observacion: NO se interpola"}
    ultimo = sorted(aplicables, key=lambda e: str(e.get("evidence")))[-1]
    return {"entidad": entidad, "tick": tick, "estado": ultimo.get("estado"),
            "certainty": ultimo.get("certainty"), "status": "AVAILABLE",
            "evidence": ultimo.get("evidence"), "nota": None}


# ================================================================ SNAPSHOT
def fortress_snapshot(entidades, eventos, tick=None):
    """Representacion determinista de lo CONOCIDO de la fortaleza.

    **No inventa edificios ni recursos**: si el dataset no los expone de forma
    fiable, se declara `NOT_AVAILABLE`.
    """
    ids = set()
    for e in entidades:
        if e.get("entity_type") == "historical_figures":
            ids.add(e.get("entity_id")
                    or (e.get("provenance") or {}).get("record_id"))
    conocidos = sorted(i for i in ids if i)
    # `construir_timeline` deduplica Y ordena. Devolver los eventos tal cual
    # haria que el snapshot dependiera del ORDEN de entrada: dos ejecuciones
    # iguales darian snapshots distintos. Es lo que trapped este test.
    return {
        "poblacion_conocida": len(conocidos),
        "figuras_conocidas": conocidos,
        "edificios": "NOT_AVAILABLE",
        "edificios_nota": "el dataset esencial no los expone de forma fiable",
        "recursos": "NOT_AVAILABLE",
        "recursos_nota": "no se ha demostrado una fuente fiable PRE-IA",
        "total_eventos": len(eventos),
        "eventos_en_tick": (construir_timeline(filtrar_por_rango(
            eventos, tick, tick)) if tick is not None
            else construir_timeline(eventos)),
        "certainty": "DERIVED",
        "nota": "snapshot de lo CONOCIDO, no del mundo completo",
    }
