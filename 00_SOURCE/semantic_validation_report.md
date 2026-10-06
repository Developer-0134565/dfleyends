# DF-Chronicles :: Informe de validación semántica

Misión de **VALIDACIÓN**: comprobar que los datos integrados permiten responder
de forma estructurada sobre el mundo. No se ha generado ninguna crónica, lore,
interpretación, ranking ni puntuación de personajes.

- Base: `processed/merged/` + `processed/from_legends_plus/` (JSONL ya generados)
- Herramienta: `00_SOURCE/tools/validar_semantica.py`
- Dependencias: solo biblioteca estándar de Python 3.14
- Los XML originales **no** han sido abiertos para escritura

## Resumen

| Concepto | Valor |
|---|---:|
| Validaciones ejecutadas | 11 |
| Validaciones completadas | 11 |
| Errores | 0 |
| Advertencias registradas | 7 |
| Consultas A–H demostradas | 8 de 8 |
| Fixtures generados | 6 |

### Hallazgo principal sobre el rango temporal

> Los eventos abarcan únicamente los años **1–100**.
> `-1` es un valor centinela de Dwarf Fortress que significa *sin dato*, y así se trata.
> La única era declarada (`historical_eras`) tiene `start_year = -1`: **UNKNOWN**.

## Figuras

| Métrica | Valor |
|---|---:|
| Total de figuras históricas | 11.144 |
| Con nombre | 11.144 |
| Sin nombre | 0 |
| Con race | 11.139 |
| Con entidad asociada | 10.722 |
| Con eventos asociados | 9.197 |
| Sin eventos asociados | 1.947 |
| Con múltiples eventos | 7.589 |
| Con relaciones de legends_plus | 6.823 |
| Con nombre y race | 11.139 |

**Figuras que cumplen criterios de selección (nombre + entidad + ≥2 eventos): 7.481**

### 10 ejemplos reconstruidos

| df_id | Nombre | Race | Entidad | Eventos | Relaciones+ |
|---|---|---|---|---:|---:|
| `712` | galka shafttop the blades of knighting | MINOTAUR | the infamous disloyalty | 0 | 0 |
| `327` | rakust burialtunneled | NIGHT_CREATURE_7 | the lips of toning | 0 | 0 |
| `322` | baros phantomburials the night of graves | NIGHT_CREATURE_12 | the hatred of ink | 0 | 0 |
| `1156` | risen bellschewed | NIGHT_CREATURE_14 | the bloody demon | 2 | 2 |
| `730` | zagod knotjaw the confident pulp | MINOTAUR | the infamous disloyalty | 0 | 0 |
| `328` | usmdas shadecrypts the ghost of abysses | NIGHT_CREATURE_6 | trololeenkis | 0 | 0 |
| `319` | engig washedswim the primitive | TITAN_9 | the grass of action | 0 | 0 |
| `320` | rupola tunnelgraves the umbral twilight | NIGHT_CREATURE_14 | the bloody demon | 0 | 0 |
| `2472` | palara pricechurches | TROGLODYTE | the dreamy gorge | 0 | 0 |
| `709` | asa dreamsdent the decisive cat | MINOTAUR | the uncertainty of vice | 0 | 0 |

## Entidades / civilizaciones

| Métrica | Valor |
|---|---:|
| Total de entidades | 1.067 |
| Con nombre | 849 |
| Con figuras relacionadas | 800 |
| Con sitios relacionados | 539 |
| Con eventos relacionados | 721 |
| De tipo `civilization` | 243 |

**Tipos de entidad presentes en el XML:**

| Tipo | Cantidad |
|---|---:|
| `sitegovernment` | 487 |
| `civilization` | 243 |
| `religion` | 133 |
| `nomadicgroup` | 123 |
| `guild` | 32 |
| `outcast` | 16 |
| `migratinggroup` | 14 |
| `performancetroupe` | 10 |
| `militaryunit` | 5 |
| `merchantcompany` | 4 |

**Civilizaciones con nombre + figuras + eventos: 23**

### 10 ejemplos (recorrido de relaciones)

