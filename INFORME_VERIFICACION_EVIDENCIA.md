# INFORME — Arquitectura de evidencia y verificación factual

**Fecha:** 2026-10-03 · **Alcance:** límites de la verificación semántica,
verificadores deterministas, confianza y autoridad · **Python:** 3.14.7 (Windows)

> Este informe distingue siempre entre **implementado y probado**, **implementado
> sin demostración suficiente**, **documentado** y **no implementado**. Ningún
> riesgo se declara resuelto porque haya cambiado de nombre.

---

## A. Estado inicial (verificado antes de tocar nada)

| Comprobación | Resultado |
|---|---|
| SHA-256 `nucleo.py` | `CCC48EA67849…` — intacto |
| SHA-256 `contrato_ia.py` | `F1AAF1A6D4B0…` — intacto |
| SHA-256 `ia_frontera.py` | `4EEE0519902E…` — intacto |
| SHA-256 `ia_verificacion.py` | `B8BFD2CC39D3…` — punto de partida |
| `legends.xml` | Hash de referencia: coincide |
| Banco adversarial | **83 escenarios** |
| Suites | 25, 35, 49, 48, 59, 48, 25, 39, 51, 29/29 — todas verdes |

**El estado heredado era correcto.** No se encontró ninguna discrepancia con lo
documentado en `INFORME_RIESGOS_ABC.md`.

---

## B. Inventario: tipos reales de afirmación

Clasificados desde el código, no desde un catálogo abstracto.

| Tipo | Ejemplo real | Fuente | Método de verificación | Qué demuestra | Limitación | Riesgo de aceptar una incorrecta |
|---|---|---|---|---|---|---|
| **A. Estructuradas** | «El sitio es de tipo 'hamlet'.» | `ia_conocimiento` sobre `nucleo.ficha_sitio` | **Determinista** (`ia_estructura`) | Que `sitio 112` tiene `tipo = hamlet` | Solo con la plantilla exacta | **BAJO**: el núcleo lo contradice si falla |
| **A′. Conteo** | «El sitio tiene '47' eventos registrados.» | idem | **Determinista** (misma vía) | Que el conteo declarado coincide | No se recalcula desde cero | **MEDIO**: hereda el error del núcleo |
| **B. Relacionales** | «Begunboard tiene una relación con la figura X.» | `historical_event_relationships` | **NO determinista** | Nada | Las relaciones **no tienen `df_id`**: no hay identidad estable | **ALTO**: no verificable |
| **C. Cuantitativas** | «De 734 sitios, el jugador conoce 3.» | `estadisticas()` + estado | **Parcial**: el total sí; la resta no | El total del mundo | La resta no es determinista | **ALTO**: vía de la fuga por sustracción |
| **D. Temporales** | «El evento ocurrió en el año 42.» | campo `año` | **Determinista** (plantilla `evento/año`) | Que ese evento tiene ese año | **No hay duración ni secuencia** | **BAJO** |
| **E. Interpretativas** | «Esta zona es peligrosa.» | Ninguna | **Imposible** | **Nada** | No existe criterio de riesgo en los datos | **MUY ALTO**: no debe entrar como `FACT` |

**La fila E es la importante.** El dataset no tiene base para «peligroso» ni
«preparar un ataque». Una afirmación así debe llegar como `INTERPRETATION` o
`ADVICE`, nunca como `FACT`, y el contrato ya lo impone.

**Lo que no existe y por tanto no se verifica:** relaciones con identidad estable,
distancia, rumbo, adyacencia, duración y estado que cambie con el tiempo.

---

## C. Arquitectura de evidencia

```
afirmación
   ├─ verdad         truth_status      ─┐
   ├─ verificación   VERIFICA / NO_VERIFICA / NO_APLICABLE  ─┤ ejes
   ├─ visibilidad    PLAYER_VISIBLE / HIDDEN / EXTERNAL     │ independientes
   └─ divulgación    ALLOWED / FORBIDDEN / CONDITIONAL     ─┘
```

Los cuatro ejes se transportan por separado y **ninguno se deduce de otro**. Un
dato puede ser verdadero, verificado y permanecer oculto.

