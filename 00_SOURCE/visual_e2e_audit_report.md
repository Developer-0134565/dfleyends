# DF Legends :: auditoría visual y pruebas end-to-end (Fase 3)

Auditoría de la aplicación web en **navegador real**. Todo lo que sigue procede
de ejecuciones comprobables: capturas PNG, medidas de `getBoundingClientRect()`,
clics reales con Playwright y peticiones HTTP observadas.

**Estado: COMPLETADA CON LIMITACIONES** (ver §11).

---

## 1. Resumen

Se auditó la aplicación en los 5 tamaños exigidos y en 13 rutas cada uno
(65 capturas), más un recorrido de navegación con clics reales, la
comprobación de la comunicación con la API, las rutas directas y el fallback
estático.

Resultado: **105 comprobaciones automáticas, 0 fallos**.

Se encontraron y corrigieron **3 defectos reales**:

| # | Defecto | Gravedad | Corrección |
|---|---|---|---|
| 1 | La API **bloqueaba** a la web por CORS (el puerto 4400 no estaba en la allowlist) | **Alta** — la app no cargaba datos | Puerto añadido a la allowlist |
| 2 | La etiqueta `RELATIONSHIPS` se partía como `RELATIONSHI / PS` | Media — defecto visual | Ancho mínimo y `word-break` en `.stat-label` |
| 3 | `servidor_estatico.py` servía el fallback para **todas** las rutas, dejando la página sin CSS | Alta — impedía auditar el build público | `os.path.abspath()` en el directorio |

---

## 2. Herramientas y navegador

| Herramienta | Versión / detalle |
|---|---|
| Navegador | **Google Chrome** instalado en el sistema, modo `--headless=new` |
| Automatización | **Playwright 1.x** (`npm i -D playwright`), con `channel: 'chrome'` |
| Servidor de la web | `dfchron/pruebas/servidor_estatico.py` (nuevo) |
| API | `python run.py` en `127.0.0.1:877` |
| Node | v24.20.0 · npm 11.19.0 |

### Sobre las dependencias añadidas

Se añadió **una**: `playwright`, como `devDependency` de `dfchron/site/`.

Justificación: es la herramienta estándar de la industria para pruebas
end-to-end y auditorías visuales, y **no descarga ningún navegador**: se usa el
Chrome ya instalado mediante `channel: 'chrome'`. Son 2 paquetes y **no entra en
el bundle** que se despliega (`npm run build` no lo referencia). No se añadió
ninguna otra dependencia.

Sin ella solo se habría podido capturar cada URL por separado
(`chrome --screenshot`), sin poder hacer clic, escribir en el buscador, recargar
ni observar la red. La misión exige un recorrido con clics reales.

---

## 3. Capturas realizadas

Directorio: **`00_SOURCE/informes/fase3/`**

- **153 PNG** en total (acumulados de las varias ejecuciones realizadas).
- Cada captura lleva fecha y hora en el nombre; **no se sobrescribe ninguna**.
- Además se guarda `medidas_<timestamp>.json` con las medidas de cada ruta.

Nomenclatura: `NN_<tamaño>_<ruta>_<timestamp>.png`, p. ej.
`02_escritorio_dashboard_2026-10-02T23-47-44.png`.

La **ejecución final** produjo 65 capturas de la matriz (5 tamaños × 13 rutas),
más 5 capturas de verificación: `prueba_chrome`, `verificacion_cors`,
`verif_stats_1440`, `build_publico_sin_api` y `build_publico_sin_api_ok`.

Las 13 rutas auditadas en cada tamaño:

`/`, `/app/world`, `/app/figures`, `/app/entities`, `/app/sites`,
`/app/artifacts`, `/app/events`, `/app/timeline`, `/app/geography`,
`/app/search?q=halesteel`, `/figures/712`, `/sites/87`, `/entities/282`.

---
## 4. Resultado por tamaño de pantalla

Todos los tamaños se midieron con `scrollWidth` del documento frente a
`clientWidth` del viewport, y comparando el `getBoundingClientRect()` de **cada
elemento** del DOM.

| Tamaño | Rutas | Resultado |
|---|---|---|
| **Escritorio 1440×900** | 13 | Sin scroll horizontal, sin desbordes, sin texto cortado |
| **Portátil 1280×800** | 13 | Sin scroll horizontal, sin desbordes, sin texto cortado |
| **Tablet 768×1024** | 13 | Sin scroll horizontal, sin desbordes, sin texto cortado |
| **Móvil 390×844** | 13 | Sin scroll horizontal, sin desbordes, sin texto cortado |
| **Móvil pequeño 320×700** | 13 | Sin scroll horizontal, sin desbordes, sin texto cortado |

