# Limitaciones del conjunto de datos

Todas las cifras están **verificadas sobre los datos actuales**. Este documento
forma parte del dataset: una futura IA debe recibirlo como contexto.

**Regla:** estas limitaciones **no se rellenan**. No se completan por inferencia.

---

## 1. Límite temporal — LA MÁS RESTRICTIVA

| Dato | Valor |
|---|---|
| Eventos con año | 57.215 de 57.215 (100 %) |
| Rango de años | **1 – 100** |
| `historical_eras` | 1 registro: *Age of Myth*, `start_year = -1` |

**La historia disponible abarca 100 años.** No hay eventos anteriores al año 1
ni posteriores al 100.

**La era es `UNKNOWN`**: el único registro de era tiene `start_year = -1`, el
centinela de Dwarf Fortress para *sin dato*. **No se puede fechar el mundo.**

Una IA **no debe**:
- Sugerir un pasado más antiguo que el año 1.
- Proyectar hechos más allá del año 100.
- Afirmar la duración del mundo.

`eventos_del_anio(500)` devuelve `certainty: UNKNOWN` con motivo explícito.

---

## 2. Eventos sin participantes

| Categoría | Casos |
|---|---:|
| Eventos sin `hfid` ni `civ_id` | **17.881** (31,3 %) |

Un tercio de los eventos no puede atribuirse a ninguna figura ni entidad. Son
candidatos naturales para eventos de estado (un mundo cambia, una estación
pasa), pero **el XML no lo dice**.

Una IA **no debe** inventar los participantes de estos eventos.

---

## 3. Coordenadas ausentes

| Categoría | Casos |
|---|---:|
| Eventos con coordenada utilizable | 1.365 (2,4 %) |
| Eventos con centinela `-1,-1` | **9.930** (17,4 %) |
| Eventos sin campo `coords` | 45.920 |

Coordenadas de evento son **raras**. No se pueden localizar geográficamente la
mayoría de los acontecimientos, aunque sí se puede consultar su sitio cuando
`site_id` existe (38.678 eventos).

---

## 4. Figuras incompletas

| Categoría | Casos | % |
|---|---:|---:|
| Figuras sin ningún evento | **1.947** | 17,5 % |
| Figuras sin entidad (`entity_link`) | 422 | 3,8 % |
| Figuras sin `birth_year` | 1.555 | 14,0 % |
| Figuras sin `death_year` | **6.734** | 60,4 % |
| Figuras sin nombre | 0 | 0 % |

**El 60 % de las figuras no tiene fecha de muerte registrada.** No significa
que vivieran eternamente: significa que el dato no consta. Esas 6.734 figuras
están probablemente vivas o el export no cerró su registro.

Una IA **no debe** inferir una fecha de muerte a partir de la ausencia de la
misma.

---

## 5. Entidades y artefactos

| Categoría | Casos |
|---|---:|
| Entidades sin nombre | **218** (de 1.067) |
| Artefactos sin propietario ni sitio | 13 (de 427) |
| Artefactos con propietario (`holder_hfid`) | 136 |
| Artefactos con sitio | 278 |
| Artefactos con creador resuelto | 377 eventos `artifact created` |

218 entidades existen con `df_id` pero sin nombre consultable. Tienen tipo
(civilization, religion, sitegovernment…) y relaciones, pero no etiqueta.

---

## 6. Relaciones sociales sin ancla temporal

| Dato | Valor |
|---|---|
| Relaciones | 13.192 |
| Con `event_id` **no resoluble** | 13.192 (100 %) |
| Con `year` propio utilizable | 13.192 (100 %) |

Ver `relationship_semantics.md`. La relación es FACT; su evento no existe.

---

## 7. Geografía incompleta

| Sección | Registros | Con `df_id` de DF |
|---|---:|---:|
| `rivers` | 2.346 | **0** |
| `landmasses` | 40 | 40 |
| `mountain_peaks` | 4 | 4 |
| `world_constructions` | 122 | 122 |

**Los 2.346 ríos no tienen ID de Dwarf Fortress.** Su identificador es
**DERIVED** (hash determinista del contenido). Dos ríos idénticos en contenido
compartirían ID. Nunca deben citarse como «río 17 de DF».

`world_constructions` tiene coordenadas reales, lo que permite enlazarlas con
sitios por coincidencia exacta (`DERIVED`). No existe relación declarada en el
XML entre una construcción y un sitio: el enlace es del núcleo, no del juego.

---

## 8. Conflictos entre las dos fuentes

| Categoría | Casos |
|---|---:|
| Divergencias totales | 12.866 |
| Conflictos reales (valores distintos) | **1.925** |
| Notaciones equivalentes (mismo dato, dos formas) | 10.941 |

Distribución:

| Campo | Tipo | Casos |
|---|---|---:|
| `race` | notación equivalente | 10.640 |
| `style` | conflicto real | 1.426 |
| `race` | conflicto real | 499 |
| `structures.structure.name` | notación equivalente | 170 |
| `structures.structure.type` | notación equivalente | 131 |

**Ninguno se ha resuelto.** Ambos valores siguen accesibles. Una IA que use
`legends.xml` para `race` obtiene el token raws (`COLOSSUS_BRONZE`); si usa
`legends_plus.xml`, obtiene el nombre legible (`bronze colossus`). Ambas cosas
son correctas en su contexto.

---

## 9. No existe tabla de guerras

| Dato | Valor |
|---|---|
| Eventos `hf simple battle event` | 5.478 |
| Tipos de subtipo distintos | 10 |
| Tabla `wars` en el XML | **no existe** |

Los conflictos aparecen como eventos discretos con `type` y `subtype`.
Cualquier agrupación en «guerras» es **DERIVED** y exige una regla explícita.

Una IA **no debe** afirmar que una guerra ocurrió. Solo puede describir
eventos tipificados como enfrentamiento.

---

## 10. Referencias rotas

| Tipo de enlace | Rotas |
|---|---:|
| `historical_events.hfid` → figura | **0** |
| `historical_events.site_id` → sitio | **0** |
| `historical_events.civ_id` → entidad | **0** |
| `relationships.source_hf` → figura | **0** |
| `relationships.target_hf` → figura | **0** |

**La integridad referencial interna de `legends.xml` es completa.** Las únicas
referencias no resolubles son las **13.192 `event_id`** de las relaciones, que
apuntan a eventos que el propio export no incluye.

---

## 11. Resumen para la IA

| Pregunta | Respuesta |
|---|---|
| ¿Cuándo? | Solo años 1–100 |
| ¿Dónde? | Solo 2,4 % de eventos tienen coordenada; usar `site_id` |
| ¿Quién? | El 31 % de eventos no tiene participantes identificables |
| ¿Por qué? | **El XML no contiene motivos, intenciones ni causalidad** |
| ¿Qué relaciones? | FACT por tipo y año; **sin evento asociado** |
| ¿Qué guerras? | **No constan.** Solo eventos de enfrentamiento tipificados |