# =============================================================================
# DF-Chronicles :: P1.3 -- HERRAMIENTA DE INVESTIGACION (NO PRODUCTIVA)
# -----------------------------------------------------------------------------
# BANCO DE EXPERIMENTOS E1-E12 (preparados, NO ejecutados)
#
# SITUACION REAL: Dwarf Fortress NO esta en ejecucion (P1.3-E003). Este modulo
# NO simula resultados. Prepara los experimentos, comprueba el pre requisito y
# declara PENDIENTE con honestidad.
#
# QUE HACE
#   - Comprueba si DF esta disponible (proceso / DFHack CLI).
#   - Para cada experimento E1..E12: objetivo, procedimiento manual exacto,
#     que se mide y el criterio de PASS/FAIL.
#   - NO inventa resultados. NO escribe en ningun save.
#
# USO
#   python experimentos_p1_3.py
#   python experimentos_p1_3.py --json x.json
#   python experimentos_p1_3.py --solo E7
# =============================================================================
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

# --------------------------------------------------------------------------
# Los 12 experimentos minimos exigidos por la seccion 13. "procedimiento" es la
# secuencia MANUAL que ejecuta una persona con el juego abierto: este script no
# puede automatizar el juego.
# --------------------------------------------------------------------------
EXPERIMENTOS: list[dict] = [
    {
        "id": "E1",
        "nombre": "mismo mundo, misma extraccion",
        "objetivo": "¿Dos extracciones del mismo estado dan el mismo dataset_id?",
        "procedimiento": [
            "1. Cargar el save y dejar el mundo en pausa.",
            "2. exportlegends -> XML A.",
            "3. Sin tocar el mundo, exportlegends otra vez -> XML B.",
            "4. Comparar sha256 de A y B, y el dataset_id de cada una.",
        ],
        "medir": ["sha256 del XML", "dataset_id", "<name> del mundo",
                  "cur_year / mes / dia en cada extraccion"],
        "pase": "A y B tienen el mismo dataset_id",
        "falla_si": "Los dataset_id difieren sin que el mundo haya cambiado",
    },
    {
        "id": "E2",
        "nombre": "avanzar un tick",
        "objetivo": "¿Un solo tick cambia el dataset_id?",
        "procedimiento": [
            "1. Exportar (XML A).",
            "2. Despausar EXACTAMENTE un tick (timestream o tecla de 1 tick).",
            "3. Volver a pausar. Exportar (XML B).",
            "4. Comparar A y B.",
        ],
        "medir": ["sha256", "dataset_id", "ReadCurrentTick() antes y despues"],
        "pase": "Se registra si dataset_id cambia o no",
        "falla_si": "El tick avanza pero el contenido no cambia (falso positivo de "
                    "freshness) O el contenido cambia con dataset_id igual",
    },
    {
        "id": "E3",
        "nombre": "avanzar N ticks",
        "objetivo": "Determinar la granularidad minima detectable de cambio.",
        "procedimiento": [
            "1. Exportar (A). Avanzar 100 ticks. Exportar (B).",
            "2. Avanzar 10 000 ticks. Exportar (C).",
            "3. Comparar A, B, C.",
        ],
        "medir": ["sha256 de los tres", "dataset_id de los tres",
                  "año y tick en cada punto"],
        "pase": "Se construye la curva 'ticks avanzados -> cambia el dataset_id?'",
        "falla_si": "Un cambio grande del mundo no altera el dataset_id",
    },
    {
        "id": "E4",
        "nombre": "save/load sin avanzar",
        "objetivo": "¿Guardar y recargar el mismo estado cambia su identidad?",
        "procedimiento": [
            "1. Exportar (A).",
            "2. Guardar SIN avanzar. Cerrar. Reabrir. Cargar.",
            "3. Exportar (B). Comparar A y B.",
        ],
        "medir": ["dataset_id", "sha256(world.sav) antes y despues",
                  "hash de los XML"],
        "pase": "Se observa si guardar ES PER SE un cambio de estado",
        "falla_si": "El hash del save cambia aunque el estado sea identico "
                    "-> el hash no puede ser identidad de estado",
    },
    {
        "id": "E5",
        "nombre": "save/load despues de avanzar",
        "objetivo": "¿El estado persiste correctamente tras avanzar+guardar?",
        "procedimiento": [
            "1. Avanzar N ticks. Exportar (A).",
            "2. Guardar. Cerrar. Reabrir. Cargar. Exportar (B).",
            "3. Comparar A y B.",
        ],
        "medir": ["dataset_id de A y B", "año/tick tras la recarga"],
        "pase": "A y B describen el mismo estado tras el round-trip",
        "falla_si": "A!=B sin causa aparente (indicio de estado no persistido)",
    },
    {
        "id": "E6",
        "nombre": "cargar un save antiguo",
        "objetivo": "La pregunta clave de la seccion 5: ¿se distinguen A, B y A?",
        "procedimiento": [
            "1. Estado A. Guardar. Exportar A.",
            "2. Avanzar hasta B. Guardar. Exportar B.",
            "3. Cargar de nuevo el guardado de A. Exportar -> D.",
            "4. Comparar A, B y D.",
        ],
        "medir": ["dataset_id de A, B, D", "año/tick de A, B, D",
                  "sha256(world.sav) tras cada guardado"],
        "pase": "Si A y D son identicos y B distinto, el sistema NO puede saber "
                "que existio una B (branching invisible)",
        "falla_si": "A y D son indistinguibles por cualquier senal disponible "
                    "-> confirma H-012",
    },
    {
        "id": "E7",
        "nombre": "duplicar save",
        "objetivo": "¿Que identidad hereda una copia del save?",
        "nota": "PARCIALMENTE RESUELTO por analisis de ficheros (P1.3-E007): una "
                "copia byte a byte produce el mismo sha256. Falta la parte que "
                "exige el juego.",
        "procedimiento": [
            "1. Copiar la carpeta del save a 'region1_copia'.",
            "2. Cargar AMBAS por separado en sesiones distintas.",
            "3. En cada una: ReadWorldFolder(), exportlegends, sha256 del save.",
            "4. Comparar.",
        ],
        "medir": ["ReadWorldFolder()", "sha256(world.sav)", "dataset_id",
                  "contenido del fichero persistente de dfhack.persistent"],
        "pase": "Se determina si la copia hereda o no la identidad",
        "falla_si": "Ambas copias producen identidades indistinguibles",
    },
    {
        "id": "E8",
        "nombre": "crear rama",
        "objetivo": "¿Existe alguna nocion de lineage en DF o DFHack?",
        "procedimiento": [
            "1. Estado A. Guardar copia del save como 'rama_base'.",
            "2. Avanzar hasta B en el save original.",
            "3. Cargar 'rama_base' otra vez y seguir jugando -> D.",
            "4. Buscar en DF y en DFHack alguna marca de que existio B.",
        ],
        "medir": ["dataset_id de B y D", "world.dat / world.sav",
                  "fichero persistente de dfhack.persistent"],
        "pase": "Se determina si DF registra historia o si es imposible",
        "falla_si": "B y D son indistinguibles -> LINEAGE no existe en DF",
    },
    {
        "id": "E9",
        "nombre": "volver a una rama anterior",
        "objetivo": "¿Se puede detectar que se ha retrocedido?",
        "procedimiento": [
            "1. Tras E8, exportar en B, en D, y de nuevo en B.",
            "2. Comparar las tres exportaciones.",
        ],
        "medir": ["dataset_id de las tres", "año/tick de las tres"],
        "pase": "Se mide el grado de reversibilidad de la identidad",
        "falla_si": "Los valores de B se repiten indistinguibles -> no hay "
                    "contador monotono que detecte el retroceso",
    },
    {
        "id": "E10",
        "nombre": "exportacion durante simulacion",
        "objetivo": "¿El fichero mezcla estados? (H-015)",
        "procedimiento": [
            "1. En modo fortaleza, con la simulacion CORRIENDO a maxima velocidad.",
            "2. exportlegends.",
            "3. Repetir 5 veces. Comparar entre si y contra E11.",
        ],
        "medir": ["sha256 de las 5 exportaciones", "año/tick al inicio y fin",
                  "diferencias en los eventos del final del fichero"],
        "pase": "Si los ficheros difieren entre si, la exportacion MEZCLA estados",
        "falla_si": "Los 5 ficheros son identicos con el mundo corriendo",
    },
    {
        "id": "E11",
        "nombre": "exportacion pausada",
        "objetivo": "Contraste de control para E10.",
        "procedimiento": [
            "1. Congelar el mundo (pausa) y exportar 5 veces.",
            "2. Comparar con los resultados de E10.",
        ],
        "medir": ["sha256 de las 5 exportaciones pausadas"],
        "pase": "Las 5 deben ser identicas",
        "falla_si": "Difieren entre si con el mundo quieto",
    },
    {
        "id": "E12",
        "nombre": "exportacion con el core bloqueado",
        "objetivo": "¿Se puede forzar un snapshot con with_suspend?",
        "procedimiento": [
            "1. Script DFHack de prueba que use dfhack.with_suspend para leer "
            "los mismos campos que lee exportlegends.",
            "2. Comparar su salida con la de exportlegends en E10.",
        ],
        "medir": ["consistencia de las lecturas dentro del lock",
                  "¿el mundo avanza durante el lock? (año/tick antes y despues)"],
        "pase": "Se determina si with_suspend detiene la SIMULACION",
        "falla_si": "El año/tick avanza pese al lock -> el lock solo serializa "
                    "lecturas, no congela la simulacion (confirma H-009)",
    },
]


