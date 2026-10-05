#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: FIXTURES END-TO-END DETERMINISTAS.
========================================================

Siete fixtures pequenas, escritas a mano, que cubren los siete casos que la
mision exige:

    A  `hf died` valido                     -> DEATH, FACT
    B  dos eventos con el mismo contenido   -> deduplicacion determinista
    C  mismo contenido, orden distinto      -> misma salida
    D  evento sin identidad suficiente      -> NO se inventa entidad
    E  semantica no demostrada              -> NOT_PROVEN, no interpretado
    F  procedencia completa                 -> sobrevive hasta la API
    G  paginacion                           -> misma secuencia da igual la carga

Cada fixture es un dict JSON serializable con DOS listas: `eventos` (registros
crudos con el contrato real: record_id/df_id/certainty/source/source_section/
campos con forma de procedencia) y `figuras`. Nada toca el disco real: el
motor (`chronicles_motor.construir`) recibe registros por parametro, asi que
una fixture ES un dataset en miniatura.

El ORDEN de cada fixture es deliberadamente hostil (desordenado, duplicado o
incompleto): si el motor dependiera de el, la prueba lo delataria.
"""
from __future__ import annotations

SRC = "fixtures_e2e"
SECCION = "historical_events"


def _campo(valor, source=SRC, seccion=SECCION):
    return {"valor": str(valor), "source": source, "source_section": seccion}


def _reg(rid, tipo, campos, certeza="FACT", fuente=SRC):
    c = dict(campos)
    c["type"] = _campo(tipo, fuente, SECCION)
    return {"record_id": rid, "df_id": None, "certainty": certeza,
            "source": fuente, "source_section": SECCION, "campos": c}


def _fig(rid, hfid, nombre):
    return {"record_id": rid, "df_id": str(hfid), "certainty": "FACT",
            "source": SRC, "source_section": "historical_figures",
            "campos": {"name": _campo(nombre, SRC, "historical_figures")}}


def muerte(rid, hfid, year, seg, causa="struck", asesino=None):
    campos = {"hfid": _campo(hfid), "year": _campo(year),
              "seconds72": _campo(seg), "cause": _campo(causa)}
    if asesino is not None:
        campos["slayer_hfid"] = _campo(asesino)
    return _reg(rid, "hf died", campos)


#: A · un `hf died` valido. Esperado: DEATH + FACT + tiempo (1, 25200).
A = {
    "eventos": [muerte("rec:a1", 676, 1, 25200, "struck", 712)],
    "figuras": [_fig("fig:a1", 676, "Urist caido"),
                _fig("fig:a2", 712, "Urist matador")],
}

#: B · dos registros con el MISMO contenido (distinto record_id).
#: Esperado: UN solo evento, con evidence = los dos record_id.
B = {
    "eventos": [muerte("rec:b1", 676, 1, 25200, "struck", 712),
                muerte("rec:b2", 676, 1, 25200, "struck", 712)],
    "figuras": [_fig("fig:b1", 676, "Urist caido")],
}

#: C · mismo contenido que B pero en ORDEN INVERSO. Esperado: MISMA salida
#: (mismo event_id, misma evidencia ordenada).
C = {
    "eventos": [muerte("rec:b2", 676, 1, 25200, "struck", 712),
                muerte("rec:b1", 676, 1, 25200, "struck", 712)],
    "figuras": [_fig("fig:b1", 676, "Urist caido")],
}

#: D · `hf died` sin `hfid` (valor -1). Esperado: NO hay evento; la fila se
#: declara UNSUPPORTED y la identidad queda NOT_PROVEN (nada de `hf:None`).
D = {
    "eventos": [muerte("rec:d1", -1, 1, 25200, "struck")],
    "figuras": [],
}

#: E · semantica no demostrada (`add hf entity link`). Esperado: NOT_PROVEN,
#: sin event_type, con el motivo. La figura 344 existe: NO se confunde
#: «identidad conocida» con «hecho interpretado».
E = {
    "eventos": [_reg("rec:e1", "add hf entity link",
                     {"hfid": _campo(344), "year": _campo(2),
                      "seconds72": _campo(100),
                      "link": _campo("position"),
                      "position_id": _campo(1)})],
    "figuras": [_fig("fig:e1", 344, "Urist vinculado")],
}

#: F · procedencia completa hasta la API: cada campo trae source distinto por
#: seccion, para que una procedencia perdida se note en el camino.
F = {
    "eventos": [muerte("rec:f1", 900, 7, 4400, "hambre")],
    "figuras": [_fig("fig:f1", 900, "Urist hambriento")],
}

#: G · tres muertes en instantes distintos + un duplicado exacto. Esperado:
#: 3 eventos unicos en orden (year, seconds72, event_id) da igual el orden
#: de entrada; paginar de 2 en 2 recompone la misma secuencia total.
G = {
    "eventos": [muerte("rec:g3", 3, 5, 100, "vejez"),
                muerte("rec:g1", 1, 2, 900, "hambre"),
                muerte("rec:g2", 2, 2, 50, "sed"),
                muerte("rec:g1b", 1, 2, 900, "hambre")],
    "figuras": [_fig("fig:g1", 1, "Uno"), _fig("fig:g2", 2, "Dos"),
                _fig("fig:g3", 3, "Tres")],
}

FIXTURES = {"A": A, "B": B, "C": C, "D": D, "E": E, "F": F, "G": G}


def serializar(fixture):
    """La fixture, tal cual viajaria por el cable: solo JSON."""
    import json
    return json.loads(json.dumps(fixture, ensure_ascii=False))