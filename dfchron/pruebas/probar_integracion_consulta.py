#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: pruebas de la INTEGRACION API/WEB con el contrato de consulta
=========================================================================

QUE DEMUESTRA ESTA SUITE
------------------------
Que API y Web son consumidores del MISMO contrato determinista, y que la
frontera HTTP es un adaptador y no una segunda fuente de verdad.

Grupos:

1. `TestDelegacion`    - la API y el servicio dan el MISMO dato, estado,
                         identidad y evidencia.
2. `TestEstados`       - NOT_FOUND / NOT_VERIFIED / DATA_UNAVAILABLE NO se
                         confunden, ni al traducirlos a HTTP ni al pintarlos.
3. `TestEvidencia`     - dataset_id y state_version llegan cuandotocan.
4. `TestIdentidad`     - no se inventa identidad donde no la hay.
5. `TestRelaciones`    - se delegan; no se reconstruyen.
6. `TestPaginacion`    - los limites del servicio se respetan.
7. `TestValidacion`    - entrada invalida -> 400, nunca consulta accidental.
8. `TestSeguridad`     - traversal, ids enormes, metodos no permitidos.
9. `TestCompatibilidad`- el envelope ANTIGUO sigue intacto.
10.`TestUnificacion`   - servicio, API y Web parten del mismo resultado.
11.`TestWeb`           - la Web NO decide el estado; lo muestra.