def df_esta_corriendo() -> dict:
    """Comprueba si DF esta en ejecucion. No lanza nada."""
    try:
        salida = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq DwarfFortress.exe"],
            capture_output=True, text=True, timeout=15)
        hay = "DwarfFortress.exe" in (salida.stdout or "")
    except Exception as exc:                       # noqa: BLE001
        return {"disponible": False, "metodo": "tasklist",
                "error": f"{type(exc).__name__}: {exc}"}
    return {
        "disponible": bool(hay),
        "metodo": "tasklist /FI IMAGENAME eq DwarfFortress.exe",
        "salida": (salida.stdout or "").strip()[:400],
    }


def dfhack_run_disponible() -> dict:
    """Comprueba si existe dfhack-run.exe. No lo ejecuta sobre un juego vivo."""
    raiz = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "..", "..", "DFHack", "hack"))
    ruta = os.path.join(raiz, "dfhack-run.exe")
    return {"ruta": ruta, "existe": os.path.isfile(ruta)}


def estado_banco(solo: str | None = None) -> dict:
    df = df_esta_corriendo()
    dfhack = dfhack_run_disponible()
    ejecucion = bool(df["disponible"] and dfhack["existe"])

    experiments = [e for e in EXPERIMENTOS
                   if solo is None or e["id"].upper() == solo.upper()]
    if solo is not None and not experiments:
        return {"error": f"Experimento desconocido: {solo}"}

    for e in experiments:
        e["estado"] = ("EJECUTABLE" if ejecucion
                       else "PENDIENTE - REQUIERE DF EN EJECUCION")
        # No se inventa resultado. Nunca.
        e["resultado"] = None

    return {
        "herramienta": "experimentos_p1_3",
        "tipo": "HERRAMIENTA DE INVESTIGACION (no productiva)",
        "garantias": {
            "no_inventa_resultados": True,
            "no_escribe_en_saves": True,
            "es_producto": False,
        },
        "entorno": {"df_corriendo": df, "dfhack_run": dfhack},
        "ejecutable": ejecucion,
        "experimentos": experiments,
        "veredicto": (
            "Todos los experimentos quedan PENDIENTES. No hay resultados que "
            "reportar. Cualquier afirmacion sobre su resultado seria inventada."
        ) if not ejecucion else (
            "DF detectado. Ejecutar los procedimientos manualmente: este script "
            "NO automatiza el juego, solo documenta y registra."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Banco de experimentos P1.3 (no simula resultados)")
    p.add_argument("--solo", default=None, help="muestra solo un experimento (E1..E12)")
    p.add_argument("--json", default=None, help="salida JSON")
    args = p.parse_args(argv)

    banco = estado_banco(args.solo)
    if "error" in banco:
        print("ERROR:", banco["error"])
        return 2

    print("=" * 74)
    print("P1.3 :: BANCO DE EXPERIMENTOS E1-E12")
    print("=" * 74)
    print(f"DF en ejecucion : {banco['entorno']['df_corriendo']['disponible']}")
    print(f"dfhack-run.exe  : {banco['entorno']['dfhack_run']['existe']}")
    print(f"Ejecutable      : {banco['ejecutable']}")
    print()
    for e in banco["experimentos"]:
        print(f"-- {e['id']}: {e['nombre']}   [{e['estado']}]")
        print(f"   objetivo : {e['objetivo']}")
        if e.get("nota"):
            print(f"   NOTA     : {e['nota']}")
        for paso in e["procedimiento"]:
            print(f"     {paso}")
        print(f"   medir    : {', '.join(e['medir'])}")
        print(f"   PASE     : {e['pase']}")
        print(f"   FALLA SI : {e['falla_si']}")
        print()

    print(f"VEREDICTO: {banco['veredicto']}")

    if args.json:
        texto = json.dumps(banco, indent=2, sort_keys=True, ensure_ascii=False)
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
        print(f"informe escrito en: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
