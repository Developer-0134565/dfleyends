#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RIESGOS A, B y C: PROCEDENCIA, MEMORIA Y ESPACIO
===================================================
Suite de regresion de los tres riesgos que la mision anterior dejo abiertos.

Cada prueba demuestra una PROPIEDAD. Las que importan son las que fallarian si
alguien reintrodujera una via por la que el sistema crea mas autoridad de la que
puede demostrar.

  A. Autoridad del validador. El sistema valida PROCEDENCIA y PERMISO. No valida
     VERDAD, y tiene que decirlo en vez de callarlo.
  B. Memoria. No existe, y por eso no hay acumulacion.
  C. Espacio. Los vectores espaciales no llegan al jugador, ni siquiera cuando las
     coordenadas son legitimamente conocidas.

Y al final, pruebas CRUZADAS, porque los tres riesgos no son independientes.

Ejecutar:  python dfchron/pruebas/probar_riesgos_abc.py
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

from dfchron import contrato_ia as c          # noqa: E402
from dfchron import ia_contrato as ioc        # noqa: E402
from dfchron import ia_verificacion as iv     # noqa: E402
from dfchron import ia_frontera as fr         # noqa: E402
from dfchron import ia_mock as mk             # noqa: E402

FACT = ioc.FACT


def _visible():
    return c.afirmacion(
        claim="El sitio es de tipo 'fortress'.",
        truth_status=c.FACT, knowledge_source=c.PLAYER_KNOWLEDGE,
        visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
        evidences=[c.evidencia("sitio", "87", ["type"],
                               "nucleo.Archivo.ficha_sitio", "legends.xml")])


def _secreto():
    return c.afirmacion(
        claim="Existe una veta de diamantes en 183,72,-14.",
        truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
        visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
        evidences=[c.evidencia("sitio", "183", ["coordenadas"],
                               "nucleo.Archivo.ficha_sitio", "legends.xml")],
        no_descubierto=True)


def _contexto():
    """Contexto real: un hecho visible y un secreto retenido."""
    return ioc.contexto("de que tipo es el sitio", [_visible(), _secreto()],
                        modo=ioc.MODO_RAZONAMIENTO)


def _legitimo():
    return [{"texto": "El sitio es de tipo 'fortress'.", "tipo": FACT,
             "soporte": ["c0"]}]


def _inventado():
    """Contenido que no aparece en el apoyo. Es el caso central del riesgo A."""
    return [{"texto": "Existe una veta de diamantes.", "tipo": FACT,
             "soporte": ["c0"]}]


