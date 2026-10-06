# DATA QUERY SERVICE CONTRACT

**Capa de consulta determinista de DF-Chronicles.**

Versión del contrato: **1**
Módulo: `dfchron/servicio_consulta.py`
Pruebas: `dfchron/pruebas/probar_servicio_consulta.py`

---

## 1. QUÉ ES

Una frontera estable para consultar el conocimiento estructurado del núcleo
**sin acceder a sus internals**, sin JSONL, sin `Archivo`, sin `Indice`.

```
consumidor ──► Query Service ──► núcleo ──► dataset
```

El consumidor no sabe si detrás hay un índice, un JSONL o una base de datos.
Solo sabe que el contrato no cambia.

## 2. QUÉ NO ES

- **No es un índice.** No hay estructura de datos nueva. Se consulta el índice
  que el núcleo ya construye.
- **No es un oráculo.** No responde más de lo que el núcleo puede demostrar.
- **No tiene IA.** Ni LLM, ni RAG, ni embeddings, ni agentes, ni prompts, ni
  memoria conversacional. **Nada de eso existe en esta capa.** La frontera
  funciona aunque se elimine cualquier IA del sistema.
- **No conoce el mundo real** de Dwarf Fortress. Solo lo que está en el dataset.

## 3. INDEPENDENCIA DE LA INTERFAZ

El contrato se define **por encima** de cualquier transporte. Lo mismo vale
para HTTP, para la Web, para la CLI y para una llamada Python interna:

```
              ┌──────────────────────────────┐
API HTTP  ───►│                              │
Web      ───►│   CAPA DE CONSULTA            │──► Núcleo
CLI      ───►│   DETERMINISTA                │
Interno  ───►│                              │
              └──────────────────────────────┘
```

Una interfaz nueva **no** implementa consulta: se apoya en esta capa.

## 4. OPERACIONES

Son seis. Deliberadamente pocas: la primera versión no se inventa el alcance,
lo demuestra.

| # | Operación | Qué hace | Delega en |
|---|-----------|----------|-----------|
| 1 | `obtener_entidad(tipo, df_id)` | La ficha de una entidad | `servicio.figura/entidad/…` |
| 2 | `obtener_atributo(tipo, df_id, atributo)` | Un atributo, o que no existe | la ficha del núcleo |
| 3 | `buscar_relaciones(origen, tipo_relacion, limite)` | Relaciones **registradas** | `servicio.figura_relaciones` |
| 4 | `contar(tipo, filtro)` | Cuántos hay, con filtro `==` | el índice del núcleo |
| 5 | `verificar(tipo, id, predicado, objeto)` | Verificar una afirmación | **`verificacion_semantica`** |
| 6 | `obtener_evidencia(tipo, df_id, campos)` | La procedencia del dato | **`ia_conocimiento.evidencia_de`** |

### 4.1 No hay duplicación

Este es el punto arquitectónico central. **Cada operación delega en algo que ya
existía.** La capa añade el sobre común; no la lógica de conocimiento.

| Necesidad | Dónde vive YA | Qué añade esta capa |
|-----------|---------------|---------------------|
| Índice | `nucleo.Archivo` / `Indice` | Nada. Lo usa. |
| Búsqueda y fichas | `servicio.*` | El sobre con evidencia |
| Envelope de respuesta | `envolver_lista/ficha/estado` | `identity`, `evidence`, `alcance` |
| Errores | `servicio.error()` | Reutiliza sus códigos |
| Paginación | `envolver_lista` (`truncado`, `limit`, `offset`) | Un tope duro (`LIMITE_MAXIMO`) |
| Evidencia y procedencia | `ia_conocimiento.evidencia_de` | Nada. La pide. |
| Verificación | `verificacion_semantica` | Nada. Traduce el veredicto. |

No se creó un índice nuevo, ni un módulo de búsqueda propio, ni una segunda
implementación de la verificación.

## 5. RESPUESTA

Toda respuesta tiene la misma forma:

```jsonc
{
  "estado": "FOUND",              // el estado del conocimiento
  "data": { },                    // el dato, o null
  "identity": {                   // quién es, si se puede probar
    "tipo": "figura",
    "df_id": "712"
  },
  "evidence": {                   // de dónde viene y de qué mundo
    "entidad": "figura",
    "df_id": "712",
    "funcion": "nucleo.Archivo.ficha_figura",
    "fuente": ["legends.xml"],
    "state_version": "v1-04170363943d4ba1"
  },
  "dataset_id": "v1-04170363943d4ba1",
  "alcance": { "puede": [ ], "no_puede": [ ] },

  // y las claves del envelope de `servicio`, intactas
  "ok": true,
  "certainty": "FACT",
  "meta": { }
}
```

Las claves de `servicio` **no se renombran ni se eliminan**: se añaden. Un
cliente antiguo que solo lea `ok` y `data` sigue funcionando.

