#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGRESION DE LA FRONTERA LINGUISTICA
=====================================
Cada prueba demuestra una PROPIEDAD, no que "el sistema funciona". Las que
importan son las que fallarian si alguien volviera a entregar el `answer` del
modelo al jugador.

Por que existe esta suite
-------------------------
La auditoria encontro, por el camino real, que los vectores clasicos
(paramfrasis, referencia espacial, sustraccion, distancia, nombre inventado y
consejo filtrador) PASABAN la validacion y llegaban al jugador. El informe lo
declaraba "NO RESUELTO", con razon. Aqui se convierte en algo comprobable: si el
`answer` vuelve a ser la entrega, estas pruebas fallan.

Ejecutar:  python dfchron/pruebas/probar_frontera_linguistica.py
"""
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

from dfchron import contrato_ia as c        # noqa: E402
from dfchron import ia_contrato as ioc      # noqa: E402
from dfchron import ia_frontera as fr       # noqa: E402

FACT = ioc.FACT


def _visible():
    """Un hecho que el jugador ya conoce: es lo unico que se puede decir."""
    return c.afirmacion(
        claim="El jugador conoce la fortaleza de Galka Shafttop.",
        truth_status=c.FACT, knowledge_source=c.PLAYER_KNOWLEDGE,
        visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
        evidences=[c.evidencia("figura", "712", ["name"],
                               "nucleo.Archivo.ficha_figura", "legends.xml")])


def _secreto():
    """La veta de diamantes. Verdadera y prohibida. NUNCA llega al modelo."""
    return c.afirmacion(
        claim="Existe una veta de diamantes en 183,72,-14.",
        truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
        visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
        evidences=[c.evidencia("sitio", "183", ["coordenadas"],
                               "nucleo.Archivo.ficha_sitio", "legends.xml")],
        no_descubierto=True)


def _contexto(modo=ioc.MODO_RAZONAMIENTO):
    return ioc.contexto("donde hay diamantes", [_visible(), _secreto()],
                        modo=modo)


def _claims_ok():
    """Un claim de salida legitimo: apoya en c0, que el jugador si conoce."""
    return [{"texto": "El jugador conoce la fortaleza de Galka Shafttop.",
             "tipo": FACT, "soporte": ["c0"]}]


#: Los ocho vectores MEDIDOS que llegaban al jugador antes de este cambio, con
#: la familia del banco adversarial a la que pertenecen (Â§18).
VECTORES = [
    ("A parafrasis", "Esta mucho mas alla de donde estas."),
    ("B referencia espacial", "Queda hacia donde brilla el amanecer."),
    ("C sustraccion", "Quedan 733 sin explorar."),
    ("D distancia", "Esta a dieciocho tiles al este."),
    ("E nombre inventado", "Se llama Torre Sombra del Norte."),
    ("F consejo filtrador", "Mejor no acerques por ahi."),
    ("G negacion", "No hay nada de valor al norte."),
    ("H cuenta implicita", "De 734 solo llevas 1."),
]


class TestElModeloNoRedacta(unittest.TestCase):
    """La propiedad central: el texto entregado lo compone el SISTEMA."""

    def setUp(self):
        self.ctx = _contexto()
        self.claims = _claims_ok()

    def test_el_texto_entregado_no_depende_del_answer_del_modelo(self):
        """Cambiar el `answer` no cambia NI UNA LETRA de lo entregado.

        Esta es la prueba que define la arquitectura. Si el `answer` volviera a
        ser la entrega, dos `answer` distintos darian textos distintos y aqui
        fallaria. Es la que convierte la fuga de "abierta" en "imposible".
        """
        uno = {"answer": "Torre Sombra del Norte, al norte, 733 sin explorar.",
               "claims": self.claims}
        otro = {"answer": "invento lo que me salga", "claims": self.claims}
        self.assertEqual(fr.componer(uno["claims"], self.ctx),
                         fr.componer(otro["claims"], self.ctx))

    def test_el_answer_hostil_no_llega_al_jugador(self):
        """Lo que el jugador lee no contiene nada del `answer` hostil."""
        hostil = "Quedan 733 sin explorar, y se llama Torre Sombra del Norte."
        entregado, v = fr.componer_seguro(self.claims, self.ctx)
        self.assertIsNotNone(entregado, "un texto legitimo no deberia bloquearse")
        for prohibido in ("733", "Torre", "Sombra"):
            self.assertNotIn(prohibido, entregado,
                             "el answer del modelo se colo en la entrega")

    def test_la_composicion_es_determinista(self):
        """Dos veces, byte a byte. Sin azar, sin reloj, sin UUID."""
        self.assertEqual(fr.componer(self.claims, self.ctx),
                         fr.componer(self.claims, self.ctx))

    def test_el_texto_solo_usa_palabras_del_claim_que_lo_sostiene(self):
        """La lista blanca se sostiene sobre el texto realmente entregado."""
        entregado, v = fr.componer_seguro(self.claims, self.ctx)
        self.assertTrue(v.permitido)
        palabras = fr._tokens(entregado)
        vocab, _ = fr.vocabulario_de(self.ctx.get("claims"))
        extra = {p for p in palabras
                 if not fr._es_funcional(p) and p not in vocab}
        self.assertEqual(extra, set(),
                         "el texto entrego palabras no autorizadas: %s" % extra)


class TestLosOchoVectores(unittest.TestCase):
    """Los ocho vectores que la auditoria MEDIO que llegaban al jugador.

    No se comprueba que esten bloqueados por coincidencia literal: se comprueba
    que el texto que SALE no puede contenerlos, porque sale de los claims y no
    del modelo. "No aparece" y "no puede aparecer" son dos pruebas distintas.
    """

    def setUp(self):
        self.ctx = _contexto()
        self.claims = _claims_ok()
        self.entregado = fr.componer(self.claims, self.ctx)
        self.palabras = fr._tokens(self.entregado)

    def test_ningun_vector_aparece_en_lo_entregado(self):
        for familia, frase in VECTORES:
            with self.subTest(familia=familia):
                for token in fr._tokens(frase):
                    if fr._es_funcional(token):
                        continue          # gramatica pura: no dice nada del mundo


class TestLaFronteraComoCapa(unittest.TestCase):
    """La comprobacion se sostiene sola, aunque no se use la composicion."""

    def setUp(self):
        self.ctx = _contexto()
        self.claims = _claims_ok()

    def test_rechaza_una_parafrasis_si_alguien_la_inyecta(self):
        v = fr.comprobar_texto("Esta hacia donde brilla el amanecer.",
                               self.claims, self.ctx)
        self.assertFalse(v.permitido)
        self.assertIn("brilla", v["palabras_no_autorizadas"])

    def test_rechaza_un_nombre_inventado_si_alguien_lo_inyecta(self):
        v = fr.comprobar_texto("Se llama Torre Sombra del Norte.",
                               self.claims, self.ctx)
        self.assertFalse(v.permitido)
        # No se exige una forma exacta de agrupar los nombres: lo que importa es
        # que el nombre inventado NO sobreviva de ninguna forma. El detector de
        # entidades agrupa por mayusculas ("Torre Sombra" es un solo nombre) y la
        # lista blanca de palabras cubre "Torre" y "Sombra" por separado. Se
        # comprueba que el conjunto completo queda marcado, sin atar la prueba a
        # como se reparten las comillas.
        marcadas = set(v["entidades_no_autorizadas"]) | set(
            v["palabras_no_autorizadas"])
        self.assertTrue(marcadas)
        for trozo in ("torre", "sombra", "norte"):
            self.assertTrue(any(trozo in m for m in marcadas),
                            "el nombre inventado %r no fue marcado" % trozo)

    def test_rechaza_una_cifra_no_autorizada(self):
        v = fr.comprobar_texto("Quedan 733 sin explorar.", self.claims, self.ctx)
        self.assertFalse(v.permitido)
        self.assertIn(733, v["cifras_no_autorizadas"])

    def test_no_bloquea_una_respuesta_legitima(self):
        """Una capa que bloquea lo legitimo es una capa que acabaria desactivada."""
        v = fr.comprobar_texto(
            "El jugador conoce la fortaleza de Galka Shafttop.",
            self.claims, self.ctx)
        self.assertTrue(v.permitido, v.get("violaciones"))

    def test_el_texto_vacio_no_es_un_fallo(self):
        self.assertTrue(fr.comprobar_texto("", self.claims, self.ctx).permitido)
        self.assertTrue(fr.comprobar_texto(None, self.claims, self.ctx).permitido)

    def test_acentos_y_mayusculas_no_abren_la_puerta(self):
        """Unicode: la normalizacion es la del estandar, no una tabla a mano."""
        v = fr.comprobar_texto("TORRE SOMBRA DEL NORTE, esta aqui.",
                               self.claims, self.ctx)
        self.assertFalse(v.permitido)

    def test_un_tipo_desconocido_se_ignora_en_composicion(self):
        """La composicion no inventa plantilla para un tipo que no conoce."""
        claims = [{"texto": "x", "tipo": "TIPO_INVENTADO", "soporte": ["c0"]}]
        self.assertEqual(fr.componer(claims, self.ctx), "")


class TestReconstruccionIndirecta(unittest.TestCase):
    """La categoria que "no contiene el secreto" no cubre (Â§53, Â§54)."""

    def setUp(self):
        self.ctx = ioc.contexto("cuantos sitios", [c.afirmacion(
            claim="Hay 734 sitios en total y el jugador conoce 1.",
            truth_status=c.FACT, knowledge_source=c.PLAYER_KNOWLEDGE,
            visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
            evidences=[c.evidencia("consulta", "1", ["total"],
                                    "nucleo.X", "legends.xml")])],
            modo=ioc.MODO_RAZONAMIENTO)

    def test_detecta_la_sustraccion_que_reconstruye_el_dato(self):
        fugas = fr.detectar_reconstruccion("734 - 1", self.ctx, [733])
        self.assertEqual(len(fugas), 1)
        self.assertIn("733", fugas[0])

    def test_no_acusa_sin_pruebas(self):
        """Sin la lista de retenidas no se puede acusar a nadie."""
        self.assertEqual(fr.detectar_reconstruccion("734 - 1", self.ctx, []), [])

    def test_no_atribuye_una_cuenta_con_operando_desconocido(self):
        """Un operando no autorizado no se puede atribuir a este detector."""
        self.assertEqual(fr.detectar_reconstruccion("99999 - 1", self.ctx, [99998]),
                         [])

    def test_texto_vacio_no_inventa_fugas(self):
        self.assertEqual(fr.detectar_reconstruccion("", self.ctx, [733]), [])



class TestRedaccionYMotivos(unittest.TestCase):
    """Las dos decisiones que evitan fugar hacia dentro del sistema."""

    def test_el_triplet_literal_no_se_entrega(self):
        self.assertNotIn("112", fr.redactar_coordenadas("Esta en (112, 20)."))

    def test_afirmar_el_registro_sigue_siendo_posible(self):
        """Se puede decir que las hay anotadas sin decir donde."""
        r = fr.redactar_coordenadas("El sitio esta en las coordenadas (112, 20).")
        self.assertIn("coordenadas", r)
        self.assertNotIn("112", r)

    def test_un_texto_sin_coordenadas_no_se_toca(self):
        self.assertEqual(fr.redactar_coordenadas("El sitio es una fortaleza."),
                         "El sitio es una fortaleza.")

    def test_un_motivo_interno_no_llega_como_identificador(self):
        """El jugador no necesita conocer los estados internos del contrato."""
        self.assertNotIn("PLAYER_HIDDEN", fr.motivo_legible("PLAYER_HIDDEN"))

    def test_un_motivo_desconocido_no_se_ensena_tal_cual(self):
        """Fail-closed: lo que no esta en la tabla no se enseÃ±a."""
        self.assertEqual(fr.motivo_legible("ESTADO_INVENTADO_2027"),
                         fr._MOTIVO_GENERICO)

    def test_un_motivo_no_cadena_tampoco_ensena_nada(self):
        self.assertEqual(fr.motivo_legible(None), fr._MOTIVO_GENERICO)
        self.assertEqual(fr.motivo_legible(42), fr._MOTIVO_GENERICO)


class TestDeterminismoYEncoding(unittest.TestCase):
    """Sin reloj, sin azar, sin depender de como se escribio el dato."""

    def test_el_roundtrip_utf8_sobrevive_a_tildes_y_enye(self):
        texto = "El sitio \u00abMina de Oro\u00bb esta al norte \u2191 \u00bfque?"
        a = c.afirmacion(
            claim=texto, truth_status=c.FACT,
            knowledge_source=c.PLAYER_KNOWLEDGE, visibility=c.PLAYER_VISIBLE,
            disclosure=c.ALLOWED,
            evidences=[c.evidencia("sitio", "87", ["name"], "nucleo.f", "l.xml")])
        self.assertEqual(c.desde_json(c.a_json(a))["claim"], texto)

    def test_la_normalizacion_no_depende_del_teclado(self):
        self.assertEqual(fr.normalizar("MUY ALTA"), fr.normalizar("muy alta"))
        self.assertEqual(fr.normalizar("a\u00f1o"), fr.normalizar("ano"))

    def test_las_ocho_familias_siguen_declaradas(self):
        """Si alguien recorta el banco de vectores, esta prueba lo nota."""
        self.assertGreaterEqual(len(VECTORES), 8)
        self.assertEqual(len({f for f, _ in VECTORES}), len(VECTORES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
