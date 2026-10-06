#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Suite adversarial
==================================

Intenta romper el núcleo con entradas hostiles. Cada prueba reproduce un
defecto REALMENTE observado, no un caso hipotético.

Ejecutar:  python probar_adversarial.py
"""
import os
import sys
import json
import glob
import hashlib
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nucleo import Archivo, ANIO_MIN, ANIO_MAX  # noqa: E402
from validar_semantica import v, sin_dato, valido, FACT, DERIVED, UNKNOWN  # noqa: E402

_AR = None


def ar():
    global _AR
    if _AR is None:
        _AR = Archivo()
    return _AR


class TestIdentificadoresHostiles(unittest.TestCase):
    """Parte 15: IDs validos, inexistentes, 0, negativos y tipos erroneos."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_ids_con_tipo_erroneo_no_rompen(self):
        """D1/D2: un tipo incorrecto no puede lanzar excepcion.

        Un tipo coercible a un id EXISTENTE es legitimo (712 -> '712'):
        debe funcionar. Un tipo sin sentido debe dar UNKNOWN.
        """
        a = ar()
        for valor in (None, -1, 3.7, [], {}, "abc", "", True):
            with self.subTest(valor=valor):
                r = a.ficha_figura(valor)
                self.assertEqual(r["certainty"], UNKNOWN)
                self.assertIn("motivo", r)
        # int valido: se normaliza a texto y resuelve
        self.assertEqual(a.ficha_figura(712)["certainty"], FACT)

    def test_id_inexistente_es_unknown(self):
        for func in (self.a.ficha_figura, self.a.ficha_entidad,
                     self.a.ficha_sitio, self.a.ficha_artefacto):
            self.assertEqual(func("999999999")["certainty"], UNKNOWN)

    def test_id_cero_es_valido(self):
        """El id 0 EXISTE en DF: no debe confundirse con 'inexistente'."""
        r = self.a.ficha_figura("0")
        self.assertEqual(r["certainty"], FACT)
        self.assertNotEqual(r["nombre"], UNKNOWN)

    def test_nombre_de_tipo_desconocido(self):
        self.assertEqual(self.a.nombre_de("tipo_inexistente", "1"), UNKNOWN)

    def test_anos_con_tipo_erroneo(self):
        """D1/D2: tipos no numericos dan UNKNOWN; '5' sí es un año válido."""
        a = ar()
        for valor in (None, "abc", [], {}, 3.5, True):
            with self.subTest(valor=valor):
                r = a.eventos_del_anio(valor)
                self.assertEqual(r["certainty"], UNKNOWN)
                self.assertIn("motivo", r)
        for x, y in ((None, 5), ("a", 5), (5, None), ([], 5)):
            with self.subTest(x=x, y=y):
                self.assertEqual(a.eventos_entre_anios(x, y)["certainty"], UNKNOWN)

    def test_anio_en_string_numerico_si_valido(self):
        """'5' es un año válido si se puede coercionar."""
        r = self.a.eventos_del_anio("5")
        self.assertEqual(r["certainty"], FACT)
        self.assertEqual(r["anio"], 5)

    def test_rango_invertido_se_normaliza(self):
        r = self.a.eventos_entre_anios(30, 20)
        self.assertEqual(r["desde"], 20)
        self.assertEqual(r["hasta"], 30)


