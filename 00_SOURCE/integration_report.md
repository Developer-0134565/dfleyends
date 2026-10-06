# DF-Chronicles :: Informe de integración de los exports de Legends

Integración de los dos exports de Legends en una base unificada y trazable.

- **Fecha de ejecución:** 2026-10-02T18:02:51.430913+00:00
- **Herramientas:** `00_SOURCE/tools/cargar_legends.py`, `integrar_legends.py`, `probar_integracion.py`
- **Dependencias:** solo biblioteca estándar de Python 3.14 (`xml.etree.ElementTree`, `pathlib`, `json`, `hashlib`, `re`, `collections`, `unittest`)
- Los XML originales se abren **solo en lectura** y no han sido modificados.

## 1. Archivos utilizados

| # | Archivo | Rol | Ruta real de origen |
|---|---|---|---|
| 1 | `legends.xml` | **Fuente primaria** | `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE\extraction\region2-00100-01-01-legends.xml` |
| 2 | `legends_plus.xml` | Fuente complementaria | `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\region2-00100-01-01-legends_plus.xml` |

> **Nota sobre la ruta.** `legends_plus.xml` no estaba en `00_SOURCE/`. Se localizó en la carpeta de
> instalación de Dwarf Fortress (`Downloads/Dwarf-Fortress-AnkerGames/Dwarf Fortress/`) y se
> documenta aquí su ruta real. No se invirtió ninguna ruta.

## 2. SHA-256 y codificación detectada

