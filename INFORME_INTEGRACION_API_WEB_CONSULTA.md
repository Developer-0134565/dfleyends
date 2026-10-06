# INTEGRACIÓN API/WEB CON `servicio_consulta.py`

> **Documento revisado tras una auditoría de solo lectura.** La integración ya
> existía. Esta auditoría la **verificó**, encontró **tres huecos reales** y los
> cerró. Las cifras de abajo son las medidas; las de la sección «Estado
> inicial» son las de la misión original.

---

## VERIFICACIÓN POST-AUDITORÍA (lo más reciente)

| Métrica | Valor |
|---------|-------|
| Endpoints que pasan por `servicio_consulta` | **13** (7 migrados + 6 nuevos) |
| Endpoints de navegación, fuera por decisión | **34**, documentados |
| Pruebas de integración | **55** (antes 53) |
| Suite de mutation testing | **3 tests, permanente en el repo** |
| Mutaciones detectadas | **5/5**, incluida la que salta la frontera |
| Hashes restaurados | **byte a byte**, CRLF preservado |
| Temporales del harness | **0** |

### Los tres huecos que encontró la auditoría

**1. El harness de mutation testing no existía en el repositorio.** Los informes
anteriores citaban «8/8» y «11/11», pero los scripts vivían en `_q/`, que se
borró como temporal. La propiedad era real pero **irreproducible para el
equipo**. Ahora existe `dfchron/pruebas/probar_mutation_frontera.py`.

**2. Ninguna prueba demostraba el flujo de ejecución real.** `TestDelegacion`
comparaba *valores*: si la API calculase lo mismo por su cuenta, pasaría igual.
Ahora `TestDelegacionReal` **instrumenta** el servicio: envuelve las seis
operaciones, pide 10 rutas por HTTP y exige que el registro contenga la
operación esperada.

**3. `probar_api.py` y `probar_web.py` NO detectaban un `dataset_id` corrupto.**
Comprobado con ejecución real:

```
dataset_id invertido:
  probar_integracion_consulta.py  -> DETECTA
  probar_api.py                   -> *** NO DETECTA ***
  probar_web.py                   -> *** NO DETECTA ***
```

Ambas suites pasaban con el mundo **equivocado** anunciado. Sigue siendo cierto
hoy, y por eso la prueba nueva no compara: instrumenta.

---

## MAPA DE CONSUMIDORES (fase 0, obtenido con `ast`)

No con expresiones regulares: el contexto de ventana de un `Select-String`
etiqueta mal las rutas multilínea.

