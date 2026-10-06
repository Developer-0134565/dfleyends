# INFORME — CAPA DE CONSULTA DETERMINISTA

Misión: construir una frontera de consulta estable para el conocimiento
estructurado del núcleo, **sin IA**.

Ficheros creados:

| Fichero | Qué es |
|---------|--------|
| `dfchron/servicio_consulta.py` | La capa |
| `dfchron/pruebas/probar_servicio_consulta.py` | Sus pruebas |
| `DATA_QUERY_SERVICE_CONTRACT.md` | El contrato |

---

## A. Estado inicial

El núcleo ya estaba maduro y —esto es lo importante— **ya tenía casi todo lo
que esta misión pedía**. Antes de escribir una línea se auditó qué existía.

| Componente | Existe | Funciona | Responsable |
|------------|--------|----------|-------------|
| Índice | Sí | Sí | `nucleo.Indice` / `nucleo.Archivo` |
| Consulta de entidades | Sí | Sí | `servicio.figura/entidad/sitio/evento/artefacto` |
| Consulta de atributos | Parcial | Sí | vía `ficha_*` del núcleo |
| Relaciones | Sí | Sí | `servicio.figura_relaciones` |
| Cantidades | Sí | Sí | `envolver_lista`, `meta.total` |
| Evidencia | Sí | Sí | `ia_conocimiento.evidencia_de` |
| Verificación | Sí | Sí | `00_SOURCE/tools/verificacion_semantica.py` |
| API HTTP | Sí | Sí | `dfchron/api.py` |
| Web | Sí | Sí | `dfchron/ui/` |

**El hueco real era uno, y no era el que parecía.** No faltaba consulta: faltaba
que la consulta **dijera de dónde viene**.

Comprobación directa sobre `servicio.figura("712")`:

```
claves del envelope: certainty, data, meta, ok, status
¿dataset_id?   False
¿evidence?     False
¿identity?     False
```

El envelope era correcto y estaba bien diseñado, pero **no transportaba
identidad ni evidencia**. Un consumidor recibía `{"ok": true, "data": {...}}` y
no tenía forma de saber si era de este mundo o de otro.

## B. Arquitectura encontrada

El proyecto **ya tenía una arquitectura de servicio adecuada**: `servicio.py`
es la capa intermedia entre la API y el núcleo, y define la forma de las
respuestas para que la UI local y la Web reciban los mismos objetos.

Se encontró además que el servicio ya tenía tres cosas que esta misión daba
por hecho de construir:

1. **Un envelope común** (`envolver_lista`, `envolver_ficha`, `envolver_estado`).
2. **Una taxonomía de errores** (`NO_ENCONTRADO`, `TIPO_DESCONOCIDO`,
   `CONSULTA_VACIA`…) con `ok: false` y códigos bilingües (`code`/`codigo`),
   explícitamente pensada para que un cliente nuevo no dependa del idioma.
3. **Paginación** con `truncado`, `limit` y `offset`.

Decisión derivada de la regla «no duplicar»: **la capa de consulta se apoya
encima de `servicio`, no al lado.** No se escribió un índice, ni una búsqueda,
ni una validación de identidad propias.

## C. Contrato definido

`DATA_QUERY_SERVICE_CONTRACT.md`, independiente de HTTP, Web, CLI e IA.

Definido en el módulo también, para que no dependa de un documento externo:

```python
consulta.contrato()   # operaciones, estados, códigos, límites, temporalidad
```

## D. Operaciones disponibles

Seis, deliberadamente pocas. Todas **delegan**:

| # | Operación | Delega en |
|---|-----------|-----------|
| 1 | `obtener_entidad(tipo, df_id)` | `servicio.*` |
| 2 | `obtener_atributo(tipo, df_id, atributo)` | la ficha del núcleo |
| 3 | `buscar_relaciones(origen, tipo_relacion, limite)` | `servicio.figura_relaciones` |
| 4 | `contar(tipo, filtro)` | el índice del núcleo |
| 5 | `verificar(tipo, id, predicado, objeto)` | **`verificacion_semantica`** |
| 6 | `obtener_evidencia(tipo, df_id, campos)` | **`ia_conocimiento`** |

**No existe un segundo verificador.** `verificar()` traduce el veredicto del
que ya había, y la prueba `test_delega_en_el_verificador_existente` lo fija.

## E. Estados de resultado

**No se inventaron estados nuevos.** El proyecto ya tenía `ok`, `certainty`
(`FACT`/`DERIVED`/`UNKNOWN`) y códigos de error, así que se reutilizaron.

