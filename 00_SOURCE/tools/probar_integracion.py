#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Prueba de integración de Legends
=================================================

Verifica que la integración de `legends.xml` + `legends_plus.xml` es correcta.

Ejecutar:  python probar_integracion.py
Devuelve 0 si todo pasa. Nunca modifica los XML originales.
"""
import os
import sys
import json
import hashlib
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import integrar_legends as IL  # noqa: E402
from cargar_legends import cargar_legends  # noqa: E402

# SHA-256 conocidos (verificados antes y después de la integración)
SHA_LEGENDS = "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f"
SHA_PLUS = "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d"

# Conteos esperados, establecidos por la verificación previa de los XML
ESPERADO_PLUS = {
    "historical_event_relationships": 13192,
    "rivers": 2346,
    "landmasses": 40,
    "mountain_peaks": 4,
    "world_constructions": 122,
    "identities": 475,
    "creature_raw": 1321,
    "historical_event_relationship_supplements": 21,
}
ESPERADO_LEGENDS = {
    "regions": 840, "underground_regions": 405, "sites": 734,
    "artifacts": 427, "historical_figures": 11144, "entity_populations": 243,
    "entities": 1067, "historical_events": 57215,
    "historical_event_collections": 6544, "historical_eras": 1,
    "written_contents": 2341, "poetic_forms": 95, "musical_forms": 104,
    "dance_forms": 107,
}

_cache = {}


def sesion(clave):
    if "s" not in _cache:
        _cache["s"] = {"l": cargar_legends(IL.ORIG_LEGENDS),
                       "p": cargar_legends(IL.ORIG_PLUS)}
    return _cache["s"][clave]


def cuenta_lineas_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def sha256_de(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class TestLectura(unittest.TestCase):
    """1-5: lectura, raíz y decodificación correcta de ambos XML."""

    def test_01_ambos_xml_se_leen(self):
        self.assertIsNone(sesion("l").error, "legends.xml no debe dar error")
        self.assertIsNone(sesion("p").error, "legends_plus.xml no debe dar error")

    def test_02_raiz_df_world(self):
        self.assertEqual(sesion("l").raiz.tag, "df_world")
        self.assertEqual(sesion("p").raiz.tag, "df_world")

    def test_03_legends_xml_decodifica_cp437(self):
        r = sesion("l")
        self.assertEqual(r.codificacion.lower().replace("-sig", ""), "cp437")
        r.bruto.decode("cp437")  # mapea los 256 bytes: no debe lanzar

    def test_04_legends_plus_decodifica_utf8(self):
        r = sesion("p")
        self.assertTrue(r.codificacion.lower().startswith("utf-8"))
        r.bruto.decode("utf-8")

    def test_05_bytes_de_control_solo_en_legends(self):
        self.assertTrue(sesion("l").requiere_saneo)
        self.assertEqual(sesion("p").bytes_control, {})


class TestConteos(unittest.TestCase):
    """6-10: los conteos exigidos por el encargo."""

    def test_06_relationships_13192(self):
        self.assertEqual(
            len(sesion("p").secciones()["historical_event_relationships"]), 13192)

    def test_07_rivers_2346(self):
        self.assertEqual(len(sesion("p").secciones()["rivers"]), 2346)

    def test_08_landmasses_40_y_peaks_4(self):
        s = sesion("p").secciones()
        self.assertEqual(len(s["landmasses"]), 40)
        self.assertEqual(len(s["mountain_peaks"]), 4)

    def test_09_world_constructions_122(self):
        self.assertEqual(len(sesion("p").secciones()["world_constructions"]), 122)

    def test_10_conteos_legends_xml(self):
        s = sesion("l").secciones()
        for sec, n in ESPERADO_LEGENDS.items():
            self.assertEqual(len(s[sec]), n, f"{sec}: esperado {n}, real {len(s[sec])}")
class TestIntegridad(unittest.TestCase):
    """11-13: originales intactos, IDs estables, sin duplicados silenciosos."""

    def test_11_originales_no_modificados(self):
        self.assertEqual(sha256_de(IL.ORIG_LEGENDS), SHA_LEGENDS,
                         "legends.xml fue modificado")
        self.assertEqual(sha256_de(IL.ORIG_PLUS), SHA_PLUS,
                         "legends_plus.xml fue modificado")

    def test_12_copias_en_original_data_identicas(self):
        for nombre, esperado in (("legends.xml", SHA_LEGENDS),
                                 ("legends_plus.xml", SHA_PLUS)):
            ruta = os.path.join(IL.ORIG_DIR, nombre)
            self.assertTrue(os.path.exists(ruta), f"falta la copia {nombre}")
            self.assertEqual(sha256_de(ruta), esperado,
                             f"la copia archivada de {nombre} difiere")

    def test_13_ids_originales_intactos(self):
        """Los df_id de legends.xml se conservan sin alteración."""
        s = sesion("l").secciones()
        hf = [e.findtext("id") for e in s["historical_figures"]]
        self.assertEqual(len(hf), 11144)
        self.assertEqual(hf[0], "0")
        self.assertEqual(hf[-1], "11143")
        ev = [e.findtext("id") for e in s["historical_events"]]
        self.assertEqual(len(ev), 57215)
        self.assertEqual(len(set(ev)), 57215, "no debe haber ids duplicados")


class TestMerge(unittest.TestCase):
    """14-19: reglas de merge y política sobre los 13.192 eventos."""

    def setUp(self):
        with open(os.path.join(IL.PROC_MERGED, "_manifiesto.json"),
                  encoding="utf-8") as f:
            self.m = json.load(f)

    def test_14_huerfanas_no_materializadas(self):
        """Los ids ausentes NO deben existir como filas de evento."""
        ev = self.m["eventos"]
        self.assertEqual(ev["historical_events"], 57215)
        self.assertEqual(ev["ids_ausentes_en_historical_events"], 13192)
        ruta = os.path.join(IL.PROC_MERGED, "historical_events.jsonl")
        self.assertEqual(cuenta_lineas_jsonl(ruta), 57215,
                         "historical_events.jsonl no debe incluir los ids ausentes")
        rel = os.path.join(IL.PROC_MERGED, "historical_event_relationships.jsonl")
        self.assertEqual(cuenta_lineas_jsonl(rel), 13192)

    def test_15_relationships_son_relaciones_no_eventos(self):
        ruta = os.path.join(IL.PROC_MERGED, "historical_event_relationships.jsonl")
        with open(ruta, encoding="utf-8") as f:
            primera = json.loads(f.readline())
        for clave in ("event_id", "event_existe_en_historical_events",
                      "source_section", "certainty"):
            self.assertIn(clave, primera)
        self.assertEqual(primera["source_section"], "historical_event_relationships")
        self.assertEqual(primera["certainty"], "FACT")

    def test_16_campos_con_procedencia(self):
        """Todo campo fusionado lleva source y source_section."""
        ruta = os.path.join(IL.PROC_MERGED, "historical_figures.jsonl")
        with open(ruta, encoding="utf-8") as f:
            fila = json.loads(f.readline())
        self.assertTrue(fila["campos"])
        for campo, meta in fila["campos"].items():
            self.assertIn("source", meta, f"campo {campo} sin source")
            self.assertIn("source_section", meta, f"campo {campo} sin source_section")
            self.assertIn(meta["source"], ("legends.xml", "legends_plus.xml"))

    def test_17_vacio_de_plus_no_pisa_primaria(self):
        """Ningún valor de legends.xml se pierde ni se pisa con un vacío de plus.

        legends.xml tiene campos genuinamente vacíos en el XML original
        (elementos autoconcluyentes como <deity />). La comprobación correcta
        es de PARIDAD: merged debe conservar exactamente los mismos vacíos
        que el original, no que no haya ninguno.
        """
        import collections
        # vacíos reales en el ORIGINAL
        orig = collections.Counter()
        for sec in IL.COMPARTIDAS:
            for el in sesion("l").secciones().get(sec, []):
                for k, v in IL._campos(el).items():
                    if k != "id" and v == "":
                        orig[sec] += 1
        # vacíos en MERGED atribuidos a legends.xml
        merged = collections.Counter()
        for sec in IL.COMPARTIDAS:
            ruta = os.path.join(IL.PROC_MERGED, f"{sec}.jsonl")
            if not os.path.exists(ruta):
                continue
            with open(ruta, encoding="utf-8") as f:
                for linea in f:
                    fila = json.loads(linea)
                    if not fila["en_legends_xml"]:
                        continue
                    for meta in fila["campos"].values():
                        if meta["source"] == "legends.xml" and meta["valor"] == "":
                            merged[sec] += 1
        self.assertEqual(dict(orig), dict(merged),
                         "los vacíos de legends.xml deben conservarse sin cambios")

    def test_17b_no_hay_campos_solo_de_plus_vacios(self):
        """plus no debe introducir campos vacíos."""
        for sec in ("historical_figures", "sites"):
            ruta = os.path.join(IL.PROC_MERGED, f"{sec}.jsonl")
            with open(ruta, encoding="utf-8") as f:
                for linea in f:
                    fila = json.loads(linea)
                    for meta in fila["campos"].values():
                        if meta["source"] == "legends_plus.xml":
                            self.assertNotEqual(meta["valor"], "",
                                                "plus no debe aportar campos vacíos")

    def test_18_sin_duplicados_silenciosos(self):
        """Cada registro fusionado conserva la traza de sus fuentes."""
        ids = set()
        ruta = os.path.join(IL.PROC_MERGED, "historical_figures.jsonl")
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                fila = json.loads(linea)
                self.assertNotIn(fila["record_id"], ids, "record_id duplicado")
                ids.add(fila["record_id"])
                self.assertTrue(fila["sources"], "registro sin fuentes declaradas")
                if fila["en_legends_xml"] and fila["en_legends_plus"]:
                    self.assertIn("legends.xml", fila["sources"])
                # Un conflicto debe existir en el registro si se declara.
                for c in fila["conflictos"]:
                    self.assertIn(c["valor_legends_xml"], (None, "",) + tuple(
                        [m["valor"] for m in fila["campos"].values()]))

    def test_19_divergencias_clasificadas(self):
        mg = self.m["merge"]
        total = mg["notaciones_equivalentes"] + mg["conflictos_reales"]
        self.assertEqual(total, mg["divergencias_totales"])
        self.assertEqual(mg["conflictos_reales"] + mg["notaciones_equivalentes"],
                         mg["divergencias_totales"])


if __name__ == "__main__":
    unittest.main(verbosity=2)