#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: VERIFICACION Y ALCANCE DE LA VALIDACION
==========================================================

QUE PROBLEMA RESUELVE, MEDIDO
-----------------------------
`ia_contrato._validar_claim()` comprueba **que la REFERENCIA del apoyo exista** y
que el tipo declarado no sea mas fuerte que el apoyo. No comprueba el CONTENIDO.
Medido por el camino real, con un apoyo real (`c0`) y contenido inventado:

    claim: "Existe una veta de diamantes."  tipo FACT  soporte ["c0"]
    veredicto: {'puede_entregarse': True, 'errores': [], 'claims_ok': 1}

El sistema dice «1 claim validado» sobre algo que **nunca leyo**. Y como
`ia_mock.evaluar_confianza()` solo mira el `tipo` declarado, ese contenido
inventado recibia `CONFIANZA_ALTA`: la maxima confianza para algo no verificado.

QUE SE PUEDE Y QUE NO SE PUEDE VERIFICAR
-----------------------------------------

  | propiedad                        | ¿verificable? | como                     |
  |----------------------------------|---------------|--------------------------|
  | Existencia de la referencia      | **SI**        | el `ref` esta en el ctx  |
  | Tipo no mas fuerte que el apoyo  | **SI**        | `truth_status` comparado |
  | Permiso de divulgacion           | **SI**        | `disclosure` del apoyo   |
  | Coherencia de dimensiones       | **SI**        | tabla de combinaciones   |
  | -------------------------------- | ------------- | ------------------------ |
  | Que el texto se DERIVE del apoyo | **NO**        | requiere semantica      |
  | Que la afirmacion sea VERDAD     | **NO**        | requiere verificar el mundo |
  | Que el nombre exista             | **NO**        | requiere el registro     |

La fila de abajo es la importante. **El sistema no puede demostrar que una frase sea
consecuencia de otra.** Y mientras no pueda, no debe *parecer* que puede.

LO QUE HACE ESTE MODULO
-----------------------
1. `trazabilidad()` mide, de forma **estructural y determinista**, que palabras del
   texto de un claim tienen respaldo en los claims que lo sostienen.
2. `alcance()` declara explicitamente que se ha comprobado y que **no**.
3. El veredicto lleva esa declaracion, para que nada pueda leer `claims_ok` como
   «esta afirmacion es verdadera».

LO QUE NO HACE, Y POR QUE
-------------------------
* **No inventa un validador semantico.** No hay forma determinista de comprobar que
  «tiene diamantes» se sigue de «es de tipo fortress». Un LLM que lo hiciera seria el
  modelo como autoridad sobre lo que puede revelarse (regla de oro nº2).
* **No usa regex para fingir semantica.** Un filtro de palabras no demuestra que una
  afirmacion sea verdadera; solo que no contiene una palabra concreta. Por eso aqui
  NO hay lista de palabras: hay medida de respaldo.
* **No baja el estandar de seguridad.** Este modulo no autoriza nada: solo describe lo
  que ya se comprobo. La frontera y el contrato siguen siendo la autoridad.

DETERMINISMO
------------
Sin azar, sin relojes, sin UUID. Misma entrada, mismo resultado, byte a byte.

Ejecutar:  python dfchron/pruebas/probar_verificacion.py
"""
import os
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    _RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

from dfchron import ia_frontera as fr         # noqa: E402


#: Estado de verificacion semantica. Es **siempre** este: el sistema no la hace, y
#: declararlo en vez de omitirlo es lo que impide que alguien la asuma.
SEMANTICA = "NO_VERIFICADA"

#: Lo que si se comprueba. Se declara para que sea auditable desde fuera.
ALCANCE = {
    "estructural": (
        "la referencia existe en el contexto recibido",
        "el tipo declarado no es mas fuerte que el truth_status del apoyo",
        "el apoyo es divulgable",
        "la combinacion de dimensiones es coherente",
    ),
    "trazabilidad": (
        "las palabras con carga informativa del texto tienen respaldo "
        "en los claims que lo sostienen",
    ),
    "semantico": (
        "QUE el texto sea una consecuencia logica del apoyo",
        "QUE la afirmacion sea verdadera en el mundo",
        "QUE las entidades citadas existan de verdad",
    ),
}


def _referencias(ctx):
    """Los claims del contexto indexados por `ref`."""
    return {cl["ref"]: cl for cl in (ctx.get("claims") or [])
            if isinstance(cl, dict) and "ref" in cl}


def trazabilidad(claims_salida, ctx):
    """Cuanto de cada claim tiene respaldo en SUS apoyos. Estructural.

    No decide si el claim es verdadero: decide **cuanto se parece a lo que dice
    respaldarlo**. Un claim cuyo texto no aparece en sus apoyos no es «falso» (puede
    estarlo, y el sistema no puede saberlo), pero **no tiene respaldo en lo que el
    sistema entrego**, que es lo unico que si puede afirmar.
    """
    recibido = _referencias(ctx)
    resultado = {}
    for i, cl in enumerate(claims_salida or []):
        if not isinstance(cl, dict):
            continue
        texto = cl.get("texto")
        if not isinstance(texto, str) or not texto.strip():
            # Sin texto no hay nada que rastrear. No es un fallo: es un claim sin
            # contenido, y su `tipo` ya lo comprobo el contrato.
            resultado[i] = {"fraccion": None, "sin_respaldo": [],
                            "motivo": "sin texto que rastrear"}
            continue
        apoyos = [recibido[r] for r in (cl.get("soporte") or []) if r in recibido]
        palabras = {p for p in fr._tokens(texto) if not fr._es_funcional(p)}
        if not apoyos:
            resultado[i] = {"fraccion": 0.0, "motivo": "sin apoyos resolubles",
                            "sin_respaldo": sorted(palabras)}
            continue
        vocab, _cifras = fr.vocabulario_de(apoyos)
        sin_respaldo = palabras - vocab
        resultado[i] = {
            "fraccion": (1.0 if not palabras else
                         (len(palabras) - len(sin_respaldo)) / float(len(palabras))),
            "sin_respaldo": sorted(sin_respaldo),
            "motivo": None,
        }
    return resultado


def alcance():
    """La declaracion de autoridad. Se mete en el veredicto, no se deduce.

    Existe para que ningun consumidor lea `claims_ok` y piense «el sistema ha
    comprobado que es verdad». Lo que ha comprobado esta enumerated arriba.
    """
    return {
        "estructural": list(ALCANCE["estructural"]),
        "trazabilidad": list(ALCANCE["trazabilidad"]),
        "semantico": list(ALCANCE["semantico"]),
        "estado_semantico": SEMANTICA,
        "autoridad": ("el sistema valida PROCEDENCIA y PERMISO; no valida VERDAD"),
    }


def resumen_verificacion(claims_salida, ctx):
    """Veredicto + trazabilidad + alcance, en un solo objeto auditable."""
    traz = trazabilidad(claims_salida, ctx)
    return {
        "trazabilidad": traz,
        "claims_sin_respaldo": sorted(i for i, v in traz.items()
                                      if v.get("fraccion") == 0.0),
        "claims_parciales": sorted(i for i, v in traz.items()
                                   if v.get("fraccion") not in (None, 0.0, 1.0)),
        "alcance": alcance(),
    }


if __name__ == "__main__":                                   # pragma: no cover
    print(__doc__)
