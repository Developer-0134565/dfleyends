#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERIFICACION SEMANTICA DETERMINISTA DEL NUCLEO.

QUE ES
------
Un verificador de afirmaciones **estructuradas** sobre el mundo, resuelto con
reglas y datos: sin LLM, sin similitud de palabras, sin inferencia.

QUE NO ES
---------
No es un «modelo semántico» reducido. `ia_estructura` verifica un campo contra
la ficha; esto verifica afirmaciones **compuestas**, con sujeto, relacion y
objeto, contra el indice real del nucleo.

LA DIFERENCIA QUE IMPORTA
-------------------------
    «El sitio es de tipo fortress»      -> un campo contra la ficha
    «La figura 712 tiene raza MINOTAUR» -> sujeto + atributo contra el indice
    «La figura 500 tiene un war_buddy»  -> sujeto + relacion contra el grafo

El segundo y el tercero no se pueden expresar en la tabla de plantillas: por
eso son cobertura nueva, no duplicada.

LOS SIETE NIVELES, Y DONDE TERMINA
----------------------------------
| Nivel       | Verificable | Regla                                  |
|-------------|-------------|----------------------------------------|
| 1 Existencia | SI          | el id existe en el indice              |
| 2 Atributo   | SI          | el campo coincide exactamente          |
| 3 Relacion   | SI          | la arista existe, en la direccion dada|
| 4 Estado     | SI          | `certainty` del registro               |
| 5 Cantidad   | SI          | recuento real sobre el indice          |
| 6 Estructura | SI          | cadena de relaciones de longitud >= 2  |
| 7 Historico  | PARCIAL     | solo si ambos lados tienen anio        |

El nivel 7 es el unico parcial, y por una razon concreta: muchas relaciones
tienen `año = NULL`. Cuando falta, se dice `NO_VERIFICADA`: no se deduce el
orden temporal de una arista sin fecha.

AMBIGUEDAD
----------
Una afirmacion ambigua NUNCA da `VERIFICADA`. Si dos lecturas son posibles y el
resultado difiere, sale `AMBIGUA` y no se fuerza ninguna.

Ejecutar:  python 00_SOURCE/tools/probar_verificacion_semantica.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nucleo import Archivo, FACT, UNKNOWN            # noqa: E402

# ============================================================== ESTADOS =====
VERIFICADA = "VERIFICADA"
NO_VERIFICADA = "NO_VERIFICADA"
AMBIGUA = "AMBIGUA"

ESTADOS = (VERIFICADA, NO_VERIFICADA, AMBIGUA)

SIGNIFICADO = {
    VERIFICADA: "el nucleo confirma la proposicion con datos del indice",
    NO_VERIFICADA: "el nucleo tiene datos y NO confirman la proposicion, o no "
                   "hay informacion suficiente para comprobarla",
    AMBIGUA: "la afirmacion admite mas de una lectura y no se fuerza ninguna",
}

#: Sujetos que el nucleo sabe identificar. Deliberadamente una lista CERRADA:
#: anadir uno aqui es una decision, no un accidente.
SUJETOS = ("figura", "sitio", "entidad", "evento", "artefacto")

#: Atributos verificables por sujeto. Cerrado por el mismo motivo.
ATRIBUTOS = {
    "figura": ("nombre", "race", "caste", "sexo", "tipo"),
    "sitio": ("nombre", "tipo"),
    "entidad": ("nombre", "race", "tipo"),
    "evento": ("tipo", "subtipo", "estado", "año"),
    "artefacto": ("nombre", "tipo", "subtipo", "material"),
}


def _resultado(estado, motivo, **extra):
    d = {"estado": estado, "motivo": motivo,
         "significado": SIGNIFICADO[estado],
         "comprobado": estado == VERIFICADA}
    d.update(extra)
    return d


