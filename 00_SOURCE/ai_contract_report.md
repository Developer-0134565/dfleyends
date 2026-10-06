# DF Legends · Informe del contrato de IA

> **La IA todavía NO está implementada.** Este informe describe una frontera,
> no un sistema. No hay LLM, ni RAG, ni embeddings, ni agentes, ni chat, ni NPCs.

---

## 1. Estado inicial: qué existía de verdad

La misión situaba los contratos en la raíz del repositorio. **No estaban ahí.**
Busqué por nombre y por contenido: viven en `08_DATABASE/`.

| Fichero | Contenido |
|---|---|
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | 192 líneas — contexto, regla dura, 10 prohibiciones |
| `08_DATABASE/ai_data_contract.md` | 197 líneas — formato de evidencia, 10 reglas |

### El hallazgo principal

Los contratos **ya definían casi todo** lo que pedía la misión: las cuatro
fuentes, las tres dimensiones, la regla de que `FACT` no es permiso para
revelar, los ejemplos, las prohibiciones.

Lo que **no** existía era lo importante. Una búsqueda de `visibility`,
`disclosure`, `PLAYER_HIDDEN` y `WORLD_KNOWLEDGE` en `dfchron/*.py` y
`00_SOURCE/tools/*.py` devuelve:

```
NINGÚN RESULTADO
```

**La política de divulgación estaba escrita, pero no implementada.** Una IA
futura que se apoyara en el código actual podría leer un `FACT` de
`WORLD_KNOWLEDGE` y llamarlo verdad revelable, porque nada se lo impedía. Ese
es exactamente el riesgo que la misión quiere cerrar.

### Contrato anterior, en resumen

| Elemento | ¿Ya existía? |
|---|---|
| `PLAYER_KNOWLEDGE` / `WORLD_KNOWLEDGE` / `EXTERNAL_KNOWLEDGE` / `INFERENCE` | Sí, documentado |
| `truth_status` / `visibility` / `disclosure` | Sí, documentado |
| «`FACT` no es permiso para revelar» | Sí, documentado |
| 5 ejemplos de política | Sí, en prosa |
| Evidencia obligatoria con `df_id` y `funcion` | Sí, documentado |
| **Implementación en código** | **No** |
| **Pruebas que lo comprueben** | **No** |

## 2. Un defecto en los contratos existentes

Al leerlos completos encontré que **ambos tenían texto desplazado**: no un
problema de formato, sino frases partidas y bloques fuera de sitio.

| Fichero | Qué pasaba |
|---|---|
| `AI_PROJECT_CONTEXT.md` | La frase que cierra la regla dura empezaba en la línea 76 y **continuaba en la línea 191**, con ocho secciones enteras intercaladas |
| `ai_data_contract.md` | El JSON de `Caso DERIVED` se cortaba sin cerrar; su cola aparecía 66 líneas después, dentro de la lista de verificación; el archivo terminaba con una valla suelta |

Es decir: **la frase más importante del contrato estaba partida en dos**.

**Reparados.** Verificado ejecutando: los tres bloques JSON del documento ahora
parsean correctamente, las vallas están emparejadas y la frase aparece una
sola vez y completa.

## 3. Contrato nuevo: qué se añadió

Implementado en **`dfchron/contrato_ia.py`**, por encima del núcleo, sin tocarlo.

```
nucleo.py / servicio.py        ← NO se modifica
        ↓  certeza ya calculada (FACT/DERIVED/UNKNOWN)
dfchron/contrato_ia.py         ← NUEVO
        ↓
   futura IA  (NO existe)
```

| Pieza | Para qué |
|---|---|
| `afirmacion(...)` | Construye **y valida**. Falla al crear, no al responder |
| `validar(a)` | Devuelve los problemas. Sin lanzar |
| `puede_revelarse(a)` | La puerta de salida. Conservadora: duda ⇒ `False` |
| `puede_afirmarse_como_hecho(a)` | Más estricta: separa *mencionar* de *afirmar* |
| `violacion(a)` | Explica el bloqueo, sin rutas ni tracebacks |
| `convertir(a, op)` | Única puerta para cambiar de categoría, con rastro |
| `contexto_obligatorio()` | Las limitaciones, montadas y obligatorias |
| `ejemplo_*()` | Los 5 casos, **ejecutables** |

Dos decisiones que merece la pena explicar:

**`INFERENCE` reutiliza `INTERPRETATION` del núcleo**, que ya existía sin
usarse ("no se genera en esta fase"). Crear un valor paralelo habría dado dos
constantes con el mismo significado: dos verdades.

**El módulo no se instancia.** Define y valida; nada más. No hay ninguna
llamada a red, ni modelo, ni generación de texto.

## 4. Arquitectura

```
                  WORLD
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
 PLAYER_KNOWLEDGE WORLD_KNOWLEDGE EXTERNAL_KNOWLEDGE
        │           │           │
        └───────────┼───────────┘
                    ▼
                INFERENCE
                    │
                    ▼
          DISCLOSURE POLICY
          (puede_revelarse)
                    │
                    ▼
                FUTURE AI
        (no implementada)
```

