# Contrato de datos para la futura IA

Define qué podrá recibir un modelo de lenguaje y con qué garantías.
**Este documento no implementa la IA.** Solo fija el contrato.

> **Estado: la parte conceptual de este contrato ya existía; ahora también es
> código.** Desde la misión del contrato de IA, todo lo que se describe aquí
> está implementado y probado en `dfchron/contrato_ia.py`, con su suite en
> `dfchron/pruebas/probar_contrato_ia.py` (49 pruebas).
>
> - `dfchron/contrato_ia.py` — las cuatro fuentes, las tres dimensiones, la
>   política de divulgación, las conversiones justificadas.
> - `dfchron/ia_conocimiento.py` — el puente que convierte el núcleo en
>   afirmaciones con su permiso (`probar_puente_conocimiento.py`, 52 pruebas).
> - `dfchron/estado_conocimiento.py` — el estado persistente de qué conoce el
>   jugador (`probar_estado_conocimiento.py`, 48 pruebas).
> - `dfchron/pruebas/probar_semantica_ia.py` — **la semántica congelada**,
>   ejecutada sobre las 144 combinaciones reales de las cuatro dimensiones.
>
> Lo que sigue describiendo el **formato**; su pareja
> `AI_PROJECT_CONTEXT.md` describe el **contexto y el trabajo**.
>
> **Y hay pruebas que vigilan estos documentos**:
> `dfchron/pruebas/probar_documentacion_ia.py` y
> `dfchron/pruebas/probar_semantica_ia.py` fallan si lo que aquí se afirma deja
> de ser cierto en el código. Se pusieron porque esta auditoría encontró cuatro
> afirmaciones falsas en estos documentos.

---

## 0-bis. CONCEPTO frente a VALOR SERIALIZADO REAL

> **Este documento es la fuente normativa.** Donde el lenguaje de la misión y el
> código no coinciden, **manda el código**, y aquí queda escrito cuál es cuál.

| CONCEPTO (arquitectura) | VALOR SERIALIZADO REAL (código) | Nota |
|---|---|---|
| `INFERENCE` (razonamiento) | `INTERPRETATION` | `contrato_ia.INFERENCE == "INTERPRETATION"`. Es el único caso en que el nombre y el valor difieren |
| `AFFIRMABLE` (afirmable) | `ALLOWED` | No se renombra. La equivalencia se declara, no se implementa |
| `(no previsto en la misión)` | `CONDITIONAL` | Estado intermedio real, con su propia semántica |
| `DERIVED` | `DERIVED` | Coincide |
| `UNKNOWN` | `UNKNOWN` | Coincide |

`truth_status` y `knowledge_source` comparten el mismo conjunto cerrado, y en
ambos `INFERENCE` significa `INTERPRETATION`.

**Comprobado ejecutando el código**, no de memoria
(`probar_semantica_ia.py::TestValoresCongelados`):

```python
TRUTH_STATUS      == ('FACT', 'DERIVED', 'UNKNOWN', 'INTERPRETATION')
KNOWLEDGE_SOURCES == ('PLAYER_KNOWLEDGE', 'WORLD_KNOWLEDGE',
                       'EXTERNAL_KNOWLEDGE', 'INTERPRETATION')
VISIBILITIES      == ('PLAYER_VISIBLE', 'PLAYER_HIDDEN', 'EXTERNAL')
DISCLOSURES       == ('ALLOWED', 'FORBIDDEN', 'CONDITIONAL')
```

Escribir `"INFERENCE"` en un JSON **sigue siendo un error**, tanto en
`truth_status` como en `knowledge_source`. No se cambió nada para que las
palabras casaran: se documentó la diferencia.

---

## 0. LA TRAMPA DE LOS NOMBRES (léase antes que nada)

> **`INFERENCE` es el nombre de la constante. `INTERPRETATION` es su valor.**

```python
contrato_ia.INFERENCE          # -> "INTERPRETATION"
```

En un JSON vale `"INTERPRETATION"`. Escribir `"INFERENCE"` **lo rechaza el
validador**:

```
truth_status invalido: 'INFERENCE'; knowledge_source invalido: 'INFERENCE'
```

Es la única fuente que se nombra distinto de su valor, y ya costó un error de
documentación. Cuando leas `INFERENCE` en cualquier sitio de este proyecto,
entiende el valor `INTERPRETATION`, salvo que se hable del identificador de
Python.

Lo mismo con la nomenclatura de la misión, que usa `AFFIRMABLE`:

| En la misión | En este proyecto |
|---|---|
| `AFFIRMABLE` | `ALLOWED` |
| `FORBIDDEN` | `FORBIDDEN` |
| (no previsto) | `CONDITIONAL` — estado intermedio real |

Se conserva la nomenclatura del proyecto: no se cambian nombres por estética.
`CONDITIONAL` **no** es inventado; significa "puedes *mencionar*, no *afirmar*",
y existe porque sin él una pista se convertía en una afirmación tajante.

---

---

## 0. La regla y sus tres dimensiones

> **La verdad de un dato y el permiso para revelarlo son cosas diferentes.**

Una afirmación va con **tres dimensiones independientes**. No son campos que
se rellenen por costumbre: cada uno responde a una pregunta distinta, y
confundirlos es el error que destruye la frontera.

| Dimensión | Pregunta que responde | Valores |
|---|---|---|
| `truth_status` | ¿Es verdad? | `FACT`, `DERIVED`, `UNKNOWN`, `INFERENCE` |
| `knowledge_source` | ¿De dónde viene? | `PLAYER_KNOWLEDGE`, `WORLD_KNOWLEDGE`, `EXTERNAL_KNOWLEDGE`, `INFERENCE` |
| `visibility` | ¿Lo conoce el jugador? | `PLAYER_VISIBLE`, `PLAYER_HIDDEN`, `EXTERNAL` |
| `disclosure` | ¿Se puede decir? | `ALLOWED`, `FORBIDDEN`, `CONDITIONAL` |

Lo crítico: **`FACT` no implica `PLAYER_VISIBLE`**. Se comprobó ejecutando el
código: un `FACT` de `WORLD_KNOWLEDGE` con `visibility: PLAYER_HIDDEN` es
perfectamente válido como dato, y `puede_revelarse()` devuelve `False`.

Y **`FACT` no implica `ALLOWED`**. Son dos preguntas distintas:

| Combinación | ¿Verdad? | ¿Revelable? | Qué significa |
|---|---|---|---|
| `FACT` + `PLAYER_VISIBLE` + `ALLOWED` | sí | **sí** | Se puede afirmar |
| `FACT` + `PLAYER_HIDDEN` + `FORBIDDEN` | sí | **no** | Verdadero y callado |
| `FACT` + `PLAYER_HIDDEN` + `ALLOWED` | sí | **no** | No revelable sin pista |
| `DERIVED` + `PLAYER_VISIBLE` + `ALLOWED` | derivado | sí, como consejo | **Nunca se convierte en `FACT`** |
| `UNKNOWN` + `PLAYER_VISIBLE` + `ALLOWED` | no consta | **no** | «No consta» es la respuesta |

### `truth_status` NO decide la divulgación

El lector tiene que tener esto presente porque es la confusión que destruye la
frontera:

* `truth_status` responde a **¿es verdad?**
* `disclosure` responde a **¿se puede decir?**

Que el primer campo valga `FACT` no dice absolutamente nada del segundo. Para
que un dato salga al jugador hay que mirar `disclosure`, y además `visibility`.

### Las cuatro categorías (`knowledge_source`)

| Fuente | Qué es | Dónde viene |
|---|---|---|
| `PLAYER_KNOWLEDGE` | Lo que el juego hizo disponible al jugador | Dataset + estado del jugador |
| `WORLD_KNOWLEDGE` | Verdad completa del mundo que escribió el juego | `legends.xml` / `legends_plus.xml` |
| `EXTERNAL_KNOWLEDGE` | Reglas del juego, wiki, raws, manuales | Fuera de la partida |
| `INFERENCE` (= `INTERPRETATION`) | Conclusión producida al razonar | Se produce, no se copia |

El dataset contiene `WORLD_KNOWLEDGE` con certeza `FACT`/`DERIVED`.
**No contiene** `EXTERNAL_KNOWLEDGE`: esto es **una** partida, no el mundo de
Dwarf Fortress.

### `WORLD_KNOWLEDGE` no se convierte en `PLAYER_KNOWLEDGE`

Que el jugador descubra algo cambia su `visibility`. **No cambia de dónde viene
el dato.** Por eso esta combinación es legal:

```json
{"knowledge_source": "WORLD_KNOWLEDGE", "visibility": "PLAYER_VISIBLE"}
```

Significa: la verdad la escribió el juego, y el jugador ya lo ha visto. La
conversión a `PLAYER_KNOWLEDGE` sería una **reescritura del origen**, y no ocurre
sola: ocurre cuando alguien lo decide y queda escrito, en
`dfchron/estado_conocimiento.py`.

Y al revés tampoco: `WORLD_KNOWLEDGE` con `no_descubierto=True` +
`PLAYER_VISIBLE` **es rechazado**. No puede ser visible lo que nadie ha visto.

