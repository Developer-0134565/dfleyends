# INFORME DE COBERTURA SEMÁNTICA, IDENTIDAD Y ESTADO

> **Sin IA.** Ningún LLM, RAG, embedding, agente ni memoria.
> **Los 10 módulos de producción tienen hash idéntico** al inicio.

---

## A. FUENTES INVESTIGADAS

El proyecto tenía **305 MB sin explotar** en `00_SOURCE/extraction/`. Era la
hipótesis más probable para las cuatro reservas, así que se investigó antes de
concluir nada.

| Fuente | Existe | Utilizada | Qué aporta | Identidad | Temporalidad |
|--------|--------|-----------|------------|-----------|--------------|
| `legends.xml` (49 MB) | Sí | Sí | Primaria: 57.215 eventos, 11.144 figuras | `df_id` por sección | `year` 1–100 |
| `legends_plus.xml` (17 MB) | Sí | Sí | Relaciones, geografía, identidades | `df_id` por sección | `year` |
| `world.sav` descomprimido (208 MB) | Sí | **No** | 10.425 bloques, 150.695 strings, vocabulario de los raw | **Ninguna** | **Ninguna** |
| `save_metadata.json` | Sí | **No** | Nombre del mundo y la fortaleza, versión 53.16 | **Ninguna** | **Ninguna** |
| `raws_tags.txt` (5.534 tags) | Sí | **No** | Vocabulario de interacciones | **Ninguna** | **Ninguna** |
| `raws_labels.txt` (3.944) | Sí | **No** | Vocabulario de etiquetas | **Ninguna** | **Ninguna** |
| `name_candidates.json` | Sí | **No** | 256 nombres candidatos | **Ninguna** | **Ninguna** |
| `strings.json` (29 MB) | Sí | **No** | Strings extraídos | **Ninguna** | **Ninguna** |

### Lo que la búsqueda en el mundo descomprimido dio

| Cadena buscada | Apariciones en 208 MB |
|----------------|----------------------|
| `historical_figure` | **0** |
| `historical_event` | **0** |
| `relationship` | **0** |
| `world` | 10 |
| `site` | 1 |
| `artifact` | 1 |

**El mundo descomprimido no contiene el historial.** Solo el vocabulario de los
raw y los strings del juego. Eso explica por qué `save_metadata.json` declara
`UNKNOWN` en las siete categorías: no es que nadie lo intentara, es que no está.

### Lo que aportan los raw

Aparecen 1.855 tags con identificador numérico. **Se comprobó si eran reales:**

* `SOURCE_HFID`: 436 valores, rango 347–1604. Los 436 caen dentro del rango de
  `df_id`… y los 436 coinciden con figuras reales del dataset.
* Pero son **vocabulario genérico del juego**, no datos de esta partida: los raw
  son los mismos para toda partida.
* Los tags `I_TARGET`, `IT_LOCATION`, `I_SOURCE` describen la **forma** de una
  relación, no ninguna relación concreta.

**Conclusión:** los raw describen qué tipos de relación existen, no qué relaciones
hay. No aportan identidad ni datos.

### Etiquetas temporales en los raw

| Patrón | Tags |
|--------|------|
| `YEAR` | **0** |
| `TICK` | **0** |
| `CYCLES` | **0** |
| `SEASON` | **0** |
| `TIME` | 4 (todas de combate: `INITIATE_SHOT_TIME`, `SHOT_RECOVERY_TIME`) |

**El juego no expone reloj de estado en los raw.** Las 4 etiquetas de `TIME` son
mecánicas de combate, no una hora del mundo.

**Ninguna fuente nueva se ha incorporado.** No aportan, y añadirlas por
curiosidad habría creado complejidad sin capacidad.

---

## B. IDENTIDAD

### Las 3 secciones sin `df_id`, investigadas una a una

| Sección | `record_id` | Por qué NO es identidad |
|---------|-------------|------------------------|
| Relaciones | `her:<event>:<índice de fila>` | El índice es **posicional** y `<event>` no resuelve |
| Suplementos | `sup:<event>:<índice de fila>` | El mismo patrón posicional |
| Eras | `historical_eras:derived:<hash>` | Con **1 sola era** no hay colisión ni referente |

**`<event>` de las relaciones: 13.192 de 13.192 NO resuelven.**

Se buscó un espacio de identificadores alternativo:

| Sección | Intersección con los `event` de las relaciones |
|---------|--------------------------------------------------|
| `historical_events` | **0** |
| `historical_event_collections` (por `eventcol`) | 96 de 13.192 |
| `historical_event_relationship_supplements` | **0** |

Los 96 no conectan: es coincidencia numérica, no un puente. El campo `eventcol`
de las colecciones apunta a su propia jerarquía.

**Prueba de que no es coincidencia:** `historical_events` tiene 57.215 ids y
ninguno coincide. Es un espacio de identificadores completamente distinto.

### ¿Es `(source, target, tipo)` una identidad?

**No.** 12.925 triplas distintas de 13.192 filas: **246 duplicados**.

```
('642', '646', 'lover')  x2
  her:540:2    event=540   year=1
  her:4225:472 event=4225  year=15
```

Son la misma relación en dos años distintos. Sin identidad de fila, no se puede
distinguir una de otra más que por posición.

### El hash de la era

`historical_eras:derived:e635c35ebbfd012f`. Comprobado que **no** es
`sha256(nombre)` (da `1a52bf02…`), ni `sha256(nombre + año)`.

Da igual: **con una sola era no hay nada que separar.** La identidad existe en la
forma y es inútil en la práctica.

---

## C. RELACIONES

### Clasificación pedida

| Tipo | Estado | Detalle |
|------|--------|---------|
| **A. Explícitas** | **DEMOSTRADO** | 10 tipos, 11.145 instancias, 0 huérfanas |
| **B. Derivables** | **DEMOSTRADO** | `sitio → figuras` (índice inverso), `artefacto → creador` (evento `artifact created`) |
| **C. Históricas** | **PARCIAL** | Las colecciones tienen `start_year`/`outcome`, pero no están en el dataset actual |
| **D. Inferidas** | **NO** | No se ha convertido ninguna inferencia en hecho |
| **E. No demostrables** | **DEMOSTRADO** | `relación → evento` (0 de 13.192), guerra (no existe), era (sin años) |

### Hallazgo nuevo: las colecciones llevan relaciones que el dataset no expone

`historical_event_collections` tiene campos que **no están** en
`historical_event_relationships`:

```
attacking_hfid, defending_hfid, outcome, start_year, end_year,
attacking_site, defending_site, attacking_squad_race, ...
```

6.544 colecciones con tipo explícito: `beast attack` (1.660), `performance`
(1.215), `ceremony` (901), `competition` (789), `battle` (148), `war` (60)…

**Es una capacidad derivable que el núcleo actual no expone**: una relación con
**clase, resultado y año**. No se ha implementado porque conectarlo exige decidir
qué es una relación y qué una colección, y eso es diseño, no evidencia.

Queda documentada como **C: histórico, pendiente**.

---

## D. ERAS

**Resultado: NO DISPONIBLE en las fuentes investigadas.**

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué es una era? | Una fila: nombre (`Age of Myth`) y `start_year` |
| ¿Tiene identificador? | `df_id = null`. `record_id` con hash, inútil con 1 elemento |
| ¿Tiene límites temporales? | **No.** `start_year = -1`, centinela de «sin dato» |
| ¿Tiene eventos asociados? | **No.** Ningún campo que lo conecte |
| ¿Puede relacionarse con entidades? | **No** |
| ¿Identidad estable? | **No demostrable** con un solo elemento |

Es la reserva mejor investigada: se buscaron identificadores en el dataset, en el
mundo descomprimido, en los raw y en las colecciones. **Ninguno existe.**

---

## E. VERIFICACIÓN SEMÁNTICA

### La distinción que cambia el resultado

«Verificación semántica» eran **dos** capacidades con una sola etiqueta:

| Qué | Antes | Ahora |
|-----|-------|-------|
| Afirmación **estructurada** (sujeto + predicado) | «no verificable» | **DEMOSTRADO** |
| Afirmación en **lengua natural** (paráfrasis, negación) | «no verificable» | **NO DISPONIBLE** |

### Taxonomía de 7 niveles, implementada

