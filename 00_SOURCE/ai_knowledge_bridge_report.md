# Informe :: Puente entre núcleo y contrato de IA

> Fase: infraestructura para que una futura IA sea segura por construcción.
> **No hay IA.** No se instaló ningún SDK, no hay RAG, ni embeddings, ni
> agentes, ni chat, ni endpoint nuevo.

Auditoría previa: [`ai_knowledge_bridge_initial_audit.md`](ai_knowledge_bridge_initial_audit.md)

## 1. Arquitectura

```
                      DF WORLD
                         │
                    legends.xml / legends_plus.xml   (solo lectura)
                         │
                         ▼
                   NÚCLEO  nucleo.Archivo
              (48+ funciones públicas, declara certeza)
                         │
                         ▼
              PUENTE DE CONOCIMIENTO
              dfchron/ia_conocimiento.py     ◄── ESTA MISIÓN
              · solo API pública del núcleo
              · traduce a afirmaciones con evidencia
              · decide visibilidad con UNA política
                         │
                         ▼
                  CONTRATO DE IA
              dfchron/contrato_ia.py
              · 4 fuentes · 3 dimensiones
              · validar() · convertir()
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  conocimiento interno          PUERTA DE DIVULGACIÓN
  claims_para_razonar()        puede_revelarse()
                                preparar_respuesta_jugador()
          └──────────────┬──────────────┘
                         ▼
                    FUTURA IA
                 (aún no existe)
```

La IA **no** importará `nucleo.py`, ni el JSONL, ni el XML. Recibirá objetos de
esta capa. Verificado por prueba: ningún módulo del proyecto importa
`ia_conocimiento`; sólo se importa desde su propia suite.

## 2. Archivos

| Fichero | Acción | Qué es |
|---|---|---|
| `dfchron/ia_conocimiento.py` | **nuevo** (~600 l.) | El puente. Adaptador y puerta |
| `dfchron/pruebas/probar_puente_conocimiento.py` | **nuevo** (52 pruebas) | Suite del puente |
| `dfchron/contrato_ia.py` | modificado | Inmutabilidad + `puede_usarse_para_razonar` |
| `00_SOURCE/_hashes_antes_bridge.txt` | nuevo | Snapshot de los 58 protegidos |
| `00_SOURCE/_hashes_despues_bridge.txt` | nuevo | Comprobación final |
| `00_SOURCE/ai_knowledge_bridge_*.md` | nuevos | Este informe y la auditoría |

**No se tocó**: `nucleo.py`, `integrar_legends.py`, `validar_semantica.py`,
`api.py`, `servicio.py`, `dfchron/web/*`, los XML ni los JSONL.

## 3. Cómo se conecta WORLD_KNOWLEDGE al núcleo

Cada consulta sigue tres pasos, y solo usa API pública:

1. `nucleo.Archivo.ficha_*()` — el núcleo lee y **declara la certeza**.
2. Se elige qué campos extraer, mediante **tablas explícitas** (no reflexión):
   se lee de dónde sale cada dato, y añadir un campo es una decisión visible.
3. Cada valor se envuelve con `afirmacion_del_mundo()`, que aplica la política
   de visibilidad y adjunta la evidencia.

Lo que se puede consultar, con datos reales del dataset actual:

```python
from dfchron import ia_conocimiento as ia

k = ia.obtener_conocimiento_sitio("87")
k["asunto"]      # {'tipo': 'sitio', 'df_id': '87', 'certeza': 'FACT',
                 #  'nombre': 'halesteel'}
k["claims"]      # 4 afirmaciones, cada una con evidencia y permiso
k["provenance"]  # {'dataset_id': 'v1-04170363943d4ba1',
                 #  'entity_type': 'sitio', 'entity_id': '87',
                 #  'funciones': ['nucleo.Archivo.ficha_sitio'],
                 #  'fuentes_xml': ['legends.xml', 'legends_plus.xml']}
k["contexto"]    # las limitaciones obligatorias del dataset
```