Y las tres dimensiones, que son independientes:

```
  ¿ES VERDAD?      truth_status  →  FACT / DERIVED / UNKNOWN / INFERENCE
        │
  ¿DE DÓNDE VIENE? knowledge_source → PLAYER / WORLD / EXTERNAL / INFERENCE
        │
  ¿LO CONOCE?      visibility    →  PLAYER_VISIBLE / PLAYER_HIDDEN / EXTERNAL
        │
  ¿PUEDE DECIRLO?  disclosure    →  ALLOWED / FORBIDDEN / CONDITIONAL
        │
        ▼
     RESPUESTA
```

> **VERDAD ≠ VISIBILIDAD ≠ DIVULGACIÓN**

## 5. Los cinco casos, ejecutados

Verificados ejecutando el contrato, no leyéndolo:

| Caso | `truth_status` | `knowledge_source` | `visibility` | `disclosure` | ¿Revelable? | ¿Como hecho? |
|---|---|---|---|---|---|---|
| A · Visible | `FACT` | `PLAYER_KNOWLEDGE` | `PLAYER_VISIBLE` | `ALLOWED` | **Sí** | **Sí** |
| B · Secreto | `FACT` | `WORLD_KNOWLEDGE` | `PLAYER_HIDDEN` | `FORBIDDEN` | **No** | **No** |
| C · Externo | `DERIVED` | `EXTERNAL_KNOWLEDGE` | `EXTERNAL` | `ALLOWED` | **Sí** | No |
| D · Inferencia | `INFERENCE` | `INFERENCE` | `PLAYER_VISIBLE` | `ALLOWED` | **Sí** | **No** |
| E · UNKNOWN | `UNKNOWN` | `WORLD_KNOWLEDGE` | `PLAYER_VISIBLE` | `ALLOWED` | **No** | No |

El caso B es el que lo resume todo: **es `FACT`, y aun así no se revela**.

## 6. Un fallo real que las pruebas detectaron

`CONDITIONAL` devolvía `puede_afirmarse_como_hecho() == True`, porque su
comprobación solo miraba `truth_status`. Consecuencia real: un dato `FACT` con
`disclosure: CONDITIONAL` y una pista autorizada **se enunciaba como hecho**,
cuando lo autorizado era mencionarlo.

La diferencia importa: «puedes contar que hay una pista» y «afirmas que hay una
veta» no son lo mismo. La segunda destruye el juego.

Corregido: `puede_afirmarse_como_hecho()` devuelve `False` para cualquier
`CONDITIONAL`. Hay una prueba que lo fija.

No lo encontré leyendo el código: lo encontró `test_conditional_no_es_un_hecho`.
Es el argumento de por qué esta frontera necesita pruebas y no solo intención.

## 7. Combinaciones prohibidas

Implementadas y con prueba para cada una:

| Combinación | Por qué se rechaza |
|---|---|
| `EXTERNAL_KNOWLEDGE` + `FACT` | Afirmaría como verdad algo que no viene de este mundo |
| `EXTERNAL_KNOWLEDGE` + `PLAYER_VISIBLE` | Lo externo no describe esta partida |
| `INFERENCE` + `FACT` | Una conclusión no es una fuente |
| `WORLD_KNOWLEDGE` + `no_descubierto` + `PLAYER_VISIBLE` | No es visible lo que no se ha visto |
| `PLAYER_HIDDEN` + `ALLOWED` | Se mostraría sin `pista_permitida` |
| Afirmación sin evidencia | «Parece lógico» no es una fuente |
| `UNKNOWN` sin motivo | Un vacío sin explicación no dice nada |
| Confirmar un `UNKNOWN` | No se rellena, ni por la puerta de conversiones |

Y su inversa, también probada: una parte de la matriz **es válida**. Si todo
fuera válido, el contrato no restringiría nada; si nada lo fuera, sería
inutilizable. Se comprueban las dos cosas.

## 8. Conversiones

Las conversiones prohibidas solo pasan por `convertir()`, que deja rastro de
qué pasó y por qué:

```python
visible = cia.convertir(secreto, "revelar", motivo="el jugador hamina la fortaleza")
visible["conversion"]
# {'operacion': 'revelar', 'campo': 'visibility',
#  'desde': 'PLAYER_HIDDEN', 'hacia': 'PLAYER_VISIBLE',
#  'motivo': 'el jugador hamina la fortaleza'}
```

`revelar` y `ocultar` solo funcionan sobre el estado del mundo: un dato
externo o una inferencia **no se revelan**, porque no son cosas que el jugador
pueda descubrir.

## 9. Pruebas

| Suite | Antes | Después |
|---|---|---|
| Núcleo | 48 | 48 OK |
| Integración | 20 | 20 OK |
| Adversarial | 39 | 39 OK |
| API | 54 | 54 OK |
| Web | 65 | 65 OK |
| Actualización | 43 | 43 OK |
| Geografía | 41 | 41 OK |
| Ciclo de refresco | 28 | 28 OK |
| **Contrato IA (nueva)** | — | **44 OK** |
| Navegador (Playwright) | 57 | 57 OK |
| **Total unitarias** | **338** | **382** |