| Nivel | Ejemplo | Estado | Regla |
|-------|---------|--------|-------|
| 1 Existencia | «la figura 712 existe» | **Completo** | el id está en el índice |
| 2 Atributo | «712 tiene raza MINOTAUR» | **Completo** | coincidencia **exacta** |
| 3 Relación | «500 tiene war_buddy con 502» | **Completo** | arista existe, en esa dirección |
| 4 Estado | «712 es FACT» | **Completo** | `certainty` del registro |
| 5 Cantidad | «hay 11.144 figuras» | **Completo** | recuento real del índice |
| 6 Estructura | «500 → 502 → X» | **Completo** | cadena entera, o nada |
| 7 Histórico | «A precede a B» | **Parcial** | requiere años en **ambos** lados |

**38 pruebas sobre datos reales. Ningún dato inventado.**

### Lo que NO hace, y declara

`alcance()` lo dice explícitamente:

* No reconoce paráfrasis: «el sitio fortificado» ≠ «el sitio es de tipo fortress».
* No verifica negaciones.
* **No usa similitud léxica.** Por eso `minotaur` no es `MINOTAUR`, y eso es
  intencionado: normalizar haría que aceptara cosas que el dato no dice.

### Un bug encontrado y corregido durante las pruebas

`historico()` daba `VERIFICADA` cuando A y B estaban **en el mismo año**:
`a < b` es falso, pero la comprobación ingenua lo contaba como bueno. Corregido:
años iguales → `NO_VERIFICADA`, «el orden no es distinguible».

Es exactamente el fallo que este tipo de verificador puede tener: no ser un
modelo semántico y aun así mentir.

---

## F. TEMPORALIDAD

| Mecanismo | ¿Existe? | Dónde |
|-----------|-----------|-------|
| Reloj de juego | **NO** | — |
| Ticks | **NO** | `nucleo.py`: 0 resultados |
| Época / revisión | **NO** | — |
| Snapshots | **NO** | — |
| Timestamps del mundo | **NO** | — |
| `year` de eventos | **Sí** | 1–100. **Tiempo narrado, no del sistema** |
| `seconds72` | **Sí** | Resolución sub-año, también narrado |
| `start_year`/`end_year` en colecciones | **Sí** | 6.544 colecciones, no expuestas |
| `year` en relaciones | **Sí** | 99 valores distintos, 1–100 |
| `dataset_id` | **Sí** | Identidad del **contenido**, no tiempo |

### La distinción que hay que tener clara

`event.year = 50` significa «en la historia narrada, año 50». **No** significa
«el dataset tiene 50 años» ni «este dato tiene 50 años». Son dos ejes distintos, y
mezclarlos es el error que esta misión evita.

---

## G. EVIDENCIA

| Escenario | Resultado |
|-----------|-----------|
| Mismo dataset | La evidencia **sigue siendo válida** |
| Dataset distinto | Es de **otro mundo** → no actual |
| Dataset derivado | **No implementable**: no hay forma de probarlo |
| Estado posterior | **No expresable**: no hay noción de estado posterior |
| Estado desconocido | Se mantiene **desconocido** (`UNKNOWN`) |

### ¿Puede demostrarse la caducidad?

**NO**, y ahora se sabe por qué, no por suposición:

1. **No hay reloj.** Sin una unidad de tiempo del mundo, «caducó» no significa
   nada expresable.
2. **No hay historial de cambios.** `world.sav` es un estado, no un registro: los
   0 resultados de `historical_*` en 208 MB lo confirman.
3. **No hay señal en los raw.** `YEAR`, `TICK`, `CYCLES`, `SEASON`: 0 tags.

**Un `dataset_id` distinto significa «el contenido cambió», no «pasó tiempo».**
Son cosas distintas, y el sistema solo mide la primera.

**No se ha implementado caducidad ficticia.** El mecanismo de `state_version` se
conserva **intacto**: sigue invalidando evidencia de otro dataset, que es lo
único demostrable.

---

## H. ESTADO VIVO

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué representa un dataset? | El contenido **histórico** exportado por el juego |
| ¿Cuándo se genera? | Cuando el jugador exporta y corre el refresco |
| ¿Se puede regenerar? | **Sí**, y de forma reproducible |
| ¿Actualización incremental? | **NO** |
| ¿Snapshots? | **NO** |
| ¿Información de cambios? | **NO** |
| ¿Origen vivo? | `world.sav`, pero **no aporta historial** (0 apariciones) |

**Definición operativa:** «estado actual» = *el contenido del `dataset_id` que
está cargado ahora*. Es una foto, y se puede nombrar con precisión.

### Lo que sí se puede ofrecer

