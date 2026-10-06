# Informe final · Estado explícito del conocimiento del jugador

**Misión:** construir la capa explícita de `PLAYER_KNOWLEDGE`, separada del
dataset histórico, sin implementar IA.
**Fecha:** 2026-03-03 · **Raíz:** `DF-Chronicles/`

---

## 1. Auditoría — qué existía antes

| Elemento | Estado previo |
|---|---|
| `PLAYER_KNOWLEDGE` | **Constante de texto** (`contrato_ia.py:60`). Sin estado. |
| `no_descubierto` | Marca por defecto `True` en todo lo que sale del puente. |
| Estado persistente del jugador | **No existía.** No había ningún fichero. |
| `puede_revelarse()`, `puede_afirmarse_como_hecho()` | Existían y funcionaban. |
| `Afirmacion` de solo lectura | Existía, **pero solo en el nivel superior**. |

### El hallazgo importante

Bloquear el nivel superior **no era suficiente**. Sondeado antes de tocar nada:

```
a["evidence"][0]["df_id"]   = "999"   → MUTADO (era "87")
a["evidence"][0]["funcion"] = "falsa"  → MUTADO
a["evidence"].append(...)               → MUTADO
ev["datos_utilizados"].append(...)       → MUTADO
ev["datos_utilizados"].sort()            → MUTADO
```

**La procedencia de un secreto era falsificable sin dejar rastro.** `disclosure`
no cambiaba, así que no había fuga directa de contenido, pero la evidencia —que
es la base de la auditoría— se podía reescribir a voluntad.

### Granularidad auditada (no inventada)

`relaciones_de_figura(712)` devuelve objetos **sin identificador**. No existe
`relation_id`. Se decidió **no inventarlo**.

---

## 2. Diseño — cómo se representa `PLAYER_KNOWLEDGE`

`dfchron/estado_conocimiento.py`. Estado de **ejecución**, fuera del dataset,
como `exports/` está fuera de `processed/`.

**Ubicación:** `DF-Chronicles/estado/estado_conocimiento.json`
(override: `DFCHRON_ESTADO_ROOT`). Se reutiliza la protección que ya tenía el
proyecto: `rutas.es_ruta_protegida()` aborta si la ruta cae en
`original_data/`, `processed/` o `validation/`.

**Esquema:**
```json
{"schema_version": 1,
 "dataset_id": "v1-04170363943d4ba1",
 "knowledge": {"campo|sitio:87:coordenadas": {
   "tipo": "sitio", "df_id": "87", "campo": "coordenadas",
   "motivo": "el jugador minimizó el mapa"}}}
```

**Granularidad (la que el núcleo sostiene):** `figura`, `sitio`, `entidad`,
`artefacto`, `evento` por `df_id`; dos niveles — entidad y campo.
`relacion` **no soportada**, con el motivo declarado en `TIPOS_NO_SOPORTADOS`.

**API:** `marcar_conocido`, `marcar_desconocido`, `esta_conocido`,
`obtener_conocimiento`, `limpiar_conocimiento`, `compatibilidad`.

**Las tres reglas:**
1. `conocido ≠ verdad`
2. `conocido ≠ revelable`
3. `WORLD_KNOWLEDGE → PLAYER_KNOWLEDGE` nunca es automático

---

## 3. Archivos

### Creados
| Archivo | Qué |
|---|---|
| `dfchron/estado_conocimiento.py` | La capa de estado |
| `dfchron/pruebas/probar_estado_conocimiento.py` | 48 pruebas |
| `00_SOURCE/ai_knowledge_state_report.md` | Este informe |
| `00_SOURCE/_hashes_antes_estado.txt` | Baseline de 62 ficheros |
| `00_SOURCE/_hashes_despues_estado.txt` | Verificación final |

### Modificados
| Archivo | Cambio | Justificación |
|---|---|---|
| `dfchron/contrato_ia.py` | `_SolaLectura`, `_ListaSolaLectura`, `_congelar_evidencia()`, `__copy__`/`__deepcopy__` | §14: la evidencia anidada era mutable |
| `dfchron/pruebas/probar_contrato_ia.py` | +5 pruebas (`TestInmutabilidadAnidada`) | Regresión del arreglo anterior |
| `dfchron/pruebas/aceptacion_mision.py` | Rutas absolutas + `raiz` a 3 niveles | **Bug previo**: buscaban `dfchron/00_SOURCE/`, que no existe |
| `00_SOURCE/ai_knowledge_bridge_report.md` | Anexo A1–A11 | §19 |

