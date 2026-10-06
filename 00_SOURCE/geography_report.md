# DF Legends · World Geography Explorer

**Estado: COMPLETADA CON LIMITACIONES.**

Todo lo que sigue procede de ejecución real: consultas a la API en vivo,
lectura del JSONL, navegación con Chrome y comprobación de hashes.

---

## Auditoría

Detalle completo en `geography_initial_audit.md`. Lo que existía **antes** de
tocar nada:

| Qué | Realidad medida |
|---|---|
| Sitios | **734**, el **100 %** con exactamente 1 coordenada |
| Rango observado | X **2–127**, Y **2–126** |
| Tipos de sitio | **23 reales**, preservados tal cual |
| Capas | ríos 2.346 · masas 40 · picos 4 · construcciones 122 |
| Z | **No existe en ningún XML** |

La geografía era **tabular**: había coordenadas, pero ninguna forma de
consultarlas. `/api/geografia` resumía las capas y
`/api/geografia/construcciones/{x}/{y}` filtraba construcciones, pero no existía
"dime qué hay en 112, 20".

### Tres defectos reales encontrados

1. **`/api/geografia?x=112&y=20` ignoraba los parámetros en silencio.** Devolvía
   el resumen completo, sin error. El cliente creía haber filtrado. El más
   peligroso, porque no se manifiesta.
2. **`/api/sitios?x=112&y=20` respondía `"el texto de busqueda esta vacio"`.**
   El endpoint no entendía coordenadas; el mensaje no llevaba a ninguna parte.
3. **`/api/sitios/abc/geografia` respondía 404** en vez de 400: no distingue
   "no existe" de "esto no es un identificador".

Los tres están corregidos y cubiertos por pruebas de regresión.

## Modelo

X e Y son **world coordinates** de Dwarf Fortress: un parche del mapa global,
enteros no negativos. Formato en el XML: `"112,20"`, y para ríos y
construcciones una polilínea `"126,14|125,14|…"`.

**Z no existe.** Se devuelve `null` y la propia API declara por qué
(`"NO EXISTE en los datos de Legends"`). La UI lo muestra como `UNKNOWN`. No se
inventa ni se estima en ningún sitio.

## Endpoints

| Endpoint | Respuesta |
|---|---|
| `GET /api/geografia` | Resumen de las 4 capas |
| `GET /api/geografia?x=&y=` | **Nuevo.** Geografía del punto exacto |
| `GET /api/geografia/punto/{x}/{y}` | **Nuevo.** Igual, con ruta explícita |
| `GET /api/geografia/area/{x}/{y}?ancho=&alto=` | **Nuevo.** Sitios de un rectángulo |
| `GET /api/geografia/{capa}` | Listado paginado (sin cambios) |
| `GET /api/geografia/construcciones/{x}/{y}` | Construcciones (sin cambios) |
| `GET /api/sitios/{id}` | Ficha con tipo real (sin cambios) |
| `GET /api/sitios/{id}/geografia` | Construcciones del sitio (sin cambios) |
| `GET /api/sitios?x=&y=` | **Nuevo.** Sitios en esa coordenada |

Validación: rango **0–65535** (16 bits por eje, el tipo de dato de DF) y área
máxima **256×256**. Fuera de eso, 400 con el motivo exacto.
## Datos

Lo que DF Legends puede mostrar, todo leído del XML:

- Coordenadas de los 734 sitios, con su **tipo real** (`fortress`, `dark
  fortress`, `mysterious lair`…), nunca colapsados a `site`.
- Las 4 capas geográficas en el punto consultado, con su polilínea real.
- Un mapa de puntos, cada uno navegable a su ficha.
- La historia de un sitio: eventos, figuras y entidades desde su ficha.

Lo que **no** se muestra y no se inventa: alturas, distancias, fronteras,
continentes, océanos, costas y cualquier relación entre dos sitios distintos.

## Limitaciones

| Limitación | Por qué |
|---|---|
| No hay Z | No está en los datos |
| No hay "cercanía" | Solo coincidencia **exacta** de parche. Calcular una distancia sería inventar una métrica que el archivo no define. El método se declara en cada respuesta. |
| Dos sitios en el mismo parche **no** se muestran como relacionados | Compartir posición no es relación. El enlace se marca `DERIVED` en todas partes. |
| El mapa no dibuja terreno | No hay datos de terreno. Un fondo geográfico sería inventado. |
| Sin Leaflet/Mapbox | La auditoría no lo justificó: el objetivo era validar el modelo. El renderer está aislado para poder añadirlo después. |
| Carga inicial de la API | 2,6 s, sin cambios respecto a antes |

## UI

**`Geography`** (`/app/geography`) ahora es un explorador real:

- **Formulario X / Y** que escribe en la URL: `/app/geography?x=112&y=20`.
  Compartible y sobrevive a la recarga.
- **Panel del punto**: X, Y, Z y el método, con su certeza visible; sitios con
  su tipo real; las capas que tocan ese parche.
- **Mapa SVG**: un punto por sitio, glifo según su tipo real, leyenda de los
  tipos presentes y navegación de viewport (← ↑ ↓ →, ampliar, mundo entero).
- Cada punto es un enlace a su ficha.
- Se conserva el listado por capas que ya existía.

Datos y dibujo están **separados**: `lib/geografia.ts` pide y traduce,
`lib/mapa.ts` dibuja. Pasar a un mapa interactivo es reescribir `renderMapa()`
y nada más.

## Tests

### API (`dfchron/pruebas/probar_geografia.py`) — 41/41

Sitios (5) · Coordenadas (11) · Construcciones (4) · Integridad de tipos (5) ·
Área (5) · Adversarial (5) · Datos reales (4) · Integridad de datos (3).

