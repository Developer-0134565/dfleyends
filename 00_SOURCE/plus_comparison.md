# DF-Chronicles :: Comparación `legends.xml` vs `legends_plus.xml`

Generado por las Tareas 2 y 3 con Python 3.14 (stdlib: `xml.etree.ElementTree`, `pathlib`, `re`, `collections`).
Ambos archivos se abrieron **en modo solo lectura**; ninguno fue modificado ni movido.

## 1. Identidad de los archivos

| | legends.xml (original) | legends_plus.xml |
|---|---|---|
| Ruta | `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE\extraction\region2-00100-01-01-legends.xml` | `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\region2-00100-01-01-legends_plus.xml` |
| Tamaño | 49,223,702 bytes (47.0 MiB) | 17,664,819 bytes (16.8 MiB) |
| Codificación real | **CP437 (fallback)** | **UTF-8** |
| Declaración | `<?xml version="1.0" encoding='CP437'?>` | `<?xml version="1.0" encoding='UTF-8'?>` |
| BOM | no | no |
| Líneas | 1,826,107 | 650,256 |
| Bytes de control | {'0x10': 12, '0x11': 12} | ninguno |
| ¿Parsea sin sanear? | **no** (requiere saneo) | **sí** |
| Raíz | `df_world` | `df_world` |

- El original **no decodifica como UTF-8**: es **CP437**, tal como anticipaba `dividir_xml.py`.
- El original contiene **12 bytes `0x10` y 12 bytes `0x11`**, que impiden el parseo XML directo.
- `legends_plus.xml` es **UTF-8 limpio**, sin BOM y **sin ningún byte de control**: parsea directamente
  con `ET.fromstring` sin aplicar el saneo. Los finales de línea son CRLF en ambos.