| Estado | Significado | Cómo se expresa |
|--------|-------------|-----------------|
| `FOUND` | existe y es verificable | `ok: true` + `certainty` |
| `NOT_FOUND` | se consultó bien; **no existe** | código `NO_ENCONTRADO` (ya existía) |
| `NOT_VERIFIED` | se consultó bien; **no se puede determinar** | código `NO_VERIFICADO` (nuevo) |
| `INVALID_QUERY` | consulta no válida | código de `servicio` (ya existía) |
| `DATA_UNAVAILABLE` | falta la fuente | código `NO_DISPONIBLE` (nuevo) |

### Los dos códigos nuevos, y por qué son inevitables

`NOT_FOUND` y `NOT_VERIFIED` **no son lo mismo**:

> *No existe* afirma algo del mundo.
> *No se puede determinar* afirma algo de lo que sabemos del mundo.

Colapsarlos en un solo código —que era lo que habría hecho si no se añadían—
destruye precisamente lo que el criterio arquitectónico más importante exige:
**no transformar ausencia de evidencia en evidencia de ausencia**.

Son los **mínimos** añadidos; todo lo demás se reusa. La prueba
`test_los_codigos_prestados_existen_en_servicio` comprueba que cada código
«prestado» existe de verdad en `servicio.py`.

### Una corrección durante la misión

Se declararon cuatro códigos «prestados», entre ellos `LIMITE_INVALIDO`. La
prueba lo detectó: **ese código no existe en `servicio.py` ni en `config.py`**.
Se eliminó en lugar de rebajarlo. Ejemplo de por qué las pruebas de contrato
importan.

## F. Tratamiento de evidencia

**El hallazgo que justificaba la capa.** Cada resultado incluye:

```json
"evidence": {
  "entidad": "figura",
  "df_id": "712",
  "funcion": "nucleo.Archivo.ficha_figura",
  "fuente": ["legends.xml"],
  "state_version": "v1-04170363943d4ba1"
}
```

La procedencia **no se reimplementa**: `ia_conocimiento.evidencia_de()` ya la
construía y ya anclaba el `state_version` al `dataset_id` leído del disco.

Si la evidencia no se puede construir, el resultado la lleva a `null`. **No se
sustituye por una explicación inventada**: fallar al construir evidencia no
significa que el dato sea falso, y la capa no dice que lo sea.

## G. Identidad

| Tipo | Identidad |
|------|-----------|
| `figura`, `entidad`, `sitio`, `evento`, `artefacto` | `df_id` real del juego |
| `relacion`, `era`, `suplemento` | **ninguna demostrable** → `identity: null` |

Nunca se usa como identidad un índice de array, una posición, un nombre, un hash
ni un `record_id` posicional.

**Un problema real detectado por mutation testing.** La guarda de `_identidad`
resultó ser **código muerto**: `obtener_entidad` filtraba antes los tipos sin
identidad, así que la guarda nunca se ejecutaba y la mutation «se inventa un id
para lo que no tiene» **no fue detectada**.

Se corrigió el código (ahora `obtener_entidad` pasa `tipo` y las guardas lo
comprueban ellas mismas) **y se añadieron dos pruebas que la ejercitan
directamente**. Un test que solo comprueba un efecto colateral no puede detectar
un fallo en su causa.

## H. Relaciones

Solo relaciones **registradas**: 12 tipos literales del XML. No se reconstruyen,
no se infieren, no se inventan relaciones históricas.

La capa distingue dos situaciones que no son la misma, y las pruebas lo fijan:

- la figura existe pero **no tiene** esa relación → lista vacía (`FOUND`, 0);
- la figura **no existe** → `NOT_FOUND`.

Comprobado sobre el grafo real, con un par tomado del propio dataset
(`test_relacion_existente` usa `_par_real()`, no un caso inventado).

## I. Temporalidad

Respeta D14: **`dataset_id` identifica contenido, no es un reloj.**

- Sin caducidad: un `dataset_id` distinto no invalida nada.
- Sin «actual» ni «obsoleto».
- Sin `timestamp`, `tick` ni marcas de tiempo. La prueba
  `test_no_se_fabrica_una_marca_de_tiempo` comprueba que esas claves **no
  existen** en ningún resultado.
- `state_version` es el `dataset_id` real, y la prueba fija que coincide con el
  `dataset_id` de la respuesta.

**«Estado actual» no existe en el contrato**, porque no hay reloj que lo defina.
Lo que hay es «el contenido del `dataset_id` cargado», que es otra cosa.

## J. Errores

| Situación | Respuesta |
|-----------|-----------|
| Consulta válida + resultado existente | `FOUND` con evidencia |
| Consulta válida + entidad inexistente | `NOT_FOUND` |
| Consulta válida + dato insuficiente | `NOT_VERIFIED` |
| Consulta inválida | `INVALID_QUERY` |
| Fuente no disponible | `DATA_UNAVAILABLE` |

**Un error interno nunca se degrada a `NOT_FOUND`.** `contar()` captura la
excepción de carga del dataset y responde `DATA_UNAVAILABLE`, no «no hay
figuras».

