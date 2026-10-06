# GARANTÍAS PRE-IA — DF Chronicles

> Documento canónico de seguridad conceptual del núcleo.
> Cada garantía enlaza a una **prueba o evidencia concreta**. Sin eso no es
> una garantía: es una intención.

---

## 1. Datos — qué puede producir

| Salida (verificada en `dataset_version.json`) | Líneas |
|---|---:|
| `historical_events` | 57.215 |
| `historical_figures` | 11.144 |
| `entities` | 1.067 |
| `regions` | 840 |
| `sites` | 734 |
| `artifacts` | 427 |
| `written_contents` | 2.341 |
| `underground_regions` | 405 |
| `entity_populations` | 243 |
| `world_constructions` | 122 |

Cada salida tiene `sha256` y `bytes`. **Estado: VERIFIED.**
Definición del dataset esencial: `DATASET_ESENCIAL_PRE_IA.md`.

---

## 2. Conocimiento — qué significa «conocido»

> **Lo que el sistema sabe ≠ lo que el jugador sabe.**

| Estado | Significado |
|---|---|
| `WORLD_KNOWLEDGE` | Existe en el dataset |
| `PLAYER_KNOWLEDGE` | El jugador puede conocerlo jugando |
| `EXTERNAL_KNOWLEDGE` | Proviene de fuera del mundo |
| `INFERENCE` | Derivado, nunca automático |

**Regla: `TRUTH` ≠ `DISCLOSURE_PERMISSION`.** Un dato puede ser verdadero y no
estar autorizado.

---

## 3. Visibilidad

**`isTileVisible(x,y,z) == true` significa «visible AHORA». Nada más.**

Un `false` significa **`NOT_VISIBLE_NOW`**. **Nunca** significa `NEVER_SEEN`.

Medido sobre 125 tiles de una fortaleza real: **100 visibles, 25 no**. El 20 %
de los tiles de la propia fortaleza no son conocimiento del jugador según el
propio juego. **VERIFIED.**

---

## 4. Histórico — qué NO puede afirmar

```
historical_discovery = SEMANTICALLY_INSUFFICIENT
```

Existe `map_block.fog_of_war` (`uint8_t[16][16]`), pero se midió en **625
tiles** de 5 cajas y valió **0 en todos**, con `isTileVisible` tanto `true`
como `false`. **No discrimina.**

Demostrarlo exigiría zona explorada **y** zona vírgena comparable, lo que
requeriría alterar la partida. **Fuera de alcance. No bloquea PRE-IA.**

---

## 5. Identidad

| Identificador | Alcance | Estado |
|---|---|---|
| `dataset_id` (`v1-04170363943d4ba1`) | **Contenido**, no estado | VERIFIED |
| `df_id` de entidad | Estable dentro de una carga | VERIFIED |
| `world_folder` | **LOCAL** de carpeta de save | VERIFIED como local |
| Identidad **portable** de mundo | — | **NOT_PROVEN** |

`world_folder` devuelve formatos distintos según instalación: `1` (AnkerGames,
DF 53.16) y `region1`/`region2` (Bay 12 Games). **No se presenta como
identidad universal.**

`dataset_id` identifica **contenido**: dos mundos idénticos → mismo `dataset_id`.

---

## 6. Temporalidad

| Tiempo | Qué es | NO es |
|---|---|---|
| `game_year`/`month`/`day` | Fecha **del juego** | Tiempo real |
| `observed_at` | Momento **de observación** (UTC) | Tiempo del juego |
| `updated` (manifest) | Momento **de procesamiento** | — |

**`state_version`: NO EXISTE.** P1.3 demostró que no hay identidad del estado
del mundo vivo. **No se inventa.**

---

## 7. Certainty

| Valor | Significado |
|---|---|
| `FACT` | Establecido con evidencia |
| `DERIVED` | Derivado de un hecho |
| `UNKNOWN` | No se puede determinar |

Regla del contrato (`API.md`): `FACT` con identificador; `UNKNOWN` si no se
puede determinar. Implementada en `servicio.envolver_ficha`.

**CERTIFICADO POR MUTATION TESTING:**

| Mutación | Estado |
|---|---|
| **M01** certainty del envelope FOUND → UNKNOWN | **KILLED** |
| **M02** certainty condicional → siempre FACT | **KILLED** |
| M07 `deepcopy` → copia superficial | **NOT_APPLICABLE** |

M01 muere porque un test detecta una **alteración observable del contrato**.

---

## 8. Evidencia y procedencia

Todo dato externo conserva `observation_id`, `source`, `observed_at`,
`visibility`, `certainty`, `dataset_id`.

`observation_id` es un **contador monotónico dentro de un fichero**. **NO es**
identidad de mundo **NI** versión de estado.

---

## 9. Escritura — solo lectura

Auditoría sobre `api.py`, `servicio.py`, `servicio_consulta.py`,
`adaptador_consulta.py`, `config.py`, `nucleo.py`, `verificacion_semantica.py`,
`validar_semantica.py`, buscando:

```
set_tiletype · spawnFlow · addItemSpatter · addMaterialSpatter
setTileAquifer · removeTileAquifer · setTileAssignment · resetTileAssignment
SetPauseState · SetCurrentWeather · dfhack.timeout
```

**CERO coincidencias → `READ_ONLY = VERIFIED`.**

---

## 10. Límites de extracción

| Límite | Valor | Dónde |
|---|---:|---|
| Tiles por barrido | **20.000** | `investigar_fog.lua` (`_G.LIMITE`) |
| Muestra cartográfica | 5×5×5 | `prototipo_mapa.lua` |
| Registros diagnósticos | 40 | `prototipo_mapa.lua` |

**Prohibido el escaneo abierto.** Un cúmulo de 256³ (16,7 M tiles) bloqueó
DFHack varios minutos. Desde entonces el tope está **en el código**.

---

## 11. Integridad de la partida

| Comprobación | Resultado |
|---|---|
| Tick en 4 observaciones con partida pausada | **Idéntico** |
| Ficheros de partida escritos por las pruebas | **0** |
| Hashes de producción antes/después | **Idénticos** |

---

## 12. API y Web

```
HTTP → api.py → adaptador_consulta → servicio_consulta → núcleo
```

**13 rutas** delegan; el adaptador hace **20 llamadas** al servicio; **cero**
lógica de dominio en `api.py`. La Web **consume**: `certeza()` lee la etiqueta,
no la calcula.

**Demostrado por mutación**: M09 → `probar_api.py` falla.

---

## 13. IA

```
IA = NO INTEGRADA
```

Sin modelos, embeddings, prompts, inferencia ni tool calling. **Cero
dependencias de IA.**

La IA futura será **otro consumidor** de `servicio_consulta`. **No tendrá
autoridad arquitectónica**: no podrá establecer verdad, verificación,
visibilidad ni política.
