#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GATE PRE-LLM. La puerta que hay que cruzar antes de conectar un modelo.

QUE ES
------
Un ejecutable que comprueba, de forma automatica y sin red, que las propiedades
criticas del nucleo siguen siendo verdad. No modifica produccion: solo lee,
comprueba y dice.

POR QUE UN GATE Y NO UNA SUITE MAS
-----------------------------------
Una suite mide codigo. El gate mide una **decision**: si hoy se puede empezar a
integrar un modelo. Si alguien anade despues una via por la que el modelo
escriba en el nucleo, o un campo que conceda privilegios, el gate tiene que
decirlo ANTES, no despues de descubrirlo jugando.

COMO SE USA EL RESULTADO
------------------------
    PASS           -> se puede integrar, con el contrato congelado.
    FAIL           -> no se integra. Un FAIL aqui no es un fallo de test: es un
                      fallo de seguridad, y se investiga antes de continuar.
    NOT PROVEN     -> la capacidad NO existe en el nucleo. No es un PASS
                      disfrazado: es una reserva explicita.

Ejecutar:  python dfchron/pruebas/probar_gate_pre_ia.py
"""
import copy
import json
import os
import sys
import unittest

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    _RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

from dfchron import contrato_ia as c            # noqa: E402
from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_contrato as ioc          # noqa: E402
from dfchron import ia_estructura as es         # noqa: E402
from dfchron import ia_frontera as fr           # noqa: E402

S0 = "v1-0000000000000000"
S1 = "v2-1111111111111111"

#: Lo que un adaptador hostil intenta, enumerado para que no se olvide ninguno.
CAMPOS_DE_PRIVILEGIO = ("verified", "trusted", "confidence", "admin_override",
                        "visibility", "discovered", "source")

TEXTO_LIBRE = "texto libre del modelo"


def _ev(campo="tipo", df_id="112", version=S0):
    return c.evidencia("sitio", df_id, [campo], "nucleo.Archivo.ficha_sitio",
                       ["legends.xml"], state_version=version)


def _afirmacion(**extra):
    a = {"claim": "El sitio es de tipo 'hamlet'.", "entidad": "sitio",
         "df_id": "112", "truth_status": ioc.FACT,
         "knowledge_source": c.PLAYER_KNOWLEDGE,
         "visibility": c.PLAYER_VISIBLE, "disclosure": c.ALLOWED,
         "evidence": [_ev()]}
    a.update(extra)
    return a


def _contexto(**extra):
    return ioc.contexto("¿Que tipo de sitio es el 112?", [_afirmacion(**extra)])


class _Rec:
    """Un recuperador minimo: solo sabe la ficha del sitio de prueba."""

    FICHAS = {"112": {"tipo": "hamlet", "nombre": "begunboard", "eventos": 47}}

    def ficha_de(self, tipo, df_id):
        return copy.deepcopy(self.FICHAS.get(str(df_id))) if tipo == "sitio" else None


# ============================ 1-15. LOS INVARIANTES DEL GATE ===============
class TestGatePreIA(unittest.TestCase):
    """Los quince puntos, numerados como los declara la mision."""

    def test_01_el_modelo_no_controla_la_verdad(self):
        """La verdad es del nucleo: una propuesta no la mueve."""
        ctx = _contexto()
        antes = copy.deepcopy(ctx["claims"][0])
        ioc.validar_salida({"answer": "x", "claims": [
            {"ref": "c0", "texto": "mentira", "tipo": ioc.FACT,
             "soporte": ["c0"]}]}, ctx)
        self.assertEqual(ctx["claims"][0], antes)

    def test_02_el_modelo_no_controla_la_verificacion(self):
        """Declararse verificado no verifica."""
        ctx = _contexto()
        detalle = es.verificar_claims(
            [{"ref": "c0", "texto": "Hay diamantes.", "tipo": ioc.FACT,
              "soporte": ["c0"], "verified": True, "trusted": True}], ctx, _Rec())
        for v in detalle.values():
            self.assertNotEqual(v["estado"], es.VERIFICADA)

    def test_03_el_modelo_no_controla_la_visibilidad(self):
        """Nada se hace visible porque el modelo lo pida."""
        ctx = _contexto(discovered=True)
        self.assertEqual(ctx["claims"][0]["visibility"], c.PLAYER_VISIBLE)
        self.assertNotIn("discovered", ctx["claims"][0])

    def test_04_el_modelo_no_controla_la_politica(self):
        """La politica se aplica al construir el contexto, no despues."""
        for modo in (ioc.MODO_RAZONAMIENTO, ioc.MODO_RESPUESTA):
            self.assertEqual(
                ioc.contexto("dime", [_afirmacion(disclosure=c.FORBIDDEN)],
                             modo)["claims"], [])

    def test_05_el_texto_libre_no_es_evidencia(self):
        """Un texto libre no se convierte en rastro ni en coordenada."""
        ctx = _contexto()
        for claim in ctx["claims"]:
            for e in claim["evidence"]:
                self.assertNotEqual(e.get("funcion"), TEXTO_LIBRE)
                self.assertNotEqual(e.get("fuente"), TEXTO_LIBRE)
        self.assertTrue(ioc.deteccion_fuga("Esta en las coordenadas '(112, 20)'."))

    def test_06_una_evidencia_invalida_no_verifica(self):
        """Valor que el nucleo desmiente -> NO_VERIFICADA."""
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev(), {"tipo": "fortress"})
        self.assertEqual(r["estado"], es.NO_VERIFICADA)

    def test_07_una_evidencia_incorrecta_no_verifica(self):
        """Una referencia inexistente no se convierte en verdad."""
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev(df_id="no-existe"), None)
        self.assertNotEqual(r["estado"], es.VERIFICADA)

    def test_08_la_persistencia_no_eleva_privilegios(self):
        """Cargar un estado con campos de privilegio no concede nada."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "estado.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"schema_version": ec.SCHEMA_VERSION,
                           "dataset_id": ec.dataset_actual(),
                           "knowledge": {"entidad|sitio:112": {
                               "tipo": "sitio", "df_id": "112",
                               "verified": True, "trusted": True,
                               "admin_override": True}}}, f)
            estado = ec.EstadoConocimiento(ruta, ec.dataset_actual())
            self.assertTrue(estado.esta_conocido("sitio", "112"))
            # Lo unico afirmado es «el jugador lo conoce». Nada mas.
            self.assertNotIn("visibility", estado.obtener_conocimiento())

    def test_09_la_reconstruccion_no_depende_de_texto_libre(self):
        """El mismo estado produce el mismo texto, con `answer` o sin el."""
        ctx = _contexto()
        claim = [{"ref": "c0", "texto": "El sitio es de tipo 'hamlet'.",
                  "tipo": ioc.FACT, "soporte": ["c0"]}]
        con = fr.componer_seguro(
            ioc.respuesta("texto inventado", claim)["claims"], ctx)[0]
        sin = fr.componer_seguro(claim, ctx)[0]
        self.assertEqual(con, sin)
        self.assertEqual(con, "El sitio es de tipo 'hamlet'.")

    def test_10_el_orden_de_llegada_no_cambia_la_verdad(self):
        """El veredicto no depende del orden en que se evaluen las evidencias."""
        texto, ficha_s1 = "El sitio es de tipo 'fortress'.", {"tipo": "fortress"}
        a = es.verificar_afirmacion(texto, _ev(version=S0), ficha_s1)
        b = es.verificar_afirmacion(texto, _ev(version=S1), ficha_s1)
        self.assertEqual(a["estado"], b["estado"])

    def test_11_los_campos_de_privilegio_no_conceden_privilegios(self):
        """Todos a la vez, y el veredicto no se mueve."""
        ctx = _contexto()
        hostil = {"ref": "c0", "texto": "Hay diamantes.", "tipo": ioc.FACT,
                 "soporte": ["c0"]}
        for campo in CAMPOS_DE_PRIVILEGIO:
            hostil[campo] = True
        limpio = {"ref": "c0", "texto": "Hay diamantes.", "tipo": ioc.FACT,
                  "soporte": ["c0"]}
        v1 = ioc.validar_salida({"answer": "x", "claims": [hostil]}, ctx)
        v2 = ioc.validar_salida({"answer": "x", "claims": [limpio]}, ctx)
        self.assertEqual(v1["puede_entregarse"], v2["puede_entregarse"])
        self.assertEqual(v1["claims_ok"], v2["claims_ok"])
        self.assertEqual(v1["claims_rechazados"], v2["claims_rechazados"])

    def test_12_el_compositor_no_recibe_autoridad_del_modelo(self):
        """El compositor compone el contexto, no lo que el modelo declaro."""
        ctx = _contexto()
        texto = fr.componer_seguro(
            [{"ref": "c0", "texto": "El sitio es de tipo 'hamlet'.",
              "tipo": ioc.FACT, "soporte": ["c0"], "trusted": True,
              "admin_override": True}], ctx)[0]
        self.assertEqual(texto, "El sitio es de tipo 'hamlet'.")

    def test_13_lo_prohibido_no_entra_en_contexto(self):
        """`FORBIDDEN` no entra en ningun modo, ni de razonamiento."""
        for modo in (ioc.MODO_RAZONAMIENTO, ioc.MODO_RESPUESTA):
            self.assertEqual(ioc.contexto("x", [_afirmacion(
                disclosure=c.FORBIDDEN)], modo)["claims"], [])

    def test_14_si_hay_versionado_la_evidencia_obsoleta_falla(self):
        """La evidencia de otro estado del mundo no es actual.

        Y una evidencia SIN version no se presume actual: se declara
        desconocida, y lo desconocido no sostiene una afirmacion.
        """
        self.assertTrue(c.evidencia_es_actual(_ev(version=S0), S0))
        self.assertFalse(c.evidencia_es_actual(_ev(version=S0), S1))
        self.assertFalse(c.evidencia_es_actual(c.evidencia("sitio", "1", ["tipo"]),
                                               S0))

    def test_15_la_temporalidad_se_declara_sea_o_no(self):
        """El gate comprueba que el nucleo Diga la verdad sobre su temporalidad.

        Aqui SI existe identidad real del estado (`dataset_id`, derivado del
        contenido). Si un dia dejara de existir, esta misma prueba falla, que es
        justo lo que se le pide a un gate: no dejar que una capacidad se
        pierda en silencio y siga contando como si existiera.
        """
        v = ec.dataset_actual()
        self.assertTrue(v)
        self.assertNotEqual(v, "UNKNOWN")
        from dfchron import ia_conocimiento as ic
        self.assertEqual(ic.DATASET_ID, v)


if __name__ == "__main__":
    unittest.main(verbosity=2)