## K. Determinismo

La misma consulta sobre el mismo dataset produce **exactamente** el mismo
resultado, byte a byte en su serialización.

Comprobado:
- misma consulta repetida → JSON idéntico;
- el orden de consultas anteriores **no** cambia el resultado;
- el resultado es serializable y sin referencias Python (`<class`,
  `object at 0x`);
- el orden de las claves es estable;
- **la ausencia de tiempo se prueba**, no se promete: ningún resultado
  contiene `timestamp`.

No depende del hash de Python, del orden de diccionarios externo, del sistema de
ficheros, del proceso ni de la hora actual.

## L. Seguridad

Sin endpoint HTTP nuevo: la capa se expone internamente primero, como pedía la
misión. Aun así se validan **todas** las entradas antes de tocar el núcleo:

| Entrada hostil | Respuesta |
|---------------|-----------|
| IDs enormes (`9`*40, `-`+`9`*40) | `NOT_FOUND` |
| `<script>`, `../../etc/passwd`, `\x00`, `'; DROP TABLE--` | `NOT_FOUND` |
| Unicode (`図`, `Ñandú`, `Ωμέγα`, `🜁`) | `NOT_FOUND` |
| Tipo no-string (`None`, `1`, `[]`, `{}`, `True`) | `INVALID_QUERY` |
| Filtro que no es un objeto | `INVALID_QUERY` |
| Filtro con valor anidado | `FOUND` con 0 coincidencias |
| `limite` a `10**9` | recortado a `LIMITE_MAXIMO` |
| `limite` inválido o `NaN` | `INVALID_QUERY` |

**Ninguna excepción escapa al consumidor**, que es lo que exige el contrato de
`servicio.error()`.

## M. API y Web

`servicio_consulta.py` **no** modifica `api.py` ni la Web. Se comprobó que ya
consumían `servicio`, que es la capa inferior de la que esta se apoya:

```
API ──┐
      ├─► servicio ──► núcleo
Web ──┘        ▲
               └── servicio_consulta (añade evidencia e identidad)
```

Cuando la API quiera, se apoya encima de esta capa y hereda el sobre con
evidencia sin cambiar su contrato. **No se alteró ningún consumidor existente**,
lo que además explica que las 30 suites sigan pasando sin modificación.

## N. Pruebas

`dfchron/pruebas/probar_servicio_consulta.py` — **66 pruebas, todas sobre el
dataset real**, agrupadas por la fase que cubren:

| Grupo | Qué fija |
|-------|----------|
| `TestContrato` | las 6 operaciones existen; el alcance declara lo que no puede |
| `TestEntidad` | FOUND / NOT_FOUND / INVALID_QUERY; evidencia y dataset siempre |
| `TestIdentidadNoInventada` | lo sin identidad no recibe id |
| `TestAtributo` | valor real; no se infiere; el centinela no es un valor |
| `TestRelaciones` | relación real del grafo; la de tipo inexistente no aparece |
| `TestContarYFiltrar` | filtro exacto, sin normalizar; campo inventado rechazado |
| `TestVerificar` | delega en el verificador; afirmación falsa no se verifica |
| `TestEvidencia` | `state_version` real; función del núcleo |
| `TestTemporalidad` | sin caducidad ni marcas de tiempo |
| `TestLimitesYPaginacion` | recorte, máximo duro, límites inválidos |
| `TestDeterminismo` | misma consulta → mismo JSON |
| `TestInmutabilidad` | hash del dataset idéntico tras consultar |
| `TestAdversarial` | entradas hostiles, sin excepciones |

Dos de ellas merecen mención por lo que fijan:

- `test_el_orden_de_consulta_no_cambia_el_resultado`: consulta otras entidades
  en medio y comprueba que la primera no se altera.
- `test_el_resultado_es_una_copia`: muta lo devuelto y comprueba que el núcleo
  no se entera.

## O. Mutation testing

**12 mutaciones deliberadas, 12 detectadas.** Se rompió una por una y se
restauró:

| Mutación | Detectada |
|----------|-----------|
| búsqueda: la ficha devuelve cualquier cosa | Sí |
| estado: inexistente se declara encontrado | Sí |
| estado: lo no verificable pasa a FOUND | Sí |
| evidencia: se borra la evidencia entera | Sí |
| identidad: se inventa un id para lo que no tiene | Sí *(tras corregir)* |
| dataset: se anuncia un mundo que no es | Sí |
| relaciones: se reconstruyen en vez de leerse | Sí |
| filtro: se comparan sin distinguir mayúsculas | Sí |
| filtro: un campo inventado deja de rechazarse | Sí |
| serialización: se filtra una referencia interna | Sí |
| temporalidad: `dataset_id` pasa a ser un reloj | Sí |
| límite: se devuelve todo sin cortar | Sí *(tras añadir prueba)* |

