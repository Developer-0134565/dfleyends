# Contexto operativo del proyecto (IA)

**Versión:** 1.0 · **Fecha:** 2026-10-03 · Ámbito: DF-Chronicles / capa de IA

> **Este documento es un CONTRATO OPERATIVO, no una nota informal.** Fija lo que
> está decidido, lo que está abierto y lo que está medido, para que una misión
> futura parta de la verdad y no de la intención. Si una afirmación aquí deja de
> ser cierta en el código, el documento es lo que está mal.

Regla de lectura que atraviesa todo el fichero: **se describe lo medido, no lo
deseado.** Lo que no existe no se escribe como «pendiente de confirmar»: se
declara ausente. Las cifras que aparecen son medidas; no hay estimaciones.

Documentos hermanos: `ai_data_contract.md` (el **formato**), `README.md` y
`ARCHITECTURE.md` (el sistema completo).

---

## Objetivo

Aplicación **local** para consultar los datos históricos que Dwarf Fortress
registra en sus exports de Legends. Sin red, sin dependencias externas, sin
`pip install`: solo biblioteca estándar de Python 3.11+.

La capa de IA de este proyecto **no** es un chat. Su objetivo es más estrecho y
está escrito para que no se amplíe por conveniencia:

> Dar al jugador respuestas sobre **su partida** que sean verdad, con su
> procedencia declarada, sin revelarle nada que su estado de descubrimiento no
> permita revelar, y sin que la capacidad lingüística de un modelo pueda ampliar
> ese conjunto.

De ahí sale la restricción que gobierna todo lo demás: el modelo es un
**componente no confiable** que se consume dentro de una arquitectura, nunca su
autoridad.

---

## Arquitectura

### Cadena de datos

```
legends.xml (CP437) + legends_plus.xml (UTF-8)
    -> cargar_legends        extracción, autodetección de codificación
    -> integrar_legends      fusión con procedencia por campo -> JSONL (20 secciones)
    -> validar_semantica     índice + consultas + referencias
    -> nucleo.py             LÓGICA DE DOMINIO (00_SOURCE/tools/)
    -> servicio.py           envelopes, límites, errores
    -> api.py                rutas HTTP, CORS (stdlib)
    -> web/ | site/ (Astro)  frontends que hablan solo con /api/...
```

### Cadena de IA

```
ia_contexto.py   recupera del dataset REAL y etiqueta
    -> ioc.contexto()      filtra por política (contrato_ia): lo FORBIDDEN no entra
    -> adaptador           frontera de ia_inferencia: invoca el modelo
    -> ioc.validar_salida()  valida la salida (FAIL CLOSED)
    -> ia_frontera.componer_seguro()  compone el texto que ve el jugador
    -> jugador
```

Dos propiedades de esta cadena, y ambas importan:

- Lo que llega al modelo ya viene filtrado por el contrato. `FORBIDDEN` no se
  «oculta»: no se envía. Mandar un secreto a un proveedor externo ya es
  divulgarlo.
- El texto final lo compone **el sistema** por composición literal de claims
  autorizados, no el modelo. `ia_frontera` es la frontera lingüística.

---

## Principios innegociables

1. **La UI nunca lee XML.** Habla solo con `/api/...` mediante `fetch()`. Sin
   `node_modules`, sin build. Lo verifica `test_la_ui_no_accede_a_los_xml`.
2. **La API nunca implementa lógica de DF.** Traduce rutas a llamadas al
   servicio. Toda la lógica de dominio está en `nucleo.py`.
3. **El núcleo no sabe rutas absolutas.** Resuelve todo desde `__file__` o
   `DFCHRON_ROOT`, para que el proyecto se pueda mover sin editar código.
4. **Ningún recorte es silencioso.** Toda lista declara `truncado`; la UI lo
   pinta como aviso.
5. **VERDAD ≠ VISIBILIDAD ≠ USO INTERNO ≠ DIVULGACIÓN.** Este es el corazón del
   sistema (`contrato_ia.py`). Un dato puede ser verdadero y aun así no poder
   decirse. Las cuatro dimensiones son independientes y se validan por separado.
6. **El modelo NUNCA recibe un dato `FORBIDDEN`**, ni para razonar. No «no debe
   usarlo»: no lo recibe.
7. **El modelo NO redacta el texto que ve el jugador.** Decide *qué* afirmaciones
   autorizadas se dicen; el texto lo compone el sistema. Es una decisión de esta
   misión.

Los cuatro primeros están en `dfchron/__init__.py` y `ARCHITECTURE.md`; los tres
últimos en `contrato_ia.py`, `ia_contrato.py` e `ia_frontera.py`.

---

## Decisiones cerradas

Decisiones tomadas, con su porqué y su evidencia. No se revierten sin una misión
que lo mida.

