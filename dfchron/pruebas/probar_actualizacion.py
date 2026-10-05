#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del sistema de actualizacion manual de datos
========================================================================

Comprueba los 10 escenarios exigidos, y sobre todo la garantia central:

    si una actualizacion falla, la version activa sigue intacta y disponible.

REGLA DE LAS PRUEBAS
--------------------
Nada de esto toca los datos reales. Cada escenario trabaja sobre un arbol
temporal con XML diminutos, y comprueba despues que el `processed/merged/`
real no ha cambiado.

Uso:  python dfchron/pruebas/probar_actualizacion.py
"""
import os
import sys
import json
import shutil
import hashlib
import tempfile
import unittest

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
_TOOLS = os.path.join(_RAIZ, "00_SOURCE", "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import actualizar_datos as AD  # noqa: E402

REAL_MERGED = os.path.join(_RAIZ, "00_SOURCE", "processed", "merged")

# XML minimos pero ESTRUCTURALMENTE VALIDOS: raiz df_world y las secciones que
# el pipeline necesita. No son datos reales: son fixtures.
XML_OK = """<?xml version="1.0" encoding="UTF-8"?>
<df_world>
  <historical_figures>
    <figure><id>1</id><name>Fixture Dwarf</name><race>62</race></figure>
    <figure><id>2</id><name>Second Dwarf</name><race>62</race></figure>
  </historical_figures>
  <entities><entity><id>10</id><name>Fixture Civ</name><race>62</race></entity></entities>
  <sites><site><id>100</id><name>Fixture Hold</name><type>0</type><civ_id>10</civ_id></site></sites>
  <historical_events>
    <event><id>500</id><year>5</year><type>2</type><site_id>100</site_id></event>
  </historical_events>
  <artifacts><artifact><id>700</id><name>Fixture Sword</name></artifact></artifacts>
  <regions><region><name>Fixture Region</name></region></regions>
