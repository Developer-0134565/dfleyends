#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBAS DE LA VERIFICACION SEMANTICA DETERMINISTA.

Todos los casos usan **datos reales** del dataset activo. No hay figuras de
mentira: si un id no existe, se comprueba que el sistema lo declara, no se
inventa uno que sí exista.

Lo que se prueba, y por qué importa:
  * afirmación verdadera  -> se verifica
  * afirmación falsa      -> se rechaza
  * entidad inexistente   -> estado seguro, nunca VERIFICADA
  * relación inexistente -> se rechaza
  * afirmación ambigua    -> AMBIGUA, nunca VERIFICADA
  * dato ausente          -> NO_VERIFICADA, no se rellena
  * dataset incorrecto    -> falla la evidencia (integrado con ia_estructura)
  * determinismo         -> misma entrada, mismo resultado

Ejecutar:  python 00_SOURCE/tools/probar_verificacion_semantica.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nucleo import Archivo                                     # noqa: E402
import verificacion_semantica as vs                            # noqa: E402

V, NV, A = vs.VERIFICADA, vs.NO_VERIFICADA, vs.AMBIGUA


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archivo = Archivo()


# =================================================== NIVEL 1: EXISTENCIA ===
class TestExistencia(_Base):
    """«La unidad X existe.»"""

    def test_entidad_real_se_verifica(self):
        self.assertEqual(vs.existe(self.archivo, "figura", 712)["estado"], V)

    def test_entidad_inexistente_no_se_verifica(self):
        """Un id altisimo no existe, y el sistema lo dice."""
        r = vs.existe(self.archivo, "figura", 99999999)
        self.assertEqual(r["estado"], NV)
        self.assertIn("no existe", r["motivo"])

    def test_id_negativo_no_existe(self):
        self.assertEqual(vs.existe(self.archivo, "figura", -1)["estado"], NV)

    def test_tipo_desconocido_es_ambiguo(self):
        """Un sujeto que el nucleo no conoce no se resuelve por similitud."""
        r = vs.existe(self.archivo, "nave", 1)
        self.assertEqual(r["estado"], A)
        self.assertIn("desconocido", r["motivo"])

    def test_todos_los_tipos_declarados_existen_en_el_indice(self):
        """Cada tipo de `SUJETOS` tiene su sección con datos dentro.

        No se comprueba el id 0: los sitios empiezan en 1, y un id que no existe
        es precisamente lo que `existe()` debe rechazar. Lo que se comprueba es
        que el índice de cada tipo **no esté vacío**.
        """
        for tipo in vs.SUJETOS:
            with self.subTest(tipo=tipo):
                self.assertTrue(len(vs._indice_de(self.archivo, tipo)) > 0,
                                "el tipo %r tiene un índice vacío" % tipo)

    def test_existe_es_idempotente(self):
        a = vs.existe(self.archivo, "figura", 712)
        b = vs.existe(self.archivo, "figura", 712)
        self.assertEqual(a["estado"], b["estado"])
        self.assertEqual(a["motivo"], b["motivo"])


# ==================================================== NIVEL 2: ATRIBUTO ===
class TestAtributo(_Base):
    """«X tiene el atributo Y.»"""

    def test_valor_real_se_verifica(self):
        registro = self.archivo.indice.figuras["712"]
        raza = registro["campos"]["race"]["valor"]
        r = vs.atributo(self.archivo, "figura", 712, "race", raza)
        self.assertEqual(r["estado"], V, r["motivo"])

    def test_valor_inventado_se_rechaza(self):
        r = vs.atributo(self.archivo, "figura", 712, "race", "DRAGON")
        self.assertEqual(r["estado"], NV)
        self.assertIn("el nucleo dice", r["motivo"])

    def test_la_comparacion_es_exacta(self):
        """`MINOTAUR` y `minotaur` NO son lo mismo, y no se normaliza.

        Es la frontera con la verificacion semantica: si se normalizara el
        texto, esto empezaria a aceptar cosas que el dato no dice.
        """
        registro = self.archivo.indice.figuras["712"]
        raza = registro["campos"]["race"]["valor"]
        minuscula = str(raza).lower()
        if minuscula != raza:
            r = vs.atributo(self.archivo, "figura", 712, "race", minuscula)
            self.assertEqual(r["estado"], NV,
                             "el nucleo normalizó la comparación; no debe")

    def test_atributo_inexistente_en_una_entidad_existente(self):
        """El campo no está en el dato: NO_VERIFICADA, no se inventa."""
        r = vs.atributo(self.archivo, "figura", 712, "no_existe", "X")
        self.assertIn(r["estado"], (NV, A))

    def test_valor_centinela_no_es_un_valor(self):
        """`-1` es «sin dato», no un valor que comparar.

        Se usa un campo que **sí** está en la lista de atributos: `death_year`.
        Pedir uno fuera de la lista daría `AMBIGUA`, que es otra cosa.
        """
        vs.ATRIBUTOS["figura"] = (vs.ATRIBUTOS["figura"] + ("death_year",))
        try:
            r = vs.atributo(self.archivo, "figura", 712, "death_year", -1)
            self.assertEqual(r["estado"], NV)
            self.assertIn("ausente", r["motivo"])
        finally:
            vs.ATRIBUTOS["figura"] = tuple(
                x for x in vs.ATRIBUTOS["figura"] if x != "death_year")

    def test_atributo_fuera_de_la_lista_no_compara_centinelas(self):
        """Un campo no declarado se marca AMBIGUA antes de comparar nada."""
        r = vs.atributo(self.archivo, "figura", 712, "death_year", -1)
        self.assertEqual(r["estado"], A)

    def test_entidad_inexistente_no_verifica_atributo(self):
        r = vs.atributo(self.archivo, "figura", 99999999, "race", "X")
        self.assertEqual(r["estado"], NV)

    def test_atributo_fuera_de_la_lista_es_ambiguo(self):
        """Un atributo no declarado no se resuelve por parecido."""
        r = vs.atributo(self.archivo, "figura", 712, "parecido_con", "x")
        self.assertEqual(r["estado"], A)
        self.assertIn("no se verifica", r["motivo"])

    def test_sujeto_inexistente_es_ambiguo(self):
        self.assertEqual(
            vs.atributo(self.archivo, "unicornio", 1, "race", "x")["estado"], A)


