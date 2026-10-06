# DATASET — INVENTARIO COMPLETO DE EVENTOS

> Barrido **completo**, no una muestra. Cada una de las **57.215** líneas de
> `00_SOURCE/processed/merged/historical_events.jsonl` se leyó exactamente una
> vez. Artefacto: `_eventos_inventario.json`.

| Métrica | Valor |
|---|---:|
| Líneas leídas | **57.215** |
| Corruptas | **0** |
| Tipos distintos | **90** |
| Tipos utilizables | **78** |
| Artefacto | `dfchron/pruebas/_eventos_inventario.json` |

Reproducir: `python dfchron/pruebas/inventario_eventos.py`

---

## El hallazgo que cambió el diseño

Mi primera heurística buscaba el sujeto en campos `hf` y `figure`.
**Esos campos NO EXISTEN.** El campo real se llama **`hfid`**.

Con los nombres correctos, los tipos utilizables pasan de **11 a 78 de 90**.

> Una lista de campos **supuesta** habría descartado el 88 % de los eventos
> por un nombre inventado. Es exactamente el fallo que este proyecto lleva
> cuatro fases evitando.

### Nombres de campo verificados

| Dimensión | Campos reales |
|---|---|
| **Tiempo** | `year`, `seconds72` — presentes en **los 57.215** registros |
| **Sujeto** | `hfid`, `hfid_target`, `target_hfid`, `slayer_hfid`, `group_1_hfid`, `group_2_hfid`, `hist_figure_id`, `entity_id`, `site_id`, `item_id`, `structure_id`, `position_id`, `civ_id`, `site_civ_id`, `occasion_id`, `schedule_id`, `link` |

---

## Tipos principales

| Tipo | N | Utilizable | Identificadores |
|---|---:|:---:|---:|
| `change hf state` | 10.718 | Sí | 2 |
| `change hf job` | 8.692 | Sí | 2 |
| `add hf entity link` | 7.534 | Sí | 4 |
| `hf simple battle event` | 5.478 | Sí | 3 |
| **`hf died`** | **4.484** | **Sí** | 3 |
| `add hf hf link` | 2.364 | Sí | 2 |
| `written content composed` | 2.341 | Sí | 2 |
| `creature devoured` | 2.085 | Sí | 1 |
| `performance` | 1.215 | Sí | 4 |
| `ceremony` | 901 | Sí | 4 |
| `hf wounded` | 871 | Sí | 1 |
| `hf abducted` | 523 | Sí | 2 |
| `created site` | 406 | Sí | 3 |
| `artifact created` | 377 | Sí | 3 |
| `created structure` | 319 | Sí | 4 |

**12 tipos no utilizables** por carecer de sujeto identificable: `assume
identity`, `create entity position`, `item stolen`, y 9 más.

---

## Ejemplo real: `hf died`

```
record_id : historical_events:829
df_id     : 829
certainty : FACT
source    : legends.xml
hfid      : 676          <- quién murió
year      : 1            <- cuándo
seconds72 : 25200        <- sub-año
cause     : struck
slayer_race : MINOTAUR
slayer_caste: FEMALE
site_id   : 111
```

**Tiene todo lo necesario**: identidad del sujeto (`hfid`), tiempo (`year`,
`seconds72`), contenido (`cause`) y procedencia (`record_id`, `source`,
`certainty`, más la procedencia **por campo** que declara el dataset merged).

---

## Procedencia por campo: un regalo del dataset

En `processed/merged/`, cada campo trae su propia procedencia:

```json
"cause": {"valor": "struck", "source": "legends.xml",
          "source_section": "historical_events"}
```

El loader ya la respeta con `valor_de()` y `procedencia_de()`. **No la inventa.**

---

## Decisión sobre el tiempo

El motor usa `tick` como clave de orden. El dataset da `year` y `seconds72`, que
son **campos reales**.

**No he convertido `year`/`seconds72` a ticks de DF.** Eso exigiría conocer la
constante exacta de la conversión (ticks por año y por tick72) y **no está
demostrada**. Convertirla sería inventar precisión temporal.

Pendiente: usar `(year, seconds72)` como clave temporal compuesta, que es
determinista y no requiere constante inventada.

---

## Mapeo semántico (propuesto, no implementado)

| Tipo de evento | Tipo Chronicles | Estado |
|---|---|---|
| `hf died` | `DEATH` | **IMPLEMENTABLE** |
| `add hf entity link`, `add hf hf link` | `ARRIVAL` | Propuesto, requiere verificar semántica |
| `created site`, `created structure` | `CONSTRUCTION` | Propuesto |
| `hf wounded` | — | **OUT_OF_SCOPE** v1 |
| `change hf job` | `PROFESSION_CHANGED` | **NO** — es un cambio *de estado*, no de profesión |

**Ninguno está implementado todavía.** La tabla documenta qué habría que
verificar, no qué se ha Connected.
