# P1.4 — INFORME FINAL

> ## Veredicto: **P1.4 CERRADA — OBSERVADOR DEMOSTRADO**
>
> Extracción real, no invasiva y verificada contra el juego en ejecución.
> Con 4 deudas técnicas y 4 pruebas pendientes declaradas.

---

## Las 10 respuestas

### 1. ¿Se ha conseguido comunicar con el DFHack del juego que estaba ejecutándose?

**Sí.** Por `hack\dfhack-run.exe`, con Lua en línea:

```
dfhack-run help   -> ayuda real de DFHack
dfhack-run ls     -> lista de comandos
dfhack-run cprobe -> "No unit is selected in the UI."   (habla con el juego)
dfhack-run lua "print('DFHACK_LUA_OK')"  -> DFHACK_LUA_OK
```

Versiones: juego **v0.53.16 win64 STEAM**, DFHack **53.16-r2rc2** (la misma de
P1.3 — sus conclusiones siguen valiendo).

### 2. ¿Se han obtenido datos reales del mundo cargado?

**Sí.** 13 hechos por ejecución, medidos contra el mundo cargado. Partida de
**fortaleza**, **pausada**, **14 ciudadanos** DWARF.

### 3. ¿Cuántos campos se han extraído?

**13**, de los cuales **12** entran en el perímetro imprimible y **1** queda
marcado `NO_VISIBLE`.

| Dato | Valor | Visibilidad |
|---|---|---|
| Nombre del mundo | `Xah Alu` | VISIBLE |
| Año | `10` | VISIBLE |
| Mes | `5` | VISIBLE |
| Día | `5` | VISIBLE |
| Estación | `1` | VISIBLE |
| Clima | `0` | VISIBLE |
| En pausa | `true` | VISIBLE |
| Población | `14` | VISIBLE |
| Profesiones | 13 oficios distintos | VISIBLE |
| Razas | `{DWARF: 14}` | VISIBLE |
| Modo fortaleza | `true` | VISIBLE_CONDITIONAL |
| Carpeta del mundo | `region1` | VISIBLE_CONDITIONAL |
| **Tick del año** | `173026` | **NO_VISIBLE** |

### 4. ¿Cuáles son visibles para el jugador normal?

9 de 13 son **`VISIBLE`** y 2 **`VISIBLE_CONDITIONAL`**.

El **tick del año** es el único `NO_VISIBLE`: el jugador ve una *fecha*, nunca
un contador interno. Queda registrado pero **fuera del perímetro**, y el
validador lo comprueba automáticamente.

### 5. ¿Qué APIs concretas los proporcionan?

| Dato | API |
|---|---|
| Nombre del mundo | `dfhack.translation.translateName(world_data.name)` |
| Año / Mes / Día | `dfhack.world.ReadCurrentYear() / ReadCurrentMonth() / ReadCurrentDay()` |
| Tick | `dfhack.world.ReadCurrentTick()` |
| Clima | `dfhack.world.ReadCurrentWeather()` |
| Pausa | `dfhack.world.ReadPauseState()` |
| Modo | `dfhack.world.isFortressMode()` |
| Carpeta | `dfhack.world.ReadWorldFolder()` |
| Población | `#dfhack.units.getCitizens()` |
| Profesión / Raza | `dfhack.units.getProfessionName() / getRaceName()` |

**Todas de solo lectura.** Las de escritura (`SetPauseState`,
`SetCurrentWeather`) no se han invocado ni una vez.

> Tres APIs que se creían correctas **no lo son** en esta versión:
> `dfhack.world.isWorldLoaded()` no existe (es `dfhack.isWorldLoaded()`),
> `dfhack.TranslateName` no existe (es `dfhack.translation.translateName`) y
> `df2utf` espera cp437, no un `language_name`.

### 6. ¿Qué datos interesantes quedan fuera del perímetro?

- **Tick del año**: `NO_VISIBLE`.
- **Carpeta del mundo**: identificador técnico, no conocimiento del jugador.
- **Sin investigar** (`UNKNOWN`, no descartado): notificaciones, muertes,
  nacimientos, llegadas, combates, salud, heridas, pensamientos, relaciones,
  inventario, animales, visitantes, migrantes.

### 7. ¿Se ha demostrado que la extracción no altera la partida?

**Sí, medido.** 4 ejecuciones en 90 s de reloj real: `game_tick` = **173026 en
todas**. El tiempo de juego no avanzó ni un tick. Y **ningún fichero de la
partida fue escrito** (verificado sobre `save/`).

> Alcance honesto: la partida estaba **pausada**. Con la partida en marcha no
> se ha medido, porque requiere tu autorización.

### 8. ¿Qué frecuencia de actualización es viable?

**No es el problema.** 60 ms por ejecución, de los cuales 53 son el proceso y
solo **~7 ms** el trabajo real. Un sondeo de 1 Hz costaría **<1 % de un
núcleo**. Recomendación: **bajo demanda** primero; **híbrida** a medio plazo.

### 9. ¿Qué problemas quedan abiertos?

| # | Problema |
|---|---|
| 1 | **Falta la tabla CP437→UTF-8**: la mitad de los nombres (7 de 14) no son utilizables |
| 2 | El observador devuelve `exit=0` al abortar: un fallo puede pasar inadvertido |
| 3 | `observation_id` se reinicia si se trunca el fichero |
| 4 | La correspondencia con la interfaz no se ha verificado **visualmente** |