### `EXTERNAL_KNOWLEDGE` no es `WORLD_KNOWLEDGE`

Es la frontera que más caro sale cuando se cruza:

```text
EXTERNAL_KNOWLEDGE: "Las fortalezas goblin pueden contener determinados enemigos."
                     ✓ explica una mecánica

NO PERMITE:         "Tu fortaleza contiene 37 goblins."
                     ✗ sería afirmar el estado de ESTA partida con la wiki
```

La wiki explica **las reglas**. El dataset representa **el estado de esta
partida**. Son cosas distintas y el contrato impide mezclarlas:

* `EXTERNAL_KNOWLEDGE` **solo** puede tener `visibility: EXTERNAL`.
* `EXTERNAL_KNOWLEDGE` **no** puede ser `FACT` sobre esta partida.
* `puede_usarse_para_razonar()` devuelve `False` para lo externo: no puede
  alimentar razonamiento sobre **esta** partida.

La asimetría es deliberada: lo externo **sí** puede mostrarse (explica una
mecánica), pero **no** puede usarse para deducir el estado concreto.

### `INFERENCE` nunca sube a `FACT`

Una inferencia es una conclusión, y una conclusión no es una fuente.
`INFERENCE` + `FACT` es rechazado por el validador.

Una inferencia **puede mostrarse** como posibilidad
(`puede_revelarse() == True`), pero **nunca se enuncia como hecho**
(`puede_afirmarse_como_hecho() == False`). Esa separación existe porque sin ella
un "probablemente" se convertía en una afirmación tajante.

Ejemplo de las cuatro operando juntas:

```text
PLAYER_KNOWLEDGE:   "Existe una fortaleza goblin al norte."
EXTERNAL_KNOWLEDGE: "Las fortalezas goblin suelen implicar riesgos."
INFERENCE:          "Probablemente debas prepararte para una posible amenaza."
```

La inferencia **no** dice que haya una amenaza. Dice que es posible. Ese matiz es
la diferencia entre una IA que razona y una que afirma cosas que no sabe.

### El formato completo

```json
{
  "claim": "Existe una veta de diamantes en 112,20,45.",
  "truth_status": "FACT",
  "knowledge_source": "WORLD_KNOWLEDGE",
  "visibility": "PLAYER_HIDDEN",
  "disclosure": "FORBIDDEN",
  "evidence": [
    {
      "entidad": "sitio",
      "df_id": "112",
      "datos_utilizados": ["type"],
      "funcion": "nucleo.Archivo.ficha_sitio",
      "fuente": "legends.xml"
    }
  ],
  "inference": false
}
```

Se conserva `certainty` como alias de `truth_status` en el formato de
evidencia heredado de la sección 4: no se rompe lo que ya existía.

### Ejemplo obligatorio: el secreto de los diamantes

Este es **el** caso que resume el contrato entero. sale de
`contrato_ia.ejemplo_secreto()`, y por eso no puede desincronizarse del código.

```json
{
  "claim": "Existe una veta de diamantes en 112,20,45.",
  "truth_status": "FACT",
  "knowledge_source": "WORLD_KNOWLEDGE",
  "visibility": "PLAYER_HIDDEN",
  "disclosure": "FORBIDDEN",
  "no_descubierto": true,
  "evidence": [{
    "entidad": "sitio", "df_id": "112", "datos_utilizados": ["type"],
    "funcion": "nucleo.Archivo.ficha_sitio", "fuente": "legends.xml"
  }]
}
```

Qué hace el sistema con ese dato:

| Pregunta | Respuesta |
|---|---|
| ¿Existe de verdad? | **Sí.** El juego lo escribió |
| ¿Puede razonar con él por dentro? | **Sí** |
| ¿Puede decírselo al jugador? | **No** |
| ¿Puede enunciarlo como hecho? | **No** |
| ¿Por qué? | `disclosure: FORBIDDEN` |

Si el jugador pregunta dónde hay diamantes, el sistema **no** puede responder
*"Hay diamantes exactamente en 112, 20, 45."*. Puede producir una respuesta
indirecta o un consejo permitido — **nunca la coordenada**, aunque el modelo
hable con absoluta seguridad.

Y esto **no depende de que el modelo se porte bien**. `puede_revelarse()` es una
función que devuelve `False`; el dato no llega a una fase donde un LLM pueda
filtrarlo. La protección es de arquitectura y de datos, no de instrucciones.

> Si en algún momento el jugador descubre la veta, la transición la escribe
> alguien de forma explícita con `convertir(a, "revelar", motivo)`. Que alguien lo
> pida **no** cambia nada por sí solo.

### `PLAYER_KNOWLEDGE`: qué es y de dónde sale

`PLAYER_KNOWLEDGE` es información **que el juego hizo disponible al jugador**. En
el dataset no existe ningún campo que lo diga, y esa es una limitación real:

> **`legends.xml` no registra qué descubrió el jugador.** No hay marca, ni campo,
> ni fecha de descubrimiento en ningún fichero.

Por eso `PLAYER_KNOWLEDGE` **no se deduce de los datos**: se registra aparte, en
`dfchron/estado_conocimiento.py`, como estado de ejecución:

```json
{
  "schema_version": 1,
  "dataset_id": "v1-04170363943d4ba1",
  "knowledge": {
    "campo|sitio:87:coordenadas": {
      "tipo": "sitio", "df_id": "87", "campo": "coordenadas",
      "motivo": "el jugador minimizó el mapa"
    }
  }
}
```

Lo que esa capa garantiza, y que la futura IA debe respetar:

| Regla | Por qué |
|---|---|
| Nunca se autodescubre | Que el dato exista, la web lo muestre o una consulta lo devuelva **no** lo marca |
| Vive fuera del dataset | Es estado, no historia. Se borra sin tocar un byte histórico |
| Es determinista | Sin timestamps, sin UUID, sin `random` |
| Va ligado a `dataset_id` | Si el dataset cambia, se levanta `DatasetDistinto` y no se continúa en silencio |
| No cambia la divulgación | Marcar como conocido **no** quita un `FORBIDDEN` |

Granularidad: hay identidad estable en `figura`, `sitio`, `entidad`, `artefacto`
y `evento`, y a dos niveles (entidad y campo). **Las relaciones no tienen
identificador estable en el dataset**, así que no se inventó uno: figura en
`TIPOS_NO_SOPORTADOS` con su motivo.

Detalle completo en `00_SOURCE/ai_knowledge_state_report.md`.

### Combinaciones que el contrato RECHAZA

Están prohibidas por `dfchron/contrato_ia.py`, con prueba para cada una:

| Combinación | Por qué |
|---|---|
| `EXTERNAL_KNOWLEDGE` + `FACT` | Afirmaría como verdad algo que no viene de este mundo |
| `EXTERNAL_KNOWLEDGE` + `PLAYER_VISIBLE` | Lo externo no describe esta partida |
| `INFERENCE` + `FACT` | Una conclusión no es una fuente |
| `WORLD_KNOWLEDGE` + `no_descubierto` + `PLAYER_VISIBLE` | No puede ser visible lo que no se ha visto |
| Afirmación `FACT` sin evidencia | «Parece lógico» no es una fuente |

### Y una que NO está prohibida (esta auditoría lo corrigió)

| Combinación | Realidad |
|---|---|
| `PLAYER_HIDDEN` + `ALLOWED` | **Se construye sin error.** No está prohibida: es *no revelable* |

La diferencia importa y antes no estaba escrita:

* **rechazada** = `afirmacion()` lanza `ContratoInvalido`. No existe.
* **no revelable** = existe y es válida, pero `puede_revelarse()` devuelve
  `False`. Puede usarse para razonar por dentro.

`PLAYER_HIDDEN` + `ALLOWED` es lo segundo. Solo se abre con `CONDITIONAL` **y**
`pista_permitida=True`; con `ALLOWED` a secas no se revela nunca. La protección
sigue intacta; lo que estaba mal era la etiqueta.

### Las tres preguntas, y por qué no se contestan con la misma

| Pregunta | Función | Secreto |
|---|---|---|
| ¿Puedo razonar con esto por dentro? | `puede_usarse_para_razonar()` | **Sí** |
| ¿Puedo mostrárselo tal cual? | `puede_revelarse()` | No |
| ¿Puedo enunciarlo como hecho? | `puede_afirmarse_como_hecho()` | No |

Razonar con un secreto es legítimo y a veces necesario; contarlo, no. De ahí
que sean tres funciones y no una.

`violacion(a)` explica por qué no puede revelarse, para diagnóstico. No
contiene rutas ni datos del sistema de ficheros.

---

## 0-ter. SEMÁNTICA CONGELADA DE LAS CUATRO DIMENSIONES

Esta sección es **normativa**. Las cuatro dimensiones, una por una.

### `truth_status` — ¿es verdad?

| VALOR REAL | Qué significa | Qué NO significa |
|---|---|---|
| `FACT` | El sistema tiene evidencia suficiente para tratar la afirmación como un hecho del estado representado | No significa que sea visible ni que se pueda decir |
| `DERIVED` | Conclusión obtenida por razonamiento a partir de hechos o evidencia | No se convierte nunca en `FACT` por la puerta de `convertir()` |
| `UNKNOWN` | El sistema **no** tiene evidencia suficiente para afirmar el dato | No es un vacío: es una respuesta válida y preferible a suponer |
| `INTERPRETATION` (= `INFERENCE`) | Resultado del razonamiento, con su evidencia de base | No es una fuente: no puede enunciarse como hecho |

