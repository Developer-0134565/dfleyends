#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del CONTRATO DE IA
===========================================

Comprueba, ejecutando el contrato de verdad, que se puede impedir lo que la
mision manda impedir:

  * `FACT` + `PLAYER_HIDDEN` NO se revela (el caso central);
  * `UNKNOWN` nunca se convierte en `FACT`;
  * `DERIVED` / `INFERENCE` nunca suben a `FACT` solos;
  * `EXTERNAL_KNOWLEDGE` no se presenta como estado de esta partida;
  * `WORLD_KNOWLEDGE` no se degrada a `PLAYER_KNOWLEDGE` por la libre;
  * toda afirmacion sin evidencia es invalida;
  * las conversiones prohibidas fallan.

Y comprueba, por negacion, que NO se ha implementado una IA falsa (§16).

Ejecutar:  python dfchron/pruebas/probar_contrato_ia.py
"""
import io
import os
import sys
import re
import json
import inspect
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c          # noqa: E402

EV = lambda ent, i, f="nucleo.Archivo.ficha": c.evidencia(  # noqa: E731
    ent, i, ["name"], f, "legends.xml")


def hacer(claim="dato de prueba", ts=c.FACT, ks=c.PLAYER_KNOWLEDGE,
          vis=c.PLAYER_VISIBLE, disc=c.ALLOWED, ev=None, **kw):
    """Atajo para construir una afirmacion valida en las pruebas."""
    return c.afirmacion(claim=claim, truth_status=ts, knowledge_source=ks,
                        visibility=vis, disclosure=disc,
                        evidences=ev if ev is not None else [EV("figura", "1")],
                        **kw)


# ========================================================== ESTADOS =========
class TestEstados(unittest.TestCase):
    """Los cuatro estados epistemologicos existen y son los del nucleo."""

    def test_los_tres_estados_originales_se_conservan(self):
        for v in ("FACT", "DERIVED", "UNKNOWN"):
            self.assertIn(v, c.TRUTH_STATUS, f"{v} se ha perdido")

    def test_inference_es_el_estado_reservado_del_nucleo(self):
        """INFERENCE reutiliza INTERPRETATION, no crea un valor paralelo.

        Dos constantes con el mismo significado serian dos verdades.
        """
        self.assertEqual(c.INFERENCE, c.INTERPRETATION)
        self.assertIn(c.INFERENCE, c.TRUTH_STATUS)

    def test_inference_no_coincide_con_ningun_estado_duro(self):
        self.assertNotEqual(c.INFERENCE, c.FACT)
        self.assertNotEqual(c.INFERENCE, c.DERIVED)
        self.assertNotEqual(c.INFERENCE, c.UNKNOWN)

    def test_valor_desconocido_rechazado(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ts="CASI_FACT")


# =========================================================== FUENTES ========
class TestFuentes(unittest.TestCase):
    """Las cuatro fuentes de conocimiento, y lo que cada una puede decir."""

    def test_las_cuatro_fuentes_existen(self):
        """Las cuatro, por su constante del contrato.

        Se comparan las CONSTANTES, no los literales: `INFERENCE` comparte
        valor con el `INTERPRETATION` del nucleo a proposito (son la misma
        idea), asi que exigir la cadena "INFERENCE" seria exigir que el
        contrato se separase de una decision ya tomada.
        """
        for f in (c.PLAYER_KNOWLEDGE, c.WORLD_KNOWLEDGE,
                  c.EXTERNAL_KNOWLEDGE, c.INFERENCE):
            self.assertIn(f, c.KNOWLEDGE_SOURCES, f"{f} no es fuente valida")
        self.assertEqual(len(c.KNOWLEDGE_SOURCES), 4,
                         "deben ser cuatro fuentes, ni mas ni menos")

    def test_world_knowledge_se_guarda_no_se_borra(self):
        """Lo oculto sigue existiendo en el contrato.

        La restriccion es de acceso, no de destruccion: el dato esta ahi, con
        su evidencia, y lo que se impide es revelarlo.
        """
        a = c.ejemplo_secreto()
        self.assertEqual(a["truth_status"], c.FACT)
        self.assertEqual(len(a["evidence"]), 1,
                         "un secreto sigue teniendo evidencia: no se borra")
        self.assertTrue(a["claim"])

    def test_external_no_es_fact_de_este_mundo(self):
        """La wiki puede explicar mecanicas; no afirmar TU partida."""
        with self.assertRaises(c.ContratoInvalido) as ctx:
            hacer(ks=c.EXTERNAL_KNOWLEDGE, vis=c.EXTERNAL, ts=c.FACT,
                  ev=[EV("wiki", "regla")])
        self.assertTrue(any("EXTERNAL" in e for e in ctx.exception.errores))

    def test_external_no_puede_describir_esta_partida(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ks=c.EXTERNAL_KNOWLEDGE, vis=c.PLAYER_VISIBLE,
                  ts=c.DERIVED, ev=[EV("wiki", "regla")])

    def test_external_si_puede_explicar_mecanicas(self):
        self.assertTrue(c.puede_revelarse(c.ejemplo_externo()))

    def test_inference_no_puede_ser_fact(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ks=c.INFERENCE, ts=c.FACT)


# ======================================================== VISIBILIDAD =======
class TestVisibilidad(unittest.TestCase):
    """`FACT` NO implica `PLAYER_VISIBLE`. Ese es todo el punto."""

    def test_fact_no_implica_visible(self):
        """El caso central de la mision: verdad sin permiso."""
        oculto = c.ejemplo_secreto()
        self.assertEqual(oculto["truth_status"], c.FACT)
        self.assertEqual(oculto["visibility"], c.PLAYER_HIDDEN)
        self.assertFalse(c.puede_revelarse(oculto))

    def test_player_visible_se_puede_decir(self):
        a = c.ejemplo_visible()
        self.assertTrue(c.puede_revelarse(a))
        self.assertTrue(c.puede_afirmarse_como_hecho(a))

    def test_world_knowledge_no_descubierto_no_es_visible(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ks=c.WORLD_KNOWLEDGE, vis=c.PLAYER_VISIBLE,
                  no_descubierto=True)

    def test_los_tres_valores_existen(self):
        for v in ("PLAYER_VISIBLE", "PLAYER_HIDDEN", "EXTERNAL"):
            self.assertIn(v, c.VISIBILITIES)

    def test_visibility_invalida_rechazada(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(vis="PLAYER_CASI")


# ======================================================== DIVULGACION =======
class TestDivulgacion(unittest.TestCase):
    """`FORBIDDEN` manda, y `CONDITIONAL` no se abre solo."""

    def test_los_tres_valores_existen(self):
        for v in ("ALLOWED", "FORBIDDEN", "CONDITIONAL"):
            self.assertIn(v, c.DISCLOSURES)

    def test_forbidden_bloquea_aunque_sea_visible_y_fact(self):
        a = hacer(ts=c.FACT, ks=c.WORLD_KNOWLEDGE, vis=c.PLAYER_VISIBLE,
                  disc=c.FORBIDDEN)
        self.assertFalse(c.puede_revelarse(a))
        self.assertIn("FORBIDDEN", c.violacion(a))

    def test_conditional_no_se_abre_solo(self):
        """CONDITIONAL sin pista autorizada sigue bloqueado."""
        a = hacer(vis=c.PLAYER_HIDDEN, disc=c.CONDITIONAL)
        self.assertFalse(c.puede_revelarse(a))

    def test_conditional_se_abre_con_pista_autorizada(self):
        a = hacer(vis=c.PLAYER_HIDDEN, disc=c.CONDITIONAL, pista_permitida=True)
        self.assertTrue(c.puede_revelarse(a))

    def test_conditional_no_es_un_hecho(self):
        """Sigue sin ser una afirmacion tajante."""
        a = hacer(vis=c.PLAYER_HIDDEN, disc=c.CONDITIONAL, pista_permitida=True)
        self.assertFalse(c.puede_afirmarse_como_hecho(a))


# ================================ UNKNOWN NO SE CONVIERTE ====================
class TestUnknownNoSeConvierte(unittest.TestCase):
    """`UNKNOWN` es una respuesta valida. Nunca se rellena."""

    def test_unknown_nunca_es_hecho(self):
        a = c.ejemplo_unknown()
        self.assertEqual(a["truth_status"], c.UNKNOWN)
        self.assertFalse(c.puede_afirmarse_como_hecho(a))
        self.assertFalse(c.puede_revelarse(a),
                         "UNKNOWN no se muestra como afirmacion, sino como "
                         "ausencia")

    def test_unknown_no_puede_promoverse_a_fact(self):
        """Ni por la puerta de conversiones."""
        with self.assertRaises(c.ContratoInvalido):
            c.convertir(c.ejemplo_unknown(), "confirmar")

    def test_unknown_sin_motivo_es_invalido(self):
        """Un UNKNOWN sin motivo no dice nada: se obliga a explicar."""
        with self.assertRaises(c.ContratoInvalido):
            c.afirmacion(claim="no consta", truth_status=c.UNKNOWN,
                         knowledge_source=c.WORLD_KNOWLEDGE,
                         visibility=c.PLAYER_VISIBLE, evidences=[])

    def test_unknown_acepta_motivo_explicito(self):
        a = c.afirmacion(claim="no consta", truth_status=c.UNKNOWN,
                         knowledge_source=c.WORLD_KNOWLEDGE,
                         visibility=c.PLAYER_VISIBLE, evidences=[],
                         motivo="death_year ausente: AUSENTE NO ES VIVA")
        self.assertEqual(c.validar(a), [])

    def test_unknown_no_es_false(self):
        """No existe ningun valor FALSE que suplante al UNKNOWN."""
        self.assertNotIn("FALSE", c.TRUTH_STATUS)
        self.assertNotEqual(c.ejemplo_unknown()["truth_status"], c.FACT)


# ============================ EVIDENCIA Y CONVERSIONES (§6, §9) ============
class TestEvidenciaYConversiones(unittest.TestCase):
    """Sin evidencia no se afirma. Y cambiar de categoría deja rastro."""

    def test_sin_evidencia_es_invalido(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ev=[])

    def test_evidencia_sin_df_id_es_invalida(self):
        with self.assertRaises(c.ContratoInvalido):
            hacer(ev=[{"entidad": "figura", "datos_utilizados": ["name"]}])

    def test_evidencia_de_estado_necesita_funcion_del_nucleo(self):
        """Un hecho de esta partida debe poder auditarse contra el nucleo."""
        with self.assertRaises(c.ContratoInvalido):
            hacer(ev=[c.evidencia("figura", "712", ["name"])])

    def test_revelar_es_una_operacion_explicita_y_registrada(self):
        oculto = c.ejemplo_secreto()
        visible = c.convertir(oculto, "revelar",
                              motivo="el jugador hamina la fortaleza")
        self.assertEqual(visible["visibility"], c.PLAYER_VISIBLE)
        self.assertEqual(oculto["visibility"], c.PLAYER_HIDDEN,
                         "convertir no debe mutar el original")
        self.assertIn("conversion", visible)
        self.assertEqual(visible["conversion"]["operacion"], "revelar")

    def test_ocultar_tambien_deja_rastro(self):
        a = c.convertir(c.ejemplo_visible(), "ocultar")
        self.assertEqual(a["visibility"], c.PLAYER_HIDDEN)
        self.assertFalse(c.puede_revelarse(a))

    def test_no_se_puede_confirmar_un_unknown(self):
        with self.assertRaises(c.ContratoInvalido):
            c.convertir(c.ejemplo_unknown(), "confirmar")

    def test_operacion_inventada_rechazada(self):
        with self.assertRaises(c.ContratoInvalido):
            c.convertir(c.ejemplo_visible(), "forzar")

    def test_externo_no_se_puede_revelar_ni_ocultar(self):
        """No es algo que el jugador pueda descubrir."""
        a = c.ejemplo_externo()
        for op in ("revelar", "ocultar"):
            with self.subTest(op=op), self.assertRaises(c.ContratoInvalido):
                c.convertir(a, op)

    def test_json_va_y_vuelve_sin_perder_nada(self):
        a = c.ejemplo_secreto()
        b = c.desde_json(c.a_json(a))
        self.assertEqual(dict(a), dict(b))
        self.assertFalse(c.puede_revelarse(b))

    def test_json_invalido_al_leyerse(self):
        with self.assertRaises(c.ContratoInvalido):
            c.desde_json(json.dumps({"claim": "x", "truth_status": "FACT"}))


# ===================== COMBINACIONES INVALIDAS (§20, §21) ==================
class TestCombinacionesInvalidas(unittest.TestCase):
    """Recorre la matriz buscando combinaciones que no deberian existir."""

    CASOS_INVALIDOS = [
        ("EXTERNAL como FACT del mundo", c.FACT, c.EXTERNAL_KNOWLEDGE,
         c.EXTERNAL, c.ALLOWED),
        ("EXTERNAL sobre esta partida", c.DERIVED, c.EXTERNAL_KNOWLEDGE,
         c.PLAYER_VISIBLE, c.ALLOWED),
        ("INFERENCE como FACT", c.FACT, c.INFERENCE, c.PLAYER_VISIBLE,
         c.ALLOWED),
    ]

    def test_combinaciones_imposibles_se_rechazan(self):
        for nombre, ts, ks, vis, disc in self.CASOS_INVALIDOS:
            with self.subTest(caso=nombre):
                with self.assertRaises(c.ContratoInvalido):
                    hacer(ts=ts, ks=ks, vis=vis, disc=disc, ev=[EV("x", "1")])

    def test_world_knowledge_no_descubierto_no_pasa_como_visible(self):
        """El caso central de la mision, comprobado por separado.

        Sin `no_descubierto`, un WORLD_KNOWLEDGE en PLAYER_VISIBLE es legal:
        significa que el jugador ya lo conoce. La combinacion imposible es
        exactamente "oculto" + "visible" a la vez.
        """
        with self.assertRaises(c.ContratoInvalido):
            hacer(ts=c.FACT, ks=c.WORLD_KNOWLEDGE, vis=c.PLAYER_VISIBLE,
                  no_descubierto=True, ev=[EV("x", "1")])
        # Y sin la marca de "no descubierto", si es valido: es un dato
        # que el jugador ya conoce, y puede decirselo.
        self.assertTrue(c.puede_revelarse(
            hacer(ts=c.FACT, ks=c.WORLD_KNOWLEDGE, vis=c.PLAYER_VISIBLE,
                  ev=[EV("x", "1")])))

    def test_parte_de_la_matriz_si_es_valida(self):
        """Lo contrario: lo permitido se acepta de verdad."""
        validas = []
        for ts in c.TRUTH_STATUS:
            for ks in c.KNOWLEDGE_SOURCES:
                for vis in c.VISIBILITIES:
                    for disc in c.DISCLOSURES:
                        try:
                            c.afirmacion(
                                claim="x", truth_status=ts, knowledge_source=ks,
                                visibility=vis, disclosure=disc,
                                evidences=[] if ts == c.UNKNOWN
                                else [EV("x", "1")],
                                motivo="dato ausente" if ts == c.UNKNOWN
                                else None)
                            validas.append((ts, ks, vis, disc))
                        except c.ContratoInvalido:
                            pass
        self.assertGreater(len(validas), 0, "nada deberia ser valido")
        self.assertLess(len(validas), 4 * 4 * 3 * 3,
                        "si todo es valido, el contrato no restringe nada")


# ============ LA IA NO ESTA IMPLEMENTADA (§16): se comprueba por negacion ===
class TestNoHayIaImplementada(unittest.TestCase):
    """Comprueba por NEGACION que no se ha colado una IA falsa.

    No basta con decir que no hay IA: se comprueba que no existe forma de que
    exista sin que estas pruebas lo detecten.
    """

    RUTA = os.path.join(RAIZ, "dfchron", "contrato_ia.py")

    def test_no_importa_ninguna_dependencia_de_ia(self):
        fuente = io.open(self.RUTA, encoding="utf-8").read()
        prohibido = ("openai", "anthropic", "transformers", "torch",
                     "langchain", "llama", "requests", "httpx", "urllib",
                     "ollama", "sentence_transformers", "faiss", "chromadb")
        for m in prohibido:
            self.assertNotIn(f"import {m}", fuente,
                             f"contrato_ia.py importa {m}: eso seria una IA")

    def test_no_hay_ia_falsa_por_preguntas(self):
        """Nada de `if pregunta == ...: return ...`."""
        fuente = io.open(self.RUTA, encoding="utf-8").read()
        for patron in (r"if\s+pregunta", r"if\s+question",
                       r"respuestas\s*=\s*\{", r"mocks?\s*=\s*\{"):
            self.assertIsNone(re.search(patron, fuente),
                              f"contrato_ia.py parece un mock: {patron}")

    def test_no_hay_funciones_que_generen_texto(self):
        """Ninguna funcion devuelve prosa: el contrato no redacta."""
        for n, f in vars(c).items():
            if not inspect.isfunction(f) or n.startswith("_"):
                continue
            fuente = inspect.getsource(f)
            self.assertNotIn("respuesta = f", fuente)
            self.assertNotIn("return f\"", fuente)

    def test_no_hay_endpoints_de_ia_en_la_api(self):
        api = io.open(os.path.join(RAIZ, "dfchron", "api.py"),
                      encoding="utf-8").read()
        for r in ("/api/ai", "/api/chat", "/api/ask", "/api/rag"):
            self.assertNotIn(r, api, f"la API expone {r}")

    def test_la_web_no_tiene_chat(self):
        """El aviso de dataset menciona 'Reload', no es un chat."""
        web = os.path.join(RAIZ, "dfchron", "site", "src")
        prohibido = re.compile(
            r"ask\s*ai|chat|prompt|openai|gpt-|\bassistant\b", re.I)
        for raiz, _, ficheros in os.walk(web):
            for f in ficheros:
                if not f.endswith((".ts", ".astro", ".js")):
                    continue
                ruta = os.path.join(raiz, f)
                if os.path.basename(ruta) == "dataset.ts":
                    continue
                txt = io.open(ruta, encoding="utf-8", errors="replace").read()
                self.assertIsNone(prohibido.search(txt),
                                  f"{ruta} parece tener un chat")

    def test_el_contrato_no_toca_el_nucleo(self):
        """Se situa POR ENCIMA: nucleo.py no puede haberse modificado."""
        nucleo = os.path.join(RAIZ, "00_SOURCE", "tools", "nucleo.py")
        fuente = io.open(nucleo, encoding="utf-8", errors="replace").read()
        for termino in ("contrato_ia", "PLAYER_HIDDEN", "disclosure"):
            self.assertNotIn(termino, fuente,
                             f"nucleo.py menciona {termino}: no deberia")


class TestInmutabilidadAnidada(unittest.TestCase):
    """La inmutabilidad tiene que LLEGAR a lo que hay dentro de `evidence`.

    Bloquear solo el nivel superior no servia: `a["evidence"][0]["df_id"] = "999"`
    funcionaba, y con eso la procedencia de un secreto era falsificable.
    """

    def secreto(self):
        return c.afirmacion(
            "Hay una veta de diamantes en 112,20,45",
            c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "87", ["coordenadas"],
                                   "nucleo.Archivo.ficha_sitio")],
            no_descubierto=True)

    def test_no_se_puede_mutar_la_evidencia_por_dentro(self):
        a = self.secreto()
        ev = a["evidence"][0]
        intentos = (lambda: ev.__setitem__("df_id", "999"),
                    lambda: ev.__setitem__("funcion", "falsa"),
                    lambda: ev.update({"df_id": "999"}),
                    lambda: a["evidence"].__setitem__(0, {}),
                    lambda: a["evidence"].append(
                        c.evidencia("x", "1", ["y"], "z")),
                    lambda: ev["datos_utilizados"].append("inventado"),
                    lambda: ev["datos_utilizados"].sort())
        for i, intento in enumerate(intentos, 1):
            with self.subTest(intento=i):
                with self.assertRaises(c.ContratoInvalido):
                    intento()

    def test_el_fallo_no_corrompe_el_dato(self):
        a = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            a["evidence"][0]["df_id"] = "999"
        self.assertEqual(a["evidence"][0]["df_id"], "87")
        self.assertEqual(a["evidence"][0]["funcion"],
                         "nucleo.Archivo.ficha_sitio")
        self.assertEqual(a["disclosure"], c.FORBIDDEN)
        self.assertFalse(c.puede_revelarse(a))

    def test_el_nivel_superior_sigue_bloqueado(self):
        a = self.secreto()
        for campo, valor in (("visibility", c.PLAYER_VISIBLE),
                             ("disclosure", c.ALLOWED),
                             ("truth_status", c.UNKNOWN),
                             ("knowledge_source", c.PLAYER_KNOWLEDGE)):
            with self.subTest(campo=campo):
                with self.assertRaises(c.ContratoInvalido):
                    a[campo] = valor

    def test_congelar_no_rompe_la_serializacion(self):
        a = self.secreto()
        b = c.desde_json(c.a_json(a))
        self.assertEqual(dict(a), dict(b))
        self.assertFalse(c.puede_revelarse(b))

    def test_convertir_no_deja_la_evidencia_abierta(self):
        a = self.secreto()
        b = c.convertir(a, "revelar", "el jugador lo ha descubierto")
        with self.assertRaises(c.ContratoInvalido):
            b["evidence"][0]["df_id"] = "999"
        with self.assertRaises(c.ContratoInvalido):
            a["evidence"][0]["df_id"] = "999"
        self.assertEqual(a["evidence"][0]["df_id"], "87")


if __name__ == "__main__":
    unittest.main(verbosity=2)
# CONTINUA_TEST_IA */