`identity` y `evidence` son `null` cuando no se pueden probar. No se rellenan
con algo verosímil.

## 6. ESTADOS

**No se inventan estados nuevos.** Se usan los que el proyecto ya tenía.

| Estado | Significado | Cómo se expresa |
|--------|-------------|-----------------|
| `FOUND` | El dato existe y es verificable | `ok: true` + `certainty` del dato |
| `NOT_FOUND` | Se consultó bien; **no existe** | `ok: false`, código `NO_ENCONTRADO` (ya existía) |
| `NOT_VERIFIED` | Se consultó bien; **no se puede determinar** | `ok: false`, código `NO_VERIFICADO` (nuevo) |
| `INVALID_QUERY` | La consulta no es válida | `ok: false`, código de `servicio` (ya existía) |
| `DATA_UNAVAILABLE` | Falta la fuente | `ok: false`, código `NO_DISPONIBLE` (nuevo) |

### 6.1 Por qué hacen falta dos códigos nuevos

Porque **`NOT_FOUND` y `NOT_VERIFIED` no son lo mismo**, y separarlos es el
requisito más importante del contrato:

> *No existe* es una afirmación sobre el mundo.
> *No se puede determinar* es una afirmación sobre lo que sabemos del mundo.

Colapsarlos en un solo código destruiría esa distinción. Es exactamente el
error de convertir **ausencia de evidencia** en **evidencia de ausencia**.

Son los **mínimos** añadidos. Todo lo demás se reusa.

## 7. ERRORES

| Situación | Respuesta |
|-----------|-----------|
| Consulta válida + resultado existente | `FOUND` con evidencia |
| Consulta válida + entidad inexistente | `NOT_FOUND` |
| Consulta válida + dato insuficiente | `NOT_VERIFIED` |
| Consulta inválida | `INVALID_QUERY` |
| Fuente no disponible | `DATA_UNAVAILABLE` |

**Un error interno nunca se convierte en `NOT_FOUND`.**
**La falta de datos nunca se convierte en `FOUND`.**

## 8. IDENTIDAD

Solo se usa el `df_id` real que el dataset declara:

| Tipo | Identidad |
|------|-----------|
| `figura`, `entidad`, `sitio`, `evento`, `artefacto` | `df_id` del juego |
| `relacion`, `era`, `suplemento` | **ninguna demostrable** |

Para los tres últimos, `identity` es `null` y el estado es `NOT_VERIFIED`.

**Nunca se usa silenciosamente** como identidad: índice de array, posición,
nombre, hash arbitrario ni `record_id` posicional.

## 9. RELACIONES

Solo se exponen relaciones **realmente registradas**: 12 tipos literales del
XML (no se traducen ni se reinterpretan) y las instancias que el grafo contiene.
No se reconstruyen ni se infieren.

Se distingue entre dos casos que no son el mismo:

- la figura existe pero **no tiene** esa relación → lista vacía;
- la figura **no existe** o **no tiene identidad** → `NOT_FOUND` /
  `NOT_VERIFIED`.

## 10. TEMPORALIDAD

**`dataset_id` identifica contenido. NO es un reloj.** (decisión D14)

Un `dataset_id` distinto significa **contenido distinto**, y nada más. De aquí
se sigue, y la capa lo respeta:

- **No hay caducidad.** Un dataset nuevo no invalida el anterior.
- **No hay «actual» ni «obsoleto».** No hay reloj contra el que medir.
- **No se fabrican** `timestamp`, `tick`, ni marcas de tiempo.
- `state_version` es el `dataset_id` real, leído del disco por el núcleo.

La capa transporta lo que hay y no fabrica lo que falta.

## 11. FILTROS

Semántica formal, mínima:

```
contar("figura", {"race": "MINOTAUR"})
```

- **Solo `==`**, comparación **exacta** de cadenas.
- `minotaur` **no** cuenta como `MINOTAUR`: no se normaliza.
- Un campo que el dataset no declara → `NOT_VERIFIED`, **no** filtro vacío.
- Un filtro que no es un objeto → `INVALID_QUERY`.

«Los mejores mineros» **no pertenece a esta capa**. No hay operadores de orden,
rangos ni texto libre, y no se planean sin necesidad demostrada.

## 12. LÍMITES

- `LIMITE_DEFECTO = 200`, `LIMITE_MAXIMO = 1000`.
- Un `limite` enorme se **recorta** al máximo; nunca se devuelve el dataset.
- Un `limite` inválido (`0`, `-1`, `"x"`, `2.5`, `True`) → `INVALID_QUERY`.
- El orden es determinista y `truncado` indica siempre si falta algo.

## 13. DETERMINISMO

La misma consulta sobre el mismo dataset produce **exactamente** el mismo
resultado: valores, orden, IDs, evidencia y serialización.