Sin `contexto`, un modelo rellena los huecos por inercia.
## 4. La regla: verdad ≠ visibilidad ≠ permiso

Un dato puede ser verdadero y estar prohibido. Comprobado con el sitio real 87
(`halesteel`), que **tiene** coordenadas registradas:

```text
[FACT    ] El sitio esta en las coordenadas '(112, 20)'.
           vis=PLAYER_HIDDEN  disc=FORBIDDEN  revelable=False  razonable=True
```

| Pregunta | Función | Respuesta |
|---|---|---|
| ¿Es verdad? | `truth_status` | `FACT` |
| ¿Lo sabe el jugador? | `visibility` | `PLAYER_HIDDEN` |
| ¿Se lo puedes decir? | `disclosure` | `FORBIDDEN` |
| ¿Puedes razonar con ello? | `puede_usarse_para_razonar` | **`True`** |
| ¿Lo revelas? | `puede_revelarse` | **`False`** |
| ¿Lo puedes afirmar? | `puede_afirmarse_como_hecho` | **`False`** |

Razonar con un secreto es legítimo: el modelo puede encadenar hechos ocultos
para llegar a una conclusión divulgable. Contarlo, no. De ahí **dos** funciones
y no una.

Y el resultado comprobado de `preparar_respuesta_jugador(k)`:

```text
'112' aparece en la respuesta: False
divulgables=0  omitidos=4  motivos={'disclosure FORBIDDEN': 4}
```

Las coordenadas **no aparecen ni parcialmente**. La omisión se declara y se
explica, pero sin el valor: se dice cuántos y por qué, nunca qué.

## 5. PLAYER_KNOWLEDGE y su límite (la parte incómoda)

`legends.xml` **no registra qué descubrió el jugador**. No hay forma de
demostrar que el jugador conoce una figura, un sitio o un objeto.

Por eso el puente **no marca nada como `PLAYER_VISIBLE`**. No es que el dato
sea secreto: es que *no se puede demostrar que sea suyo*. Todo `WORLD_KNOWLEDGE`
sale como `PLAYER_HIDDEN` + `FORBIDDEN`, y hay una prueba que lo fija para que
nadie lo "arregle" por intuición:

```python
def test_ningun_hecho_se_marca_visible_por_el_puente(self):
```

Es una limitación conservadora y **deliberada**: preferimos no revelar de más
a revelar de menos. La vía para abrirla ya existe y es `convertir('revelar')`,
que exige motivo y registra quién decidió y por qué. El día que exista un
registro real de descubrimientos, se enchufa ahí sin reescribir nada.

## 6. INFERENCE

`registrar_inferencia()` **no genera** inferencias: solo las declara. Exige las
evidencias, porque una conclusión sin evidencia es justo lo que el contrato
prohíbe. Con la evidencia, nace `INFERENCE`:

```text
puede_revelarse            → True   (se puede mencionar)
puede_afirmarse_como_hecho → False  (no se puede afirmar)
```

La separación está en `truth_status`, no en el permiso: por eso mencionar y
afirmar son cosas distintas incluso cuando ambas están permitidas.
## 7. EXTERNAL_KNOWLEDGE, preparado y desconectado

Existe la pieza (`externo_pendiente()`, `EXTERNAL_PENDIENTE`,
`EXTERNAL_NO_CONECTADO`) pero **no hay ninguna fuente conectada**: no se ha
descargado wiki, ni raws, ni manuales. Se declara por escrito que no las hay.

La frontera ya está puesta: el contrato **rechaza** que algo externo sea `FACT`
sobre esta partida, y hay prueba de ello:

```python
with self.assertRaises(c.ContratoInvalido):
    c.afirmacion("en tu mundo hay 37 goblins", truth_status=c.FACT,
                 knowledge_source=c.EXTERNAL_KNOWLEDGE, ...)
```

## 8. Provenance y `dataset_id`

Cada sobre lleva `dataset_id`, `entity_type`, `entity_id`, `funciones` y
`fuentes_xml`. Responde a «¿de qué dato real salió esto?» **sin** que la IA lea
el JSONL.

