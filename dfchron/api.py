#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: API HTTP local
===============================

Servidor HTTP minimo, SOLO biblioteca estandar (`http.server`). Sin Flask, sin
FastAPI, sin dependencias externas.

POR QUE ESTA SEPARADA DE LA UI
-------------------------------
    UI (cualquier navegador)
        |
        |  HTTP + JSON
        v
    dfchron.api          <-- este fichero: rutas y translating
        |
        v
    dfchron.servicio     <-- envelopes y validacion
        |
        v
    00_SOURCE/tools/nucleo.py

La UI NUNCA habla con el nucleo ni con los XML. Y esta API NO contiene logica
de Dwarf Fortress: delega. Por eso, montar una web contra la misma API mas
adelante es cambiar el origen de las peticiones, no reescribir el nucleo.

SEGURIDAD POR CONSTRUCCION
--------------------------
* Escucha solo en 127.0.0.1: no es accesible desde la red local.
* No sirve ficheros de disco: la UI se entrega embebida en memoria.
* Toda ruta que no sea `/api/...` devuelve 404. No hay path traversal posible.
* Solo hay un verbo: GET. Ningun endpoint modifica el dataset.
* Los limites se acotan en `config` antes de tocar el nucleo.

Uso:  python -m dfchron.api            o    python run.py
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

try:
    from . import config
    from . import servicio as svc
    from . import adaptador_consulta as ac
except ImportError:              # ejecucion directa: python api.py
    import config
    import servicio as svc
    import adaptador_consulta as ac

VERSION = "1.0"

# La UI se sirve desde memoria. Esto elimina por construccion cualquier
# recorrido de rutas del sistema de ficheros.
UI_DIR = config.WEB_ROOT
_MIMETYPES = {".html": "text/html; charset=utf-8",
              ".css": "text/css; charset=utf-8",
              ".js": "application/javascript; charset=utf-8",
              ".svg": "image/svg+xml"}


class Router:
    """Tabla de rutas: metodo -> patron -> manejador.

    Los patrones usan {nombre} para capturar un segmento. Se comparan sobre
    segmentos ya decodificados, nunca sobre una concatenacion de texto.
    """

    def __init__(self):
        self.rutas = []

    def add(self, patron, manejador, nombre=None):
        self.rutas.append((patron.strip("/").split("/"), manejador, nombre))

    def resolver(self, camino):
        """Devuelve (manejador, params) o (None, None)."""
        segs = [unquote(s) for s in camino.strip("/").split("/") if s]
        for patron, manejador, nombre in self.rutas:
            if len(patron) != len(segs):
                continue
            params = {}
            ok = True
            for p, s in zip(patron, segs):
                if p.startswith("{") and p.endswith("}"):
                    params[p[1:-1]] = s
                elif p != s:
                    ok = False
                    break
            if ok:
                return manejador, params
        return None, None

    def documentacion(self):
        """Lista de endpoints, para /api y para la UI.

        Los patrones ya empiezan por 'api', asi que se antepone solo '/'.
        """
        return sorted({"/" + "/".join(p) for p, _, _ in self.rutas})


R = Router()


def _peticion(f):
    """Envoltura: traduce query params y llama al servicio.

    Los errores de red nunca escapan como excepcion de Python: cualquier
    fallo inesperado se convierte en un error 500 estructurado.
    """
    def manejador(params, q):
        try:
            return f(params, q)
        except Exception as exc:                      # noqa: BLE001
            # No se filtra el traceback al cliente: se registra y se responde.
            print(f"[api] ERROR interno en {f.__name__}: {exc!r}")
            return svc.error("ERROR_INTERNO",
                             "error inesperado en el servidor", http=500)
    return manejador


def _lim(q):
    return q.get("limit", [None])[0]


def _off(q):
    return q.get("offset", [None])[0]


# --- metadatos ---------------------------------------------------------------
R.add("api", _peticion(lambda p, q: svc.envolver_estado({
    "nombre": "DF-Chronicles API", "version": VERSION,
    "endpoints": R.documentacion(),
    "nota": ("Las respuestas usan envelopes: ok, data, meta, "
             "total_encontrados, devueltos, truncado, limit, certainty. "
             "`meta` es la forma canónica; el resto son alias compatibles."),
}, status="OK", certainty="DERIVED")), "raiz")
R.add("api/salud", _peticion(lambda p, q: svc.salud()), "salud")
R.add("api/stats", _peticion(lambda p, q: svc.stats()), "stats")
R.add("api/limitaciones", _peticion(lambda p, q: svc.limitaciones()),
      "limitaciones")