| Decisión | Por qué | Evidencia |
|---|---|---|
| `contrato_ia.py` fija **4 fuentes** (`PLAYER_KNOWLEDGE`, `WORLD_KNOWLEDGE`, `EXTERNAL_KNOWLEDGE`, `INFERENCE`), **4 `truth_status`** (`FACT`, `DERIVED`, `UNKNOWN`, `INFERENCE`/`INTERPRETATION`), **3 visibilidades** y **3 divulgaciones**. Afirmaciones de solo lectura (`Afirmacion`, `_SolaLectura`). Única puerta de cambio: `convertir()` con motivo. | La verdad de un dato y el permiso para revelarlo son cosas distintas. La inmutabilidad hace que una afirmación no pueda subir de certeza sin dejar rastro de quién lo hizo y por qué. | 49 pruebas de contrato + 59 de semántica congelada. |
| `ia_contrato.py`: `ContextoIA` y `RespuestaIA` de solo lectura; `FORBIDDEN` no entra **ni en modo razonamiento**. | La IA es consumidora de la arquitectura, nunca su autoridad. No se le delega ninguna decisión de verdad, visibilidad o divulgación. | 48 pruebas (`probar_contrato_io`). |
| **`ia_frontera.py` (nuevo, esta misión): el texto que ve el jugador lo compone el SISTEMA**, por composición literal de los claims de contexto autorizados. Es una **lista blanca** de vocabulario. | Seis vectores de fuga medidos (paráfrasis, referencia espacial, sustracción, distancia, nombre inventado, consejo filtrador) tenían una sola causa común: que el modelo redactara el texto. Con lista blanca, cada palabra con carga informativa tiene que existir en el claim que la respalda. Una lista negra es infinita; la blanca es finita y auditada. | 25 pruebas lingüísticas + 12 de inferencia. Banco 83/83, 0 fugas. |
| `estado_conocimiento.py`: el estado de ejecución (qué ha descubierto el jugador) es **separado** del dataset histórico. | El dataset es una partida cerrada e inmutable. Lo que el jugador va descubriendo es de otra naturaleza y no puede contaminar la fuente de verdad. | 48 pruebas (`probar_estado_conocimiento`). |
| `ia_inferencia.py`: `inferir()` es el camino real. El presupuesto es un **techo**, no un objetivo. Un `Perfil` **NO** cambia las reglas de divulgación. | La capacidad lingüística del modelo no amplía el conjunto de información divulgable: un modelo más potente recibe exactamente el mismo contexto. | 12 pruebas (`probar_frontera_inferencia`). |

---

## Decisiones abiertas

No decidido. No se inventa. Cada punto dice por qué sigue abierto.

### Qué cerró esta misión y qué dejó abierto

| Riesgo | Estado tras esta misión | Dónde está |
|---|---|---|
| **Autoridad del validador** | **MITIGADO**: el sistema ya declara qué verifica y qué no, y la confianza ya no se afirma sin respaldo medible. La verificación **semántica** sigue sin existir y sin decidir quién la haría. | «Seguridad» |
| **Memoria entre turnos** | **CERRADO COMO NO-APLICABLE**: se demostró por ausencia que no existe memoria. Se añadió la defensa que faltaba al leer el estado. | «Fugas conocidas» |
| **Índice espacial** | **NO IMPLEMENTADO, PERO LA AFIRMACIÓN ANTERIOR ERA FALSA**: el índice **sí existe** en el núcleo y no lo usa la IA. La defensa la da la frontera, no el índice. | «Seguridad» |

- **Verificación semántica: quién la ejecuta y con qué autoridad.** Sigue sin
  decidir, y es la decisión que bloquea el resto. **Lo que sí se ha hecho** es
  delimitar su alcance con precisión: `ia_verificacion.alcance()` declara qué
  comprueba el sistema y qué no. Ningún consumidor puede ya leer `claims_ok`
  como «el sistema comprobó que es verdad».
- **`knowledge_owner`: la autorización NO depende del agente.** Hoy solo existe
  `PLAYER`, de modo que la suposición no se nota. Añadir `DWARF` o `GOBLIN`
  exigiría esa dimensión nueva. Se deja la puerta, no la respuesta.
- **Memoria de conversación.** No existe y no se ha inventado. Lo que sí se ha
  preparado son las interfaces mínimas justificadas: la frontera por la que
  tendría que pasar cualquier recuerdo (`componer_seguro`).
- **Relaciones espaciales derivadas (distancia, rumbo, adyacencia).** El núcleo
  declara que **no las calcula**, y los XML no definen la métrica. Sigue sin
  construirse: hacerlo sería inventar una medida que el dataset no sostiene.

---

## Perspectivas de conocimiento (idea futura, NO implementada)

Hoy el sistema tiene **una** perspectiva: la del jugador. El estado del jugador
(`estado_conocimiento.py`) responde «qué sabe este jugador».

Registrado como posibilidad, **no como funcionalidad**:

| Perspectiva | Qué significaría | Estado |
|-------------|------------------|--------|
| Jugador | Lo que ha descubierto. **Existe hoy** | IMPLEMENTADA |
| Enanos | Lo que una figura concreta del mundo sabe | **NO EXISTE** |
| Goblins | Ídem, para otra especie | **NO EXISTE** |
| Criaturas | Lo que sabe cada entidad viva | **NO EXISTE** |

Por qué es interesante: un enano puede saber algo que el jugador ignora. Si algún
día se quisiera, la granularidad por `df_id` que ya existe lo haría natural. Pero
**no se ha implementado nada** de esto, y no debe darse por hecho.

