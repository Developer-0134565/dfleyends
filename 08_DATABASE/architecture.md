# Arquitectura de DF-Chronicles

Documento técnico de la capa de datos y consulta: qué existe, por qué se
decidió así y qué límites tiene.

---

## 1. Flujo de datos

```
region2-...-legends.xml  ──┐
region2-...-legends_plus.xml ─┼─> 00_SOURCE/processed/  ──(nucleo.py)──> API
                                        │
                                   merged/       normalizado
                                   validation/   fixtures
```

`world.sav` → `extraction/` es un camino independiente (ver `extract_world.py`);
no participa en el núcleo de consulta.

Cada etapa escribe en su propia carpeta y **nunca sobrescribe los originales**.

---

## 2. Las dos fuentes

| | `legends.xml` | `legends_plus.xml` |
|---|---|---|
| Rol | **Primaria** | **Complementaria** |
| Codificación | CP437 | UTF-8 |
| Tamaño | 49.223.702 B | 17.664.819 B |
| Aporta | eventos, colecciones, era, nombres en línea | relaciones sociales, geografía, identidades |
| SHA-256 | `77db4739…a4681f` | `fb6be93d…94abc2d` |

**`legends_plus.xml` no sustituye al original**: pierde las 6.544
`historical_event_collections`, la era y los nombres en línea de las 11.144
figuras. Se integra como complemento.

### Detección de codificación

`cargar_legends.py` **no tiene valores hardcodeados**. Orden de detección:

1. BOM UTF-8 / UTF-16.
2. Decodificación estricta UTF-8 (si pasa, el archivo es UTF-8 válido).
3. La codificación declarada en `<?xml encoding="..."?>`.
4. Cascada de candidatos.
5. CP437 como último recurso (mapea los 256 valores de byte).

Los bytes de control prohibidos (`0x00-0x08`, `0x0b`, `0x0c`, `0x0e-0x1f`) se
eliminan **solo en memoria**. Los originales quedan intactos.

---

## 3. Capas del sistema

### 3.1 `cargar_legends.py` — acceso a bytes

Decodifica, sanea en memoria y parsea. Devuelve un árbol ElementTree.

### 3.2 `integrar_legends.py` — normalización y merge

Vuelca cada sección a JSONL con metadatos:

```json
{
  "record_id": "historical_figures:712",
  "df_id": "712",
  "certainty": "FACT",
  "source": "legends.xml",
  "source_section": "historical_figures",
  "sources": ["legends.xml", "legends_plus.xml"],
  "campos": {
    "name": {"valor": "galka shafttop…", "source": "legends.xml",
             "source_section": "historical_figures"}
  },
  "conflictos": []
}
```

**Reglas de merge**

1. `legends.xml` es primaria: sus campos nunca se pierden.
2. Un valor vacío en plus **nunca** pisa un valor de la primaria.
3. Un valor de la primaria **nunca** se descarta por faltar en plus.
4. Divergencia con ambos valores no vacíos → se conservan **ambos** y se
   registra el conflicto con su tipo.
5. Los datos exclusivos de plus se incorporan íntegros.

### 3.3 `validar_semantica.py` — índice de referencias cruzadas

Construye el índice en memoria y valida que las relaciones se resuelvan. Es la
capa que `nucleo.py` **reutiliza**, no duplica.

| Índice | Enlace |
|---|---|
| `ev_por_hf` | `historical_events.hfid`, `group_1_hfid`, `group_2_hfid`, `target_hfid`… |
| `ev_por_entidad` | `historical_events.civ_id` |
| `ev_por_sitio` | `historical_events.site_id` |
| `hf_por_entidad` | `historical_figures.entity_link.entity_id` |
| `hf_por_sitio` | `historical_figures.site_link.site_id` |
| `ent_por_sitio` | `sites.civ_id`, `sites.cur_owner_id` |
| `art_por_hf` | `artifacts.holder_hfid` |
| `art_por_sitio` | `artifacts.site_id` |
| `rel_por_hf` | `relationships.source_hf` / `target_hf` |
| `col_por_evento` | `historical_event_collections.event` |

> **Detalle crítico:** todas las claves se normalizan a **texto**. `df_id` es
> una cadena en los JSONL; usar enteros rompe *silenciosamente* todas las
> referencias cruzadas.
### 3.4 `nucleo.py` — API de consulta

Añade sobre lo anterior: búsqueda con normalización, fichas estructuradas,
cronología, relaciones sociales tipadas, agrupaciones de conflicto DERIVED y
exportación a JSON/Markdown.

---

## 4. Modelo de certeza

| Nivel | Significado | Ejemplo |
|---|---|---|
| `FACT` | Está literalmente en el XML | `race: "MINOTAUR"` |
| `DERIVED` | Calculado mecánicamente sobre FACT | construcción en la coordenada de un sitio |
| `INTERPRETATION` | Lectura humana. **No se genera** | — |
| `UNKNOWN` | El dato no consta | `birth_year` con `-1` |

El centinela `-1` de Dwarf Fortress significa *sin dato*: se trata como
ausente, nunca como un ID válido ni como una fecha.

---

## 5. Decisiones de diseño

**Por qué JSONL y no SQLite.**
El volumen es pequeño (≈80.000 registros) y el acceso es por índice. JSONL
permite inspección directa, streaming y regeneración trivial. `schema/schema.sql`
documenta la estructura relacional para cuando haga falta una base de datos.

**Por qué se conserva el conflicto.**
Los 1.925 conflictos reales son datos, no errores. Elegir un valor destruiría
información: `legends.xml` da el token raws (`COLOSSUS_BRONZE`) y plus el
nombre legible (`bronze colossus`). Ambos se guardan con su procedencia.

**Por qué no hay tabla de guerras.**
El XML no la tiene. Los conflictos son eventos discretos con `type` y
`subtype`. Una entidad `WAR` sería DERIVED y exige una regla explícita:
`type == 'hf simple battle event'` y `subtype ∈ {attacked, ambushed, confront…}`.
La regla está en `nucleo.conflictos()`, pero **no afirma que una guerra
ocurriera**.

**Por qué las 13.192 relaciones no son eventos.**
Sus `event_id` apuntan a IDs que **no existen** en `historical_events`
(coincidencia exacta 13.192/13.192). Dwarf Fortress las exporta en una tabla
aparte. Convertirlas en eventos sería inventar 13.192 filas.

---

## 6. Rendimiento

Medido en `probar_nucleo.py::TestRendimiento`:

| Operación | Tiempo |
|---|---:|
| Carga inicial (índice completo) | ≈ 2,5 s |
| Ficha de figura (158 eventos) | ≈ 0,002 s |
| Búsqueda por nombre | ≈ 0,003 s |
| Miembros de entidad | < 0,001 s |
| Eventos entre dos años | ≈ 0,12 s |
| Ficha de sitio (1.546 eventos) | ≈ 0,05 s |
| Conflictos (5.478 eventos) | ≈ 0,32 s |

La carga la domina el parseo de los JSONL. Para un servicio, lo natural es
cachear el índice o moverlo a una base de datos.

---

## 7. Garantías de integridad

- Los XML de `original_data/` se abren en modo lectura; su SHA-256 se verifica
  en la suite de integración (prueba 11).
- Las copias archivadas se comparan por hash y **nunca se sobrescriben**.
- Las pruebas verifican **valores concretos**, no la ausencia de excepciones:
  la figura 712 tiene exactamente 158 eventos, el sitio 87 tiene 1.546 eventos
  y 48 figuras, la entidad 282 tiene 25 miembros.