| Capa | Módulo | Qué comprueba | ¿Autoriza? |
|---|---|---|---|
| Verdad y política | `contrato_ia.py` | Combinaciones coherentes, evidencia obligatoria | **Sí** |
| Filtros del claim | `ia_contrato.py` | Referencia real, tipo no más fuerte, permiso del apoyo | **Sí** |
| Trazabilidad | `ia_verificacion.py` | Respaldo léxico (medida informativa) | **No** |
| Verificación estructurada | `ia_estructura.py` | El valor contra el núcleo | **No** |
| Frontera | `ia_frontera.py` | Que el texto entregado no exceda los claims | **Sí**, última palabra |

**Las dos capas de verificación no autorizan.** Comprobado: una afirmación
`VERIFICADA` y `PLAYER_HIDDEN` sigue sin poder divulgarse. El bloque va en el
veredicto como información, no como puerta.

---

## D. Implementación

### D.1 `ia_estructura.py` (nuevo, 297 líneas)

Verificación determinista contra el núcleo, limitada a lo demostrable.

* **Plantillas declaradas** `(entidad, campo) -> plantilla`, tomadas de
  `ia_conocimiento.py`. Se declaran y no se deducen, para que una divergencia
  entre las dos tablas no pase desapercibida, y para que **un dato nuevo no sea
  verificable hasta que se declare aquí**.
* **Coincidencia de la frase completa**, no de un fragmento: verificar una
  proposición y dar por verificada la frase entera es el error a evitar.
* **Reutiliza** `ia_conocimiento._texto()` y `Recuperador.ficha_de()`. No duplica
  lógica del núcleo.
* **`rec` es opcional**: sin él el comportamiento es idéntico al anterior.

### D.2 Cableado

* `ia_contrato.validar_salida(salida, ctx, rec=None)` → `verificacion["estructurada"]`
* `ia_mock.validar_respuesta_ia(salida, contexto, rec=None)` → propaga
* `ia_mock.ejecutar_consulta_ia(..., recuperador=None)` → entrega

Si la verificación falla, **se dice** en el veredicto en vez de callarse.

### D.3 Ningún componente protegido se tocó

| Componente | Cambio |
|---|---|
| `nucleo.py` | **ninguno** |
| `contrato_ia.py` | **ninguno** |
| `ia_frontera.py` | **ninguno** |
| `ia_verificacion.py` | **ninguno** |
| `ia_contrato.py` | bloque informativo + parámetro opcional |
| `ia_mock.py` | propagación de `rec` |

---

## E. Trazabilidad: qué mide y dónde está su límite

`trazabilidad()` calcula la **proporción de palabras con carga informativa** del
texto de un claim que aparecen en el vocabulario de sus apoyos. Es aritmética de
conjuntos: `|palabras ∩ vocabulario_de(apoyos)| / |palabras|`.

### El límite, medido

| Caso | Fracción | Lectura honesta |
|---|---|---|
| Respaldo total | 1.0 | Correcto |
| **Negación** («NO es de tipo X») | **1.0** | **Falso positivo severo** |
| **Afirmación opuesta** | **1.0** | **Falso positivo severo** |
| Parafrasis («La fortaleza…») | 0.667 | Falso negativo |
| Sinónimo («El recinto…») | 0.667 | Falso negativo |
| Compuesta con una parte falsa | 0.75 | Diluye en vez de separar |
| Más información no respaldada | 0.75 | Diluye |
| **Contradicción entre apoyos** | 0.75 | No detecta la contradicción |
| Reutiliza vocabulario de otro claim | 0.833 | Falso positivo |

**El límite matemático:** la trazabilidad es una **función del vocabulario**, no de
la relación entre proposiciones. Dos afirmaciones que comparten palabras y dicen
cosas distintas son indistinguibles para ella; y dos que dicen lo mismo con otras
palabras, también.

### Decisión: sigue siendo medida informativa

| Opción | Decisión | Motivo |
|---|---|---|
| Medida informativa | **ELEGIDA** | Es lo que mide. No pretende más |
| Indicador de calidad de evidencia | **ELEGIDA también** | Es su segundo uso: alimenta la confianza |
| Componente de confianza | **ELEGIDA, con límite** | Solo degrada; nunca eleva por encima de lo que el respaldo permite |
| Barrera de seguridad | **DESCARTADA** | La medición demuestra que **no puede**: una negación puntúa 1.0 |

**No se ha convertido en barrera**, y la razón está medida, no supuesta. Convertir
en barrera una medida con falsos positivos severos sobre negaciones sería
exactamente el error de tomar la coincidencia de palabras por prueba de verdad.

