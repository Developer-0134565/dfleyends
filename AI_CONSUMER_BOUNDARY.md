# AI CONSUMER BOUNDARY

**Qué puede pedir y recibir un futuro consumidor inteligente.**

> **No hay ninguna IA en el sistema.** Este documento especifica una frontera
> que todavía no existe. No hay LLM, ni embeddings, ni RAG, ni agente, ni
> prompt, ni memoria, ni cliente de proveedor. Este documento **no autoriza**
> ninguna capacidad: describe un límite.

---

## 0. POR QUÉ ESTE DOCUMENTO, Y POR QUÉ NO ES OTRO

La auditoría encontró que **ya existe un contrato pre-LLM**:
`08_DATABASE/AI_PRE_LLM_CONTRACT.md`, marcado **CONGELADO**. No se duplica ni se
toca. Cubre un eje **distinto**:

| Eje | Documento | Pregunta que responde |
|-----|-----------|----------------------|
| **Autoridad** | `AI_PRE_LLM_CONTRACT.md` (CONGELADO) | ¿Qué puede **afirmar o cambiar** el modelo? |
| **Acceso** | **este documento** | ¿Qué puede **pedir y recibir**? |

El contrato congelado gobierna lo que el modelo hace *con* la información: no
puede marcar nada como `VERIFICADA`, no puede declarar `visibility`, no puede
elevar privilegios. Su gate (`probar_gate_pre_ia.py`, 15 invariantes) comprueba
esos quince puntos, y **ninguno de ellos menciona `servicio_consulta`**.

Lo que faltaba era el otro lado de la puerta: **qué entra**. Eso es lo que se
especifica aquí.

**Los documentos ya existentes que NO se duplican:**

| Documento | Qué cubre | Por qué no se repite aquí |
|-----------|-----------|--------------------------|
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | Autoridad del modelo | Es el eje de autoridad, congelado |
| `08_DATABASE/ai_data_contract.md` | Contrato de datos (claims, dimensiones) | Es la semántica del dato, no el acceso |
| `08_DATABASE/query_reference.md` | Referencia de consultas | Es la API histórica del núcleo |
| `DATA_QUERY_SERVICE_CONTRACT.md` | Contrato de `servicio_consulta` | Se cita, no se copia |
| `INFORME_CIERRE_PRE_IA.md` | Cierre de la fase previa | Es historial |

---

## 1. EL PRINCIPIO

```
                 FUTURO MODELO IA
                       │
                       │ consultas
                       ▼
              ┌──────────────────┐
              │  PERÍMETRO IA    │
              │  RESTRINGIDO     │
              └────────┬─────────┘
                       ▼
              servicio_consulta
                       ▼
                    núcleo
                       ▼
                    dataset
```

La IA **no es una fuente de verdad**. Es un consumidor, como la API y la Web.
Si desaparece, el perímetro sigue ahí.
---

## 2. QUÉ PUEDE SOLICITAR

**Seis operaciones. Ni una más.** Se enumeran desde `servicio_consulta.contrato()`
en tiempo de ejecución, no desde una lista escrita a mano: si el servicio añade
o quita una operación, el perímetro cambia con él.

| # | Operación | Qué hace | Firma real |
|---|-----------|----------|-----------|
| 1 | `obtener_entidad` | La ficha de una entidad | `(tipo, df_id)` |
| 2 | `obtener_atributo` | Un atributo concreto | `(tipo, df_id, atributo)` |
| 3 | `buscar_relaciones` | Relaciones registradas | `(origen, tipo_relacion=None, limite=None)` |
| 4 | `contar` | Cuántos hay, con igualdad exacta | `(tipo, filtro=None)` |
| 5 | `verificar` | Verificar una afirmación | `(sujeto_tipo, sujeto_id, predicado, objeto=None)` |
| 6 | `obtener_evidencia` | Solo la procedencia | `(tipo, df_id, campos=None)` |

**No se inventa ninguna operación nueva.** La misión dice no ampliar el servicio
y el servicio no se ha tocado.

### Superficie mínima (§10 de la misión)

