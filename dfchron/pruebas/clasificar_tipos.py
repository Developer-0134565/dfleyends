#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles v1 :: CLASIFICACION DE TIPOS SEGUN EVIDENCIA REAL.
============================================================

Para cada uno de los 90 tipos de `historical_events`: ¿se puede convertir a un
evento Chronicle, y con que GRADO DE DEMOSTRACION?

    SUPPORTED    la semantica esta DEMOSTRADA por evidencia del propio registro
    PARTIAL      se convierte en parte; falta tiempo, sujeto o identidad
    NOT_PROVEN   tiene tiempo y sujeto, pero su SIGNIFICADO no esta demostrado
    UNSUPPORTED  no se puede construir un evento utilizable

DETERMINACION, NO JUICIO
------------------------
Este script NO decide la semantica: la DECLARA desde un unico sitio, el
registro `MAPA_TIPOS` de `chronicles_datos.py`, que solo contiene lo que se ha
verificado leyendo el dataset. Cualquier tipo fuera de ese mapa se clasifica
por lo que SUS CAMPOS permiten, no por lo que su nombre sugiere.

Un nombre como `hf died` NO se acepta como evidencia de que hubo una muerte:
se acepta porque sus CAMPOS lo demuestran. Si mañana `hf died` perdiera el
campo `hfid`, este script lo degrada a PARTIAL automaticamente.

Uso:  python dfchron/pruebas/clasificar_tipos.py [--json SALIDA] [--muestra N]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dfchron import chronicles_datos as cd   # noqa: E402

RUTA = cd.ruta_de("historical_events")

#: Grados de clasificacion. Se nombran aqui, en UN sitio, y no se escriben a
#: mano en ningun otro fichero.
SUPPORTED = "SUPPORTED"
PARTIAL = "PARTIAL"
NOT_PROVEN = "NOT_PROVEN"
UNSUPPORTED = "UNSUPPORTED"
GRADOS = (SUPPORTED, PARTIAL, NOT_PROVEN, UNSUPPORTED)

#: Los sujetos y temporales NO se escriben aqui: son los del vocabulario
#: congelado (`chronicles_vocab`), el mismo que usa el motor. Una lista
#: propia seria una segunda fuente de verdad que se quedaria vieja.
TEMPORALES = cd.TEMPORALES
SUJETOS = cd.SUJETOS

#: Valores que el dataset usa para "ausente". Un `-1` NO es un identificador:
#: es la manera que tiene DF de decir "no lo se".
AUSENTES = ("", "-1", "-1.0", "None", "null")


def _valor(campos, clave, defecto=None):
    """Igual que `cd.valor_de`: respeta la forma REAL del campo."""
    return cd.valor_de(campos, clave, defecto)


def _tiene_valor(campos, clave):
    return str(_valor(campos, clave, "")).strip() not in AUSENTES