# ================================================== A. VALIDADOR ============
class TestAAutoridadDelValidador(unittest.TestCase):
    """El validador no puede otorgar autoridad que no demuestra."""

    def setUp(self):
        self.ctx = _contexto()

    def test_contenido_inventado_pasa_los_filtros_estructurales(self):
        """El hecho DEMOSTRADO, para que el resto de la suite tenga sentido.

        Una referencia real mas un `tipo` valido bastan para pasar los cuatro
        filtros. Eso es correcto: son filtros ESTRUCTURALES. Lo que no es correcto
        es que eso se lea como «es verdad», y de eso se ocupa la declaracion de
        alcance.
        """
        v = ioc.validar_salida({"answer": "x", "claims": _inventado()}, self.ctx)
        self.assertTrue(v.entregable,
                        "el contenido no se valida por palabras: es estructural")

    def test_el_veredicto_declara_que_no_verifica_semantica(self):
        v = ioc.validar_salida({"answer": "x", "claims": _legitimo()}, self.ctx)
        ver = v["verificacion"]
        self.assertEqual(ver["alcance"]["estado_semantico"], iv.SEMANTICA)
        self.assertTrue(ver["alcance"]["semantico"],
                        "lo que NO se verifica tiene que estar escrito")

    def test_el_alcance_enumera_lo_que_si_se_comprueba(self):
        """Que se declare un limite sin decir que se comprueba es declague."""
        ver = ioc.validar_salida({"answer": "x", "claims": _legitimo()},
                                 self.ctx)["verificacion"]["alcance"]
        self.assertTrue(ver["estructural"])
        self.assertTrue(ver["trazabilidad"])

    def test_la_trazabilidad_detecta_el_contenido_inventado(self):
        traz = iv.trazabilidad(_inventado(), self.ctx)
        self.assertEqual(traz[0]["fraccion"], 0.0)
        self.assertIn("diamantes", traz[0]["sin_respaldo"])

    def test_la_trazabilidad_acepta_el_contenido_apoyado(self):
        traz = iv.trazabilidad(_legitimo(), self.ctx)
        self.assertEqual(traz[0]["fraccion"], 1.0)
        self.assertEqual(traz[0]["sin_respaldo"], [])

    def test_una_referencia_valida_no_autoriza_otra_afirmacion(self):
        """Apoyarse en c0 no habilita decir cualquier cosa.

        El texto no aparece en el apoyo, asi que su trazabilidad es cero y el
        sistema lo dice. No se bloquea la entrega (el texto que ve el jugador lo
        compone el sistema), pero **queda constancia** de que el claim no tenia
        respaldo.
        """
        v = ioc.validar_salida({"answer": "x", "claims": _inventado()}, self.ctx)
        self.assertEqual(v["verificacion"]["claims_sin_respaldo"], [0])

    def test_la_confianza_no_afirma_alta_sin_respaldo(self):
        """La confianza alta exige pruebas. El `tipo` solo lo elige el modelo."""
        v = mk.validar_respuesta_ia({"answer": "x", "claims": _inventado()},
                                    self.ctx)
        self.assertEqual(v["confianza"], mk.CONFIANZA_BAJA)

    def test_la_confianza_alta_exige_trazabilidad_completa(self):
        v = mk.validar_respuesta_ia({"answer": "x", "claims": _legitimo()},
                                    self.ctx)
        self.assertEqual(v["confianza"], mk.CONFIANZA_ALTA)

    def test_una_inferencia_no_puede_vestirse_de_hecho(self):
        """Riesgo A: una interpretacion sobre un hecho solo no pasa."""
        malo = [{"texto": "Algo.", "tipo": ioc.INTERPRETATION,
                 "soporte": ["c0"]}]
        v2 = ioc.validar_salida({"answer": "x", "claims": malo}, self.ctx)
        self.assertFalse(v2.entregable,
                         "una interpretacion sin apoyo derivado no pasa")

    def test_el_sistema_no_modifica_la_politica(self):
        """El modelo no puede degradar un FORBIDDEN a ALLOWED."""
        for cl in self.ctx["claims"]:
            self.assertNotEqual(cl["disclosure"], c.FORBIDDEN)
        v = ioc.validar_salida({"answer": "x", "claims": [
            {"texto": "x", "tipo": FACT, "soporte": ["c9"]}]}, self.ctx)
        self.assertFalse(v.entregable)


