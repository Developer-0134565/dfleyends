#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REGRESION DE LA VERIFICACION ESTRUCTURADA. Lo que se demuestra y lo que no."""
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
from dfchron import ia_estructura as es       # noqa: E402
from dfchron import ia_verificacion as iv     # noqa: E402

FACT = ioc.FACT


def _ev_sitio(campo="tipo", df_id="112"):
    return {"entidad": "sitio", "df_id": df_id,
            "datos_utilizados": [campo],
            "funcion": "nucleo.Archivo.ficha_sitio",
            "fuente": ["legends.xml", "legends_plus.xml"]}


def _ficha(tipo="hamlet", nombre="begunboard", eventos=47):
    return {"tipo": tipo, "nombre": nombre, "eventos": eventos}


class TestVerificacionPositiva(unittest.TestCase):
    """Lo que el nucleo CONFIRMA. Solo esto es `VERIFICADA`."""

    def test_valor_correcto_se_verifica(self):
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev_sitio("tipo"), _ficha())
        self.assertEqual(r["estado"], es.VERIFICADA)
        self.assertTrue(r["comprobado"])
        self.assertEqual(r["esperado"], "hamlet")
        self.assertEqual(r["obtenido"], "hamlet")

    def test_cada_campo_declarado_se_verifica(self):
        for campo, texto, valor in (
                ("tipo", "El sitio es de tipo 'hamlet'.", "hamlet"),
                ("nombre", "El sitio se llama 'begunboard'.", "begunboard"),
                ("eventos", "El sitio tiene '47' eventos registrados.", "47")):
            with self.subTest(campo=campo):
                r = es.verificar_afirmacion(texto, _ev_sitio(campo), _ficha())
                self.assertEqual(r["estado"], es.VERIFICADA)
                self.assertEqual(r["obtenido"], valor)

    def test_el_estado_declara_que_significa(self):
        """Un estado sin explicación puede leerse como mas de lo que es."""
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev_sitio("tipo"), _ficha())
        self.assertIn("nucleo", r["significado"])
        self.assertIn("no dice nada mas", es.SIGNIFICADO[es.VERIFICADA])


class TestDeteccionDeFabricacion(unittest.TestCase):
    """El caso que `trazabilidad` NO puede ver."""

    def test_valor_inventado_se_detecta(self):
        """Misma referencia real, valor distinto. El nucleo lo desmiente."""
        r = es.verificar_afirmacion("El sitio es de tipo 'dragoncave'.",
                                    _ev_sitio("tipo"), _ficha())
        self.assertEqual(r["estado"], es.NO_VERIFICADA)
        self.assertFalse(r["comprobado"])
        self.assertIn("hamlet", r["motivo"])

    def test_entidad_inexistente_se_rechaza(self):
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev_sitio("tipo", df_id="999999999"), None)
        self.assertEqual(r["estado"], es.NO_VERIFICADA)

    def test_campo_que_el_nucleo_no_tiene_se_rechaza(self):
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    _ev_sitio("tipo"), {"nombre": "x"})
        self.assertEqual(r["estado"], es.NO_VERIFICADA)