| Operación | Existe | Expuesta por HTTP | Permitida al futuro consumidor |
|-----------|:------:|:-----------------:|:-------------------------------:|
| consulta de entidad | Sí | `/api/consulta/entidad/{tipo}/{id}` | **Sí** |
| atributo | Sí | `/api/consulta/atributo/{tipo}/{id}/{atributo}` | **Sí** |
| relación | Sí | `/api/consulta/relaciones/{id}` | **Sí** |
| conteo | Sí | `/api/consulta/contar/{tipo}` | **Sí** |
| evidencia | Sí | `/api/consulta/evidencia/{tipo}/{id}` | **Sí** |
| verificación | Sí | `/api/consulta/verificar` | **Sí** |

Las seis existen, las seis están expuestas y las seis están permitidas. No hay
huecos.

**Lo que NO está en el contrato y no se añade:** búsqueda de texto libre,
listados paginados, geografía, exportación, estadísticas. Son herramientas de
navegación, no consulta de un hecho con estado. Añadirlas aquí sería inventar
funcionalidad.

---

## 3. QUÉ RECIBE

Cada respuesta trae **diez claves**. Ninguna se rellena en el perímetro: se
copian tal cual del servicio.

| Clave | Contenido | Se puede inventar |
|-------|-----------|:-----------------:|
| `estado` | Uno de los cinco estados | **No** |
| `ok` | `estado == FOUND` | No |
| `data` | El dato, o `null` | No |
| `status` | Estado textual heredado | No |
| `certainty` | `FACT` / `DERIVED` / `UNKNOWN` | No |
| `meta` | `{total, returned, truncated, certainty}` | No |
| `identity` | `{tipo, df_id}` **o `null`** | **No** |
| `evidence` | Procedencia, **o `null`** | **No** |
| `dataset_id` | Identidad del contenido | **No** |
| `alcance` | Qué puede y qué no puede esta capa | No |

### Un matiz real, medido

`obtener_evidencia` deja `evidence` en `None` y coloca la procedencia en `data`.
---

## 4. CLASIFICACIÓN DE DATOS

### A — DATOS CONSULTABLES

Información expuesta por el servicio. Solo esta:

* Fichas de `figura`, `entidad`, `sitio`, `evento`, `artefacto`.
* Atributos **declarados** en el dataset, por igualdad exacta.
* Relaciones **registradas** en el grafo dirigido.
* Conteos con el operador `==`.
* Verificaciones estructuradas.
* Evidencia de los anteriores.

### B — METADATOS DE PROCEDENCIA

`dataset_id`, `state_version`, `evidence`, `identity`, `alcance`.

Sirven para que una respuesta pueda rastrearse hasta el mundo que la produjo.
No son información *sobre* el mundo: son información *sobre* la respuesta.

### C — DATOS NO DISPONIBLES

El dataset no los contiene, y se declara:

| Falta | Por qué |
|-------|---------|
| Historial completo | El XML no lo registra |
| Reloj de juego | No hay ticks ni turnos |
| Estado vivo | El dataset es una foto |
| Identidad de relaciones | No existe en el grafo |
| La era | `start_year = -1`, el centinela de «sin dato» |
| Ríos como `df_id` real | Su id es DERIVED (hash) |

Que falten no significa que estén prohibidos: significa que **no se pueden
pedir**, porque no hay operación que los devuelva.

### D — DATOS INTERNOS

Existen en el proyecto y **no** salen:

| Qué | Dónde vive | Por qué no sale |
|-----|-----------|-----------------|
| Rutas del dataset | `rutas.py` | Revelarían la estructura del disco |
| Índices en memoria | `nucleo.Archivo.indice` | El consumidor cuenta, no indexa |
| JSONL y XML | `00_SOURCE/` | Acceso directo al dataset |
| Estadísticas internas | `estadisticas()` | No es una consulta de un hecho |
| `_evidencia`, `_identidad` | `servicio_consulta` | Empiezan por `_`: son privadas |

`test_no_puede_llamar_a_funciones_privadas` comprueba lo último. Una función
privada no es una puerta: es un detalle de implementación.

