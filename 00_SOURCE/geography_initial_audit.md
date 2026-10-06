# DF Legends · Auditoría inicial de geografía

Auditoría **ejecutada antes de modificar nada**. Todas las cifras y respuestas
de este documento proceden de consultas reales contra `127.0.0.1:877` y de la
lectura del JSONL, no de supuestos.

---

## 1. Qué información geográfica existe REALMENTE

### 1.1 Capas geográficas

| Capa | Registros | Formato de coordenadas | Coord. por registro |
|---|---:|---|---|
| `rivers` | 2.346 | `path` → `x,y\|x,y\|x,y\|` (polilínea) | muchas |
| `landmasses` | 40 | `coord_1` → `x,y` | 1 |
| `mountain_peaks` | 4 | `coords` → `x,y` | 1 |
| `world_constructions` | 122 | `coords` → `x,y\|x,y\|…` (polilínea) | muchas |

### 1.2 Sitios

Medido recorriendo los 734 sitios vía `/api/listar/sites`:

| Dato | Resultado |
|---|---|
| Sitios totales | **734** |
| Sitios **con** coordenadas | **734** (el 100 %) |
| Sitios **sin** coordenadas | **0** |
| Pares de coordenadas por sitio | exactamente **1** |
| Rango X observado | **2 … 127** |
| Rango Y observado | **2 … 126** |

Los 23 tipos reales que aparecen (**se conservan tal cual, nunca colapsan a
`site`**):

```
camp, castle, cave, dark fortress, dark pits, forest retreat, fort, fortress,
hamlet, hillocks, labyrinth, lair, monastery, mountain halls,
mysterious dungeon, mysterious lair, mysterious palace, shrine, tomb, tower,
town, vault
```

### 1.3 Eventos ligados a un lugar

Los eventos tienen `site_id` (el sitio 87 concentra 1.546). Este es el **único**
enlace fiable entre un lugar y su historia: no existe ninguna relación
"cercana" en los datos.

---

## 2. Semántica real de X e Y

| Aspecto | Realidad en los datos |
|---|---|
| Qué son | **World coordinates** de Dwarf Fortress: parche del mapa global |
| Formato en el XML | `"112,20"`, o polilínea `"126,14\|125,14\|…"` |
| Tipo | Dos enteros **no negativos** |
| **Z / altura** | **No existe.** Ningún campo de ningún XML contiene Z |
| Centinela | `-1,-1` significa "sin posición" y se descarta |
| Filtrado | `coords_primeras()` descarta negativos y no numéricos |

**Consecuencia para el contrato:** `z` se expone siempre como `null`, con la
ausencia declarada como **FACT**. **No se inventa.**

---

## 3. Endpoints que existen

| Endpoint | Estado real | Veredicto |
|---|---|---|
| `GET /api/geografia` | Resumen de las 4 capas con ejemplos | Correcto |
| `GET /api/geografia` | Resumen de las 4 capas con ejemplos | Correcto |
| `GET /api/geografia/{capa}` | Listado paginado con coordenadas parseadas | Correcto |
| `GET /api/geografia/construcciones/{x}/{y}` | Construcciones cuya ruta pasa por el punto | Correcto (`DERIVED`) |
| `GET /api/sitios/{id}` | Ficha con tipo real y coordenadas | Correcto |
| `GET /api/sitios/{id}/geografia` | Construcciones del sitio, con `coordenadas_comunes` | Correcto (`DERIVED`) |

`/api/sitios/{id}/geografia` está **bien implementado**: no inventa una capa,
reutiliza la coincidencia exacta de coordenadas, declara su método
(`"coincidencia exacta de coordenadas (x, y)"`), marca `DERIVED` y devuelve
`UNKNOWN` con motivo si el sitio no tuviera coordenadas. **Se conserva tal cual,
y ahora cubierto por pruebas propias** (`test_geografia_de_sitio_sigue_funcionando`).

## 3-bis. Endpoints añadidos en esta fase

