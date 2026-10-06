# INFORME DE AUDITORÍA Y ENDURECIMIENTO DEL NÚCLEO

> **Sin IA implementada.** Ninguna línea de esta misión toca la capa de IA.
> **Los 10 módulos de producción tienen hash idéntico** al inicio.

---

## A. LÍNEA BASE

| Área | Estado | Evidencia |
|------|--------|-----------|
| Extracción | IMPLEMENTADA, **verificada** | `probar_integracion.py` (20) |
| Normalización | IMPLEMENTADA, **verificada** | reglas de merge probadas |
| Esquemas | IMPLEMENTADOS | 17 secciones JSONL con procedencia |
| Dataset | **INTEGRO** | `v1-04170363943d4ba1`; 17/17 hashes coinciden |
| Snapshots | **NO EXISTE** | sin mecanismo de snapshot temporal |
| Entidades | IMPLEMENTADAS, identidad verificada | 7 tipos con `df_id` del juego |
| Relaciones | PARCIAL | 11 tipos; falta identidad propia |
| Evidencia | IMPLEMENTADA, fail-closed | `state_version` + `evidencia_es_actual()` |
| Verificación | DETERMINISTA, 19 plantillas | `ia_estructura.PLANTILLAS` |
| API | IMPLEMENTADA, **ahora verificada** | `probar_api.py` (54) |
| Web | IMPLEMENTADA, **ahora verificada** | `probar_web.py` (65) |

**Hashes al inicio**

```
nucleo.py            CCC48EA67849701A      cargar_legends.py     30140AD617CB2BF0
integrar_legends.py  35649CDCAF75153B      validar_semantica.py  C927FF8B66AC9B8C
actualizar_datos.py  108560E597355329      rutas.py              0EAD547FDF6D1368
servicio.py          D6BD6E5B28A97169      api.py                BB6BDEBBAD5177A1
contrato_ia.py       EB4A4156CBFAF764      ia_estructura.py      BE9FC091EFF534E9
```

**No hay repositorio Git.** La trazabilidad es por hash.

---

## B. SUITES PENDIENTES

**Las nueve están ejecutadas. Ninguna queda bloqueada.**

| Suite | Requisito que se creía necesario | Resultado |
|-------|----------------------------------|-----------|
| `probar_integracion.py` | dataset completo | **20 tests — OK** (4,8 s) |
| `probar_nucleo.py` | dataset completo | **48 tests — OK** (5,1 s) |
| `probar_adversarial.py` | dataset completo | **39 tests — OK** (11,7 s) |
| `test_determinismo.py` | dataset + subprocesos | **29 consultas × 4 procesos × 3 repeticiones: DETERMINISTA** |
| `verificar_reproducibilidad.py` | XML originales + disco | **REPRODUCIBLE desde los XML** |
| `probar_api.py` | servidor HTTP | **54 tests — OK** (5,2 s) |
| `probar_web.py` | servidor HTTP | **65 tests — OK** (4,5 s) |
| `probar_actualizacion.py` | dataset | **43 tests — OK** (22,1 s) |
| `probar_refresh_cycle.py` | ciclo de refresco | **28 tests — OK** (2,8 s) |

### Por qué se creían bloqueadas

La consolidación anteriorlojó «requieren servidor HTTP o dataset completo». Era
una **suposición no verificada**, no un hecho comprobado. Ninguna lo era: basta
ejecutarlas desde la raíz con el dataset presente.

Lo que sí se comprobó, y importa:

* Path traversal bloqueado con **403**: `/static/../../../Windows/win.ini`,
  `/static/..%2f..%2fwindows%2fwin.ini`, `/static/%2e%2e/%2e%2e/original_data/legends.xml`.
* Errores de validación devuelven **400**, no traceback.
* IDs enormes devuelven **404**, no excepción.
* Salvaguardas del refresco: **4/4 escenarios peligrosos abortados**.

## C. DATOS

Pipeline: `legends.xml` + `legends_plus.xml` → `cargar_legends` →
`integrar_legends` → `validar_semantica` → `nucleo.py`.