def barrer():
    """Barrido TOTAL. Cada linea se lee una vez. Nada se descarta en silencio."""
    total = corruptas = 0
    por_tipo = collections.Counter()
    con_tiempo = collections.Counter()
    con_anio = collections.Counter()
    con_sujeto = collections.Counter()
    con_estructura = collections.Counter()
    campo_sujeto = collections.defaultdict(collections.Counter)
    cert = collections.defaultdict(collections.Counter)
    fuente = collections.defaultdict(collections.Counter)
    secciones = collections.defaultdict(collections.Counter)
    ejemplos = {}

    with open(RUTA, "r", encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            total += 1
            try:
                reg = json.loads(linea)
            except ValueError:
                corruptas += 1
                continue
            campos = reg.get("campos") or {}
            tipo = str(_valor(campos, "type", "(sin type)"))
            por_tipo[tipo] += 1
            cert[tipo][str(reg.get("certainty"))] += 1
            fuente[tipo][str(reg.get("source"))] += 1
            secciones[tipo][str(reg.get("source_section"))] += 1
            tiene_seg = all(_tiene_valor(campos, t) for t in TEMPORALES)
            tiene_anio = _tiene_valor(campos, "year")
            hay_sujeto = False
            for s in SUJETOS:
                if _tiene_valor(campos, s):
                    campo_sujeto[tipo][s] += 1
                    hay_sujeto = True
            if tiene_seg:
                con_tiempo[tipo] += 1
            if tiene_anio:
                con_anio[tipo] += 1
            if hay_sujeto:
                con_sujeto[tipo] += 1
            if tiene_anio and hay_sujeto:
                con_estructura[tipo] += 1
            if tipo not in ejemplos:
                ejemplos[tipo] = {
                    "record_id": reg.get("record_id"),
                    "df_id": reg.get("df_id"),
                    "certainty": reg.get("certainty"),
                    "source": reg.get("source"),
                    "source_section": reg.get("source_section"),
                    "campos": {k: _valor(campos, k) for k in sorted(campos)},
                }
    return {"total": total, "corruptas": corruptas, "por_tipo": por_tipo,
            "con_tiempo": con_tiempo, "con_anio": con_anio,
            "con_sujeto": con_sujeto, "con_estructura": con_estructura,
            "campo_sujeto": campo_sujeto, "cert": cert, "fuente": fuente,
            "secciones": secciones, "ejemplos": ejemplos}


def _sujeto_real(b, tipo):
    """El campo de sujeto que MAS registros de este tipo traen.

    Se elige por CONTEO, no por suposicion. Un campo que aparece en el 3 % de
    los registros no identifica al sujeto de forma fiable.
    """
    conteo = b["campo_sujeto"][tipo]
    if not conteo:
        return None, 0
    par = conteo.most_common(1)[0]
    return par[0], par[1]


def clasificar(b):
    """Clasifica cada tipo. Filas ordenadas por conteo descendente.

    Estructura = `year` utilizable + algun sujeto utilizable en el MISMO
    registro (comparacion conjunta, no acumulados por tipo: el `any()` sobre
    el contador global era un defecto que inflaba `con_sujeto`).
    Instante = ademas `seconds72` utilizable. La estructura decide la base;
    la regla demostrada (`MAPA_TIPOS`) decide la emision:

        SUPPORTED   regla demostrada + estructura en todos sus registros
        PARTIAL     regla demostrada pero estructura incompleta en parte
        NOT_PROVEN  sin regla demostrada, con algun registro con estructura
        UNSUPPORTED sin regla y ningun registro con estructura
    """
    filas = []
    mapa = cd.MAPA_TIPOS
    for tipo, n in b["por_tipo"].most_common():
        campo, _n_suj = _sujeto_real(b, tipo)
        n_completo = b["con_tiempo"][tipo]
        n_estructura = b["con_estructura"][tipo]
        estructura_total = (n_estructura == n)
        comun = {"tipo_raw": tipo, "n": n,
                 "registros_con_estructura": n_estructura,
                 "registros_con_instante": n_completo,
                 "campo_sujeto_observado": campo,
                 "certainty_observada": dict(b["cert"][tipo].most_common(3)),
                 "source": dict(b["fuente"][tipo].most_common(2)),
                 "source_section": dict(b["secciones"][tipo].most_common(2))}

        if tipo in mapa:
            tipo_ch, campo_mapa = mapa[tipo]
            regla = ("hfid + year + seconds72 + cause + slayer_hfid. El sujeto "
                     "es quien murio; `slayer_hfid` es un PAPEL, no el sujeto."
                     if tipo_ch == cd.ch.DEATH else
                     "%s + year + seconds72" % campo_mapa)
            if estructura_total:
                grado = SUPPORTED
                motivo = ("regla demostrada en MAPA_TIPOS + year y sujeto en "
                          "el 100%% de sus %d registros (instante completo en "
                          "%d; el resto se emite con tiempo PARTIAL, no se "
                          "descarta)" % (n, n_completo))
            elif n_estructura > 0:
                grado = PARTIAL
                motivo = ("regla demostrada pero sin year+sujeto en %d de %d "
                          "registros: esa parte se declara, no se inventa"
                          % (n - n_estructura, n))
            else:
                grado = UNSUPPORTED
                motivo = ("regla demostrada, pero NINGUN registro trae "
                          "year+sujeto utilizables")
            filas.append(dict(comun, tipo_chronicle=tipo_ch, grado=grado,
                              regla=regla, campo_sujeto=campo_mapa,
                              evidencia="MAPA_TIPOS + %d/%d estructura + %d/%d "
                                        "instante" % (n_estructura, n,
                                                      n_completo, n),
                              motivo=motivo))
            continue

        if n_estructura == 0:
            grado = UNSUPPORTED
            motivo = ("ningun registro trae year+sujeto utilizables en el "
                      "mismo registro; no hay nada que colocar en una "
                      "cronica")
        else:
            grado = NOT_PROVEN
            motivo = ("estructura presente en %d/%d registros, pero la "
                      "SEMANTICA no esta demostrada: el motor no la infiere "
                      "del nombre" % (n_estructura, n))
        filas.append(dict(comun, tipo_chronicle=None, grado=grado,
                          regla=None, campo_sujeto=campo,
                          evidencia="%d/%d estructura (year+sujeto), %d/%d "
                                    "con instante, sujeto en `%s`"
                                    % (n_estructura, n, n_completo, n, campo),
                          motivo=motivo))
    return filas


def resumen(filas, total, corruptas):
    por_grado = collections.Counter(f["grado"] for f in filas)
    return {
        "version": 1,
        "contrato": "tipo_raw -> tipo_chronicle -> regla_semantica -> evidencia",
        "grados": list(GRADOS),
        "definicion": {
            SUPPORTED: "semantica demostrada; se convierte en evento Chronicle",
            PARTIAL: "se convierte en parte; el resto se declara, no se inventa",
            NOT_PROVEN: "estructura suficiente, significado NO demostrado",
            UNSUPPORTED: "no se puede construir un evento utilizable",
        },
        "registros_totales": total,
        "registros_corruptos": corruptas,
        "tipos_totales": len(filas),
        "por_grado": dict((g, por_grado.get(g, 0)) for g in GRADOS),
        "tipos": filas,
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Clasifica los tipos de evento por evidencia real")
    p.add_argument("--json", default=None, help="fichero de salida")
    p.add_argument("--muestra", type=int, default=0, help="filas a imprimir")
    a = p.parse_args(argv)

    b = barrer()
    filas = clasificar(b)
    doc = resumen(filas, b["total"], b["corruptas"])
    doc["ejemplos"] = b["ejemplos"]

    print("=" * 78)
    print("CLASIFICACION DE TIPOS POR EVIDENCIA")
    print("=" * 78)
    print("registros leidos : %d" % b["total"])
    print("corruptos       : %d" % b["corruptas"])
    print("tipos           : %d" % len(filas))
    for g in GRADOS:
        n = doc["por_grado"][g]
        regs = sum(f["n"] for f in filas if f["grado"] == g)
        print("  %-12s %3d tipos  %8d registros" % (g, n, regs))
    if a.muestra:
        print()
        print("%-38s %7s %-12s" % ("TIPO", "N", "GRADO"))
        print("-" * 78)
        for f in filas[:a.muestra]:
            print("%-38s %7d %-12s"
                  % (f["tipo_raw"][:38], f["n"], f["grado"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        print("\n-> %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())