Riesgo conocido de esa idea: varias perspectivas multiplican las vías por las que
un dato puede filtrarse. Cada perspectiva nueva necesita su propia política, no
compartir la del jugador.

---

## Qué sabe el modelo, y qué puede decir

> **La IA puede conocer más cosas de las que conoce el jugador, pero nunca debe
> confundir conocer algo con tener permiso para revelarlo.**

La regla literal, en `contrato_ia.REGLA`:

> La verdad de un dato y el permiso para revelarlo son cosas diferentes.

Ejemplo, ya documentado y probado: la IA puede tener acceso interno a la
**ubicación de una veta de diamantes** que el jugador no ha descubierto. Ese dato
es `FACT` (existe), es `PLAYER_HIDDEN` (el jugador no lo sabe) y su `disclosure`
es `FORBIDDEN`. Que sea verdad no lo hace revelable.

Lo que **no** está resuelto, y hay que decirlo: la detección de fugas es un
esqueleto heurístico. Detecta coordenadas estructuradas, pero **no** detecta una
paráfrasis sin cifras («está justo al norte»). Eso exige comprensión del
lenguaje, y aquí no la hay. Está declarado como límite, no como garantía.

### La separación de responsabilidades

```
El modelo propone.  El núcleo verifica.
La política autoriza. El compositor expresa.
```

Ninguna se delega. El modelo no salta ninguna capa: elige entre opciones que el
sistema ya le dio, y su salida se revalida.

---

## Versión de la evidencia (cierre PRE-LLM)

La evidencia **declara de qué estado del mundo** salió:

```text
evidencia.state_version = dataset_id real (v1-04170363943d4ba1)
```

Viene de `dataset_version.json`, que se deriva del **SHA-256 del contenido**, no
de un reloj. Por eso es determinista y cambia cuando cambia el **contenido
extraído**.

> **Corrección P1.1 (2026-10-04).** Este texto decía antes «cambia exactamente
> cuando cambia el mundo». **Eso es falso y está demostrado** con datos reales
> en `P1_VERSIONADO_MUNDO_VIVO.md` §20.1: dos mundos con el mismo contenido
> reciben el MISMO `dataset_id`, y el mundo puede cambiar sin que el contenido
> extraído cambie. `state_version` identifica **contenido**, no **estado**.
> La identidad del mundo (`world_name`, `world_folder`) se capturó aparte en
> P1.1 y **no** es estado. Ver `P1.1_IDENTIDAD_MUNDO.md` §7.

`evidencia_es_actual(ev, version_actual)` es **fail-closed**: solo es actual la
evidencia que declara versión y coincide. La que no la declara, es `UNKNOWN` y
no sostiene nada. `verificar_afirmacion(..., version_actual=…)` devuelve
`NO_VERIFICADA` para evidencia de otro mundo.

**Lo que esto NO es:** `dataset_id` no es un reloj. No hay ticks, ni turnos, ni
caducidad. Cerró el invariante I14 (una evidencia de t0 no valida t1), no la
temporalidad completa. Ver `ARCHITECTURE_DECISIONS.md` D09.

---

## Estado PRE-LLM

| Qué | Estado |
|-----|--------|
| Contrato congelado | `08_DATABASE/AI_PRE_LLM_CONTRACT.md` |
| Gate previo al LLM | `probar_gate_pre_ia.py`, 15 invariantes, **PASS** |
| Conclusión | **PRE-LLM CERRADO CON RESERVAS** |
| Limitaciones abiertas | `INFORME_CIERRE_PRE_IA.md` §E.3 |

Las reservas son reales: verificación semántica, relaciones complejas, caducidad
temporal y estado en vivo **siguen sin demostrarse**. No están resueltas, y
ningún documento debe leerlas como resueltas.

---

## Estado actual

Cifras medidas de la capa de IA:

| Suite | Módulo que cubre | Pruebas |
|---|---|---|
| `probar_contrato_ia.py` | `contrato_ia.py` | 49 |
| `probar_contrato_io.py` | `ia_contrato.py` | 48 |
| `probar_semantica_ia.py` | semántica congelada (144 combinaciones) | 59 |
| `probar_ia_mock.py` | `ia_mock.py` (flujo completo sin LLM) | 35 |
| `probar_ia_contexto.py` | `ia_contexto.py` (recuperación real) | 39 |
| `probar_puente_conocimiento.py` | `ia_conocimiento.py` (núcleo → afirmaciones) | 52 |
| `probar_estado_conocimiento.py` | `estado_conocimiento.py` | 48 |
| `probar_banco_ia.py` | banco adversarial (83 escenarios) | 29 |
| `probar_frontera_inferencia.py` | `ia_inferencia.py` | 12 |
| `probar_frontera_linguistica.py` | `ia_frontera.py` | 25 |

**Banco adversarial:** 83 escenarios, **0 fugas, 0 falsos negativos, 0 falsos
positivos**.

### La capa de estado del jugador

`estado_conocimiento.py` es **estado de ejecución**, no parte de la historia:
vive fuera del dataset y se puede borrar sin tocar un solo byte histórico. Sin
él, `WORLD_KNOWLEDGE` estaría perfecto y `PLAYER_KNOWLEDGE` no tendría dónde
apoyarse, porque `legends.xml` **no registra qué descubrió el jugador**.

