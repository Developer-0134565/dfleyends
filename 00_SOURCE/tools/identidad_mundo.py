#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Identidad del MUNDO durante la extraccion
=========================================================

QUE HACE
--------
Lee del export de Legends la identidad del **mundo** que lo produjo y la devuelve
como metadata. No genera ningun identificador: solo conserva lo que DFHack ya
escribio.

POR QUE EXISTE
--------------
P1 (`P1_VERSIONADO_MUNDO_VIVO.md`) demostro que `dataset_id` es un hash del
CONTENIDO extraido, y que por lo tanto:

  * dos mundos con el mismo contenido reciben el MISMO `dataset_id`;
  * el mundo puede cambiar sin que cambie el `dataset_id`.

La informacion que si distingue un mundo de otro existe en el export, y
`exportlegends.lua` la produce en cada ejecucion:

  * `world_data.name` -> `<df_world><name>`  (linea 139 del script)
  * `cur_savegame.save_dir` -> el PREFIJO del nombre del fichero exportado
                            (linea 130: `save_dir.."-"..fecha.."-legends_plus.xml"`)

El pipeline lo descartaba. Este modulo lo conserva.

LO QUE ESTE MODULO NO ES
------------------------
NO identifica el **estado** del mundo. No hay aqui ningun `state_id`,
`lineage_id`, `branch_id`, `snapshot_id` ni `tick_id`, y no debe añadirse sin
la evidencia que P1 declara ausente.

  * `world_name`   -> identificador DESCRIPTIVO. Dos mundos distintos pueden
                      llamarse igual; un unico mundo puede renombrarse.
  * `world_folder` -> identificador PRACTICO de la instancia de save DENTRO del
                      entorno donde se exporto. No es globalmente unico.

DETERMINISMO
------------
Sin reloj, sin aleatorio, sin `uuid`. Las mismas entradas dan siempre el mismo
resultado, y por tanto el mismo `dataset_version.json`.

AUSENCIAS
---------
Si un dato no esta, se declara `UNKNOWN` con su motivo. **Nunca** se rellena
con un timestamp, con el nombre del fichero, ni con un valor inventado: un
identificador falso es peor que ningun identificador.
"""
import os
import re

#: Valor para "el export no lo trae". Es el mismo criterio que ya usa
#: `ia_conocimiento.DESCONOCIDO`: lo ausente se declara, no se supone.
DESCONOCIDO = "UNKNOWN"

#: Motivos posibles de ausencia. Se guardan con el dato para que una ausencia
#: siga siendo informacion y no un simple `None`.
SIN_NOMBRE = "el export no contiene <df_world><name>"
SIN_CARPETA = ("el nombre del fichero exportado no conserva el prefijo "
               "save_dir que escribe exportlegends.lua")
SIN_FICHERO = "el fichero de export no existe"

#: exportlegends.lua:130 compone el nombre as::
#:
#:     save_dir .. "-" .. '%05d-%02d-%02d' .. "-legends_plus.xml"
#:
#: donde el segundo grupo es `cur_year`-`mes`-`dia`. Solo se conserva el
#: PRIMER grupo (`save_dir`). El segundo se descarta a proposito: es una fecha de
#: juego, y P1 demostro que el estado del mundo no es funcion del tiempo
#: (`timestream` avanza el mundo sin avanzar el reloj). Guardarla aqui seria
#: crear una identidad de estado sin haberla demostrado.
_SUFIJO = re.compile(r"^(?P<carpeta>.+?)-\d{5}-\d{2}-\d{2}-legends_plus\.xml$")

#: El nombre del mundo va al principio del fichero (`exportlegends.lua:138-139`
#: escribe `<df_world>` y `<name>` antes que nada). Se leen los primeros
#: `_CABECERA` bytes en vez de los 17 MB enteros.
_CABECERA = 1 << 20  # 1 MiB
_RE_NOMBRE = re.compile(r"<df_world>\s*<name>(.*?)</name>", re.S)


def _texto(bruto, codificacion):
    """Decodifica y limpia. Devuelve None si no queda texto utilizable."""
    if not bruto:
        return None
    texto = bruto.decode(codificacion, errors="replace")
    # `escape_xml` de exportlegends.lua escapa &, < y >. Se deshace lo basico
    # para no guardar entidades donde el mundo se llamaba "A & B".
    texto = texto.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    texto = texto.strip()
    return texto or None


def mundo_nombre(ruta_plus):
    """`world_data.name` tal como lo escribio exportlegends.lua.

    Devuelve `(valor, motivo_de_ausencia)`. Nunca lanza por un fichero malo:
    una identidad ausente es un dato, no un fallo del pipeline.
    """
    if not ruta_plus or not os.path.isfile(ruta_plus):
        return None, SIN_FICHERO
    with open(ruta_plus, "rb") as f:
        cabecera = f.read(_CABECERA)
    for cod in ("utf-8", "cp437"):
        try:
            texto = cabecera.decode(cod)
        except UnicodeDecodeError:
            continue
        m = _RE_NOMBRE.search(texto)
        if m:
            valor = _texto(m.group(1).encode(cod), cod)
            if valor:
                return valor, None
    return None, SIN_NOMBRE


def mundo_carpeta(ruta_plus):
    """`save_dir` a partir del nombre con que DFHack escribio el export.

    exportlegends.lua:130 antepone `save_dir` al nombre del fichero. Si el
    fichero se copio o renombro (que es lo que hizo este proyecto), ese prefijo
    ya no esta y no hay forma de recuperarlo del XML: `save_dir` no se escribe
    en el cuerpo. En ese caso se declara ausente, sin adivinar.
    """
    nombre = os.path.basename(ruta_plus or "")
    m = _SUFIJO.match(nombre)
    if not m:
        return None, SIN_CARPETA
    carpeta = m.group("carpeta").strip()
    return (carpeta or None), None


def desde_export(ruta_plus):
    """Metadata de identidad del mundo de un export. Claves SIEMPRE presentes.

    El shape es fijo a proposito: un consumidor puede leer `mundo["world_name"]`
    sin comprobar antes si la clave existe, y obtiene `UNKNOWN` en vez de un
    `KeyError`.
    """
    nombre, falta_nombre = mundo_nombre(ruta_plus)
    carpeta, falta_carpeta = mundo_carpeta(ruta_plus)
    return {
        "world_name": nombre or DESCONOCIDO,
        "world_folder": carpeta or DESCONOCIDO,
        "world_name_ausente_porque": falta_nombre,
        "world_folder_ausente_porque": falta_carpeta,
        "origen": "exportlegends.lua",
        "campos": "<df_world><name> y prefijo save_dir del nombre del export",
    }


def anadir_a_registro(registro, identidad):
    """Inyecta la identidad del mundo en un `dataset_version.json`.

    ES ADITIVO Y AISLADO A PROPOSITO:

      * no toca `dataset_id`, que se deriva de `salidas` y por tanto no cambia;
      * no toca `salidas`, `entradas`, `conteos` ni `merge`;
      * por tanto `es_actual()` y toda la invalidacion por dataset siguen
        funcionando exactamente igual.

    Devuelve el mismo `registro`, mutado, para poder encadenar la llamada.
    """
    if isinstance(registro, dict):
        registro["mundo"] = identidad
    return registro


if __name__ == "__main__":  # pragma: no cover - herramienta manual
    import json
    import sys
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "original_data", "legends_plus.xml")
    print(json.dumps(desde_export(destino), ensure_ascii=False, indent=2))