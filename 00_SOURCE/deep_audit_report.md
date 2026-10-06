# DF-Chronicles :: Informe de auditoría profunda

**Misión Extra — auditoría y endurecimiento del núcleo.**

Procedimiento respetado: se leyó toda la documentación, se inspeccionó el
código, se ejecutaron las pruebas existentes y se escribió un **informe de
auditoría inicial (`00_SOURCE/audit_inicial.md`) ANTES de modificar nada**.

---

## Resumen ejecutivo

Se auditó el núcleo buscando fallos reales en cinco ejes: contrato de API,
manejo de errores, semántica FACT/DERIVED/UNKNOWN, truncamientos y
determinismo.

**Resultado: 7 defectos demostrados, todos corregidos y con prueba de
regresión.** El más grave no estaba en la lógica sino en el propio fichero:
**dos métodos estaban definidos dos veces**, y la definición muerta del final
anulaba silenciosamente la corrección.

| Métrica | Antes | Después |
|---|---:|---:|
| Pruebas de integración | 20/20 | **20/20** |
| Pruebas del núcleo | 48/48 | **48/48** |
| Pruebas adversariales | *no existían* | **38/38** |
| Crashes con entradas hostiles | **4** | **0** |
| Funciones públicas documentadas | 40/40 | 40/40 |
| Discrepancias de firmas doc↔código | 0 | 0 |
| Referencias rotas | 0 | 0 |
| Escenarios peligrosos bloqueados | 0/4 | **4/4** |

---

## 1. Estado inicial

| Comprobación | Resultado |
|---|---|
| `probar_nucleo.py` | 48/48 OK |
| `probar_integracion.py` | 20/20 OK |
| `test_determinismo.py` | 29 consultas × 4 procesos, idénticas |
| `verificar_reproducibilidad.py` | 9/9 secciones byte-idénticas |
| Solo lectura | Hash del dataset sin cambios tras 150 consultas |
| Git | **No existe** |

Las suites pasaban. Los defectos estaban **fuera de su cobertura**.

---

## 2. Problemas encontrados y corregidos

### D1 — `eventos_del_anio` fallaba con tipo no numérico · CRASH

* **Reproducción:** `eventos_del_anio('5')` → `TypeError: '<=' not supported between instances of 'int' and 'str'`
* **Impacto:** cualquier consumidor con un año como texto reventaba el proceso.
* **Causa:** comparación `ANIO_MIN <= anio <= ANIO_MAX` sin coerción.
* **Corrección:** helper `_anio_seguro()` que devuelve `None` si no es un
  entero válido; la función responde `UNKNOWN` con motivo.
* **Prueba:** `test_anos_con_tipo_erroneo`

### D2 — `eventos_entre_anios` fallaba con tipo no numérico · CRASH

* **Reproducción:** `eventos_entre_anios('a', 5)` → `ValueError`
* **Causa:** `int(anio_a)` sin validación.
* **Corrección:** misma coerción segura.
* **Prueba:** `test_anos_con_tipo_erroneo`

### D3 — Definiciones duplicadas: código muerto que anulaba la corrección · **GRAVE**

* **Reproducción:** tras corregir D1/D2, los crashes **persistían**.
* **Causa:** `nucleo.py` contenía **dos** definiciones de `eventos_del_anio`
  (líneas 224 y 581) y de `eventos_entre_anios` (238 y 591). Python usa la
  **última**, así que la versión corregida nunca se ejecutaba. Restos de una
  edición anterior.
* **Impacto:** invisible a `ast.parse` y a los tests; cualquier corrección
  futura de esos métodos habría parecido no funcionar.
* **Corrección:** eliminado el bloque muerto (líneas 580–600).
* **Prueba:** `test_no_hay_definiciones_duplicadas` recorre el AST y falla si
  cualquier método aparece dos veces.

### D4 — `buscar_evento` inconsistente con las demás búsquedas

* Las cinco búsquedas exponen `total_encontrados`/`devueltos`/`truncado`/
  `limite`. `buscar_evento` no exponía ninguno.
* **Corrección:** propagados los cuatro campos.
* **Prueba:** `test_todas_las_busquedas_comunican_total`

### D5 — Truncamientos no comunicados

| Función | Antes | Después |
|---|---|---|
| `eventos_entre_anios` | `total` sin `truncado` | `total`/`devueltos`/`truncado` |
| `relaciones_de_figura` | ídem | ídem |
| `cronologia_figura` / `_entidad` / `_sitio` | ídem | ídem |
| `eventos_de_figura` / `_sitio` | lista desnuda, sin total | `con_total=True` opcional |

