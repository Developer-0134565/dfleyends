#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: SEMANTICA CONGELADA del contrato de IA
========================================================

La mision de congelar el contrato NO permite inventar semantica. Este fichero no
la inventa: **la ejecuta** y la fija.

Cada prueba responde a una pregunta que la documentacion tiene que poder
contestar con la misma respuesta. Si alguien cambia el contrato sin cambiar esta
semantica, estas pruebas fallan. Si alguien cambia la documentacion para que
diga otra cosa, falla `probar_documentacion_ia.py`.

LO QUE CONGELA
--------------
  * Los valores REALES serializados de las cuatro dimensiones.
  * Que `validar()` y `puede_revelarse()` NO son la misma pregunta.
  * La matriz completa de combinaciones: valida / revelable / afirmable.
  * `CONDITIONAL`: que condicion necesita, donde se evalua, y que NO abre.
  * `disclosure_alias`: que es, quien lo rellena (nadie), quien lo consume.
  * `INFERENCE` + `FORBIDDEN`: comportamiento real, no el imaginado.
  * La inmutabilidad de la evidencia y de la procedencia.
  * El determinismo: misma entrada, misma decision, sin timestamps.

LO QUE NO HACE
--------------
No prueba una IA porque no hay ninguna. No inventa un consumidor para
`disclosure_alias`. No decide lo que el codigo no decide.