`DERIVED` e `INTERPRETATION` se distinguen así: `DERIVED` es un cálculo
determinista sobre datos (el núcleo lo produce y lo etiqueta);
`INTERPRETATION` es una conclusión que además puede ser de un agente. Los dos se
difieren de `FACT`, pero la frontera real está en
`puede_afirmarse_como_hecho()`, que exige `FACT` **y** no `CONDITIONAL`.

### `knowledge_source` — ¿de dónde viene?

| VALOR REAL | Qué es | Dónde viene | Razonar sobre esta partida |
|---|---|---|---|
| `PLAYER_KNOWLEDGE` | Lo que el juego hizo disponible al jugador | Dataset + `estado_conocimiento.py` | Sí |
| `WORLD_KNOWLEDGE` | La verdad completa del mundo que escribió el juego | `legends.xml` / `legends_plus.xml` | Sí |
| `EXTERNAL_KNOWLEDGE` | Wiki, raws, manuales, documentación, mecánicas | Fuera de la partida | **No** |
| `INTERPRETATION` (= `INFERENCE`) | Se produce, no se copia | Razonamiento | Sí |

`EXTERNAL_KNOWLEDGE` es la única fuente que **no** puede razonar sobre esta
partida: `puede_usarse_para_razonar()` devuelve `False` siempre. Sí puede
*mostrarse*, porque explica reglas.

### `visibility` — ¿lo conoce el jugador?

| VALOR REAL | Pregunta que responde |
|---|---|
| `PLAYER_VISIBLE` | ¿Lo ve el jugador? |
| `PLAYER_HIDDEN` | ¿No lo ha visto todavía? |
| `EXTERNAL` | No describe esta partida |

`visibility` **no** responde a «¿puede la IA revelarlo?». Para eso está
`disclosure`. Nunca se sustituyen entre sí.

### `disclosure` — ¿se puede decir?

| VALOR REAL | Significado exacto |
|---|---|
| `ALLOWED` | Divulgable, sujeto a `visibility` (ver la matriz) |
| `FORBIDDEN` | **Nunca** comunicable directamente al jugador |
| `CONDITIONAL` | Divulgable **solo** con `pista_permitida is True`, y solo como mención |

`AFFIRMABLE` (concepto de la misión) ≈ `ALLOWED` (valor real). **No se renombra
el identificador.**

---

## 0-quater. MATRIZ DE COMBINACIONES (medida, no supuesta)

Ejecutada sobre las **144 combinaciones** reales (`4 × 4 × 3 × 3`). Lo que
sigue son las filas que la misión exige; el resto queda cubierto por las
invariantes de `probar_semantica_ia.py`.

**Las categorías se mezclan a propósito y no deben confundirse:**

| Categoría | Significado |
|---|---|
| **NO VÁLIDA** | `afirmacion()` lanza `ContratoInvalido`. La combinación no existe |
| **VÁLIDA** | Se construye sin error |
| **DIVULGABLE** | `puede_revelarse()` devuelve `True` |
| **CONDICIONAL** | Divulgable solo si se cumple una condición externa (`pista_permitida`) |

> **Válida no es lo mismo que divulgable.** Es la distinción que este contrato
> existe para sostener, y la que hace que `PLAYER_HIDDEN + ALLOWED` no sea un
> error sino un dato correcto que todavía no se puede contar.

| truth_status | source | visibility | disclosure | Resultado |
|---|---|---|---|---|
| `FACT` | `PLAYER_KNOWLEDGE` | `PLAYER_VISIBLE` | `ALLOWED` | Válida · **divulgable** · afirmable |
| `FACT` | `WORLD_KNOWLEDGE` | `PLAYER_VISIBLE` | `ALLOWED` | Válida · **divulgable** · afirmable *(solo si no lleva `no_descubierto=True`)* |
| `FACT` | `WORLD_KNOWLEDGE` | `PLAYER_HIDDEN` | `ALLOWED` | Válida · **no divulgable** · razonable |
| `FACT` | `WORLD_KNOWLEDGE` | `PLAYER_HIDDEN` | `FORBIDDEN` | Válida · **no divulgable** · razonable · **el secreto canónico** |
| `FACT` | `EXTERNAL_KNOWLEDGE` | `EXTERNAL` | `ALLOWED` | **NO VÁLIDA** — lo externo no puede ser `FACT` de esta partida |
| `DERIVED` | `PLAYER_KNOWLEDGE` | `PLAYER_VISIBLE` | `ALLOWED` | Válida · divulgable · **no afirmable** (nunca sube a `FACT`) |
| `DERIVED` | `WORLD_KNOWLEDGE` | `PLAYER_HIDDEN` | `FORBIDDEN` | Válida · no divulgable · razonable |
| `UNKNOWN` | cualquiera | cualquiera | cualquiera | Válida (salvo `EXTERNAL_KNOWLEDGE` con visibility distinta de `EXTERNAL`) · **nunca divulgable** · nunca afirmable |
| `INTERPRETATION` | cualquiera | `PLAYER_VISIBLE` | `ALLOWED` | Válida · divulgable · **no afirmable** |
| `INTERPRETATION` | cualquiera | `PLAYER_VISIBLE` | `CONDITIONAL` | Válida · **no divulgable** (la rama `INFERENCE` solo acepta `ALLOWED`) |
| `INTERPRETATION` | cualquiera | cualquiera | `FORBIDDEN` | Válida · no divulgable · razonable — **ver la decisión de abajo** |

### Invariantes que se cumplen en las 144

| Invariante | Por qué importa |
|---|---|
| `FORBIDDEN` **nunca** es divulgable, en ninguna combinación | `FORBIDDEN` manda sobre las demás dimensiones |
| `UNKNOWN` **nunca** es divulgable, en ninguna combinación | Un hueco no es una afirmación |
| `visibility=PLAYER_HIDDEN` con `disclosure != CONDITIONAL` **nunca** es divulgable | Aunque le cuelgues `pista_permitida=True` |
| `EXTERNAL_KNOWLEDGE` **nunca** razona sobre esta partida | La wiki explica reglas, no hechos de tu partida |
| Solo `FACT`, y nunca `CONDITIONAL`, se afirma como hecho | La mención no es la afirmación |

### Combinaciones NO VÁLIDAS (rechazadas, no «no divulgables»)

| Combinación | Por qué |
|---|---|
| `EXTERNAL_KNOWLEDGE` + `visibility != EXTERNAL` | Lo externo no describe esta partida |
| `EXTERNAL_KNOWLEDGE` + `FACT` | Afirmaría como verdad algo que no viene de este mundo |
| `knowledge_source = INFERENCE` + `truth_status = FACT` | Una conclusión no es una fuente |
| `WORLD_KNOWLEDGE` + `no_descubierto=True` + `PLAYER_VISIBLE` | No puede ser visible lo que no se ha visto |
| `disclosure_alias = ALLOWED` + `disclosure = FORBIDDEN` | Registro que se contradice a sí mismo |
| Afirmación sin evidencia (`≠ UNKNOWN`) | «Parece lógico» no es una fuente |
| `UNKNOWN` sin evidencia y sin `motivo` | Un vacío sin explicación no dice nada |
| Evidencia sin `df_id` | Procedencia no rastreable |
| Evidencia de fuente de estado sin `funcion` | No se sabe qué consulta del núcleo la produjo |

---

## 0-quin. `CONDITIONAL`: SU SEMÁNTICA REAL

Determinada leyendo `puede_revelarse()`, **no inventada**.

### Qué significa

> **Se puede MENCIONAR, no AFIRMAR.**

Es el único estado que autoriza a decir algo que el jugador todavía no sabe y,
aun así, impide que eso se convierta en una afirmación tajante.

### Qué condición necesita

**Dos cosas a la vez**, y solo en la rama `visibility == PLAYER_HIDDEN`:

```python
a["disclosure"] == c.CONDITIONAL  and  a.get("pista_permitida") is True
```

* No basta `CONDITIONAL` sin pista: sigue bloqueado.
* No basta la pista sin `CONDITIONAL`: `ALLOWED` + `pista_permitida` **no**
  revela nada.
* La pista debe ser **el booleano `True`**: `1`, `"si"` y `"True"` **no** abren
  la puerta. Se comprueba con `is True`, no con *truthiness*.

### Dónde se evalúa

En `puede_revelarse()`, en la rama `visibility == PLAYER_HIDDEN`. Con
`PLAYER_VISIBLE`, el valor `CONDITIONAL` **no abre nada**: si el jugador ya lo
sabe, corresponde `ALLOWED`.

### Qué ocurre si la condición se cumple

| Función | Resultado |
|---|---|
| `puede_revelarse()` | `True` — se puede mencionar |
| `puede_afirmarse_como_hecho()` | **`False`** — nunca se enuncia como hecho |
| `puede_usarse_para_razonar()` | `True` |