**Sin tocar:** `nucleo.py`, `legends.xml`, `legends_plus.xml`, los 56 JSONL,
`api.py`, `servicio.py`, `web/`, `ia_conocimiento.py`, `rutas.py`.

---

## 4. Tests — cifras exactas

| Suite | Antes | Después |
|---|---|---|
| `probar_nucleo` | 48 | 48 |
| `probar_integracion` | 20 | 20 |
| `probar_adversarial` | 39 | 39 |
| `probar_contrato_ia` | 44 | **49** (+5) |
| `probar_puente_conocimiento` | 52 | 52 |
| `probar_estado_conocimiento` | — | **48** (nueva) |
| `probar_api` | 54 | 54 |
| `probar_web` | 65 | 65 |
| `probar_geografia` | 41 | 41 |
| `probar_refresh_cycle` | 28 | 28 |
| `probar_actualizacion` | 43 | 43 |
| **TOTAL** | **434** | **487** (+53) |

Medido, no estimado. Las 11 suites en verde.

---

## 5. Ataques adversariales ejecutados

| # | Ataque | Resultado |
|---|---|---|
| **A** | Marcar `FORBIDDEN` como conocido → ¿se revela? | **NO.** Sigue `puede_revelarse() == False` |
| **B** | Marcar `PLAYER_HIDDEN` conocido → ¿se revela? | **NO.** |
| **C** | `FORBIDDEN → ALLOWED` por mutación | **BLOQUEADO** (nivel superior y anidado) |
| **D** | `PLAYER_HIDDEN → PLAYER_VISIBLE` por mutación | **BLOQUEADO** |
| **E** | Marcar/desmarcar/resetear/`dataset_id` alterado → ¿cambia el dataset? | **NO.** 62/62 hashes idénticos |
| **F** | Editar `dataset_id` a mano | **DETECTADO.** `DatasetDistinto`; `esta_conocido()` → `False` |
| **G** | Marcar todo `WORLD_KNOWLEDGE` como conocido | **IMPOSIBLE.** No existe la API (verificado por AST) |
| + | Mutación anidada de `evidence` (5 vectores) | **BLOQUEADO** — el agujero encontrado |
| + | Copia superficial / profunda del snapshot | **SELLADAS.** El estado real no se entera |
| + | Alias entre dos `obtener_conocimiento()` | **SIN COMPARTIR** estructura |
| + | Lectura repetida | **No escribe** (mtime intacto) |
| + | `schema_version` falsificada | **RECHAZADA**, no se migra sola |

### Prueba estructural anti-ataque
`test_el_estado_no_puede_tocar_la_disclosure` analiza el **árbol sintáctico** de
`estado_conocimiento.py` y falla si aparece una llamada a `convertir`,
`puede_revelarse`, `puede_afirmarse_como_hecho` o `afirmacion`, o si se importa
`contrato_ia`. **No es un grep**: el nombre puede aparecer en la prosa.

### Casos 1–7 (§16): los 7 verdes.

---

## 6. Dataset

`dataset_id` **real**: `v1-04170363943d4ba1`

Leído de `00_SOURCE/dataset_version.json`. **No está hardcodeado** — hay una
prueba que compara ambas fuentes.

---

## 7. Hashes

62 ficheros protegidos (2 XML + 56 JSONL + `nucleo.py`, `validar_semantica.py`,
`integrar_legends.py`, `rutas.py`):

```
antes : 62 ficheros
despues: 62 ficheros
DIFERENCIAS: 0
```

`nucleo.py` = `ccc48ea6...7ce81` — **idéntico al inicial**.

Comprobado **después** de arrancar el servidor y pasar la aceptación: sigue igual.

---

## 8. Determinismo

Tres procesos **independientes**, uno con el orden de marcado invertido:

```
proceso A (orden 1)  5f4600e0f916a548ce9f4a487b0fbbfb4a9767260d5f1bac51fb3f02a58e9280
proceso B (orden 2)  5f4600e0f916a548ce9f4a487b0fbbfb4a9767260d5f1bac51fb3f02a58e9280
proceso A (otra vez) 5f4600e0f916a548ce9f4a487b0fbbfb4a9767260d5f1bac51fb3f02a58e9280
```

**Idénticos byte a byte**, incluso invirtiendo el orden. Sin timestamps, sin
UUID, sin `random`, sin orden de `set`.

---

## 9. Aceptación — SÍ se ejecutó de verdad

**`aceptacion_mision.py` se ejecutó contra el servidor vivo: 20/20, salida 0.**

La limitación de la misión anterior **queda resuelta**. No era un misterio: eran
**dos cosas distintas**:

1. **Una carrera de arranque.** El núcleo tarda unos segundos en cargarse; si el
   cliente prueba antes de que el socket escuche, recibe `WinError 10061`
   (ECONNREFUSED). Se resuelve **esperando a que `/api/salud` responda** de
   verdad, no suponiendo que ya está. Aquí: listo en 2 intentos.
2. **Un bug en el propio script de aceptación** (preexistente, no de esta
   misión): `raiz` subía **2** niveles y buscaba `dfchron/00_SOURCE/…`, que no
   existe — `00_SOURCE/` está un nivel más arriba. El criterio 20 reventaba con
   `FileNotFoundError`. Corregido a 3 niveles; `web/app.js` pasa a ruta
   absoluta. **Ninguna aserción se modificó.**

> No hay variables de proxy en el entorno (`getproxies()` → `{}`), así que no
> era un proxy. Era la carrera, más el path.

---

## 10. IA — no hay ninguna

| Comprobación | Resultado |
|---|---|
| `/api/ai` | **HTTP 404** (servidor real) |
| `/api/chat` | **HTTP 404** |
| `/api/assistant` | **HTTP 404** |
| `/api/ia` | **HTTP 404** |
| `/api/ask` | **HTTP 404** |
| SDK (openai, anthropic, ollama, langchain, transformers, torch…) | **0 en todo el proyecto** |
| RAG / embeddings / vector DB / agentes / streaming | **ninguno** |
| Cambios en `web/` | **ninguno** (probado) |

---

## 11. Limitaciones que siguen existiendo

1. **El estado puede mentir.** Es una afirmación sobre el jugador escrita por el
   sistema. Nada en el dataset la confirma. Inevitable: no hay otra fuente.
2. **Sin granularidad por relación.** El núcleo no da identidad. Documentado en
   `TIPOS_NO_SOPORTADOS`, no escondido.
3. **Un solo jugador.** No hay perspectiva por NPC ni facción.
4. **Sin sincronización.** Dos procesos escribiendo a la vez: gana el último.
   Es un archivo, no una base de datos.
5. **No se registra quién marcó ni cuándo.** El `motivo` es texto libre. Es
   deliberado: una marca de tiempo rompería el determinismo de §18. Si algún día
   hace falta, será un campo aparte y explícito.
6. **`limpiar_conocimiento()` sin argumentos borra todo.** Documentado en el
   docstring y probado; con `tipo`/`df_id` borra solo esa entrada.
7. **La capa no está conectada a nada.** No la usa la API, ni la web, ni el
   puente: es infraestructura, exactamente como se pidió. Su primer consumidor
   real será la futura IA.
8. **No hay repositorio git.** `git status` no es posible
   (`fatal: not a git repository`); la trazabilidad de esta misión es este
   informe y los ficheros de hashes.

---

## Cierre

La frontera de datos queda completa y probada:

```
HISTORIA DEL MUNDO → WORLD_KNOWLEDGE → ┌──────────────────────────┐
                                      │ ¿qué conoce el jugador? │
                                      │ estado_conocimiento.py  │
                                      └──────────────────────────┘→ VERDAD → DIVULGACIÓN → [IA, después]
```

Las tres separaciones —`WORLD`/`PLAYER`, verdad/divulgación,
conocimiento/revelable— no son convenciones: están **probadas y atacadas**, y
el intento de romperlas es lo que dejó el contrato con la evidencia congelada.

**La IA sigue sin existir. Y ahora se sabe por qué todavía no.**