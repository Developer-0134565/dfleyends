# CONTRATOS PRE-IA — AUDITORÍA Y MATRIZ

> Auditoría sobre el código real, no sobre documentación.

## Matriz de contratos

| ID | Contrato | Productor | Consumidor | Test | Estado |
|---|---|---|---|---|---|
| C01 | envelope (`ok`/`data`/`status`/`meta`) | `servicio.py` | API, Web | `probar_api.py` | VERIFIED |
| C02 | `certainty` | `envolver_ficha` | API, Web | `probar_contrato_certainty.py` + **M01, M02** | VERIFIED |
| C03 | `evidence` | `ia_conocimiento.evidencia_de` | API | `probar_integracion_consulta.py` + **M05** | VERIFIED |
| C04 | `identity` | `servicio_consulta._resultado` | API | `probar_integracion_consulta.py` | VERIFIED |
| C05 | `dataset_id` | `ia_conocimiento.DATASET_ID` | API | `probar_integracion_consulta.py` + **M06** | VERIFIED |
| C06 | `state_version` | — | — | — | **NOT_AVAILABLE** |
| C07 | paginación (`meta`/límites) | `envolver_lista` | API | `probar_api.py` | VERIFIED |
| C08 | HTTP status por estado | `adaptador_consulta._http_de` | API | `probar_integracion_consulta.py` + **M08, M10** | VERIFIED |
| C09 | estados (`FOUND`/`NOT_FOUND`/`NOT_VERIFIED`/…) | `servicio_consulta` | API | `probar_integracion_consulta.py` + **M03, M04** | VERIFIED |
| C10 | `visibility` (mapa) | `dfhack.maps.isTileVisible` | observador | `validar_mapa.py` (8/8) | VERIFIED |
| C11 | Codes CP437→UTF-8 | `cp437.lua` generado | observador | `validar_cp437.py` (128/128) | VERIFIED |
| C12 | procedencia (`observation_id`) | observador | observador | `validar_mapa.py` | VERIFIED |
| C13 | frontera servicio→API | `adaptador_consulta` | API | `probar_api.py` + **M09** | VERIFIED |
| C14 | identidad portable de mundo | — | — | — | **NOT_PROVEN** |
| C15 | descubrimiento histórico | — | — | — | **SEMANTICALLY_INSUFFICIENT** |

---

## FASE 4 — Envelope por estado (medido, no supuesto)

Comprobado sobre respuestas reales del servidor:

| Estado | HTTP | `certainty` | `evidence` | `data` |
|---|---:|---|---|---|
| `FOUND` | 200 | `FACT` | presente | objeto |
| `NOT_FOUND` | **404** | `UNKNOWN` | `null` | `null` |
| `NOT_VERIFIED` | **200** | `UNKNOWN` | cuando aplica | objeto |
| `INVALID_QUERY` | **400** | — | — | `null` |
| `DATA_UNAVAILABLE` | **503** | — | — | `null` |

**Distinción crítica preservada**: `NOT_VERIFIED` es **200**, no 404.
Convertirlo en 404 afirmaría «la figura no existe», que es **más fuerte y
FALSO**. Verificado por **M08** (que degrada `NOT_VERIFIED` a 404 → KILLED).

---

## FASE 7 — Separación temporal

| Símbolo | Significado | No es |
|---|---|---|
| `game_year/month/day` | Fecha del juego | Tiempo real |
| `observed_at` | Momento de observación UTC | Tiempo del juego |
| `updated` (manifest) | Momento de procesamiento | Ninguno de los anteriores |
| `_diag_tick` | Canal **diagnóstico** de P1.6 | **No** conocimiento del jugador |

**No se presenta uno como otro.**

---

## FASE 9 — Procedencia

Auditoría de las 126 líneas de `P1.7/mapa.jsonl`: 100 registros de
conocimiento y 25 diagnósticos, cada uno con `provenance` completa
(método, api, `df_version`, `dfhack_version`, `read_only`).

- **0** fugas: ningún `NOT_VISIBLE` aparece como conocimiento.
- **0** IDs duplicados.
- **0** conversiones silenciosas: CP437 marcado `__NO_UTF8_PENDIENTE` con hex
  reversible.

---

## Contratos que NO existen (y está bien)

| Ausencia | Clasificación |
|---|---|
| `state_version` | `NOT_AVAILABLE` — P1.3 demostró que no hay identidad del estado vivo |
| UUID de mundo | `NOT_AVAILABLE` |
| Identidad portable entre instalaciones | `NOT_PROVEN` |
| Expiración / caducidad de evidencia | `NOT_AVAILABLE` — no hay reloj |

**No se crean para rellenar una casilla.** Un contrato inventado que ningún test
puede matar es peor que una ausencia documentada.