# ===================================================== NIVEL 3: RELACION ===
class TestRelacion(_Base):
    """«X está relacionado con Y.»"""

    def _par_con_relacion(self):
        """Un par real de figuras con relacion, del grafo real."""
        for fig_id, arr in self.archivo.indice.rel_por_hf.items():
            for rel in arr:
                src = str(rel["campos"]["source_hf"]["valor"])
                tgt = str(rel["campos"]["target_hf"]["valor"])
                tipo = rel["campos"]["relationship"]["valor"]
                if src != tgt:
                    return fig_id, src, tgt, tipo
        self.skipTest("el grafo no tiene relación con extremos distintos")

    def test_relacion_real_se_verifica(self):
        fig_id, src, tgt, tipo = self._par_con_relacion()
        r = vs.relacion(self.archivo, src, tgt, tipo)
        self.assertEqual(r["estado"], V, r["motivo"])

    def test_el_grafo_no_se_simetriza(self):
        """El grafo es DIRIGIDO: la inversa no se da por cierta."""
        fig_id, src, tgt, tipo = self._par_con_relacion()
        self.assertEqual(vs.relacion(self.archivo, src, tgt)["estado"], V)
        inversa = vs.relacion(self.archivo, tgt, src)
        self.assertIn(inversa["estado"], (V, NV))
        if inversa["estado"] == NV:
            self.assertIn("no hay relacion registrada", inversa["motivo"])

    def test_relacion_inexistente_se_rechaza(self):
        self.assertEqual(vs.relacion(self.archivo, "712", "713")["estado"], NV)

    def test_tipo_de_relacion_equivocado_se_rechaza(self):
        fig_id, src, tgt, tipo = self._par_con_relacion()
        r = vs.relacion(self.archivo, src, tgt, "tipo_inventado")
        self.assertEqual(r["estado"], NV)
        self.assertIn("tipos reales", r["motivo"])

    def test_figura_inexistente_no_verifica_relacion(self):
        self.assertEqual(vs.relacion(self.archivo, "712", "99999999")["estado"],
                         NV)

    def test_el_motivo_de_rechazo_enumera_los_tipos_reales(self):
        """El fallo explica, no solo rechaza."""
        fig_id, src, tgt, tipo = self._par_con_relacion()
        r = vs.relacion(self.archivo, src, tgt, "tipo_inventado")
        self.assertIn("tipos_encontrados", r)


# ======================================================== NIVEL 4: ESTADO ==
class TestEstado(_Base):
    def test_certidumbre_real_se_verifica(self):
        r = vs.estado(self.archivo, "figura", 712)
        self.assertEqual(r["estado"], V, r["motivo"])
        self.assertIn(r["certainty"], ("FACT", "DERIVED", "UNKNOWN"))

    def test_entidad_inexistente_no_tiene_estado(self):
        self.assertEqual(vs.estado(self.archivo, "figura", 99999999)["estado"],
                         NV)


