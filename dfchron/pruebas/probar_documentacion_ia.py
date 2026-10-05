#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: La DOCUMENTACION del contrato no puede mentir
==============================================================

Existe porque la auditoria encontro que se habia desviado del codigo sin que
nadie se enterara. La prueba mas dura de esta suite no es del contrato de IA:
es de sus propios documentos.

Lo que se comprueba:

  * la doc no nombra valores que el codigo rechaza (la trampa de `INFERENCE`);
  * la doc no llama "prohibida" a combinaciones que el codigo construye;
  * el contexto de Cline esta al dia respecto al estado real;
  * los ejemplos obligatorios siguen estando;
  * las cifras que se dan como ciertas lo son.

Ejecutar:  python dfchron/pruebas/probar_documentacion_ia.py
"""
import json
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c              # noqa: E402
from dfchron import estado_conocimiento as ec     # noqa: E402

CONTRATO = os.path.join(RAIZ, "08_DATABASE", "ai_data_contract.md")
CONTEXTO = os.path.join(RAIZ, "08_DATABASE", "AI_PROJECT_CONTEXT.md")


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def num_tests_de_contrato():
    """Cuenta las pruebas reales de la suite del contrato, sin ejecutarlas."""
    import importlib.util
    ruta = os.path.join(RAIZ, "dfchron", "pruebas", "probar_contrato_ia.py")
    spec = importlib.util.spec_from_file_location("pcia", ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pcia"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:                                  # noqa: BLE001
        return None
    return unittest.TestLoader().loadTestsFromModule(mod).countTestCases()


# ============================================= LA DOC NO PUEDE MENTIR ========
class TestDocumentacionVeraz(unittest.TestCase):
    """1. Lo que la doc afirma sobre el codigo, es codigo."""

    def setUp(self):
        self.contrato = leer(CONTRATO)
        self.contexto = leer(CONTEXTO)

    def test_INFERENCE_no_se_escribe_como_valor_seriado(self):
        """`INFERENCE` es el NOMBRE de la constante; su VALOR es INTERPRETATION.

        Escribir `"INFERENCE"` en un JSON lo rechaza el validador. La doc lo
        hacia, y eso habria roto a la siguiente mision.
        """
        self.assertEqual(c.INFERENCE, "INTERPRETATION",
                         "si esto cambia, hay que actualizar ambas docs")
        doc = self.contrato + self.contexto
        codigo_json = re.findall(r':\s*"INFERENCE"', doc)
        self.assertEqual(
            codigo_json, [],
            "la doc presenta INFERENCE como valor de JSON, pero el codigo "
            "rechaza ese valor: el serializado es INTERPRETATION")

    def test_el_valor_real_aparece_documentado(self):
        self.assertIn("INTERPRETATION", self.contrato,
                      "ai_data_contract.md debe nombrar el valor real")
        self.assertIn("INTERPRETATION", self.contexto)

    def test_las_cuatro_fuentes_documentadas_existen(self):
        for fuente in c.KNOWLEDGE_SOURCES:
            with self.subTest(fuente=fuente):
                self.assertIn(fuente, self.contrato)

    def test_los_valores_de_cada_dimension_existen(self):
        for nombre, valores in (("truth_status", c.TRUTH_STATUS),
                                ("knowledge_source", c.KNOWLEDGE_SOURCES),
                                ("visibility", c.VISIBILITIES),
                                ("disclosure", c.DISCLOSURES)):
            for valor in valores:
                with self.subTest(d=nombre, v=valor):
                    self.assertIn(f"`{valor}`", self.contrato,
                                  f"{valor} no aparece documentado")

    # --- la tabla de combinaciones prohibidas ----------------------------
    def test_la_doc_no_llama_prohibida_a_lo_que_se_construye(self):
        """`PLAYER_HIDDEN + ALLOWED` NO es prohibido: es no-revelable.

        Se construye sin error y lo bloquea la politica de divulgacion. La doc
        lo listaba como "combinacion que el contrato RECHAZA": era falso.
        """
        EV = [c.evidencia("sitio", "87", ["t"], "nucleo.Archivo.ficha_sitio")]
        a = c.afirmacion("x", c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                         c.ALLOWED, evidences=EV)
        self.assertFalse(c.puede_revelarse(a),
                         "sigue sin ser revelable: eso es lo que importa")
        self.assertIn("no revelable", self.contrato.lower(),
                      "falta distinguir 'rechazada' de 'no revelable'")

    def test_las_rechazadas_de_verdad_son_rechazadas(self):
        EV = [c.evidencia("sitio", "87", ["t"], "nucleo.Archivo.ficha_sitio")]
        casos = [
            ("EXTERNAL_KNOWLEDGE + FACT",
             dict(truth_status=c.FACT, knowledge_source=c.EXTERNAL_KNOWLEDGE,
                  visibility=c.EXTERNAL, disclosure=c.ALLOWED)),
            ("EXTERNAL_KNOWLEDGE + PLAYER_VISIBLE",
             dict(truth_status=c.DERIVED,
                  knowledge_source=c.EXTERNAL_KNOWLEDGE,
                  visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED)),
            ("INFERENCE + FACT",
             dict(truth_status=c.FACT, knowledge_source=c.INFERENCE,
                  visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED)),
            ("WORLD + no_descubierto + PLAYER_VISIBLE",
             dict(truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
                  visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
                  no_descubierto=True)),
        ]
        for nombre, kw in casos:
            with self.subTest(caso=nombre):
                with self.assertRaises(c.ContratoInvalido):
                    c.afirmacion("x", evidences=EV, **kw)

    # --- cifras que se dan por ciertas ----------------------------------
    def test_la_cifra_de_pruebas_del_contrato_no_esta_obsoleta(self):
        reales = num_tests_de_contrato()
        self.assertIsNotNone(reales)
        self.assertIn(str(reales), self.contrato,
                      f"la doc deberia decir {reales} pruebas del contrato")
        self.assertIn(str(reales), self.contexto)

    def test_la_doc_no_afirma_cifras_obsoletas(self):
        for obsoleta in ("44 pruebas", "161 pruebas", "382 unitarias"):
            with self.subTest(cifra=obsoleta):
                self.assertNotIn(obsoleta, self.contrato + self.contexto,
                                 "cifra obsoleta todavia en la documentacion")


# ================================== EL CONTEXTO DE CLINE ESTA AL DIA ========
class TestContextoParaCline(unittest.TestCase):
    """2. El contexto operativo refleja el estado REAL."""

    def setUp(self):
        self.contexto = leer(CONTEXTO)
        self.bajo = self.contexto.lower()

    def test_documenta_la_capa_de_estado_del_jugador(self):
        for token in ("estado_conocimiento", "dataset_id",
                      "PLAYER_KNOWLEDGE"):
            with self.subTest(token=token):
                self.assertIn(token, self.contexto,
                              "el contexto de Cline no lo menciona")

    def test_documenta_lo_que_la_capa_NO_puede_hacer(self):
        for token in ("no_descubierto", "relacion"):
            with self.subTest(token=token):
                self.assertIn(token, self.contexto)

    def test_documenta_la_regla_de_determinismo(self):
        self.assertTrue("determinism" in self.bajo, "falta la regla")
        self.assertIn("timestamp", self.bajo,
                      "falta nombrar timestamps como prohibidos")

    def test_documenta_que_la_frontera_es_arquitectonica(self):
        """La proteccion no puede depender del LLM."""
        # Se aceptan las dos redacciones naturales; lo que no vale es que
        # falte la idea. Comprobar una frase exacta seria fragil.
        negaciones = ("no depender", "no puede depender", "no debe depender",
                      "no ha de depender")
        self.assertTrue(any(n in self.bajo for n in negaciones),
                        "falta decir que la proteccion no depende del modelo")
        self.assertIn("frontera", self.bajo)

    def test_documenta_que_no_hay_ia(self):
        self.assertIn("No existe", self.contexto,
                      "debe quedar claro que la IA no existe todavia")

    def test_las_cuatro_categorias_estan_las_cuatro(self):
        for cat in ("PLAYER_KNOWLEDGE", "WORLD_KNOWLEDGE",
                    "EXTERNAL_KNOWLEDGE", "INFERENCE"):
            with self.subTest(cat=cat):
                self.assertIn(cat, self.contexto)


# ================================ LOS EJEMPLOS OBLIGATORIOS =================
class TestEjemplosObligatorios(unittest.TestCase):
    """3. Lo que la mision exige que este escrito, esta escrito."""

    def setUp(self):
        self.contrato = leer(CONTRATO)

    def test_el_secreto_de_diamantes_esta_documentado(self):
        """Sec.6: WORLD + PLAYER_HIDDEN + FACT + FORBIDDEN, con ejemplo."""
        self.assertIn("PLAYER_HIDDEN", self.contrato)
        self.assertIn("FORBIDDEN", self.contrato)
        self.assertRegex(self.contrato, r"\d+,\s*\d+,\s*\d+",
                         "falta el ejemplo con coordenadas reales")

    def test_el_secreto_es_verdad_y_no_revelable(self):
        s = c.ejemplo_secreto()
        self.assertEqual(s["truth_status"], c.FACT)
        self.assertEqual(s["knowledge_source"], c.WORLD_KNOWLEDGE)
        self.assertEqual(s["visibility"], c.PLAYER_HIDDEN)
        self.assertEqual(s["disclosure"], c.FORBIDDEN)
        self.assertTrue(c.puede_usarse_para_razonar(s))
        self.assertFalse(c.puede_revelarse(s))

    def test_external_knowledge_no_es_world_knowledge(self):
        """Sec.7: la wiki explica reglas; el dataset es ESTA partida."""
        e = c.ejemplo_externo()
        self.assertEqual(e["knowledge_source"], c.EXTERNAL_KNOWLEDGE)
        self.assertEqual(e["visibility"], c.EXTERNAL)
        self.assertFalse(c.puede_usarse_para_razonar(e),
                         "lo externo no puede razonar sobre ESTA partida")
        self.assertTrue(c.puede_revelarse(e),
                        "pero si puede explicar una mecanica")

    def test_la_frontera_external_world_esta_escrita(self):
        self.assertIn("esta partida", self.contrato.lower(),
                      "falta la frase que separa la partida de las reglas")

    def test_fact_no_implica_revelable(self):
        """La regla de oro, con el caso que la demuestra."""
        a = c.afirmacion("secreto", c.FACT, c.WORLD_KNOWLEDGE,
                         c.PLAYER_HIDDEN, c.FORBIDDEN,
                         evidences=[c.evidencia("sitio", "87", ["t"], "f")])
        self.assertEqual(a["truth_status"], c.FACT)
        self.assertFalse(c.puede_revelarse(a), "FACT no puede implicar ALLOWED")
        bajo = self.contrato.lower()
        self.assertTrue("no es permiso" in bajo or "no implica" in bajo,
                        "falta la regla 'FACT no implica ALLOWED'")


# ============================== LA CAPA DE ESTADO SIGUE VIVA ==============
class TestEstadoDelJugadorIntacto(unittest.TestCase):
    """4. Lo que la doc afirma de la capa de estado, sigue siendo cierto."""

    def test_granularidad_real(self):
        self.assertEqual(len(ec.TIPOS_SOPORTADOS), 5)
        self.assertIn("relacion", ec.TIPOS_NO_SOPORTADOS)
        self.assertNotIn("relacion", ec.TIPOS_SOPORTADOS)

    def test_dataset_id_real(self):
        import json
        with open(os.path.join(RAIZ, "00_SOURCE", "dataset_version.json"),
                  encoding="utf-8") as f:
            self.assertEqual(ec.dataset_actual(), json.load(f)["dataset_id"])

    def test_la_capa_no_depende_del_contrato(self):
        """Separacion real: el estado no puede tocar la divulgacion."""
        import ast
        with open(os.path.join(RAIZ, "dfchron", "estado_conocimiento.py"),
                  encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        imports = set()
        for n in ast.walk(arbol):
            if isinstance(n, ast.Import):
                imports.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                imports.add(n.module.split(".")[0])
        self.assertNotIn("contrato_ia", imports)

    def test_la_evidencia_sigue_congelada(self):
        """La inmutabilidad profunda sigue viva."""
        a = c.ejemplo_secreto()
        with self.assertRaises(c.ContratoInvalido):
            a["evidence"][0]["df_id"] = "999"
        with self.assertRaises(c.ContratoInvalido):
            a["evidence"][0]["funcion"] = "falsa"


# ================= 4. LA SEMANTICA CONGELADA ESTA ESCRITA ===============
class TestSemanticaCongeladaDocumentada(unittest.TestCase):
    """Lo que esta mision decidio, tiene que estar escrito.

    Nace porque la auditoria encontro que el codigo y la documentacion pueden
    separarse sin que nadie se entere. Aqui se comprueba lo contrario.
    """

    def setUp(self):
        self.contrato = leer(CONTRATO)
        self.contexto = leer(CONTEXTO)
        self.bajo_contrato = self.contrato.lower()
        self.bajo_contexto = self.contexto.lower()

    # --- la distincion que lo gobierna todo -----------------------------
    def test_distingue_validar_de_revelar(self):
        """§13: las dos funciones existen y responden a preguntas distintas."""
        for token in ("validar()", "puede_revelarse()"):
            with self.subTest(token=token):
                self.assertIn(token, self.contrato,
                              "el contrato debe nombrar las dos funciones")

    def test_player_hidden_allowed_es_valido_y_no_revelable(self):
        """§7/§13: valido, NO invalido, y no revelable. Las tres cosas."""
        EV = [c.evidencia("sitio", "87", ["t"], "nucleo.Archivo.ficha_sitio")]
        a = c.afirmacion("x", c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                         c.ALLOWED, evidences=EV)
        self.assertEqual(c.validar(a), [], "es valido")
        self.assertFalse(c.puede_revelarse(a), "pero no es revelable")
        self.assertIn("no revelable", self.bajo_contrato,
                      "la doc debe usar esa distincion")

    # --- CONDITIONAL ----------------------------------------------------
    def test_conditional_documenta_su_condicion_real(self):
        """§9: su condicion es `pista_permitida`, y hay que nombrarla."""
        self.assertIn("pista_permitida", self.contrato)
        self.assertIn("mencionar", self.bajo_contrato,
                      "hay que decir que se puede mencionar, no afirmar")

    def test_conditional_declara_quien_autoriza_la_pista(self):
        """§9: se decide, o se declara pendiente. Nunca en el aire."""
        pendientes = ("quien autoriza", "no esta decidido", "pendiente",
                      "sin decidir", "no definido", "no esta definido")
        self.assertTrue(
            any(p in self.bajo_contrato for p in pendientes),
            "hay que declarar que autorizar la pista no esta decidido, "
            "o decidirlo explicitamente")

    # --- disclosure_alias -----------------------------------------------
    def test_disclosure_alias_tiene_decision_explicita(self):
        """§10: no se elimina, no se rellena, pero se DECIDE que es."""
        self.assertIn("disclosure_alias", self.contrato,
                      "la decision sobre disclosure_alias debe estar escrita")
        self.assertTrue(
            any(t in self.bajo_contrato for t in ("nadie", "ningun", "ningún")),
            "hay que decir que nadie lo rellena")

    def test_disclosure_alias_no_es_una_dimension_del_codigo(self):
        for nombre, valores in (("truth_status", c.TRUTH_STATUS),
                                ("knowledge_source", c.KNOWLEDGE_SOURCES),
                                ("visibility", c.VISIBILITIES),
                                ("disclosure", c.DISCLOSURES)):
            with self.subTest(dimension=nombre):
                self.assertNotIn("disclosure_alias", valores)
        self.assertNotIn("disclosure_alias",
                         json.dumps(c.contexto_obligatorio()))
# --- INFERENCE + FORBIDDEN -----------------------------------------
    def test_inference_forbidden_tiene_decision_documentada(self):
        """§11: no se deja en el aire. Se dice que NO se rechaza, y por que."""
        EV = [c.evidencia("sitio", "87", ["t"], "nucleo.Archivo.ficha_sitio")]
        a = c.afirmacion("x", c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE,
                         c.FORBIDDEN, evidences=EV)
        # El comportamiento real que la doc tiene que describir:
        self.assertEqual(c.validar(a), [], "no se rechaza")
        self.assertFalse(c.puede_revelarse(a), "y no se divulga")
        self.assertTrue(c.puede_usarse_para_razonar(a), "pero se puede razonar")
        # Y la doc tiene que(holder) los tres valores para contarlo.
        self.assertIn(c.FORBIDDEN, self.contrato)

    def test_la_doc_no_dice_que_inference_forbidden_se_rechaza(self):
        """La doc no puede afirmar lo contrario de lo que hace el codigo."""
        EV = [c.evidencia("sitio", "87", ["t"], "nucleo.Archivo.ficha_sitio")]
        # Si la doc presentara esta fila como "prohibida", estasarian mal:
        c.afirmacion("x", c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE,
                     c.FORBIDDEN, evidences=EV)
        # La fila aparece junto a `ALLOWED` y `CONDITIONAL` en la matriz.
        self.assertRegex(self.contrato, r"INFERENCE[^\n]*FORBIDDEN")

    # --- la matriz ------------------------------------------------------
    def test_la_matriz_cubre_las_filas_que_la_mision_exige(self):
        """Las combinaciones clave son legibles en la doc."""
        for token in ("PLAYER_HIDDEN", "FORBIDDEN", "ALLOWED", "CONDITIONAL",
                      "INTERPRETATION"):
            with self.subTest(token=token):
                self.assertIn(token, self.contrato)

    # --- no vender como implementado lo que no lo esta -----------------
    def test_el_contexto_declara_el_estado_de_implementacion(self):
        """§27: LLM, SDK, endpoints y mod, todos explicitamente NO."""
        ctx = self.contexto.upper()
        for token in ("LLM", "SDK"):
            with self.subTest(token=token):
                self.assertIn(token, ctx)
        self.assertIn("404", self.contexto,
                      "los endpoints IA siguen en 404 y hay que decirlo")
        self.assertIn("NO IMPLEMENTADO", ctx,
                      "el estado de implementacion debe ir escrito en mayusculas")

    def test_no_vende_como_existente_lo_que_no_esta(self):
        """Nada puede leerse como una capacidad ya montada."""
        # Se aceptan las redacciones naturales; lo que no vale es que falte.
        ausencias = ("no implementado", "no existe", "todavia no",
                     "no está implementado", "no hay", "no existe todavia")
        for doc, nombre in ((self.bajo_contrato, "contrato"),
                            (self.bajo_contexto, "contexto")):
            with self.subTest(documento=nombre):
                self.assertTrue(any(a in doc for a in ausencias),
                                "falta declarar que algo NO esta implementado")

    def test_el_contrato_distingue_concepto_de_valor_serializado(self):
        """§28: `INFERENCE` es concepto, `INTERPRETATION` es el valor."""
        self.assertIn("CONCEPTO", self.contrato.upper())
        self.assertIn("VALOR SERIALIZADO", self.contrato.upper())

    def test_las_cifras_de_la_contexto_son_las_reales(self):
        """§31: no se declara una cifra que no se haya comprobado."""
        real = num_tests_de_contrato()
        self.assertIsNotNone(real)
        self.assertIn(str(real), self.contrato)
        self.assertIn(str(real), self.contexto)

    def test_la_frontera_no_depende_del_llm(self):
        """§14: la proteccion es del sistema, no del modelo.

        No basta con que un prompt pida discrecion: la decision la toma una
        funcion que devuelve `False`.
        """
        negaciones = ("no depender", "no puede depender", "no debe depender",
                      "no ha de depender")
        bajo = self.bajo_contexto + self.bajo_contrato
        self.assertTrue(any(n in bajo for n in negaciones),
                        "hay que declarar que la frontera no depende del LLM")

    def test_la_cifra_de_la_semantica_congelada_es_la_real(self):
        """La suite nueva tiene que existir y estar contada en la doc."""
        import importlib.util
        base = os.path.join(RAIZ, "dfchron", "pruebas")
        suites = [f for f in os.listdir(base)
                  if f.startswith("probar_") and f.endswith(".py")]
        self.assertTrue(suites)
        self.assertIn("probar_semantica_ia.py", suites)
        ruta = os.path.join(base, "probar_semantica_ia.py")
        spec = importlib.util.spec_from_file_location("psia", ruta)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["psia"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:                                  # noqa: BLE001
            self.fail("la suite de semantica no se pudo cargar")
        n = unittest.TestLoader().loadTestsFromModule(mod).countTestCases()
        self.assertIn(str(n), self.contexto,
                      "el numero de pruebas de la semantica congelada "
                      "tiene que estar escrito en el contexto")

    def test_la_regla_de_oro_esta_en_los_dos_documentos(self):
        regla = ("La verdad de un dato y el permiso para revelarlo son cosas "
                 "diferentes")
        for nombre, doc in (("contrato", self.contrato),
                            ("contexto", self.contexto)):
            with self.subTest(documento=nombre):
                self.assertIn(regla, doc)
class TestContratoDeEntradaSalidaDocumentado(unittest.TestCase):
    """Lo que la mision de entrada/salida decidio, escrito y vigente."""

    def setUp(self):
        self.contrato = leer(CONTRATO)
        self.contexto = leer(CONTEXTO)
        self.ambos = self.contrato + "\n" + self.contexto

    # --- el problema EXTERNAL -------------------------------------------
    def test_la_decision_de_external_esta_escrita(self):
        """§3: la decision tiene que constar, no solo estar en el codigo."""
        self.assertIn("EXTERNAL", self.contrato)
        for token in ("opcion", "decisión", "elegida"):
            with self.subTest(token=token):
                self.assertIn(token, self.contrato.lower())

    def test_external_ya_no_es_una_via_de_evasion(self):
        """La combinacion prohibida, comprobada contra el codigo real."""
        for ks in (c.WORLD_KNOWLEDGE, c.PLAYER_KNOWLEDGE, c.INFERENCE):
            with self.subTest(ks=ks):
                with self.assertRaises(c.ContratoInvalido):
                    c.afirmacion(
                        "x", c.FACT, ks, c.EXTERNAL, c.ALLOWED,
                        evidences=[c.evidencia("sitio", "1", ["t"], "f")])

    def test_external_knowledge_sigue_pudiendo_explicarse(self):
        """El cierre no castiga a la wiki."""
        a = c.afirmacion(
            "x", c.DERIVED, c.EXTERNAL_KNOWLEDGE, c.EXTERNAL, c.ALLOWED,
            evidences=[c.evidencia("wiki", "w", ["t"], "doc")])
        self.assertTrue(c.puede_revelarse(a))

    # --- entrada y salida -----------------------------------------------
    def test_el_contrato_de_io_existe_y_es_una_parte_del_contrato(self):
        from dfchron import ia_contrato as io
        self.assertIn("ia_contrato", self.contrato + self.contexto,
                      "el modulo de E/S tiene que estar nombrado")
        self.assertEqual(len(io.TIPOS_SALIDA), 7)

    def test_los_siete_tipos_de_salida_estan_documentados(self):
        from dfchron import ia_contrato as io
        for t in io.TIPOS_SALIDA:
            with self.subTest(tipo=t):
                self.assertIn(t, self.ambos)

    def test_los_dos_modos_estan_documentados(self):
        from dfchron import ia_contrato as io
        for m in io.MODOS:
            with self.subTest(modo=m):
                self.assertIn(m, self.ambos)

    def test_la_regla_del_secreto_esta_escrita(self):
        """La decision central: FORBIDDEN no llega al modelo. Ni para razonar."""
        bajo = self.ambos.lower()
        self.assertIn("nunca recibe", bajo)
        self.assertIn("forbidden", bajo)

    def test_el_limite_de_parafrasis_esta_declarado(self):
        """§19: el problema se DECLARA abierto. No se disimula."""
        bajo = self.ambos.lower()
        self.assertTrue(any(t in bajo for t in ("paráfrasis", "parafrasis")))
        self.assertTrue(any(t in bajo for t in ("pendiente", "abierto",
                                                "no se resuelve")))

    def test_fail_closed_esta_documentado(self):
        self.assertIn("fail closed", self.ambos.lower())

    # --- no vender lo que no existe --------------------------------------
    def test_no_se_afirma_que_exista_un_modelo(self):
        """§37: distinguir IMPLEMENTADO de ARQUITECTURA FUTURA."""
        for nombre, doc in (("contrato", self.contrato),
                            ("contexto", self.contexto)):
            with self.subTest(documento=nombre):
                self.assertIn("NO IMPLEMENTADO", doc.upper())

    def test_no_hay_sdk_ni_endpoint_de_ia(self):
        from dfchron import ia_contrato as io
        import io as _stdlib_io
        with _stdlib_io.open(
                os.path.join(RAIZ, "dfchron", "ia_contrato.py"),
                encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("openai", "anthropic", "api_key"):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)
        with _stdlib_io.open(os.path.join(RAIZ, "dfchron", "api.py"),
                             encoding="utf-8") as f:
            self.assertNotIn("ia_contrato", f.read())

    def test_la_capa_de_io_no_toca_el_nucleo(self):
        """El modulo nuevo no se importa desde el nucleo."""
        import io as _stdlib_io
        with _stdlib_io.open(
                os.path.join(RAIZ, "00_SOURCE", "tools", "nucleo.py"),
                encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotIn("ia_contrato", fuente)
        self.assertNotIn("contrato_ia", fuente)


if __name__ == "__main__":
    unittest.main(verbosity=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)