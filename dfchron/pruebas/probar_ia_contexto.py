#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del MOTOR DE CONTEXTO
===============================================

Comprueba, contra los DATOS REALES del dataset, que el motor:

  * recupera entidades, sitios y figuras que existen;
  * devuelve contexto vacío cuando no encuentra nada;
  * respeta la granularidad de descubrimiento, campo a campo;
  * NO entrega coordenadas de un sitio que el jugador no ha descubierto;
  * minimiza y REGISTRA el truncamiento;
  * ordena de forma determinista;
  * no escribe ni en el dataset ni en el estado.

Cada prueba dice qué limitation conoce. No hay pruebas que finjan cubrir algo
que no se cubre.

Ejecutar:  python dfchron/pruebas/probar_ia_contexto.py
"""
import os
import re
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c            # noqa: E402
from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_contexto as cx           # noqa: E402
from dfchron import ia_contrato as ioc         # noqa: E402

#: Un sitio REAL del dataset, con coordenadas reales. Se usa el mismo en todas
#: las pruebas para que el resultado no dependa de lo que se busque.
SITIO = "87"
SITIO_NOMBRE = "halesteel"
FIGURA = "712"
FIGURA_NOMBRE = "galka shafttop"


def estado_temporal():
    """Un estado de jugador AISLADO, en un fichero temporal.

    Importa en una linea: las pruebas no pueden escribir en el estado real de
    nadie. Se borra al terminar la clase.
    """
    return ec.EstadoConocimiento(
        ruta=os.path.join(tempfile.gettempdir(),
                          "dfchron_test_ia_contexto.json"))


class Base(unittest.TestCase):
    """Carga el indice UNA vez: `nucleo.Archivo` tarda ~2,5 s."""

    @classmethod
    def setUpClass(cls):
        cls.rec = cx.Recuperador()
        cls.archivo = cls.rec.puente.archivo

    def setUp(self):
        self.est = estado_temporal()

    def tearDown(self):
        try:
            os.remove(self.est.ruta)
        except OSError:
            pass


# ================================================ 1. RECUPERACION ==========
class TestRecuperacion(Base):
    """Que se找 lo que existe, y solo eso."""

    def test_el_dataset_real_carga(self):
        stats = self.archivo.estadisticas()
        self.assertIn("sitios", stats)
        self.assertGreater(stats["sitios"], 0,
                           "el dataset real tiene que estar disponible")

    def test_encuentra_un_sitio_real(self):
        r = self.rec.buscar(SITIO_NOMBRE, tipo="sitio")
        self.assertTrue(r, "halesteel esta en el dataset")
        self.assertEqual(r[0]["df_id"], SITIO)

    def test_encuentra_una_figura_real(self):
        r = self.rec.buscar(FIGURA_NOMBRE, tipo="figura")
        self.assertTrue(r, "galka shafttop esta en el dataset")
        self.assertEqual(r[0]["df_id"], FIGURA)

    def test_no_encuentra_lo_que_no_existe(self):
        self.assertEqual(self.rec.buscar("xyzqqqnoexiste", tipo="sitio"), [])

    def test_tipo_invalido_rechazado(self):
        with self.assertRaises(cx.ConsultaInvalida):
            self.rec.buscar("x", tipo="relacion")

    def test_consulta_vacia_rechazada(self):
        for mala in ("", "   ", None):
            with self.subTest(consulta=mala):
                with self.assertRaises(cx.ConsultaInvalida):
                    self.rec.buscar(mala)

    def test_las_relaciones_no_se_recuperan(self):
        """El nucleo no da id estable a las relaciones. No se inventa uno."""
        self.assertIn("relacion", cx.TIPOS_NO_RECUPERABLES)
        self.assertNotIn("relacion", cx.TIPOS_RECUPERABLES)

    def test_orden_determinista(self):
        a = self.rec.buscar("the", limite=5)
        b = self.rec.buscar("the", limite=5)
        self.assertEqual([x["df_id"] for x in a], [x["df_id"] for x in b])

    def test_respeta_el_limite_de_busqueda(self):
        r = self.rec.buscar("the", limite=3)
        self.assertLessEqual(len(r), 3)

    def test_conserva_la_procedencia(self):
        """Cada resultado sabe de donde vino."""
        sobre = self.rec.conocimiento_de("sitio", SITIO)
        prov = sobre["provenance"]
        self.assertEqual(prov["entity_type"], "sitio")
        self.assertEqual(prov["entity_id"], SITIO)
        self.assertTrue(prov["funciones"])
        self.assertTrue(prov["dataset_id"])
# --- un dato que no existe da UNKNOWN, no un fallo -------------------
    def test_registro_inexistente_da_unknown(self):
        sobre = self.rec.conocimiento_de("sitio", "999999999")
        self.assertEqual(sobre["asunto"]["certeza"], c.UNKNOWN)
        for a in sobre["claims"]:
            self.assertEqual(a["truth_status"], c.UNKNOWN)


# ==================================================== 2. CONTEXTO ==========
class TestContexto(Base):
    """La granularidad de descubrimiento, campo a campo."""

    def descubre_sitio(self, *campos):
        for campo in campos:
            self.est.marcar_conocido("sitio", SITIO, campo, "prueba")

    def test_sin_descubrir_no_entra_nada(self):
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        self.assertEqual(inf["claims_entregados"], 0)
        self.assertEqual(inf["ocultos_excluidos"], 1)

    def test_descubierto_el_tipo_entra_el_tipo(self):
        self.descubre_sitio("tipo")
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        self.assertGreater(inf["claims_entregados"], 0)
        for cl in inf["contexto"]["claims"]:
            self.assertIn("fortress", cl["claim"])

    def test_no_entra_lo_que_no_se_ha_descubierto(self):
        """Descubrir el tipo NO da las coordenadas. Campo a campo."""
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("dime todo de halesteel",
                                    consulta=SITIO_NOMBRE, tipo="sitio",
                                    estado=self.est)
        self.assertNotIn("112", ioc.a_json(inf["contexto"]),
                         "la coordenada real no puede aparecer")

    def test_descubrir_todo_lo_da_todo(self):
        """Si conoce el registro entero, entra el registro entero."""
        self.est.marcar_conocido("sitio", SITIO, None, "prueba")
        inf = cx.consultar_contexto("dime todo de halesteel",
                                    consulta=SITIO_NOMBRE, tipo="sitio",
                                    estado=self.est)
        self.assertGreater(inf["claims_entregados"], 0)

    def test_nada_va_en_disclosure_forbidden(self):
        """La invariante que no se negocia, sobre datos reales."""
        self.descubre_sitio("nombre", "tipo", "coordenadas")
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        for cl in inf["contexto"]["claims"]:
            self.assertNotEqual(cl["disclosure"], c.FORBIDDEN)

    def test_el_contexto_pasa_el_cerrojo(self):
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        self.assertTrue(inf["cerrable"])
        self.assertTrue(ioc.cerrar_contexto(inf["contexto"]))

    def test_el_contexto_es_de_solo_lectura(self):
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        with self.assertRaises(c.ContratoInvalido):
            inf["contexto"]["claims"] = []

    # --- REGRESION: los defectos hallados por la evaluacion del banco ----
    def test_regresion_consulta_por_tipo_devuelve_el_tipo(self):
        """DEFECTO-01 (corregido): «¿qué tipo de sitio es halesteel?»

        Antes el motor fijaba el campo por el TIPO de la consulta, así que una
        pregunta de tipo solo recibía el campo tipo. Ahora el campo se deduce
        de la PREGUNTA.
        """
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("¿Qué tipo de sitio es halesteel?",
                                    consulta=SITIO_NOMBRE, tipo="sitio",
                                    estado=self.est)
        self.assertTrue(inf["claims_entregados"] > 0)
        for cl in inf["contexto"]["claims"]:
            self.assertEqual(cl["evidence"][0]["datos_utilizados"], ["tipo"])

    def test_regresion_consulta_por_ubicacion_devuelve_coordenadas(self):
        """DEFECTO-01 (corregido): un sitio con coordenadas DESCUBIERTAS.

        Antes la coordenada nunca llegaba aunque estuviera descubierta: el
        filtro la descartaba porque la consulta venía marcada como `sitio`.
        """
        self.descubre_sitio("nombre", "coordenadas")
        inf = cx.consultar_contexto("¿Dónde está halesteel?",
                                    consulta=SITIO_NOMBRE, tipo="sitio",
                                    estado=self.est)
        self.assertTrue(inf["claims_entregados"] > 0)
        for cl in inf["contexto"]["claims"]:
            self.assertEqual(cl["evidence"][0]["datos_utilizados"],
                             ["coordenadas"])

    def test_regresion_consulta_sin_tipo_no_revienta(self):
        """DEFECTO-02 (corregido): buscar en los cinco tipos reventaba.

        `EstadoInvalido: tipo de conocimiento no soportado: None`. Ahora usa el
        tipo del REGISTRO, que es lo que la búsqueda ya sabe.
        """
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("dime todo de halesteel",
                                    consulta=SITIO_NOMBRE, tipo=None,
                                    estado=self.est)
        self.assertIsNotNone(inf["contexto"])

    def test_regresion_una_consulta_por_nombre_no_se_descarta_a_si_misma(self):
        """DEFECTO-03 (corregido): el filtro de palabras tumbaba la respuesta.

        Con la pregunta «dime halesteel», el claim «El sitio es de tipo
        'fortress'» se descartaba porque la palabra «halesteel» no aparece en
        la FRASE del claim. Ahora un claim de una entidad que la búsqueda
        encontró es relevante siempre.
        """
        self.descubre_sitio("nombre", "tipo")
        inf = cx.consultar_contexto("dime halesteel", consulta=SITIO_NOMBRE,
                                    tipo="sitio", estado=self.est)
        self.assertTrue(inf["claims_entregados"] > 0,
                        "una consulta por nombre no puede quedarse vacia")

    def test_campo_buscado_se_deduce_de_la_pregunta(self):
        for pregunta, esperado in (
                ("¿Dónde está?", "coordenadas"),
                ("¿Quién es?", "nombre"),
                ("¿Qué tipo es?", "tipo"),
                ("dime algo", None),
                ("", None)):
            with self.subTest(pregunta=pregunta):
                self.assertEqual(cx._campo_buscado("sitio", pregunta),
                                 esperado)

class TestMinimizacion(Base):
    """Solo lo pertinente, y el truncamiento declarado."""

    def test_limites_explicitos(self):
        for limite in (cx.LIMITE_CLAIMS, cx.LIMITE_FICHAS_POR_BUSQUEDA):
            with self.subTest(limite=limite):
                self.assertIsInstance(limite, int)
                self.assertGreater(limite, 0)

    def test_reducir_registra_el_truncamiento(self):
        muchos = [{"claim": "dato %d" % i,
                   "evidence": [{"entidad": "x", "df_id": str(i),
                                 "datos_utilizados": ["campo"]}]}
                  for i in range(50)]
        _, registro = cx.reducir(muchos, limite=10)
        self.assertTrue(registro["truncado"])
        self.assertEqual(registro["quedan"], 10)
        self.assertEqual(registro["total"], 50)

    def test_sin_truncamiento_no_se_declara(self):
        _, registro = cx.reducir([{"claim": "dato", "evidence": []}],
                                 limite=10)
        self.assertFalse(registro["truncado"])

    def test_lo_irrelevante_se_descarta_y_se_cuenta(self):
        claims = [{"claim": "El sitio se llama 'halesteel'.",
                   "evidence": [{"entidad": "sitio", "df_id": "87",
                                 "datos_utilizados": ["nombre"]}]},
                  {"claim": "La muerte es 5.",
                   "evidence": [{"entidad": "figura", "df_id": "712",
                                 "datos_utilizados": ["muerte"]}]}]
        _, registro = cx.reducir(claims, consulta="halesteel")
        self.assertEqual(registro["descartados_por_relevancia"], 1)

# ==================================== 4. AUDITORIA DE DEPENDENCIAS (§7) =====
class TestAuditoriaDeDependencias(Base):
    """Lo que se detecta, y —sobre todo— lo que NO."""

    def claim(self, texto, campos, df_id="87"):
        return c.afirmacion(
            claim=texto, truth_status=c.FACT,
            knowledge_source=c.WORLD_KNOWLEDGE, visibility=c.PLAYER_VISIBLE,
            disclosure=c.ALLOWED,
            evidences=[c.evidencia("sitio", df_id, campos,
                                   "nucleo.ficha_sitio")])

    def test_coordenada_de_un_registro_oculto_se_retira(self):
        """El caso clasico: decir donde esta algo que no se ha visto."""
        a = self.claim("El sitio esta en 112, 20.", ["coordenadas"])
        informe, limpios = cx.auditar_dependencias(
            [a], [{"df_id": "87", "nombre": "halesteel"}],
            cifras={"coordenadas": 734})
        self.assertEqual(limpios, [])
        self.assertEqual(informe["retirados"], 1)

    def test_coordenada_de_un_registro_visible_pasa(self):
        """Si el jugador lo conoce, la coordenada es suya y puede decirse."""
        a = self.claim("El sitio esta en 112, 20.", ["coordenadas"])
        informe, limpios = cx.auditar_dependencias([a], [], cifras={"eventos": 57215})
        self.assertEqual(len(limpios), 1)
        self.assertEqual(informe["retirados"], 0)

    def test_un_conteo_imposible_se_retira(self):
        a = self.claim("El sitio tiene 999999 eventos.", ["eventos"])
        informe, limpios = cx.auditar_dependencias([a], [], cifras={"eventos": 57215})
        self.assertEqual(limpios, [])
        self.assertEqual(informe["riesgo_indirecto"][0]["tipo"], "conteo")

    def test_un_conteo_normal_pasa(self):
        a = self.claim("El sitio tiene 1546 eventos.", ["eventos"])
        _, limpios = cx.auditar_dependencias([a], [], cifras={"eventos": 57215})
        self.assertEqual(len(limpios), 1)

    # --- LO QUE NO SE DETECTA. Y SE DICE. ------------------------------
    def test_una_afirmacion_inocua_no_se_retira(self):
        a = self.claim("El sitio es una fortaleza.", ["tipo"])
        _, limpios = cx.auditar_dependencias([a], [], cifras={"eventos": 57215})
        self.assertEqual(len(limpios), 1)

    def test_el_conteo_indirecto_NO_SE_DETECTA(self):
        """«734 sitios, el jugador conoce 3» NO se marca. Y no se finge."""
        a = self.claim("El jugador conoce 3 sitios.", ["nombre"])
        informe, limpios = cx.auditar_dependencias([a], [], cifras={"eventos": 57215})
        self.assertEqual(len(limpios), 1,
                         "la inferencia por resta NO esta cubierta: la "
                         "heuristica solo detecta imposibilidad, no deducci贸n")

    def test_el_total_del_mundo_no_se_envia_como_campo(self):
        """La proteccion real: el sistema sabe el total, el modelo no.

        Se comprueba que el contexto NO lleva un campo con el total. No se
        comprueba que el numero no aparezca nunca: las limitaciones fijas del
        contrato mencionan otras cifras del mundo a proposito, y eso es otra
        cosa.
        """
        for campo in cx.CAMPOS_POR_TIPO["sitio"]:
            self.est.marcar_conocido("sitio", SITIO, campo, "prueba")
        inf = cx.consultar_contexto("halesteel", consulta="halesteel",
                                    tipo="sitio", estado=self.est)
        claves = set(inf["contexto"].keys())
        self.assertNotIn("total_sitios", claves)
        self.assertNotIn("estadisticas", claves)
        for cl in inf["contexto"]["claims"]:
            self.assertNotIn("total_sitios", cl)
            self.assertNotIn("estadisticas", cl)


# ================================================= 5. DETERMINISMO ========
class TestDeterminismo(Base):
    """Misma entrada, mismo contexto, byte a byte."""

    def test_el_contexto_es_byte_a_byte_identico(self):
        for campo in cx.CAMPOS_POR_TIPO["sitio"]:
            self.est.marcar_conocido("sitio", SITIO, campo, "prueba")
        a = cx.consultar_contexto("halesteel", consulta="halesteel",
                                  tipo="sitio", estado=self.est)
        b = cx.consultar_contexto("halesteel", consulta="halesteel",
                                  tipo="sitio", estado=self.est)
        self.assertEqual(ioc.a_json(a["contexto"]), ioc.a_json(b["contexto"]))
        self.assertEqual(a["claims_entregados"], b["claims_entregados"])

    def test_el_informe_es_identico(self):
        a = cx.consultar_contexto("halesteel", consulta="halesteel",
                                  tipo="sitio", estado=self.est)
        b = cx.consultar_contexto("halesteel", consulta="halesteel",
                                  tipo="sitio", estado=self.est)
        self.assertEqual(a.resumen(), b.resumen())

    def test_una_consulta_no_escribe_en_el_estado(self):
        """Consultar es de SOLO LECTURA. Se comprueba, no se promete."""
        antes = self.est.obtener_conocimiento()
        cx.consultar_contexto("halesteel", consulta="halesteel", tipo="sitio",
                              estado=self.est)
        despues = self.est.obtener_conocimiento()
        self.assertEqual(antes, despues)

    def test_una_consulta_no_toca_el_dataset(self):
        """El dataset no se abre ni para escribir."""
        with open(os.path.join(RAIZ, "dfchron", "ia_contexto.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("_escribir", "json.dump", "open(.*[\"']w",
                          "shutil", "os.remove", "os.rename"):
            with self.subTest(patron=prohibido):
                self.assertNotIn(prohibido, fuente)
        self.assertNotIn("import shutil", fuente)

    def test_no_importa_relojes_ni_azar(self):
        with open(os.path.join(RAIZ, "dfchron", "ia_contexto.py"),
                      encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotRegex(fuente, r"^\s*import\s+time", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+random", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+uuid", re.M)


if __name__ == "__main__":
    unittest.main(verbosity=2)