**65/65 correctas.** El caso más exigente (320 px) no genera barra horizontal.

### Qué se comprobó en cada ruta

- **Barras horizontales:** `documentElement.scrollWidth <= clientWidth`.
- **Desbordes:** ningún elemento visible se sale por la derecha del viewport.
- **Texto cortado:** elementos cuyo `scrollWidth` supera su `clientWidth` sin
  tener scroll declarado (etiquetas, títulos, definiciones).
- **Enlaces y botones utilizables:** altura mínima de 16 px.

**Identidad visual:** conservada en los cinco tamaños — fondo de piedra,
tipografía serif para títulos, latón en los acentos, monoespaciada para las
etiquetas. No se tocó la paleta ni las tipografías.

Las tablas anchas (eventos, artefactos) llevan scroll **propio y declarado**
dentro de `.tabla-scroll`; se comprobó que ese contenedor scrollea sin arrastrar
a la página.

---

## 5. Recorrido completo de navegación

Realizado con **clics reales**, no con URLs escritas a mano.

La cadena se verificó **contra la API antes de escribir el recorrido**, para no
elegir registros que no tuvieran relación:

```
figura 712 → evento 826 → sitio 111 ("faintflies", dark pits) → entidad 312
```

De los 158 eventos de la figura 712, **129 tienen sitio**; se eligió el primero
que lo tiene. No se inventó ninguna relación.

| Paso | Acción | Resultado |
|---|---|---|
| 1 | Abrir el dashboard | Cifras reales: 11.144 figuras, 57.215 eventos |
| 2 | Buscar `halesteel` (escribiendo y pulsando) | Declara ambigüedad, lista figuras y sitios |
| 3 | Buscar `galka shafttop`, abrir figura 712 | Ficha real en `/figures/712`, MINOTAUR |
| 4 | Clic en un evento **con sitio** | `/events/826` |
| 5 | Clic en el sitio relacionado | `/sites/111`, tipo `dark pits` **preservado** |
| 6 | Clic en la entidad relacionada | `/entities/312` |
| 7 | Volver atrás **dos veces** | Sigue pintando contenido en `/events/826` |
| 8 | Acceso directo a `/figures/712` | Datos reales |
| 9 | **Recargar** `/figures/712` | Correcto tras recargar |
| 10 | Abrir `/figures/712` en **pestaña nueva** | Correcto en contexto independiente |

**10/10 correctos.** La navegación encadenada funciona en ambos sentidos.

### Cambio de registro documentado

La figura 712 **sí** tenía sitio y entidad (vía el evento 826), así que se
mantuvo como registro principal. Se **descartó** el sitio 87 como punto de
partida del recorrido inicial porque un evento suyo puede no tener figura
asociada; sigue usándose para comprobar que se preserva el tipo `fortress`.

---

## 6. Resultado de las comprobaciones de API

Se observó **cada petición** que hacía el navegador y **cada respuesta** que
recibía la página.

| # | Comprobación | Resultado |
|---|---|---|
| 11 | Etiquetas `FACT` y `Unknown` visibles | Ambas presentes |
| 12 | `UNKNOWN` no se presenta como afirmación | Nacimiento y muerte: *Unknown*, sin fecha inventada |
| 13 | Truncamiento declarado | "Showing 50 of 11.144" |
| 14 | Filtro combinado | `from=1&to=3&figure=712` → **6** eventos, no los 158 |
| 15 | Paginación navegable | La página 2 carga datos distintos |
| 16 | Error de API | Mensaje claro, sin `undefined` en pantalla |
| 17 | Búsqueda sin resultados | Mensaje de vacío correcto |
| 18 | Ficha inexistente (`/figures/99999999`) | Avisa de que no existe |
| — | **Peticiones a servidores externos** | **Ninguna**: solo `127.0.0.1:4400` y `127.0.0.1:877` |

Los datos que llegan a pantalla son **reales**: 11.144 figuras, 1.067 entidades,
734 sitios, 57.215 eventos, 427 artefactos y 13.192 relaciones, coincidentes con
el XML.

### Pérdida de API simulada

Se bloquearon las peticiones a `**/api/**` desde el navegador (equivale a apagar
la API) y se comprobó el resultado: aparece

