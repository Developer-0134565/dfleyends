# INFORME DE CONSOLIDACIÓN ARQUITECTÓNICA

> **Naturaleza:** misión **documental y de auditoría**.
> **No se ha implementado ninguna funcionalidad de IA.** El proyecto sigue en
> estado PRE-LLM.

---

## A. ESTADO INICIAL

### Qué existía

| Elemento | Estado al empezar |
|----------|-------------------|
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | EXISTS. Contrato congelado, 13 secciones |
| `INFORME_CIERRE_PRE_IA.md` | EXISTS. Secciones A–H |
| `dfchron/pruebas/probar_cierre_pre_ia.py` | EXISTS. 54 pruebas |
| `dfchron/pruebas/probar_gate_pre_ia.py` | EXISTS. 15 invariantes |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | EXISTS. 678 líneas, 24 secciones |
| `08_DATABASE/ai_data_contract.md` | EXISTS. Contrato de datos |
| `ARCHITECTURE.md` | EXISTS. Cadena completa y reglas de diseño |
| `08_DATABASE/architecture.md` | EXISTS. Capa de datos en detalle |
| `dfchron/pruebas/probar_documentacion_ia.py` | EXISTS. 51 pruebas de veracidad |
| `ARCHITECTURE_OVERVIEW.md` | **NO EXISTÍA** |
| `ARCHITECTURE_DECISIONS.md` | **NO EXISTÍA** |
| `TECHNICAL_ROADMAP.md` | **NO EXISTÍA** |
| `PROJECT_DOCUMENTATION_INDEX.md` | **NO EXISTÍA** |
| Comprobación de enlaces y cifras | **NO EXISTÍA** |

### Dos documentos «de arquitectura», y por qué no son duplicados

`ARCHITECTURE.md` (raíz) y `08_DATABASE/architecture.md` tienen el mismo título y
podrían leerse como duplicados. **No lo son**, y no se fusionaron:

| Documento | Alcance |
|-----------|---------|
| `ARCHITECTURE.md` | Cadena XML → núcleo → servicio → API → UI. Las cinco reglas de diseño |
| `08_DATABASE/architecture.md` | Las dos fuentes, reglas de merge, modelo de certeza, rendimiento |

Se verificó además que `ARCHITECTURE.md` es **fiel**: las siete suites y los
módulos que cita existen (`probar_integracion.py`, `probar_nucleo.py`,
`probar_adversarial.py`, `probar_api.py`, `test_determinismo.py`,
`verificar_reproducibilidad.py`, `rutas.py`, `servicio.py`, `api.py`, `web/app.js`).
No se modificó.

### Discrepancias detectadas entre código y documentación

| # | Documento | Afirmaba | Realidad | Resolución |
|---|-----------|----------|----------|------------|
| D-1 | `AI_PROJECT_CONTEXT.md:152` | `probar_ia_mock.py` = 32 pruebas | **35** | Corregido el documento |
| D-2 | `ai_data_contract.md:1165` | `ia_mock.py` = 32 pruebas | **35** | Corregido el documento |

En ambos casos **el código era correcto y el documento mentía**. No se tocó el
código. Los otros cinco documentos que mencionan `ia_mock.py` ya decían 35.

> **Por qué no se detectó antes:** `probar_documentacion_ia.py` comprueba que la
> cifra de `probar_contrato_ia.py` sea real, pero no las demás. El hueco estaba en
> la comprobación, no en los documentos. Por eso esta misión añade
> `probar_documentacion_indice.py::TestCifrasDocumentadas`, que recorre **todas**
> las filas de cifras y ejecuta cada suite.

Tres referencias adicionales resultaron ser **falsos positivos** de un primer
borrador del comprobador, no enlaces rotos: `data_limitations.md` y
`AI_PROJECT_CONTEXT.md` se citan sin prefijo en prosa (existen en `08_DATABASE/`),
y `extract_world.py` vive en `00_SOURCE/extraction/tools/`. El comprobador final
resuelve por ruta, por ruta relativa y por nombre en todo el árbol.

