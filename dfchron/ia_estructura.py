#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: VERIFICACION ESTRUCTURADA (determinista)
==========================================================

QUE ES, Y QUE NO ES
-------------------
Este modulo **verifica afirmaciones estructuradas contra los datos reales**. Es
lo unico que el sistema puede demostrar de forma determinista, y por eso esta
limitado a lo que se puede demostrar de verdad.

LO QUE DEMUESTRA
----------------
Una afirmacion cuyo texto encaja con una **plantilla conocida** y cuya evidencia
apunta a `(entidad, df_id, campo)`, siempre que el nucleo confirme que ese campo
vale lo que la afirmacion dice.

    claim    : "El sitio es de tipo 'hamlet'."
    evidencia: {entidad: sitio, df_id: "112", datos_utilizados: [tipo]}
    nucleo   : ficha_sitio("112")["type"] == "hamlet"   -> VERIFICADA

LO QUE NO DEMUESTRA, Y POR QUE NO SE INTENTA
--------------------------------------------
* Que una frase libre sea consecuencia de su evidencia. Requiere semantica.
* Que un sinonimo o una parafrasis sean «lo mismo». «La fortaleza» frente a «El
  sitio» cambia el vocabulario sin cambiar el hecho: el sistema no lo sabe, y por
  eso **no** lo declara verificado.
* Que una negacion se derive. Medido: «El sitio NO es de tipo 'fortress'» comparte
  el 100 % del vocabulario con su apoyo, y `trazabilidad` le da fraccion 1.0. Aqui,
  en cambio, **no hay plantilla que encaje** —ninguna admite negacion—, asi que el
  resultado es NO_APLICABLE: no verificado, y no fingido.
* Que una afirmacion compuesta este respaldada como un todo. Una oracion con dos
  proposiciones no encaja con ninguna plantilla: no se verifica a medias, se
  declara no aplicable.

POR QUE NO SE CONVIERTE EN BARRERA DE SEGURIDAD
------------------------------------------------
Verificar **no** autoriza. Este modulo no toca `disclosure`, ni `visibility`, ni la
frontera. Una afirmacion VERIFICADA que sea `PLAYER_HIDDEN` sigue sin poder
divulgarse, y una NO_VERIFICADA que sea visible sigue sin estar verificada.
`ia_contrato.validar_salida()` mantiene la autoridad; esto solo le informa.

ACTUALIDAD
----------
La evidencia lleva `state_version`: el `dataset_id` real del mundo que produjo
el dato. Si quien verifica le pasa `version_actual`, una evidencia de otro
estado del mundo se devuelve `NO_VERIFICADA` aunque el valor coincida: comparar
un dato viejo contra un mundo nuevo no demuestra nada sobre este mundo.

Lo que NO se comprueba, y se declara: que la afirmacion siga siendo *verdad*.
Invalidar por antiguedad no es comprobar la verdad de hoy; es negarse a usar un
rastro que no pertenece al mundo que se mira.

FALLO CERRADO
-------------
Todo lo que no se puede comprobar con certeza se declara NO_APLICABLE o
NO_VERIFICADA. **Nunca** hay un camino por el que una afirmacion sin comprobar
llegue a `VERIFICADA`, y nunca se infiere un valor que el nucleo no dio.

DETERMINISMO
------------
Sin azar, sin relojes, sin UUID. Misma entrada, mismo veredicto, byte a byte.