### Qué ocurre si no se cumple

`puede_revelarse()` devuelve `False` y `violacion(a)` lo explica. La afirmación
sigue siendo **válida**: es una pista que aún no se ha autorizado.

### ¿La condición es `disclosure_alias`?

**No.** Son dos campos distintos con dos papeles distintos: `pista_permitida`
abre la divulgación; `disclosure_alias` solo se comprueba en `validar()` y no
participa de esta decisión.

### `CONDITIONAL` = DEFINIDO PARCIALMENTE

| Parte | Estado |
|---|---|
| Qué hace, y con qué condición | **Determinado** por el código, y congelado aquí |
| **Quién autoriza `pista_permitida`, y con qué criterio** | **PENDIENTE — no está decidido** |

Esa autorización **no se inventa**. De hecho se comprueba en las pruebas:
**ningún módulo de producción del proyecto pone `pista_permitida=True`**. Es
decir, `CONDITIONAL` existe, está probado, y **hoy no se abre en producción**.
Quién lo autorice, y con qué criterio, es una decisión que corresponde a la
misión del contrato de entrada/salida.

---

## 0-sext. `disclosure_alias`: DECISIÓN DE AUDITORÍA

La misión pedía decidir si es (A) capacidad futura deliberada, (B) campo
muerto, (C) campo requerido pendiente, u (D) otra cosa.

**Decisión: es una guarda de coherencia (D), y se conserva.**

| Pregunta | Respuesta, verificada en el código |
|---|---|
| **¿Qué es?** | Un campo **opcional** que `validar()` consulta para detectar un registro que se contradice a sí mismo: `disclosure_alias == ALLOWED` junto a `disclosure == FORBIDDEN` |
| **¿Quién lo rellena?** | **Nadie.** Ningún módulo de `dfchron/` lo produce. Se comprueba con una prueba que lee el código |
| **¿Quién lo consume?** | **Nadie.** No aparece en `puede_revelarse()`, ni en `convertir()`, ni en `contexto_obligatorio()`, ni en ninguna de las cuatro dimensiones |
| **¿Es una quinta dimensión?** | **No.** Su valor **no** se valida contra `DISCLOSURES`: hasta `"basura"` pasa sin error. Solo se comprueba la contradicción concreta |
| **¿Se elimina?** | **No.** No se elimina, no se rellena, no se le inventan consumidores |
| **¿Queda pendiente?** | **Sí.** Su población depende de un productor de datos externos que todavía no existe |

Por qué no es (B), un campo muerto sin más: **sí hace trabajo hoy**. Rechaza una
clase de entrada incoherente, sin coste y sin riesgo. Lo que no tiene es
*consumidor*, y eso es exactamente lo que queda declarado como pendiente.

> No se ha cambiado nada en el contrato para darle semántica: hacerlo sería
> inventar el comportamiento.

---

## 0-sept. `INFERENCE` + `FORBIDDEN`: DECISIÓN DE AUDITORÍA

**Comportamiento real, verificado:** la combinación **no se rechaza**. Es
válida, no es divulgable, y sí se puede usar para razonar.

Eso corresponde a la lectura **(A)**: *la inferencia puede existir internamente,
pero no divulgarse*.

**Por qué (A) y no las demás, según el código:**

* `puede_revelarse()` comprueba `disclosure == FORBIDDEN` **antes** de mirar
  `truth_status`. `FORBIDDEN` es el primer filtro y vale para cualquier
  `truth_status`, incluido `INTERPRETATION`.
* **(B)**, «inválida como afirmación», implicaría que el contrato no puede
  guardar conclusiones internas. Contradice el diseño: razonar con datos ocultos
  es legítimo, y por eso existe `puede_usarse_para_razonar()`.
* **(C)**, «puede existir pero necesita transformación antes de divulgarse»,
  describe algo que el código **no** implementa: no hay ninguna función que
  transforme una inferencia para volverla divulgable.
* **(D)** no aplica: no hay comportamiento especial registrado para inferencias.

**Consecuencia congelada:** `INTERPRETATION` + `FORBIDDEN` es una conclusión
interna que jamás sale. Y no se degrada: sigue siendo `INFERENCE`, no `UNKNOWN`.

> **Queda para la siguiente misión, y aquí NO se decide:** si una inferencia
> llega alguna vez a la frontera del jugador, ¿debe transformarse en una
> afirmación `DERIVED` con su evidencia visible, o seguir siendo una inferencia
> mostrada como posibilidad? El código actual solo contempla la segunda. La
> primera **no está implementada** y no se inventa.

---

## 0-oct. PERSPECTIVA: ESTADO Y LÍMITE ACTUALES (§18)

Auditado: **el contrato actual NO soporta múltiples perspectivas.** No hay
campo de agente, ni de observador, ni `perspective`. No se añade ninguno.

La estructura de hoy es de **una sola perspectiva, la del jugador**:

```text
                 ┌─────────────────────┐
                 │       MUNDO         │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
 PLAYER_KNOWLEDGE    WORLD_KNOWLEDGE   EXTERNAL_KNOWLEDGE
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                     TRUTH / EVIDENCE
                            ▼
                       VISIBILITY
                            ▼
                     DISCLOSURE POLICY
                            ▼
              ALLOWED      │      FORBIDDEN
                            ▼
                        INFERENCE
```

Extensión **documentada, no implementada** (queda para una misión posterior):

```text
 MUNDO
  ├── PLAYER_KNOWLEDGE
  ├── DWARF_KNOWLEDGE      (no implementado)
  ├── GOBLIN_KNOWLEDGE     (no implementado)
  └── ...
```

Cada agente tendría su propio `knowledge`, `visibility` y `disclosure`. **Lo que
haría falta y hoy no existe:** una clave de agente en el estado
(`estado_conocimiento.py` es de un solo jugador) y una noción de «divulgable
*para este* agente» en lugar de «divulgable *al* jugador».

**Límite explícito:** esta misión **no** implementa IA de NPC y **no** añade
campos futuros al contrato actual. Se documenta la dirección; nada más.

---

## 0-nov. EL PROBLEMA `EXTERNAL`: DECISIÓN DE AUDITORÍA

> **Prioridad de esta misión.** Era un agujero real, no una duda teórica.

### Comportamiento actual (ANTES)

`visibility=EXTERNAL` **esquivaba** la rama `PLAYER_HIDDEN` de
`puede_revelarse()`. Como el único filtro de lo oculto es `vis ==
PLAYER_HIDDEN`, marcar un secreto como `EXTERNAL` lo sacaba del filtro:

```python
WORLD_KNOWLEDGE + FACT + PLAYER_HIDDEN + ALLOWED → no revelable
WORLD_KNOWLEDGE + FACT + EXTERNAL      + ALLOWED → REVELABLE, AFIRMABLE
```

### Semántica documentada

| Fuente | `visibility` | Qué significa |
|---|---|---|
| `EXTERNAL_KNOWLEDGE` | `EXTERNAL` | «No describe esta partida» |
| `PLAYER_KNOWLEDGE` | `PLAYER_VISIBLE` | «El jugador lo ve» |
| `WORLD_KNOWLEDGE` | `PLAYER_VISIBLE` / `PLAYER_HIDDEN` | Estado de esta partida |

### Contradicción

**Sí, existía, y era grave.** `WORLD_KNOWLEDGE` significa, por definición, «la
verdad de ESTE mundo». Combinarlo con `visibility=EXTERNAL`, que significa «no
describe esta partida», es una **contradicción semántica**: se afirmaba que el
dato viene del mundo y a la vez que no viene del mundo.

Y tenía consecuencia práctica: `puede_afirmarse_como_hecho()` devolvía `True`,
así que un secreto reconstruido así pasaba a ser una afirmación enunciable al
jugador. La frontera de divulgación se eludía **cambiando una etiqueta**.

### Opciones consideradas

| Opción | Descripción | Veredicto |
|---|---|---|
| A | Simétrica: `visibility=EXTERNAL` ⟺ `knowledge_source=EXTERNAL_KNOWLEDGE` | **ELEGIDA** |
| B | Tratar `EXTERNAL` como equivalente a `PLAYER_HIDDEN` | Rechazada: rompe la wiki, que sí es `EXTERNAL` y sí debe poder mostrarse |
| C | No tocar, solo documentar | Rechazada: deja un agujero abierto |
| D | Eliminar el valor `EXTERNAL` | Rechazada: destruiría la semántica de las mecánicas |

### Decisión

> **`visibility=EXTERNAL` significa exactamente «esto no describe esta partida».
> Solo `EXTERNAL_KNOWLEDGE` puede declararlo.**

La regla 1 de `validar()` era de una sola dirección; ahora es **bidireccional**
(regla 3-bis):

```python
if vis == EXTERNAL and ks != EXTERNAL_KNOWLEDGE:
    e.append("EXTERNAL_KNOWLEDGE y visibility EXTERNAL son la misma cosa: "
             "solo lo externo puede declarar que no describe esta partida")
```

