# TECHNICAL ROADMAP

Qué falta, en qué orden, y qué bloquea qué.

> **No hay fechas ni compromisos.** Solo estado real y dependencias. Una hoja de
> ruta con fechas se vuelve una promesa falsa en cuanto algo se bloquea.
>
> **Prioridad: terminar el núcleo antes que la IA.** Las fases E y F no empiezan
> hasta que A–D estén estables.

**Leyenda de estado:**

| Estado | Significado |
|--------|-------------|
| COMPLETO | Hecho y probado |
| PARCIAL | Parte hecha; queda algo |
| PENDIENTE | No empezado |
| BLOQUEADO | No se puede empezar hasta que se resuelva otra cosa |

---

## Resumen

| Fase | Nombre | Estado | Bloqueada por |
|------|--------|--------|---------------|
| A | Núcleo de DF | COMPLETO | — |
| B | Datos y trazabilidad | COMPLETO | — |
| C | Verificación | PARCIAL | — |
| D | Conocimiento y visibilidad | COMPLETO | — |
| H | Capa de consulta determinista | COMPLETO (interna) | API expuesta → pendiente |
| E | Integración de IA | PENDIENTE | A–D estables |
| F | Integración con Dwarf Fortress | PENDIENTE | — (vía sin decidir) |

---

## A. Núcleo de DF — **COMPLETO**

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| Extracción con autodetección de codificación | COMPLETO | `probar_integracion.py` |
| Merge de dos fuentes con procedencia | COMPLETO | `probar_integracion.py` |
| Índice de referencias cruzadas | COMPLETO | `probar_integracion.py` |
| Fichas, búsqueda, cronología, relaciones | COMPLETO | `probar_nucleo.py` (48) |
| Servicio con envelopes y límites | COMPLETO | `probar_api.py` (54) |
| UI que habla solo con la API | COMPLETO | `probar_web.py` |
| Determinismo | COMPLETO | `test_determinismo.py` |
| Reproducibilidad desde los XML | COMPLETO | `verificar_reproducibilidad.py` |

**Qué falta:** nada bloqueante. La fase E puede empezar cuando se quiera.

---

## B. Datos y trazabilidad — **COMPLETO**

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| Versión del dataset por SHA-256 (`dataset_id`) | COMPLETO | `dataset_version.json` |
| Integridad de `original_data/` (solo lectura) | COMPLETO | `probar_integracion.py` |
| Rutas protegidas (`es_ruta_protegida()`) | COMPLETO | `probar_api.py` |
| Procedencia por campo en el merge | COMPLETO | `08_DATABASE/architecture.md` |
| Conflictos conservados, no resueltos | COMPLETO | `probar_nucleo.py` |
| Refresco versionado con backup | COMPLETO | `probar_refresh_cycle.py` |

**Nota.** `dataset_id` identifica el contenido. **No** es un reloj: no hay
caducidad. Ver `ARCHITECTURE_DECISIONS.md` D09.

---

## C. Verificación — **PARCIAL**

| Tarea | Estado | Qué falta |
|-------|--------|-----------|
| Verificación estructurada contra la ficha | COMPLETO | — |
| Estados `VERIFICADA`/`NO_VERIFICADA`/`NO_APLICABLE` | COMPLETO | — |
| Versionado de evidencia (`state_version`) | COMPLETO | — |
| Invalidación por cambio de mundo | COMPLETO | — |
| **Verificación semántica (paráfrasis, negación)** | **NO DISPONIBLE** | No hay datos que lo permitan sin un juez lingüístico. Se mantiene `NO_APLICABLE` |
| **Verificación semántica determinista (7 niveles)** | **DEMOSTRADO** | `verificacion_semantica.py`: existencia, atributo, relación, estado, cantidad, estructura (completos) e histórico (parcial). 38 pruebas sobre datos reales |
| **Afirmaciones relacionales complejas** | **PARCIALMENTE DEMOSTRADO** | La *relación* entre figuras se verifica (`relacion()`); la *fila de relación* no tiene identidad (`NOT PROVEN`) |
| **Caducidad temporal** | **BLOQUEADO** | Requiere un reloj de juego, que no existe (→ depende de F) |
| **Estado en vivo versionado** | **BLOQUEADO** | Requiere decidir cómo se versiona un mundo mutable (→ depende de F) |

