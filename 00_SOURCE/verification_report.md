# DF-Chronicles :: Verificación de integridad de los XML divididos

Generado por `Tarea 1` con Python 3.14 (stdlib: `xml.etree.ElementTree`, `pathlib`, `re`, `collections`).

- Directorio auditado: `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE\processed`
- Patrón: `legends_*.xml`
- Archivos encontrados: **83**
- Tamaño total: **49,242,615 bytes** (47.0 MiB)
- Declaraciones XML detectadas: {'v1.0 enc=UTF-8': 83}
- Fecha del análisis: 2026-10-02

## Detalle por archivo

| Archivo | Entradas | Estado | Notas |
|---|---:|---|---|
| `legends_01_regions.xml` | 840 | OK | parsea, raíz y sección correctas |
| `legends_02_underground.xml` | 405 | OK | parsea, raíz y sección correctas |
| `legends_03_sites.xml` | 734 | OK | parsea, raíz y sección correctas |
| `legends_04_constructions.xml` | 0 | OK | parsea, raíz y sección correctas |
| `legends_05_artifacts.xml` | 427 | OK | parsea, raíz y sección correctas |
| `legends_06_entity_populations.xml` | 243 | OK | parsea, raíz y sección correctas |
| `legends_07_entities.xml` | 1067 | OK | parsea, raíz y sección correctas |
| `legends_08_event_collections.xml` | 6544 | OK | parsea, raíz y sección correctas |
| `legends_09_eras.xml` | 1 | OK | parsea, raíz y sección correctas |
| `legends_10_written_contents.xml` | 2341 | OK | parsea, raíz y sección correctas |
| `legends_11_poetic_forms.xml` | 95 | OK | parsea, raíz y sección correctas |
| `legends_12_musical_forms.xml` | 104 | OK | parsea, raíz y sección correctas |
| `legends_13_dance_forms.xml` | 107 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_00000-00999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_01000-01999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_02000-02999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_03000-03999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_04000-04999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_05000-05999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_06000-06999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_07000-07999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_08000-08999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_09000-09999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_10000-10999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_20_historical_figures_11000-11143.xml` | 144 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_00000-00999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_01000-01999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_02000-02999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_03000-03999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_04000-04999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_05000-05999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_06000-06999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_07000-07999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_08000-08999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_09000-09999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_10000-10999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_11000-11999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_12000-12999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_13000-13999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_14000-14999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_15000-15999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_16000-16999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_17000-17999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_18000-18999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_19000-19999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_20000-20999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_21000-21999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_22000-22999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_23000-23999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_24000-24999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_25000-25999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_26000-26999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_27000-27999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_28000-28999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_29000-29999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_30000-30999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_31000-31999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_32000-32999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_33000-33999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_34000-34999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_35000-35999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_36000-36999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_37000-37999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_38000-38999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_39000-39999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_40000-40999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_41000-41999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_42000-42999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_43000-43999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_44000-44999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_45000-45999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_46000-46999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_47000-47999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_48000-48999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_49000-49999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_50000-50999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_51000-51999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_52000-52999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_53000-53999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_54000-54999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_55000-55999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_56000-56999.xml` | 1000 | OK | parsea, raíz y sección correctas |
| `legends_21_historical_events_57000-57214.xml` | 215 | OK | parsea, raíz y sección correctas |

## Entradas por sección

| Sección | Entradas | Referencia esperada | Estado |
|---|---:|---:|---|
| `regions` | 840 | 840 | OK |
| `underground_regions` | 405 | 405 | OK |
| `sites` | 734 | 734 | OK |
| `world_constructions` | 0 | 0 | OK (vacía, esperado) |
| `artifacts` | 427 | 427 | OK |
| `entity_populations` | 243 | 243 | OK |
| `entities` | 1067 | 1067 | OK |
| `historical_event_collections` | 6544 | 6544 | OK |
| `historical_eras` | 1 | 1 | OK |
| `written_contents` | 2341 | 2341 | OK |
| `poetic_forms` | 95 | 95 | OK |
| `musical_forms` | 104 | 104 | OK |
| `dance_forms` | 107 | 107 | OK |
| `historical_figures` | 11144 | 11144 | OK |
| `historical_events` | 57215 | 57215 | OK |

**Total de entradas agregadas:** 81,267

## Cotejo directo contra el original (`extraction/`)

Además de validar cada archivo por separado, se releyó el original completo
(`region2-00100-01-01-legends.xml`, 49,223,702 bytes) **en modo solo lectura** y se comparó
sección por sección con la suma de los lotes.

- Codificación real del original: **no decodifica como UTF-8 → CP437** (como anticipaba `dividir_xml.py`).
- Bytes de control presentes en el original: `0x10` × 12 y `0x11` × 12. Fueron saneados **en memoria
  únicamente** para poder parsear; el archivo original no se modificó.
- Raíz del original: `<df_world>`. Contiene las mismas 15 secciones.
- Para las 14 secciones con `<id>`: la **secuencia de ids es idéntica en el mismo orden**
  (`mismo_orden=True`, `mismo_conjunto=True`). Sin pérdidas, sin duplicados, sin reordenaciones.
- `historical_eras` no tiene hijos `<id>` (su única entrada es `<historical_era>` con `name` y
  `start_year`), por lo que no es comparable por id; sí coincide en número (1 = 1).

### Sobre el aviso de ids ausentes en `historical_events`

El original contiene 13,192 huecos dentro del rango `0..70406`. El cotejo confirma que
`processed/` reproduce **exactamente los mismos 13,192 huecos**: son inherentes al archivo
exportado por Dwarf Fortress (ids de eventos no consecutivos), no una pérdida del troceado.

## Resumen final

- Número total de archivos auditados: **83**
- Archivos que parsean correctamente: **83 / 83**
- Archivos con raíz `<df_world>` y una única sección: **83 / 83**
- Discrepancias de recuento encontradas: **0**
- IDs duplicados detectados: **0**
- Total de incidencias registradas: **1**

## Incidencias

- **AVISO**: historical_events: 13192 id(s) ausentes dentro del rango contiguo (p.ej. [536, 537, 540, 541, 542, 570, 581, 582, 583, 596])
