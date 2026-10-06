#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: servidor estatico para pruebas de la web
==========================================================

Sirve `dfchron/site/dist/` como lo haria un hosting estatico, INCLUDING el
fallback a `404.html`. Eso es lo que hace Cloudflare Workers con
`not_found_handling: "404-page"`, y es imprescindible para comprobar el
comportamiento real de las rutas limpias (`/figures/712`).

Por que hace falta y por que no se usa `astro preview`:

`astro preview` sirve ficheros LITERALES y devuelve 404 para `/figures/712`,
porque no aplica los `rewrites` ni el fallback. El despliegue real si los
aplica. Para auditar lo que se desplegaria de verdad hay que servirlo como lo
sirve el hosting.

NO es parte de la aplicacion: es una herramienta de pruebas, como las demas de
`dfchron/pruebas/`. No se importa desde la API ni desde la web.

Uso:
    python dfchron\\pruebas\\servidor_estatico.py [--puerto 4400] [--dist RUTA]
"""
import argparse
import functools
import http.server
import os
import socketserver

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
DIST_POR_DEFECTO = os.path.join(RAIZ, "dfchron", "site", "dist")


class ManejadorEstatico(http.server.SimpleHTTPRequestHandler):
    """Sirve `dist/` con las mismas reglas que un hosting estatico.

    - Si la ruta no existe, sirve `404.html` (fallback), como Cloudflare.
    - Si la ruta es un directorio, sirve su `index.html`.
    - Nunca sale de `dist/`: se valida la ruta resuelta.
    """

    def translate_path(self, path):
        raiz = os.path.realpath(self.directory)
        destino = os.path.realpath(os.path.join(raiz, super().translate_path(path)))
        # Defensa contra traversal: todo lo que se sirve esta dentro de dist/.
        if destino != raiz and not destino.startswith(raiz + os.sep):
            return os.path.join(raiz, "404.html")
        if os.path.isdir(destino):
            indice = os.path.join(destino, "index.html")
            if os.path.isfile(indice):
                return indice
        if os.path.isfile(destino):
            return destino
        # Ruta desconocida -> el shell SPA (404.html).
        return os.path.join(raiz, "404.html")

    def end_headers(self):
        # El cache no debe interferir con la auditoria: cada recarga es nueva.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass   # silencio: esta herramienta es auxiliar


def servir(dist, puerto=4400):
    # `abspath` es imprescindible: `SimpleHTTPRequestHandler` resuelve las
    # rutas relativas contra `self.directory`. Con una ruta RELATIVA el join
    # se descuadra y TODAS las peticiones caen al 404.html (incluidos los
    # .css y .js), dejando la pagina sin estilos. Se detecto al auditar el
    # build publico y se corrige aqui.
    dist = os.path.abspath(dist)
    if not os.path.isdir(dist):
        raise SystemExit(f"No existe el build: {dist}\n"
                         "Ejecuta antes:  cd dfchron/site && npm run build")
    socketserver.TCPServer.allow_reuse_address = True
    manejador = functools.partial(ManejadorEstatico, directory=dist)
    with socketserver.TCPServer(("127.0.0.1", puerto), manejador) as srv:
        print(f"Servidor estatico en http://127.0.0.1:{puerto}/  (root: {dist})")
        print("Fallback 404.html activo. Ctrl+C para detener.")
        srv.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=4400)
    ap.add_argument("--dist", default=DIST_POR_DEFECTO)
    args = ap.parse_args()
    servir(args.dist, args.puerto)