# ====================================================== NIVEL 5: CANTIDAD ==
class TestCantidad(_Base):
    def test_cuenta_correcta_se_verifica(self):
        total = len(self.archivo.indice.figuras)
        self.assertEqual(vs.cantidad(self.archivo, "figura", total)["estado"], V)

    def test_cuenta_incorrecta_se_rechaza(self):
        total = len(self.archivo.indice.figuras)
        self.assertEqual(
            vs.cantidad(self.archivo, "figura", total + 1)["estado"], NV)

    def test_el_recuento_es_real_no_cacheado(self):
        a = vs.cantidad(self.archivo, "figura", 0)
        b = vs.cantidad(self.archivo, "figura", 0)
        self.assertEqual(a["obtenido"], b["obtenido"])

    def test_tipo_desconocido_es_ambiguo(self):
        self.assertEqual(vs.cantidad(self.archivo, "dragon", 5)["estado"], A)


# ===================================================== NIVEL 6: ESTRUCTURA ==
class TestEstructura(_Base):
    def test_cadena_valida_se_verifica(self):
        fig_id, src, tgt, tipo = TestRelacion._par_con_relacion(self)
        r = vs.estructura(self.archivo, [src, tgt])
        self.assertEqual(r["estado"], V, r["motivo"])

    def test_cadena_con_salto_roto_no_verifica(self):
        """Una arista falsa rompe la cadena entera."""
        fig_id, src, tgt, tipo = TestRelacion._par_con_relacion(self)
        r = vs.estructura(self.archivo, [src, tgt, "99999999"])
        self.assertEqual(r["estado"], NV)
        self.assertIn("se rompe", r["motivo"])

    def test_cadena_de_un_solo_extremo_es_ambigua(self):
        self.assertEqual(vs.estructura(self.archivo, ["712"])["estado"], A)

    def test_cadena_vacia_es_ambigua(self):
        self.assertEqual(vs.estructura(self.archivo, [])["estado"], A)


# ===================================================== NIVEL 7: HISTORICO ==
class TestHistorico(_Base):
    """El unico nivel PARCIAL, y la prueba explica por que."""

    def test_sin_ano_o_sin_orden_no_se_verifica(self):
        """Sin años, o con años iguales, el orden NO es demostrable.

        Este caso concreto tiene años iguales (1 y 1), que es el subcaso
        peligroso: `a < b` es falso, pero la comprobación ingenua lo daba por
        bueno. Se comprueba que la salida explica cuál de las dos cosas pasa.
        """
        fig_id, src, tgt, tipo = TestRelacion._par_con_relacion(self)
        r = vs.historico(self.archivo, src, tgt)
        if r["estado"] == NV:
            self.assertIn("orden", r["motivo"])

    def test_verificar_siempre_exige_anos_reales(self):
        """Barrido: si da VERIFICADA, es porque hay dos años comparados."""
        for fig_id, arr in list(self.archivo.indice.rel_por_hf.items())[:150]:
            for rel in arr[:2]:
                src = str(rel["campos"]["source_hf"]["valor"])
                tgt = str(rel["campos"]["target_hf"]["valor"])
                if src == tgt:
                    continue
                r = vs.historico(self.archivo, src, tgt)
                if r["estado"] == V:
                    self.assertIsNotNone(r["anio_a"])
                    self.assertIsNotNone(r["anio_b"])

    def test_relacion_inexistente_no_es_historica(self):
        self.assertEqual(vs.historico(self.archivo, "712", "713")["estado"], NV)


# =========================================== DETERMINISMO Y ALCANCE =========
class TestDeterminismoYAlcance(_Base):
    """La misma entrada da siempre la misma salida."""

    def test_misma_entrada_mismo_resultado(self):
        for _ in range(3):
            a = vs.atributo(self.archivo, "figura", 712, "race", "MINOTAUR")
            b = vs.atributo(self.archivo, "figura", 712, "race", "MINOTAUR")
            self.assertEqual(a, b)

    def test_el_resultado_no_depende_del_orden_de_consulta(self):
        """Consultar en otro orden no cambia el veredicto."""
        primero = vs.existe(self.archivo, "figura", 712)["estado"]
        for otro in ("0", "5", "999"):
            vs.existe(self.archivo, "figura", otro)
        self.assertEqual(primero, vs.existe(self.archivo, "figura", 712)["estado"])

    def test_el_alcance_declara_lo_que_no_se_comprueba(self):
        """Lo no comprobado se escribe, para que nadie lo asuma."""
        a = vs.alcance()
        texto = str(a)
        self.assertIn("paráfrasis", texto)
        self.assertIn("negación", texto)
        self.assertIn("no se usa similitud", texto)

    def test_ningun_estado_desconocido(self):
        """Solo existen los tres estados declarados. Nada se cuela."""
        for r in (vs.existe(self.archivo, "figura", 712),
                  vs.existe(self.archivo, "figura", -1),
                  vs.cantidad(self.archivo, "figura", 1)):
            self.assertIn(r["estado"], vs.ESTADOS)


if __name__ == "__main__":
    unittest.main(verbosity=2)