| Endpoint | Tipo | Fuente | ¿Pasa por `servicio_consulta`? | ¿Debe? |
|---|---|---|---|---|
| `/api/figuras/{id}` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/entidades/{id}` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/sitios/{id}` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/artefactos/{id}` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/eventos/{id}` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/figuras/{id}/relaciones` | Hecho | ADAPTADOR | Sí | Sí |
| `/api/consulta/*` (7) | Hecho | ADAPTADOR | Sí | Sí |
| `/api/salud`, `/api/stats`, `/api/estadisticas` | Navegación | `servicio.py` | No | No |
| `/api/limitaciones` | Navegación | `servicio.py` | No | No |
| `/api/buscar`, `/api/buscar/{tipo}` | Navegación | `servicio.py` | No | No |
| `/api/listar/{tipo}` | Navegación | `servicio.py` | No | No |
| `/api/eventos` (explorador) | Navegación | `servicio.py` | No | No |
| `/api/eventos/tipos`, `/api/relaciones/tipos`, `/api/conflictos` | Navegación | `servicio.py` | No | No |
| `/api/geografia*` (5) | Navegación (dato secreto) | `servicio.py` | No | No |
| `/api/exportar` | Navegación | `servicio.py` | No | No |
| Colecciones por entidad (14) | Navegación | `servicio.py` | No | No |

**Ninguno de los de navegación accede al dataset**: todos van por `servicio.py`,
que envuelve al núcleo. Eso es lo que la regla 8 prohíbe; ninguno va a
`nucleo.py` ni a los ficheros.

**La Web tampoco accede al dataset.** `probar_web.py:486-494` veta
`legends.xml`, `.jsonl`, `readFileSync`, `XMLHttpRequest` sobre el código real
de `app.js`.

**Misión:** cerrar la fase H. Que `API → servicio_consulta → núcleo` y
`WEB → servicio_consulta → núcleo` sean las rutas **reales** de consulta.

**Resultado: COMPLETADA Y DEMOSTRADA.**

| Métrica | Valor |
|---------|-------|
| Regresiones de compatibilidad | **0** sobre 48 rutas |
| Rutas idénticas byte a byte | 29 |
| Rutas ampliadas (aditivas) | 19 |
| Endpoints migrados | 7 (6 fichas + relaciones) |
| Endpoints nuevos | 7 (`/api/consulta/*`) |
| Pruebas nuevas | **53**, todas en verde |
| Mutation testing del adaptador | **8/8 detectadas** |
| Regresión completa | **29 suites, 1124 tests, 0 fallos** |
| Dataset | `v1-04170363943d4ba1` — **intacto** |
| IA introducida | **Ninguna** |

---

## MUTATION TESTING PERMANENTE

`dfchron/pruebas/probar_mutation_frontera.py` — 3 tests, en el repositorio.

| Mutación | Detectada por |
|----------|---------------|
| A · `dataset_id` anuncia otro mundo | integración |
| B · evidencia se borra | integración |
| C · `NOT_VERIFIED` pasa a `FOUND` | integración |
| D · relaciones deja de delegar | integración, API |
| **E · el adaptador se salta la frontera** | **integración, API, Web** |

**5/5.** La E es la importante: reproduce lo que la regla 9 prohíbe
(`API → índice` en vez de `API → servicio_consulta → índice`).

### Garantías del harness

1. Guarda los **bytes** originales, no una re-serialización.
2. Restaura en un `finally`.
3. **Verifica por hash** que la restauración es exacta.
4. **Preserva CRLF/LF** escribiendo en binario.

El punto 4 no es teórico. En una auditoría anterior un harness temporal
reescribió `servicio_consulta.py` con LF y cambió su hash (`0A5B6B1C…` →
`7CFD4CD4…`) con el contenido **idéntico**. Por eso hay un test que comprueba
que no queden finales de línea mezclados ni BOM.

### Lo que el harness NO cubre

`probar_perimetro_ia.py` **no detecta la mutación E**. No es un fallo: esa suite
prueba el perímetro IA, que llama al servicio directamente y no pasa por el
adaptador HTTP.

---

## ESTADO FINAL

```
INTEGRACIÓN API/WEB CERRADA CON RESERVAS
```

**Reservas, enumeradas como manda la fase 16:**

1. **34 endpoints de navegación quedan fuera de la frontera.** No es un defecto:
   están documentados con su condición de migración. Pero la frontera cubre las
   *consultas de hechos*, no el 100 % de la API. Quien lea `/api/stats` no
   obtiene `dataset_id`.

2. **`probar_api.py` y `probar_web.py` no validan `dataset_id` por sí solas.**
   Solo la suite de integración lo hace. Si alguien las ejecutara aisladas, una
   corrupción de `dataset_id` pasaría. El harness lo demuestra explícitamente.

3. **El fallback de `app.js:86-91` sigue presente**: si un envelope llega sin
   `estado`, la Web lo deduce de `ok`/`error`. Para las rutas migradas nunca se
   activa. Para las de navegación, un error que no sea `NO_ENCONTRADO` se muestra
   como `DATA_UNAVAILABLE` — conservador, nunca inventa `FOUND`, pero es una
   decisión del cliente. **No se corrigió en silencio**: está aquí.

### La afirmación pedida, y su demostración

> Si un consumidor externo consulta un hecho que pertenece al contrato de
> consulta, la respuesta procede de la misma frontera determinista que utilizará
> cualquier futuro consumidor, sin duplicar la autoridad del núcleo.

**Demostrado por ejecución, no por imports:**
- `TestDelegacionReal` instrumenta el servicio y comprueba que 10 rutas lo
  ejecutan.
- La mutación E —el adaptador saltándose la frontera— la detectan integración,
  API y Web.

**Todavía no existe ningún modelo IA.** Ninguna integración IA se ha iniciado.

---

# HISTÓRICO (informe original de la fase H)

Lo que sigue es el informe tal como se redactó al cerrar la fase H. Sus cifras
siguen siendo válidas **salvo donde la verificación de arriba las corrige**.

## A. Estado inicial

La fase H anterior había creado `dfchron/servicio_consulta.py` (66 pruebas,
12/12 mutaciones) pero **no lo había conectado a nada**. Ni la API ni la Web lo
usaban. El hueco era real y medido:

```
servicio.figura("712") → claves: certainty, data, meta, ok, status
¿dataset_id?  False      ¿evidence?  False      ¿identity?  False
```

El envelope no transportaba **de qué mundo** venía el dato, y la frontera HTTP
ignoraba los cinco estados que el servicio sí distinguía.

**Línea base medida antes de tocar nada:** `probar_api.py` 54 pruebas OK,
`probar_web.py` 65 pruebas OK.

---

## B. Auditoría de API

`dfchron/api.py`, servidor `http.server` puro, 40 endpoints registrados.

**Hallazgo principal: la API ya delegaba.** Todas las fichas llamaban a
`servicio.figura/entidad/...`, es decir, ya iban por `servicio → núcleo`. Lo que
no hacían era pasar por la capa que añade identidad, evidencia y estado.

**Segundo hallazgo, no previsto por la misión: hay DOS Webs.**

| Web | Ubicación | ¿Accede al dataset? |
|-----|-----------|---------------------|
| Clásica | `dfchron/web/` (`index.html`, `app.js`, `estilo.css`) | No, solo `/api/...` |
| Astro | `dfchron/site/src/` (TypeScript, `astro build`) | No, todo por `lib/api.ts` |

Ambas ya respetaban la frontera: ninguna lee XML, JSONL ni el índice. Ninguna
tenía `Web → dataset`. Ese antipatrón **no existía** y no hubo que arreglarlo.

---

## C. Auditoría Web

Ninguna de las dos Webs decidía conocimiento, pero **tampoco mostraba** el
estado ni la evidencia, porque no llegaban. Antes de esta misión, una entidad
inexistente y un atributo no determinable se pintaban igual.

Se verificó que la URL de la API se escribe **en un solo sitio** en cada Web
(`app.js:45` y `lib/api.ts`), y que ninguna referencia ficheros del dataset.

---

## D. Endpoints migrados

Siete. Todos ahora pasan por `adaptador_consulta` → `servicio_consulta`:

| Endpoint | Antes | Ahora |
|----------|-------|-------|
| `/api/figuras/{id}` | `svc.figura` | `obtener_entidad("figura", …)` |
| `/api/entidades/{id}` | `svc.entidad` | `obtener_entidad("entidad", …)` |
| `/api/sitios/{id}` | `svc.sitio` | `obtener_entidad("sitio", …)` |
| `/api/artefactos/{id}` | `svc.artefacto` | `obtener_entidad("artefacto", …)` |
| `/api/eventos/{id}` | `svc.evento` | `obtener_entidad("evento", …)` |
| `/api/figuras/{id}/relaciones` | `svc.figura_relaciones` | `buscar_relaciones(…)` |

### Endpoints nuevos: el contrato completo por HTTP

| Ruta | Operación del servicio |
|------|------------------------|
| `GET /api/consulta/contrato` | `contrato()` — el contrato, legible sin leer código |
| `GET /api/consulta/entidad/{tipo}/{id}` | `obtener_entidad` |
| `GET /api/consulta/atributo/{tipo}/{id}/{atributo}` | `obtener_atributo` |
| `GET /api/consulta/relaciones/{id}` | `buscar_relaciones` |
| `GET /api/consulta/contar/{tipo}?campo=&valor=` | `contar` |
| `GET /api/consulta/verificar?…` | `verificar` |
| `GET /api/consulta/evidencia/{tipo}/{id}` | `obtener_evidencia` |

No existían: antes `/api/consulta/...` daba **404**, y sigue dando 404 para
cualquier otra cosa bajo ese prefijo.

---

## E. Endpoints deliberadamente no migrados

**Herramientas de exploración** (sin equivalente en `servicio_consulta`, y
migrarlas obligaría a inventar operaciones que el servicio no tiene):

`/api/salud` · `/api/stats` · `/api/limitaciones` · `/api/buscar` ·
`/api/listar/{tipo}` · `/api/eventos` · `/api/eventos/tipos` ·
`/api/relaciones/tipos` · `/api/conflictos` · `/api/geografia/*` · `/api/exportar`

**Colecciones por entidad** (listar *qué más* hay alrededor, no *si algo es
cierto*): `figuras/{id}/eventos` · `/cronologia` · `/artefactos` ·
`/identidad` · `entidades/{id}/miembros` · `/sitios` · `/eventos` ·
`/cronologia` · `sitios/{id}/eventos` · `/cronologia` · `/figuras` ·
`artefactos/{id}/propietarios` · `/eventos` · `eventos/{id}/participantes`

**Motivo:** son navegación de registros, no consulta de un hecho con estado.
Crear una operación de servicio para ellos sería *inventar* funcionalidad, que es
justo lo que la arquitectura prohíbe. Se dejan en `servicio`, que ya es la capa
de envelopes.

**Verificado:** sus respuestas son **idénticas byte a byte** antes y después.
---

## F. Delegación en `servicio_consulta`

`adaptador_consulta.py` es un adaptador puro. Tres pruebas lo blindan:

| Prueba | Qué garantiza |
|--------|---------------|
| `test_el_adaptador_no_toca_el_nucleo` | No importa `nucleo`, ni `obtener_archivo`, ni `Archivo(` |
| `test_la_api_delega_en_el_servicio` | HTTP y servicio dan el mismo `data`, `estado`, `identity`, `evidence` |
| `test_el_contrato_es_la_unica_fuente_de_la_api` | El adaptador no declara tipos por su cuenta |

`verificar()` sigue delegando en `verificacion_semantica`. **No hay segundo
verificador.** El adaptador no implementa reglas: traduce.

---

## G. Compatibilidad

**Cómo se demostró.** No con una opinión: fotografiando 48 rutas **antes** (con
las líneas de ruta revertidas en una copia en memoria) y **después**, y
comparando clave por clave.

```
0 regresiones · 19 rutas ampliadas · 29 idénticas byte a byte
```

### Dos regresiones se detectaron y se corrigieron

**1. Endurecer una ruta con clientes.** La primera versión rechazaba parámetros
desconocidos y validaba el límite estrictamente. El oráculo lo detectó al
instante: `?limite=99999` pasó de **200 a 400**.

**2. El recorte mal hecho.** Corregido eso, apareció la segunda: legacy
`?limit=99999999` devolvía **200 recortado a 500**; la versión estricta devolvía
**400**. El oráculo lo cazó al ampliar la captura con los casos de límite.

La causa era usar validación estricta en una ruta preexistente. La solución
**no fue relajar las pruebas**: fue reutilizar `config.limite_seguro`, que es la
misma normalización de antes, y documentar en el propio adaptador por qué esa
línea parece redundante y no lo es (ver §K).

**Asimetría deliberada y documentada:**

| Ruta | Params desconocidos | `limit=-5` |
|------|---------------------|------------|
| `/api/figuras/{id}/relaciones` (existía) | se ignoran | **200** recortado |
| `/api/consulta/relaciones/{id}` (nueva) | **400** | **400** |

La ruta vieja conserva su permeabilidad porque tiene clientes. La nueva es
estricta porque no hay compatibilidad que preservar.

---

## H. Evidencia

La API **serializa**; no fabrica. `dataset_id`, `evidence` e `identity` se
copian del resultado del servicio.

```json
"dataset_id": "v1-04170363943d4ba1",
"evidence": {
  "entidad": "figura", "df_id": "712",
  "datos_utilizados": ["nombre", "race", "caste", "..."],
  "funcion": "nucleo.Archivo.ficha_figura",
  "fuente": ["legends.xml"],
  "state_version": "v1-04170363943d4ba1"
}
```

**Pruebas:** `test_dataset_id_llega`, `test_state_version_llega_en_la_evidencia`,
`test_el_endpoint_de_evidencia`.

**Y una prueba negativa:** `test_el_dataset_no_es_un_reloj` comprueba que la
cabecera **no** contiene `expires`, `ttl`, `caduca`… Se comprueban las *claves*,
no subcadenas: un primer intento buscaba texto y daba un falso positivo trivial
(`settled` contiene `ttl`). Se corrigió la prueba, no el código.

---

## I. Identidad

| Tipo | `identity` | HTTP | Estado |
|------|-----------|------|--------|
| `figura`, `entidad`, `sitio`, `evento`, `artefacto` | `{"tipo", "df_id"}` | 200 | `FOUND` |
| `relacion`, `era`, `suplemento` | **`null`** | 200 | `NOT_VERIFIED` |

Un `identity: null` viaja como `null`. La API **no lo completa**, y la Web lo
pinta como `UNKNOWN` con la explicación, no con un id inventado.

`test_no_hay_ids_artificiales` comprueba que no aparecen `record_id`, `posicion`,
`indice` ni `hash`.

---

## J. Relaciones

Se **leen**, no se reconstruyen. `buscar_relaciones` delega en
`servicio.figura_relaciones`, que aplica el grafo dirigido. La API no calcula
tipos ni aristas, y la Web no dibuja nada que la API no le devuelva.
---

## K. Paginación

| Capa | Máximo | Quién decide |
|------|--------|--------------|
| `servicio_consulta` | 1000 | el servicio |
| `config` (rutas viejas) | 500 | el límite histórico de la API |
| `/api/consulta/relaciones/{id}` | 1000 | el servicio; pedir más da **400** con el máximo declarado |

**Una línea que parece redundante y no lo es.** El adaptador normaliza el límite
con `config.limite_seguro` antes de llamar al servicio, que *vuelve* a
normalizarlo. Sin esa primera normalización, un `limit=-5` llegaría crudo al
servicio y volvería `INVALID_QUERY` → **400**, donde antes había **200**. Está
documentado en el docstring para que nadie la «simplifique» fuera.

**Y un hueco de prueba que encontró el mutation testing:** la figura 712 **no
tiene relaciones**, así que ahí el límite es invisible. Un recorte roto pasaba
desapercibido. Se añadió `test_el_limite_se_aplica_a_un_tipo_con_relaciones`,
que usa la figura **345** (6 relaciones) y verifica 1 → 1, 2 → 2, 500 → 6.

---

## L. Errores

Cada estado conserva su código HTTP, y son **distintos a propósito**:

| Estado | HTTP | Significado |
|--------|------|-------------|
| `FOUND` | 200 | |
| `NOT_FOUND` | 404 | El dato **no existe**. Ausencia confirmada |
| `NOT_VERIFIED` | **200** | **No se pudo determinar.** Un 404 afirmaría algo más fuerte y falso |
| `INVALID_QUERY` | 400 | |
| `DATA_UNAVAILABLE` | 503 | Fallo técnico, no ausencia |

El caso central, `test_no_verificado_no_es_404`, falla si alguien cambia esa
decisión:

> `NO_VERIFIED` no puede ser 404: diría que no existe.

---

## M. Seguridad

Nada se relajó. `adaptador_consulta` no toca el sistema de ficheros.

| Prueba | Qué cubre |
|--------|-----------|
| `test_traversal` | `..%2f..%2f`, `%2e%2e%2f`, `../../etc/passwd` |
| `test_traversal_doblemente_codificado` | `%252e%252e%252f` |
| `test_no_se_sirven_ficheros` | `/static/../../config.py`; no se filtran rutas internas |
| `test_metodos_de_escritura_rechazados` | POST/PUT/DELETE/PATCH → **405** |
| `test_no_se_filtra_traceback` | ni `Traceback`, ni rutas del proyecto |
| `test_id_enorme` | 400, no reventón |

Las protecciones de `api.py` (solo `127.0.0.1`, solo GET, sin ficheros de
disco) **no se tocaron**; el oráculo confirma que sus respuestas no cambiaron.

---

## N. Pruebas API

`dfchron/pruebas/probar_integracion_consulta.py` — **53 pruebas, 53 en verde**,
en 11 grupos: delegación, estados, evidencia, identidad, relaciones, paginación,
validación, seguridad, compatibilidad, unificación y Web.

`probar_api.py` (54) y `probar_web.py` (65) siguen **sin tocar** y en verde.

---

## O. Pruebas Web

La Web **muestra**, no decide:

- `estadoDe()` **lee** `env.estado`. No lo deduce, no lo recalcula.
- `test_not_verified_no_se_texto_como_no_existe` comprueba el **texto**.
- `test_not_verified_tiene_color_distinto_de_not_found` comprueba el **color**:
  si compartieran color, la distinción desaparecería en pantalla.
- `test_la_web_no_accede_al_dataset` veta `legends.xml`, `.jsonl`,
  `readFileSync`, `XMLHttpRequest` y `original_data`.

El sitio Astro tiene las mismas garantías
(`test_el_sitio_astro_tiene_las_mismas_garantias`) y **`astro build` compila
limpio**, lo que valida el TypeScript.

---

## P. Prueba de unificación

`test_servicio_api_y_web_coinciden` — la misma consulta por las tres rutas:

```
servicio_consulta.obtener_entidad("figura", "712")   → dato, estado, identity, evidence
GET /api/consulta/entidad/figura/712                  → idéntico en las 5 claves
web/app.js                                            → pinta env.identity, env.evidence,
                                                        env.dataset_id, env.estado
```

Las tres parten del mismo resultado semántico. El formato visual difiere; el
significado, no.

---

## Q. Mutation testing

**8/8 mutaciones detectadas.** Tres sobre el servicio (que es quien decide esos
campos), cinco sobre el adaptador.

| Mutación | Detectada |
|----------|-----------|
| servicio: se borra la evidencia | Sí |
| servicio: se anuncia un dataset inventado | Sí |
| servicio: se inventa identidad | Sí |
| adaptador: `NOT_VERIFIED` → 404 | Sí |
| adaptador: `NOT_FOUND` → 200 | Sí |
| adaptador: se ignoran params desconocidos | Sí |
| adaptador: el id deja de acotarse | Sí |
| adaptador: el límite se pasa sin normalizar | Sí |

**Dos mutaciones sobrevivieron al principio, y las dos eran síntomas reales:**

1. **Cambiar `NOT_FOUND: 404` por 200.** Sobrevivió porque el servicio ya pone
   `http_status: 404` y `_http_de` lo respeta antes de mirar el mapa: esa línea
   del mapa es una red de seguridad. Se añadió
   `test_el_mapa_estado_http_es_el_declarado`, que la ejerce directamente.

2. **Ignorar el límite.** Sobrevivió porque, para la figura 712, límite 200 y
   límite 100000 dan **la misma respuesta**: no tiene relaciones. Era un hueco
   de prueba real, no un mal mutante. Se añadió la prueba con la figura 345.

En ningún caso se relajó una prueba. En los dos casos se añadió cobertura.

El servicio obtiene la lista de tipos del núcleo; **no hay constante duplicada**
en el adaptador. `test_relaciones_delegan_en_el_servicio` compara la respuesta
---

## R. Regresión completa

```
29 suites · 1124 tests · 0 fallos
```

Incluye las 66 de `servicio_consulta`, las 53 nuevas, `probar_api` (54),
`probar_web` (65), adversarial, determinismo y reproducibilidad.

**Nota sobre el recuento.** Un primer barrido recogió 24 suites en
`dfchron/pruebas/`. Las 5 restantes (`probar_nucleo`, `probar_integracion`,
`probar_adversarial`, `probar_adversarial_nucleo`,
`probar_verificacion_semantica`) viven en `00_SOURCE/tools/`. El total correcto
es **29**, coherente con la cifra de la fase anterior más la suite nueva.

**Un fallo documental, real y útil.** `probar_documentacion_indice.py` falló
al entrar en la regresión: el índice ya referenciaba este informe y el fichero
**todavía no existía**. Es exactamente el fallo que esa suite existe para
detectar, y se resolvió creando el fichero, no silenciando la prueba.

---

## S. Hashes

**Producción intacta.** `nucleo.py`, `servicio.py`, `validar_semantica.py`,
`actualizar_datos.py`, `cargar_legends.py`, `integrar_legends.py`, `rutas.py`,
`verificacion_semantica.py`, `config.py`, `ia_conocimiento.py`,
`ia_estructura.py`, `ia_verificacion.py`, `contrato_ia.py`: **sin cambios**.

**Ficheros que sí cambiaron, y por qué:**

| Fichero | Cambio | Motivo |
|---------|--------|--------|
| `dfchron/api.py` | 7 rutas delegan + 7 rutas nuevas | Punto de integración (D18) |
| `dfchron/adaptador_consulta.py` | **nuevo** | El adaptador |
| `dfchron/pruebas/probar_integracion_consulta.py` | **nuevo** | 53 pruebas |
| `dfchron/web/app.js` | Muestra estado y evidencia | Fases 13–14 |
| `dfchron/web/estilo.css` | Estilos de los 5 estados | Fase 14 |
| `dfchron/site/src/lib/api.ts` | Tipos y helpers del contrato | Fase 13 |
| `dfchron/site/src/lib/vistas.ts` | Muestra estado y evidencia | Fase 13 |
| `dfchron/site/src/styles/components.css` | Estilos de los 5 estados | Fase 14 |

`servicio_consulta.py` **no se modificó** (solo se mutó temporalmente durante el
mutation testing, y se restauró verificado por hash).

`dataset_id` = `v1-04170363943d4ba1`, **intacto**.

**Determinismo:** tres procesos separados produjeron respuestas
**byte a byte idénticas** (`sha256 dd16215fea17ac3…`).

---

## T. Limitaciones restantes

1. **`NOT_VERIFIED` con HTTP 200 y `ok: false`.** Es deliberado, pero un
   cliente que solo mire `ok` y el status HTTP leerá «algo va mal» donde lo
   correcto es «no consta». Debe leer `estado`.

2. **El mapa `HTTP_POR_ESTADO` es en parte una red de seguridad.** El servicio
   suele traer `http_status` ya puesto, así que el mapa casi no se ejerce por
   HTTP. Se pruebe directamente (§Q).

3. **Doble normalización del límite** en las rutas migradas (§K). Necesaria
   para no romper el 200 existente, pero confunde al leer. Documentada.

4. **`identity` para un id inexistente.** `obtener_entidad("figura", "999")`
   devuelve `identity: {"tipo": "figura", "df_id": "999"}` junto a
   `NOT_FOUND`. Es el id **consultado**, no una afirmación de existencia: el
   `estado` es el que dice que no existe. Documentado; no cambiado por no
   tocar `servicio_consulta` en esta misión.

5. **Las colecciones por entidad no están en el contrato** (§E). Para quien
   necesite «qué más sabe de esta figura», el contrato todavía no es suficiente.

6. **`/api/consulta/*` es de solo lectura**, como toda la API. No hay
   paginación por `offset` en las rutas nuevas: solo `limit`.

---

## Conclusión

> **API y Web son consumidores del mismo contrato determinista de consulta.**

Y es demostrable con pruebas: la unificación de la §P, las 53 pruebas de
integración, el 8/8 de mutation testing y el 0 de regresiones sobre 48 rutas.

La arquitectura queda como se pidió:

```
WEB ─▶ API HTTP ─▶ adaptador ─▶ servicio_consulta ─▶ NÚCLEO ─▶ DATASET
```

Sin ruta paralela. Sin lógica de conocimiento fuera del servicio. Sin
identidades inventadas. Sin estados colapsados.

**La IA sigue completamente fuera del sistema.**
HTTP con la del servicio, dato a dato.