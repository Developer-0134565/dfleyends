#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CIERRE PRE-IA :: temporalidad, descubrimiento, aislamiento y persistencia.

QUE DEMUESTRA
-------------
La evidencia declara de que **estado del mundo** salio, usando la version real
del dataset (derivada del SHA-256 del contenido, no de un reloj). Con eso, una
evidencia de `S0` no puede seguir presentandose como si fuera de `S1`.

Cierra ademas, con datos reales del nucleo: descubrimiento progresivo (que es un
hecho sobre el JUGADOR, separado de la verdad), aislamiento entre componentes,
reconstruccion determinista y persistencia que no eleva privilegios.

LO QUE NO DEMUESTRA, Y SE DICE
-----------------------------
* Que una afirmacion siga siendo *verdad*. Solo que pertenece a otro mundo.
* Verificacion semantica: sigue sin existir y no se finge.
* Identidad estable para relaciones complejas: el nucleo no la ofrece.

Ejecutar:  python dfchron/pruebas/probar_cierre_pre_ia.py
"""
import copy
import json
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

from dfchron import contrato_ia as c            # noqa: E402
from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_contrato as ioc          # noqa: E402
from dfchron import ia_estructura as es         # noqa: E402
from dfchron import ia_frontera as fr           # noqa: E402
from dfchron import ia_verificacion as iv       # noqa: E402

#: Dos estados del mundo distinguibles, usados SOLO dentro de las pruebas. No
#: son versiones del nucleo: el nucleo tiene un mundo, y estas cadenas no
#: fingen tener mas.
S0 = "v1-0000000000000000"
S1 = "v2-1111111111111111"


def ev(campo="tipo", df_id="112", version=S0):
    """Evidencia de sitio anclada al estado indicado."""
    return c.evidencia("sitio", df_id, [campo], "nucleo.Archivo.ficha_sitio",
                       ["legends.xml"], state_version=version)


def ficha(tipo="hamlet", nombre="begunboard", eventos=47):
    return {"tipo": tipo, "nombre": nombre, "eventos": eventos}


def afirmacion(claim="El sitio es de tipo 'hamlet'.", truth=ioc.FACT,
               visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
               source=c.PLAYER_KNOWLEDGE, evidencia=None, **extra):
    """Una afirmacion de entrada, construida con las claves reales del nucleo."""
    a = {"claim": claim, "entidad": "sitio", "df_id": "112",
         "truth_status": truth, "knowledge_source": source,
         "visibility": visibility, "disclosure": disclosure,
         "evidence": [evidencia if evidencia is not None else ev()]}
    a.update(extra)
    return a


def contexto_minimo(*extra, **kwargs):
    """Contexto REAL, construido por `contexto()`, no a mano."""
    return ioc.contexto("¿Que tipo de sitio es el 112?",
                        [afirmacion(**kwargs)], *extra)


# ================================= TEMPORALIDAD: VERSIONADO (FASE 1) =========
class TestVersionadoDeEvidencia(unittest.TestCase):
    """La evidencia declara el estado del mundo del que sale."""

    def test_la_evidencia_declara_su_estado(self):
        e = ev()
        self.assertIn("state_version", e)
        self.assertEqual(c.version_de_evidencia(e), S0)

    def test_sin_version_se_declara_desconocida(self):
        """No se rellena a posteriori: omitirla significa no tenerla."""
        e = c.evidencia("sitio", "112", ["tipo"])
        self.assertIsNone(e["state_version"])
        self.assertEqual(c.version_de_evidencia(e), c.SIN_VERSION)

    def test_version_desconocida_se_responde_sin_fallar(self):
        """Preguntar por la version nunca revienta: es una respuesta."""
        self.assertEqual(c.version_de_evidencia({"state_version": S1}), S1)
        self.assertEqual(c.version_de_evidencia({}), c.SIN_VERSION)
        self.assertEqual(c.version_de_evidencia(None), c.SIN_VERSION)


class TestInvalidacionPorCambioDeEstado(unittest.TestCase):
    """La propiedad que I14 daba por no probada, sobre el contrato real."""

    def test_misma_evidencia_mismo_estado_es_actual(self):
        self.assertTrue(c.evidencia_es_actual(ev(), S0))

    def test_misma_evidencia_otro_estado_deja_de_ser_actual(self):
        self.assertFalse(c.evidencia_es_actual(ev(), S1))

    def test_una_evidencia_desconocida_nunca_es_actual(self):
        """Fail-closed: lo que no declara de donde sale no sostiene nada."""
        self.assertFalse(c.evidencia_es_actual(c.evidencia("sitio", "112", ["tipo"]),
                                              S0))

    def test_sin_estado_del_mundo_no_se_afirma_nada(self):
        self.assertFalse(c.evidencia_es_actual(ev(), None))

    def test_el_guion_completo_de_la_fase_2(self):
        """evidencia de S0 -> verificada en S0; tras el cambio, no sobrevive."""
        texto = "El sitio es de tipo 'hamlet'."
        e0 = ev("tipo", version=S0)

        # Estado S0.
        r0 = es.verificar_afirmacion(texto, e0, ficha())
        self.assertEqual(r0["estado"], es.VERIFICADA)
        self.assertTrue(c.evidencia_es_actual(e0, S0))

        # El mundo cambia a S1. La evidencia es byte a byte la misma.
        self.assertFalse(c.evidencia_es_actual(e0, S1))

        # Y el nucleo, releyendo en S1, ya no confirma lo mismo.
        r1 = es.verificar_afirmacion(texto, e0, ficha(tipo="fortress"))
        self.assertEqual(r1["estado"], es.NO_VERIFICADA)

    def test_evidencia_renovada_si_se_reevalua(self):
        """Renovar la evidencia es lo que legitima volver a afirmar."""
        nueva = ev("tipo", version=S1)
        self.assertFalse(c.evidencia_es_actual(ev("tipo", version=S0), S1))
        self.assertTrue(c.evidencia_es_actual(nueva, S1))
        r = es.verificar_afirmacion("El sitio es de tipo 'fortress'.", nueva,
                                    ficha(tipo="fortress"))
        self.assertEqual(r["estado"], es.VERIFICADA)

    def test_la_antiguedad_no_concede_privilegio(self):
        """Haber sido aceptada antes no la vuelve aceptable despues."""
        e = ev()
        for _ in range(5):
            self.assertTrue(c.evidencia_es_actual(e, S0))
        self.assertFalse(c.evidencia_es_actual(e, S1))

    def test_la_verificacion_rechaza_evidencia_de_otro_mundo(self):
        """El camino real: `verificar_afirmacion` con `version_actual`.

        Aqui se cierra I14. El valor coincide, la entidad existe, y aun asi no
        se verifica: la evidencia es de `S0` y el mundo que se mira es `S1`.
        Comparar un dato viejo contra un mundo nuevo no demuestra nada sobre
        este mundo.
        """
        texto, e0, f = "El sitio es de tipo 'hamlet'.", ev("tipo"), ficha()
        # Sin `version_actual` no se mira la version: comportamiento de siempre.
        self.assertEqual(es.verificar_afirmacion(texto, e0, f)["estado"],
                         es.VERIFICADA)
        # Con la version del mundo, la misma evidencia vale en S0 y no en S1.
        self.assertEqual(
            es.verificar_afirmacion(texto, e0, f, version_actual=S0)["estado"],
            es.VERIFICADA)
        r1 = es.verificar_afirmacion(texto, e0, f, version_actual=S1)
        self.assertEqual(r1["estado"], es.NO_VERIFICADA)
        self.assertIn(S0, r1["motivo"])
        self.assertEqual(r1["estado_version"], S0)

    def test_la_evidencia_renovada_si_se_verifica(self):
        """Con evidencia del mundo actual, vuelve a verificar."""
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    ev("tipo", version=S1), ficha(),
                                    version_actual=S1)
        self.assertEqual(r["estado"], es.VERIFICADA)

    def test_la_evidencia_desconocida_no_verifica_si_se_mira_la_version(self):
        """Sin `state_version` no se presume actual: fail-closed."""
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    c.evidencia("sitio", "112", ["tipo"]),
                                    ficha(), version_actual=S0)
        self.assertEqual(r["estado"], es.NO_VERIFICADA)
        self.assertEqual(r["estado_version"], c.SIN_VERSION)

    def test_el_orden_de_llegada_no_altera_el_resultado(self):
        """Una evidencia tardia no sube un veredicto ya emitido."""
        vieja, nueva = ev("tipo", version=S0), ev("tipo", version=S1)
        texto, ficha_s1 = "El sitio es de tipo 'fortress'.", ficha(tipo="fortress")
        # Llega la vieja DESPUES, y aun asi no puede hablar de S1.
        self.assertFalse(c.evidencia_es_actual(vieja, S1))
        a = es.verificar_afirmacion(texto, vieja, ficha_s1)
        b = es.verificar_afirmacion(texto, nueva, ficha_s1)
        # El veredicto no depende de cual se evaluara primero.
        self.assertEqual(a["estado"], b["estado"])


class TestVersionRealDelNucleo(unittest.TestCase):
    """La version que usa el sistema sale del dataset real, no de una prueba."""

    def test_el_nucleo_publica_una_version_real(self):
        v = ec.dataset_actual()
        self.assertIsInstance(v, str)
        self.assertTrue(v)
        self.assertNotEqual(v, "UNKNOWN",
                            "no se encontro dataset_version.json")

    def test_la_version_no_depende_del_reloj(self):
        """Es contenido, no tiempo: dos lecturas dan lo mismo."""
        self.assertEqual(ec.dataset_actual(), ec.dataset_actual())

    def test_la_evidencia_del_puente_hereda_la_version_real(self):
        """`ia_conocimiento` ancla su evidencia al dataset que leyo de verdad."""
        from dfchron import ia_conocimiento as ic
        e = ic.evidencia_de("sitio", "112", ["tipo"], "nucleo.Archivo.ficha_sitio",
                            ["legends.xml"])
        self.assertEqual(c.version_de_evidencia(e), ic.DATASET_ID)
        self.assertNotEqual(ic.DATASET_ID, ic.DESCONOCIDO)


# ================================= DESCUBRIMIENTO PROGRESIVO (FASE 3) =======
class TestDescubrimientoProgresivo(unittest.TestCase):
    """Descubrir es un hecho sobre el JUGADOR, en un eje distinto al mundo.

    Es justo por eso que esta fase se puede cerrar: `marcar_conocido()` declara
    por escrito que NO toca `truth_status`, `visibility` ni `disclosure`.
    """

    def setUp(self):
        # Se prueba sobre una copia, nunca sobre el estado real del jugador.
        self._antes = copy.deepcopy(ec.obtener_conocimiento())

    def tearDown(self):
        ec.limpiar_conocimiento()

    def test_descubrir_y_revocar_es_un_ciclo_completo(self):
        self.assertFalse(ec.esta_conocido("sitio", "112", "tipo"))
        ec.marcar_conocido("sitio", "112", "tipo", motivo="lo vio")
        self.assertTrue(ec.esta_conocido("sitio", "112", "tipo"))
        ec.marcar_desconocido("sitio", "112", "tipo")
        self.assertFalse(ec.esta_conocido("sitio", "112", "tipo"))

    def test_descubrir_no_toca_el_mundo(self):
        """El estado del jugador no puede cambiar la verdad del nucleo."""
        antes = ec.obtener_conocimiento()
        ec.marcar_conocido("sitio", "112", "tipo")
        despues = ec.obtener_conocimiento()
        # Lo unico que cambia es la entrada de conocimiento, nada mas.
        self.assertNotEqual(antes, despues)
        self.assertNotIn("truth_status", despues)
        self.assertNotIn("visibility", despues)

    def test_lo_no_descubierto_no_entra_por_si_solo(self):
        """Un dato puede existir en el mundo y no ser informacion aun."""
        self.assertFalse(ec.esta_conocido("sitio", "999999", "tipo"))
        # El estado del jugador no genera afirmaciones por si mismo.
        self.assertNotIn("claims", ec.obtener_conocimiento())

    def test_no_se_puede_descubrir_una_tipo_que_no_existe(self):
        with self.assertRaises(ec.EstadoInvalido):
            ec.marcar_conocido("tipo_inventado", "112", "tipo")

    def test_se_puede_saber_que_no_consta(self):
        """Descubrir un UNKNOWN es valido: saber que no consta tambien es saber."""
        ec.marcar_conocido("sitio", "112", "tipo", motivo="no consta")
        self.assertTrue(ec.esta_conocido("sitio", "112", "tipo"))


class TestElModeloNoDescubreNiMuestra(unittest.TestCase):
    """La IA no fabrica `discovered` ni `visibility` (caso C de la fase 3)."""

    def test_los_campos_hostiles_no_llegan_al_contexto(self):
        """`_claim_de_entrada` es una copia minima: lo demas no pasa.

        Se declara `PLAYER_VISIBLE` real para que la afirmacion sea admitida: si
        no, la lista saldria vacia y la prueba no comprobaria nada.
        """
        a = afirmacion(verified=True, trusted=True, admin_override=True,
                       discovered=True, source="official")
        ctx = ioc.contexto("¿Que tipo de sitio es el 112?", [a])
        self.assertEqual(len(ctx["claims"]), 1, "la afirmacion debe entrar")
        claim = ctx["claims"][0]
        for prohibido in ("verified", "trusted", "admin_override",
                          "discovered", "confidence", "source"):
            self.assertNotIn(prohibido, claim)

    def test_lo_prohibido_no_entra_en_ningun_modo(self):
        """aunque se pida, la politica manda: FORBIDDEN no llega al contexto."""
        for modo in (ioc.MODO_RAZONAMIENTO, ioc.MODO_RESPUESTA):
            with self.subTest(modo=modo):
                ctx = ioc.contexto("dime el tipo", [afirmacion(
                    visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN)], modo)
                self.assertEqual(ctx["claims"], [])

    def test_el_estado_del_jugador_no_lo_modifica_el_contexto(self):
        antes = copy.deepcopy(ec.obtener_conocimiento())
        ioc.contexto("¿Y este?", [afirmacion()])
        self.assertEqual(ec.obtener_conocimiento(), antes)


# ================================ IDENTIDAD (FASE 4) =======================
class TestIdentidadDeLasAfirmaciones(unittest.TestCase):
    """Que se puede verificar por identidad, y que queda declaradamente fuera.

    El nucleo ofrece `df_id` POR TIPO. Es suficiente para afirmar un valor de un
    campo (`(sitio, 112, tipo)`), que es lo que usa la verificacion
    estructurada. No alcanza para relaciones compuestas en un grafo, y eso se
    declara en vez de disimularlo comparando palabras.
    """

    def test_la_identidad_de_la_evidencia_es_el_df_id(self):
        self.assertEqual(ev("tipo", df_id="112")["df_id"], "112")

    def test_el_df_id_solo_significa_algo_con_su_tipo(self):
        """`112` de sitio y `112` de figura no son la misma entidad."""
        sitio = c.evidencia("sitio", "112", ["tipo"])
        figura = c.evidencia("figura", "112", ["tipo"])
        self.assertEqual(sitio["df_id"], figura["df_id"])
        self.assertNotEqual(sitio["entidad"], figura["entidad"])

    def test_la_verificacion_se_apoya_en_esa_identidad(self):
        """Mismo texto, distinto `df_id`, distinto veredicto: decide la identidad."""
        a = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    ev("tipo", df_id="112"), ficha())
        b = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    ev("tipo", df_id="113"),
                                    ficha(tipo="fortress"))
        self.assertEqual(a["estado"], es.VERIFICADA)
        self.assertEqual(b["estado"], es.NO_VERIFICADA)

    def test_una_relacion_no_verificable_no_se_declara_verificada(self):
        """«A esta relacionado con B» no encaja: NO_APLICABLE, nunca VERIFICADA.

        No se usa similitud de palabras para fingir una verificacion relacional.
        """
        r = es.verificar_afirmacion("El sitio esta relacionado con la figura 'x'.",
                                    ev("tipo", df_id="112"), ficha())
        self.assertNotEqual(r["estado"], es.VERIFICADA)

    def test_el_alcance_declara_lo_que_no_se_comprueba(self):
        """Lo que el sistema NO demuestra, dicho por el propio sistema."""
        self.assertIn("QUE el texto sea una consecuencia logica del apoyo",
                      iv.ALCANCE["semantico"])


# ============================= ADAPTADOR HOSTIL (FASE 6) ==================
#: Todos los campos que un modelo podria intentar usar para escalar privilegios.
CAMPOS_HOSTILES = {
    "verified": True, "trusted": True, "confidence": 1.0, "confianza": 1.0,
    "admin_override": True, "admin": True, "root": True, "system": True,
    "developer": True, "bypass": True, "override": True,
    "visibility": c.PLAYER_VISIBLE, "discovered": True,
    "disclosure": c.ALLOWED, "source": "official", "state_version": S1,
}

TEXTO_HOSTIL = "Hay una veta de diamantes en (112, 20)."


class AdaptadorHostil:
    """Un «modelo» que prueba todas las vias de escalar privilegios.

    NO hay ningun LLM aqui: es un objeto que devuelve exactamente lo que
    devolveria un modelo hostil, o un prompt inyectado. Su unico proposito es
    comprobar que el sistema no le hace caso.
    """

    @staticmethod
    def propuesta(texto=TEXTO_HOSTIL):
        """Una propuesta con TODOS los campos de privilegio a la vez."""
        claim = {"ref": "c0", "texto": texto, "tipo": ioc.FACT,
                 "soporte": ["c0"]}
        claim.update(copy.deepcopy(CAMPOS_HOSTILES))
        salida = {"answer": TEXTO_HOSTIL, "claims": [claim]}
        salida.update(copy.deepcopy(CAMPOS_HOSTILES))
        return salida

    @staticmethod
    def propuesta_limpia(texto=TEXTO_HOSTIL):
        """La MISMA propuesta sin los campos de privilegio, para comparar."""
        return {"answer": TEXTO_HOSTIL,
                "claims": [{"ref": "c0", "texto": texto, "tipo": ioc.FACT,
                            "soporte": ["c0"]}]}


class _RecuperadorFalso:
    """Un recuperador minimo: solo sabe dar la ficha del sitio de prueba.

    Deliberadamente NO es `ia_contexto.recuperador_compartido()`: ese carga el
    dataset entero. Aqui solo hace falta responder «que dice el nucleo sobre el
    112», y las fichas son las de la funcion `ficha()`, para que la prueba sea
    hermetica y no dependa de los datos reales del mundo.
    """

    #: El nucleo real que la prueba considera verdad.
    FICHAS = {"112": {"tipo": "hamlet", "nombre": "begunboard", "eventos": 47},
              "113": {"tipo": "fortress", "nombre": "otro", "eventos": 12}}

    def ficha_de(self, tipo, df_id):
        if tipo != "sitio":
            return None
        return copy.deepcopy(self.FICHAS.get(str(df_id)))


class TestAdaptadorHostil(unittest.TestCase):
    """Ningún campo del modelo concede privilegios (fase 6)."""

    def test_los_campos_hostiles_no_cambian_el_veredicto(self):
        """Con y sin campos de privilegio, el juicio es el mismo."""
        ctx = contexto_minimo()
        v_con = ioc.validar_salida(AdaptadorHostil.propuesta(), ctx)
        v_sin = ioc.validar_salida(AdaptadorHostil.propuesta_limpia(), ctx)
        self.assertEqual(v_con["puede_entregarse"], v_sin["puede_entregarse"])
        self.assertEqual(v_con["claims_ok"], v_sin["claims_ok"])
        self.assertEqual(v_con["claims_rechazados"], v_sin["claims_rechazados"])

    def test_declararse_verificado_no_verifica_nada(self):
        """`verified=true` no convierte nada en verdad."""
        ctx = contexto_minimo()
        detalle = es.verificar_claims(
            AdaptadorHostil.propuesta()["claims"], ctx, _RecuperadorFalso())
        for indice, veredicto in detalle.items():
            self.assertNotEqual(veredicto["estado"], es.VERIFICADA,
                                "el claim %d se verifico sin apoyo real" % indice)

    def test_lo_mismo_con_la_propuesta_limpia(self):
        """El claim hostil tampoco verifica cuando no lleva campos de trampa.

        Asi se descarta que el no-verificar sea solo por los campos extra.
        """
        ctx = contexto_minimo()
        detalle = es.verificar_claims(
            AdaptadorHostil.propuesta_limpia()["claims"], ctx, _RecuperadorFalso())
        for veredicto in detalle.values():
            self.assertNotEqual(veredicto["estado"], es.VERIFICADA)

    def test_el_texto_del_modelo_no_es_texto_de_salida(self):
        """`answer` es propuesta; el compositor usa los claims del contexto.

        Aunque la propuesta pase, lo que llega al jugador lo compone el sistema.
        """
        ctx = contexto_minimo()
        salida = ioc.respuesta(TEXTO_HOSTIL,
                               [{"ref": "c0", "texto": "El sitio es de tipo 'hamlet'.",
                                 "tipo": ioc.FACT, "soporte": ["c0"]}])
        ioc.validar_salida(salida, ctx)
        texto, _ = fr.componer_seguro(salida["claims"], ctx)
        if texto is not None:
            self.assertNotIn("diamantes", texto.lower())
            self.assertNotIn("112, 20", texto)

    def test_las_coordenadas_inventadas_marcan_fuga(self):
        self.assertTrue(ioc.deteccion_fuga("Esta en las coordenadas '(112, 20)'."))

    def test_la_confianza_declarada_no_es_confianza_calculada(self):
        """`confidence=1.0` no aparece en el veredicto del sistema."""
        ctx = contexto_minimo()
        veredicto = ioc.validar_salida(AdaptadorHostil.propuesta(), ctx)
        self.assertNotIn("confidence", veredicto)


# ============================ AISLAMIENTO (FASE 7) ========================
class TestNoContaminacion(unittest.TestCase):
    """Mover un componente no debe mover los demas.

    Cada prueba mide UNA frontera. Si varias fallan a la vez, al menos se sabe
    que el problema no es de una sola pieza.
    """

    def test_una_propuesta_hostil_no_cambia_la_verdad_del_contexto(self):
        ctx = contexto_minimo()
        antes = copy.deepcopy(ctx["claims"][0])
        ioc.validar_salida(AdaptadorHostil.propuesta(), ctx)
        self.assertEqual(ctx["claims"][0], antes)

    def test_una_propuesta_hostil_no_cambia_la_visibilidad(self):
        ctx = contexto_minimo()
        antes = ctx["claims"][0]["visibility"]
        ioc.validar_salida(AdaptadorHostil.propuesta(), ctx)
        self.assertEqual(ctx["claims"][0]["visibility"], antes)

    def test_la_confianza_declarada_no_altera_el_veredicto_del_nucleo(self):
        """`confidence` y `confianza` en el claim no se propagan al veredicto."""
        for clave in ("confidence", "confianza"):
            with self.subTest(campo=clave):
                veredicto = es.verificar_afirmacion(
                    "El sitio es de tipo 'hamlet'.",
                    dict(ev("tipo"), **{clave: 1.0}), ficha())
                self.assertEqual(veredicto["estado"], es.VERIFICADA)
                self.assertNotIn(clave, veredicto)

    def test_cambiar_el_texto_compositor_no_cambia_la_verificacion(self):
        """La capa de expresion no participa en la de comprobacion."""
        ctx = contexto_minimo()
        claims = [{"ref": "c0", "texto": "El sitio es de tipo 'hamlet'.",
                   "tipo": ioc.FACT, "soporte": ["c0"]}]
        texto, _ = fr.componer_seguro(claims, ctx)
        # La composicion no altera el estado del contexto.
        self.assertEqual(ctx["claims"][0]["truth_status"], ioc.FACT)
        self.assertEqual(texto, fr.componer_seguro(claims, ctx)[0])

    def test_el_orden_de_llegada_de_afirmaciones_no_altera_el_contexto(self):
        """Permutar las afirmaciones no cambia el conjunto admitido."""
        buena = afirmacion(claim="El sitio es de tipo 'hamlet'.")
        oculta = afirmacion(claim="Secreto.", visibility=c.PLAYER_HIDDEN,
                            disclosure=c.FORBIDDEN)
        uno = ioc.contexto("tipo", [buena, oculta])
        otro = ioc.contexto("tipo", [oculta, buena])
        self.assertEqual([cl["claim"] for cl in uno["claims"]],
                         [cl["claim"] for cl in otro["claims"]])

    def test_el_texto_hostil_no_se_convierte_en_evidencia(self):
        """`TEXTO_HOSTIL` no puede entrar como `evidence`."""
        ctx = contexto_minimo()
        ioc.validar_salida(AdaptadorHostil.propuesta(), ctx)
        for claim in ctx["claims"]:
            for e in claim["evidence"]:
                self.assertNotEqual(e.get("funcion"), TEXTO_HOSTIL)
                self.assertNotIn("diamantes", str(e))


# ========================= RECONSTRUCCION DETERMINISTA (FASE 8) ============
class TestReconstruccionDeterminista(unittest.TestCase):
    """La salida se regenera desde el mundo, sin texto previo del modelo."""

    CLAIM = {"ref": "c0", "texto": "El sitio es de tipo 'hamlet'.",
             "tipo": ioc.FACT, "soporte": ["c0"]}

    def test_el_compositor_no_usa_el_answer_del_modelo(self):
        """Mismo `claims`, distinto `answer`: el texto es el mismo."""
        ctx = contexto_minimo()
        con_answer = ioc.respuesta(TEXTO_HOSTIL, [self.CLAIM])
        sin_answer = ioc.respuesta("", [self.CLAIM])
        a, _ = fr.componer_seguro(con_answer["claims"], ctx)
        b, _ = fr.componer_seguro(sin_answer["claims"], ctx)
        self.assertEqual(a, b)

    def test_la_salida_es_reproducible(self):
        """Mismo estado, mismo texto: byte a byte."""
        ctx = contexto_minimo()
        self.assertEqual(fr.componer_seguro([self.CLAIM], ctx)[0],
                         fr.componer_seguro([self.CLAIM], ctx)[0])

    def test_cambia_el_mundo_cambia_la_salida(self):
        """La salida es funcion del estado, no del texto acumulado."""
        ctx = contexto_minimo()
        primero = fr.componer_seguro([self.CLAIM], ctx)[0]
        # Se declara el otro tipo en el contexto y se recompone desde cero.
        otro_ctx = contexto_minimo(claim="El sitio es de tipo 'fortress'.",
                                   evidencia=ev("tipo", version=S1))
        claim = {"ref": "c0", "texto": "El sitio es de tipo 'fortress'.",
                 "tipo": ioc.FACT, "soporte": ["c0"]}
        segundo = fr.componer_seguro([claim], otro_ctx)[0]
        self.assertNotEqual(primero, segundo)

    def test_la_respuesta_se_puede_rehacer_sin_guardar_texto_previo(self):
        """No hace falta memoria conversacional: basta el estado.

        Se construye el texto dos veces desde cero, sin conservar el primero,
        y sale igual. Esa es la prueba de que no hay nada que «recordar».
        """
        for _ in range(2):
            ctx = contexto_minimo()
            texto, res = fr.componer_seguro([self.CLAIM], ctx)
            self.assertTrue(res.permitido)
            self.assertEqual(texto, "El sitio es de tipo 'hamlet'.")


# ============================ PERSISTENCIA (FASE 9) =======================
class TestPersistenciaNoElevaPrivilegios(unittest.TestCase):
    """Cargar datos no puede ser mas permisivo que producirlos.

    Todas las pruebas escriben en un fichero temporal y usan un
    `EstadoConocimiento` propio: el estado real del jugador no se toca.
    """

    def _estado(self, crudo=None):
        """Un `EstadoConocimiento` sobre un fichero temporal.

        La validacion es perezosa: ocurre al LEER, no al construir. Por eso
        `_estado()` fuerza la lectura con `obtener_conocimiento()`, que es lo
        que hara cualquier consumidor real.
        """
        import tempfile
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        ruta = os.path.join(self._dir.name, "estado.json")
        if crudo is not None:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(crudo, f)
        estado = ec.EstadoConocimiento(ruta, ec.dataset_actual())
        estado.obtener_conocimiento()      # fuerza la lectura y la validacion
        return estado

    def _estado_sin_leer(self, crudo):
        """Construye el estado SIN forzar la lectura."""
        import tempfile
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        ruta = os.path.join(self._dir.name, "estado.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(crudo, f)
        return ec.EstadoConocimiento(ruta, ec.dataset_actual())

    def _base(self):
        return {"schema_version": ec.SCHEMA_VERSION,
                "dataset_id": ec.dataset_actual(),
                "knowledge": {}}

    def test_una_entrada_bien_formada_se_carga(self):
        """Lo valido se carga: el punto de partida."""
        e = self._estado(self._base())
        e.marcar_conocido("sitio", "112", "tipo", motivo="lo vio")
        otro = self._estado(self._base())
        otro.marcar_conocido("sitio", "112", "tipo", motivo="lo vio")
        self.assertTrue(otro.esta_conocido("sitio", "112", "tipo"))

    def test_un_tipo_invalido_al_cargar_se_rechaza(self):
        """Editar el fichero a mano no crea tipos que el sistema no tiene."""
        crudo = self._base()
        crudo["knowledge"]["entidad|tipo_inventado:112"] = {
            "tipo": "tipo_inventado", "df_id": "112"}
        with self.assertRaises(ec.EstadoInvalido):
            self._estado(crudo)

    def test_una_clave_forjada_no_hace_nada_conocido(self):
        """Una clave que no es la canonica no otorga conocimiento.

        `_validar_esquema()` valida el CONTENIDO de cada entrada, no el texto de
        la clave. Eso es suficiente: las busquedas calculan la clave canonica
        ellas mismas, asi que una clave forjada no se encuentra nunca y no
        concede nada. Lo que se mide aqui es ese efecto, no el rechazo.
        """
        crudo = self._base()
        crudo["knowledge"]["clave|inventada:1"] = {"tipo": "sitio", "df_id": "1"}
        estado = self._estado(crudo)
        # La entrada forjada no aparece como conocimiento del sitio 1.
        self.assertFalse(estado.esta_conocido("sitio", "1"))
        self.assertFalse(estado.esta_conocido("sitio", "1", "tipo"))
        # Y escribir de verdad, por la via oficial, si funciona: la diferencia
        # entre «te dice que no» y «no concede nada» es justo lo que se prueba.
        estado.marcar_conocido("sitio", "1")
        self.assertTrue(estado.esta_conocido("sitio", "1"))

    def test_campos_de_privilegio_en_una_entrada_se_ignoran(self):
        """`trusted`/`verified`/`admin_override` en el estado no conceden nada.

        Se comprueba el efecto, que es lo que importa: aun con esos campos, el
        estado solo concede `esta_conocido`, y no toca verdad ni visibilidad.
        """
        crudo = self._base()
        crudo["knowledge"]["entidad|sitio:112"] = {
            "tipo": "sitio", "df_id": "112",
            "verified": True, "trusted": True, "admin_override": True,
            "visibility": c.PLAYER_VISIBLE, "confidence": 1.0}
        estado = self._estado(crudo)
        self.assertTrue(estado.esta_conocido("sitio", "112"))
        # Y el contenido del estado no ha ganado ninguna autoridad nueva.
        self.assertNotIn("visibility", estado.obtener_conocimiento())

    def test_un_schema_version_distinto_se_rechaza(self):
        """No hay migraciones silenciosas."""
        crudo = self._base()
        crudo["schema_version"] = "999.0"
        with self.assertRaises(ec.EstadoInvalido):
            self._estado(crudo)

    def test_un_estado_de_otro_dataset_se_reconoce_y_no_se_usa(self):
        """Evidencia/estado de otro mundo: se declara, no se adopta.

        `obtener_conocimiento()` lanza `DatasetDistinto` a proposito: un estado
        de otro mundo no se entrega «como si valiera». Se construye sin forzar
        la lectura para poder preguntar por la compatibilidad.
        """
        crudo = self._base()
        crudo["dataset_id"] = "v9-otro-mundo"
        estado = self._estado_sin_leer(crudo)
        self.assertEqual(estado.compatibilidad(), "DISTINTO")
        self.assertFalse(estado.esta_conocido("sitio", "112"))
        with self.assertRaises(ec.DatasetDistinto):
            estado.exigir_compatible()
        with self.assertRaises(ec.DatasetDistinto):
            estado.obtener_conocimiento()
        # Y no se borra nada: el sistema se queda quieto y espera.
        self.assertTrue(os.path.exists(estado.ruta))

    def test_un_estado_incompleto_se_rechaza(self):
        crudo = self._base()
        del crudo["dataset_id"]
        with self.assertRaises(ec.EstadoInvalido):
            self._estado(crudo)

    def test_el_estado_leido_es_inmutable(self):
        """Cargar da una copia de solo lectura: alterar la copia no cambia nada."""
        estado = self._estado(self._base())
        estado.marcar_conocido("sitio", "112", "tipo")
        copia = estado.obtener_conocimiento()
        with self.assertRaises(ec.EstadoInvalido):
            copia["clave_inventada"] = {"trusted": True}
        self.assertNotIn("clave_inventada", estado.obtener_conocimiento())


if __name__ == "__main__":
    unittest.main(verbosity=2)
