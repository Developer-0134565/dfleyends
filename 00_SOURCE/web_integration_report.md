# DF Legends :: informe de integración Web ↔ API local

Fase: **conexión de la web con la API local**. Todo lo que sigue procede de
**ejecución real**: `python`, `npm` y peticiones HTTP comprobadas. No hay
cifras ni resultados afirmados sin ejecutar.

---

## 1. Estado inicial

Antes de modificar nada se auditó el repositorio y se ejecutaron las suites.

**Lo que ya existía:**

| Pieza | Estado real encontrado |
|---|---|
| API Python | `dfchron/api.py` + `servicio.py`, en `127.0.0.1:877`, GET-only |
| Núcleo | `00_SOURCE/tools/nucleo.py` (1.089 líneas), fuente de verdad |
| Datos | JSONL en `00_SOURCE/processed/merged/` (~40 ficheros) |
| UI antigua | `dfchron/web/` (`app.js`, 837 líneas, 15 vistas) — **conservada** |
| Web Astro | `dfchron/site/` con **una sola página** (`index.astro`) |
| `API_BASE_URL` | **No existía** en ninguna parte del workspace |

**Cifras del mundo** (de `run.py --comprobar`, no escritas a mano):

| Figuras | Entidades | Sitios | Eventos | Artefactos | Relaciones | Años |
|---|---|---|---|---|---|---|
| 11.144 | 1.067 | 734 | 57.215 | 427 | 13.192 | 1–100 |

**Hashes de protección (inicio):**

| Fichero | Bytes | SHA-256 |
|---|---|---|
| `legends.xml` | 49.223.702 | `77DB4739C4064911CDD6A94FD68D5B3CEFCBFDBC5A4459D7495CA63985A4681F` |
| `legends_plus.xml` | 17.664.819 | `FB6BE93DAC3E878B36EB5BDD47BFE288B66D682FDA30023BA9538E81194ABC2D` |

Coinciden con los que imprime `verificar_reproducibilidad.py`: doble
verificación con dos herramientas independientes.

**Tests de partida:** 48 núcleo + 20 integración + 39 adversarial + 54 API,
todas **OK**. Determinismo y reproducibilidad **OK**.

> Nota de método: la primera ejecución dio `code 1` en tres suites. **No eran
> fallos**: es el artefacto de PowerShell con `stderr` que el propio proyecto
> documenta en `WINDOWS.md:131`. Repetido con `cmd /c` para leer el recuento
> real. Se documenta porque es exactamente el tipo de error que no debe
> reportarse como "pruebas rotas".

---

## 2. Archivos modificados y creados

### Python (API)

| Fichero | Cambio |
|---|---|
| `dfchron/servicio.py` | Envelope `ok`/`meta` aditivo; `envolver_estado()`; alias singulares de búsqueda |
| `dfchron/api.py` | 4 aliases; CORS (allowlist, `Vary`, `OPTIONS`); nota de la raíz |
| `dfchron/config.py` | `ORIGENES_CORS` (allowlist local) |

### Frontend (Astro) — nuevo

| Fichero | Propósito |
|---|---|
| `src/lib/api.ts` | **ÚNICA** fuente de la dirección de la API |
| `src/lib/escapes.ts` | Helpers compartidos (rompe un ciclo de imports) |
| `src/lib/listados.ts` | Listados, eventos, timeline, búsqueda, geografía |
| `src/lib/vistas.ts` | Fichas (figura, entidad, sitio, artefacto, evento) + router |
| `src/pages/app.astro` | Shell de la aplicación |
| `src/pages/404.astro` | Mismo shell, para las rutas limpias |
| `src/styles/app.css` | Maquetación de la aplicación |
| `src/components/Certainty.astro` | Badge FACT / DERIVED / UNKNOWN |
| `src/components/Truncado.astro` | Aviso único de truncamiento |

### Frontend — modificado

| Fichero | Cambio |
|---|---|
| `src/pages/index.astro` | Identidad conservada + acceso a la aplicación |
| `src/components/SiteHeader.astro` | Navegación real (`/app/...`) |
| `astro.config.mjs` | `rewrites`; comentarios de decisión |
| `README.md` (site) | Reescrito: el anterior decía "no habla con la API", ya no era cierto |

### Pruebas y documentación

| Fichero | Cambio |
|---|---|
| `dfchron/pruebas/probar_web.py` | **Nueva suite**, 62 pruebas |
| `README.md` (raíz) | Sección web + arquitectura |
| `00_SOURCE/web_integration_report.md` | Este informe |

