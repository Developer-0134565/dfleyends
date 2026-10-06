# =============================================================================
# DF-Chronicles :: P1.3 -- HERRAMIENTA DE INVESTIGACION (NO PRODUCTIVA)
# -----------------------------------------------------------------------------
# INVENTARIO ESTÁTICO DE EXPORTADORES DFHack
#
# PROPOSITO
#   Auditar automáticamente los scripts de exportación de DFHack para responder,
#   con evidencia reproducible y determinista, a la pregunta:
#     "En qué puntos cede el control el exportador, y por tanto en qué puntos
#      puede cambiar el mundo mientras se escribe el fichero?"
#
# QUE HACE
#   Analiza ficheros .lua de DFHack de forma ESTATICA (no ejecuta Lua) y produce
#   un inventario de:
#     - puntos de cesion (script.sleep / coroutine.yield / dfhack.suspend)
#     - lecturas del mundo (df.global.world.*, dfhack.world.Read*)
#     - escrituras a disco (io.open, file:write)
#     - escrituras a memoria de DF (asignaciones a df.global.*)
#     - metadatos capturados (save_dir, world_data.name, fecha de mundo)
#
# GARANTIAS DE ESTA HERRAMIENTA
#   - SOLO LECTURA. Nunca escribe en los .lua analizados ni en los saves.
#   - DETERMINISTA: misma entrada -> misma salida. Sin timestamps, sin azar, sin
#     dependencia del orden del sistema de ficheros.
#   - No requiere Dwarf Fortress en ejecucion (analisis estatico).
#   - No es producto: no lo importa dfchron.servicio ni la API.
#
# USO
#   python inventario_exportador.py
#   python inventario_exportador.py --json salida.json
#   python inventario_exportador.py --raiz <ruta DFHack/hack>
# =============================================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# Lexicon. Cada patron apunta a una CLASE DE EVENTO, no a un significado.
# Documentado explicitamente: esto describe la SINTAXIS observada, no la
# semantica garantizada por DFHack.
# --------------------------------------------------------------------------
PATRONES: dict[str, "re.Pattern[str]"] = {
    # Cesion de control: el script devuelve el control al juego.
    "cesion_script_sleep": re.compile(r"\bscript\.sleep\s*\("),
    "cesion_suspend": re.compile(r"\bdfhack\.suspend\s*\("),
    "cesion_with_suspend": re.compile(r"\bwith_suspend\s*\("),
    "cesion_coroutine_yield": re.compile(r"\bcoroutine\.yield\s*\("),
    "cesion_start_script": re.compile(r"\bscript\.start\s*\("),
    # Reloj de mundo.
    "reloj_readcurrent": re.compile(
        r"\bdfhack\.world\.Read(Current\w+|WorldFolder)\s*\("),
    "reloj_frame_counter": re.compile(r"\bframe_counter\b"),
    "reloj_cur_year": re.compile(r"\bdf\.global\.cur_year\b"),
    "reloj_cur_year_tick": re.compile(r"\bdf\.global\.cur_year_tick\b"),
    "reloj_get_tick_count": re.compile(r"\bdfhack\.getTickCount\s*\("),
    # Relojes NO de mundo (del host / del proceso).
    "host_reloj": re.compile(r"\bos\.time\s*\(|\bos\.getpid\s*\("),
    # Persistencia dentro del save.
    "persistencia_world_data": re.compile(
        r"\bdfhack\.persistent\.(get|save|delete)WorldData\w*\s*\("),
    "persistencia_site_data": re.compile(
        r"\bdfhack\.persistent\.(get|save|delete)SiteData\w*\s*\("),
    "persistencia_unsaved": re.compile(
        r"\bdfhack\.persistent\.getUnsavedSeconds\s*\("),
    # Identidad: mundo / save.
    "identidad_save_dir": re.compile(r"\bcur_savegame\.save_dir\b"),
    "identidad_world_data_name": re.compile(r"\bworld_data\.name\b"),
    "identidad_read_world_folder": re.compile(
        r"\bdfhack\.world\.ReadWorldFolder\s*\("),
    # Escrituras.
    "escritura_io_open": re.compile(r"\bio\.open\s*\("),
    "escritura_file_write": re.compile(r"\bfile:write\s*\("),
    "escritura_memoria_df": re.compile(r"df\.global\.[A-Za-z_][\w.]*\s*="),
    # Hooks de ciclo de vida.
    "hook_state_change": re.compile(r"\bdfhack\.onStateChange\s*\["),
}