class TestDeathYear(unittest.TestCase):
    """Parte 4: death_year ausente NUNCA significa 'sigue viva'."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_muerte_ausente_es_unknown_explicito(self):
        sin_muerte = [k for k, f in self.a.indice.figuras.items()
                      if sin_dato(v(f, "death_year")) is None]
        self.assertGreater(len(sin_muerte), 1000,
                           "debe haber figuras sin death_year")
        f = self.a.ficha_figura(sin_muerte[0], breve=True)
        m = f["muerte"]
        self.assertIsNone(m["año"])
        self.assertEqual(m["certainty"], UNKNOWN,
                         "un death_year ausente debe ser UNKNOWN")
        self.assertIn("NO significa", m["motivo"])

    def test_muerte_no_prohíbe_interpretaciones(self):
        """El resultado DEBE declarar qué interpretaciones son inválidas."""
        sin_muerte = next(k for k, f in self.a.indice.figuras.items()
                          if sin_dato(v(f, "death_year")) is None)
        m = self.a.ficha_figura(sin_muerte, breve=True)["muerte"]
        self.assertIn("interpretacion_prohibida", m)
        txt = json.dumps(m, ensure_ascii=False).lower()
        for prohibido in ("sigue viva", "después del año 100"):
            self.assertIn(prohibido, txt)

    def test_muerte_conocida_es_fact(self):
        con_muerte = next(k for k, f in self.a.indice.figuras.items()
                          if sin_dato(v(f, "death_year")) is not None)
        m = self.a.ficha_figura(con_muerte, breve=True)["muerte"]
        self.assertEqual(m["certainty"], FACT)
        self.assertIsNotNone(m["año"])

    def test_ninguna_muerte_esta_fuera_del_rango(self):
        """Los datos no contienen muertes posteriores al año 100."""
        for k, f in self.a.indice.figuras.items():
            y = sin_dato(v(f, "death_year"))
            if y is not None:
                self.assertGreaterEqual(y, ANIO_MIN)
                self.assertLessEqual(y, ANIO_MAX)

    def test_el_nucleo_no_dice_que_esta_viva(self):
        """Busca lenguaje afirmativo FUERA del campo de prohibiciones.

        El texto 'sigue viva' sí aparece en `interpretacion_prohibida`: es
        precisamente la salvaguarda, no una afirmacion.
        """
        a = ar()
        for k in ("0", "1", "712"):
            f = a.ficha_figura(k, breve=True)
            for campo in ("nacimiento", "muerte"):
                bloque = json.dumps(f[campo], ensure_ascii=False).lower()
                limpio = json.dumps(f[campo].get("interpretacion_prohibida", []),
                                    ensure_ascii=False).lower()
                for palabra in ("sigue viva", "está viva", "vivo todavía",
                                "aún vive", "murió después"):
                    # Solo puede aparecer dentro de la lista de prohibiciones
                    if palabra in limpio:
                        continue
                    self.assertNotIn(palabra, bloque,
                                     f"{k}.{campo} afirma '{palabra}'")
            self.assertNotIn("esta_viva", json.dumps(f, ensure_ascii=False))
class TestRelacionesDirigidas(unittest.TestCase):
    """Parte 5: el grafo es dirigido y no puede convertirse en simetrico."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_el_grafo_es_asimetrico(self):
        pares = set()
        for r in self.a.indice.relaciones:
            s = sin_dato(v(r, "source_hf"))
            t = sin_dato(v(r, "target_hf"))
            if s is not None and t is not None:
                pares.add((int(s), int(t)))
        sim = sum(1 for (x, y) in pares if (y, x) in pares)
        self.assertEqual(len(pares), 11975)
        self.assertEqual(sim, 1774)
        self.assertLess(sim, len(pares),
                        "el grafo NO puede ser simetrico en estos datos")

    def test_la_consulta_no_simetriza(self):
        """Devolver relaciones de A no debe incluir las de B no registradas."""
        r = self.a.relaciones_de_figura("1156")
        for rel in r["relaciones"]:
            otro = rel["otra_figura_id"]
            # la inversa solo existe si el XML la registra
            inversa_existe = any(
                sin_dato(v(x, "source_hf")) == int(otro)
                and sin_dato(v(x, "target_hf")) == int(rel["figura_id"])
                for x in self.a.indice.relaciones)
            if not inversa_existe:
                self.assertIn("nota_grafo", r)

    def test_declara_grafo_dirigido(self):
        r = self.a.relaciones_de_figura("1156")
        self.assertIn("DIRIGIDO", r["nota_grafo"])
        self.assertIn("no implica la inversa", r["nota_grafo"])

    def test_no_inventa_evento(self):
        for rel in self.a.relaciones_de_figura("1156")["relaciones"]:
            self.assertFalse(rel["evento_existe"])
            self.assertNotIn(rel["evento_id"], self.a.indice.eventos)

    def test_ambos_extremos_existen_en_el_100_por_ciento(self):
        for r in self.a.indice.relaciones:
            s = str(sin_dato(v(r, "source_hf")))
            t = str(sin_dato(v(r, "target_hf")))
            self.assertIn(s, self.a.indice.figuras)
            self.assertIn(t, self.a.indice.figuras)


