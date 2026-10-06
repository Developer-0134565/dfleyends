#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del núcleo de consulta
================================================

Comprueba que las consultas devuelven los VALORES CORRECTOS, no solo que no
lancan excepciones. Reutiliza los fixtures de la Fase 2.

Ejecutar:  python probar_nucleo.py
"""
import os
import sys
import json
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nucleo import Archivo, ANIO_MIN, ANIO_MAX  # noqa: E402
from validar_semantica import FACT, DERIVED, UNKNOWN  # noqa: E402

VALID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "processed", "validation")

_AR = None
_TIEMPOS = {}


def ar():
    """Archivo compartido: cargar 57k eventos es costoso."""
    global _AR
    if _AR is None:
        t0 = time.perf_counter()
        _AR = Archivo()
        _TIEMPOS["carga"] = time.perf_counter() - t0
    return _AR


def fixture(nombre):
    with open(os.path.join(VALID, nombre), encoding="utf-8") as f:
        return json.load(f)


def cronometrar(clave, fn):
    t0 = time.perf_counter()
    r = fn()
    _TIEMPOS[clave] = _TIEMPOS.get(clave, 0) + (time.perf_counter() - t0)
    return r


class TestCarga(unittest.TestCase):
    """El archivo carga los conteos conocidos de la Fase 2."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_conteos_correctos(self):
        self.assertEqual(len(self.a.indice.figuras), 11144)
        self.assertEqual(len(self.a.indice.entidades), 1067)
        self.assertEqual(len(self.a.indice.sitios), 734)
        self.assertEqual(len(self.a.indice.eventos), 57215)
        self.assertEqual(len(self.a.indice.artefactos), 427)
        self.assertEqual(len(self.a.indice.relaciones), 13192)

    def test_ids_son_cadenas_de_df(self):
        for d in self.a.indice.figuras:
            self.assertIsInstance(d, str)
            break
        self.assertIn("0", self.a.indice.figuras)

    def test_geografia_cargada(self):
        g = self.a.geografia()
        self.assertEqual(g["rivers"]["registros"], 2346)
        self.assertEqual(g["landmasses"]["registros"], 40)
        self.assertEqual(g["mountain_peaks"]["registros"], 4)
        self.assertEqual(g["world_constructions"]["registros"], 122)