---

## B. AUDITORÍA DE ENTREGABLES

| Entregable | Estado inicial | Acción | Estado final | Verificación |
|------------|----------------|--------|--------------|--------------|
| `AI_PRE_LLM_CONTRACT.md` | COMPLETO | No modificar | COMPLETO | Revisado contra código |
| `INFORME_CIERRE_PRE_IA.md` | COMPLETO | No modificar | COMPLETE | A–H, hashes verificados |
| `probar_cierre_pre_ia.py` | COMPLETO | No modificar | COMPLETO | 54/54 PASS |
| `probar_gate_pre_ia.py` | COMPLETO | No modificar | COMPLETO | 15/15 PASS |
| `AI_PROJECT_CONTEXT.md` | PARCIAL | Ampliar | COMPLETO | Cifras + secciones nuevas |
| `ARCHITECTURE.md` | COMPLETO | Enlazar | COMPLETO | Citas verificadas |
| `08_DATABASE/architecture.md` | COMPLETO | Enlazar | COMPLETO | Sin cambios |
| `ARCHITECTURE_OVERVIEW.md` | FALTANTE | Crear | COMPLETO | Enlaces OK |
| `ARCHITECTURE_DECISIONS.md` | FALTANTE | Crear | COMPLETO | 12 fichas + 6 preguntas |
| `TECHNICAL_ROADMAP.md` | FALTANTE | Crear | COMPLETO | Fases A–G |
| `PROJECT_DOCUMENTATION_INDEX.md` | FALTANTE | Crear | COMPLETO | Rutas verificadas |
| Integridad documental | PARCIAL | Extender | COMPLETO | Suite nueva |
| `INFORME_CONSOLIDACION_ARQUITECTONICA.md` | FALTANTE | Crear | COMPLETO | Este fichero |
| Cifra `probar_ia_mock.py` | INCORRECTA | Corregir | CORRECTO | Ejecutada: 35 |

## C. DOCUMENTACIÓN CREADA O ACTUALIZADA

### C.1 Creados

| Fichero | Líneas | Contenido |
|---------|--------|-----------|
| `PROJECT_DOCUMENTATION_INDEX.md` | 135 | Índice central en 8 categorías, con propósito y estado por documento |
| `ARCHITECTURE_OVERVIEW.md` | 216 | Mapa de módulos (pipeline, servicio, IA), flujos, puntos de entrada, límites conocidos, puntos no claros |
| `ARCHITECTURE_DECISIONS.md` | 283 | 12 fichas de decisión (contexto/decisión/motivo/consecuencias/estado) + 6 preguntas abiertas |
| `TECHNICAL_ROADMAP.md` | 199 | Fases A–G con estado, dependencias, bloqueo y método de verificación |
| `INFORME_CONSOLIDACION_ARQUITECTONICA.md` | este | Informe de la misión |
| `dfchron/pruebas/probar_documentacion_indice.py` | 285 | Comprobación de integridad documental |

### C.2 Actualizados

| Fichero | Cambio | Motivo |
|---------|--------|--------|
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Cifra 32 → 35; añadida versión de evidencia, perspectivas y estado PRE-LLM | Cifra falsa; le faltaban las secciones §4.6 y el trabajo PRE-LLM |
| `08_DATABASE/ai_data_contract.md` | Cifra 32 → 35 | Cifra falsa |

### C.3 Sin cambios (deliberadamente)

`AI_PRE_LLM_CONTRACT.md`, `INFORME_CIERRE_PRE_IA.md`, `ARCHITECTURE.md`,
`08_DATABASE/architecture.md`, `README.md`, `API.md`, `WINDOWS.md`,
`probar_cierre_pre_ia.py`, `probar_gate_pre_ia.py`,
`probar_documentacion_ia.py`.

---

## D. ESTADO ARQUITECTÓNICO

El sistema es un pipeline de datos consultable con una capa de IA preparada y
**sin modelo**.