* Granularidad: identidad por `df_id`. Soportado para `figura`, `sitio`,
  `entidad`, `artefacto` y `evento`. **No** para `relacion`: no tienen
  identificador estable, e inventarlo sería fabricar una granularidad que el
  dataset no sostiene.
* Dos niveles, ambos derivados de datos reales: **entidad** (el jugador conoce el
  sitio 87) y **campo** (el jugador conoce las *coordenadas* del sitio 87).
* El estado lleva `dataset_id`: si el dataset cambia, el estado guardado deja de
  ser compatible y se dice, en vez de seguir mezclando dos mundos distintos.

Tres reglas que no se negocian:

1. **Conocido no es verdad.** `conocido=True` dice qué sabe el jugador; la verdad
   la sigue dictando el núcleo (`FACT`/`DERIVED`/`UNKNOWN`).
2. **Conocido no es revelable.** El `disclosure` no cambia por ser conocido.
3. **Nada se autodescubre.** Que el núcleo lo tenga o la web lo muestre **no**
   marca nada como conocido.

Lo que esta capa **no** puede hacer: marcar `PLAYER_VISIBLE` por el hecho de
conocer, decidir si algo es revelable, ni cambiar una sola dimensión de una
afirmación. `no_descubierto` se decide en el puente (`ia_conocimiento.py`), no
en el estado.

Lo que **no** existe, para que una misión no lo dé por hecho: ningún LLM
conectado, ningún SDK de IA, ningún endpoint IA (`/api/ia`, `/api/ask` y
similares son 404), ningún RAG / embeddings / vectorstore, ningún mod de DFHack,
ningún perfil de hardware definido.

---

## Modelo de conocimiento

Una afirmación (`afirmacion()`) tiene cuatro dimensiones independientes. Ninguna
se deduce de otra, y una combinación incoherente no es «un dato raro»: es un
error de contrato.

**1. Fuente (`knowledge_source`) — de dónde sale el dato**

| Fuente | Significado |
|---|---|
| `PLAYER_KNOWLEDGE` | Lo sabe el jugador por haberlo experimentingado. |
| `WORLD_KNOWLEDGE` | Está en el mundo; el sistema lo ha leído del dataset. |
| `EXTERNAL_KNOWLEDGE` | Viene de fuera de esta partida (documentación, internet). |
| `INFERENCE` | No viene de ningún sitio: **se produce**. |

`INFERENCE` es a la vez la cuarta fuente y su propio estado epistemológico.
Comparte valor con la constante `INTERPRETATION` del núcleo a propósito: son la
misma idea, y dos constantes distintas serían dos verdades.

Regla adicional: solo `PLAYER_KNOWLEDGE` y `WORLD_KNOWLEDGE` pueden describir el
estado de **esta** partida (`FUENTES_DE_ESTADO`). Las otras dos no pueden: una
es del jugador, la otra no es de este mundo.

**2. Certeza (`truth_status`)**

| Estado | Significado |
|---|---|
| `FACT` | Está en el XML. |
| `DERIVED` | Calculado con una regla declarada, que viaja con el dato. |
| `UNKNOWN` | No se puede determinar. Nunca se convierte en suposición. |
| `INFERENCE` / `INTERPRETATION` | Lectura, no hecho. |

`FACT` y `DERIVED` se importan del núcleo para que no haya dos definiciones de
lo mismo.

**3. Visibilidad** y **4. Divulgación** se tratan en sus propias secciones,
porque son las que más se confunden con las dos anteriores.

Las afirmaciones son **de solo lectura**. Se envuelven en `_SolaLectura`: no se
puede mutar un campo del contrato sin pasar por la puerta explícita
`convertir(nueva_certeza, motivo)`. La razón es que una afirmación que sube sola
de `UNKNOWN` a `FACT` es exactamente el fallo que el sistema existe para impedir.

### Verificación: qué se comprueba y qué no

Verificar **no** autoriza a divulgar. Son ejes independientes, y el sistema los
mantiene separados:

| Eje | Qué significa | Módulo |
|---|---|---|
| Verdad (`truth_status`) | Qué clase de dato es: `FACT`, `DERIVED`, `UNKNOWN`, `INFERENCE` | `contrato_ia` |
| **Verificación** | Qué ha comprobado el sistema **y hasta dónde** | `ia_verificacion`, `ia_estructura` |
| Visibilidad | Si el jugador lo conoce | `contrato_ia` |
| Divulgación | Si puede mostrarse ahora | `contrato_ia` |

Hay dos capas de verificación, y es importante no confundirlas.

**1. Verificación estructural** (`ia_verificacion.py`). Mide la *trazabilidad*:
qué proporción de las palabras con carga informativa del texto de un claim tienen
respaldo en los claims que lo sostienen. Es una **medida informativa**, y su
límite es real y medido:

| Caso | Fracción |
|---|---|
| Respaldo total | 1.0 |
| **Negación** («El sitio **NO** es de tipo X») | **1.0** |
| **Afirmación opuesta** | **1.0** |
| Parafrasis («La fortaleza…» en vez de «El sitio…») | 0.67 |
| Compuesta con una parte falsa | 0.75 |

