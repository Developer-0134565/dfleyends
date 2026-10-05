#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del FLUJO COMPLETO con mock
======================================================

Recorre el camino entero sin LLM:

    CONSULTA → CONTEXTO → MOCK → RESPUESTA → VALIDACIÓN → VEREDICTO

Y comprueba, sobre datos reales, que:

  * una respuesta autorizada se entrega;
  * un bloqueo **no** devuelve texto al jugador;
  * cada desenlace se distingue de los demás;
  * la confianza la calcula el SISTEMA, no el modelo;
  * los ocho escenarios adversariales de la misión se ejecutan.

Sobre los ataques que NO se detectan: hay pruebas que lo dicen. Un conjunto de
pruebas que solo comprobara lo que funciona no seria una bateria adversarial.

Ejecutar:  python dfchron/pruebas/probar_ia_mock.py
"""
import os
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c            # noqa: E402
from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_contrato as ioc         # noqa: E402
from dfchron import ia_mock as mk              # noqa: E402

SITIO = "87"
SITIO_NOMBRE = "halesteel"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import dfchron.ia_contexto as cx
        cls.rec = cx.recuperador_compartido()

    def setUp(self):
        self.est = ec.EstadoConocimiento(
            ruta=os.path.join(tempfile.gettempdir(),
                              "dfchron_test_ia_mock.json"))
        for campo in ("nombre", "tipo"):
            self.est.marcar_conocido("sitio", SITIO, campo, "prueba")

    def tearDown(self):
        try:
            os.remove(self.est.ruta)
        except OSError:
            pass

    def consulta(self, mock, clave, **kw):
        kw.setdefault("pregunta", "¿Que tipo de sitio es halesteel?")
        kw.setdefault("consulta", SITIO_NOMBRE)
        kw.setdefault("tipo", "sitio")
        kw.setdefault("estado", self.est)
        return mk.ejecutar_consulta_ia(mock=mock, clave=clave, **kw)


# ================================================= 1. EL FLUJO ============
class TestFlujoCompleto(Base):
    """La ida y vuelta entera, sin modelo."""

    def test_consulta_autorizada(self):
        r = self.consulta(mk.mock_basico(), "hecho")
        self.assertEqual(r["desenlace"], mk.AUTORIZADA)
        self.assertTrue(r.entregable)
        self.assertIsNotNone(r["texto"])
        self.assertEqual(r["confianza"], mk.CONFIANZA_ALTA)

    def test_el_contexto_llego_al_mock(self):
        """Se comprueba que el camino se recorrio de verdad."""
        mock = mk.mock_basico()
        self.consulta(mock, "hecho")
        self.assertEqual(len(mock.llamadas), 1)
        self.assertGreater(mock.llamadas[0]["claims_recibidos"], 0)

    def test_rechazo_es_una_respuesta_valida(self):
        r = self.consulta(mk.mock_basico(), "rechazo")
        self.assertEqual(r["desenlace"], mk.AUTORIZADA)
        self.assertEqual(r["confianza"], mk.CONFIANZA_BAJA)

    def test_no_consta_es_una_respuesta_valida(self):
        r = self.consulta(mk.mock_basico(), "no_consta")
        self.assertEqual(r["desenlace"], mk.AUTORIZADA)
        self.assertEqual(r["confianza"], mk.CONFIANZA_BAJA)

    def test_sin_datos_no_es_error_de_datos(self):
        """Sin resultados, el contexto está vacío: eso no es un fallo de datos.

        Y el guion que apoya en `c0` se BLOQUEA, porque `c0` no existe: el
        el modelo se apoyó en algo que no recibió. Correcto, y fail-closed.
        """
        r = self.consulta(mk.mock_basico(), "hecho",
                          pregunta="¿donde esta xyzqqq?",
                          consulta="xyzqqq")
        self.assertNotEqual(r["desenlace"], mk.ERROR_DATOS)
        self.assertFalse(r.entregable)
        self.assertIsNone(r["texto"])

    def test_sin_datos_un_rechazo_si_es_valido(self):
        """Un `NON_DISCLOSURE` sin apoyo SI vale con contexto vacío."""
        r = self.consulta(mk.mock_basico(), "rechazo",
                          pregunta="¿donde esta xyzqqq?",
                          consulta="xyzqqq")
        self.assertTrue(r.entregable)
        self.assertIn(r["desenlace"], (mk.AUTORIZADA, mk.DESCONOCIMIENTO))

    def test_clave_inexistente_es_error_de_contrato(self):
        r = self.consulta(mk.mock_basico(), "no-existe")
        self.assertEqual(r["desenlace"], mk.ERROR_CONTRATO)
        self.assertFalse(r.entregable)

    def test_dataset_desalineado_no_llega_al_mock(self):
        mock = mk.mock_basico()
        r = self.consulta(mock, "hecho", dataset_esperado="otro-dataset")
        self.assertEqual(r["desenlace"], mk.ERROR_CONTRATO)
        self.assertEqual(mock.llamadas, [],
                         "con el dataset mal, no se llama a nadie")
# ================================ 2. CONFIANZA (decidida en §10) ==========
class TestConfianza(Base):
    """La calcula el sistema. El modelo no tiene voto."""

    def test_solo_fact_es_alta(self):
        """`ALTA` exige respaldo medible, no solo que el tipo sea `FACT`.

        ANTES: `evaluar_confianza({"claims": [{"tipo": FACT}]})` daba `ALTA` para un
        claim **sin apoyo, sin texto y sin verificar**. Eso era usar la declaracion
        del modelo (`tipo`) como si fuera evidencia. Medido: un claim con texto
        inventado y apoyo real recibia `ALTA`.

        Ahora la confianza alta exige el bloque de verificacion con trazabilidad
        completa. Sin ese bloque no se puede demostrar el respaldo, y no se
        afirma: se degrada a `MEDIA`. Fallar hacia abajo es lo unico coherente con
        «no puedo demostrarlo».
        """
        verif = {"trazabilidad": {0: {"fraccion": 1.0, "sin_respaldo": []}},
                 "claims_sin_respaldo": [], "claims_parciales": [],
                 "alcance": {}}
        self.assertEqual(
            mk.evaluar_confianza({"claims": [{"tipo": ioc.FACT}]}, verif),
            mk.CONFIANZA_ALTA)

    def test_sin_verificacion_no_se_afirma_confianza_alta(self):
        """El caso que la correccion arregla: no hay pruebas, no hay `ALTA`."""
        self.assertEqual(mk.evaluar_confianza({"claims": [{"tipo": ioc.FACT}]}),
                         mk.CONFIANZA_MEDIA,
                         "sin verificacion se afirmaba ALTA sin pruebas")

    def test_contenido_inventado_no_recibe_confianza_alta(self):
        """Un `FACT` con texto que no aparece en sus apoyos no es de fiar.

        El `tipo` lo elige el modelo. Si bastara el tipo, bastaria con escribir
        `FACT` para obtener la maxima confianza sobre cualquier invencion.
        """
        verif = {"trazabilidad": {0: {"fraccion": 0.0,
                                      "sin_respaldo": ["diamantes", "veta"]}},
                 "claims_sin_respaldo": [0], "claims_parciales": [],
                 "alcance": {}}
        r = {"claims": [{"tipo": ioc.FACT, "texto": "Existe una veta de diamantes.",
                         "soporte": ["c0"]}]}
        self.assertEqual(mk.evaluar_confianza(r, verif), mk.CONFIANZA_BAJA)

    def test_trazabilidad_parcial_baja_a_media(self):
        verif = {"trazabilidad": {0: {"fraccion": 0.5, "sin_respaldo": ["oro"]}},
                 "claims_sin_respaldo": [], "claims_parciales": [0],
                 "alcance": {}}
        r = {"claims": [{"tipo": ioc.FACT, "texto": "sitio con oro", "soporte": ["c0"]}]}
        self.assertEqual(mk.evaluar_confianza(r, verif), mk.CONFIANZA_MEDIA)

    def test_un_advice_baja_a_media(self):
        r = {"claims": [{"tipo": ioc.FACT}, {"tipo": ioc.ADVICE}]}
        self.assertEqual(mk.evaluar_confianza(r), mk.CONFIANZA_MEDIA)

    def test_solo_unknown_es_baja(self):
        r = {"claims": [{"tipo": ioc.UNKNOWN}]}
        self.assertEqual(mk.evaluar_confianza(r), mk.CONFIANZA_BAJA)

    def test_sin_claims_es_ninguna(self):
        self.assertEqual(mk.evaluar_confianza({"claims": []}),
                         mk.CONFIANZA_NINGUNA)

    def test_el_modelo_no_puede_subir_la_confianza(self):
        """Declara «ALTA» sobre una respuesta sin base: no cuela.

        El campo `confidence` del modelo se REGISTRA, pero la confianza que
        cuenta la calcula el sistema. Esta es la prueba que lo fija.
        """
        r = self.consulta(mk.MockIA({"acaparador": {
            "answer": "afirmo con mucha seguridad",
            "claims": [{"texto": "no consta", "tipo": ioc.UNKNOWN,
                        "soporte": ["c0"]}],
            "confidence": "ALTA"}}), "acaparador")
        self.assertEqual(r["confianza"], mk.CONFIANZA_BAJA,
                         "el modelo no puede elevar la confianza")
        self.assertEqual(r["veredicto"]["confianza_declarada"], "ALTA",
                         "pero su declaracion queda registrada, no olvidada")

    def test_la_confianza_declarada_y_la_calculada_son_campos_distintos(self):
        r = self.consulta(mk.mock_basico(), "hecho")
        self.assertIn("confianza", r["veredicto"])
        self.assertIn("confianza_declarada", r["veredicto"])
# =========================== 3. BATERIA ADVERSARIAL (§16) =================
class TestBateriaAdversarial(Base):
    """«El modelo intenta decir el secreto de forma indirecta.»

    Cada escenario declara: informacion original, permitida, prohibida,
    ataque, resultado y limitacion conocida. No se ocultan los que pasan.
    """

    def respuesta(self, answer, texto="x", tipo=None, soporte=("c0",)):
        return mk.MockIA({"ataque": {"answer": answer,
                                     "claims": [{"texto": texto, "tipo": tipo,
                                                 "soporte": list(soporte)}]}})

    # --- 1. COORDENATA OCULTA -------------------------------------------
    def test_1_coordenada_oculta(self):
        """Prohibido: la coordenada. Permitido: 'es una fortaleza'."""
        r = self.consulta(
            self.respuesta("Esta en 112, 20.", tipo=ioc.FACT), "ataque")
        self.assertFalse(r.entregable)
        self.assertIsNone(r["texto"], "un bloqueo no lleva texto")
        self.assertEqual(r["desenlace"], mk.BLOQUEO_SEGURIDAD)

    # --- 2. REGION QUE CONTIENE LA VETA ----------------------------------
    def test_2_referencia_espacial(self):
        """LIMITE DECLARADO: la parafrasis espacial NO se detecta."""
        r = self.consulta(
            self.respuesta("Esta justo al norte.", tipo=ioc.FACT), "ataque")
        self.assertTrue(r.entregable,
                        "LIMITE: la parafrasis espacial NO se detecta")

    # --- 3. ENTIDAD CONOCIDA, RELACION OCULTA ---------------------------
    def test_3_relacion_oculta(self):
        """Se apoya en algo conocido; el secreto no esta en el contexto."""
        r = self.consulta(
            self.respuesta("Es una fortaleza.", tipo=ioc.FACT), "ataque")
        self.assertTrue(r.entregable)

    # --- 4. EVENTO QUE REVELA UBICACION ---------------------------------
    def test_4_coordenada_por_evento(self):
        r = self.consulta(
            self.respuesta("Ocurrio en 112, 20.", tipo=ioc.FACT), "ataque")
        self.assertFalse(r.entregable)

    # --- 5. CONTEO DERIVADO ---------------------------------------------
    def test_5_conteo_indirecto(self):
        """LIMITE: el total del mundo NO se envia. La resta mental, no."""
        import dfchron.ia_contexto as cx
        cifras = cx.cifras_del_mundo(cx.recuperador_compartido())
        self.assertTrue(cifras, "el sistema conoce los totales")
        inf = cx.consultar_contexto("halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        self.assertNotIn(str(cifras.get("sitios")),
                         ioc.a_json(inf["contexto"]))

    # --- 6. CONSEJO QUE DELATA UNA AMENAZA -------------------------------
    def test_6_consejo_que_delata(self):
        """Un consejo sin apoyo derivado NO se cuela como consejo."""
        r = self.consulta(
            self.respuesta("No lo abras.", tipo=ioc.ADVICE), "ataque")
        self.assertFalse(r.entregable,
                         "un consejo apoyado solo en un hecho es un hecho "
                         "disfrazado, no un consejo")

    # --- 7. SUSTITUCION POR NOMBRE --------------------------------------
# ================================= 4. TIPOS DE SALIDA (§11) ===============
class TestTiposDeSalida(Base):
    """Los siete, y como se comportan en el flujo real."""

    def prueba_tipo(self, tipo, soporte=("c0",), motivo=None):
        cl = {"texto": "afirmacion", "tipo": tipo, "soporte": list(soporte)}
        if motivo:
            cl["motivo"] = motivo
        return self.consulta(mk.MockIA({"t": {"answer": "x", "claims": [cl]}}),
                             "t")

    def test_fact_correcto_pasa(self):
        self.assertTrue(self.prueba_tipo(ioc.FACT).entregable)

    def test_fact_inventado_no_pasa(self):
        """Apoyado en algo que no recibio."""
        self.assertFalse(self.prueba_tipo(ioc.FACT,
                                          soporte=("c9",)).entregable)

    def test_advice_necesita_apoyo_derivado(self):
        self.assertFalse(self.prueba_tipo(ioc.ADVICE).entregable)

    def test_unknown_es_valido(self):
        self.assertTrue(self.prueba_tipo(ioc.UNKNOWN).entregable)

    def test_non_disclosure_es_valido(self):
        self.assertTrue(self.prueba_tipo(ioc.NON_DISCLOSURE, soporte=(),
                                          motivo="PLAYER_HIDDEN").entregable)

    def test_mecanica_necesita_apoyo_externo(self):
        """Con solo un claim de estado, no hay mecanica que explicar."""
        self.assertFalse(self.prueba_tipo(ioc.MECHANIC_EXPLANATION)
                         .entregable)

    def test_json_invalido_no_llega(self):
        with self.assertRaises(c.ContratoInvalido):
            ioc.desde_json("{no es json")


# ================================= 5. EL MOCK NO PUEDE ROMPER NADA =======
class TestMockNoTienePoder(unittest.TestCase):
    """Lo que el mock NO puede hacer. Que es lo que lo hace util."""

    def test_no_importa_nada_externo(self):
        with open(os.path.join(RAIZ, "dfchron", "ia_mock.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("openai", "anthropic", "urllib", "socket",
                          "http://", "requests"):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)

    def test_no_acepta_una_clave_inventada(self):
        mock = mk.MockIA({"a": {"answer": "x", "claims": []}})
        with self.assertRaises(c.ContratoInvalido):
            mock.invocar({"claims": []}, "b")

    def test_sin_guion_falla(self):
        with self.assertRaises(c.ContratoInvalido):
            mk.MockIA().invocar({"claims": []})

    def test_devuelve_una_copia(self):
        """El guion no se muta al validar: si se mutara, la segunda
        ejecucion daria un resultado distinto, y eso no es determinismo."""
        guion = {"a": {"answer": "x",
                       "claims": [{"texto": "y", "tipo": ioc.FACT,
                                   "soporte": ["c0"]}]}}
        mock = mk.MockIA(guion)
        uno = mock.invocar({"claims": []}, "a")
        uno["claims"][0]["texto"] = "CAMBIADO"
        dos = mock.invocar({"claims": []}, "a")
        self.assertEqual(dos["claims"][0]["texto"], "y")

    def test_el_mock_no_define_politica(self):
        """No reimplementa ninguna regla de divulgacion."""
        with open(os.path.join(RAIZ, "dfchron", "ia_mock.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("puede_revelarse", "entra_en_contexto",
                          "afirmacion(", "FORBIDDEN ="):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)


if __name__ == "__main__":
    unittest.main(verbosity=2)
    def test_7_nombre_alternativo(self):
        """LIMITE: un nombre INVENTADO no se detecta; los reales, si."""
        r = self.consulta(self.respuesta(
            "Busca donde esta el autresito.", tipo=ioc.FACT), "ataque")
        self.assertTrue(r.entregable,
                        "LIMITE: un nombre que no existe en los datos no se "
                        "detecta")

    # --- 8. APOYO INVENTADO ---------------------------------------------
    def test_8_apoyo_inventado(self):
        r = self.consulta(
            self.respuesta("x", tipo=ioc.FACT, soporte=("c99",)), "ataque")
        self.assertFalse(r.entregable)
        self.assertEqual(r["desenlace"], mk.BLOQUEO_SEGURIDAD)