* El `dataset_id` se **lee** de `dataset_version.json` (`v1-04170363943d4ba1`).
  No se genera con reloj, y si el fichero faltara se declara `UNKNOWN` en vez de
  inventar uno.
* **Deliberadamente no se incluye la ruta del dataset en disco.** El
  `dataset_id` ya lo identifica, y una ruta interna solo le da información del
  sistema de ficheros al consumidor. Lo detectó la prueba
  `test_no_filtra_rutas_internas`, que falló en la primera versión.

## 9. Seguridad: inmutabilidad

El hallazgo de la auditoría está cerrado. `Afirmacion` sigue siendo un `dict`
—para que salga en JSON sin conversión— pero es de **solo lectura**:

| Operación | Resultado |
|---|---|
| `a["visibility"] = PLAYER_VISIBLE` | `ContratoInvalido` |
| `a["disclosure"] = ALLOWED` | `ContratoInvalido` |
| `a["truth_status"] = DERIVED` | `ContratoInvalido` |
| `del a["disclosure"]` | `ContratoInvalido` |
| `update` / `pop` / `setdefault` / `clear` / `\|=` | `ContratoInvalido` |

Y tras intentarlo, el dato **sigue siendo el que era** (`puede_revelarse()`
continúa en `False`). La vía legítima sigue abierta: `convertir('revelar')`
devuelve un objeto nuevo y deja `conversion` con el motivo.

## 10. Fallos encontrados y corregidos

| # | Fallo | Corrección |
|---|---|---|
| 1 | `Afirmacion` mutable: un secreto se volvía divulgable en 2 líneas | `_Candado` + bloqueo de las 8 escrituras |
| 2 | `validar(None)` lanzaba `AttributeError` en vez de devolver un problema | `validar()` devuelve `["no es una afirmación: …"]` |
| 3 | `convertir('revelar')` cambiaba la visibilidad pero dejaba `FORBIDDEN`: revelar no revelaba | Al revelar sube también `disclosure`, registrado en `conversion["tambien"]` |
| 4 | `registrar_inferencia` nacía `CONDITIONAL`, y con `CONDITIONAL` una inferencia nunca es revelable | Nace `ALLOWED`; la separación la da `truth_status=INFERENCE` |
| 5 | La procedencia filtraba `00_SOURCE/dataset_version.json` | Se quitó la ruta; queda solo el `dataset_id` |
| 6 | `buscar_evento()` no devolvía fichas: los eventos salían con 0 claims | Se usa `ficha_evento()`, que sí la devuelve |
| 7 | `_RAIZ` con un `dirname` de más: `dataset_id` salía `UNKNOWN` | Corregido a dos niveles |

Tres (2, 4, 5) los detectaron pruebas propias, no la lectura del código. Y una
prueba mía estaba mal escrita (`assertIn` sobre una tupla de un elemento busca
elementos, no subcadenas): se corrigió la prueba, no el código.

## 11. Pruebas

`dfchron/pruebas/probar_puente_conocimiento.py` — **52 pruebas, todas verdes**.
Cubre los 18 puntos del encargo: los cuatro estados, las tres visibilidades,
los tres permisos, procedencia, `dataset_id`, la puerta, inferencias, las cinco
entidades reales y la inmutabilidad.

Adversariales (§16): identificadores inexistentes, negativos, `None`, tipos no
esperados, `bytes`, objetos, Unicode (`ografía`, `ゼロ`, emoji), cadenas de 400
caracteres, traversal (`../../etc/passwd`), inyección (`712; DROP TABLE`), y
afirmaciones que no son afirmaciones. **Ninguna produce traceback ni dato
inventado.**

Negativas (§14): se comprueba que **no** hay `/api/ai`, `/api/chat`,
`/api/assistant`, `/api/ia`, `/api/ask`, `/api/preguntar`, ni SDK de IA, ni
salida a red, ni lectura del XML o el JSONL desde el puente.
## 12. Determinismo (§18)

