# Arquitectura de DF-Chronicles

## La cadena completa

```
                    Dwarf Fortress
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
   legends.xml                     legends_plus.xml
   49.223.702 B                   17.664.819 B
   CP437, fuente primaria          UTF-8, complementaria
        │                                   │
        └───────────────┬───────────────────┘
                        ↓  NUNCA se modifican
        ┌───────────────────────────────┐
        │  00_SOURCE/original_data/     │  solo lectura, SHA-256 verificado
        └───────────────┬───────────────┘
                        ↓
                   EXTRACCIÓN
     cargar_legends.py   autodetección de codificación,
                         saneado de bytes de control, parseo XML
                        ↓
                   NORMALIZACIÓN
     integrar_legends.py  fusión con procedencia por campo,
                         sin descartar ningún valor
                        ↓
        ┌────────────────────────────────────────┐
        │  00_SOURCE/processed/merged/*.jsonl    │  20 secciones
        │  + _manifiesto.json                    │  solo lectura
        └───────────────────┬────────────────────┘
                            ↓
                       VALIDACIÓN
     validar_semantica.py  Indice + Consultas,
                           comprobación de referencias
                            ↓
                         NÚCLEO
     nucleo.py  Archivo: búsqueda, fichas, cronología,
                relaciones, geografía, exportación
                            ↓
                      SERVICIO
     dfchron/servicio.py   envelopes, límites, errores
                            ↓
                     ┌──────┴──────┐
                     ↓             ↓
                   API           UI
     dfchron/api.py          dfchron/web/
     HTTP (stdlib)          fetch() -> /api/...
                     ↓
              FUTURA WEB (misma API)
```

---

## Las cinco reglas que sostienen el diseño

### 1. La UI nunca lee los XML

`dfchron/web/app.js` no contiene una sola referencia a `legends.xml`, a
`.jsonl` ni a `original_data/`. Habla **solo** con `/api/...` mediante
`fetch()`. Lo comprueba una prueba automática
(`test_la_ui_no_accede_a_los_xml`).

**Por qué importa:** si la UI leyera los datos, cada pantalla tendría su
propia lógica. Cambiar un campo obligaría a tocar JavaScript, y la UI web
futura no podría reutilizar nada.

### 2. La API nunca implementa lógica de Dwarf Fortress

`dfchron/api.py` traduce rutas HTTP en llamadas a `servicio.py`, y nada más.
No sabe qué es una figura ni qué es un sitio. Toda la lógica de dominio está
en `nucleo.py`.

### 3. El servicio es el único que conoce el formato de la respuesta

`envolver_lista()` y `envolver_ficha()` son las **únicas** funciones que
construyen envelopes. Así, la UI local y una futura UI web reciben objetos
idénticos.

### 4. El núcleo no sabe nada de rutas absolutas

`00_SOURCE/tools/rutas.py` resuelve `PROJECT_ROOT`, `DATA_ROOT`,
`ORIGINAL_DATA_ROOT`, `PROCESSED_ROOT`, `MERGED_ROOT` y `EXPORT_ROOT` a
partir de `__file__` o de la variable `DFCHRON_ROOT`.

**Por qué importa:** el proyecto funciona desde cualquier carpeta y se puede
mover sin editar código.

### 5. Ningún recorte es silencioso

Toda lista pasa por `envolver_lista()`, que siempre calcula
`truncado = (offset + devueltos) < total_encontrados`. La UI lo pinta como
aviso. No existe forma de recortar en silencio por la API.

---

## Las tres capas de certeza

| Nivel | Significado | Ejemplo |
|---|---|---|
| **FACT** | Está en el XML | `halesteel` es `fortress` en (112, 20) |
| **DERIVED** | Calculado con una regla declarada | Agrupar 5.478 `hf simple battle event` |
| **UNKNOWN** | No se puede determinar | La era histórica (`start_year = -1`) |

`DERIVED` siempre viaja con su `metodo` o su `regla`, para que sea auditable:

```json
{ "construcciones": [...],
  "certainty": "DERIVED",
  "metodo": "coordenada exacta compartida" }
```

`UNKNOWN` nunca se convierte en suposición. La ausencia de `death_year` es
`UNKNOWN`, e incluye `interpretacion_prohibida` para que ninguna interfaz lo
lea como «sigue viva».

---

## Por qué JSONL y no una base de datos

