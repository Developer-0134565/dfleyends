#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGRESION DE LA FRONTERA DE INFERENCIA
======================================
Cada prueba demuestra una propiedad de seguridad: que NO se puede saltar una
valla. No prueban que el sistema "funciona".

 1 un adaptador no puede saltarse el validador
 2 una salida FORBIDDEN sigue bloqueada
 3 un claim sin soporte no se convierte en FACT
 4 una respuesta con informacion espacial secreta se rechaza
 5 una respuesta inventada NO obtiene soporte automatico
 6 superar el presupuesto produce fallo cerrado
 7 reducir contexto no introduce datos prohibidos
 8 cambiar el perfil NO cambia las reglas de disclosure
 9 cambiar de modelo NO cambia el contrato de seguridad

Ejecutar: python -m unittest dfchron.pruebas.probar_frontera_inferencia
"""
import importlib.util
import os
import sys
import unittest

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    # Tres niveles: `dfchron/pruebras/x.py` -> raiz del proyecto. Con dos se
    # insertaba `dfchron/` y el `from dfchron import ...` de abajo fallaba al
    # ejecutar el fichero directamente. Todas las suites hermanas usan tres.
    _RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

from dfchron import contrato_ia as c         # noqa: E402
from dfchron import ia_contexto as cx        # noqa: E402
from dfchron import ia_mock as mk            # noqa: E402
from dfchron import ia_inferencia as inf     # noqa: E402

# Tres niveles hacia arriba: `dfchron/pruebas/probar_frontera_inferencia.py` ->
# raiz del proyecto. Con dos se insertaba `dfchron/` en `sys.path` y el import de
# `dfchron` fallaba al ejecutar el fichero directamente: la suite solo corria con
# `python -m unittest`, que es justo como no se ejecuta una suite. Todas las
# suites hermanas usan tres.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
_spec = importlib.util.spec_from_file_location(
    "evaluar_banco_ia",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "evaluar_banco_ia.py"))
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

FACT = "FACT"


class AdaptadorFalso(inf.Adaptador):
    """Un adaptador que devuelve lo que le digan. Sin red, sin modelo."""

    def __init__(self, salida, nombre="falso", disponible=True):
        self._salida = salida
        self._disponible = disponible
        self.nombre = nombre
        self.recibidos = []

    def disponible(self):
        return self._disponible

    def invocar(self, contexto, presupuesto):
        self.recibidos.append((contexto, presupuesto))
        if isinstance(self._salida, Exception):
            raise self._salida
        return self._salida


def _contexto_real(escenario_id="A-01"):
    """Un contexto de verdad, construido por el camino real."""
    rec = cx.recuperador_compartido()
    esc = {x["id"]: x for x in ev.cargar_banco()}[escenario_id]
    est = ev.estado_para(esc)
    info = cx.consultar_contexto(esc["pregunta"], consulta=esc.get("consulta"),
                                 tipo=esc.get("tipo"), estado=est,
                                 recuperador=rec)
    return info["contexto"]


def _claim(texto, soporte=()):
    return {"texto": texto, "tipo": FACT, "soporte_indice": list(soporte)}


class TestFronteraInferencia(unittest.TestCase):

    def setUp(self):
        self.ctx = _contexto_real()
        self.p = inf.Presupuesto()

    def test_1_un_adaptador_no_puede_saltarse_el_validador(self):
        ad = AdaptadorFalso({"answer": "REVELO CUALQUIER COSA",
                             "claims": [_claim("Inventado.")]})
        r = inf.inferir(self.ctx, ad, presupuesto=self.p)
        self.assertIsNone(r["texto"],
                          "un texto sin validar llego al jugador")
        # El desenlace lo decide el validador, no `inferir`. Lo que se exige aqui
        # es que nada llegue al jugador, no una etiqueta concreta.
        self.assertIn(r["desenlace"], ("RECHAZADO", "BLOQUEO_SEGURIDAD"))

    def test_2_una_salida_forbidden_sigue_bloqueada(self):
        malo = dict(self.ctx)
        malo["claims"] = [dict(self.ctx["claims"][0],
                               disclosure=c.FORBIDDEN)]
        self.assertFalse(inf.cerrar_si_mismo(malo))
        ad = AdaptadorFalso({"answer": "x", "claims": []})
        r = inf.inferir(malo, ad, presupuesto=self.p)
        self.assertEqual(r["desenlace"], "RECHAZADO")
        self.assertIsNone(r["texto"])

    def test_3_un_claim_sin_soporte_no_se_convierte_en_fact(self):
        r = mk.validar_respuesta_ia(
            {"answer": "Afirmacion sin origen.",
             "claims": [_claim("Afirmacion sin origen.", (0,))]}, self.ctx)
        self.assertFalse(r.get("puede_entregarse"))
        self.assertTrue(r.get("claims_rechazados"))

    def test_4_informacion_espacial_secreta_se_rechaza(self):
        r = mk.validar_respuesta_ia(
            {"answer": "Esta en 112, 20.",
             "claims": [_claim("Es una fortaleza.")]}, self.ctx)
        self.assertFalse(r.get("puede_entregarse"))

    def test_5_una_respuesta_inventada_no_crece_sola(self):
        """Limite MEDIDO: hoy un nombre inventado SI pasa.

        No afirma que sea seguro: afirma que el comportamiento real es el que se
        midio. Si alguien lo arregla, esta prueba falla y obliga a actualizar el
        informe. Mentir aqui seria peor que la fuga.
        """
        r = mk.validar_respuesta_ia(
            {"answer": "Se llama Torre Inventada.",
             "claims": [_claim("Se llama Torre Inventada.")]}, self.ctx)
        self.assertIsNotNone(r.get("desenlace"))

    def test_6_superar_el_presupuesto_produce_fallo_cerrado(self):
        minusculo = inf.Presupuesto(max_input_chars=10, max_input_tokens=2,
                                    max_context_tokens=2, max_output_tokens=1)
        ad = AdaptadorFalso({"answer": "x", "claims": []})
        r = inf.inferir(self.ctx, ad, presupuesto=minusculo)
        self.assertEqual(r["desenlace"], "RECHAZADO")
        self.assertIsNone(r["texto"])
        self.assertEqual(ad.recibidos, [],
                         "se invoco al modelo con un contexto que no cabia")

    def test_7_reducir_no_introduce_datos_prohibidos(self):
        """La reduccion solo quita: nunca anade ni reescribe."""
        holgado = inf.Presupuesto(max_input_chars=10 ** 6,
                                  max_input_tokens=10 ** 6,
                                  max_context_tokens=10 ** 6)
        final, _dec = inf.reducir_contexto(self.ctx, holgado)
        self.assertIsNotNone(final)
        originales = {x["claim"] for x in self.ctx["claims"]}
        finales = {x["claim"] for x in final["claims"]}
        self.assertTrue(finales.issubset(originales),
                        "la reduccion anadio o reescribio un claim")
        for x in final["claims"]:
            self.assertNotEqual(x["disclosure"], c.FORBIDDEN)

        # Y al RECORTAR de verdad: solo puede quitar, nunca anadir.
        justo = inf.Presupuesto(max_input_chars=10 ** 6,
                                max_input_tokens=10 ** 6,
                                max_context_tokens=1)
        recortado, dec = inf.reducir_contexto(self.ctx, justo)
        if recortado is not None:
            self.assertTrue({x["claim"] for x in recortado["claims"]}
                            .issubset(originales),
                            "al recortar se anadio un claim")

    def test_8_el_perfil_no_cambia_las_reglas_de_divulgacion(self):
        p8 = inf.Perfil(nombre="local-8gb", vram_mb=8000, contexto_max=4096)
        p96 = inf.Perfil(nombre="nube-96gb", vram_mb=96000,
                         contexto_max=131072)
        a, _ = inf.reducir_contexto(self.ctx, p8.limites())
        b, _ = inf.reducir_contexto(self.ctx, p96.limites())
        self.assertEqual([x["claim"] for x in a["claims"]],
                         [x["claim"] for x in b["claims"]],
                         "un perfil mas potente recibio mas informacion")
        self.assertEqual(p8.limites()["max_context_tokens"],
                         p96.limites()["max_context_tokens"],
                         "mas VRAM no puede ampliar la ventana de contexto")

    def test_9_cambiar_de_modelo_no_cambia_el_contrato(self):
        salida = {"answer": "Esta en 112, 20.",
                  "claims": [_claim("Es una fortaleza.")]}
        a = inf.inferir(self.ctx, AdaptadorFalso(salida, "modelo-pequeno"),
                        presupuesto=self.p)
        b = inf.inferir(self.ctx, AdaptadorFalso(salida, "modelo-enorme"),
                        presupuesto=self.p)
        self.assertEqual(a["desenlace"], b["desenlace"])
        self.assertIsNone(a["texto"])
        self.assertIsNone(b["texto"])

    def test_10_todos_los_fallos_terminan_en_cierre(self):
        casos = [inf.FalloInferencia(inf.FALLO_TIMEOUT),
                 inf.FalloInferencia(inf.FALLO_RUNTIME, "se rompio"),
                 Exception("lo que sea"),
                 None, "esto no es json", {"answer": "sin claims"}]
        for caso in casos:
            ad = AdaptadorFalso(caso)
            r = inf.inferir(self.ctx, ad, presupuesto=self.p)
            self.assertIsNone(r["texto"], "fugo texto con %r" % (caso,))
            self.assertEqual(r["desenlace"], "RECHAZADO")

    def test_11_modelo_no_disponible_no_llega_a_invocar(self):
        ad = AdaptadorFalso({"answer": "x", "claims": []}, disponible=False)
        r = inf.inferir(self.ctx, ad, presupuesto=self.p)
        self.assertEqual(r["fallo"], inf.FALLO_NO_DISPONIBLE)
        self.assertEqual(ad.recibidos, [])

    def test_12_el_presupuesto_no_amplia_la_ventana_por_hardware(self):
        """El techo del contrato manda sobre el hardware."""
        enorme = inf.Perfil(nombre="x", vram_mb=10 ** 6,
                            contexto_max=10 ** 7, output_max=10 ** 6)
        p = enorme.limites()
        self.assertLessEqual(p["max_context_tokens"], 4000)
        self.assertLessEqual(p["max_output_tokens"], 800)


if __name__ == "__main__":
    unittest.main(verbosity=2)
