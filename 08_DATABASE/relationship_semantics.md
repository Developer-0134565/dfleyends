# Semántica de las 13.192 relaciones

Las relaciones sociales vienen de `legends_plus.xml`, en la sección
`historical_event_relationships`. Este documento fija **qué significa** y
**qué no significa** una de estas relaciones.

Auditoría verificada sobre el conjunto completo (13.192 de 13.192).

---

## 1. La idea central

> **Existe una relación entre A y B**

**NO implica**

> **La relación ocurrió en el evento X.**

El campo `event_id` que acompaña a cada relación **apunta a un evento que no
existe** en `historical_events`. Verificado:

| Comprobación | Resultado |
|---|---|
| Relaciones totales | 13.192 |
| `event_id` distintos citados | 13.192 |
| De esos, **existen** en `historical_events` | **0** |
| Marcadas `event_existe=True` | **0** |

Dwarf Fortress exporta esos eventos en una tabla separada. `legends.xml` no los
incluye en `historical_events`; `legends_plus.xml` sí describe su contenido
social, pero sin el evento correspondiente.

**Convertir estas relaciones en eventos sería inventar 13.192 filas.**

---

## 2. Qué SÍ se puede afirmar

Cada relación aporta estos datos, todos **FACT**:

| Campo | Tipo | Ejemplo |
|---|---|---|
| `tipo` | FACT | `lover` |
| `año` | FACT | `8` |
| `source_hf` | FACT | id de figura (siempre existe) |
| `target_hf` | FACT | id de figura (siempre existe) |
| `event_id` | FACT (referencia) | `2429` — **no resoluble** |

### Integridad verificada

| Comprobación | Resultado |
|---|---|
| `source_hf` resuelve a una figura existente | 13.192 / 13.192 (100 %) |
| `target_hf` resuelve a una figura existente | 13.192 / 13.192 (100 %) |
| Ambas partes resueltas | 13.192 / 13.192 (100 %) |
| Relaciones con `year` propio | 13.192 / 13.192 |
| Rango de esos años | 1 – 99 |

**No hay ninguna referencia rota en las relaciones.**

---

## 3. Qué NO se puede afirmar

| Afirmación | Estado |
|---|---|
| «Ocurrió en el evento 2429» | **IMPOSIBLE**: ese evento no existe |
| «Fue el evento X lo que creó la relación» | **IMPOSIBLE**: no hay evento |
| «La relación;{{nbsp;causó un evento» | **IMPOSIBLE**: no hay causalidad en el XML |
| «A y B se conocieron en el sitio S» | **IMPOSIBLE**: la relación no tiene sitio |
| «Fueron lovers *y después* husbandos» | **IMPOSIBLE**: hay tipos, no una secuencia |
| «Esta relación explica su conflicto posterior» | **INTERPRETACIÓN**: no está en los datos |

---

## 4. El año sí es un dato

La relación tiene su **propio campo `year`** (1–99). Esto **sí** permite decir:

> **FACT** — la relación `lover` entre la figura 1156 y la figura 345 está
> registrada en el año 8.

Lo que **no** permite decir es:

> **IMPOSIBLE** — esa relación ocurrió *durante* el evento 2429.

El `year` es un atributo de la relación, no una referencia temporal a un evento
consultable.

### Tipos y su distribución temporal

| Tipo | Casos | Años |
|---|---:|---|
| `childhood_friend` | 6.106 | 8–99 |
| `lover` | 4.728 | 1–99 |
| `former_lover` | 1.591 | 2–99 |
| `war_buddy` | 562 | 1–98 |
| `jealous_obsession` | 97 | 7–99 |
| `athlete_buddy` | 44 | 1–98 |
| `religious_persecution_grudge` | 39 | 68–95 |
| `artistic_buddy` | 16 | 26–96 |
| `scholar_buddy` | 5 | 70–90 |
| `business_rival` | 2 | 63–89 |
| `grudge` | 1 | 50 |
| `lieutenant` | 1 | 93 |

Los 12 tipos son **literales del XML**: no se traducen ni se reinterpretan.

---

## 5. Hallazgo de la auditoría: el grafo es ASIMÉTRICO

| Comprobación | Resultado |
|---|---|
| Pares `(A,B)` distintos | 11.975 |
| De ellos, con su inverso `(B,A)` también presente | 1.774 (14,8 %) |
| **El grafo es simétrico** | **NO** |

Esto no es un error de datos: es la semántica de Dwarf Fortress. `lover` y
`former_lover` son relaciones **dirigidas en el tiempo**.

**Consecuencia práctica:** una futura IA **no debe** tratar estas relaciones
como un grafo no dirigido. Si A es `lover` de B, **no** se sigue que B sea
`lover` de A en el mismo momento; la relación inversa, si existe, será de otro
tipo (`former_lover`).

---

## 6. Cómo consultar una relación

```python
a.relaciones_de_figura("1156")
```

Cada elemento devuelto incluye:

```json
{
  "tipo": "lover",
  "año": 8,
  "figura_id": "1156",
  "otra_figura_id": "345",
  "otra_figura_nombre": "sibrek lancedape",
  "evento_id": "2429",
  "evento_existe": false,
  "certainty": "FACT",
  "source": "legends_plus.xml",
  "nota": "el evento citado no existe en historical_events; la relación se conserva sin evento asociado"
}
```

Tres señales obligatorias para quien consume el dato:

1. `evento_existe: false` — el evento no está en el dataset.
2. `nota` — la explicación textual del mismo hecho.
3. `certainty: FACT` — **lo FACT es la relación**, no su ancla temporal.

### Filtrar por tipo

```python
a.amigos(df_id)            # childhood_friend
a.amantes(df_id)           # lover
a.exparejas(df_id)         # former_lover
a.companeros_de_guerra(df_id)   # war_buddy
a.obsesiones(df_id)        # jealous_obsession
a.relaciones_de_figura(df_id, tipo="cualquier_tipo_del_xml")
a.tipos_relacion_disponibles()   # los 12 con su recuento
```

---

## 7. Tabla de Suplementos

`historical_event_relationship_supplements` (21 registros) sigue la misma
lógica: aporta `occasion_type`, `reason` y `site` sobre eventos igualmente
ausentes. Se conserva aparte y con la misma advertencia.

---

## 8. Reglas para la futura IA

1. Una relación es **FACT**. Su ancla temporal, **no**.
2. **Nunca** generar, citar ni describir el evento citado por una relación.
3. **Nunca** afirmar causalidad: el XML no la contiene.
4. El grafo es **dirigido**: respetar la asimetría.
5. El `year` de la relación es utilizable; el `event_id` **no**.
6. Si se necesita una narración sobre estas relaciones, debe apoyarse
   únicamente en: tipo, año y las dos figuras implicadas.