Una negación conserva el 100 % del vocabulario, así que **la trazabilidad es
ciega a la negación y a la paráfrasis**. Por eso **no es una barrera de
seguridad**: solo informa la confianza y queda en el veredicto. La barrera sigue
siendo `ia_frontera`.

**2. Verificación estructurada** (`ia_estructura.py`). Sí es determinista, y es
lo único que el sistema puede demostrar. Comprueba afirmaciones que encajan con
una **plantilla declarada** y cuya evidencia apunta a `(entidad, df_id, campo)`:

```
claim     : "El sitio es de tipo 'hamlet'."
evidencia : {entidad: sitio, df_id: "112", datos_utilizados: [tipo]}
nucleo    : ficha_sitio("112")["tipo"] == "hamlet"   -> VERIFICADA
```

Tres estados, y cada uno dice lo que significa:

| Estado | Cuándo | Qué NO significa |
|---|---|---|
| `VERIFICADA` | El núcleo confirma ese campo con ese valor | No dice nada más allá de **esa** proposición |
| `NO_VERIFICADA` | Hay plantilla, pero el núcleo **contradice** el valor | Marca fabricación sobre referencia real |
| `NO_APLICABLE` | No hay plantilla que encaje | **No se afirma nada**: ni falso ni verdadero |

`NO_APLICABLE` es el estado honesto para una paráfrasis, una negación o una
afirmación compuesta. El sistema **no verifica a medias**: una frase con dos
proposiciones no se verifica aunque una sea cierta, porque verificar una parte y
dar por verificada la frase entera es exactamente el error a evitar.

**Lo que no se ha hecho, y por qué:** no hay verificador semántico. No se ha
usado un LLM como juez de verdad (sería el modelo como autoridad), ni un
clasificador probabilístico presentado como demostración, ni regex que simulen
comprensión. Una paráfrasis sigue sin verificarse, y eso se declara.

---

## Procedencia

`evidencia(entidad, df_id, datos_utilizados, funcion=None, fuente=None)` es el
rastro de un dato hasta el punto del dataset del que salió:

```python
cia.evidencia("sitio", "112", ["type"])   # entidad, df_id, datos usados
```

**Sin evidencia no se afirma.** Es la regla literal del contrato: sin esto, una
afirmación sería plausible pero no auditable, y el sistema no puede permitirse
«plausible».

Única excepción: `UNKNOWN` puede construirse sin evidencia, pero **lleva
motivo**, y el motivo es su evidencia: decir que no consta algo exige declarar
qué se buscó.

`ia_conocimiento.py` es el puente que cumple esta regla: traduce objetos del
núcleo a afirmaciones, y cada una sale con su evidencia. 52 pruebas.

---

## Visibilidad

`PLAYER_VISIBLE`, `PLAYER_HIDDEN`, `EXTERNAL`.

La visibilidad responde a **quién** puede ver el dato. No responde a si puede
decirse. Por eso es una dimensión aparte:

> Un dato `PLAYER_HIDDEN` puede ser `FACT` y seguir sin poder revelarse.

Ese es el error que el módulo existe para impedir. Si `puede_revelarse()`
comprobara solo `truth_status`, un `FACT` de `WORLD_KNOWLEDGE` pasaría
directamente, y sería justo el fallo buscado.

Restricción de coherencia (`contrato_ia.py`, línea 411): `visibility = EXTERNAL`
solo es admisible con `knowledge_source = EXTERNAL_KNOWLEDGE`. Se cerró por
auditoría: la combinación `WORLD_KNOWLEDGE` + `FACT` + `EXTERNAL` + `ALLOWED`
pasaba de no-divulgable a afirmable, y por `puede_revelarse()` escapaba.

---

## Divulgación

`ALLOWED`, `FORBIDDEN`, `CONDITIONAL`.

`puede_revelarse()` es **conservador**: ante cualquier duda, `False`. Si el
contrato no valida la afirmación, no sale.

Dos consecuencias que hay que tener presentes:

- `CONDITIONAL` no es «casi permitido». Su resolución no está automatizada: una
  afirmación condicional que llega al jugador tiene que haberse resuelto antes, y
  resolverla es una decisión del contrato, no del modelo.
- Quien razona sobre lo oculto **no lo recibe**. Lo que queda para razonar es
  determinista: `ia_conocimiento.py` razona sobre el estado completo y produce
  afirmaciones ya etiquetadas; el modelo recibe el resultado etiquetado, no el
  secreto.

Regla que se repite en el código: un `Perfil` no cambia las reglas de divulgación.
El presupuesto limita cuánto ve el modelo; no redefine qué puede revelar.

---

## Inferencia

`INFERENCE` es la única fuente que **se produce** en vez de leerse. Es también
un `truth_status`. Su estado natural es el estado epistemológico, y por eso
comparte valor con `INTERPRETATION` del núcleo.

Reglas que el contrato impone:

- Una inferencia **no puede ser `FACT`**. Aunque el conjunto completo de hechos
  esté disponible para razonar, el resultado sigue siendo lectura.
- Una inferencia **no describe el estado de esta partida** por derecho propio: no
  está en `FUENTES_DE_ESTADO`.
