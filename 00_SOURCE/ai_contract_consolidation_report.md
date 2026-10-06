# Informe final · Auditoría y consolidación del contrato de IA

**Misión:** auditar la documentación de IA y consolidarla contra el código real.
**Fecha:** 2026-03-03 · **Raíz:** `DF-Chronicles/`

> **No se implementó nada de IA.** No hay LLM, ni endpoint, ni SDK, ni
> integración externa. Este documento se limita a decir la verdad sobre lo que
> ya existe, y a poner una prueba que lo compruebe.

---

## A. Archivos revisados

| Archivo | Veredicto |
|---|---|
| `08_DATABASE/ai_data_contract.md` | **4 afirmaciones falsas.** Corregido |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | **Desactualizado e incompleto.** Corregido |
| `dfchron/contrato_ia.py` | Correcto. Leído entero, **no modificado** |
| `dfchron/ia_conocimiento.py` | Correcto. No modificado |
| `dfchron/estado_conocimiento.py` | Correcto. No modificado |
| `dfchron/pruebas/probar_contrato_ia.py` | Correcto. No modificado |
| `dfchron/pruebas/probar_estado_conocimiento.py` | Correcto. No modificado |
| `00_SOURCE/ai_contract_report.md` | Correcto (informe histórico) |
| `00_SOURCE/ai_knowledge_bridge_report.md` | Correcto |
| `00_SOURCE/ai_knowledge_state_report.md` | Correcto |
| `00_SOURCE/tools/rutas.py` | Correcto. **No modificado** |
| `00_SOURCE/tools/nucleo.py` | Correcto. **No modificado** |
| `dfchron/api.py`, `servicio.py`, `web/` | Correctos. **No modificados** |

El método no fue leer y opinar: se **ejecutó** el contrato contra cada
afirmación de la documentación (§D).

---

## B. Cambios realizados

### Creados
| Archivo | Qué |
|---|---|
| `dfchron/pruebas/probar_documentacion_ia.py` | **23 pruebas** que vigilan estos documentos |
| `00_SOURCE/ai_contract_consolidation_report.md` | Este informe |
| `00_SOURCE/_hashes_antes_consolidacion.txt` | Baseline de 62 ficheros |
| `00_SOURCE/_hashes_despues_consolidacion.txt` | Verificación final |

### Modificados — **solo documentación**
| Archivo | Cambio |
|---|---|
| `08_DATABASE/ai_data_contract.md` | Sección 0 (la trampa de los nombres); tabla de prohibiciones corregida; tabla de verdad/divulgación; las cuatro categorías; `WORLD`/`PLAYER`; `EXTERNAL` ≠ `WORLD`; `INFERENCE` no sube a `FACT`; **ejemplo obligatorio de la veta**; `PLAYER_KNOWLEDGE` y su capa de estado |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Cifras reales; tres capas con sus módulos; tabla de las cuatro dimensiones; regla de oro; **restricción fundamental**; **regla de determinismo**; **sección nueva del estado del jugador**; riesgos y referencias |

### Código de producción: **cero cambios**
Ni `contrato_ia.py`, ni `ia_conocimiento.py`, ni `estado_conocimiento.py`, ni
`nucleo.py`, ni la API. **Ningún contrato de código se modificó.**

---

## C. Decisiones arquitectónicas consolidadas

1. **Cuatro categorías** (`PLAYER_KNOWLEDGE`, `WORLD_KNOWLEDGE`,
   `EXTERNAL_KNOWLEDGE`, `INFERENCE`), con su procedencia declarada.
2. **Cuatro dimensiones** (`truth_status`, `knowledge_source`, `visibility`,
   `disclosure`), cada una respondiendo a una pregunta distinta.
3. **`FACT` no implica `ALLOWED`.** Se añadió una tabla de las cinco
   combinaciones, con su respuesta a «¿revelable?».
4. **`DERIVED` nunca sube a `FACT`.** Queda escrito en la tabla.
5. **`INFERENCE` nunca sube a `FACT`** y nunca se enuncia como hecho: se
   menciona, no se afirma.