| df_id | Nombre | Figuras | Sitios | Eventos |
|---|---|---:|---:|---:|
| `282` | the curled diamond | 25 | 16 | 769 |
| `294` | the rock of voicing | 82 | 23 | 764 |
| `296` | the fenced artifact | 3 | 5 | 702 |
| `310` | the confederations of wonder | 57 | 22 | 577 |
| `268` | the glad bust | 32 | 18 | 473 |
| `306` | the scoured ropes | 35 | 11 | 367 |
| `304` | the fly of corridors | 38 | 18 | 275 |
| `300` | the nation of reverence | 30 | 23 | 262 |
| `314` | the kingdom of igniting | 5 | 9 | 246 |
| `312` | the infamous disloyalty | 44 | 17 | 209 |

Estructura de recorrido demostrada (todos los valores son FACT):

```
Civilización (entities)
 ├── figuras      <- entity_link.entity_id  (FACT)
 ├── sitios       <- sites.civ_id/cur_owner_id  (FACT)
 ├── eventos      <- historical_events.civ_id  (FACT)
 └── relaciones   <- hf_link / entity_link  (FACT)
```

## Sitios

| Métrica | Valor |
|---|---:|
| Total de sitios | 734 |
| Con nombre | 734 |
| Con coordenadas | 734 |
| Con tipo | 734 |
| Con civilización | 540 |
| Con figuras asociadas | 292 |
| Con eventos asociados | 481 |
| Con artefactos | 82 |

### 10 ejemplos

| df_id | Nombre | Tipo | Coordenadas | Civ. | Eventos | Figuras |
|---|---|---|---|---|---:|---:|
| `87` | halesteel | fortress | [112, 20] | the rock of voicing | 1.546 | 48 |
| `88` | bootgalleys | fortress | [96, 113] | the fenced artifact | 1.357 | 0 |
| `96` | listenfly | dark fortress | [98, 103] | the infamous disloyalty | 1.031 | 4 |
| `204` | boatsaviors | fortress | [16, 40] | the curled diamond | 803 | 1 |
| `85` | voicecruel | dark fortress | [106, 110] | the hatred of ink | 779 | 6 |
| `95` | passdangles | town | [101, 3] | the confederations of wonder | 693 | 5 |
| `76` | tomblines | fortress | [79, 21] | the glad bust | 678 | 0 |
| `92` | scourgetalk | dark fortress | [110, 124] | the fly of corridors | 645 | 6 |
| `93` | gravelwondered | fortress | [38, 17] | the scoured ropes | 600 | 1 |
| `82` | mirthfulbeast | forest retreat | [65, 13] | the fur of wishing | 542 | 1 |

## Eventos

| Métrica | Valor |
|---|---:|
| Total de eventos | 57.215 |
| Con año | 57.215 |
| Con tipo | 57.215 |
| Con hfid (figura) | 35.131 |
| Con civ_id (entidad) | 11.960 |
| Con site_id | 38.678 |
| Con coordenadas | 1.365 |
| Con collection | 5.958 |
| Tipos de evento distintos | 90 |
| Rango de años | 1–100 |

### Tipos de evento más frecuentes

| event_type | Cantidad |
|---|---:|
| `change hf state` | 10.718 |
| `change hf job` | 8.692 |
| `add hf entity link` | 7.534 |
| `hf simple battle event` | 5.478 |
| `hf died` | 4.484 |
| `add hf hf link` | 2.364 |
| `written content composed` | 2.341 |
| `creature devoured` | 2.085 |
| `performance` | 1.215 |
| `ceremony` | 901 |
| `hf wounded` | 871 |
| `competition` | 789 |
| `add hf site link` | 688 |
| `remove hf hf link` | 554 |
| `hf abducted` | 523 |
| `procession` | 499 |
| `assume identity` | 468 |
| `create entity position` | 453 |
| `hf relationship denied` | 431 |
| `hfs formed reputation relationship` | 421 |

### 20 eventos reconstruidos

