# API/WEB — MATRIZ DE PRUEBAS

> Todas las suites se ejecutaron **en solitario**, nunca en paralelo con el
> harness de mutación: el harness muta ficheros de producción y correr a la vez
> produce falsos negativos. Ver E4 en `00_DIARIO.md`.

---

## Regresión completa — 15 suites, 606 pruebas, cero fallos

```
python API_WEB\_banco.py
```

| Suite | Pruebas | Estado |
|---|---:|---|
| `00_SOURCE/tools/probar_nucleo.py` | 48 | OK |
| `00_SOURCE/tools/probar_adversarial.py` | 39 | OK |
| `dfchron/pruebas/probar_api.py` | 54 | OK |
| `dfchron/pruebas/probar_web.py` | 65 | OK |
| `dfchron/pruebas/probar_integracion_consulta.py` | 55 | OK |
| `dfchron/pruebas/probar_servicio_consulta.py` | 66 | OK |
| `dfchron/pruebas/probar_perimetro_ia.py` | 50 | OK |
| `dfchron/pruebas/probar_identidad_mundo_consumo.py` | 35 | OK |
| `dfchron/pruebas/probar_verificacion_estructurada.py` | 18 | OK |
| `dfchron/pruebas/probar_frontera_inferencia.py` | 12 | OK |
| `dfchron/pruebas/probar_frontera_linguistica.py` | 25 | OK |
| `dfchron/pruebas/probar_geografia.py` | 41 | OK |
| `dfchron/pruebas/probar_identidad_mundo.py` | 30 | OK |
| `dfchron/pruebas/p1_3/probar_p1_3.py` | 50 | OK |
| **`API_WEB/probar_frontera_adversarial.py`** | **18** | **OK** |

**TOTAL: 606. En falla: ninguna.**

> `probar_p1_3.py` imprime su resultado con otro formato (`RESULTADO: 50/50`),
> por eso el resumen automático del banco muestra `?` en esa fila. Ejecutada por
> separado: 50/50.

---

## Pruebas nuevas de esta misión

| Suite | Pruebas | Qué aporta |
|---|---:|---|
| `API_WEB/probar_frontera_adversarial.py` | **18** | Los 6 casos adversariales A–F, con nombre propio |
| `dfchron/pruebas/probar_mutation_frontera.py` | 4 (era 3) | Mutaciones 5 → 9; suite adversarial añadida a las detectores |
| `API_WEB/auditar_frontera.py` | *(herramienta)* | Clasificación de las 51 rutas, derivada del código |

**Antes: 588 pruebas · Después: 606.** +18 nuevas, 0 eliminadas, 0 relajadas.

---

## Matriz: caso adversarial → prueba

| Caso | Prueba | Qué demuestra |
|---|---|---|
| **A** · dataset equivocado | `test_el_dataset_id_anunciado_es_el_real` | El `dataset_id` coincide con el leído del disco |
| **A** | `test_la_evidencia_no_anuncia_otro_dataset` | `state_version` de la evidencia es el real |
| **A** | `test_fabricar_un_dataset_id_no_pasa_desapercibido` | El sobre y la evidencia **deben coincidir**; si uno se falsea, se nota |
| **B** · evidencia eliminada | `test_todas_las_fichas_traen_evidencia` | Las 5 fichas llevan evidencia **con** `state_version` |
| **B** | `test_el_endpoint_de_evidencia_responde` | El endpoint de evidencia responde con versión y función |
| **C** · estado alterado | `test_no_existente_es_404_y_NOT_FOUND` | Ausencia total → 404 + `NOT_FOUND` |
| **C** | `test_una_relacion_inexistente_no_es_FOUND` | Una relación inexistente no se presenta como verdad |
| **C** | `test_atributo_no_declarado_no_es_found` | **Ancla la mutación C**: entidad existe, dataset no declara → `NOT_VERIFIED` |
| **C** | `test_entidad_inexistente_es_404_no_not_verified` | Aquí sí es ausencia: 404 |
| **C** | `test_verificar_fallido_no_es_verificado` | Afirmación falsa → `NOT_VERIFIED`, ni 404 ni 503 |
| **C** | `test_tipo_sin_identidad_no_inventa_identidad` | `relacion` no tiene identidad: `identity` es `null` |
| **D** · bypass | `test_el_flujo_real_pasa_por_el_servicio` | 10 rutas ejecutan su operación de `servicio_consulta` |
| **D** | `test_la_navegacion_no_usa_la_frontera_por_accidente` | 6 rutas de navegación **no** la usan |
| **D** | `test_el_adaptador_no_puede_saltarse_al_nucleo` | El adaptador no pide el archivo del núcleo |
| **E** · respuesta fabricada | `test_el_envelope_coincide_con_el_servicio` | API y servicio devuelven el **mismo** valor, no uno parecido |
| **F** · mundo incorrecto | `test_el_mundo_llega_por_la_api_y_no_se_inventa` | Si el mundo falta, declara **por qué** |
| **F** | `test_el_mundo_no_es_el_dataset_id` | Mundo ≠ contenido (P1) |
| **F** | `test_el_sobre_de_consulta_no_inventa_mundo` | El sobre de consulta no fabrica identidad de mundo |

---

## Matriz: compatibilidad

| Prueba | Garantiza |
|---|---|
| `test_el_envelope_coincide_con_el_servicio` | La API no degrada `estado`, `dataset_id`, `certainty` ni `status` |
| `test_atributo_no_declarado_no_es_found` | `NOT_VERIFIED ≠ NOT_FOUND`, y `NOT_VERIFIED` **no** es 503 |
| `test_verificar_fallido_no_es_verificado` | `NOT_VERIFIED` no colapsa a 404 |
| `probar_identidad_mundo_consumo.py::test_el_sobre_de_consulta_no_cambio` | Las claves del sobre no cambiaron al añadir la frontera |
| `probar_identidad_mundo_consumo.py::test_salud_sigue_teniendo_sus_claves_originales` | `/api/salud` conserva su envelope |

---

## Mutation testing

```
python dfchron\pruebas\probar_mutation_frontera.py
→ Ran 4 tests in 172.428s — OK
```

| Introducidas | Detectadas | Supervivientes |
|---:|---:|---:|
| **9** | **9** | **0** |

Detalle en `04_MUTACIONES.md`.

---

## Qué NO se pudo probar

| Prueba | Por qué | Cómo cubrirla |
|---|---|---|
| Comportamiento de la **build de Astro** (`site/`) en producción | Las reglas del proyecto no permiten regenerar artefactos publicados en esta misión | Se verificó el **código fuente**; la build queda pendiente de una misión de publicación |
| `Web → API` en un navegador real | No hay navegador ni build servida en este entorno | El código fuente de la Web está auditado y sus 65 pruebas pasan; el salto HTTP está cubierto por `probar_web.py` |

Ambas quedan declaradas, no ocultas.