# --- busqueda y listados -----------------------------------------------------
R.add("api/buscar", _peticion(lambda p, q: svc.buscar(
    q.get("q", [""])[0], q.get("tipo", [None])[0], _lim(q))), "buscar")
R.add("api/figuras", _peticion(lambda p, q: svc.buscar(
    q.get("q", [""])[0], "figuras", _lim(q))), "figuras_busqueda")
R.add("api/entidades", _peticion(lambda p, q: svc.buscar(
    q.get("q", [""])[0], "entidades", _lim(q))), "entidades_busqueda")
def _sitios_con_coordenada(p, q):
    """`/api/sitios` acepta texto o coordenadas.

    ANTES, `?x=&y=` caia en la busqueda por texto y respondia
    "el texto de busqueda esta vacio", que no lleva a ninguna parte. Ahora las
    coordenadas se responden por su cuenta y el mensaje de error nombra lo que
    falta de verdad.
    """
    x, y = q.get("x", [None])[0], q.get("y", [None])[0]
    texto = q.get("q", [""])[0]
    if x is not None or y is not None:
        if x is None or y is None:
            falta = "x" if x is None else "y"
            return svc.error(
                "COORDENADA_INVALIDA",
                f"falta la coordenada '{falta}': se necesitan x e y juntas",
                http=400)
        r = svc.geografia_coordenada(x, y)
        if not r.get("ok", True):
            return r
        # Se devuelve en la MISMA forma que la busqueda: una lista de sitios.
        sitios = r["data"]["sitios"]
        return svc.envolver_lista(
            sitios, len(sitios), len(sitios), certainty=svc.FACT,
            nota=("sitios cuya coordenada coincide EXACTAMENTE con (x, y). "
                  "No significa que esten relacionados entre si: solo "
                  "comparten parche."), coordenadas=r["data"]["coordenada"])
    return svc.buscar(texto, "sitios", _lim(q))


R.add("api/sitios", _peticion(_sitios_con_coordenada), "sitios_busqueda")
R.add("api/artefactos", _peticion(lambda p, q: svc.buscar(
    q.get("q", [""])[0], "artefactos", _lim(q))), "artefactos_busqueda")
R.add("api/listar/{tipo}", _peticion(
    lambda p, q: svc.listar(p["tipo"], _lim(q), _off(q))), "listar")

# --- ALIAS (compatibilidad hacia adelante) --------------------------------------
# Rutas ALIAS. NO son endpoints nuevos: cada una delega en la MISMA funcion de
# `servicio` que su ruta canonica, de modo que ambos caminos devuelven el MISMO
# objeto. No hay logica duplicada aqui, y el nucleo sigue siendo la fuente.
#
#   canonica                     alias
#   /api/stats                   /api/estadisticas
#   /api/buscar?tipo=<t>         /api/buscar/<t>
#   /api/geografia/<capa>        /api/sitios/<id>/geografia
#   /api/listar/artefactos       /api/artefactos
R.add("api/estadisticas", _peticion(lambda p, q: svc.stats()), "estadisticas")
R.add("api/buscar/{tipo}", _peticion(
    lambda p, q: svc.buscar(q.get("q", [""])[0], p["tipo"], _lim(q))),
    "buscar_alias")