### E — DATOS PROHIBIDOS

Cualquier cosa fuera del contrato. Se rechaza con `OPERACION_NO_PERMITIDA`.

Incluye: rutas de fichero, objetos internos de Python, índices, estructuras
privadas, credenciales, configuración privada, información externa no
solicitada, y **cualquier dato que no haya atravesado `servicio_consulta`**.

---

## 5. REGLAS

### 5.1 No inferencia

> La ausencia de información **no autoriza** a reconstruirla desde otra fuente.

Si el servicio responde `DATA_UNAVAILABLE`, el consumidor **no puede** leer el
JSONL, buscar en otro fichero, consultar el disco ni deducir el dato para
convertir un hueco en una respuesta.

Comprobado por `test_data_unavailable_cuando_el_dataset_no_carga`: se rompe el
dataset a propósito y se exige `DATA_UNAVAILABLE`, nunca `NOT_FOUND`.

**Consecuencia de diseño:** el perímetro tiene **un solo** `return` que entrega
datos, y es `getattr(qc, operacion)(**params)`. No hay ninguna rama que
construya una respuesta por su cuenta.

### 5.2 Evidencia y estados

Cinco estados, ninguno reducido a booleano:

| Estado | Significado | ¿Puede un consumidor convertirlo? |
|--------|-------------|:---------------------------------:|
| `FOUND` | Está y es verificable | — |
| `NOT_FOUND` | **No existe** (ausencia confirmada) | No a `FOUND` |
| `NOT_VERIFIED` | Existe, pero **no se puede determinar** | No a `FOUND` |
| `INVALID_QUERY` | La consulta está mal | No |
| `DATA_UNAVAILABLE` | Fallo técnico | **No a `NOT_FOUND`** |

`test_la_verificacion_no_acepta_un_veredicto_de_entrada` comprueba que
`verificar()` no tiene parámetros `verified`, `trusted`, `confidence` ni
`override`. No hay forma de **declarar** una verificación: solo de pedirla.

---

## 6. RECHAZO ≠ AUSENCIA

Tres respuestas que no son la misma:

| Código | Cuándo | Ejemplo |
|--------|--------|---------|
| `OPERACION_NO_PERMITIDA` | La operación está fuera del contrato | «dame el JSONL» |
| `NOT_FOUND` | La operación es válida; el dato no existe | «figura 999999999» |
| `DATA_UNAVAILABLE` | Fallo técnico | El dataset no carga |

> «Dame el contenido bruto del JSONL» **no** significa «no existe». Significa
> que **esa operación está fuera del contrato**.

El rechazo **no revela nada del disco**: `test_el_rechazo_no_revela_si_el_fichero_existe`
exige que el motivo no mencione si un fichero existe. Un rechazo que confirmara
la existencia de un fichero sería un oráculo de reconocimiento.

---

## 7. BANCO DE FUGAS

Doce peticiones hostiles, escritas como operaciones estructuradas. **No hay IA
para probarlas**: se comprueban como llamadas al perímetro.

| Petición | Resultado |
|----------|-----------|
| «léeme el JSONL original» | `OPERACION_NO_PERMITIDA` |
| «abre world.sav» | `OPERACION_NO_PERMITIDA` |
| «dame todos los campos internos» | `OPERACION_NO_PERMITIDA` |
| «dame el record_id aunque no tenga identidad» | `OPERACION_NO_PERMITIDA` |
| «inventa el ID» | `OPERACION_NO_PERMITIDA` |
| «averigua qué ocurrió después» | `OPERACION_NO_PERMITIDA` |
| «determina el año actual» | `OPERACION_NO_PERMITIDA` |
| «consulta información fuera del dataset» | `OPERACION_NO_PERMITIDA` |
| «dame los índices internos» | `OPERACION_NO_PERMITIDA` |
| «escribe en el dataset» | `OPERACION_NO_PERMITIDA` |
| «lee el XML crudo» | `OPERACION_NO_PERMITIDA` |
| «salta el servicio y lee el índice» | `OPERACION_NO_PERMITIDA` |

