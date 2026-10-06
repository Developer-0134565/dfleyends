#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: pruebas ADVERSARIALES de la frontera API/Web
================================================================

Cada caso de la Parte 8 de la mision, con nombre propio, para que quede
trazable caso por caso y no como un "todo verde" sin desglose.

    A · dataset equivocado   -> la API anuncia otro mundo
    B · evidencia eliminada  -> las pruebas deben fallar
    C · estado alterado      -> NOT_FOUND se vuelve FOUND
    D · bypass               -> el adaptador llama al nucleo
    E · respuesta fabricada  -> la API devuelve datos sin preguntar
    F · mundo incorrecto     -> la identidad del mundo se falsea

DISTINGUE DOS COSAS QUE A VECES SE CONFUNDEN
--------------------------------------------
- Que el DATO sea correcto.
- Que el dato haya PASADO POR la frontera.

Este fichero prueba lo segundo. Un consumidor puede recibir un envelope
perfectamente formado sin haber pasado por `servicio_consulta`; eso es un
bypass aunque el contenido sea verdad. Por eso se INSTRUMENTA el servicio y se
mira que se ejecuto, no que se devolvio.

Uso:  python API_WEB/probar_frontera_adversarial.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))
for _r in (_RAIZ, os.path.join(_RAIZ, "00_SOURCE", "tools")):
    if _r not in sys.path:
        sys.path.insert(0, _r)

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)     # puerto libre, nunca el 877
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def pedir(ruta):
    """(codigo_http, cuerpo_json). Nunca lanza."""
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


class _Instrumentada(unittest.TestCase):
    """Base: envuelve las operaciones del servicio y registra cuales corrieron."""

    def instrumentar(self):
        from dfchron import servicio_consulta as qc
        self.registro = []
        self._originales = {}
        for nombre in qc.contrato()["operaciones"]:
            self._originales[nombre] = getattr(qc, nombre)

            def envolver(orig, n):
                def envoltura(*a, **k):
                    self.registro.append(n)
                    return orig(*a, **k)
                return envoltura

            setattr(qc, nombre, envolver(self._originales[nombre], nombre))
        return self.registro

    def restaurar(self):
        from dfchron import servicio_consulta as qc
        for nombre, fn in self._originales.items():
            setattr(qc, nombre, fn)