El contrato previo se mantiene: por defecto `eventos_de_figura` sigue
devolviendo una lista. Quien necesite el total lo pide explícitamente.
* **Prueba:** `test_cronologias_comunican_truncado`,
  `test_relaciones_comunican_truncado`,
  `test_envelope_con_total_opcional`

### D6 — `death_year` ausente sin certeza explícita

* **Reproducción:** una figura sin `death_year` devolvía
  `{'año': None, 'segundos72': None}`. **`None` es ambiguo**: podía leerse
  como «murió en fecha desconocida» o «sigue viva». Afecta a **6.734 de
  11.144 figuras (60 %)**.
* **Corrección:** `_fecha_legible()` añade `certainty` y una lista
  `interpretacion_prohibida` que declara explícitamente qué lecturas son
  inválidas.
* **Pruebas:** `test_muerte_ausente_es_unknown_explicito`,
  `test_muerte_no_prohíbe_interpretaciones`,
  `test_el_nucleo_no_dice_que_esta_viva`

### D7 — Colecciones vacías presentadas como FACT

* **Reproducción:** un sitio sin eventos devolvía `eventos: 0` con
  `certainty: FACT`. Eso afirma «ocurrieron cero eventos», que los datos no
  permiten sostener.
* **Corrección:** `certainty_eventos: UNKNOWN` + `nota_eventos` cuando el
  recuento es 0.
* **Prueba:** `test_sitio_sin_eventos_lo_declara`
---

## 3. Problemas NO corregidos (justificados)

### N1 — Salvaguardas de reproducibilidad con lógica invertida

La primera versión de `rutas_seguras()` comprobaba si la ruta protegida
estaba dentro del temporal, cuando debía comprobar lo contrario. La prueba
adversaria lo detectó: **2 de 4 escenarios peligrosos NO se abortaban**.

**Corregido.** Ahora comprueba ambas direcciones (el temporal no puede estar
dentro de las rutas protegidas ni contenerlas). 4/4 escenarios bloqueados.

### N2 — Observaciones sin acción (punto 25)

| Observación | Por qué no se toca |
|---|---|
| `eventos_del_anio(3.7)` devuelve 0 eventos | 3.7 no es un año, pero cae dentro de 1–100. No inventa: simplemente no hay coincidencias. Cambiarlo sería menos preciso. |
| `buscar` con 0 resultados devuelve `FACT` | La búsqueda **sí** se ejecutó. «No hay coincidencias» es un hecho. |
| `test_cronologia_sitio` es trivial | Auditado en Fase 4. Añadir cobertura sin valor real. |
| `solo_documentados` de `conflictos()` no hace nada | Parámetro reservado, sin efecto. Documentado como tal. |
| Sin Git | **Riesgo residual real**, ver sección 10. |

---

## 4. Métricas

### Rendimiento

| Métrica | Antes | Después | Nota |
|---|---:|---:|---|
| Arranque | 2,1 s | 2,9 s | +0,14 s por el índice de año |
| Memoria | ~507 MiB | ~507 MiB | +0,47 MiB (0,09 %) |
| `eventos_del_anio` | 30 ms | **3,8 ms** | ×8 |
| `eventos_entre_anios` | 95 ms | **5,1 ms** | ×19 |
| Ficha de figura | 0,6 ms | 0,6 ms | sin cambio |
| Búsqueda | 3 ms | 3 ms | sin cambio |

### Índice por año (parte 13)

Evaluado **antes** de decidir, con la medición de memoria corregida:

| | Sin índice | Con índice |
|---|---:|---:|
| Coste de construcción | — | +0,136 s |
| Memoria | — | +0,47 MiB |
| `eventos_del_anio` | 32,3 ms | 2,5 ms |

**Decisión: SÍ implementado.** Beneficio ×13 por un coste del 0,09 % de la
memoria. Verificado que los **100 años dan resultados idénticos** al barrido
completo, y que `eventos_entre_anios(y,y)` coincide con `eventos_del_anio(y)`.

*Mi primera decisión fue NO implementarlo, basándome en una medición de
memoria defectuosa (−506 MiB, artefacto de `tracemalloc`). Al corregirla, el
balance cambió. Lo documento porque casi dejó sin aplicar una mejora real.*
---

## 5. Verificaciones que pasaron sin cambios

