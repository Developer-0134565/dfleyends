# ARCHITECTURE DECISIONS

Registro de decisiones arquitectónicas de **DF-Chronicles**.

Cada ficha tiene: **contexto** (qué se decidió), **decisión**, **motivo**, **consecuencias** y **estado**.

**Estados posibles:**

| Estado | Significado |
|--------|-------------|
| **VIGENTE** | Implementada y con pruebas que lo sostienen |
| **PROVISIONAL** | Adoptada, revisable si aparece una razón |
| **PENDIENTE** | No decidida. Documentada como pregunta abierta |

> **Nada de este documento se aplica solo porque esté escrito.** Un decisión
> marcada VIGENTE tiene código y pruebas detrás. Si el código y esta ficha
> discrepan, el código manda y la ficha es lo que hay que corregir.

Documentos de referencia: `08_DATABASE/AI_PRE_LLM_CONTRACT.md` (el contrato
congelado) y `INFORME_CIERRE_PRE_IA.md` (la evidencia de cada cierre).

---

## D01 — El núcleo funciona sin ningún LLM

**Estado: VIGENTE**

**Contexto.** Dwarf Fortress genera datos históricos que se pueden consultar. La
tentación natural es conectarle un modelo para explicarlos mejor.

**Decisión.** El pipeline de datos, el núcleo, la API y la UI se construyen y se
prueban **sin ninguna dependencia de IA**. La capa de IA es opcional y siempre
consumida desde dentro, nunca desde fuera.

**Motivo.** Si el núcleo dependiera del modelo, un fallo del modelo sería un
fallo del sistema. Además, los datos hay que poder consultar aunque el modelo no
esté disponible: eso es lo que hace que el proyecto sea utilizable hoy.

**Consecuencias.** `nucleo.py` no importa nada de `dfchron/ia_*`. Las suites del
núcleo pasan sin red. Sustituir o retirar el modelo no toca el núcleo.

---

## D02 — El núcleo es la autoridad sobre la verdad del mundo

**Estado: VIGENTE**

**Contexto.** Un sistema que responde sobre una partida necesita decidir qué es
cierto. Si eso lo decide quien genera el texto, la verdad depende de quién
hable.

**Decisión.** La verdad del estado del juego la determina exclusivamente el
núcleo, leyendo el dataset. Ni el modelo, ni la confianza declarada, ni el
formato de una respuesta pueden alterar un `truth_status`.

**Motivo.** El `FACT`/`DERIVED`/`UNKNOWN` de una afirmación lo decide el dato, no
la fuente que lo cuenta. Un modelo que dice «esto es un hecho» no lo convierte en
hecho.

**Consecuencias.** `truth_status` solo lo escribe el puente desde el núcleo.
Invariante I01. Prueba: `probar_auditoria_final.py::TestP`.

---

## D03 — La IA será una capa intercambiable

**Estado: VIGENTE**

**Contexto.** Los proveedores de modelo cambian, se deprecian y tienen límites
distintos. Acoplar el sistema a uno impediría cambiarlo.

**Decisión.** El modelo entra por un contrato: recibe contexto autorizado y
propone; su salida se valida con `ia_contrato.validar_salida()` y se compone con
`ia_frontera.componer_seguro()`. Ningún módulo del núcleo importa un SDK de IA.

**Motivo.** El valor del proyecto está en el núcleo y en sus garantías, no en el
modelo. Si cambiar de proveedor obliga a reescribir el núcleo, el diseño está mal.

**Consecuencias.** `ia_inferencia.py` define la frontera como interfaz. El
núcleo no menciona proveedores. La regla está en `AI_PRE_LLM_CONTRACT.md` §9.

---

## D04 — Las afirmaciones se verifican antes de presentarse como hechos

**Estado: VIGENTE**

**Contexto.** Validar «que la referencia exista» no es validar «que sea verdad».
Una afirmación con apoyo real puede ser falsa.

**Decisión.** La verificación ocurre contra la ficha del núcleo
(`ia_estructura`) y tiene tres estados honestos: `VERIFICADA`, `NO_VERIFICADA`
y `NO_APLICABLE`. Un claim no verificado nunca se presenta como hecho.

**Motivo.** El sistema no puede demostrar que una frase libre sea consecuencia
de su evidencia. Como no puede, no debe *parecer* que puede: de ahí el tercer
estado, que significa «no sé comprobar esto».

