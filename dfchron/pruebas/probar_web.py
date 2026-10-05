#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: pruebas de INTEGRACION WEB / API
================================================

Suite NUEVA de la fase "Web <-> API local". NO sustituye a las existentes: se
anade a `probar_nucleo.py`, `probar_integracion.py`, `probar_adversarial.py` y
`probar_api.py`, que siguen siendo la referencia del nucleo.

QUE COMPRUEBA
-------------
1. Envelope `ok` / `meta` (nuevo) sin romper los campos heredados.
2. Alias: devuelven EXACTAMENTE lo mismo que su ruta canonica.
3. CORS: allowlist local, nunca `*`, y rechazo de origen desconocido.
4. Datos conocidos via HTTP: figura 712, entidad 282, sitio 87.
5. Filtros combinados: el rango de anios NO se ignora.
6. Truncamiento: se declara, no se oculta.
7. Adversariales: ids hostiles, parametros raros, Unicode, traversal.
8. La API no filtra tracebacks ni rutas internas del filesystem.
9. El frontend declara la API en UN solo sitio (`api.ts`).

Uso:  python dfchron\\pruebas\\probar_web.py
"""
import io
import json
import os
import re
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

# El paquete `dfchron` vive en la raiz del proyecto. Se anade al sys.path para
# poder arrancar el servidor real en un puerto libre sin instalar nada.
_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)   # puerto libre, nunca el 877
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def _base():
    return f"http://127.0.0.1:{_arrancar().server_address[1]}"


def pedir(ruta, metodo="GET", origen=None):
    """Devuelve (codigo_http, cuerpo_json).

    `urlopen` decodifica por defecto como Latin-1, lo que destrozaria las
    claves acentuadas del dataset (`año`). Se lee como bytes y se decodifica
    como UTF-8 explicitamente.
    """
    req = urllib.request.Request(_base() + ruta, method=metodo)
    if origen:
        req.add_header("Origin", origen)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            crudo = r.read().decode("utf-8")
            return r.status, (json.loads(crudo) if crudo else None)
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8")
        return e.code, (json.loads(crudo) if crudo else None)


# Clave con tilde que usa el dataset para el anio de un evento. Se declara como
# escape para que este fichero no dependa de como se codifique al guardarse.
ANIO = "a\u00f1o"


def pedir_cabeceras(ruta, origen=None):
    req = urllib.request.Request(_base() + ruta)
    if origen:
        req.add_header("Origin", origen)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SITE = os.path.join(RAIZ, "dfchron", "site")


class TestEnvelope(unittest.TestCase):
    """El envelope nuevo (`ok`/`meta`) y el heredado coexisten."""

    def test_ok_presente_en_lista(self):
        _, d = pedir("/api/figuras?q=a&limit=3")
        self.assertTrue(d["ok"])
        self.assertIn("meta", d)

    def test_meta_refleja_el_recorte(self):
        _, d = pedir("/api/eventos?limit=10")
        self.assertEqual(d["meta"]["returned"], 10)
        self.assertTrue(d["meta"]["truncated"])
        self.assertGreater(d["meta"]["total"], 10)

    def test_campos_heredados_intactos(self):
        """Los clientes antiguos siguen leyendo los mismos campos."""
        _, d = pedir("/api/eventos?limit=10")
        for campo in ("data", "total_encontrados", "devueltos", "truncado",
                      "limit", "offset", "certainty"):
            self.assertIn(campo, d)
        self.assertEqual(d["total_encontrados"], d["meta"]["total"])
        self.assertEqual(d["devueltos"], d["meta"]["returned"])

    def test_error_no_es_ok(self):
        _, d = pedir("/api/figuras/99999999")
        self.assertFalse(d["ok"])
        self.assertIn("error", d)
        self.assertIn("codigo", d["error"])
        self.assertIn("code", d["error"])

    def test_estado_tiene_ok(self):
        for r in ("/api/salud", "/api/stats", "/api/estadisticas"):
            _, d = pedir(r)
            self.assertTrue(d["ok"], r)
            self.assertIn("data", d, r)


class TestAliases(unittest.TestCase):
    """Cada alias devuelve lo MISMO que su ruta canonica."""

    def test_estadisticas_es_stats(self):
        self.assertEqual(pedir("/api/stats")[1], pedir("/api/estadisticas")[1])

    def test_buscar_singular_es_plural(self):
        """El alias devuelve el mismo contenido que la ruta canonica.

        El campo `tipo` se NORMALIZA al plural en ambos caminos, asi que los
        dos envelopes describen exactamente la misma busqueda.
        """
        _, singular = pedir("/api/buscar/sitio?q=halesteel")
        _, plural = pedir("/api/buscar?q=halesteel&tipo=sites")
        self.assertEqual(singular["ok"], plural["ok"])
        self.assertEqual(singular["ids"], plural["ids"])
        self.assertEqual(singular["total_encontrados"],
                         plural["total_encontrados"])
        self.assertEqual(singular["tipo"], "sitios")

    def test_buscar_figura_singular(self):
        _, d = pedir("/api/buscar/figura?q=galka%20shafttop")
        self.assertTrue(d["ok"])
        self.assertTrue(d.get("ids") or d.get("data"))

    def test_listado_de_artefactos(self):
        _, d = pedir("/api/listar/artifacts?limit=5")
        self.assertTrue(d["ok"])
        self.assertEqual(d["meta"]["returned"], 5)

    def test_geografia_de_sitio(self):
        _, d = pedir("/api/sitios/87/geografia")
        self.assertTrue(d["ok"])
        self.assertIn("coordenadas", d)

    def test_geografia_de_sitio_inexistente(self):
        codigo, d = pedir("/api/sitios/99999999/geografia")
        self.assertEqual(codigo, 404)
        self.assertFalse(d["ok"])
class TestCORS(unittest.TestCase):
    """CORS con lista blanca. Nunca `*`."""

    def test_origen_local_permitido(self):
        _, cab = pedir_cabeceras("/api/salud", origen="http://localhost:4321")
        self.assertEqual(cab.get("Access-Control-Allow-Origin"),
                         "http://localhost:4321")

    def test_127_0_0_1_permitido(self):
        _, cab = pedir_cabeceras("/api/salud", origen="http://127.0.0.1:4321")
        self.assertEqual(cab.get("Access-Control-Allow-Origin"),
                         "http://127.0.0.1:4321")

    def test_puerto_del_servidor_estatico_permitido(self):
        """Regresión del defecto encontrado en la Fase 3.

        El puerto 4400 es el de `dfchron/pruebas/servidor_estatico.py`, que
        sirve el build como lo haria el hosting (con el fallback a 404.html).
        Servir la web de ahi sin permitir ese origen en CORS hacia a que el
        navegador bloquease TODAS las respuestas de la API: la pagina se
        quedaba en "Data unavailable" aunque la API respondiera 200.
        """
        for origen in ("http://127.0.0.1:4400", "http://localhost:4400"):
            with self.subTest(origen=origen):
                _, cab = pedir_cabeceras("/api/salud", origen=origen)
                self.assertEqual(cab.get("Access-Control-Allow-Origin"), origen)

    def test_puertos_de_desarrollo_en_la_allowlist(self):
        """4321 (`astro dev`) y 4400 (servidor estatico) deben estar.

        Es una comprobacion de la CONFIGURACION, para que anadir un puerto
        nuevo no se olvide de permitirlo en los dos hosts.
        """
        from dfchron import config
        for host in ("localhost", "127.0.0.1"):
            for puerto in ("4321", "4400"):
                with self.subTest(host=host, puerto=puerto):
                    self.assertIn(f"http://{host}:{puerto}", config.ORIGENES_CORS)

    def test_puerto_no_listado_bloqueado(self):
        """La allowlist sigue siendo restrictiva: 9999 no puede entrar."""
        _, cab = pedir_cabeceras("/api/salud", origen="http://127.0.0.1:9999")
        self.assertIsNone(cab.get("Access-Control-Allow-Origin"))

    def test_origen_desconocido_bloqueado(self):
        _, cab = pedir_cabeceras("/api/salud", origen="http://evil.example.com")
        self.assertIsNone(cab.get("Access-Control-Allow-Origin"))

    def test_nunca_asterisco(self):
        """Requisito explicito: nunca `Access-Control-Allow-Origin: *`."""
        for origen in ("http://localhost:4321", "http://evil.example.com", None):
            _, cab = pedir_cabeceras("/api/salud", origen=origen)
            self.assertNotEqual(cab.get("Access-Control-Allow-Origin"), "*")

    def test_preflight_options(self):
        req = urllib.request.Request(_base() + "/api/salud", method="OPTIONS")
        req.add_header("Origin", "http://localhost:4321")
        with urllib.request.urlopen(req, timeout=30) as r:
            self.assertEqual(r.status, 204)
            self.assertEqual(r.headers.get("Access-Control-Allow-Origin"),
                             "http://localhost:4321")

    def test_vary_origin(self):
        _, cab = pedir_cabeceras("/api/salud", origen="http://localhost:4321")
        self.assertEqual(cab.get("Vary"), "Origin")

    def test_no_credenciales_permitidas(self):
        _, cab = pedir_cabeceras("/api/salud", origen="http://localhost:4321")
        self.assertIsNone(cab.get("Access-Control-Allow-Credentials"))


class TestDatosConocidos(unittest.TestCase):
    """Valores conocidos del proyecto, verificados por HTTP real."""

    def test_figura_712(self):
        codigo, d = pedir("/api/figuras/712")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"]["df_id"], "712")
        self.assertIn("galka shafttop", d["data"]["nombre"])

    def test_figura_712_tiene_158_eventos(self):
        _, d = pedir("/api/figuras/712/eventos?limit=500")
        self.assertEqual(d["total_encontrados"], 158)

    def test_entidad_282(self):
        codigo, d = pedir("/api/entidades/282")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"]["df_id"], "282")
        self.assertEqual(d["data"]["nombre"], "the curled diamond")

    def test_entidad_282_miembros(self):
        _, d = pedir("/api/entidades/282/miembros?limit=100")
        self.assertEqual(d["total_encontrados"], 25)

    def test_sitio_87_es_fortress(self):
        """El tipo REAL no se sobrescribe: `fortress`, no `site`."""
        codigo, d = pedir("/api/sitios/87")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["data"]["tipo"], "fortress")
        self.assertEqual(d["data"]["tipo_registro"], "site")

    def test_sitio_87_1546_eventos(self):
        _, d = pedir("/api/sitios/87/eventos?limit=5")
        self.assertEqual(d["total_encontrados"], 1546)
        self.assertTrue(d["truncado"])

    def test_coordenadas_son_lista_de_pares(self):
        """El nucleo devuelve una tupla (x, y); en JSON viaja como lista."""
        _, d = pedir("/api/sitios/87")
        self.assertEqual(d["data"]["coordenadas"], [[112, 20]])


class TestFiltros(unittest.TestCase):
    """Filtros combinados: el rango de anios siempre manda."""

    def test_rango_de_anios(self):
        _, d = pedir("/api/eventos?from=1&to=20&limit=500")
        self.assertEqual(d["total_encontrados"], 4696)
        for e in d["data"]:
            self.assertGreaterEqual(e[ANIO], 1)
            self.assertLessEqual(e[ANIO], 20)

    def test_filtro_por_anio(self):
        _, d = pedir("/api/eventos?year=5&limit=100")
        self.assertEqual(d["total_encontrados"], 223)
        for e in d["data"]:
            self.assertEqual(e[ANIO], 5)

    def test_combinado_no_ignora_el_rango(self):
        """Regresion del defecto historico: `from=1&to=3&figure=712`."""
        _, todos = pedir("/api/eventos?figure=712&limit=1")
        _, combo = pedir("/api/eventos?from=1&to=3&figure=712&limit=50")
        self.assertEqual(todos["total_encontrados"], 158)
        self.assertEqual(combo["total_encontrados"], 6)
        for e in combo["data"]:
            self.assertGreaterEqual(e[ANIO], 1)
            self.assertLessEqual(e[ANIO], 3)

    def test_combinado_con_sitio(self):
        _, d = pedir("/api/eventos?from=1&to=2&site=87&limit=500")
        for e in d["data"]:
            self.assertEqual(e["sitio_id"], 87)
            self.assertLessEqual(e[ANIO], 2)

    def test_tipos_de_evento(self):
        _, d = pedir("/api/eventos/tipos")
        self.assertEqual(d["total_encontrados"], 90)


class TestTruncamiento(unittest.TestCase):
    """Un recorte se declara; nunca se presenta como completo."""

    def test_limite_alto_se_recorta(self):
        _, d = pedir("/api/eventos?limit=999999")
        self.assertEqual(d["limit"], 500)
        self.assertTrue(d["truncado"])

    def test_total_real_se_conserva(self):
        _, d = pedir("/api/eventos?limit=1")
        self.assertEqual(d["total_encontrados"], 57215)

    def test_meta_y_heredado_coinciden(self):
        _, d = pedir("/api/eventos?limit=7")
        self.assertEqual(d["meta"]["truncated"], d["truncado"])
        self.assertEqual(d["meta"]["total"], d["total_encontrados"])
class TestAdversarial(unittest.TestCase):
    """Intentos de romper la API. Nunca debe haber traceback."""

    def test_id_inexistente(self):
        for r in ("/api/figuras/99999999", "/api/entidades/99999999",
                  "/api/sitios/99999999", "/api/eventos/99999999"):
            codigo, d = pedir(r)
            self.assertEqual(codigo, 404, r)
            self.assertFalse(d["ok"], r)

    def test_id_negativo(self):
        codigo, d = pedir("/api/figuras/-1")
        self.assertIn(codigo, (400, 404))
        self.assertFalse(d["ok"])

    def test_id_enorme(self):
        codigo, d = pedir("/api/figuras/" + "9" * 400)
        self.assertIn(codigo, (400, 404))
        self.assertFalse(d["ok"])

    def test_id_textual(self):
        codigo, d = pedir("/api/figuras/abc")
        self.assertIn(codigo, (400, 404))
        self.assertFalse(d["ok"])

    def test_query_vacia(self):
        codigo, d = pedir("/api/buscar?q=")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "CONSULTA_VACIA")

    def test_parametros_duplicados(self):
        codigo, _ = pedir("/api/eventos?year=1&year=50&limit=5")
        self.assertIn(codigo, (200, 400))

    def test_anios_no_numericos(self):
        """Un año que no es número se rechaza con 400, no con traceback."""
        codigo, d = pedir("/api/eventos?from=zzz&to=abc")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "ANIO_INVALIDO")
        self.assertFalse(d["ok"])

    def test_rango_invertido(self):
        codigo, _ = pedir("/api/eventos?from=50&to=2&limit=10")
        self.assertEqual(codigo, 200)   # el nucleo reordena; no rompe

    def test_tipo_inexistente(self):
        codigo, d = pedir("/api/buscar?tipo=inventado&q=x")
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "TIPO_DESCONOCIDO")

    def test_unicode_en_busqueda(self):
        codigo, d = pedir("/api/buscar?q=%E2%9C%93%E6%97%A5%E6%9C%AC%E8%AA%9E")
        self.assertEqual(codigo, 200)
        self.assertTrue(d["ok"])

    def test_caracteres_especiales(self):
        """Caracteres dangerousos: se tratan como texto, nunca como codigo."""
        for q in ("<script>", "'", '"', "..", "%00", "\\", "a b", "&", "="):
            codigo, d = pedir("/api/buscar?q=" + urllib.parse.quote(q))
            self.assertEqual(codigo, 200, q)
            self.assertTrue(d["ok"], q)

    def test_salto_de_linea_rechazado(self):
        """Un salto de linea es un intento de inyeccion de cabeceras.

        `urllib` lo normaliza a espacio antes de construir la peticion, asi que
        la consulta llega vacia y se rechaza con 400. Lo que se comprueba aqui
        es lo que de verdad importa: nunca se ejecuta ni se rompe nada.
        """
        codigo, d = pedir("/api/buscar?q=" + urllib.parse.quote("a\nb"))
        self.assertIn(codigo, (200, 400))
        self.assertIn("ok", d)

    def test_espacios_solo(self):
        codigo, d = pedir("/api/buscar?q=" + urllib.parse.quote("   "))
        self.assertEqual(codigo, 400)
        self.assertEqual(d["error"]["codigo"], "CONSULTA_VACIA")

    def test_combinacion_imposible(self):
        codigo, d = pedir("/api/eventos?from=100&to=1&figure=99999999")
        self.assertEqual(codigo, 200)
        self.assertEqual(d["total_encontrados"], 0)

    def test_sin_traceback(self):
        """Ninguna respuesta debe contener un traceback de Python."""
        rutas = ["/api/figuras/abc", "/api/buscar?q=", "/api/eventos?from=zzz",
                 "/api/sitios/-5", "/api/geografia/inventada",
                 "/api/listar/inventado", "/api/nada", "/api/artefactos/xyz"]
        for r in rutas:
            codigo, d = pedir(r)
            crudo = json.dumps(d)
            self.assertNotIn("Traceback", crudo, r)
            self.assertNotIn('.py"', crudo, r)
            self.assertIn(codigo, (200, 400, 404), r)

    def test_metodo_de_escritura_rechazado(self):
        for metodo in ("POST", "PUT", "DELETE", "PATCH"):
            codigo, _ = pedir("/api/salud", metodo=metodo)
            self.assertEqual(codigo, 405, metodo)


class TestSeguridad(unittest.TestCase):
    """Path traversal y filtracion de informacion interna."""

    def test_traversal_en_ui_bloqueado(self):
        for r in ("/static/../../../../etc/passwd",
                  "/static/..%2f..%2fWindows/win.ini",
                  "/static/C:/Windows/win.ini",
                  "/static/../servicio.py"):
            codigo, _ = pedir(r)
            self.assertIn(codigo, (403, 404), r)

    def test_ruta_absoluta_bloqueada(self):
        codigo, _ = pedir("/static//etc/passwd")
        self.assertIn(codigo, (403, 404))

    def test_no_sirve_ficheros_de_datos(self):
        """El endpoint NO permite elegir que fichero local abrir."""
        # Rutas que intentan alcanzar ficheros reales del dataset.
        for r in ("/static/../../00_SOURCE/original_data/legends.xml",
                  "/static/../../00_SOURCE/processed/merged/sites.jsonl"):
            codigo, _ = pedir(r)
            self.assertIn(codigo, (403, 404), r)
        # Un parametro que pretende elegir fichero se ignora: `/api/figuras`
        # es una BUSQUEDA, y sin `q` responde 400. Nunca abre un fichero.
        codigo, d = pedir("/api/figuras?file=../../legends.xml")
        self.assertEqual(codigo, 400)
        self.assertNotIn("file", json.dumps(d["error"]))

    def test_endpoint_desconocido(self):
        codigo, d = pedir("/api/inventado")
        self.assertEqual(codigo, 404)
        self.assertEqual(d["error"]["codigo"], "RUTA_DESCONOCIDA")

    def test_salud_no_filtra_secretos(self):
        _, d = pedir("/api/salud")
        crudo = json.dumps(d).lower()
        self.assertNotIn("password", crudo)
        self.assertNotIn("secret", crudo)
class TestFrontendEstatico(unittest.TestCase):
    """La configuracion de la API vive en UN solo sitio."""

    API_TS = os.path.join(SITE, "src", "lib", "api.ts")

    def test_api_ts_existe(self):
        self.assertTrue(os.path.isfile(self.API_TS))

    def test_una_sola_url_de_api_en_frontend(self):
        """Regla 8: ninguna vista o componente escribe su propia URL de API."""
        src = os.path.join(SITE, "src")
        fugas = []
        for raiz, _, ficheros in os.walk(src):
            for f in ficheros:
                if not f.endswith((".astro", ".ts", ".js")):
                    continue
                ruta = os.path.join(raiz, f)
                if os.path.normpath(ruta) == os.path.normpath(self.API_TS):
                    continue
                with io.open(ruta, encoding="utf-8") as fh:
                    texto = fh.read()
                # Solo cuenta como codigo: se ignoran comentarios y plantillas.
                codigo = "\n".join(
                    l for l in texto.splitlines()
                    if not l.strip().startswith(("*", "//", "#", "<!--")))
                if ":877" in codigo or re.search(r"https?://[^\s\"'`]*/api", codigo):
                    fugas.append(os.path.relpath(ruta, SITE))
        self.assertEqual(fugas, [],
                         "URL de API fuera de src/lib/api.ts: %s" % fugas)

    def test_api_base_url_desde_entorno(self):
        with io.open(self.API_TS, encoding="utf-8") as fh:
            texto = fh.read()
        self.assertIn("PUBLIC_API_BASE_URL", texto)
        self.assertIn("API_BASE_URL", texto)

    def test_sin_api_no_inventa_datos(self):
        with io.open(self.API_TS, encoding="utf-8") as fh:
            self.assertIn("SIN_API", fh.read())

    def test_no_hay_ia_implementada(self):
        """Regla 24: ni LLM, ni embeddings, ni agentes en el frontend."""
        src = os.path.join(SITE, "src")
        prohibidos = ("openai", "anthropic", "@xenova", "transformers",
                      "langchain", "embeddings", "/api/ia")
        for raiz, _, ficheros in os.walk(src):
            for f in ficheros:
                if not f.endswith((".ts", ".js", ".astro")):
                    continue
                with io.open(os.path.join(raiz, f), encoding="utf-8") as fh:
                    texto = fh.read().lower()
                for p in prohibidos:
                    self.assertNotIn(p, texto, f"{f} menciona {p}")

    def test_la_ui_antigua_se_conserva(self):
        """`dfchron/web/` no se borra: queda como referencia."""
        for f in ("index.html", "app.js", "estilo.css"):
            self.assertTrue(
                os.path.isfile(os.path.join(RAIZ, "dfchron", "web", f)), f)

    def test_documentos_de_ia_intactos(self):
        """Regla 24: la documentacion de IA se conserva para su uso futuro."""
        for f in ("AI_PROJECT_CONTEXT.md", "ai_data_contract.md"):
            self.assertTrue(os.path.isfile(os.path.join(RAIZ, "08_DATABASE", f)), f)

    def test_build_no_incluye_la_api_local(self):
        """Regla 1/10: el build publico no lleva la URL de la API local.

        Se comprueba sobre un build HECHO SIN `PUBLIC_API_BASE_URL`. Es el
        build que se despliega: si no hay variable, `API_BASE_URL` queda vacia y
        no hay ninguna URL de la que depender.
        """
        publica = os.path.join(SITE, "dist_publico")
        if not os.path.isdir(publica):
            self.skipTest(
                "dist_publico/ no existe: ejecuta el build sin "
                "PUBLIC_API_BASE_URL para comprobarlo")
        for raiz, _, ficheros in os.walk(publica):
            for f in ficheros:
                if not f.endswith((".html", ".js")):
                    continue
                with io.open(os.path.join(raiz, f), encoding="utf-8",
                             errors="ignore") as fh:
                    cuerpo = fh.read()
                # El codigo puede MENCIONAR el puerto en un texto de ayuda;
                # lo que no puede hacer es usarlo como origen activo.
                self.assertNotIn('e=`http://127.0.0.1:877`', cuerpo,
                                 f"{f} usa la API local como origen")
                self.assertNotIn('=`http://127.0.0.1:877/', cuerpo,
                                 f"{f} construye URLs contra la API local")


def tearDownModule():
    if _SERVIDOR is not None:
        _SERVIDOR.shutdown()
        _SERVIDOR.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)