class TestConsultaPorID(unittest.TestCase):
    """Consulta por ID: valores concretos, no solo 'no lanza excepción'."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()
        cls.fig = cls.a.ficha_figura("712")

    def test_figura_712_valores_reales(self):
        self.assertEqual(self.fig["df_id"], "712")
        self.assertEqual(self.fig["nombre"], "galka shafttop the blades of knighting")
        self.assertEqual(self.fig["race"], "MINOTAUR")
        self.assertEqual(self.fig["certainty"], FACT)

    def test_figura_tiene_158_eventos(self):
        self.assertEqual(len(self.fig["acontecimientos"]), 158)

    def test_cronologia_ordenada(self):
        cr = self.fig["cronologia"]
        anios = [e["año"] for e in cr["linea_temporal"] if e["año"] is not None]
        self.assertEqual(anios, sorted(anios), "la cronología debe estar ordenada")

    def test_entidad_asociada_resuelve(self):
        ent = self.fig["entidad"]
        self.assertEqual(ent["df_id"], 312)
        self.assertEqual(ent["nombre"], "the infamous disloyalty")
        self.assertEqual(ent["tipo"], "civilization")

    def test_entidad_miembros(self):
        m = cronometrar("entidad_miembros", lambda: self.a.miembros_entidad("282"))
        self.assertEqual(m["nombre"], "the curled diamond")
        self.assertEqual(m["total"], 25)
        for f in m["miembros"]:
            self.assertNotEqual(f["nombre"], UNKNOWN)

    def test_sitio_87_valores(self):
        s = cronometrar("sitio", lambda: self.a.ficha_sitio("87"))
        self.assertEqual(s["nombre"], "halesteel")
        self.assertEqual(s["tipo"], "fortress")
        self.assertEqual(s["coordenadas"], [(112, 20)])
        self.assertEqual(s["civilizacion"]["df_id"], 294)
        self.assertEqual(s["eventos"], 1546)

    def test_artefacto_con_creador(self):
        a = ar()
        for df_id, creator in list(a.creador_artefacto.items())[:1]:
            f = a.ficha_artefacto(df_id)
            self.assertEqual(f["creador"]["figura_id"], creator)
            self.assertNotEqual(f["creador"]["nombre"], UNKNOWN)
            self.assertEqual(f["creador"]["certainty"], FACT)
class TestConsultaPorNombre(unittest.TestCase):
    """Búsqueda por nombre, con detección de ambigüedad."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_buscar_exito_devuelve_la_figura_correcta(self):
        r = cronometrar("busqueda", lambda: self.a.buscar_figura("galka shafttop"))
        self.assertIn("712", r["ids"])
        nombres = [f["nombre"] for f in r["fichas"]]
        self.assertIn("galka shafttop the blades of knighting", nombres)

    def test_busqueda_ambigua_no_elige(self):
        """Con varias coincidencias el sistema NO selecciona una."""
        r = self.a.buscar_figura("the")
        self.assertTrue(r["consulta_ambigua"],
                        "con 'the' debe haber múltiples coincidencias")
        self.assertGreater(len(r["ids"]), 1)

    def test_busqueda_sin_resultados(self):
        r = self.a.buscar_figura("zzzqqqxxxnoexiste")
        self.assertEqual(r["ids"], [])
        self.assertFalse(r["consulta_ambigua"])

    def test_busqueda_sitio(self):
        r = self.a.buscar_sitio("halesteel")
        self.assertIn("87", r["ids"])
        self.assertFalse(r["consulta_ambigua"])

    def test_busqueda_entidad(self):
        r = self.a.buscar_entidad("curled diamond")
        self.assertIn("282", r["ids"])

    def test_busqueda_artefacto(self):
        r = self.a.buscar_artefacto("wave of prairies")
        self.assertTrue(len(r["ids"]) >= 1)