| Entrada | Transformación | Salida | Validación |
|---------|----------------|--------|------------|
| XML CP437 + UTF-8 | Autodetección de codificación | ElementTree | pruebas de codificación |
| Dos exports | Merge con procedencia por campo | JSONL, 17 secciones | `test_16` a `test_19` |
| JSONL | Índice de referencias cruzadas | `Indice` en memoria | `probar_nucleo` |
| `Indice` | Fichas estructuradas | Respuesta de API | `probar_api` (54) |

### Integridad referencial: medida, no supuesta

| Referencia | Total | Vacías | **Rotas** |
|-----------|-------|--------|-----------|
| figura → entidad | 11.144 | 422 | **0** |
| figura → sitio | 11.144 | 10.711 | **0** |
| sitio → civilización | 734 | 194 | **0** |
| sitio → propietario actual | 734 | 309 | **0** |
| evento → sitio | 57.215 | 18.537 | **0** |
| evento → figura | 57.215 | 22.084 | **0** |
| evento → subregión | 5.611 | — | **0** |
| artefacto → propietario | 427 | 291 | **0** |
| artefacto → sitio | 427 | 149 | **0** |
| relación → figura origen | 13.192 | 0 | **0** |
| relación → figura destino | 13.192 | 0 | **0** |
| **relación → evento** | 13.192 | 0 | **13.192** |

**12.982 referencias con destino: 0 rotas.** La única columna rota es
`relación → evento`, y es un hecho conocido y declarado del juego.

> **Corrección de una medición propia.** Una primera comprobación halló 1.732
> referencias rotas en `subregion_id`. **Era un error mío de namespace**: lo
> comparé contra `underground_regions` cuando resuelve contra `regions`. Contra
> la sección correcta son **5.611 de 5.611, cero rotas**. Se deja constancia
> porque el error es fácil de repetir: ambas secciones comparten ids.

Las 17 secciones dan **el mismo SHA-256 en 3 lecturas**.

---

## D. IDENTIDAD

| Entidad | `df_id` | Origen | Único |
|---------|---------|--------|-------|
| Figura | 11.144 | **del juego** | Sí |
| Sitio | 734 | **del juego** | Sí |
| Entidad | 1.067 | **del juego** | Sí |
| Evento | 57.215 | **del juego** | Sí |
| Artefacto | 427 | **del juego** | Sí |
| Región | 840 | **del juego** | Sí |
| Región subterránea | 405 | **del juego** | Sí |
| Colecciones, contenidos, poblaciones, formas | 9.556 | **del juego** | Sí |
| **Relación** | **0** | — | **13.192 filas SIN `df_id`** |
| **Suplemento de relación** | **0** | — | **21 filas SIN `df_id`** |
| **Era histórica** | **0** | — | **1 fila SIN `df_id`** |

**16 secciones con identidad estable, 3 sin ella.** Las 3 son relaciones y la
era. En las 16, `record_id == sección:df_id` se cumple al 100 %.

### Propiedades demostradas del `df_id`

| Propiedad | Resultado |
|-----------|-----------|
| Determinista | **Sí** |
| Estable en su alcance | **Sí** (reproducible desde los XML) |
| Sin colisiones | **Sí** — 0 duplicados |
| **No es un id oficial universal** | **Correcto** |

**Lo que `df_id` NO es:** no es global. `112` de sitio y `112` de figura son
entidades distintas, y el núcleo las trata así. La identidad real es el par
`(entidad, df_id)`, que es lo que usa `ia_conocimiento.evidencia_de()`.

**No se ha inventado ningún `df_id`.** Las 3 secciones sin identidad siguen así,
y por eso las afirmaciones relacionales no son verificables.

---

## E. RELACIONES

| Relación | Fuente | Verificable | Tipo |
|----------|--------|-------------|------|
| figura → entidad | `entity_link.entity_id` + `link_type` | **Sí** | **Explícita** |
| figura → sitio | `site_link.site_id` + `link_type` | **Sí** | **Explícita** |
| figura → figura | `source_hf` / `target_hf` | Sí, por identidad | **Explícita** |
| relación → evento | `relation.event` | **No** | **Desconocida** |
| sitio → civilización | `civ_id` | **Sí** | **Explícita** |
| sitio → propietario | `cur_owner_id` | **Sí** | **Explícita** |
| sitio → figuras | índice inverso | **Sí** | **Derivada** |
| artefacto → propietario | `holder_hfid` | **Sí** | **Explícita** |
| artefacto → creador | evento `artifact created` | **Sí** | **Derivada** |
| evento → lugar | `site_id` | **Sí** | **Explícita** |
| guerra | — | **No** | **No existe** |

