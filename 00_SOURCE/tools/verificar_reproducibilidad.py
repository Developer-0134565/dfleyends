#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Verificacion de reproducibilidad
==================================================

Reconstruye el pipeline COMPLETO desde los dos XML originales, en un
directorio temporal, y comprueba que el resultado coincide con el actual.

NO modifica el dataset funcional: trabaja sobre una copia temporal.

Uso:  python verificar_reproducibilidad.py
"""
import os
import sys
import json
import shutil
import hashlib
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402

BASE = rutas.PROJECT_ROOT
SRC = rutas.DATA_ROOT
TOOLS = rutas.TOOLS_ROOT

# Lo que se reconstruye y con qué fingerprint se compara.
OBJETIVOS = [
    "historical_figures", "entities", "sites", "historical_events",
    "artifacts", "historical_event_relationships",
    "historical_event_relationship_supplements",
    "historical_event_collections", "historical_eras",
]


def sha_de(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def fingerprint(processed_dir):
    """Huella de los JSONL: nombre de sección + nº de líneas + hash."""
    out = {}
    merged = os.path.join(processed_dir, "merged")
    for sec in OBJETIVOS:
        p = os.path.join(merged, f"{sec}.jsonl")
        if not os.path.exists(p):
            out[sec] = {"lineas": 0, "sha256": None}
            continue
        with open(p, "rb") as f:
            h = hashlib.sha256()
            n = 0
            for line in f:
                h.update(line)
                n += 1
        out[sec] = {"lineas": n, "sha256": h.hexdigest()}
    return out


def rutas_seguras(proc_real, orig_real, tmp):
    """ABORTA si el temporal o su salida pueden caer sobre el dataset real.

    Salvaguarda exigida por la auditoría Extra (parte 10): la
    reconstrucción debe ser SEGURA POR CONSTRUCCION, no por suerte.

    Regla: el temporal NUNCA puede estar dentro de las rutas protegidas, y
    las rutas de salida NUNCA pueden coincidir con ellas.
    """
    objetivo = os.path.abspath(tmp)
    protegidas = {os.path.abspath(proc_real), os.path.abspath(orig_real)}

    # 1. el temporal no puede estar DENTRO de una ruta protegida
    for p in protegidas:
        if objetivo == p or objetivo.startswith(p + os.sep):
            raise RuntimeError(
                f"ABORTA: el temporal {objetivo} esta dentro de {p}")

    # 2. el temporal no puede ser un ancestro de una ruta protegida
    for p in protegidas:
        if p.startswith(objetivo + os.sep):
            raise RuntimeError(
                f"ABORTA: el temporal {objetivo} contiene la ruta protegida {p}")

    # 3. las salidas dentro del temporal deben existir alli de verdad
    return True


def comprobar_salvaguardas():
    """Intenta provocar el escenario peligroso: debe ABORTAR."""
    print("\n6) Prueba de las salvaguardas (debe ABORTAR)")
    proc_real = os.path.abspath(os.path.join(SRC, "processed"))
    orig_real = os.path.abspath(os.path.join(SRC, "original_data"))
    casos = [
        ("temporal DENTRO de processed/",
         os.path.join(proc_real, "_repro_tmp")),
        ("temporal DENTRO de original_data/",
         os.path.join(orig_real, "_repro_tmp")),
        ("salida IGUAL al dataset real", proc_real),
        ("salida IGUAL a original_data", orig_real),
    ]
    ok = 0
    for nombre, destino in casos:
        try:
            rutas_seguras(proc_real, orig_real, destino)
            print(f"   [FALLO] {nombre}: NO aborted (deberia abortar)")
        except RuntimeError:
            print(f"   [OK   ] {nombre}: abortado correctamente")
            ok += 1
    print(f"   {ok}/{len(casos)} escenarios peligrosos bloqueados")
    return ok == len(casos)


def main():
    print("=" * 72)
    print("VERIFICACION DE REPRODUCIBILIDAD (segura por construccion)")
    print("=" * 72)

    actual = fingerprint(os.path.join(SRC, "processed"))
    print("\n1) Fingerprint del dataset ACTUAL")
    for k, v in actual.items():
        print(f"   {k:46s} {v['lineas']:>7,} lineas  "
              f"{(v['sha256'] or '')[:16]}")

    tmp = tempfile.mkdtemp(prefix="dfch_repro_")
    print(f"\n2) Directorio temporal: {tmp}")
    try:
        # SALVAGUARDAS antes de copiar o ejecutar nada.
        rutas_seguras(os.path.join(SRC, "processed"),
                      os.path.join(SRC, "original_data"), tmp)
        print("   salvaguardas: OK (el temporal esta aislado)")

        odir = os.path.join(tmp, "original_data")
        os.makedirs(odir, exist_ok=True)
        for n in ("legends.xml", "legends_plus.xml"):
            shutil.copy2(os.path.join(SRC, "original_data", n),
                         os.path.join(odir, n))
        tdir = os.path.join(tmp, "tools")
        shutil.copytree(TOOLS, tdir,
                        ignore=shutil.ignore_patterns("__pycache__"))
        print(f"   copiados 2 XML + {len(os.listdir(tdir))} herramientas")

        runner = os.path.join(tdir, "_runner.py")
        with open(runner, "w", encoding="utf-8") as f:
            f.write(
                "import os, sys\n"
                f"sys.path.insert(0, {tdir!r})\n"
                "import integrar_legends as IL\n"
                f"IL.SRC = {tmp!r}\n"
                f"IL.ORIG_DIR = {odir!r}\n"
                f"IL.PROC = {os.path.join(tmp, 'processed')!r}\n"
                f"IL.PROC_LEGENDS = {os.path.join(tmp, 'processed', 'from_legends_xml')!r}\n"
                f"IL.PROC_PLUS = {os.path.join(tmp, 'processed', 'from_legends_plus')!r}\n"
                f"IL.PROC_MERGED = {os.path.join(tmp, 'processed', 'merged')!r}\n"
                f"IL.ORIG_LEGENDS = {os.path.join(odir, 'legends.xml')!r}\n"
                f"IL.ORIG_PLUS = {os.path.join(odir, 'legends_plus.xml')!r}\n"
                "m = IL.integrar()\n"
                "print('OK', m['merge']['divergencias_totales'])\n")

        print("\n3) Reejecutando la integracion sobre el temporal")
        r = subprocess.run([sys.executable, "_runner.py"], cwd=tdir,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            print(f"   ERROR: {r.stderr[-600:]}")
            return 1
        print(f"   integracion terminada: {(r.stdout or '').strip().splitlines()[-1]}")

        nueva = fingerprint(os.path.join(tmp, "processed"))
        print("\n4) Comparacion dataset actual vs reconstruido")
        iguales = 0
        for k in OBJETIVOS:
            a, b = actual[k], nueva[k]
            okk = a["lineas"] == b["lineas"] and a["sha256"] == b["sha256"]
            iguales += okk
            print(f"   [{'OK ' if okk else 'DIF'}] {k:44s} "
                  f"{a['lineas']:>7,} vs {b['lineas']:>7,}")
        print(f"\n   {iguales}/{len(OBJETIVOS)} secciones byte-identicas")

        print("\n5) Los XML originales siguen intactos")
        intactos = 0
        for n, exp in (("legends.xml",
                        "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f"),
                       ("legends_plus.xml",
                        "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d")):
            h = sha_de(os.path.join(SRC, "original_data", n))
            intactos += h == exp
            print(f"   [{'OK ' if h == exp else 'CAMBIO'}] {n:20s} {h[:20]}")

        if not comprobar_salvaguardas():
            print("\nRESULTADO: LAS SALVAGUARDAS NO FUNCIONAN")
            return 1

        if iguales == len(OBJETIVOS) and intactos == 2:
            print("\nRESULTADO: REPRODUCIBLE desde los XML originales")
            return 0
        print("\nRESULTADO: HAY DIFERENCIAS")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n(temporal eliminado)")


if __name__ == "__main__":
    sys.exit(main())