# API de DF-Chronicles

Referencia completa de la API HTTP local.

* **Base:** `http://127.0.0.1:877`
* **Método:** solo `GET`. `POST`/`PUT`/`DELETE`/`PATCH` responden `405`.
* **Formato:** JSON UTF-8.
* **Documentación viva:** <http://127.0.0.1:877/api>

---

## Formato de respuesta

### Listado

```json
{
  "data": [ ... ],
  "total_encontrados": 1546,
  "devueltos": 200,
  "truncado": true,
  "limit": 200,
  "offset": 0,
  "certainty": "FACT"
}
```

`truncado` es `(offset + devueltos) < total_encontrados`. **Una respuesta
recortada siempre lo dice**: la UI pinta un aviso y nunca oculta que hay más.

### Ficha individual

```json
{ "data": { ... }, "status": "FACT", "certainty": "FACT" }
```

`status` refleja la certeza del dato: `FACT`, `DERIVED` o `UNKNOWN`.

### Error

```json
{
  "error": { "codigo": "NO_ENCONTRADO",
             "mensaje": "no existe la figura con df_id '999999999'" },
  "status": "UNKNOWN",
  "certainty": "UNKNOWN",
  "http_status": 404
}
```

Códigos: `RUTA_DESCONOCIDA` (404), `NO_ENCONTRADO` (404),
`CONSULTA_VACIA` (400), `ANIO_INVALIDO` (400), `TIPO_DESCONOCIDO` (400),
`CAPA_DESCONOCIDA` (400), `COORDENADA_INVALIDA` (400), `FALTA_OBJETIVO` (400),
`FORMATO_NO_SOPORTADO` (400), `NOMBRE_EXPORTACION_INVALIDO` (400),
`EXPORTACION_BLOQUEADA` (400), `METODO_NO_PERMITIDO` (405),
`ERROR_INTERNO` (500).

> Nunca se devuelve una excepción de Python al cliente. El traceback se
> registra en el servidor y la respuesta es un error estructurado.

---

## Parámetros comunes

| Parámetro | Por defecto | Efecto |
|---|---|---|
| `limit` | 50 (200 en fichas) | Filas devueltas. **Tope duro: 500.** |
| `offset` | 0 | Paginación. Valores absurdos se normalizan. |

Un `limit=999999999` no rompe nada: se acota a 500 y la respuesta declara el
`limit` aplicado y `truncado: true`.

---

## Metadatos

| Endpoint | Devuelve |
|---|---|
| `GET /api` | Nombre, versión y lista de endpoints |
| `GET /api/salud` | Estado, ruta de datos, `export_root`, límite máximo y **dataset activo** |
| `GET /api/stats` | Conteos reales del mundo |
| `GET /api/limitaciones` | Limitaciones **con su cifra medida** y el motivo |

`/api/stats` ejemplo:

```json
{ "figuras": 11144, "entidades": 1067, "sitios": 734, "eventos": 57215,
  "artefactos": 427, "relaciones": 13192, "rios": 2346, "masas_tierra": 40,
  "picos": 4, "construcciones_mundo": 122, "anio_min": 1, "anio_max": 100 }
```

### El dataset activo

`/api/salud` incluye un bloque `dataset` que dice **qué mundo se está
sirviendo ahora**:

```json
{
  "data": {
    "estado": "ok",
    "dataset": {
      "dataset_id": "v1-04170363943d4ba1",
      "dataset_generado": "2026-10-03T03:24:16.109+02:00",
      "conteos": { "figuras": 11144, "entidades": 1067, "sitios": 734,
                   "eventos": 57215, "artefactos": 427, "anios": [1, 100] },
      "certainty": "FACT"
    }
  }
}
```