- El original de `extraction\` y la copia `region2-00100-01-01-legends.xml` de la carpeta de
  instalación son **byte a byte idénticos** (SHA-256 verificado: `True`).

## 2. Recuento por sección

| Sección | legends.xml | legends_plus.xml | Diferencia |
|---|---:|---:|---:|
| `regions` | 840 | 840 | 0 |
| `underground_regions` | 405 | 405 | 0 |
| `sites` | 734 | 734 | 0 |
| `world_constructions` | 0 | 122 | **+122** |
| `artifacts` | 427 | 427 | 0 |
| `historical_figures` | 11144 | 11144 | 0 |
| `entity_populations` | 243 | 243 | 0 |
| `entities` | 1067 | 1067 | 0 |
| `historical_events` | 57215 | 40061 | **-17154** |
| `historical_event_collections` | 6544 | 0 | **-6544** |
| `historical_eras` | 1 | 0 | **-1** |
| `written_contents` | 2341 | 2341 | 0 |
| `poetic_forms` | 95 | 95 | 0 |
| `musical_forms` | 104 | 104 | 0 |
| `dance_forms` | 107 | 107 | 0 |
| `name` | *(ausente)* | 0 | **+0 solo en plus** |
| `altname` | *(ausente)* | 0 | **+0 solo en plus** |
| `landmasses` | *(ausente)* | 40 | **+40 solo en plus** |
| `mountain_peaks` | *(ausente)* | 4 | **+4 solo en plus** |
| `rivers` | *(ausente)* | 2346 | **+2346 solo en plus** |
| `creature_raw` | *(ausente)* | 1321 | **+1321 solo en plus** |
| `identities` | *(ausente)* | 475 | **+475 solo en plus** |
| `historical_event_relationships` | *(ausente)* | 13192 | **+13192 solo en plus** |
| `historical_event_relationship_supplements` | *(ausente)* | 21 | **+21 solo en plus** |

## 3. Tarea 3 — Secciones ausentes o desconocidas

### Solo en `legends_plus.xml` (nuevas, no contempladas en el pipeline actual)

| Sección | Entradas | Campos de una entrada |
|---|---:|---|
| `landmasses` | 40 | `coord_1`, `coord_2`, `id`, `name` |
| `mountain_peaks` | 4 | `coords`, `height`, `id`, `name` |
| `rivers` | 2346 | `end_pos`, `name`, `path` |
| `creature_raw` | 1321 | `all_castes_alive`, `biome_pool_temperate_brackishwater`, `biome_pool_temperate_freshwater`, `biome_pool_temperate_saltwater`, `biome_pool_tropical_brackishwater`, `biome_pool_tropical_freshwater`, `biome_pool_tropical_saltwater`, `creature_id`, `has_any_can_swim`, `has_any_has_blood`, `has_any_natural_animal`, `has_any_not_fireimmune`, `has_any_race_gait`, `has_any_vermin_hateable` |
| `identities` | 475 | `birth_second`, `birth_year`, `entity_id`, `histfig_id`, `id`, `name` |
| `historical_event_relationships` | 13192 | `event`, `relationship`, `source_hf`, `target_hf`, `year` |
| `historical_event_relationship_supplements` | 21 | `event`, `occasion_type`, `reason`, `site` |
| `name` | 0 |  |
| `altname` | 0 |  |
| `world_constructions` | 122 | `coords`, `id`, `name`, `type` |

### Solo en `legends.xml`

**Ninguna.** `legends_plus.xml` contiene **todas** las etiquetas de sección del original, incluidas
`historical_event_collections` y `historical_eras`, que aparecen pero vacías.

### Secciones desconocidas a tratar en el pipeline

Estas etiquetas no estaban en `tools/dividir_xml.py` y quedaron descartadas por su rama
`else: print('(desconocido, ignorado)')`:

| Etiqueta | Dónde | Entradas | Prioridad |
|---|---|---:|---|
| `historical_event_relationships` | solo plus | 13.192 | **alta** |
| `rivers` | solo plus | 2.346 | **alta** (geografía, ausente por completo) |
| `identities` | solo plus | 475 | **alta** (nombres reales de figuras) |
| `creature_raw` | solo plus | 1.321 | media |
| `historical_event_relationship_supplements` | solo plus | 21 | media |
| `landmasses` | solo plus | 40 | baja (geografía) |
| `mountain_peaks` | solo plus | 4 | baja |
| `name` | solo plus | 0 | nula (elemento escalar vacío) |
| `altname` | solo plus | 0 | nula |

Además, `world_constructions` deja de estar vacía: **0 → 122** entradas, y su volcado actual
(`legends_04_constructions.xml`, 108 bytes) no contiene nada aprovechable.

## 4. Hallazgo principal: los huecos de `historical_events` son datos reales

La Tarea 1 detectó que `historical_events` tiene **13.192 ids ausentes** en el rango `0..70406`, y confirmó
que esos huecos ya estaban en el original. La Tarea 2 explica su origen:

| Comprobación | Resultado |
|---|---|
| Rango de ids de eventos | `0..70406` (70.407 valores) |
| Eventos presentes en `legends.xml` | 57,215 |
| Huecos | 70.407 − 57,215 = **13192** |
| Entradas en `historical_event_relationships` (plus) | 13,192 |
| Eventos distintos referenciados en `<event>` | 13,192 |
| **Los relationships cubren EXACTAMENTE los huecos** | **sí (13192/13192)** |
| Huecos sin relationship ni supplement | **0** |

Dwarf Fortress **no pierde** esos 13.192 eventos: los exporta en una tabla aparte. `legends.xml` los deja
fuera de `historical_events`; `legends_plus.xml` los conserva. Ejemplo real extraído del archivo:

```xml
<historical_event_relationship>
  <event>536</event>
  <relationship>lover</relationship>
  <source_hf>541</source_hf>
  <target_hf>542</target_hf>
  <year>1</year>