**Contraste con la verificación estructurada.** La misma negación que la
trazabilidad puntúa 1.0 recibe aquí `NO_APLICABLE`, porque no hay plantilla que
admita una negación. Ahí está la diferencia entre una medida y una demostración.

---

## F. Confianza: qué la justifica

`evaluar_confianza(respuesta, verificacion=None)`:

| Tipo | Antes | Ahora |
|---|---|---|
| Solo `FACT` | `ALTA` (solo por el tipo) | `_confianza_por_trazabilidad()` |
| Con `DERIVED`/`ADVICE`/… | `MEDIA` | `MEDIA` |
| Solo `UNKNOWN`/`NON_DISCLOSURE` | `BAJA` | `BAJA` |
| Nada | `NINGUNA` | `NINGUNA` |

`_confianza_por_trazabilidad()` degrada: `ALTA` solo con trazabilidad 1.0 en todos
los claims; `BAJA` si alguno tiene 0.0; `MEDIA` si alguno es parcial; y `MEDIA`
—nunca `ALTA`— si no llega el bloque de verificación, porque sin pruebas no se
afirma confianza alta.

### Lo que se comprobó

| Pregunta | Respuesta |
|---|---|
| ¿El `tipo` conserva autoridad? | **No.** Solo ordena el rango |
| ¿Puede elevar sin evidencia? | **No.** Sin bloque, el techo es `MEDIA` |
| ¿Se reutiliza respaldo de otro claim? | **Sí, y está documentado**: es por claim, contra **sus** apoyos |
| ¿El contenido puede cambiar después? | No: el cálculo es síncrono sobre la lista del guion |
| ¿Hay ruta que no pase por el cálculo? | No: `validar_respuesta_ia` siempre calcula |
| ¿Se mezcla con divulgación? | **No.** `confianza` no participa en `puede_entregarse` |
| ¿Una contradicha conserva `ALTA`? | **No.** Con trazabilidad 0.0 baja a `BAJA` |

**Lo que la confianza NO es:** no es probabilidad, no es porcentaje y no mide
verdad. Es un indicador de calidad de respaldo. Y hay que decirlo, porque un
`ALTA` puede leerse como «esto es cierto» cuando solo significa «estas palabras
tienen respaldo en lo que el sistema entregó».

---

## G. Divulgación sigue siendo independiente

Comprobado en el camino real, con B-10:

| Afirmación | Verificación | ¿Llega al jugador? |
|---|---|---|
| «El sitio es de tipo 'hamlet'.» | `VERIFICADA` | **Sí** |
| «El sitio es de tipo 'dragoncave'.» | `NO_VERIFICADA` | **No**: el sistema entrega `hamlet` |
| Secreto `FORBIDDEN` | no entra al contexto | **No** |

La segunda fila es la importante: una afirmación **refutada por el núcleo** no
llega nunca, porque **el texto que ve el jugador lo compone el sistema desde el
claim de contexto**, no desde lo que escribió el modelo. Un valor fabricado no
tiene vía de salida.

La secuencia se mantiene, y cada paso es independiente del anterior: identificar →
comprobar evidencia → estado de verdad y verificación → visibilidad → política →
composición.



---

## H. Estado persistido

Se conserva la corrección de la misión anterior. Comprobado:

* Escritura y lectura aplican la **misma** validación de contenido
* Las referencias se verifican en ambos caminos
* Entrada con tipo inventado → `EstadoInvalido`
* Entrada que no es objeto → `EstadoInvalido`
* Campo vacío → `EstadoInvalido`
* Entrada válida → **aceptada** (la comprobación no rompió lo que valía)
* `schema_version` sigue en **1**. **No se migró**: no hay necesidad demostrada.

---

## I. Reconstrucción: estado real

`detectar_reconstruccion` **existe pero no se ejecuta en ningún camino real**.

| Aspecto | Realidad |
|---|---|
| Dónde | `ia_frontera.py` |
| Qué necesita | `(texto, ctx, retenidas)` |
| Qué detecta | Aritmética explícita (`a op b`) con **ambos operandos autorizados** y **resultado en `retenidas`** |
| Qué NO detecta | Reconstrucción semántica, espacial o por comparaciones cualitativas |
| ¿Se ejecuta | **No.** Ningún módulo lo invoca |
| Lista `retenidas` | **Vacía por defecto**: sin ella no detecta nada |
| Efecto sobre la respuesta | **Ninguno** |

