# DF-Chronicles :: Informe de auditoría inicial (pre-corrección)

**Fase Extra — punto 6 de la regla principal.** Este informe se escribe
**antes de modificar una sola línea**, según el procedimiento exigido.

Fecha: auditoría ejecutada sobre el estado heredado de la Fase 4.

---

## 1. Estado inicial verificado

| Suite | Resultado |
|---|---|
| `probar_nucleo.py` | **48 / 48 OK** |
| `probar_integracion.py` | **20 / 20 OK** |
| `test_determinismo.py` | 29 consultas, 4 procesos, idénticas |
| Hash del dataset tras 150 consultas | **sin cambios** |
| Git | No existe (proyecto sin control de versiones) |

Las suites pasan. La auditoría busca defectos **que las pruebas no cubren**.

---

## 2. Sondas ejecutadas

| Sonda | Resultado |
|---|---|
| Tipos incorrectos en IDs (`None`, `int`, `float`, `list`, `str`) | 8/8 tolerados |
| Años inválidos (`str`, `None`, `float`, invertido, fuera de rango) | **4 CRASHES** |
| Truncamientos silenciosos | **5 funciones** |
| Inconsistencias entre búsquedas | **1 función** |
| Semántica de `death_year` | **1 ambigüedad** |
| Solo lectura | Correcto |
| Centinela `-1` | Correcto |
| Lenguaje causal en el código | 0 apariciones |
| Grafo de relaciones | Dirigido, correcto |
| `death_year > 100` | 0 casos |

---

## 3. Defectos demostrados (a corregir)

### D1 — `eventos_del_anio` falla con tipo no numérico · **CRASH**
```
eventos_del_anio('5')   → TypeError: '<=' not supported between 'int' and 'str'
eventos_del_anio(None)  → TypeError: '<=' not supported between 'int' and 'NoneType'
```
Causa: comparación directa `ANIO_MIN <= anio <= ANIO_MAX` sin coerción.

### D2 — `eventos_entre_anios` falla con tipo no numérico · **CRASH**
```
eventos_entre_anios('a', 5)  → ValueError: invalid literal for int()
eventos_entre_anios(None, 5) → TypeError: int() argument must be ...
```
Causa: `int(anio_a)` sin validación previa.

### D3 — `buscar_evento` inconsistente con el resto de búsquedas
`buscar_figura`/`entidad`/`sitio`/`artefacto` exponen `total_encontrados`,
`devueltos`, `truncado` y `limite`. `buscar_evento` **no expone ninguno**,
aunque comparte la implementación con `buscar`.

### D4 — Truncamiento no comunicado en 5 funciones
| Función | Comunica `total` | Comunica `truncado` |
|---|---|---|
| `eventos_entre_anios` | sí | **no** |
| `relaciones_de_figura` | sí | **no** |
| `cronologia_figura` | sí | **no** |
| `cronologia_entidad` | sí | **no** |
| `cronologia_sitio` | sí | **no** |
| `eventos_de_figura` | **no** (lista desnuda) | **no** |
| `eventos_de_sitio` | **no** (lista desnuda) | **no** |

### D5 — `muerte` sin tipo de certeza
Una figura sin `death_year` devuelve:
```python
'muerte': {'año': None, 'segundos72': None}
```
`None` es **ambiguo**: puede leerse como «murió en un año que no consta» o
como «sigue viva». El núcleo no afirma lo segundo, pero tampoco lo impide:
el campo no lleva `certainty`. **6.734 figuras** (60 %) están en esta
situación.

### D6 — Colecciones vacías presentadas como FACT
Un sitio sin eventos devuelve `eventos: 0` con `certainty: FACT`. El dato
correcto es «**no constan eventos**», no «ocurrieron 0 eventos». Esto es el
error de ausencia-vs-negación described en el punto 19 de la misión.

---

## 4. Observado, NO accionable

Según el punto 25 de la misión, se registra sin modificar.

| Observación | Por qué no se toca |
|---|---|
| `eventos_del_anio(3.7)` devuelve 0 eventos con FACT | Un float no es un año válido, pero `3.7` cae dentro de 1–100. Se documentará, no se cambiará: el núcleo no inventa, simplemente no encuentra coincidencias. |
| `buscar` con 0 resultados devuelve `certainty: FACT` | La búsqueda **sí** se realizó: es un hecho que no hay coincidencias. Cambiarlo sería menos preciso. |
| `test_cronologia_sitio` es trivial | Detectado en la auditoría de Fase 4. Añadir cobertura sin valor real. |
| Memoria ~507 MiB | Optimizable, pero no afecta semántica, contrato ni reproducibilidad. Punto 25: no tocar. |
| `solo_documentados` de `conflictos()` no hace nada | Parámetro preparado, sin efecto. Se documenta como tal. |
| `nombre_de` público | Útil para consumidores externos. Se mantiene. |
| Sin Git | Punto 24: sin control de versiones no hay nada que auditar en Git. **Riesgo residual a señalar.** |

---

## 5. Verificaciones que PASARON (sin defecto)

| Comprobación | Resultado |
|---|---|
| Solo lectura | Hash del dataset idéntico tras 150 consultas |
| `coords_primeras('-1,-1')` | `[]` — el centinela no se convierte en coordenada |
| `coords_primeras('-1,5')` | `[]` — correcto |
| `site_id` válidos que no existen | 0 |
| Lenguaje causal en `nucleo.py` | 0 apariciones de 11 términos buscados |
| Grafo de relaciones | Dirigido; sin función que lo convierta en no dirigido |
| `death_year > 100` | 0 figuras |
| Relaciones: ambos extremos existen | 13.192 / 13.192 |
| Relaciones: `evento_existe` | 0 |

---

## 6. Plan de corrección

Corregir **solo** D1–D6, con prueba de regresión para cada uno:

1. Coerción segura de años → `UNKNOWN` en vez de excepción.
2. Propagar `total_encontrados`/`truncado` a `buscar_evento`.
3. Añadir `truncado` a las 5 funciones que ya informan `total`.
4. Añadir envelope `{items, total, devueltos, truncado}` a las 2 que devuelven
   lista desnuda, **sin romper** el contrato documentado.
5. `certainty` explícita en `muerte` y `nacimiento`.
6. Marcar como `UNKNOWN` las colecciones vacías que no significan «cero».

**Nada más se toca.**