def _geografia_de_sitio(p, q):
    """Alias: geografia de UN sitio concreto.

    No inventa una capa ni un metodo. Reutiliza `construcciones_en_sitio`, que
    ya existe en el nucleo y enlaza por coincidencia exacta de coordenadas
    (x, y). Lo unico que hace este alias es devolver esas construcciones en la
    forma de listado normalizado.

    Si el sitio no tiene coordenadas, se devuelve UNKNOWN con el motivo: no se
    inventa una posicion.
    """
    a = svc.obtener_archivo()
    if str(p["id"]) not in a.indice.sitios:
        return svc._no_existe("el sitio", p["id"])
    ficha = a.ficha_sitio(str(p["id"]))
    crds = ficha.get("coordenadas")
    sin_coord = (crds in (None, svc.UNKNOWN) or not crds)
    construcciones = ficha.get("construcciones") or []
    if sin_coord:
        return svc.envolver_lista(
            [], 0, config.LIMITE_POR_DEFECTO, certainty=svc.UNKNOWN,
            sitio_id=str(p["id"]), nombre=ficha.get("nombre", svc.UNKNOWN),
            coordenadas=None,
            nota=("este sitio no tiene coordenadas en el XML: no hay "
                  "geografia que mostrar"))
    return svc.envolver_lista(
        construcciones, len(construcciones), config.LIMITE_POR_DEFECTO,
        certainty=svc.DERIVED,
        sitio_id=str(p["id"]), nombre=ficha.get("nombre", svc.UNKNOWN),
        coordenadas=crds,
        metodo="coincidencia exacta de coordenadas (x, y)")


R.add("api/sitios/{id}/geografia", _peticion(_geografia_de_sitio),
      "sitio_geografia")
# El nucleo nombra los tipos de registro en ingles (`artifacts`), que es el
# identificador real de `listar_registros`. Se usa ese nombre, no el espanol.
R.add("api/artefactos", _peticion(
    lambda p, q: svc.listar("artifacts", _lim(q), _off(q))),
    "artefactos_listado")


# --- figuras -----------------------------------------------------------------
R.add("api/figuras/{id}", _peticion(
    lambda p, q: ac.ficha_figura(p["id"])), "figura")
R.add("api/figuras/{id}/eventos", _peticion(
    lambda p, q: svc.figura_eventos(p["id"], _lim(q))), "figura_eventos")
R.add("api/figuras/{id}/cronologia", _peticion(
    lambda p, q: svc.figura_cronologia(p["id"], _lim(q))), "figura_cronologia")
R.add("api/figuras/{id}/relaciones", _peticion(
    lambda p, q: ac.relaciones_figura(p["id"], q)), "figura_relaciones")
R.add("api/figuras/{id}/artefactos", _peticion(
    lambda p, q: svc.figura_artefactos(p["id"])), "figura_artefactos")
R.add("api/figuras/{id}/identidad", _peticion(
    lambda p, q: svc.figura_identidad(p["id"])), "figura_identidad")

# --- entidades ---------------------------------------------------------------
R.add("api/entidades/{id}", _peticion(
    lambda p, q: ac.ficha_entidad(p["id"])), "entidad")
R.add("api/entidades/{id}/miembros", _peticion(
    lambda p, q: svc.entidad_miembros(p["id"], _lim(q))), "entidad_miembros")
R.add("api/entidades/{id}/sitios", _peticion(
    lambda p, q: svc.entidad_sitios(p["id"], _lim(q))), "entidad_sitios")
R.add("api/entidades/{id}/eventos", _peticion(
    lambda p, q: svc.entidad_eventos(p["id"], _lim(q), _off(q))),
    "entidad_eventos")
R.add("api/entidades/{id}/cronologia", _peticion(
    lambda p, q: svc.entidad_cronologia(p["id"], _lim(q))),
    "entidad_cronologia")

# --- sitios ------------------------------------------------------------------
R.add("api/sitios/{id}", _peticion(lambda p, q: ac.ficha_sitio(p["id"])), "sitio")
R.add("api/sitios/{id}/eventos", _peticion(
    lambda p, q: svc.sitio_eventos(p["id"], _lim(q))), "sitio_eventos")
R.add("api/sitios/{id}/cronologia", _peticion(
    lambda p, q: svc.sitio_cronologia(p["id"], _lim(q))), "sitio_cronologia")
R.add("api/sitios/{id}/figuras", _peticion(
    lambda p, q: svc.sitio_figuras(p["id"], _lim(q))), "sitio_figuras")

# --- artefactos --------------------------------------------------------------
R.add("api/artefactos/{id}", _peticion(
    lambda p, q: ac.ficha_artefacto(p["id"])), "artefacto")
R.add("api/artefactos/{id}/propietarios", _peticion(
    lambda p, q: svc.artefacto_propietarios(p["id"])),
    "artefacto_propietarios")
R.add("api/artefactos/{id}/eventos", _peticion(
    lambda p, q: svc.artefacto_eventos(p["id"], _lim(q))), "artefacto_eventos")

