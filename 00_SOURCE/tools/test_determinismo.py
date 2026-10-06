#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Prueba de determinismo
======================================

Verifica que las consultas del núcleo producen EXACTAMENTE el mismo resultado
cuando se repiten, incluso en procesos distintos con distinta semilla de hash.

Determinismo comprobado: búsquedas, cronologías, relaciones, conflictos,
exportaciones (JSON y Markdown), consultas geográficas y fichas.

Qué NO debe afectar al resultado:
  * orden de iteración de `dict` / `set`
  * PYTHONHASHSEED
  * hora actual
  * orden de lectura del filesystem
  * ejecuciones anteriores

Ejecutar:  python test_determinismo.py
Devuelve 0 si todo es determinista.
"""
import os
import sys
import json
import hashlib
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nucleo import Archivo  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

CONSULTAS = [
    ("busqueda_figura", lambda a: a.buscar_figura("galka shafttop")),
    ("busqueda_generica_the", lambda a: a.buscar("the")),
    ("busqueda_entidad", lambda a: a.buscar_entidad("curled diamond")),
    ("busqueda_sitio", lambda a: a.buscar_sitio("halesteel")),
    ("busqueda_artefacto", lambda a: a.buscar_artefacto("wave")),
    ("busqueda_vacia_resultados", lambda a: a.buscar_figura("zzzqqqxxxnoexiste")),
    ("busqueda_ambigua", lambda a: a.buscar_figura("the")),
    ("ficha_figura_712", lambda a: a.ficha_figura("712")),
    ("ficha_sitio_87", lambda a: a.ficha_sitio("87")),
    ("ficha_entidad_282", lambda a: a.ficha_entidad("282")),
    ("ficha_artefacto", lambda a: a.ficha_artefacto("50")),
    ("cronologia_figura_712", lambda a: a.cronologia_figura("712")),
    ("cronologia_entidad_282", lambda a: a.cronologia_entidad("282")),
    ("cronologia_sitio_87", lambda a: a.cronologia_sitio("87")),
    ("eventos_anio_1", lambda a: a.eventos_del_anio(1)),
    ("eventos_entre_20_30", lambda a: a.eventos_entre_anios(20, 30)),
    ("relaciones_1156", lambda a: a.relaciones_de_figura("1156")),
    ("relaciones_war_buddy", lambda a: a.relaciones_de_figura("1156", "war_buddy")),
    ("tipos_relacion", lambda a: a.tipos_relacion_disponibles()),
    ("conflictos", lambda a: a.conflictos()),
    ("muertes_conflicto", lambda a: a.muertes_por_conflicto()),
    ("geografia", lambda a: a.geografia()),
    ("construccion_coordenada", lambda a: a.construir_en_coordenada(112, 20)),
    ("miembros_entidad_282", lambda a: a.miembros_entidad("282")),
    ("participantes_evento", lambda a: a.participantes_evento("421")),
    ("export_json_figura_712", lambda a: a.exportar_historia_figura("712", "json")),
    ("export_md_figura_712", lambda a: a.exportar_historia_figura("712", "markdown")),
    ("export_json_sitio_87", lambda a: a.exportar_json(a.ficha_sitio("87"), "s87")),
    ("export_md_sitio_87", lambda a: a.exportar_markdown(a.ficha_sitio("87"), "s87")),
]


def huella(obj):
    """Huella estable de cualquier resultado JSON-serializable."""
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True,
                   default=str).encode("utf-8")).hexdigest()


def ejecutar_en_proceso(semilla):
    """Ejecuta el cálculo en un proceso NUEVO con PYTHONHASHSEED concreto."""
    codigo = (
        "import sys, json;"
        f"sys.path.insert(0, {HERE!r});"
        "import test_determinismo as T;"
        "from nucleo import Archivo;"
        "a=Archivo();"
        "print(json.dumps({n: T.huella(fn(a)) for n, fn in T.CONSULTAS}))"
    )
    env = dict(os.environ, PYTHONHASHSEED=semilla)
    p = subprocess.run([sys.executable, "-c", codigo], cwd=HERE, env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"subproceso fallo: {p.stderr[-800:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])
def main():
    print("=" * 70)
    print("DETERMINISMO DEL NUCLEO")
    print("=" * 70)

    print("\n1) Repeticiones en el MISMO proceso")
    a = Archivo()
    fallo = 0
    base = {n: huella(fn(a)) for n, fn in CONSULTAS}
    for rep in range(3):
        for n, fn in CONSULTAS:
            if huella(fn(a)) != base[n]:
                print(f"   FALLO en {n} (repeticion {rep})")
                fallo += 1
    print(f"   {len(CONSULTAS)} consultas x 3 repeticiones: "
          f"{'TODAS IDENTICAS' if fallo == 0 else f'{fallo} DIFERENCIAS'}")

    print("\n2) Procesos NUEVOS con PYTHONHASHSEED distinto")
    semillas = ["0", "1", "12345", "random"]
    resultados = []
    for s in semillas:
        resultados.append((s, ejecutar_en_proceso(s)))
        print(f"   PYTHONHASHSEED={s:7s} -> calculado")

    fallos_proceso = 0
    for n, _ in CONSULTAS:
        if len({r[n] for _, r in resultados}) != 1:
            print(f"   FALLO: '{n}' difiere entre procesos")
            fallos_proceso += 1
    print(f"   {len(CONSULTAS)} consultas x {len(semillas)} procesos: "
          f"{'TODAS IDENTICAS' if fallos_proceso == 0 else f'{fallos_proceso} DIFERENCIAS'}")

    print("\n3) Puntos de riesgo conocidos")
    riesgos = []

    r = a.buscar("the")
    ids = r["resultados"].get("historical_figures", [])
    no_num = [x for x in ids if not x.isdigit()]
    riesgos.append(("buscar: sin colisiones en la clave de orden",
                    len(no_num) == 0,
                    f"{len(no_num)} ids no numericos (los df_id de DF son numericos)"))

    c = a.conflictos(limite_eventos=100)
    completo = a.conflictos()
    riesgos.append(("conflictos(limite=N) declara el total real",
                    bool(c.get("truncado")) or "total_real" in c,
                    f"con limite devuelve {len(c['eventos'])}; "
                    f"'eventos_de_enfrentamiento' dice {c['eventos_de_enfrentamiento']}; "
                    f"el real es {completo['eventos_de_enfrentamiento']}"))

    b = a.buscar_figura("the")
    riesgos.append(("buscar_* declara cuantos hay en total",
                    "total_encontrados" in b,
                    f"devuelve {len(b['ids'])} ids; "
                    f"{'informa' if 'total_encontrados' in b else 'NO informa del total'}"))

    md = a.exportar_markdown(a.ficha_sitio("87"), "s87")
    riesgos.append(("exportar_markdown avisa de truncamiento",
                    "trunc" in md.lower(),
                    f"el sitio 87 tiene 1546 eventos; "
                    f"{'avisa' if 'trunc' in md.lower() else 'NO avisa'}"))

    for nombre, ok, detalle in riesgos:
        print(f"   [{'OK ' if ok else 'GAP'}] {nombre}")
        print(f"        {detalle}")

    total = fallo + fallos_proceso
    print("\n" + "=" * 70)
    if total == 0:
        print(f"RESULTADO: DETERMINISTA ({len(CONSULTAS)} consultas, "
              f"{len(semillas)} procesos, 3 repeticiones)")
        return 0
    print(f"RESULTADO: {total} DIFERENCIAS DETECTADAS")
    return 1


if __name__ == "__main__":
    sys.exit(main())