**Efecto sobre producción: ninguno.** Se comprobó que ningún módulo del proyecto
construye `WORLD_KNOWLEDGE`/`PLAYER_KNOWLEDGE`/`INFERENCE` con
`visibility=EXTERNAL`: el puente usa `PLAYER_HIDDEN` + `FORBIDDEN` para todo lo
del núcleo, y `EXTERNAL` solo aparece junto a `EXTERNAL_KNOWLEDGE`. **La
combinación era construible, pero no se usaba.**

**Lo que sí se conserva:** `EXTERNAL_KNOWLEDGE + EXTERNAL` sigue siendo legal y
divulgable. Explicar una mecánica no se penaliza por el cierre.

### Consecuencia para la IA del jugador

`WORLD_KNOWLEDGE + EXTERNAL` ya no es una vía para convertir un secreto en
afirmación.

**Verificado por:** `test_external_ya_no_esquiva_la_frontera` y
`test_external_knowledge_conserva_external` (`probar_semantica_ia.py`).

---

## 0-dec. EL CONTRATO DE ENTRADA Y SALIDA

> **Fuente normativa.** Implementado en `dfchron/ia_contrato.py`, con 54 pruebas
> en `dfchron/pruebas/probar_contrato_io.py`.
>
> **Lo que NO incluye: el modelo.** No hay cliente, ni SDK, ni endpoint, ni
> prompt, ni llamada a la red.

### Principio

```text
SABER   ≠ UTILIZAR ≠ REVELAR
RAZONAR ≠ AFIRMAR  ≠ REVELAR
```

El modelo es una **consumidora** de esta arquitectura, nunca su autoridad. No
decide verdad, ni visibilidad, ni divulgación, ni procedencia, ni permisos.

### La decisión de seguridad central

> **El modelo NUNCA recibe un dato `FORBIDDEN`.** No «no debe usarlo»: **no lo
> recibe**. Mandarle un secreto a un proveedor externo ya es divulgarlo.

Por eso `FORBIDDEN` no aparece en el contexto, **ni en modo razonamiento**. Lo
que queda para razonar con lo oculto lo hace el sistema, de forma determinista,
antes de que el modelo intervenga.

### ENTRADA — el objeto `ContextoIA`

```json
{
  "schema": "io-1",
  "agente": "PLAYER",
  "modo": "razonamiento",
  "pregunta": "¿Qué debería hacer con esta fortaleza?",
  "claims": [
    {
      "ref": "c0",
      "claim": "Existe una fortaleza goblin al norte.",
      "truth_status": "FACT",
      "knowledge_source": "PLAYER_KNOWLEDGE",
      "visibility": "PLAYER_VISIBLE",
      "disclosure": "ALLOWED",
      "evidence": [
        {"entidad": "sitio", "df_id": "87",
         "datos_utilizados": ["type"],
         "funcion": "nucleo.Archivo.ficha_sitio",
         "fuente": "legends.xml"}
      ]
    }
  ],
  "contexto": { "...limitaciones fijas, siempre presentes..." }
}
```

**El modelo NO recibe datos crudos.** Ni JSONL, ni tablas, ni rutas, ni
estructuras internas. Recibe **unidades semánticas** (`CLAIM` + `EVIDENCE`) con
sus cuatro campos normativos.

**No hay campos duplicados por derivación.** No existe `divulgable` ni
`es_secreto`: se deducen de `disclosure` + `visibility`. Un campo más sería una
segunda verdad, capaz de contradecir a la primera.

**No viajan los campos de la casa.** `no_descubierto`, `pista_permitida` y
`conversion` se omiten: son internos, y el modelo no puede actuar sobre ellos.

**Minimización:** el sistema **no** incluye `WORLD_KNOWLEDGE` por sistema. Si el
jugador ya conoce el dato, basta el claim de `PLAYER_KNOWLEDGE`. Cada afirmación
que sobra es una vía de más por la que colarse un secreto.

### Los dos modos

| Modo | Qué es | `FORBIDDEN` | `UNKNOWN` | Oculto sin pista |
|---|---|---|---|---|
| `razonamiento` | Lo que puede leer para **formular** | **NO** | sí | **NO** |
| `respuesta` | Lo que puede **decirse** | **NO** | **NO** | **NO** |

`respuesta` es subconjunto estricto de `razonamiento`. Se implementa como **una
sola estructura con un filtro por modo**, no como dos estructuras: el filtrado
ocurre en `entra_en_contexto()` y es determinista. Dos estructuras obligarían a
mantener sincronizadas dos copias de la misma verdad.

### Identidad del agente

| Agente | Estado |
|---|---|
| `PLAYER` | **Implementado** |
| `DWARF`, `GOBLIN`, `OTHER_AGENT` | **NO implementados** |

`agente` viaja en la consulta y se valida contra la lista de conocidos. La puerta
está abierta sin romper `PLAYER_KNOWLEDGE`, y añadir un agente es una constante
más.

> **Supuesto actual, declarado:** el permiso de una afirmación **no depende del
> agente**. No se resuelve aquí si debería. Abrirlo exigiría una dimensión nueva
> (`knowledge_owner`), que esta misión tiene prohibido inventar.

---

## 0-die. SALIDA, VALIDACIÓN Y SEGURIDAD

### SALIDA — el objeto `RespuestaIA`

```json
{
  "answer": "Podría ser útil explorar la zona norte.",
  "claims": [
    {
      "texto": "Podría ser útil explorar la zona norte.",
      "tipo": "ADVICE",
      "soporte": ["c0", "c1"]
    }
  ],
  "confidence": "media"
}
```

### El `answer` NO se entrega. Decisión de la auditoría de la frontera

Este párrafo **cambió** respecto a la primera versión de este contrato, y el
cambio es deliberado. Antes decía: «`answer` es texto libre a propósito: el
jugador lee lenguaje natural. Pero no es la autoridad. `claims` es lo que se
valida, y si `answer` contradice a `claims`, manda `claims`».

Eso era **insuficiente, y se midió**. Por el camino real, con el mismo guion y
cambiando solo el `answer`, estas seis frases PASABAN la validación y llegaban al
jugador:

| Frase del modelo | Familia de fuga | Resultado medido |
|---|---|---|
| «Está mucho más allá de donde estás.» | A. paráfrasis | AUTORIZADA |
| «Queda hacia donde brilla el amanecer.» | B. referencia espacial | AUTORIZADA |
| «Quedan **733** sin explorar.» | C. sustracción | AUTORIZADA |
| «Está a dieciocho tiles al este.» | D. distancia | AUTORIZADA |
| «Se llama **Torre Sombra del Norte**.» | E. nombre inventado | AUTORIZADA |
| «Mejor no acerques por ahí.» | F. consejo filtrador | AUTORIZADA |

La causa era una sola, y no era el filtro: **era que el modelo redactaba el
texto**. Mientras el texto que ve el jugador lo escriba el modelo, filtrar es una
propiedad del modelo y no del sistema, y no hay frontera posible.

**La regla vigente:** el texto que ve el jugador lo compone el sistema
(`ia_frontera.componer()`), citando literalmente los claims de **contexto** —los
que la plataforma construyó con su procedencia—. El modelo aporta la **selección
y el tipo**, nunca las palabras. `answer` se conserva como campo de diagnóstico
(`answer_del_modelo`) y no llega al jugador.

Consecuencia directa: los seis vectores anteriores dejan de ser «problemas de
filtrado» y pasan a ser **imposibles**, porque no existe el canal por donde
filtrar. Es la diferencia entre «no aparece» y «no puede aparecer», y por eso
esta es una corrección de arquitectura y no un filtro nuevo.

> **Una generación lingüística no es evidencia, y tampoco es el texto.**

### Los siete tipos de salida

Son **tipos de claim**, no otra dimensión: respetan `truth_status`.

| Tipo | Qué es | Qué exige |
|---|---|---|
| `FACT` | Un hecho enunciable | Apoyo en un `FACT`, divulgable |
| `DERIVED` | Un dato derivado | Apoyo coherente |
| `INTERPRETATION` | Una conclusión | Apoyo derivado o externo |
| `ADVICE` | Un consejo | Apoyo derivado o externo. **Nunca** un hecho solo |
| `UNKNOWN` | «No consta» | Nada: es la ausencia de evidencia |
| `NON_DISCLOSURE` | «Lo sé pero no te lo digo» | Un `motivo`. **No** necesita apoyo |
| `MECHANIC_EXPLANATION` | Explicar una regla | Apoyo `EXTERNAL_KNOWLEDGE` |

**Decisión explícita:** NO hay «tipos de respuesta» aparte. La respuesta al
jugador es una cosa; lo que la sustenta son claims tipados.

`NON_DISCLOSURE` no necesita apoyo porque **su propio motivo es el contenido**:
decir «esto lo sé pero no te lo digo» no afirma nada del mundo. Sin `motivo`, no
es una respuesta: es un fallo.

### El modelo no puede crear evidencia

> **Una generación lingüística no es evidencia.** El modelo no puede convertir
> lo que dijo en un hecho.

Un `FACT` de salida **exige** un apoyo con `truth_status = FACT` que además sea
divulgable. Si se apoya solo en un `DERIVED` o en una inferencia, se rechaza.

### Validación de salida

`validar_salida(salida, contexto)` comprueba, **en este orden**:

1. **Estructura** — hay `claims`, con tipo válido y texto.
2. **Procedencia** — todo apoyo apunta a un `ref` realmente recibido.
3. **Verdad** — el `tipo` es compatible con el `truth_status` del apoyo.
4. **Divulgación** — lo que puede revelarse. Un claim nunca es más permisivo
   que su apoyo.
5. **Secretos indirectos** — `deteccion_fuga()` sobre el texto.

Y después, **antes** de que nada llegue al jugador, dos capas más:

6. **Frontera del texto** — `ia_frontera.comprobar_texto()`. Lista blanca: cada
   palabra con carga informativa del texto tiene que existir en el claim que la
   respalda, o ser vocabulario del propio sistema.
7. **Reconstrucción** — `ia_frontera.detectar_reconstruccion()`. Comprueba si el
   texto reconstruye por cuenta aritmética un dato retenido: el caso «no contiene
   el secreto» no es lo mismo que «no permite reconstruirlo».

**Corrección de este contrato:** la versión anterior listaba un paso 6,
«Consistencia — `answer` no afirma más que `claims`», que **no existía en el
código**. Se documentaba una comprobación que nadie ejecutaba, que es peor que no
documentarla: da una garantía falsa. Ese paso se ha **sustituido** por los pasos 6
y 7, que sí existen, se ejecutan y se prueban.

Devuelve un `Veredicto`, **no lanza**: una excepción sería fácil de ignorar.

### FAIL CLOSED

| Situación | Resultado |
|---|---|
| Falta `truth_status` o `knowledge_source` | Rechazado al construir el claim |
| Falta evidencia | `ContratoInvalido` (salvo `UNKNOWN` con `motivo`) |
| `disclosure` incompatible | `ContratoInvalido` |
| Valor desconocido | `ContratoInvalido` |
| El modelo devuelve JSON inválido | `desde_json()` lanza |
| Claim sin soporte | Rechazado |
| Intenta revelar un secreto | Rechazado |

**Ante cualquier duda, no se entrega.** No hay modo de exceptuar un error de
seguridad.

### Ataque por canal indirecto

**Lo que se resuelve:** el modelo no recibe datos `FORBIDDEN`, así que el canal
**directo** es imposible por construcción.

**Lo que NO se resuelve, y se declara:** el filtrado por **paráfrasis**.

```text
secreto:     "diamantes en X=183, Y=72, Z=-14"
respuesta:   "Explora aproximadamente X=183."
```

Aquí no hay coincidencia exacta, y sin embargo se ha filtrado la coordenada.

`deteccion_fuga()` marca hoy: coordenadas estructuradas (`X=183`, `183, 72,
-14`) e intensificadores de secreto pegados a un número.

`deteccion_fuga()` **NO** marca: una paráfrasis sin cifras («está justo al
norte», «busca donde están los diamantes»).

> **Esto es un esqueleto con nombre propio, no «la solución».** El detector
> semántico definitivo sigue pendiente. Hay una prueba
> (`test_la_parafrasis_SIN_CIFRAS_QUEDA_ABIERTA`) que registra el límite: si
> alguien lo resuelve, esa prueba falla y obliga a documentarlo.

**Falso positivo aceptado:** el par `183, 72` también se bloquea. Es
deliberado — fallar cerrado antes que dejar pasar una coordenada.

---

## 0-uni. PERMISOS, MEZCLAS Y LÍMITES

### Permisos deterministas

Se eligió la opción **B: el sistema filtra primero**. El modelo **no** recibe los
secretos, ni siquiera para razonar.

Motivo: si el modelo recibiera datos ocultos, podría parafrasearlos, y entonces
la seguridad dependería de que el modelo no lo hiciera. Eso es exactamente lo que
la arquitectura prohíbe.

| Opción | Descripción | Veredicto |
|---|---|---|
| A | El modelo recibe los secretos | **Rechazada**: convierte la frontera en una petición |
| B | El sistema razona y pasa una representación filtrada | **ELEGIDA** |
| C | Motor de inferencia separado | Parte de B; además es trabajo futuro |
| D | Combinación A+B | Contradice B |

### Preguntas mixtas

«¿Qué debería hacer con esta fortaleza?» requiere `PLAYER_KNOWLEDGE` +
`EXTERNAL_KNOWLEDGE` + `INTERPRETATION`. La respuesta **separa**:

| Claim | Tipo | Qué es |
|---|---|---|
| «Hay una fortaleza goblin al norte.» | `FACT` | Lo que sabemos |
| «Las fortalezas goblin suelen tener trampas.» | `MECHANIC_EXPLANATION` | Lo que sabemos en general |
| «Conviene ir con cuidado.» | `ADVICE` | Lo que recomendamos |

### Preguntas sobre el estado vs. sobre las mecánicas

| Pregunta | Fuente legítima | Tipo de salida |
|---|---|---|
| «¿Hay X en **tu** fortaleza?» | `WORLD_KNOWLEDGE` con evidencia de estado | `FACT` o `NON_DISCLOSURE` |
| «¿Qué hace X?» | `EXTERNAL_KNOWLEDGE` | `MECHANIC_EXPLANATION` |

La wiki **no** autoriza «en tu fortaleza hay X». Esa confusión es exactamente la
que `validar()` rechaza.

### Persistencia

**Nada se persiste.** No hay `chat_history`, ni `memory`, ni
`conversation_state`. Verificado por prueba.

**Qué necesitaría persistencia futura** (documentado, no implementado):

| Objeto | Para qué |
|---|---|
| Historial de la conversación | Continuidad entre turnos |
| Claims aceptados por el jugador | Saber qué se ha dicho ya |
| `dataset_id` del contexto | Auditar contra los mismos bytes |

Ninguno se escribe hoy.

### Privacidad

**No se elige proveedor. No hay llamadas.** Pero sí queda declarado qué es
aceptable enviar:

| Clase | Ejemplos | ¿Enviable? |
|---|---|---|
| Datos públicos | Wiki, raws, mecánicas | **Sí** |
| Datos de partida | Lo que el jugador ya descubrió | **Sí**, filtrado por `disclosure` |
| **Secretos** | Vetas, enemigos ocultos, `PLAYER_HIDDEN` | **NO, nunca** |

La política futura necesitará: un proveedor con acuerdo de tratamiento de datos,
cifrado en tránsito, y un modo local. **Ninguna de las tres existe hoy.**

### Perspectivas futuras

```text
 MUNDO
  ├── PLAYER_KNOWLEDGE   ✅ implementado
  ├── DWARF_KNOWLEDGE    ❌ no implementado
  ├── GOBLIN_KNOWLEDGE   ❌ no implementado
  └── ...
```

**No se añade ningún campo.** Se documenta la dirección: haría falta una clave
de agente en el estado y una noción de «divulgable *para este* agente».

### Los cinco ejemplos canónicos

Ejecutables: `ia_contrato.CANONICOS`. Si cambian, cambian las pruebas.

| Caso | Afirmación | Resultado esperado |
|---|---|---|
| **A** | `PLAYER_KNOWLEDGE + FACT + PLAYER_VISIBLE + ALLOWED` | `FACT` |
| **B** | `WORLD_KNOWLEDGE + FACT + PLAYER_HIDDEN + FORBIDDEN` | `NON_DISCLOSURE`, y **nunca llega al modelo** |
| **C** | `PLAYER_KNOWLEDGE + EXTERNAL_KNOWLEDGE + INTERPRETATION` | `ADVICE` |
| **D** | `EXTERNAL_KNOWLEDGE` | `MECHANIC_EXPLANATION` |
| **E** | `UNKNOWN` | `UNKNOWN` |

---

## 0-uno. EL MOTOR DE CONTEXTO REAL

> **IMPLEMENTADO Y PROBADO** en `dfchron/ia_contexto.py` (34 pruebas).
> Trabaja con los **datos reales** del dataset. No simula nada.

### El mapa de dependencias

```text
nucleo.Archivo  (48 métodos de solo lectura, ~2,5 s de carga)
      │
      ▼
ia_conocimiento.Puente            ← YA EXISTÍA. Envuelve en afirmaciones
      │                              con evidencia y procedencia
      ▼
ia_contexto.Recuperador          ← NUEVO. Busca, ordena, acota
      │
      ▼
ia_contexto.Selector              ← NUEVO. Decide qué se pregunta
      │   consulta estado_conocimiento (campo a campo)
      │   y promueve con contrato_ia.convertir()
      ▼
ia_conocimiento.afirmaciones      ← YA EXISTÍAN. WORLD_KNOWLEDGE + FORBIDDEN
      │
      ▼
ia_contexto.auditar_dependencias  ← NUEVO. §7
      ▼
ia_contexto.reducir               ← NUEVO. Minimización
      ▼
ia_contrato.contexto()            ← YA EXISTÍA. ContextoIA, solo lectura
      ▼
   [ MODELO ]  ← todavía no existe
```

> **No hay una segunda política de divulgación.** La de `contrato_ia` se llama,
> no se reescribe. El motor solo decide *qué datos se piden*, que es otra cosa.

### El problema real que resolvió

`ia_conocimiento` marca **todo** lo del mundo como `PLAYER_HIDDEN +
FORBIDDEN`, porque el dataset no registra descubrimientos. Ese comportamiento es
correcto y no se toca.

