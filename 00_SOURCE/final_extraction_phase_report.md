# DF-Chronicles :: Informe de la fase de cierre del núcleo y primera interfaz

**Misión:** cierre de extracción/núcleo + primera interfaz funcional.
**Estado:** completada. Aplicación local operativa, verificada con 161 pruebas
sobre los datos reales.

Todas las cifras de este informe se obtuvieron **ejecutando** el software, no
copiándose de informes anteriores.

---

## 1. Datos de partida

### Fuentes originales (solo lectura, nunca modificadas)

| Archivo | Bytes | Codificación | SHA-256 | Rol |
|---|---:|---|---|---|
| `legends.xml` | 49.223.702 | cp437 | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` | primaria |
| `legends_plus.xml` | 17.664.819 | utf-8 | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` | complementaria |

**Hashes verificados al inicio y al final de la misión: idénticos.**

Juego de origen: Dwarf Fortress **53.16**, partida `region2-00100-01-01`.

### Dataset normalizado

| Sección | Registros | | Sección | Registros |
|---|---:|---|---|---:|
| `historical_figures` | 11.144 | | `rivers` | 2.346 |
| `entities` | 1.067 | | `landmasses` | 40 |
| `sites` | 734 | | `mountain_peaks` | 4 |
| `historical_events` | 57.215 | | `world_constructions` | 122 |
| `artifacts` | 427 | | `identities` | 475 |
| `historical_event_relationships` | 13.192 | | `collections` | 6.544 |
| `..._relationship_supplements` | 21 | | `historical_eras` | 1 |

**Rango temporal: años 1–100.** Todos los 57.215 eventos tienen año.
**Era: UNKNOWN** (`start_year = -1`, centinela de DF).

---

## 2. Auditoría inicial: qué se encontró de verdad

Se volvieron a ejecutar **todas** las suites antes de tocar nada, y los
informes anteriores se auditaron contra el código, no al revés.

### Resultado de la línea base

| Suite | Informe previo | Ejecutado | Veredicto |
|---|---|---|---|
| Integración | 20/20 | **20/20** | correcto |
| Núcleo | 48/48 | **48/48** | correcto |
| Adversarial | 38/38 | **38/38** | correcto |
| Determinismo | 29 × 4 | **29 × 4** | correcto |
| Reproducibilidad | 9/9 + 4/4 | **9/9 + 4/4** | correcto |

Los informes previos eran fiables. Pero la auditoría del **código** sí encontró
defectos reales que ningún informe mencionaba.

### Defectos encontrados y corregidos

| # | Defecto | Gravedad | Corrección |
|---|---|---|---|
| 1 | **Prueba muerta**: `test_el_codigo_no_contiene_lenguaje_causal` tenía el cuerpo vacío (solo un `import inspect` huérfano). No podía fallar jamás. | Alta | Reescrita: analiza el AST de `nucleo.py` y busca conectores causales en las cadenas. La suite pasó de 38 a 39 pruebas. |
| 2 | **Rutas absolutas duplicadas** en 5 módulos. El proyecto no se podía mover. | Alta | Nuevo `rutas.py` como fuente única. Cero rutas absolutas en el código. |
| 3 | **`integrar_legends.py` apuntaba a `Downloads/`** para `legends_plus.xml`: una descarga que ya no existe. | Alta | Usa la copia de `original_data/`, idéntica por hash. |
| 4 | **`dividir_xml.py` ejecutaba lógica en el `import`**: importarlo escribía 83 ficheros. | Alta | Todo bajo `main()` con guarda `if __name__`. |
| 5 | **Filtro combinado roto**: `eventos_filtrados(from=1,to=3,figure=712)` devolvía los 158 eventos, ignorando el año. | Alta | El rango se revalida siempre. Verificado: ahora devuelve 6. |
| 6 | **`salud()` devolvía 500**: `import config` local fallaba en modo paquete. | Media | Import resuelto en el módulo. |
| 7 | **`/api` documentaba mal sus endpoints**: mostraba `/api/api/...`. | Baja | Corregido el generador. |
| 8 | **Tipografía en `nucleo.py`**: `sito` en el filtro por sitio. | Media | Corregido. |
| 9 | **Bugs de UI**: temporal dead zone de `VISTAS`, `truncado()` truncado, geografía sin guarda. | Alta | Corregidos y verificados renderizando las 15 vistas contra la API real. |

