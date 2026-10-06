# P1.4 — ENTORNO REAL (Fase A)

> Todo lo de aquí procede de **ejecución real**, no de documentación online ni
> de suposiciones. Donde documentación e instalación discrepan, gana la
> instalación.

---

## 1. El juego estaba realmente en marcha

| Comprobación | Resultado | Cómo se obtuvo |
|---|---|---|
| Proceso `Dwarf Fortress` | **VIVO** | `Get-Process` → PID 17428 |
| Ruta | `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\Dwarf Fortress.exe` | `Process.Path` |
| Iniciado | 04/10/2026 16:08 | `StartTime` |
| RAM | 808 MB | `WorkingSet64` |
| Versión del juego | **v0.53.16 win64 STEAM** | `dfhack.getDFVersion()` |
| Versión de DFHack | **53.16-r2rc2** | `dfhack.getDFHackVersion()` |

DFHack coincide exactamente con la versión estudiada en **P1.3**: las
conclusiones de P1.3 sobre `dfhack.persistent`, `with_suspend` y `exportlegends`
se apoyan en la misma versión que esta misión.

---

## 2. DFHack está cargado y es OPERATIVO

```
dfhack-run help   -> devuelve la ayuda real de DFHack
dfhack-run ls     -> lista los comandos disponibles
dfhack-run cprobe -> "No unit is selected in the UI."   <-- consulta al juego
dfhack-run lua "print('DFHACK_LUA_OK')"  -> DFHACK_LUA_OK
```

`cprobe` respondiendo sobre el estado de la interfaz prueba que DFHack **habla
con el juego en ejecución**, no solo con sus propios ficheros.

| Componente | Ruta |
|---|---|
| Motor | `hack\dfhack.dll` (19.627.008 B) |
| Inyección | `dfhooks.dll` (263.168 B) |
| Cliente remoto | `hack\dfhack-client.dll` |
| Ejecutable remoto | `hack\dfhack-run.exe` |

---

## 3. Existe un mundo cargado (solo lectura)

| Comprobación | Valor | Significado |
|---|---|---|
| `dfhack.isWorldLoaded()` | **true** | Hay mundo |
| `dfhack.isMapLoaded()` | **true** | Mapa cargado |
| `dfhack.isSiteLoaded()` | **true** | Sitio activo |
| `dfhack.world.isFortressMode()` | **true** | Partida de **fortaleza** |
| `dfhack.world.ReadPauseState()` | **true** | Partida **pausada** |

**Estaba pausada**, tal como indicó el usuario. Verificado, no supuesto.

---

## 4. Mecanismos de ejecución

### 4.1 `dfhack-run` + Lua en línea

```
dfhack-run lua "<código Lua>"
```

**Limitación descubierta, importante:** si la cadena va entrecomillada,
`dfhack-run` la trata como **un único nombre de comando**:

```
dfhack-run "lua local x=1"    -> "not a recognized command"
dfhack-run lua "print(1)"     -> FUNCIONA
```

Los argumentos deben llegar **separados**. No estaba en la documentación y costó
dos intentos fallidos.

### 4.2 Ejecutar un fichero sin escribir en la instalación

El argumento de `lua` se evalúa como expresión; con `dofile()` se carga un
script desde cualquier ruta absoluta, usando `/` para evitar escapes:

```
dfhack-run lua "dofile('C:/ruta/al/script.lua')"
```

**Esto es la clave del aislamiento:** no hay que escribir nada dentro de la
instalación de Dwarf Fortress. Los scripts viven en `dfchron/pruebas/p1_4/`.

### 4.3 Globales

`_G.NOMBRE = v` **sí** cruza el `dofile`; `NOMBRE = v` a secas **no**.

---

## 5. API descubierta por introspección

No se asumió: se recorrió el espacio de nombres **dentro del juego vivo**.

### `dfhack.world` (53.16-r2rc2)

```
ReadCurrentDay   ReadCurrentMonth  ReadCurrentTick   ReadCurrentWeather
ReadCurrentYear  ReadPauseState    ReadWorldFolder   getAdventurer
getCurrentSite   GetCurrentSiteId  isAdventureMode   isArena
isFortressMode   isLegends         SetCurrentWeather SetPauseState
```

> Los `Set*` son **escritura**. No se han invocado ni una vez en esta misión.

### Estado: funciones de primer nivel

```
dfhack.isWorldLoaded()   dfhack.isMapLoaded()   dfhack.isSiteLoaded()
```

> **Corrección importante:** `dfhack.world.isWorldLoaded()` **no existe** en
> esta versión; falló con `attempt to call a nil value`.

### Conversión de nombres — lo que se creía vs. la realidad

| Se cree que es | Realidad |
|---|---|
| `dfhack.TranslateName` | **no existe** |
| `dfhack.df2utf(language_name)` | **no**: espera cp437, no `language_name` |
| `dfhack.units.getReadableName(u)` | tipo incompatible con `translateName` |
| **`dfhack.translation.translateName(...)`** | **la correcta** |

Verificado en la documentación *de la instalación* (`Lua API.txt`:1072) y luego
en ejecución.

---

## 6. Otros hallazgos

| Hallazgo | Evidencia |
|---|---|
| `hack\lua\json.lua` presente → JSON oficial | `require('json')` → OK |
| `hack\lua\plugins\eventful.lua` → eventos/callbacks | inspección del árbol |
| **`dfhack.units.isVisible(u)`** → DFHack tiene su propio predicado de visibilidad | introspección |
| `remote-server.json`: `allow_remote: false` | lectura del fichero |

Lo último se **respeta**: la comunicación es local, no por red.

---

## 7. Lo que NO se hizo

| Acción | Motivo |
|---|---|
| Escribir script en `hack\scripts\` | Innecesario: `dofile` basta |
| Habilitar `allow_remote` | Expondría DFHack por red |
| `SetPauseState` / `SetCurrentWeather` | Son escritura al juego |
| Arrancar o cerrar DF | El juego ya estaba abierto |
| OCR o capturas | Prohibido como mecanismo de extracción |

**Fase A: entorno verificado por completo. Sin bloqueos.**