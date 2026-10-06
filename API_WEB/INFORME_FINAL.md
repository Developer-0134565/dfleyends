# API/WEB — INFORME FINAL

> **Veredicto: API/WEB CERRADA.**
> Con una salvedad declarada, no oculta: quedan 5 deudas arquitectónicas
> documentadas, ninguna bloqueante, ninguna oculta.

Expediente: [`00_DIARIO.md`](00_DIARIO.md) ·
[`01_MAPA_ENDPOINTS.md`](01_MAPA_ENDPOINTS.md) ·
[`02_DECISIONES.md`](02_DECISIONES.md) ·
[`03_EVIDENCIAS.md`](03_EVIDENCIAS.md) ·
[`04_MUTACIONES.md`](04_MUTACIONES.md) ·
[`05_PRUEBAS.md`](05_PRUEBAS.md)

---

## 0. La premisa de la misión era falsa, y eso cambió el trabajo

La misión se enuncia como si hubiera que **construir** la frontera API/Web.
No había que construirla: ya existía, implementada y probada por una misión
anterior (`ARCHITECTURE_DECISIONS.md` D18).

Eso convirtió la misión en **auditoría y cierre verificable**, que es más difícil:
no basta con que las pruebas den verde, hay que demostrar que prueban algo.

---

## Respuestas a las 20 preguntas

| # | Pregunta | Respuesta |
|---:|---|---|
| 1 | **¿Qué endpoints pasan por `servicio_consulta`?** | **13 de 51**: las 5 fichas (`/api/figuras/{id}`, `/api/entidades/{id}`, `/api/sitios/{id}`, `/api/artefactos/{id}`, `/api/eventos/{id}`), `/api/figuras/{id}/relaciones` y las 7 rutas `/api/consulta/*` |
| 2 | **¿Cuáles quedan fuera y por qué?** | **38**. Navegación (un «no aparece» no es un hecho), estadísticas, metadatos, salud y exportación. Cada una con motivo en `01_MAPA_ENDPOINTS.md` |
| 3 | **¿La Web tiene acceso directo al dataset?** | **No.** Cero `readFileSync`, `XMLHttpRequest`, `fs`, `.jsonl` o `.xml`. Solo `fetch` a `/api/...` |
| 4 | **¿Se demostró el flujo por ejecución real?** | **Sí.** `TestD_Bypass` instrumenta las 6 operaciones del servicio, pide 10 rutas por HTTP y exige verlas ejecutarse. Y demuestra lo contrario: 6 rutas de navegación **no** la usan |
| 5 | **¿Cuántas mutaciones se introdujeron?** | **9** (el harness tenía 5; se ampliaron a 9) |
| 6 | **¿Cuántas fueron detectadas?** | **9**. Supervivientes: **0** |
| 7 | **¿Qué estados se preservan?** | `FOUND`, `NOT_FOUND`, `NOT_VERIFIED`, `INVALID_QUERY`, `DATA_UNAVAILABLE`, más `status`, `certainty` y `ok`. Medidos contra el servidor real |
| 8 | **¿Qué evidencia se preserva?** | `evidence` en las 5 fichas, con `state_version`, `funcion` y `fuente`. Las mutaciones B (borrarla) y G (falsear `state_version`) se detectan |
| 9 | **¿Se preservan `dataset_id` y `state_version`?** | **Sí.** El `dataset_id` viaja en la raíz; `state_version`, en la evidencia. Una prueba exige que **coincidan entre sí**: si uno se falsea, se nota |
| 10 | **¿Se preserva la identidad del mundo?** | **Sí, y sin inventarla.** El sobre de consulta **no** lleva `mundo`: no hay identidad de mundo demostrada. El mundo viaja solo donde existe (`/api/salud`), con su motivo de ausencia |
| 11 | **¿Qué compatibilidad se mantiene?** | Las fichas viejas conservan su envelope íntegro y solo **ganan** claves. `NOT_VERIFIED ≠ NOT_FOUND`, y `NOT_VERIFIED` **no** se degrada a 404 ni a 503 |
| 12 | **¿Qué limitaciones quedan?** | No se probó la **build de Astro en producción** (las reglas del proyecto no permiten regenerar artefactos publicados) ni un navegador real. Se auditó el código fuente y sus 65 pruebas |
| 13 | **¿Qué deuda arquitectónica queda?** | **5**, todas en `02_DECISIONES.md`: ruta duplicada, `evidence: null`, código muerto, Web sin contrato de tipos, docs desactualizadas |
| 14 | **¿Qué ficheros se modificaron?** | Solo de pruebas y documentación. **Ningún fichero de producción de la API, la Web o el servicio** |
| 15 | **¿Qué hashes cambiaron?** | **Ninguno.** Los 7 recursos vigilados conservan su hash exacto, incluidos los dos XML y el contrato congelado |
| 16 | **¿Cuántos tests antes/después?** | **588 → 606.** +18 nuevos, 0 eliminados, 0 relajados |
| 17 | **¿Hay alguna dependencia de IA?** | **No.** Cero SDK, cero cliente HTTP de IA, cero embeddings. Lo único que menciona un modelo es un docstring que explica que **no hay ninguno** |
| 18 | **¿Queda algún acceso directo al dataset?** | **No.** Ni en la API ni en la Web |
| 19 | **¿Sobrevive alguna mutación?** | **No.** 9/9 detectadas |
| 20 | **¿Siguiente misión recomendada?** | §6 |
---