def _indice_de(archivo, tipo):
    """El indice del nucleo que corresponde a un tipo de sujeto.

    Centralizado a proposito: los cinco verificadores consultan el mismo
    diccionario, y repetir el `if` en cada uno seria cinco sitios donde
    anadir un tipo a medias.
    """
    return {"figura": archivo.indice.figuras,
            "sitio": archivo.indice.sitios,
            "entidad": archivo.indice.entidades,
            "evento": archivo.indice.eventos,
            "artefacto": archivo.indice.artefactos}[tipo]


def _registro(archivo, tipo, df_id):
    """El registro crudo del dataset, o `None` si no existe."""
    return _indice_de(archivo, tipo).get(str(df_id))


# ================================================= NIVEL 1: EXISTENCIA =====
def existe(archivo, tipo, df_id):
    """Nivel 1. ¿Existe esa entidad con ese id?

    Es la afirmacion mas basica y la unica que no depende de ningun campo.
    """
    if tipo not in SUJETOS:
        return _resultado(AMBIGUA, "tipo de sujeto desconocido: %r" % tipo)
    clave = str(df_id)
    if _registro(archivo, tipo, clave) is None:
        return _resultado(NO_VERIFICADA,
                          "no existe %s con id %r en el dataset" % (tipo, clave))
    return _resultado(VERIFICADA, "%s %s existe" % (tipo, clave),
                      tipo=tipo, df_id=clave)


# ================================================== NIVEL 2: ATRIBUTO =====
def atributo(archivo, tipo, df_id, atributo_nombre, valor_esperado):
    """Nivel 2. ¿X tiene el atributo Y?

    Comparacion EXACTA contra el indice. Sin normalizar, sin buscar por
    parecido: «minotaur» no es «MINOTAUR», y esa distincion es el motivo por el
    que esto no es un modelo semantico.
    """
    if tipo not in SUJETOS:
        return _resultado(AMBIGUA, "tipo de sujeto desconocido: %r" % tipo)
    permitidos = ATRIBUTOS[tipo]
    if atributo_nombre not in permitidos:
        # No es un error: es una afirmacion que este verificador no cubre.
        return _resultado(AMBIGUA,
                          "el atributo %r no se verifica sobre %s; "
                          "permitidos: %s" % (atributo_nombre, tipo,
                                              ", ".join(permitidos)))
    r = existe(archivo, tipo, df_id)
    if r["estado"] != VERIFICADA:
        return _resultado(NO_VERIFICADA, r["motivo"])
    registro = _registro(archivo, tipo, df_id)
    campos = registro.get("campos") or {}
    entrada = campos.get(atributo_nombre)
    if not isinstance(entrada, dict):
        return _resultado(NO_VERIFICADA,
                          "el registro no declara el campo %r" % atributo_nombre)
    obtenido = entrada.get("valor")
    if obtenido in (None, "", "-1"):
        return _resultado(NO_VERIFICADA,
                          "el campo %r esta ausente en el dato" % atributo_nombre,
                          obtenido=None)
    if str(obtenido) == str(valor_esperado):
        return _resultado(VERIFICADA,
                          "el nucleo confirma %s/%s = %r"
                          % (tipo, atributo_nombre, obtenido),
                          obtenido=obtenido, esperado=str(valor_esperado))
    return _resultado(NO_VERIFICADA,
                      "el nucleo dice %r y la afirmacion dice %r"
                      % (obtenido, valor_esperado),
                      obtenido=obtenido, esperado=str(valor_esperado))