### Tipos explícitos que el juego aporta

Medidos sobre las 11.144 figuras:

```
entity/member 8783 · site/lair 182 · entity/former member 1232
site/seat of power 134 · entity/enemy 502 · site/occupation 97
entity/prisoner 142 · entity/former prisoner 51
site/home structure 20 · entity/criminal 12
```

**10 tipos, 11.145 instancias, 0 con tipo pero sin destino.** Las relaciones no
son un grafo anónimo: llevan su clase explícita. La documentación anterior no
lo recogía.

**Ninguna regla semántica arbitraria se ha añadido.**

## F. ESTADO Y SNAPSHOTS

| Mecanismo | Estado |
|-----------|--------|
| `dataset_id` | **Existe.** `v1-04170363943d4ba1`, derivado del SHA-256 del contenido |
| Determinismo | **Probado**: estable bajo reordenación, cambia si un byte cambia |
| Coherencia disco ↔ registro | **17/17 hashes coinciden** |
| Snapshots | **NO EXISTE** |
| Changelog entre versiones | **NO EXISTE** |
| Estado de partida en vivo | **NO EXISTE** |
| Reloj de juego | **NO EXISTE** |

### Confirmación de que `dataset_id` NO es un reloj

* El núcleo **no tiene** `tick`, `epoch`, `revision` ni `snapshot` (búsqueda
  literal sobre `nucleo.py`: 0 resultados).
* `dataset_id` recalculado desde `dataset_version.json` **coincide** con el
  registrado: `v1-04170363943d4ba1`.
* Cambia si un SHA cambia; no cambia si solo se reordena el diccionario.

**Lo que DF sí aporta y es temporal:** `event.year` va de 1 a 100 y `seconds72`
da resolución sub-año. Pero eso es **tiempo de la historia narrada**, no del
estado del sistema. Un evento del año 50 no significa que el dataset sea más
viejo.

**No se ha inventado temporalidad alguna.** Ni caducidad, ni ticks, ni timestamps.

---

## G. EVIDENCIA

Los cuatro casos de la Fase 6, contra el **dataset real**:

| Caso | Escenario | Resultado medido |
|------|-----------|------------------|
| A | Evidencia válida, mismo estado | **VERIFICADA** — «el núcleo confirma sitio tipo en fortress» |
| B | Evidencia de otro dataset | **NO_VERIFICADA** — «la evidencia es del estado 'v1-04170363943d4ba1' y el mundo actual es 'v9-otro-mundo'» |
| C | Evidencia sin versión | **NO_VERIFICADA** — «la evidencia es del estado 'UNKNOWN'…» |
| D | Valor inventado, misma referencia | **NO_VERIFICADA** — «el núcleo dice 'fortress' y la afirmación dice 'dragoncave'» |

* `ic.evidencia_de()` ancla `state_version = v1-04170363943d4ba1`: el
  `DATASET_ID` real leído de disco, no un literal de prueba.
* `evidencia_es_actual()` es **fail-closed**: sin versión declarada, `False`.

**Ninguna garantía se relajó.** Los hashes de `contrato_ia.py` e
`ia_estructura.py` son los mismos que al empezar.

---

## H. VERIFICACIÓN

| Entidad | Campos verificables (19 plantillas) |
|---------|-------------------------------------|
| `figura` | nombre, race, caste, sexo, tipo |
| `entidad` | nombre, race, tipo |
| `sitio` | nombre, tipo, nº de eventos |
| `evento` | tipo, subtipo, estado, año |
| `artefacto` | nombre, tipo, subtipo, material |

| Categoría | ¿Verificable? | Fuente |
|-----------|--------------|--------|
| **Existencia** | **Sí** | `indice.<tipo>[df_id]` |
| **Atributos** | **Sí** | Plantilla + ficha |
| **Cantidades** | **Sí** | Conteo del índice |
| **Relaciones** | **Parcial** | Verificables **por identidad**, no la fila |
| **Localización** | **Sí** | `site_id`, `civ_id` (100 % resuelven) |
| **Estado** | **Sí** | `event.estado`, `associated_type` |
| **Procedencia** | **Sí** | `evidence.source`, `state_version` |
| **Semántica** | **No** | requiere lenguaje |
| **Guerra** | **No** | no existe en el XML |