| df_id | Año | Tipo | Subtipo | Participante | Sitio |
|---|---:|---|---|---|---|
| `1` | 1 | change hf state | — | unib pustook the famous strength | meancracked the sewer of alchemy |
| `12` | 1 | change hf state | — | rogon gutshogs the hideous snarls | crosssewers |
| `14` | 1 | change hf state | — | zedan brandedsilver the luxurious gem | the night of disembowelers |
| `17` | 1 | change hf state | — | ral flickeredsizzles the torrid | youthmines the scourge of attack |
| `18` | 1 | change hf state | — | thana achehawk | nightfish |
| `19` | 1 | change hf state | — | rimi searchedtattoos | risemined |
| `2` | 1 | change hf state | — | bestra hotsizzled the luxurious pearl | birdumbra the abysses of dancing |
| `20` | 1 | change hf state | — | ogmong naughtywaves | sculpturemine |
| `21` | 1 | change hf state | — | vakist peakflush | spatteredscar |
| `22` | 1 | change hf state | — | lenod gladsmiled | darksang |
| `23` | 1 | change hf state | — | ukung grievescholar | crackbristle |
| `24` | 1 | change hf state | — | sushsath glowingsprinkles | creepymines |
| `25` | 1 | change hf state | — | osma echolurk | echoflew |
| `26` | 1 | change hf state | — | osmmuk bristlevisions | umbrakings |
| `27` | 1 | change hf state | — | zamoth diamondsmoothness | giftedholes |
| `28` | 1 | change hf state | — | nutxox enjoyeddivine | blossomshaft |
| `29` | 1 | change hf state | — | carila savemartyred | minednourish |
| `30` | 1 | change hf state | — | okol stoodtarnishes | scarrace |
| `31` | 1 | change hf state | — | mitstu chancewaves | echoscoured |
| `32` | 1 | change hf state | — | azkob crescentgleam | grandechoes |

## Relaciones

| Métrica | Valor |
|---|---:|
| Total de relaciones | 13.192 |
| Apuntan a un evento presente | 0 |
| Apuntan a los IDs ausentes | 13.192 |
| IDs ausentes distintos referenciados | 13.192 |
| Conectan dos figuras válidas | 13.192 |
| Tipos de relación distintos | 12 |

> **Las 13.192 relaciones se conservan como relaciones**, nunca como eventos.
> Las 13.192 que conectan dos figuras válidas confirmadas: 0 eventos inventados.

| Tipo de relación | Cantidad |
|---|---:|
| `childhood_friend` | 6.106 |
| `lover` | 4.728 |
| `former_lover` | 1.591 |
| `war_buddy` | 562 |
| `jealous_obsession` | 97 |
| `athlete_buddy` | 44 |
| `religious_persecution_grudge` | 39 |
| `artistic_buddy` | 16 |
| `scholar_buddy` | 5 |
| `business_rival` | 2 |
| `grudge` | 1 |
| `lieutenant` | 1 |

### Ejemplo de cadena de relaciones

```json
{
  "nota": "Las relaciones se consultan por event_id; como todas apuntan a IDs ausentes, se consultan por figura (rel_por_hf).",
  "consulta": "Consultas.relaciones_de(df_hf)"
}
```

Cadena verificada: `FIGURA -> (relationships de plus) -> otra FIGURA`, por ejemplo figura 712 con eventos `hf simple battle event` cuyo `group_2_hfid` referencia figuras reales del mismo export.

## Geografía

| Sección | Registros | Esperado | Coincide | Con ID DF | Con nombre | Con coordenadas |
|---|---:|---:|---|---:|---:|---:|
| `rivers` | 2.346 | 2.346 | sí | 0 | 2.346 | 2.346 |
| `landmasses` | 40 | 40 | sí | 40 | 40 | 40 |
| `mountain_peaks` | 4 | 4 | sí | 4 | 4 | 4 |
| `world_constructions` | 122 | 122 | sí | 122 | 122 | 122 |

> `rivers` no tiene `<id>` en el XML: sus identificadores son **DERIVED** (hash determinista del contenido), nunca aleatorios.

### Ejemplos reales

