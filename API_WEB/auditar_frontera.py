#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: auditoria permanente de la FRONTERA API/WEB
=================================================================

QUE DEMUESTRA
-------------
Que existe una unica via de acceso al conocimiento, y permite demostrarlo
leyendo el CODIGO de las rutas, no comparando resultados.

Una prueba que compara «el JSON de la API» con «el JSON del servicio» pasa
igual aunque la API se salte el servicio, si el resultado coincide. Aqui se
inspecciona el manejador de cada ruta y se determina a quien llama de verdad.

CLASIFICACION
-------------
El criterio es SEMANTICO, no «devuelve JSON»:

    consulta      -> afirma algo sobre una entidad concreta. Necesita
                     identidad y evidencia, asi que pasa por la frontera.
    navegacion    -> devuelve un subconjunto para orientarse. No afirma que
                     algo sea cierto: no gana nada con la frontera.
    estadisticas  -> cuenta agregada. No es una afirmacion sobre una entidad.
    metadatos     -> describe el dataset o el contrato, no el contenido.
    salud         -> estado del SERVICIO, no del conocimiento.
    exportacion   -> volca datos a disco; es un consumidor de salida.

GARANTIAS
---------
- SOLO LECTURA: no modifica nada del repositorio.
- DETERMINISTA: mismo codigo -> mismo informe, sin relojes ni azar.
- No requiere servidor en ejecucion.
- No es producto: no lo importa `dfchron.api`.

Uso:
    python API_WEB/auditar_frontera.py
    python API_WEB/auditar_frontera.py --json informe.json
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)


# --------------------------------------------------------------- CLASIFICACION
#: (prefijo de ruta, tipo semantico, razon)
REGLAS = (
    ("api/consulta", "consulta",
     "Expone una operacion del contrato de consulta. Afirma sobre entidades."),
    ("api/salud", "salud",
     "Estado del SERVICIO (carga, dataset disponible). No es conocimiento."),
    ("api/stats", "estadisticas",
     "Cuenta agregada del dataset. No afirma nada sobre una entidad concreta."),
    ("api/estadisticas", "estadisticas",
     "ALIAS de /api/stats. Misma funcion, mismo criterio."),
    ("api/limitaciones", "metadatos",
     "Declara lo que el dataset NO sabe. Es contrato, no contenido."),
    ("api/exportar", "exportacion",
     "Vuelca a disco. Es un consumidor de salida, no una consulta."),
    ("api/relaciones/tipos", "metadatos",
     "Vocabulario de relaciones. Declara, no afirma."),
    ("api/eventos/tipos", "metadatos",
     "Vocabulario de eventos. Declara, no afirma."),
    ("api/conflictos", "navegacion",
     "Listado de conflictos entre fuentes. Explora, no afirma."),
    ("api/buscar", "navegacion",
     "Busqueda por texto: orientacion. Un 'no aparece' NO es un hecho."),
    ("api/figuras", "navegacion", "ALIAS de busqueda de figuras."),
    ("api/entidades", "navegacion", "ALIAS de busqueda de entidades."),
    ("api/sitios", "navegacion", "Busqueda o coordenadas: orientacion espacial."),
    ("api/artefactos", "navegacion", "Listado o busqueda de artefactos."),
    ("api/listar", "navegacion", "Listado paginado: orientacion."),
    ("api/geografia", "navegacion", "Geografia: capas y puntos, no afirmaciones."),
    ("api/eventos", "navegacion",
     "Listado de eventos filtrado: exploracion del historico."),
)

#: Subrutas de ficha: afirman sobre UNA entidad -> la frontera aporta identidad
#: y evidencia. Son las unicas migradas ademas de /api/consulta/*.
FICHAS = {
    "api/figuras/{id}": "obtener_entidad('figura')",
    "api/entidades/{id}": "obtener_entidad('entidad')",
    "api/sitios/{id}": "obtener_entidad('sitio')",
    "api/artefactos/{id}": "obtener_entidad('artefacto')",
    "api/eventos/{id}": "obtener_entidad('evento')",
    "api/figuras/{id}/relaciones": "buscar_relaciones",
}

#: Subrutas de navegacion que se apoyan en una entidad pero NO afirman nada
#: sobre ella: son relaciones "de listado", no afirmaciones verificadas.
NAVEGACION_SOBRE_ENTIDAD = {
    "api/figuras/{id}/eventos", "api/figuras/{id}/cronologia",
    "api/figuras/{id}/artefactos", "api/figuras/{id}/identidad",
    "api/entidades/{id}/miembros", "api/entidades/{id}/sitios",
    "api/entidades/{id}/eventos", "api/entidades/{id}/cronologia",
    "api/sitios/{id}/eventos", "api/sitios/{id}/cronologia",
    "api/sitios/{id}/figuras", "api/sitios/{id}/geografia",
    "api/artefactos/{id}/propietarios", "api/artefactos/{id}/eventos",
    "api/eventos/{id}/participantes",
}