| Comprobación | Resultado |
|---|---|
| Solo lectura | Hash del dataset idéntico tras 150 consultas |
| `coords_primeras('-1,-1')` | `[]` — el centinela nunca se vuelve coordenada |
| `coords_primeras('-1,5')` | `[]` |
| `site_id` válidos inexistentes | 0 |
| Lenguaje causal en el código | 0 apariciones de 11 términos |
| Grafo de relaciones | Dirigido: 11.975 pares, 1.774 con inverso (14,8 %) |
| `death_year > 100` | 0 figuras |
| Relaciones con ambos extremos | 13.192 / 13.192 |
| Relaciones con `evento_existe` | 0 |
| Exportación JSON sin truncar | 158 de 158 eventos |

---

## 6. Integridad

```
legends.xml        49,223,702 bytes  77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f  INTACTO
legends_plus.xml   17,664,819 bytes  fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d  INTACTO
```

El manifiesto `dataset_manifest.json` coincide con los ficheros. El hash se
comprueba en `probar_integracion.py` y en `probar_adversarial.py`. **No existe
ningún mecanismo de actualización automática de hashes**: cambiarlos es una
operación manual y consciente.

---

## 7. Estado semántico

| Nivel | Uso verificado |
|---|---|
| `FACT` | Solo valores presentes en el XML o respaldados por un campo del XML. |
| `DERIVED` | Índices, ordenaciones, agrupaciones de conflicto, `total`/`devueltos`/`truncado`, construcciones por coordenada. |
| `UNKNOWN` | ID inexistente, año inválido o fuera de rango, `death_year` ausente, colecciones vacías, eventos sin participantes. |

**No existe ninguna conversión `UNKNOWN → FACT` ni `DERIVED → FACT`.**

Transformaciones prohibidas, implementadas y probadas:

| Transformación | Estado |
|---|---|
| `UNKNOWN → estimación` | No existe. `_fecha_legible` marca UNKNOWN y declara qué NO concluir. |
| `UNKNOWN → valor por defecto` | No existe. |
| `-1 → coordenada válida` | No existe. `coords_primeras` filtra negativos. |
| `ausencia de muerte → sigue viva` | No existe, y ahora está prohibido en el propio dato. |
| `0 eventos → no pudieron ocurrir` | Corregido en D7. |
| `relación → evento` | No existe. `evento_existe` es siempre `False`. |
| `conflicto → guerra` | No existe. `certainty: DERIVED` + aviso. |
| grafo dirigido → no dirigido | No existe. Ahora además se declara en la respuesta. |

---

## 8. Estado de API

**40 funciones públicas, 40 documentadas, 0 discrepancias de firmas.**

Verificado automáticamente cruzando `query_reference.md` contra el código real
mediante `inspect`. Falsos positivos corregidos: las tablas de *ejemplos de
uso* se confundían con declaraciones de firma.

---

## 9. Estado de reproducibilidad

`verificar_reproducibilidad.py` ahora es **seguro por construcción**:

1. Resuelve rutas absolutas.
2. **ABORTA** si el temporal está dentro de `processed/` o `original_data/`.
3. **ABORTA** si el temporal contiene una ruta protegida.
4. Crea un temporal aislado del sistema.
5. Copia solo las fuentes necesarias.
6. Reapunta las constantes del módulo importándolo, sin editar ficheros.
7. Compara 9 secciones byte a byte.
8. Elimina el temporal.

**Prueba de las salvaguardas: 4/4 escenarios peligrosos bloqueados**,
incluidos intentar reconstruir directamente sobre `processed/` y sobre
`original_data/`. Resultado: **9/9 secciones byte-idénticas**.

---

## 10. Riesgos residuales

| Riesgo | Gravedad | Nota |
|---|---|---|
| **Sin Git** | Media | Los originales están protegidos por hash, pero no hay historial. Una edición accidental sería detectable, no reversible. |
| Memoria ~507 MiB | Baja | Funciona. Si se cargan varios mundos, optimizar antes que migrar. |
| Arranque 2,9 s | Baja | Irrelevante en CLI. Cachear `Archivo()` si es un servicio. |
| `hash randomization` | Ninguna | Verificado con 4 semillas distintas. |
| Datos ausentes | **Estructural** | 17.881 eventos sin participantes, 6.734 figuras sin muerte, 9.930 coordenadas centinela. No es un defecto del código. |

---

## 11. Estado de IA

**Implementado:** contrato, formato de evidencia, límites documentados,
verificaciones de integridad y salvaguardas de reproducibilidad.

**NO implementado (por diseño):** LLM, RAG, embeddings, base de datos, web,
mod de Dwarf Fortress. Ninguna tentativa.

El núcleo queda preparado para que una futura IA reciba **solo** lo que la
capa de contexto decida entregar, con `certainty` explícita y las
limitaciones como contexto de sistema obligatorio.
