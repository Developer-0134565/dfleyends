# P1 — VERSIONADO DEL MUNDO VIVO

> **Estado: P1 ABIERTA. NO RESUELTA.**
> La investigación ha demostrado que **no existe hoy una identificación fiable del
> estado de un mundo vivo** en DF-Chronicles, y que la que parece existir
> (`state_version`) **no es lo que su nombre afirma**. No se ha implementado nada.
> Este documento es investigación, auditoría y diseño. Ninguna conclusión sin
> evidencia se ha marcado como demostrada.

- **Misión:** P1 — Versionado del mundo vivo.
- **Naturaleza:** investigación / auditoría / diseño. **Cero implementación.**
- **Cambios en producción:** ninguno. Verificado por hash en el Anexo A.
- **IA introducida:** ninguna.

---

## 1. Problema

P1 pregunta:

> **¿Cómo sabemos exactamente de qué estado del mundo procede cada dato que el
> sistema consulta?**

El sistema declara que cada evidencia lleva `dataset_id` y `state_version`
(`dfchron/contrato_ia.py`). La pregunta es si esos dos campos **cumplen** esa
función o si solo parecen cumplirla.

La hipótesis de trabajo era que `state_version` resolvería el problema. **La
investigación demuestra que no**, y de forma estructural, no accidental.

Las tres distinciones que P1 necesita:

```text
¿Qué mundo es?          -> identidad de mundo
¿Qué estado tiene?      -> identidad de estado
 Stocks morph             -> observación (cuándo lo vimos)
```

Un identificador que responda solo a la segunda pregunta **no** permite saber de
qué mundo se trata. Y un identificador derivado del contenido extraído responde
a una cuarta pregunta distinta: *¿qué contiene esto?*

---

## 2. Estado actual

### 2.1 Hallazgo principal: `state_version` **es** `dataset_id`

`state_version` no es un campo independiente. Es el mismo valor, con otro nombre.

```python
# dfchron/ia_conocimiento.py:173
# "Se inyecta aqui el `state_version` real (`DATASET_ID`) ..."
list(fuentes_xml) or None, state_version=DATASET_ID)

# dfchron/ia_conocimiento.py:76
def dataset_id(): ...   # lee dataset_version.json
```

`servicio_consulta.py` documenta la cadena completa:

```text
dataset_id / state_version  ->  ia_conocimiento.DATASET_ID
```

**Consecuencia directa:** la frontera expone dos campos que un consumidor
razonable interpretaría como dos ejes independientes, y que en realidad son **un
solo valor duplicado**. No hay eje temporal. No hay eje de mundo. No hay nada más.

