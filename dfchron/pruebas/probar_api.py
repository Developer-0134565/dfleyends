#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas de la API y de la UI
==============================================

Levanta un servidor REAL en un puerto libre y lo somete a entradas hostiles.

No usa `requests` ni `unittest.mock`: habla HTTP de verdad con `urllib`, que
es biblioteca estandar. Asi se prueba tambien el servidor, no solo el
servicio.

Comprueba:
  * valores REALES conocidos (no solo "no lanza excepcion")
  * formato de envelope (data / total_encontrados / truncado / certainty)
  * errores: 404, 400, 405
  * seguridad: traversal, export hacia rutas protegidas, limites absurdos,
    IDs invalidos, metodos de escritura
  * que el dataset NO se modifica al servir peticiones
  * que la UI se sirve y NO lee los XML

Ejecutar:  python probar_api.py
"""
import os
import sys
import glob
import json
import time
import hashlib
import threading
import unittest
import urllib.parse
import urllib.request
import urllib.error

# dfchron/pruebas/ -> dfchron/ -> raiz del proyecto
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import config            # noqa: E402
from dfchron import api                # noqa: E402
from dfchron import servicio as svc    # noqa: E402

# Valores REALES verificados contra el dataset. Si el nucleo cambia, estas
# pruebas fallan: son la garantia de "la aplicacion carga Y es correcta".
ESPERADO = {
    "figuras": 11144, "entidades": 1067, "sitios": 734,
    "eventos": 57215, "artefactos": 427, "relaciones": 13192,
}
SHA_XML = {
    "legends.xml": "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f",
    "legends_plus.xml": "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d",
}

_SERVIDOR = None
_HILOS = []


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is not None:
        return _SERVIDOR
    # Puerto 0 = el sistema elige uno libre: evita choques en pruebas.
    _SERVIDOR = api.crear_servidor("127.0.0.1", 0)
    h = threading.Thread(target=_SERVIDOR.serve_forever, daemon=True)
    h.start()
    _HILOS.append(h)
    return _SERVIDOR


def _base():
    srv = _arrancar()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def pedir(ruta, metodo="GET", datos=None):
    """Pide una ruta. Devuelve (codigo_http, cuerpo_json)."""
    url = _base() + ruta
    req = urllib.request.Request(url, method=metodo)
    if datos is not None:
        req.data = datos
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            crudo = r.read().decode("utf-8")
            codigo = r.status
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8", "replace")
        codigo = e.code
    try:
        return codigo, json.loads(crudo)
    except ValueError:
        return codigo, {"_texto": crudo}


def pedir_texto(ruta):
    url = _base() + ruta
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), \
                r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, "", ""


def huella_dataset():
    """Huella de TODO processed/ + los XML originales."""
    h = hashlib.sha256()
    for patron in ("*.json", "*.jsonl"):
        for p in sorted(glob.glob(os.path.join(config.PROCESSED_ROOT,
                                               "**", patron),
                                  recursive=True)):
            h.update(p.encode())
            with open(p, "rb") as f:
                h.update(f.read())
    for n in SHA_XML:
        with open(os.path.join(config.ORIGINAL_DATA_ROOT, n), "rb") as f:
            h.update(f.read())
    return h.hexdigest()



class TestMetadatos(unittest.TestCase):
    """Estadisticas y metadatos: cifras REALES del nucleo."""

    def test_salud(self):
        codigo, d = pedir("/api/salud")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"]["estado"], "ok")

    def test_stats_tienen_los_valores_reales(self):
        codigo, d = pedir("/api/stats")
        self.assertEqual(codigo, 200)
        for clave, valor in ESPERADO.items():
            self.assertEqual(d["data"][clave], valor, clave)

    def test_stats_declara_el_rango_temporal(self):
        _, d = pedir("/api/stats")
        self.assertEqual(d["data"]["anio_min"], 1)
        self.assertEqual(d["data"]["anio_max"], 100)

    def test_limitaciones_son_visibles(self):
        codigo, d = pedir("/api/limitaciones")
        self.assertEqual(codigo, 200)
        datos = d["data"]
        self.assertEqual(datos["era"], "UNKNOWN")
        self.assertEqual(datos["rango_temporal"], [1, 100])
        self.assertTrue(datos["grafo_dirigido"])
        self.assertTrue(datos["sin_tabla_de_guerras"])
        # Cifras medidas, no redaccion.
        self.assertEqual(datos["eventos_sin_participantes"], 17881)
        self.assertEqual(datos["relaciones_sin_evento"], 13192)

    def test_documentacion_lista_los_endpoints(self):
        codigo, d = pedir("/api")
        self.assertEqual(codigo, 200)
        self.assertGreaterEqual(len(d["data"]["endpoints"]), 30)


class TestFichas(unittest.TestCase):
    """Valores concretos de fichas. No basta con 'no lanza excepcion'."""

    def test_figura_712_valores_reales(self):
        codigo, d = pedir("/api/figuras/712")
        self.assertEqual(codigo, 200)
        f = d["data"]
        self.assertEqual(f["certainty"], "FACT")
        self.assertEqual(f["race"], "MINOTAUR")
        self.assertEqual(len(f["acontecimientos"]), 158)

    def test_sitio_87_conserva_el_tipo_de_dwarf_fortress(self):
        codigo, d = pedir("/api/sitios/87")
        self.assertEqual(codigo, 200)
        s = d["data"]
        self.assertEqual(s["nombre"], "halesteel")
        # REGRESION: 'fortress' jamas debe convertirse en 'site'.
        self.assertEqual(s["tipo"], "fortress")
        self.assertEqual(s["tipo_registro"], "site")
        self.assertEqual(s["coordenadas"], [[112, 20]])
        self.assertEqual(s["eventos"], 1546)

    def test_entidad_282_valores_reales(self):
        codigo, d = pedir("/api/entidades/282")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"]["nombre"], "the curled diamond")
        self.assertEqual(d["data"]["eventos"], 769)
        codigo, m = pedir("/api/entidades/282/miembros")
        self.assertEqual(m["total_encontrados"], 25)

    def test_figura_0_es_valida(self):
        """El id 0 EXISTE en DF: no debe confundirse con 'inexistente'."""
        codigo, d = pedir("/api/figuras/0")
        self.assertEqual(codigo, 200)


class TestBusqueda(unittest.TestCase):
    """Busqueda global y por tipo, con ambiguedad declarada."""

    def test_buscar_galka_shafttop(self):
        codigo, d = pedir("/api/buscar?q=galka%20shafttop&tipo=figuras")
        self.assertEqual(codigo, 200)
        self.assertIn("712", d["ids"])

    def test_busqueda_ambigua_no_elige(self):
        codigo, d = pedir("/api/buscar?q=the&tipo=figuras")
        self.assertEqual(codigo, 200)
        self.assertTrue(d["consulta_ambigua"])
        self.assertGreater(d["total_encontrados"], 1)

    def test_busqueda_sin_resultados(self):
        codigo, d = pedir("/api/buscar?q=zzzqqqxxxnoexiste")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["total_encontrados"], 0)

    def test_busqueda_devuelve_grupo_por_tipo(self):
        codigo, d = pedir("/api/buscar?q=halesteel")
        self.assertEqual(codigo, 200)
        self.assertTrue(d["por_tipo"])
        tipos = {g["tipo"] for g in d["data"]}
        self.assertIn("sites", tipos)


class TestColecciones(unittest.TestCase):
    """Listados, eventos y paginacion."""

    def test_eventos_de_figura(self):
        _, d = pedir("/api/figuras/712/eventos?limit=500")
        self.assertEqual(d["total_encontrados"], 158)
        self.assertEqual(d["devueltos"], 158)
        self.assertFalse(d["truncado"])

    def test_eventos_de_sitio(self):
        _, d = pedir("/api/sitios/87/eventos?limit=10")
        self.assertEqual(d["total_encontrados"], 1546)
        self.assertTrue(d["truncado"])

    def test_filtro_por_anio(self):
        _, d = pedir("/api/eventos?year=5&limit=100")
        self.assertEqual(d["total_encontrados"], 223)
        for e in d["data"]:
            self.assertEqual(e["año"], 5)

    def test_filtro_por_rango_de_anos(self):
        _, d = pedir("/api/eventos?from=1&to=20&limit=500")
        self.assertEqual(d["total_encontrados"], 4696)
        for e in d["data"]:
            self.assertTrue(1 <= e["año"] <= 20)

    def test_filtro_por_tipo_figura_y_sitio(self):
        _, a = pedir("/api/eventos?figure=712&limit=5")
        self.assertEqual(a["total_encontrados"], 158)
        _, b = pedir("/api/eventos?site=87&limit=5")
        self.assertEqual(b["total_encontrados"], 1546)
        _, c = pedir("/api/eventos?entity=282&limit=5")
        self.assertEqual(c["total_encontrados"], 769)
        # Combinado: el rango debe seguir mandando.
        _, d = pedir("/api/eventos?from=1&to=3&figure=712&limit=50")
        self.assertLess(d["total_encontrados"], 158)
        for e in d["data"]:
            self.assertTrue(1 <= e["año"] <= 3)

    def test_tipos_de_evento_son_los_del_xml(self):
        _, d = pedir("/api/eventos/tipos")
        self.assertEqual(d["total_encontrados"], 90)
        self.assertEqual(sum(t["eventos"] for t in d["data"]), ESPERADO["eventos"])

    def test_paginacion_no_se_solapa(self):
        _, p1 = pedir("/api/listar/sites?limit=10&offset=0")
        _, p2 = pedir("/api/listar/sites?limit=10&offset=10")
        ids1 = {i["df_id"] for i in p1["data"]}
        ids2 = {i["df_id"] for i in p2["data"]}
        self.assertEqual(len(ids1), 10)
        self.assertFalse(ids1 & ids2)

    def test_cronologia_ordenada(self):
        _, d = pedir("/api/figuras/712/cronologia?limit=200")
        anios = [e["año"] for e in d["data"]["linea_temporal"]
                 if e["año"] is not None]
        self.assertEqual(anios, sorted(anios))

    def test_relaciones_declaran_el_grafo_dirigido(self):
        _, d = pedir("/api/figuras/1156/relaciones")
        self.assertIn("DIRIGIDO", d["nota_grafo"])

    def test_tipos_de_relacion(self):
        _, d = pedir("/api/relaciones/tipos")
        self.assertEqual(d["total_encontrados"], 12)



class TestConflictosYGeografia(unittest.TestCase):
    """Conflictos DERIVED y capas geograficas."""

    def test_conflictos_son_derived_y_no_guerras(self):
        _, d = pedir("/api/conflictos?limit=10")
        self.assertEqual(d["certainty"], "DERIVED")
        self.assertEqual(d["total_encontrados"], 5478)
        self.assertTrue(d["truncado"])
        self.assertIn("NO demuestra guerras", d["advertencia"])

    def test_geografia_resumen(self):
        _, d = pedir("/api/geografia")
        self.assertEqual(d["data"]["rivers"]["registros"], 2346)
        self.assertEqual(d["data"]["landmasses"]["registros"], 40)
        self.assertEqual(d["data"]["mountain_peaks"]["registros"], 4)
        self.assertEqual(d["data"]["world_constructions"]["registros"], 122)

    def test_geografia_capa(self):
        _, d = pedir("/api/geografia/mountain_peaks?limit=10")
        self.assertEqual(d["total_encontrados"], 4)
        for i in d["data"]:
            self.assertIn("coordenadas", i)

    def test_rios_avisan_de_su_id_derivado(self):
        _, d = pedir("/api/geografia/rivers?limit=5")
        self.assertIn("DERIVED", d["nota_derivada"])

    def test_construcciones_en_coordenada(self):
        _, d = pedir("/api/geografia/construcciones/112/20")
        self.assertEqual(d["certainty"], "DERIVED")


class TestErrores(unittest.TestCase):
    """Entradas invalidas: deben fallar de forma SEGURA y explicita."""

    def test_endpoint_inexistente_es_404(self):
        codigo, d = pedir("/api/no-existe")
        self.assertEqual(codigo, 404)
        self.assertEqual(d["error"]["codigo"], "RUTA_DESCONOCIDA")

    def test_id_inexistente_es_404(self):
        for ruta in ("/api/figuras/999999999", "/api/sitios/999999999",
                     "/api/entidades/999999999", "/api/artefactos/999999999",
                     "/api/eventos/999999999"):
            codigo, d = pedir(ruta)
            self.assertEqual(codigo, 404, ruta)
            self.assertEqual(d["error"]["codigo"], "NO_ENCONTRADO")

    def test_id_no_numerico_no_rompe(self):
        codigo, d = pedir("/api/figuras/abc")
        self.assertIn(codigo, (400, 404))
        self.assertIn("error", d)

    def test_anio_invalido_es_400(self):
        codigo, d = pedir("/api/eventos?year=abc")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "ANIO_INVALIDO")

    def test_anio_fuera_de_rango_no_rompe(self):
        codigo, _ = pedir("/api/eventos?year=999999&limit=5")
        self.assertEqual(codigo, 200)   # sin resultados, no un fallo

    def test_busqueda_vacia_es_400(self):
        codigo, d = pedir("/api/buscar?q=")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "CONSULTA_VACIA")

    def test_tipo_desconocido_es_400(self):
        codigo, _ = pedir("/api/listar/inventado")
        self.assertEqual(codigo, 400)
        codigo, _ = pedir("/api/geografia/capa_inventada")
        self.assertEqual(codigo, 400)

    def test_coordenada_invalida_es_400(self):
        codigo, _ = pedir("/api/geografia/construcciones/abc/def")
        self.assertEqual(codigo, 400)

    def test_export_sin_destino_es_400(self):
        codigo, d = pedir("/api/exportar")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "FALTA_OBJETIVO")

    def test_metodo_de_escritura_es_405(self):
        for metodo in ("POST", "PUT", "DELETE", "PATCH"):
            codigo, _ = pedir("/api/stats", metodo=metodo)
            self.assertEqual(codigo, 405, metodo)

    def test_ruta_no_api_es_404(self):
        codigo, _ = pedir("/cualquier/cosa")
        self.assertEqual(codigo, 404)



class TestSeguridad(unittest.TestCase):
    """La API no puede leer fuera del proyecto ni escribir en los datos."""

    def test_traversal_en_la_ui(self):
        for intento in ("/static/../../../Windows/win.ini",
                        "/static/..%2f..%2fwindows%2fwin.ini",
                        "/static/%2e%2e/%2e%2e/original_data/legends.xml"):
            codigo, _, _ = pedir_texto(intento)
            self.assertIn(codigo, (403, 404), intento)

    def test_ruta_absoluta_en_la_ui(self):
        codigo, _, _ = pedir_texto("/static/C:/Windows/win.ini")
        self.assertEqual(codigo, 403)

    def test_no_sirve_xml_nada(self):
        """El XML original jamas se sirve por HTTP."""
        for intento in ("/api/../original_data/legends.xml",
                        "/original_data/legends.xml",
                        "/api/legends.xml"):
            codigo, _, _ = pedir_texto(intento)
            self.assertIn(codigo, (403, 404), intento)

    def test_export_no_puede_salir_de_exports(self):
        for nombre in ("../../evil.json", "..\\..\\evil.json",
                       "/etc/passwd", "sub/dir.json", ".."):
            codigo, d = pedir("/api/exportar?figura=712&escribir=1&nombre="
                              + urllib.parse.quote(nombre))
            self.assertEqual(codigo, 400, nombre)
            self.assertIn("NOMBRE_EXPORTACION_INVALIDO",
                          d["error"]["codigo"], nombre)

    def test_export_invalido_no_escribe(self):
        codigo, d = pedir("/api/exportar?figura=712&format=exe")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "FORMATO_NO_SOPORTADO")

    def test_limites_absurdos_se_acotan(self):
        for limite in ("999999999", "-5", "abc", "", "0"):
            codigo, d = pedir("/api/listar/sites?limit="
                              + urllib.parse.quote(limite))
            self.assertEqual(codigo, 200, limite)
            self.assertLessEqual(d["limit"], config.LIMITE_MAXIMO, limite)
            self.assertLessEqual(len(d["data"]), config.LIMITE_MAXIMO, limite)

    def test_offset_absurdo_se_acota(self):
        codigo, d = pedir("/api/listar/sites?limit=5&offset=99999999")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"], [])
        self.assertEqual(d["devueltos"], 0)


    def test_export_por_defecto_no_escribe(self):
        """Sin `escribir`, la API devuelve texto y NO toca el disco."""
        antes = set(os.listdir(config.EXPORT_ROOT)) \
            if os.path.isdir(config.EXPORT_ROOT) else set()
        codigo, d = pedir("/api/exportar?figura=712&format=json")
        self.assertEqual(codigo, 200)
        self.assertIsNone(d["escrito_en"])
        self.assertGreater(d["data"]["caracteres"], 1000)
        despues = set(os.listdir(config.EXPORT_ROOT)) \
            if os.path.isdir(config.EXPORT_ROOT) else set()
        self.assertEqual(antes, despues)

    def test_export_seguro_escribe_solo_en_exports(self):
        codigo, d = pedir("/api/exportar?figura=712&format=json"
                          "&escribir=1&nombre=prueba_seguridad.json")
        self.assertEqual(codigo, 200)
        destino = d["escrito_en"]
        self.assertTrue(os.path.normcase(destino).startswith(
            os.path.normcase(os.path.normpath(config.EXPORT_ROOT))))
        self.assertTrue(os.path.isfile(destino))
        os.remove(destino)

    def test_el_dataset_no_cambia_al_servir(self):
        antes = huella_dataset()
        for ruta in ("/api/stats", "/api/figuras/712",
                     "/api/eventos?limit=100", "/api/sitios/87/eventos?limit=100",
                     "/api/conflictos?limit=50", "/api/exportar?figura=712",
                     "/api/geografia?limit=50"):
            pedir(ruta)
        self.assertEqual(antes, huella_dataset(),
                         "servir peticiones modifico el dataset")


class TestInterfaz(unittest.TestCase):
    """La UI se sirve y NO lee los XML."""

    def test_raiz_sirve_html(self):
        codigo, cuerpo, tipo = pedir_texto("/")
        self.assertEqual(codigo, 200)
        self.assertIn("text/html", tipo)
        self.assertIn("DF-Chronicles", cuerpo)

    def test_los_estaticos_se_sirven(self):
        for ruta, tipo_esperado in (("/static/app.js", "javascript"),
                                    ("/static/estilo.css", "css")):
            codigo, cuerpo, tipo = pedir_texto(ruta)
            self.assertEqual(codigo, 200, ruta)
            self.assertIn(tipo_esperado, tipo, ruta)
            self.assertGreater(len(cuerpo), 500, ruta)

    def test_la_ui_no_accede_a_los_xml(self):
        """La UI solo conoce la API: no hay XML ni JSONL en su codigo."""
        with open(os.path.join(config.WEB_ROOT, "app.js"), encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("legends.xml", "legends_plus", ".jsonl",
                          "original_data", "processed/merged", "readFileSync",
                          "XMLHttpRequest"):
            self.assertNotIn(prohibido, fuente,
                             f"la UI referencia {prohibido!r}")

    def test_la_ui_usa_la_api(self):
        with open(os.path.join(config.WEB_ROOT, "app.js"), encoding="utf-8") as f:
            fuente = f.read()
        self.assertIn("/api/", fuente)
        self.assertIn("fetch(", fuente)


class TestIntegridadDatos(unittest.TestCase):
    """Los originales siguen intactos."""

    def test_xml_originales_intactos(self):
        for nombre, esperado in SHA_XML.items():
            ruta = os.path.join(config.ORIGINAL_DATA_ROOT, nombre)
            h = hashlib.sha256()
            with open(ruta, "rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            self.assertEqual(h.hexdigest(), esperado, nombre)


if __name__ == "__main__":
    t0 = time.perf_counter()
    try:
        unittest.main(verbosity=2)
    finally:
        if _SERVIDOR is not None:
            _SERVIDOR.shutdown()
            _SERVIDOR.server_close()
    print(f"\n({time.perf_counter() - t0:.1f}s)")