### Identidad: qué hay y qué no

Medido sobre el dataset activo. **No se ha inventado ningún identificador.**

| Entidad | Identificador | Origen | Estado |
|---------|--------------|--------|--------|
| Figura | `df_id` | **del juego** | Estable y único (11.144) |
| Sitio | `df_id` | **del juego** | Estable y único (734) |
| Entidad | `df_id` | **del juego** | Estable y único (1.067) |
| Evento | `df_id` | **del juego** | Estable y único (57.215) |
| Artefacto | `df_id` | **del juego** | Estable y único (427) |
| Región | `df_id` | **del juego** | Estable y único (840) |
| Región subterránea | `df_id` | **del juego** | Estable y único (405) |
| **Relación** | **NINGUNO** | — | **13.192 filas sin `df_id`** |
| **Suplemento de relación** | **NINGUNO** | — | **21 filas sin `df_id`** |
| **Era histórica** | **NINGUNO** | — | 1 fila, sin `df_id` |

Las 3 secciones sin identificador son la razón exacta por la que las
afirmaciones relacionales no son verificables. **No se ha creado un `df_id`
sintético**: eso sería fabricar la capacidad justo para poder marcarla PASS.

**Investigado y confirmado que no hay identidad recuperable.** Los tres
`record_id` que sí existen se auditaron uno a uno:

| Sección | `record_id` | Por qué NO sirve como identidad |
|---------|-------------|-------------------------------|
| Relaciones | `her:<event>:<índice de fila>` | El índice es **posicional** (prohibido como identidad) y `<event>` **no resuelve** en ninguna sección |
| Suplementos | `sup:<event>:<índice de fila>` | El mismo patrón posicional |
| Eras | `historical_eras:derived:<hash>` | Con **1 sola era** no hay colisión posible ni referente con el que comparar |

Comprobado además que `(source_hf, target_hf, relationship)` **no es único**:
12.925 triplas distintas de 13.192 filas, es decir **246 duplicados**.

`df_id` **no es universal**: `112` de sitio y `112` de figura son entidades
distintas. La identidad real es el par `(entidad, df_id)`.

### Relaciones: matriz

| Relación | Fuente | Verificable | Tipo |
|----------|--------|-------------|------|
| figura → entidad | `entity_link.entity_id` + `link_type` | **Sí** | **Explícita** — 10 tipos: member, former member, enemy, prisoner, former prisoner, criminal, lair, seat of power, occupation, home structure |
| figura → sitio | `site_link.site_id` + `link_type` | **Sí** | **Explícita** |
| figura → figura | `source_hf` / `target_hf` | Sí, por identidad | **Explícita** (pero la fila no tiene id propio) |
| relación → evento | `relation.event` | **No** | **Desconocida**: 13.192 de 13.192 no resuelve |
| sitio → civilización | `civ_id` | **Sí** | **Explícita** |
| sitio → propietario actual | `cur_owner_id` | **Sí** | **Explícita** |
| sitio → figuras | índice inverso | **Sí** | **Derivada** |
| artefacto → propietario | `holder_hfid` | **Sí** | **Explícita** |
| artefacto → creador | evento `artifact created` | **Sí** | **Derivada** |
| evento → lugar | `site_id` | **Sí** | **Explícita** |
| guerra | — | **No** | **No existe en el XML** |

Ninguna regla semántica arbitraria se ha añadido. Lo que el XML no dice, se
declama desconocido.

### Cómo se verificaría cada pendiente

* **Semántica:** con pruebas que demuestren que una paráfrasis NO verifica.
  Hoy ya existen (`test_F*`); lo que falta es una estrategia **positiva** que no
  convierta un juez semántico en autoridad.