Ejecutar:  python dfchron/pruebas/probar_verificacion_estructurada.py
"""
import os
import re
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    _RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

from dfchron import contrato_ia as c                 # noqa: E402
from dfchron import ia_conocimiento as ic      # noqa: E402

# ============================== ESTADOS ====================================
#: El unico estado que concede autoridad: el nucleo lo confirma.
VERIFICADA = "VERIFICADA"
#: Hay plantilla y evidencia, pero el valor del nucleo NO coincide. Es la marca
#: de una afirmacion fabricada sobre una referencia REAL.
NO_VERIFICADA = "NO_VERIFICADA"
#: No hay plantilla que encaje: no es una afirmacion estructurada. No se afirma
#: nada en ninguno de los dos sentidos.
NO_APLICABLE = "NO_APLICABLE"

ESTADOS = (VERIFICADA, NO_VERIFICADA, NO_APLICABLE)


SIGNIFICADO = {
    VERIFICADA: ("el nucleo confirma que la entidad tiene ese valor en ese "
                 "campo; no dice nada mas alla de esa proposicion"),
    NO_VERIFICADA: ("hay una afirmacion estructurada, pero el valor del nucleo "
                    "no coincide con el afirmado"),
    NO_APLICABLE: ("la afirmacion no es estructurada, o no hay evidencia "
                   "suficiente: el sistema no puede comprobarla"),
}
#: Que significa cada estado, en texto. Viaja con el resultado para que ningun
#: consumidor tenga que adivinarlo por el nombre.

# ============================== PLANTILLAS =================================
#: Tabla `(entidad, campo) -> plantilla`, tomada de `ia_conocimiento.py`.
#:
#: Se declara aqui y **no** se deduce, por dos razones:
#:
#:   1. Si las dos tablas se separaran, un claim dejaria de verificarse sin que
#:      nadie notase el cambio. Es una tabla corta: declararla es mas barato que
#:      vigilar que coincida.
#:   2. Declararla permite RECHAZAR una plantilla nueva sin tocar este modulo: un
#:      dato nuevo no es verificable hasta que se declare aqui. Escribir es mas
#:      lento que leer, y en seguridad interesa lo lento.
#:
#: `{valor}` se sustituye por `_texto(valor)`, igual que en el puente.
PLANTILLAS = {
    ("figura", "nombre"): "La figura se llama '{valor}'.",
    ("figura", "race"): "La raza de la figura es '{valor}'.",
    ("figura", "caste"): "El caste de la figura es '{valor}'.",
    ("figura", "sexo"): "La figura esta registrada con sexo '{valor}'.",
    ("figura", "tipo"): "El registro es de tipo '{valor}'.",
    ("entidad", "nombre"): "La entidad se llama '{valor}'.",
    ("entidad", "race"): "La raza de la entidad es '{valor}'.",
    ("entidad", "tipo"): "El registro es de tipo '{valor}'.",
    ("sitio", "nombre"): "El sitio se llama '{valor}'.",
    ("sitio", "tipo"): "El sitio es de tipo '{valor}'.",
    ("sitio", "eventos"): "El sitio tiene '{valor}' eventos registrados.",
    ("evento", "tipo"): "El evento es de tipo '{valor}'.",
    ("evento", "estado"): "El estado registrado del evento es '{valor}'.",
    ("evento", "subtipo"): "El subtipo del evento es '{valor}'.",
    ("artefacto", "nombre_item"): "El objeto es '{valor}'.",
    ("artefacto", "tipo"): "El registro es de tipo '{valor}'.",
    ("artefacto", "subtipo"): "El subtipo del objeto es '{valor}'.",
    ("artefacto", "material"): "El material del objeto es '{valor}'.",
}

#: Plantillas cuyo `{valor}` va SIN comillas. El anio es un caso real: el puente
#: lo emite asi, y por eso la plantilla es distinta y no se «normaliza».
PLANTILLAS_SIN_COMILLAS = {
    ("evento", "año"): "El evento ocurrio en el ano {valor}.",
}

#: El separador de comillas es ASCII simple. Se declara aqui para que no haya
#: ningun caracter tipografico escondido en la comparacion.
COMILLA = "'"


def _plantilla_para(entidad, campo):
    """La plantilla declarada para ese par, y si su valor va entrecomillado."""
    p = PLANTILLAS.get((entidad, campo))
    if p is not None:
        return p, True
    p = PLANTILLAS_SIN_COMILLAS.get((entidad, campo))
    if p is not None:
        return p, False
    return None, False


def _valor_en(texto, plantilla, con_comillas):
    """El valor que la afirmacion dice, si su texto ES exactamente esa plantilla.

    Devuelve `None` si el texto no es esa plantilla. Es deliberado: se exige
    coincidencia de la frase COMPLETA, no de un fragmento. Aceptar un fragmento
    permitiria verificar una proposicion y dar por verificada la frase entera,
    que es justo el error que este diseno evita.
    """
    if not isinstance(texto, str):
        return None
    patron = "^" + re.escape(plantilla).replace(r"\{valor\}", r"(.+?)") + "$"
    m = re.match(patron, texto.strip())
    if not m:
        return None
    # El patron ya incluye las comillas como caracteres literales, asi que el
    # grupo capturado es el valor SIN ellas. No hay que pelarlo otra vez: hacerlo
    # era un error que hacia que NADA cuadrase nunca.
    return m.group(1).strip() or None


def _resultado(estado, motivo, **extra):
    d = {"estado": estado, "motivo": motivo,
         "significado": SIGNIFICADO[estado],
         "comprobado": None, "esperado": None, "obtenido": None}
    d.update(extra)
    return d


def verificar_afirmacion(texto, evidencia, ficha, version_actual=None):
    """Verifica UNA afirmacion estructurada contra la ficha cruda del nucleo.

    Args:
        texto:     lo que dice la afirmacion.
        evidencia: una evidencia `{entidad, df_id, datos_utilizados, ...}`.
        ficha:    la ficha cruda del nucleo para ese `df_id`, o `None`.
        version_actual: el `dataset_id` del mundo que se esta mirando. Si se
                   pasa, la evidencia de OTRO mundo se rechaza antes de
                   comprobar nada (ver `ACTUALIDAD`).

    Devuelve un dict con `estado` en `ESTADOS`. **No lanza**: un fallo aqui es
    un resultado y no una excepcion, porque quien valida necesita ver el motivo.
    """
    if not isinstance(evidencia, dict):
        return _resultado(NO_APLICABLE, "sin evidencia utilizable")
    if version_actual is not None and not c.evidencia_es_actual(
            evidencia, version_actual):
        # La evidencia es de otro estado del mundo. Da igual que el valor
        # coincida: se esta comparando un dato viejo contra un mundo nuevo, y
        # eso no demuestra nada sobre este mundo.
        return _resultado(
            NO_VERIFICADA,
            "la evidencia es del estado %r y el mundo actual es %r"
            % (c.version_de_evidencia(evidencia), version_actual),
            esperado=None, obtenido=None, comprobado=False,
            estado_version=c.version_de_evidencia(evidencia))
    entidad = str(evidencia.get("entidad") or "")
    df_id = evidencia.get("df_id")
    usados = evidencia.get("datos_utilizados") or []
    if not entidad or df_id is None or not usados:
        return _resultado(NO_APLICABLE, "evidencia incompleta")
    if len(usados) != 1:
        # Varios campos en una evidencia: no se sabe cual se esta afirmando. Se
        # rechaza en vez de elegir uno, porque elegir seria adivinar.
        return _resultado(NO_APLICABLE,
                          "la evidencia declara %d campos y la afirmacion no "
                          "dice cual" % len(usados))
    campo = str(usados[0])
    plantilla, comillas = _plantilla_para(entidad, campo)
    if plantilla is None:
        return _resultado(
            NO_APLICABLE,
            "no hay plantilla declarada para %s/%s" % (entidad, campo))
    esperado = _valor_en(texto, plantilla, comillas)
    if esperado is None:
        return _resultado(
            NO_APLICABLE,
            "el texto no es la plantilla de %s/%s: no es una afirmacion "
            "estructurada" % (entidad, campo))
    if not isinstance(ficha, dict):
        return _resultado(NO_VERIFICADA,
                          "la entidad %s %r no existe en el nucleo"
                          % (entidad, df_id), esperado=esperado)
    obtenido = ic._texto(ficha.get(campo))
    if obtenido is None:
        return _resultado(
            NO_VERIFICADA,
            "el nucleo no tiene valor para %s/%s" % (entidad, campo),
            esperado=esperado)
    if esperado != obtenido:
        return _resultado(
            NO_VERIFICADA,
            "el nucleo dice %r y la afirmacion dice %r" % (obtenido, esperado),
            esperado=esperado, obtenido=obtenido, comprobado=False)
    return _resultado(VERIFICADA,
                      "el nucleo confirma %s %s en %s" % (entidad, campo,
                                                          esperado),
                      esperado=esperado, obtenido=obtenido, comprobado=True)


def verificar_claims(claims, ctx, rec):
    """Verifica varios claims de salida. Devuelve el detalle por indice.

    Cada claim se mide contra SUS apoyos, y cada apoyo aporta una evidencia. Un
    claim queda VERIFICADA si **alguna** de sus evidencias se verifica: se
    necesita una, no todas, porque un claim puede apoyarse en un dato concreto y
    en otro que no se pudo comprobar.
    """
    recibido = {cl["ref"]: cl for cl in (ctx.get("claims") or [])
                if isinstance(cl, dict) and "ref" in cl}
    salida = {}
    for i, cl in enumerate(claims or []):
        if not isinstance(cl, dict):
            continue
        # El motivo por defecto solo vale si de verdad no habria apoyos. En
        # cuanto hay alguno pero la afirmacion no encaja con su plantilla, el
        # motivo que interesa es el de la plantilla: decir «sin apoyos» cuando los
        # hay seria un diagnostico falso.
        mejor = _resultado(NO_APLICABLE, "sin apoyos")
        hay_apoyo = False
        for ref in (cl.get("soporte") or []):
            base = recibido.get(ref)
            if base is None:
                continue
            for ev in (base.get("evidence") or []):
                tipo = ev.get("entidad")
                ficha = (rec.ficha_de(tipo, str(ev.get("df_id")))
                         if tipo and ev.get("df_id") is not None else None)
                r = verificar_afirmacion(cl.get("texto"), ev, ficha)
                if r["estado"] == VERIFICADA:
                    mejor = r
                    hay_apoyo = True
                    break
                if r["estado"] == NO_VERIFICADA and mejor["estado"] == NO_APLICABLE:
                    mejor = r
                    hay_apoyo = True
                elif (not hay_apoyo and mejor["motivo"] == "sin apoyos"
                        and r["motivo"] != "sin apoyos"):
                    # Conserva el primer motivo informative de la plantilla.
                    mejor = r
                    hay_apoyo = True
            if mejor["estado"] == VERIFICADA:
                break
        salida[i] = mejor
    return salida


def resumen(claims, ctx, rec):
    """Resultado agregado, pensado para ir en el veredicto.

    Declara **que clase de verificacion se hizo**, porque un veredicto sin esa
    frase se puede leer como «el sistema lo comprobo todo».
    """
    detalle = verificar_claims(claims, ctx, rec)
    return {
        "detalle": detalle,
        "verificadas": sorted(i for i, v in detalle.items()
                              if v["estado"] == VERIFICADA),
        "no_verificadas": sorted(i for i, v in detalle.items()
                                 if v["estado"] == NO_VERIFICADA),
        "no_aplicables": sorted(i for i, v in detalle.items()
                                if v["estado"] == NO_APLICABLE),
        "alcance": (
            "se comprueban SOLO afirmaciones estructuradas contra el nucleo; "
            "una afirmacion libre, una parafrasis o una negacion NO se verifica "
            "y se declara NO_APLICABLE"),
        "no_autoriza": (
            "verificar NO autoriza a divulgar: la politica de divulgacion y la "
            "frontera se aplican despues y con independencia de esto"),
    }


if __name__ == "__main__":                                   # pragma: no cover
    print(__doc__)