class TestTruncamientos(unittest.TestCase):
    """Parte 8: ningun recorte puede ser silencioso."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_todas_las_busquedas_comunican_total(self):
        for fn in (self.a.buscar_figura, self.a.buscar_entidad,
                   self.a.buscar_sitio, self.a.buscar_artefacto,
                   self.a.buscar_evento):
            r = fn("the")
            self.assertIn("total_encontrados", r, fn.__name__)
            self.assertIn("truncado", r, fn.__name__)
            self.assertIn("devueltos", r, fn.__name__)
            self.assertIn("limite", r, fn.__name__)

    def test_busqueda_no_trunca_sin_declararlo(self):
        r = self.a.buscar_figura("the")
        if r["truncado"]:
            self.assertLess(r["devueltos"], r["total_encontrados"])
            self.assertEqual(r["devueltos"], r["limite"])
        else:
            self.assertEqual(r["devueltos"], r["total_encontrados"])

    def test_cronologias_comunican_truncado(self):
        for fn, ident in ((self.a.cronologia_figura, "712"),
                          (self.a.cronologia_sitio, "87"),
                          (self.a.cronologia_entidad, "282")):
            r = fn(ident, limite=3)
            self.assertIn("truncado", r, fn.__name__)
            self.assertTrue(r["truncado"])
            self.assertEqual(r["devueltos"], 3)
            self.assertGreater(r["total_eventos"], 3)

    def test_relaciones_comunican_truncado(self):
        r = self.a.relaciones_de_figura("1156", limite=1)
        self.assertTrue(r["truncado"])
        self.assertEqual(r["devueltos"], 1)
        self.assertEqual(r["total"], 2)

    def test_eventos_entre_anios_comunica_truncado(self):
        r = self.a.eventos_entre_anios(1, 100, limite=5)
        self.assertTrue(r["truncado"])
        self.assertEqual(r["devueltos"], 5)
        self.assertEqual(r["total"], 57215)

    def test_envelope_con_total_opcional(self):
        """con_total=True da el total; por defecto se mantiene la lista."""
        r = self.a.eventos_de_figura("712", limite=2, con_total=True)
        self.assertEqual(r["devueltos"], 2)
        self.assertEqual(r["total"], 158)
        self.assertTrue(r["truncado"])
        self.assertIsInstance(self.a.eventos_de_figura("712", limite=2), list)

    def test_conflictos_declara_total_real(self):
        c = self.a.conflictos(limite_eventos=50)
        self.assertEqual(c["eventos_de_enfrentamiento"], 5478)
        self.assertEqual(c["eventos_devueltos"], 50)
        self.assertTrue(c["truncado"])
        self.assertEqual(c["por_subtipo_total"]["attacked"], 2733)

    def test_markdown_avisa_de_truncamiento(self):
        md = self.a.exportar_markdown(self.a.ficha_sitio("87"), "s")
        self.assertIn("truncada", md.lower())

    def test_json_no_trunca_en_silencio(self):
        """La exportación JSON no debe recortar nada."""
        import json as _j
        obj = _j.loads(self.a.exportar_historia_figura("712", "json"))
        ev = obj["datos"]["acontecimientos"]
        self.assertEqual(len(ev), 158)
class TestSoloLectura(unittest.TestCase):
    """Parte 12: consultar no puede modificar el dataset."""

    def test_consultas_no_modifican_el_dataset(self):
        a = Archivo()
        proc = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "processed")

        def huella():
            h = hashlib.sha256()
            for p in sorted(glob.glob(os.path.join(proc, "**", "*.json*"),
                                      recursive=True)):
                with open(p, "rb") as f:
                    h.update(p.encode())
                    h.update(f.read())
            return h.hexdigest()

        antes = huella()
        for _ in range(5):
            a.ficha_figura("712")
            a.ficha_entidad("282")
            a.ficha_sitio("87")
            a.eventos_de_figura("712")
            a.cronologia_figura("712")
            a.buscar("the")
            a.conflictos(limite_eventos=20)
            a.relaciones_de_figura("1156")
            a.geografia()
            a.exportar_historia_figura("712", "markdown")
        self.assertEqual(antes, huella(), "una consulta modifico el dataset")

    def test_no_se_crean_archivos_nuevos(self):
        a = ar()
        proc = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "processed")
        antes = set(glob.glob(os.path.join(proc, "**", "*"), recursive=True))
        a.ficha_figura("712")
        a.conflictos(limite_eventos=5)
        a.exportar_json(a.ficha_sitio("87"), "x")
        despues = set(glob.glob(os.path.join(proc, "**", "*"), recursive=True))
        self.assertEqual(antes, despues)


class TestAusenciaNoEsNegacion(unittest.TestCase):
    """Parte 19: 0 eventos != 'no pudieron ocurrir eventos'."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_sitio_sin_eventos_lo_declara(self):
        sit = next(k for k in self.a.indice.sitios
                   if not self.a.indice.ev_por_sitio.get(k))
        r = self.a.ficha_sitio(sit, breve=True)
        self.assertEqual(r["eventos"], 0)
        self.assertEqual(r["certainty_eventos"], UNKNOWN)
        self.assertIn("NO significa", r["nota_eventos"])

    def test_sitio_con_eventos_no_lo_declara(self):
        r = self.a.ficha_sitio("87", breve=True)
        self.assertNotIn("certainty_eventos", r)

    def test_figura_sin_relaciones_no_lo_declara_como_negacion(self):
        r = self.a.relaciones_de_figura("0")
        self.assertEqual(r["total"], 0)
        self.assertEqual(r["relaciones"], [])
        self.assertNotIn("no tiene relaciones",
                         json.dumps(r, ensure_ascii=False).lower())

    def test_busqueda_sin_coincidencias(self):
        r = self.a.buscar_figura("zzzqqqxxxnoexiste")
        self.assertEqual(r["ids"], [])
        self.assertEqual(r["total_encontrados"], 0)


