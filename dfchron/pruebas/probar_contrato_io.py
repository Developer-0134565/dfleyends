#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del CONTRATO DE ENTRADA Y SALIDA
===========================================================

Comprueba, ejecutando el contrato de verdad, que se puede impedir lo que la
mision manda impedir:

  * ningun secreto llega al modelo, en NINGUN modo;
  * un `FACT` de salida necesita un `FACT` de apoyo;
  * un apoyo inventado se rechaza;
  * una mecanica necesita apoyo `EXTERNAL_KNOWLEDGE`;
  * `NON_DISCLOSURE` y `UNKNOWN` son salidas validas;
  * el contexto es de solo lectura y determinista;
  * la filtracion por canal indirecto esta marcada como ABIERTA, no resuelta.

La ultima es importante: hay una prueba que verifica que el detector NO sabe
detectar una parafrasis sin cifras. No es un fallo del test: es el registro
honesto del limite del sistema.

Ejecutar:  python dfchron/pruebas/probar_contrato_io.py
"""
import io as _io
import json
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c          # noqa: E402
from dfchron import ia_contrato as io         # noqa: E402


def ctx_de_prueba():
    """El contexto canonico de trabajo: hecho visible, mecanica y consejo."""
    return io.contexto(
        "¿Que deberia hacer?",
        [io.canonico_hecho_visible(), io.canonico_mecanica(),
         io.canonico_consejo()])


# ======================================================== ENTRADA ==========
class TestContextoDeEntrada(unittest.TestCase):
    """Que puede leer el modelo, y que no."""

    def test_el_contexto_tiene_forma_y_version(self):
        ctx = io.contexto("¿qué hay?", [io.canonico_hecho_visible()])
        for clave in ("schema", "agente", "modo", "pregunta", "claims",
                      "contexto"):
            with self.subTest(clave=clave):
                self.assertIn(clave, ctx)
        self.assertEqual(ctx["agente"], io.AGENTE_JUGADOR)
        self.assertEqual(ctx["schema"], io.SCHEMA_VERSION)

    def test_no_acepta_un_modo_inventado(self):
        with self.assertRaises(c.ContratoInvalido):
            io.contexto("q", [], modo="adivinar")

    def test_no_acepta_un_agente_inventado(self):
        """La puerta queda abierta a DWARF/GOBLIN, pero no por descuido."""
        with self.assertRaises(c.ContratoInvalido):
            io.contexto("q", [], agente="GOBLIN")

    def test_la_pregunta_es_obligatoria(self):
        for mala in ("", "   ", None, 42):
            with self.subTest(pregunta=mala):
                with self.assertRaises(c.ContratoInvalido):
                    io.contexto(mala, [])

    # --- el filtro central -------------------------------------------------
    def test_el_secreto_no_llega_al_modelo_en_ningun_modo(self):
        """La regla mas importante del modulo."""
        secreto = io.canonico_secreto()
        for modo in io.MODOS:
            with self.subTest(modo=modo):
                ctx = io.contexto("¿dónde hay diamantes?", [secreto], modo)
                self.assertEqual(len(ctx["claims"]), 0,
                                 "un FORBIDDEN no puede viajar al proveedor")
                self.assertTrue(io.cerrar_contexto(ctx))

    def test_cerrar_contexto_detecta_un_secreto_colado(self):
        """Y detecta que alguien lo colara, por si acaso."""
        cl = {"claims": [{"ref": "c0", "claim": "secreto",
                          "truth_status": c.FACT,
                          "knowledge_source": c.WORLD_KNOWLEDGE,
                          "visibility": c.PLAYER_HIDDEN,
                          "disclosure": c.FORBIDDEN, "evidence": []}]}
        self.assertFalse(io.cerrar_contexto(cl))

    def test_el_contexto_es_de_solo_lectura(self):
        ctx = io.contexto("q", [io.canonico_hecho_visible()])
        with self.assertRaises(c.ContratoInvalido):
            ctx["claims"] = []
        with self.assertRaises(c.ContratoInvalido):
            ctx["modo"] = "otro"
        with self.assertRaises(c.ContratoInvalido):
            ctx.pop("claims")

    def test_no_hay_campos_duplicados_por_derivacion(self):
        """Una segunda verdad podria contradecir a la primera."""
        ctx = io.contexto("q", [io.canonico_hecho_visible()])
        for prohibido in ("divulgable", "es_secreto", "puede_revelarse"):
            with self.subTest(campo=prohibido):
                self.assertNotIn(prohibido, ctx)
                self.assertNotIn(prohibido, ctx["claims"][0])

    def test_no_se_envian_campos_de_la_casa(self):
        """`no_descubierto` y `pista_permitida` son internos."""
        a = c.afirmacion(
            "pista", c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
            c.CONDITIONAL,
            evidences=[c.evidencia("sitio", "9", ["tipo"], "f")],
            no_descubierto=True, pista_permitida=True)
        cl = io.contexto("q", [a])["claims"][0]
        for interno in ("no_descubierto", "pista_permitida", "conversion"):
            with self.subTest(campo=interno):
                self.assertNotIn(interno, cl)

    def test_el_contexto_no_trae_datos_crudos(self):
        """Ni rutas, ni ficheros internos, ni tablas."""
        texto = io.a_json(io.contexto("q", [io.canonico_hecho_visible()]))
        for patron in ("00_SOURCE", ".jsonl", "processed", "dfchron"):
            with self.subTest(patron=patron):
                self.assertNotIn(patron, texto)
# --- los dos modos ----------------------------------------------------
    def test_modo_respuesta_es_subconjunto_del_razonamiento(self):
        """La relacion entre modos, comprobada con todos los canonicos."""
        for nombre, fabrica in io.CANONICOS.items():
            with self.subTest(canonico=nombre):
                a = fabrica()
                r = io.contexto("q", [a], io.MODO_RAZONAMIENTO)
                p = io.contexto("q", [a], io.MODO_RESPUESTA)
                self.assertLessEqual(len(p["claims"]), len(r["claims"]))

    def test_unknown_entra_para_razonar_pero_no_para_responder(self):
        """«No consta» se lee, pero no se lee al jugador como afirmacion."""
        d = io.canonico_desconocido()
        self.assertEqual(len(io.contexto("q", [d], io.MODO_RAZONAMIENTO)
                           ["claims"]), 1)
        self.assertEqual(len(io.contexto("q", [d], io.MODO_RESPUESTA)
                           ["claims"]), 0)

    def test_la_mecanica_entra_en_los_dos_modos(self):
        """Explicar reglas no es filtrar secretos."""
        m = io.canonico_mecanica()
        for modo in io.MODOS:
            with self.subTest(modo=modo):
                self.assertEqual(len(io.contexto("q", [m], modo)["claims"]), 1)

    # --- determinismo ------------------------------------------------------
    def test_misma_entrada_mismo_contexto_byte_a_byte(self):
        a = [io.canonico_hecho_visible(), io.canonico_mecanica()]
        self.assertEqual(io.a_json(io.contexto("q", a)),
                         io.a_json(io.contexto("q", a)))

    def test_el_contexto_no_depende_del_orden_de_llegada(self):
        """Entrar en desorden no cambia lo que se decide, solo el orden."""
        a, b = io.canonico_hecho_visible(), io.canonico_mecanica()
        uno = io.contexto("q", [a, b])
        otro = io.contexto("q", [b, a])
        self.assertEqual({x["claim"] for x in uno["claims"]},
                         {x["claim"] for x in otro["claims"]})

    def test_no_importa_relojes_ni_azar(self):
        with _io.open(os.path.join(RAIZ, "dfchron", "ia_contrato.py"),
                      encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotRegex(fuente, r"^\s*import\s+time\b", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+random\b", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+uuid\b", re.M)
        self.assertNotIn("time.time()", fuente)
        self.assertNotIn("datetime.now", fuente)


# ======================================================== SALIDA ==========
class TestValidacionDeSalida(unittest.TestCase):
    """La puerta. FAIL CLOSED, y se explica cuando cierra."""

    def test_un_fact_valido_pasa(self):
        ctx = ctx_de_prueba()
        v = io.validar_salida(io.respuesta(
            "El jugador conoce a Galka Shafttop.",
            [io.claim_de_salida("El jugador conoce a Galka Shafttop.",
                                io.FACT, ["c0"])]), ctx)
        self.assertTrue(v.entregable)
        self.assertEqual(v["errores"], [])

    def test_un_hecho_visible_si_puede_ser_afirmado(self):
        """El criterio de `FACT` de salida es el del contrato, no el nuestro."""
        a = io.canonico_hecho_visible()
        self.assertTrue(c.puede_afirmarse_como_hecho(a))

    def test_fact_sin_fact_de_apoyo_rechazado(self):
        """La regla §12: el modelo no convierte generacion en evidencia."""
        v = io.validar_salida(io.respuesta(
            "Los enanos pueden extraer piedra.",
            [io.claim_de_salida("Los enanos pueden extraer piedra.",
                                io.FACT, ["c1"])]), ctx_de_prueba())
        self.assertFalse(v.entregable)
        self.assertTrue(any("FACT necesita apoyo" in e for e in v["errores"]))

    def test_apoyo_inventado_rechazado(self):
        """Procedencia: no puede apoyarse en lo que no recibio."""
        v = io.validar_salida(io.respuesta(
            "x", [io.claim_de_salida("x", io.FACT, ["c99"])]), ctx_de_prueba())
        self.assertFalse(v.entregable)
        self.assertTrue(any("inexistente" in e for e in v["errores"]))

    def test_mecanica_necesita_apoyo_externo(self):
        """La wiki explica reglas; no puede explicar la partida."""
        v = io.validar_salida(io.respuesta(
            "mecanica", [io.claim_de_salida("mecanica",
                                            io.MECHANIC_EXPLANATION, ["c0"])]),
            ctx_de_prueba())
        self.assertFalse(v.entregable)
        self.assertTrue(any("EXTERNAL_KNOWLEDGE" in e for e in v["errores"]))

    def test_mecanica_con_apoyo_externo_pasa(self):
        v = io.validar_salida(io.respuesta(
            "mecanica", [io.claim_de_salida("mecanica",
                                            io.MECHANIC_EXPLANATION, ["c1"])]),
            ctx_de_prueba())
        self.assertTrue(v.entregable)

    def test_un_hecho_no_se_reviste_de_consejo(self):
        """Un consejo apoyado solo en un hecho no aporta nada."""
        v = io.validar_salida(io.respuesta(
            "consejo", [io.claim_de_salida("consejo", io.ADVICE, ["c0"])]),
            ctx_de_prueba())
        self.assertFalse(v.entregable)

    def test_conditional_no_se_afirma_como_hecho(self):
        """La pista se menciona, no se afirma. Es la distincion del contrato."""
        a = c.afirmacion(
            "pista", c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
            c.CONDITIONAL,
            evidences=[c.evidencia("sitio", "9", ["tipo"], "f")],
            no_descubierto=True, pista_permitida=True)
        ctx = io.contexto("q", [a], io.MODO_RAZONAMIENTO)
        v = io.validar_salida(io.respuesta(
            "Hay algo alli", [io.claim_de_salida("Hay algo alli",
                                                 io.FACT, ["c0"])]), ctx)
        self.assertFalse(v.entregable)

    def test_salida_no_estructurada_rechazada(self):
        """Texto suelto no es auditable."""
        for mala in ("texto", None, 42, {"answer": "x"}):
            with self.subTest(salida=mala):
                self.assertFalse(
                    io.validar_salida(mala, ctx_de_prueba()).entregable)

    def test_claims_vacios_rechazados(self):
        v = io.validar_salida(io.respuesta("solo texto", []), ctx_de_prueba())
        self.assertFalse(v.entregable)

    def test_el_veredicto_explica_el_por_que(self):
        """Un fallo sin explicacion no se puede arreglar."""
        v = io.validar_salida(io.respuesta(
            "x", [io.claim_de_salida("x", io.FACT, ["c99"])]), ctx_de_prueba())
        self.assertTrue(v["errores"])
        self.assertFalse(bool(v))

    def test_json_invalido_se_rechaza_al_parsear(self):
        with self.assertRaises(c.ContratoInvalido):
            io.desde_json("{esto no es json")

    def test_json_valido_llega_a_validar(self):
        """Parsear y validar son pasos separados, a proposito."""
        crudo = ('{"answer": "x", "claims": [{"texto":"x","tipo":"FACT",'
                 '"soporte":["c0"]}]}')
        self.assertTrue(
            io.validar_salida(io.desde_json(crudo), ctx_de_prueba()).entregable)


# ================== EL MODELO NO PUEDE REVELAR (§17, §20) ================
class TestElModeloNoDecideDivulgacion(unittest.TestCase):
    """La politica va antes y despues del modelo. Nunca en medio."""

    def test_el_contexto_limpio_pasa_el_cerrojo(self):
        self.assertTrue(io.cerrar_contexto(ctx_de_prueba()))

    def test_la_salida_se_valida_siempre_despues(self):
        """Aun con un contexto limpio, la salida se vuelve a comprobar."""
        v = io.validar_salida(io.respuesta(
            "x", [io.claim_de_salida("x", io.FACT, ["c99"])]), ctx_de_prueba())
        self.assertFalse(v.entregable)

    def test_un_inference_forbidden_no_llega_ni_para_razonar(self):
        """§20: una inferencia prohibida no es un canal indirecto permitido."""
        a = c.afirmacion(
            "no abras la puerta", c.INFERENCE, c.INFERENCE,
            c.PLAYER_HIDDEN, c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "5", ["tipo"], "f")],
            pista_permitida=True)
        for modo in io.MODOS:
            with self.subTest(modo=modo):
                ctx = io.contexto("hay algo detras?", [a], modo)
                self.assertEqual(len(ctx["claims"]), 0,
                                 "una inferencia prohibida se queda dentro")

    def test_un_conditional_solo_no_llega(self):
        """Sin `pista_permitida`, la pista no viaja."""
        a = c.afirmacion(
            "pista", c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
            c.CONDITIONAL,
            evidences=[c.evidencia("sitio", "9", ["tipo"], "f")],
            no_descubierto=True)
        self.assertEqual(len(io.contexto("q", [a])["claims"]), 0)


class TestAdversarialCanalIndirecto(unittest.TestCase):
    """El modelo intenta decir el secreto de forma indirecta.

    Aqui no se busca un detector perfecto: se establece QUE DEBE detectar la
    arquitectura, y se registra honestamente lo que hoy NO detecta.
    """

    #: Los cinco casos que la mision enumera, con lo que hoy pasarian.
    #: (texto del modelo, ¿lo bloquea hoy?)
    CASOS = (
        ("Esta justo al norte.", False),
        ("Explora aproximadamente X=183.", True),
        ("Busca en la zona donde estan los diamantes.", False),
        ("Hay algo valioso en esa coordenada.", False),
        ("Yo evitaria concretamente esa ubicacion.", True),
    )

    def test_coordenada_estructurada_se_bloquea(self):
        """El formato con el que se explica un secreto se delata solo."""
        for texto in ("Explora aproximadamente X=183.",
                      "Hay diamantes en 183, 72, -14.",
                      "x = 183, y = 72",
                      "Ve a 183, 72"):
            with self.subTest(texto=texto):
                self.assertTrue(io.deteccion_fuga(texto),
                                "una coordenada estructurada es sospechosa")

    def test_intensificador_con_numero_se_bloquea(self):
        self.assertTrue(io.deteccion_fuga(
            "Yo evitaria concretamente la ubicacion 42"))

    def test_intensificador_sin_numero_no_es_fuga(self):
        """Sino retorica. Marcarlo todo seria marcarlo todo."""
        self.assertFalse(io.deteccion_fuga("Exactamente, eso es lo que digo"))

    def test_texto_limpio_no_se_marca(self):
        for limpio in ("El jugador conoce a Galka Shafttop.",
                       "Los enanos pueden extraer piedra.",
                       "Podrias explorar la zona norte."):
            with self.subTest(texto=limpio):
                self.assertFalse(io.deteccion_fuga(limpio))

# ============================ CANONICOS Y DETERMINISMO ===================
class TestCanonicosYDeterminismo(unittest.TestCase):
    """Los cinco casos obligatorios, y el determinismo de todo lo demas."""

    def test_los_cinco_canonicos_construyen(self):
        self.assertEqual(len(io.CANONICOS), 5)
        for nombre, fabrica in io.CANONICOS.items():
            with self.subTest(canonico=nombre):
                self.assertEqual(c.validar(fabrica()), [])

    def test_canonico_A_es_un_hecho_afirmable(self):
        a = io.canonico_hecho_visible()
        self.assertTrue(c.puede_afirmarse_como_hecho(a))
        self.assertEqual(a["truth_status"], c.FACT)

    def test_canonico_B_es_secreto_y_no_llega(self):
        a = io.canonico_secreto()
        self.assertFalse(c.puede_revelarse(a))
        self.assertEqual(a["disclosure"], c.FORBIDDEN)
        self.assertEqual(len(io.contexto("q", [a])["claims"]), 0)

    def test_canonico_C_es_una_interpretacion(self):
        a = io.canonico_consejo()
        self.assertEqual(a["truth_status"], c.INFERENCE)
        self.assertTrue(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "un consejo nunca es un hecho del mundo")

    def test_canonico_D_es_externo_y_no_afirmable(self):
        a = io.canonico_mecanica()
        self.assertEqual(a["knowledge_source"], c.EXTERNAL_KNOWLEDGE)
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "explicar una mecanica no afirma nada de la partida")

    def test_canonico_E_es_desconocido_valido(self):
        a = io.canonico_desconocido()
        self.assertEqual(a["truth_status"], c.UNKNOWN)
        self.assertFalse(c.puede_revelarse(a))
        self.assertTrue(a["motivo"], "un UNKNOWN explica siempre por que")

    def test_misma_salida_mismo_veredicto(self):
        ctx = ctx_de_prueba()
        salida = io.respuesta(
            "x", [io.claim_de_salida("El jugador conoce a Galka Shafttop.",
                                     io.FACT, ["c0"])])
        v1 = io.validar_salida(salida, ctx)
        v2 = io.validar_salida(salida, ctx)
        self.assertEqual(v1, v2)

    def test_la_serializacion_es_byte_a_byte_identica(self):
        ctx = ctx_de_prueba()
        self.assertEqual(io.a_json(ctx), io.a_json(ctx))
        r = io.respuesta("x", [io.claim_de_salida("y", io.FACT, ["c0"])])
        self.assertEqual(io.a_json(r), io.a_json(r))


# ===================================== NO HAY UN MODELO AQUI ==============
class TestNoHayModelo(unittest.TestCase):
    """La mision prohibe implementar el LLM. Esto lo comprueba."""

    def test_no_hay_cliente_ni_proveedor(self):
        with _io.open(os.path.join(RAIZ, "dfchron", "ia_contrato.py"),
                      encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotRegex(
            fuente, r"^\s*(import|from)\s+(openai|anthropic|cohere|transformers)",
            re.M)
        for prohibido in ("api_key", "API_KEY", "requests.post", "urllib",
                          "http://", "https://"):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)

    def test_no_se_persiste_nada(self):
        """Nada de memoria, historial ni estado de conversacion."""
        with _io.open(os.path.join(RAIZ, "dfchron", "ia_contrato.py"),
                      encoding="utf-8") as f:
            fuente = f.read().lower()
        for prohibido in ("chat_history", "conversation_state", "memory",
                          "historial"):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)

    def test_la_api_no_usa_este_modulo(self):
        with _io.open(os.path.join(RAIZ, "dfchron", "api.py"),
                      encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotIn("ia_contrato", fuente)
        self.assertNotIn("api/ia", fuente)


if __name__ == "__main__":
    unittest.main(verbosity=2)
    def test_coordenada_bloquea_la_respuesta_entera(self):
        """No basta con que el claim sea valido: manda el texto."""
        v = io.validar_salida(io.respuesta(
            "Busca en X=183, 72, -14",
            [io.claim_de_salida("Hay algo.", io.FACT, ["c0"])]),
            ctx_de_prueba())
        self.assertFalse(v.entregable)
        self.assertTrue(any("fuga indirecta" in e for e in v["errores"]))

    def test_la_parafrasis_SIN_CIFRAS_QUEDA_ABIERTA(self):
        """LIMITE CONOCIDO Y DECLARADO. No se disimula.

        Estas frases filtran informacion sin ninguna coordenada. El detector no
        las ve, porque no hay detector semantico. Esta prueba EXISTE para que
        el limite este escrito en el codigo y no se pierda: si alguien resuelve
        el problema, esta prueba falla y obliga a documentarlo.
        """
        sin_cifras = [t for t, b in self.CASOS if not b]
        self.assertTrue(sin_cifras, "debe quedar al menos un caso abierto")
        for texto in sin_cifras:
            with self.subTest(texto=texto):
                self.assertEqual(io.deteccion_fuga(texto), [],
                                 "si esto ahora se detecta, actualiza el "
                                 "modulo y la documentacion: el limite cambio")

    def test_un_secreto_no_puede_salir_ni_por_apoyo(self):
        """Aun con un claim bien formado, el secreto no esta en el contexto."""
        ctx = io.contexto("diamantes", [io.canonico_secreto()])
        v = io.validar_salida(io.respuesta(
            "Hay diamantes", [io.claim_de_salida("Hay diamantes", io.FACT,
                                                 ["c0"])]), ctx)
        self.assertFalse(v.entregable, "no hay ni un solo claim que apoyar")
        """Texto suelto no es auditable."""
        for mala in ("texto", None, 42, {"answer": "x"}):
            with self.subTest(salida=mala):
                self.assertFalse(io.validar_salida(mala, ctx_de_prueba())
                                 .entregable)

    def test_claims_vacios_rechazados(self):
        v = io.validar_salida(io.respuesta("solo texto", []), ctx_de_prueba())
        self.assertFalse(v.entregable)

    def test_el_veredicto_explica_el_por_que(self):
        """Un fallo sin explicacion no se puede arreglar."""
        v = io.validar_salida(io.respuesta(
            "x", [io.claim_de_salida("x", io.FACT, ["c99"])]), ctx_de_prueba())
        self.assertTrue(v["errores"])
        self.assertFalse(bool(v))

    def test_json_invalido_se_rechaza_al_parsear(self):
        with self.assertRaises(c.ContratoInvalido):
            io.desde_json("{esto no es json")

    def test_json_valido_llega_a_validar(self):
        """Parsear y validar son pasos separados, a proposito."""
        crudo = '{"answer": "x", "claims": [{"texto":"x","tipo":"FACT","soporte":["c0"]}]}'
        salida = io.desde_json(crudo)
        self.assertTrue(io.validar_salida(salida, ctx_de_prueba()).entregable)
class TestTiposDeSalida(unittest.TestCase):
    """Los siete tipos, y lo que cada uno obliga."""

    def test_los_siete_tipos_existen(self):
        self.assertEqual(len(io.TIPOS_SALIDA), 7)
        for t in ("FACT", "DERIVED", "INTERPRETATION", "ADVICE", "UNKNOWN",
                  "NON_DISCLOSURE", "MECHANIC_EXPLANATION"):
            with self.subTest(tipo=t):
                self.assertIn(t, io.TIPOS_SALIDA)

    def test_tipo_desconocido_rechazado(self):
        with self.assertRaises(c.ContratoInvalido):
            io.claim_de_salida("x", "CHISTE", ["c0"])

    def test_texto_obligatorio(self):
        for malo in ("", "   ", None, 7):
            with self.subTest(texto=malo):
                with self.assertRaises(c.ContratoInvalido):
                    io.claim_de_salida(malo, io.FACT, ["c0"])

    def test_sin_apoyo_rechazado(self):
        """Salvo NON_DISCLOSURE, cuyo motivo es el contenido."""
        with self.assertRaises(c.ContratoInvalido):
            io.claim_de_salida("x", io.FACT)
        io.claim_de_salida("x", io.NON_DISCLOSURE,
                           motivo="PLAYER_HIDDEN")   # este si vale

    def test_non_disclosure_necesita_motivo(self):
        """«No te lo digo» sin razon no es respuesta: es un fallo."""
        with self.assertRaises(c.ContratoInvalido):
            io.claim_de_salida("no te lo digo", io.NON_DISCLOSURE)

    def test_la_evidencia_llega_completa(self):
        """La procedencia es lo que permite auditar (§9)."""
        ev = io.contexto("q", [io.canonico_hecho_visible()])["claims"][0][
            "evidence"][0]
        for campo in ("entidad", "df_id", "datos_utilizados", "funcion",
                      "fuente"):
            with self.subTest(campo=campo):
                self.assertIn(campo, ev)
        self.assertEqual(ev["df_id"], "712")