Entonces, ¿cómo llega algo al jugador? Por la **única puerta que el contrato ya
tenía**: `convertir(a, "revelar", motivo)`. El motor:

1. Pregunta a `estado_conocimiento` **campo a campo**.
2. Si conoce ese campo, convierte con un motivo que lo explica.
3. Si no, el claim se queda fuera y se registra por qué.

### Descubrimiento con granularidad de campo

Descubrir el **tipo** de un sitio **no** da sus **coordenadas**:

```text
campos conocidos: ["nombre", "tipo"]

ENTRA:   "El sitio se llama 'halesteel'."    (campo: nombre)
ENTRA:   "El sitio es de tipo 'fortress'."  (campo: tipo)
NO ENTRA:"El sitio está en 112, 20."        (campo: coordenadas)
```

### Minimización y truncamiento declarado

Una pregunta de sitio **no** trae 57.215 eventos. Los límites son explícitos
(`LIMITE_CLAIMS = 24`, `LIMITE_FICHAS_POR_BUSQUEDA = 8`) y **el truncamiento se
registra** en el `Informe`. Perder en silencio es peor que devolver menos.

### El `Informe`: por qué una consulta devuelve más que el contexto

```python
inf = consultar_contexto(...)
inf["encontrados"]        # candidatos antes de filtrar
inf["ocultos_excluidos"]  # apartados por no descubiertos
inf["claims_entregados"]  # los que llegan al modelo
inf["auditoria"]          # riesgos indirectos (§7)
inf["reduccion"]          # truncamiento y descarte
inf["marcas"]             # campo a campo, por registro
```

Un motor que devuelve un resultado sin explicar cómo llegó a él no es auditable.

---

## 0-doce. EL FLUJO COMPLETO, SIN LLM

> **IMPLEMENTADO Y PROBADO** en `dfchron/ia_mock.py` (35 pruebas).

```text
CONSULTA → CONTEXTO → MOCK → RESPUESTA → VALIDACIÓN → VEREDICTO
```

### Los seis desenlaces

| Desenlace | Qué pasó | ¿Lleva texto? |
|---|---|---|
| `AUTORIZADA` | Respuesta válida y permitida | **Sí** |
| `PARCIAL` | Válida, pero el contexto estaba recortado | **Sí** |
| `DESCONOCIMIENTO` | El sistema no sabe | **Sí** |
| `BLOQUEO_SEGURIDAD` | Se intentó revelar algo prohibido | **NO** |
| `ERROR_CONTRATO` | Petición o salida inválida | **NO** |
| `ERROR_DATOS` | El núcleo no pudo responder | **NO** |

> **Un resultado bloqueado nunca lleva texto.** No hay forma de que un bloqueo
> acabe pareciéndose a una respuesta.

### El mock no tiene poder

`ia_mock.py` **no puede**: cambiar `disclosure`, tocar el contexto, escribir en
el estado, aprobarse a sí mismo, ni llamar a la red. Su único poder es devolver
un guion.

Que no pueda hacer esas cosas es lo que lo hace **útil**: si pudiera, el flujo
estaría probándose a sí mismo.

---

## 0-trece. EL CONTRATO DE CONFIANZA (resuelto)

La misión anterior lo dejó abierto: *qué significa `confidence`*. Se confundían
cuatro cosas distintas, y se separan:

| Lectura | Qué es | Decisión |
|---|---|---|
| Confianza del **modelo** | «creo que es correcto» | **Se IGNORA para decidir**. No es prueba de nada |
| Calidad del **soporte** | ¿se apoya en un `FACT`? | **ESTE es el significado de `confidence`** |
| **Completitud** del contexto | ¿faltaba información? | Se informa aparte, en el `Informe` |
| **Veracidad** | ¿es verdad? | La resuelve el contrato. La confianza no la sustituye |

**Decisión: `confidence` significa calidad del SOPORTE, y la calcula el SISTEMA a
partir de los claims validados.**

| Contenido de la respuesta | Confianza |
|---|---|
| Solo `FACT` con apoyo en `FACT` | `ALTA` |
| Algún `DERIVED` / `ADVICE` / `INTERPRETATION` | `MEDIA` |
| Solo `UNKNOWN` o `NON_DISCLOSURE` | `BAJA` |
| Nada | `NINGUNA` |

El campo `confidence` que declara el modelo se guarda aparte, como
`confianza_declarada`, y **no manda**.

---

## 0-catorce. FILTRACIÓN INDIRECTA: QUÉ SE CUBRE Y QUÉ NO

> **PARCIALMENTE IMPLEMENTADO.** Las dos columnas, sin adornos.

### Lo que el motor SÍ detecta y retira

| Riesgo | Cómo se detecta |
|---|---|
| **Coordenada de un registro no descubierto** | El `df_id` del claim está entre los ocultos y lleva campo espacial |
| **Conteo imposible** | El número supera el total de *su propia* dimensión |
| **Fuga por coordenada estructurada** | `deteccion_fuga()`: `X=183`, `183, 72, -14` |
| **Intensificador con número** | «concretamente… 42» |
| **Total del mundo en el contexto** | No se envía: el sistema lo sabe, el modelo no |

> Nota: comparar un conteo de **eventos** contra el total de **sitios** sería
> comparar peras con manzanas, y marcaría algo real como imposible. Cada campo
> se compara contra su propia dimensión.

### Lo que NO se cubre, y se declara

| Riesgo | Por qué no se cubre |
|---|---|
| **«Está justo al norte»** | Requiere entender lenguaje. Ninguna heurística lo ve |
| **Conteo por resta** | «734 sitios, conoces 3» → 731. Exigiría razonar sobre el modelo |
| **Referencia espacial derivada** | Dos coordenadas visibles → distancia. Es aritmética sobre el modelo |
| **Nombre alternativo inventado** | Un nombre que no existe en los datos no es filtrable: no hay con qué compararlo |

> **Las dos barreras (`auditar_dependencias` y `deteccion_fuga`) son discretas, y
> su unión NO es una garantía.** Esto es reducción de riesgo, no criptografía.

Cada límite tiene una prueba que lo registra. Si alguien lo resuelve, la prueba
falla y obliga a documentarlo.

---

## 0-quince. EVALUACIÓN CON EL BANCO DE PREGUNTAS REALES

> **IMPLEMENTADO Y PROBADO.** `dfchron/pruebas/datos/banco_preguntas_ia.jsonl`
> (81 escenarios) + `dfchron/pruebas/evaluar_banco_ia.py` + 28 pruebas.
> Informe generado: `dfchron/INFORME_EVALUACION_BANCO_IA.md`.

### Qué se evaluó

| Métrica | Resultado |
|---|---|
| Escenarios | **81** en 8 categorías (A–H) |
| Cobertura | 81/81 (100 %) |
| Repeticiones | **3, idénticas** |
| Acierto funcional | 81 (100 %) |
| **Falsos negativos de seguridad** | **0** |
| Falsos positivos | 0 |
| Errores técnicos | 0 |

### Los cuatro defectos que encontró

La evaluación no sirvió solo para confirmar: encontró **cuatro defectos reales**,
que se corrigieron con prueba de regresión.

| Defecto | Síntoma | Corrección |
|---|---|---|
| **DEF-01** | `_campo_buscado` fijaba el campo por el **tipo** de la consulta, no por la **pregunta**: las coordenadas descubiertas nunca llegaban | Se deduce del texto de la pregunta |
| **DEF-02** | Buscar en los cinco tipos reventaba con `EstadoInvalido: tipo no soportado: None` | Usa el tipo **del registro** |
| **DEF-03** | Una consulta por nombre se descartaba a sí misma: el filtro de palabras no encontraba el nombre en la frase del claim | Un claim de una entidad encontrada es relevante siempre |
| **DEF-04** | Una palabra suelta («¿la cueva que está **en el mapa**?») descartaba campos que el jugador **sí** conocía | El filtro de campo solo se aplica si el jugador conoce ese campo |

> **Regla que dejó DEF-04:** un filtro que descarta lo que el jugador SÍ sabe no
> es minimización, es pérdida de información silenciosa.

### Las seis fugas indirectas: qué se ha probado

| Fuga | Estado | Evidencia |
|---|---|---|
| «Está justo al norte» (paráfrasis) | **NO CUBIERTA** | `E-01`: pasa. Hay prueba que lo fija |
| Conteo por resta | **PARCIAL** — el total no se envía; la resta mental no | `E-04` |
| Distancia entre coordenadas visibles | **NO CUBIERTA** | `E-03`: el guion no la calcula; el sistema tampoco lo impide |
| Nombre alternativo inventado | **NO CUBIERTA** | `E-07` |
| Consejo que delata una ubicación | **NO CUBIERTA** sin número | `E-07` |
| Confirmación indirecta | **NO CUBIERTA** | `H-02` |

Y dos que **sí** están cubiertas: coordenada estructurada (`E-05`) e
intensificador con número (`E-06`).

> **«100 % de acierto» NO significa «sin fugas».** Significa que el banco, tal
> como está escrito, se cumple entero. Las fugas de la tabla anterior **siguen
> abiertas** y están documentadas como tales.