| | legends.xml | legends_plus.xml |
|---|---|---|
| SHA-256 | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` |
| Tamaño | 49.223.702 bytes | 17.664.819 bytes |
| Codificación detectada | **CP437** | **utf-8** |
| Método de detección | UTF-8 falló; 'CP437' decodifica (= declaración XML) | declaración declara UTF-8 |
| BOM | ninguno | ninguno |
| Bytes de control | `{'0x10': 12, '0x11': 12}` | `{}` |
| Requiere saneo en memoria | sí | no |
| Raíz XML | `df_world` | `df_world` |
| Total de entradas | 81.267 | 75.089 |

La codificación **se detecta en tiempo de ejecución**, no está hardcodeada: el cargador prueba
UTF-8 estricto, luego la declaración XML, luego una cascada, y usa CP437 solo como último recurso.

### Originales archivados en `00_SOURCE/original_data/`

| Archivo | Acción | Copia idéntica al original |
|---|---|---|
| `legends.xml` | ya existía (NO sobrescrito) | sí |
| `legends_plus.xml` | ya existía (NO sobrescrito) | sí |

La copia es **idempotente**: si el archivo ya existe se compara el hash y **nunca se sobrescribe**.

## 3. Registros por sección

### 3.1 `legends.xml` (fuente primaria)

| Sección | Entradas |
|---|---:|
| `historical_events` | 57.215 |
| `historical_figures` | 11.144 |
| `historical_event_collections` | 6.544 |
| `written_contents` | 2.341 |
| `entities` | 1.067 |
| `regions` | 840 |
| `sites` | 734 |
| `artifacts` | 427 |
| `underground_regions` | 405 |
| `entity_populations` | 243 |
| `dance_forms` | 107 |
| `musical_forms` | 104 |
| `poetic_forms` | 95 |
| `historical_eras` | 1 |
| `world_constructions` | 0 |
| **Total** | **81.267** |

### 3.2 `legends_plus.xml` (fuente complementaria)

| Sección | Entradas |
|---|---:|
| `historical_events` | 40.061 |
| `historical_event_relationships` | 13.192 |
| `historical_figures` | 11.144 |
| `rivers` | 2.346 |
| `written_contents` | 2.341 |
| `creature_raw` | 1.321 |
| `entities` | 1.067 |
| `regions` | 840 |
| `sites` | 734 |
| `identities` | 475 |
| `artifacts` | 427 |
| `underground_regions` | 405 |
| `entity_populations` | 243 |
| `world_constructions` | 122 |
| `dance_forms` | 107 |
| `musical_forms` | 104 |
| `poetic_forms` | 95 |
| `landmasses` | 40 |
| `historical_event_relationship_supplements` | 21 |
| `mountain_peaks` | 4 |
| `name` | 0 |
| `altname` | 0 |
| `historical_event_collections` | 0 |
| `historical_eras` | 0 |
| **Total** | **75.089** |

## 4. Registros exclusivos de cada fuente

| Categoría | Registros | Significado |
|---|---:|---|
| Solo en `legends.xml` | 63.760 | Existen en la primaria y plus no los aporta |
| Solo en `legends_plus.xml` | 122 | Aportados únicamente por la complementaria |
| **Fusionados (ambos)** | **17.507** | Presentes en las dos fuentes |

Las secciones exclusivas de `legends.xml` (`historical_events`, `historical_event_collections`,
`historical_eras`) se vuelcan en `merged/` sin mezclarlas, porque `legends_plus.xml` las tiene vacías.

## 5. Divergencias entre las dos fuentes

Total de divergencias detectadas: **12.866**. Ninguna se resuelve en silencio: **se conservan ambos valores** con su procedencia.

| Tipo | Registros | Descripción |
|---|---:|---|
| `notacion_equivalente` | 10.941 | El mismo dato en dos notaciones (token raws frente a nombre legible). Ambos se conservan. |
| `conflicto_real` | 1.925 | Valores efectivamente distintos. Ambos se conservan sin elegir. |

### Divergencias por campo

| Campo | Tipo | Casos |
|---|---|---:|
| `race` | notacion_equivalente | 10.640 |
| `style` | conflicto_real | 1.426 |
| `race` | conflicto_real | 499 |
| `structures.structure.name` | notacion_equivalente | 170 |
| `structures.structure.type` | notacion_equivalente | 131 |

Ejemplo canónico del caso `notacion_equivalente`: el campo `race` aparece como token raws en
`legends.xml` (`COLOSSUS_BRONZE`) y como nombre legible en `legends_plus.xml` (`bronze colossus`).
Es **el mismo dato**, no una contradicción: se conservan ambas formas y `legends.xml` aporta el
token original.

## 6. Eventos y los 13.192 relationships

| Concepto | Valor |
|---|---:|
| Eventos en `historical_events` | 57.215 |
| Ids ausentes en el rango | 13.192 |
| `historical_event_relationships` (plus) | 13.192 |
| Supplements (plus) | 21 |

**Política aplicada, sin inventar eventos:**

> Los ids ausentes NO se materializan como eventos; los relationships se conservan como sección relacionada.

Los ids ausentes **no se materializan** como filas de evento. `merged/historical_events.jsonl`
contiene exactamente 57.215 filas, y las relaciones se guardan aparte en
`merged/historical_event_relationships.jsonl`, cada una con su `event_id` y el indicador
`event_existe_en_historical_events`, que en los 13.192 casos es `false`.

Esto reproduce exactamente lo que exporta Dwarf Fortress: los eventos de relación no forman parte
de la tabla de eventos del export principal.

## 7. Comprobaciones realizadas

`00_SOURCE/tools/probar_integracion.py` — **20 pruebas, todas correctas**.

| # | Comprobación | Resultado |
|---|---|---|
| 01-02 | Ambos XML se leen y tienen raíz `<df_world>` | OK |
| 03-04 | Decodificación correcta: CP437 para `legends.xml`, UTF-8 para `legends_plus.xml` | OK |
| 05 | Bytes de control solo en `legends.xml` (0x10 y 0x11) | OK |
| 06 | 13.192 `historical_event_relationships` | OK |
| 07 | 2.346 `rivers` | OK |
| 08 | 40 `landmasses` y 4 `mountain_peaks` | OK |
| 09 | 122 `world_constructions` | OK |
| 10 | Conteos de `legends.xml` intactos en las 15 secciones | OK |
| 11 | Los XML originales **no fueron modificados** (SHA-256 verificado) | OK |
| 12 | Las copias en `original_data/` son idénticas a los originales | OK |
| 13 | Los IDs originales de `legends.xml` permanecen intactos y sin duplicados | OK |
| 14 | Los ids ausentes **no** se materializan como eventos | OK |
| 15 | Los relationships se guardan como relaciones, no como eventos | OK |
| 16 | Todo campo lleva `source` y `source_section` | OK |
| 17 | Paridad de campos vacíos: `merged` conserva los mismos que el original | OK |
| 17b | `legends_plus.xml` no introduce campos vacíos | OK |
| 18 | Sin duplicados silenciosos ni registros sin fuente declarada | OK |
| 19 | Las divergencias están clasificadas y suman el total | OK |

### Verificación byte a byte de los originales

| Archivo | SHA-256 antes | SHA-256 después | Estado |
|---|---|---|---|
| `legends.xml` | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` | **sin cambios** |
| `legends_plus.xml` | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` | **sin cambios** |

## 8. Estructura generada

```
00_SOURCE/
|-- original_data/                      <- originales archivados (solo lectura)
|   |-- legends.xml
|   +-- legends_plus.xml
|-- processed/
|   |-- from_legends_xml/               <- volcado trazable de la primaria
|   |   +-- <seccion>.jsonl
|   |-- from_legends_plus/              <- volcado trazable de la complementaria
|   |   +-- <seccion>.jsonl
|   +-- merged/                         <- datos normalizados y fusionados
|       |-- <seccion>.jsonl
|       |-- historical_event_relationships.jsonl
|       |-- historical_event_relationship_supplements.jsonl
|       |-- indice_evento_relaciones.json      (DERIVED)
|       +-- _manifiesto.json
|-- tools/
|   |-- cargar_legends.py               <- cargador con deteccion de codificacion
|   |-- integrar_legends.py             <- normalizador / fusionador
|   +-- probar_integracion.py           <- 20 pruebas de integracion
+-- integration_report.md
08_DATABASE/schema/schema.sql          <- 15 tablas, 4 vistas
```

### Formato de un registro normalizado

```json
{
  "record_id": "historical_figures:1234",
  "df_id": "1234",
  "certainty": "FACT",
  "source": "legends.xml",
  "source_section": "historical_figures",
  "sources": ["legends.xml", "legends_plus.xml"],
  "en_legends_xml": true,
  "en_legends_plus": true,
  "campos": {
    "name": {"valor": "...", "source": "legends.xml",
               "source_section": "historical_figures"},
    "race": {"valor": "COLOSSUS_BRONZE", "source": "legends.xml",
              "source_section": "historical_figures", "conflicto": true}
  },
  "conflictos": [
    {"campo": "race", "record_id": "historical_figures:1234",
     "valor_legends_xml": "COLOSSUS_BRONZE",
     "valor_legends_plus_xml": "bronze colossus",
     "tipo": "notacion_equivalente",
     "resolucion": "Mismo valor en dos notaciones; se conservan ambos."}
  ]
}
```

## 9. Clasificación de certeza

| Nivel | Uso en esta integración |
|---|---|
| **FACT** | Valor presente literalmente en el XML. Caso de todos los registros de `from_legends_xml/`, `from_legends_plus/` y los campos de `merged/`. |
| **DERIVED** | Valor calculado: `record_id` de registros sin `<id>` (p.ej. `rivers`, hash determinista del contenido) e `indice_evento_relaciones.json`. |
| **INTERPRETATION** | **No se genera en esta fase.** No se ha producido ninguna crónica, lore ni interpretación. |
| **UNKNOWN** | Reservado. No se ha rellenado ningún campo con datos inventados. |

## 10. Reglas de merge aplicadas

1. `legends.xml` es la fuente **primaria**: sus campos nunca se pierden.
2. Un valor vacío en `legends_plus.xml` **nunca** pisa un valor de `legends.xml`.
3. Un valor de `legends.xml` **nunca** se descarta por no existir en `legends_plus.xml`.
4. Divergencia con ambos valores no vacíos → se conservan **ambos** y se registra el conflicto.
5. Los datos exclusivos de `legends_plus.xml` se incorporan íntegros.
6. Todo campo lleva `source` y `source_section`.
7. Los ids ausentes de `historical_events` no se materializan; las relaciones se conservan aparte.
8. Los registros que ya tienen ID de Dwarf Fortress conservan su ID original. Los que no lo tienen
   reciben un `record_id` **determinista** derivado del contenido (nunca aleatorio).

## 11. Estado y siguientes pasos

Integración completada y verificada. **No se ha generado ninguna crónica, lore ni interpretación.**

Trabajo pendiente, si se desea continuar:

- Poblar las tablas de `08_DATABASE/schema/schema.sql` desde los JSONL.
- Extender el esquema relacional a las secciones exclusivas de `legends_plus.xml`
  (`rivers`, `landmasses`, `mountain_peaks`, `identities`, `creature_raw`), ya volcadas en
  `from_legends_plus/`.
