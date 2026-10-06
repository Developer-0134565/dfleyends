# API/WEB — DIARIO DE LA MISIÓN

> Se escribe **durante** la misión. No se borra ninguna entrada.
> Cada entrada: fecha, hipótesis, comprobación, resultado, decisión.

---

## [2026-10-04 — E0. Reconocimiento: ¿qué existe ya?]

**Hipótesis.** La misión cierra una frontera que aún no existe, y habrá que
construirla.

**Comprobación.** Inventario del repositorio antes de leer una sola línea:
- `dfchron/servicio_consulta.py` — **EXISTE** (frozen, 460 líneas)
- `dfchron/adaptador_consulta.py` — **EXISTE**
- `dfchron/api.py` — 48 rutas, importa `adaptador_consulta as ac`
- `dfchron/pruebas/probar_integracion_consulta.py` — **EXISTE** (suite de integración)
- `dfchron/pruebas/probar_mutation_frontera.py` — **EXISTE** (harness PERMANENTE,
  5 mutaciones A–E)
- `INFORME_INTEGRACION_API_WEB_CONSULTA.md` — **EXISTE**
- `ARCHITECTURE_DECISIONS.md` D18 — la decisión de integración ya está tomada

**Resultado.** **La premisa implícita de la misión es falsa.** La frontera
API → adaptador → servicio_consulta **ya está implementada y probada** por una
misión anterior (D18). La misión NO es de construcción: es de **auditoría y
cierre verificable** de lo que hay.

Esto cambia el trabajo a hacer, y hay que decirlo en lugar de rehacerlo:
- No hay que migrar endpoints: hay que **clasificar** los ya migrados y los que
  legítimamente no lo están.
- No hay que crear el harness de mutación: hay que **auditarlo** y completar los
  casos que la misión exige y todavía no cubre.

**Decisión.** D-001 — tratar la misión como *auditoría de una frontera existente*
y ampliar únicamente los huecos demostrables. No reescribir lo que funciona.

---

## [2026-10-04 — E1. Mapa de rutas: qué pasa por la frontera]

**Hipótesis.** Las fichas (`/api/figuras/{id}` etc.) y las rutas
`/api/consulta/*` pasan por el adaptador; el resto va directo a `servicio.py`.

**Comprobación.** Lectura íntegra de `api.py` (líneas 106–386) y del bloque
`R.add(...)` de cada ruta.

**Resultado.** Confirmado, y más preciso de lo que asumía:

| Grupo | Nº | Delega en |
|---|---:|---|
| Fichas de entidad | 5 | `ac.ficha_*` → `qc.obtener_entidad` |
| Relaciones de figura | 1 | `ac.relaciones_figura` → `qc.buscar_relaciones` |
| Contrato `/api/consulta/*` | 7 | `ac.*` → `qc.*` |
| **Total por la frontera** | **13** | |
| Resto (búsqueda, listados, geografía, eventos, salud, stats, exportar…) | 35 | `svc.*` directo |