```
legends.xml + legends_plus.xml
   -> cargar_legends -> integrar_legends -> validar_semantica
   -> nucleo.py -> servicio.py -> api.py -> web/ | site/

Capa de IA (sin LLM):
   ia_conocimiento -> ia_contrato.contexto()   [política]
       -> [adaptador: UNA propuesta]
       -> ia_contrato.validar_salida()        [fail-closed]
       -> ia_estructura                       [verificación]
       -> ia_frontera.componer_seguro()       [texto desde el contexto]
```

**La ruta `MODELO → TEXTO → JUGADOR` no existe**, y esa es la propiedad que hace
auditable el conjunto.

Decisiones consolidadas en `ARCHITECTURE_DECISIONS.md`. Las doce están
**VIGENTES** y cada una tiene código y pruebas detrás. Seis preguntas siguen
**PENDIENTES** y están separadas de las decisiones para que no se confundan.

### Lo que la consolidación añadió conceptualmente

Una separación que antes no estaba escrita en ningún sitio: **D09**, que dice que
`dataset_id` **no** es un reloj. El trabajo PRE-LLM cerró I14 integrando la
versión real del dataset, y fue fácil leer eso como «la temporalidad está
resuelta». No lo está. La caducidad y el estado en vivo siguen abiertos, y ahora
eso está escrito como decisión, no como nota al pie.

---

## E. ESTADO DE PRE-LLM

### Garantías conservadas (verificadas, no supuestas)

| Garantía | Cómo se comprueba | Estado |
|----------|-------------------|--------|
| `DATASET_ID` identifica el dataset | `dataset_actual()` lee `dataset_version.json` | CONSERVADA |
| Evidencia trazable | `evidencia()` con entidad, `df_id`, campos, función, fuente | CONSERVADA |
| Evidencia obsoleta rechazada | `evidencia_es_actual()` fail-closed | CONSERVADA |
| Fail-closed en validación | `validar_salida()` | CONSERVADA |
| Verificada ≠ No verificada | `ia_estructura` con tres estados | CONSERVADA |
| La ruta al jugador no existe | `componer_seguro()` compone desde el contexto | CONSERVADA |
| Limitaciones declaradas | `AI_PRE_LLM_CONTRACT.md` §11 | CONSERVADA |

### Limitaciones que siguen abiertas

Ninguna se cerró. Están en `ARCHITECTURE_OVERVIEW.md` §8.2,
`AI_PRE_LLM_CONTRACT.md` §11 y `INFORME_CIERRE_PRE_IA.md` §E.3:

* **Verificación semántica** — no existe; `NO_APLICABLE`.
* **Relaciones complejas** — sin identidad estable; fuera de alcance.
* **Caducidad temporal** — no hay reloj de juego.
* **Estado en vivo** — el dataset es una foto.
* **Memoria conversacional** — no existe.
* **Trazabilidad léxica** — medida de descripción, no barrera de seguridad.
* **`deteccion_fuga()`** — esqueleto: detecta coordenadas, no paráfrasis.

`TestLimitacionesVisibles` falla si alguna de estas desaparece de los tres
documentos clave.

## F. PRUEBAS

### Comandos ejecutados y resultados

| Comando | Resultado |
|---------|-----------|
| `probar_gate_pre_ia.py` | **15 tests — OK** |
| `probar_cierre_pre_ia.py` | **54 tests — OK** |
| `probar_auditoria_final.py` | **49 tests — OK** |
| `probar_documentacion_ia.py` | **51 tests — OK** |
| `probar_documentacion_indice.py` | **11 tests — OK** |
| `probar_contrato_ia.py` | 49 tests — OK |
| `probar_contrato_io.py` | 48 tests — OK |
| `probar_semantica_ia.py` | 59 tests — OK |
| `probar_verificacion_estructurada.py` | 18 tests — OK |
| `probar_riesgos_abc.py` | 25 tests — OK |
| `probar_ia_contexto.py` | 39 tests — OK |
| `probar_puente_conocimiento.py` | 52 tests — OK |
| `probar_estado_conocimiento.py` | 48 tests — OK |
| `probar_ia_mock.py` | 35 tests — OK |
| `probar_frontera_inferencia.py` | 12 tests — OK |
| `probar_frontera_linguistica.py` | 25 tests — OK |
| `probar_banco_ia.py` | 29 tests — OK |
| `probar_geografia.py` | 41 tests — OK |
| `evaluar_banco_ia.py` | **83/83, 0 fugas, 0 discrepancias** |

