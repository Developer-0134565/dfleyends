#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Arranque
========================

Punto de entrada unico de la aplicacion.

    python run.py                 # arranca en http://127.0.0.1:877/
    python run.py 9000            # en otro puerto
    python run.py --sin-navegador # no abre el navegador
    python run.py --comprobar     # no arranca: comprueba datos y API
    python run.py --actualizar    # actualiza los datos manualmente y sale

No requiere instalar nada: solo la biblioteca estandar de Python 3.
"""
import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import config            # noqa: E402
from dfchron import servicio as svc    # noqa: E402
from dfchron import api                # noqa: E402


def comprobar():
    """Verifica que los datos existen y que el núcleo responde."""
    print("DF-Chronicles :: comprobacion previa")
    print("=" * 62)
    rutas = config.resumen_rutas()
    for clave in ("PROJECT_ROOT", "DATA_ROOT", "ORIGINAL_DATA_ROOT",
                  "PROCESSED_ROOT", "MERGED_ROOT", "EXPORT_ROOT"):
        print(f"  {clave:20s} {rutas[clave]}")
    if not os.path.isdir(rutas["MERGED_ROOT"]):
        print("\nERROR: no existe el dataset normalizado.")
        print("       Ejecuta primero:  python 00_SOURCE/tools/integrar_legends.py")
        return 1

    print("\n  Cargando el indice (unos segundos)...")
    e = svc.stats()
    d = e["data"]
    print(f"    Figuras      : {d['figuras']:,}")
    print(f"    Entidades    : {d['entidades']:,}")
    print(f"    Sitios       : {d['sitios']:,}")
    print(f"    Eventos      : {d['eventos']:,}")
    print(f"    Artefactos   : {d['artefactos']:,}")
    print(f"    Relaciones   : {d['relaciones']:,}")
    print(f"    Anios        : {d['anio_min']}-{d['anio_max']}")
    print("\n  API y UI: OK (endpoints en /api)")
    return 0


def main():
    p = argparse.ArgumentParser(description="DF-Chronicles")
    p.add_argument("puerto", nargs="?", type=int, default=None,
                   help="puerto HTTP (por defecto 877)")
    p.add_argument("--host", default=None, help="interfaz (por defecto 127.0.0.1)")
    p.add_argument("--sin-navegador", action="store_true",
                   help="no abrir el navegador automaticamente")
    p.add_argument("--comprobar", action="store_true",
                   help="solo comprobar los datos y salir")
    p.add_argument("--actualizar", action="store_true",
                   help="actualizar manualmente los datos y salir")
    p.add_argument("--estado", action="store_true",
                   help="mostrar el estado de los datos y salir")
    args = p.parse_args()

    if args.comprobar:
        return comprobar()

    if args.actualizar or args.estado:
        sys.path.insert(0, config.TOOLS_ROOT)
        import actualizar_datos
        return actualizar_datos.main(["actualizar" if args.actualizar
                                      else "estado"])

    print("=" * 62)
    print("DF-Chronicles iniciado")
    print("=" * 62)
    print(f"  Datos   : {config.DATA_ROOT}")
    print(f"  Índice  : {config.MERGED_ROOT}")
    print(f"  Exports : {config.EXPORT_ROOT}")
    print(f"  UI      : {config.WEB_ROOT}")
    print()
    try:
        svc.obtener_archivo()
        print(f"  Núcleo cargado en {svc.obtener_archivo().tiempo_carga:.2f}s")
    except Exception as exc:                          # noqa: BLE001
        print(f"  ERROR al cargar el núcleo: {exc}")
        return 1
    print()
    return api.arrancar(args.host, args.puerto,
                        abrir_navegador=not args.sin_navegador)


if __name__ == "__main__":
    sys.exit(main())