</historical_event_relationship>
```

## 5. ¿Es `legends_plus.xml` redundante?

**No: es complementaria.** Aporta información que `legends.xml` no contiene, pero pierde detalle.

### Lo que aporta y `legends.xml` no tiene

- **7 secciones nuevas**: geografía (`rivers`, `landmasses`, `mountain_peaks`), `creature_raw`,
  `identities` y las dos tablas de relaciones de eventos.
- **Los 13.192 eventos de relación**, que en el original son huecos. Única fuente de esos datos.
- **`world_constructions` con 122 entradas**, frente a 0 en el original.
- Campos que el original no trae: `regions` gana `coords` y `evilness`; `sites` gana
  `civ_id` y `cur_owner_id`; `artifacts` gana `item_type`, `mat`, `writing` y `page_count`; `entities`
  gana `race`, `child` y `type`; `historical_figures` gana `sex`; `written_contents` gana `author`.

### Lo que pierde respecto a `legends.xml`

- **`historical_event_collections`: 6.544 → 0** y **`historical_eras`: 1 → 0**. Se vacían por completo.
- **`historical_events`: 57,215 → 40,061**. Los eventos del original son un **superconjunto**: los
  40,061 de plus están todos en el original, y al original le sobran **17,154** que plus no trae.
- **Pierde el `name` en línea**: las 11.144 `historical_figures` de plus **no tienen `<name>`** (el original sí),
  ni 849 `entities`, ni 374 `artifacts`, ni los 734 `sites`.
- Las referencias quedan como id en vez de nombre (`hfid`→`hf`, `civ_id`→`civ`, `site_id`→`site`), lo que obliga
  a resolver indirecciones para poder leer nombres.

### Dictamen

- El original es la vista **plana y legible**: nombres en línea, colecciones y eras.
- El plus es la vista **normalizada y georeferenciada**: nombres en tablas, coordenadas y relaciones.

Ninguna sustituye a la otra.

## 6. Recomendación

**Sí merece la pena incorporarlo, pero como fuente complementaria y selectiva, no como sustituto.**

Motivos para sí:

1. Cubre información **irrecuperable** de otro modo: los 13.192 eventos de relación y las 475 identidades.
2. Aporta **geografía ausente por completo**: 2.346 ríos, que el pipeline no tiene de ninguna forma.
3. Rellena `world_constructions`, hoy procesada como sección vacía.

Motivos para no sustituir el original:

1. `legends_plus.xml` **no tiene nombres en línea**; adoptarlo solo obligaría a resolver 11.144
   identidades por `id`, un trabajo que el original ya viene resuelto.
2. Pierde 17.154 eventos y las 6.544 colecciones y la era, que son la espina dorsal del archivo.

| Prioridad | Sección de plus | Acción |
|---|---|---|
| 1 | `historical_event_relationships` (13.192) | **Añadir.** Cierra los 13.192 huecos de eventos. |
| 2 | `historical_event_relationship_supplements` (21) | **Añadir.** Complementa a la anterior. |
| 3 | `rivers` (2.346), `landmasses` (40), `mountain_peaks` (4) | **Añadir** como capas geográficas. |
| 4 | `world_constructions` (122) | **Añadir** y reemplazar el volcado vacío actual. |
| 5 | `identities` (475) | Añadir como tabla de referencias. |
| 6 | `creature_raw` (1.321) | Añadir si el pipeline llega a estadísticas de criaturas. |
| — | `historical_events`, `..._collections`, `historical_eras`, nombres en línea | **No incorporar**: el original es superior. |

## 7. Notas de implementación

- Los originales se leen **sin sanear en disco**: los bytes `0x10`/`0x11` de `legends.xml` se sustituyen
  **en memoria** solo para poder parsear. `legends_plus.xml` no necesita saneo previo.
- `legends_plus.xml` es **UTF-8 con CRLF** y `legends.xml` es **CP437**: cualquier cargador nuevo debe
  detectar la codificación, no asumir una sola.
- `world_constructions` en plus aporta `coords`, lo que permite geolocalizar construcciones que ahora no
  tienen posición utilizable.
- Los archivos están duplicados: el original existe en `extraction\` y en la carpeta de instalación de DF
  (idénticos); `legends_plus.xml` solo existe en la carpeta de instalación.