# =================================================== NIVEL 3: RELACION =====
def relacion(archivo, figura_a, figura_b, tipo_rel=None):
    """Nivel 3. ¿A tiene relacion con B?

    El grafo es **DIRIGIDO**: que A tenga relacion con B no implica la
    inversa. Se comprueba la direccion que la afirmacion declara, y solo esa.

    Si `tipo_rel` es None se busca cualquier relacion entre los dos; si se
    declara, la arista tiene que ser de ese tipo exacto.
    """
    for etiqueta, a, b in (("origen", figura_a, figura_b),
                           ("destino", figura_b, figura_a)):
        if existe(archivo, "figura", a)["estado"] != VERIFICADA:
            return _resultado(NO_VERIFICADA,
                              "no existe la figura %r (%s de la relacion)"
                              % (a, etiqueta))
    if existe(archivo, "figura", figura_b)["estado"] != VERIFICADA:
        return _resultado(NO_VERIFICADA,
                          "no existe la figura %r" % figura_b)

    relaciones = archivo.relaciones_de_figura(str(figura_a))["relaciones"]
    entre = [r for r in relaciones if r["otra_figura_id"] == str(figura_b)]
    if not entre:
        return _resultado(NO_VERIFICADA,
                          "no hay relacion registrada entre %s y %s"
                          % (figura_a, figura_b))
    if tipo_rel is None:
        tipos = sorted({r["tipo"] for r in entre})
        return _resultado(VERIFICADA,
                          "existe relacion entre %s y %s" % (figura_a, figura_b),
                          tipos_encontrados=tipos)
    coincide = [r for r in entre if r["tipo"] == tipo_rel]
    if not coincide:
        return _resultado(NO_VERIFICADA,
                          "hay relacion pero no de tipo %r; los tipos reales "
                          "son: %s" % (tipo_rel,
                                       ", ".join(sorted({r["tipo"]
                                                         for r in entre}))),
                          tipos_encontrados=sorted({r["tipo"] for r in entre}))
    return _resultado(VERIFICADA,
                      "existe relacion %r entre %s y %s"
                      % (tipo_rel, figura_a, figura_b),
                      tipo_relacion=tipo_rel,
                      anios=[r["año"] for r in coincide])


# ===================================================== NIVEL 4: ESTADO ====
def estado(archivo, tipo, df_id):
    """Nivel 4. ¿Que estado tiene el registro de esa entidad?

    El `certainty` es del propio dataset: `FACT` si el dato esta literalmente en
    el XML, `DERIVED` si lo calcula el nucleo, `UNKNOWN` si no consta. Se
    comprueba contra lo declarado, sin reinterpretarlo.
    """
    r = existe(archivo, tipo, df_id)
    if r["estado"] != VERIFICADA:
        return _resultado(NO_VERIFICADA, r["motivo"])
    registro = _registro(archivo, tipo, df_id)
    certeza = registro.get("certainty")
    if certeza not in (FACT, "DERIVED", UNKNOWN):
        return _resultado(NO_VERIFICADA,
                          "el registro declara una certeza no reconocida: %r"
                          % certeza)
    return _resultado(VERIFICADA,
                      "%s %s tiene certeza %s" % (tipo, df_id, certeza),
                      certainty=certeza)


# ==================================================== NIVEL 5: CANTIDAD ===
def cantidad(archivo, tipo, cuenta_esperada):
    """Nivel 5. ¿Cuántas entidades de ese tipo hay?

    Recuento real sobre el indice cargado. Es la afirmacion mas simple de
    comprobar y la que mas riesgo tiene de desviarse si alguien cachea un
    numero en lugar de contarlo.
    """
    if tipo not in SUJETOS:
        return _resultado(AMBIGUA, "tipo de sujeto desconocido: %r" % tipo)
    real = len(_indice_de(archivo, tipo))
    if real == cuenta_esperada:
        return _resultado(VERIFICADA,
                          "hay %d entidades de tipo %s" % (real, tipo),
                          obtenido=real, esperado=cuenta_esperada)
    return _resultado(NO_VERIFICADA,
                      "hay %d entidades de tipo %s, no %d"
                      % (real, tipo, cuenta_esperada),
                      obtenido=real, esperado=cuenta_esperada)