> Los defectos 5, 6 y 8 son la razón de exigir verificación con ejecución:

---

## 3. Cambios realizados

### Módulos del pipeline (modificados)

| Archivo | Cambio |
|---|---|
| `tools/rutas.py` | **NUEVO.** Configuración central de rutas + guardas de escritura. |
| `tools/validar_semantica.py` | Importa rutas de `rutas.py`. |
| `tools/nucleo.py` | Importa rutas; **+7 funciones públicas**. |
| `tools/integrar_legends.py` | Rutas centralizadas; original desde `original_data/`. |
| `tools/verificar_reproducibilidad.py` | Rutas centralizadas. |
| `tools/dividir_xml.py` | Rutas centralizadas; ejecución bajo `main()`. |
| `tools/probar_adversarial.py` | Prueba muerta convertida en prueba real. |

### Funciones nuevas en el núcleo

| Función | Para qué |
|---|---|
| `estadisticas()` | Conteos reales para la portada (nada escrito a mano) |
| `tipos_evento()` | Desplegable «Tipo» del explorador (90 tipos) |
| `eventos_filtrados()` | Filtros combinables: año, rango, tipo, figura, sitio, entidad |
| `ficha_evento()` | Ficha completa de un evento |
| `listar_registros()` | Listados paginados para explorar sin buscar |
| `eventos_de_artefacto()` | Eventos que mencionan un artefacto |
| `listar_geografia()` | Las 4 capas geográficas con coordenadas |

### Aplicación nueva (`dfchron/`)

| Archivo | Líneas | Responsabilidad |
|---|---:|---|
| `config.py` | 70 | Rutas y límites de la API |
| `servicio.py` | 478 | Envelopes, validación, errores |
| `api.py` | 318 | Servidor HTTP (solo stdlib), 38 endpoints |
| `web/index.html` | 39 | Cáscara de la UI |
| `web/app.js` | 780 | 15 vistas, enrutado por hash |
| `web/estilo.css` | 192 | Estilo único |
| `pruebas/probar_api.py` | 428 | 54 pruebas de API, UI y seguridad |
| `run.py` | 76 | Arranque |

**Total: 6.438 líneas de código** (5.427 Python, 780 JS, 192 CSS, 39 HTML).
**Dependencias externas: cero.**

---

## 4. Arquitectura final

```
Dwarf Fortress 53.16
        │
   legends.xml (49 MB, CP437)  +  legends_plus.xml (18 MB, UTF-8)
        │                       SOLO LECTURA · SHA-256 verificado
        ↓  cargar_legends.py        autodetección de codificación
        ↓  integrar_legends.py      fusión con procedencia por campo
        ↓  processed/merged/*.jsonl 20 secciones normalizadas
        ↓  validar_semantica.py     índice y validación de referencias
        ↓  nucleo.py                LÓGICA DE DOMINIO (47 funciones)
        ↓  dfchron/servicio.py      envelopes, límites, errores
        ↓
   ┌────┴─────┐
   ↓          ↓
 API         UI
 38 endpoints  15 pantallas
 (stdlib)     (fetch → /api)
   ↓
 [web futura: mismo núcleo, misma API]
```

### Las tres reglas que lo sostienen

1. **La UI nunca lee los XML.** Habla solo con `/api`. Comprobado por prueba
   automática que busca `legends.xml`, `.jsonl` y `original_data` en el
   JavaScript.
2. **La API nunca implementa lógica de Dwarf Fortress.** Traduce rutas y nada
   más. Si mañana se sirve por web, no hay nada que reescribir.
3. **El núcleo no sabe nada de rutas absolutas.** Todo se resuelve desde
   `__file__` o `DFCHRON_ROOT`.

---

## 5. API

38 endpoints, todos `GET`, escuchados en `127.0.0.1:877`.