### Eliminado

`world.astro`, `figures.astro`, `entities.astro`, `sites.astro`,
`artifacts.astro`, `events.astro`, `timeline.astro`, `search.astro`,
`geography.astro`, `types-historicos.astro`, `AppLayout.astro`.

Motivo: eran páginas pre-renderizadas que **congelaban los datos del build**
(el defecto se explica en §11). Su lógica vive ahora en `src/lib/listados.ts` y
`src/lib/vistas.ts`.

**No se eliminó** `dfchron/web/` (UI antigua), `nucleo.py`, ni los XML.

---

## 3. Endpoints: canónicos y aliases

**41 endpoints** en total. Los canónicos no cambian de comportamiento.

### Aliases añadidos (4)

| Alias | Canónico | Delegación |
|---|---|---|
| `/api/estadisticas` | `/api/stats` | `svc.stats()` |
| `/api/buscar/{tipo}` | `/api/buscar?tipo=<t>` | `svc.buscar()` |
| `/api/sitios/{id}/geografia` | `/api/geografia/{capa}` | `construcciones_en_sitio()` del núcleo |
| `/api/artefactos` | `/api/listar/artifacts` | `svc.listar("artifacts")` |

Se aceptan singulares y plurales: `/api/buscar/figura` y `/api/buscar/figuras`
ejecutan **el mismo** método del núcleo.

**Verificado:** `/api/stats` y `/api/estadisticas` devuelven objetos idénticos.

---
## 4. Funcionalidades reales

Todas verificadas con la API en marcha:

| Funcionalidad | Verificación |
|---|---|
| Dashboard con cifras reales | 11.144 · 1.067 · 734 · 57.215 · 427 · 13.192 · años 1–100 |
| Listado paginado | `Showing 50 of 11.144`, `Page 1 of 223` |
| Búsqueda global | `halesteel` → 4 resultados (3 figuras + sitio 87) |
| Ambigüedad declarada | `the` → 262 figuras, `Nothing was selected automatically` |
| Cero resultados | `zzzqqqnoexiste` → `No results` |
| Ficha de figura | 712: MINOTAUR, FEMALE, `Born Unknown` |
| Ficha de entidad | 282: *the curled diamond*, 25 miembros |
| Ficha de sitio | 87: **fortress**, (112, 20), 1.546 eventos |
| Ficha de evento | 123: tipo, subtipo, estado |
| Filtro combinado | `from=1&to=3&figure=712` → **6** eventos (no los 158) |
| Truncamiento declarado | `Showing 50 of 1.182` en timeline |
| Geografía | 4 capas: ríos 2.346, masas 40, picos 4, construcciones 122 |
| Tipo real preservado | `fortress` sigue siendo `fortress` |

---

## 5. Pruebas

| Suite | Antes | Después |
|---|---|---|
| `probar_nucleo.py` | 48 / 48 | **48 / 48** |
| `probar_integracion.py` | 20 / 20 | **20 / 20** |
| `probar_adversarial.py` | 39 / 39 | **39 / 39** |
| `probar_api.py` | 54 / 54 | **54 / 54** |
| `probar_web.py` (nueva) | — | **62 / 62** |
| `test_determinismo.py` | DETERMINISTA | **DETERMINISTA** (29 × 4 × 3) |
| `verificar_reproducibilidad.py` | REPRODUCIBLE | **REPRODUCIBLE**, 4/4 bloqueados |

**Total: 223 pruebas.** Ninguna suite antigua se sustituyó ni se eliminó.

La nueva suite cubre: envelope, aliases, CORS, datos conocidos, filtros,
truncamiento, adversarial (ids hostiles, Unicode, traversal) y estático del
frontend.

---

## 6. Rendimiento (medido)

| Operación | Tiempo |
|---|---|
| Arranque + 1ª petición | 27,6 ms |
| `/api/salud` | 13,2 ms |
| `/api/estadisticas` | 0,9 ms |
| Búsqueda "galka shafttop" | 3,9 ms |
| Ficha figura 712 | 3,7 ms |
| Ficha sitio 87 | 53,4 ms |
| Eventos años 1–20 (500 filas) | 14,7 ms |
| Filtro combinado | 1,4 ms |
| Timeline años 1–5 | 18,7 ms |
| Geografía | 26,4 ms |
| Listado de figuras (50) | 25,0 ms |

El navegador nunca recibe el dataset: las listas piden `limit` (50) y se
verificó que llegan 50 filas más la cabecera, no 11.144.