# Documentacion de cada clase, para que el informe sea autocontenido.
DESCRIPCION: dict[str, str] = {
    "cesion_script_sleep":
        "El script cede el control al juego durante N frames. NO congela la "
        "simulacion: el mundo puede avanzar.",
    "cesion_suspend":
        "dfhack.suspend() toma el lock de core. La documentacion lo describe como "
        "necesario para 'acceder a un estado consistente de la memoria de DF'. "
        "No afirma que el mundo deje de avanzar.",
    "cesion_with_suspend":
        "dfhack.with_suspend(f) ejecuta f con el lock de core tomado.",
    "cesion_coroutine_yield": "Cede la corrutina al planificador de Lua.",
    "cesion_start_script":
        "script.start() arranca el script como corrutina (asincrono).",
    "reloj_readcurrent":
        "Reloj de mundo expuesto por DFHack (year/tick/month/day/worldfolder).",
    "reloj_frame_counter":
        "Contador de ticks DESDE EL INICIO DEL ANO (se reinicia cada ano).",
    "reloj_cur_year": "Anio de mundo actual.",
    "reloj_cur_year_tick": "Tick intra-anio del mundo.",
    "reloj_get_tick_count":
        "Reloj de RENDER del proceso (milisegundos). Se reinicia al arrancar el "
        "proceso. NO es reloj de mundo.",
    "host_reloj": "Reloj del sistema anfitrion.",
    "persistencia_world_data":
        "Almacena datos en el directorio del save, asociados al mundo. Se "
        "escribe en disco SOLO cuando el juego se guarda.",
    "persistencia_site_data":
        "Igual que WorldData pero asociado al sitio (fortaleza).",
    "persistencia_unsaved":
        "Segundos desde el ultimo guardado/carga. Mide 'suciedad', no tiempo de mundo.",
    "identidad_save_dir":
        "Nombre del directorio del save. Persistente en el juego, NO unico por "
        "estado (solo cambia al renombrar el save).",
    "identidad_world_data_name":
        "Nombre del mundo. Persistente, NO unico por estado.",
    "identidad_read_world_folder":
        "Carpeta del save cargada. Vacio si no hay juego cargado esta sesion.",
    "escritura_io_open": "Abre un fichero para escritura.",
    "escritura_file_write": "Escribe en el fichero de salida.",
    "escritura_memoria_df": "Asigna a memoria de DF (modifica el mundo).",
    "hook_state_change": "Registra un handler de onStateChange.",
}

# Clases que implican MUTAR el mundo (no solo leerlo).
CLASES_MUTANTES = ("escritura_memoria_df",)


def analizar_fichero(ruta: str) -> dict:
    """Analiza un .lua y devuelve su inventario de eventos. SOLO LECTURA."""
    with open(ruta, "r", encoding="utf-8", errors="replace") as fh:
        lineas = fh.read().splitlines()

    eventos: dict[str, list[dict]] = {}
    for i, linea in enumerate(lineas, start=1):
        codigo = linea
        # Se ignoran los comentarios: no son codigo ejecutable.
        if "--" in linea:
            codigo = linea.split("--", 1)[0]
        if not codigo.strip():
            continue
        for nombre, patron in PATRONES.items():
            for _m in patron.finditer(codigo):
                eventos.setdefault(nombre, []).append({
                    "linea": i,
                    "texto": codigo.strip(),
                })

    return {
        "fichero": os.path.basename(ruta),
        "lineas": len(lineas),
        "resumen": {k: len(v) for k, v in sorted(eventos.items())},
        "eventos": {k: v for k, v in sorted(eventos.items())},
        "escritura_memoria_df": bool(eventos.get("escritura_memoria_df")),
    }