Incluye los adversariales exigidos: `%2e%2e`, `..`, `null`, `NaN`, `Infinity`,
Unicode, valores de 10²³, parámetros repetidos y métodos de escritura. Ninguno
produce 500 ni filtra un traceback.

### Navegador (`dfchron/site/pruebas_geografia.mjs`) — 57/57

Chrome real vía Playwright. **233 puntos navegables** en el mapa del mundo;
`(112,20)` devuelve la fortaleza `halesteel` con tipo `fortress`; el formulario
navega de verdad; mapa → sitio → figuras (48 enlaces) → eventos (50 enlaces) →
atrás; un punto vacío lo dice sin inventar; solo se habla con la API, sin XML ni
JSONL.

### Regresión — 269/269, sin pérdidas

| Suite | Resultado |
|---|---|
| Núcleo | 48/48 |
| Integración | 20/20 |
| Adversarial | 39/39 |
| API | 54/54 |
| Web | 65/65 |
| Actualización manual | 43/43 |
| **Geografía (nueva)** | **41/41** |
| **Navegador (nueva)** | **57/57** |

Determinismo y reproducibilidad: **OK**. El índice de coordenadas se comparó
contra un recorrido lineal completo: **idéntico** (678 parches, 734 sitios).
## Responsive

Las 9 resoluciones, medidas en navegador real, sobre cajas reales:

| Ancho | Scroll horizontal | Botón mapa | Campo X | Mapa |
|---:|---|---|---|---|
| 320 | Ninguno | 37×34 px | 120×40 px | 249 ≤ 320 |
| 360 | Ninguno | 45×34 px | 140×40 px | 289 ≤ 360 |
| 390 | Ninguno | 51×34 px | 155×40 px | 319 ≤ 390 |
| 414 | Ninguno | 34×34 px | 167×40 px | 343 ≤ 414 |
| 600 | Ninguno | 62×34 px | 252×40 px | 514 ≤ 600 |
| 768 | Ninguno | 32×34 px | 120×40 px | 659 ≤ 768 |
| 1024 | Ninguno | 32×34 px | 120×40 px | 891 ≤ 1024 |
| 1280 | Ninguno | 32×34 px | 120×40 px | 987 ≤ 1280 |
| 1440 | Ninguno | 32×34 px | 120×40 px | 987 ≤ 1440 |

Ningún botón por debajo de 28×28 px ni ningún campo por debajo de 36 px de alto.
Capturas en `00_SOURCE/informes/fase5/`.

## Integridad

| Fichero | Antes | Después |
|---|---|---|
| `legends.xml` | `77DB4739…85A4681F` | **idéntico** |
| `legends_plus.xml` | `FB6BE93D…194ABC2D` | **idéntico** |
| 20 JSONL de `processed/merged` | manifestados | **byte-idénticos** |

Además, la propia suite verifica que servir geografía **no escribe nada**: toma
una huella SHA-256 de `processed/` + los XML antes y después de las peticiones y
las compara.

## Problemas encontrados

Todos reales, todos corregidos:

| # | Problema | Gravedad | Corrección |
|---|---|---|---|
| 1 | `/api/geografia?x=&y=` ignoraba los parámetros **en silencio** | **Alta** | Rama explícita: con `x` e `y` devuelve el punto; si falta alguno, 400 nombrándolo |
| 2 | `/api/sitios?x=&y=` daba `"el texto de busqueda esta vacio"` | Media | Mensaje que dice qué falta y por qué |
| 3 | `/api/sitios/{id}/geografia` con id no numérico daba 404 | Baja | El envelope ya distingue; se documenta 404 = no existe, 400 = mal formado |
| 4 | **500 en `/api/sitios?x=`**, fallo mío | **Alta** | `_peticion` invoca `f(params, q)` con dos argumentos; mi función aceptaba uno. Firma corregida. Lo detectó la prueba, no el compilador. |
| 5 | `num` ya existía en `listados.ts` | Media | El build lo dijo (`Identifier num has already been declared`). Renombrado a `enteroDe`. |
| 6 | Tipos con espacios sin comillas en el mapa (`dark pits: '○'`) | Media | Build detectado. Claves entrecomilladas; los 23 tipos reales tienen glifo. |
| 7 | **Hash de `legends_plus.xml` mal transcrito en mi test** | **Alta** | El test falló contra un XML **intacto**: mi constante tenía un carácter de menos. Corregida contra el hash registrado al inicio. |
| 8 | Un `waitForSelector` abortaba toda la auditoría E2E | Media | Cada bloque va en `bloque()`, que registra la excepción y sigue. Un fallo ya no oculta los pasos siguientes. |
| 9 | Build sin `PUBLIC_API_BASE_URL` servía "Data unavailable" | Baja | Se verifica el bundle antes de auditar. |

Los tres primeros eran **preexistentes**. El 4 y el 7 los cometí yo en esta fase
y los encontraron las pruebas, que es justo para lo que existen.

## Criterio de aceptación

Recorrido verificado con clics reales:

```
Geography → 112,20 → "halesteel" FORTRESS → ficha
   → 48 figuras · 50 eventos → volver al mapa
```

Y en un punto vacío: *"Nothing is recorded at this coordinate. That does not mean
nothing existed there: it means the file does not say."*

## Deuda técnica registrada

- La API debe reiniciarse para cargar datos activados por `actualizar_datos.py`
  (heredado, no introducido aquí).
- `probar_integracion.py` fija conteos del mundo actual: hay que revisarlo al
  cambiar de partida.
- `backups/` crece sin limpieza automática.