**Consecuencias.** `ia_estructura` cubre solo lo que cabe en una plantilla
declarada. Lo demás sale `NO_APLICABLE`, nunca `VERIFICADA`.

---

## D05 — La evidencia obsoleta falla de forma segura

**Estado: VIGENTE**

**Contexto.** Una auditoría dejó abierto si una evidencia válida en un momento
sigue valiendo después de que el mundo cambie. Sin identidad temporal, la
respuesta honesta era «no se puede saber».

**Decisión.** La evidencia declara `state_version`: el `dataset_id` real del
mundo que la produjo. `evidencia_es_actual()` es **fail-closed**: solo es actual
la evidencia que declara versión y coincide; la que no la declara, es
`UNKNOWN` y no sostiene nada.

**Motivo.** El núcleo no tiene reloj de juego, así que no se inventó un tick. Pero
sí tenía algo real: `dataset_id`, derivado del SHA-256 del contenido, que cambia
exactamente cuando cambia el mundo. Integrarlo era mejor que fabricar tiempo.

> **Corrección P1.1 (2026-10-04).** El «Motivo» anterior dice que `dataset_id`
> «cambia exactamente cuando cambia el mundo». **Eso es falso y está demostrado**
> (`P1_VERSIONADO_MUNDO_VIVO.md` §20.1): dos mundos con contenido idéntico
> reciben el MISMO `dataset_id`. Lo que la decisión **sí** aporta —y lo que sigue
> vigente— es la invalidez *fail-closed* por dataset. Lo que **no** aporta es
> identidad de estado. La *decisión* no se revierte; se corrige el motivo.

**Consecuencias.** `verificar_afirmacion(..., version_actual=…)` devuelve
`NO_VERIFICADA` para evidencia de otro mundo. Invariante I14.
**Lo que NO se ha ganado:** no hay caducidad temporal (no hay reloj) ni estado
en vivo (el dataset es una foto).

---

## D06 — Verdad, visibilidad y permiso de revelación son cosas distintas

**Estado: VIGENTE**

**Contexto.** Es fácil fusionar «es cierto» con «se puede decir». Cuando se
fusionan, un dato secreto se filtra por ser verdadero.

**Decisión.** Tres ejes independientes: `truth_status` (FACT/DERIVED/UNKNOWN),
`visibility` (PLAYER_VISIBLE/PLAYER_HIDDEN/EXTERNAL) y `disclosure`
(ALLOWED/FORBIDDEN/CONDITIONAL). Ninguno se deriva del otro.

**Motivo.** Que un dato sea verdadero no significa que el jugador pueda verlo, y
que esté oculto no significa que sea falso. Colapsar los ejes en uno produce
filtraciones en ambas direcciones.

**Consecuencias.** Un `FACT` con `PLAYER_HIDDEN` es normal y no se revela. La
regla literal está en `contrato_ia.REGLA`.

---

## D07 — El conocimiento externo explica, pero no demuestra

**Estado: VIGENTE**

**Contexto.** Una wiki o un manual puede servir para explicar mecánicas. También
puede contradecir a la partida, y entonces el jugador recibe información falsa
con apariencia de dato del juego.

**Decisión.** `EXTERNAL_KNOWLEDGE` sirve para explicar mecánicas, orientar y
dar contexto. No puede usarse como prueba de un hecho concreto de la partida
actual.

**Motivo.** La fuente externa no observa **esta** partida. Un ejemplo de manual
no es un dato de esta partida aunque cuadre con lo que debería pasar.

**Consecuencias.** Un claim externo no puede degradar a `FACT` ni declararse
`WORLD_KNOWLEDGE`. `ia_contrato` lo rechaza. Invariante I07.

---

## D08 — El texto libre de un modelo no es evidencia

**Estado: VIGENTE**

**Contexto.** Un modelo produce texto, y el texto parece una afirmación. Si el
texto puede entrar por la puerta de atrás, toda la arquitectura se vuelve
decorativa.

**Decisión.** El texto libre nunca constituye evidencia ni verdad por sí mismo.
La respuesta que ve el jugador la compone `ia_frontera` a partir de los claims
del **contexto**, no de los del modelo.

**Motivo.** Si el compositor usara el texto del modelo, la frontera dependería de
que el modelo se portara bien. Como el modelo elige qué decir, no puede decidir
qué se revela.