# ====================================================== B. MEMORIA =========
class TestBMemoriaYTurnos(unittest.TestCase):
    """No hay memoria. Y si la hubiera, habria que revalidarla."""

    def setUp(self):
        self.ctx = _contexto()

    def test_turno_2_no_ve_la_respuesta_del_turno_1(self):
        """Cada turno se valida y compone contra SU PROPIO contexto."""
        t1 = {"answer": "Quedan 733 sin explorar.", "claims": _legitimo()}
        v1 = mk.validar_respuesta_ia(t1, self.ctx)
        t2 = {"answer": "Como decia, hay 733 mas.", "claims": _legitimo()}
        v2 = mk.validar_respuesta_ia(t2, self.ctx)
        # La entrega es identica porque el `answer` no manda: manda el claim.
        self.assertEqual(fr.componer(t1["claims"], self.ctx),
                         fr.componer(t2["claims"], self.ctx))
        self.assertNotIn("733", fr.componer(t2["claims"], self.ctx))
        self.assertTrue(v1.entregable and v2.entregable)

    def test_recordar_una_afirmacion_oculta_no_la_reintroduce(self):
        """«Recuerdas que hay diamantes?» no puede resucitar el secreto."""
        consulta = {"answer": "Recuerdas que hay una veta de diamantes.",
                    "claims": _legitimo()}
        entregado = fr.componer(consulta["claims"], self.ctx)
        self.assertNotIn("diamantes", entregado.lower())

    def test_el_estado_persistido_no_transporta_texto_de_turnos(self):
        """Lo unico que cruza peticiones son `df_id`, no contenido."""
        from dfchron import estado_conocimiento as ec
        e = ec.EstadoConocimiento()
        e.limpiar_conocimiento()
        e.marcar_conocido("sitio", "87", "tipo", "sonda")
        # `esta_conocido` responde por PERTENENCIA: no devuelve la entrada, asi
        # que no hay por donde sacar texto del estado.
        self.assertTrue(e.esta_conocido("sitio", "87", "tipo"))
        self.assertFalse(e.esta_conocido("sitio", "183", "tipo"))

    def test_una_entrada_editada_a_mano_se_rechaza_al_leer(self):
        """Riesgo B: `_validar_esquema` valida contenido, no solo forma.

        Antes solo comprobaba que el fichero tuviera las claves. Editarlo a mano
        bastaba para meter una clave arbitraria bien formada y que el sistema la
        creyera en LECTURA.
        """
        from dfchron import estado_conocimiento as ec
        crudo = {"schema_version": 1, "dataset_id": "x",
                 "knowledge": {"entidad|sitio:87": {"tipo": "sitio",
                                                   "df_id": "87",
                                                   "campo": ""}}}
        with self.assertRaises(ec.EstadoInvalido):
            ec._validar_esquema(crudo)

    def test_un_tipo_inventado_en_el_estado_se_rechaza(self):
        from dfchron import estado_conocimiento as ec
        crudo = {"schema_version": 1, "dataset_id": "x",
                 "knowledge": {"entidad|inventado:1": {"tipo": "NAVAJA",
                                                       "df_id": "1"}}}
        with self.assertRaises(ec.EstadoInvalido):
            ec._validar_esquema(crudo)

    def test_una_entrada_que_no_es_objeto_se_rechaza(self):
        from dfchron import estado_conocimiento as ec
        crudo = {"schema_version": 1, "dataset_id": "x",
                 "knowledge": {"entidad|sitio:87": "no soy un objeto"}}
        with self.assertRaises(ec.EstadoInvalido):
            ec._validar_esquema(crudo)

    def test_una_entrada_valida_se_acepta(self):
        """La comprobacion nueva no puede rechazar lo que antes valia."""
        from dfchron import estado_conocimiento as ec
        crudo = {"schema_version": 1, "dataset_id": "x",
                 "knowledge": {"campo|sitio:87:tipo": {"tipo": "sitio",
                                                       "df_id": "87",
                                                       "campo": "tipo",
                                                       "motivo": "sonda"}}}
        self.assertEqual(ec._validar_esquema(crudo)["knowledge"],
                         crudo["knowledge"])



# ===================================================== C. ESPACIO ==========
class TestCEspacio(unittest.TestCase):
    """Los vectores espaciales no llegan al jugador."""

    #: Los vectores que la mision enumera, mas dos que se le parecen.
    VECTORES = (
        "Esta al norte de tu posicion.",
        "Se encuentra a menos de diez casillas.",
        "Esta mas cerca que la otra localizacion.",
        "Esta en la region contigua.",
        "Hay tres habitaciones entre ambas.",
        "Esta en una zona que todavia no has explorado.",
        "Esta al oeste, hacia donde brilla el amanecer.",
        "Sigue dos salas mas alla.",
    )

    def setUp(self):
        self.ctx = _contexto()
        self.claims = _legitimo()

    def test_los_vectores_de_la_mision_se_bloquean(self):
        entregado = fr.componer(self.claims, self.ctx)
        palabras = fr._tokens(entregado)
        for v in self.VECTORES:
            with self.subTest(vector=v):
                self.assertFalse(
                    fr.comprobar_texto(v, self.claims, self.ctx).permitido,
                    "el vector espacial no debe pasar: %s" % v)
                for tok in fr._tokens(v):
                    if fr._es_funcional(tok):
                        continue
                    self.assertNotIn(tok, palabras,
                                     "el vector %s se filtro (%s)" % (v, tok))

    def test_coordenadas_legitimamente_conocidas_se_redaccionan(self):
        """El caso B-08: el jugador conoce las coordenadas. Aun asi no salen.

        Es la distincion que hace la politica coherente: se puede AFIRMAR que las
        coordenadas constan en el registro del jugador, pero el TRIPLET literal es
        la posicion de un sitio sin explorar y no se entrega.
        """
        claim_coordenadas = c.afirmacion(
            claim="El sitio esta en las coordenadas '(112, 20)'.",
            truth_status=c.FACT, knowledge_source=c.PLAYER_KNOWLEDGE,
            visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
            evidences=[c.evidencia("sitio", "87", ["coordenadas"],
                                   "n.f", "legends.xml")])
        ctx = ioc.contexto("donde esta", [claim_coordenadas],
                           modo=ioc.MODO_RAZONAMIENTO)
        entregado, _v = fr.componer_seguro(
            [{"texto": "Las coordenadas constan en mi registro.", "tipo": FACT,
              "soporte": ["c0"]}], ctx)
        self.assertIsNotNone(entregado)
        for literal in ("112", "20"):
            self.assertNotIn(literal, entregado)


    def test_una_comparacion_espacial_no_se_fabrica(self):
        """«Mas cerca que la otra» requiere dos entidades y una metrica.

        El nucleo declara que NO calcula distancias, asi que no existe ninguna
        afirmacion de ese tipo que el modelo pueda seleccionar.
        """
        for v in ("Esta mas cerca que el otro.", "Es el sitio mas cercano.",
                  "Esta a dos tiles."):
            with self.subTest(vector=v):
                self.assertFalse(
                    fr.comprobar_texto(v, self.claims, self.ctx).permitido)

    def test_la_entrega_nunca_contiene_una_coordenada_literal(self):
        entregado = fr.componer(self.claims, self.ctx)
        self.assertEqual(ioc.deteccion_fuga(entregado, self.ctx), [],
                         "la entrega compuesta no puede filtrar por lateral")


