#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: PRUEBA END-TO-END DE LA CADENA COMPLETA.
==============================================================

Recorre SIN simular ninguna capa:

    fixture (registros crudos)
        ↓
    chronicles_motor.construir      (motor: evento, orden, dedupe, informe)
        ↓
    servicio_consulta.consultar_*   (servicio: sobre + estados + contrato)
        ↓
    adaptador_consulta.*            (adaptador: validacion + http_status)
        ↓
    dfchron.api (HTTP real)         (API: delegacion, sin logica de dominio)
        ↓
    respuesta JSON                  (lo que la Web consumiria)

LA PRUEBA CLAVE DE DELEGACION
-----------------------------
`test_la_api_delega_en_el_servicio`: se sustituye `qc.consultar_eventos` por
una funcion rota; las rutas `/api/chronicles/eventos` deben cambiar (no dar
el resultado correcto). Si la API duplicara la logica en vez de delegar, la
respuesta seguiria intacta y la prueba fallaria. Es la demostracion de que la
API USA el servicio y no lo imita.

NOTA SOBRE EL SERVICIO Y EL DATASET REAL
----------------------------------------
`servicio_consulta` lee SIEMPRE el dataset real (su `_cronica()` cachea por
huella). Para que el E2E corra sobre fixtures, esta suite inyecta la cronica
de la fixture sustituyendo `_cronica` durante la prueba: es la unica costura
necesaria, y solo existe AQUI (en produccion no hay ningun interruptor).
Cada test restaura el original en `finally`.
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
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dfchron import chronicles_motor as cm          # noqa: E402
from dfchron import servicio_consulta as qc         # noqa: E402
from dfchron import adaptador_consulta as ac        # noqa: E402
from dfchron.pruebas import fixtures_e2e as fx      # noqa: E402

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def _base():
    return "http://127.0.0.1:%d" % _arrancar().server_address[1]


def pedir(ruta):
    """`(codigo, cuerpo)` sobre el servidor HTTP REAL."""
    req = urllib.request.Request(_base() + ruta, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            crudo = r.read().decode("utf-8")
            return r.status, (json.loads(crudo) if crudo else None)
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8")
        return e.code, (json.loads(crudo) if crudo else None)


def _cronica_de(letra):
    """Cronica construida desde la fixture, pasando por JSON (como el cable)."""
    datos = fx.serializar(fx.FIXTURES[letra])
    return cm.construir(datos["eventos"], datos["figuras"], (),
                        dataset_id="ds:fixture-%s" % letra)


class _ConFixture(unittest.TestCase):
    """Inyecta la cronica de la fixture en el servicio durante el test."""

    def _inyectar(self, letra):
        self._letra = letra
        self._orig = qc._cronica
        cronica = _cronica_de(letra)
        qc._cronica = lambda: cronica   # noqa: E731
        return cronica

    def tearDown(self):
        qc._cronica = self._orig


def setUpModule():
    _arrancar()