## 1. Arquitectura: demostrada

```text
API → adaptador_consulta → servicio_consulta → núcleo     (13 rutas)
Web → API → adaptador_consulta → servicio_consulta → núcleo
```

**Verificado por ejecución, no por lectura.** `auditar_frontera.py` lee el
código de cada manejador y determina a quién llama:

```
Rutas registradas            : 51
Delegan en el adaptador      : 13
Deberian pasar por frontera  : 13
Discrepancia                 : 0
```

La **ausencia** de discrepancia es el resultado. Una frontera usada de más
también sería un defecto: significaría pagar el coste de la evidencia sin
comprar nada.

### Por qué 13 y no 51

El criterio es semántico: *¿el endpoint afirma algo?*

`/api/figuras/712/relaciones` está dentro. `/api/figuras/712/eventos` está
fuera. La primera es *la* relación de esa figura: sujeto único, verificable. La
segunda es *la lista* de eventos donde aparece, y **un listado no se verifica
elemento a elemento**. El perímetro termina donde `verificar()` tiene algo que
verificar.

---

## 2. La Web: sin acceso directo

| Búsqueda | Resultado |
|---|---|
| `readFileSync`, `XMLHttpRequest`, `node:fs`, `require(`, `readFile` | **0** |
| `.jsonl`, `legends.xml`, `legends_plus` | **0 accesos** |
| Reconstrucción de búsquedas o índices | **0** |

Dos coincidencias aparentes, revisadas una a una:
`web/index.html:38` dice `legends.xml` en un texto descriptivo;
`site/src/lib/mapa.ts:25` dice `sites.jsonl` en un **comentario**.
Ninguna de las dos lee nada.

`web/app.js` tiene **dos** `fetch`: uno genérico y `/api/salud`.
`site/src/lib/api.ts` es el punto único de red. `dataset.ts` lee el
`dataset_id` **del envelope**, nunca del disco.

---

## 3. Mutaciones: 9/9, 0 supervivientes

| ID | Mutación | Detectada por |
|---|---|---|
| A | `dataset_id` anuncia otro mundo | integración, **adversarial** |
| B | evidencia se borra | integración, **adversarial** |
| C | `NOT_VERIFIED` → `FOUND` | integración, **adversarial** |
| D | `buscar_relaciones` deja de delegar | integración, api |
| E | el adaptador salta a `servicio.py` | integración, api, web, **adversarial** |
| F | `dataset_id` desaparece | integración, **adversarial** |
| G | `state_version` falseado | integración, **adversarial** |
| H | el adaptador lee el núcleo | integración, api, web, **adversarial** |
| I | la API fabrica la respuesta | integración, api, web, **adversarial** |

Las tres nuevas eran las que faltaban de las 8 categorías exigidas: **F**
(eliminar `dataset_id`, no solo falsearlo), **G** (`state_version`, que vive en
`ia_conocimiento`, no en el servicio) e **I** (respuesta fabricada).

**I es la que justifica el harness entero**: fabricar un envelope *correcto por
casualidad* no lo detectaría ninguna prueba de igualdad de valores. Solo lo
detecta que la ruta **deje de llamar al adaptador**.

---

## 4. Lo que salió mal, y no se tapa

### 4.1 Un fichero de producción se quedó mutado

Una ejecución del harness fue cancelada por el límite de 30 s de la shell
**con una mutación aplicada**. El `finally` no corrió y
`servicio_consulta.py` quedó con `evidence = None`.

**Lo interesante: ningún test falló.** El sistema *funcionaba* con la evidencia
rota. Solo el hash lo delató. Restaurado byte a byte
(`0a5b6b1c…` → `689047bb…` → `0a5b6b1c…`).

**Consecuencia de diseño, no de esta misión:** un harness que muta ficheros de
producción no es seguro frente a una interrupción. El `finally` protege de las
excepciones, no de que maten el proceso. Documentado, con su modo de fallo, en
`04_MUTACIONES.md`.

### 4.2 Cuatro de mis pruebas fallaron de primeras

Todas porque las escribí **suposiendo** el contrato en vez de mirarlo. El caso
peor: `verificar?predicado=es_de_tipo&objeto=kobold` devolvió `FOUND` porque la
figura 712 **sí** es un kobold. Una prueba que esperase `NOT_VERIFIED` habría
pasado **por la razón equivocada** el día que el resultado cambiara.

Se escribió una sonda para imprimir las respuestas reales antes de afirmar nada,
y se corrigieron las pruebas contra lo observado. Decisión D-008.

### 4.3 Una carrera que inventé yo

