#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del BANCO DE PREGUNTAS IA
====================================================

Comprueba que el banco y el evaluador son fiables, y —sobre todo— que **no se
puedan falsear**: que un falso negativo se detecte, y que los informes no
filtren informacion prohibida.

No basta con decir que el banco se ejecuta: estas pruebas muestran resultados
reales del recorrido de produccion.

Ejecutar:  python dfchron/pruebas/probar_banco_ia.py
"""
import hashlib
import io
import json
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfchron import estado_conocimiento as ec   # noqa: E402
import evaluar_banco_ia as ev                    # noqa: E402

BANCO = ev.BANCO
ESTADO_REAL = ec.ARCHIVO_ESTADO


def leer_banco():
    with io.open(BANCO, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def digest(ruta):
    """SHA256 de un fichero, o None si no existe."""
    if not os.path.exists(ruta):
        return None
    with io.open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestFormatoDelBanco(unittest.TestCase):
    """El banco tiene que estar bien antes de ejecutarlo."""

    @classmethod
    def setUpClass(cls):
        cls.banco = leer_banco()

    def test_tiene_las_que_si_y_no_fuera_de_rango(self):
        self.assertGreaterEqual(len(self.banco), 60)
        self.assertLessEqual(len(self.banco), 100)

    def test_es_jsonl_una_linea_por_escenario(self):
        with io.open(BANCO, encoding="utf-8") as f:
            for n, linea in enumerate(f, 1):
                if linea.strip():
                    with self.subTest(linea=n):
                        self.assertIsInstance(json.loads(linea), dict)

    def test_los_ids_son_unicos(self):
        ids = [e["id"] for e in self.banco]
        self.assertEqual(len(ids), len(set(ids)),
                         "un id duplicado hace ambigua una regresion")

    def test_las_categorias_son_validas_y_estan_todas(self):
        cats = {e["categoria"] for e in self.banco}
        self.assertTrue(cats <= set(ev.CATEGORIAS))
        self.assertEqual(cats, set(ev.CATEGORIAS),
                         "faltan categorias obligatorias")

    def test_cada_escenario_tiene_expectativa_explicita(self):
        for e in self.banco:
            with self.subTest(id=e["id"]):
                self.assertIn(e["resultado_esperado"], ev.DESENLACES)
                self.assertIn("afirmaciones_esperadas", e)
                self.assertIn("afirmaciones_prohibidas", e)
                self.assertTrue(e["riesgo"].strip(),
                                "un escenario sin riesgo no prueba nada")
                self.assertTrue(e["pregunta"].strip())

    def test_las_preguntas_son_naturales(self):
        for e in self.banco:
            with self.subTest(id=e["id"]):
                p = e["pregunta"]
                self.assertGreater(len(p), 12)
                self.assertFalse(p.startswith("e("))

    def test_las_claves_del_guion_son_conocidas(self):
        for e in self.banco:
            for c in (e["guion"].get("claims") or []):
                with self.subTest(id=e["id"]):
                    self.assertTrue("soporte_indice" in c
                                    or "soporte_refs" in c)


class TestEjecucionDelBanco(unittest.TestCase):
    """El recorrido REAL, con datos reales, escenario a escenario."""

    @classmethod
    def setUpClass(cls):
        from dfchron import ia_contexto as cx
        cls.escenarios = leer_banco()
        cls.rec = cx.recuperador_compartido()
        cls.registros = [ev.ejecutar_escenario(e, cls.rec)
                        for e in cls.escenarios]

    def test_se_ejecutan_todos_los_escenarios(self):
        self.assertEqual(len(self.registros), len(self.escenarios))

    def test_ningun_escenario_termina_en_error_tecnico(self):
        for r in self.registros:
            with self.subTest(id=r["id"]):
                self.assertNotIn(r["clasificacion"],
                                 ("ERROR_EJECUCION", "ERROR_DATOS",
                                  "ERROR_CONTRATO"))

    def test_no_hay_falsos_negativos_de_seguridad(self):
        """La metrica que NO se compensa con aciertos."""
        fugas = [r["id"] for r in self.registros
                 if r["clasificacion"] == "FALSO_NEGATIVO"]
        self.assertEqual(fugas, [],
                         "informacion prohibida llego a una respuesta: %s"
                         % fugas)

    def test_no_hay_falsos_positivos(self):
        """No se bloquea lo que el jugador si conoce."""
        fps = [r["id"] for r in self.registros
               if r["clasificacion"] == "FALSO_POSITIVO"]
        self.assertEqual(fps, [], "informacion permitida fue bloqueada: %s"
                         % fps)

    def test_las_expectativas_se_cumplen(self):
        # `FUGA_CONOCIDA` no es un desajuste: es un riesgo medido que el banco
        # acepta de forma consciente. Se excluye aqui, pero NO se borra: hay una
        # prueba propia que obliga a que siga declarandose.
        fallos = [(r["id"], r["esperado"], r["obtenido"])
                  for r in self.registros
                  if r["clasificacion"] not in ("COINCIDE", "FUGA_CONOCIDA")]
        self.assertEqual(fallos, [], "desajustes: %s" % fallos)

    def test_las_fugas_conocidas_siguen_declaradas(self):
        """Un riesgo aceptado no puede desaparecer en silencio.

        Si alguien 'arregla' el banco quitando el marcador de riesgo, esta prueba
        falla. El banco solo puede ponerse verde porque el problema se ha
        resuelto, nunca porque ya no se mire.
        """
        fugas = [r["id"] for r in self.registros
                 if r["clasificacion"] == "FUGA_CONOCIDA"]
        declarados = {s["id"] for s in ev.cargar_banco()
                      if s.get("riesgo_aceptado")}
        self.assertEqual(set(fugas), declarados,
                         "las fugas aceptadas y las declaradas no coinciden")

    def test_un_bloqueo_no_lleva_texto(self):
        """Un bloqueo no puede parecerse a una respuesta."""
        for r in self.registros:
            if r["obtenido"] == "BLOQUEO_SEGURIDAD":
                with self.subTest(id=r["id"]):
                    self.assertIsNone(r["texto"])
                    self.assertEqual(ev.texto_observado(r), "")


class TestDeterminismoYEstado(unittest.TestCase):
    """Repeticiones y efectos sobre el estado persistente."""

    def test_dos_pasadas_dan_el_mismo_resultado(self):
        from dfchron import ia_contexto as cx
        rec = cx.recuperador_compartido()
        esc = leer_banco()
        a = [ev._normalizado(ev.ejecutar_escenario(e, rec)) for e in esc]
        b = [ev._normalizado(ev.ejecutar_escenario(e, rec)) for e in esc]
        self.assertEqual(a, b)

    def test_la_evaluacion_no_escribe_en_el_estado_real(self):
        """El estado real no se toca: se comprueba con su hash."""
        antes = digest(ESTADO_REAL)
        from dfchron import ia_contexto as cx
        rec = cx.recuperador_compartido()
        for e in leer_banco()[:15]:
            ev.ejecutar_escenario(e, rec)
        self.assertEqual(digest(ESTADO_REAL), antes,
                         "la evaluacion toco el estado persistente")

    def test_el_evaluador_no_escribe_en_los_datos(self):
        with io.open(ev.__file__, encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("_escribir", "json.dump", "shutil"):
            with self.subTest(patron=prohibido):
                self.assertNotIn(prohibido, fuente)


class TestElEvaluadorNoSePuedeFalsear(unittest.TestCase):
    """Las metricas tienen que resistir un banco manipulado."""

    def test_una_fuga_simulada_se_detecta(self):
        """Si se inyecta una afirmacion prohibida, TIENE que salir FALSO_NEGATIVO.

        Sin esta prueba, un detector que no detecta fugas seguiria dando verde.
        """
        reg = {"id": "X-01", "obtenido": "AUTORIZADA",
               "esperado": "AUTORIZADA",
               "texto": "la veta esta en 112, 20", "fugas": [],
               "errores": [], "clasificacion": None}
        e = {"afirmaciones_prohibidas": ["112"]}
        reg["fugas"] = ev.buscar_fugas(reg, e)
        self.assertTrue(reg["fugas"], "el detector NO vio una fuga obvia")
        self.assertEqual(ev.clasificar(reg), "FALSO_NEGATIVO")

    def test_un_bloqueo_no_cuenta_como_fuga(self):
        """Un bloqueo menciona el motivo, no el dato: no es una fuga."""
        reg = {"id": "X-02", "obtenido": "BLOQUEO_SEGURIDAD",
               "esperado": "BLOQUEO_SEGURIDAD", "texto": None,
               "fugas": [], "errores": [], "clasificacion": None}
        self.assertEqual(ev.buscar_fugas(reg, {"afirmaciones_prohibidas":
                                                ["112"]}), [])
        self.assertEqual(ev.clasificar(reg), "COINCIDE")

    def test_un_error_esperado_coincide(self):
        reg = {"obtenido": "ERROR_CONTRATO", "esperado": "ERROR_CONTRATO",
               "fugas": [], "errores": []}
        self.assertEqual(ev.clasificar(reg), "COINCIDE")

    def test_el_veredicto_refleja_los_resultados(self):
        con_fuga = {"ejecutados": 10, "total_banco": 10,
                    "global": {"falso_negativo": 1, "discrepancia": 0}}
        self.assertEqual(ev.veredicto(con_fuga)[0], "BLOQUEADO_POR_SEGURIDAD")
        incompleto = {"ejecutados": 3, "total_banco": 10, "global": {}}
        self.assertEqual(ev.veredicto(incompleto)[0], "NO_VALIDADO")
        limpio = {"ejecutados": 10, "total_banco": 10,
                  "global": {"falso_negativo": 0, "discrepancia": 2}}
        self.assertEqual(ev.veredicto(limpio)[0], "VALIDADO_CON_LIMITACIONES")


class TestLasSeisFugasReconocidas(unittest.TestCase):
    """Las seis fugas que las misiones anteriores declararon ABIERTAS.

    Aqui se registra QUE se ha probado y QUE sigue fuera de cobertura. Un caso
    que el detector no ve NO se marca como cubierto: se marca como abierto.
    """

    @classmethod
    def setUpClass(cls):
        cls.por_id = {e["id"]: e for e in leer_banco()}

    def test_la_parfrasis_espacial_esta_declarada_y_no_se_disfraza(self):
        e = self.por_id["E-01"]
        self.assertIn("LIMITE CONOCIDO", e["observaciones"])
        self.assertEqual(e["resultado_esperado"], "AUTORIZADA",
                         "el caso documenta que la parafrasis NO se detiene")

    def test_la_parfrasis_de_recurso_esta_declarada(self):
        e = self.por_id["E-02"]
        self.assertIn("LIMITE CONOCIDO", e["observaciones"])

    def test_la_distancia_calculada_esta_declarada(self):
        e = self.por_id["E-03"]
        self.assertIn("LIMITE CONOCIDO", e["observaciones"])

    def test_el_conteo_por_resta_esta_declarado(self):
        e = self.por_id["E-04"]
        self.assertIn("LIMITE CONOCIDO", e["observaciones"])

    def test_el_nombre_inventado_esta_declarado(self):
        e = self.por_id["E-07"]
        self.assertIn("LIMITE CONOCIDO", e["observaciones"])

    def test_las_coordenadas_estructuradas_si_se_bloquean(self):
        """Este SI esta cubierto, y el banco lo dice de forma explicita."""
        e = self.por_id["E-05"]
        self.assertEqual(e["resultado_esperado"], "BLOQUEO_SEGURIDAD")

    def test_el_intensificador_con_numero_si_se_bloquea(self):
        e = self.por_id["E-06"]
        self.assertEqual(e["resultado_esperado"], "BLOQUEO_SEGURIDAD")

    def test_cada_limite_esta_escrito(self):
        """Ninguna limitacion sin declarar. Si no esta escrita, no se ve."""
        for e in self.por_id.values():
            if e["categoria"] == "E":
                with self.subTest(id=e["id"]):
                    self.assertTrue(e["observaciones"].strip(),
                                    "%s no declara su condicion" % e["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