Todas con `python dfchron\pruebas\<suite>` desde la raíz del proyecto.

**Comparación con la línea base:** las cifras de las 18 suites existentes son
**idénticas** a las del inicio de la misión. Ninguna prueba se eliminó ni se
debilitó. Lo único añadido es la suite nueva de 11 pruebas.

### La prueba nueva detecta el fallo que motivó la misión

Para no entregar una comprobación que pasara siempre, se reprodujo
voluntariamente el error que esta misión encontró (32 en lugar de 35):

```
FAIL: dice 32 pruebas de probar_ia_mock.py; el código ejecuta 35
Ran 11 tests — FAILED (failures=1)
```

Documento restaurado a 35 y la suite vuelve a **OK**. La comprobación tiene
dientes.

### Advertencia sobre tiempos

`probar_documentacion_indice.py` **ejecuta 10 suites** para contar sus pruebas, y
tarda ~65 s. Es deliberado: una cifra declarada tiene que salir de ejecutarla, no
de contarla con `def test_`. Si molesta en el bucle de trabajo, conviene
ejecutarla aparte de la regresión rápida, **no** relajarla.

---

## G. CAMBIOS DE CÓDIGO

**Ninguno.** Esta misión no ha modificado código de producción.

Comprobado por hash SHA-256, antes y después, en los 14 módulos:

```
00_SOURCE/tools/nucleo.py        SIN CAMBIOS      dfchron/ia_contrato.py       SIN CAMBIOS
00_SOURCE/tools/rutas.py         SIN CAMBIOS      dfchron/ia_estructura.py     SIN CAMBIOS
dfchron/api.py                   SIN CAMBIOS      dfchron/ia_frontera.py       SIN CAMBIOS
dfchron/servicio.py              SIN CAMBIOS      dfchron/ia_inferencia.py     SIN CAMBIOS
dfchron/contrato_ia.py           SIN CAMBIOS      dfchron/ia_mock.py           SIN CAMBIOS
dfchron/estado_conocimiento.py   SIN CAMBIOS      dfchron/ia_verificacion.py   SIN CAMBIOS
dfchron/ia_conocimiento.py       SIN CAMBIOS
dfchron/ia_contexto.py           SIN CAMBIOS
```

El **único fichero de código** creado es `dfchron/pruebas/probar_documentacion_indice.py`,
que es una prueba, no producción. Importa solo `io`, `os`, `re`, `subprocess`,
`sys`, `unittest`: **sin dependencias externas**.

Sobre el diff de Git: **no hay repositorio Git en este proyecto.** No se ha
verificado ningún diff de Git porque no existe. La comparación se hizo por
hashes SHA-256 antes y después.

---

## H. PENDIENTES

### Lo que esta misión NO ha hecho

| Pendiente | Por qué |
|-----------|---------|
| Integración con DF-Hack | La vía **no está decidida**. Es `P5` y fase F del roadmap |
| Verificación semántica | No existe. `NO_APLICABLE`, y no se usará otro LLM como juez |
| Identidad relacional | El dataset no la da. Fuera de alcance verificable |
| Caducidad temporal | Requiere un reloj de juego, que no existe |
| Memoria conversacional | No existe ni se ha pedido |
| Auditoría de `dfchron/site/` (Astro) | No participa del camino de datos ni de la capa de IA |

### Lo que quedó sin ejecutar