| Grupo | Endpoints |
|---|---|
| Metadatos | `/api`, `/api/salud`, `/api/stats`, `/api/limitaciones` |
| Búsqueda | `/api/buscar`, `/api/{figuras,entidades,sitios,artefactos}`, `/api/listar/{tipo}` |
| Figuras | `/{id}`, `/eventos`, `/cronologia`, `/relaciones`, `/artefactos`, `/identidad` |
| Entidades | `/{id}`, `/miembros`, `/sitios`, `/eventos`, `/cronologia` |
| Sitios | `/{id}`, `/eventos`, `/cronologia`, `/figuras` |
| Artefactos | `/{id}`, `/propietarios`, `/eventos` |
| Eventos | `/{id}`, `/participantes`, `/tipos`, y filtros de listado |
| Otros | `/relaciones/tipos`, `/conflictos`, `/geografia`, `/exportar` |

### Formato de respuesta

```json
{ "data": [...], "total_encontrados": 1546, "devueltos": 200,
  "truncado": true, "limit": 200, "offset": 0, "certainty": "FACT" }
```

**Ningún truncamiento es silencioso.** La UI lo muestra como aviso.

### Límites

`limit` por defecto 50, **tope duro 500**. `?limit=999999999` se acota a 500 y
la respuesta lo declara. `offset` absurdo devuelve lista vacía, no un error.

---

## 6. UI

9 pantallas de menú: **Inicio**, **Figuras**, **Entidades**, **Sitios**,
**Artefactos**, **Eventos**, **Cronología**, **Geografía**, **Limitaciones**;
más las fichas de detalle (figura, entidad, sitio, artefacto, evento) con
pestañas. 15 vistas en total.

Tecnología: **JavaScript plano, sin framework, sin build.** Sin `node_modules`,
sin paso de compilación.

Dos decisiones deliberadas:

* **Las limitaciones se muestran en todas las pantallas**, en una banda
  permanente, no solo en su propia página. Una interfaz no debe esconder lo que
  los datos no saben.
* **El tipo de sitio se conserva tal cual.** `halesteel` es `fortress`, nunca
  `site`. `tipo_registro` distingue el tipo de registro del tipo real. Hay una
  prueba de regresión específica: `test_sitio_87_conserva_el_tipo_de_dwarf_fortress`.


---

## 7. Pruebas

### Todas las suites, ejecutadas

| Suite | Resultado | Tiempo |
|---|---|---|
| `probar_integracion.py` | **20 / 20** | 3,7 s |
| `probar_nucleo.py` | **48 / 48** | 3,8 s |
| `probar_adversarial.py` | **39 / 39** | 8,5 s |
| `probar_api.py` | **54 / 54** | 4,6 s |
| `test_determinismo.py` | **DETERMINISTA** (29 consultas × 4 procesos × 3 repeticiones) | 18,7 s |
| `verificar_reproducibilidad.py` | **9/9 byte-idénticas + 4/4 salvaguardas** | 8,8 s |

**Total: 161 pruebas. 161 correctas. 0 fallos.**

La suite adversarial subió de 38 a 39 porque la prueba muerta pasó a ser real.
Ninguna prueba se eliminó ni se relajó.

### Cobertura de `probar_api.py`

| Clase | Qué cubre |
|---|---|
| `TestMetadatos` (5) | Salud, estadísticas reales, limitaciones, documentación |
| `TestFichas` (4) | Valores concretos de figura 712, sitio 87, entidad 282, figura 0 |
| `TestBusqueda` (4) | Búsqueda correcta, ambigüedad, sin resultados, agrupación por tipo |
| `TestColecciones` (9) | Eventos, filtros combinados, paginación, cronología, relaciones |
| `TestConflictosYGeografia` (5) | Conflictos DERIVED, 4 capas, río con id derivado |
| `TestErrores` (10) | 404, 400, 405, IDs inválidos, años inválidos, formatos |
| `TestSeguridad` (9) | Traversal, XML no servido, export bloqueado, límites, dataset intacto |
| `TestInterfaz` (4) | HTML y estáticos servidos, UI sin acceso a XML, UI usa la API |
| `TestIntegridadDatos` (1) | Hashes de los XML originales |

### Verificación de la UI