class TestLoQueNoSeVerifica(unittest.TestCase):
    """La parte incomoda: lo que el sistema NO puede demostrar, y lo declara."""

    def test_la_negacion_no_se_verifica(self):
        """LA PRUEBA CENTRAL DE ESTA MISION.

        `trazabilidad` da 1.0 a esta frase: comparte el 100 % del vocabulario con
        su apoyo. Aqui da NO_APLICABLE, porque no hay plantilla que admita una
        negacion. El sistema no dice «es falsa»: dice «no lo puedo comprobar».
        """
        texto = "El sitio NO es de tipo 'hamlet'."
        ev = _ev_sitio("tipo")
        ficha = _ficha()
        r = es.verificar_afirmacion(texto, ev, ficha)
        self.assertEqual(r["estado"], es.NO_APLICABLE)
        # Y se demuestra que trazabilidad, en cambio, la daria por respaldada.
        ctx = ioc.contexto("x", [c.afirmacion(
            claim="El sitio es de tipo 'hamlet'.", truth_status=c.FACT,
            knowledge_source=c.PLAYER_KNOWLEDGE, visibility=c.PLAYER_VISIBLE,
            disclosure=c.ALLOWED,
            evidences=[c.evidencia("sitio", "112", ["type"], "n.f", "l.xml")])],
            modo=ioc.MODO_RAZONAMIENTO)
        claims = [{"texto": texto, "tipo": FACT, "soporte": ["c0"]}]
        self.assertEqual(iv.trazabilidad(claims, ctx)[0]["fraccion"], 1.0,
                         "si trazabilidad bajara, este argumento no valdria")

    def test_una_parfrasis_no_se_verifica(self):
        r = es.verificar_afirmacion("La fortaleza es de tipo 'hamlet'.",
                                    _ev_sitio("tipo"), _ficha())
        self.assertEqual(r["estado"], es.NO_APLICABLE,
                         "un sinonimo no es la plantilla: no se verifica")

    def test_una_afirmacion_compuesta_no_se_verifica(self):
        """«es de tipo X y tiene diamantes» no se verifica a medias.

        Verificaria la primera proposicion y dejaria la segunda sin comprobar, que
        es exactamente el fallo que la seccion de atomizacion prohibe.
        """
        r = es.verificar_afirmacion(
            "El sitio es de tipo 'hamlet' y tiene diamantes.",
            _ev_sitio("tipo"), _ficha())
        self.assertEqual(r["estado"], es.NO_APLICABLE)

    def test_campo_distinto_al_de_la_evidencia_no_se_verifica(self):
        """La evidencia dice `tipo`; el texto habla del nombre. No se cruzan."""
        r = es.verificar_afirmacion("El sitio se llama 'dragoncave'.",
                                    _ev_sitio("tipo"), _ficha())
        self.assertEqual(r["estado"], es.NO_APLICABLE)

    def test_una_plantilla_no_declarada_no_se_verifica(self):
        """Un dato nuevo NO es verificable hasta que se declare aqui."""
        r = es.verificar_afirmacion("El sitio huele a azufre.",
                                    _ev_sitio("olor"), _ficha())
        self.assertEqual(r["estado"], es.NO_APLICABLE)
        self.assertIn("plantilla", r["motivo"])

    def test_evidencia_con_varios_campos_no_se_verifica(self):
        """Con dos campos no se sabe cual se afirma: elegir seria adivinar."""
        ev = {"entidad": "sitio", "df_id": "112",
              "datos_utilizados": ["tipo", "nombre"],
              "funcion": "nucleo.Archivo.ficha_sitio"}
        r = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.", ev, _ficha())
        self.assertEqual(r["estado"], es.NO_APLICABLE)

    def test_sin_evidencia_no_se_verifica(self):
        self.assertEqual(
            es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    None, _ficha())["estado"],
            es.NO_APLICABLE)

    def test_evidencia_incompleta_no_se_verifica(self):
        self.assertEqual(
            es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                    {"entidad": "sitio"}, _ficha())["estado"],
            es.NO_APLICABLE)


class TestSeparacionDeAutoridad(unittest.TestCase):
    """VERIFICADA no autoriza. Es la separacion que la mision exige."""

    def test_un_claim_verificado_y_oculto_sigue_sin_divulgar(self):
        """Verificacion y divulgacion son ejes INDEPENDIENTES."""
        secreto = c.afirmacion(
            claim="El sitio es de tipo 'hamlet'.", truth_status=c.FACT,
            knowledge_source=c.WORLD_KNOWLEDGE, visibility=c.PLAYER_HIDDEN,
            disclosure=c.FORBIDDEN,
            evidences=[c.evidencia("sitio", "112", ["type"],
                                   "nucleo.Archivo.ficha_sitio", "l.xml")],
            no_descubierto=True)
        ctx = ioc.contexto("donde esta", [secreto], modo=ioc.MODO_RAZONAMIENTO)
        # FORBIDDEN ni siquiera entra al contexto del modelo.
        self.assertEqual(ctx["claims"], [])
        # Y aunque entrase, la politica seguiria negandolo.
        self.assertFalse(c.puede_revelarse(secreto))

    def test_el_resumen_declara_que_no_autoriza(self):
        self.assertIn("NO autoriza", es.resumen([], {}, None)["no_autoriza"])

    def test_el_resumen_declara_su_alcance(self):
        r = es.resumen([], {}, None)
        self.assertIn("SOLO", r["alcance"])
        self.assertIn("NO_APLICABLE", r["alcance"])


class TestDeterminismo(unittest.TestCase):
    def test_misma_entrada_mismo_veredicto(self):
        for _ in range(3):
            a = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                        _ev_sitio("tipo"), _ficha())
            b = es.verificar_afirmacion("El sitio es de tipo 'hamlet'.",
                                        _ev_sitio("tipo"), _ficha())
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
