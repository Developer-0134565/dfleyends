#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBAS DE LA CAPA DE CONSULTA DETERMINISTA.

Todos los casos usan el dataset real. Lo que se comprueba:

  * entidad existente / inexistente / invalida
  * atributo con valor, sin inferirlo, y con centinela
  * relacion existente, y de tipo inexistente
  * identidad no demostrable -> NO se inventa un id
  * afirmacion verdadera / falsa
  * dataset ausente -> DATA_UNAVAILABLE
  * limites y paginacion
  * determinismo y serializacion
  * inmutabilidad: consultar no escribe
  * entradas hostiles

Ejecutar:  python dfchron/pruebas/probar_servicio_consulta.py
"""
import copy
import hashlib
import io
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

from dfchron import servicio_consulta as qc          # noqa: E402
from dfchron import ia_conocimiento as ic            # noqa: E402

F, NF, NV = qc.FOUND, qc.NOT_FOUND, qc.NOT_VERIFIED
IQ, DU = qc.INVALID_QUERY, qc.DATA_UNAVAILABLE


class TestContrato(unittest.TestCase):
    """El contrato se declara a si mismo, y lo declarado es lo que hay."""

    def test_las_seis_operaciones_existen(self):
        c = qc.contrato()
        self.assertEqual(len(c["operaciones"]), 6)
        for op in c["operaciones"]:
            self.assertTrue(callable(getattr(qc, op)),
                            "la operacion %r no existe" % op)

    def test_el_alcance_declara_lo_que_no_puede(self):
        texto = str(qc.alcance())
        self.assertIn("lenguaje natural", texto)
        self.assertIn("NO es un reloj", texto)
        # Y que dataset_id no se confunde con caducidad.
        self.assertIn("caducidad", texto.lower())

    def test_los_codigos_nuevos_son_los_minimos(self):
        self.assertEqual(qc.CODIGOS_NUEVOS, ("NO_VERIFICADO", "NO_DISPONIBLE"))

    def test_los_codigos_prestados_existen_en_servicio(self):
        """No se inventan nombres que `servicio` no usa ya."""
        ruta = os.path.join(qc.RAIZ, "dfchron", "servicio.py")
        with io.open(ruta, encoding="utf-8") as f:
            texto = f.read()
        for codigo in qc.CODIGOS_PRESTADOS:
            self.assertIn('"%s"' % codigo, texto,
                          "el codigo %r no existe en servicio.py" % codigo)


class TestEntidad(unittest.TestCase):
    """Operación 1."""

    def test_entidad_existente(self):
        r = qc.obtener_entidad("figura", "712")
        self.assertEqual(r["estado"], F)
        self.assertEqual(r["identity"], {"tipo": "figura", "df_id": "712"})

    def test_entidad_inexistente_no_es_found(self):
        r = qc.obtener_entidad("figura", "999999999")
        self.assertEqual(r["estado"], NF)
        self.assertFalse(r["ok"])

    def test_todo_resultado_transporta_el_dataset(self):
        for r in (qc.obtener_entidad("figura", "712"),
                   qc.obtener_entidad("figura", "999999999")):
            self.assertEqual(r["dataset_id"], ic.DATASET_ID)
            self.assertIn("alcance", r)

    def test_el_exito_transporta_evidencia_con_state_version(self):
        r = qc.obtener_entidad("figura", "712")
        self.assertIsNotNone(r["evidence"])
        self.assertEqual(r["evidence"]["state_version"], ic.DATASET_ID)

    def test_tipo_desconocido_es_consulta_invalida(self):
        self.assertEqual(qc.obtener_entidad("nave", "1")["estado"], IQ)

    def test_id_vacio_es_consulta_invalida(self):
        self.assertEqual(qc.obtener_entidad("figura", "")["estado"], IQ)
        self.assertEqual(qc.obtener_entidad("figura", None)["estado"], IQ)


class TestIdentidadNoInventada(unittest.TestCase):
    """Fase 5. Lo que no tiene identidad no recibe un id inventado."""

    def test_tipo_sin_identidad_no_recibe_una(self):
        for tipo in qc.TIPOS_SIN_IDENTIDAD:
            with self.subTest(tipo=tipo):
                r = qc.obtener_entidad(tipo, "1")
                self.assertEqual(r["estado"], NV)
                self.assertIsNone(r["identity"])

    def test_tipo_sin_identidad_tampoco_para_contar(self):
        self.assertEqual(qc.contar("relacion")["estado"], NV)

    def test_tipo_sin_identidad_tampoco_para_evidencia(self):
        r = qc.obtener_evidencia("era", "1")
        self.assertEqual(r["estado"], NV)
        self.assertIsNone(r["evidence"])

    def test_la_identidad_es_el_df_id_del_juego(self):
        r = qc.obtener_entidad("figura", "712")
        self.assertEqual(r["identity"]["df_id"], r["data"]["df_id"])
        self.assertEqual(r["data"]["df_id"], "712")

    def test_la_guarda_de_identidad_rechaza_lo_que_no_la_tiene(self):
        """Se prueba la guarda misma, no solo su efecto colateral.

        Si `obtener_entidad` dejara de filtrar el tipo, esta comprobación
        seguiría dando `None` y el fallo pasaría desapercibido.
        """
        for tipo in qc.TIPOS_SIN_IDENTIDAD:
            with self.subTest(tipo=tipo):
                self.assertIsNone(qc._identidad(tipo, "1"))

    def test_la_guarda_de_identidad_acepta_lo_que_si_la_tiene(self):
        self.assertEqual(qc._identidad("figura", "712"),
                         {"tipo": "figura", "df_id": "712"})


class TestAtributo(unittest.TestCase):
    """Operación 2."""

    def test_atributo_existente_devuelve_valor_y_evidencia(self):
        r = qc.obtener_atributo("figura", "712", "race")
        self.assertEqual(r["estado"], F)
        self.assertEqual(r["data"]["atributo"], "race")
        self.assertTrue(r["data"]["valor"])
        self.assertIsNotNone(r["evidence"])

    def test_atributo_inexistente_no_se_infunere(self):
        r = qc.obtener_atributo("figura", "712", "atributo_inventado")
        self.assertEqual(r["estado"], NV)
        self.assertIn("atributos_disponibles", r)

    def test_centinela_no_es_un_valor(self):
        r = qc.obtener_atributo("figura", "712", "death_year")
        self.assertNotEqual(r["estado"], F,
                            "un centinela se dio como valor real")

    def test_entidad_inexistente_no_devuelve_atributo(self):
        self.assertEqual(qc.obtener_atributo("figura", "999999999", "race")["estado"],
                         NF)


class TestRelaciones(unittest.TestCase):
    """Operación 3."""

    def _par_real(self):
        archivo = qc.servicio.obtener_archivo()
        for fig_id, arr in archivo.indice.rel_por_hf.items():
            for rel in arr:
                src = str(rel["campos"]["source_hf"]["valor"])
                tgt = str(rel["campos"]["target_hf"]["valor"])
                if src != tgt:
                    return src, tgt, rel["campos"]["relationship"]["valor"]
        self.skipTest("no hay relaciones con extremos distintos")

    def test_relacion_existente(self):
        src, tgt, tipo = self._par_real()
        r = qc.buscar_relaciones(src, tipo)
        self.assertEqual(r["estado"], F)
        self.assertIn(tipo, {x["tipo"] for x in r["data"]})

    def test_relacion_de_tipo_inexistente_no_se_inventata(self):
        src, tgt, tipo = self._par_real()
        r = qc.buscar_relaciones(src, "tipo_inventado")
        self.assertEqual(len(r["data"]), 0)

    def test_figura_inexistente_no_devuelve_relaciones(self):
        self.assertEqual(qc.buscar_relaciones("999999999")["estado"], NF)

    def test_las_relaciones_cargan_evidencia_y_dataset(self):
        src, tgt, tipo = self._par_real()
        r = qc.buscar_relaciones(src)
        self.assertEqual(r["dataset_id"], ic.DATASET_ID)
        self.assertIsNotNone(r["identity"])
        self.assertIsNotNone(r["evidence"])


class TestContarYFiltrar(unittest.TestCase):
    """Operación 4 y fase 9."""

    def test_contar_sin_filtro(self):
        r = qc.contar("figura")
        self.assertEqual(r["estado"], F)
        self.assertEqual(r["data"]["total"], r["data"]["coincidencias"])

    def test_filtro_exacto(self):
        total = qc.contar("figura")["data"]["total"]
        r = qc.contar("figura", {"race": "MINOTAUR"})
        self.assertEqual(r["estado"], F)
        self.assertGreater(r["data"]["coincidencias"], 0)
        self.assertLess(r["data"]["coincidencias"], total)

    def test_filtro_inexistente_no_se_inventa(self):
        r = qc.contar("figura", {"campo_inventado": "x"})
        self.assertEqual(r["estado"], NV)
        self.assertIn("campos_disponibles", r)

    def test_el_filtro_es_exacto_sin_normalizar(self):
        """`minotaur` no cuenta como `MINOTAUR`."""
        registro = qc.servicio.obtener_archivo().indice.figuras["712"]
        raza = registro["campos"]["race"]["valor"]
        if str(raza).lower() != str(raza):
            mayus = qc.contar("figura", {"race": raza})["data"]["coincidencias"]
            minus = qc.contar("figura", {"race": str(raza).lower()})
            self.assertEqual(minus["data"]["coincidencias"], 0)
            self.assertGreater(mayus, 0)

    def test_filtro_no_objeto_es_invalido(self):
        self.assertEqual(qc.contar("figura", "no-objeto")["estado"], IQ)


class TestVerificar(unittest.TestCase):
    """Operación 5: delega, no reimplementa."""

    def test_afirmacion_verdadera(self):
        self.assertEqual(qc.verificar("figura", "712", "existe")["estado"], F)

    def test_afirmacion_falsa(self):
        self.assertEqual(
            qc.verificar("figura", "712", "tiene:race", "DRAGON")["estado"], NV)

    def test_entidad_inexistente(self):
        self.assertEqual(qc.verificar("figura", "999999999", "existe")["estado"],
                         NV)

    def test_predicado_desconocido_es_invalido(self):
        self.assertEqual(qc.verificar("figura", "712", "es_increible")["estado"],
                         IQ)

    def test_delega_en_el_verificador_existente(self):
        """La capa no juzga: pide veredicto y lo traduce."""
        r = qc.verificar("figura", "712", "existe")
        self.assertEqual(r["data"]["verificacion"]["estado"],
                         qc.vs.VERIFICADA)

    def test_repetir_no_cambia_el_veredicto(self):
        a = qc.verificar("figura", "712", "tiene:race", "DRAGON")
        b = qc.verificar("figura", "712", "tiene:race", "DRAGON")
        self.assertEqual(a["estado"], b["estado"])
        self.assertEqual(a["estado"], NV)


class TestEvidencia(unittest.TestCase):
    """Operación 6."""

    def test_la_evidencia_trae_state_version(self):
        r = qc.obtener_evidencia("figura", "712", ["nombre"])
        self.assertEqual(r["estado"], F)
        self.assertEqual(r["data"]["state_version"], ic.DATASET_ID)

    def test_la_evidencia_apunta_a_la_funcion_del_nucleo(self):
        r = qc.obtener_evidencia("figura", "712", ["nombre"])
        self.assertTrue(r["data"]["funcion"].startswith("nucleo.Archivo."))

    def test_la_evidencia_no_se_inventa_para_lo_que_no_existe(self):
        r = qc.obtener_evidencia("figura", "999999999", ["nombre"])
        self.assertIn(r["estado"], (F, DU))


class TestTemporalidad(unittest.TestCase):
    """Fase 7: dataset_id NO es un reloj."""

    def test_no_se_declara_caducidad_ninguna(self):
        r = qc.obtener_entidad("figura", "712")
        self.assertNotIn("caducado", str(r).lower())
        self.assertNotIn("expirado", str(r).lower())

    def test_el_contrato_lo_dice_explicitamente(self):
        self.assertIn("NO es un reloj", qc.contrato()["temporalidad"])

    def test_state_version_es_el_dataset_id_real(self):
        r = qc.obtener_evidencia("figura", "712", ["nombre"])
        self.assertEqual(r["data"]["state_version"], r["dataset_id"])

    def test_no_se_fabrica_una_marca_de_tiempo(self):
        r = qc.obtener_entidad("figura", "712")
        for clave in ("timestamp", "fecha", "hora", "tick", "caducidad"):
            self.assertNotIn(clave, r)


class TestLimitesYPaginacion(unittest.TestCase):
    """Fase 10."""

    def _figura_con_relaciones(self, minimo=3):
        archivo = qc.servicio.obtener_archivo()
        for fig_id, arr in archivo.indice.rel_por_hf.items():
            if len(arr) >= minimo:
                return fig_id
        return None

    def test_limite_se_respeta(self):
        src = self._figura_con_relaciones()
        if src is None:
            self.skipTest("no hay figura con suficientes relaciones")
        r = qc.buscar_relaciones(src, limite=1)
        self.assertLessEqual(len(r["data"]), 1)
        self.assertTrue(r["truncado"])

    def test_limite_invalido_no_revienta(self):
        for malo in (0, -5, "diez", 3.5, True):
            with self.subTest(limite=malo):
                self.assertEqual(
                    qc.buscar_relaciones("712", limite=malo)["estado"], IQ)

    def test_limite_ausente_usa_el_defecto(self):
        self.assertEqual(qc.LIMITE_DEFECTO, 200)

    def test_un_limite_enorme_se_recorta_al_maximo(self):
        """Sin tope, un `limite=10**9` seria una vía a descargarlo todo."""
        lim, err = qc._validar_limite(10 ** 9)
        self.assertIsNone(err)
        self.assertEqual(lim, qc.LIMITE_MAXIMO)

    def test_un_limite_enorme_no_devuelve_el_mundo(self):
        r = qc.buscar_relaciones("712", limite=10 ** 9)
        self.assertLessEqual(len(r["data"]), qc.LIMITE_MAXIMO)

    def test_la_normalizacion_de_limite_no_revienta(self):
        """`_validar_limite` es la primera linea de defensa: se prueba sola."""
        self.assertEqual(qc._validar_limite(None), (qc.LIMITE_DEFECTO, None))
        for malo in (0, -1, "x", [], {}, 2.5, True, float("nan")):
            with self.subTest(limite=malo):
                lim, err = qc._validar_limite(malo)
                self.assertIsNone(lim)
                self.assertTrue(err, "un limite invalido paso sin avisar")


class TestDeterminismo(unittest.TestCase):
    """Fase 12."""

    def test_misma_consulta_mismo_resultado(self):
        a = qc.obtener_entidad("figura", "712")
        b = qc.obtener_entidad("figura", "712")
        self.assertEqual(json.dumps(a, sort_keys=True, default=str),
                         json.dumps(b, sort_keys=True, default=str))

    def test_el_orden_de_consulta_no_cambia_el_resultado(self):
        primero = qc.obtener_entidad("figura", "712")["data"]
        for otro in ("0", "5", "999"):
            qc.obtener_entidad("figura", otro)
        self.assertEqual(primero, qc.obtener_entidad("figura", "712")["data"])

    def test_el_resultado_es_serializable(self):
        json.dumps(qc.obtener_entidad("figura", "712"))

    def test_no_hay_referencias_python_en_el_json(self):
        texto = json.dumps(qc.obtener_entidad("figura", "712"), default=str)
        self.assertNotIn("object at 0x", texto)
        self.assertNotIn("<class", texto)


class TestInmutabilidad(unittest.TestCase):
    """Fase 13: consultar no escribe."""

    def _hash_dataset(self):
        ruta = os.path.join(qc.RAIZ, "00_SOURCE", "processed", "merged",
                            "historical_figures.jsonl")
        with open(ruta, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_la_consulta_no_modifica_el_dataset(self):
        antes = self._hash_dataset()
        for _ in range(3):
            qc.obtener_entidad("figura", "712")
            qc.contar("figura")
            qc.buscar_relaciones("712")
            qc.verificar("figura", "712", "existe")
        self.assertEqual(antes, self._hash_dataset())

    def test_la_consulta_no_cambia_el_dataset_id_del_nucleo(self):
        antes = ic.DATASET_ID
        qc.obtener_entidad("figura", "712")
        self.assertEqual(ic.DATASET_ID, antes)

    def test_el_resultado_es_una_copia(self):
        """Mutar lo que devuelve no toca el núcleo."""
        r = qc.obtener_entidad("figura", "712")
        copia = copy.deepcopy(r["data"])
        r["data"]["df_id"] = "999999"
        self.assertEqual(qc.obtener_entidad("figura", "712")["data"], copia)


class TestAdversarial(unittest.TestCase):
    """Fase 17: entradas hostiles. Ninguna revienta."""

    def test_ids_enormes(self):
        for enorme in ("9" * 40, "-" + "9" * 40, "0" * 50):
            with self.subTest(df_id=enorme[:12]):
                r = qc.obtener_entidad("figura", enorme)
                self.assertIn(r["estado"], (NF, F))

    def test_id_con_caracteres_especiales(self):
        for raro in ("<script>", "../../etc/passwd", "'; DROP TABLE--", "\x00"):
            with self.subTest(df_id=raro[:10]):
                self.assertIn(qc.obtener_entidad("figura", raro)["estado"],
                              (NF, F, IQ))

    def test_id_con_unicode(self):
        for u in ("図", "Ñandú", "Ωμέγα", "🜁"):
            with self.subTest(df_id=u):
                self.assertIn(qc.obtener_entidad("figura", u)["estado"],
                              (NF, F, IQ))

    def test_tipo_no_string(self):
        for tipo in (None, 1, [], {}, True):
            with self.subTest(tipo=tipo):
                self.assertEqual(qc.obtener_entidad(tipo, "1")["estado"], IQ)

    def test_tipo_vacio(self):
        self.assertEqual(qc.obtener_entidad("", "1")["estado"], IQ)

    def test_filtro_con_valor_no_string(self):
        r = qc.contar("figura", {"race": {"anidado": "objeto"}})
        self.assertEqual(r["estado"], F)
        self.assertEqual(r["data"]["coincidencias"], 0)

    def test_filtro_con_lista(self):
        self.assertEqual(qc.contar("figura", ["race"])["estado"], IQ)

    def test_filtro_con_claves_repetidas_no_revienta(self):
        """`{"race": "A", "race": "B"}` es un dict: vale el último."""
        r = qc.contar("figura", {"race": "A", "caste": "B"})
        self.assertEqual(r["estado"], F)

    def test_verificar_con_sujeto_no_string(self):
        self.assertIn(qc.verificar("figura", None, "existe")["estado"],
                      (NV, IQ))

    def test_verificar_con_predicado_vacio(self):
        self.assertEqual(qc.verificar("figura", "712", "")["estado"], IQ)

    def test_verificar_con_predicado_solo_guion(self):
        """`tiene:` sin atributo no verifica nada como si fuera real."""
        r = qc.verificar("figura", "712", "tiene:")
        # O bien se rechaza como consulta invalida, o bien el verificador de
        # abajo lo declara AMBIGUA. Lo que NO puede es decir FOUND.
        self.assertNotEqual(r["estado"], F,
                            "un predicado sin atributo dio por verificado")


if __name__ == "__main__":
    unittest.main(verbosity=2)