### 10. ¿Cuál es el siguiente paso técnico recomendado?

**Implementar la tabla CP437→UTF-8 completa.** Es el bloqueador más claro y no
necesita autorización. Sin ella, el observador no puede observar lo único que
realmente distingue a Dwarf Fortress: **los nombres**.
---

## Tres hallazgos que la investigación cambió

### 1. `dfhack-run` solo acepta un token entrecomillado

```
dfhack-run "lua print(1)"  -> "not a recognized command"
dfhack-run lua "print(1)"   -> FUNCIONA
```

No está en la documentación. Costó dos intentos fallidos y condicionó la forma
del prototipo.

### 2. Se puede ejecutar Lua **sin escribir nada** en la instalación

```
dfhack-run lua "dofile('C:/ruta/aislada/script.lua')"
```

El script vive en `dfchron/pruebas/p1_4/`, como debe ser. **Cero escrituras en
`hack/scripts/`** y cero contaminación de la instalación.

### 3. `translateName` devuelve **CP437**, no UTF-8

Un ciudadano se escribe `S\x86kzul Tulonroder`: el `\x86` es la **é** en CP437.
**7 de 14 ciudadanos** tienen bytes no-ASCII, así que medio JSONL habría sido
ilegible para un lector UTF-8 estricto.

El prototipo **no escribe bytes rotos ni finge lo contrario**: los marca
`__NO_UTF8_PENDIENTE(cp437):<hex>`, válido y reversible. No se implantó una
tabla parcial, que corromperia en silencio lo que no cubriera.

> Se conserva la evidencia: `P1.4/evidencias/DEFECTO_jsonl_no_valido.txt` es la
> **primera** salida del observador, que no era JSONL válido (22 líneas por
> observación, por `json.encode` con tabuladores). El defecto se detectó al
> validar, se corrigió con `{pretty=false}` y modo binario, y **se conservó**
> el fichero roto.

---

## Artefactos

```
P1.4/00_ENTORNO_REAL.md              entorno verificado, API por introspección
P1.4/01_INVENTARIO_VISIBILIDAD.md    tabla maestra + justificación
P1.4/03_VALIDACION_JUEGO_VIVO.md     no-invasión, repetibilidad, fallos
P1.4/04_RENDIMIENTO.md               mediciones reales
P1.4/06_ARQUITECTURA_FUTURA.md       propuesta (NO implementada)
P1.4/09_LIMITACIONES_Y_DEUDAS.md     lo que no se hizo ni se midió
P1.4/evidencias/DEFECTO_jsonl_no_valido.txt
P1.4/resultados/observaciones.jsonl  65 observaciones reales
```

Scripts aislados (no entran en producción):

```
dfchron/pruebas/p1_4/observador.lua          el observador
dfchron/pruebas/p1_4/sonda_entorno.lua       sondeo del entorno
dfchron/pruebas/p1_4/prueba_codificacion.lua prueba del guardián CP437
dfchron/pruebas/p1_4/validar_jsonl.py        validador estricto
```

### Cómo ejecutarlo

```powershell
$d = '...\Dwarf Fortress\hack\dfhack-run.exe'
$s = 'C:/.../dfchron/pruebas/p1_4/observador.lua'
$o = 'C:/.../P1.4/resultados/observaciones.jsonl'
& $d lua "_G.DFCHRON_OUT='$o'; dofile('$s')"
```

---

## Integridad

| Recurso | Estado |
|---|---|
| `servicio_consulta.py` | **intacto** `0a5b6b1c…` |
| `adaptador_consulta.py` | **intacto** `c456256e…` |
| `api.py` | **intacto** `0426f63a…` |
| `AI_PRE_LLM_CONTRACT.md` | **intacto** `5d2c3d00…` |
| `legends.xml` | **intacto** `77db4739…` |
| Ficheros de la partida | **ninguno escrito** |
| Instalación de DFHack | **ninguna escritura** |
| Dependencias de IA | **0** |

El JSONL final valida: **válido, UTF-8 estricto, `observation_id` monótono,
procedencia en todas las líneas, `game_tick` fuera del perímetro**.

---

## Criterios de cierre

| Criterio | Estado |
|---|---|
| Juego real y mundo cargado | ✅ verificado |
| DFHack: versión y funcionamiento | ✅ `53.16-r2rc2` |
| APIs concretas identificadas | ✅ 13, todas probadas |
| Visibilidad clasificada y justificada | ✅ 13/13 |
| ≥3 datos reales | ✅ **13** |
| JSONL real generado y validado | ✅ 65 observaciones |
| Procedencia por dato | ✅ `mechanism` en todas |
| Correspondencia con la interfaz | ⚠️ **pendiente de verificación humana** |
| Integridad del núcleo | ✅ hashes intactos |
| Rendimiento | ✅ medido (~7 ms) |
| Expediente | ✅ 6 documentos + evidencias |
| Regresión sin alteraciones | ✅ núcleo intacto |

**No se declara nada cerrado basándose solo en documentación:** todos los datos
proceden de ejecución real contra el juego vivo.

---

## Lo que esta misión NO hace

No conecta el observador a la API ni a la Web. No modifica ningún contrato
congelado. No conecta ningún modelo. No introduce identidad de estado por la
puerta de atrás — P1.3 la cerró sin demostración y aquí **no se pretende
reabrirla**.