---

## 7. Responsive

`app.css` verificado con: `clamp()` (7 usos), `auto-fit` (4),
`flex-wrap: wrap` (6), `overflow-x: auto` para tablas, y dos media queries
(`≤600px`, `≤380px`).

Las tres páginas del build llevan `viewport` y enlace de salto.

**Declaración honesta:** se verificó la **estructura CSS** y el HTML generado,
pero **no se tomó una captura visual en un navegador real** en las 9
resoluciones (320, 360, 390, 414, 600, 768, 1024, 1280, 1440). Las medidas
son fluidas por diseño, pero eso no equivale a haberlo visto renderizado.

---

## 8. Seguridad y CORS

**CORS** (allowlist en `config.ORIGENES_CORS`):

| Origen | Resultado |
|---|---|
| `http://localhost:4321` | Permitido |
| `http://127.0.0.1:4321` | Permitido |
| `http://evil.example.com` | **Sin cabecera** (bloqueado) |
| Sin `Origin` | Sin cabecera |

Nunca `Access-Control-Allow-Origin: *`. Preflight `OPTIONS` → 204.
`Vary: Origin` presente. **Sin** `Allow-Credentials`.

**Probado:**

- Path traversal: `/static/../../etc/passwd`, `..%2f..%2fWindows/win.ini`, rutas
  absolutas → **403/404**.
- Un parámetro HTTP **no puede elegir fichero**: `?file=../../legends.xml` se
  ignora; la ruta responde 400 por ser búsqueda sin `q`.
- Métodos de escritura → **405**.
- Sin tracebacks en 8 rutas hostiles.
- Sin secretos en `/api/salud`.

---

## 9. Integridad de los datos

| Fichero | Antes | Después | Estado |
|---|---|---|---|
| `legends.xml` | `77DB4739…85A4681F` | `77DB4739…85A4681F` | **INTACTO** |
| `legends_plus.xml` | `FB6BE93D…194ABC2D` | `FB6BE93D…194ABC2D` | **INTACTO** |
| `merged/historical_events.jsonl` | `07204F1B…` | `07204F1B…` | **INTACTO** |
| `merged/historical_figures.jsonl` | `DA400A37…` | `DA400A37…` | **INTACTO** |
| `merged/entities.jsonl` | `B2866523…` | `B2866523…` | **INTACTO** |
| `merged/sites.jsonl` | `53E5EC2D…` | `53E5EC2D…` | **INTACTO** |

Ningún dato protegido fue modificado.

---

## 10. Build de Astro

```
npm run build   →  Complete!  3 page(s) built
```

Genera `index.html`, `app/index.html` y `404.html`, todo estático, **sin
adaptador y sin runtime**.

**Build público** (sin `PUBLIC_API_BASE_URL`): el bundle queda con
`function e(){return!1}` — es decir, `hayApi()` es `false`. La URL
`127.0.0.1:877` aparece **solo** dentro de un texto de ayuda, nunca como
origen activo. **El build público no está conectado a la API local.**

---
## 11. Problemas encontrados y corregidos

Se documentan todos, incluidos los que fallaron a la primera.

### API

| # | Problema | Corrección |
|---|---|---|
| 1 | `/api/artefactos` devolvía **400**. El núcleo llama a los tipos `artifacts` (inglés), no `artefactos`. | Se usa el nombre real del núcleo. |
| 2 | El proyecto usa `codigo`/`mensaje`; el contrato genérico pide `code`/`message`. | Se conservan los dos. |

### Frontend

| # | Problema | Corrección |
|---|---|---|
| 3 | **Build falló**: JSX dentro de un arrow function en `events/[id].astro`. | Reescrito con lógica plana. |
| 4 | **Build falló**: `../../layouts` en páginas de primer nivel. | Corregidas 9 rutas de import. |
| 5 | **Build falló**: `output: "hybrid"` ya no existe en Astro 7. | Se usa `static`. |
| 6 | **Build falló**: `NoAdapterInstalled` al usar `prerender = false`. | Decisión de arquitectura (ver §12.1). |
| 7 | **Build falló**: `Duplicated export 'interpretar'`. | Eliminado el router antiguo huérfano. |
| 8 | **Build falló**: `MISSING_EXPORT "Vacio"` por **ciclo de imports** entre `vistas.ts` y `listados.ts`. | Helpers movidos a `escapes.ts`. |
| 9 | **Runtime**: `ReferenceError: avisoTruncamiento is not defined` — consecuencia del ciclo anterior. | Resuelto junto con el nº 8. |
| 10 | **Bug funcional**: `consultar()` codificaba los query params como segmentos → `/api/eventos/from%3D1%26to%3D3`. La API respondía "endpoint inexistente". | La query se monta con `?`/`&` antes de codificar. |
| 11 | **Dato falso**: `[object Object]` en el contador de artefactos (el núcleo devuelve a veces lista, a veces número). | Helper `contar()` que cuenta lo que haya. |
| 12 | **Doble codificación** en `probar_web.py`: `ñ` guardado como `Ã±`, lo que rompía las claves `año`. | Reescrito con escape `\u00f1`. |
| 13 | `astro preview` devuelve 404 en rutas limpias. | **Documentado, no corregido**: preview sirve ficheros literales. El fallback a `404.html` es lo que usa Cloudflare. |