**Consecuencias.** El modelo aporta selección, nunca palabras. Errores, logs,
`repr()` y JSON no son canales de salida. Invariante I09.

---

## D09 — `dataset_id` no es un reloj del mundo

**Estado: VIGENTE**

**Contexto.** Al integrar la identidad del dataset era fácil creer que la
temporalidad estaba resuelta del todo. No lo está.

**Decisión.** `dataset_id` identifica **qué contenido** hay cargado. Es
determinista y cambia con el contenido. **No** es tiempo: no hay ticks, ni turnos,
ni caducidad.

**Motivo.** Un identificador de contenido permite invalidar evidencia cuando el
dataset se regenera. No permite decir «esto pasó hace tres segundos» en un mundo
que no tiene reloj.

**Consecuencias.** La caducidad temporal y el estado de partida en vivo siguen
**sin demostrar**. Está declarado en `AI_PRE_LLM_CONTRACT.md` §6 y §11, y
`test_H1b` falla si alguien convierte la versión en reloj.

---

## D10 — Las limitaciones no demostradas se documentan como tales

**Estado: VIGENTE**

**Contexto.** Un `NOT PROVEN` se puede tapar sin querer: basta añadir una prueba
que verifique otra cosa y renombrar el invariante.

**Decisión.** Lo que no está demostrado se escribe como tal, en el documento y en
las pruebas que lo vigilan. No se convierte en PASS por tener una prueba parecida.

**Motivo.** Un límite declarado es información. Un límite oculto se convierte en
una sorpresa cuando algo falla.

**Consecuencias.** `INFORME_CIERRE_PRE_IA.md` §E.3 enumera lo que sigue abierto.
`test_H1`/`test_H2` son guardas: se invirtieron cuando llegó la temporalidad; no
se borraron.

---

## D11 — El modelo no controla la política de revelación

**Estado: VIGENTE**

**Contexto.** Un modelo con buenos resultados puede tener la tentación de «juzgar»
si algo es revelable. Es exactamente el privilegio que no puede tener.

**Decisión.** La política es del sistema y se aplica al construir el contexto
(`ia_contrato.contexto()`), no después. `FORBIDDEN` no entra ni en modo
razonamiento.

**Motivo.** Si el modelo decidiera qué se revela, la garantía dependería de su
juicio, y la auditoría no podría verificar nada.

**Consecuencias.** Los campos `visibility`, `disclosure` o `discovered` en la
salida del modelo no conceden nada. `_claim_de_entrada()` es copia mínima
declarada: un campo desconocido ni siquiera existe en el contexto.

---

## D12 — El núcleo no depende de un proveedor concreto

**Estado: VIGENTE**

**Contexto.** Acoplar el diseño a un proveedor concreto limita de ejecución,
coste y disponibilidad, y obliga a reescribir si cambia.

**Decisión.** Ningún módulo del núcleo importa un SDK de IA. `ia_inferencia.py`
define una interfaz (`invocar`), y `ia_mock.py` la implementa **sin LLM** para
poder probar el flujo completo.

**Motivo.** El motor de prueba tiene que existir aunque no haya modelo. Un flujo
que solo se puede probar con el modelo es un flujo que no se puede probar.

**Consecuencias.** `probar_ia_mock.py` ejecuta el camino entero sin red. Las
pruebas que prohíben SDK (`probar_contrato_ia.py`, `probar_semantica_ia.py`)
vigilan que esto no se rompa por descuido.

---

## D13 — La verificación determinista se extiende a afirmaciones estructuradas

**Estado: VIGENTE**

**Contexto.** La verificación anterior solo cubría un campo contra una ficha
(`«el sitio es de tipo fortress»`). Las afirmaciones con sujeto y predicado más
compuestos no tenían dónde comprobarse, y la respuesta era que no había forma
determinista.

**Decisión.** Se añade `verificacion_semantica.py` con siete niveles: existencia,
atributo, relación, estado, cantidad, estructura e histórico. Los seis primeros
son completos; el séptimo es parcial y lo dice.

**Motivo.** La pregunta «¿no puede el núcleo verificar esto?» tenía una respuesta
distinta según la afirmación. Una afirmación estructurada **sí** se puede
comprobar contra el índice, sin lenguaje y sin inferencia. Decir que no era
posible era cierto solo para la lengua natural, y esa distinción no estaba
escrita.