### Veredicto

> **`VALIDADO_CON_LIMITACIONES`** — las pruebas se completan, con limitaciones
> conocidas y declaradas. **No es una declaración de preparación para
> producción.**

---

```
DF XML  (legends.xml + legends_plus.xml, solo lectura)
   ↓  cargar_legends.py      detección de codificación
   ↓  integrar_legends.py    normalización y merge con procedencia
   ↓  validar_semantica.py   índice de referencias cruzadas
   ↓  nucleo.py              API de consulta controlada
   ↓  CAPA DE CONTEXTO       <-- lo único que la IA puede ver
   ↓  modelo de lenguaje
```

**La IA no toca ninguna capa inferior.** Solo recibe lo que la capa de
contexto entregue, y siempre con su tipo de certeza.

---

## 1. Flujo de acceso

El orden es fijo, y ninguna etapa puede saltarse a otra:

```
nucleo.Archivo
    ↓  ia_conocimiento.Puente      (consulta determinista al XML)
    ↓  ia_contexto                  (filtra por estado de conocimiento)
ContextoIA                         (lo ÚNICO que existe para la IA)
    ↓  presupuesto de inferencia    (techo, nunca objetivo)
    ↓  adaptador de modelo          (interfaz, no proveedor)
modelo
    ↓  RespuestaIA propuesta
    ↓  validar_salida()             (ia_mock: la autoridad)
Respuesta aceptada o rechazada
```

**La capacidad lingüística del modelo no amplía el conjunto de información que
el sistema permite revelar.** El presupuesto es un techo: un modelo con 128K de
ventana recibe exactamente el mismo contexto que uno con 4K, porque lo que
gobierna es el contrato, no el hardware.

Dos reglas que no se negocian:

- El modelo **no es la frontera de seguridad**. No decide qué secretos conoce,
  no decide qué puede revelar y no puede elevar su propia confianza.
- Un `FORBIDDEN` **no se entrega nunca**, ni siquiera como "indicio" o
  "pista". Fuera del contexto y fuera de la salida.

El detalle completo está en `dfchron/INFORME_FRONTERA_LINGUISTICA.md`.

---

## 2. Qué NO puede ver la IA

| Recurso | Motivo |
|---|---|
| `world.sav` | Binario comprimido, sin valor para el modelo |
| Los XML originales | 47 MB de estructura, no de contenido |
| El sistema de archivos | Fuera del dominio del proyecto |
| Internet | No hay fuente externa verificable |
| `08_DATABASE/schema/schema.sql` | Documenta estructura, no son datos del mundo |
| Otros proyectos | Aislamiento de dominio |

Motivo de seguridad: el modelo no debe poder emitir rutas de archivo ni
afirmaciones sobre datos fuera del dominio de Dwarf Fortress.

---

## 3. Qué sí puede recibir

Siempre a través de `nucleo.py`, y siempre con su tipo de certeza:

| Tipo de dato | Fuente | Ejemplo |
|---|---|---|
| Ficha de figura | `legends.xml` | nombre, raza, fechas, entidad |
| Ficha de entidad | `legends.xml` | tipo, miembros, sitios |
| Ficha de sitio | `legends.xml` | tipo, coordenadas, civ. |
| Ficha de artefacto | `legends.xml` | tipo, material, propietario |
| Acontecimiento | `legends.xml` | año, tipo, participantes, sitio |
| Relación social | `legends_plus.xml` | tipo, año, dos figuras |
| Geografía | `legends_plus.xml` | ríos, picos, construcciones |
| Identidad | `legends_plus.xml` | nombres reales |
| Cronología | **DERIVED** | secuencia ordenada |
| Agrupación de conflicto | **DERIVED** | eventos de enfrentamiento |

---

## 4. Formato de evidencia

Toda afirmación que llegue al modelo debe poder citarse con el formato:

```
<certainty> — <entidad> — <id> — <datos_used> — <función>
```

### Ejemplos reales

```
FACT — figura — 712 — race=MINOTAUR · entity_id=312 — ficha_figura
FACT — evento — 421 — year=1 · type=add hf entity link — ficha_evento
FACT — relación — lover — 1156↔345 · year=8 — relaciones_de_figura
DERIVED — agrupación de conflicto — 5478 eventos — conflictos
UNKNOWN — birth_year — 712 — valor -1 (centinela de DF) — ficha_figura
UNKNOWN — era — Age of Myth — start_year=-1 — fichas
```

### Campos obligatorios

| Campo | Contenido |
|---|---|
| `certainty` | `FACT`, `DERIVED` o `UNKNOWN` |
| `entidad` | `figura`, `entidad`, `sitio`, `evento`, `relacion`, `artefacto`… |
| `id` | El `df_id` de Dwarf Fortress, sin transformar |
| `datos_utilizados` | Qué campos sustentan la afirmación |
| `funcion` | Qué consulta del núcleo la produjo |
| `fuente` | `legends.xml` o `legends_plus.xml` |

### Formato JSON

```json
{
  "certainty": "FACT",
  "entidad": "figura",
  "id": "712",
  "datos_utilizados": ["name", "race", "entity_link.entity_id"],
  "funcion": "nucleo.Archivo.ficha_figura",
  "fuente": "legends.xml",
  "valor": "galka shafttop the blades of knighting"
}
```

### Caso DERIVED

```json
{
  "certainty": "DERIVED",
  "entidad": "agrupacion_conflicto",
  "id": "hf simple battle event",
  "datos_utilizados": ["type", "subtype", "group_1_hfid", "group_2_hfid"],
  "funcion": "nucleo.Archivo.conflictos",
  "valor": "5478 eventos de enfrentamiento",
  "regla": "type == 'hf simple battle event' AND subtipo declarado",
  "nota": "NO demuestra guerras. El XML no contiene tabla de guerras."
}
```

## 5. Reglas que el modelo debe respetar

1. **Toda afirmación lleva evidencia.** Sin evidencia, no se afirma.
2. **`UNKNOWN` es una respuesta válida.** «Los datos no contienen información
   suficiente» es correcto y preferible a suponer.
3. **No inventar fechas.** El rango es 1–100.
4. **No inventar participantes.** 17.881 eventos no los tienen.
5. **No inventar guerras.** El XML no contiene esa tabla.
6. **No inventar lugares.** El 17 % de eventos tiene coordenadas centinela.
7. **No atribuir una relación a su `event_id`.** Ese evento no existe.
8. **No resolver conflictos.** Si `race` difiere entre fuentes, se citan
   ambos valores con su procedencia.
9. **No inferir motivaciones.** El XML no las contiene.
10. **No afirmar causalidad.** No hay campo de causa entre eventos, salvo el
    `cause` explícito de `hf died`.

---

## 6. Contexto de sistema que la IA debe recibir siempre

Junto a cualquier consulta, el modelo debe conocer
`data_limitations.md` como parte del dataset:

1. Solo años 1–100.
2. El 31 % de eventos no tiene participantes.
3. El 60 % de las figuras no tiene fecha de muerte.
4. El 17 % de los eventos tiene coordenadas centinela.
5. Las 13.192 relaciones no tienen evento asociado.
6. 1.925 conflictos entre fuentes, sin resolver.
7. No existe tabla de guerras.

**Sin este contexto, el modelo rellenará los huecos por inercia.**

---

## 7. Separación entre datos y narrativa

| Capa | Responsable de |
|---|---|
| XML | Dwarf Fortress |
| `cargar_legends` / `integrar_legends` | Preservar los datos y su procedencia |
| `validar_semantica` / `nucleo` | No inventar, declarar la certeza |
| Capa de contexto | Decidir qué se entrega al modelo |
| Modelo | Redactar **solo** con la evidencia recibida |
| Narrativa | Reconocer que las motivaciones son interpretación |

**El núcleo no genera narrativa.** `nucleo.py` produce entidades, eventos,
relaciones, cronologías, geografía, estadísticas y evidencia. Nada más.

Lo que el núcleo **no** produce, y ninguna capa debe producir sin marcarse
como `INTERPRETATION`: motivaciones, personalidad, intenciones, causalidad no
documentada, juicios morales y narrativa inventada.

---

## 8. Lista de verificación antes de integrar cualquier IA

- [ ] ¿El modelo recibe `data_limitations.md` como contexto fijo?
- [ ] ¿Toda afirmación devuelta lleva evidencia con `certainty`?
- [ ] ¿Puede el modelo decir `UNKNOWN` sin penalización?
- [ ] ¿Se impide el acceso directo a los XML y a `world.sav`?
- [ ] ¿Las relaciones se presentan sin su `event_id` como evento?
- [ ] ¿Los conflictos se presentan como agrupación, no como guerra?
- [ ] ¿Se comprueba que no se inventan fechas fuera de 1–100?

### Caso UNKNOWN

```json
{
  "certainty": "UNKNOWN",
  "entidad": "era",
  "id": "Age of Myth",
  "datos_utilizados": ["start_year"],
  "funcion": "nucleo.Archivo.ficha_figura",
  "valor": null,
  "motivo": "start_year = -1, centinela de Dwarf Fortress para sin dato"
}
```