Las 15 vistas se ejecutaron en Node contra la API **real** (no simulada),
comprobando que renderizan sin lanzar y que muestran las cifras correctas
(11.144 figuras, 57.215 eventos, era UNKNOWN, rango 1–100). Además se
verificó visualmente con Chrome headless.

---

## 8. Resultados: los datos conocidos siguen siendo correctos

Verificados a través de la API HTTP, no del núcleo directamente:

| Comprobación | Valor esperado | Obtenido |
|---|---|---|
| Figura 712 — nombre | `galka shafttop the blades of knighting` | ✅ |
| Figura 712 — raza | `MINOTAUR` | ✅ |
| Figura 712 — eventos | 158 | ✅ |
| Figura 712 — eventos (endpoint de colección) | 158 | ✅ |
| Sitio 87 — nombre | `halesteel` | ✅ |
| Sitio 87 — **tipo** | `fortress` (no `site`) | ✅ |
| Sitio 87 — coordenadas | `(112, 20)` | ✅ |
| Sitio 87 — eventos | 1.546 | ✅ |
| Entidad 282 — nombre | `the curled diamond` | ✅ |
| Entidad 282 — miembros | 25 | ✅ |
| Entidad 282 — eventos | 769 | ✅ |
| Búsqueda `galka shafttop` | contiene el id 712 | ✅ |
| Eventos año 5 | 223 | ✅ |
| Eventos rango 1–20 | 4.696 | ✅ |
| Eventos figura 712 | 158 | ✅ |
| Eventos sitio 87 | 1.546 | ✅ |
| Eventos entidad 282 | 769 | ✅ |
| Eventos año 1–3 + figura 712 | 6 (combinado correcto) | ✅ |
| Cronología de 712 | ordenada por año | ✅ |
| Picos mountainos | 4 | OK |
| Ríos | 2.346 | ✅ |
| Conflictos | 5.478, `certainty: DERIVED` | ✅ |
| Tipos de evento | 90 | ✅ |
| Tipos de relación | 12 | ✅ |
| Era historica | UNKNOWN | OK |

---

## 9. Problemas encontrados y bugs corregidos

Los 9 defectos de la tabla del apartado 2, todos corregidos. Los que más
importaban:

1. **La prueba de lenguaje causal estaba muerta.** Un informe que dice «38/38
   correctas» ocultaba que una de esas 38 no comprobaba nada.
2. **El filtro combinado por año y figura estaba roto.** Devolvía 158 eventos
   en vez de 6. Nadie lo habría notado sin probarlo.
3. **`dividir_xml.py` escribía 83 ficheros al importarlo.**
4. **La UI no arrancaba** por un `const` usado antes de declararse. Los
   errores de JavaScript no se ven leyendo el archivo: se ven ejecutándolo.

---

## 10. Limitaciones

### De los datos

| Limitación | Cifra |
|---|---|
| Rango temporal | Solo años **1–100** |
| Era histórica | **UNKNOWN** (`start_year = -1`) |
| Eventos sin participantes | **17.881** de 57.215 (31 %) |
| Eventos con coordenadas centinela | **9.930** |
| Figuras sin `death_year` | **6.734** (ausente ≠ viva) |
| Figuras sin eventos | **1.947** |
| Figuras sin entidad | 422 |
| Entidades sin nombre | 218 |
| Relaciones sin evento asociado | **13.192** |
| Artefactos sin dueño ni sitio | 13 |
| Ríos sin id en el XML | **2.346** (id DERIVED) |
| Conflictos entre fuentes sin resolver | **1.925** |
| Tabla de guerras | **No existe** |

### De la aplicación

* **Sin autenticación.** Pensada para `127.0.0.1`. Exponerla en una red
  requeriría añadirla (documentado en `WINDOWS.md`).
* **Sin caché ni índice en disco.** El arranque cuesta 2,1–2,6 s y ~500 MiB.
  Aceptable para un archivo de una partida; no para un catálogo grande.
* **Sin mapa geográfico.** La geografía es tabular y por coordenadas, no
  cartográfica. Es una decisión de esta fase, no una limitación técnica.