### El defecto más importante

**Las páginas pre-renderizadas congelaban los datos del build.** Se detectó
porque `/world` mostraba cifras reales mientras `/figures` mostraba
`Data unavailable`, en el mismo build. La causa: durante ese build la API no
estaba viva, y cada página guardó el resultado de su momento.

La solución fue **un único shell estático** que pide los datos en cada visita
(`app.astro` + `404.html` + `src/lib/vistas.ts`). Esto además resolvió el
`NoAdapterInstalled`.

---

## 12. Desviaciones respecto al plan

### 12.1 Sin adaptador: render en cliente en lugar de render en servidor

**El plan aprobado asumía fichas renderizadas en el servidor.** No es posible
sin adaptador, y un adaptador implica un runtime en la capa pública — lo que
choca con las reglas 5 y 6 del bloque de dominio público.

Se paró y se preguntó antes de continuar. La decisión fue: **SPA cliente ahora,
adaptador documentado como fase posterior** (cuando exista backend remoto).

Efecto colateral aceptado: las rutas limpias (`/figures/712`) dependen del
fallback a `404.html`. `astro preview` no lo emula; un servidor estático con
fallback sí, como Cloudflare.

### 12.2 Las vistas viven bajo `/app/...`

Como las páginas ya no se pre-renderizan, las rutas navegables son
`/app/figures`, `/app/sites/87`, etc. Las **URLs limpias siguen funcionando**
(las sirve `404.html` y las resuelve el router), pero la navegación interna
apunta a `/app/...` para ser explícita.

### 12.3 Componentes Astro sin uso final

`AppLayout.astro` quedó huérfano al pasar al shell y se eliminó.
`Certainty.astro`, `Truncado.astro` y `ListaRegistros.astro` **sí se conservan**
(comparten tokens y sirven de referencia de maquetación), pero el render final
de los datos ocurre en el cliente.

### 12.4 Qué NO se hizo (por diseño)

| Elemento | Estado |
|---|---|
| IA (LLM, RAG, embeddings) | **No implementada.** Docs intactas y verificadas por test. |
| `.exe` / PyInstaller / MSI | **No implementado.** |
| Autenticación | **No implementada.** La API es local y GET-only. |
| Supabase / BD remota | **No implementado.** |
| Backend público | **No implementado.** |
| Conexión Cloudflare ↔ API local | **NO implementada** (regla 10). |
| `127.0.0.1:877` expuesto | **NO.** Sigue en `config.py`. |
| Modificaciones al núcleo | **Ninguna.** `nucleo.py` intacto. |

---

## 13. Cómo usarlo

```bash
# 1. API
python run.py

# 2. Web
cd dfchron/site
set PUBLIC_API_BASE_URL=http://127.0.0.1:877 && npm run dev
```

Abre <http://localhost:4321/>.

El recorrido del enunciado está verificado con datos reales:

```
Abrir DF Legends → cifras reales → buscar "galka shafttop"
   → abrir figura 712 → ver eventos → ver cronología → ver relaciones
   → abrir sitios y entidades relacionadas → explorar otros eventos
```

---

## 14. Qué queda pendiente para la siguiente fase

1. **Adaptador de render** cuando exista backend remoto, para no depender del
   fallback a `404.html`.
2. **Mapa visual** en geografía: la arquitectura ya lo permite (los datos de
   coordenadas están en `escapes.ts`/`listados.ts`), pero no se ha añadido
   ninguna librería de mapas.
3. **Verificación responsive con navegador real** en las 9 resoluciones.
4. **API remota**: solo cuando se autorice; el cambio en el frontend es una
   variable.