> **Data unavailable** — The API did not return world statistics: could not…

sin romperse la interfaz, sin `undefined` y sin errores de JavaScript.

---

## 7. Resultado de rutas directas y fallback

| Comprobación | Resultado |
|---|---|
| Acceso directo a `/figures/712` | Correcto (ruta limpia servida por el fallback) |
| Recarga de `/figures/712` | Correcto |
| Pestaña nueva con la misma ruta | Correcto |
| Navegación SPA entre vistas | Correcto |
| Ruta inexistente `/no/existe/esta/ruta` | El shell responde y avisa de que no existe |

### El problema de `astro preview` y su solución

`astro preview` sirve ficheros literales y devuelve **404** para
`/figures/712`, porque no aplica los `rewrites` ni el fallback. El despliegue
real en Cloudflare **sí** lo aplica (`not_found_handling: "404-page"`). Para
auditar lo que se desplegaría de verdad se creó:

**`dfchron/pruebas/servidor_estatico.py`** — sirve `dist/` con las mismas reglas
que el hosting: si la ruta no existe entrega `404.html` (el shell SPA), valida
que nada salga del directorio y usa `Cache-Control: no-store`.

Comprobado con él: `/`, `/app/world`, `/figures/712` y `/sites/87` devuelven
**HTTP 200** con el shell, y los `.css`/`.js` se sirven con su tamaño real
(el CSS pesa 6.690 B, no el HTML de fallback).

### Build de producción

| Comprobación | Resultado |
|---|---|
| `npm run build` | Correcto |
| Páginas estáticas generadas | 3 (`index`, `app`, `404`), sin adaptador |
| Build **sin** `PUBLIC_API_BASE_URL` | `hayApi()` compila a `return false` |
| Ese build intenta llamar a `localhost` | **No** |
| Render del build público | Estilos correctos + "This build has no API configured…" |

**No se añadió adaptador de Cloudflare** ni se cambió la estrategia de
despliegue. Sigue siendo una SPA estática.

---

## 8. Problemas encontrados y correcciones realizadas

### 8.1 — La API bloqueaba a la web por CORS (gravedad alta)

**Síntoma:** al abrir la web servida desde el puerto 4400, todas las vistas
mostraban *«Data unavailable … no se pudo contactar con la API local en
http://127.0.0.1:877»*, **aunque la API respondía HTTP 200**.

**Diagnóstico:** la allowlist de `config.ORIGENES_CORS` solo contenía el puerto
4321 (`astro dev`). El navegador aplicaba la política de origen cruzado y
descartaba la respuesta. Comprobado con `curl` con `Origin:` 4321 → cabecera
presente; con `Origin:` 4400 → cabecera ausente.

**Corrección:** añadir `4400` a la lista por defecto en `dfchron/config.py`,
documentando por qué existe ese puerto y cómo añadir otros
(`DFCHRON_CORS_PUERTOS`). La allowlist **sigue siendo restrictiva**: no se usa
`*` y ningún origen externo entra.

```python
puertos = ["4321", "4400"]   # astro dev | servidor_estatico.py
```

**Pruebas añadidas** (`dfchron/pruebas/probar_web.py`, +3):
- `test_puerto_del_servidor_estatico_permitido`
- `test_puertos_de_desarrollo_en_la_allowlist`
- `test_puerto_no_listado_bloqueado` (garantiza que 9999 siga bloqueado)

### 8.2 — La etiqueta `RELATIONSHIPS` se partía (gravedad media)

**Síntoma:** en el dashboard, la sexta tarjeta mostraba `RELATIONSHI` y una
`S` suelta en la línea siguiente, partiendo el enlace y el diseño.

**Diagnóstico:** `.stats` usaba `minmax(9.5rem, 1fr)` y `.stat-label`
`letter-spacing: 0.16em`; la etiqueta no cabía en la caja.

**Corrección:** `.stat-label` con `overflow-wrap: normal`,
`word-break: keep-all` y `letter-spacing: 0.12em`, más
`minmax(10rem, 1fr)` en la rejilla.

*Detalle del ajuste:* con `11rem` la etiqueta cabía, pero solo se colgaban
**cinco** tarjetas por fila y la sexta quedaba huérfana. `10rem` es el valor
mínimo que cumple **las dos** condiciones: la etiqueta entera en una línea y
las seis tarjetas en una fila. Verificado en la captura
`verif_stats_1440.png`.

### 8.3 — `servidor_estatico.py` servía el fallback para todo (gravedad alta)

