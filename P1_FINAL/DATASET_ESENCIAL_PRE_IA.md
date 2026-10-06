# DATASET ESENCIAL PRE-IA

> Definición formal del mínimo dataset necesario para que DF Chronicles cuente
> una crónica de una fortaleza.
>
> **Regla de oro:** no se añade nada porque «podría ser útil», «DFHack lo
> expone» o «la wiki lo menciona». Cada campo entra solo si **existe**, está
> **probado** y es **necesario**.

---

## Principio de selección

Un campo entra en el dataset esencial si cumple **las tres**:

1. **EXISTE** — hay un extractor que lo produce hoy.
2. **PROBADO** — hay una prueba o un hash que lo respalda.
3. **NECESARIO** — sin él no se puede contar una crónica básica.

Si falla una, el campo se registra como `NOT_AVAILABLE`, `NOT_PROVEN` u
`OUT_OF_SCOPE` en `DATASET_ESENCIAL_COBERTURA.md`.

---

## A. Identidad del mundo

| Campo | Fuente | Estado |
|---|---|---|
| `dataset_id` | `ia_conocimiento.DATASET_ID` | **IMPLEMENTED** — `v1-04170363943d4ba1` |
| Nombre del mundo | `translateName(world_data.name)` | **IMPLEMENTED** — `Xah Alu` |
| Carpeta del mundo | `ReadWorldFolder()` | **IMPLEMENTED** — **solo local** |
| Identidad portable | — | **NOT_PROVEN** |

**Nada más se acepta como identidad.** Ni nombres, ni posiciones, ni índices
mutables, ni orden de aparición.

---

## B. Fortaleza

| Campo | Fuente | Estado |
|---|---|---|
| Población | `#getCitizens()` | **IMPLEMENTED** |
| Razas | `getRaceName(u)` | **IMPLEMENTED** |
| Profesiones | `getProfessionName(u)` | **IMPLEMENTED** |
| Fecha de juego | `ReadCurrentYear/Month/Day` | **IMPLEMENTED** |
| Estación | `df.global.cur_season` | **IMPLEMENTED** |
| Clima | `ReadCurrentWeather()` | **IMPLEMENTED** |
| Estado de pausa | `ReadPauseState()` | **IMPLEMENTED** |
| Nombre de la fortaleza | — | **NOT_AVAILABLE** (DF no lo expone a DFHack) |

---

## C. Unidades

| Campo | Fuente | Estado |
|---|---|---|
| Nombre | `translateName(getVisibleName(u))` + CP437→UTF-8 | **IMPLEMENTED** |
| Raza | `getRaceName` / `getRaceReadableName` | **IMPLEMENTED** |
| Profesión | `getProfessionName` | **IMPLEMENTED** |
| Posición | `u.pos` | **IMPLEMENTED_CONDITIONAL** — exige `units.isVisible` |
| Edad | `units.getAge` | **IMPLEMENTED** |
| Sexo | `isFemale` | **IMPLEMENTED** |
| Estrés | `getStressCategory` | **IMPLEMENTED** |
| Visible al jugador | `units.isVisible` | **IMPLEMENTED** |
| Salud detallada, heridas, enfermedades | — | **OUT_OF_SCOPE** |
| Pensamientos, relaciones familiares | — | **OUT_OF_SCOPE** |
| Inventario, equipo | `dfhack.items` existe | **OUT_OF_SCOPE** (no ejercitado) |

**Posición es condicional, no libre.** Solo se emite si `isVisible == true`.

---

## D. Terreno

| Campo | Fuente | Estado |
|---|---|---|
| Coordenada x/y/z | `forEachTile` | **IMPLEMENTED** |
| Tipo de tile | `getTileType` + `df.tiletype[]` | **IMPLEMENTED** |
| Visibilidad | `isTileVisible` | **IMPLEMENTED** |
| Bioma | `getBiomeType` | **IMPLEMENTED_COMO_BOOKLEAN** — devuelve `true`/`false`, no un bioma |
| Región | `getRegionBiome` | **NOT_AVAILABLE** — devuelve objeto, no identificador |
| Memoria histórica | `fog_of_war` | **SEMANTICALLY_INSUFFICIENT** |

26 tipos de terreno leídos en una muestra de 100 tiles: `MineralWall`,
`TreeTrunkEW`, `GrassDarkFloor1`, `Sapling`, `Shrub`, `OpenSpace`…

---

## E. Eventos y construcción (dataset histórico)

| Campo | Líneas | Estado |
|---|---:|---|
| Eventos históricos | 57.215 | **IMPLEMENTED** |
| Figuras históricas | 11.144 | **IMPLEMENTED** |
| Entidades | 1.067 | **IMPLEMENTED** |
| Sitios | 734 | **IMPLEMENTED** |
| Regiones | 840 | **IMPLEMENTED** |
| Construcciones del mundo | 122 | **IMPLEMENTED** |
| Artefactos | 427 | **IMPLEMENTED** |
| Contenidos escritos | 2.341 | **IMPLEMENTED** |

---

## F. Lo que deliberadamente NO entra

| Descartado | Motivo |
|---|---|
| `game_tick` como fecha | `NOT_VISIBLE` — el jugador ve fecha, no un contador |
| Excavación geológica completa | `OUT_OF_SCOPE` — requiere expedición |
| Minerales y recursos ocultos | `OUT_OF_SCOPE` |
| Escuadras yAscendance militar | `NOT_AVAILABLE` — `dfhack.military` tiene **5 miembros**, 2 de escritura |
| Eventos **en vivo** | `OUT_OF_SCOPE` — el observador PRE-IA no se conecta al dataset |
| Cualquier campo «porque podría servir» | No cumple la regla de oro |

---

## Ampliación

El dataset esencial **no es cerrado**: es la base mínima. Ampliarlo requiere
solo:

1. Un extractor nuevo (o uno existente subutilizado).
2. Procedencia con `dataset_id`.
3. Una prueba.

Sin cambiar el núcleo ni el contrato.
