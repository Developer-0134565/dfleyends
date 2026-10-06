#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: VOCABULARIO CONGELADO Y CONTRATO SEMANTICO.
==============================================================

QUE ES ESTE FICHERO
-------------------
La respuesta documentada a «¿que tipo de evento del dataset es un evento
Chronicle, y con que grado de certeza?». Es un REGISTRO, no una implementacion:
aqui se DECLARA lo demostrado, y `chronicles_evento` lo USA.

LA REGLA QUE LO GOBIERNA
------------------------
> No asumir. Ejecutar, observar, demostrar.

Un tipo NO entra en el mapa por lo que su NOMBRE sugiere. Entra si se ha LEIDO
en sus registros y se ha decidido acceptarlo. Por eso `hf died` si es `DEATH`
—y esta demostrado— mientras que `add hf entity link`, que trae `hfid`, tiempo
y `link`, NO es `ARRIVAL`: el dataset dice que se creo un vinculo, y afirmar
que alguien llego seria inventar el desplazamiento.

LOS CUATRO GRADOS
-----------------
    SUPPORTED    semantica demostrada. Se emite como evento Chronicle.
    PARTIAL      se emite parte de lo que el registro sostiene; el resto se
                 declara no disponible. NUNCA se rellena.
    NOT_PROVEN   no hay regla semantica demostrada. El registro se CONSERVA y
                 se declara, pero NO se presenta como hecho interpretado.
    UNSUPPORTED  no hay nada que emitir. Se cuenta y se declara.