* **Relaciones:** solo si el dataset llegara a exponer un identificador estable.
  Hoy no lo expone, y **no se inventaría**.
* **Temporalidad en vivo:** con un adaptador DF-Hack que aporte `df_id`,
  procedencia, descubrimiento, visibilidad, política y **versión**.

**Nada de esto se cierra con una prueba parecida.** Si no hay dato, no hay
prueba honesta.

---

## D. Conocimiento y visibilidad — **COMPLETO**

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| Cuatro categorías de conocimiento | COMPLETO | `probar_semantica_ia.py` (144 combinaciones) |
| Separación verdad / visibilidad / divulgación | COMPLETO | `probar_documentacion_ia.py` |
| Estado del jugador, persistencia, fail-closed | COMPLETO | `probar_estado_conocimiento.py` (48) |
| Descubrimiento progresivo (dataset estático) | COMPLETO | `probar_cierre_pre_ia.py` |
| Descubrimiento en partida en vivo | **BLOQUEADO** | Depende de F |

---

## H. Capa de consulta determinista — **COMPLETA (interna + API + Web)**

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| Contrato de consulta independiente de transporte | COMPLETO | `DATA_QUERY_SERVICE_CONTRACT.md` |
| Seis operaciones que delegan, sin duplicar | COMPLETO | `probar_servicio_consulta.py` (66) |
| `identity` + `evidence` + `dataset_id` en cada respuesta | COMPLETO | Mismo (D17) |
| `NOT_FOUND` ≠ `NOT_VERIFIED` | COMPLETO | Mismo |
| Límites y paginación deterministas | COMPLETO | Mismo |
| Mutation testing de la capa | COMPLETO | 12/12 detectadas |
| **Endpoint HTTP que use la capa** | **COMPLETO** | `/api/consulta/*` (D18) |
| **Web consumiendo la capa** | **COMPLETO** | Ambas (D18) |
| Adaptador HTTP sin lógica de dominio | COMPLETO | `adaptador_consulta.py`, `probar_integracion_consulta.py` |
| Compatibilidad de las rutas existentes | COMPLETO | 0 regresiones sobre 48 rutas |
| Mutation testing del adaptador | COMPLETO | 8/8 detectadas |

**Cómo se cerró la frontera.** En dos vías a la vez, porque una sola habría
fallado: las 6 fichas y las relaciones **existentes** ahora pasan por
`servicio_consulta` (enriquecimiento **aditivo**: el envelope antiguo queda
intacto), y se añadieron las rutas **`/api/consulta/*`**, que exponen el
contrato completo. La Web muestra el estado y la evidencia que llegan, sin
decidir nada.

**Lo que se decidió NO hacer.** Endpoints de IA, atajos para la IA, ni
preparativos para futuros modelos: `/api/consulta/*` es una API de datos
determinista, útil exista o no IA. Ver D18.

---

## E. Integración de IA — **PENDIENTE (por diseño)**

**Esta fase no debe empezar hasta que A–D estén estables y el gate pase.**

| Tarea | Estado | Dependencia | Cómo se verificaría |
|-------|--------|-------------|---------------------|
| Contrato de entrada del adaptador (autoridad) | **Ya existe y congelado** | `AI_PRE_LLM_CONTRACT.md` §9 | `probar_gate_pre_ia.py` |
| Contrato de salida (`validar_salida()`) | **Ya existe** | — | `probar_contrato_io.py` |
| Composición desde contexto | **Ya existe** | — | `probar_cierre_pre_ia.py` |
| Adaptador hostil sin LLM | **Ya existe** | — | `probar_cierre_pre_ia.py` |
| **Perímetro de acceso (qué puede pedir)** | **Ya existe y congelado** | `servicio_consulta` | `probar_perimetro_ia.py` (50) |
| **Adaptador de acceso, implementado** | **PENDIENTE** | Decisión D19 | Reutiliza `probar_perimetro_ia.py` |
| Elegir y cablear un modelo concreto | PENDIENTE | Decisión D12 | Una suite nueva que reutilice el contrato |
| Estrategia de prompts | PENDIENTE | Adaptador | — |