class TestReferenciasCruzadas(unittest.TestCase):
    """FIGURA → EVENTOS → SITIOS → ENTIDADES."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_recorrido_completo_figura(self):
        evs = self.a.eventos_de_figura("712")
        self.assertEqual(len(evs), 158)
        con_sitio = [e for e in evs if e["sitio_nombre"] != UNKNOWN]
        self.assertTrue(con_sitio, "debe haber eventos con sitio resuelto")
        self.assertEqual(con_sitio[0]["sitio_nombre"], "faintflies")
        with_ent = [e for e in evs if e["entidad_nombre"] != UNKNOWN]
        self.assertTrue(with_ent, "debe haber eventos con entidad resuelta")

    def test_sitio_lista_figuras(self):
        s = self.a.ficha_sitio("87")
        self.assertEqual(s["figuras_asociadas"], 48)
        self.assertEqual(len(s["figuras"]), 48)

    def test_artefactos_de_figura(self):
        a = self.a
        con_art = list(a.indice.art_por_hf)
        self.assertTrue(con_art, "debe haber figuras con artefactos")
        arts = a.artefactos_de_figura(con_art[0])
        for art in arts:
            self.assertNotEqual(art["nombre"], UNKNOWN)

    def test_relaciones_conectan_figuras_existentes(self):
        """Las 13.192 relaciones conectan dos figuras reales."""
        a = self.a
        for rel in a.indice.relaciones[:200]:
            s = str(rel["campos"]["source_hf"]["valor"])
            t = str(rel["campos"]["target_hf"]["valor"])
            self.assertIn(s, a.indice.figuras, f"source_hf {s} no existe")
            self.assertIn(t, a.indice.figuras, f"target_hf {t} no existe")

    def test_relaciones_no_se_asocian_a_eventos_ausentes(self):
        """Las relaciones conservan event_id pero no lo inventan como evento."""
        a = ar()
        for rel in a.relaciones_de_figura("1156")["relaciones"]:
            self.assertFalse(rel["evento_existe"],
                             "no debe asociarse a un evento inexistente")
            self.assertNotIn(rel["evento_id"], a.indice.eventos)


class TestCronologia(unittest.TestCase):
    """Ordenación y límites temporales."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_eventos_entre_anios(self):
        r = cronometrar("cronologia", lambda: self.a.eventos_entre_anios(1, 3))
        self.assertEqual(r["desde"], 1)
        self.assertEqual(r["hasta"], 3)
        self.assertEqual(r["total"], 1462)
        for e in r["eventos"]:
            self.assertTrue(1 <= e["año"] <= 3)

    def test_rango_ordenado_por_anio_y_segundos(self):
        r = self.a.eventos_entre_anios(20, 30)
        claves = [(e["año"], e["segundos72"] if e["segundos72"] is not None else -1)
                  for e in r["eventos"]]
        self.assertEqual(claves, sorted(claves))

    def test_eventos_del_anio(self):
        r = self.a.eventos_del_anio(1)
        self.assertEqual(r["anio"], 1)
        for e in r["eventos"]:
            self.assertEqual(e["año"], 1)

    def test_anio_fuera_de_rango_es_unknown(self):
        r = self.a.eventos_del_anio(500)
        self.assertEqual(r["certainty"], UNKNOWN)
        self.assertIn("motivo", r)

    def test_cronologia_entidad(self):
        c = self.a.cronologia_entidad("282")
        self.assertEqual(c["nombre"], "the curled diamond")
        self.assertEqual(c["total_eventos"], 769)
        anios = [e["año"] for e in c["linea_temporal"] if e["año"] is not None]
        self.assertEqual(anios, sorted(anios))

    def test_cronologia_sitio(self):
        c = self.a.cronologia_sitio("87")
        self.assertEqual(c["nombre"], "halesteel")
        self.assertTrue(c["total_eventos"] > 0)
class TestRelacionesSociales(unittest.TestCase):
    """Tipos literales del XML; sin asociación a eventos ausentes."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_tipos_disponibles_son_los_del_xml(self):
        t = self.a.tipos_relacion_disponibles()
        self.assertEqual(t["total_relaciones"], 13192)
        for k, val in (("childhood_friend", 6106), ("lover", 4728),
                       ("former_lover", 1591), ("war_buddy", 562)):
            self.assertEqual(t["tipos"][k], val)

    def test_consultar_amigos(self):
        for rel in self.a.amigos("712")["relaciones"]:
            self.assertEqual(rel["tipo"], "childhood_friend")

    def test_consultar_por_tipo_generico(self):
        for rel in self.a.relaciones_de_figura("1156", "jealous_obsession")["relaciones"]:
            self.assertEqual(rel["tipo"], "jealous_obsession")

    def test_figura_sin_relaciones_no_inventa(self):
        r = self.a.relaciones_de_figura("0")
        self.assertEqual(r["total"], 0)
        self.assertEqual(r["relaciones"], [])


class TestConflictos(unittest.TestCase):
    """Agrupaciones DERIVED; nunca guerras confirmadas."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_eventos_de_enfrentamiento(self):
        c = cronometrar("conflictos", lambda: self.a.conflictos())
        self.assertEqual(c["certainty"], DERIVED)
        self.assertTrue(c["eventos_de_enfrentamiento"] > 0)
        self.assertIn("NO demuestra guerras", c["advertencia"])

    def test_subtipos_conocidos(self):
        c = self.a.conflictos()
        self.assertEqual(c["por_subtipo"].get("attacked"), 2733)
        self.assertEqual(c["por_subtipo"].get("scuffle"), 1906)
        self.assertEqual(c["por_subtipo"].get("ambushed"), 428)

    def test_muertes_por_conflicto(self):
        m = self.a.muertes_por_conflicto()
        self.assertEqual(m["por_causa"].get("struck"), 3687)
        self.assertEqual(m["por_causa"].get("old age"), None)

    def test_no_declara_guerras(self):
        c = self.a.conflictos()
        self.assertNotIn("guerra", str(c["eventos"]).lower())