Sin relojes, sin `random`, sin UUID, sin orden no determinista. Las claims se
ordenan por clave explícita, no por el orden del diccionario.

Comprobado **entre dos procesos independientes**, que es más fuerte que
comprobarlo en el mismo proceso:

```text
longitud A = 16131
longitud B = 16131
DETERMINISTA: dos procesos independientes producen salida IDÉNTICA
SHA-256 (32): 5babb4bde6d892c0e23db1be29b3355a
```

## 13. Regresión completa (§20)

Ninguna suite existente se sustituyó. Todas verdes:

| Suite | Pruebas | Resultado |
|---|---|---|
| núcleo | 48 | OK |
| integración | 20 | OK |
| adversarial | 39 | OK |
| API | 54 | OK |
| Web/API | 65 | OK |
| geografía | 41 | OK |
| actualización | 43 | OK |
| ciclo de refresco | 28 | OK |
| contrato IA (existente) | 44 | OK |
| **puente (nueva)** | **52** | **OK** |
| reproducibilidad desde XML | — | REPRODUCIBLE |
| **Total** | **434** | **todas verdes** |

Rutas de IA comprobadas **contra el servidor vivo**, no solo en el código:
`/api/ai`, `/api/chat`, `/api/assistant`, `/api/ia`, `/api/ask` → **404** las
cinco.

### Una salvedad honesta

`dfchron/pruebas/aceptacion_mision.py` **no se pudo ejecutar**: necesita un
servidor ya arrancado en `127.0.0.1:877` y, en este entorno, el proceso Python
no puede alcanzar por loopback un servidor levantado por otro proceso
(`WinError 10061`), aunque PowerShell sí reciba `200` del mismo puerto. Es una
limitación del entorno, no una regresión: el script falla en su **primera**
línea, al pedir `/api/salud`, antes de tocar nada de esta misión. Se comprobó
además que **`api.py`, `servicio.py`, `dfchron/web/` y todo `00_SOURCE/tools/`
no importan `contrato_ia` ni `ia_conocimiento`**, de modo que el servidor no
puede verse afectado por estos cambios. Queda pendiente ejecutarlo en un
entorno sin esa restricción.

## 14. Hashes antes / después (§19)

**58 archivos protegidos, SHA-256 completo, idénticos.**

```
77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f  00_SOURCE/original_data/legends.xml
fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d  00_SOURCE/original_data/legends_plus.xml
```

Los 56 JSONL de `00_SOURCE/processed/` (los tres árboles `from_legends_xml`,
`from_legends_plus` y `merged`) también coinciden. `nucleo.py`,
`integrar_legends.py` y `validar_semantica.py` conservan su fecha de
modificación original.

## 15. Lo que queda para la misión que añada IA

1. Conectar `EXTERNAL_KNOWLEDGE` a fuentes reales, sabiendo que ya no podrá
   afirmar nada sobre esta partida sin evidencia de `WORLD_KNOWLEDGE`.
2. Decidir cómo se registra el descubrimiento del jugador, para que
   `convertir('revelar')` tenga una fuente y no una intuición.
3. Dar a `preparar_respuesta_jugador()` un consumidor real. Hoy es la puerta y
   está probada, pero nadie redacta todavía.

## 16. Una línea

El núcleo sabe qué es verdad; esta capa decide qué de eso puede decirse, deja
constancia de por qué, y no deja ninguna otra puerta.

---

# ANEXO · Estado del conocimiento del jugador

> Añadido por la misión de *estado del conocimiento del jugador*
> (`dfchron/estado_conocimiento.py`).

El punto 2 de arriba ("decidir cómo se registra el descubrimiento del jugador")
**ya está resuelto**. Aquí está cómo.

## A1. Las cuatro capas, separadas

Son **cuatro preguntas distintas**, y una respuesta nunca implica la siguiente.