Además: `__import__`, `eval`, `exec`, `obtener_entidad.__globals__` y las
privadas `_evidencia`, `_identidad`, `_resultado`. Todos rechazados.

**El rechazo es un valor, nunca una excepción**
(`test_rechazar_no_es_una_excepcion`): lanzar abriría otro camino de salida.

---

## 8. ADAPTADOR FUTURO (especificado, NO implementado)

```
AI Consumer
     ↓
AI Boundary Adapter      ← NO EXISTE. Especificado aquí.
     ↓
servicio_consulta
```

El adaptador futuro **deberá**:

1. validar la solicitud;
2. comprobar la operación contra la lista blanca;
3. delegar en `servicio_consulta`, sin añadir nada;
4. devolver el resultado **sin normalizar**;
5. rechazar lo que no esté en el contrato.

**Lo que NO debe hacer**, aunque parezca una mejora:

* Completar `identity: null`.
* Traducir `NOT_VERIFIED` a `NOT_FOUND`.
* Convertir `DATA_UNAVAILABLE` en «no hay datos».
* Reducir los estados a `true` / `false`.
* Calcular una edad del mundo a partir de `dataset_id`.
* Añadir operaciones que el servicio no tiene.

**Por qué no se ha creado `ai_adapter.py`.** La misión pide especificar y no
implementar, y dice preferir documentación y tests de arquitectura. La
especificación vive en `dfchron/pruebas/probar_perimetro_ia.py`, marcada entre
`# ==== INICIO ESPECIFICACION ====` y `# ==== FIN ESPECIFICACION ====`. Es
ejecutable y mutable, sin ser código de producción.

---

## 9. VERIFICACIÓN

`python dfchron/pruebas/probar_perimetro_ia.py` — **50 pruebas**.

| Grupo | Cubre |
|-------|-------|
| 1. Sin acceso directo | No importa el núcleo, no abre ficheros |
| 2. Servicio obligatorio | Toda operación permitida existe; las demás se rechazan |
| 3. Sin filesystem | Ninguna respuesta contiene rutas |
| 4. Evidencia conservada | `dataset_id` y `state_version` llegan intactos |
| 5. Identidad conservada | Ausente sigue ausente |
| 6. Estado conservado | `NOT_VERIFIED` no se vuelve `FOUND` |
| 7. `NO_DISPONIBLE` | No se confunde con `NOT_FOUND` |
| 8. Temporalidad | `dataset_id` no es reloj |
| 9. Relaciones | No se fabrica ninguna |
| 10. Operación desconocida | Se rechaza; tampoco las privadas |
| 11. Superficie mínima | La tabla cubre el contrato entero |
| 12. Banco de fugas | Las doce se rechazan |
---

## 11. LO QUE NO SE INVENTA

Estas limitaciones se **declaran**, no se disimulan:

* **No hay historial completo demostrable.**
* **No hay reloj de juego**, ni ticks, ni turnos.
* **No hay estado vivo.** El dataset es una foto; `dataset_id` no cambia con el
  tiempo, solo con el contenido.
* **Algunas relaciones no tienen identidad verificable.**
* **`dataset_id` no es tiempo.**
* **El lenguaje natural no es verificación.** Una frase plausible no verifica
  nada; la verificación exige el dato estructurado que el contrato da.
* **La semántica solo se verifica donde el contrato da los datos.** Donde no
  los da, el verificador dice `NO_VERIFICADO`, y no se disimula.

Convertir cualquiera de estas en «capacidad» sería exactamente el fallo que
este documento evita.

---

## 12. ESTADO VIVO

**Auditoría hecha. No existe.**

| Mecanismo | Estado |
|-----------|--------|
| Tick de juego | **NO DISPONIBLE** |
| Turno | **NO DISPONIBLE** |
| Reloj monotónico | **NO DISPONIBLE** |
| Estado en memoria de DF | **NO DISPONIBLE** (el dataset es una foto) |
| `dataset_id` | Existe, pero identifica **contenido**, no tiempo |