**Interpretación.** El criterio semántico de la misión ("¿el endpoint
proporciona *hechos* derivados del conocimiento?") coincide con el criterio
que el proyecto ya aplicó: las **fichas** y las **relaciones** son afirmaciones
sobre entidades concretas y por eso llevan identidad y evidencia. Los listados y
la geografía son **navegación**: dan un subconjunto para orientarse, no afirman
que algo sea cierto. Migrarlos no aportaría evidencia, solo coste.

**Decisión.** D-002 — el perímetro son esas 13 rutas. Se documenta por qué las
otras 35 se quedan fuera, una a una, en `01_MAPA_ENDPOINTS.md`.

---

## [2026-10-04 — E2. Auditoría de la Web: acceso directo]

**Hipótesis.** La Web no lee el dataset: solo habla con la API.

**Comprobación.** Búsqueda en `dfchron/web/*` y `dfchron/site/src/**` de:
`legends.xml`, `legends_plus`, `.jsonl`, `readFileSync`, `XMLHttpRequest`,
`node:fs`, `require(`, `readFile`, `.xml`, `dataset_id`, `indice`, `glob`.

**Resultado.**
- **Cero** accesos a disco. Ni `readFileSync`, ni `XMLHttpRequest`, ni `fs`.
- `app.js` tiene **dos** `fetch`: uno genérico (línea 45) y `/api/salud` (921).
- `site/src/lib/api.ts` centraliza la construcción de URL y hace `fetch`.
- `dataset_id` aparece en la Web, pero **leído del envelope de la respuesta**,
  nunca calculado. Eso es consumir, no acceder.
- `index.html:38` menciona `legends.xml` en un texto descriptivo estático.
- `mapa.ts:25` menciona `sites.jsonl` dentro de un **comentario**.

**Interpretación.** La Web no tiene conocimiento de cómo está almacenado el
dataset. Los dos únicos "riesgos" son texto y comentarios, no accesos.

**Decisión.** D-003 — cerrar la auditoría de la Web con un test que falle si
alguien reintroduce un acceso a disco en los ficheros de la Web.

---

## [2026-10-04 — E3. Hallazgo: código muerto en el adaptador]

**Hipótesis.** El adaptador es un módulo limpio y sin restos.

**Comprobación.** Lectura de `adaptador_consulta.py` líneas 249–256.

**Resultado.** Al final de `relaciones_figura()` hay **tres líneas inalcanzables**:

```python
    return _responder(qc.buscar_relaciones(...))
    return None                       # <- inalcanzable
    out["http_status"] = _http_de(out)  # <- inalcanzable, y `out` NO existe
    return out                        # <- inalcanzable
```

No es un fallo funcional: es código muerto tras un `return`. Pero `out` no está
definido en ese ámbito, así que si alguien reordenase esas líneas, el error
sería un `NameError` en tiempo de ejecución, no un fallo silencioso.

**Interpretación.** Es un resto de una edición anterior. No cambia el
comportamiento, pero es exactamente el tipo de cosa que un mutation test no
detecta y que un humano acabaría "limpiando" sin querer, moviendo código por
error.

**Decisión.** D-004 — **NO tocarlo en esta misión.** No está en el alcance
(la misión prohíbe tocar la semántica del adaptador), no causa fallo, y borrarlo
cambiaría el hash de un fichero de producción sin necesidad. Se documenta como
deuda explícita en `02_DECISIONES.md`.


---

## [2026-10-04 — E4. INCIDENTE: el harness dejó un fichero de producción mutado]

**Hipótesis.** El harness de mutación es seguro: restaura en un `finally` y
verifica por hash.

**Comprobación.** Ejecuté el harness con `cmd /c` a través de la capa de
comandos de la shell, que tiene un **límite de 30 s**. El harness tarda ~120 s
(9 mutaciones × 3 suites, cada una carga el dataset).

**Resultado — Y UN FALLO REAL.** La ejecución fue **cancelada a mitad**, con una
mutación aplicada. El `finally` nunca llegó a ejecutarse y
`dfchron/servicio_consulta.py` se quedó mutado en producción:

```
linea 165 antes : base["evidence"] = _evidencia(tipo, df_id, campos) if tipo else None
linea 165 ahora : base["evidence"] = None

hash baseline : 0a5b6b1c3244e6192752f311b89d075e6b75de23d971a4972fdba54f3a73f834
hash hallada  : 689047bb4e5e12b62bb16a58d91b65c26352579bb22a66aa947d051aa8c0110f
```

Se detectó porque el hash dejó de coincidir, **no** porque una prueba fallara.
Y hay un segundo síntoma: al relanzar, la mutación B falló con *"el patrón ya no
existe"*, porque la línea que B busca mutada era, en realidad, la que había
dejado la ejecución anterior.

**Interpretación.** Es un hallazgo de verdad sobre el diseño del harness, no un
accidente que esconder:

> **Un harness de mutación que escribe sobre ficheros de producción NO es
> seguro frente a una interrupción. El `finally` protege de las excepciones, no
> de que alguien mate el proceso.**

La misión (Parte 13) exige que si una herramienta modifica CRLF/LF, BOM o
codificación, se detenga y se restauren los bytes originales. Eso es
exactamente lo que ocurrió, y el mecanismo de detección —comparar hash contra un
baseline conocido— funcionó.

**Restauración.** `API_WEB/restaurar_servicio.py`, escrita para el caso,
verifica que haya **exactamente una** ocurrencia mutada, escribe en binario (sin
tocar CRLF ni añadir BOM) y **aborta si el hash final no coincide**:

```
hash despues : 0a5b6b1c3244e6192752f311b89d075e6b75de23d971a4972fdba54f3a73f834
hash esperado: 0a5b6b1c3244e6192752f311b89d075e6b75de23d971a4972fdba54f3a73f834
RESTAURADO byte a byte. CRLF=459, LF sueltos=0
```

**Decisión.** D-005 — relanzar el harness siempre en segundo plano y NUNCA a
través de un comando con límite de tiempo. Dejar constancia en
`04_MUTACIONES.md` de que este modo de fallo existe y de cómo se detecta.
---

## [2026-10-04 — E7. Cuatro pruebas nuevas fallaron. Todas mías.]

**Hipótesis.** Las pruebas adversariales A–F que acabo de escribir pasan a la
primera.

**Comprobación.** Escritas contra lo que *creía* que era el contrato, sin mirar
la respuesta real antes.

**Resultado. 4 de 16 fallaron:**

| Prueba | Lo que yo esperaba | Lo que hace el sistema |
|---|---|---|
| `la_evidencia_no_anuncia_otro_dataset` | `evidence.state_version` en la raíz | La evidencia real viaja en **`data`** |
| `el_endpoint_de_evidencia_responde` | `evidence` no nulo | `evidence` llega a **`null`** |
| `verificar_fallido_no_es_verificado` | `es_de_tipo&objeto=kobold` falla | Sale `FOUND`: 712 **sí** es kobold |
| `la_navegacion_no_usa_la_frontera` | `/api/listar/figuras` → 200 | **400**: el tipo es `artifacts`, en inglés |

**Interpretación.** Ninguno de los cuatro fallos era del producto: eran
suposiciones mías escritas sin evidencia. Y cada una habría convertido una
prueba verde en una mentira:

- Si «arreglara» el producto para que `evidence` saliera en la raíz, habría
  duplicado el contrato.
- Si dejara `es_de_tipo&objeto=kobold` esperando `NOT_VERIFIED`, la prueba
  pasaría **por la razón equivocada** cuando el resultado cambiara.

Se escribió `API_WEB/_sonda.py` para imprimir la forma real de las respuestas
antes de afirmar nada. Las cuatro se corrigieron contra lo observado, no contra
lo supuesto.

**Decisión.** D-008 — una prueba se escribe **después** de mirar la respuesta
real. Una prueba que se «arregla» hasta dar verde sin mirar el sistema no prueba
el sistema: prueba la suposición del que la escribió.

---

## [2026-10-04 — E8. Hallazgo EVID-006: `evidence` a `null` en su propia ruta]

**Hallazgo colateral de E7.**

`GET /api/consulta/evidencia/figura/712` responde:

```json
{
  "estado": "FOUND",
  "evidence": null,          <-- a null en SU PROPIA ruta
  "data": { "state_version": "v1-04170363943d4ba1",
            "funcion": "nucleo.Archivo.ficha_figura", ... }
}
```

**Causa.** En `servicio_consulta.obtener_evidencia()`:

```python
ev = _evidencia(tipo, df_id, campos or ["nombre"])            # -> OK, con campos
out = _resultado(FOUND, tipo=tipo, df_id=df_id, campos=campos)  # campos == None
```

`_resultado()` vuelve a llamar a `_evidencia(tipo, df_id, campos)` con
`campos=None` en vez de `["nombre"]`. `_evidencia` lo pasa a
`ic.evidencia_de(..., list(None))`, que lanza, y el `except` devuelve `None`.

**Interpretación.** No rompe nada: la evidencia **sí viaja**, en `data`. Pero es
una inconsistencia real: la clave `evidence` de primer nivel es fiable en las
fichas (`/api/figuras/{id}`…) y **a `null` en la ruta que existe precisamente
para devolver evidencia**. Un cliente que la leyera de forma uniforme recibiría
`null` justo donde más la necesita.

**Decisión.** D-009 — **NO corregir.** El arreglo está en `servicio_consulta.py`,
que es un **contrato congelado** por esta misión (regla 3). Se documenta como
deuda con su causa exacta, para que corregirse sea trivial en una misión que sí
tenga permiso.

Las pruebas adversariales leen `data.state_version` en esa ruta, que es donde la
evidencia está de verdad. Ver `05_PRUEBAS.md`.