```
        HISTORIA DEL MUNDO  (legends.xml, JSONL)
                    │
                    ▼
        WORLD_KNOWLEDGE ─────► "¿es verdad?"     FACT / DERIVED /
                    │                            UNKNOWN / INFERENCE
                    ▼
      ┌──────────────────────────────────┐
      │  ¿QUÉ CONOCE EL JUGADOR?         │  ◄── ESTADO DE EJECUCIÓN
      │  estado_conocimiento.py          │      (nuevo, externo)
      └──────────────────────────────────┘
                    │
                    ▼
        CONTRATO DE DIVULGACIÓN ────────► "¿se puede decir?"
        contrato_ia.py                      ALLOWED / FORBIDDEN /
                                             CONDITIONAL
                    │
                    ▼
             LA FUTURA IA  (todavía no existe)
```

| Capa | Pregunta | Quién responde | Dónde vive |
|---|---|---|---|
| Mundo | ¿qué pasó? | `nucleo.py` | `00_SOURCE/` |
| Verdad | ¿es cierto? | `contrato_ia.py` | en la afirmación |
| **Jugador** | **¿lo sabe?** | **`estado_conocimiento.py`** | **`estado/`** |
| Divulgación | ¿se puede decir? | `contrato_ia.py` | en la afirmación |

**La respuesta a "¿lo sabe?" no cambia ninguna de las otras tres.**

## A2. Lo que el dataset sabe: `WORLD_KNOWLEDGE`

Viene del núcleo. Es verdad del mundo, exista o no el jugador. Se usa para
**razonar** (`puede_usarse_para_razonar() == True`) aunque no se pueda decir.

```
halesteel es una fortaleza en (112, 20)
  truth_status     = FACT
  knowledge_source = WORLD_KNOWLEDGE
  visibility       = PLAYER_HIDDEN
  disclosure       = FORBIDDEN
```

## A3. Lo que el jugador sabe: `PLAYER_KNOWLEDGE`

**No sale de los datos.** Sale de una decisión explícita, escrita en
`estado/estado_conocimiento.json`:

```json
{
  "schema_version": 1,
  "dataset_id": "v1-04170363943d4ba1",
  "knowledge": {
    "campo|sitio:87:coordenadas": {
      "campo": "coordenadas",
      "df_id": "87",
      "motivo": "el jugador minimizó el mapa",
      "tipo": "sitio"
    }
  }
}
```

### Granularidad: la que el núcleo sostiene de verdad

Se auditó `nucleo.py` antes de decidir nada. Hay identidad estable (`df_id`) en
`figura`, `sitio`, `entidad`, `artefacto` y `evento`.

**Las relaciones NO se soportan**: `relaciones_de_figura()` devuelve objetos sin
identificador. Inventar un `relation_id` sería fabricar una granularidad que el
dataset no puede sostener, y una granularidad inventada acaba siendo una
dirección equivocada. Está declarado en `TIPOS_NO_SOPORTADOS`, con el motivo.

Dos niveles, ambos derivados de datos reales:

* **entidad** — el jugador conoce el sitio 87.
* **campo** — el jugador conoce las *coordenadas* del sitio 87.

El segundo existe porque las afirmaciones hablan de **campos**
(`evidence[0]["datos_utilizados"]`), no de entidades enteras. Saber que existes
no es saber dónde estás.

## A4. Lo que el sistema puede usar para razonar

```python
contrato_ia.puede_usarse_para_razonar(afirmacion)  ->  bool
```

No exige visibilidad ni permiso. Un secreto puede usarse **por dentro** para no
decir una falsehood. Devolver `True` aquí **no** autoriza a decirlo: son dos
preguntas.

## A5. Lo que el sistema puede revelar

```python
contrato_ia.puede_revelarse(afirmacion)            ->  bool
```

Es la **única** autoridad, y no se puede esquivar:

```
PLAYER_KNOWLEDGE + FORBIDDEN = NO revelar
PLAYER_KNOWLEDGE + ALLOWED   = puede pasar el resto de reglas
```

En `estado_conocimiento.py` **no existe** ningún `si conocido: revelar()`: no
llama a `convertir()`, ni consulta `puede_revelarse()`, y ni siquiera importa
`contrato_ia`. Eso no es casualidad — hay una prueba que analiza el **árbol
sintáctico** del módulo y falla si alguien lo añade.