* **Sin `.exe`.** Ver `WINDOWS.md` §7: se documentó el camino pero no se
  construyó, para no sacrificar la arquitectura.
* **Sin tests de navegador automatizados.** La UI se verificó ejecutando las
  vistas en Node y con Chrome headless, no con un framework de tests. Node no
  es un requisito del proyecto (verificado sin él).


---

## 11. Decisiones arquitectónicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| `http.server` (stdlib) | Flask, FastAPI | Cero dependencias. `pip install` es barrera y riesgo en un equipo local. |
| JavaScript plano | React, Vue | Sin `node_modules` ni build. La UI se lee de un vistazo. |
| Envelopes en el servicio, no en la API | En la API | La UI web recibiría otro formato; habría que duplicar lógica. |
| Paginación `limit`/`offset` | Traer todo | 57.215 eventos en una respuesta no es viable. |
| `EXPORT_ROOT` separado | Escribir junto a los datos | Un export nunca puede contaminar el dataset. |
| Rutas relativas a `__file__` | Rutas absolutas | El proyecto se puede mover sin editar código. |
| Núcleo agnóstico del formato | Núcleo que devuelve envelopes | Permite que una web reutilice el mismo núcleo sin tocarlo. |
| Solo `GET` | API con escritura | Elimina por construcción toda escritura remota. |
| HTML y atributos semánticos | Framework | El HTML ya distingue tipos y roles; un aria-label no necesita más. |
| Sin caché | Índice en disco | El arranque es aceptable; una caché invalidaría los hashes. |

---

## 12. Archivos creados

| Archivo | Propósito |
|---|---|
| `run.py` | Punto de entrada único |
| `dfchron/__init__.py` | Paquete de la aplicación |
| `dfchron/config.py` | Rutas y límites |
| `dfchron/servicio.py` | Envelopes, validación, errores |
| `dfchron/api.py` | Servidor HTTP, 38 endpoints |
| `dfchron/pruebas/probar_api.py` | 54 pruebas de API, UI y seguridad |
| `dfchron/web/index.html` | Cáscara de la UI |
| `dfchron/web/app.js` | 15 vistas |
| `dfchron/web/estilo.css` | Estilo único |
| `00_SOURCE/tools/rutas.py` | Configuración central de rutas |
| `README.md` | Documentación principal (reescrito) |
| `API.md` | Referencia de la API |
| `ARCHITECTURE.md` | Arquitectura y camino a web |
| `WINDOWS.md` | Instalación, arranque, `.exe`, problemas |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Contrato operativo para la futura IA |
| `00_SOURCE/final_extraction_phase_report.md` | Este informe |

## 13. Archivos modificados

| Archivo | Cambio |
|---|---|
| `00_SOURCE/tools/nucleo.py` | +7 funciones públicas; rutas centralizadas |
| `00_SOURCE/tools/validar_semantica.py` | Rutas centralizadas |
| `00_SOURCE/tools/integrar_legends.py` | Rutas centralizadas; original desde `original_data/` |
| `00_SOURCE/tools/verificar_reproducibilidad.py` | Rutas centralizadas |
| `00_SOURCE/tools/dividir_xml.py` | Rutas centralizadas; ejecución bajo `main()` |
| `00_SOURCE/tools/probar_adversarial.py` | Prueba muerta convertida en prueba real |

## 14. Archivos protegidos (no modificados)

| Ruta | Estado |
|---|---|
| `00_SOURCE/original_data/legends.xml` | **SHA-256 intacto** |
| `00_SOURCE/original_data/legends_plus.xml` | **SHA-256 intacto** |
| `00_SOURCE/processed/merged/*.jsonl` | Sin cambios (verificado por huella antes/después de servir peticiones) |
| `00_SOURCE/processed/validation/` | Sin cambios |
| `00_SOURCE/extraction/` | Sin cambios |

`original_data/`, `processed/` y `validation/` están declarados en
`RUTAS_SOLO_LECTURA`, y `rutas.es_ruta_protegida()` aborta cualquier escritura
sobre ellos.

---

## 15. Cómo arrancar

```powershell
cd DF-Chronicles
python run.py
```

