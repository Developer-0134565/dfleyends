# INFORME CONTINUACIÓN PRE-IA

> Dos resultados, y uno es una **corrección a la premisa de la misión**: la
> integración API/Web ya existía y está verificada.

---

## 1. §9 — Memoria histórica de tiles

### Veredicto

```
HISTORICAL_DISCOVERY_SEMANTICALLY_INSUFFICIENT
```

**No es PASS.** Existe la estructura, pero no se ha demostrado que distinga los
estados necesarios.

### Método

6 cajas de 5×5×5 alrededor de la fortaleza. **Tope duro de 20 000 tiles**: el
script aborta si lo supera. El incidente anterior vino de un cúmulo abierto sin
cota; esta vez la cota está en el código.

| Caja | Tiles | `fog_of_war` |
|---|---:|---|
| fortaleza | 125 | `{0: 125}` |
| abajo z−2 | 125 | `{0: 125}` |
| este x+2 | 125 | `{0: 125}` |
| oeste x−2 | 125 | `{0: 125}` |
| norte y+2 | 125 | `{0: 125}` |
| arriba z+2 | **0** | bloque no asignado |
| **TOTAL** | **625** | **`{0: 625}`** |

**Coste: 134 ms.** Sin aborto. Partida pausada, tick 174512 sin cambios.

### Interpretación

**`fog_of_war` vale 0 en los 625 tiles.** Ningún valor distinto de cero.

La estructura existe (`df.map_block.fog_of_war`, `uint8_t[16][16]`) y es donde DF
*guardaría* memoria de niebla. Pero en zona **totalmente explorada** vale 0
tanto si `isTileVisible` es `true` como si es `false`: **no discrimina**.

No se ha observado ningún valor no nulo. Por tanto no existe ninguna
observación que permita responder a la pregunta de A4: *¿hay un par de tiles
con la misma visibilidad actual pero distinto estado histórico?*

### Condición de parada aplicada (A6)

Aparecida la evidencia suficiente para **no** poder responder, se detiene.
Seguir habría sido explorar, no investigar, con un coste ya demostrado.

### Estado final

| | |
|---|---|
| ¿Estructura candidata? | **Sí** (`map_block.fog_of_war`) |
| ¿Semántica histórica demostrada? | **No** |
| ¿Necesaria para el perímetro? | **No**: `isTileVisible` basta para *visibilidad actual* |
| Riesgo | Convertir `false` en «nunca descubierto» sería **información negativa inventada** |

**Regla fijada:** `isTileVisible == false` significa **«no visible ahora»**.
Nunca «nunca visto».

---

## 2. Identidad: `world_folder`

| Instalación | Valor | Formato |
|---|---|---|
| AnkerGames (esta, DF 53.16) | `1` | **numérico** |
| Bay 12 Games (P1.3) | `region1`, `region2` | **con nombre** |

`ReadWorldFolder()` devuelve formatos **distintos según la instalación**: es un
**identificador local de carpeta de mundo**, no portable. Puede depender de
versión, instalación y mecanismo de creación.

**Identidad portable de mundo: `NOT PROVEN`.** No se sustituye por otra
identidad inventada.

**Auditoría de uso:** se usa como `subject.id` en las observaciones del
prototipo y como etiqueta de procedencia en P1.4. En **ningún** uso se trata
como identidad universal. **No hay corrección que hacer.**

---

## 3. API — la premisa de la misión era incorrecta

La misión afirma que «la API y la Web todavía no exponen `servicio_consulta`» y
pide migrarlas. **Verificado lo contrario.**

| Comprobación | Resultado |
|---|---|
| `api.py` importa el adaptador | **Sí** |
| Rutas que delegan en `ac.*` | **13** |
| Llamadas del adaptador a `servicio_consulta` (`qc.*`) | **20** |
| Lógica de dominio en `api.py` | **0** |

**No hay nada que migrar.** La arquitectura ya es:

```
HTTP → api.py → adaptador_consulta → servicio_consulta → núcleo
```

Reescribirla habría sido **destruir una integración funcionando** para
satisfacer una premisa equivocada.

Verificado **por ejecución**:

| Suite | Resultado |
|---|---|
| `probar_integracion_consulta.py` | **55/55 OK** |
| `probar_api.py` | **54/54 OK** |
| `probar_web.py` | **65/65 OK** |

### Web

| Fichero | Coincidencias | Veredicto |
|---|---:|---|
| `web/app.js` | 1 | Comentario sobre cómo **etiquetar** la certeza |
| `site/src/lib/api.ts` | 3 | `certeza()` **lee** la etiqueta del envelope |
| `site/src/lib/dataset.ts` | 0 | — |
| `site/src/lib/vistas.ts` | 2 | `visibilitychange` = **pestaña del navegador** |

**Ninguna calcula verdad, verificación, conocimiento o visibilidad.** La Web
*lee* lo que el contrato dice.

---

## 4. Arquitectura (verificada)

```
DF (vivo, pausado)
 ↓
DFHack  ── forEachTile(bounds, callback) ── isTileVisible
 ↓
JSONL (procedencia + visibilidad)
 ↓
Core: truth · evidence · knowledge · visibility · identity · verification · policy
 ↓
servicio_consulta.py       [CONGELADO, hash 0a5b6b1c…]
 ↓
adaptador_consulta.py      [13 rutas, 20 llamadas]
 ↓
api.py ──────────► web/

IA = NO IMPLEMENTADA — 0 dependencias
```

---

## 5. Estado por área

| Área | Estado | Evidencia |
|---|---|---|
| DFHack | **DEMOSTRADO** | v0.53.16 / 53.16-r2rc2 |
| Extracción cartográfica | **DEMOSTRADO** | 125 tiles, `changed=0` |
| Frontera de visibilidad | **DEMOSTRADA** | 100 visibles / 25 retenidos |
| **Descubrimiento histórico** | **SEMANTICALLY INSUFFICIENT** | 625 tiles, fog=0 |
| Identidad portable de mundo | **NOT PROVEN** | `world_folder` no portable |
| API → servicio_consulta | **DEMOSTRADO** | 13 rutas, 55/55 |
| Web → frontera | **DEMOSTRADO** | sin lógica de dominio, 65/65 |
| Duplicación de verificador | **NO** | 0 ocurrencias |
| IA | **CERO** | — |
| Producción | **INTACTA** | 7/7 hashes |

---

## 6. Límites de esta ejecución

**No ejecuté la regresión completa** de las 40 suites: solo las tres que tocan
API, Web e integración. El estado global **no está verificado aquí**.

**No ejecuté mutation testing** del adaptador. Las 9/9 documentadas son de la
misión API/WEB anterior.

Ambas quedan como `NOT_TESTED`, no como `PASS`.

---

## 7. Lo que sigue abierto

1. **Descubrimiento histórico**: haría falta una partida con zona explorada y
   zona vírgena en el mismo mapa. No se puede provocar aquí.
2. **Regresión completa** de las 40 suites.
3. **Mutation testing** del adaptador.
4. **Identidad portable de mundo**: `NOT PROVEN`.