**Consecuencias.**

* La comparación es **exacta**: `minotaur` no es `MINOTAUR`. Normalizar haría
  que aceptara cosas que el dato no dice.
* El grafo se comprueba **dirigido**: la inversa no se da por cierta.
* Una afirmación ambigua da `AMBIGUA`, nunca `VERIFICADA`.
* **No** reconoce paráfrasis ni negaciones, y `alcance()` lo declara.
* 38 pruebas sobre datos reales.

**Lo que NO cambia:** `08_DATABASE/AI_PRE_LLM_CONTRACT.md` §9 sigue diciendo que la
verificación semántica es `NO_APLICABLE`. No se ha tocado. Este módulo verifica
afirmaciones estructuradas, no lengua natural, y esa frontera sigue en pie.

---

## D14 — Un `dataset_id` distinto no significa evidencia caducada

**Estado: VIGENTE**

**Contexto.** Cerrar I14 dio nombre a `state_version`, y fue fácil leer eso como
«la caducidad está resuelta». No lo está, y esta misión lo investigó con datos
reales para poder decirlo con certeza.

**Decisión.** `dataset_id` identifica **qué contenido** hay cargado. Un dataset
distinto significa que el contenido cambió, y solo eso. **No** significa que la
evidencia haya caducado, y el sistema no lo trata como tal.

**Motivo.** Se buscó caducidad y no aparece en ninguna fuente: el núcleo no tiene
reloj, los raw del juego no traen etiquetas temporales (`YEAR`, `TICK`, `CYCLES`,
`SEASON`: 0 resultados), y `world.sav` no aporta historial. Sin reloj no hay
«cuánto ha pasado», y sin historial no hay «qué cambió desde cuándo».

**Consecuencias.**

* El mecanismo de `state_version` **se conserva intacto**: sigue siendo lo que
  invalida evidencia de otro dataset.
* **No se implementa caducidad.** Habría que inventar un reloj que no existe.
* La diferencia real: `dataset_id` distinto → la evidencia es de **otro mundo**
  (esto ya se demostraba); evidencia *caducada* → no se puede expresar.

---

## D15 — Las fuentes sin explotar se declaran, no se presuponen

**Estado: VIGENTE**

**Contexto.** El proyecto tenía 305 MB en `00_SOURCE/extraction/`: el
`world.sav` descomprimido, el vocabulario de los raw, `save_metadata.json`. No
estaban explotados, y era posible que contuvieran lo que faltaba.

**Decisión.** Se investiga qué aportan realmente y se documenta. El mundo
descomprimido tiene **0 apariciones** de `historical_figure`, `historical_event` y
`relationship` en 208 MB. `save_metadata.json` declara `UNKNOWN` en las siete
categorías de entidades. Los raw aportan vocabulario genérico, no datos de esta
partida.

**Motivo.** «Puede que haya más información» es hipótesis, no capacidad. Antes de
añadir una fuente hay que demostrar qué aporta; si no aporta, decirlo evita que
alguien la vuelva a explorar esperando milagros.

**Consecuencias.** La limitación de las relaciones **queda investigada**, no
supuesta. Ver `INFORME_COBERTURA_SEMANTICA_NUCLEO.md` §A.

---

## D16 — «Semántico» significa dos cosas distintas, y se separan

**Estado: VIGENTE**

**Contexto.** La documentación trataba «verificación semántica» como una única
reserva. Al implementarla quedó claro que son dos cosas con respuestas
distintas.

**Decisión.**

* **Afirmación estructurada** con sujeto y predicado → **DEMOSTRADO**.
* **Afirmación en lengua natural** (paráfrasis, negación) → **NO DISPONIBLE**,
  se mantiene en `NO_APLICABLE`.

**Motivo.** «Semántica» sugería una sola capacidad sin cobertura. Decir
«no verificable» para ambas era conservador en un caso y pesimista en el otro. La
distinción es la que permite saber qué falta de verdad.

**Consecuencias.** La reserva ya no se llama «verificación semántica» a secas.
Ver `TECHNICAL_ROADMAP.md` §C y `ARCHITECTURE_OVERVIEW.md` §8.2 bis.

---

## D17 — La capa de consulta delega; no reimplementa

