#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1_FINAL :: mutation testing del nucleo PRE-IA (harness).

Demuestra que las pruebas de API dependen REALMENTE de servicio_consulta.py y
del adaptador, y no de una coincidencia de valores.

SEGURIDAD (leccion de P1.3, donde un proceso muerto dejo produccion mutada):
  1. Lectura y escritura en BINARIO: nunca se toca CRLF ni se anade BOM.
  2. La garantia NO es el `finally`: es el HASH.
  3. Antes de mutar se anota el hash esperado en `_hash_esperado.json`.
  4. Las mutaciones son SECUENCIALES y en PRIMER PLANO. Nunca en segundo
     plano: un proceso muerto es el fallo que hay que evitar.

Uso:  python P1_FINAL/mutaciones.py [salida.json]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import time

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.abspath(os.path.join(_AQUI, ".."))
SVC = os.path.join(_RAIZ, "dfchron", "servicio_consulta.py")
ADA = os.path.join(_RAIZ, "dfchron", "adaptador_consulta.py")
# `servicio.py` es donde NACEN los envelopes FOUND (`envolver_ficha`). Es el
# punto correcto para la mutacion de `certainty`: el bloque de `_resultado()`
# solo se ejecuta en la ruta de error, donde la certeza ya es UNKNOWN.
SER = os.path.join(_RAIZ, "dfchron", "servicio.py")
ESTADO = os.path.join(_AQUI, "_hash_esperado.json")
API, INT = "probar_api.py", "probar_integracion_consulta.py"
# Suite nueva: fija el contrato de `certainty` y el aislamiento del adaptador.
CERT = "probar_contrato_certainty.py"
DEL = "    return _responder(qc.obtener_entidad(\"figura\", df_id))"
FABRICA = ("    import dfchron.servicio as _s\n"
           "    return _responder({'estado': 'FOUND', 'ok': True,\n"
           "                       'data': _s.figura(str(df_id)),\n"
           "                       'certainty': 'FACT', 'dataset_id': 'v1-x'})")

# (id, capa, fichero, buscar, reemplazar, suite, que rompe)
MUTACIONES = [
    ("M01", "service/certainty_ficha", SER,
     '    cert = datos.get("certainty", UNKNOWN) if isinstance(datos, dict) else UNKNOWN',
     '    cert = UNKNOWN   # MUTACION M01: la certeza de la ficha se degrada',
     CERT,
     "certainty de todo envelope FOUND pasa a UNKNOWN"),
    ("M02", "service/certainty", SVC,
     '"certainty": "FACT" if estado == FOUND else "UNKNOWN",',
     '"certainty": "FACT",', CERT, "certainty siempre FACT"),
    ("M03", "service/not_proven", SVC,
     '            NOT_VERIFIED, tipo=tipo, df_id=df_id,',
     '            FOUND, tipo=tipo, df_id=df_id,', INT,
     "atributo no declarado pasa a FOUND"),
    ("M04", "service/verificador", SVC,
     "    out = _resultado(FOUND if verificado else NOT_VERIFIED,",
     "    out = _resultado(FOUND,", INT, "verificacion fallida pasa a FOUND"),
    ("M05", "evidence", SVC,
     '    base["evidence"] = _evidencia(tipo, df_id, campos) if tipo else None',
     '    base["evidence"] = None', INT, "la evidencia se elimina"),
    ("M06", "identity", SVC, '    base["dataset_id"] = ic.DATASET_ID',
     '    base["dataset_id"] = "v1-inventado"', INT, "dataset_id miente"),
    # M07 esta CLASIFICADO como NOT_APPLICABLE: `servicio_consulta._resultado()`
    # construye un dict NUEVO en cada llamada, asi que no existe aliasing
    # observable que distinga copia profunda de copia superficial. La mutacion se
    # conserva para reevaluarla si algun dia el servicio cachea envelopes.
    ("M07", "api/serializacion", ADA, "    out = copy.deepcopy(dict(resultado))",
     "    out = dict(resultado)", CERT,
     "deja de ser copia profunda [NOT_APPLICABLE]", True),
    ("M08", "api/http", ADA, "    qc.NOT_VERIFIED: 200,",
     "    qc.NOT_VERIFIED: 404,", INT, "NOT_VERIFIED degrada a 404"),
    ("M09", "api/delegacion", ADA, DEL, FABRICA, API,
     "la ficha deja de pasar por servicio_consulta"),
    ("M10", "api/envelope", ADA, '    out["http_status"] = _http_de(out)',
     "    pass", INT, "no calcula el codigo HTTP"),
]