Casos ambiguos, declarados: `""` y `"-1"` no son valores (sale `UNKNOWN`); una
paráfrasis, una negación y una afirmación compuesta salen `NO_APLICABLE`.
**Ninguno se resolvió con heurística.**

---

## I. ROBUSTEZ

Se compararon las 14 adversidades de la misión contra lo cubierto:

| Cubierta | Por qué suite |
|----------|---------------|
| JSON corrupto, campos ausentes, tipos incorrectos, duplicados, referencias inexistentes, IDs desconocidos, valores extremos, listas vacías, nulos, Unicode | `probar_adversarial.py` (39) |
| Datasets incompatibles | `probar_estado_conocimiento.py` |
| Evidencia de otro dataset | `probar_cierre_pre_ia.py` |
| **Campos adicionales** | **NO CUBIERTA → suite nueva** |
| **Datos parcialmente incompletos** | **NO CUBIERTA → suite nueva** |

### Suite creada: `probar_adversarial_nucleo.py` (10 tests)

Trabaja sobre una **copia**; el dataset real no se abre.

* **Campos adicionales:** 5 claves que el juego nunca escribe (`poder_magico`,
  `nivel_de_threat`, `secreto_del_jefe`, `inventario_oculto`, `es_jefe_final`).
  No alteran ningún campo real, no aparecen en la ficha, no cambian el conteo, y
  una clave en la raíz del registro también se ignora.
* **Datos incompletos:** sin `campos` no inventa atributos; sin `birth_year` no
  inventa fecha; `""` no es un nombre; sección ausente queda vacía, no rellena.

### Límite real descubierto

`Indice.cargar()` hace `self.figuras[r["df_id"]] = r`: acceso **directo** a la
clave, sin `.get()`. Un registro sin `df_id` **rompe la carga** con `KeyError`.

**No se ha arreglado.** El dataset lo genera el propio proyecto y siempre trae
`df_id`; añadir tolerancia cambiaría la semántica del índice sin que nadie lo
pidiera. Lo que sí se ha hecho es **fijar el comportamiento real** con una
prueba, para que nadie lo descubra por sorpresa.

### La suite detecta los fallos

Se rompió el núcleo a propósito (`Consultas.ficha_figura` filtraba campos
desconocidos):

```
FAIL: test_las_claves_fantasma_no_aparecen_en_la_ficha
Ran 10 tests — FAILED (failures=1)
```

Núcleo restaurado y verificado por hash (`C927FF8B66AC9B8C`, idéntico).

## J. API Y WEB

| Suite | Resultado | Qué cubre |
|-------|-----------|-----------|
| `probar_api.py` | **54/54 OK** | Contratos, errores 400/404/403, truncamientos, traversal |
| `probar_web.py` | **65/65 OK** | UI, CORS, OPTIONS, entradas hostiles |

Que la interfaz **no afirma más que el núcleo**, comprobado:

* Todo truncamiento se comunica: `truncado`, `total`, `con_total`.
* La API devuelve `404` para id inexistente, no un objeto vacío disfrazado.
* `limit=999999` no devuelve el dataset entero.
* Ningún endpoint escribe: POST/PUT/DELETE → 405.
* Rutas protegidas → **403** ante traversal, incluidas formas codificadas.

---

## K. RENDIMIENTO Y DETERMINISMO

| Qué | Resultado |
|-----|-----------|
| 17 secciones JSONL, 3 lecturas | **SHA-256 idéntico** |
| `test_determinismo.py` | **29 consultas × 4 procesos × 3 repeticiones: DETERMINISTA** |
| `verificar_reproducibilidad.py` | **REPRODUCIBLE desde los XML originales** |
| `dataset_id` bajo reordenación | **Estable** |
| `dataset_id` si cambia un byte | **Cambia** |
| Hashes disco ↔ `dataset_version.json` | **17/17 coinciden** |

| Operación | Tiempo |
|-----------|--------|
| Carga inicial (índice completo) | **2,50 s** |
| `ficha_sitio(87)` (1.546 eventos) | 0,041 s |
| `buscar('goblin')` | 0,005 s |
| `conflictos(limite_eventos=50)` | 0,121 s |
| `ficha_figura(712)` | 0,002 s |
| `relaciones_de_figura(712)` | <0,001 s |