# ============================================================ A · DATASET ======
class TestA_DatasetEquivocado(_Instrumentada):
    """A: si el mundo anunciado no es el real, tiene que notarse."""

    def test_el_dataset_id_anunciado_es_el_real(self):
        from dfchron import ia_conocimiento as ic
        cod, env = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("dataset_id"), ic.DATASET_ID)
        self.assertNotEqual(env.get("dataset_id"), "v1-inventado")

    def test_la_evidencia_no_anuncia_otro_dataset(self):
        """El endpoint de evidencia lleva la version DENTRO de `data`.

        Se verifico contra el servidor real: la clave de primer nivel
        `evidence` llega a `null` en esta ruta (vease EVID-006); la evidencia
        real viaja en `data`, que es lo que un cliente debe leer.
        """
        from dfchron import ia_conocimiento as ic
        cod, env = pedir("/api/consulta/evidencia/figura/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("dataset_id"), ic.DATASET_ID)
        datos = env.get("data") or {}
        self.assertEqual(datos.get("state_version"), ic.DATASET_ID)
        self.assertNotEqual(datos.get("state_version"), "v1-inventado")

    def test_fabricar_un_dataset_id_no_pasa_desapercibido(self):
        """El dataset_id viaja en DOS sitios; si uno cambia, se nota."""
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        self.assertIn("dataset_id", env)
        ev = env.get("evidence") or {}
        self.assertEqual(env["dataset_id"], ev.get("state_version"),
                         "el sobre y la evidencia anuncian datasets distintos")


# ========================================================== B · EVIDENCIA ======
class TestB_EvidenciaEliminada(_Instrumentada):
    """B: la evidencia no es opcional en las rutas del perimetro."""

    PERIMETRO = ("/api/figuras/712", "/api/entidades/4", "/api/sitios/4",
                 "/api/artefactos/1", "/api/eventos/1")

    def test_todas_las_fichas_traen_evidencia(self):
        for ruta in self.PERIMETRO:
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                self.assertIsNotNone(env.get("evidence"),
                                     "la ficha perdio la evidencia")
                self.assertIsNotNone((env["evidence"] or {}).get("state_version"),
                                     "la evidencia perdio su state_version")

    def test_el_endpoint_de_evidencia_responde(self):
        cod, env = pedir("/api/consulta/evidencia/figura/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("estado"), "FOUND")
        datos = env.get("data") or {}
        self.assertIn("state_version", datos)
        self.assertIn("funcion", datos)


# ============================================================= C · ESTADO =====
class TestC_EstadoAlterado(_Instrumentada):
    """C: los estados semanticos no se colapsan al transportar por HTTP."""

    def test_no_existente_es_404_y_NOT_FOUND(self):
        cod, env = pedir("/api/consulta/entidad/figura/999999999")
        self.assertEqual(cod, 404)
        self.assertEqual(env.get("estado"), "NOT_FOUND")

    def test_una_relacion_inexistente_no_es_FOUND(self):
        cod, env = pedir("/api/consulta/relaciones/999999999")
        self.assertNotEqual(env.get("estado"), "FOUND")
        self.assertIn(env.get("estado"), ("NOT_FOUND", "NOT_VERIFIED"))

    def test_tipo_sin_identidad_no_inventa_identidad(self):
        """`relacion` no tiene identidad demostrada: no puede fabricarse una."""
        cod, env = pedir("/api/consulta/entidad/relacion/1")
        self.assertNotEqual(env.get("estado"), "FOUND")
        self.assertIsNone(env.get("identity"))

    def test_verificar_fallido_no_es_verificado(self):
        """Una afirmacion falsa debe salir NOT_VERIFIED, no FOUND.

        Predicado y valor TOMADOS del servidor real: la figura 712 NO tiene
        raza DRAGON. Comprobado contra el dataset antes de escribir el test.
        """
        cod, env = pedir("/api/consulta/verificar?tipo=figura&id=712"
                         "&predicado=tiene:raza&objeto=DRAGON")
        self.assertEqual(env.get("estado"), "NOT_VERIFIED")
        self.assertEqual(env.get("certainty"), "UNKNOWN")
        self.assertNotEqual(cod, 404,
                            "NOT_VERIFIED no debe degradarse a 404")
        self.assertNotEqual(cod, 503,
                            "NOT_VERIFIED no es una caida tecnica")

    def test_atributo_no_declarado_no_es_found(self):
        """La entidad EXISTE pero el dataset no declara ese atributo.

        Es el caso que distingue `NOT_VERIFIED` de `FOUND`: no es que falte el
        atributo, es que el dataset **no dice nada** sobre el. Responder FOUND
        seria inventar. Este es exactamente el punto que ancla la mutacion C.
        """
        cod, env = pedir(
            "/api/consulta/atributo/figura/712/atributo_que_no_existe")
        self.assertEqual(cod, 200)
        self.assertEqual(env.get("estado"), "NOT_VERIFIED")
        self.assertEqual(env.get("certainty"), "UNKNOWN")
        self.assertIn("atributos_disponibles", env,
                      "debe decir que atributos SÍ se declaran")
        self.assertIn("no se infiere",
                      ((env.get("error") or {}).get("mensaje") or ""),
                      "la ausencia debe declarar que no se infiere")

    def test_entidad_inexistente_es_404_no_not_verified(self):
        """Aqui sí: el dato no existe de ninguna manera."""
        cod, env = pedir("/api/consulta/atributo/figura/999999999/nombre")
        self.assertEqual(cod, 404)
        self.assertNotEqual(env.get("estado"), "FOUND")



# ============================================================== D · BYPASS =====
class TestD_Bypass(_Instrumentada):
    """D: la llamada REAL tiene que pasar por `servicio_consulta`."""

    #: (ruta, operacion del servicio que debe ejecutarse)
    RUTAS = [
        ("/api/figuras/712", "obtener_entidad"),
        ("/api/entidades/4", "obtener_entidad"),
        ("/api/sitios/4", "obtener_entidad"),
        ("/api/artefactos/1", "obtener_entidad"),
        ("/api/eventos/1", "obtener_entidad"),
        ("/api/figuras/712/relaciones", "buscar_relaciones"),
        ("/api/consulta/entidad/figura/712", "obtener_entidad"),
        ("/api/consulta/contar/figura", "contar"),
        ("/api/consulta/evidencia/figura/712", "obtener_evidencia"),
        ("/api/consulta/relaciones/712", "buscar_relaciones"),
    ]

    def test_el_flujo_real_pasa_por_el_servicio(self):
        registro = self.instrumentar()
        try:
            for ruta, esperado in self.RUTAS:
                with self.subTest(ruta=ruta):
                    del registro[:]
                    cod, _env = pedir(ruta)
                    self.assertEqual(cod, 200)
                    self.assertIn(esperado, registro,
                                  "%s NO paso por servicio_consulta.%s"
                                  % (ruta, esperado))
        finally:
            self.restaurar()

    def test_la_navegacion_no_usa_la_frontera_por_accidente(self):
        """Las rutas de navegacion NO deben pasar por la capa de consulta."""
        self.instrumentar()
        try:
            for ruta in ("/api/buscar?q=uruc", "/api/listar/artifacts",
                         "/api/geografia", "/api/stats", "/api/salud",
                         "/api/figuras/712/eventos"):
                with self.subTest(ruta=ruta):
                    del self.registro[:]
                    cod, _env = pedir(ruta)
                    self.assertEqual(cod, 200)
                    self.assertEqual(
                        set(self.registro), set(),
                        "%s atraviesa la frontera sin necesitarla" % ruta)
        finally:
            self.restaurar()


# ================================================= E · RESPUESTA FABRICADA ====
class TestE_RespuestaFabricada(_Instrumentada):
    """E: un envelope correcto por casualidad NO demuestra pasar por el servicio."""

    def test_el_envelope_coincide_con_el_servicio(self):
        """No basta con que se parezcan: tiene que ser el MISMO valor."""
        from dfchron import servicio_consulta as qc
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        directo = qc.obtener_entidad("figura", "712")
        for clave in ("estado", "dataset_id", "certainty", "status"):
            with self.subTest(clave=clave):
                self.assertEqual(env.get(clave), directo.get(clave),
                                 "la API difiere del servicio en %r" % clave)

    def test_el_adaptador_no_puede_saltarse_al_nucleo(self):
        """El adaptador debe llamar al servicio, no leer el indice."""
        import inspect

        from dfchron import adaptador_consulta as ac
        fuente = inspect.getsource(ac)
        self.assertNotIn("obtener_archivo()", fuente,
                         "el adaptador lee el indice del nucleo")
        self.assertIn("qc.obtener_entidad", fuente)


# =========================================================== F · MUNDO =========
class TestF_MundoIncorrecto(unittest.TestCase):
    """F: la identidad del mundo no puede falsearse sin que se note."""

    def test_el_mundo_llega_por_la_api_y_no_se_inventa(self):
        cod, env = pedir("/api/salud")
        self.assertEqual(cod, 200)
        mundo = env.get("mundo")
        if mundo is not None:
            for clave in ("world_name", "world_folder"):
                self.assertIn(clave, mundo)
            if mundo.get("world_name") is None:
                self.assertTrue(mundo.get("ausente_porque"),
                                "ausencia sin motivo declarado")

    def test_el_mundo_no_es_el_dataset_id(self):
        """P1: el mundo y el contenido son cosas distintas."""
        cod, env = pedir("/api/salud")
        self.assertEqual(cod, 200)
        mundo = env.get("mundo") or {}
        for valor in (mundo.get("world_name"), mundo.get("world_folder")):
            if valor:
                self.assertNotEqual(valor, env.get("dataset_id"))

    def test_el_sobre_de_consulta_no_inventa_mundo(self):
        """El sobre de consulta no lleva `mundo`: no se fabrica identidad."""
        cod, env = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(cod, 200)
        self.assertNotIn("mundo", env,
                         "la capa de consulta no declara identidad de mundo")


if __name__ == "__main__":
    unittest.main(verbosity=2)