6. **`EXTERNAL_KNOWLEDGE` no describe esta partida.** Solo puede llevar
   `visibility: EXTERNAL`, no puede ser `FACT`, y no puede alimentar
   razonamiento sobre la partida.
7. **`WORLD_KNOWLEDGE` no se convierte en `PLAYER_KNOWLEDGE`.** Descubrirlo
   cambia `visibility`, no el origen.
8. **La frontera es arquitectónica**, no lingüística: el dato `FORBIDDEN` no
   llega al modelo.
9. **Determinismo** declarado como norma del estado persistente.

---

## D. Contradicciones encontradas

### D1 · `INFERENCE` como valor serializado — **LA MÁS GRAVE**

| | |
|---|---|
| **ANTES** | Ambos documentos presentaban `"INFERENCE"` como valor de `truth_status` y de `knowledge_source` |
| **DESPUÉS** | Se documenta que `INFERENCE` es el **nombre** de la constante y su **valor** es `"INTERPRETATION"` |
| **MOTIVO** | Ejecutando el código: `contrato_ia.INFERENCE == "INTERPRETATION"`, y escribir `"INFERENCE"` **lanza** `truth_status invalido: 'INFERENCE'; knowledge_source invalido: 'INFERENCE'` |

Una misión que hubiera seguido la documentación al pie de la letra habría
escrito un JSON inválido sin entender por qué. Ahora la sección 0 del contrato
abre con la trampa, y `test_INFERENCE_no_se_escribe_como_valor_seriado` falla si
vuelve a colarse.

### D2 · `PLAYER_HIDDEN + ALLOWED` marcado como «prohibido»

| | |
|---|---|
| **ANTES** | En la tabla de «combinaciones que el contrato RECHAZA» |
| **DESPUÉS** | En una tabla aparte: **se construye sin error; es *no revelable*** |
| **MOTIVO** | Ejecutando el código: `afirmacion()` no lanza; `puede_revelarse()` devuelve `False` |

La **protección nunca estuvo en riesgo** — el dato no se revelaba igual. Lo que
estaba mal era la etiqueta, y confundía dos cosas distintas: *no existir* y *no
poder decirse*. La distinción quedó escrita, con `puede_usarse_para_razonar()`
al lado para dejar claro que sí se puede razonar por dentro.

Matiz adicional: `PLAYER_HIDDEN + ALLOWED` **tampoco** se revela añadiendo
`pista_permitida=True`. La combinación que lo abre es `CONDITIONAL` **y**
`pista_permitida`. La documentación no distinguía «rechazado» de «paseable», y
esa era una confusión disfrazada de seguridad.

### D3 · Cifras obsoletas

| | |
|---|---|
| **ANTES** | «44 pruebas» (contrato), «382 unitarias», «161 pruebas actuales» |
| **DESPUÉS** | 49 / 510 / 510 |
| **MOTIVO** | Las tres ya eran falsas al llegar esta misión |

### D4 · El contexto de Cline no mencionaba la capa de estado

| | |
|---|---|
| **ANTES** | `AI_PROJECT_CONTEXT.md` no mencionaba `estado_conocimiento`, `dataset_id`, `no_descubierto`, el determinismo ni la restricción arquitectónica |
| **DESPUÉS** | Sección 3 nueva, con las garantías y los prohibiciones |
| **MOTIVO** | El módulo existía y estaba probado, pero era invisible para quien viniera después |

### D5 · El ejemplo obligatorio no estaba

`ai_data_contract.md` no tenía el caso `WORLD` + `PLAYER_HIDDEN` + `FACT` +
`FORBIDDEN` con coordenadas reales. Ahora sí, tomado de
`contrato_ia.ejemplo_secreto()`, con lo que hace el sistema con él: razonar sí,
decir no.

---

## E. Tests

