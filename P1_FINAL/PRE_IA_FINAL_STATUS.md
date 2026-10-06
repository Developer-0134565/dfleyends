# PRE-IA — ESTADO FINAL

```
PROJECT: DF Chronicles

PRE_IA_STATUS: COMPLETE

DATASET_ESSENTIAL:     VERIFIED
CONTRACTS:             VERIFIED
SERVICE_BOUNDARY:      VERIFIED
API:                   VERIFIED
WEB:                   VERIFIED
READ_ONLY:             VERIFIED
PROVENANCE:            VERIFIED
IDENTITY:              VERIFIED (local) / NOT_PROVEN (portable)
TEMPORALITY:           VERIFIED
VISIBILITY:            VERIFIED
REGRESSION:            PASS
MUTATION:
    KILLED:         9
    SURVIVED:       0
    NOT_APPLICABLE: 1

AI: NOT_IMPLEMENTED

PRODUCTION_HASHES: INTACT
GAME_STATE:       INTACT

OPEN_BLOCKERS: 0
```

---

## Cómo secertificó cada línea

| Línea | Evidencia |
|---|---|
| `DATASET_ESSENTIAL` | `dataset_version.json`: 10 salidas con `sha256` y conteos reales |
| `CONTRACTS` | `AUDITORIA_CONTRATOS_PRE_IA.md`, 15 contratos, 11 VERIFIED |
| `SERVICE_BOUNDARY` | 13 rutas delegan · 20 llamadas al servicio · **0** lógica de dominio en `api.py` |
| `API` / `WEB` | 54/54 + 65/65; Web no calcula certeza, la lee |
| `READ_ONLY` | Auditoría de 10 APIs de escritura + `dfhack.timeout`: **0 coincidencias** |
| `PROVENANCE` | 126 registros JSONL, 0 fugas, 0 IDs duplicados |
| `IDENTITY` | `world_folder` con dos formatos distintos → documentado como local |
| `TEMPORALITY` | 4 tiempos separados; `state_version` declarado `NOT_AVAILABLE` |
| `VISIBILITY` | 125 tiles: 100 visibles, 25 retenidos |
| `REGRESSION` | 32/32 suites, **1.241 tests**, 0 skipped, 0 xfail, 0 regresiones |
| `MUTATION` | 10 mutaciones reales, 9 KILLED, 0 SUPVIVIENTES, 1 NOT_APPLICABLE |

---

## Lo que NO se工作和 no bloquea

| | |
|---|---|
| `state_version` | `NOT_AVAILABLE` — P1.3 lo demostró |
| Identidad portable de mundo | `NOT_PROVEN` |
| Descubrimiento histórico | `SEMANTICALLY_INSUFFICIENT` |

Las tres están **documentadas y clasificadas**. Ninguna se ha inventado para
llenar una casilla.

---

## Hashes de producción

| Fichero | SHA-256 (prefijo) |
|---|---|
| `servicio_consulta.py` | `0a5b6b1c3244e619…` |
| `adaptador_consulta.py` | `c456256ec1c1d731…` |
| `servicio.py` | `48eb8354dca8728b…` |
| `api.py` | `0426f63a632fd243…` |
| `AI_PRE_LLM_CONTRACT.md` | `5d2c3d001c542e77…` |
| `legends.xml` | `77db4739c4064911…` |
| `legends_plus.xml` | `fb6be93dac3e878b…` |

**Los mismos que al inicio de la fase PRE-IA.**

---

## Reproducibilidad

```powershell
python P1_FINAL\corredor.py           # regresion completa
python P1_FINAL\verificar_anclas.py   # 10/10 anclas, antes de mutar
python P1_FINAL\mutaciones.py         # mutation testing (desacoplado)
python dfchron\pruebas\probar_contrato_certainty.py
```

> **Nota operativa:** `mutaciones.py` muta ficheros de producción. Ejecutarlo
> **desacoplado** (`Start-Process`). Con `cmd /c`, el límite de tiempo de la
> shell puede matarlo **con una mutación aplicada**. Ocurrió dos veces y ambas
> se detectaron por hash.

---

## Estado del juego

Partida `Xah Alu`, **pausada**, día 6 del año 10, 14 ciudadanos. **No
modificada** por esta fase: tick constante, cero escrituras en `save/`.

---

# PRE_IA_COMPLETE

El núcleo determinista está terminado y sabemos exactamente qué sabe, qué no
sabe y qué no puede saber.

La futura IA tendrá **un único punto de entrada**: `servicio_consulta`, como
**consumidor**, detrás del mismo contrato. No podrá establecer verdad,
verificación, visibilidad ni política.

**Detenerse aquí. No comenzar IA.**