Ninguna suite se sustituyó ni pasó de verde a rojo.

### Lo que comprueba la suite nueva

44 pruebas en ocho grupos: estados, fuentes, visibilidad, divulgación,
`UNKNOWN`, evidencia y conversiones, combinaciones y —lo más importante—

**que no hay una IA falsa**, comprobado por negación:

| Prueba | Qué descarta |
|---|---|
| `test_no_importa_ninguna_dependencia_de_ia` | 13 imports: `openai`, `torch`, `transformers`… |
| `test_no_hay_ia_falsa_por_preguntas` | Tablas de preguntas y respuestas prefijadas |
| `test_no_hay_funciones_que_generen_texto` | Ninguna función redacta |
| `test_no_hay_endpoints_de_ia_en_la_api` | `/api/ai`, `/api/chat`, `/api/ask`, `/api/rag` |
| `test_la_web_no_tiene_chat` | `chat`, `prompt`, `assistant`, `openai` en `src/` |
| `test_el_contrato_no_toca_el_nucleo` | Que `nucleo.py` siga sin saber de esto |

## 10. Integridad

| Recurso | Antes | Después |
|---|---|---|
| `legends.xml` | `77DB4739…A4681F` | **idéntico** |
| `legends_plus.xml` | `FB6BE93D…94ABC2D` | **idéntico** |
| JSONL de `processed/` | 56 ficheros | **56, los 56 idénticos** |

## 11. Cambios

**Creado**

| Fichero | Qué es |
|---|---|
| `dfchron/contrato_ia.py` | El contrato, ejecutable |
| `dfchron/pruebas/probar_contrato_ia.py` | 44 pruebas |
| `00_SOURCE/ai_contract_initial_audit.md` | La auditoría |
| `00_SOURCE/ai_contract_report.md` | Este informe |

**Modificado**

| Fichero | Qué cambió |
|---|---|
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Reparado (frase partida) + sección de implementación + cifras al día |
| `08_DATABASE/ai_data_contract.md` | Reparado (JSON partido) + sección 0 de dimensiones y combinaciones |

**Sin tocar**: `nucleo.py`, `servicio.py`, `api.py`, `validar_semantica.py`,
`integrar_legends.py`, `run.py`, el pipeline de extracción, la API, la Web,
los XML y los JSONL.

## 12. Lo que NO se ha hecho

| No | Por qué |
|---|---|
| LLM, SDK, RAG, embeddings | Fuera de alcance (§16) |
| Chat, «Ask AI», botón en la Web | Fuera de alcance (§13) |
| Endpoints `/api/ai` y compañía | Fuera de alcance (§14) |
| IA de NPC, agentes | Fuera de alcance (§12) |
| Modificar `nucleo.py` | Prohibido (§17) |
| Cambiar la semántica de los datos | Prohibido (§24) |

Comprobado por pruebas, no por promesa: la suite lee el código de la API, el
de la Web y el del propio contrato para verificar que nada de esto se ha
colado.

## 13. Limitaciones

> **La IA todavía NO está implementada.** Lo que existe es la frontera.

Concretamente, esto **no** está hecho y sigue pendiente:

- No hay generación de texto en ninguna parte.
- `WORLD_KNOWLEDGE` no se lee del mundo real todavía: el contrato lo define
  pero **no está conectado a `nucleo.py`**. Conectar las certezas del núcleo
  con las cuatro fuentes es el siguiente paso natural.
- `no_descubierto` hay que marcarlo a mano: el dataset **no registra** qué
  descubrió el jugador. Es la limitación de datos más importante para una IA
  futura, y no se resuelve en código.
- `CONDITIONAL` y `pista_permitida` existen como mecanismo; **quién autoriza
  la pista y con qué criterio** no está decidido.
- No hay primitivas de perspectiva para NPC (§12): el contrato admite la idea,
  pero no el mecanismo.

## 14. Qué habilita esto

| Sistema futuro | Qué necesitaría |
|---|---|
| **IA consejera** | Lo que ya hay: contexto obligatorio, evidencia, política |
| **Agentes con perspectiva** | Primitivas de punto de vista por entidad |
| **NPC que conocen su mundo** | Marcar `no_descubierto` por agente, no global |

La separación que lo permite: **el agente recibe una perspectiva, no el
mundo**. El `WORLD_KNOWLEDGE` completo sigue aquí, pero cada afirmación pasa
por `puede_revelarse()` antes de llegar a nadie. Por eso una IA podrá ser más
conocedora que el jugador sin convertirse en un visor de secretos.

---

**Resumen en una línea:** el núcleo sabe qué es verdad; el contrato decide qué
puede decirse; y una IA que exista en el futuro tendrá que pasar por esa
puerta antes de escribir nada.