def _funcion_real(manejador):
    """Desenvuelve el cierre que produce `_peticion`.

    `api._peticion(f)` devuelve `maneja_dor`, cuyo `__closure__` guarda `f`.
    Sin desenvolver, `inspect.getsource` daria el fuente del envoltorio —que
    contiene `svc.error`— y TODAS las rutas parecerian llamar a `servicio`.
    """
    for celda in (getattr(manejador, "__closure__", None) or ()):
        try:
            valor = celda.cell_contents
        except ValueError:
            continue
        if callable(valor):
            return valor
    return manejador


def _llama_a(manejador):
    """Nombre del modulo al que llama realmente el manejador de la ruta.

    Se lee el CODIGO. No se infiere del resultado: eso es justamente lo que
    un bypass puede imitar.
    """
    real = _funcion_real(manejador)
    try:
        fuente = inspect.getsource(real)
    except (OSError, TypeError):
        return "desconocido"
    if "ac." in fuente:
        return "adaptador_consulta"
    if "svc." in fuente:
        return "servicio"
    if "config." in fuente:
        return "config"
    return "desconocido"


def clasificar(patron):
    """(tipo, razon, debe_pasar_por_frontera)."""
    if patron == "api":
        return ("metadatos",
                "Documento de la API: describe endpoints, no conocimiento.",
                False)
    if patron in FICHAS:
        return ("consulta",
                "Afirma sobre UNA entidad concreta: aporta identidad y "
                "evidencia. Es la razon de estar en la frontera.",
                True)
    if patron in NAVEGACION_SOBRE_ENTIDAD:
        return ("navegacion",
                "Se apoya en una entidad pero devuelve un LISTADO. Un listado "
                "no lleva evidencia por elemento: migrarlo no aportaria nada.",
                False)
    for prefijo, tipo, razon in REGLAS:
        if patron == prefijo or patron.startswith(prefijo + "/"):
            # `/api/consulta/*` SI es frontera por definicion: es el contrato.
            return (tipo, razon, tipo == "consulta")
    return ("navegacion", "Sin regla explicita: se clasifica como navegacion.",
            False)


def auditar():
    """Recorre TODAS las rutas registradas y las clasifica. Solo lectura."""
    from dfchron import api

    filas = []
    for patron, manejador, nombre in api.R.rutas:
        tipo, razon, debe = clasificar("/".join(patron))
        filas.append({
            "endpoint": "/" + "/".join(patron),
            "nombre": nombre,
            "tipo": tipo,
            "delega_en": _llama_a(manejador),
            "debe_pasar_por_frontera": debe,
            "razon": razon,
        })
    filas.sort(key=lambda f: f["endpoint"])
    return {
        "herramienta": "auditar_frontera",
        "tipo": "HERRAMIENTA DE AUDITORIA (no productiva)",
        "garantias": {
            "solo_lectura": True,
            "determinista": True,
            "modifica_originales": False,
            "es_producto": False,
        },
        "total_rutas": len(filas),
        "por_frontera": sum(1 for f in filas
                            if f["delega_en"] == "adaptador_consulta"),
        "deben_pasar_por_frontera": sum(1 for f in filas
                                        if f["debe_pasar_por_frontera"]),
        "rutas": filas,
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Auditoria de la frontera API/Web (solo lectura)")
    p.add_argument("--json", default=None, help="salida JSON")
    args = p.parse_args(argv)

    informe = auditar()

    print("=" * 78)
    print("P1 :: AUDITORIA DE LA FRONTERA API/WEB")
    print("=" * 78)
    print("Rutas registradas            : %d" % informe["total_rutas"])
    print("Delegan en el adaptador      : %d" % informe["por_frontera"])
    print("Deberian pasar por frontera  : %d" % informe["deben_pasar_por_frontera"])
    print()
    print("%-46s %-13s %-20s" % ("ENDPOINT", "TIPO", "DELEGA EN"))
    print("-" * 78)
    for f in informe["rutas"]:
        marca = "  *" if f["debe_pasar_por_frontera"] else "   "
        print("%s%-44s %-13s %-20s" % (marca, f["endpoint"], f["tipo"],
                                       f["delega_en"]))
    print()
    print("(*) = debe pasar por la frontera determinista")

    if args.json:
        texto = json.dumps(informe, indent=2, sort_keys=True, ensure_ascii=False)
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
        print("\ninforme escrito en: %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