### Orden de los pasos que faltan

1. **Antes:** leer `08_DATABASE/AI_PRE_LLM_CONTRACT.md` (autoridad) y
   `AI_CONSUMER_BOUNDARY.md` (acceso). Los dos están congelados.
2. Ejecutar `probar_gate_pre_ia.py` **y** `probar_perimetro_ia.py`. Si alguna
   falla, **no** se integra nada.
3. Escribir el adaptador de acceso como el bloque de especificación de
   `probar_perimetro_ia.py`, moviéndolo a producción **solo cuando exista un
   consumidor real**. Sin SDK en el núcleo.
4. El adaptador de acceso se mueve entero: lista blanca derivada de
   `contrato()`, rechazo `OPERACION_NO_PERMITIDA`, sin normalizar resultados.
5. Escribir el adaptador de inferencia como implementación de la interfaz
   `invocar()` de `ia_inferencia.py`.
6. Toda salida pasa por `validar_salida()`. No hay otra ruta.
7. El texto del jugador lo compone `componer_seguro()`, no el modelo.
8. Añadir pruebas que reutilicen `probar_cierre_pre_ia.py` (adaptador hostil),
   sin debilitar las existentes.

### Restricciones que no se negocian

* No se añade `confidence` como autoridad.
* No se usa un LLM como juez semántico.
* No se conecta texto libre a la salida.
* Si una integración nueva necesita una capacidad que el núcleo no tiene, se
  escribe en este documento **antes** de implementarla, y se justifica.

---

## F. Integración con Dwarf Fortress — **PENDIENTE, vía sin decidir**

**La vía no está decidida.** Se documentan las direcciones candidatas, no una
elección.

| Dirección | Qué implicaría | Estado |
|-----------|----------------|--------|
| Solo exports (actual) | Ningún cambio. El jugador exporta y el proyecto lo lee | **FUNCIONANDO** |
| Mod / DFHack | Estado en vivo. Exige resolver versionado (P1), descubrimiento en vivo, y granularidad | **SIN ESTUDIAR** |
| Otro mecanismo | Por decidir | **SIN ESTUDIAR** |

> **Importante:** esta misión **no** decide que la vía sea un mod. Es una
> dirección a estudiar cuando llegue el momento, con sus requisitos escritos.

### Requisitos comunes a cualquier vía

Todo adaptador de DF-Hack debe aportar, como mínimo:

1. `df_id` (identidad estable);
2. procedencia;
3. estado de descubrimiento;
4. visibilidad;
5. política de divulgación;
6. **versión temporal**.

### Qué se desbloquea con F

* Caducidad temporal y evidencia obsoleta en partida en vivo (C).
* Descubrimiento progresivo real (D).
* Resolución de `P1`, `P2` y `P5` en `ARCHITECTURE_DECISIONS.md`.

---

## G. Memoria conversacional — **PENDIENTE, sin origen**

No está en A–F porque **nadie la ha pedido** ni existe. Se registra solo para que
conste el límite.

Si algún día se añade, sus requisitos no son opcionales:

* revalidarse en **cada** turno (un claim del turno 3 no se da por bueno en el 7);
* recomponerse desde el estado, no acumularse;
* el texto previo del modelo **no** puede ser insumo de la composición.

Mientras no se decida, el sistema reconstruye cada respuesta desde cero, que es
lo que `probar_cierre_pre_ia.py::TestReconstruccionDeterminista` demuestra.

---

## Cómo usar esta hoja de ruta

1. Elija una tarea de las fases A–D y hágala.
2. Añada su prueba.
3. Actualice el estado **en el mismo cambio**.
4. Pase el gate y la regresión completa.

Una tarea no se marca COMPLETA porque se pueda hacer: se marca cuando hay una
prueba que lo demuestra. Si la capacidad no existe en los datos, se queda
PENDIENTE o BLOQUEADA, y se dice por qué.