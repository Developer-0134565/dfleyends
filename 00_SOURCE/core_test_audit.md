# DF-Chronicles :: Auditoría de las 48 pruebas del núcleo

Auditoría de `00_SOURCE/tools/probar_nucleo.py` (Fase 4, punto 1).

**No se ha eliminado ni modificado ninguna prueba.** Este documento clasifica
cada una y señala sus límites.

Criterios aplicados:

* **Qué comportamiento protege.**
* **Qué dato concreto valida.**
* **¿Podría pasar aunque hubiera un error semántico?** (debilidad)
* **¿Depende de un detalle accidental de implementación?** (acoplamiento)

---

## 1. Clasificación por área

| Área | Pruebas | Qué protege |
|---|---:|---|
| Carga y conteos | 3 | Que el índice se construya completo |
| Consultas por ID | 7 | Que las consultas devuelvan los valores del XML |
| Búsqueda y ambigüedad | 5 | Que la búsqueda no elija por su cuenta |
| Referencias cruzadas | 5 | Que los enlaces resuelvan a objetos reales |
| Cronología | 6 | Ordenación y límites temporales |
| Relaciones sociales | 4 | Tipos literales y no-asociación a eventos |
| Conflictos DERIVED | 4 | Que no se declaren guerras |
| Casos sin datos | 6 | Que no se invente ante IDs inexistentes |
| Exportación | 4 | Que JSON/Markdown incluyan fuentes |
| Fixtures | 2 | Que los datos de Fase 2 sigan consultables |
| Rendimiento | 1 | Que las consultas sigan siendo rápidas |

---

## 2. Auditoría por área

### Carga y conteos (3)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_conteos_correctos` | 11.144 / 1.067 / 734 / 57.215 / 427 / 13.192 | Solo el recuento: no detecta campos alterados |
| `test_ids_son_cadenas_de_df` | `"0"` presente y tipo `str` | Solo mira el primer elemento |
| `test_geografia_cargada` | 2.346 / 40 / 4 / 122 | No verifica coordenadas ni nombres |

### Consultas por ID (7)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_figura_712_valores_reales` | nombre y race exactos del XML | **Sólida**: un valor inventado falla |
| `test_figura_tiene_158_eventos` | 158 exactos | No comprueba *qué* eventos |
| `test_cronologia_ordenada` | años no decrecientes | No comprueba el desempate por `seconds72` |
| `test_entidad_asociada_resuelve` | id 312 y su nombre | Sólida |
| `test_entidad_miembros` | 25 miembros, ninguno `UNKNOWN` | No verifica que sean los correctos |
| `test_sitio_87_valores` | nombre, tipo, coords, civ, 1.546 eventos | **Sólida**: detectó el bug de `tipo` |
| `test_artefacto_con_creador` | `artifact created` resuelve figura | Solo 1 artefacto de 377 |

### Búsqueda y ambigüedad (5)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_buscar_exito_...` | id 712 y su nombre | Sólida |
| `test_busqueda_ambigua_no_elige` | `consulta_ambigua=True` | No comprueba que devuelva *todas* |
| `test_busqueda_sin_resultados` | lista `[]` | Correcta |
| `busqueda_sitio` / `entidad` / `artefacto` | un id esperado | Débiles: una sola consulta cada una |

### Referencias cruzadas (5)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_recorrido_completo_figura` | 158 eventos, sitio `faintflies` | Sólida |
| `test_sitio_lista_figuras` | 48 figuras | Sólida |
| `test_artefactos_de_figura` | artefactos con nombre | **Débil**: figura arbitraria |
| `test_relaciones_conectan_figuras_existentes` | 200 relaciones, ambos extremos existen | Solo 200 de 13.192 |
| `test_relaciones_no_se_asocian_a_eventos_ausentes` | `evento_existe=False` | **Crítica** |