No depende del hash de Python, del orden de un diccionario externo, del sistema
de ficheros, del proceso ni de la hora actual. La ausencia de tiempo se
comprueba en las pruebas: ningún resultado contiene `timestamp`.

## 14. INMUTABILIDAD

Consultar es **leer**. La capa no escribe en el dataset ni en el estado del
núcleo, y devuelve copias, no referencias vivas.

## 15. LÍMITES DE LA CAPA

Queda **explícitamente fuera**:

- lenguaje natural;
- inferencia semántica libre;
- predicción;
- razonamiento histórico no respaldado;
- relaciones que no existen en el dataset;
- datos externos y conocimiento del mundo real;
- conocimiento oculto ausente del dataset;
- interpretación subjetiva;
- cualquier forma de IA.

## 16. SEGURIDAD

Toda entrada se valida antes de tocar el núcleo:

- IDs enormes, vacíos, con `\x00`, con `<script>`, con rutas (`../../`) o con
  Unicode → respuesta de estado, nunca excepción, nunca acceso a disco.
- Tipos no-string, listas y diccionarios donde se espera un tipo → `INVALID_QUERY`.
- `limite` se normaliza y se recorta antes de usarse.
- No se exponen rutas internas del dataset en la evidencia.

## 17. SERIALIZACIÓN

Todo resultado es JSON válido y estable. No contiene objetos internos de
Python, ni `<class`, ni `object at 0x`, ni rutas del dataset.

## 18. COMO SE USA

### Desde Python

```python
from dfchron import servicio_consulta as consulta

r = consulta.obtener_entidad("figura", "712")
r["estado"]            # "FOUND"
r["identity"]          # {"tipo": "figura", "df_id": "712"}
r["evidence"]          # {... "state_version": "v1-..."}
consulta.contrato()    # el contrato, legible desde el código
```

### Desde HTTP — `dfchron/adaptador_consulta.py`

El adaptador traduce HTTP a este contrato y de vuelta. **No decide nada del
dominio.** La API usa dos vías a la vez, porque una sola dejaría un hueco:

| Vía | Rutas | Qué aporta |
|-----|-------|------------|
| **Enriquecimiento** | `/api/figuras/{id}`, `/api/entidades/{id}`, `/api/sitios/{id}`, `/api/artefactos/{id}`, `/api/eventos/{id}`, `/api/figuras/{id}/relaciones` | Las fichas y relaciones de siempre ahora llevan `estado`, `identity`, `evidence`, `dataset_id` y `alcance` |
| **Contrato explícito** | `/api/consulta/...` | Las seis operaciones, con sus estados, por HTTP |

```http
GET /api/consulta/entidad/figura/712
GET /api/consulta/atributo/figura/712/nombre
GET /api/consulta/relaciones/712?limit=50
GET /api/consulta/contar/figura?campo=race&valor=DRAGON
GET /api/consulta/verificar?tipo=figura&id=712&predicado=existe
GET /api/consulta/evidencia/figura/712?campos=nombre
GET /api/consulta/contrato
```

**El envelope se amplía, no se sustituye.** Las rutas viejas conservan `ok`,
`data`, `status`, `certainty`, `meta` y los campos heredados. Solo se **añaden**
claves. Medido sobre 48 rutas: **0 regresiones**.

**Códigos HTTP.** Se derivan del estado, con un mapa declarado
(`HTTP_POR_ESTADO`) que mantiene la distinción de la §6:

| Estado | HTTP |
|--------|------|
| `FOUND` | 200 |
| `NOT_FOUND` | 404 |
| `NOT_VERIFIED` | **200** (no 404: diría que no existe) |
| `INVALID_QUERY` | 400 |
| `DATA_UNAVAILABLE` | 503 |

### Desde la Web

Las dos Webs (`dfchron/web/` y `dfchron/site/`) hablan **solo** con `/api/...`.
Ninguna lee el dataset. Muestran el estado y la evidencia que llegan, y
**leen** `env.estado` en vez de deducirlo: si la API dice `NOT_VERIFIED`, la
interfaz dice «no se puede determinar con estos datos», nunca «no existe».

Verificación cruzada en
`dfchron/pruebas/probar_integracion_consulta.py::TestUnificacion`.

---

## RELACIÓN CON LA IA

Esta capa **no contiene IA y no la necesita**. Cuando exista una IA, será **un
consumidor más** de este contrato, por fuera de la frontera:

```
IA (futura) ──► DATA QUERY SERVICE ──► núcleo
```

`/api/consulta/*` **no** es «una API para la IA». Es una API de datos
determinista, útil exista o no IA. No hay endpoints de IA, ni atajos, ni
preparativos para futuros modelos.

Si se eliminase por completo la IA del proyecto, esta frontera **seguiría
funcionando exactamente igual**. Ese es el criterio de diseño.