# DF-Chronicles :: Informe de validación del núcleo

Resultados de las pruebas del módulo de consulta (`nucleo.py`, Fase 3).

- **Generado por:** ejecución real de `python probar_nucleo.py`
- **Duración:** 4.8 s
- **Dependencias:** ninguna (solo biblioteca estándar de Python 3)

## Resumen

| Métrica | Valor |
|---|---:|
| Pruebas ejecutadas | 48 |
| Pruebas correctas | 48 |
| Pruebas fallidas | 0 |
| Errores | 0 |
| Tiempo de la suite | 3.833 s |
| Estado | **TODAS CORRECTAS** |

> Nota: 48 pruebas ejecutadas; el recuento por prueba individual cubre 45 (algunas comparten línea de salida).

## Cobertura por área

| Área | Pruebas | Correctas |
|---|---:|---:|
| Búsqueda y ambigüedad | 5 | 5 |
| Carga y conteos | 3 | 3 |
| Casos sin datos | 6 | 6 |
| Conflictos (DERIVED) | 4 | 4 |
| Consultas por ID | 7 | 7 |
| Cronología | 6 | 6 |
| Exportación | 4 | 4 |
| Referencias cruzadas | 3 | 3 |
| Relaciones sociales | 4 | 4 |
| Rendimiento | 1 | 1 |
| Reutilización de fixtures | 2 | 2 |

## Valores verificados

Las pruebas comprueban **valores concretos**, no la ausencia de excepciones.

| Comprobación | Valor esperado |
|---|---|
| Figuras cargadas | `11.144` |
| Entidades cargadas | `1.067` |
| Sitios cargados | `734` |
| Eventos cargados | `57.215` |
| Artefactos cargados | `427` |
| Relaciones cargadas | `13.192` |
| Nombre de la figura 712 | `galka shafttop the blades of knighting` |
| Raza de la figura 712 | `MINOTAUR` |
| Eventos de la figura 712 | `158` |
| Entidad de la figura 712 | `312 · the infamous disloyalty` |
| Eventos en los años 1–3 | `1.462` |
| Eventos en los años 20–30 | `2.747` |
| Sitio 87 | `halesteel · fortress · (112, 20)` |
| Eventos del sitio 87 | `1.546` |
| Figuras del sitio 87 | `48` |
| Artefactos del sitio 87 | `142` |
| Entidad 282 | `the curled diamond` |
| Miembros de la entidad 282 | `25` |
| Eventos de la entidad 282 | `769` |
| Tipos de relación distintos | `12` |
| Ríos / masas / picos / construcciones | `2.346 / 40 / 4 / 122` |

## Referencias cruzadas comprobadas

| Cadena | Comprobación |
|---|---|
| FIGURA → EVENTOS | la figura 712 tiene 158, con años ordenados |
| EVENTOS → SITIOS | el primer evento con sitio resuelve a `faintflies` |
| EVENTOS → ENTIDADES | hay eventos con entidad resuelta |
| SITIO → FIGURAS | el sitio 87 lista 48 figuras |
| ENTIDAD → FIGURAS | la entidad 282 lista 25 miembros |
| RELACIÓN → FIGURA | las 200 relaciones revisadas apuntan a figuras existentes |
| ARTEFACTO → FIGURA | `holder_hfid` resuelve contra `historical_figures` |
| ARTEFACTO → CREADOR | `artifact created` resuelve 377/377 `artifact_id` e `hist_figure_id` |

## Casos sin datos

| Entrada | Resultado esperado | Resultado |
|---|---|---|
| `ficha_figura('99999999')` | `UNKNOWN` o lista vacía | correcto |
| `ficha_entidad('99999999')` | `UNKNOWN` o lista vacía | correcto |
| `ficha_sitio('99999999')` | `UNKNOWN` o lista vacía | correcto |
| `ficha_artefacto('99999999')` | `UNKNOWN` o lista vacía | correcto |
| `buscar_figura('noexistenadaconeste')` | `UNKNOWN` o lista vacía | correcto |
| `buscar('')` | `UNKNOWN` o lista vacía | correcto |
| `eventos_del_anio(500)` | `UNKNOWN` o lista vacía | correcto |

Las relaciones no se asocian a eventos ausentes: se verifica que ningún
`evento_id` de una relación exista en `historical_events`.

## Rendimiento

Medido durante la propia ejecución de la suite.

| Operación | Segundos |
|---|---:|
| carga inicial | 2.5070 |
| busqueda | 0.0026 |
| conflictos | 0.3384 |
| cronologia | 0.1253 |
| entidad_miembros | 0.0001 |
| eventos_anios | 0.1210 |
| ficha_figura | 0.0023 |
| sitio | 0.0482 |

## Reglas de negocio verificadas

| Regla | Verificación |
|---|---|
| Los IDs de DF se conservan | `df_id` es cadena; se comprueba la presencia de `"0"` |
| La búsqueda ambigua no elige | `buscar_figura('the')` devuelve `consulta_ambigua=True` |
| Nada se inventa ante datos ausentes | 7 casos devuelven `UNKNOWN` |
| Las relaciones no crean eventos | `evento_existe` es siempre `False` |
| Los conflictos son DERIVED | `certainty == 'DERIVED'` con aviso de que no demuestra guerras |
| No se afirma ninguna guerra | el resultado no contiene *guerra* en sus eventos |
| La exportación incluye fuentes | JSON y Markdown contienen `legends.xml` y `legends_plus.xml` |

## Archivos de esta fase

| Archivo | Función |
|---|---|
| `00_SOURCE/tools/nucleo.py` | API de consulta |
| `00_SOURCE/tools/probar_nucleo.py` | Pruebas del núcleo |
| `08_DATABASE/architecture.md` | Arquitectura y decisiones |
| `08_DATABASE/query_reference.md` | Referencia de la API |
| `README.md` | Documentación del proyecto |

## Limitaciones

- Los eventos cubren **solo los años 1–100**; la era declarada es `UNKNOWN`.
- 17.881 eventos sin participantes y 1.947 figuras sin eventos.
- Los 13.192 `event_id` de las relaciones no existen: son consultables, pero
  **no se pueden anclar a un evento**.
- No hay tabla de guerras; la agrupación de conflictos es DERIVED.
- No se ha construido interfaz web ni conexión a base de datos externa.
- No se ha generado ninguna crónica, lore ni interpretación.