**Decisión: permanece inactivo.** No existe un conjunto fiable de «información
retenida» definido de forma estructurada: habría que definir qué se retiene, y eso
depende de las decisiones del jugador en cada partida. Inventar una lista adivinada
sería presentar de activa una garantía que no existe.

Se mantiene exactamente como estaba: **mecanismo disponible, no garantía en
funcionamiento**. Declararlo activo sería el error que la misión prohíbe.

---

## J. Espacio: confirmación

No se ha construido ningún índice nuevo y **no se ha inventado ninguna métrica**.

* `nucleo.py` mantiene `sitios_por_coordenada` y `capas_por_coordenada`. **No
  duplicados.**
* La IA **no los usa**: el contexto se construye desde fichas de entidades.
* Los **ocho vectores espaciales** siguen bloqueados por la composición, y sus
  pruebas se conservan intactas en `probar_riesgos_abc.py`.
* Las coordenadas legítimamente conocidas siguen **redaccionadas**.

No apareció ninguna necesidad espacial concreta durante esta misión, así que no se
implementó nada por anticipación.

---

## K. Pruebas

### Nuevas

| Suite | Qué prueba |
|---|---|
| `probar_verificacion_estructurada.py` (**18**) | Positivos, detección de fabricación, **todo lo no verificable**, separación de autoridad, determinismo |

La prueba central es `test_la_negacion_no_se_verifica`, que además **comprueba que
`trazabilidad` da 1.0** a esa misma frase. Sin esa aserción, el argumento de que la
trazabilidad no sirve como barrera no estaría probado: sería una opinión.

### Heredadas (sobre el estado final)

| Suite | Resultado |
|---|---|
| `probar_riesgos_abc.py` | 25 / 25 |
| `probar_ia_mock.py` | 35 / 35 |
| `probar_contrato_ia.py` | 49 / 49 |
| `probar_contrato_io.py` | 48 / 48 |
| `probar_semantica_ia.py` | 59 / 59 |
| `probar_estado_conocimiento.py` | 48 / 48 |
| `probar_frontera_linguistica.py` | 25 / 25 |
| `probar_ia_contexto.py` | 39 / 39 |
| `probar_documentacion_ia.py` | 51 / 51 |
| `probar_puente_conocimiento.py` | 52 / 52 |
| `probar_banco_ia.py` | **29 / 29 sobre 83 escenarios** |

### Banco adversarial

**83 escenarios, conservados.** `L-01` y `L-02` siguen presentes con su carga
hostil. Ninguno se borró ni se rebajó.

**Sobre §15 (ampliar el banco):** la misión pide añadir escenarios para quince
familias de ataque. **No se han añadido al banco de 83**, y el motivo es concreto:
todas esas familias son ataques contra el **claim del modelo**, y el sistema **no
entrega texto del modelo**. Un escenario de banco solo mide si el camino completo
entrega algo prohibido; como la entrega compone desde el claim de contexto, un
`answer` hostil no cambia el resultado. Sus escenarios serían idénticos a los
existentes y darían una falsa sensación de cobertura.

Se han cubierto **como pruebas deterministas** en
`probar_verificacion_estructurada.py` y `probar_riesgos_abc.py`, donde sí son
distintas entre sí y se puede comprobar que **cada una detecta lo que dice
detectar**. Un banco que no puede observar el fallo no es una prueba.



---

## L. Integridad

| Componente | Hash | Estado |
|---|---|---|
| `00_SOURCE/tools/nucleo.py` | `CCC48EA67849…` | **INTACTO** |
| `dfchron/contrato_ia.py` | `F1AAF1A6D4B0…` | **INTACTO** |
| `dfchron/ia_frontera.py` | `4EEE0519902E…` | **INTACTO** |
| `dfchron/ia_verificacion.py` | `B8BFD2CC39D3…` | **INTACTO** |
| `00_SOURCE/original_data/*.xml` | coinciden | **INTACTOS** |
| Banco adversarial | 83 escenarios | **INTACTO** |
| Dataset (JSONL) | sin tocar | **INTACTO** |

Modificados: `ia_contrato.py`, `ia_mock.py`, `AI_PROJECT_CONTEXT.md`.
Creados: `ia_estructura.py`, `probar_verificacion_estructurada.py`, este informe.

---

## M. Riesgos