# --- eventos -----------------------------------------------------------------
R.add("api/eventos", _peticion(lambda p, q: svc.eventos({
    "anio": q.get("year", q.get("anio", [None]))[0],
    "desde": q.get("from", q.get("desde", [None]))[0],
    "hasta": q.get("to", q.get("hasta", [None]))[0],
    "tipo": q.get("type", q.get("tipo", [None]))[0],
    "figura": q.get("figure", q.get("figura", [None]))[0],
    "sitio": q.get("site", q.get("sitio", [None]))[0],
    "entidad": q.get("entity", q.get("entidad", [None]))[0],
    "limit": _lim(q), "offset": _off(q)})), "eventos")
R.add("api/eventos/tipos", _peticion(
    lambda p, q: svc.tipos_evento()), "eventos_tipos")
R.add("api/eventos/{id}", _peticion(lambda p, q: ac.ficha_evento(p["id"])), "evento")
R.add("api/eventos/{id}/participantes", _peticion(
    lambda p, q: svc.evento_participantes(p["id"])), "evento_participantes")

# --- relaciones, conflictos y geografia --------------------------------------
R.add("api/relaciones/tipos", _peticion(
    lambda p, q: svc.tipos_relacion()), "relaciones_tipos")
R.add("api/conflictos", _peticion(
    lambda p, q: svc.conflictos(_lim(q))), "conflictos")
def _geografia_con_coordenada(p, q):
    """/api/geografia?x=&y= : punto exacto. Sin coordenadas: el resumen.

    ANTES este endpoint ignoraba x e y en silencio y devolvia el resumen
    completo: un cliente creia haber filtrado y no lo habia hecho. Ahora si
    vienen las dos, se devuelve la geografia del punto; si falta alguna, se
    responde 400 diciendo cual falta.
    """
    x = q.get("x", [None])[0]
    y = q.get("y", [None])[0]
    if x is None and y is None:
        return svc.geografia()
    if x is None or y is None:
        falta = "x" if x is None else "y"
        return svc.error(
            "COORDENADA_INVALIDA",
            f"falta la coordenada '{falta}': se necesitan x e y juntas",
            http=400)
    return svc.geografia_coordenada(x, y)


R.add("api/geografia", _peticion(_geografia_con_coordenada), "geografia")
R.add("api/geografia/{capa}", _peticion(
    lambda p, q: svc.geografia(p["capa"], _lim(q), _off(q))), "geografia_capa")
R.add("api/geografia/construcciones/{x}/{y}", _peticion(
    lambda p, q: svc.construir_en_coordenada(p["x"], p["y"])),
    "geografia_coordenada")

# --- geografía por coordenada -------------------------------------------------
# `?x=&y=` en /api/geografia devolvía ANTES el resumen completo ignorando los
# parámetros en silencio: el cliente creía haber filtrado y no lo había hecho.
# Ahora, si vienen x e y, se devuelve la geografía de ese punto; si falta
# alguno, se responde 400 diciendo cuál falta.
R.add("api/geografia/punto/{x}/{y}", _peticion(
    lambda p, q: svc.geografia_coordenada(p["x"], p["y"])),
    "geografia_punto")
R.add("api/geografia/area/{x}/{y}", _peticion(
    lambda p, q: svc.geografia_area(p["x"], p["y"], q.get("ancho", [None])[0],
                                    q.get("alto", [None])[0],
                                    q.get("capas", [None])[0])),
    "geografia_area")

# --- exportacion -------------------------------------------------------------
R.add("api/exportar", _peticion(lambda p, q: svc.exportar(
    q.get("format", ["json"])[0],
    figura_id=q.get("figura", [None])[0],
    entidad_id=q.get("entidad", [None])[0],
    sitio_id=q.get("sitio", [None])[0],
    nombre=q.get("nombre", [None])[0],
    escribir=q.get("escribir", ["0"])[0] in ("1", "true", "si", "yes"))),
    "exportar")