- Reducir el contexto **no introduce** datos prohibidos: `inferir()` cierra antes
  de llamar al modelo si el contexto no cabe, en vez de recortar a lo oculto
  (`probar_frontera_inferencia`, caso 7).

El presupuesto (`Presupuesto`) tiene cinco límites: `max_input_chars` (barrera
barata, antes de contar tokens), `max_context_tokens`, `max_input_tokens`,
`max_output_tokens` y `max_claims`, además de qué se hace al excederlos.

`estimar_tokens()` es una estimación **conservadora**: ~3,6 caracteres por token,
redondeando **hacia arriba**. Quedarse corto dejaría pasar un contexto mayor del
permitido; quedarse largo solo cuesta una reducción de más. El error va siempre a
favor de la seguridad. Cuando exista un tokenizador real, se inyecta con
`Presupuesto(contar=...)` y el contrato **no cambia**.

`Adaptador` es la interfaz hacia el runtime, con fallo cerrado en cada error. La
clase concreta sin implementar falla siempre: no hay proveedor elegido, y elegirlo
sin medir sería inventar.

---

## Claims

Un claim es la afirmación que el modelo devuelve. `RespuestaIA` lleva la lista, y
cada claim tiene que ser reconstruible desde la evidencia, no solo parecerse a
uno.

**Estructura de la evidencia**

```python
evidencia(entidad, df_id, datos_utilizados, funcion=None, fuente=None)
        │        │       │
        │        │       └─ qué campos del XML se leyeron
        │        └─ el identificador en el dataset
        └─ sobre qué entidad del mundo
```

**Sin evidencia no se afirma** (salvo `UNKNOWN`, y entonces con motivo). Esta es
la regla que impide que un modelo rellene un hueco plausible: no puede afirmar
sobre un hueco, y si no hay dato, la respuesta honesta es `UNKNOWN` con su
motivo.

**Solo se admiten combinaciones coherentes.** Ejemplos de lo que se rechaza por
incoherencia, no por secreto:

| Combinación | Por qué no cabe |
|---|---|
| `EXTERNAL_KNOWLEDGE` + `FACT` sobre esta partida | Una fuente externa no describe esta partida. |
| `INFERENCE` + `FACT` | Una inferencia es lectura, no hecho. |
| `EXTERNAL` (visibilidad) + fuente distinta de `EXTERNAL_KNOWLEDGE` | Son la misma cosa con dos nombres; se cerró por auditoría. |
| Afirmación que el contrato no valida | `puede_revelarse()` devuelve `False` antes de mirar nada más. |

Hay un caso que conviene no confundir: `INFERENCE` + `FORBIDDEN` **no** es
rechazado por el contrato —se construye y no se revela—, y por eso **no** está
en la tabla de prohibidas. Si algún día debe rechazarse, es un cambio de
contrato, no un ajuste de este documento.

Lo que un claim **no** puede hacer: elevar su propia confianza, tratar una
ausencia de evidencia como `FACT`, ni usar una afirmación que el contrato no
valida. Las tres cosas las decide `contrato_ia`, antes y después del modelo.

---

## Seguridad

Cuatro capas, **en este orden**. La orden importa: cada capa assume que la
anterior ya pasó, y ninguna sustituye a otra.

**1. `contrato_ia` — decide verdad, visibilidad y divulgación.**
Es la ley. Todo lo demás verifica que se le haya obedecido.

**2. `ia_contrato` — valida procedencia, tipo y consistencia de los claims.**
`validar_salida()` es la puerta y falla cerrada: cualquier error deja la
respuesta sin texto.

**3. `ia_frontera` — comprueba que el TEXTO no exceda a los claims.**
Lista blanca de vocabulario: cada palabra con carga informativa del texto tiene
que existir en el claim que la respalda. Además comprueba que no haya coordenadas
en el texto entregado. No es un filtro de palabras prohibidas: es lo contrario,
una lista finita y auditada de lo que **sí** puede aparecer.

**4. `deteccion_fuga` + `detectar_reconstruccion`.**
`deteccion_fuga` (`ia_contrato.py`) es la heurística determinista de fuga
indirecta por canal lateral. `detectar_reconstruccion` (`ia_frontera.py`)
comprueba si el texto reconstruye por cuenta un dato retenido.

Es **profundidad, no sustitución**. Si se desactivara la capa 3 el sistema
seguiría siendo seguro frente a lo que ya sabía; lo que se perdería es la
garantía de que el texto no exceda a los claims. Por eso hay cuatro capas y no
un muro único.

La frontera **no depende** del LLM. No es que se le pida al modelo que se
comporte: la decisión la toma una función que devuelve `False`, y el texto que
ve el jugador lo compone el sistema. Si el modelo fuera un loro, o un adversario
que quiere filtrar, el resultado sería el mismo. **El modelo es un componente no
confiable**: propone, y el sistema decide qué está autorizado.

En una frase, que es la que gobierna el diseño entero:

> La proteccion no puede depender del LLM. El sistema no pide permiso al
> modelo; le quita la posibilidad de escribir lo que el jugador lee. Cambiar de
> modelo, de perfil o de hardware no cambia una sola regla de divulgacion.