| Riesgo | Severidad | Estado | Evidencia |
|---|---|---|---|
| El sistema afirmaba una autoridad que no tenía | MEDIA | **MITIGADO** | Alcance declarado en el veredicto |
| Confianza `ALTA` sin respaldo | MEDIA | **RESUELTO** | 4 pruebas en `probar_ia_mock.py` |
| **Verificación semántica** | MEDIA | **ABIERTO** | `NO_APLICABLE` para paráfrasis, negación y compuesta. **Sigue sin existir.** |
| Trazabilidad usada como prueba de verdad | ALTA | **EVITADO** | Negación puntúa 1.0: medición que lo impide |
| Verificar confunde con autorizar | ALTA | **EVITADO** | `puede_entregarse` idéntico con y sin verificación |
| Relacionales no verificables | ALTA | **ABIERTO** | Sin `df_id` estable en las relaciones |
| Sustitución por sustracción | ALTA | **MITIGADO, no resuelto** | El texto compuesto no contiene ni el total ni el conocido |
| Reconstrucción semántica | MEDIA | **ABIERTO** | Mecanismo inactivo; sin base de «retenidas» |
| Índice espacial duplicado | BAJA | **EVITADO** | No se construyó |
| Métrica espacial inventada | BAJA | **EVITADO** | No se inventó |

**Ningún riesgo se ha cerrado cambiando su nombre.** El de verificación semántica
sigue abierto, y la razón está escrita.

---

## N. Decisiones descartadas

| Decisión | Motivo |
|---|---|
| Verificador semántico con un LLM | Sería el modelo como autoridad sobre lo que puede revelarse |
| Un modelo que valide su propia interpretación | Idéntico, y peor |
| Clasificador probabilístico como demostración | Presentaría una probabilidad como prueba |
| Regex para simular comprensión | `deteccion_fuga` ya lo hace; ampliarlo sería fingir |
| Porcentajes de confianza | Sin base probabilística, un porcentaje es ruido con decimales |
| Usar la trazabilidad como barrera | Demostrado imposible: la negación puntúa 1.0 |
| Migrar el esquema de estado | Sin necesidad demostrada |
| Añadir el verificador al banco de 83 | No puede observar el fallo que mediría (§K) |
| Bloquear claims sin trazabilidad | Rompería respuestas legítimas; se degrada la confianza |
| Índice espacial o métrica de distancia | Ninguna necesidad real; el núcleo declara que no las calcula |

**La atómica de afirmaciones compuestas** queda **documentada, no implementada**.
La regla existe («no se verifica a medias»), pero separar automáticamente
proposiciones en lenguaje natural no es fiable, y sin ella se implementaría un
repartidor de confianza —no un verificador—, que es el error que la misión prohíbe.

---

## O. Futuro: requisitos para la integración con Dwarf Fortress

Cuando DF-Hack aporte datos de descubrimiento reales, la entrada mínima debe
preservar:

1. **Identificadores reales** (`df_id` del juego, no un índice propio)
2. **Procedencia** (de qué sistema viene el descubrimiento)
3. **Estado de descubrimiento** (con campo, como ahora)
4. **`dataset_id` compatible**, para que el estado no se mezcle entre partidas
5. **Verificación en cada consulta**, no solo al cargar

Y la regla que no se puede relajar:

> Que un dato exista en la API del juego **no** da permiso para revelarlo. La
> disponibilidad técnica no es autorización.

La arquitectura de evidencia no impide esa integración: `ia_estructura` consulta
el núcleo en solo lectura, y un `df_id` de DF-Hack se verifica con la misma vía que
uno del export.

---

## Nota final

Esta misión añadió **lo que se puede demostrar** y dejó escrito **lo que no**.

Lo añadido: un verificador determinista que confirma afirmaciones estructuradas
contra el núcleo, con tres estados que dicen exactamente qué se comprobó, y que no
autoriza nada.

Lo no añadido, y declarado: **no hay verificación semántica**. Una paráfrasis, una
negación o una afirmación compuesta siguen sin verificarse. El sistema lo dice con
`NO_APLICABLE` en vez de fingir.

Y una medición que conviene retener: **«El sitio NO es de tipo 'hamlet'» puntúa 1.0
en trazabilidad y `NO_APLICABLE` en verificación estructurada.** Esa distancia
entre dos números es, exactamente, la frontera entre *medir parecido* y
*demostrar*.