# --- contrato de consulta determinista ---------------------------------------
# Rutas NUEVAS. No existian: antes `/api/consulta/...` daba 404 y sigue dando
# 404 para cualquier otra cosa bajo ese prefijo. No rompen nada porque no hay
# nada que romper.
#
# Estas exponen el contrato completo de `servicio_consulta` por HTTP, que es
# lo que permite que un consumidor futuro (una web, un script, otro programa)
# use el servicio sin conocer Python.
R.add("api/consulta/contrato", _peticion(lambda p, q: ac.contrato()),
      "consulta_contrato")
R.add("api/consulta/entidad/{tipo}/{id}", _peticion(
    lambda p, q: ac.entidad(p, q)), "consulta_entidad")
R.add("api/consulta/atributo/{tipo}/{id}/{atributo}", _peticion(
    lambda p, q: ac.atributo(p, q)), "consulta_atributo")
R.add("api/consulta/relaciones/{id}", _peticion(
    lambda p, q: ac.relaciones(p, q)), "consulta_relaciones")
R.add("api/consulta/contar/{tipo}", _peticion(
    lambda p, q: ac.contar(p, q)), "consulta_contar")
R.add("api/consulta/verificar", _peticion(
    lambda p, q: ac.verificar(p, q)), "consulta_verificar")
R.add("api/consulta/evidencia/{tipo}/{id}", _peticion(
    lambda p, q: ac.evidencia(p, q)), "consulta_evidencia")


# --- chronicles v1 -------------------------------------------------------------
# Rutas NUEVAS de la cronica. Patron identico a `/api/consulta/...`: el
# manejador es UNA llamada al adaptador (`ac.`), que traduce HTTP al servicio
# (`servicio_consulta.consultar_*`). La API NO contiene logica de dominio: si
# el servicio cambiara su respuesta, el test de delegacion fallaria.
R.add("api/chronicles/fortaleza", _peticion(
    lambda p, q: ac.fortaleza(p, q)), "chronicles_fortaleza")
R.add("api/chronicles/figuras", _peticion(
    lambda p, q: ac.figuras(p, q)), "chronicles_figuras")
R.add("api/chronicles/figuras/{hfid}", _peticion(
    lambda p, q: ac.figura(p, q)), "chronicles_figura")
R.add("api/chronicles/eventos", _peticion(
    lambda p, q: ac.eventos(p, q)), "chronicles_eventos")
R.add("api/chronicles/eventos/{id}", _peticion(
    lambda p, q: ac.evento(p, q)), "chronicles_evento")
R.add("api/chronicles/cronologia", _peticion(
    lambda p, q: ac.cronologia(p, q)), "chronicles_cronologia")
R.add("api/chronicles/tipos", _peticion(
    lambda p, q: ac.tipos_evento(p, q)), "chronicles_tipos")