> **La verdad de un dato y el permiso para revelarlo son cosas diferentes.**

**El `answer` del modelo ya no se entrega.** Se guarda como `answer_del_modelo`
y nada más, solo para diagnóstico. El jugador lee únicamente lo que compone el
sistema. Es el cambio de esta misión, y es lo que cierra los vectores que antes
pasaban.

### Determinismo

La frontera es determinista y **no depende del LLM**: misma entrada, mismo
veredicto, byte a byte. Sin `random`, sin UUID, sin relojes, sin `timestamp`, sin
`datetime.now()`, sin orden de `set` sensible al orden, sin locale ni timezone
implícitos. El presupuesto de `ia_inferencia.py` es un **techo, no un
objetivo**: más VRAM no amplía lo que cabe, y cambiar de perfil no cambia una
sola regla de divulgación.

---

## Fugas conocidas

**En el banco no hay fugas medidas abiertas**: 83 escenarios, 0 fugas, 0 falsos
negativos, 0 falsos positivos. Eso es lo que se ha medido y es lo único que se
afirma aquí.

Lo que persiste son **límites de clase**, que no son fugas del banco pero
impiden declarar el sistema cerrado:

- **No se resuelve la reconstrucción puramente semántica o espacial** si el texto
  lo compusiera un tercero. Hoy está cerrado porque el sistema compone el texto y
  aplica lista blanca, **no** porque exista un detector semántico. Si mañana un
  componente externo redacta, esa defensa se pierde y no hay nada detrás que la
  reponga.
- **La lista blanca puede marcar texto legítimo** si un adaptador futuro trae
  redacción propia. Es un falso positivo conocido, no una fuga. Consecuencia
  práctica: un adaptador con redacción propia no funcionará tal cual.
- **La memoria entre turnos NO existe, y se demostró por ausencia.** No hay
  historial, ni contexto resumido, ni embeddings, ni caché de conversación. Lo
  único que cruza peticiones es `estado_conocimiento.json`, que transporta
  `tipo:df_id` y un campo — **identificadores, no texto de turnos**. El navegador
  solo guarda el índice de página (`sessionStorage['pag']`), ningún contenido.
  Por eso la acumulación entre turnos no es un problema mitigado: es un problema
  **que no puede ocurrir mientras su premisa sea falsa**.
- **Lo que sí se corrigió en la memoria:** `_validar_esquema` validaba la FORMA del
  fichero de estado pero no el CONTENIDO de sus entradas. Editar el fichero a mano
  bastaba para introducir una clave bien formada y que el sistema la aceptara al
  leer. Ahora cada entrada se revalida con el mismo `_validar()` que se usa al
  escribir: leer no es más permisivo que escribir.
- **Corrección importante sobre el índice espacial.** La afirmación anterior de que
  «no existe índice espacial» era **FALSA**. El índice sí existe
  (`nucleo.py`: `sitios_por_coordenada`, `capas_por_coordenada`) y hay endpoints
  que lo consultan por coordenada. **La IA no lo usa**: el contexto se construye
  desde fichas de entidades, no desde índices espaciales. Y no se ha construido un
  índice nuevo, porque no lo necesita: la defensa la da la frontera, y un índice de
  vecinos exigiría inventar una métrica de distancia que los XML no definen.
- **`detectar_reconstruccion` solo ve aritmética explícita**, con operandos
  autorizados y una lista de retenidas que **pasa el llamante**. Por defecto esa
  lista está vacía: **no detecta nada**. Es una función disponible, no una
  garantía en funcionamiento.
- **La verificación semántica sigue sin existir.** El sistema comprueba
  procedencia, tipo, permiso y trazabilidad estructural. **No** comprueba que una
  frase sea consecuencia de otra, ni que sea verdadera. Ahora eso está **declarado**
  en `ia_verificacion.alcance()` y viaja en cada veredicto, para que no se lea como
  una garantía que el sistema nunca dio.

Declarar esto aquí es lo que permite que «0 fugas en el banco» siga siendo una
afirmación precisa y no una afirmación de deja-vu.

---

## Testing

Diez suites Python, más el banco adversarial:

```cmd
python dfchron/pruebas/probar_contrato_ia.py
python dfchron/pruebas/probar_contrato_io.py
python dfchron/pruebas/probar_semantica_ia.py
python dfchron/pruebas/probar_ia_mock.py
python dfchron/pruebas/probar_ia_contexto.py
python dfchron/pruebas/probar_puente_conocimiento.py
python dfchron/pruebas/probar_estado_conocimiento.py
python dfchron/pruebas/probar_banco_ia.py
python dfchron/pruebas/probar_frontera_inferencia.py
python dfchron/pruebas/probar_frontera_linguistica.py
python dfchron/pruebas/probar_riesgos_abc.py
```

Si se necesita la salida completa a fichero, usar `cmd /c`:

```cmd
cmd /c "python dfchron/pruebas/probar_frontera_linguistica.py > out.txt 2>&1"
```

Motivo: PowerShell trata de forma distinta la redirección de `stderr` cuando la
salida se canaliza, y el resumen de estas pruebas escribe ahí. Es un detalle del
entorno, no de las pruebas.