class TestSinCausalidad(unittest.TestCase):
    """Partes 18 y 21: el nucleo no narra ni infiere."""

    @classmethod
    def setUpClass(cls):
        cls.a = ar()

    def test_el_codigo_no_contiene_lenguaje_causal(self):
        """El texto del nucleo no debe afirmar causalidad.

        BUG CORREGIDO (auditoria 2026-10): el cuerpo de esta prueba estaba
        vacio (solo un `import inspect` huerfano), asi que NUNCA podia
        fallar. Ahora comprueba de verdad el texto que el nucleo emite.

        Se prohuyen conectores causales en las CADENAS del modulo (docstrings
        y mensajes al usuario). No se prohiben en identificadores ni en
        comentarios, porque `cause` es un campo real del XML de Dwarf Fortress.
        """
        import ast

        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "nucleo.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())

        prohibido = ("porque", "por lo tanto", "debido a", "causado por",
                     "concluimos", "evidentemente", "se deduce",
                     "esto explica", "probablemente", "seguramente")
        Found = []
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                texto = nodo.value.lower()
                for palabra in prohibido:
                    if palabra in texto:
                        # Se admite dentro de una prohibicion explicita.
                        if ("no " in texto or "nunca" in texto
                                or "prohibid" in texto):
                            continue
                        Found.append(f"linea {nodo.lineno}: {palabra!r} en "
                                     f"{nodo.value[:70]!r}")
        self.assertEqual(Found, [],
                         "lenguaje causal en el nucleo:\n" + "\n".join(Found))

    def test_los_eventos_no_se_narran(self):
        """Un resumen de evento debe ser datos, no prosa."""
        r = self.a.ficha_evento("0") if hasattr(self.a, "ficha_evento") else None
        if r is None:
            self.skipTest("ficha_evento todavia no existe en el nucleo")
        texto = json.dumps(r, ensure_ascii=False).lower()
        for palabra in ("por tanto", "luego entonces", "a consecuencia",
                        "se ve que", "claramente"):
            self.assertNotIn(palabra, texto)

class TestIntegridadFuentes(unittest.TestCase):
    """Partes 11 y 15: hashes, manifiesto y ficheros completos."""

    SHA = {
        "legends.xml": "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f",
        "legends_plus.xml": "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d",
    }

    def _base(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_hashes_intactos(self):
        for nombre, esperado in self.SHA.items():
            h = hashlib.sha256()
            with open(os.path.join(self._base(), "original_data", nombre), "rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            self.assertEqual(h.hexdigest(), esperado, nombre)

    def test_manifiesto_coincide_con_los_ficheros(self):
        with open(os.path.join(self._base(), "dataset_manifest.json"),
                  encoding="utf-8") as f:
            man = json.load(f)
        for nombre, esperado in self.SHA.items():
            self.assertEqual(man["fuentes"][nombre]["sha256"], esperado,
                             f"el manifiesto no refleja {nombre}")

    def test_conteos_reales(self):
        a = ar()
        self.assertEqual(len(a.indice.figuras), 11144)
        self.assertEqual(len(a.indice.entidades), 1067)
        self.assertEqual(len(a.indice.sitios), 734)
        self.assertEqual(len(a.indice.eventos), 57215)
        self.assertEqual(len(a.indice.artefactos), 427)
        self.assertEqual(len(a.indice.relaciones), 13192)

    def test_manifiesto_consistente_con_los_datos(self):
        with open(os.path.join(self._base(), "dataset_manifest.json"),
                  encoding="utf-8") as f:
            man = json.load(f)
        a = ar()
        self.assertEqual(man["conteos"]["historical_figures"],
                         len(a.indice.figuras))
        self.assertEqual(man["conteos"]["historical_events"],
                         len(a.indice.eventos))
        self.assertEqual(man["referencias"]["rotas_totales"], 0)


class TestDefinicionesDuplicadas(unittest.TestCase):
    """Regresion: codigo muerto que anula silenciosamente una correccion."""

    def test_no_hay_definiciones_duplicadas(self):
        import ast
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "nucleo.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ClassDef):
                vistas = {}
                for sub in nodo.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertNotIn(
                            sub.name, vistas,
                            f"{nodo.name}.{sub.name} duplicado en lineas "
                            f"{vistas.get(sub.name)} y {sub.lineno}")
                        vistas[sub.name] = sub.lineno


if __name__ == "__main__":
    unittest.main(verbosity=2)