`NOT_PROVEN` NO es un evento descartado: es un HECHO sobre lo que no se ha
demostrado. Y eso tambien viaja hasta la API y la Web, porque un dato que se
esconde no es un dato honesto.
"""
from __future__ import annotations

# ===================================================================== TIEMPO
#: Representacion temporal V1. Es la unica.
#:
#: NO se convierte a ticks de DF. La constante exacta de conversion no esta
#: DEMOSTRADA, y escribirla seria inventar precision que el dataset no tiene.
#: Un error de una unidad en esa constante desplazaria eventos enteros de la
#: cronologia sin que nada lo delatara.
TEMPORAL_V1 = ("year", "seconds72")

#: Nombres de la representacion temporal. Se publican en la API para que un
#: cliente sepa EXACTAMENTE que recibe.
TEMPORAL_V1_NOMBRE = "year+seconds72"

#: Orden cronologico obligatorio. `event_id` actua como desempate
#: determinista: dos eventos del mismo instante siguen teniendo un orden
#: estable, y ese orden no depende del orden de lectura del JSONL.
ORDEN_V1 = ("year", "seconds72", "event_id")


# ==================================================================== CERTEZA
#: Certidumbres Chronicles. `servicio` usa FACT/DERIVED/UNKNOWN; estas son las
#: suyas. Se AÑADEN, no se sustituyen.
FACT = "FACT"
DERIVED = "DERIVED"
NOT_VERIFIED = "NOT_VERIFIED"
NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_PROVEN = "NOT_PROVEN"
CERTEZAS = (FACT, DERIVED, NOT_VERIFIED, NOT_AVAILABLE, NOT_PROVEN)

#: Regla dura: `DERIVED` nunca se presenta como `FACT`. Una afirmacion derivada
#: de comparacion es una INFERENCIA; sin embargo es la unica verificable, y por
#: eso se distingue en todas partes.
CERTEZA_MAS_FUERTE = FACT


# ===================================================================== GRADOS
SUPPORTED = "SUPPORTED"
PARTIAL = "PARTIAL"
NOT_PROVEN = "NOT_PROVEN"
UNSUPPORTED = "UNSUPPORTED"
GRADOS = (SUPPORTED, PARTIAL, NOT_PROVEN, UNSUPPORTED)
# ========================================================= CAMPOS VERIFICADOS
#: Campos temporales. Leidos en las 57.215 lineas: ambos presentes SIEMPRE.
CAMPOS_TEMPORALES = ("year", "seconds72")

#: Campos de sujeto VERIFICADOS barriendo las 57.215 lineas: todos los campos
#: cuyo NOMBRE acaba en `hfid`/`hf_id` (48, ver `inventario_campos.py`), mas
#: los demas identificadores que el barrido encontro (`hist_figure_id`,
#: `entity_id`, `site_id`, `civ_id`, `item_id`, `position_id`,
#: `structure_id`, `occasion_id`, `schedule_id`, `wc_id`).
#:
#: NO incluye `link`: `add hf entity link` trae `link: position`, que es el
#: TIPO de vinculo, no un identificador. Usarlo como sujeto habria convertido
#: 7.534 eventos en «sujetos position» inventados.
#:
#: OJO: que un campo IDENTIFIQUE a una persona NO significa que sea el sujeto
#: PRINCIPAL del evento. `slayer_hfid` identifica a quien MATO, no a quien
#: murio. Por eso la tabla `SEMANTICA` declara, para cada tipo, QUE campo es el
#: sujeto; y por eso `identidades_de()` lista las identidades sin elegir
#: ninguna para los tipos no demostrados.
CAMPOS_SUJETO = (
    "hfid",
    "hfid_target",
    "target_hfid",
    "slayer_hfid",
    "group_1_hfid",
    "group_2_hfid",
    "group_hfid",
    "woundee_hfid",
    "wounder_hfid",
    "competitor_hfid",
    "winner_hfid",
    "hist_figure_id",
    "entity_id",
    "site_id",
    "item_id",
    "structure_id",
    "position_id",
    "civ_id",
    "site_civ_id",
    "occasion_id",
    "schedule_id",
    "wc_id",
    "acquirer_hfid",
    "actor_hfid",
    "attacker_general_hfid",
    "attacker_hfid",
    "builder_hfid",
    "changee_hfid",
    "changer_hfid",
    "coconspirator_hfid",
    "conspirator_hfid",
    "convicted_hfid",
    "corruptor_hfid",
    "creator_hfid",
    "defender_general_hfid",
    "doer_hfid",
    "expelled_hfid",
    "fooled_hfid",
    "framer_hfid",
    "gambler_hfid",
    "implicated_hfid",
    "instigator_hfid",
    "interrogator_hfid",
    "last_owner_hfid",
    "leader_hfid",
    "lure_hfid",
    "modifier_hfid",
    "new_leader_hfid",
    "overthrown_hfid",
    "persecutor_hfid",
    "pos_taker_hfid",
    "property_confiscated_from_hfid",
    "seeker_hfid",
    "site_hfid",
    "snatcher_hfid",
    "speaker_hfid",
    "student_hfid",
    "teacher_hfid",
    "trader_hfid",
    "trickster_hfid",
)

#: Valores con los que el dataset declara «no lo se». Un `-1` NO es un
#: identificador: es la forma que tiene Dwarf Fortress de decir que no lo sabe.
#: Aceptarlo como sujeto seria fabricar una identidad para el valor centinela.
VALORES_AUSENTES = ("", "-1", "-1.0", "None", "null")


# =================================================== CONTRATO SEMANTICO V1
#: tipo_raw -> regla. SOLO entra lo que se ha decidido conscientemente. La
#: clave es el tipo EXACTO del dataset, no un patron: un prefijo exigiria
#: suponer lo que hay detras.
#:
#: `hf died` -> `DEATH` es la equivalencia con evidencia completa
#: (recuento real sobre el dataset, no estimacion):
#:     hfid        quien murio          4.484/4.484
#:     year        anio del hecho       4.484/4.484 (rango 1..100)
#:     cause       como murio           4.484/4.484
#:     slayer_hfid quien lo mato        4.484/4.484
#:     seconds72   instante en el anio  3.540/4.484 (en 944, DF dice -1)
#: El TIPO esta demostrado -> SUPPORTED. El registro que no tiene `seconds72`
#: se emite igual: la muerte consta, el INSTANTE EXACTO no. Se declara
#: `time.estado = PARTIAL` en vez de inventar el segundo ni ocultar el hecho.
SEMANTICA = {
    "hf died": {
        "tipo_chronicle": "DEATH",
        "campo_sujeto": "hfid",
        "grado": SUPPORTED,
        "regla": ("hfid + year + seconds72 + cause + slayer_hfid. El sujeto "
                  "es quien murio; `slayer_hfid` es un PAPEL, no el sujeto."),
        "evidencia": ("4.484 registros, todos con hfid y `cause`; 3.540 con "
                      "(year, seconds72) utilizable. Fuente: legends.xml, "
                      "seccion historical_events."),
    },
}

#: Tipos cuyo nombre SUGIERE una semantica que el dataset NO demuestra. Se
#: declaran aqui para que conste que se considero y se rechazo.
#:
#: Es la parte importante de este fichero. Sin esta lista, un developer
#: tenderia a asumir el significado por el nombre; con ella, cada equivalencia
#: que no este aqui se considera, se comprueba con numero en el lado y se
#: DESCARTA hasta que alguien la demuestre. No basta con que sea verosimil.
SEMANTICA_NO_DEMOSTRADA = {
    "change hf job": ("8.692 registros con hfid y year, pero el dataset NO "
                      "trae NINGUN campo que describa el trabajo: no hay "
                      "`job` ni `position`, solo sitio/subregion. Añadirlo a "
                      "`PROFESSION_CHANGE` seria deducir la profesion del "
                      "NOMBRE del tipo. Ademas solo 107/8.692 tienen "
                      "seconds72 utilizable."),
    "change hf state": ("10.718 registros con hfid; trae `state`, `mood` y "
                        "`reason`, pero el vocabulario de `state` (settled, "
                        "visiting, wandering, be with master...) no esta "
                        "documentado en el dataset y no hay tipo Chronicle "
                        "cuya equivalencia este demostrada. 7.932/10.718 sin "
                        "seconds72."),
    "add hf entity link": ("7.534 registros. `link` toma valores position, "
                           "enemy, member, prisoner: describe un VINCULO "
                           "administrativo. Afirmar que la figura LLEGO seria "
                           "inventar el desplazamiento."),
    "add hf site link": ("688 registros SIN campo hfid: no identifica a "
                         "ninguna figura (solo site_id). El sujeto que "
                         "Chronicles sigue no existe en este tipo."),
    "add hf hf link": ("2.364 registros con hfid + hfid_target, pero el TIPO "
                       "de vinculo no esta documentado: no consta si es "
                       "alianza, parentesco u otro. Semantica no "
                       "demostrada."),
    "remove hf hf link": ("554 registros; NINGUNO tiene seconds72 utilizable "
                          "(0/554), asi que no hay instante. Y como "
                          "`add hf hf link`, el tipo de vinculo no esta "
                          "documentado."),
    "hf simple battle event": ("5.478 registros con dos bandos "
                               "(group_1_hfid/group_2_hfid) y `subtype` con "
                               "valores no documentados (attacked, scuffle, "
                               "ambushed, confront...). Que sea un combate lo "
                               "afirma su NOMBRE, no un vocabulario declarado."),
    "hf wounded": ("871 registros con `woundee_hfid` y `wounder_hfid`, pero "
                   "ningun campo declara la GRAVEDAD de la herida, y "
                   "`WOUNDED` no es un tipo Chronicle cuya semantica este "
                   "demostrada."),
    "hf abducted": ("523 registros con `snatcher_hfid` y `target_hfid`; solo "
                    "15 tienen seconds72 y `ABDUCTION` no es un tipo "
                    "Chronicle demostrado."),
}


# ==================================================== HELPERS DE CONTRATO
def es_tipo_soportado(tipo_raw):
    """¿Este tipo tiene una equivalencia Chronicle DEMOSTRADA?"""
    return tipo_raw in SEMANTICA


def grado_de(tipo_raw):
    """El grado declarado. `NOT_PROVEN` por defecto: el motor no presume."""
    entrada = SEMANTICA.get(tipo_raw)
    return entrada["grado"] if entrada else NOT_PROVEN


def tipo_chronicle_de(tipo_raw):
    """El tipo Chronicle, o `None` si la semantica no esta demostrada."""
    entrada = SEMANTICA.get(tipo_raw)
    return entrada["tipo_chronicle"] if entrada else None


def campo_sujeto_de(tipo_raw):
    """Que campo es el SUJETO de este tipo. `None` si no esta declarado."""
    entrada = SEMANTICA.get(tipo_raw)
    return entrada["campo_sujeto"] if entrada else None


def regla_de(tipo_raw):
    """La regla semantica completa, o `None`."""
    entrada = SEMANTICA.get(tipo_raw)
    return dict(entrada) if entrada else None


def contrato():
    """El contrato, legible desde el codigo. Lo que esta capa promete.

    No es documentacion externa: es lo que el motor garantiza sobre si mismo.
    """
    return {
        "version": 1,
        "temporal": {
            "representacion": TEMPORAL_V1_NOMBRE,
            "campos": list(TEMPORAL_V1),
            "orden": list(ORDEN_V1),
            "ticks_df": "NO_IMPLEMENTADO",
            "ticks_motivo": ("la constante de conversion a ticks de DF no esta "
                             "demostrada; convertir seria inventar precision"),
        },
        "certezas": list(CERTEZAS),
        "grados": list(GRADOS),
        "campos_temporales": list(CAMPOS_TEMPORALES),
        "campos_sujeto": list(CAMPOS_SUJETO),
        "valores_ausentes": list(VALORES_AUSENTES),
        "tipos_soportados": sorted(SEMANTICA),
        "tipos_no_demostrados": sorted(SEMANTICA_NO_DEMOSTRADA),
        "reglas": dict((k, dict(v)) for k, v in SEMANTICA.items()),
        "no_demostradas": dict(SEMANTICA_NO_DEMOSTRADA),
        "identidad": ("derivada del contenido con sha256; nunca aleatoria, "
                      "nunca un reloj, nunca el orden de lectura"),
        "invariantes": [
            "NO DATA -> NO CLAIM",
            "AUSENCIA != NEGACION",
            "DERIVED nunca se presenta como FACT",
            "NOT_PROVEN nunca se presenta como hecho interpretado",
            "no se inventa entidad, fecha ni causalidad",
            "no se descartan registros en silencio: se clasifican",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(contrato(), ensure_ascii=False, indent=2))