| Campo | Significado |
|---|---|
| `dataset_id` | `v1-<16 hex>`, **derivado del contenido** del dataset, no de un reloj |
| `dataset_generado` | Fecha real de la activación (`dataset_version.json`) |
| `conteos` | Conteos del dataset, no del índice en memoria |
| `certainty` | `FACT` con identificador; `UNKNOWN` si no se puede determinar |
| `motivo` | Por qué es `UNKNOWN`, cuando lo es |

Se lee **del disco** en cada llamada, a propósito: así refleja lo que está
activado ahora, que es lo que la Web necesita para detectar un cambio.

Reglas:

- **Determinista**: el mismo contenido da siempre el mismo id.
- **Sin invenciones**: si no hay registro, se declara `UNKNOWN` con motivo.
  Nunca se rellenan fecha ni id.
- **Los campos antiguos no cambian**: `dataset` es puramente aditivo.
- **No acepta rutas**: no existe ningún parámetro que elija dataset o fichero.

Ninguna cifra está escrita a mano: todas se cuentan en el índice cargado.

---

## Búsqueda

| Endpoint | Notas |
|---|---|
| `GET /api/buscar?q=` | Global; devuelve un grupo por tipo con su total |
| `GET /api/figuras?q=` | Atajo de búsqueda de figuras |
| `GET /api/entidades?q=` | Atajo de entidades |
| `GET /api/sitios?q=` | Atajo de sitios |
| `GET /api/artefactos?q=` | Atajo de artefactos |

Parámetro `tipo=` en `/api/buscar`: `figuras`, `entidades`, `sitios`,
`artefactos` o `eventos`.

Las coincidencias múltiples **no se resuelven**: la respuesta incluye
`consulta_ambigua: true` y el cliente decide.

```bash
curl "http://127.0.0.1:877/api/buscar?q=galka%20shafttop&tipo=figuras"
```

---

## Listados

`GET /api/listar/{tipo}?limit=&offset=`

`tipo` ∈ `historical_figures`, `entities`, `sites`, `artifacts`.
Devuelve fichas breves ordenadas por ID numérico.

---

## Figuras

| Endpoint | Devuelve |
|---|---|
| `GET /api/figuras/{id}` | Ficha completa: identidad, entidad, sitio, eventos, cronología, relaciones, artefactos |
| `GET /api/figuras/{id}/eventos` | Eventos de la figura (FACT) |
| `GET /api/figuras/{id}/cronologia` | Línea temporal en el orden validado |
| `GET /api/figuras/{id}/relaciones?tipo=` | Relaciones sociales, con `nota_grafo` |
| `GET /api/figuras/{id}/artefactos` | Artefactos vinculados por `holder_hfid` |
| `GET /api/figuras/{id}/identidad` | Identidad asociada o UNKNOWN |

```bash
curl "http://127.0.0.1:877/api/figuras/712"
```

Campos clave: `nombre`, `race`, `caste`, `sexo`, `nacimiento`, `muerte`,
`entidad`, `sitio`, `acontecimientos`, `cronologia`.

`muerte` sin `death_year` devuelve `certainty: UNKNOWN` y una lista

---

## Entidades

| Endpoint | Devuelve |
|---|---|
| `GET /api/entidades/{id}` | Ficha con figuras, sitios, eventos y cronología |
| `GET /api/entidades/{id}/miembros` | Miembros (FACT vía `entity_link`) |
| `GET /api/entidades/{id}/sitios` | Sitios por `civ_id` / `cur_owner_id` |
| `GET /api/entidades/{id}/eventos` | Eventos de la entidad |
| `GET /api/entidades/{id}/cronologia` | Línea temporal |

```bash
curl "http://127.0.0.1:877/api/entidades/282/miembros"    # 25 miembros
```

---

## Sitios

| Endpoint | Devuelve |
|---|---|
| `GET /api/sitios/{id}` | Ficha completa |
| `GET /api/sitios/{id}/eventos` | Eventos del sitio |
| `GET /api/sitios/{id}/cronologia` | Línea temporal |
| `GET /api/sitios/{id}/figuras` | Figuras asociadas |