Ver `08_DATABASE/decision_storage.md`. Resumen: el dataset son 20 ficheros de
texto plano que ya son la fuente de verdad, se versionan, se verifican por
hash y se reconstruyen byte a byte desde los XML. Una base de datos añadiría
una dependencia que no aporta nada a un archivo de **una sola partida** que
se consulta en local.

---

## Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| `http.server` (stdlib) | Flask, FastAPI | Cero dependencias: `pip install` es una barrera y un riesgo en un equipo local. |
| JavaScript plano | React, Vue | Sin `node_modules`, sin build. La UI se lee de un vistazo. |
| Envelopes en el servicio | En la API | La UI web recibiría otro formato y habría que duplicar la lógica. |
| Paginación `limit`/`offset` | Traer todo | 57.215 eventos en una respuesta no es viable. |
| `EXPORT_ROOT` separado | Escribir junto a los datos | Un export nunca puede contaminar el dataset. |

---

## Capas de protección de datos

```
original_data/   ─┐
processed/        ├─ RUTAS_SOLO_LECTURA ── rutas.es_ruta_protegida() ── aborta
validation/      ─┘
        │
        ├─ Ningún endpoint de escritura. POST/PUT/DELETE → 405.
        ├─ El export solo puede escribir en EXPORT_ROOT.
        └─ La UI se sirve comprobando la ruta real contra web/.
```

`rutas.py` declara `RUTAS_SOLO_LECTURA` y `es_ruta_protegida()`. La prueba
`test_export_no_puede_salir_de_exports` intenta cinco vectores de path
traversal y todos se rechazan con `400`.

---

## Verificación

| Suite | Cubre |
|---|---|
| `probar_integracion.py` (20) | Lectura, codificación, conteos, merge, integridad |
| `probar_nucleo.py` (48) | Valores concretos de fichas, referencias cruzadas, orden, exportación |
| `probar_adversarial.py` (39) | IDs hostiles, `death_year` ausente, grafo dirigido, truncamientos, solo lectura, hashes |
| `probar_api.py` (54) | API real por HTTP, errores, seguridad, UI, integridad |
| `test_determinismo.py` | 29 consultas × 4 procesos con `PYTHONHASHSEED` distinto |
| `verificar_reproducibilidad.py` | Reconstruye el pipeline desde los XML en un temporal y compara hashes |

---

## Cómo añadir una web futura

La UI actual **ya es una web**: HTML + JS plano que habla por HTTP. Para
servirla desde otro sitio:

```
Navegador
   │
   ↓  GET https://tu-servidor/
Web UI  (los MISMOS index.html y app.js)
   │
   ↓  fetch('https://tu-servidor/api/...')
API HTTP  (dfchron/api.py, sin cambios)
   │
   ↓
dfchron.servicio
   │
   ↓
nucleo.py
```

Los cambios necesarios son mínimos:

1. **Servir los estáticos** desde el mismo origen que la API (o añadir CORS).
2. **Apuntar el `fetch`** al origen correcto. En `app.js` el `api()` ya es el
   único punto de contacto:

   ```js
   async function api(ruta) {
     const r = await fetch(ruta, { ... });
   }
   ```

   Basta cambiar la ruta a absoluta si la UI y la API están en dominios
   distintos.
3. **Añadir autenticación** si se expone fuera de la máquina. La API actual no
   la tiene, y está pensada para `127.0.0.1`.

Lo que **no** hay que tocar: `nucleo.py`, `servicio.py`, los JSONL ni los XML.
Por eso el núcleo es agnóstico de la forma de la respuesta: es lo que permite
que la capa de presentación cambie sin arrastrar la lógica de dominio.

---

## Mapa de responsabilidades

| Fichero | Responde de | NO sabe de |
|---|---|---|
| `00_SOURCE/tools/rutas.py` | dónde vive cada carpeta | Dwarf Fortress |
| `cargar_legends.py` | leer XML con su codificación | el mundo histórico |
| `integrar_legends.py` | fusionar dos exports sin perder datos | consultas |
| `validar_semantica.py` | índices y validación de referencias | HTTP, UI |
| `nucleo.py` | qué se puede saber del mundo | HTTP, formatos de respuesta |
| `dfchron/servicio.py` | forma de las respuestas, límites, errores | Dwarf Fortress |
| `dfchron/api.py` | rutas HTTP | qué es una figura o un sitio |
| `dfchron/web/*` | cómo se ve | qué significa un evento |
| `run.py` | arranque | nada: solo orquesta |

| Rutas relativas a `__file__` | Rutas absolutas | El proyecto se puede mover. |