Ejecutar:  python dfchron/pruebas/probar_semantica_ia.py
"""
import copy
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

#: Evidencia real y valida. Es la misma que usa el puente contra `nucleo.py`.
EV = [c.evidencia("sitio", "183", ["type"], "nucleo.Archivo.ficha_sitio",
                  "legends.xml")]

#: Las cuatro dimensiones, con los valores que tiene HOY el codigo. Se leen de
#: las constantes y no se escriben a mano: si el codigo cambia, la matriz se
#: recalcula sola y las pruebas dicen la verdad.
DIMENSIONES = (
    ("truth_status", c.TRUTH_STATUS),
    ("knowledge_source", c.KNOWLEDGE_SOURCES),
    ("visibility", c.VISIBILITIES),
    ("disclosure", c.DISCLOSURES),
)


def evidencia_valida():
    """Una evidencia nueva cada vez: las de abajo son de solo lectura."""
    return [c.evidencia("sitio", "183", ["type"],
                        "nucleo.Archivo.ficha_sitio", "legends.xml")]


def cruda(ts, ks, vis, disc, **extra):
    """Diccionario tal como lo recibe `validar()` (clave `evidence`)."""
    d = {"claim": "afirmacion de prueba",
         "truth_status": ts, "knowledge_source": ks,
         "visibility": vis, "disclosure": disc,
         "evidence": evidencia_valida()}
    d.update(extra)
    return d


def construir(ts, ks, vis, disc, **extra):
    """La misma combinacion, ya construida y sellada."""
    return c.afirmacion(claim="afirmacion de prueba", truth_status=ts,
                        knowledge_source=ks, visibility=vis, disclosure=disc,
                        evidences=evidencia_valida(), **extra)


def todas_las_combinaciones():
    """Las 4 x 4 x 3 x 3 = 144 combinaciones, sin filtrar."""
    for ts in c.TRUTH_STATUS:
        for ks in c.KNOWLEDGE_SOURCES:
            for vis in c.VISIBILITIES:
                for disc in c.DISCLOSURES:
                    yield ts, ks, vis, disc


def validas():
    """Las combinaciones que `validar()` acepta."""
    for ts, ks, vis, disc in todas_las_combinaciones():
        if not c.validar(cruda(ts, ks, vis, disc)):
            yield ts, ks, vis, disc


def modulos_de_dfchron():
    """Contenido de los modulos de `dfchron/`, para comprobar que nadie usa
    un campo por su cuenta."""
    raiz = os.path.join(RAIZ, "dfchron")
    for nombre in sorted(os.listdir(raiz)):
        if not nombre.endswith(".py"):
            continue
        with open(os.path.join(raiz, nombre), encoding="utf-8") as f:
            yield nombre, f.read()


# ============================ 1. LOS VALORES REALES SERIALIZADOS ==========
class TestValoresCongelados(unittest.TestCase):
    """Lo que se escribe en un JSON, no lo que se escribe en el codigo."""

    def test_los_valores_serializados_reales(self):
        """La verdad del contrato, leida del codigo y no de la documentacion."""
        self.assertEqual(c.TRUTH_STATUS,
                         ("FACT", "DERIVED", "UNKNOWN", "INTERPRETATION"))
        self.assertEqual(c.KNOWLEDGE_SOURCES,
                         ("PLAYER_KNOWLEDGE", "WORLD_KNOWLEDGE",
                          "EXTERNAL_KNOWLEDGE", "INTERPRETATION"))
        self.assertEqual(c.VISIBILITIES,
                         ("PLAYER_VISIBLE", "PLAYER_HIDDEN", "EXTERNAL"))
        self.assertEqual(c.DISCLOSURES,
                         ("ALLOWED", "FORBIDDEN", "CONDITIONAL"))

    def test_inference_es_nombre_e_interpretation_es_valor(self):
        """La trampa de la mision: el CONCEPTO no es el VALOR SERIALIZADO."""
        self.assertEqual(c.INFERENCE, "INTERPRETATION")
        self.assertNotEqual(c.INFERENCE, "INFERENCE")

    def test_inference_como_valor_serializado_se_rechaza(self):
        """Escribir "INFERENCE" en un JSON rompe, y debe seguir rompiendo."""
        for ts, ks in (("INFERENCE", c.WORLD_KNOWLEDGE),
                       (c.FACT, "INFERENCE")):
            with self.subTest(ts=ts, ks=ks):
                with self.assertRaises(c.ContratoInvalido):
                    construir(ts, ks, c.PLAYER_VISIBLE, c.ALLOWED)

    def test_allowed_es_el_valor_real_de_afirmable(self):
        """`AFFIRMABLE` es el concepto de la mision. `ALLOWED` es el valor.

        La equivalencia se DECLARA, no se renombra: el identificador del codigo
        se queda como esta.
        """
        self.assertIn(c.ALLOWED, c.DISCLOSURES)
        self.assertNotIn("AFFIRMABLE", c.DISCLOSURES)

    def test_ninguna_dimension_se_llama_afirmable(self):
        for nombre, valores in DIMENSIONES:
            with self.subTest(dimension=nombre):
                self.assertNotIn("AFFIRMABLE", valores)

    def test_los_certezas_vienen_del_nucleo(self):
        """`truth_status` no es una decision del contrato: la hace el nucleo."""
        sys.path.insert(0, os.path.join(RAIZ, "00_SOURCE", "tools"))
        import nucleo
        self.assertEqual(c.FACT, nucleo.FACT)
        self.assertEqual(c.DERIVED, nucleo.DERIVED)
        self.assertEqual(c.UNKNOWN, nucleo.UNKNOWN)
        self.assertEqual(c.INFERENCE, nucleo.INTERPRETATION)


# ==================== 2. VALIDAR() Y REVELAR() NO SON LO MISMO =============
class TestValidarNoEsRevelar(unittest.TestCase):
    """La distincion que motiva el caso `PLAYER_HIDDEN + ALLOWED`."""

    def test_valida_pero_no_revelable(self):
        """`PLAYER_HIDDEN + ALLOWED` es VALIDA y NO REVELABLE. Las dos cosas."""
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.ALLOWED)
        self.assertEqual(c.validar(a), [], "debe ser estructuralmente valida")
        self.assertFalse(c.puede_revelarse(a))

    def test_revelable_implica_valida(self):
        """Lo revelable nunca es invalido: es la direccion de la flecha."""
        for ts, ks, vis, disc in validas():
            a = construir(ts, ks, vis, disc)
            if c.puede_revelarse(a):
                with self.subTest(combo="%s/%s/%s/%s" % (ts, ks, vis, disc)):
                    self.assertEqual(c.validar(a), [])

    def test_la_que_bloquea_es_una_regla_concreta(self):
        """`puede_revelarse()` con `PLAYER_HIDDEN` exige CONDITIONAL y pista.

        No es una condicion difusa: son las dos cosas, y las dos a la vez.
        """
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.ALLOWED)
        self.assertIn("PLAYER_HIDDEN", c.violacion(a))

    def test_razonar_revelar_afirmar_son_tres_preguntas(self):
        """El secreto razonable pero no contable: las tres funciones difieren."""
        s = c.ejemplo_secreto()
        self.assertTrue(c.puede_usarse_para_razonar(s))
        self.assertFalse(c.puede_revelarse(s))
        self.assertFalse(c.puede_afirmarse_como_hecho(s))
# ========================= 3. LA MATRIZ DE COMBINACIONES ===================
class TestMatrizDeCombinaciones(unittest.TestCase):
    """Las filas que la mision exige, con el resultado REAL de cada una."""

    #: (truth, source, visibility, disclosure, valida, revelable, afirmable)
    FILAS = (
        (c.FACT, c.PLAYER_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED,
         True, True, True),
        (c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED,
         True, True, True),
        (c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.ALLOWED,
         True, False, False),
        (c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.FORBIDDEN,
         True, False, False),
        (c.FACT, c.EXTERNAL_KNOWLEDGE, c.EXTERNAL, c.ALLOWED,
         False, False, False),
        (c.DERIVED, c.PLAYER_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED,
         True, True, False),
        (c.DERIVED, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN, c.FORBIDDEN,
         True, False, False),
        (c.UNKNOWN, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED,
         True, False, False),
        (c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE, c.ALLOWED,
         True, True, False),
        (c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE, c.CONDITIONAL,
         True, False, False),
        (c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE, c.FORBIDDEN,
         True, False, False),
    )

    def test_cada_fila_de_la_mision(self):
        """Las 11 filas obligatorias, comprobadas una a una."""
        for ts, ks, vis, disc, valida, rev, hecho in self.FILAS:
            with self.subTest(combo="%s/%s/%s/%s" % (ts, ks, vis, disc)):
                if not valida:
                    with self.assertRaises(c.ContratoInvalido):
                        construir(ts, ks, vis, disc)
                    continue
                a = construir(ts, ks, vis, disc)
                self.assertEqual(c.puede_revelarse(a), rev, "revelable")
                self.assertEqual(c.puede_afirmarse_como_hecho(a), hecho,
                                 "afirmable")

    def test_world_knowledge_visible_necesita_no_descubierto_falso(self):
        """La fila 2 es legal SIN `no_descubierto`; con el, es ilegal.

        No es un detalle: es lo que distingue "el jugador ya lo vio" de "nadie
        lo ha visto". Sin la marca, el contrato no puede saberlo, y por eso el
        puente hace nacer `WORLD_KNOWLEDGE` con `no_descubierto=True`.
        """
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED)
        self.assertTrue(c.puede_revelarse(a))
        with self.assertRaises(c.ContratoInvalido):
            construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, c.ALLOWED,
                      no_descubierto=True)

    # --- invariantes sobre las 144 combinaciones -------------------------
    def test_forbidden_nunca_es_revelable(self):
        """`FORBIDDEN` manda sobre las demas dimensiones. Sin excepciones."""
        for ts, ks, vis, disc in validas():
            if disc != c.FORBIDDEN:
                continue
            with self.subTest(combo="%s/%s/%s" % (ts, ks, vis)):
                a = construir(ts, ks, vis, disc)
                self.assertFalse(c.puede_revelarse(a))
                self.assertFalse(c.puede_afirmarse_como_hecho(a))

    def test_unknown_nunca_es_revelable(self):
        """`UNKNOWN` es valido y no rellenable, pero no es una afirmacion."""
        for ts, ks, vis, disc in validas():
            if ts != c.UNKNOWN:
                continue
            with self.subTest(combo="%s/%s/%s" % (ks, vis, disc)):
                self.assertFalse(c.puede_revelarse(construir(ts, ks, vis, disc)))

    def test_solo_un_fact_visible_se_afirma_como_hecho(self):
        """`puede_afirmarse_como_hecho()` exige `FACT`, `PLAYER_VISIBLE` y
        no `CONDITIONAL`.

        HALLAZGO DE AUDITORIA (§3 del contrato de I/O): antes de cerrarlo, esto
        tambien era `True` con `visibility = EXTERNAL`, porque `EXTERNAL`
        esquivaba la rama `PLAYER_HIDDEN`. Se cerro haciendo la regla
        bidireccional: `visibility=EXTERNAL` es exactamente "esto no describe
        esta partida", asi que solo lo externo puede llevarla. Verificado abajo.
        """
        for ts, ks, vis, disc in validas():
            a = construir(ts, ks, vis, disc)
            if c.puede_afirmarse_como_hecho(a):
                with self.subTest(combo="%s/%s/%s/%s" % (ts, ks, vis, disc)):
                    self.assertEqual(ts, c.FACT)
                    self.assertNotEqual(disc, c.CONDITIONAL)
                    self.assertEqual(vis, c.PLAYER_VISIBLE)

    def test_external_ya_no_esquiva_la_frontera(self):
        """El cierre de §3: `EXTERNAL` solo es de `EXTERNAL_KNOWLEDGE`.

        Antes, `WORLD_KNOWLEDGE + FACT + EXTERNAL + ALLOWED` era una via para
        convertir un secreto en afirmacion. Ahora es una combinacion imposible.
        """
        for ks in (c.WORLD_KNOWLEDGE, c.PLAYER_KNOWLEDGE, c.INFERENCE):
            for ts in (c.FACT, c.DERIVED):
                with self.subTest(ks=ks, ts=ts):
                    with self.assertRaises(c.ContratoInvalido):
                        construir(ts, ks, c.EXTERNAL, c.ALLOWED)

    def test_external_knowledge_conserva_exTERNAL(self):
        """El cierre no rompe el caso legitimo: la wiki sigue siendo externa."""
        a = construir(c.DERIVED, c.EXTERNAL_KNOWLEDGE, c.EXTERNAL, c.ALLOWED)
        self.assertEqual(c.validar(a), [])
        self.assertTrue(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "explicar una mecanica no es un hecho de la partida")

    def test_externo_no_razona_sobre_esta_partida(self):
        for ts, ks, vis, disc in validas():
            if ks != c.EXTERNAL_KNOWLEDGE:
                continue
            with self.subTest(combo="%s/%s/%s" % (ts, vis, disc)):
                self.assertFalse(
                    c.puede_usarse_para_razonar(construir(ts, ks, vis, disc)))

    def test_nada_oculto_se_revela_su_al_permitido(self):
        """Regla de oro: `FACT` no implica divulgable, en ninguna parte.

        Si alguna combinacion con `visibility=PLAYER_HIDDEN` resultara
        revelable sin `CONDITIONAL`, esta prueba lo detectaria.
        """
        for ts, ks, vis, disc in validas():
            if vis == c.PLAYER_HIDDEN and disc != c.CONDITIONAL:
                with self.subTest(combo="%s/%s/%s" % (ts, ks, disc)):
                    self.assertFalse(
                        c.puede_revelarse(construir(ts, ks, vis, disc)))

    def test_lo_rechazado_dice_siempre_por_que(self):
        """Cada combinacion invalida se explica en texto."""
        for ts, ks, vis, disc in todas_las_combinaciones():
            problemas = c.validar(cruda(ts, ks, vis, disc))
            if problemas:
                with self.subTest(combo="%s/%s/%s/%s" % (ts, ks, vis, disc)):
                    self.assertTrue(all(isinstance(p, str) and p
                                        for p in problemas))
# ================================ 4. CONDITIONAL ===========================
class TestConditional(unittest.TestCase):
    """Su semantica REAL, deducida de `puede_revelarse()`.

    No se inventa: se lee. La condicion es `disclosure == CONDITIONAL` Y
    `pista_permitida is True`, y solo se evalua en la rama `PLAYER_HIDDEN`.
    """

    def test_necesita_las_dos_cosas(self):
        """`CONDITIONAL` solo, sin pista, sigue bloqueado."""
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                      c.CONDITIONAL)
        self.assertEqual(c.validar(a), [], "es valida: valida y no revelable")
        self.assertFalse(c.puede_revelarse(a))

    def test_la_pista_autorizada_lo_abre(self):
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                      c.CONDITIONAL, pista_permitida=True)
        self.assertTrue(c.puede_revelarse(a))

    def test_la_pista_debe_ser_el_booleano_true(self):
        """`is True`: ni `1`, ni `"si"`, ni `"True"` abren la puerta.

        Si fuera truthy, un dato externo que llegue como texto abriria la
        frontera sin querer.
        """
        for valor in (1, "si", "True", "1", [1], {"x": 1}, True):
            with self.subTest(pista=valor):
                a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                              c.CONDITIONAL, pista_permitida=valor)
                self.assertEqual(c.puede_revelarse(a), valor is True)

    def test_conditional_permite_mencionar_no_afirmar(self):
        """Su sentido: la MENCION se autoriza, la AFIRMACION no."""
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                      c.CONDITIONAL, pista_permitida=True)
        self.assertTrue(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a))

    def test_conditional_no_abre_allowed_oculto(self):
        """`ALLOWED + pista_permitida` NO revela: hace falta `CONDITIONAL`."""
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                      c.ALLOWED, pista_permitida=True)
        self.assertFalse(c.puede_revelarse(a),
                         "una pista no convierte ALLOWED en revelable")

    def test_conditional_solo_cabe_en_player_hidden(self):
        """Es la rama donde se evalua. En `PLAYER_VISIBLE` no abre nada.

        Consecuencia congelada: `CONDITIONAL` solo tiene sentido sobre algo que
        el jugador todavia no sabe. Si ya lo sabe, corresponde `ALLOWED`.
        """
        for pista in (None, True):
            with self.subTest(pista=pista):
                kw = {} if pista is None else {"pista_permitida": True}
                a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE,
                              c.CONDITIONAL, **kw)
                self.assertFalse(c.puede_revelarse(a))

    def test_conditional_no_es_la_condicion_de_disclosure_alias(self):
        """No se confunden: son dos campos con dos papeles distintos.

        `pista_permitida` abre la divulgacion. `disclosure_alias` solo se
        comprueba en `validar()` y no participa de esta decision.
        """
        a = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                      c.CONDITIONAL, pista_permitida=True)
        sin_alias = dict(a)
        sin_alias["disclosure_alias"] = c.CONDITIONAL
        self.assertEqual(c.puede_revelarse(a), c.puede_revelarse(sin_alias))

    def test_quien_autoriza_la_pista_no_esta_decidido(self):
        """Esto es una AMBIGUEDAD documentada, no una funcionalidad.

        Se comprueba de verdad: ningun modulo del proyecto pone
        `pista_permitida=True` fuera de las pruebas. Es decir, `CONDITIONAL`
        hoy no se abre en produccion. No se inventa quien autoriza.
        """
        autores = [nombre for nombre, texto in modulos_de_dfchron()
                   if re.search(r"pista_permitida\s*=\s*True", texto)]
        self.assertEqual(
            autores, [],
            "ningun modulo de produccion debe autorizar una pista por su "
            "cuenta; si aparece uno, hay que documentar quien y con que "
            "criterio")


# ============================= 5. disclosure_alias ========================
class TestDisclosureAlias(unittest.TestCase):
    """Decision de la auditoria: es una GUARDA, no una dimension.

    Que es:            un campo opcional que `validar()` consulta para detectar
                      un registro que se contradice a si mismo.
    Quien lo rellena: NADIE. Ningun modulo del proyecto lo produce.
    Quien lo consume: NADIE. No entra en `puede_revelarse()` ni en
                      `convertir()`.
    Si queda pendiente: SI. Su poblacion depende de un productor de datos
                      externos que todavia no existe.
    """

    def test_solo_detecta_la_contradiccion_allowed_forbidden(self):
        """Unica regla: alias ALLOWED junto a disclosure FORBIDDEN."""
        d = cruda(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, c.FORBIDDEN,
                  disclosure_alias=c.ALLOWED)
        problemas = c.validar(d)
        self.assertTrue(problemas)
        self.assertTrue(any("contradictoria" in p for p in problemas))

    def test_cualquier_otra_combinacion_pasa(self):
        """La guarda es ESTRECHA: no es una segunda dimension.

        Incluido `disclosure_alias` con un valor que no existe: no se valida
        contra `DISCLOSURES`, luego no es una dimension disfrazada.
        """
        for alias in (None, c.ALLOWED, c.FORBIDDEN, c.CONDITIONAL, "basura"):
            for disc in c.DISCLOSURES:
                extra = {} if alias is None else {"disclosure_alias": alias}
                d = cruda(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_VISIBLE, disc,
                          **extra)
                problemas = c.validar(d)
                with self.subTest(alias=alias, disc=disc):
                    if alias == c.ALLOWED and disc == c.FORBIDDEN:
                        self.assertTrue(problemas)
                    else:
                        self.assertEqual(problemas, [])

    def test_no_es_una_quinta_dimension(self):
        """No aparece en las dimensiones ni en `contexto_obligatorio()`."""
        for nombre, valores in DIMENSIONES:
            self.assertNotIn("disclosure_alias", valores)
        self.assertNotIn("disclosure_alias",
                         json.dumps(c.contexto_obligatorio()))

    def test_no_afecta_a_la_divulgacion(self):
        """Llevarlo puesto no abre ni cierra nada."""
        base = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                         c.FORBIDDEN, disclosure_alias=c.CONDITIONAL)
        self.assertFalse(c.puede_revelarse(base))
        self.assertFalse(c.puede_afirmarse_como_hecho(base))

    def test_nadie_lo_produce_en_el_codigo(self):
        """Se comprueba contra el codigo, no contra una promesa.

        Decision de auditoria: se CONSERVA la guarda, pero nadie la rellena. Si
        algun dia lo hace, hay que decidir su semantica ANTES de seguir.
        """
        autores = [nombre for nombre, texto in modulos_de_dfchron()
                   if "disclosure_alias" in texto
                   and nombre != "contrato_ia.py"]
        self.assertEqual(
            autores, [],
            "nadie deberia rellenar disclosure_alias todavia; si ya lo hace, "
            "hay que decidir su semantica antes de seguir")

# ==================== 6. INFERENCE (INTERPRETATION) + FORBIDDEN ==========
class TestInferenceForbidden(unittest.TestCase):
    """La ambiguedad que la mision pide NO cerrar a lo bruto.

    Resultado de la auditoria: el codigo NO lo rechaza, y el comportamiento que
    tiene es coherente con la lectura (A): la inferencia existe por dentro y no
    se divulga. No es un descuido: es la unica lectura compatible con que
    `FORBIDDEN` se compruebe ANTES que cualquier otra dimension.
    """

    def test_no_se_rechaza(self):
        a = construir(c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE,
                      c.FORBIDDEN)
        self.assertEqual(c.validar(a), [], "es estructuralmente valida")

    def test_existe_pero_no_se_divulga(self):
        """(A): puede razonar con ella, no contarla, no afirmarla."""
        a = construir(c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE,
                      c.FORBIDDEN)
        self.assertTrue(c.puede_usarse_para_razonar(a))
        self.assertFalse(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a))

    def test_no_es_un_hueco_sin_uso(self):
        """`FORBIDDEN` no anula el sentido: sigue siendo `INTERPRETATION`.

        Si `FORBIDDEN` la degradara, un `convertir()` podria promoverla.
        """
        a = construir(c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE,
                      c.FORBIDDEN)
        self.assertEqual(a["truth_status"], c.INFERENCE)
        self.assertEqual(a["knowledge_source"], c.INFERENCE)

    def test_inference_allowed_sigue_siendo_solo_mencion(self):
        """El contraste: con `ALLOWED` se menciona, pero no se afirma."""
        a = construir(c.INFERENCE, c.INFERENCE, c.PLAYER_VISIBLE, c.ALLOWED)
        self.assertTrue(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "una inferencia jamas se enuncia como hecho")

    def test_inference_oculta_no_se_revela_ni_con_pista(self):
        a = construir(c.INFERENCE, c.INFERENCE, c.PLAYER_HIDDEN, c.ALLOWED,
                      pista_permitida=True)
        self.assertFalse(c.puede_revelarse(a))

    def test_inference_jamas_es_fact(self):
        """Una conclusion no es una fuente.

        El rechazo es solo para `knowledge_source = INFERENCE`: un `FACT` de
        `PLAYER_KNOWLEDGE` o `WORLD_KNOWLEDGE` con `FORBIDDEN` es perfectamente
        valido (es un secreto, que es justo el caso canonico).
        """
        with self.assertRaises(c.ContratoInvalido):
            construir(c.FACT, c.INFERENCE, c.PLAYER_VISIBLE, c.FORBIDDEN)
        # Y el hecho de estado con FORBIDDEN sigue siendo valido:
        secreto = construir(c.FACT, c.WORLD_KNOWLEDGE, c.PLAYER_HIDDEN,
                            c.FORBIDDEN)
        self.assertEqual(c.validar(secreto), [])
        self.assertFalse(c.puede_revelarse(secreto))


# ============================== 7. SEGURIDAD ==============================
class TestSeguridadDeLaFrontera(unittest.TestCase):
    """La proteccion no depende de que nadie tenga cuidado."""

    def secreto(self):
        """El caso canonico: un diamante con sus coordenadas."""
        return c.afirmacion(
            claim="Existe una veta de diamantes en 183,72,-14.",
            truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
            visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "183", ["coordenadas"],
                                   "nucleo.Archivo.ficha_sitio",
                                   "legends.xml")],
            no_descubierto=True)

    def test_el_secreto_canonico_no_se_revela(self):
        s = self.secreto()
        self.assertFalse(c.puede_revelarse(s))
        self.assertFalse(c.puede_afirmarse_como_hecho(s))
        self.assertTrue(c.puede_usarse_para_razonar(s))

    def test_no_se_puede_cambiar_visibility(self):
        s = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            s["visibility"] = c.PLAYER_VISIBLE

    def test_no_se_puede_cambiar_disclosure(self):
        s = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            s["disclosure"] = c.ALLOWED

    def test_no_se_puede_quitar_la_marca_de_no_descubierto(self):
        s = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            s["no_descubierto"] = False

    def test_no_se_puede_colar_una_pista(self):
        """Anadir `pista_permitida` despues tampoco: es de solo lectura."""
        s = self.secreto()
        with self.assertRaises(c.ContratoInvalido):
            s["pista_permitida"] = True
        self.assertFalse(c.puede_revelarse(s))

    def test_no_se_puede_alterar_la_evidencia_anidada(self):
        """La regresion del ataque original, y sus equivalentes."""
        s = self.secreto()
        datos = s["evidence"][0]["datos_utilizados"]
        ataques = {
            "df_id": lambda: s["evidence"][0].__setitem__("df_id", "999"),
            "funcion": lambda: s["evidence"][0].__setitem__("funcion", "falsa"),
            "entidad": lambda: s["evidence"][0].__setitem__("entidad", "figura"),
            "fuente": lambda: s["evidence"][0].__setitem__("fuente", "inventada"),
            "datos_append": lambda: datos.append("inventado"),
            "datos_setitem": lambda: datos.__setitem__(0, "x"),
            "datos_sort": lambda: datos.sort(),
            "evidencia_append": lambda: s["evidence"].append(
                {"entidad": "x", "df_id": "1"}),
            "evidence_setdefault": lambda: s["evidence"][0].setdefault(
                "df_id", "9"),
            "evidence_update": lambda: s["evidence"][0].update({"df_id": "9"}),
            "evidence_pop": lambda: s["evidence"][0].pop("df_id"),
            "evidence_clear": lambda: s["evidence"][0].clear(),
        }
        for nombre, ataque in ataques.items():
            with self.subTest(ataque=nombre):
                with self.assertRaises(c.ContratoInvalido):
                    ataque()
        self.assertFalse(c.puede_revelarse(s))
        self.assertEqual(s["evidence"][0]["df_id"], "183")

    def test_la_comparacion_no_abre_la_frontera(self):
        """Copiar una afirmacion es util, pero la copia sigue cerrada.

        HALLAZGO DE AUDITORIA: `copy.copy` / `copy.deepcopy` de una
        `Afirmacion` LANZAN `ContratoInvalido`, porque reconstruyen el dict
        llamando a `__setitem__`, que esta cerrado a proposito. No es un fallo:
        es la misma garantia. Para comparar se usa `a_json()` o `dict(a)`, y
        para volver a construir, `desde_json()`.
        """
        s = self.secreto()
        for nombre in ("copy", "deepcopy"):
            with self.subTest(operacion=nombre):
                with self.assertRaises(c.ContratoInvalido):
                    getattr(copy, nombre)(s)

        # Las dos vias que si funcionan.
        self.assertEqual(json.loads(c.a_json(s)), json.loads(c.a_json(s)))
        plano = dict(s)
        self.assertEqual(plano, s)
        # Y una copia "plana" no deja de estar congelada por dentro.
        with self.assertRaises(c.ContratoInvalido):
            plano["evidence"][0]["df_id"] = "999"

    def test_desde_json_devuelve_una_afirmacion_cerrada(self):
        """La ida y vuelta por JSON conserva la frontera."""
        s = self.secreto()
        vuelta = c.desde_json(c.a_json(s))
        self.assertEqual(vuelta, s)
        self.assertFalse(c.puede_revelarse(vuelta))
        with self.assertRaises(c.ContratoInvalido):
            vuelta["evidence"][0]["df_id"] = "999"
        with self.assertRaises(c.ContratoInvalido):
            vuelta["disclosure"] = c.ALLOWED

    def test_la_salida_serializada_no_trae_campos_nuevos(self):
        """`a_json()` entrega lo que hay, sin inventar ni quitar campos."""
        s = self.secreto()
        datos = json.loads(c.a_json(s))
        self.assertEqual(set(datos), set(s.keys()))
        self.assertEqual(datos["evidence"][0]["df_id"], "183")

    def test_convertir_es_la_unica_puerta_y_deja_constancia(self):
        """Descubrir el dato es lo que autoriza a decirlo, y queda escrito."""
        s = self.secreto()
        b = c.convertir(s, "revelar", "el jugador minimizo el mapa")
        self.assertTrue(c.puede_revelarse(b))
        self.assertEqual(b["conversion"]["motivo"],
                         "el jugador minimizo el mapa")
        self.assertEqual(b["conversion"]["desde"], c.PLAYER_HIDDEN)
        self.assertEqual(b["conversion"]["hacia"], c.PLAYER_VISIBLE)
        self.assertEqual(b["conversion"]["tambien"]["campo"], "disclosure")
        # Y el original no se toca.
        self.assertEqual(s["disclosure"], c.FORBIDDEN)
        self.assertFalse(c.puede_revelarse(s))

    def test_convertir_no_acepta_operaciones_inventadas(self):
        s = self.secreto()
        for operacion in ("hackear", "forzar", "", None):
            with self.subTest(operacion=operacion):
                with self.assertRaises(c.ContratoInvalido):
                    c.convertir(s, operacion)

    def test_convertir_no_toca_lo_externo_ni_las_inferencias(self):
        """No "se revelan": no son cosas que el jugador pueda descubrir."""
        for a in (c.ejemplo_externo(), c.ejemplo_inferencia()):
            with self.subTest(afirmacion=a["claim"][:30]):
                with self.assertRaises(c.ContratoInvalido):
                    c.convertir(a, "revelar")

# ============================== 8. DETERMINISMO ===========================
class TestDeterminismo(unittest.TestCase):
    """Misma entrada, misma decision. Sin relojes, sin azar."""

    def test_la_misma_combinacion_da_la_misma_decision(self):
        for ts, ks, vis, disc in list(validas())[:20]:
            with self.subTest(combo="%s/%s/%s/%s" % (ts, ks, vis, disc)):
                a1 = construir(ts, ks, vis, disc)
                a2 = construir(ts, ks, vis, disc)
                self.assertEqual(c.puede_revelarse(a1), c.puede_revelarse(a2))
                self.assertEqual(c.puede_afirmarse_como_hecho(a1),
                                 c.puede_afirmarse_como_hecho(a2))

    def test_la_serializacion_es_byte_a_byte_identica(self):
        self.assertEqual(c.a_json(c.ejemplo_secreto()),
                         c.a_json(c.ejemplo_secreto()))

    def test_el_contrato_no_importa_relojes_ni_azar(self):
        """Se comprueba sobre el codigo: no basta con decirlo en la doc."""
        with open(os.path.join(RAIZ, "dfchron", "contrato_ia.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotRegex(fuente, r"^\s*import\s+time\b", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+random\b", re.M)
        self.assertNotRegex(fuente, r"^\s*import\s+uuid\b", re.M)
        self.assertNotIn("time.time()", fuente)
        self.assertNotIn("datetime.now", fuente)

    def test_los_ejemplos_canonicos_son_estables(self):
        for nombre in ("ejemplo_visible", "ejemplo_secreto",
                       "ejemplo_externo", "ejemplo_inferencia",
                       "ejemplo_unknown"):
            with self.subTest(ejemplo=nombre):
                a1, a2 = getattr(c, nombre)(), getattr(c, nombre)()
                self.assertEqual(c.a_json(a1), c.a_json(a2))


# ========================== 9. LO QUE ESTA PENDIENTE ======================
class TestPendientesDeclarados(unittest.TestCase):
    """Las ambiguedades se declaran. No se rellenan con suposiciones.

    Si alguien decide una de estas, la decision tiene que existir como codigo que
    la imponga. Mientras tanto, estas pruebas vigilan que nadie la de por hecha.
    """

    def test_no_existe_una_quinta_dimension(self):
        """Ni `AFFIRMABLE`, ni `PERSPECTIVE`, ni `AGENT` como dimensiones."""
        for nombre, valores in DIMENSIONES:
            with self.subTest(dimension=nombre):
                for prohibido in ("AFFIRMABLE", "PERSPECTIVE", "AGENT"):
                    self.assertNotIn(prohibido, valores)

    def test_el_contrato_no_inventa_identidad_de_relacion(self):
        """No hay `relation_id`: el dataset no da identidad estable."""
        from dfchron import estado_conocimiento as ec
        self.assertIn("relacion", ec.TIPOS_NO_SOPORTADOS)
        self.assertNotIn("relacion", ec.TIPOS_SOPORTADOS)

    def test_la_frontera_no_depende_de_la_palabra_del_modelo(self):
        """`puede_revelarse()` es una funcion: decide antes de existir el LLM."""
        import inspect
        fuente = inspect.getsource(c.puede_revelarse)
        for prohibido in ("openai", "anthropic", "prompt", "llm"):
            with self.subTest(token=prohibido):
                self.assertNotIn(prohibido, fuente)

    def test_no_hay_sdk_de_ia_instalado_en_el_contrato(self):
        """La frontera no importa ningun proveedor de modelos."""
        for nombre, texto in modulos_de_dfchron():
            if nombre not in ("contrato_ia.py", "estado_conocimiento.py",
                              "ia_conocimiento.py"):
                continue
            with self.subTest(modulo=nombre):
                self.assertNotRegex(
                    texto, r"^\s*(import|from)\s+(openai|anthropic|cohere)\b",
                    re.M)


if __name__ == "__main__":
    unittest.main(verbosity=2)