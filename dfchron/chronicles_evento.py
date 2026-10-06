#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: MOTOR DE EVENTOS.
=====================================

Convierte UN registro crudo del dataset en una fila Chronicles, o en una
observacion CLASIFICADA si la semantica no esta demostrada.

Nada desaparece: cada registro del dataset sale de aqui como `event_id`
(evento interpretado) o como `record_id` con su `grade` y su `motivo`
(observacion declarada). Es la garantia contra drops silenciosos.

TIEMPO: (year, seconds72), NUNCA TICKS
--------------------------------------
La representacion temporal V1 es la propia del dataset. NO se convierte a
ticks de DF porque la constante exacta de conversion NO esta demostrada; un
error de una unidad desplazaria eventos enteros sin que nada lo delatara.
`seconds72 = -1` significa «DF no lo sabe» y se refleja como
`time.estado = PARTIAL`, no como un segundo inventado.

IDENTIDAD: DERIVADA DEL CONTENIDO
---------------------------------
`event_id = sha256(event_type | entity | time | payload)`. Depende solo de
los VALORES: igual entrada, igual id, en cualquier proceso, con cualquier
PYTHONHASHSEED y en cualquier orden de lectura. Jamas `uuid4()`, jamas un
reloj. Dos registros con contenido identico son el MISMO hecho: sus
`record_id` se conservan juntos como evidencia, y esa fusion es la
deduplicacion determinista.

DOS TIPOS DE FILA
-----------------
    evento        semantica demostrada. Tiene `event_id` y `event_type`.
    observacion   semantica NO demostrada. Tiene `record_id` y `grade`.

Ambas se ordenan juntas con la MISMA clave, asi que una observacion no
interpretada sigue siendo visible en la cronologia con su `NOT_PROVEN`.

