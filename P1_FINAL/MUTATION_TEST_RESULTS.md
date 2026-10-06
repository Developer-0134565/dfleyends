# MUTATION TESTING PRE-IA — RESULTADOS

```
MUTATIONS_TOTAL:  10
KILLED:            9
SURVIVED:          0
NOT_APPLICABLE:    1
NOT_EXECUTED:      0
```

**Veredicto: `MUTATION_TESTING_STRONG_WITH_M07_NOT_APPLICABLE`**

| ID | Capa | Mutación | Suite | Resultado |
|---|---|---|---|---|
| M01 | `servicio.py` / `envolver_ficha` | certainty del envelope FOUND → UNKNOWN | `probar_contrato_certainty.py` | **KILLED** |
| M02 | `servicio_consulta._resultado` | certainty condicional → siempre FACT | `probar_contrato_certainty.py` | **KILLED** |
| M03 | `servicio_consulta` | atributo no declarado → FOUND | `probar_integracion_consulta.py` | **KILLED** |
| M04 | `servicio_consulta.verificar` | verificación fallida → FOUND | `probar_integracion_consulta.py` | **KILLED** |
| M05 | evidencia | `base["evidence"] = None` | `probar_integracion_consulta.py` | **KILLED** |
| M06 | identidad | `dataset_id` miente | `probar_integracion_consulta.py` | **KILLED** |
| M07 | adaptador | `deepcopy` → copia superficial | `probar_contrato_certainty.py` | **NOT_APPLICABLE** |
| M08 | adaptador | NOT_VERIFIED → 404 | `probar_integracion_consulta.py` | **KILLED** |
| M09 | API | la ficha deja de pasar por `servicio_consulta` | `probar_api.py` | **KILLED** |
| M10 | adaptador | no calcula `http_status` | `probar_integracion_consulta.py` | **KILLED** |

---

## M01 — cerrada en el lugar correcto

**Por qué sobrevivía en su anclaje anterior.** `servicio_consulta._resultado()`
solo evalúa su bloque por defecto cuando `env is None`:

```python
base = dict(env) if isinstance(env, dict) else {}
if env is None:            # <-- solo aquí nace `certainty`
    base = { ... "certainty": "FACT" if estado == FOUND else "UNKNOWN" ... }
```

`obtener_entidad` **pasa `env`**, así que ese bloque solo se ejecuta en la ruta
de error, donde el resultado ya es `UNKNOWN`. La mutación `FACT → UNKNOWN` sobre
esa línea **no cambia nada observable**: es un mutante equivalente.

**Dónde nace realmente la certeza.** La encontré leyendo el código, no suponiendo:

```python
# dfchron/servicio.py :: envolver_ficha()
cert = datos.get("certainty", UNKNOWN) if isinstance(datos, dict) else UNKNOWN
return {"ok": True, "data": datos, "status": cert, "certainty": cert,
        "meta": {..., "certainty": cert}, **extra}
```

**Evidencia de que M01 no es equivalente** (Objetivo 2):

| Campo | Valor |
|---|---|
| `mutation_location` | `dfchron/servicio.py` → `envolver_ficha()` |
| `original_expression` | `cert = datos.get("certainty", UNKNOWN) if isinstance(datos, dict) else UNKNOWN` |
| `mutated_expression` | `cert = UNKNOWN   # MUTACION M01` |
| `test_executed` | `test_un_envelope_FOUND_declara_FACT` |
| `original_result` | **PASS** |
| `mutated_result` | **FAIL** |
| `status` | **KILLED** |

Además el hash de `servicio.py` se restauró byte a byte:
`48eb8354dca8728b…` antes y después.

**No se tocó producción para que muriera.** Se movió el anclaje al punto donde
el contrato realmente establece la certeza.

---

## M07 — NOT_APPLICABLE

1. **Qué mutaba:** `copy.deepcopy(dict(resultado))` → `dict(resultado)` en
   `adaptador_consulta._responder`.
2. **Qué garantía pretendía probar:** el docstring del adaptador declara
   *«No muta el resultado del servicio»*.
3. **Por qué no es observable:** `servicio_consulta._resultado()` construye un
   **`dict` nuevo en cada llamada**. No existe ningún objeto persistente que una
   copia superficial pudiera contaminar.
4. **No hay aliasing observable** que distinga copia profunda de copia superficial.
5. **La mutación se conserva** para reevaluarla si algún día el servicio cachea
   envelopes. Se ejecuta y se registra, pero **no cuenta como KILLED**.
6. **No se modificó producción** para preservar una implementación que no
   constituye garantía observable.

No se añadió ningún test artificial que comprobara que se llama a `deepcopy`:
eso demostraría implementación, no contrato.

---

## Correcciones de infraestructura aplicadas

| Error previo | Corrección |
|---|---|
| Suite asignada incorrectamente (M08/M10) | Se usa `probar_integracion_consulta.py`, donde vive `test_cada_estado_conserva_su_codigo_http` |
| Ancla con normalización de texto → falso positivo | `verificar_anclas.py` lee **en bytes**, como hace el harness |
| `cmd /c` mataba el proceso con una mutación aplicada | Ejecución **desacoplada** (`Start-Process`) |

`verificar_anclas.py` se ejecuta **antes** de mutar nada y confirma
**10/10 anclas existentes**. Si una no existiera, el harness marcaría
`NOT_APPLICABLE` y parecería un resultado válido.

---

## Ejecución reproducible

```powershell
python P1_FINAL\verificar_anclas.py     # 10/10 anclas, antes de mutar
python P1_FINAL\mutaciones.py          # desacoplado, secuencial
```

| Salvaguarda | Cómo |
|---|---|
| Los bytes originales se guardan | `_b(ruta)` abre en `"rb"` |
| Restauración | `finally` **y** comparación de hash |
| Interrupción del proceso | `_hash_esperado.json` anota el hash a recuperar |
| Finales de línea / BOM | Escritura siempre binaria |

---

## Integridad

| Recurso | Estado |
|---|---|
| `servicio_consulta.py` | **intacto** `0a5b6b1c…` |
| `adaptador_consulta.py` | **intacto** `c456256e…` |
| `servicio.py` | **intacto** `48eb8354…` |
| Tests originales | **54/54 · 55/55 · 8/8 · 66/66 · 65/65** |
| Partida de DF | No tocada |
| IA | **0** |

## Lo que NO se declara

`PRE_IA_COMPLETE` **no** se emite. Siguen pendientes: auditoría de contratos,
auditoría documental, `GARANTIAS_PRE_IA.md` y cierre global.