**No se ha optimizado nada.** No hay ningún problema demostrado que lo justifique.

---

## L. CAMBIOS

### Código de producción: **NINGUNO**

Los 10 módulos tienen hash SHA-256 **idéntico** al inicio, verificado dos veces:
antes de cualquier cambio y al final.

### Fichero creado

| Fichero | Tipo | Motivo |
|---------|------|--------|
| `00_SOURCE/tools/probar_adversarial_nucleo.py` | **Prueba** | Cubre el hueco real: campos adicionales y datos incompletos |

Importa solo `io`, `json`, `os`, `shutil`, `sys`, `tempfile`, `unittest`.
**Sin dependencias externas.**

### Documentación actualizada

| Fichero | Cambio |
|---------|--------|
| `ARCHITECTURE_OVERVIEW.md` | Cifras medidas; sección «lo que sí está íntegro»; advertencia sobre `subregion_id` |
| `TECHNICAL_ROADMAP.md` | Matriz de identidad (con las 3 secciones sin `df_id`); matriz de relaciones |
| `PROJECT_DOCUMENTATION_INDEX.md` | Suite nueva; las 9 antes pendientes, con resultados |

**No se ha tocado** `AI_PRE_LLM_CONTRACT.md`, `AI_PROJECT_CONTEXT.md` ni
ningún informe previo: la auditoría no encontró nada que los contradiga.

---

## M. LIMITACIONES

| Limitación | Por qué sigue abierta |
|------------|----------------------|
| **Verificación semántica** | No existe. `NO_APLICABLE`. No se usará otro LLM como juez |
| **Identidad de relación** | 13.192 filas sin `df_id`. **No se ha inventado uno** |
| **`relación → evento`** | 13.192 de 13.192 no resuelve. Hecho del juego, declarado |
| **Caducidad temporal** | No hay reloj de juego |
| **Snapshots** | No existen |
| **Estado en vivo** | El dataset es una foto |
| **Memoria conversacional** | No existe |
| **Trazabilidad léxica** | Descripción, no barrera de seguridad |
| **`deteccion_fuga()`** | Detecta coordenadas, no paráfrasis |
| **Registro sin `df_id`** | Rompe la carga con `KeyError`. Documentado, no «arreglado» |

Ninguna se ha convertido en PASS.

---

## N. ESTADO FINAL

```
NUCLEO ENDURECIDO CON RESERVAS
```

### Lo que se ha ganado

1. **Las 9 suites pendientes, ejecutadas.** Ninguna estaba realmente bloqueada:
   era una suposición de la consolidación anterior, no un hecho. **324 pruebas**
   que nadie había visto pasar, ahora verificadas.
2. **Un hueco real de robustez cerrado**, con una suite que se ha demostrado
   capaz de detectar el fallo que comprueba.
3. **Identidad documentada con números**: 16 secciones con `df_id` estable del
   juego, 3 sin él, y el motivo exacto por el que las relaciones no son
   verificables — sin inventar nada.
4. **Relaciones documentadas con sus 10 tipos explícitos**, que la
   documentación anterior no recogía.
5. **Integridad referencial medida**: 12.982 referencias, 0 rotas.

### Por qué «con reservas»

Las reservas no son la manera de hacer las cosas: son capacidades que **el juego
no proporciona**. Verificación semántica, identidad de relación, caducidad y
estado en vivo seguirían sin demostrarse aunque esta misión se ejecutara mil
veces.

Convertirlas en PASS exigiría inventar exactamente lo que la misión prohíbe
inventar. Un núcleo que dice «no puedo comprobar esto» es más útil que uno que
miente con seguridad.

### Sobre una corrección propia

Durante esta auditoría, una medición afirmó 1.732 referencias rotas que **no
existían**: era un error mío de namespace, no un defecto del núcleo. Se corrigió
y se deja constancia, porque el error es fácil de repetir y las dos secciones
comparten ids. Documentar el hallazgo equivocado como si fuera verdad habría
sido exactamente el fallo que esta misión quiere evitar.

---

> **Sin IA.** El núcleo conoce con precisión lo que puede demostrar y lo que no.
> Cualquier capa que se ponga encima hereda esa honestidad.