`tipo` conserva el **tipo real de Dwarf Fortress** (`fortress`, `town`,
`cave`, …). `tipo_registro` vale siempre `site`. Si un sitio no tiene eventos
registrados, `certainty_eventos` pasa a `UNKNOWN` con la nota
«no significa que no ocurriera ninguno».

```bash
curl "http://127.0.0.1:877/api/sitios/87"
# tipo: "fortress"   tipo_registro: "site"   coordenadas: [[112,20]]
```

---

## Artefactos

| Endpoint | Devuelve |
|---|---|
| `GET /api/artefactos/{id}` | Ficha: tipo, material, propietario, sitio, creador |
| `GET /api/artefactos/{id}/propietarios` | Propietario declarado (`holder_hfid`) |
| `GET /api/artefactos/{id}/eventos` | Eventos que mencionan el artefacto |

El **creador** es DERIVED por un método explícito: se toma del evento
`artifact created` y se declara en el campo `metodo`.

---

## Eventos

| Endpoint | Devuelve |
|---|---|
| `GET /api/eventos/{id}` | Ficha completa con participantes y relaciones |
| `GET /api/eventos/{id}/participantes` | Figura principal, objetivo y grupos |
| `GET /api/eventos/tipos` | Tipos literales del XML con su recuento (90 tipos) |

### Filtros de `GET /api/eventos`

| Parámetro | Alias | Significado |
|---|---|---|
| `year` | `anio` | Año exacto |
| `from` | `desde` | Año inicial (inclusive) |
| `to` | `hasta` | Año final (inclusive) |
| `type` | `tipo` | Tipo literal del XML |
| `figure` | `figura` | ID de figura |
| `site` | `sitio` | ID de sitio |
| `entity` | `entidad` | ID de entidad |

Los filtros **se combinan**: `?from=1&to=3&figure=712` devuelve solo los
eventos de esa figura en ese rango, no todos sus eventos.

```bash
curl "http://127.0.0.1:877/api/eventos?year=5&limit=10"
curl "http://127.0.0.1:877/api/eventos?from=1&to=20&type=hf%20died"
curl "http://127.0.0.1:877/api/eventos?site=87&limit=5"
```

Un año que no es entero devuelve `400 ANIO_INVALIDO`. Un año fuera de rango
devuelve `200` con cero resultados: no es un error, es una ausencia.

---

## Relaciones

| Endpoint | Devuelve |
|---|---|
| `GET /api/figuras/{id}/relaciones?tipo=&limit=` | Relaciones de una figura |
| `GET /api/relaciones/tipos` | Tipos literales del XML con su recuento (12 tipos) |

Cada relación incluye `tipo`, `año`, `otra_figura_id`, `otra_figura_nombre`,
`evento_id`, `evento_existe` y `certainty`.

> **El grafo es dirigido.** Que A tenga relación con B no implica la inversa.
> La respuesta incluye `nota_grafo` para que ninguna interfaz lo presente como
> simétrico.

Los 13.192 registros de `historical_event_relationships` citan eventos que **no
existen** en `historical_events`: se conservan con `evento_existe: false` y una
nota explicando que no hay evento asociado.

---

## Conflictos (DERIVED)

`GET /api/conflictos?limit=`

Agrupa eventos `hf simple battle event` por subtipo.

* `certainty`: **DERIVED**
* `total_encontrados`: 5.478
* `por_subtipo_total`: recuento sobre **todo** el conjunto, sin límite
* `advertencia`: «esto NO demuestra guerras. El XML no contiene una tabla de
  guerras»

> No existe una entidad `WAR`. Cualquier agrupación de guerras sería DERIVED,
> y así se declara.

---

## Geografía