**Dos mutaciones NO fueron detectadas en la primera pasada**, y ambas
correspondían a problemas reales, no a pruebas débiles:

1. **La guarda de `_identidad` era código muerto.** La mutation «se inventa un
   id» no la alcanzó porque la ruta que llega a ella ya filtraba antes. Se
   corrigió el código y se añadió una prueba que la ejercita directamente.
2. **El recorte de `LIMITE_MAXIMO` no estaba probado.** La mutation «se
   devuelve todo sin cortar» no la alcanzó porque las pruebas usaban límites
   pequeños. Se añadieron tres pruebas, incluida la del recorte efectivo.

Se prefirió arreglar las causas a relajar las pruebas. Ninguna prueba existente
se eliminó ni se debilitó.

## P. Cambios de producción

**Ninguno.** No se modificó ni una línea de los módulos de producción.

Hashes SHA-256 antes y después de la misión (primeros 16 caracteres):

| Módulo | Antes | Después |
|--------|-------|---------|
| `00_SOURCE/tools/nucleo.py` | `CCC48EA67849701A` | *sin cambios* |
| `00_SOURCE/tools/validar_semantica.py` | `C927FF8B66AC9B8C` | *sin cambios* |
| `00_SOURCE/tools/actualizar_datos.py` | `108560E597355329` | *sin cambios* |
| `00_SOURCE/tools/cargar_legends.py` | `30140AD617CB2BF0` | *sin cambios* |
| `00_SOURCE/tools/integrar_legends.py` | `35649CDCAF75153B` | *sin cambios* |
| `00_SOURCE/tools/rutas.py` | `0EAD547FDF6D1368` | *sin cambios* |
| `dfchron/servicio.py` | `D6BD6E5B28A97169` | *sin cambios* |
| `dfchron/api.py` | `BB6BDEBBAD5177A1` | *sin cambios* |
| `dfchron/contrato_ia.py` | `EB4A4156CBFAF764` | *sin cambios* |
| `dfchron/ia_estructura.py` | `BE9FC091EFF534E9` | *sin cambios* |
| `dfchron/ia_conocimiento.py` | `7EBCBBC2C2B4F044` | *sin cambios* |
| `dfchron/ia_verificacion.py` | `B8BFD2CC39D3F302` | *sin cambios* |
| dataset | `v1-04170363943d4ba1` | *sin cambios* |

Todo lo añadido es **nuevo y aditivo**. `servicio.py` no se tocó precisamente
porque la capa se apoya en él; reescribirlo habría sido duplicar.

## Q. Limitaciones

Límites honestos, no resueltos:

1. **La Web y la API no exponen todavía esta capa.** Existen y funcionan, pero
   no se les añadió un endpoint. Es deliberado: primero se estabiliza el
   servicio interno, como pedía la misión.
2. **El filtro es solo `==` y exacto.** No hay rangos ni orden. Se añadió lo
   mínimo que el dataset demuestra; ampliarlo exigiría justificarlo con datos
   reales, no por simetría con otros sistemas.
3. **`contar()` recorre el índice en memoria.** Para un filtro es aceptable
   sobre ~11.000 elementos, pero no es una base de datos y no pretende serlo.
4. **No hay consulta de relaciones por atributo**, solo por tipo. El grafo no
   tiene índices por atributo y no se han creado.
5. **La verificación delega, no amplía.** Las capacidades son las de
   `verificacion_semantica`; esta capa no añade niveles nuevos.
6. **El estado temporal «actual» no existe** y no se ha simulado.
7. **Dos códigos nuevos** (`NO_VERIFICADO`, `NO_DISPONIBLE`) son una ampliación
   mínima de la taxonomía. Se justifican en el módulo y están probados, pero
   conviene revisarlos cuando la API los exponga públicamente.

## R. Estado final

**Completado.**

- Capa de consulta determinista clara, con contrato explícito.
- No duplica nada: cada operación delega en lo que ya existía.
- Distingue `NOT_FOUND` de `NOT_VERIFIED`.
- Transporta evidencia, identidad y `dataset_id` en cada respuesta.
- Respeta `dataset_id` y `state_version`.
- No inventa identidades, relaciones ni temporalidad.
- Determinista y sin efectos secundarios, demostrado.
- 66 pruebas propias, **66/66**; 12/12 mutaciones detectadas.
- **0 regresiones** en las 30 suites existentes.
- Dataset intacto: `v1-04170363943d4ba1`.
- **Ninguna IA.**

> «Cualquier consumidor puede consultar el conocimiento estructurado de Dwarf
> Fortress mediante un contrato estable, reproducible y limitado por la evidencia
> real del núcleo.»

Eso es cierto **aunque se elimine por completo cualquier IA del proyecto**, que
es lo que siempre se pidió.

PLACEHOLDER_INFORME