| Endpoint | Qué hace |
|---|---|
| `GET /api/geografia/punto/{x}/{y}` | Todo lo que el XML sitúa **exactamente** en el punto |
| `GET /api/geografia/area/{x}/{y}?ancho=&alto=` | Sitios dentro de un rectángulo (el viewport del mapa) |
| `GET /api/geografia?x=&y=` | **Arreglado**: antes ignoraba los parámetros en silencio |
| `GET /api/sitios?x=&y=` | **Arreglado**: antes daba un error engañoso |
---

## 4. Defectos encontrados en la API (antes de implementar)

### 4.1 `GET /api/geografia?x=112&y=20` ignora los parámetros EN SILENCIO

Comprobado: la respuesta es **idéntica** a `GET /api/geografia` sin parámetros.
Devuelve el resumen completo de las 4 capas y ni un error.

Es el más peligroso de los tres: un cliente cree que ha filtrado por
coordenada y en realidad ha recibido todo. **Fallo silencioso.**

### 4.2 `GET /api/sitios?x=112&y=20` devuelve un error engañoso

Responde `400 CONSULTA_VACIA — "el texto de busqueda esta vacio"`. No falta
texto: el endpoint **no entiende coordenadas**. El mensaje no lleva a la
solución.

### 4.3 `GET /api/sitios/abc/geografia` responde 404 en vez de 400

`'abc'` no es un ID, es un formato inválido. Distinguir ambos casos mejora el
diagnóstico sin romper a nadie: 404 = "no existe", 400 = "no puedes preguntar
esto".

---

## 5. Qué falta

| Necesidad | Estado |
|---|---|
| Consultar una coordenada y obtener todo lo que hay ahí | **Ausente** (y mal emulado: §4.1) |
| Sitios en una coordenada | **Ausente** |
| Sitios en un área (para dibujar un mapa) | **Ausente** |
| Eventos en un lugar | **Ausente** (`/api/sitios/{id}/eventos` sí existe, por sitio) |
| Eventos en una coordenada suelta | **Ausente** |
| Cualquier representación visual | **Ausente** |

---

## 6. ¿Basta lo que hay?

| Pregunta | Respuesta |
|---|---|
| ¿La información existe en los datos? | **Sí**, completa: 734 sitios con posición exacta |
| ¿Existe ya una función reutilizable? | **No**. Solo `construir_en_coordenada()`, que cubre solo `world_constructions` |
| ¿Puede la API actual exponerlo? | **No**, sin tocar nada (§4.1 lo demuestra) |

**Conclusión: hay que ampliar, y el sitio correcto es el núcleo**, porque ya
tiene el patrón (`construir_en_coordenada`) y ya construye índices DERIVED en
`Archivo.__init__` (`ev_por_artefacto`, `eventos_por_anio`).

Ampliación propuesta, mínima y reutilizable:

- `Archivo._geo_por_coordenada`: índice `(x, y) → registros`. DERIVED.
- `geografia_en_coordenada(x, y)`: qué hay en un punto exacto.
- `geografia_en_area(x, y, ancho, alto)`: qué hay en un rectángulo (mapa).

---

## 7. Qué NO se puede mostrar (y no se inventará)

| No existe | Por tanto |
|---|---|
| Altura Z | `z: null` |
| Fronteras, continentes, océanos | No se dibujan |
| Ríos como cauce continuo navegable | Se muestran sus puntos reales; no un trazo inventado |
| "Sitios cercanos" por distancia | Solo coincidencia **exacta**, salvo que se defina y documente una distancia |
| Relaciones entre sitios distintos | No existen en los datos |

---

## 8. Clasificación de certeza

| Dato | Certeza | Motivo |
|---|---|---|
| Coordenadas de un sitio | **FACT** | Leídas del XML |
| Tipo de sitio | **FACT** | Leído del XML |
| Nombre de construcción / río / masa / pico | **FACT** | Leído del XML |
| Punto de un río | **FACT** | Leído del XML |
| `df_id` de los ríos | **DERIVED** | El XML no asigna `<id>`; es un hash del contenido |
| Construcción que pasa por (x, y) | **DERIVED** | Inferida por coincidencia exacta |
| Índice de coordenadas | **DERIVED** | Construido en memoria a partir de FACT |
| Z | **UNKNOWN** | No existe en los datos |