# =============================================================================
# SERVIDOR
# =============================================================================
class Manejador(BaseHTTPRequestHandler):
    """Manejador HTTP. Solo GET, solo local, sin acceso a ficheros."""

    server_version = f"DF-Chronicles/{VERSION}"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # -- CORS ------------------------------------------------------------------
    # La API es GET-only y local, pero la web de Astro se sirve desde otro
    # origen. Solo se responde a los origenes de la lista blanca de `config`:
    # un origen desconocido NO recibe `Access-Control-Allow-Origin`, y el
    # navegador bloquea la respuesta. Nunca se envia `*`.
    def _cabeceras_cors(self):
        origen = self.headers.get("Origin")
        cab = {}
        if origen and origen in config.ORIGENES_CORS:
            cab["Access-Control-Allow-Origin"] = origen
            cab["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            cab["Access-Control-Allow-Headers"] = "Content-Type"
            cab["Access-Control-Max-Age"] = "600"
        # La respuesta depende del Origin: sin esto, una cache compartida podria
        # devolver la cabecera de un origen a otro.
        cab["Vary"] = "Origin"
        return cab

    def do_OPTIONS(self):                                 # noqa: N802
        """Preflight. Siempre 204; quien filtra es la cabecera de origen.

        Un origen no permitido recibe 204 SIN `Access-Control-Allow-Origin`, y
        el navegador descarta la respuesta. A diferencia de un 403, asi el
        preflight de un origen desconocido no revela nada sobre la API.
        """
        self.send_response(204)
        for k, v in self._cabeceras_cors().items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- utilidades -----------------------------------------------------------
    def _enviar_json(self, obj, codigo=200):
        cuerpo = json.dumps(obj, ensure_ascii=False,
                           default=str).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in self._cabeceras_cors().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _enviar_fichero_ui(self, nombre_rel):
        """Sirve un fichero de la UI desde disco, contenido dentro de web/.

        La ruta se resuelve y se COMPRUEBA que siga dentro de UI_DIR antes de
        abrirla. Aunque el nombre ya viene filtrado, se valida de nuevo: es la
        unica defensa real contra path traversal.
        """
        raiz = os.path.realpath(UI_DIR)
        destino = os.path.realpath(os.path.join(raiz, nombre_rel))
        if destino != raiz and not destino.startswith(raiz + os.sep):
            return self._enviar_json(
                svc.error("RUTA_INVALIDA", "ruta no permitida", http=403), 403)
        if not os.path.isfile(destino):
            return self._enviar_json(
                svc.error("NO_ENCONTRADO", "fichero de UI no encontrado",
                          http=404), 404)
        with open(destino, "rb") as f:
            cuerpo = f.read()
        ext = os.path.splitext(destino)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type",
                         _MIMETYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):
        """Log compacto: una linea por peticion."""
        print(f"[api] {self.address_string()} {fmt % args}")

    # -- verbo unico ----------------------------------------------------------
    def do_GET(self):                                  # noqa: N802
        url = urlparse(self.path)
        camino = unquote(url.path)
        q = parse_qs(url.query, keep_blank_values=True)

        # 1. API
        if camino == "/api" or camino.startswith("/api/"):
            manejador, params = R.resolver(camino)
            if manejador is None:
                return self._enviar_json(
                    svc.error("RUTA_DESCONOCIDA",
                              f"no existe el endpoint {camino}", http=404), 404)
            resultado = manejador(params, q)
            codigo = resultado.pop("http_status", 200) if isinstance(
                resultado, dict) else 200
            return self._enviar_json(resultado, codigo)

        # 2. UI estatica. Cualquer otra ruta NO se sirve desde disco.
        if camino in ("/", "/index.html"):
            return self._enviar_fichero_ui("index.html")
        if camino.startswith("/static/"):
            resto = camino[len("/static/"):]
            if not resto or os.path.isabs(resto):
                return self._enviar_json(
                    svc.error("RUTA_INVALIDA", "ruta no permitida", http=403),
                    403)
            return self._enviar_fichero_ui(resto)

        return self._enviar_json(
            svc.error("NO_ENCONTRADO", f"no existe {camino}", http=404), 404)

    def do_POST(self):                                 # noqa: N802
        # No hay ningun endpoint de escritura. Se responde 405, no 404, para
        # que quede claro que el verbo existe pero no se permite.
        self._enviar_json(
            svc.error("METODO_NO_PERMITIDO",
                      "esta API es de solo lectura: use GET", http=405), 405)

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST


def crear_servidor(host=None, puerto=None):
    """Crea el servidor. No lo arranca.

    Se usa `is None` y no `or` a proposito: el puerto 0 es una peticion
    VALIDA de "elige tu un puerto libre", pero `0 or PUERTO_DEFECTO`
    devuelve el puerto por defecto. Con un servidor ya escuchando en el puerto
    habitual, eso hacia que `crear_servidor("127.0.0.1", 0)` no creara el
    servidor esperado, y las pruebas acababan hablando con el ajeno.
    """
    host = config.HOST_PUERTA_DEFECTO if host is None else host
    puerto = config.PUERTO_DEFECTO if puerto is None else int(puerto)
    return ThreadingHTTPServer((host, puerto), Manejador)


def arrancar(host=None, puerto=None, abrir_navegador=False):
    """Arranca el servidor y sirve para siempre."""
    srv = crear_servidor(host, puerto)
    url = f"http://{srv.server_address[0]}:{srv.server_address[1]}/"
    print(f"DF-Chronicles API escuchando en {url}")
    print(f"  documento de la API: {url}api")
    print("  Ctrl+C para detener.")
    if abrir_navegador:
        try:
            import webbrowser
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        except Exception:                              # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDF-Chronicles detenido.")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    import sys
    argumentos = sys.argv[1:]
    _puerto = int(argumentos[0]) if argumentos else None
    sys.exit(arrancar(puerto=_puerto, abrir_navegador=True))