Estas suites **no se ejecutaron** en esta misión, porque necesitan servidor HTTP
o dataset completo:

`probar_api.py`, `probar_web.py`, `probar_actualizacion.py`,
`probar_refresh_cycle.py`, `probar_integracion.py`, `probar_nucleo.py`,
`probar_adversarial.py`, `test_determinismo.py`, `verificar_reproducibilidad.py`.

Consecuencia honesta: la auditoría **sí verificó que esos ficheros existen** y
que las rutas que cita `ARCHITECTURE.md` son correctas. Lo que **no** hizo fue
ejecutarlos. Sus cifras en ese documento (20, 48, 39, 54) **siguen sin
revalidar**, y son anteriores a esta misión.

Lo mismo ocurre con las cifras propias de `ai_data_contract.md`, que no se
comprueban automáticamente.

Si esto importa, el sitio natural es añadir esos documentos a `CON_CIFRAS` en la
suite nueva, aceptando el coste de ejecutar esas suites.

---

## I. CONFIRMACIÓN DE RESTRICCIONES

| Restricción (§10) | Cumplida | Cómo se comprueba |
|-------------------|----------|-------------------|
| No implementar un LLM | **Sí** | No hay ningún modelo |
| No añadir llamadas a APIs de IA | **Sí** | Sin red; `probar_ia_mock.py` corre el flujo entero |
| No añadir RAG | **Sí** | Ausente |
| No añadir embeddings | **Sí** | Ausente |
| No añadir memoria conversacional | **Sí** | Ausente; registrado como límite en §G del roadmap |
| No añadir dependencias de proveedores de IA | **Sí** | `test_no_hay_sdk_de_ia_en_el_codigo` recorre `dfchron/` |
| No implementar conocimiento omnisciente | **Sí** | Sin cambios de código |
| No implementar políticas de revelación en producción | **Sí** | Sin cambios de código |
| No alterar el núcleo sin necesidad | **Sí** | Hashes idénticos |
| No reescribir módulos que funcionan | **Sí** | Hashes idénticos |
| No eliminar pruebas existentes | **Sí** | Las 18 suites siguen; cifras idénticas |
| No rebajar garantías | **Sí** | Gate 15/15, cierre 54/54, auditoría 49/49 |
| No convertir pendientes en aprobadas | **Sí** | Las 6 preguntas siguen `PENDIENTE`; las limitaciones, comprobadas por prueba |
| No inventar funcionalidades | **Sí** | `TestNoSeVendeLoInexistente` |
| No hacer refactorización general | **Sí** | Cero cambios de código |

### Una nota sobre «no inventar funcionalidades»

`ARCHITECTURE_DECISIONS.md` incluye una sección de **preguntas abiertas** (P1–P6)
separada de las decisiones. Podría haberse omitido por si se confundía con
compromisos. Se mantuvo porque el riesgo real no es que alguien las lea como
decisiones: es que las capacidades que faltan **no estén escritas en ningún
sitio**, y eso es peor.

---

## J. CONCLUSIÓN

La documentación ahora describe **lo que el proyecto es hoy**: qué módulo hace
qué, por qué se decidió así, qué garantías existen con pruebas detrás, y qué
sigue sin demostrarse.

Dos cosas cambiaron de verdad, no solo en el papel:

1. **Una cifra falsa corregida** en dos documentos, y una comprobación que
   demuestra que ya no puede volver a colarse sin que nadie lo note.
2. **Una separación escrita** que antes no estaba: `dataset_id` no es un reloj.
   El cierre PRE-LLM resolvió I14, y era fácil leer eso como «la temporalidad
   está resuelta». No lo está. Ahora está escrito como decisión, con su límite.

El índice y los cuatro documentos nuevos se referencian entre sí y están
verificados por comprobación automática. Un documento renombrado rompe la
prueba en vez de dejar un enlace mentiroso.

---

> **Sin IA implementada.** El núcleo sigue siendo la autoridad.
> El modelo, cuando llegue, solo va a proponer.