Lancé la regresión **al mismo tiempo** que el harness de mutación, que estaba
mutando ficheros de producción. Dos suites «fallaron» — falsa alarma, ninguna
prueba estaba mal. Relanzado en solitario: 15/15 en verde.

Vale la pena dejarlo escrito: es la razón por la que `05_PRUEBAS.md` insiste en
que el banco **nunca** corre en paralelo con el harness.

### 4.4 Dos defectos reales, no corregidos

| Defecto | Por qué no se corrigió |
|---|---|
| `/api/artefactos` registrada dos veces; la segunda es inalcanzable | Arreglarlo cambiaría el contrato de una ruta con clientes |
| `evidence: null` en `/api/consulta/evidencia/*` | El arreglo está en `servicio_consulta.py`, **congelado** por esta misión |

Ninguno rompe nada. Los dos están documentados con su causa exacta.
---

## 5. Integridad

### Hashes: ninguno cambió

| Recurso | Estado |
|---|---|
| `dfchron/servicio_consulta.py` | **intacto** `0a5b6b1c…` |
| `dfchron/adaptador_consulta.py` | **intacto** `c456256e…` |
| `dfchron/api.py` | **intacto** `0426f63a…` |
| `dfchron/ia_conocimiento.py` | **intacto** `63954816…` |
| `dfchron/web/app.js` | **intacto** `297087bc…` |
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | **intacto** `5d2c3d00…` |
| `legends.xml` / `legends_plus.xml` | **intactos** |

> Un script de comparación mío marcó dos de ellos como «CAMBIO» por un fallo de
> PowerShell al indexar claves con barras invertidas. Verificado byte a byte
> después: **intactos**. Se dice aquí porque el aviso existió.

### Cero IA

Sin SDK, sin cliente HTTP de IA, sin embeddings, sin agentes, sin prompts.
`ia_inferencia.py:288` dice literalmente *«La interfaz con un modelo. SOLO la
interfaz; no hay ninguna aquí»*.

### Ficheros creados o modificados

**Creados** (documentación y herramientas de auditoría, todas en `API_WEB/`):

```
API_WEB/00_DIARIO.md, 01_MAPA_ENDPOINTS.md, 02_DECISIONES.md,
API_WEB/03_EVIDENCIAS.md, 04_MUTACIONES.md, 05_PRUEBAS.md, INFORME_FINAL.md
API_WEB/auditar_frontera.py, mapa_frontera.json, mapa_frontera.txt
API_WEB/probar_frontera_adversarial.py, restaurar_servicio.py
API_WEB_MAPA_FRONTERA.md
```

**Modificados** (solo pruebas, nunca producción):
`dfchron/pruebas/probar_mutation_frontera.py`

**No modificados:** `servicio_consulta.py`, `adaptador_consulta.py`, `api.py`,
`servicio.py`, `ia_conocimiento.py`, `web/`, `site/`, los XML, los JSONL y el
contrato congelado.

### Temporales

Ninguno de esta misión. Los que aparecen con `_` en `00_SOURCE/tools/*.png` y
los `__pycache__` son **preexistentes** de la misión P1.3 o subproducto normal de
ejecutar Python; no se han tocado.

---

## 6. Siguiente misión recomendada

**Corregir las deudas que quedaron fuera de alcance**, por impacto:

1. **`evidence: null` en `/api/consulta/evidencia/*`** — una línea, y elimina la
   única inconsistencia real del contrato. Requiere permiso para tocar
   `servicio_consulta.py`.
2. **`/api/artefactos` duplicada** — hay que **decidir** si la ruta debe ser
   búsqueda o listado. No es un arreglo mecánico: es una decisión de contrato.
3. **Código muerto de `adaptador_consulta.py`** (3 líneas) — trivial, pero
   cualquier futuro cambio de ese fichero lo dificulta.

Y después, lo que de verdad importa y no depende de ninguna de estas:

4. **Hacer el harness de mutación seguro por construcción**, mutando copias en
   un directorio temporal en vez de ficheros de producción. Es lo que impide que
   una interrupción deje el repositorio inconsistente.
5. **Prueba de la build de Astro en producción**, cuando las reglas del proyecto
   permitan publicar artefactos.

---

## Veredicto

```text
API → adaptador_consulta → servicio_consulta → núcleo      13 rutas
Web → API → adaptador_consulta → servicio_consulta → núcleo
```

- Mutaciones introducidas / detectadas: **9 / 9**
- Mutaciones supervivientes: **0**
- Hashes de producción alterados: **0**
- Dependencias de IA: **0**
- Accesos directos de la Web al dataset: **0**
- Tests: **588 → 606**, ninguno eliminado ni relajado

**API/WEB CERRADA.**

La frontera está terminada antes de conectar ningún modelo. Un futuro
consumidor IA será simplemente otro consumidor de este mismo contrato, sin
privilegios arquitectónicos especiales: es lo que las 9 mutaciones y las 18
pruebas adversariales hacen demostrable, y no una promesa.