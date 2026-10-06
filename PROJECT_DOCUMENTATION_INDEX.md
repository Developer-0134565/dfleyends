# PROJECT DOCUMENTATION_INDEX

Índice central de la documentación de **DF-Chronicles**.

**Regla de este índice:** una entrada existe solo si el fichero existe. La
comprobación es automática (`probar_documentacion_indice.py`), así que un
documento renombrado o borrado rompe la prueba en vez de dejar un enlace
mentiroso.

> **Al incorporarse a este proyecto, lea esto primero.** Para qué sirve cada capa,
> qué garantías existen y qué queda sin demostrar, ver `README.md`.

---

## 1. Punto de entrada

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `README.md` | Qué es el proyecto, cómo se arranca, mapa de la documentación | Vigente |
| `WINDOWS.md` | Puesta en marcha en Windows | Vigente |
| `API.md` | Endpoints HTTP disponibles | Vigente |

---

## 2. Arquitectura

Estos tres documentos **se complementan, no se duplican**. Léanse en orden.

| Ruta | Cubre | Estado |
|------|-------|--------|
| `ARCHITECTURE.md` | Cadena completa: XML → núcleo → servicio → API → UI. Las cinco reglas de diseño | Vigente |
| `08_DATABASE/architecture.md` | Capa de datos: las dos fuentes, reglas de merge, modelo de certeza, rendimiento | Vigente |
| `ARCHITECTURE_OVERVIEW.md` | Navegador: qué módulo es quién, flujo de datos y de verificación, límites | Vigente |

---

## 3. Decisiones

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `ARCHITECTURE_DECISIONS.md` | 12 decisiones arquitectónicas con contexto, motivo y consecuencias | Vigente |
| `TECHNICAL_ROADMAP.md` | Hoja de ruta por fases (A–F), con dependencias y bloqueos | Vigente |

---

## 4. Contratos (IA)

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | **Contrato congelado previo al LLM.** Autoridad, flujo, campos prohibidos, texto libre, temporalidad, identidad, descubrimiento, adaptador | **Congelado** |
| `08_DATABASE/ai_data_contract.md` | Contrato de datos: el formato de las afirmaciones y su semántica | Vigente |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Contexto operativo para quien programe la capa de IA | Vigente |

### 4.1 Contratos (consulta de datos)

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `DATA_QUERY_SERVICE_CONTRACT.md` | **Contrato de la capa de consulta determinista.** Operaciones, estados, identidad, evidencia, temporalidad, límites. Independiente de HTTP, Web, CLI e IA | Vigente |
| `AI_CONSUMER_BOUNDARY.md` | **Qué podrá pedir y recibir un futuro consumidor IA.** Perímetro de acceso, clasificación de datos, fugas, adaptación futura. **No hay IA** | Vigente |
| `INFORME_INTEGRACION_API_WEB_CONSULTA.md` | **Integración de API y Web con el contrato.** Mapa de consumidores, endpoints migrados y fuera, **mutation testing permanente (5/5)**, flujo de ejecución instrumentado | Vigente |

---

## 5. Documentación de datos

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `08_DATABASE/data_limitations.md` | Lo que los datos **no** permiten saber | Vigente |
| `08_DATABASE/query_reference.md` | Referencia de consultas | Vigente |
| `08_DATABASE/relationship_semantics.md` | Semántica de las relaciones | Vigente |
| `08_DATABASE/decision_storage.md` | Dónde y cómo se guardan las decisiones del jugador | Vigente |

---

## 6. Auditorías e informes

| Ruta | Propósito | Estado |
|------|-----------|--------|
| `INFORME_CIERRE_PRE_IA.md` | Cierre de la fase PRE-LLM: cambios, invariantes, riesgos | Vigente |
| `INFORME_AUDITORIA_FINAL_PRE_IA.md` | Auditoría adversarial final (18 invariantes, 44 ataques) | Vigente |
| `INFORME_CONSOLIDACION_ARQUITECTONICA.md` | Consolidación documental: auditoría de entregables y estado | Vigente |
| `INFORME_AUDITORIA_ENDURECIMIENTO_NUCLEO.md` | Auditoría técnica: identidad, relaciones, evidencia, determinismo | Vigente |
| `INFORME_COBERTURA_SEMANTICA_NUCLEO.md` | Fuentes, identidad, semántica determinista, temporalidad | Vigente |
| `INFORME_CAPA_CONSULTA_DETERMINISTA.md` | Capa de consulta determinista: contrato, estados, evidencia, pruebas, mutation testing | Vigente |
| `INFORME_VERIFICACION_EVIDENCIA.md` | Estado de la verificación de evidencia | Historial |
| `INFORME_RIESGOS_ABC.md` | Riesgos A/B/C y sus resoluciones | Historial |
| `INFORME_AUTORIA_EXTREMA.md` | Auditoría de autoría y modelo no confiable | Historial |
| `dfchron/INFORME_FRONTERA_LINGUISTICA.md` | La frontera lingüística, con sus límites | Vigente |
| `dfchron/INFORME_EVALUACION_BANCO_IA.md` | Resultado del banco adversarial | Vigente |
| `P1_VERSIONADO_MUNDO_VIVO.md` | Investigación: por qué `dataset_id` no identifica el estado vivo | Vigente |
| `P1.1_IDENTIDAD_MUNDO.md` | Captura de `world_name` / `world_folder`; qué sigue sin resolverse | Vigente |
| `P1.2_PROPAGACION_IDENTIDAD_MUNDO.md` | Dónde vive la identidad del mundo y cómo llega a los consumidores | Vigente |