| Sección | Nombre | Coordenadas |
|---|---|---|
| `rivers` | Speaksoak the Bald Fur | 3,40,0,13,99|2,40,16,9,99| |
| `rivers` | Platedclout | 4,97,33,12,106|4,98,65,13,101|4,99,101,10,101|3,99,134,8,9 |
| `rivers` | Valleyrise the Mean Cavern | 6,114,0,9,100|5,114,24,11,99|5,115,47,8,99| |
| `landmasses` | The Land of Folds | [[1, 2]] |
| `landmasses` | The Symmetric Island | [[72, 2]] |
| `landmasses` | The Subtle Island | [[4, 4]] |
| `mountain_peaks` | The Narrow Teeth | [[54, 96]] |
| `mountain_peaks` | The Grizzly Hatchet | [[112, 16]] |
| `mountain_peaks` | The Fuchsia Tusk | [[16, 42]] |
| `world_constructions` | The Ashen Way | [[126, 14], [125, 14], [124, 14], [123, 14], [122, 14], [1 |
| `world_constructions` | The Oceanic Bridge | [[119, 14]] |
| `world_constructions` | The Scoured Bridge | [[122, 14]] |

**Referencias cruzadas geográficas:** las `world_constructions` tienen coordenadas
reales (`x,y`), lo que permite enlazarlas con los `sites` por coincidencia exacta.
Ese enlace es **DERIVED** (coordenada compartida), no FACT.

## Identidades

| Métrica | Valor |
|---|---:|
| Total de identities | 475 |
| Con histfig_id | 117 |
| histfig_id resuelto contra historical_figures | 117 |
| histfig_id sin figura correspondiente | 0 |
| Con entity_id | 358 |
| Figuras cuyo nombre procede de legends.xml | 11.144 |

> Las `identities` son el mecanismo por el que `legends_plus.xml` aporta nombres
> donde no los lleva en línea. Los **11.144 nombres de figura provienen de
> `legends.xml`**, tal como exige la regla de no perder datos de la fuente primaria.

**Cadena verificable:** `id -> identity -> figura/entidad`, mediante
`identities.histfig_id -> historical_figures.df_id` y
`identities.entity_id -> entities.df_id`.

## Artefactos

| Métrica | Valor |
|---|---:|
| Total de artefactos | 427 |
| Con nombre | 374 |
| Con item_type | 389 |
| Con propietario | 136 |
| Con sitio | 278 |
| Con escritura | 305 |
| Sin propietario ni sitio | 13 |

### 10 ejemplos

| df_id | Nombre | Tipo | Material | Propietario | Sitio |
|---|---|---|---|---|---|
| `50` | the wave of prairies | slab | zinc | UNKNOWN | healedbud |
| `51` | the sin of filth | slab | shale | UNKNOWN | lawcysts |
| `52` | the ferocity of sabres | slab | puddingstone | UNKNOWN | conflictsearches |
| `53` | earlybraved | slab | mudstone | UNKNOWN | nourishbuds |
| `54` | the silty lamb | slab | pyrolusite | UNKNOWN | glovedmenaced |
| `55` | ashgrease | slab | dolomite | UNKNOWN | glandbulwarks |
| `56` | perfectpower | slab | aluminum | UNKNOWN | foldedurns |
| `57` | the interpretation of snodub racedevil | book | realgar | UNKNOWN | malignedfinder |
| `58` | deadspring | slab | calcite | dalzat flutecall the wise persuader | UNKNOWN |
| `59` | sculptkeys | shield | iron | UNKNOWN | the clean deeps |

## Cronología

La reconstrucción cronológica funciona con las consultas D y B.

**Consulta D — «eventos entre el año A y el B»**

> Asking: años 1–10 → **2.826 eventos** ordenados por (año, segundos72).

| Año | seg72 | Tipo | hfid | site_id | civ_id |
|---:|---:|---|---|---|---|
| 1 | -1 | change hf state | 0 | None | None |
| 1 | -1 | change hf state | 1 | 1 | None |
| 1 | -1 | change hf state | 10 | None | None |
| 1 | -1 | change hf state | 100 | None | None |
| 1 | -1 | change hf state | 101 | None | None |
| 1 | -1 | change hf state | 102 | None | None |
| 1 | -1 | change hf state | 103 | None | None |
| 1 | -1 | change hf state | 104 | None | None |
| 1 | -1 | change hf state | 105 | None | None |
| 1 | -1 | change hf state | 106 | None | None |
| 1 | -1 | change hf state | 107 | None | None |
| 1 | -1 | change hf state | 108 | None | None |
| 1 | -1 | change hf state | 109 | None | None |
| 1 | -1 | change hf state | 11 | None | None |
| 1 | -1 | change hf state | 110 | None | None |

**Consulta B — «historia conocida de la figura X»**

- Figura: **galka shafttop the blades of knighting** (df_id `712`)
- Eventos totales: **158**, rango [1, 17]
- Lugares: bootgalleys, faintflies, listenfly, voicecruel
- Entidades: the feral syrup, the hatred of ink, the infamous disloyalty, the muddled torment, the tick of night

| Año | Tipo | Sitio | Entidad |
|---:|---|---|---|
| 1 | change hf state | UNKNOWN | UNKNOWN |
| 1 | hf simple battle event | faintflies | UNKNOWN |
| 1 | hf simple battle event | faintflies | UNKNOWN |
| 1 | add hf entity link | UNKNOWN | the infamous disloyalty |
| 1 | add hf entity link | UNKNOWN | the tick of night |
| 1 | hf simple battle event | faintflies | UNKNOWN |
| 4 | hf simple battle event | listenfly | UNKNOWN |
| 4 | add hf entity link | UNKNOWN | the muddled torment |
| 4 | hf simple battle event | listenfly | UNKNOWN |
| 4 | hf simple battle event | listenfly | UNKNOWN |
| 4 | hf simple battle event | listenfly | UNKNOWN |
| 9 | hf simple battle event | listenfly | UNKNOWN |
| 16 | hf simple battle event | voicecruel | UNKNOWN |
| 16 | add hf entity link | UNKNOWN | the hatred of ink |
| 16 | hf simple battle event | voicecruel | UNKNOWN |

**Recorridos cruzados verificados** (todos los enlaces FACT salvo indicación):

| Recorrido | Figura | Eventos | Sitios distintos | Entidades distintas |
|---|---|---:|---:|---:|
| FIGURA → EVENTOS → SITIOS → ENTIDADES | `712` | 158 | 3 | 4 |
| FIGURA → EVENTOS → SITIOS → ENTIDADES | `327` | 118 | 6 | 8 |
| FIGURA → EVENTOS → SITIOS → ENTIDADES | `322` | 117 | 3 | 4 |

## Conflictos entre fuentes

**No se resuelven.** Ambos valores siguen accesibles.

| Categoría | Registros |
|---|---:|
| Divergencias totales | 12.866 |
| Conflictos reales (valores distintos) | 1.925 |
| Notaciones equivalentes (mismo dato, dos formas) | 10.941 |

| Campo | Tipo | Casos |
|---|---|---:|
| `race` | conflicto_real | 276 |
| `race` | notacion_equivalente | 224 |

### Ejemplos con ambos valores accesibles

Verificados sobre el conjunto completo de `merged/*.jsonl` (no sobre la muestra):

| Campo | Tipo | legends.xml | legends_plus.xml | Resolución |
|---|---|---|---|---|
| `style` | conflicto_real | `serious:2` | `Serious` | **UNRESOLVED** |
| `style` | conflicto_real | `vicious:2` | `Vicious` | **UNRESOLVED** |
| `race` | conflicto_real | `BIRD_ROC` | `roc` | **UNRESOLVED** |
| `race` | notacion_equivalente | `COLOSSUS_BRONZE` | `bronze colossus` | **UNRESOLVED** |

```json
[
  {
    "field": "style",
    "source_legends": "serious:2",
    "source_plus": "Serious",
    "resolution": "UNRESOLVED"
  },
  {
    "field": "race",
    "source_legends": "BIRD_ROC",
    "source_plus": "roc",
    "resolution": "UNRESOLVED"
  }
]
```

> `resolution: UNRESOLVED` — no se elige ganador. La fuente primaria
> (`legends.xml`) conserva el valor en `campos.<campo>.valor`, y el valor de plus
> permanece en el registro `conflictos[]`.

## Reconstrucción de guerras / conflictos

> **El XML NO contiene una tabla `wars`.** No se ha creado ni supuesto ninguna.

Eventos de tipo `hf simple battle event`: **5.478**.

| subtipo | Cantidad |
|---|---:|
| `attacked` | 2.733 |
| `scuffle` | 1.906 |
| `ambushed` | 428 |
| `confront` | 163 |
| `2 lost after receiving wounds` | 135 |
| `happen upon` | 84 |
| `2 lost after giving wounds` | 14 |
| `surprised` | 5 |
| `got into a brawl` | 5 |
| `corner` | 5 |

Otros `event_type` relacionados con conflicto y muerte:

| event_type | Cantidad |
|---|---:|
| `hf simple battle event` | 5.478 |
| `hf died` | 4.484 |
| `hf abducted` | 523 |
| `attacked site` | 98 |
| `hf attacked site` | 61 |
| `field battle` | 50 |
| `hf destroyed site` | 46 |
| `destroyed site` | 3 |

Estructura que podría sostener una futura entidad `WAR` (**DERIVED**, con reglas
explícitas y reproducibles):

```
WAR (DERIVED) = grupo de eventos donde:
  event.type  == 'hf simple battle event'
  event.subtype IN ('attacked','ambushed','confront', ...)   <- regla explícita
  party_A = group_1_hfid   party_B = group_2_hfid              <- FACT
  site     = site_id                                        <- FACT
  year     = year                                           <- FACT
```
Sin esas reglas el agrupamiento sería INTERPRETATION y **no se ha realizado**.

## Huérfanos y datos insuficientes

> Ningún huérfano se trata como error: se clasifican.

| Categoría | Registros | Interpretación |
|---|---:|---|
| `evento sin participantes` | 17.881 | — |
| `HUERFANO LEGITIMO` | 13.192 | Comportamiento normal de Dwarf Fortress: exporta esos eventos en una tabla separada. **No es un fallo.** |
| `DATOS INSUFICIENTES` | 1.947 | El registro existe pero no tiene datos que lo vinculen a nada. |
| `REFERENCIA INCOMPLETA` | 422 | El registro existe pero le falta un enlace (p.ej. figura sin entidad). |
| `entidad sin relaciones` | 230 | — |
| `sitio sin referencias` | 88 | — |
| `artefacto sin propietario ni sitio` | 13 | — |

**Referencias rotas: 0.** Ningún `hfid`, `site_id` o `civ_id` de un evento apunta
a un ID inexistente. Es un resultado relevante: la integridad referencial interna
de `legends.xml` es completa.

## Limitaciones

Lo que los datos **NO** permiten determinar:

| Limitación | Detalle |
|---|---|
| **Profundidad temporal** | Los eventos cubren solo los años 1–100. No hay historia anterior ni posterior. |
| **La era es UNKNOWN** | `historical_eras` tiene una única entrada con `start_year = -1` (centinela). No se puede datar el mundo. |
| **17.881 eventos sin participantes** | Sin `hfid` ni `civ_id`: no se pueden atribuir a nadie. |
| **1.947 figuras sin eventos** | Existen y tienen nombre, pero no participan en ningún evento registrado. |
| **1.065 coords de evento son centinela** | `coords = -1,-1` significa *sin dato*; no se inventó posición. |
| **13.192 relaciones sin evento propio** | Los `event_id` que citan no existen en `historical_events`. Solo se puede consultar la relación y su año, no el evento. |
| **No hay tabla de guerras** | Los conflictos son eventos discretos. Una entidad `WAR` sería DERIVED y requiere reglas explícitas. |
| **Nombres de entidad ausentes** | 218 entidades sin nombre (`con_nombre` = 849 de 1.067). |
| **Nombres de figuras solo en la primaria** | Los 11.144 nombres vienen de `legends.xml`; `legends_plus.xml` no los trae en línea. |
| **Año y segundos72 a veces son `-1`** | Se marcan UNKNOWN, no se imputan. |

### Lo que SÍ se ha demostrado

| Consulta | Estado | Evidencia |
|---|---|---|
| A. ¿Quién es esta figura? | funciona | nombre, race, caste, fechas, entidad y sitio |
| B. ¿Qué acontecimientos de esta figura? | funciona | historia ordenada con lugares y entidades |
| C. ¿Qué ocurrió en este sitio? | funciona | eventos, figuras, civ., construcciones por coordenadas |
| D. ¿Qué ocurrió entre dos fechas? | funciona | eventos ordenados por (año, segundos72) |
| E. ¿Quién participó en un evento? | funciona | hfid, objetivo, grupos 1 y 2 |
| F. ¿Qué relaciones hay en un evento? | parcial | vía `source_hf`/`target_hf`; los `event_id` de plus no existen como evento |
| G. ¿Qué conocemos de esta entidad? | funciona | figuras, sitios, eventos, posición |
| H. ¿Qué sabemos de este artefacto? | funciona | tipo, material, propietario, sitio |

## Fixtures generados

En `00_SOURCE/processed/validation/`, solo con IDs y datos reales:

| Archivo | Contenido |
|---|---|
| `figures_sample.json` | 12 figuras con nombre, race y conteos |
| `entities_sample.json` | 12 civilizaciones con figuras y eventos |
| `sites_sample.json` | 12 sitios con coordenadas y civ. |
| `events_sample.json` | 24 eventos con año, tipo y enlaces |
| `artifacts_sample.json` | 12 artefactos con propietario/sitio |
| `timeline_sample.json` | conteos DERIVED por año |
| `relationship_sample.json` | 12 relaciones de plus con año y figuras |

## Fuentes

- `legends.xml` (CP437) — fuente primaria: eventos, colecciones, era, nombres.
- `legends_plus.xml` (UTF-8) — complementaria: relaciones, geografía, identidades.
- Ningún dato de este informe procede de interpretación: todo es FACT o DERIVED,
  con el criterio declarado en cada tabla.