| | Antes | Después |
|---|---|---|
| Suites | 11 | **12** |
| Pruebas | 487 | **510** |
| Nuevas | — | **23** (`probar_documentacion_ia.py`) |
| **Resultado** | | **510/510 verdes** |

Las 23 nuevas **no prueban código de IA**: **prueban que los documentos sean
ciertos**. Se añadieron porque la misión lo permite cuando el proyecto ya tiene
mecanismo para verificar contratos, y porque el problema encontrado era
exactamente eso: la documentación se desvió sin que ninguna prueba lo notara.

Cubren:

* la doc no nombra valores que el código rechaza (D1);
* la doc no llama «prohibida» a combinaciones que el código construye (D2);
* el contexto de Cline menciona la capa de estado, el determinismo y la
  restricción arquitectónica (D4);
* los ejemplos obligatorios están;
* las cifras que se dan por ciertas lo son (D3);
* la evidencia sigue congelada y el estado sigue sin depender del contrato.

---

## F. Archivos NO modificados

| | |
|---|---|
| `nucleo.py` | **Intacto.** `ccc48ea6…7ce81`, el mismo hash de siempre |
| `legends.xml`, `legends_plus.xml` | **Intactos** |
| Los 56 JSONL | **Intactos** |
| `contrato_ia.py`, `ia_conocimiento.py`, `estado_conocimiento.py` | **Sin cambios** |
| `api.py`, `servicio.py`, `web/` | **Sin cambios** |
| `rutas.py`, `validar_semantica.py`, `integrar_legends.py` | **Sin cambios** |
| Endpoints de IA | `/api/ai`, `/api/chat`, `/api/assistant`, `/api/ia`, `/api/ask` → **404** |

**Hashes: 62/62 idénticos, 0 diferencias**, antes y después.

**Aceptación: 20/20 contra el servidor real, salida 0.**

---

## G. Limitaciones pendientes

1. **`no_descubierto` convive con la capa de estado.** El campo dentro de la
   afirmación y el fichero externo cuentan lo mismo. Es una duplicación
   consciente (el primero es legible junto al dato, el segundo se consulta y se
   persiste), pero **su unificación necesita una decisión futura**: si el estado
   externo pasa a ser la única fuente, hay que tocar `contrato_ia.py`, y eso no
   cabía en esta misión.

2. **`disclosure_alias`** se comprueba en `validar()` pero **nadie lo rellena**.
   Es una guarda para datos externos mal formados. Se documenta aquí para que
   nadie lo lea como una quinta dimensión.

3. **`INFERENCE + FORBIDDEN`** tampoco es rechazado: se construye y no se
   revela. No está en la tabla de prohibidas porque no lo está en el código. Si
   algún día debe rechazarse, es un cambio de contrato, no de documento.

4. **Las cifras de las pruebas se obsolecen solas.**
   `test_la_cifra_de_pruebas_del_contrato_no_esta_obsoleta` solo verifica la del
   contrato (49), que es rápida de contar. **No** hay ninguna prueba que verifique
   el total global (510): hacerlo exigiría lanzar las 12 suites, y una prueba que
   ejecuta el resto de pruebas es una prueba frágil. La cifra global está en el
   documento y hay que actualizarla a mano.

5. **Los criterios de aceptación quedan verificados por inspección, no por
   prueba.** La suite cubre el *contenido*; el orden y la numeración son
   humanos.

6. **No hay repositorio git**, así que `git diff` no da trazabilidad. La de esta
   misión son los dos ficheros de hashes y este informe.

---

## H. Cierre

La documentación y el código dicen lo mismo, y ahora hay una prueba que lo
comprueba.

Lo que la siguiente misión hereda, sin tener que reinterpretar nada:

```text
4 categorías  →  qué clase de dato es
4 dimensiones →  qué es verdad / de dónde viene / qué se ve / qué se dice
3 funciones   →  razonar sí · revelar no · afirmar menos aún
```

Y una frontera que **no depende del modelo**: el dato prohibido no llega a la
fase donde un LLM pudiera filtrarlo.