# =================================================== NIVEL 6: ESTRUCTURA ==
def estructura(archivo, cadena):
    """Nivel 6. ¿X está relacionado con Y, que está relacionado con Z?

    Se comprueba que **cada** arista consecutiva existe y va en la direccion
    declarada. Una cadena rota en cualquier punto es `NO_VERIFICADA`: no se
    acepta «va bien casi todo».
    """
    if not isinstance(cadena, (list, tuple)) or len(cadena) < 2:
        return _resultado(AMBIGUA,
                          "una estructura necesita al menos dos extremos")
    for a, b in zip(cadena, cadena[1:]):
        r = relacion(archivo, a, b)
        if r["estado"] != VERIFICADA:
            return _resultado(NO_VERIFICADA,
                              "la cadena se rompe entre %s y %s: %s"
                              % (a, b, r["motivo"]), rota_en=(str(a), str(b)))
    return _resultado(VERIFICADA,
                      "existe la cadena %s" % " -> ".join(map(str, cadena)),
                      longitud=len(cadena))


# ==================================================== NIVEL 7: HISTORICO ==
def historico(archivo, figura_a, figura_b, antes_de=True):
    """Nivel 7. ¿A se relacionó con B antes que al revés?

    **PARCIAL, y se declara.** Solo se verifica si **ambos** lados tienen año.
    Cuando alguno no lo tiene, el orden no es demostrable y sale
    `NO_VERIFICADA`: no se deduce de la posición en la lista.
    """
    r = relacion(archivo, figura_a, figura_b)
    if r["estado"] != VERIFICADA:
        return _resultado(NO_VERIFICADA, r["motivo"])

    def anios_entre(desde, hacia):
        return [x["año"] for x
                in archivo.relaciones_de_figura(str(desde))["relaciones"]
                if x["otra_figura_id"] == str(hacia) and x["año"] is not None]

    ida = anios_entre(figura_a, figura_b)
    vuelta = anios_entre(figura_b, figura_a)
    if not ida:
        return _resultado(NO_VERIFICADA,
                          "la relacion no tiene año; el orden temporal no es "
                          "demostrable")
    if not vuelta:
        return _resultado(NO_VERIFICADA,
                          "no hay relacion inversa con año; no se puede "
                          "comparar el orden temporal")
    a, b = min(ida), min(vuelta)
    if a == b:
        # Mismo año en ambos sentidos: el orden NO es demostrable. Decir que
        # «A precede a B» porque a < b es cierto, pero cuando a == b la
        # afirmacion seria falsa y el sistema la daba por buena.
        return _resultado(
            NO_VERIFICADA,
            "A y B estan ambos en el ano %s; el orden no es distinguible" % a,
            anio_a=a, anio_b=b)
    ok = (a < b) if antes_de else (b < a)
    return _resultado(
        VERIFICADA if ok else NO_VERIFICADA,
        "A en el ano %s y B en el ano %s; %s" % (
            a, b, "A precede a B" if antes_de else "B precede a A"),
        anio_a=a, anio_b=b)


# ===================================================== ALCANCE ============
def alcance():
    """Que comprueba este modulo, y que NO. Viaja en el resultado."""
    return {
        "niveles_comprobados": ["existencia", "atributo", "relacion", "estado",
                                "cantidad", "estructura"],
        "niveles_parciales": ["historico (solo si ambos lados tienen año)"],
        "niveles_no_comprobados": [
            "paráfrasis: «el sitio fortificado» frente a «el sitio es de tipo "
            "fortress» NO se reconoce",
            "negación: «no es de tipo X» NO se verifica",
            "comparación de palabras: no se usa similitud léxica",
        ],
        "fuera_de_alcance": [
            "relaciones sin identidad propia: no se verifican como entidad",
            "guerra: el XML no tiene tabla de guerras",
            "era: la única era no tiene años utilizables ni eventos asociados",
        ],
    }


if __name__ == "__main__":
    import json
    _a = Archivo()
    print(json.dumps({
        "figura 712 existe": existe(_a, "figura", 712)["estado"],
        "raza de 712": atributo(_a, "figura", 712, "race",
                                "MINOTAUR")["estado"],
        "cuantas figuras": cantidad(_a, "figura",
                                     len(_a.indice.figuras))["estado"],
        "alcance": alcance(),
    }, ensure_ascii=False, indent=2))