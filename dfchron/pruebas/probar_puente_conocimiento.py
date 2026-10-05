#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del PUENTE DE CONOCIMIENTO
====================================================

Comprueba, ejecutando de verdad, que se puede demostrar lo que la mision pide:

    VERDAD  !=  VISIBILIDAD  !=  PERMISO DE DIVULGACION

Y que un dato verdadero y prohibido (una veta de diamantes con sus
coordenadas) existe internamente, es util para razonar, y NO sale nunca por la
puerta de divulgacion.

A diferencia de `probar_contrato_ia.py`, que prueba el CONTRATO, esta suite
prueba el ADAPTADOR: que convierte entidades reales del nucleo en objetos de
conocimiento con evidencia y procedencia.

Las dos suites se necesitan. Esta NO sustituye a la otra: la otra sigue verde.

Ejecutar:  python dfchron/pruebas/probar_puente_conocimiento.py
"""
import os
import re
import sys
import json
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c        # noqa: E402
from dfchron import ia_conocimiento as ia   # noqa: E402

#: Un solo Puente por proceso: cargar 57.215 eventos cuesta ~2,5 s.
PUENTE = ia.Puente()

#: Identificadores REALES del dataset actual (fixtures de la validacion).
FIGURA_REAL = "712"        # galka shafttop the blades of knighting
SITIO_REAL = "87"          # halesteel, fortaleza, coordenadas reales
ENTIDAD_REAL = 294         # the rock of voicing
ARTEFACTO_REAL = 1         # primeval wood halberd
EVENTO_REAL = 1            # change hf state

#: Lo que la mision exige poder demostrar, en texto plano.
COORDENADAS_SECRETAS = "112, 20"


def claims_de(k, texto):
    return [a for a in k["claims"] if texto in a["claim"]]


# ============================================================== LOS ESTADOS ==
class TestLosCuatroEstados(unittest.TestCase):
    """1-4. FACT, DERIVED, UNKNOWN y CONDITIONAL se comportan como es debido."""

    def test_fact_del_nucleo_llega_como_fact(self):
        k = ia.Puente(PUENTE.archivo).obtener_conocimiento_figura(FIGURA_REAL)
        hechos = [a for a in k["claims"] if a["truth_status"] == c.FACT]
        self.assertTrue(hechos, "una figura real debe traer hechos")
        for a in hechos:
            self.assertEqual(a["knowledge_source"], c.WORLD_KNOWLEDGE)
            self.assertTrue(a["evidence"],
                            "un FACT sin evidencia no puede construirse")

    def test_derived_se_distingue_de_fact(self):
        """Un DERIVED nunca se presenta como FACT."""
        a = c.afirmacion("el sitio tiene contactos con el exterior",
                         truth_status=c.DERIVED,
                         knowledge_source=c.WORLD_KNOWLEDGE,
                         visibility=c.PLAYER_HIDDEN,
                         evidences=[c.evidencia("sitio", "87", ["eventos"],
                                                "nucleo.Archivo.ficha_sitio")])
        self.assertNotEqual(a["truth_status"], c.FACT)
        self.assertEqual(a["truth_status"], c.DERIVED)

    def test_unknown_no_se_rellena(self):
        """El hueco se declara; no se completa."""
        k = ia.Puente(PUENTE.archivo).obtener_conocimiento_figura(FIGURA_REAL)
        huecos = [a for a in k["claims"] if a["truth_status"] == c.UNKNOWN]
        self.assertTrue(huecos, "esta figura no tiene fechas: debe declararlo")
        for a in huecos:
            self.assertIsNotNone(a.get("motivo"),
                                 "un UNKNOWN necesita motivo")
            self.assertFalse(c.puede_afirmarse_como_hecho(a),
                             "UNKNOWN no puede enunciarse como hecho")

    def test_conditional_es_permiso_no_estado(self):
        """`CONDITIONAL` pertenece a `disclosure`, no a `truth_status`.

        DISCREPANCIA DOCUMENTADA con el encargo de la mision: pedia `CONDITIONAL`
        como valor de `truth_status`. Una afirmacion no es "condicionalmente
        verdadera": o es verdad o no lo es. Lo que si puede ser condicional es
        el PERMISO de decirla. El contrato ya lo tenia asi, con 44 pruebas, y
        cambiarlo romperia el diseno. Aqui se fija, no se admite.
        """
        self.assertIn(c.CONDITIONAL, c.DISCLOSURES)
        self.assertNotIn(c.CONDITIONAL, c.TRUTH_STATUS)

    def test_conditional_conserva_su_naturaleza(self):
        """Se puede MENCIONAR, nunca AFIRMAR. Aunque este permitido."""
        a = c.afirmacion("hay indicios de peligro en la fortaleza",
                         truth_status=c.FACT,
                         knowledge_source=c.WORLD_KNOWLEDGE,
                         visibility=c.PLAYER_HIDDEN,
                         disclosure=c.CONDITIONAL,
                         evidences=[c.evidencia("sitio", "87", ["tipo"],
                                                "nucleo.Archivo.ficha_sitio")],
                         pista_permitida=True)
        self.assertTrue(c.puede_revelarse(a), "con pista se puede mencionar")
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "pero mentioning no es afirmar")
# ============================================================ VISIBILIDAD ===
class TestVisibilidad(unittest.TestCase):
    """5-7. PLAYER_VISIBLE, PLAYER_HIDDEN y EXTERNAL."""

    def test_el_mundo_nace_oculto(self):
        """Nada del nucleo se marca visible: no hay prueba de descubrimiento."""
        k = ia.Puente(PUENTE.archivo).obtener_conocimiento_sitio(SITIO_REAL)
        for a in k["claims"]:
            if a["truth_status"] == c.FACT:
                self.assertEqual(a["visibility"], c.PLAYER_HIDDEN,
                                 "un dato del mundo nace oculto mientras no "
                                 "se demuestre que el jugador lo descubrio")
                self.assertTrue(a.get("no_descubierto"))

    def test_ningun_hecho_se_marca_visible_por_el_puente(self):
        """La limitacion de PLAYER_KNOWLEDGE, fijada como prueba.

        `legends.xml` no registra que descubrio el jugador. Por eso el puente
        no marca NADA como `PLAYER_VISIBLE`, ni aunque este en el indice.
        """
        for k in (PUENTE.obtener_conocimiento_figura(FIGURA_REAL),
                  PUENTE.obtener_conocimiento_sitio(SITIO_REAL),
                  PUENTE.obtener_conocimiento_entidad(ENTIDAD_REAL)):
            for a in k["claims"]:
                self.assertNotEqual(a["knowledge_source"], c.PLAYER_KNOWLEDGE,
                                    "el puente no convierte mundo en "
                                    "conocimiento del jugador por su cuenta")
                if a["truth_status"] == c.FACT:
                    self.assertNotEqual(a["visibility"], c.PLAYER_VISIBLE)

    def test_external_no_describe_esta_partida(self):
        """EXTERNAL puede existir, pero no como estado de este mundo."""
        a = ia.externo_pendiente("regla_juego", "wiki:goblin_fortress",
                                 "Las fortalezas goblin pueden contener "
                                 "determinados enemigos.")
        self.assertEqual(a["knowledge_source"], c.EXTERNAL_KNOWLEDGE)
        self.assertEqual(a["visibility"], c.EXTERNAL)
        self.assertNotEqual(a["truth_status"], c.FACT)
        with self.assertRaises(c.ContratoInvalido):
            c.afirmacion("en tu mundo hay 37 goblins",
                         truth_status=c.FACT,
                         knowledge_source=c.EXTERNAL_KNOWLEDGE,
                         visibility=c.EXTERNAL,
                         evidences=[c.evidencia("wiki", "x", ["t"], "doc")])


# ============================================================= DIVULGACION ===
class TestDisclosure(unittest.TestCase):
    """8-9. ALLOWED, FORBIDDEN y la puerta unica."""

    def test_allowed_visible_se_puede_revelar(self):
        a = c.afirmacion("el jugador conoce su fortaleza",
                         truth_status=c.FACT,
                         knowledge_source=c.PLAYER_KNOWLEDGE,
                         visibility=c.PLAYER_VISIBLE,
                         disclosure=c.ALLOWED,
                         evidences=[c.evidencia("sitio", "87", ["tipo"],
                                                "nucleo.Archivo.ficha_sitio")])
        self.assertTrue(c.puede_revelarse(a))
        self.assertTrue(c.puede_afirmarse_como_hecho(a))

    def test_forbidden_no_se_puede_revelar(self):
        a = c.afirmacion("hay una veta de diamantes",
                         truth_status=c.FACT,
                         knowledge_source=c.WORLD_KNOWLEDGE,
                         visibility=c.PLAYER_VISIBLE,
                         disclosure=c.FORBIDDEN,
                         evidences=[c.evidencia("sitio", "87", ["tipo"],
                                                "nucleo.Archivo.ficha_sitio")])
        self.assertFalse(c.puede_revelarse(a))
        self.assertEqual(c.violacion(a), "disclosure FORBIDDEN")

    def test_la_puerta_es_una_sola(self):
        """No hay una segunda puerta: `convertir()` es el unico cambio."""
        self.assertIn("revelar", c.OPERACIONES)
        with self.assertRaises(c.ContratoInvalido):
            c.convertir(c.afirmacion("x", c.FACT, c.PLAYER_KNOWLEDGE,
                                     c.PLAYER_VISIBLE,
                                     evidences=[c.evidencia("s", "1", ["t"],
                                                            "f")]),
                        "forzar_lo_que_sea")
# =========================================================== PUERTA REAL =====
class TestPuertaDeDivulgacion(unittest.TestCase):
    """12. El caso critico de la mision, con datos reales."""

    def test_el_caso_de_la_veta_de_diamantes(self):
        """FACT + PLAYER_HIDDEN + FORBIDDEN existe, razona y NO se revela."""
        secreto = c.afirmacion(
            claim=f"Hay una veta de diamantes en {COORDENADAS_SECRETAS}",
            truth_status=c.FACT,
            knowledge_source=c.WORLD_KNOWLEDGE,
            visibility=c.PLAYER_HIDDEN,
            disclosure=c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "87", ["coordenadas"],
                                   "nucleo.Archivo.ficha_sitio",
                                   "legends.xml")],
            no_descubierto=True)

        self.assertTrue(c.puede_usarse_para_razonar(secreto),
                        "razonar con un secreto es legitimo")
        self.assertFalse(c.puede_revelarse(secreto), "pero contarlo no")
        self.assertFalse(c.puede_afirmarse_como_hecho(secreto))

    def test_la_respuesta_al_jugador_no_lleva_coordenadas(self):
        """La comprobacion que de verdad importa, contra el sitio real.

        El sitio 87 TIENE coordenadas reales. Tienen que existir como dato
        interno y no aparecer en absoluto en lo que se responde.
        """
        k = PUENTE.obtener_conocimiento_sitio(SITIO_REAL)

        con_coords = claims_de(k, "coordenadas")
        self.assertTrue(con_coords, "el sitio real tiene coordenadas")
        self.assertEqual(con_coords[0]["truth_status"], c.FACT)
        self.assertEqual(con_coords[0]["visibility"], c.PLAYER_HIDDEN)
        self.assertEqual(con_coords[0]["disclosure"], c.FORBIDDEN)

        self.assertIn(con_coords[0], ia.claims_para_razonar(k))
        self.assertNotIn(con_coords[0], ia.claims_divulgables(k))

        respuesta = ia.preparar_respuesta_jugador(k)
        texto = json.dumps(respuesta, ensure_ascii=False)
        self.assertNotIn(COORDENADAS_SECRETAS, texto,
                         "las coordenadas NO pueden aparecer en la respuesta")
        self.assertNotIn("112", texto)
        self.assertGreater(respuesta["omitidos"], 0)
        self.assertIn("FORBIDDEN", json.dumps(respuesta["motivos"]))

    def test_una_inferencia_se_puede_decir_pero_no_afirmar(self):
        """13 y el segundo caso de §12."""
        inf = ia.registrar_inferencia(
            "La fortaleza podría ser peligrosa",
            [c.evidencia("razonamiento", "sitio-87", ["tipo"],
                         "nucleo.Archivo.ficha_sitio")])
        self.assertEqual(inf["truth_status"], c.INFERENCE)
        self.assertEqual(inf["disclosure"], c.ALLOWED)
        self.assertTrue(c.puede_revelarse(inf), "se puede mencionar")
        self.assertFalse(c.puede_afirmarse_como_hecho(inf),
                         "pero no enunciarse como hecho")
# ============================================================ INMUTABILIDAD ==
class TestInmutabilidad(unittest.TestCase):
    """17. Un dato prohibido no se degrada por mutacion accidental."""

    @staticmethod
    def secreto():
        return c.afirmacion(
            claim=f"Hay una veta de diamantes en {COORDENADAS_SECRETAS}",
            truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
            visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "87", ["coordenadas"],
                                   "nucleo.Archivo.ficha_sitio")],
            no_descubierto=True)

    def test_no_se_puede_asignar_visibility(self):
        a = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            a["visibility"] = c.PLAYER_VISIBLE

    def test_no_se_puede_asignar_disclosure(self):
        a = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            a["disclosure"] = c.ALLOWED

    def test_no_se_puede_asignar_truth_status(self):
        a = self.secreto()
        for destino in (c.DERIVED, c.UNKNOWN, c.INFERENCE):
            with self.assertRaises(c.ContratoInvalido):
                a["truth_status"] = destino

    def test_no_se_puede_borrar_disclosure(self):
        a = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            del a["disclosure"]

    def test_no_se_puede_update_ni_pop_ni_clear(self):
        a = self.secreto()
        for operacion in (lambda: a.update({"visibility": c.PLAYER_VISIBLE}),
                          lambda: a.pop("disclosure"),
                          lambda: a.setdefault("x", 1),
                          lambda: a.clear(),
                          lambda: a.__ior__({"visibility": c.PLAYER_VISIBLE})):
            with self.assertRaises(c.ContratoInvalido):
                operacion()

    def test_tras_intentar_mutar_sigue_prohibido(self):
        """El fallo no corrompe el dato: sigue siendo el que era."""
        a = self.secreto()
        for operacion in (lambda: a.update({"visibility": c.PLAYER_VISIBLE}),
                          lambda: a.__setitem__("disclosure", c.ALLOWED)):
            try:
                operacion()
            except c.ContratoInvalido:
                pass
        self.assertEqual(a["visibility"], c.PLAYER_HIDDEN)
        self.assertEqual(a["disclosure"], c.FORBIDDEN)
        self.assertFalse(c.puede_revelarse(a))

    def test_convertir_si_deja_cambiar_legitimamente(self):
        """La via legitima sigue abierta, y deja constancia."""
        a = c.afirmacion("el sitio tiene contactos", c.FACT,
                         c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.FORBIDDEN,
                         evidences=[c.evidencia("sitio", "87", ["eventos"],
                                                "nucleo.Archivo.ficha_sitio")],
                         no_descubierto=True)
        b = c.convertir(a, "revelar", "el jugador lo ha descubierto")
        self.assertEqual(b["visibility"], c.PLAYER_VISIBLE)
        self.assertEqual(b["disclosure"], c.ALLOWED)
        self.assertIn("conversion", b)
        self.assertEqual(b["conversion"]["motivo"],
                         "el jugador lo ha descubierto")
        self.assertEqual(a["visibility"], c.PLAYER_HIDDEN,
                         "la original no se toca")
# ============================================================ PROCEDENCIA ====
class TestProvenance(unittest.TestCase):
    """10-11. Procedencia y `dataset_id`, con datos reales."""

    def test_dataset_id_real_y_no_inventado(self):
        self.assertNotEqual(ia.DATASET_ID, ia.DESCONOCIDO,
                            "el dataset_id debe leerse del disco")
        with open(os.path.join(RAIZ, "00_SOURCE", "dataset_version.json"),
                  encoding="utf-8") as f:
            self.assertEqual(ia.DATASET_ID, json.load(f)["dataset_id"])

    def test_no_se_usa_reloj_para_identificar(self):
        """El identificador no depende de la hora: es el del dataset."""
        self.assertNotRegex(ia.DATASET_ID, r"\d{4}-\d{2}-\d{2}")
        self.assertTrue(ia.DATASET_ID.startswith("v1-"))

    def test_cada_tipo_trae_procedencia(self):
        casos = [(PUENTE.obtener_conocimiento_figura(FIGURA_REAL), "figura"),
                 (PUENTE.obtener_conocimiento_entidad(ENTIDAD_REAL), "entidad"),
                 (PUENTE.obtener_conocimiento_sitio(SITIO_REAL), "sitio"),
                 (PUENTE.obtener_conocimiento_evento(EVENTO_REAL), "evento"),
                 (PUENTE.obtener_conocimiento_artefacto(ARTEFACTO_REAL),
                  "artefacto")]
        for k, tipo in casos:
            p = k["provenance"]
            self.assertEqual(p["dataset_id"], ia.DATASET_ID)
            self.assertEqual(p["entity_type"], tipo)
            self.assertTrue(p["entity_id"])
            self.assertTrue(p["funciones"],
                            "la procedencia dice de que funcion salio")

    def test_la_evidencia_apunta_a_la_funcion_del_nucleo(self):
        """14-18. Se responde a: ¿de que dato real salio esto?"""
        k = PUENTE.obtener_conocimiento_sitio(SITIO_REAL)
        for a in k["claims"]:
            if not a["evidence"]:
                continue
            ev = a["evidence"][0]
            self.assertEqual(ev["df_id"], "87")
            self.assertTrue(ev["funcion"].startswith("nucleo.Archivo."))
            self.assertTrue(ev["datos_utilizados"],
                            "la evidencia dice que campo se uso")

    def test_el_contexto_mandatory_viene_siempre(self):
        k = PUENTE.obtener_conocimiento_figura(FIGURA_REAL)
        ctx = k["contexto"]
        self.assertTrue(ctx["exige_evidencia"])
        self.assertTrue(ctx["unknown_es_respuesta_valida"])
        self.assertTrue(ctx["limitaciones"])


# ========================================================= ENTIDADES REALES ==
class TestEntidadesReales(unittest.TestCase):
    """14-18. Los cinco tipos, contra el dataset real."""

    def test_figura_real(self):
        k = PUENTE.obtener_conocimiento_figura(FIGURA_REAL)
        self.assertEqual(k["asunto"]["nombre"],
                         "galka shafttop the blades of knighting")
        self.assertTrue(any("MINOTAUR" in a["claim"] for a in k["claims"]))

    def test_entidad_real(self):
        k = PUENTE.obtener_conocimiento_entidad(ENTIDAD_REAL)
        self.assertEqual(k["asunto"]["nombre"], "the rock of voicing")
        self.assertTrue(any("dwarf" in a["claim"] for a in k["claims"]))

    def test_sitio_real(self):
        k = PUENTE.obtener_conocimiento_sitio(SITIO_REAL)
        self.assertEqual(k["asunto"]["nombre"], "halesteel")
        self.assertTrue(claims_de(k, "fortress"))

    def test_evento_real(self):
        k = PUENTE.obtener_conocimiento_evento(EVENTO_REAL)
        self.assertEqual(k["asunto"]["certeza"], c.FACT)
        self.assertTrue(claims_de(k, "change hf state"))

    def test_artefacto_real(self):
        k = PUENTE.obtener_conocimiento_artefacto(ARTEFACTO_REAL)
        self.assertTrue(claims_de(k, "primeval wood halberd"))

    def test_ningun_claim_se_revela_de_magia(self):
        """Real o no, nada sale sin pasar por la puerta."""
        for k in (PUENTE.obtener_conocimiento_figura(FIGURA_REAL),
                  PUENTE.obtener_conocimiento_entidad(ENTIDAD_REAL),
                  PUENTE.obtener_conocimiento_sitio(SITIO_REAL),
                  PUENTE.obtener_conocimiento_evento(EVENTO_REAL),
                  PUENTE.obtener_conocimiento_artefacto(ARTEFACTO_REAL)):
            for a in k["claims"]:
                # todo lo que sale del puente ha de estar validado
                self.assertEqual(c.validar(a), [],
                                 "un claim invalido no debe construirse")
                if c.puede_revelarse(a):
                    self.assertEqual(a["disclosure"], c.ALLOWED)
                else:
                    # lo que no se revela explica por que, y sin filtrar rutas
                    self.assertIsNotNone(c.violacion(a))
# ============================================================= ADVERSARIAL ==
class TestIdentificadoresHostiles(unittest.TestCase):
    """16. El consumidor intenta romper el puente."""

    #: Valores con los que no puede haber traceback ni dato inventado.
    HOSTILES = ("abc", "", "  ", "-1", "0", "None", "null", "NaN",
                "../../etc/passwd", "712; DROP TABLE", "{'a':1}", "[]",
                "999999999999999999999", "9" * 400, "🙂🙂🙂",
                "ografía", "ゼロ", "1e10", "0x1f", "true")

    def _consulta(self, metodo, valor):
        k = getattr(PUENTE, metodo)(valor)
        self.assertIn("claims", k, "siempre devuelve un sobre")
        self.assertIn("provenance", k)
        for a in k["claims"]:
            self.assertEqual(c.validar(a), [])
            self.assertIsNotNone(c.violacion(a) or "")
        return k

    def test_ids_hostiles_en_figura(self):
        for v in self.HOSTILES:
            with self.subTest(v=v):
                self._consulta("obtener_conocimiento_figura", v)

    def test_ids_hostiles_en_sitio(self):
        for v in self.HOSTILES:
            with self.subTest(v=v):
                self._consulta("obtener_conocimiento_sitio", v)

    def test_ids_hostiles_en_entidad_evento_artefacto(self):
        for metodo in ("obtener_conocimiento_entidad",
                       "obtener_conocimiento_evento",
                       "obtener_conocimiento_artefacto"):
            for v in self.HOSTILES:
                with self.subTest(m=v):
                    self._consulta(metodo, v)

    def test_none_y_tipos_no_esperados(self):
        for v in (None, [], {}, set(), 1.5, True, b"712", object()):
            with self.subTest(v=type(v).__name__):
                k = self._consulta("obtener_conocimiento_figura", v)

    def test_un_id_inexistente_es_unknown_con_motivo(self):
        k = PUENTE.obtener_conocimiento_figura("999999999")
        self.assertEqual(k["asunto"]["certeza"], c.UNKNOWN)
        for a in k["claims"]:
            self.assertEqual(a["truth_status"], c.UNKNOWN)
            self.assertIsNotNone(a.get("motivo"))

    def test_un_id_hostile_no_inventa_claims(self):
        """Un id raro no puede producir un hecho: o hay dato o hay hueco."""
        k = PUENTE.obtener_conocimiento_sitio("../../etc/passwd")
        for a in k["claims"]:
            self.assertEqual(a["truth_status"], c.UNKNOWN)


class TestEntradasHostiles(unittest.TestCase):
    """16. La puerta recibe basura y no filtra ni revienta."""

    def test_sobre_no_dict(self):
        for basura in (None, [], "texto", 42, 3.5, set()):
            with self.subTest(b=type(basura).__name__):
                self.assertEqual(ia.claims_divulgables(basura), [])
                self.assertEqual(ia.claims_para_razonar(basura), [])
                r = ia.preparar_respuesta_jugador(basura)
                self.assertEqual(r["divulgable"], [])
                self.assertIn("nota", r)

    def test_sobre_con_claims_que_no_son_afirmaciones(self):
        k = {"claims": [None, "texto", 42, {"claim": "x"}, []]}
        self.assertEqual(ia.claims_divulgables(k), [])
        self.assertEqual(ia.claims_para_razonar(k), [])
        r = ia.preparar_respuesta_jugador(k)
        self.assertEqual(r["divulgable"], [])
        self.assertEqual(r["omitidos"], 5)

    def test_no_filtra_rutas_internas(self):
        """Lo que se explica al consumidor no menciona el disco."""
        for metodo, valor in (("obtener_conocimiento_figura", "abc"),
                              ("obtener_conocimiento_sitio", None)):
            texto = json.dumps(ia.preparar_respuesta_jugador(
                getattr(PUENTE, metodo)(valor)), ensure_ascii=False)
            for prohibido in ("00_SOURCE", "jsonl", "Traceback",
                              "Dwarf Fortress", "\\", "dfchron"):
                self.assertNotIn(prohibido, texto)
class TestInferenciaAdversarial(unittest.TestCase):
    """7 y 13. Una inferencia sin evidencia no se puede construir."""

    def test_inferencia_sin_evidencia_se_rechaza(self):
        for caso in (None, [], (), ""):
            with self.subTest(caso=repr(caso)):
                with self.assertRaises(ia.ConocimientoNoDisponible):
                    ia.registrar_inferencia("podria ser peligroso", caso)

    def test_inferencia_sin_enunciado_se_rechaza(self):
        for vacio in ("", "   ", None, 42, []):
            with self.subTest(vacio=repr(vacio)):
                with self.assertRaises(ia.ConocimientoNoDisponible):
                    ia.registrar_inferencia(vacio, [c.evidencia("s", "1", [])])

    def test_inferencia_nunca_es_fact(self):
        inf = ia.registrar_inferencia(
            "quizá hay indicios",
            [c.evidencia("r", "x", ["tipo"], "nucleo.Archivo.ficha_sitio")])
        self.assertNotEqual(inf["truth_status"], c.FACT)
        with self.assertRaises(c.ContratoInvalido):
            c.afirmacion("conclusion", c.FACT, c.INFERENCE, c.PLAYER_VISIBLE,
                         evidences=[c.evidencia("r", "x", ["t"], "f")])


class TestDeterminismo(unittest.TestCase):
    """18. Misma entrada, misma salida. Siempre."""

    def test_misma_consulta_da_identico_bytes(self):
        for metodo, valor in (("obtener_conocimiento_figura", FIGURA_REAL),
                              ("obtener_conocimiento_entidad", ENTIDAD_REAL),
                              ("obtener_conocimiento_sitio", SITIO_REAL),
                              ("obtener_conocimiento_evento", EVENTO_REAL),
                              ("obtener_conocimiento_artefacto",
                               ARTEFACTO_REAL)):
            with self.subTest(m=metodo):
                uno = json.dumps(getattr(PUENTE, metodo)(valor),
                                 ensure_ascii=False, sort_keys=True)
                dos = json.dumps(getattr(PUENTE, metodo)(valor),
                                 ensure_ascii=False, sort_keys=True)
                self.assertEqual(uno, dos)

    def test_dos_puentes_distintos_coinciden(self):
        a = ia.Puente(PUENTE.archivo).obtener_conocimiento_sitio(SITIO_REAL)
        b = ia.Puente(PUENTE.archivo).obtener_conocimiento_sitio(SITIO_REAL)
        self.assertEqual(json.dumps(a, ensure_ascii=False, sort_keys=True),
                         json.dumps(b, ensure_ascii=False, sort_keys=True))

    def test_no_hay_reloj_en_la_procedencia(self):
        """Nada de marcas de tiempo: el mismo dataset da la misma firma."""
        p = PUENTE.obtener_conocimiento_sitio(SITIO_REAL)["provenance"]
        self.assertEqual(sorted(p), ["dataset_id", "entity_id", "entity_type",
                                     "fuentes_xml", "funciones"])
        for clave in p:
            self.assertNotRegex(str(p[clave]), r"\d{4}-\d{2}-\d{2}T")


# ================================================== NO HAY IA EN ESTA MISION =
class TestNoHayIA(unittest.TestCase):
    """14 y §16. Se comprueba POR NEGACION que no se ha instalado una IA."""

    #: Endpoints de IA que no deben existir. La web no tiene chat.
    RUTAS_PROHIBIDAS = ("/api/ai", "/api/chat", "/api/assistant",
                        "/api/ia", "/api/ask", "/api/preguntar")

    def test_la_api_no_expone_rutas_de_ia(self):
        with open(os.path.join(RAIZ, "dfchron", "api.py"), encoding="utf-8") as f:
            fuente = f.read()
        for ruta in self.RUTAS_PROHIBIDAS:
            self.assertNotIn(f'"{ruta}"', fuente,
                             f"{ruta} no debe existir")

    def test_esta_mision_no_creo_rutas(self):
        """El modulo nuevo tampoco declara rutas de IA.

        Solo se mira `ia_conocimiento.py`: esta suite contiene los nombres
        prohibidos para comprobarlos, asi que escanearse a si misma daria un
        falso positivo.
        """
        with open(os.path.join(RAIZ, "dfchron", "ia_conocimiento.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for ruta in self.RUTAS_PROHIBIDAS:
            self.assertNotIn(f'"{ruta}"', fuente,
                             f"{ruta} no debe existir")

    def test_no_hay_sdk_de_ia_instalado(self):
        """El proyecto sigue usando solo la biblioteca estandar."""
        with open(os.path.join(RAIZ, "dfchron", "ia_conocimiento.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for sdk in ("openai", "anthropic", "google.generativeai", "ollama",
                    "langchain", "llama_index", "transformers", "requests",
                    "urllib", "http", "socket"):
            self.assertNotRegex(
                fuente, rf"^\s*(import|from)\s+{re.escape(sdk)}\b",
                f"{sdk} no debe importarse")

    def test_el_puente_no_abre_los_datos_del_mundo(self):
        """Solo lee `dataset_version.json`; los datos llegan por el nucleo.

        Abrir el XML o el JSONL aqui seria saltarse el nucleo, que es quien
        declara la certeza de cada dato. Por eso no puede ocurrir.
        """
        with open(os.path.join(RAIZ, "dfchron", "ia_conocimiento.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("legends.xml", "legends_plus.xml", ".jsonl",
                          "processed/", "merged"):
            self.assertNotIn(f'"{prohibido}"', fuente,
                             f"{prohibido} no se abre directamente")
        # y la unica lectura de disco es el identificador del dataset
        aperturas = re.findall(r"open\(([^)]*)\)", fuente)
        self.assertEqual(len(aperturas), 1, "una sola lectura: el dataset_id")
        self.assertIn("VERSION_DATASET", aperturas[0])

    def test_external_esta_declarado_desconectado(self):
        """Se nombran las fuentes FUTURAS y se declara que no hay ninguna."""
        self.assertEqual(ia.EXTERNAL_PENDIENTE,
                         ("wiki", "raws", "manuales", "documentacion"))
        # es una tupla de un solo texto largo: se busca la palabra dentro
        texto = " ".join(ia.EXTERNAL_NO_CONECTADO)
        self.assertIn("desconectado", texto)
        self.assertIn("no hay ninguna fuente", texto)
        self.assertIn("EXTERNAL_KNOWLEDGE", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)