| Endpoint | Devuelve |
|---|---|
| `GET /api/geografia` | Resumen de las 4 capas |
| `GET /api/geografia/{capa}?limit=&offset=` | Elementos de una capa |
| `GET /api/geografia/construcciones/{x}/{y}` | Construcciones en un punto (DERIVED) |
| `GET /api/geografia?x=&y=` | Geografía del punto exacto |
| `GET /api/geografia/punto/{x}/{y}` | Igual, con ruta explícita |
| `GET /api/geografia/area/{x}/{y}?ancho=&alto=` | Sitios de un rectángulo (viewport del mapa) |
| `GET /api/sitios?x=&y=` | Sitios cuya coordenada coincide con el punto |

`capa` ∈ `rivers` (2.346), `landmasses` (40), `mountain_peaks` (4),
`world_constructions` (122).

Los ríos **no tienen id en el XML**: su `df_id` es un hash DERIVED del
contenido, y la respuesta lo declara en `nota_derivada`.

### Coordenadas

`x` e `y` son las **world coordinates** de Dwarf Fortress: un parche del mapa
global. Se aceptan enteros en **0–65535** (16 bits por eje); fuera de ese rango
la API responde `400 COORDENADA_INVALIDA` diciendo qué valor recibió.

**No hay Z.** Ningún campo de ningún XML contiene altura, así que `z` se
devuelve siempre como `null` y la respuesta lo declara en
`data.coordenadas.z`. No se inventa ni se estima.

`/api/geografia` con `?x=&y=` **filtra de verdad**. Antes ignoraba esos
parámetros en silencio y devolvía el resumen completo; ahora, si falta uno de
los dos, responde `400` nombrando el que falta.

### La coincidencia es EXACTA

Todos estos enlaces son por **coincidencia exacta del parche (x, y)**. Cada
respuesta lo declara en `data.coordenadas.metodo`. Dos registros que comparten
parche **no** están relacionados entre sí: la respuesta separa `certainty:
FACT` (la posición) de `certainty_enlace: DERIVED` (el vínculo).

---

## Exportación

`GET /api/exportar?format=&figura=&entidad=&sitio=&nombre=&escribir=`

| Parámetro | Valores |
|---|---|
| `format` | `json` (por defecto) o `markdown` |
| `figura` / `entidad` / `sitio` | ID (obligatorio uno) |
| `nombre` | Nombre del fichero, **solo si** `escribir=1` |
| `escribir` | `1` para guardar en disco; por defecto devuelve el texto |

Sin `escribir`, **no se toca el disco**: la respuesta trae `contenido`.

Con `escribir=1`, el fichero solo puede escribirse en
`00_SOURCE/exportes/`. Un `nombre` con separadores o `..` se rechaza con
`400 NOMBRE_EXPORTACION_INVALIDO`. Nunca se sobrescriben los XML originales
ni el dataset.

```bash
# Ver el JSON en el terminal
curl "http://127.0.0.1:877/api/exportar?figura=712&format=json"

# Guardar el Markdown en 00_SOURCE/exportes/
curl "http://127.0.0.1:877/api/exportar?figura=712&format=markdown&escribir=1&nombre=galka.md"
```

---

## Seguridad

* Escucha **solo en `127.0.0.1`** por defecto.
* **Solo `GET`**: no existe ningún endpoint que modifique datos.
* La UI se sirve desde `dfchron/web/`, con la ruta resuelta y **comprobada**
  contra el directorio antes de abrir el fichero.
* Cualquier ruta fuera de `/api/...` y `/static/...` devuelve `404`.
* El XML original **jamás** se sirve por HTTP.
* Los límites se acotan antes de tocar el núcleo.

Verificado por `dfchron/pruebas/probar_api.py` (clase `TestSeguridad`).

---

## Próxima etapa: web

Esta API es el contrato. Una web futura puede:

```
Navegador
   ↓  fetch() a /api/...
Web UI (los mismos index.html / app.js)
   ↓
dfchron.api
   ↓
nucleo.py
```

Basta con cambiar el origen del `fetch` en `app.js`. Ver `ARCHITECTURE.md`.

`interpretacion_prohibida` que impide leerlo como «sigue viva».