OBJETIVOS = [
    "exportlegends.lua",
    "asyncexport.lua",
    "racefilter.lua",
    "open-legends.lua",
    "export-world-map.lua",
    "quicksave.lua",
    "load-save.lua",
    "once-per-save.lua",
    "timestream.lua",
]


def analizar_arbol(raiz: str, nombres: list[str]) -> dict:
    """Analiza los .lua indicados bajo `raiz`. No escribe nada."""
    hallazgos = []
    for nombre in nombres:
        for base, _dirs, ficheros in os.walk(raiz):
            if nombre in ficheros:
                hallazgos.append(analizar_fichero(os.path.join(base, nombre)))
                break
    hallazgos.sort(key=lambda h: h["fichero"])
    return {
        "raiz": raiz,
        "ficheros_analizados": [h["fichero"] for h in hallazgos],
        "faltantes": sorted(set(nombres) - {h["fichero"] for h in hallazgos}),
        "detalle": hallazgos,
    }


def construir_informe(raiz: str) -> dict:
    """Informe completo y determinista del inventario de exportadores."""
    analisis = analizar_arbol(raiz, OBJETIVOS)
    return {
        "herramienta": "inventario_exportador",
        "tipo": "HERRAMIENTA DE INVESTIGACION (no productiva)",
        "modo": "analisis estatico; NO requiere DF en ejecucion",
        "garantias": {
            "solo_lectura": True,
            "determinista": True,
            "modifica_originales": False,
            "es_producto": False,
        },
        "descripcion_clases": DESCRIPCION,
        "analisis": analisis,
    }


def main(argv: list[str] | None = None) -> int:
    aqui = os.path.dirname(os.path.abspath(__file__))
    raiz_defecto = os.path.abspath(
        os.path.join(aqui, "..", "..", "..", "..", "DFHack", "hack"))

    p = argparse.ArgumentParser(
        description="Inventario estatico de exportadores DFHack (P1.3, solo lectura)")
    p.add_argument("--raiz", default=raiz_defecto,
                   help="raiz de DFHack/hack (por defecto: ruta relativa)")
    p.add_argument("--json", default=None,
                   help="escribe el informe JSON en esta ruta de SALIDA")
    args = p.parse_args(argv)

    if not os.path.isdir(args.raiz):
        print(f"ERROR: no existe la raiz de DFHack: {args.raiz}")
        print("Indica --raiz <ruta a DFHack/hack>")
        return 2

    informe = construir_informe(args.raiz)

    print("=" * 74)
    print("P1.3 :: INVENTARIO ESTATICO DE EXPORTADORES DFHack")
    print("=" * 74)
    print(f"Raiz: {args.raiz}")
    print(f"Ficheros analizados: {len(informe['analisis']['ficheros_analizados'])}")
    if informe["analisis"]["faltantes"]:
        print(f"No encontrados: {', '.join(informe['analisis']['faltantes'])}")
    print()
    for det in informe["analisis"]["detalle"]:
        print(f"-- {det['fichero']} ({det['lineas']} lineas)")
        if not det["resumen"]:
            print("     (sin eventos de las clases buscadas)")
        for clase, n in det["resumen"].items():
            marca = "  <-- MUTA EL MUNDO" if clase in CLASES_MUTANTES else ""
            print(f"     {clase:30s} x{n}{marca}")
        print()

    if args.json:
        texto = json.dumps(informe, indent=2, sort_keys=True, ensure_ascii=False)
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
        print(f"informe escrito en: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