Solo lectura. Determinista. Sin estado mutable entre llamadas.
"""
from __future__ import annotations

import hashlib
import json

from . import chronicles_vocab as vocab

# ====================================================== LECTURA DE CAMPOS ====
# Hallazgo empirico: en el dataset MERGED cada campo NO es un escalar sino un
# objeto de procedencia:
#
#     "year": {"valor": "1", "source": "legends.xml",
#              "source_section": "historical_events"}
#
# Leer `campos["year"]` devuelve ese diccionario. Una lectura ingenua daria un
# dict donde deberia haber un valor, y compararlo contra "1" fallaria EN
# SILENCIO. Estas dos funciones son las unicas formas permitidas de leer.


def valor_de(campos, clave, defecto=None):
    """Valor REAL de un campo, sea escalar u objeto de procedencia."""
    v = (campos or {}).get(clave)
    if isinstance(v, dict):
        return v.get("valor", defecto)
    return defecto if v is None else v


def procedencia_de(campos, clave):
    """Procedencia POR CAMPO. La declara el dataset; el motor no la inventa."""
    v = (campos or {}).get(clave)
    if isinstance(v, dict):
        return {"valor": v.get("valor"), "source": v.get("source"),
                "source_section": v.get("source_section")}
    return None


def _entero(crudo):
    """Entero desde el valor crudo, o `None`. `-1` NO se convierte: lo decide
    el llamador, porque `-1` es «no lo se» en DF y no un numero."""
    if crudo is None:
        return None
    try:
        return int(str(crudo).strip())
    except (TypeError, ValueError):
        return None


# ==================================================================== TIEMPO ===
def tiempo_de(registro):
    """`(year, seconds72)` del registro, con su estado REAL.

        AVAILABLE   hay anio y hay instante dentro del anio
        PARTIAL     hay anio; `seconds72` es -1 o ilegible (DF no lo sabe)
        NOT_AVAILABLE  no hay anio utilizable: no se puede colocar en el tiempo

    NUNCA se genera un `tick`. Ver `chronicles_vocab.TEMPORAL_V1`.
    """
    campos = registro.get("campos") or {}
    crudo_a = valor_de(campos, "year")
    crudo_s = valor_de(campos, "seconds72")

    anio = None if str(crudo_a).strip() in vocab.VALORES_AUSENTES else _entero(crudo_a)
    seg = None if str(crudo_s).strip() in vocab.VALORES_AUSENTES else _entero(crudo_s)
    # `-1` en seconds72 = «no lo se». Es un valor, no un instante.
    if seg is not None and seg < 0:
        seg = None

    if anio is None:
        estado = "NOT_AVAILABLE"
        motivo = "sin year utilizable: el registro no se puede colocar en el tiempo"
    elif seg is None:
        estado = "PARTIAL"
        motivo = "seconds72 ausente o -1: consta el anio, no el instante dentro del anio"
    else:
        estado = "AVAILABLE"
        motivo = None
    salida = {"year": anio, "seconds72": seg,
              "estado": estado, "representacion": vocab.TEMPORAL_V1_NOMBRE}
    if motivo:
        salida["motivo"] = motivo
    return salida


# ================================================================ IDENTIDAD ====
def id_de_evento(event_type, entity, time, payload):
    """`event_id` DETERMINISTA, derivado solo del contenido.

    `json.dumps(sort_keys=True)` fija el orden de las claves (nunca depende de
    la semilla del hash de Python) y `sha256` es estable entre versiones y
    plataformas. El resultado es el mismo en dos procesos, con
    PYTHONHASHSEED distinto y con el JSONL leido en orden distinto.

    NO se incluye `record_id`: dos registros con el mismo contenido son el
    mismo hecho y deben colapsar en un solo evento.
    """
    semilla = json.dumps(
        {"event_type": str(event_type), "entity": str(entity),
         "time": [time.get("year"), time.get("seconds72")],
         "payload": payload},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        default=str)
    return "ev_" + hashlib.sha256(semilla.encode("utf-8")).hexdigest()[:20]


# ============================================================ IDENTIDADES ======
def identidades_de(registro):
    """TODAS las identidades que el registro declara, sin elegir ninguna.

    Para tipos sin semantica demostrada NO se elige «el sujeto»: decidir si en
    `hf wounded` el sujeto es `woundee_hfid` o `wounder_hfid` seria una
    decision semantica sin demostracion. Se listan las identidades que el
    dataset declara y se acabara aqui.
    """
    campos = registro.get("campos") or {}
    salida = []
    for campo in vocab.CAMPOS_SUJETO:
        v = valor_de(campos, campo)
        if v is None or str(v).strip() in vocab.VALORES_AUSENTES:
            continue
        salida.append({"campo": campo, "valor": str(v),
                       "procedencia": procedencia_de(campos, campo)})
    return salida


def _certainty_de(registro):
    """Certidumbre del registro. Si no la trae: `NOT_AVAILABLE`.

    No se asume FACT por existir: el dataset declara su propia certidumbre y
    aqui solo se lee. Ausencia de certidumbre declarada no es certidumbre
    maxima.
    """
    c = registro.get("certainty")
    if c is None or str(c).strip() in ("", "None", "null"):
        return vocab.NOT_AVAILABLE
    return str(c)


# =================================================================== FILA ======
def fila_de_registro(registro):
    """UN registro crudo -> UNA fila Chronicles. **Nunca devuelve `None`.**

    Dos salidas posibles, segun lo que el registro DEMUESTRE:

      evento        regla semantica + sujeto declarado + year
                    -> `event_id`, `event_type`, `grado` SUPPORTED/PARTIAL
      observacion   cualquier otra cosa
                    -> `record_id`, `grado` NOT_PROVEN/UNSUPPORTED + motivo

    Ninguna rama descarta el registro: la rama que no emite evento lo deja
    escrito con su motivo, que es exactamente la informacion que le falta.
    """
    campos = registro.get("campos") or {}
    tipo_raw = str(valor_de(campos, "type", "") or "")
    tiempo = tiempo_de(registro)
    identidades = identidades_de(registro)
    record_id = registro.get("record_id")

    base = {
        "record_id": record_id,
        "type_raw": tipo_raw,
        "certainty": _certainty_de(registro),
        "source": registro.get("source"),
        "source_section": registro.get("source_section"),
        "time": tiempo,
        "identidades": identidades,
        "identity_status": ("DEMONSTRATED" if identidades else "NOT_PROVEN"),
        "event_id": None,
        "event_type": None,
    }

    regla = vocab.SEMANTICA.get(tipo_raw)

    # --- 1. Regla demostrada: se emite EVENTO, o se declara por que no ------
    if regla is not None:
        campo = regla["campo_sujeto"]
        valor = valor_de(campos, campo)
        sin_sujeto = (valor is None
                      or str(valor).strip() in vocab.VALORES_AUSENTES)
        if sin_sujeto:
            return dict(base, grado=vocab.UNSUPPORTED,
                        motivo="sin sujeto utilizable en `%s`: no se inventa "
                               "entidad para un evento %s"
                               % (campo, regla["tipo_chronicle"]),
                        regla=regla["regla"])
        if tiempo["year"] is None:
            return dict(base, grado=vocab.UNSUPPORTED,
                        motivo="sin year utilizable: el %s no se puede "
                               "colocar en la cronica" % regla["tipo_chronicle"],
                        regla=regla["regla"])

        entidad = "hf:%s" % valor
        # Payload = TODOS los campos del registro salvo `type`, que lo
        # sustituye `event_type`. Incluye year/seconds72/hfid: el contenido
        # completo es lo que define la identidad y lo que permite auditar.
        payload = dict((k, valor_de(campos, k))
                       for k in sorted(campos) if k != "type")
        event_id = id_de_evento(regla["tipo_chronicle"], entidad, tiempo, payload)
        grado = (vocab.SUPPORTED if tiempo["estado"] == "AVAILABLE"
                 else vocab.PARTIAL)
        provenance = {
            "record_id": record_id,
            "source": registro.get("source"),
            "source_section": registro.get("source_section"),
            "campos": dict(
                (k, procedencia_de(campos, k)) for k in sorted(campos)
                if procedencia_de(campos, k) is not None),
        }
        fila = dict(base, grado=grado, event_id=event_id,
                    event_type=regla["tipo_chronicle"],
                    entity=entidad, hfid=str(valor),
                    payload=payload, evidence=[record_id],
                    provenance=provenance,
                    regla=regla["regla"], evidencia_regla=regla["evidencia"])
        if grado == vocab.PARTIAL:
            fila["motivo"] = tiempo.get("motivo")
        return fila

    # --- 2. Sin regla demostrada: se DECLARA, nunca se interpreta -----------
    if not identidades:
        return dict(base, grado=vocab.UNSUPPORTED,
                    motivo="sin identidad: ningun campo de sujeto con valor "
                           "(los ausentes NO cuentan como identidad)")
    if tiempo["year"] is None:
        return dict(base, grado=vocab.UNSUPPORTED,
                    motivo="sin year utilizable: no se puede colocar en el "
                           "tiempo y no se inventa fecha")
    return dict(base, grado=vocab.NOT_PROVEN,
                motivo=vocab.SEMANTICA_NO_DEMOSTRADA.get(
                    tipo_raw,
                    "tiempo e identidades presentes, pero la semantica de "
                    "%r no esta demostrada en el dataset" % tipo_raw))


# ================================================== ORDEN, DEDUPE, FILTROS =====
def clave_temporal(fila):
    """`(year, seconds72)`. `None` -> `-1`, la misma convencion que el orden.

    Convencion, no afirmacion: un instante desconocido se coloca al PRINCIPIO
    de su anio en la ordenacion. La alternativa (colocarlo al final) tambien
    seria una afirmacion; esta se eligio por ser la que ya usa el motor
    `chronicles.py` (`-1 if t is None else t`).
    """
    t = fila.get("time") or {}
    y, s = t.get("year"), t.get("seconds72")
    return (-1 if y is None else int(y), -1 if s is None else int(s))


def clave_de_orden(fila):
    """Orden obligatorio: `year`, `seconds72`, identificador.

    El desempate es `event_id` (derivado del contenido) y, para observaciones
    que no son eventos, `record_id` (unico por registro). Los dos son
    deterministas e independientes del orden de lectura del JSONL.
    """
    k = fila.get("event_id") or fila.get("record_id") or ""
    return clave_temporal(fila) + (str(k),)


def ordenar(filas):
    """Orden ESTABLE y determinista. No depende del orden de llegada."""
    return sorted(filas, key=clave_de_orden)


def deduplicar(filas):
    """`(filas, fusiones)`. Eventos con el MISMO contenido colapsan en uno.

    `event_id` solo cubre contenido, asi que dos registros identicos salvo el
    `record_id` son el mismo hecho. Sus `record_id` NO se pierden: se FUSIONAN
    en `evidence` ordenada. La fusion es visible en el informe (`fusiones`),
    nunca silenciosa.

    Las observaciones (sin `event_id`) no colapsan: cada `record_id` es un
    registro distinto del dataset.
    """
    por_id, salida, fusiones = {}, [], 0
    for fila in ordenar(filas):
        eid = fila.get("event_id")
        if eid is None:
            salida.append(fila)
            continue
        if eid in por_id:
            destino = por_id[eid]
            unidos = set(destino.get("evidence") or ())
            unidos.update(fila.get("evidence") or ())
            destino["evidence"] = sorted(unidos)
            fusiones += 1
            continue
        por_id[eid] = fila
        salida.append(fila)
    return salida, fusiones

def filtrar(filas, hfid=None, tipo=None, tipo_raw=None, year=None,
            desde=None, hasta=None, grado=None):
    """Filtros de igualdad EXACTA. Ninguno inventa ni normaliza valores.

    `desde`/`hasta` son pares `(year, seconds72)` INCLUSIVOS y se comparan con
    la MISMA clave que el orden, de modo que un filtro de rango nunca puede
    cruzar una frontera de pagina al reves. Una fila sin `year` queda fuera de
    cualquier rango: no se sabe cuando ocurrio.

    `hfid` casa con el sujeto del evento y con cualquier identidad declarada
    en una observacion: no se elige un «sujeto» que el dataset no eligio.
    """
    salida = []
    for f in filas:
        if hfid is not None:
            objetivo = str(hfid)
            referidos = [f.get("hfid")] + [
                i.get("valor") for i in (f.get("identidades") or ())]
            if objetivo not in [str(x) for x in referidos if x is not None]:
                continue
        if tipo is not None and f.get("event_type") != tipo:
            continue
        if tipo_raw is not None and f.get("type_raw") != tipo_raw:
            continue
        if grado is not None and f.get("grado") != grado:
            continue
        ct = clave_temporal(f)
        if year is not None and ct[0] != int(year):
            continue
        if desde is not None and ct < (int(desde[0]), int(desde[1])):
            continue
        if hasta is not None and ct > (int(hasta[0]), int(hasta[1])):
            continue
        salida.append(f)
    return salida


def paginar(filas, limite, offset=0):
    """`(pagina, total, truncado)`. Corte estable: la lista ya esta ordenada.

    La estabilidad NO depende del orden de insercion: la lista de entrada
    llega SIEMPRE de `deduplicar`, que ordena por la clave obligatoria.
    """
    total = len(filas)
    pagina = filas[offset:offset + limite]
    return pagina, total, (offset + len(pagina)) < total