* **Actualidad del contenido**: `dataset_id` + los 17 SHA-256 de sección.
* **Integridad**: las hashes del disco coinciden con el registro.
* **Reconstrucción**: `probar_refresh_cycle.py` (28) demuestra el ciclo completo.

### Lo que no

Ninguna garantía de «los datos de la partida de este momento». El juego exporta
historia; el estado en vivo requiere otro camino, que es fase F del roadmap y
cuya **vía ni está decidida**.

**No se ha implementado polling ni watchers.** No hay necesidad demostrada.

---

## I. CAMBIOS DE CÓDIGO

### Ficheros nuevos (2)

| Fichero | Tipo | Motivo |
|---------|------|--------|
| `00_SOURCE/tools/verificacion_semantica.py` | **Código nuevo** | La reserva que sí se puede cerrar |
| `00_SOURCE/tools/probar_verificacion_semantica.py` | Prueba | 38 pruebas sobre datos reales |

El módulo nuevo **no modifica nada existente**: lee `archivo.indice` y
`archivo.relaciones_de_figura()`, APIs públicas que ya estaban. Se puede borrar
sin que nada más cambie.

> **Aviso de nombre.** Se llama `verificacion_semantica.py` y ya existía un
> `validar_semantica.py` (49 KB) que valida el dataset. **Son distintos y
> coexisten** —comprobado con `import` de ambos—, pero el parecido es una trampa
> para quien lea. `validar_…` comprueba la integridad del dataset;
> `verificar_…` comprueba afirmaciones. Si alguna vez se renombra, este es el
> candidato.

### Producción existente: **NINGUNO MODIFICADO**

```
nucleo.py            CCC48EA67849701A      cargar_legends.py     30140AD617CB2BF0
integrar_legends.py  35649CDCAF75153B      validar_semantica.py  C927FF8B66AC9B8C
actualizar_datos.py  108560E597355329      rutas.py              0EAD547FDF6D1368
servicio.py          D6BD6E5B28A97169      api.py                BB6BDEBBAD5177A1
contrato_ia.py       EB4A4156CBFAF764      ia_estructura.py      BE9FC091EFF534E9
```

### La reserva `Indice.cargar()` (Fase 12)

Se investigó si «todo registro tiene `df_id`» es contrato del generador:

* **Sí lo es.** `integrar_legends.py` genera los JSONL y **siempre** escribe
  `df_id`; las 16 secciones con identidad lo confirman.
* Además, `record_id == sección:df_id` al 100 %.

**Decisión: se mantiene, sin cambios.** Tolerar registros sin `df_id` ocultaría
un dataset mal formado detrás de un índice silenciosamente incompleto. Romperse y
decirlo es el comportamiento correcto.

---

## J. NUEVAS PRUEBAS

| Suite | Tests | Resultado |
|-------|-------|-----------|
| `probar_verificacion_semantica.py` | **38** | **OK** |

Cubren afirmación verdadera, falsa, entidad inexistente, relación inexistente,
afirmación ambigua, dato ausente y determinismo.

**La suite detecta los fallos.** Se rompió `existe()` a propósito:

```
FAIL: test_entidad_inexistente_no_se_verifica
FAIL: test_id_negativo_no_existe
Ran 38 tests — FAILED (failures=2, errors=2)
```

Restaurado y verificado.

### Regresión completa

| Suite | Resultado | Suite | Resultado |
|-------|-----------|-------|-----------|
| `probar_gate_pre_ia` | 15 OK | `probar_banco_ia` | 29 OK |
| `probar_cierre_pre_ia` | 54 OK | `probar_documentacion_indice` | 11 OK |
| `probar_auditoria_final` | 49 OK | `probar_api` | 54 OK |
| `probar_contrato_ia` | 49 OK | `probar_web` | 65 OK |
| `probar_contrato_io` | 48 OK | `probar_actualizacion` | 43 OK |
| `probar_verificacion_estructurada` | 18 OK | `probar_refresh_cycle` | 28 OK |
| `probar_semantica_ia` | 59 OK | `probar_integracion` | 20 OK |
| `probar_riesgos_abc` | 25 OK | `probar_nucleo` | 48 OK |
| `probar_documentacion_ia` | 51 OK | `probar_adversarial` | 39 OK |
| `probar_ia_mock` | 35 OK | `probar_adversarial_nucleo` | 10 OK |
| `probar_ia_contexto` | 39 OK | `test_determinismo` | **DETERMINISTA** |
| `probar_puente_conocimiento` | 52 OK | `verificar_reproducibilidad` | **REPRODUCIBLE** |
| `probar_estado_conocimiento` | 48 OK | `evaluar_banco_ia` | **83/83, 0 fugas** |
| `probar_geografia` | 41 OK | `probar_frontera_inferencia` | 12 OK |
| `probar_frontera_linguistica` | 25 OK | `probar_verificacion_semantica` | **38 OK** |

