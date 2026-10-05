#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Legends :: Pruebas del explorador geografico
==============================================

Levanta un servidor REAL (puerto libre elegido por el sistema) y habla HTTP de
verdad, igual que `probar_api.py`. No usa mocks: se prueba el servidor entero.

Cubre lo exigido por la Fase 5:

  * SITIOS        existente, inexistente, id invalido, con y sin coordenadas
  * COORDENADAS   validas, negativas, cero, enormes, no numericas, ausentes
  * CONSTRUCCIONES con y sin construcciones
  * INTEGRIDAD    el tipo real (`fortress`) NO se colapsa a `site`
  * ADVERSARIAL   traversal, duplicados, null, NaN, Infinity, Unicode, gigantic
  * DATOS REALES  puntos obtenidos de la API, nunca inventados

Ejecutar:  python dfchron/pruebas/probar_geografia.py
"""
import os
import sys
import json
import time
import glob
import threading
import hashlib
import unittest
import urllib.request
import urllib.error

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import config            # noqa: E402
from dfchron import api                # noqa: E402

# Hashes de los XML originales: si cambian, estas pruebas lo dicen.
SHA_XML = {
    "legends.xml": "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f",
    "legends_plus.xml": "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d",
}

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        _SERVIDOR = api.crear_servidor("127.0.0.1", 0)
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def pedir(ruta):
    """Devuelve (codigo, cuerpo_json) hablando HTTP de verdad."""
    srv = _arrancar()
    url = f"http://127.0.0.1:{srv.server_address[1]}{ruta}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")


def datos(ruta):
    """Solo el `data`, comprobando que la peticion fue buena."""
    env = sobre(ruta)
    return env["data"]


def sobre(ruta):
    """El envelope ENTERO, para leer campos de la lista (`total_encontrados`).

    `data()` devuelve `env["data"]`, que en un listado es una LISTA: los campos
    brothers (`certainty`, `coordenada`, ...) viven en el envelope, no dentro.
    """
    codigo, env = pedir(ruta)
    assert codigo == 200, f"{ruta} devolvio {codigo}: {env}"
    assert env.get("ok") is True, f"{ruta} no vino ok: {env}"
    return env


def todos_los_sitios():
    """Los 734 sitios, paginando de verdad. Se usa mucho."""
    salida, offset = [], 0
    while True:
        lote = datos(f"/api/listar/sites?limit=500&offset={offset}")
        salida.extend(lote)
        if len(lote) < 500:
            return salida
        offset += 500


def huella_datos():
    """Huella de processed/ + los dos XML. Sirve para probar que NADIE escribe."""
    h = hashlib.sha256()
    for patron in ("*.json", "*.jsonl"):
        for p in sorted(glob.glob(os.path.join(config.PROCESSED_ROOT, "**",
                                              patron), recursive=True)):
            h.update(p.encode())
            with open(p, "rb") as f:
                h.update(f.read())
    for n in SHA_XML:
        with open(os.path.join(config.ORIGINAL_DATA_ROOT, n), "rb") as f:
            h.update(f.read())
    return h.hexdigest()
# ---------------------------------------------------------------- SITIOS ---
class TestSitios(unittest.TestCase):
    """Ficha de sitio: existe, no existe, id invalido, coordenadas."""

    def test_sitio_existente(self):
        d = datos("/api/sitios/87")
        self.assertEqual(str(d["df_id"]), "87")
        self.assertEqual(d["certainty"], "FACT")

    def test_sitio_inexistente_es_404(self):
        codigo, env = pedir("/api/sitios/999999999/geografia")
        self.assertEqual(codigo, 404)
        self.assertFalse(env["ok"])
        self.assertEqual(env["certainty"], "UNKNOWN")

    def test_id_invalido_no_revienta(self):
        """'abc' no es un id: error controlado, nunca un 500 ni un traceback."""
        for malo in ("abc", "%2e%2e", "..", "1e5", "null", "-1"):
            codigo, env = pedir(f"/api/sitios/{malo}/geografia")
            self.assertIn(codigo, (400, 404), f"{malo} devolvio {codigo}")
            self.assertNotEqual(codigo, 500, f"{malo} produjo error interno")
            self.assertNotIn("Traceback", json.dumps(env))

    def test_sitio_con_coordenadas(self):
        d = datos("/api/sitios/87")
        self.assertTrue(d["coordenadas"], "el sitio 87 deberia tener coordenada")
        x, y = d["coordenadas"][0]
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_todos_los_sitios_tienen_coordenada(self):
        """El dato que sostiene el mapa entero, verificado sobre los 734."""
        sitios = todos_los_sitios()
        faltan = [s["df_id"] for s in sitios if not s.get("coordenadas")]
        self.assertEqual(len(sitios), 734, "el numero de sitios cambio")
        self.assertEqual(faltan, [], "hay sitios sin coordenada: no mapeables")


# ----------------------------------------------------------- COORDENADAS ---
class TestCoordenadas(unittest.TestCase):
    """Coordenadas validas, extremas y mal formadas."""

    def test_coordenada_valida(self):
        d = datos("/api/geografia/punto/112/20")
        self.assertEqual(d["coordenada"]["x"], 112)
        self.assertEqual(d["coordenada"]["y"], 20)

    def test_z_no_se_inventa(self):
        """No hay Z en los datos: null, no un 0 ni una estimacion."""
        d = datos("/api/geografia/punto/112/20")
        self.assertIsNone(d["coordenada"]["z"])
        self.assertIn("z", d["coordenadas"])
        self.assertIn("NO EXISTE", d["coordenadas"]["z"])

    def test_cero_es_valido(self):
        d = datos("/api/geografia/punto/0/0")
        self.assertEqual(d["coordenada"]["x"], 0)
        self.assertEqual(d["total_sitios"], 0)

    def test_negativo_es_400(self):
        codigo, env = pedir("/api/geografia/punto/-5/20")
        self.assertEqual(codigo, 400)
        self.assertEqual(env["error"]["codigo"], "COORDENADA_INVALIDA")

    def test_valor_enorme_es_400(self):
        for enorme in ("999999999999999999999999", "4294967296", "1000000"):
            codigo, _ = pedir(f"/api/geografia/punto/{enorme}/20")
            self.assertEqual(codigo, 400, f"{enorme} deberia ser 400")

    def test_no_numerico_es_400(self):
        for malo in ("abc", "1.5", "null", "NaN", "Infinity", "0x10", "1e3"):
            codigo, env = pedir(f"/api/geografia/punto/{malo}/20")
            self.assertEqual(codigo, 400, f"{malo} deberia ser 400")
            self.assertNotIn("Traceback", json.dumps(env))

    def test_parametro_ausente(self):
        codigo, env = pedir("/api/geografia?x=112")
        self.assertEqual(codigo, 400)
        self.assertIn("y", env["error"]["mensaje"])
        codigo, env = pedir("/api/geografia?y=20")
        self.assertEqual(codigo, 400)
        self.assertIn("x", env["error"]["mensaje"])

    def test_parametro_vacio(self):
        codigo, _ = pedir("/api/geografia?x=&y=")
        self.assertEqual(codigo, 400)

    def test_sin_coordenadas_sigue_dando_el_resumen(self):
        """Sin ?x/?y el comportamiento antiguo se conserva intacto."""
        d = datos("/api/geografia")
        for capa in ("rivers", "landmasses", "mountain_peaks",
                     "world_constructions"):
            self.assertIn(capa, d)

    def test_query_x_y_ya_no_se_ignora(self):
        """Regresion del fallo silencioso: ?x=&y= debe filtrar de verdad."""
        d = datos("/api/geografia?x=112&y=20")
        self.assertEqual(d["coordenada"]["x"], 112)
        self.assertEqual(len(d["capas"]), 4, "faltan capas en la respuesta")
# ---------------------------------------------------------- CONSTRUCCIONES --
class TestConstrucciones(unittest.TestCase):
    """Construcciones con y sin nada en el punto."""

    def test_construcciones_en_coordenada_con_datos(self):
        env = sobre("/api/geografia/construcciones/112/20")
        self.assertEqual(env["certainty"], "DERIVED")
        self.assertGreater(len(env["data"]), 0)
        for c in env["data"]:
            self.assertIn("metodo", c)
            self.assertEqual(c["certainty"], "DERIVED")

    def test_construcciones_en_coordenada_vacia(self):
        env = sobre("/api/geografia/construcciones/999/999")
        self.assertEqual(env["data"], [])
        self.assertEqual(env["coordenada"], [999, 999])

    def test_construcciones_coordenada_invalida(self):
        codigo, _ = pedir("/api/geografia/construcciones/abc/def")
        self.assertEqual(codigo, 400)

    def test_geografia_de_sitio_sigue_funcionando(self):
        """No se rompio el endpoint previo: mismo comportamiento."""
        env = sobre("/api/sitios/87/geografia")
        self.assertEqual(env["certainty"], "DERIVED")
        self.assertIn("metodo", env)
        for c in env["data"]:
            self.assertEqual(c["certainty"], "DERIVED")
            self.assertIn("coordenadas_comunes", c)


# ------------------------------------------------------------- INTEGRIDAD --
class TestIntegridadDeTipos(unittest.TestCase):
    """El tipo REAL se conserva. Jamas se colapsa a 'site'."""

    def test_fortress_no_es_site(self):
        d = datos("/api/sitios/87")
        self.assertEqual(d["tipo"], "fortress")
        self.assertNotEqual(d["tipo"], "site")

    def test_tipo_real_en_geografia(self):
        d = datos("/api/geografia?x=112&y=20")
        tipos = [s["tipo"] for s in d["sitios"]]
        self.assertIn("fortress", tipos)
        for t in tipos:
            self.assertNotEqual(t, "site", f"el tipo {t} se perdio")

    def test_tipo_real_en_sitios_por_coordenada(self):
        env = sobre("/api/sitios?x=112&y=20")
        self.assertEqual(env["total_encontrados"], 1)
        self.assertEqual(env["data"][0]["tipo"], "fortress")

    def test_tipos_reales_presentes_en_el_mundo(self):
        """Los tipos que documenta la auditoria siguen existiendo."""
        tipos = {s.get("tipo") for s in todos_los_sitios()}
        esperados = {"fortress", "town", "hamlet", "cave", "tower", "tomb",
                     "monastery", "shrine", "camp", "dark fortress"}
        self.assertTrue(esperados.issubset(tipos),
                        f"faltan tipos: {esperados - tipos}")
        self.assertNotIn("site", tipos)

    def test_certidumbres_declaradas(self):
        d = datos("/api/geografia?x=112&y=20")
        self.assertEqual(d["certainty"], "FACT", "la posicion es FACT")
        self.assertEqual(d["certainty_enlace"], "DERIVED",
                         "compartir coordenada es DERIVED")


# ---------------------------------------------------------------- AREA ----
class TestArea(unittest.TestCase):
    """El viewport que alimenta el mapa."""

    def test_area_devuelve_sitios_en_el_rectangulo(self):
        d = datos("/api/geografia/area/100/10?ancho=20&alto=20")
        a = d["area"]
        self.assertEqual((a["x"], a["y"], a["ancho"], a["alto"]),
                         (100, 10, 20, 20))
        self.assertEqual(a["x_max"], 119)
        self.assertEqual(a["y_max"], 29)
        for s in d["sitios"]:
            x, y = s["coordenadas"][0]
            self.assertTrue(100 <= x <= 119, f"x={x} fuera del area")
            self.assertTrue(10 <= y <= 29, f"y={y} fuera del area")

    def test_area_mundo_entero_trae_los_734(self):
        d = datos("/api/geografia/area/0/0?ancho=128&alto=128")
        self.assertEqual(d["total_sitios"], 734)

    def test_area_orden_estable(self):
        """Dos llamadas iguales deben devolver SIEMPRE la misma lista."""
        a = datos("/api/geografia/area/100/10?ancho=20&alto=20")
        b = datos("/api/geografia/area/100/10?ancho=20&alto=20")
        self.assertEqual(a["sitios"], b["sitios"])
        claves = [(s["coordenadas"][0][0], s["coordenadas"][0][1], s["df_id"])
                  for s in a["sitios"]]
        self.assertEqual(claves, sorted(claves), "el orden no es estable")

    def test_area_invalida(self):
        for q in ("ancho=0", "ancho=-5", "ancho=99999", "alto=abc"):
            codigo, _ = pedir(f"/api/geografia/area/10/10?{q}")
            self.assertEqual(codigo, 400, q)

    def test_area_vacia_devuelve_cero(self):
        d = datos("/api/geografia/area/65000/65000?ancho=8&alto=8")
        self.assertEqual(d["total_sitios"], 0)
# ------------------------------------------------------------ ADVERSARIAL --
class TestAdversarial(unittest.TestCase):
    """Entradas hostiles contra el modulo geografico."""

    HOSTILES = (
        "/api/geografia/punto/%2e%2e/%2e%2e/20",
        "/api/geografia/punto/0/0?x=1",
        "/api/geografia/punto/1/1/extra",
        "/api/geografia/area/10/10/20/20",
        "/api/geografia/punto/+/20",
        "/api/geografia/punto/%00/20",
        "/api/geografia/punto/1%2F2/20",
        "/api/geografia/punto/..%2F..%2Fetc%2Fpasswd/20",
        "/api/geografia/area/..%2F../1",
    )

    def test_no_produce_500_nunca(self):
        for ruta in self.HOSTILES:
            codigo, env = pedir(ruta)
            self.assertNotEqual(codigo, 500, f"{ruta} dio 500: {env}")
            self.assertNotIn("Traceback", json.dumps(env),
                             f"{ruta} filtro un traceback")
            self.assertNotIn("Windows", json.dumps(env),
                             f"{ruta} filtro el sistema de ficheros")

    def test_traversal_no_abre_ficheros(self):
        for ruta in ("/api/geografia/punto/..%2F..%2Fetc%2Fpasswd/1",
                     "/api/geografia/punto/1/..%2F..%2Fetc"):
            codigo, env = pedir(ruta)
            self.assertNotEqual(codigo, 500)
            self.assertNotIn("root:", json.dumps(env))

    def test_unicode_en_coordenada(self):
        for raro in ("%E2%98%83", "%C3%A1", "%00", "%F0%9F%92%A9", "%20"):
            codigo, env = pedir(f"/api/geografia/punto/{raro}/20")
            self.assertEqual(codigo, 400, raro)
            self.assertNotIn("Traceback", json.dumps(env))

    def test_parametros_repetidos_no_provocan_500(self):
        codigo, _ = pedir("/api/geografia?x=112&x=99999999999&y=20&y=abc")
        self.assertNotEqual(codigo, 500)

    def test_metodo_de_escritura_rechazado(self):
        srv = _arrancar()
        url = f"http://127.0.0.1:{srv.server_address[1]}/api/geografia/punto/1/1"
        for metodo in ("POST", "PUT", "DELETE", "PATCH"):
            req = urllib.request.Request(url, data=b"x", method=metodo)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    codigo = r.status
            except urllib.error.HTTPError as e:
                codigo = e.code
            self.assertIn(codigo, (404, 405), f"{metodo} devolvio {codigo}")


# --------------------------------------------------------------- DATOS -----
class TestDatosReales(unittest.TestCase):
    """Puntos TOMADOS de la API. Ninguna coordenada inventada aqui."""

    def test_punto_con_fortaleza(self):
        d = datos("/api/geografia/punto/112/20")
        self.assertEqual(d["total_sitios"], 1)
        s = d["sitios"][0]
        self.assertEqual(s["df_id"], "87")
        self.assertEqual(s["tipo"], "fortress")
        self.assertEqual(s["coordenadas"], [[112, 20]])

    def test_segundo_sitio_distinto(self):
        otro = next(s for s in todos_los_sitios() if s["df_id"] != "87")
        x, y = otro["coordenadas"][0]
        p = datos(f"/api/geografia/punto/{x}/{y}")
        self.assertGreaterEqual(p["total_sitios"], 1)
        self.assertIn(otro["df_id"], [s["df_id"] for s in p["sitios"]])

    def test_punto_sin_nada(self):
        d = datos("/api/geografia/punto/1/1")
        self.assertEqual(d["total_sitios"], 0)
        self.assertEqual(d["total_registros_capas"], 0)

    def test_rango_real_del_mundo(self):
        """Las coordenadas observadas caben en el rango del mundo."""
        pares = [s["coordenadas"][0] for s in todos_los_sitios()]
        for x, y in pares:
            self.assertTrue(0 <= x <= 255, f"x={x} fuera de rango")
            self.assertTrue(0 <= y <= 255, f"y={y} fuera de rango")


# ------------------------------------------------------------ INTEGRIDAD ---
class TestIntegridadDeDatos(unittest.TestCase):
    """Servir geografia NO puede escribir en el disco."""

    def test_huella_igual_antes_y_despues(self):
        antes = huella_datos()
        for ruta in ("/api/geografia", "/api/geografia/punto/112/20",
                     "/api/geografia/area/0/0?ancho=128&alto=128",
                     "/api/sitios?x=112&y=20", "/api/sitios/87/geografia"):
            pedir(ruta)
        self.assertEqual(huella_datos(), antes,
                         "una peticion geografica modifico los datos")

    def test_xml_originales_intactos(self):
        for nombre, esperado in SHA_XML.items():
            with open(os.path.join(config.ORIGINAL_DATA_ROOT, nombre), "rb") as f:
                real = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(real, esperado, f"{nombre} ha cambiado")

    def test_todas_las_rutas_documentadas_responden(self):
        for ruta in ("/api/geografia", "/api/geografia/rivers",
                     "/api/geografia/construcciones/112/20",
                     "/api/geografia/punto/112/20",
                     "/api/geografia/area/100/10",
                     "/api/sitios/87/geografia"):
            codigo, _ = pedir(ruta)
            self.assertEqual(codigo, 200, ruta)


if __name__ == "__main__":
    t0 = time.perf_counter()
    unittest.main(verbosity=2, exit=False)
    print(f"\n[probar_geografia] {time.perf_counter() - t0:.1f}s")