**Decisión.** `dfchron/servicio_consulta.py` es una frontera de consulta, pero
**no es una segunda implementación**. Sus seis operaciones delegan:

| Operación | Delega en |
|-----------|-----------|
| `obtener_entidad`, `obtener_atributo` | `servicio.*` |
| `buscar_relaciones` | `servicio.figura_relaciones` |
| `contar` | el índice de `nucleo.Archivo` |
| `verificar` | `verificacion_semantica` |
| `obtener_evidencia` | `ia_conocimiento.evidencia_de` |

**Por qué.** El núcleo ya tenía envelope (`envolver_lista/ficha/estado`),
paginación y una taxonomía de errores con códigos bilingües. Escribir un índice
o un módulo de consulta propios habría creado dos fuentes de verdad para la
misma búsqueda, que es exactamente el fallo que D03 y D12 prohíben.

**Lo único que la capa añade** es `identity`, `evidence` y `dataset_id` en cada
respuesta, porque los envelopes existentes **no transportaban de qué mundo
venía el dato**. Un consumidor recibía `{"ok": true, "data": {...}}` sin poder
saber si era de este dataset o de otro.

**Consecuencias.** `servicio.py` no se modifica. Los códigos `NO_VERIFICADO`
y `NO_DISPONIBLE` son la **única** ampliación de la taxonomía, y existen solo
para no colapsar «no existe» con «no se puede determinar» (D10). El contrato
vive en `DATA_QUERY_SERVICE_CONTRACT.md` y en `servicio_consulta.contrato()`.

**Sin IA.** Esta frontera se define por consumidores abstractos. Cuando exista una
IA, será un consumidor más, por fuera. Si se eliminase toda IA del proyecto, la
frontera seguiría funcionando igual.

---

## D18 — La API es un adaptador; las rutas nuevas no rompen las viejas

**Decisión.** `dfchron/adaptador_consulta.py` traduce HTTP a `servicio_consulta`
y de vuelta. No decide nada del dominio. La integración se hizo **de dos
formas a la vez**, porque una sola habría roto consumidores:

| Vía | Qué hace | Por qué |
|-----|----------|---------|
| **Enriquecimiento** | Las 6 fichas y las relaciones ya existentes ahora pasan por el servicio | Una sola fuente de verdad para el dato |
| **Rutas nuevas** | `/api/consulta/...` expone el contrato completo | Un consumidor nuevo no tiene que conocer Python |

**Por qué las dos.** El enriquecimiento sola no bastaba: un cliente que quiere
`estado`, `identity` y `evidence` de forma explícita no debería tener que deducir
que `/api/figuras/{id}` las trae. Las rutas nuevas sola no bastaban: habrían
dejado las viejas consultando `servicio` directamente, que es exactamente la
ruta paralela que se quiere cerrar.

**El envelope se amplía, no se sustituye.** Las respuestas antiguas conservan
`ok`, `data`, `status`, `certainty`, `meta` y los campos heredados. Solo se
**añaden** `estado`, `identity`, `evidence`, `dataset_id` y `alcance`. Un
cliente anterior no se entera; uno nuevo lee más. Medido sobre 48 rutas: **0
regresiones, 19 ampliadas, 29 idénticas byte a byte**.

**Los códigos HTTP se derivan del estado, no del contexto.** El adaptador tiene
un mapa declarado, `HTTP_POR_ESTADO`:

| Estado | HTTP | Razón |
|--------|------|-------|
| `FOUND` | 200 | |
| `NOT_FOUND` | 404 | El dato no existe: ausencia **confirmada** |
| `NOT_VERIFIED` | **200** | No se pudo determinar. Un 404 afirmaría algo más fuerte y falso |
| `INVALID_QUERY` | 400 | |
| `DATA_UNAVAILABLE` | 503 | Fallo técnico, no ausencia |

**Las rutas viejas conservan su permeabilidad.** `/api/figuras/{id}/relaciones`
aceptaba antes cualquier `limit` (incluso `-5`) y devolvía 200 recortado. La
versión migrada **reutiliza `config.limite_seguro`** en vez de endurecer la
validación: endurecer una ruta con clientes sería romper el contrato sin
avisar. La ruta **nueva** `/api/consulta/relaciones/{id}` sí es estricta, porque
ahí no hay compatibilidad que preservar. La asimetría es deliberada y está
documentada en el propio adaptador.

