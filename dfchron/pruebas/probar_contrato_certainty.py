#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: contrato de `certainty` y aislamiento del adaptador
====================================================================

CIERRA tres supervivientes del mutation testing:

  M01  certainty FACT -> UNKNOWN en todo envelope
  M02  certainty siempre FACT
  M07  el adaptador deja de hacer copia profunda

EL CONTRATO (leido del codigo y de la documentacion, no supuesto)
-------------------------------------------------------------------
`API.md`:  | `certainty` | `FACT` con identificador; `UNKNOWN` si no se puede
           determinar |

`servicio_consulta._resultado()` lo implementa como:

    "certainty": "FACT" if estado == FOUND else "UNKNOWN"

Es decir, la certidumbre contractual **se deriva del estado**. Un envelope
FOUND con certainty UNKNOWN pierde la certeza que el consumidor espera; uno
NO_FOUND con certainty FACT afirma una certeza inexistente.

`AI_CONSUMER_BOUNDARY.md` declara los valores permitidos:
`FACT` / `DERIVED` / `UNKNOWN`.

POR QUE NO SON TESTS ARTIFICIALES
---------------------------------
Comprueban la RESPUESTA OBSERVADA por el consumidor (JSON sobre HTTP), no una
variable interna. Un test que inspeccionase el codigo de `_resultado` pasaria
igual con el contrato roto.

Uso:  python dfchron/pruebas/probar_contrato_certainty.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _r in (_RAIZ, os.path.join(_RAIZ, "00_SOURCE", "tools")):
    if _r not in sys.path:
        sys.path.insert(0, _r)

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def pedir(ruta):
    base = "http://127.0.0.1:%d" % _arrancar().server_address[1]
    try:
        r = urllib.request.urlopen(base + ruta, timeout=30)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except ValueError:
            return e.code, {}
    except Exception as exc:                        # noqa: BLE001
        return -1, {"<excepcion>": type(exc).__name__}


def setUpModule():
    _arrancar()


class TestContratoCertainty(unittest.TestCase):
    """`certainty` se deriva del estado, en las DOS direcciones."""

    PERMITIDOS = {"FACT", "DERIVED", "UNKNOWN"}   # AI_CONSUMER_BOUNDARY.md

    def test_certainty_esta_en_la_lista_permitida(self):
        for ruta in ("/api/figuras/712", "/api/entidades/4",
                     "/api/consulta/entidad/figura/712"):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                self.assertIn(env.get("certainty"), self.PERMITIDOS,
                              "certainty %r fuera del contrato"
                              % env.get("certainty"))

    def test_un_envelope_FOUND_declara_FACT(self):
        """Mata M01: si FOUND dijera UNKNOWN, se perderia la certeza."""
        cod, env = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("estado"), "FOUND")
        self.assertEqual(env.get("certainty"), "FACT",
                         "un envelope FOUND debe declarar certainty FACT")

    def test_un_envelope_NO_FOUND_no_declara_FACT(self):
        """Mata M02: si fuera siempre FACT, se afirmaria certeza inexistente."""
        cod, env = pedir("/api/consulta/entidad/figura/999999999")
        self.assertEqual(cod, 404)
        self.assertNotEqual(env.get("estado"), "FOUND")
        self.assertEqual(env.get("certainty"), "UNKNOWN",
                         "un envelope no-FOUND no puede declarar FACT")

    def test_NOT_VERIFIED_no_declara_FACT(self):
        """El caso mas delicado: existe, pero no se puede determinar."""
        cod, env = pedir(
            "/api/consulta/atributo/figura/712/atributo_inexistente")
        self.assertEqual(env.get("estado"), "NOT_VERIFIED")
        self.assertEqual(env.get("certainty"), "UNKNOWN",
                         "NOT_VERIFIED no puede declarar certeza FACT")

    def test_meta_coincide_con_el_nivel_superior(self):
        cod, env = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("certainty"),
                         (env.get("meta") or {}).get("certainty"),
                         "certainty y meta.certainty discrepan")

    def test_FACT_exige_estado_FOUND(self):
        for ruta in ("/api/figuras/712", "/api/consulta/relaciones/712",
                     "/api/consulta/contar/figura"):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                if env.get("certainty") == "FACT":
                    self.assertEqual(
                        env.get("estado"), "FOUND",
                        "certainty FACT con estado %r" % env.get("estado"))
class TestAislamientoAdaptador(unittest.TestCase):
    """El adaptador declara: "No muta el resultado del servicio".

    Es una garantia OBSERVABLE: si el consumidor modifica el sobre que recibe,
    el resultado del servicio no debe verse afectado. Mata M07.
    """

    def test_modificar_la_respuesta_no_altera_el_servicio(self):
        from dfchron import servicio_consulta as qc
        from dfchron import adaptador_consulta as ac

        antes = json.dumps(qc.obtener_entidad("figura", "712"),
                          sort_keys=True, default=str)

        respuesta = ac.ficha_figura("712")
        # El consumidor modifica lo que recibe, como haria cualquier cliente.
        respuesta["certainty"] = "MANIPULADO"
        respuesta["data"] = None
        respuesta["estado"] = "FABRICADO"

        despues = json.dumps(qc.obtener_entidad("figura", "712"),
                             sort_keys=True, default=str)
        self.assertEqual(despues, antes,
                         "modificar la respuesta del adaptador altero el "
                         "resultado del servicio")

    def test_la_respuesta_no_es_el_mismo_objeto_del_servicio(self):
        from dfchron import servicio_consulta as qc
        from dfchron import adaptador_consulta as ac

        respuesta = ac.ficha_figura("712")
        servicio = qc.obtener_entidad("figura", "712")
        self.assertIsNot(respuesta, servicio,
                         "el adaptador devuelve el MISMO objeto: una "
                         "modificacion del consumidor lo alcanzaria")
        self.assertIsNot(respuesta.get("data"), servicio.get("data"),
                         "data no es una copia independiente")


if __name__ == "__main__":
    unittest.main(verbosity=2)