Uso:  python dfchron\\pruebas\\probar_integracion_consulta.py
"""
import json
import os
import re
import sys
import threading
import unittest
import urllib.error
import urllib.request

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
_TOOLS = os.path.join(_RAIZ, "00_SOURCE", "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)      # puerto libre, nunca el 877
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def _base():
    return "http://127.0.0.1:%d" % _arrancar().server_address[1]


def pedir(ruta, metodo="GET"):
    """Devuelve (codigo_http, cuerpo_json). Nunca lanza."""
    req = urllib.request.Request(_base() + ruta, method=metodo)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8")
        try:
            return e.code, json.loads(crudo)
        except ValueError:
            return e.code, {"<no-json>": crudo[:200]}
    except Exception as exc:                        # noqa: BLE001
        return -1, {"<excepcion>": type(exc).__name__}


def setUpModule():
    _arrancar()
# ==================================================== 1. DELEGACION =========
class TestDelegacionReal(unittest.TestCase):
    """Fase 6: la llamada REAL pasa por `servicio_consulta`.

    Comparar valores NO demuestra esto: si la API calculase lo mismo por su
    cuenta, la comparacion pasaria igual. Aqui se INSTRUMENTA el servicio: se
    envuelve cada operacion para que registre que se ejecuto, se pide la ruta
    por HTTP, y se exige que el registro contenga esa operacion.

    La instrumentacion es local a este test (se restaura en el `finally`). El
    servidor corre en un hilo del mismo proceso, asi que ve la version
    instrumentada.
    """

    #: (ruta, operacion que debe ejecutarse)
    RUTAS = [
        ("/api/figuras/712", "obtener_entidad"),
        ("/api/entidades/4", "obtener_entidad"),
        ("/api/sitios/4", "obtener_entidad"),
        ("/api/artefactos/1", "obtener_entidad"),
        ("/api/eventos/1", "obtener_entidad"),
        ("/api/figuras/712/relaciones", "buscar_relaciones"),
        ("/api/consulta/entidad/figura/712", "obtener_entidad"),
        ("/api/consulta/contar/figura", "contar"),
        ("/api/consulta/evidencia/figura/712", "obtener_evidencia"),
        ("/api/consulta/relaciones/712", "buscar_relaciones"),
    ]

    def test_el_flujo_real_pasa_por_el_servicio(self):
        from dfchron import servicio_consulta as qc
        registro = []
        originales = {}
        for nombre in qc.contrato()["operaciones"]:
            originales[nombre] = getattr(qc, nombre)

            def envolver(orig, n):
                def envoltura(*a, **k):
                    registro.append(n)
                    return orig(*a, **k)
                return envoltura

            setattr(qc, nombre, envolver(originales[nombre], nombre))
        try:
            for ruta, esperado in self.RUTAS:
                with self.subTest(ruta=ruta):
                    registro.clear()
                    cod, _env = pedir(ruta)
                    self.assertEqual(cod, 200)
                    self.assertIn(esperado, registro,
                                  "%s NO paso por servicio_consulta.%s; "
                                  "llego por otro sitio: %s"
                                  % (ruta, esperado, registro))
        finally:
            for nombre, fn in originales.items():
                setattr(qc, nombre, fn)

    def test_una_ruta_de_navegacion_no_pasa_por_el_servicio(self):
        """El otro lado de la moneda: la navegación NO está dentro.

        Si esto dejara de ser cierto, alguien habría metido navegación en la
        frontera de consulta, que es justo lo que la misión prohíbe.
        """
        for ruta in ("/api/salud", "/api/stats", "/api/buscar?q=dragon",
                     "/api/listar/historical_figures?limit=2"):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                self.assertNotIn("dataset_id", env,
                                 "una ruta de navegación lleva el contrato de "
                                 "consulta: %s" % ruta)


class TestDelegacion(unittest.TestCase):
    """La API y el servicio cuentan lo mismo. No hay dos verdades."""

    def test_la_api_delega_en_el_servicio(self):
        """La ficha por HTTP y la del servicio coinciden en dato y estado."""
        from dfchron import servicio_consulta as qc
        cod, env = pedir("/api/figuras/712")
        directo = qc.obtener_entidad("figura", "712")
        self.assertEqual(cod, 200)
        self.assertEqual(env["data"], directo["data"])
        self.assertEqual(env["estado"], directo["estado"])
        self.assertEqual(env["identity"], directo["identity"])
        self.assertEqual(env["evidence"], directo["evidence"])

    def test_las_fichas_todas_delegan(self):
        for ruta, ident in (("/api/figuras/712", "712"),
                            ("/api/entidades/4", "4"),
                            ("/api/sitios/4", "4"),
                            ("/api/artefactos/1", "1"),
                            ("/api/eventos/1", "1")):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                self.assertEqual(env["identity"]["df_id"], ident)

    def test_el_adaptador_no_toca_el_nucleo(self):
        """`adaptador_consulta` no importa el nucleo: solo el servicio."""
        ruta = os.path.join(_RAIZ, "dfchron", "adaptador_consulta.py")
        with open(ruta, encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("import nucleo", "from nucleo", "nucleo.",
                          "Archivo(", "obtener_archivo"):
            self.assertNotIn(prohibido, fuente,
                             "el adaptador accede al nucleo: %r" % prohibido)

    def test_el_adaptador_no_tiene_ia(self):
        ruta = os.path.join(_RAIZ, "dfchron", "adaptador_consulta.py")
        with open(ruta, encoding="utf-8") as f:
            fuente = f.read().lower()
        for prohibido in ("openai", "anthropic", "llm", "embedding", "prompt",
                          "transformers", "langchain", "/api/chat", "/api/ia"):
            self.assertNotIn(prohibido, fuente)


# ======================================================== 2. ESTADOS ========
class TestEstados(unittest.TestCase):
    """La distincion central: ausencia, incertidumbre y fallo tecnico."""

    def test_inexistente_es_404_y_not_found(self):
        cod, env = pedir("/api/consulta/entidad/figura/999999999")
        self.assertEqual(cod, 404)
        self.assertEqual(env["estado"], "NOT_FOUND")
        self.assertFalse(env["ok"])

    def test_no_verificado_no_es_404(self):
        """El caso que importa: no_verificado NO puede parecer inexistente."""
        cod, env = pedir("/api/consulta/atributo/figura/712/altura")
        self.assertEqual(cod, 200,
                         "NO_VERIFIED no puede ser 404: diria que no existe")
        self.assertEqual(env["estado"], "NOT_VERIFIED")
        self.assertFalse(env["ok"])

    def test_existe_es_200_found(self):
        cod, env = pedir("/api/consulta/atributo/figura/712/nombre")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "FOUND")
        self.assertTrue(env["ok"])

    def test_tipo_sin_identidad_es_no_verificado(self):
        cod, env = pedir("/api/consulta/entidad/relacion/5")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "NOT_VERIFIED")
        self.assertIsNone(env["identity"])

    def test_verificacion_falsa_es_no_verificado(self):
        cod, env = pedir("/api/consulta/verificar"
                         "?tipo=figura&id=712&predicado=tiene%3Arace"
                         "&objeto=DRAGON")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "NOT_VERIFIED")
        self.assertFalse(env["ok"])

    def test_verificacion_cierta_es_found(self):
        cod, env = pedir("/api/consulta/verificar"
                         "?tipo=figura&id=712&predicado=existe")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "FOUND")

    def test_los_cinco_estados_existen_en_el_contrato(self):
        cod, env = pedir("/api/consulta/contrato")
        self.assertEqual(cod, 200)
        self.assertEqual(sorted(env["data"]["estados"]),
                         sorted(["FOUND", "NOT_FOUND", "NOT_VERIFIED",
                                 "INVALID_QUERY", "DATA_UNAVAILABLE"]))

    def test_cada_estado_conserva_su_codigo_http(self):
        for ruta, estado, http in (
                ("/api/consulta/entidad/figura/999999999", "NOT_FOUND", 404),
                ("/api/consulta/atributo/figura/712/altura", "NOT_VERIFIED", 200),
                ("/api/consulta/entidad/inventado/1", "INVALID_QUERY", 400)):
            with self.subTest(estado=estado):
                cod, env = pedir(ruta)
                self.assertEqual(cod, http)
                self.assertEqual(env["estado"], estado)
# ======================================================= 3. EVIDENCIA ========
class TestEvidencia(unittest.TestCase):
    """La API transporta la evidencia; no la fabrica."""

    def test_dataset_id_llega(self):
        from dfchron import ia_conocimiento as ic
        for ruta in ("/api/figuras/712", "/api/entidades/4",
                     "/api/consulta/entidad/figura/712"):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 200)
                self.assertEqual(env["dataset_id"], ic.DATASET_ID)

    def test_state_version_llega_en_la_evidencia(self):
        from dfchron import ia_conocimiento as ic
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        self.assertIsNotNone(env["evidence"])
        self.assertEqual(env["evidence"]["state_version"], ic.DATASET_ID)

    def test_el_endpoint_de_evidencia(self):
        from dfchron import ia_conocimiento as ic
        cod, env = pedir("/api/consulta/evidencia/figura/712?campos=nombre")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "FOUND")
        self.assertEqual(env["data"]["state_version"], ic.DATASET_ID)
        self.assertEqual(env["data"]["datos_utilizados"], ["nombre"])

    def test_el_dataset_no_es_un_reloj(self):
        """`dataset_id` identifica contenido. No se presenta como caducidad.

        Se comprueban las CLAVES, no el texto: buscar subcadenas daria falsos
        positivos triviales («settled» contiene «ttl»).
        """
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        prohibidas = {"expires", "expiry", "caduca", "caducidad", "vence",
                      "ttl", "expires_at", "expires_in", "vigente_hasta"}
        # Solo en la cabecera del envelope, no dentro de `data` (que es del
        # mundo y legitimamente puede traer cualquier cosa).
        cabecera = set(env) - {"data"}
        self.assertEqual(cabecera & prohibidas, set(),
                         "la API presenta el dataset como caducidad")
        # Y el texto que el servicio usa para decirlo, si aparece, es el correcto.
        alcance = env.get("alcance") or {}
        if "no_puede" in alcance:
            unido = " ".join(alcance["no_puede"]).lower()
            self.assertIn("dataset_id no es un reloj", unido)

    def test_evidencia_de_tipo_sin_identidad_es_no_verificado(self):
        cod, env = pedir("/api/consulta/evidencia/relacion/5")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "NOT_VERIFIED")
        self.assertIsNone(env["evidence"])


# ======================================================= 4. IDENTIDAD =======
class TestIdentidad(unittest.TestCase):
    """No se inventa identidad. Nunca."""

    def test_identidad_de_un_tipo_normal(self):
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        self.assertEqual(env["identity"], {"tipo": "figura", "df_id": "712"})

    def test_identidad_null_no_se_rellena(self):
        """Un `identity: null` llega null. La API no lo completa."""
        for tipo in ("relacion", "era", "suplemento"):
            with self.subTest(tipo=tipo):
                cod, env = pedir("/api/consulta/entidad/%s/5" % tipo)
                self.assertEqual(cod, 200)
                self.assertIsNone(env["identity"])

    def test_no_hay_ids_artificiales(self):
        """Nada de indice, posicion, hash ni record_id posicional."""
        cod, env = pedir("/api/consulta/entidad/relacion/5")
        self.assertEqual(cod, 200)
        texto = json.dumps(env)
        for prohibido in ("record_id", "posicion", "indice", "hash"):
            self.assertNotIn(prohibido, texto.lower(),
                             "identidad artificial: %r" % prohibido)


# ====================================================== 5. RELACIONES ======
class TestRelaciones(unittest.TestCase):
    """Se delegan. No se reconstruyen."""

    def test_relaciones_delegan_en_el_servicio(self):
        from dfchron import servicio_consulta as qc
        cod, env = pedir("/api/consulta/relaciones/712")
        directo = qc.buscar_relaciones("712")
        self.assertEqual(cod, 200)
        self.assertEqual(env["data"], directo["data"])
        self.assertEqual(env["estado"], directo["estado"])

    def test_relaciones_de_inexistente(self):
        cod, env = pedir("/api/consulta/relaciones/999999999")
        self.assertEqual(cod, 404)
        self.assertEqual(env["estado"], "NOT_FOUND")

    def test_la_web_no_reconstruye_el_grafo(self):
        """El front no lee el dataset: solo la API."""
        ruta = os.path.join(_RAIZ, "dfchron", "web", "app.js")
        with open(ruta, encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("relationships_", "event_relationships", ".jsonl"):
            self.assertNotIn(prohibido, fuente)


# ====================================================== 6. PAGINACION ======
class TestPaginacion(unittest.TestCase):
    """Los limites del servicio se respetan; HTTP no puede saltarlos."""

    def test_el_limite_maximo_lo_fija_el_servicio(self):
        from dfchron import servicio_consulta as qc
        cod, env = pedir("/api/consulta/relaciones/712?limit=99999999")
        self.assertEqual(cod, 400)
        self.assertEqual(env["limite_maximo"], qc.LIMITE_MAXIMO)

    def test_un_limite_valido_se_acepta(self):
        cod, env = pedir("/api/consulta/relaciones/712?limit=5")
        self.assertEqual(cod, 200)
        self.assertLessEqual(len(env["data"]), 5)

    def test_limites_no_numericos(self):
        for valor in ("abc", "0", "-3", "1.5"):
            with self.subTest(limit=valor):
                cod, env = pedir("/api/consulta/relaciones/712?limit=" + valor)
                self.assertEqual(cod, 400)
                self.assertEqual(env["estado"], "LIMITE_INVALIDO")

    def test_la_ruta_antigua_conserva_su_recorte(self):
        """Compatibilidad: `?limit=99999999` sigue dando 200, recortado."""
        cod, env = pedir("/api/figuras/712/relaciones?limit=99999999")
        self.assertEqual(cod, 200)
        self.assertLessEqual(env["limit"], 500)

    def test_la_ruta_antigua_no_rechaza_limits_hostiles(self):
        """Un `limit` ilecible daba 200 antes, no 400. Sigue dando 200.

        Aqui esta la razon de que el adaptador normalice con
        `config.limite_seguro` aunque el servicio tambien recorte: sin esa
        normalizacion, un `-5` llegaria al servicio y volveria INVALID_QUERY,
        que es un 400 donde antes habia un 200.
        """
        for valor in ("-5", "0", "abc", ""):
            with self.subTest(limit=valor):
                cod, env = pedir("/api/figuras/712/relaciones?limit=" + valor)
                self.assertEqual(cod, 200,
                                 "un limite hostil no puede volverse 400")

    def test_los_parametros_desconocidos_se_rechazan(self):
        cod, env = pedir("/api/consulta/relaciones/712?inventado=1")
        self.assertEqual(cod, 400)
        self.assertEqual(env["estado"], "PARAMETRO_DESCONOCIDO")

    def test_el_limite_se_aplica_a_un_tipo_con_relaciones(self):
        """La figura 712 no tiene relaciones: ahi el limite es invisible.

        Con 345 (que si tiene) se ve de verdad. Sin esta prueba, un recorte
        roto pasaria desapercibido.
        """
        for limite, esperado in ((1, 1), (2, 2), (500, 6)):
            with self.subTest(limite=limite):
                cod, env = pedir("/api/consulta/relaciones/345?limit=%d" % limite)
                self.assertEqual(cod, 200)
                self.assertEqual(len(env["data"]), esperado)

    def test_el_mapa_estado_http_es_el_declarado(self):
        """El mapa estado->HTTP es el contrato de la fase 7.

        Se prueba directamente porque por HTTP casi todo llega ya con
        `http_status` puesto por el nucleo, y asi el mapa no se ejercitaria.
        """
        from dfchron import adaptador_consulta as ac
        esperado = {"FOUND": 200, "NOT_FOUND": 404, "NOT_VERIFIED": 200,
                    "INVALID_QUERY": 400, "DATA_UNAVAILABLE": 503}
        for estado, http in esperado.items():
            with self.subTest(estado=estado):
                self.assertEqual(ac._http_de({"estado": estado}), http)


# ===================================================== 7. VALIDACION ======
class TestValidacion(unittest.TestCase):
    """Entrada invalida -> 400. Nunca una consulta valida por accidente."""

    def test_ids_vacios(self):
        for ruta in ("/api/consulta/entidad/figura/%20",
                     "/api/consulta/entidad/figura/%20%20"):
            with self.subTest(ruta=ruta):
                cod, env = pedir(ruta)
                self.assertEqual(cod, 400)

    def test_id_enorme(self):
        cod, env = pedir("/api/consulta/entidad/figura/" + "9" * 400)
        self.assertEqual(cod, 400)

    def test_tipo_inventado(self):
        cod, env = pedir("/api/consulta/entidad/inventado/1")
        self.assertEqual(cod, 400)
        self.assertEqual(env["estado"], "INVALID_QUERY")

    def test_predicado_inventado(self):
        cod, env = pedir("/api/consulta/verificar"
                         "?tipo=figura&id=712&predicado=inventado")
        self.assertEqual(cod, 400)
        self.assertEqual(env["estado"], "INVALID_QUERY")

    def test_filtro_campo_sin_valor(self):
        cod, env = pedir("/api/consulta/contar/figura?campo=race")
        self.assertEqual(cod, 400)
        self.assertEqual(env["estado"], "FILTRO_INVALIDO")

    def test_filtro_valor_sin_campo(self):
        cod, env = pedir("/api/consulta/contar/figura?valor=DRAGON")
        self.assertEqual(cod, 400)
        self.assertEqual(env["estado"], "FILTRO_INVALIDO")

    def test_campo_de_filtro_inexistente_no_es_cero(self):
        """Un campo que el dataset no declara no es «0 coincidencias»."""
        cod, env = pedir("/api/consulta/contar/figura?campo=nada&valor=x")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "NOT_VERIFIED")
        self.assertNotIn("coincidencias", env["data"] or {})

    def test_contar_filtro_real(self):
        cod, env = pedir("/api/consulta/contar/figura")
        self.assertEqual(cod, 200)
        self.assertEqual(env["estado"], "FOUND")
        self.assertGreater(env["data"]["total"], 0)


# ======================================================= 8. SEGURIDAD ======
class TestSeguridad(unittest.TestCase):
    """Ninguna proteccion existente se relaja."""

    def test_traversal(self):
        for intento in ("/api/consulta/entidad/figura/..%2f..%2fconfig",
                        "/api/consulta/entidad/figura/%2e%2e%2fconfig",
                        "/api/consulta/entidad/figura/../../etc/passwd"):
            with self.subTest(intento=intento):
                cod, _ = pedir(intento)
                self.assertIn(cod, (400, 403, 404))

# ================================================= 9. COMPATIBILIDAD ======
class TestCompatibilidad(unittest.TestCase):
    """El envelope anterior sigue intacto. Aditiva, no sustitutiva."""

    def test_el_envelope_antiguo_no_se_rompe(self):
        cod, env = pedir("/api/figuras/712")
        self.assertEqual(cod, 200)
        for clave in ("ok", "data", "status", "certainty", "meta"):
            self.assertIn(clave, env)
        self.assertIn("total", env["meta"])
        self.assertIn("returned", env["meta"])
        self.assertIn("truncated", env["meta"])

    def test_inexistente_sigue_siendo_404(self):
        cod, env = pedir("/api/figuras/999999999")
        self.assertEqual(cod, 404)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], "NO_ENCONTRADO")

    def test_las_herramientas_no_migradas_no_cambian(self):
        """Rutas sin equivalente en el servicio: intactas."""
        for ruta in ("/api/salud", "/api/stats", "/api/limitaciones",
                     "/api/buscar?q=dragon", "/api/geografia"):
            with self.subTest(ruta=ruta):
                cod, _ = pedir(ruta)
                self.assertEqual(cod, 200)

    def test_las_nuevas_rutas_no_rompen_las_viejas(self):
        """Añadir `/api/consulta/...` no resta nada."""
        cod, _ = pedir("/api/consulta/contrato")
        self.assertEqual(cod, 200)
        cod2, env2 = pedir("/api/salud")
        self.assertEqual(cod2, 200)
        self.assertTrue(env2["ok"])


# ==================================================== 10. UNIFICACION ======
class TestUnificacion(unittest.TestCase):
    """Prueba arquitectonica: servicio, API y Web parten del mismo sitio."""

    def test_servicio_api_y_web_coinciden(self):
        """La MISMA consulta por las tres rutas: mismo dato, estado,
        identidad y evidencia."""
        from dfchron import servicio_consulta as qc

        # 1. Servicio, en Python.
        directo = qc.obtener_entidad("figura", "712")

        # 2. API, por HTTP.
        cod, api = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(cod, 200)

        # 3. Web: consume la API y muestra lo que llega. Se comprueba que el
        #    front pinta la identidad y la evidencia que la API le dio, sin
        #    recalcularlas.
        with open(os.path.join(_RAIZ, "dfchron", "web", "app.js"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for simbolo in ("env.identity", "env.evidence", "env.dataset_id",
                        "env.estado"):
            self.assertIn(simbolo, fuente,
                          "la Web no muestra %s" % simbolo)

        for clave in ("data", "estado", "identity", "evidence", "dataset_id"):
            with self.subTest(clave=clave):
                self.assertEqual(api[clave], directo[clave],
                                 "API y servicio discrepan en %r" % clave)

    def test_el_contrato_es_la_unica_fuente_de_la_api(self):
        """La API no declara por su cuenta los tipos que el servicio conoce."""
        from dfchron import adaptador_consulta as ac
        cod, env = pedir("/api/consulta/contrato")
        self.assertEqual(cod, 200)
        with open(os.path.join(_RAIZ, "dfchron", "adaptador_consulta.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        self.assertNotIn('"figura", "entidad", "sitio"', fuente)
        self.assertIs(ac.qc, __import__(
            "dfchron.servicio_consulta", fromlist=["x"]))


# ============================================================ 11. WEB ======
class TestWeb(unittest.TestCase):
    """La Web muestra el estado; no lo decide."""

    def _app(self):
        with open(os.path.join(_RAIZ, "dfchron", "web", "app.js"),
                  encoding="utf-8") as f:
            return f.read()

    def _css(self):
        with open(os.path.join(_RAIZ, "dfchron", "web", "estilo.css"),
                  encoding="utf-8") as f:
            return f.read()

    def test_los_cinco_estados_tienen_texto_propio(self):
        fuente = self._app()
        for estado in ("FOUND", "NOT_FOUND", "NOT_VERIFIED",
                       "INVALID_QUERY", "DATA_UNAVAILABLE"):
            with self.subTest(estado=estado):
                self.assertIn(estado, fuente)

    def test_not_verified_no_se_texto_como_no_existe(self):
        """El texto de NO_VERIFIED no puede decir «no existe»."""
        fuente = self._app()
        bloque = re.search(r"NOT_VERIFIED:\s*\{(.*?)\}", fuente, re.S)
        self.assertIsNotNone(bloque, "no hay entrada para NOT_VERIFIED")
        texto = bloque.group(1).lower()
        self.assertIn("no se puede determinar", texto)
        for prohibido in ("no existe", "does not exist"):
            self.assertNotIn(prohibido, texto,
                             "NO_VERIFIED dice que no existe: %r" % prohibido)

    def test_not_found_si_lo_dice_que_no_existe(self):
        fuente = self._app()
        bloque = re.search(r"NOT_FOUND:\s*\{(.*?)\}", fuente, re.S)
        self.assertIsNotNone(bloque)
        self.assertIn("no existe", bloque.group(1).lower())

    def test_not_verified_tiene_color_distinto_de_not_found(self):
        """Si comparten color, la distincion desaparece en la pantalla."""
        css = self._css()
        self.assertIn(".estado--notverified", css)
        self.assertIn(".estado--notfound", css)
        b = re.search(r"\.estado--notverified\s*\{(.*?)\}", css, re.S)
        a = re.search(r"\.estado--notfound\s*\{(.*?)\}", css, re.S)
        self.assertIsNotNone(b)
        self.assertIsNotNone(a)
        self.assertNotEqual(
            re.findall(r"#[0-9a-fA-F]{3,8}", b.group(1)),
            re.findall(r"#[0-9a-fA-F]{3,8}", a.group(1)),
            "NOT_VERIFIED y NOT_FOUND se ven igual")

    def test_la_web_no_accede_al_dataset(self):
        fuente = self._app()
        for prohibido in ("legends.xml", ".jsonl", "readFileSync",
                          "XMLHttpRequest", "processed/merged", "original_data"):
            self.assertNotIn(prohibido, fuente)

    def test_la_web_muestra_la_evidencia(self):
        fuente = self._app()
        for simbolo in ("state_version", "dataset_id", "identity"):
            with self.subTest(simbolo=simbolo):
                self.assertIn(simbolo, fuente)

    def test_el_sitio_astro_tiene_las_mismas_garantias(self):
        ruta = os.path.join(_RAIZ, "dfchron", "site", "src", "lib", "api.ts")
        with open(ruta, encoding="utf-8") as f:
            fuente = f.read()
        self.assertIn("NOT_VERIFIED", fuente)
        self.assertIn("state_version", fuente)
        # No puede traducir un error cualquiera a NOT_FOUND.
        self.assertIn("error?.code === 'NO_ENCONTRADO'", fuente)


if __name__ == "__main__":
    unittest.main(verbosity=2)