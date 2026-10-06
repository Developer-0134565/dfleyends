#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Troceador del XML de Legends
=============================================

Divide el XML original en fragmentos por seccion, para poder inspeccionarlos
sin abrir 49 MB de golpe.

NOTA: antes este script ejecutaba su logica EN EL IMPORT. Eso hacia que
cualquier `import dividir_xml` escribiera ficheros. Ahora todo va bajo
`main()`, y solo si se ejecuta directamente.

Uso:  python dividir_xml.py
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402

BASE = Path(rutas.DATA_ROOT)
# Por defecto se trocea el XML YA REGISTRADO en original_data/ (no el volcado
# intermedio de extraction/, que es una copia de trabajo).
ENTRADA = Path(os.environ.get("DFCHRON_SPLIT_INPUT", "").strip()
               or (BASE / "original_data" / "legends.xml"))
PROC = Path(os.environ.get("DFCHRON_SPLIT_OUTPUT", "").strip()
            or (BASE / "processed"))

# Tamaño de lote para secciones con muchas entradas repetidas
TAM_LOTE = 1000


def trocear():
    if not ENTRADA.exists():
        raise SystemExit(f"No existe el XML de entrada: {ENTRADA}")
    raw = ENTRADA.read_bytes()
    try:
        text = raw.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("cp437", errors="replace")
        enc = "cp437"
    print(f"Codificación usada: {enc}")

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"<\?xml[^>]*\?>", '<?xml version="1.0" encoding="UTF-8"?>',
                  text, count=1)

    root = ET.fromstring(text)
    return root, enc


# Secciones "simples": se vuelcan tal cual, un archivo por sección
SIMPLES = {
    "regions":                    "legends_01_regions.xml",
    "underground_regions":        "legends_02_underground.xml",
    "sites":                      "legends_03_sites.xml",
    "world_constructions":        "legends_04_constructions.xml",
    "artifacts":                  "legends_05_artifacts.xml",
    "entity_populations":         "legends_06_entity_populations.xml",
    "entities":                   "legends_07_entities.xml",
    "historical_event_collections": "legends_08_event_collections.xml",
    "historical_eras":            "legends_09_eras.xml",
    "written_contents":           "legends_10_written_contents.xml",
    "poetic_forms":               "legends_11_poetic_forms.xml",
    "musical_forms":              "legends_12_musical_forms.xml",
    "dance_forms":                "legends_13_dance_forms.xml",
}

# Secciones que conviene partir en lotes (muchas entradas por sección)
LOTEABLES = {
    "historical_figures": "legends_20_historical_figures",
    "historical_events":  "legends_21_historical_events",
}


def main():
    root, _ = trocear()
    PROC.mkdir(parents=True, exist_ok=True)

    for hijo in list(root):
        tag = hijo.tag

        if tag in SIMPLES:
            r = ET.Element("df_world")
            r.append(hijo)
            ET.ElementTree(r).write(PROC / SIMPLES[tag], encoding="UTF-8",
                                   xml_declaration=True)
            print(f"  {SIMPLES[tag]}  ({len(list(hijo))} entradas)")

        elif tag in LOTEABLES:
            prefijo = LOTEABLES[tag]
            entradas = list(hijo)
            total = len(entradas)
            print(f"  {tag}: {total} entradas -> lotes de {TAM_LOTE}")
            for i in range(0, total, TAM_LOTE):
                lote = entradas[i:i + TAM_LOTE]
                r = ET.Element("df_world")
                sec = ET.SubElement(r, tag)
                for e in lote:
                    sec.append(e)
                nombre = f"{prefijo}_{i:05d}-{i + len(lote) - 1:05d}.xml"
                ET.ElementTree(r).write(PROC / nombre, encoding="UTF-8",
                                       xml_declaration=True)
                print(f"    {nombre}")

        else:
            print(f"  (desconocido, ignorado) {tag}")

    print("Listo.")


if __name__ == "__main__":
    main()