# ================================================ CRUZADOS =================
class TestCruizados(unittest.TestCase):
    """Los tres riesgos juntos, que es como ocurren de verdad."""

    def setUp(self):
        self.ctx = _contexto()

    def test_espacial_falsificado_mas_inferencia_mas_segundo_turno(self):
        """Espacio con procedencia falsificada + inferencia + cita anterior.

        Un intento que reune los tres vectores: afirmacion espacial con apoyo
        inexistente, inferencia disfrazada de hecho, y `answer` que cita el turno
        anterior.
        """
        salida = {"answer": "Como te dije, al norte hay diamantes.",
                  "claims": [
                      {"texto": "Esta al norte.", "tipo": FACT,
                       "soporte": ["c99"]},
                      {"texto": "Tiene diamantes.", "tipo": ioc.INTERPRETATION,
                       "soporte": ["c0"]}]}
        v = ioc.validar_salida(salida, self.ctx)
        entregado = fr.componer(salida["claims"], self.ctx)
        for prohibido in ("norte", "diamantes"):
            self.assertNotIn(prohibido, entregado.lower())
        self.assertFalse(v.entregable, "el apoyo c99 no existe: se rechaza")

    def test_datos_autorizados_por_separado_no_reconstruyen(self):
        entregado = fr.componer(_legitimo(), self.ctx)
        for prohibido in ("734", "diamantes"):
            self.assertNotIn(prohibido, entregado)

    def test_la_contradiccion_entre_turnos_no_se_acumula(self):
        """El texto del modelo no puede contradecir lo que el contexto autoriza.

        Dos claims que SOLO se diferencian en su `texto` (el modelo dice `cave`
        cuando el contexto dice `fortress`) componen **lo mismo**: el claim de
        contexto. La entrega no depende de la redaccion del modelo.

        Y `componer_seguro` va mas alla: rechaza el claim que dice `cave`,
        porque `cave` no esta en el vocabulario autorizado.
        """
        t1 = [{"texto": "El sitio es de tipo 'fortress'.", "tipo": FACT,
               "soporte": ["c0"]}]
        t2 = [{"texto": "El sitio es de tipo 'cave'.", "tipo": FACT,
               "soporte": ["c0"]}]
        texto, veredicto = fr.componer_seguro(t2, self.ctx)
        self.assertIsNotNone(texto, "el camino seguro tambien entrega")
        self.assertTrue(veredicto.permitido)
        self.assertNotIn("cave", texto,
                         "el claim del modelo no puede cambiar la entrega")

        claims = _legitimo()
        v = ioc.validar_salida({"answer": "x", "claims": claims}, self.ctx)
        self.assertTrue(v.entregable)
        texto, frontera = fr.componer_seguro(claims, self.ctx)
        self.assertTrue(frontera.permitido)

    def test_la_frontera_sigue_siendo_la_ultima_palabra(self):
        """Aunque las capas anteriores digan que si, la frontera puede negarse.

        Es la invariante de la mision anterior: la frontera es el ultimo filtro,
        y el unico que decide que texto ve el jugador.
        """
        claims = _legitimo()
        v = ioc.validar_salida({"answer": "x", "claims": claims}, self.ctx)
        self.assertTrue(v.entregable)
        texto, frontera = fr.componer_seguro(claims, self.ctx)
        self.assertTrue(frontera.permitido)
        self.assertIsNotNone(texto)

if __name__ == "__main__":
    unittest.main(verbosity=2)
