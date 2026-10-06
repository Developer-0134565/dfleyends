# INFORME DEL PERÍMETRO IA

**Misión:** especificar y blindar qué podrá ver y hacer un futuro consumidor
inteligente, **sin implementar ningún componente de IA**.

**Resultado: COMPLETADA Y DEMOSTRADA. Cero IA en el sistema.**

| Métrica | Valor |
|---------|-------|
| Documento de contrato | `AI_CONSUMER_BOUNDARY.md` |
| Pruebas del perímetro | **50**, todas en verde |
| Mutation testing | **11/11 detectadas** |
| Fugas adversariales | **12**, todas rechazadas |
| Operaciones permitidas | **6** (todas las del servicio, ninguna más) |
| Cambios en `servicio_consulta.py` | **0** (hash idéntico) |
| Dependencias de IA instaladas | **0** |

---

## A. Estado inicial

La fase H había cerrado `servicio_consulta` como **puerta de consulta**, pero no
existía ninguna definición de **qué puede pedir un consumidor inteligente** por
esa puerta, ni pruebas que lo demostraran.

**La auditoría encontró algo que la misión no mencionaba:** ya existe
`08_DATABASE/AI_PRE_LLM_CONTRACT.md`, **CONGELADO**, con 12 secciones y un gate
de **15 invariantes** (`probar_gate_pre_ia.py`).

---

## B. Auditoría

### B.1 El contrato congelado ya existía

Ruta real: `08_DATABASE/AI_PRE_LLM_CONTRACT.md`. La misión lo nombraba sin ruta
y en la raíz; **no está ahí**. Está en `08_DATABASE/`, junto a otros cinco
documentos normativos (`ai_data_contract.md` — 64 KB—, `AI_PROJECT_CONTEXT.md`,
`query_reference.md`, `relationship_semantics.md`, `data_limitations.md`).

### B.2 Cubre un eje distinto

| Eje | Documento | Pregunta |
|-----|-----------|----------|
| **Autoridad** | `AI_PRE_LLM_CONTRACT.md` (CONGELADO) | ¿Qué puede **afirmar o cambiar** el modelo? |
| **Acceso** | **`AI_CONSUMER_BOUNDARY.md`** (nuevo) | ¿Qué puede **pedir y recibir**? |

Comprobado, no supuesto: **`servicio_consulta` no aparece en ninguna de las 15
pruebas del gate.** El contrato congelado gobierna lo que el modelo hace *con* la
información; no mira qué entra por la frontera.

**No se modificó el documento congelado**, ni sus 15 invariantes, ni su gate.

### B.3 Estado vivo

Auditado. **No existe**: tick, turno, reloj monotónico, ni estado en memoria de
DF. `dataset_id` existe, pero identifica **contenido**, no tiempo.

---

## C. OPERACIONES PERMITIDAS

Seis, derivadas en tiempo de ejecución de `servicio_consulta.contrato()`:

| # | Operación | Firma real |
|---|-----------|-----------|
| 1 | `obtener_entidad` | `(tipo, df_id)` |
| 2 | `obtener_atributo` | `(tipo, df_id, atributo)` |
| 3 | `buscar_relaciones` | `(origen, tipo_relacion=None, limite=None)` |
| 4 | `contar` | `(tipo, filtro=None)` |
| 5 | `verificar` | `(sujeto_tipo, sujeto_id, predicado, objeto=None)` |
| 6 | `obtener_evidencia` | `(tipo, df_id, campos=None)` |

Las firmas están **medidas con `inspect.signature`**, no escritas de memoria.

**La lista blanca se deriva, no se escribe.** Una lista escrita a mano se
quedaría vieja y sería una segunda fuente de verdad — lo que D17 y D18 prohíben.

**Ninguna operación nueva.** `servicio_consulta.py` no se ha tocado.

---

## D. OPERACIONES PROHIBIDAS

Doce fugas, todas `OPERACION_NO_PERMITIDA`:

«léeme el JSONL original» · «abre world.sav» · «dame todos los campos internos»
· «dame el record_id aunque no tenga identidad» · «inventa el ID» ·
«averigua qué ocurrió después» · «determina el año actual» ·
«consulta información fuera del dataset» · «dame los índices internos» ·
«escribe en el dataset» · «lee el XML crudo» · «salta el servicio y lee el índice»

Más: `__import__`, `eval`, `exec`, `obtener_entidad.__globals__`, y las
privadas `_evidencia`, `_identidad`, `_resultado`.

---

## E. DATOS DISPONIBLES

---

## F. DATOS NO DISPONIBLES

Historial completo · reloj de juego · estado vivo · identidad de relaciones ·
la era (`start_year = -1`) · `df_id` real de los ríos (es DERIVED).

No están prohibidos: **no hay operación que los devuelva**.

---

## G. IDENTIDAD

`identity` llega, o llega `null`. **`null` no es una invitación a rellenarlo.**

Comprobado sobre los tres tipos sin identidad (`relacion`, `era`, `suplemento`).
Ningún `record_id`, `hash` ni `posicion` aparece.

---

## H. EVIDENCIA

