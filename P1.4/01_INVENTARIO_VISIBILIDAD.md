# P1.4 — INVENTARIO DE VISIBILIDAD (Fase B) y MAPA DE APIs (Fase C)

> Criterio **estrictamente semántico**: *¿puede verlo un jugador normal por la
> interfaz habitual?*
> Que DFHack pueda obtenerlo **no** lo hace visible. Solo `VISIBLE` y
> `VISIBLE_CONDITIONAL` pueden entrar en el perímetro del observador.

---

## Tabla maestra de datos.extraídos en vivo

Valores **medidos hoy** contra el mundo cargado, no copiados de documentación.

| # | Dato | Valor real | Visibilidad | API | Solo lectura |
|---|---|---|---|---|:---:|
| 1 | Nombre del mundo | `Xah Alu` | `VISIBLE` | `dfhack.translation.translateName(df.global.world.world_data.name)` | Sí |
| 2 | Año | `10` | `VISIBLE` | `dfhack.world.ReadCurrentYear()` | Sí |
| 3 | Mes | `5` | `VISIBLE` | `dfhack.world.ReadCurrentMonth()` | Sí |
| 4 | Día | `5` | `VISIBLE` | `dfhack.world.ReadCurrentDay()` | Sí |
| 5 | Estación | `1` | `VISIBLE` | `df.global.cur_season` | Sí |
| 6 | Clima | `0` | `VISIBLE` | `dfhack.world.ReadCurrentWeather()` | Sí |
| 7 | En pausa | `true` | `VISIBLE` | `dfhack.world.ReadPauseState()` | Sí |
| 8 | Población | `14` | `VISIBLE` | `#dfhack.units.getCitizens()` | Sí |
| 9 | Profesiones | `{Bone Carver:1, Doctor:1, …}` | `VISIBLE` | `dfhack.units.getProfessionName()` | Sí |
| 10 | Razas | `{DWARF: 14}` | `VISIBLE` | `dfhack.units.getRaceName()` | Sí |
| 11 | Modo fortaleza | `true` | `VISIBLE_CONDITIONAL` | `dfhack.world.isFortressMode()` | Sí |
| 12 | Carpeta del mundo | `region1` | `VISIBLE_CONDITIONAL` | `dfhack.world.ReadWorldFolder()` | Sí |
| 13 | Tick del año | `173026` | **`NO_VISIBLE`** | `dfhack.world.ReadCurrentTick()` | Sí |

**13 hechos, 12 imprimibles.** El tick queda registrado pero **marcado fuera del
perímetro**, y el validador lo comprueba automáticamente.

---

## Justificación de cada clasificación

### `VISIBLE` — el jugador lo ve en su interfaz normal

| Dato | Por qué |
|---|---|
| Año / Mes / Día | La fecha aparece en la interfaz de la fortaleza y en la ficha de cualquier casilla |
| Estación | Visible al seleccionar casillas; también en las fichas de la fortaleza |
| Clima | La interfaz de la fortaleza muestra el clima actual |
| En pausa | El jugador controla la pausa; sabe si la partida está pausada |
| Población | La pantalla de población de la fortaleza muestra los ciudadanos |
| Profesiones / Razas | La lista de ciudadanos muestra nombre, raza y profesión |

### `VISIBLE_CONDITIONAL`

| Dato | Por qué |
|---|---|
| Modo de partida | Depende del modo en el que esté la partida (no es siempre fortaleza) |
| Carpeta del mundo | El jugador la ve si abre sus carpetas de partida, pero **no es conocimiento del mundo**: es un identificador técnico. Se usa para **no mezclar mundos**, no para contar como dato de juego |

### `NO_VISIBLE` — DFHack lo da, el jugador no

| Dato | Razón |
|---|---|
| **Tick del año** | Es un **contador interno**. El jugador ve una *fecha* (año/mes/día); nunca un tick crudo. Extrapolar el valor numérico del tick **no** es algo que el jugador pueda leer en ningún sitio |

Se registra por trazabilidad técnica, pero el observador lo declara
explícitamente fuera del perímetro imprimible.

---

## B4 Entorno y B5 Acontecimientos —研究的, no extraídos

| Categoría | Estado | Motivo |
|---|---|---|
| Clima / tiempo | **DEMOSTRADO** | `ReadCurrentWeather()` → `0` |
||Notificaciones, muertes, nacimientos, llegadas, combates | **NO INVESTIGADO** | Fuera del presupuesto de esta primera pasada. `eventful` es el mecanismo candidato y está presente |
| Salud, heridas, pensamientos, relaciones individuales, inventario | **NO INVESTIGADO** | Ídem |
| Animales, visitantes, migrantes | **NO INVESTIGADO** | `dfhack.units.isVisitor()` / `isPet()` existen y son solo lectura; no se han ejercido |

> **Honestidad:** `UNKNOWN` de investigación, no `NO_VISIBLE`. Que no se haya
> investigated **no** autoriza a incluirlos, pero tampoco demuestra que sean
> invisibles. Queda pendiente, no descartado.

---

## Hallazgo estructural: `dfhack.units.isVisible`

DFHack incluye su propio predicado de visibilidad por unidad. Es relevante
porque permite, en el futuro, implementar el perímetro de conocimiento **con el
mismo criterio que usa la propia herramienta**, en vez de inventar uno.

```
dfhack.units.isVisible(u)  ->  true   (para un ciudadano)
```

---

## Codificación: un hallazgo que condiciona el catálogo

**`dfhack.translation.translateName()` devuelve CP437, no UTF-8.**

Comprobado con un ciudadano real:

```
bytes escritos = 53 86 6B 7A 75 6C ...  ->  "S\x86kzul Tulonroder"
```

`0x86` es la **é** en CP437. Tal cual, ese texto **rompe** la exigencia de
«codificación UTF-8» del JSONL.

**Y no es un caso teórico.** En la partida actual:

| Comprobación | Resultado |
|---|---|
| Ciudadanos totales | 14 |
| Nombres solo-ASCII | 7 |
| Nombres con bytes ≥ 0x80 | **7** |

La mitad de la población rompería un lector UTF-8 estricto.

**Decisión tomada en el prototipo:** no escribir bytes que no son UTF-8 ni
fingir que lo son. Un valor con bytes ≥ 0x80 se marca explícitamente como
`__NO_UTF8_PENDIENTE(cp437):<hex>`, que **sí** es válido y reversible
(`53 86 6B...` → `Sékzul Tulonroder`).

No se implementó una tabla parcial CP437→UTF-8: corromperia en silencio los
caracteres que no cubriera. Ver `09_LIMITACIONES_Y_DEUDAS.md`.