Abre <http://127.0.0.1:877/>. Carga el índice en 2,1–2,6 s.

```powershell
python run.py --comprobar     # comprobar sin arrancar
python run.py 9000            # otro puerto
python run.py --sin-navegador # no abrir el navegador
```

## 16. Cómo comprobar que todo sigue bien

```powershell
python 00_SOURCE\tools\probar_integracion.py          # 20/20
python 00_SOURCE\tools\probar_nucleo.py               # 48/48
python 00_SOURCE\tools\probar_adversarial.py          # 39/39
python dfchron\pruebas\probar_api.py                  # 54/54
python 00_SOURCE\tools\test_determinismo.py           # determinista
python 00_SOURCE\tools\verificar_reproducibilidad.py # reproducible
```

Las seis devuelven código de salida `0`.

## 17. Cómo añadir una futura interfaz web

La UI actual **ya es una web**. Para servirla desde otro sitio:

```
Navegador
   ↓  GET https://tu-servidor/
Web UI  (los MISMOS index.html y app.js)
   ↓  fetch('https://tu-servidor/api/...')
dfchron.api          (sin cambios)
   ↓
dfchron.servicio     (sin cambios)
   ↓
nucleo.py            (sin cambios)
```

Cambios necesarios: servir los estáticos desde el mismo origen (o añadir
CORS), apuntar el `fetch` al origen correcto (basta cambiar la ruta en la
función `api()` de `app.js`) y añadir autenticación si se expone fuera de la
máquina.

Lo que **no** hay que tocar: `nucleo.py`, `servicio.py`, los JSONL ni los XML.


---

## 18. Estado del contexto para la futura IA

**No hay IA. No se ha implementado nada de IA.**

Se ha preservado la decisión arquitectónica:

* `08_DATABASE/ai_data_contract.md` — revisado y **conservado**: define el
  formato de evidencia (`certainty`, `df_id`, `función`, `fuente`).
* `08_DATABASE/AI_PROJECT_CONTEXT.md` — **nuevo**: contrato operativo. Fija la
  distinción `PLAYER_KNOWLEDGE` / `WORLD_KNOWLEDGE` / `EXTERNAL_KNOWLEDGE` /
  `INFERENCE`, y la regla de que **`FACT` no es permiso para revelar**
  (`truth_status` / `visibility` / `disclosure`).

La API de limitaciones (`GET /api/limitaciones`) queda disponible como
contexto fijo para un futuro modelo, con sus cifras medidas.

## 19. Trabajo que queda para futuras fases

1. **IA** — requiere el contrato de `AI_PROJECT_CONTEXT.md` y, antes,
   autenticación si se expone fuera de `127.0.0.1`.
2. **Índice en disco** — si 2,6 s de arranque y 500 MiB deja de ser aceptable.
3. **Mapa geográfico** — la geografía existe como datos; falta la capa visual.
4. **Autenticación** — necesaria antes de exponer la API en una red.
5. **Empaquetado `.exe`** — camino documentado en `WINDOWS.md` §7.
6. **Más partidas** — el dataset es una sola partida; el diseño ya soporta más
   parametrando `DFCHRON_ROOT`.
7. **Tests de navegador automatizados** — la UI se verificó ejecutándola, pero
   sin framework de tests en el navegador. Node no es un requisito del
   proyecto: se comprobó que todo funciona sin él.

---

## Conclusión

DF-Chronicles ha pasado de ser un conjunto de herramientas de extracción a ser
**una aplicación local funcional** para explorar el archivo histórico de Dwarf
Fortress, con un núcleo estable, verificable y reutilizable.

Lo que se consiguió importa más allá de las cifras:

* **La verdad sobre los datos está garantizada por construcción**, no por
  disciplina: cada respuesta declara su certeza y cada recorte declara que hay
  más.
* **Las limitaciones son parte de la interfaz**, no una nota al pie.
* **La lógica de dominio está aislada del servidor y de la presentación**, lo
  que hace que una web futura sea un cambio de configuración, no de código.
* **Los originales están intactos**, verificado por hash antes y después.

El núcleo está terminado, estable y verificable. La IA llegará después.

> ninguno se habría visto leyendo el código.