**0 fallos. Ninguna prueba eliminada. Ninguna cobertura reducida.**

---

## K. LIMITACIONES

### No implementado

| Capacidad | Por qué |
|-----------|---------|
| Caducidad temporal | Requeriría inventar un reloj que no existe |
| Verificación en lengua natural | Requeriría un juez lingüístico |
| Relaciones derivadas de las colecciones | Requiere diseño previo |

### No demostrado

| Capacidad | Por qué |
|-----------|---------|
| Identidad de la fila de relación | `record_id` posicional; `<event>` no resuelve |
| Identidad de la era | 1 sola era; el hash no separa nada |
| `relación → evento` | 0 de 13.192 resuelve, en todas las fuentes |
| Progresión temporal del estado | El dataset es una foto |
| Detección de paráfrasis | Requiere comprensión del lenguaje |

### No disponible en las fuentes

| Capacidad | Evidencia de que no está |
|-----------|--------------------------|
| Reloj / ticks del mundo | `YEAR`, `TICK`, `CYCLES`, `SEASON`: 0 tags |
| Historial en `world.sav` | 0 apariciones de `historical_*` en 208 MB |
| Identificadores de relación | Ninguno en el XML, ni en el mundo, ni en los raw |
| Identificadores de era | Ninguno; 1 sola era con `start_year = -1` |
| Estructuras de guerra | El XML no tiene tabla de guerras |

**Ninguna limitación se ha convertido en PASS.**

---

## L. RESULTADO FINAL

| Área | Resultado | Qué se ha hecho |
|------|-----------|-----------------|
| **Verificación semántica** | **PARCIALMENTE DEMOSTRADO** | 7 niveles deterministas sobre afirmaciones **estructuradas**: 6 completos, 1 parcial. En **lengua natural**: NO DISPONIBLE |
| **Identidad relacional/histórica** | **NO DISPONIBLE** | 8 fuentes investigadas. `record_id` posicional, `<event>` no resuelve, 246 duplicados |
| **Caducidad temporal** | **NO DISPONIBLE** | No hay reloj, ni historial, ni señal en los raw |
| **Estado vivo** | **NO DISPONIBLE** | El mundo descomprimido no contiene historial |

### Las diez preguntas

1. **¿Qué identidades proporciona DF?** 16 secciones con `df_id` del juego,
   estable y único. 3 sin ella, ninguna recuperable.
2. **¿Qué relaciones verificamos?** 10 tipos explícitos + 2 derivadas. La arista
   sí; la fila, no.
3. **¿Qué semántica verificamos?** Afirmaciones estructuradas: 7 niveles, 6
   completos. Lengua natural: ninguna.
4. **¿Qué información histórica existe?** Años, `seconds72`, y las colecciones
   con `outcome`. **Vinculada al estado del sistema: ninguna.**
5. **¿Qué información temporal existe?** Tiempo **narrado**, no del sistema.
6. **¿Qué significa `dataset_id`?** Identidad del **contenido**. No es tiempo.
7. **¿Cuándo es válida una evidencia?** Cuando su `state_version` coincide con
   el `dataset_id` cargado.
8. **¿Puede demostrarse la caducidad?** **No.** No hay reloj ni historial.
9. **¿Qué significa «estado actual»?** El contenido del `dataset_id` cargado.
10. **¿Qué no puede demostrar?** Lo que el XML no dice: identidad de relación,
    orden temporal sin años, guerra, paráfrasis.

---

```
NÚCLEO CON LÍMITES CONOCIDOS
```

Una de las cuatro reservas se cierra parcialmente, y las otras tres quedan
**investigadas hasta el límite de las fuentes**. No se ha añadido una capacidad
ficticia para que la tabla quedara bonita, y sí se ha descubierto una que existía
y no estaba escrita.