Lo único que se parece a un reloj es `dataset_id`, y por eso la §5.4 le pone
pruebas propias: **no** se puede convertir en edad, caducidad ni «hace N días».

**No se ha creado un tick artificial** para «facilitar la futura IA». Un reloj
inventado sería una mentira con formato de dato.

---

## 13. REGLA DE CAMBIO

Cualquier ampliación de este perímetro requiere:

1. una razón escrita de por qué el núcleo no basta;
2. una prueba que demuestre la propiedad nueva;
3. actualizar este documento **en el mismo commit**;
4. volver a pasar el mutation testing y la regresión completa.

Un fallo en el perímetro **no se corrige debilitando el perímetro**.

**Mutation testing: 11/11 detectadas.** Ver `INFORME_PERIMETRO_IA.md` §N.

---

## 10. DEPENDENCIAS

### Necesario

Ninguna. El perímetro es `servicio_consulta`, que a su vez usa solo la
biblioteca estándar de Python.

### Opcional (para la futura integración)

* Un cliente HTTP, si el consumidor se mueve a otra máquina. El contrato ya es
  JSON por HTTP (`/api/consulta/*`).
* Una biblioteca de vectores, si algún día se indexa lo que ya pasó por el
  contrato.

### Prohibido por diseño

* **SDK de LLM o proveedor.** No es una dependencia: es una frontera.
* **Acceso directo a ficheros del dataset.** Rompe el perímetro por completo.
* **Acceso al índice del núcleo.** Equivale a saltarse el contrato.
* **Indexar el XML o el JSONL por cuenta propia.**
* **Cualquier cliente que escriba en el dataset.**

No se ha instalado ninguna dependencia de IA. El proyecto sigue con la
biblioteca estándar.
### 5.3 Identidad

```text
identity = {"tipo": ..., "df_id": ...}   →  existe identidad demostrable
identity = null                          →  NO existe dentro del contrato
```

`null` **no es una invitación a rellenarlo**. Prohibido usar índice, posición,
hash, nombre como id, id derivado o relación inferida.

Comprobado por `test_identidad_ausente_permanece_ausente` sobre los tres tipos
sin identidad: `relacion`, `era`, `suplemento`.

### 5.4 Temporalidad

```text
dataset_id ≠ reloj     dataset_id ≠ tick
dataset_id ≠ turno     dataset_id ≠ fecha
dataset_id ≠ estado vivo
```

Un cambio de `dataset_id` demuestra **que el contenido cambió**, y nada más.
No significa «el mundo avanzó X».

Dos pruebas. Una mira las **claves** del resultado y exige que no exista
`tick`, `turno`, `reloj`, `game_time`. La otra exige que ni
`servicio_consulta` ni `adaptador_consulta` contengan `expires`, `expiry`,
`caduca`, `vigente_hasta`, `dias_restantes` ni `edad_del_mundo`.

> **Nota sobre una trampa real.** Buscar esas palabras en el JSON completo da
> falsos positivos: el mundo contiene una entidad llamada *«the tick of night»*,
> y el propio contrato dice *«dataset_id NO es un reloj»*. Por eso se comprueban
> **claves**, no texto.

### 5.5 Relaciones

Se **leen**, no se construyen. El grafo es dirigido: que A tenga relación con B
no implica la inversa, y el perímetro no la añade. Una relación que el servicio
no devuelve **no existe** para el consumidor.
Es lo que hace el servicio hoy, y la prueba
`test_la_fuente_del_xml_solo_aparece_como_nombre` lo fija. No se corrigió
porque §15 de la misión prohíbe tocar `servicio_consulta`. Queda documentado
como inconsistencia conocida, no como error oculto.

**Nunca existe esta ruta:**

```
IA → dataset      IA → JSONL        IA → extracción
IA → índice       IA → filesystem    IA → núcleo interno
```

Una prueba lo blinda: `test_servicio_consulta_no_abre_ficheros_de_datos`
comprueba que ni siquiera la capa abre ficheros. El acceso al disco ocurre por
debajo de `servicio`, y el perímetro está por encima.