**Consecuencias.** `servicio.py` y `nucleo.py` **no se modifican**. La Web
sigue hablando con la API (no hay `Web → dataset`) y ahora muestra el estado y
la evidencia que la API le da, sin decidir nada: `estadoDe()` **lee**
`env.estado`, no lo deduce.

**Sin IA.** `/api/consulta/*` no es «una API para la IA». Es una API de datos
determinista, útil con o sin IA. No hay endpoints de IA, ni preparativos, ni
código específico para futuros modelos.

---

## D19 — El perímetro IA se especifica sin implementarse

**Decisión.** `AI_CONSUMER_BOUNDARY.md` define qué podrá pedir y recibir un
futuro consumidor inteligente. **No hay IA.** La frontera se especifica como un
bloque ejecutable dentro de `probar_perimetro_ia.py`, no como un módulo de
producción.

**Por qué no hay un módulo de adaptador de IA.** La misión pide especificar y
no implementar, y dice preferir documentación y tests de arquitectura. Un módulo
de producción con ese nombre sería ambiguo: ¿está listo? ¿se usa? No. Un bloque
marcado en un fichero de pruebas es inequívoco: es una especificación, se lee,
se ejecuta y se puede mutar, y no puede importarse por accidente.

**Por qué no se duplicó `AI_PRE_LLM_CONTRACT.md`.** Ese documento existe, está
**CONGELADO** y cubre la **autoridad** del modelo. Su gate comprueba 15
invariantes, y **ninguno menciona `servicio_consulta`**: no mira qué entra por
la frontera, solo qué puede hacer el modelo con lo que ya tiene. Eran dos ejes
distintos y documentarlos juntos habría producido un documento confuso y medio
falso.

| Eje | Documento | Pregunta |
|-----|-----------|----------|
| Autoridad | `AI_PRE_LLM_CONTRACT.md` (CONGELADO) | ¿Qué puede afirmar o cambiar? |
| Acceso | `AI_CONSUMER_BOUNDARY.md` | ¿Qué puede pedir y recibir? |

**La lista blanca se deriva, no se escribe.** `OPERACIONES_PERMITIDAS` sale de
`servicio_consulta.contrato()["operaciones"]` en tiempo de ejecución. Una lista
escrita a mano se quedaría vieja en cuanto el servicio cambiara, y se volvería
una segunda fuente de verdad — justo lo que D17 y D18 prohíben.

**Un rechazo que no informa.** `OPERACION_NO_PERMITIDA` es un código **nuevo**,
distinto de `NOT_FOUND` y de `DATA_UNAVAILABLE`, y su motivo **no** menciona si
el fichero existe. Un rechazo que confirmara la existencia de un fichero sería
un oráculo de reconocimiento: filtraría estructura del disco por la puerta que
debería impedirlo.

**Consecuencias.** `servicio_consulta.py` **no se modifica**: su hash es
`0A5B6B1C3244E619…` antes y después. 50 pruebas y 11/11 mutaciones.

**Sin IA.** No hay modelo, ni SDK, ni prompt, ni embeddings, ni vector store.
Ninguna dependencia instalada.

---

## Preguntas abiertas (NO son decisiones)

Se registran aquí para que no se confundan con decisiones adoptadas.

| # | Pregunta | Estado |
|---|----------|--------|
| P1 | ¿Cómo se versiona un mundo **en vivo**? El dataset es una foto; DF-Hack daría estado mutable. Sin `dataset_id` para eso | **PENDIENTE** |
| P2 | ¿Habrá caducidad temporal? Requiere un reloj de juego, que hoy no existe | **PENDIENTE** |
| P3 | ¿Las afirmaciones relacionales complejas reciben identidad estable, o quedan fuera del alcance verificable? Hoy quedan fuera | **PENDIENTE** |
| P4 | ¿Habrá verificación semántica? Se mantiene `NO_APLICABLE`; no se usará otro LLM como juez | **PENDIENTE** |
| P5 | ¿Cómo se integrará con Dwarf Fortress? La vía (mod, DFHack, export) **no está decidida**: hay que estudiarla | **PENDIENTE** |
| P6 | ¿Habrá memoria conversacional? No existe. Si se añade, debe revalidarse y recomponerse en cada turno | **PENDIENTE** |

Ninguna de estas está implementada. Están en `TECHNICAL_ROADMAP.md` con sus
dependencias.