`dataset_id` y `state_version` llegan intactos. La procedencia **no se puede
inyectar**: `obtener_evidencia` no tiene parámetro `fuente`, ni la tiene
`_evidencia`. Comprobado con `inspect.signature`.

---

## I. TEMPORALIDAD

`dataset_id` no es reloj, tick, turno ni fecha. Dos pruebas lo fijan, y una
tercera cubre `adaptador_consulta.py`.

> **Una trampa real que la auditoría destapó.** Buscar `tick` en el JSON
> completo devuelve `True`: existe una entidad llamada *«the tick of night»*.
> Y `reloj` también: el propio contrato dice *«dataset_id NO es un reloj»*.
> Buscar texto habría dado dos falsos positivos. **Se comprueban claves**, no
> subcadenas.

---

## J. ESTADO VIVO

**No existe, y se declara.** No se ha creado un tick artificial para «facilitar
la futura IA»: un reloj inventado es una mentira con formato de dato.

---

## K. RELACIONES

Se leen, no se construyen. El grafo es dirigido y el perímetro no añade la
inversa.

---

## L. ARQUITECTURA PROPUESTA

```
FUTURO MODELO IA ──▶ PERÍMETRO RESTRINGIDO ──▶ servicio_consulta ──▶ núcleo ──▶ dataset
```

**El perímetro tiene un solo `return` que entrega datos:**
`getattr(qc, operacion)(**params)`. No hay ninguna rama que construya una
respuesta por su cuenta. Esa es la garantía estructural de no-inferencia.

**Por qué no hay `ai_adapter.py`.** La misión pide especificar y no
implementar, y dice preferir documentación y tests. Un módulo de producción
llamado «adaptador de IA» sería ambiguo: ¿está listo? ¿se usa? No. La
especificación vive en `probar_perimetro_ia.py`, entre
`# ==== INICIO ESPECIFICACION ====` y `# ==== FIN ESPECIFICACION ====`.

---

## M. PRUEBAS

**50 pruebas**, en 12 grupos que cubren los 10 tests pedidos y dos más.

| Grupo | Cubre |
|-------|-------|
| 1 | No acceso directo |
| 2 | Servicio obligatorio |
| 3 | Sin filesystem |
| 4 | Evidencia conservada |
| 5 | Identidad conservada |
| 6 | Estado conservado |
---

## N. MUTATION TESTING

**11/11 detectadas**, sobre dos ficheros: el servicio (de dónde salen los datos)
y el perímetro (la frontera en sí).

| Mutación | Detectada por |
|----------|---------------|
| lee el índice directamente en vez del servicio | `test_contar_con_filtro_devuelve_menos_o_igual` |
| evidencia: se borra | `test_state_version_conservado` |
| `dataset_id`: se anuncia otro mundo | `test_dataset_id_conservado` |
| `state_version`: se borra | `test_state_version_conservado` |
| `NOT_VERIFICADO` pasa a `FOUND` | `test_no_verificado_llega_como_no_verificado` |
| `DATA_UNAVAILABLE` pasa a `NOT_FOUND` | `test_data_unavailable_cuando_el_dataset_no_carga` |
| identidad: se inventa donde no la hay | `test_identidad_ausente_permanece_ausente` |
| `dataset_id` se presenta como edad | `test_dataset_id_conservado` |
| el perímetro acepta cualquier operación | `test_el_rechazo_no_es_un_not_found` |
| la lista blanca se dispara sola | `test_no_puede_llamar_a_funciones_privadas` |
| el dispatcher lee del disco | `test_la_fuente_del_xml_solo_aparece_como_nombre` |

### Dos supervivientes iniciales, y qué eran

**1. «Lee el índice directamente» sobrevivió.** No era un mal mutante: mis
pruebas miraban que `contar` devolviera `total > 0`, y un índice de un elemento
también lo cumple. Añadí `test_contar_devuelve_el_total_real` (>10.000) y
`test_el_total_coincide_con_el_indice_del_nucleo` (igualdad exacta).

**2. `DATA_UNAVAILABLE → NOT_FOUND` sobrevivió.** El estado es prácticamente
inalcanzable en condiciones normales: solo se da si el dataset no carga. Añadí
`test_data_unavailable_cuando_el_dataset_no_carga`, que **rompe el dataset a
propósito** (parcheando `obtener_archivo` y restaurándolo en un `finally`) y
exige `DATA_UNAVAILABLE`.

En ningún caso se relajó una prueba.

### Un fallo mío que no era del código

La primera ejecución del harness imprimió «suite verde sin mutar: **NO**»,
mientras la suite pasaba por separado. La causa era **mi harness**: `correr()`
devolvía `returncode != 0` y yo lo imprimía como si significara «verde». Los
---

## P. REGRESIÓN

```
30 suites · 1174 tests · 0 fallos
```

Incluye `probar_perimetro_ia.py` (50), `probar_servicio_consulta.py` (66),
`probar_api.py` (54), `probar_web.py` (65), `probar_integracion_consulta.py`
(53), `probar_gate_pre_ia.py` (15), adversarial, determinismo y reproducibilidad.

---