</df_world>
"""

XML_ROTO = '<?xml version="1.0"?>\n<df_world><sites><site><id>1</id>\n'

XML_VACIO = ""


def _sha_real():
    """Huella del dataset real, para demostrar que no se toca."""
    if not os.path.isdir(REAL_MERGED):
        return None
    h = hashlib.sha256()
    for nombre in sorted(os.listdir(REAL_MERGED)):
        p = os.path.join(REAL_MERGED, nombre)
        if os.path.isfile(p):
            h.update(nombre.encode())
            with open(p, "rb") as f:
                for bloque in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloque)
    return h.hexdigest()


class Base(unittest.TestCase):
    """Arbol temporal con sus propias entradas, processed/, work/ y backups/."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dfch_act_")
        self.raiz = os.path.join(self.tmp, "datos")
        self.orig = os.path.join(self.raiz, "original_data")
        os.makedirs(self.orig, exist_ok=True)
        self.merged = os.path.join(self.raiz, "processed", "merged")
        self.backups = os.path.join(self.raiz, "backups")
        self.work = os.path.join(self.raiz, "work")
        self.sha_real_antes = _sha_real()
        self._escribir("legends.xml", XML_OK)
        self._escribir("legends_plus.xml", XML_OK)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop(AD.VAR_FALLO, None)

    def _escribir(self, nombre, contenido):
        with open(os.path.join(self.orig, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)

    def actualizar(self, **kw):
        kw.setdefault("origenes", self.orig)
        kw.setdefault("raiz_datos", self.raiz)
        kw.setdefault("merged_destino", self.merged)
        kw.setdefault("work_root", self.work)
        kw.setdefault("backups_root", self.backups)
        return AD.actualizar(**kw)

    def huella(self, carpeta=None):
        """Huella del contenido de `merged`, para comparar versiones."""
        base = carpeta or self.merged
        h = hashlib.sha256()
        if not os.path.isdir(base):
            return None
        for nombre in sorted(os.listdir(base)):
            p = os.path.join(base, nombre)
            if os.path.isfile(p):
                h.update(nombre.encode())
                with open(p, "rb") as f:
                    for bloque in iter(lambda: f.read(1 << 20), b""):
                        h.update(bloque)
        return h.hexdigest()

    def assertRealIntacto(self, msg=""):
        self.assertEqual(_sha_real(), self.sha_real_antes,
                         "el dataset REAL ha cambiado: " + msg)

    def assertApiSirve(self):
        """El nucleo debe poder cargar la version activa."""
        env = dict(os.environ)
        codigo = (
            "import sys, json\n"
            f"sys.path.insert(0, {_TOOLS!r})\n"
            "import rutas\n"
            f"rutas.DATA_ROOT = {self.raiz!r}\n"
            f"rutas.PROCESSED_ROOT = {os.path.join(self.raiz, 'processed')!r}\n"
            f"rutas.MERGED_ROOT = {self.merged!r}\n"
            "import validar_semantica as VS\n"
            f"VS.MERGED = {self.merged!r}\n"
            f"VS.PLUS = {os.path.join(self.raiz, 'processed', 'from_legends_plus')!r}\n"
            "from nucleo import Archivo\n"
            "a = Archivo()\n"
            "print('OK ' + str(len(a.indice.figuras)))\n")
        import subprocess
        p = subprocess.run([sys.executable, "-c", codigo], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=env, cwd=self.tmp)
        self.assertEqual(p.returncode, 0,
                         f"la API no pudo cargar la version activa: {p.stderr[-400:]}")
        return p.stdout.strip()
# =============================================================================
# Escenario 1 - Actualizacion correcta
# =============================================================================
class Test01ActualizacionCorrecta(Base):
    def test_flujo_completo_activa_y_la_api_sirve(self):
        r = self.actualizar()
        self.assertTrue(r["activado"], "deberia activar la version nueva")
        self.assertTrue(os.path.isdir(self.merged), "merged debe existir")
        self.assertApiSirve()
        self.assertRealIntacto("tras una actualizacion correcta")

    def test_genera_las_etapas_basicas(self):
        self.actualizar()
        for nombre in ("historical_figures", "entities", "sites",
                       "historical_events", "artifacts"):
            ruta = os.path.join(self.merged, f"{nombre}.jsonl")
            self.assertTrue(os.path.isfile(ruta), f"falta {nombre}.jsonl")

    def test_registra_version_con_hashes_de_entrada(self):
        self.actualizar()
        v = AD.leer_version(self.raiz)
        self.assertIsNotNone(v, "debe existir dataset_version.json")
        self.assertIn("actualizada", v)
        self.assertEqual(set(v["entradas"]), {"legends.xml", "legends_plus.xml"})
        for meta in v["entradas"].values():
            self.assertEqual(len(meta["sha256"]), 64, "sha256 completo")

    def test_escribe_manifiesto_de_hashes(self):
        self.actualizar()
        ruta = os.path.join(self.merged, "_hashes.json")
        self.assertTrue(os.path.isfile(ruta), "falta _hashes.json")
        with open(ruta, encoding="utf-8") as f:
            doc = json.load(f)
        self.assertIn("historical_figures", doc["secciones"])
        self.assertEqual(len(doc["secciones"]["historical_figures"]["sha256"]), 64)

    def test_los_xml_de_entrada_no_se_modifican(self):
        antes = {n: AD.sha256_de(os.path.join(self.orig, n))
                 for n in ("legends.xml", "legends_plus.xml")}
        self.actualizar()
        despues = {n: AD.sha256_de(os.path.join(self.orig, n))
                   for n in antes}
        self.assertEqual(antes, despues, "los XML de entrada NO pueden cambiar")

    def test_sin_activar_no_toca_la_version_activa(self):
        """--sin-activar genera pero conserva la version en uso."""
        self.actualizar()
        h1 = self.huella()
        r = self.actualizar(activar_nuevo=False)
        self.assertFalse(r["activado"])
        self.assertEqual(self.huella(), h1, "la version activa cambio")

    def test_el_staging_se_limpia_tras_el_exito(self):
        """Nada de basura: el area de trabajo se queda vacia."""
        self.actualizar()
        self.assertFalse(os.path.isdir(self.work) and os.listdir(self.work),
                         "el staging debe borrarse tras activar")

    def test_primera_actualizacion_no_crea_backup_innecesario(self):
        """Sin version previa no hay nada que respaldar: no se crea backup."""
        self.actualizar()
        self.assertFalse(os.path.isdir(self.backups)
                         and os.listdir(self.backups),
                         "la primera actualizacion no debe crear un backup vacio")


# =============================================================================
# Escenario 2 - XML de entrada ausente
# =============================================================================
class Test02EntradaAusente(Base):
    def test_falta_legends_xml(self):
        os.remove(os.path.join(self.orig, "legends.xml"))
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            self.actualizar()
        self.assertIn("legends.xml", str(ctx.exception))
        self.assertFalse(os.path.isdir(self.merged), "no debe activarse nada")

    def test_falta_legends_plus(self):
        os.remove(os.path.join(self.orig, "legends_plus.xml"))
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertFalse(os.path.isdir(self.merged))

    def test_carpeta_originales_inexistente(self):
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar(origenes=os.path.join(self.tmp, "no_existe"))


# =============================================================================
# Escenario 3 - XML ilegible o invalido
# =============================================================================
class Test03XmlInvalido(Base):
    def _con_version_previa(self):
        self.actualizar()

    def test_xml_mal_formado(self):
        self._con_version_previa()
        h = self.huella()
        self._escribir("legends.xml", XML_ROTO)
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertEqual(self.huella(), h, "la version activa debe seguir igual")

    def test_xml_vacio(self):
        self._con_version_previa()
        h = self.huella()
        self._escribir("legends_plus.xml", XML_VACIO)
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            self.actualizar()
        self.assertIn("vac", str(ctx.exception).lower())
        self.assertEqual(self.huella(), h)

    def test_xml_que_no_es_xml(self):
        self._con_version_previa()
        h = self.huella()
        self._escribir("legends.xml", "esto no es un XML en absoluto")
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertEqual(self.huella(), h)

    def test_raiz_correcta_inexistente(self):
        """Un XML bien formado pero con otra raiz debe rechazarse."""
        self._con_version_previa()
        h = self.huella()
        self._escribir("legends.xml",
                       '<?xml version="1.0"?>\n<otra_cosa><x/></otra_cosa>')
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            self.actualizar()
        self.assertIn("df_world", str(ctx.exception))
        self.assertEqual(self.huella(), h)
# =============================================================================
# Escenario 4 - Fallo durante la extraccion
# =============================================================================
class Test04FalloExtraccion(Base):
    def test_extraccion_corrupta_no_toca_la_version_activa(self):
        self.actualizar()
        h = self.huella()
        # Bytes de control y basura: el cargador debe rechazarlo.
        self._escribir("legends.xml", XML_OK[:200] + "\x00\x01\x02" + "</df_world>")
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertEqual(self.huella(), h, "la version activa cambio tras fallar")
        self.assertApiSirve()
        self.assertRealIntacto("tras un fallo de extraccion")

    def test_xml_truncado_a_la_mitad(self):
        self.actualizar()
        h = self.huella()
        completo = XML_OK
        self._escribir("legends.xml", completo[:len(completo) // 2])
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertEqual(self.huella(), h)

    def test_fallo_en_extraccion_via_hook(self):
        self.actualizar()
        h = self.huella()
        os.environ[AD.VAR_FALLO] = "integrar"
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar()
        self.assertEqual(self.huella(), h)
        self.assertApiSirve()


# =============================================================================
# Escenario 5 - Fallo durante la integracion
# =============================================================================
class Test05FalloIntegracion(Base):
    def test_hook_de_integracion_aborta(self):
        self.actualizar()
        h = self.huella()
        os.environ[AD.VAR_FALLO] = "integrar"
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            self.actualizar()
        self.assertIn("integrar", str(ctx.exception))
        self.assertEqual(self.huella(), h, "la version activa cambio")
        self.assertApiSirve()

    def test_fallo_sin_version_previa_no_deja_datos_activados(self):
        os.environ[AD.VAR_FALLO] = "integrar"
        try:
            with self.assertRaises(AD.ErrorActualizacion):
                self.actualizar()
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertFalse(os.path.isdir(self.merged),
                         "no debe existir version activa tras fallar la integracion")

    def test_xml_sin_secciones_minimas_se_rechaza(self):
        vacio = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 "<df_world>\n</df_world>\n")
        d = os.path.join(self.tmp, "vacias")
        os.makedirs(d, exist_ok=True)
        for n in ("legends.xml", "legends_plus.xml"):
            with open(os.path.join(d, n), "w", encoding="utf-8") as f:
                f.write(vacio)
        with self.assertRaises(AD.ErrorActualizacion):
            self.actualizar(origenes=d)
        self.assertFalse(os.path.isdir(self.merged))
# =============================================================================
# Escenario 6 - Fallo durante la validacion
# =============================================================================
class Test06FalloValidacion(Base):
    def test_fallo_en_validacion_aborta_antes_de_activar(self):
        self.actualizar()
        h = self.huella()
        os.environ[AD.VAR_FALLO] = "validar"
        try:
            self.assertRaises(AD.ErrorActualizacion, self.actualizar)
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertEqual(self.huella(), h, "se activo pese al fallo de validacion")
        self.assertApiSirve()

    def test_fallo_al_generar_el_manifiesto_aborta(self):
        self.actualizar()
        h = self.huella()
        os.environ[AD.VAR_FALLO] = "manifiesto"
        try:
            self.assertRaises(AD.ErrorActualizacion, self.actualizar)
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertEqual(self.huella(), h)

    def test_fallo_en_la_comprobacion_posterior_revierte(self):
        """Si la comprobacion post-activacion falla, se vuelve atras.

        Este caso se detecto al escribir las pruebas: la version nueva ya
        estaba activada, y un fallo ahi dejaba el sistema con datos que no
        habian pasado la verificacion. Ahora se revierte automaticamente.
        """
        self.actualizar()
        h = self.huella()
        os.environ[AD.VAR_FALLO] = "verificar"
        try:
            with self.assertRaises(AD.ErrorActualizacion) as ctx:
                self.actualizar()
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertIn("revertido", str(ctx.exception))
        self.assertEqual(self.huella(), h,
                         "deberia haber vuelto a la version anterior")
        AD.verificar_hashes(self.merged)
        self.assertApiSirve()

    def test_estructura_invalida_detectada(self):
        self.actualizar()
        ruta = os.path.join(self.merged, "historical_figures.jsonl")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("{esto no es json}\n")
        self.assertTrue(AD.validar_estructura(self.merged),
                        "deberia detectar el JSONL corrupto")


# =============================================================================
# Escenario 7 - Interrupcion antes de activar
# =============================================================================
class Test07InterrupcionAntesDeActivar(Base):
    def test_staging_generado_no_activado_no_toca_nada(self):
        self.actualizar()
        h = self.huella()
        r = self.actualizar(activar_nuevo=False)
        self.assertFalse(r["activado"])
        self.assertEqual(self.huella(), h, "la version activa no debe cambiar")
        self.assertApiSirve()

    def test_interrumpir_en_cualquier_etapa_conserva_la_version(self):
        """Todos los puntos de fallo previos a la activacion son seguros."""
        for etapa in ("entradas", "preparar", "integrar", "validar", "manifiesto"):
            with self.subTest(etapa=etapa):
                self.actualizar()
                h = self.huella()
                os.environ[AD.VAR_FALLO] = etapa
                try:
                    self.assertRaises(AD.ErrorActualizacion, self.actualizar)
                finally:
                    os.environ.pop(AD.VAR_FALLO, None)
                self.assertEqual(self.huella(), h,
                                 f"la version cambio al fallar en '{etapa}'")
                self.assertApiSirve()

    def test_el_staging_se_borra_al_fallar(self):
        self.actualizar()
        os.environ[AD.VAR_FALLO] = "integrar"
        try:
            self.assertRaises(AD.ErrorActualizacion, self.actualizar)
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertFalse(os.path.isdir(self.work) and os.listdir(self.work),
                         "el staging fallido debe limpiarse")

    def test_se_puede_conservar_el_staging_para_depurar(self):
        os.environ[AD.VAR_FALLO] = "integrar"
        try:
            self.assertRaises(AD.ErrorActualizacion,
                              lambda: self.actualizar(dejar_staging=True))
        finally:
            os.environ.pop(AD.VAR_FALLO, None)
        self.assertTrue(os.listdir(self.work),
                        "con --dejar-staging debe conservarse")
# =============================================================================
# Escenario 8 - Manifiesto de hashes incorrecto
# =============================================================================
class Test08ManifiestoIncorrecto(Base):
    def _manifiesto(self):
        ruta = os.path.join(self.merged, "_hashes.json")
        with open(ruta, encoding="utf-8") as f:
            return ruta, json.load(f)

    def test_hash_manipulado_se_detecta(self):
        self.actualizar()
        ruta, doc = self._manifiesto()
        doc["secciones"]["historical_figures"]["sha256"] = "0" * 64
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            AD.verificar_hashes(self.merged, doc)
        self.assertIn("no coincide", str(ctx.exception))

    def test_fichero_ausente_se_detecta(self):
        """Si una seccion desaparece del manifiesto, se detecta el descuadre."""
        self.actualizar()
        ruta, doc = self._manifiesto()
        doc["secciones"].pop("historical_figures")
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            AD.verificar_hashes(self.merged, doc)
        self.assertIn("historical_figures", str(ctx.exception))

    def test_jsonl_borrado_se_detecta(self):
        self.actualizar()
        os.remove(os.path.join(self.merged, "historical_figures.jsonl"))
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            AD.verificar_hashes(self.merged)
        self.assertIn("no existe", str(ctx.exception))

    def test_manifiesto_ilegible_se_detecta(self):
        self.actualizar()
        ruta = os.path.join(self.merged, "_hashes.json")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("{no es json")
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            AD.verificar_hashes(self.merged)
        self.assertIn("ilegible", str(ctx.exception))

    def test_manifiesto_vacio_se_detecta(self):
        self.actualizar()
        with self.assertRaises(AD.ErrorActualizacion):
            AD.verificar_hashes(self.merged, {"secciones": {}})

    def test_jsonl_adulterado_se_detecta(self):
        self.actualizar()
        ruta = os.path.join(self.merged, "historical_figures.jsonl")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write('{"record_id":"inyectado"}\n')
        with self.assertRaises(AD.ErrorActualizacion):
            AD.verificar_hashes(self.merged)

    def test_version_valida_pasa_la_comprobacion(self):
        self.actualizar()
        AD.verificar_hashes(self.merged)


# =============================================================================
# Escenario 9 - Recuperacion de la version anterior
# =============================================================================
class Test09Recuperacion(Base):
    def test_recuperar_devuelve_la_version_anterior(self):
        self.actualizar()
        h1 = self.huella()
        # Segunda version con OTRO contenido.
        self._escribir("legends.xml", XML_OK.replace(
            "<figure><id>2</id><name>Second Dwarf</name><race>62</race></figure>",
            ""))
        self.actualizar()
        h2 = self.huella()
        self.assertNotEqual(h1, h2, "las dos versiones deben diferir")

        AD.recuperar(self.merged, 0, self.backups)
        self.assertEqual(self.huella(), h1, "no se restauro la version anterior")
        AD.verificar_hashes(self.merged)
        self.assertApiSirve()

    def test_no_se_borran_copias_anteriores(self):
        self.actualizar()
        self.actualizar()
        self.actualizar()
        backups = AD.listar_backups(self.backups)
        self.assertGreaterEqual(len(backups), 2,
                                "cada activacion debe guardar la anterior")

    def test_recuperar_es_tambien_reversible(self):
        self.actualizar()
        h1 = self.huella()
        self._escribir("legends.xml", XML_OK.replace("Fixture Dwarf", "Otro"))
        self.actualizar()
        h2 = self.huella()
        AD.recuperar(self.merged, 0, self.backups)
        self.assertEqual(self.huella(), h1)
        # Recuperar otra vez devuelve la segunda version.
        AD.recuperar(self.merged, 0, self.backups)
        self.assertEqual(self.huella(), h2, "recuperar deberia ser reversible")

    def test_recuperar_sin_copias_falla(self):
        with self.assertRaises(AD.ErrorActualizacion) as ctx:
            AD.recuperar(self.merged, 0, self.backups)
        self.assertIn("copia anterior", str(ctx.exception))

    def test_indice_inexistente_falla(self):
        self.actualizar()
        with self.assertRaises(AD.ErrorActualizacion):
            AD.recuperar(self.merged, 99, self.backups)


# =============================================================================
# Escenario 10 - Segunda actualizacion consecutiva
# =============================================================================
class Test10SegundaActualizacion(Base):
    def test_dos_actualizaciones_seguidas(self):
        r1 = self.actualizar()
        h1 = self.huella()
        v1 = AD.leer_version(self.raiz)

        r2 = self.actualizar()
        h2 = self.huella()
        v2 = AD.leer_version(self.raiz)

        self.assertTrue(r1["activado"] and r2["activado"])
        self.assertNotEqual(v1["actualizada"], v2["actualizada"],
                            "cada version debe llevar su fecha")
        self.assertEqual(v2.get("version_anterior"), v1["actualizada"],
                         "la nueva version debe recordar la anterior")
        self.assertTrue(os.path.isdir(self.backups), "debe existir la copia")
        self.assertApiSirve()
        if h1 != h2:
            self.assertEqual(self.huella(), h2)

    def test_tres_actualizaciones_mantienen_el_rastro(self):
        for i in range(3):
            self._escribir("legends.xml", XML_OK.replace("Fixture Dwarf",
                                                         f"Dwarf {i}"))
            self.actualizar()
        v = AD.leer_version(self.raiz)
        self.assertIn("version_anterior", v)
        backups = AD.listar_backups(self.backups)
        self.assertGreaterEqual(len(backups), 2)
        self.assertApiSirve()
        self.assertRealIntacto("tras tres actualizaciones sobre fixtures")


if __name__ == "__main__":
    unittest.main(verbosity=2)