**Síntoma:** el build público se renderizaba **sin estilos**: solo el favicon
como un arco azul gigante y "Skip to content" en azul por defecto.

**Diagnóstico:** **fallo de la herramienta de pruebas, no de la aplicación.**
Con `--dist` en ruta **relativa**, `SimpleHTTPRequestHandler` resuelve mal las
rutas y todas las peticiones (incluidos `.css` y `.js`) caían al `404.html`.
Se detectó porque cuatro URLs distintas devolvían exactamente el mismo
tamaño, 2.237 bytes.

**Corrección:** `os.path.abspath(dist)` en `servidor_estatico.py`.

**Comprobación posterior:** `/favicon.svg` → 348 B, `/_astro/app.*.css` →
6.690 B, `/app/world` → 2.237 B (el shell). El build público se renderiza
correctamente con estilos.

### 8.4 — Falsos positivos del propio script de auditoría

- **`.skip-link`**: la primera ejecución marcó 65 fallos falsos. El enlace de
  salto vive en `left: -9999px` hasta recibir foco; está completamente fuera
  del viewport y no genera barra horizontal. Se corrigió el criterio: solo
  cuenta como desborde lo que se sale por la **derecha**.
- **Selector del recorrido**: `.lista-rel a[href^="/events/"]` no existe en la
  ficha de sitio (los eventos están en una tabla). Corregido para buscar el
  enlace en toda la vista.

Ningún cambio de los anteriores altera el comportamiento de la aplicación.

---

## 9. Pruebas ejecutadas y resultados exactos

### 9.1 — Auditoría en navegador (esta fase)

| Ejecución | Comprobaciones | Fallos |
|---|---:|---:|
| Completa (5 tamaños + navegación + API + fallback) | **85** | **0** |
| Recorrido de navegación (`--solo=recorrido`) | **20** | **0** |

Capturas: 85 PNG. Ninguna sobrescrita.

### 9.2 — Regresión completa

| Suite | Resultado |
|---|---|
| `probar_nucleo.py` | **48/48** OK |
| `probar_integracion.py` | **20/20** OK |
| `probar_adversarial.py` | **39/39** OK |
| `probar_api.py` | **54/54** OK |
| `probar_web.py` | **65/65** OK (era 62; +3 por el defecto de CORS) |
| **TOTAL** | **226/226** |

### 9.3 — Determinismo y reproducibilidad

| Prueba | Resultado |
|---|---|
| `test_determinismo.py` | **DETERMINISTA** (29 consultas, 4 procesos, 3 repeticiones) |
| `verificar_reproducibilidad.py` | **REPRODUCIBLE desde los XML originales** (9 secciones y los 2 XML coinciden) |

### 9.4 — Build

`npm run build` → correcto, 3 páginas estáticas, sin adaptador.

### 9.5 — Incidencia durante la regresión (resuelta)

`probar_integracion.py` dio **7 errores** al ejecutarla por primera vez: faltaba
`00_SOURCE/processed/merged/_manifiesto.json`.

**Causa:** artefacto ausente, generado por `00_SOURCE/tools/integrar_legends.py`.
**No está relacionada con la web**, con CORS ni con el CSS: es un fichero de
metadatos de la fusión.

**Resolución:** se regeneró ejecutando `integrar_legends.py`, que es idempotente
y **solo escribe en `00_SOURCE/processed/`**. Los XML se comprobaron antes y
después: **hash idéntico**. Tras regenerarlo, las 20 pruebas de integración
vuelven a pasar.

---
## 10. Comparación de hashes

### 10.1 — XML originales (cifras de control)

| XML | Esperado (informe de Fase 2) | Obtenido | Estado |
|---|---|---|---|
| `legends.xml` | `77DB4739C4064911CDD6A94FD68D5B3CEFCBFDBC5A4459D7495CA63985A4681F` | idéntico | **INTACTO** |
| `legends_plus.xml` | `FB6BE93DAC3E878B36EB5BDD47BFE288B66D682FDA30023BA9538E81194ABC2D` | idéntico | **INTACTO** |

Comprobado tres veces: al empezar la auditoría, después de regenerar los datos
procesados y al terminar. **Los XML no se han modificado.**

### 10.2 — Datos procesados

Pendiente de la Fase 2 (aquí solo se comprobaban XML y algunos JSONL), se generó
el manifiesto completo de los **19 ficheros** de
`00_SOURCE/processed/merged/`, guardado en:

**`00_SOURCE/processed/MANIFESTO_HASHES.md`**

Incluye SHA-256 y tamaño de cada JSONL: `historical_figures`,
`historical_events`, `historical_event_relationships`,
`historical_event_relationship_supplements`, `historical_event_collections`,
`entities`, `entity_populations`, `sites`, `regions`, `artifacts`,
`world_constructions`, `underground_regions`, `written_contents`,
`musical_forms`, `poetic_forms`, `dance_forms`, `historical_eras`,
`indice_evento_relaciones` y `_manifiesto.json`.

### 10.3 — Lo que sí se modificó

| Fichero | Cambio | Motivo |
|---|---|---|
| `dfchron/config.py` | Puerto 4400 en la allowlist CORS | Defecto 8.1 |
| `dfchron/site/src/styles/app.css` | Ancho mínimo y `word-break` | Defecto 8.2 |
| `dfchron/pruebas/servidor_estatico.py` | `os.path.abspath()` | Defecto 8.3 |
| `dfchron/pruebas/probar_web.py` | +3 pruebas CORS | Regresión 8.1 |
| `dfchron/site/pruebas_visual.mjs` | Nuevo (herramienta de auditoría) | Auditoría de esta fase |
| `dfchron/site/package.json` | +`playwright` (devDependency) | Ver §2 |

**No se tocó** `nucleo.py`, `servicio.py`, `api.py` (salvo el puerto de CORS en
config), los XML, los JSONL ni la UI antigua `dfchron/web/`.

---

## 11. Limitaciones y comprobaciones no realizadas

Se documenta exactamente lo que **no** se ha podido verificar, sin simular
resultados.

### 11.1 — Navegador

- Solo se probó **Google Chrome** (`--headless=new`). **No** se probó Firefox,
  Safari ni Edge, ni en dispositivos ni sistemas reales.
- Sin GPU y sin ventana visible: es el renderizado real de Chrome, pero no una
  sesión interactiva con ratón humano.
- **No** se probó con lector de pantalla ni con navegación solo por teclado
  (aunque existe un `.skip-link` y el orden del DOM es semántico).

### 11.2 — Despliegue real

- El fallback se comprobó con `servidor_estatico.py`, que **replica** el
  comportamiento del hosting. **No** se desplegó en Cloudflare ni se probó con
  `wrangler dev`: eso requiere credenciales y red.
- **No** se comprobó el rendimiento real de red (4G, caché de Cloudflare, CDN).

### 11.3 — Entorno

- La auditoría se ejecutó en Windows con Chrome instalado en el sistema. En
  otros sistemas operativos el resultado puede variar.
- `playwright` se añadió como dependencia de desarrollo. Quien no la instale no
  puede repetir la auditoría visual, aunque el resto del proyecto funciona sin
  ella.

### 11.4 — Pendiente de la Fase 2 que sigue abierto

- La **delegación estricta** del alias geográfico (mover el glue de
  `/api/sitios/{id}/geografia` de `api.py` a `servicio.py`) **no** se ha
  revisado: es una decisión de arquitectura interna, ajena a esta auditoría
  visual y no bloquea nada.
- `00_SOURCE/web_integration_initial_audit.md` (auditoría inicial) **no** se ha
  creado: es un documento histórico de la Fase 2, no de esta fase.

---

## 12. Estado final

# COMPLETADA CON LIMITACIONES

**Qué se puede afirmar con pruebas reales:**

- DF Legends **se usa en un navegador** y carga datos reales de la API local.
- Se **navega entre sus fichas** con clics reales: figura → evento → sitio →
  entidad, y también hacia atrás, con recarga y en pestaña nueva.
- La interfaz **se adapta correctamente** a los cinco tamaños comprobados,
  incluido 320 px, **sin barras horizontales ni texto cortado**.
- Se corrigieron **3 defectos reales** y se añadieron 3 pruebas de regresión.
- **226/226 pruebas** del proyecto pasan; determinismo y reproducibilidad
  confirmados; **XML intactos**.

**Por qué no es un COMPLETADA sin más:** solo se auditó Chrome en un único
entorno y el fallback se verificó con un servidor propio que replica el
hosting, sin desplegar en Cloudflare. El resto está documentado en §11.

### Criterio de finalización

> *«DF Legends se puede utilizar en un navegador, navegar entre sus fichas y
> consultar los datos de la API sin errores, y la interfaz se adapta
> correctamente a los tamaños comprobados.»*

**Cumplido**, con las salvedades de §11.