## A6. Lo que el sistema nunca debe hacer

```text
WORLD_KNOWLEDGE ──► PLAYER_KNOWLEDGE      NUNCA, automáticamente
conocido       ──► verdad                 NUNCA (conocer un UNKNOWN no lo hace FACT)
conocido       ──► revelable              NUNCA (conocer no quita un FORBIDDEN)
```

Que el dato exista, que la web lo muestre, que una consulta lo devuelva o que
sea `FACT` **no** lo marca como conocido. La transición es siempre explícita y
queda escrita con su motivo.

## A7. Cambio de dataset

```
estado guardado (dataset X)  +  dataset actual (Y)
```

Se levanta `DatasetDistinto` y el sistema **se para**:

* **No** se borra nada.
* **No** hay migración silenciosa.
* `esta_conocido()` devuelve `False` — falla **cerrado**.
* `obtener_conocimiento()` se niega a entregar el estado.
* Se sale con un **reset explícito**, que además vuelve a ligar el estado al
  dataset actual.

Sin ese último detalle, cambiar de dataset dejaría el estado inservible para
siempre. `schema_version` también se comprueba: una versión desconocida **no se
migra sola**.

## A8. Determinismo

Claves ordenadas, sin reloj, sin UUID, sin `random`, sin orden accidental de
`set`, sin depender del directorio de trabajo. Dos procesos independientes que
construyen el mismo estado producen el mismo fichero **byte a byte**, incluso
invirtiendo el orden de las marcas.

## A9. La limitación fundamental

> **Dwarf Fortress no registra en `legends.xml` qué descubrió el jugador.**

El juego escribe la historia del mundo, no la memoria de quien la jugó. No hay
campo, ni marca, ni fecha de descubrimiento en ningún fichero del dataset.

Por eso el conocimiento del jugador **no puede derivarse de los datos**: tiene
que ser **estado externo explícito**, y puede estar equivocado. Si nadie lo
marca, no existe — y el sistema no lo va a suponer.

Hoy se marca así, a mano:

```python
from dfchron import estado_conocimiento as ec

ec.marcar_conocido("sitio", "87", "coordenadas", motivo="minimizó el mapa")
ec.esta_conocido("sitio", "87", "coordenadas")     # True
```

Y a partir de ahí, si procede, la afirmación pasa por la puerta de siempre:

```python
revelada = contrato_ia.convertir(afirmacion, "revelar", "el jugador lo descubrió")
```

`convertir()` sigue siendo la **única** vía para cambiar de categoría, y sigue
exigiendo un motivo. Que el estado diga «lo conoce» **no** la invoca.

## A10. Limitaciones que siguen existiendo

* **El estado puede mentir.** Es una afirmación sobre el jugador escrita por el
  sistema; nada en el dataset la confirma.
* **No hay granularidad por relación.** El núcleo no da identidad. Documentado,
  no escondido.
* **El estado es de un solo jugador.** No hay perspectiva por NPC ni facción.
* **`limpiar_conocimiento()` sin argumentos borra todo**; con `tipo` y `df_id`
  borra solo esa entrada.
* **No hay sincronización.** Si dos procesos escriben a la vez, el último gana.
  Es un archivo de un jugador, no una base de datos.
* **No se registra quién marcó cada cosa.** El `motivo` es texto libre, sin
  fecha: las marcas de tiempo romperían el determinismo de §A8. Si algún día
  hace falta, será un campo aparte y explícito.

## A11. Sigue sin haber IA

No hay LLM, ni chat, ni RAG, ni embeddings, ni agente, ni endpoint `/api/ai`.
`/api/ai`, `/api/chat`, `/api/assistant`, `/api/ia` y `/api/ask` devuelven 404,
comprobado contra el servidor real. Esta capa prepara la frontera de datos; el
modelo viene después, y solo cuando la frontera esté probada y atacada.