> Esto **no es un bug**: es una decisión previa, deliberada y documentada
> (`contrato_ia.py:105-117` lo justifica: *"No es un tick inventado ... el dataset
> no tiene reloj de juego"*). La auditoría de P1 confirma que el razonamiento fue
> correcto **para un dataset inmutable** y se queda corto en cuanto el mundo es
> mutable.

### 2.2 De dónde viene `dataset_id`

```python
# 00_SOURCE/tools/actualizar_datos.py:104-125
def calcular_dataset_id(salidas):
    texto = json.dumps(salidas, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":"))
    return "v1-" + hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
```

`salidas` son **15 secciones del dataset** (`historical_figures`, `entities`,
`sites`, `historical_events`, …). Es decir:

> **`dataset_id` = SHA-256 del inventario de hashes del contenido extraído.**

No consulta el mundo. No conoce el nombre del mundo. No conoce la fecha del
mundo. No sabe si el mundo es el mismo que ayer.

### 2.3 Evidencia empírica (experimentos temporales, ya eliminados)

**Experimento A — dos ejecuciones distintas producen el MISMO `dataset_id`.**
El repositorio conserva dos backups de extracciones reales:

| Backup | `generado` | `dataset_id` |
| --- | --- | --- |
| `merged-20261003-022539` | `2026-10-03T02:24:16.653+02:00` | `v1-04170363943d4ba1` |
| `merged-20261003-032416` | `2026-10-03T02:25:38.890+02:00` | `v1-04170363943d4ba1` |

Dos extracciones separadas por **82 segundos** → **el mismo identificador de
estado**. Si `dataset_id` fuera un estado del mundo, dos observaciones distintas
del mundo en momentos distintos deberían poder coincidir (el mundo puede no haber
cambiado) — pero aquí no estamos probando eso: estamos probando que el
### 2.4 El XML real no contiene identidad de mundo

Inventario empírico de los **344 tags** de `00_SOURCE/original_data/legends.xml`
(49 223 702 bytes, export real):

| Buscado | Resultado |
| --- | --- |
| `world_name` | **NO APARECE** |
| `world_id` | **NO APARECE** |
| `tick` | **NO APARECE** |
| `seed` / `world_seed` / `worldgen_parms` | **NO APARECE** |
| `save_game` / `fortress` / `map` | **NO APARECE** |
| `year` | 57 215 ocurrencias (1..100), **por evento** |
| `historical_eras` | 1 (única sección global) |

El `df_world` del XML contiene `regions`, `landmasses`, `mountain_peaks`,
`underground_regions`, `rivers` — **geografía, no identidad**.

**Conclusión:** la información de mundo y estado **existe en el juego** (ver §4),
pero **nunca llega al dataset**. La pérdida no es de DF: es del pipeline.

### 2.5 Tabla de conceptos del estado actual

| Concepto | Archivo | Campo/función | Qué identifica | Persistente | Determinista | Fiable para mundo vivo |
| --- | --- | --- | --- | --- | --- | --- |
| `dataset_id` | `dataset_version.json`, `ia_conocimiento.dataset_id()` | `dataset_id` | **Contenido extraído** (15 secciones) | Sí (disco) | Sí | **NO** — ciego a identidad de mundo y a cambios no exportados |
| `state_version` | `ia_conocimiento.py:180` | `state_version=DATASET_ID` | **Lo mismo que `dataset_id`** | Sí (disco) | Sí | **NO** — mismo defecto, con nombre que promete más |
| `snapshot` | — | — | **No existe** | — | — | **NO** |
| `revision` | — | — | **No existe** | — | — | **NO** |
| `tick` | — | — | **No existe en el dataset** | — | — | **NO** |
| `actualizada` | `dataset_version.json` | timestamp ISO | Momento de la **extracción** | Sí (disco) | **NO** (reloj) | **Parcial** — reloj de la máquina, no del mundo |
| `generado` | `backups/*/_hashes.json` | timestamp ISO | Momento de la ejecución | Sí (disco) | **NO** | **Parcial** — mismo defecto |
| `merge.generado` | `dataset_version.json` | timestamp ISO | Momento del merge | Sí (disco) | **NO** | **Parcial** |
| `version_anterior` | `dataset_version.json` | timestamp ISO | Enlace al estado previo | Sí (disco) | **NO** | **Parcial** — encadena extracciones, no mundos |
| `origen` | `dataset_version.json` | ruta absoluta | De qué fichero se leyó | Sí (disco) | Sí | **NO** — es procedencia de fichero, no de mundo |
| Identidad de ejecución | — | — | **No existe** | — | — | **NO** — los backups lo demuestran: 2 ejecuciones, 0 identidad |
| Identidad de mundo | — | — | **NO EXISTE** | — | — | **NO** |
| Identidad de mapa/fortaleza | — | — | **NO EXISTE** | — | — | **NO** |
| Invalidación | `contrato_ia.evidencia_es_actual()` | comparación de igualdad | "¿cambió el contenido?" | No (cálculo) | Sí | **NO** — detecta cambios de contenido, no de mundo |
| Caché | — | — | No hay caché de estado | — | — | **NO** |
---

## 3. Investigación Dwarf Fortress

DF **sí** mantiene un reloj de mundo. El problema es que **DF-Chronicles no lo
extrae**.

### 3.1 El reloj de DF

Descubierto leyendo el código de DFHack instalado (§4), no de suposición:

| Dato | Fuente | Valor / rango |
| --- | --- | --- |
| Año actual | `df.global.cur_year` | entero |
| Tick intra-año | `df.global.cur_year_tick` | contador `seconds72` intra-año |
| Ticks por mes | `TICKS_PER_MONTH` (emigration.lua:28) | `33600` |
| Ticks por año | `TICKS_PER_YEAR` (emigration.lua:29) | `403200` |
| Mes | `ReadCurrentMonth()` | 0–11 |
| Día | `ReadCurrentDay()` | 1–28 |
| Frame counter | `df.global.world.frame_counter` | ticks **desde el inicio del año actual** |

Fuente: `DFHack/hack/scripts/emigration.lua:28-29`, `Lua API.txt:2167-2181`.

### 3.2 Lo que DF NO tiene

De lo inspeccionado (`symbols.xml`, `Lua API.txt`, 344 tags del XML, ~400 scripts
Lua de DFHack):

- **No hay un contador global monotónico de ticks que sobreviva al cambio de año.**
  `frame_counter` está documentado explícitamente como *"the number of game ticks
  since the start of the current game year"* (`Lua API.txt:2173`). **Se reinicia.**
- **No hay identificador de mundo expuesto en el XML exportado** (§2.4).
- **No hay seed de generación de mundo disponible para el exportador**:
  `exportlegends.lua` no escribe ningún `worldgen_parms`.
- **El reloj no es un reloj de pared.** Ver §3.4.

### 3.3 ¿Qué ocurre al guardar, cargar, viajar o cambiar de fortaleza?

**NO DEMOSTRADO — no verificable con el material disponible.**

Dwarf Fortress **no está instalado** en el entorno (verificado: no existe en
`Program Files`, `Steam/steamapps/common`, ni en el workspace), y DFHack está
desacoplado de DF (`DFHack/hack/` sin el binario del juego al lado). El único
`Dwarf Fortress.exe` documentado está en `Downloads`, fuera del workspace, y la
misión prohíbe launches.

Lo que sí se puede afirmar **con evidencia indirecta fuerte** es que *cargar un
save* devuelve el mundo a un estado anterior, y por tanto cualquier contador
derivado del estado del juego **se reinicia a ese valor**. Eso es la razón por la
que el modelo recomendado **no depende del tick de DF**.

| Escenario | Comportamiento esperado | Estado |
| --- | --- | --- |
| Guardar | El estado se persiste; el reloj del mundo queda congelado | **NO DEMOSTRADO** |
| Cerrar y reabrir | El mundo se restaura desde disco; contadores restaurados | **NO DEMOSTRADO** |
| Cargar otro save | Otro mundo, o el mismo en otro punto del tiempo | **NO DEMOSTRADO** |
| Viajar | El mapa se recarga; el reloj avanza normalmente | **NO DEMOSTRADO** |
| Cambiar de fortaleza | Otro sitio del mismo mundo | **NO DEMOSTRADO** |

### 3.4 Timestream: prueba documental de que el reloj no es tiempo

La documentación de DFHack `timestream` es la evidencia más clara de que el
tiempo de DF está desacoplado del tiempo real:

> *"It then balances things out by proportionally advancing the in-game calendar.
> Therefore, more 'happens' per step, and DF has to simulate fewer 'steps' for
> the same amount of work to get done."*
>
> *"DF does critical game tasks every 10 calendar ticks that must not be skipped, so
> timestream cannot advance more than 9 ticks at a time."*

Y, sobre lo **no** ajustado:

> *"Army movement across the world map (including raids sent out from the fort)
> [moves] at the same (real-time) rate regardless of changes that timestream is
> making to the calendar."*

**Consecuencia para P1:** el estado del mundo **no es una función del tiempo**.
`timestream` puede comprimir 9 ticks de calendario en un frame, y el movimiento
militar puede avanzar a ritmo real. **No existe "un instante" globalmente
---

## 4. Investigación DFHack

DFHack está instalado en `C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack`
(`53.16-r2`). Esta sección se apoya en **su propia documentación y código
fuente**, no en Summersday ni en documentación de terceros.

### 4.1 Identidad de mundo y de sitio

| Mecanismo | API | Qué da | Persistente |
| --- | --- | --- | --- |
| Carpeta del save | `dfhack.world.ReadWorldFolder()` | *"the name of the directory/folder the current saved game is under"* | **Sí** — es una carpeta en disco |
| Carpeta activa | `world.cur_savegame.save_dir` | Carpeta del save en curso | **Sí** |
| Nombre del mundo | `world.world_data.name` | Nombre traducido del mundo | **Sí** (está en el save) |
| Sitio actual | `dfhack.world.getCurrentSite()` | `df.world_site` o `nil` | Sí |
| Modo de juego | `dfhack.world.isFortressMode()` | ¿Fortaleza / Aventura / Arena / Legends? | Sí |
| Estado cargado | `dfhack.isWorldLoaded()` / `isMapLoaded()` | Booleano de disponibilidad | No (es runtime) |

Fuente: `Lua API.txt:2191-2211`, `Lua API.txt:1000-1006`.

**Este es el hallazgo decisivo de la investigación.** La identidad de mundo
**existe y es accesible** (`save_dir` / `ReadWorldFolder`), y DFHack la usa en su
propio exportador para nombrar el fichero de salida:

```lua
-- exportlegends.lua:130
local filename = world.cur_savegame.save_dir.."-"..get_world_date_str().."-legends_plus.xml"
```

Y el nombre del mundo también se escribe:

```lua
-- exportlegends.lua:139
file:write("<name>"..escape_xml(df2utf(translateName(world.world_data.name))).."</name>\n")
```

**Pero DF-Chronicles no captura ninguno de los dos.** El pipeline llama a
`exportlegends.lua`, lee el fichero, lo fusiona, y **descarta el nombre del mundo
y la carpeta del save**. La identidad estaba disponible y se perdió en el camino.

> Verificado: `00_SOURCE/tools/*.py` no contiene ninguna referencia a `save_dir`,
> `cur_year`, `world_date` ni nombre de mundo.

### 4.2 Reloj y cambio de estado

| Mecanismo | Disponible | Persistente | Monótono | Identifica estado | Garantía |
| --- | --- | --- | --- | --- | --- |
| `ReadCurrentYear()` | Sí | Sí | Sí | **Muy graso** (año) | Solo el año |
| `ReadCurrentTick()` = `frame_counter` | Sí | Sí | **NO** — se reinicia cada año | **Muy fino, pero no único** | *"since the start of the current game year"* |
| `ReadCurrentMonth()` / `ReadCurrentDay()` | Sí | Sí | Sí | Grano de día | grano día |
| `eventful` (eventos de objeto) | Sí | No | No | **NO** | Notifican cambios de *objeto*, no de mundo |
| `dfhack.onStateChange` | Sí | No | No | **NO** | `SC_WORLD_LOADED`, `SC_WORLD_UNLOADED`, `SC_MAP_LOADED`, `SC_MAP_UNLOADED`, `SC_VIEWSCREEN_CHANGED`, `SC_CORE_INITIALIZED`. **Transiciones, no estados** |
| `dfhack.getTickCount()` | Sí | No | Sí (ms) | **NO** | *"the tick count in ms, exactly as DF ui uses"* — reloj de **render**, se reinicia con el proceso |
| `dfhack.persistent.getUnsavedSeconds()` | Sí | — | No | **NO** | Segundos desde el último guardado |
| `script.sleep` | Sí | No | — | **NO** | **Cede el control: el mundo avanza** |

### 4.3 `dfhack.persistent` — persistencia dentro del save

Mecanismo más importante de DFHack para P1:

```lua
dfhack.persistent.saveWorldData(key, data)  -- asociado al mundo global
dfhack.persistent.saveSiteData(key, data)   -- asociado al sitio (fortaleza)
dfhack.persistent.getSiteData(key, default)
```

Características documentadas (`Lua API.txt:735-782`):

- Se escribe **en el directorio del savegame**: *"It is all written to a json file
  in the game save directory when the game is saved."*
- **"The data is kept in memory, so no I/O occurs when getting or saving keys."**
  → los datos solo llegan al disco **al guardar**.
- Sobre sitios: *"The data will still be associated with a fort if the fort is
  retired and then later unretired."*

**Implicaciones para P1:**

1. Un contador almacenado con `saveWorldData` **sobrevive a cerrar y reabrir DF**
   porque viaja dentro del save.
2. Ese contador **se resetea** si el jugador carga un save antiguo → **esto es
   exactamente el contador de linaje que P1 necesita**, no un tick.
3. **NO sobrevive a que el mundo se destruya** (se va con el savegame). Correcto
   para identidad de mundo, incorrecto como identidad permanente.
4. **Trampa conocida:** DFHack corrigió un bug donde `saveSiteData` fallaba
   *"on newly reclaimed fortresses until the first save"*
   (`changelogs/news.txt:67`). Un contador que solo se materializa en el primer
   guardado puede **no existir** al observar un mundo recién creado.

### 4.4 Lo que DFHack **no** ofrece

- **No hay API de "capturar el estado del mundo" ni de "snapshot transaccional".**
- **No hay un identificador de estado nativo, único y monotónico.**
- **No hay hook de "el mundo ha cambiado de forma observable".** `eventful` avisa
---

## 5. El problema del snapshot

### 5.1 Lo que P1 temía, confirmado por el propio código de DFHack

El exportador de DFHack **cede el control a mitad de extracción**:

```lua
-- exportlegends.lua:46-58
local function yield_if_timeout()
    local now_ms = dfhack.getTickCount()
    if now_ms - last_update_ms > YIELD_TIMEOUT_MS then
        script.sleep(1, 'frames')      -- <-- el mundo SIGUE CORRIENDO
        last_update_ms = dfhack.getTickCount()
    end
end
```

`YIELD_TIMEOUT_MS = 10`, es decir, cada 10 ms durante una exportación de
**segundos o minutos**. Con su propio comentario: *"should be frequent enough so
that user can still effectively use the vanilla legends UI to browse while export
is in progress"*.

**Esto es una demostración de que ni siquiera el exportador oficial considera que
su salida sea un estado atómico.** El mundo avanza mientras se exporta. El
`legends.xml` que produce **ya es una fotografía inconsistente**, tomada a lo
largo de un intervalo.

### 5.2 Respuestas a las 5 preguntas del encargo

| # | Pregunta | Respuesta |
| --- | --- | --- |
| 1 | ¿Capturar un estado? | **NO.** No hay mecanismo de captura atómica |
| 2 | ¿Congelarlo? | **Parcial.** `CoreSuspender` / `dfhack.suspend` pausa el núcleo **durante** la lectura. Sí permite congelar **dentro** de DFHack, pero **el sistema actual no lo usa** |
| 3 | ¿Identificarlo? | **NO.** Nada en DF ni en el dataset identifica ese estado |
| 4 | ¿Consultar varios datos contra él? | **NO.** El dataset es estático; el problema no se plantea. En vivo, requeriría suspender |
| 5 | ¿Saber cuándo deja de ser válido? | **NO.** No hay forma de saberlo |

### 5.3 Veredicto sobre el snapshot

> **El sistema no puede capturar, congelar, identificar, ni invalidar un estado
> del mundo. Y la fuente de la que bebe —`exportlegends.lua`— tampoco lo hace,
> por diseño explícito de rendimiento.**

Cualquier afirmación de que las 55 pruebas de integración o las 1176 de
regresión dicen algo sobre esto sería falsa: **ninguna toca un mundo vivo.**

---

## 6. Consistencia entre evidencias

### 6.1 Lo que hace el sistema hoy

```python
# contrato_ia.py:145-157
def evidencia_es_actual(ev, version_actual):
    if version_actual is None:
        return False
    return version_de_evidencia(ev) == version_actual
```

Regla: **fail-closed**. Solo es actual la evidencia que declara versión **y**
coincide. Sin versión (`UNKNOWN`) → no es actual. Sin versión actual → no es
actual.

**Esta regla es correcta y está bien implementada.** P1 no la objeta. Lo que P1
objeta es que **la comparación es entre hashes de contenido**, así que la
pregunta que responde es *"¿el contenido del dataset sigue siendo el mismo?"*, no
*"¿esta evidencia refleja el mundo actual?"*.

### 6.2 El caso A(X), B(X), C(Y)

| Decisión | Regla | Fundamento |
| --- | --- | --- |
| ¿Combinar A+B? | **Sí** | Misma versión declarada |
| ¿Combinar C con ellas? | **No**, por la regla actual | Versión distinta |
| ¿Rechazar? | **Sí**, fail-closed | Conserva la postura existente |
| ¿Marcar stale? | **Sí, y solo eso** | `stale` ≠ «incorrecto»: significa «posiblemente desfasado» |
| ¿Crear snapshot nuevo? | **Solo tras investigación** | §13, §12: no se ha demostrado que sea posible |
| ¿Reconsultar? | **Recomendado** | Único camino hoy con garantía real |

### 6.3 Matiz que el contrato actual **no** puede expresar

---

## 7. Datos obsoletos

### 7.1 Definiciones (conceptuales, **no implementadas**)

| Estado | Definición | ¿Se puede demostrar hoy? |
| --- | --- | --- |
| `fresh` | Evidencia cuyo `state_version` coincide con el actual y el dataset no ha cambiado | **Sí** — respecto al dataset |
| `stale` | `state_version` distinta de la actual; el mundo pudo cambiar | **Sí** — respecto al dataset |
| `unknown` | `state_version` ausente o `UNKNOWN` | **Sí** — ya implementado (`SIN_VERSION`) |
| `inconsistent` | Evidencias del mismo conjunto con versiones distintas entre sí | **Sí** — ya implementado |
| `unavailable` | No hay estado actual con el que comparar | **Sí** — `version_actual is None` |

### 7.2 De válida a potencialmente obsoleta

| Transición | ¿Demostrable? | Con qué |
| --- | --- | --- |
| válida → **potencialmente obsoleta** | **Sí** | Cambió `dataset_id` (cambió el contenido) |
| válida → **obsoleta de forma demostrable** | **NO** | El mundo puede haber cambiado sin cambiar el contenido extraído (§2.3-D) |
| válida → obsoleta | **NO DEMOSTRABLE** | Requiere un reloj de mundo que no tenemos |

**Consecuencia:** el sistema **no puede demostrar la obsolescencia**. Solo puede
detectar cambios de contenido. La distinción entre "el mundo cambió" y "el
contenido cambió" es exactamente lo que P1 no puede resolver.

---

## 8. Guardar y cargar

Las 7 preguntas del encargo, respondidas con honestidad:

| # | Pregunta | Respuesta | Base |
| --- | --- | --- | --- |
| 1 | ¿El mundo conserva identidad? | **Sí, conceptualmente** — la carpeta del save y `world_data.name` persisten | DFHack `Lua API.txt:2191` |
| 2 | ¿El estado conserva identidad? | **Hoy, no** — nada en el dataset lo registra | §2.4 |
| 3 | ¿El tick continúa? | **NO CONFIRMADO.** Si el reloj se restaura con el save, reinicia al valor guardado | **NO DEMOSTRADO** |
| 4 | ¿Puede cambiar? | **NO DEMOSTRADO** | |
| 5 | ¿Puede volver a un estado anterior? | **Sí** — cargar un save es exactamente eso | Mecánica del juego |
| 6 | ¿Dos saves del mismo mundo pueden divergir? | **Sí** — es el caso de la §9 | Mecánica del juego |
| 7 | ¿Cómo representar la divergencia? | **Ver §12: `lineage` dentro del save** | Diseño |

### 8.1 El caso que invalida un tick ingenuo

```text
save A, tick 1000
juego hasta tick 1100
cargo save A  ->  tick 1000
```

El número vuelve a ser 1000 en **dos momentos distintos del mundo**, con **dos
historias distintas detrás**. Un contador puro es **ambiguo**: se repite. Si el
sistema lo tratara como versión, dos mundos distintos podrían recibir el mismo
número.

**DFHack resuelve esto en su propio código** combinando año y tick:

```lua
-- emigration.lua:129
state.last_cycle_tick = dfhack.world.ReadCurrentTick() + TICKS_PER_YEAR * ReadCurrentYear()
```

`frame_counter` reinicia cada año, así que **`(año, tick)` es la granularidad
mínima real** de DFHack, y sigue sin ser global: **dos mundos distintos empiezan
en el año 1**.

Y un segundo indicio, más fuerte: la caché interna de DFHack **no confía en
año+tick**:

```lua
-- notifications.lua:397-403
if force ~= true
   and dfhack.world.ReadCurrentYear()  == self.ATTRS.cached_on_year
   and dfhack.world.ReadCurrentTick()   < recheck_after
   and self.ATTRS.nemesis_all_length   == #df.global.world.nemesis.all
   and self.ATTRS.units_active_length  == #df.global.world.units.active
then return end
```

DFHack, cuyo sustento depende de invalidar cachés correctamente, **añade
---

## 9. Ramificación del mundo

```text
mundo W
├── estado A  (save)
│   ├── rama B
│   └── rama C
└── estado D
```

### 9.1 ¿Puede `dataset_id` representar ramificación?

**Parcialmente, y de forma no fiable.** El experimento B mostró que ramas con
contenido distinto producen ids distintos. Pero:

- Dos ramas que **difieren y luego convergen al mismo contenido** son
  **indistinguibles**. Un hash no guarda linaje.
- Un hash **no tiene padre**: no puede expresar "B deriva de A".
- **No hay linaje recuperable** del artefacto actual.

### 9.2 Lo que sí puede

`dfhack.persistent.saveWorldData` almacena datos **dentro del savegame**
(`Lua API.txt:770-782`). Eso significa que un contador de linaje **sobrevive a
guardar/cargar** y **se transporta con la rama**. Si el jugador carga un save
antiguo, el contador **regresa al valor que tenía en ese save** — que es
exactamente la semántica de "rama", y no la de "tiempo".

> **Ésta es la pieza que hace resoluble la ramificación**, y ya está disponible en
> DFHack sin escribir un mod. Es un contador **transportado con la rama**, no un
> reloj. Un reloj no puede expresar ramificación; un contador guardado en el save
> sí.

**NO DEMOSTRADO** que sobreviva a todas las operaciones (§3.3).

---

## 10. Reinicio del juego

| Escenario | ¿Distinguible hoy? | ¿Distinguible con el modelo propuesto? |
| --- | --- | --- |
| Cerrar DF → abrir → cargar mundo | **NO.** Mismo `dataset_id` | **Sí**, vía `world_folder` |
| Cerrar DF → abrir → **crear otro mundo** | **NO.** Si el contenido coincide, mismo `dataset_id` (experimento C) | **Sí**: otra carpeta de save + otro linaje |
| Cargar un save de **otro mundo** | **NO** | **Sí** |

### 10.1 ¿Qué impide que dos mundos distintos reciban la misma `state_version`?

**Respuesta directa: nada. Hoy no hay nada que lo impida.**

`state_version` es un hash de contenido. El espacio de valores está bien
distribuido (SHA-256/64 bits: probabilidad de colisión de cumpleaños ≈ 2³²), así
que **las colisiones criptográficas no son el riesgo**. El riesgo es **semántico**:

> Dos mundos con el mismo contenido extraído reciben **exactamente** la misma
> `state_version`. No es improbable. Es **inevitable**, y está demostrado en el
> experimento C.

Y hay un segundo vector, peor: **`dataset_id` no incluye ninguna identidad de
mundo**, así que un mundo nuevo con contenido parecido es indistinguible.

---

## 11. Identidad del mundo vs identidad del estado

Esto queda **absolutamente claro**, y es el hallazgo estructural de P1:

```text
state_version = v1-04170363943d4ba1
```

**No significa "estado 04170363943d4ba1 del mundo X".** Significa:

> "El contenido extraído cuyo inventario de hashes es 04170363943d4ba1."

De ahí:

| Pregunta | ¿La puede responder `state_version`? |
| --- | --- |
| ¿De qué **mundo** es este dato? | **NO** |
| ¿De qué **estado** de ese mundo es este dato? | **NO** — es un estado *del dataset* |
---

## 12. Modelos de datos considerados

Ninguno implementado. Todos evaluados contra la evidencia recogida.

### 12.1 Propuestas

| Propiedad | **A. Solo contenido (actual)** | **B. Tick de DF** | **C. Tick + año + mundo** | **D. Content + mundo + linaje** |
| --- | --- | --- | --- | --- |
| Identidad mundial | ❌ ninguna | ❌ ninguna | ⚠️ `save_dir` | ✅ `save_dir` + `name` |
| Identidad de estado | ⚠️ contenido | ⚠️ intra-año | ✅ año+tick | ✅ hash de contenido |
| Save/load | ⚠️ reinicia hash | ❌ **ambiguo** | ⚠️ reinicia año+tick | ✅ linaje persiste en el save |
| Branching | ❌ sin linaje | ❌ imposible | ❌ imposible | ✅ contador en el save |
| Monotonicidad | ❌ ninguna | ❌ reinicia cada año | ⚠️ por año | ⚠️ por contenido |
| Persistencia | ✅ | ⚠️ en el save | ⚠️ en el save | ✅ |
| Reproducibilidad | ✅ total | ✅ | ✅ | ✅ |
| Coste | ✅ cero | ✅ cero | ⚠️ requiere suspender | ⚠️ requiere suspender |
| Complejidad | ✅ trivial | ✅ trivial | ⚠️ media | ⚠️ media |
| Riesgos | 🔴 colisión semántica | 🔴 repetición, ambigüedad | 🟠 granularidad gruesa | 🟠 sin garantía atómica |
| Estado | **EN PRODUCCIÓN** | ❌ descartado | ❌ descartado | ⚠️ candidato |

### 12.2 Análisis de las soluciones "obvias" (Parte 16)

**Usar el timestamp.**
`dataset_version.json` ya tiene `actualizada`, `merge.generado` y
`version_anterior`. Son relojes de la **máquina de extracción**, no del mundo.
*Determinista:* no. *Identifica un estado:* no — dos extracciones del mismo estado
difieren en nanosegundos. Además rompe la reproducibilidad del hash.
**Rechazado.**

**Usar el tick.**
Rechazado por tres motivos independientes, todos con evidencia:
1. `frame_counter` **se reinicia cada año** (`Lua API.txt:2173`; `History.txt`
   documenta explícitamente el bug *"frame_counter getting reset properly"*).
2. **Empieza en 0/año 1** en cada mundo → dos mundos colisionan desde el tick 0.
3. **Cargar un save lo hace retroceder** (§8.1) → repetición de valores.
Y `timestream` demuestra que ni siquiera es tiempo (§3.4).
**Rechazado.**

**Usar el hash del dataset.**
Es lo que ya hay. Determinista, persistente, reproducible, coste cero. Pero:
identifica **contenido**, no **estado**, y no lleva identidad de mundo
(experimentos A y C). **Insuficiente por sí solo**, y esto está demostrado, no
supuesto.

**Usar `dataset_id` para resolver P1.**
La misión lo prohíbe explícitamente (reglas 14 y 15). Y la investigación
confirma que la prohibición es correcta: **no funciona**. No lo vamos a cambiar,
ni siquiera ampliar.

| ¿Este dato es del mundo que está cargado? | **NO** — no hay forma de preguntarlo |
| ¿Dos datos vienen del mismo estado del mundo? | **NO** — solo del mismo dataset |
| ¿Dos datos vienen de estados distintos del mundo? | **Indeterminado** — a veces sí (cambió el contenido), a veces no |

**P1 tiene que ser explícito: el sistema actual no puede responder a la pregunta
que P1 le hace.** Y no por un fallo de implementación, sino porque el dato nunca
se recogió (§2.4).

### 12.3 Recomendación

> **No hay evidencia suficiente para elegir un modelo de estado del mundo.**
> **P1 sigue abierta.**

Lo que sí hay evidencia suficiente para afirmar, con máxima claridad:

1. **El modelo A (actual) está mal nombrado, no necesariamente mal construido.**
   Es un buen identificador de **dataset**. El problema es que se llama
   `state_version` y eso promete una garantía que no da.
2. **La identidad de mundo se puede añadir de forma barata, fiable y verificable.**
   `save_dir` + `world_data.name` ya los produce `exportlegends.lua` en cada
   ejecución; el pipeline simplemente los descarta. Esto es un **defecto de
   extracción**, no un problema de modelado.
3. **La ramificación es representable** mediante un contador en
   `dfhack.persistent`, porque viaja con el savegame.
4. **El snapshot atómico es el hueco irreducible** y no se ha demostrado
   resoluble más allá de suspender el core.

Si la decisión tuviera que tomarse hoy, la dirección correcta es
**D + identidad de mundo de A**, es decir:

```text
WorldIdentity    = save_dir + world_data.name          [FÁCIL, hoy]
StateIdentity    = hash de contenido (dataset_id)     [YA EXISTE]
Lineage          = contador persistente en el save    [VIABLE, NO DEMOSTRADO]
ObservationMeta  = observed_at + suspended            [VIABLE]
```

**Pero el último renglón no debe adoptarse hasta que DF esté disponible para
demostrarlo.** Adoptarlo antes sería exactamente la "falsa sensación de
consistencia temporal" que la misión prohíbe (regla 16).

---

## 13. Snapshot: qué significa y qué garantiza

| Garantía | ¿Disponible? | Evidencia |
| --- | --- | --- |
| Que las 10 consultas de un lote usen un estado | **NO** | `exportlegends.lua` cede el control durante la extracción (§5.1) |
| Que el mundo estaba pausado al observar | **NO** | Nadie lo pausa; no hay registro |
| Que dos consultas consecutivas leen lo mismo | **NO** | El mundo avanza entre llamadas |
| Que se puede invalidar un snapshot | **NO** | Sin identidad de estado |
| Que el extract es atómico | **NO** | El extract cede el control por diseño |

**Conclusión:** hoy, "snapshot" **no significa nada** en este sistema. El término
debe evitarse en el contrato hasta que exista una implementación real.

---

## 14. Obsolescencia: diseño (no implementado)

| Situación | Detección | Acción propuesta |
| --- | --- | --- |
| `state_version` ≠ actual | Inmediata | `stale` |
| Sin `state_version` | Inmediata | `unknown` |
| Sin estado actual | Inmediata | `unavailable` |
| Mundo avanzando, contenido igual | **INDETECTABLE** | `stale` por timeout (`observed_at`) — **heurística, no garantía** |
| Ramificación (mismo mundo, linaje distinto) | **NO DETECTABLE hoy** | Requiere `lineage` |

**Nota sobre la última fila:** es la razón por la que P1 no se puede cerrar. El
sistema no puede detectar que volvió a un save antiguo, porque no tiene ningún
registro de a dónde volvió.

---

## 15. Save/load y ramificación

Diseño propuesto, **no implementado**:

```text
---

## 16. Impacto futuro

| Capa | Cambio necesario | Bloqueado por |
| --- | --- | --- |
| **Extracción** | **Capturar `save_dir` y `world_data.name`** al ejecutar `exportlegends.lua` | Nada — **es el cambio más barato y de mayor valor** |
| **Extracción** | Capturar fecha de mundo (`cur_year/month/day`) y decidir si va al dataset | El año es granular, no identifica estado |
| **Extracción** | Marcar si la extracción fue atómica o `best_effort` | Requiere suspender el core |
| **Núcleo** | Emitir `world_identity` junto al dataset | Depende de extracción |
| **`servicio_consulta`** | **Propietario del contrato de estado.** Publicar `world_identity`, propagar `lineage` y `consistency` | **Prohibido tocarlo en esta misión** |
| **API** | Exponer los nuevos ejes por separado, sin romper `dataset_id` | — |
| **Web** | Mostrar mundo y antigüedad de la evidencia | — |
| **Futura IA** | **Recibir los ejes y NO decidir igualdad** | La IA no arbitra consistencia (§18) |

### 16.1 Cambio mínimo de mayor impacto

```diff
-  state_version: "v1-04170363943d4ba1"     # ¿estado? no se sabe
+  dataset_id:    "v1-04170363943d4ba1"     # dataset, sin ambigüedad
+  world_identity: "region1"                 # identifica al mundo
```

Este cambio **no requiere modelo de estado**, **no requiere snapshot**, y
**resuelve la mitad de la pregunta de P1** (¿de qué mundo?).

---

## 17. Pruebas necesarias cuando P1 se implemente

**Diseñadas, no implementadas.** Ninguna existe hoy.

### 17.1 Identidad

| # | Prueba | Objetivo |
| --- | --- | --- |
| 1 | Dos mundos con contenido idéntico | `world_identity` **distinta**, `dataset_id` puede coincidir |
| 2 | Dos mundos, mismo tick/año | No se confunden (**falla hoy**: no hay identidad de mundo) |
| 3 | Mismo mundo, contenido distinto | `dataset_id` distinto, `world_identity` igual |

### 17.2 Evolución

| # | Prueba | Objetivo |
| --- | --- | --- |
| 4 | `state 1 < state 2 < state 3` | Solo si el modelo promete orden. **Con hash de contenido NO se promete** |
| 5 | Volver al contenido anterior | El sistema **no** puede distinguir → documentar la limitación |

### 17.3 Save/load

| # | Prueba | Objetivo |
| --- | --- | --- |
| 6 | A → B → guardar → cerrar → abrir → cargar | `world_identity` estable |
| 7 | Tras cargar, el `lineage` | Coherente con la rama restaurada |

### 17.4 Branching

| # | Prueba | Objetivo |
| --- | --- | --- |
| 8 | A → B y A → C | `lineage` diverge |
| 9 | Cargar A tras llegar a C | Se detecta la regresión de rama |

### 17.5 Repetición

| # | Prueba | Objetivo |
| --- | --- | --- |
| 10 | El mismo `dataset_id` dos veces | Documentado: puede ocurrir legítimamente |
| 11 | El mismo `lineage` en dos mundos | **Imposible**: `world_identity` lo descarta |

### 17.6 Coherencia

| # | Prueba | Objetivo |
| --- | --- | --- |
| 12 | 10 consultas contra un snapshot suspendido | Todas con la misma identidad |
| 13 | 10 consultas con el mundo corriendo | Se marca `best_effort`, **nunca `atomic`** |

### 17.7 Obsolescencia

| # | Prueba | Objetivo |
---

## 18. Relación con la IA futura

Sin implementar IA. Solo el contrato que necesitará.

### 18.1 Lo que la IA **no** debe decidir

> **La IA NO debe decidir si dos estados son equivalentes.** Esa decisión es de
> infraestructura determinista.

Si la IA puede "razonar" que `v1-041…` y `v1-041…` son equivalentes, el sistema
ha fallado en dar una igualdad comparable con `==`. La coherencia debe ser **una
comparación de cadenas en código determinista**, no un juicio.

### 18.2 Lo que el versionado protegería

```text
Consulta 1  state = X
Consulta 2  state = X     -> coherente (igualdad determinista)
Consulta 3  state = Y     -> no combinar como una sola fotografía
```

Y el caso que la misión subrayaba:

```text
Consulta 1  state = X
el mundo cambia
la IA recibe la respuesta
```

Hoy, la IA **no puede determinar** si la evidencia sigue siendo utilizable,
porque "el mundo cambia" **no cambia `dataset_id`**. Con `world_identity` +
`lineage` + `observed_at`, al menos podría saber **qué mundo** y **qué rama**, y
que la evidencia es *posiblemente* antigua — sin afirmar que lo es.

### 18.3 Principio rector

> **Un `state_version` que la IA debe interpretar es un contrato mal diseñado.**
> Debe ser una cadena que se compara, no un concepto que se razona.

---

## 19. Decisiones pendientes

Ninguna de estas puede cerrarse sin acceso a un Dwarf Fortress en ejecución.

| # | Decisión | Por qué está pendiente |
| --- | --- | --- |
| 1 | ¿Adoptar `WorldIdentity` con `save_dir` + `name`? | **Es la única con evidencia suficiente.** Requiere decisión de contrato |
| 2 | ¿Renombrar `state_version` a algo honesto? | Afecta a contratos; decisión de arquitectura |
| 3 | ¿Adoptar `lineage` persistente? | Viable en diseño, **NO DEMOSTRADO** en ejecución |
| 4 | ¿Adoptar suspensión del core para snapshots? | **NO DEMOSTRADO**: falta medir el impacto |
| 5 | ¿Definir `consistency: atomic \| best_effort`? | Depende de #4 |
| 6 | ¿Qué granularidad temporal se expone? | El año es demasiado grueso; el tick no es único |
| 7 | ¿Cómo se comporta `exportlegends` si cede el control? | Afecta a la atomicidad de §5 |

---

## 20. Veredicto

### 20.1 Lo que está **DEMOSTRADO**

1. `state_version` **es** `dataset_id`; no son dos ejes.
2. `dataset_id` = SHA-256 del inventario de 15 secciones de contenido.
3. Dos extracciones separadas por 82 s producen el **mismo** `dataset_id`.
4. Dos mundos con el mismo contenido reciben el **mismo** `dataset_id`.
5. El XML de 344 tags **no contiene** nombre de mundo, `world_id`, `tick` ni seed.
6. DF **sí** tiene reloj (`cur_year`, `frame_counter`, mes, día) y DF lo expone.
7. `frame_counter` **se reinicia cada año** y DFHack lo compensa con `+TICKS_PER_YEAR*año`.
8. La caché de DFHack **añade longitudes de contenedores** a año+tick.
9. `exportlegends.lua` **cede el control durante la extracción**.
10. `timestream` prueba que el estado del mundo **no es función del tiempo**.
11. `save_dir` y `world_data.name` **existen** y el pipeline **los descarta**.
12. `dfhack.persistent` guarda datos **dentro del savegame**, y solo los escribe **al guardar**.

### 20.2 Lo que está **NO DEMOSTRADO**

1. Que DF conserve/reinicie el tick al guardar y cargar.
2. Que `lineage` sobreviva a todas las operaciones de §3.3.
3. Que suspender el core produzca un snapshot atómico aceptable.
4. Que exista algún contador de DF que sobreviva al cambio de año sin ambiguidad.

### 20.3 Conclusión

> **P1 sigue ABIERTA.**
>
> **Todavía no existe una identificación suficientemente fiable del estado de un
---

## Anexo A — Comprobación de no-modificación

Experimentos: 5 scripts temporales (`_p1exp.py`, `_p1xml.py`, `_p1tags.py`,
`_p1w.py`, `_p1coll.py`) + sus `.out`/`.err`. **Todos eliminados.** Todos fueron
de **solo lectura**.

```
dfchron\servicio_consulta.py               0A5B6B1C3244E619  (baseline conocida: OK)
dfchron\adaptador_consulta.py              C456256EC1C1D731
dfchron\api.py                             0426F63A632FD243
dfchron\web\app.js                         297087BC23678580
dfchron\contrato_ia.py                     EB4A4156CBFAF764
dfchron\ia_conocimiento.py                 7EBCBBC2C2B4F044
00_SOURCE\dataset_version.json             3C81E92EF2883ED8
```

- `servicio_consulta.py` = `0A5B6B1C3244E619`, idéntico al hash registrado al
  cierre de la misión anterior. **Sin cambios.**
- `dataset_id` sigue siendo `v1-04170363943d4ba1`. Dataset **no tocado**.
- `08_DATABASE/AI_PRE_LLM_CONTRACT.md` **no modificado**.
- Cero dependencias añadidas. Cero IA. Cero SDK de IA.
- Sin `git` en el workspace: la verificación es por **hash de contenido**.

---

## Anexo B — Fuentes de DFHack utilizadas

Todas locales: `C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\hack\`

| Fuente | Qué aportó |
| --- | --- |
| `docs/docs/dev/Lua API.txt:2167-2181` | `ReadCurrentYear/Tick/Month/Day`; *"since the start of the current game year"* |
| `docs/docs/dev/Lua API.txt:2191-2211` | `ReadWorldFolder()`, `getCurrentSite()`, `isFortressMode()` |
| `docs/docs/dev/Lua API.txt:1000-1006` | `isWorldLoaded()`, `isMapLoaded()` |
| `docs/docs/dev/Lua API.txt:735-782` | `dfhack.persistent`; *"written to a json file in the game save directory when the game is saved"* |
| `docs/docs/dev/Lua API.txt:3398-3402` | Códigos `SC_*` de `onStateChange` |
| `docs/docs/about/History.txt:5921` | *"Events from EventManager: deals with frame_counter getting reset properly now"* |
| `scripts/exportlegends.lua:46-58` | `yield_if_timeout()` → `script.sleep` durante la exportación |
| `scripts/exportlegends.lua:130,139` | `save_dir` y `world_data.name` escritos al XML |
| `scripts/emigration.lua:28-29,129` | `TICKS_PER_MONTH=33600`, `TICKS_PER_YEAR`, combinación tick+año |
| `scripts/internal/notify/notifications.lua:397-406` | Caché con año+tick **+ longitudes de contenedores** |
| `docs/docs/tools/timestream.html` | Desacople tiempo/estado; 9 ticks de golpe |
| `docs/docs/changelogs/news.txt:67` | Bug de `saveSiteData` en fortalezas nuevas |

---

## Anexo C — Configuración de la auditoría

- **DF instalado:** ❌ no (verificado en rutas estándar y workspace).
- **DF en workspace:** ❌ no.
- **DFHack:** ✅ instalado, `53.16-r2`, desacoplado del juego.
- **Ejecuciones de DF realizadas:** 0 (fuera del alcance de la misión).
- **Experimentos:** todos de **solo lectura** sobre XML y metadatos existentes.

> mundo vivo** en DF-Chronicles.
>
> El `state_version` actual **no es un estado del mundo**: es un hash de
> contenido con un nombre que promete más de lo que garantiza. Su uso actual es
> **correcto** para lo que hace —comparar si dos evidencias vienen del mismo
> dataset— y **engañoso** por lo que sugiere.
>
> **No se ha implementado la solución.** No se ha modificado el núcleo, ni
> `servicio_consulta.py`, ni ningún contrato congelado. No se ha introducido IA.
> Todos los experimentos temporales han sido eliminados.

### 20.4 La única acción de alto valor y bajo riesgo

**Capturar `world_folder` y `world_name` en la extracción.**

DFHack ya los produce. `exportlegends.lua` ya los escribe. El pipeline los
descarta. Sin esto, P1 **no puede empezar**, porque la identidad de mundo es la
base de todo lo demás.

Y no requiere elegir modelo, no requiere snapshot, no requiere `lineage`, y no
rompe nada.

| --- | --- | --- |
| 14 | Cambiar el mundo tras capturar evidencia | `stale` |
| 15 | Mundo avanza sin cambiar el contenido | **La obsolescencia es invisible** → documentar como limitación conocida |

### 17.8 Reinicio

| # | Prueba | Objetivo |
| --- | --- | --- |
| 16 | Cerrar y abrir DF, cargar el mismo mundo | Misma identidad |
| 17 | Cerrar y abrir DF, crear otro mundo | **Identidad distinta** |

### 17.9 Corrupción

| # | Prueba | Objetivo |
| --- | --- | --- |
| 18 | Alterar `world_identity` | Se rechaza la evidencia |
| 19 | Alterar `state_version` | Se rechaza la evidencia |
| 20 | Evidencia sin versión | `unknown`, fail-closed (**ya implementado**) |

WorldIdentity
  world_folder   = ReadWorldFolder()   # persistente, barato, ya disponible
  world_name     = world_data.name     # legible, persistente

Lineage
  branch_epoch   = contador en saveWorldData   # viaja con el save
                 # cargar un save antiguo => retrocede con la rama (correcto)

StateIdentity
  content_hash   = dataset_id          # ya existe, no se renombra aún

ObservationMeta
  observed_at
  suspended      # ¿se leyó con el core pausado?
  consistency    # atomic | best_effort
```

**El punto clave es `branch_epoch`.** Semántica:

- Es un contador **transportado con la rama**, no un reloj.
- Cargar un save antiguo **retrocede** el contador → detecta ramificación.
- Crear un mundo nuevo → contador nuevo en `0`.
- **NO es global**: dos mundos tienen contadores independientes. Por eso
  `world_folder` es obligatorio y no opcional.

longitudes de contenedores** a la identidad temporal. `(año, tick)` no basta.

**Esta es la refutación más fuerte que P1 puede aportar**: el *framework* de
referencia, escrito por quien mejor conoce el motor, **no considera que un reloj
identifique un estado**.

Supón A(X) y B(X) donde X es `v1-04170363943d4ba1`. El sistema dice «coherentes».
Correcto.

Pero supón que entre A y B el mundo avanzó 5 000 ticks. El contenido extraído no
cambió. `dataset_id` = X. El sistema dice «coherentes». **Y tiene razón:**
ambas vienen del mismo dataset en disco. Son coherentes *con respecto al dataset*.

La trampa no está en la regla de consistencia. Está en la **etiqueta**: si
llamamos «estado del mundo» a X, estaríamos afirmando que el mundo no cambió
durante 5 000 ticks. **No lo sabemos.** No podemos saberlo.

> **Este es el corazón de P1: la regla es correcta pero la semántica del nombre
> es incorrecta. Y un nombre incorrecto en un contrato se paga cuando alguien
> construye encima.**

  de eventos de objeto; `onStateChange` avisa de transiciones. Ninguno equivale a
  "el estado del mundo es ahora X".
- **No hay garantía de que dos llamadas a dos funciones distintas lean el mismo
  estado**, salvo suspender el core.

definido.** Cualquier modelo que intente capturar un estado por "posición en el
tiempo" está mal fundado desde la raíz.


**`state_version` NO es una versión del mundo. Es un alias de `dataset_id`.**
Registramos esto porque el encargo advertía: *"No asumir que algo es una versión
simplemente porque se llama version"*. Aquí se cumple literalmente.

identificador **solo depende del contenido**, y que por construcción no puede
distinguir "el mundo no cambió" de "nunca miramos el mundo".

**Experimento B — sensibilidad real del hash.**
Cambiar `historical_events.lineas` en +1 produce `v1-7605579fd5d90e02`; en −1,
`v1-1dc1c7fe8424d7ba`. El hash es determinista y sensible. **Funciona bien como
identidad de contenido.** Ese es exactamente su límite.

**Experimento C — dos mundos distintos, una identidad.**
Dos mundos con el mismo contenido extraído reciben `dataset_id` idéntico
(`v1-04170363943d4ba1`). Esto **sí** es una colisión semántica: el identificador
no incorpora ninguna identidad de mundo.

**Experimento D — el mundo avanza y el identificador no se mueve.**
Si el mundo avanza y ninguna de las 15 secciones cambia, `dataset_id` no cambia.
El mundo ha cambiado (unidades se mueven, jobs se crean) pero **la obsolescencia es
invisible**.