## Q. HASHES

**`servicio_consulta.py`: `0A5B6B1C3244E6192752F311B89D075E6B75DE23D971A4972FDBA54F3A73F834`
— idéntico antes y después.** Objetivo cumplido.

Iguales: `nucleo.py`, `servicio.py`, `config.py`, `rutas.py`,
`validar_semantica.py`, `verificacion_semantica.py`, `adaptador_consulta.py`,
`contrato_ia.py`, `ia_conocimiento.py`, `ia_estructura.py`, `ia_verificacion.py`.

**Único fichero de código nuevo:** `dfchron/pruebas/probar_perimetro_ia.py`.
**Documentos nuevos:** `AI_CONSUMER_BOUNDARY.md`, este informe.

Dataset `v1-04170363943d4ba1`, **intacto**.

---

## R. LIMITACIONES

1. **`obtener_evidencia` deja `evidence` en `None`** (§E). No corregido por §15.
2. **`identity` para un id inexistente** devuelve el id **consultado** junto a
   `NOT_FOUND`. El `estado` es el que afirma la ausencia, no la `identity`.
3. **No hay paginación por `offset`** en el contrato. Solo `limit` (máx. 1000).
4. **La superficie no cubre navegación**: búsqueda, listados, geografía y
   exportación siguen fuera. Son herramientas, no consultas.
5. **`probar_perimetro_ia.py` es a la vez spec y suite.** Si alguien ejecuta la
   suite, ejecuta el perímetro. Es intencionado, pero conviene saberlo.
6. **La clasificación C (no disponibles) se declara por ausencia de operación.**
   No hay una operación que diga «esto no existe en el mundo»: la ausencia se
   infiere de que no hay operación que lo devuelva.

---

## S. DECISIONES NUEVAS

**D19 — El perímetro IA se especifica sin implementarse.** En
`ARCHITECTURE_DECISIONS.md`. No se modifica ninguna decisión histórica.

---

## T. RECOMENDACIÓN PARA LA FUTURA IMPLEMENTACIÓN

1. **Pasar los dos gates antes de escribir una línea de integración:**
   `probar_gate_pre_ia.py` (autoridad) **y** `probar_perimetro_ia.py` (acceso).
   Si cualquiera falla, no se integra nada.

2. **Mover el bloque de especificación a producción solo cuando exista un
   consumidor real**, y sin cambiarlo: la lista blanca derivada de `contrato()`,
   el rechazo `OPERACION_NO_PERMITIDA`, y el resultado sin normalizar.

3. **No tocar `servicio_consulta` para que la IA vaya más cómoda.** Si falta una
   capacidad, se escribe y se justifica *antes* de implementarla (§15, regla de
   cambio).

4. **Resolver `obtener_evidencia` antes de usarlo desde fuera.** Hoy devuelve
   `evidence: None` con la procedencia en `data`. Un consumidor que lea
   `evidence` creerá que no hay procedencia.

5. **Mantener el contrato como el único camino**, incluso si el modelo consume
   por HTTP. `/api/consulta/*` y `servicio_consulta` dan lo mismo; el perímetro no
   necesita otra ruta.

---

## Conclusión

> **Un futuro componente de IA podrá consultar el conocimiento de Dwarf Fortress
> exclusivamente a través de una frontera determinista, limitada y trazable, sin
> acceso directo al dataset ni capacidad para convertir ausencia de evidencia en
> conocimiento inventado.**

Demostrado con: 50 pruebas, 11/11 mutaciones, 12 fugas rechazadas, un único
`return` que entrega datos, y `servicio_consulta.py` sin un solo byte cambiado.

**Todavía no existe ningún modelo IA. Ninguna. Ninguna dependencia instalada.**
veredictos de mutación eran correctos; solo la etiqueta estaba invertida.
Corregido.

---

## O. FUGAS DETECTADAS

Las doce peticiones hostiles se rechazan. Además:

* `test_el_rechazo_no_revela_si_el_fichero_existe`: el motivo no dice si el
  fichero existe. Un rechazo que lo confirmara sería un **oráculo de
  reconocimiento**.
* `test_rechazar_no_es_una_excepcion`: el rechazo es un valor. Lanzar abriría
  otro camino de salida.

**Ninguna fuga pasó. Ningún hueco se rellenó.**
| 7 | `NO_DISPONIBLE` |
| 8 | Temporalidad |
| 9 | Relaciones |
| 10 | Operación desconocida |
| 11 | Superficie mínima |
| 12 | Banco de fugas |
Las diez claves del envelope: `estado`, `ok`, `data`, `status`, `certainty`,
`meta`, `identity`, `evidence`, `dataset_id`, `alcance`. Ninguna se rellena en
el perímetro.

### Una inconsistencia real que se documentó

`obtener_evidencia` devuelve `evidence: None` y mete la procedencia en `data`.
Comprobado:

```
evidencia estado: FOUND | evidence: NoneType
evidencia data  : ['legends.xml']
```

**No se corrigió**, porque §15 prohíbe tocar `servicio_consulta`. Queda fijado
por una prueba y documentado como inconsistencia conocida, no escondido.