Además, `probar_documentacion_ia.py` **vigila estos documentos**: falla si lo que
se afirma aquí deja de ser cierto en el código. Se puso porque una auditoría
anterior encontró cuatro afirmaciones falsas en la documentación.

**Las tres clases del benchmark no se pueden confundir.** La distinción es la
razón de que exista el instrumento:

| Clase | Significado |
|---|---|
| `OK` | El modelo acertó y el validador lo dejó pasar. |
| `MODELO_INCORRECTO` | El modelo dijo algo inválido. |
| `VALIDADOR_BLOQUEO` | El validador hizo su trabajo. **Esto es un éxito.** |
| `CONTRATO` | El sistema falló antes de llegar al modelo. |

Un modelo mediocre con un buen validador sigue siendo seguro. Medir solo aciertos
convertiría el benchmark en un instrumento de autobombo. Por eso `_clase_de()`
está en un único sitio: para que las dos rutas del benchmark no puedan discrepar
en cómo etiquetan un mismo desenlace.

---

## Benchmark

```python
ia_inferencia.ejecutar_benchmark(adaptador, con_frontera=True)
```

Con `con_frontera=True` (el valor por defecto) **cada escenario recorre
`inferir()` de extremo a extremo**: presupuesto, adaptador, `normalizar_salida()`,
validación y composición. Es el camino real.

**Defecto corregido en esta misión.** Antes esta función recorría el banco por
`evaluar_banco_ia.ejecutar_escenario`, que va por `MockIA`: el `adaptador`
recibido se guardaba en `config` y **no se invocaba nunca**. Un benchmark «con
modelo real» medía, en realidad, el guion del mock. Era un instrumento que no
midía lo que decía medir.

Recorrer el camino real es además la única forma de distinguir las cuatro
combinaciones que el benchmark existe para separar:

```
modelo mediocre + seguridad correcta
modelo bueno    + seguridad incorrecta
modelo bueno    + seguridad correcta
modelo hostil   + seguridad correcta
```

Con `con_frontera=False` se conserva el recorrido por `MockIA`, que sirve para
comprobar el instrumento sin depender de ningún runtime. No es el default a
propósito: por defecto se mide la verdad.

Los campos `tokens_entrada`, `tokens_salida` y `tokens_totales` **siguen a
`None`** porque ningún runtime los ha dado todavía. No se rellenan con
estimaciones: se rellenarán cuando exista un runtime real. `latencia_ms` sí se
mide.

---

## Riesgos

| Riesgo | Severidad | Estado |
|---|---|---|
| **Autoridad del validador.** El sistema validaba la *referencia* pero no el *contenido*, y su veredicto no lo decía. | MEDIA | **MITIGADO**: `ia_verificacion.py` declara el alcance y la confianza exige respaldo medible. La verificación semántica sigue ausente. |
| Memoria multi-turno. Si se añade, la acumulación de turnos puede filtrar. | ALTA | **NO APLICABLE (demostrado por ausencia)**, más la defensa que faltaba al leer el estado |
| Índice espacial. La afirmación previa de que no existía era **falsa**. | MEDIA | **CORREGIDO**: existe en el núcleo y no lo usa la IA. No se construye otro: la frontera basta |
| Verificación semántica: quién la ejecuta y con qué autoridad. | MEDIA | **ABIERTO** — bloquea el resto |
| Lista blanca con falsos positivos ante un adaptador con redacción propia. | BAJA | Conocido, declarado |
| `detectar_reconstruccion` inactivo por defecto (lista de retenidas vacía). | BAJA | Conocido, declarado |
| Perfiles de hardware no definidos, por falta de medición. | BAJA | Intencional |

Ninguno de estos riesgos está cerrado por la existencia del banco en verde: el
banco mide lo que mide, y esos límites quedan fuera de su alcance. El riesgo de
memoria es el único que **cambió de categoría**: de «abierto y sin medir» a «no
aplicable y demostrado por ausencia».

---

## Próximas_mediciones

Cada punto bloquea una decisión abierta. No se proponen por completitud: sin su
medida, la decisión no se puede tomar.

1. **Decidir la autoridad del validador semántico.** Es lo primero porque bloquea
   todo lo demás. Requiere medir qué haría falta para distinguir un error
   semántico de uno formal, y qué coste tendría.
2. **Medir si hace falta índice espacial.** Depende de si aparece un consumidor
   real que exija referencias espaciales. Mientras no exista, construirlo sería
   añadir superficie de ataque sin demanda.
3. **Medir consumo real de tokens con un runtime.** Con eso se sustituye
   `estimar_tokens()` por un conteo real y se dejan de emitir `None` en el
   benchmark. También permitiría decidir si los valores del presupuesto son
   suficientes o demasiado conservadores.
4. **Medir si el estado del jugador necesita persistencia.** Determina si el
   riesgo ALTA se materializa. Si se decide que sí, hay que volver a auditar
   «Riesgos» (§17) antes de tratarlo como resuelto.

Complementarias, en el mismo criterio: qué respuesta da un adaptador con
redacción propia frente a la lista blanca, y qué ocurre al pasar una lista de
retenidas real a `detectar_reconstruccion`. Ninguna de las dos se puede responder
con el banco actual.