def _b(r):
    with io.open(r, "rb") as fh:
        return fh.read()


def _w(r, d):
    with io.open(r, "wb") as fh:
        fh.write(d)


def _sha(d):
    return hashlib.sha256(d).hexdigest()
def _mutar(mid, capa, ruta, buscar, poner, suite, nota, na=False):
    orig = _b(ruta)
    h0 = _sha(orig)
    txt = orig.decode("utf-8")
    if buscar not in txt:
        return {"id": mid, "capa": capa, "estado": "NOT_APPLICABLE",
                "mutacion": nota,
                "motivo": "el patron ya no existe: no probaria nada"}
    _w(ruta, txt.replace(buscar, poner, 1).encode("utf-8"))
    try:
        t0 = time.time()
        p = subprocess.run(
            [sys.executable, os.path.join(_RAIZ, "dfchron", "pruebas", suite)],
            cwd=_RAIZ, capture_output=True, text=True, timeout=1200)
        dur = round(time.time() - t0, 1)
        det = p.returncode != 0
        cola = ""
        for l in ((p.stdout or "") + (p.stderr or "")).splitlines():
            if l.startswith(("FAILED", "FAIL:", "ERROR:")):
                cola = l[:110]
                break
    finally:
        _w(ruta, orig)
    h1 = _sha(_b(ruta))
    if h1 != h0:
        print("!!! %s NO RESTAURADO" % mid)
    if na:
        # Se ejecuta para CONSTATAR, pero no se cuenta como fallo de cobertura:
        # la garantia que pretendia probar no es observable bajo el contrato.
        estado = "NOT_APPLICABLE"
    else:
        estado = "KILLED" if det else "SURVIVED"
    return {"id": mid, "capa": capa, "mutacion": nota, "suite": suite,
            "estado": estado, "deteccion": det, "clasificado_na": na,
            "restaurado": h1 == h0, "hash_antes": h0, "hash_despues": h1,
            "segundos": dur, "cola": cola}


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        _AQUI, "MUTATION_TEST_RESULTS.json")
    with io.open(ESTADO, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"servicio_consulta.py": _sha(_b(SVC)),
                   "adaptador_consulta.py": _sha(_b(ADA))}, fh, indent=1)
        fh.write("\n")
    print("Ejecutando %d mutaciones (secuencial, primer plano)\n" % len(MUTACIONES))
    res = []
    for m in MUTACIONES:
        r = _mutar(*m)
        res.append(r)
        print("[%s] %-20s %-14s %5.1fs restaura=%-5s %s"
              % (r["id"], r["capa"], r["estado"], r.get("segundos", 0),
                 r.get("restaurado"), r.get("cola", "")))
        sys.stdout.flush()
    k = [r for r in res if r["estado"] == "KILLED"]
    s = [r for r in res if r["estado"] == "SURVIVED"]
    n = [r for r in res if r["estado"] == "NOT_APPLICABLE"]
    print("\nKILLED=%d SURVIVED=%d NOT_APPLICABLE=%d restaurados_ok=%s"
          % (len(k), len(s), len(n), all(r.get("restaurado") for r in res)))
    for r in s:
        print("   SUPERVIVIENTE %s %s :: %s" % (r["id"], r["capa"], r["mutacion"]))
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"resultados": res}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("resultados -> %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())