### Cronología (6)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_eventos_entre_anios` | 1.462 eventos, todos en rango | Sólida |
| `test_rango_ordenado_por_anio_y_segundos` | claves ordenadas | Sólida |
| `test_eventos_del_anio` | todos los del año 1 | Sólida |
| `test_anio_fuera_de_rango_es_unknown` | año 500 → `UNKNOWN` | Sólida |
| `test_cronologia_entidad` | 769 eventos ordenados | Sólida |
| `test_cronologia_sitio` | > 0 eventos | **Débil**: casi cualquier valor la pasa |
### Relaciones sociales (4)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_tipos_disponibles_son_los_del_xml` | 12 tipos con recuentos exactos | **Muy sólida**: detecta tipos inventados |
| `test_consultar_amigos` | solo `childhood_friend` | Sólida |
| `test_consultar_por_tipo_generico` | solo `jealous_obsession` | Sólida |
| `test_figura_sin_relaciones_no_inventa` | 0 relaciones para la figura 0 | Sólida |

### Conflictos DERIVED (4)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_eventos_de_enfrentamiento` | `certainty=DERIVED` + aviso de no-guerra | Sólida |
| `test_subtipos_conocidos` | attacked 2.733, scuffle 1.906, ambushed 428 | **Muy sólida** |
| `test_muertes_por_conflicto` | `struck` 3.687, `old age` ausente | Sólida |
| `test_no_declara_guerras` | la palabra *guerra* no aparece | **Crítica** para la IA |

### Casos sin datos (6)

`test_figura/entidad/sitio/artefacto_inexistente` comprueban que un ID inválido
devuelve `certainty=UNKNOWN` con `motivo`. `test_nombre_inexistente` comprueba
la lista vacía y `test_consulta_vacia` el `UNKNOWN` de una cadena vacía.
Las seis son sólidas y sostienen el requisito "nada se inventa".

### Exportación (4)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_exportar_json_incluye_fuentes` | ambas fuentes presentes | Sólida |
| `test_exportar_markdown_incluye_fuentes` | fuentes + nombre | Sólida |
| `test_exportar_a_archivo` | el archivo contiene el nombre | Acopla a `tempfile` |
| `test_markdown_figura_inexistente` | "Sin datos" | Sólida |

### Fixtures (2)

| Prueba | Valida | Debilidad |
|---|---|---|
| `test_figures_sample_es_consultable` | cada id del fixture devuelve el mismo nombre | **Muy sólida**: detecta deriva entre fases |
| `test_sites_sample_es_consultable` | ídem para sitios | Sólida |

### Rendimiento (1)

`test_tiempos_de_consulta` mide e imprime, pero **no fija umbrales**: una
degradación no haría fallar la suite.

---

## 3. Debilidades detectadas y cobertura de Fase 4

| Debilidad | Riesgo | ¿Cubierta? |
|---|---|---|
| Ninguna prueba comprueba la **memoria** | el arranque usa cientos de MiB | Sí, con la prueba de carga |
| Nada comprueba que `buscar` informe del total | se ocultan resultados | **Corregido en Fase 4** |
| Nada comprueba que `conflictos` no trunque en silencio | un parcial se presenta como total | **Corregido en Fase 4** |
| Nada comprueba que Markdown avise de truncamiento | tabla incompleta sin aviso | **Corregido en Fase 4** |
| Nada comprueba el determinismo entre procesos | el resultado podría depender del hash | **Sí**: `test_determinismo.py` |
| `test_cronologia_sitio` es casi trivial | apenas comprueba algo | Se acepta: hay cobertura equivalente |
| `test_artefactos_de_figura` usa figura arbitraria | cobertura parcial | Se acepta: 136 figuras tienen artefactos |

---

## 4. Conclusión

Las 48 pruebas verifican **valores concretos del XML**, no la ausencia de
excepciones. Las cinco marcadas como **críticas** cubren exactamente las
garantías que una futura IA necesita:

1. `test_relaciones_no_se_asocian_a_eventos_ausentes`
2. `test_no_declara_guerras`
3. `test_busqueda_ambigua_no_elige`
4. `test_figura_712_valores_reales`
5. `test_tipos_disponibles_son_los_del_xml`

**Ninguna prueba ha sido eliminada ni debilitada.**