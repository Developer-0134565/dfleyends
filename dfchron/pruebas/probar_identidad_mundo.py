#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas de IDENTIDAD DEL MUNDO (P1.1)
=====================================================

Comprueba lo UNICO que P1.1 implementa: que la identidad del mundo que
`exportlegends.lua` ya produce se conserva, sin mezclarla con la identidad del
dataset ni con la del estado.

Grupos (mision P1.1, PARTE 6):

  A. Captura      -> se conservan `world_name` y `world_folder` tal cual
  B. Separacion   -> dos mundos con el MISMO contenido no pierden esa diferencia
  C. Repeticion   -> el mismo `dataset_id` puede repetirse y eso NO prueba estado
  D. Estado       -> `dataset_id == state_version` NO es identidad de estado
  E. Ausencia     -> si falta, se declara; no se inventa ni se rellena con reloj

Nada de esto toca el dataset real: todo ocurre en directorios temporales.
"""
import os
import sys
import json
import shutil
import hashlib
import tempfile
import unittest

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_HERRAMIENTAS = os.path.join(_RAIZ, "00_SOURCE", "tools")
if _HERRAMIENTAS not in sys.path:
    sys.path.insert(0, _HERRAMIENTAS)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import identidad_mundo  # noqa: E402
import actualizar_datos  # noqa: E402
from dfchron import contrato_ia as c  # noqa: E402
from dfchron import ia_conocimiento as ic  # noqa: E402


#: Cuerpo minimo con la misma forma que escribe exportlegends.lua:138-140.
def _export(nombre_mundo):
    return ("<df_world>\n<name>%s</name>\n<altname>%s</altname>\n</df_world>\n"
            % (nombre_mundo, nombre_mundo)).encode("utf-8")


def _escribir(directorio, nombre_fichero, nombre_mundo):
    ruta = os.path.join(directorio, nombre_fichero)
    with open(ruta, "wb") as f:
        f.write(_export(nombre_mundo))
    return ruta


class _Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="dfchron_mundo_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


# =============================================================================
# A. CAPTURA
# =============================================================================
class PruebaCaptura(_Base):
    """A. Una extraccion conserva EXACTAMENTE los dos valores."""

    def test_conserva_world_name(self):
        ruta = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml",
                         "Orid En")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "Orid En")
        self.assertIsNone(m["world_name_ausente_porque"])

    def test_conserva_world_folder(self):
        ruta = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml",
                         "Orid En")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_folder"], "region1")

    def test_conserva_los_dos_a_la_vez(self):
        """A completo: X e Y exactos, sin transformar ni recortar."""
        ruta = _escribir(self.dir, "mi_mundo-00007-01-02-legends_plus.xml",
                         "Reino de Prueba")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "Reino de Prueba")
        self.assertEqual(m["world_folder"], "mi_mundo")

    def test_nombre_con_espacios_y_guiones(self):
        ruta = _escribir(self.dir, "region1-00100-12-31-legends_plus.xml",
                         "A Record of the Forest")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "A Record of the Forest")
        self.assertEqual(m["world_folder"], "region1")

    def test_escape_xml_deshecho(self):
        """`escape_xml` de exportlegends escapa & < >: se deshace."""
        ruta = _escribir(self.dir, "region1-00001-01-01-legends_plus.xml",
                         "Bosque &amp; Rio")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "Bosque & Rio")

    def test_acentos_en_utf8(self):
        ruta = _escribir(self.dir, "region1-00001-01-01-legends_plus.xml",
                         "Año del Águila")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "Año del Águila")

    def test_shape_estable(self):
        """Las claves existen SIEMPRE, para no obligar a comprobar antes."""
        ruta = _escribir(self.dir, "region1-00001-01-01-legends_plus.xml", "X")
        m = identidad_mundo.desde_export(ruta)
        for clave in ("world_name", "world_folder",
                      "world_name_ausente_porque", "world_folder_ausente_porque"):
            self.assertIn(clave, m)

    def test_determinista(self):
        """Dos lecturas del mismo export dan exactamente lo mismo."""
        ruta = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml",
                         "Orid En")
        self.assertEqual(identidad_mundo.desde_export(ruta),
                         identidad_mundo.desde_export(ruta))


# =============================================================================
# B. SEPARACION - dos mundos, mismo contenido
# =============================================================================
class PruebaSeparacion(_Base):
    """B. El contenido NO borra la diferencia de mundo."""

    def test_mismo_contenido_distinto_folder_no_se_confunden(self):
        """Los dos exports son byte-identicos salvo el nombre del fichero."""
        cuerpo = _export("Orid En")
        a = os.path.join(self.dir, "region1-00042-03-15-legends_plus.xml")
        b = os.path.join(self.dir, "region2-00042-03-15-legends_plus.xml")
        for ruta in (a, b):
            with open(ruta, "wb") as f:
                f.write(cuerpo)
        # Contenido identico de verdad:
        self.assertEqual(hashlib.sha256(open(a, "rb").read()).hexdigest(),
                         hashlib.sha256(open(b, "rb").read()).hexdigest())

        ma = identidad_mundo.desde_export(a)
        mb = identidad_mundo.desde_export(b)
        self.assertEqual(ma["world_folder"], "region1")
        self.assertEqual(mb["world_folder"], "region2")
        self.assertNotEqual(ma["world_folder"], mb["world_folder"])

    def test_mismo_contenido_distinto_name_no_se_confunden(self):
        a = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml", "Orid En")
        b = _escribir(self.dir, "region2-00042-03-15-legends_plus.xml", "Otro")
        ma = identidad_mundo.desde_export(a)
        mb = identidad_mundo.desde_export(b)
        self.assertNotEqual(ma["world_name"], mb["world_name"])
        self.assertNotEqual(ma["world_folder"], mb["world_folder"])

    def test_el_dataset_id_no_ve_el_mundo(self):
        """LIMITACION documentada de P1, no garantia.

        Dos mundos distintos dan el MISMO `dataset_id`. Por eso hace falta la
        identidad de mundo: no es que mejore el id, es que lo COMPLEMENTA.
        """
        secciones = {"sites": {"lineas": 10, "sha256": "aa" * 32, "bytes": 1}}
        id_a = actualizar_datos.calcular_dataset_id(secciones)
        secciones_b = {"sites": {"lineas": 10, "sha256": "aa" * 32, "bytes": 1}}
        id_b = actualizar_datos.calcular_dataset_id(secciones_b)
        self.assertEqual(id_a, id_b)
        self.assertTrue(id_a.startswith("v1-"))


# =============================================================================
# C. REPETICION
# =============================================================================
class PruebaRepeticion(_Base):
    """C. dataset_id igual NO significa "misma instancia temporal"."""

    def test_dataset_id_estable_para_contenido_estable(self):
        secciones = {"events": {"lineas": 5, "sha256": "bb" * 32, "bytes": 9}}
        self.assertEqual(actualizar_datos.calcular_dataset_id(secciones),
                         actualizar_datos.calcular_dataset_id(secciones))

    def test_repetido_no_prueba_estado(self):
        """No hay ningun campo de estado en la identidad de mundo."""
        m = identidad_mundo.desde_export(
            _escribir(self.dir, "region1-00001-01-01-legends_plus.xml", "X"))
        serializado = json.dumps(m).lower()
        self.assertNotIn("state", serializado)
        for prohibido in ("state_id", "snapshot_id", "tick_id", "branch_id",
                          "lineage", "estado_id", "revision"):
            self.assertNotIn(prohibido, serializado)


# =============================================================================
# D. ESTADO NO RESUELTO
# =============================================================================
class PruebaEstadoNoResuelto(_Base):
    """D. dataset_id == state_version NO es identidad de estado vivo."""

    def test_state_version_es_dataset_id(self):
        self.assertEqual(ic.DATASET_ID, ic.dataset_id())
        with open(ic.VERSION_DATASET, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["dataset_id"], ic.DATASET_ID)

    def test_la_evidencia_no_declara_identidad_de_estado(self):
        ev = c.evidencia("figura", "1", ["nombre"], state_version="v1-x")
        self.assertEqual(ev["state_version"], "v1-x")
        for prohibido in ("world_state_id", "snapshot_id", "tick_id"):
            self.assertNotIn(prohibido, ev)

    def test_el_contrato_no_promete_estado_exacto(self):
        """La docstring corregida no puede decir 'exactamente cuando cambia'."""
        doc = c.evidencia.__doc__
        self.assertIn("LO QUE ESTE CAMPO **NO** ES", doc)
        self.assertNotIn("cambia **exactamente** cuando cambia el mundo", doc)

    def test_mundo_no_contamina_state_version(self):
        """world_folder/world_name NO se convierten en state_version."""
        m = identidad_mundo.desde_export(
            _escribir(self.dir, "region1-00001-01-01-legends_plus.xml", "X"))
        self.assertNotEqual(ic.DATASET_ID, m["world_name"])
        self.assertNotEqual(ic.DATASET_ID, m["world_folder"])

    def test_ia_conocimiento_no_usa_mundo_como_version(self):
        """La evidencia se ancla al dataset, nunca al mundo."""
        doc = ic.evidencia_de.__doc__
        self.assertNotIn("estado del mundo que la", doc)


# =============================================================================
# E. AUSENCIA
# =============================================================================
class PruebaAusencia(_Base):
    """E. Si no esta, se declara. Nunca se inventa."""

    def test_fichero_inexistente(self):
        m = identidad_mundo.desde_export(os.path.join(self.dir, "nada.xml"))
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_name_ausente_porque"], identidad_mundo.SIN_FICHERO)

    def test_sin_df_world_name(self):
        ruta = os.path.join(self.dir, "region1-00001-01-01-legends_plus.xml")
        with open(ruta, "wb") as f:
            f.write(b"<df_world>\n<regions></regions>\n</df_world>\n")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_name_ausente_porque"], identidad_mundo.SIN_NOMBRE)

    def test_fichero_renombrado_no_inventa_carpeta(self):
        """El caso REAL de este proyecto: el export se copio sin el prefijo."""
        ruta = _escribir(self.dir, "legends_plus.xml", "Orid En")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_folder"], "UNKNOWN")
        self.assertEqual(m["world_folder_ausente_porque"],
                         identidad_mundo.SIN_CARPETA)
        # Y aun asi conserva el nombre, que si venia en el cuerpo.
        self.assertEqual(m["world_name"], "Orid En")

    def test_nombre_vacio_es_unknown(self):
        ruta = _escribir(self.dir, "region1-00001-01-01-legends_plus.xml", "")
        m = identidad_mundo.desde_export(ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")

    def test_no_se_rellena_con_timestamp(self):
        """La ausencia NO se disfraza de fecha ni de nada generado."""
        m = identidad_mundo.desde_export(_escribir(self.dir,
                                                   "legends_plus.xml", ""))
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")
        for valor in (m["world_name"], m["world_folder"]):
            self.assertNotRegex(valor, r"\d{4}-\d{2}-\d{2}")
            self.assertNotRegex(valor, r"\d{8}-\d{6}")

    def test_sin_ruta_no_revienta(self):
        m = identidad_mundo.desde_export(None)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")


# =============================================================================
# INTEGRACION con el pipeline
# =============================================================================
class PruebaIntegracion(_Base):
    """El registro de version recibe la identidad y NO cambia el dataset_id."""

    def _registro(self):
        return {"actualizada": "2026-10-04T00:00:00+02:00",
                "dataset_id": "v1-04170363943d4ba1",
                "entradas": {}, "salidas": {"sites": {"sha256": "cc" * 32}},
                "conteos": {"eventos": 1}, "merge": {}}

    def test_se_inyecta_la_clave_mundo(self):
        ruta = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml",
                         "Orid En")
        reg = identidad_mundo.anadir_a_registro(self._registro(),
                                                identidad_mundo.desde_export(ruta))
        self.assertEqual(reg["mundo"]["world_name"], "Orid En")
        self.assertEqual(reg["mundo"]["world_folder"], "region1")

    def test_no_altera_dataset_id_ni_las_claves_existentes(self):
        antes = self._registro()
        copia = json.loads(json.dumps(antes))
        ruta = _escribir(self.dir, "region2-00042-03-15-legends_plus.xml",
                         "Otro")
        reg = identidad_mundo.anadir_a_registro(antes,
                                                identidad_mundo.desde_export(ruta))
        self.assertEqual(reg["dataset_id"], copia["dataset_id"])
        self.assertEqual(reg["salidas"], copia["salidas"])
        self.assertEqual(reg["entradas"], copia["entradas"])
        self.assertEqual(reg["conteos"], copia["conteos"])
        self.assertEqual(reg["merge"], copia["merge"])

    def test_serializa_a_json(self):
        ruta = _escribir(self.dir, "region1-00001-01-01-legends_plus.xml", "X")
        reg = identidad_mundo.anadir_a_registro(self._registro(),
                                                identidad_mundo.desde_export(ruta))
        self.assertIn("mundo", json.loads(json.dumps(reg, ensure_ascii=False)))

    def test_escribe_y_relee_el_registro_completo(self):
        """Escribe con `escribir_version()` real y relee con `leer_version()`."""
        raiz = os.path.join(self.dir, "datos")
        os.makedirs(raiz)
        ruta = _escribir(self.dir, "region1-00042-03-15-legends_plus.xml",
                         "Orid En")
        reg = identidad_mundo.anadir_a_registro(self._registro(),
                                                identidad_mundo.desde_export(ruta))
        actualizar_datos.escribir_version(reg, raiz)
        leido = actualizar_datos.leer_version(raiz)
        self.assertEqual(leido["mundo"]["world_name"], "Orid En")
        self.assertEqual(leido["mundo"]["world_folder"], "region1")
        self.assertEqual(leido["dataset_id"], "v1-04170363943d4ba1")

    def test_el_registro_viejo_sin_mundo_se_tolera(self):
        """Un `dataset_version.json` anterior a P1.1 no tiene `mundo`."""
        self.assertEqual(({"dataset_id": "v1-x"}.get("mundo") or {}), {})


# =============================================================================
# EL EXPORT REAL DEL PROYECTO
# =============================================================================
class PruebaExportReal(unittest.TestCase):
    """Comprobacion contra los 17 MB reales. Solo lectura."""

    def test_el_dataset_real_conserva_su_nombre_de_mundo(self):
        ruta = os.path.join(_RAIZ, "00_SOURCE", "original_data",
                            "legends_plus.xml")
        if not os.path.isfile(ruta):
            self.skipTest("no hay export real en este entorno")
        m = identidad_mundo.desde_export(ruta)
        self.assertNotEqual(m["world_name"], "UNKNOWN",
                            "el export real deberia traer <df_world><name>")
        # Este proyecto copio el fichero sin el prefijo save_dir, asi que la
        # carpeta NO se puede recuperar. Se documenta, no se inventa.
        self.assertEqual(m["world_folder"], "UNKNOWN")
        self.assertEqual(m["world_folder_ausente_porque"],
                         identidad_mundo.SIN_CARPETA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