Los informes marcados **Historial** describen un estado pasado. Se conservan
porque explican decisiones, no porque describan el sistema hoy.

En `00_SOURCE/` hay ~28 informes de extracción, integración y validación. Son
historia de la construcción del dataset; para el estado actual, la fuente de
verdad es `dataset_version.json`.

---

## 7. Pruebas

Todas en `dfchron/pruebas/`, salvo las de pipeline en `00_SOURCE/tools/`.

| Suite | Cubre | En |
|-------|-------|----|
| `probar_gate_pre_ia.py` | **Gate**: 15 invariantes previos al LLM | `dfchron/pruebas/` |
| `probar_cierre_pre_ia.py` | Cierre PRE-IA: temporalidad, descubrimiento, aislamiento, persistencia | `dfchron/pruebas/` |
| `probar_auditoria_final.py` | Auditoría final, 18 invariantes | `dfchron/pruebas/` |
| `probar_documentacion_ia.py` | La documentación no puede mentir sobre el código | `dfchron/pruebas/` |
| `probar_documentacion_indice.py` | Integridad: enlaces y cifras de este índice | `dfchron/pruebas/` |
| `probar_contrato_ia.py`, `probar_contrato_io.py` | Contrato de afirmaciones y de entrada/salida | `dfchron/pruebas/` |
| `probar_semantica_ia.py` | Semántica congelada (144 combinaciones) | `dfchron/pruebas/` |
| `probar_ia_contexto.py`, `probar_puente_conocimiento.py` | Recuperación real y puente núcleo→afirmaciones | `dfchron/pruebas/` |
| `probar_estado_conocimiento.py` | Estado del jugador, persistencia, fail-closed | `dfchron/pruebas/` |
| `probar_ia_mock.py`, `probar_frontera_inferencia.py`, `probar_frontera_linguistica.py` | Flujo sin LLM y fronteras | `dfchron/pruebas/` |
| `probar_banco_ia.py`, `evaluar_banco_ia.py` | Banco adversarial (83 escenarios) | `dfchron/pruebas/` |
| `probar_api.py`, `probar_web.py`, `probar_geografia.py`, `probar_actualizacion.py`, `probar_refresh_cycle.py` | API, UI, geografía, refresco | `dfchron/pruebas/` |
| `probar_integracion.py`, `probar_nucleo.py`, `probar_adversarial.py`, `test_determinismo.py`, `verificar_reproducibilidad.py` | Pipeline y núcleo | `00_SOURCE/tools/` |
| `verificacion_semantica.py` | Verificación determinista de afirmaciones estructuradas (7 niveles). **NO confundir con `validar_semantica.py`**, que valida el dataset | **Código nuevo** |
| `probar_verificacion_semantica.py` | 38 pruebas de los 7 niveles | `00_SOURCE/tools/` |
| `probar_adversarial_nucleo.py` | Campos adicionales y datos incompletos: el núcleo no inventa | `00_SOURCE/tools/` |

**Las nueve suites que la consolidación anterior dejó sin ejecutar, ya
ejecutadas:** `probar_integracion` (20), `probar_nucleo` (48),
`probar_adversarial` (39), `test_determinismo` (29 consultas × 4 procesos),
`verificar_reproducibilidad`, `probar_api` (54), `probar_web` (65),
`probar_actualizacion` (43), `probar_refresh_cycle` (28). Todas en PASS.
Resultado en `INFORME_AUDITORIA_ENDURECIMIENTO_NUCLEO.md` §B.

Las cifras de pruebas por suite **no** se declaran aquí a propósito: se
comprueban contra el código en `probar_documentacion_indice.py`. Publicarlas
en el índice obligaría a mantenerlas al día a mano, que es justo el modo de
fallar que la misión quiere evitar.

---

## 8. Estado del proyecto

| Qué | Valor |
|-----|-------|
| Dataset activo | `v1-04170363943d4ba1` |
| Identidad del mundo | **Capturada y propagada** (`world_name`, `world_folder` vía `/api/salud`) — `P1.2_PROPAGACION_IDENTIDAD_MUNDO.md` |
| Identidad del estado vivo | **NO RESUELTA** — abierta en P1 |
| IA implementada | **Ninguna.** No hay LLM, ni SDK, ni endpoint de IA |
| Gate PRE-LLM | **PASS** (15 invariantes) |
| Conclusión de la fase | `PRE-LLM CERRADO CON RESERVAS` |

Lo que sigue **sin demostrar** está en `INFORME_CIERRE_PRE_IA.md` §E.3 y en
`08_DATABASE/AI_PRE_LLM_CONTRACT.md` §11. No está cerrado, y no debe leerse
como cerrado.

En particular: **`state_version` no es identidad del estado vivo.** Es
`dataset_id`, que es un hash del contenido extraído. No existe todavía una
identificación fiable del estado de un mundo en ejecución.

---

## Mantenimiento de este índice

Al añadir, renombrar o borrar un documento: actualiza este fichero en el mismo
cambio. `probar_documentacion_indice.py` falla si una ruta deja de existir, así
que la omisión no pasa desapercibida.