class TestCasosSinDatos(unittest.TestCase):
    """IDs inexistentes y datos ausentes."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_figura_inexistente(self):
        f = self.a.ficha_figura("99999999")
        self.assertEqual(f["certainty"], UNKNOWN)
        self.assertIn("motivo", f)

    def test_entidad_inexistente(self):
        self.assertEqual(self.a.ficha_entidad("99999999")["certainty"], UNKNOWN)

    def test_sitio_inexistente(self):
        self.assertEqual(self.a.ficha_sitio("99999999")["certainty"], UNKNOWN)

    def test_artefacto_inexistente(self):
        self.assertEqual(self.a.ficha_artefacto("99999999")["certainty"], UNKNOWN)

    def test_nombre_inexistente(self):
        self.assertEqual(self.a.buscar_figura("noexistenadaconeste")["ids"], [])

    def test_consulta_vacia(self):
        self.assertEqual(self.a.buscar("")["certainty"], UNKNOWN)


class TestExportacion(unittest.TestCase):
    """Exportación a JSON y Markdown, siempre con fuentes."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_exportar_json_incluye_fuentes(self):
        obj = json.loads(self.a.exportar_historia_figura("712", "json"))
        self.assertIn("legends.xml", obj["fuentes"])
        self.assertIn("legends_plus.xml", obj["fuentes"])
        self.assertEqual(obj["datos"]["df_id"], "712")

    def test_exportar_markdown_incluye_fuentes(self):
        md = self.a.exportar_historia_figura("712", "markdown")
        self.assertIn("legends.xml", md)
        self.assertIn("galka shafttop", md)
        self.assertIn("Certeza global", md)

    def test_exportar_a_archivo(self):
        import tempfile
        ruta = os.path.join(tempfile.gettempdir(), "dfch_test_fig712.md")
        self.a.exportar_historia_figura("712", "markdown", ruta)
        self.assertTrue(os.path.exists(ruta))
        with open(ruta, encoding="utf-8") as f:
            self.assertIn("galka shafttop", f.read())
        os.remove(ruta)

    def test_markdown_figura_inexistente(self):
        md = self.a.exportar_markdown(self.a.ficha_figura("99999999"), "inexistente")
        self.assertIn("Sin datos", md)


class TestFixtures(unittest.TestCase):
    """Reutiliza los fixtures de la Fase 2."""

    def test_figures_sample_es_consultable(self):
        datos = fixture("figures_sample.json")
        self.assertEqual(datos["certainty"], FACT)
        self.assertGreaterEqual(len(datos["figuras"]), 10)
        for f in datos["figuras"]:
            ficha = ar().ficha_figura(f["df_id"], breve=True)
            self.assertEqual(ficha["nombre"], f["nombre"])

    def test_sites_sample_es_consultable(self):
        for s in fixture("sites_sample.json")["sitios"]:
            ficha = ar().ficha_sitio(s["df_id"], breve=True)
            self.assertEqual(ficha["nombre"], s["nombre"])


class TestRendimiento(unittest.TestCase):
    """Mide tiempos reales de consulta."""

    def test_tiempos_de_consulta(self):
        a = ar()
        cronometrar("ficha_figura", lambda: a.ficha_figura("712"))
        cronometrar("busqueda", lambda: a.buscar_figura("galka"))
        cronometrar("eventos_anios", lambda: a.eventos_entre_anios(20, 30))
        print("\n  === TIEMPOS (segundos) ===")
        print(f"  carga inicial      : {_TIEMPOS.get('carga', 0):.3f}")
        for k, val in sorted(_TIEMPOS.items()):
            if k != "carga":
                print(f"  {k:<18}: {val:.4f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
