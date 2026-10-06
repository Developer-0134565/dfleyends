# INFORME DE CIERRE PRE-IA

> **Estado:** PREPARADO + CONTRATO PRE-IA CONGELADO
> **Conclusion:** **PRE-LLM CERRADO CON RESERVAS** (ver seccion G)
> **El modelo IA sigue SIN implementar. No se ha implementado.**

---

## A. ESTADO INICIAL

Según `INFORME_AUDITORIA_FINAL_PRE_IA.md`:

| Medida | Valor |
| ------ | ----- |
| Invariantes | 18 evaluados: **17 PASS**, 1 NOT PROVEN (I14), 0 FAIL |
| Ataques | 44 evaluados: **44 PASS**, 2 NOT PROVEN (temporalidad) |
| Suites de regresion | 15/15 PASS |
| Tests | 455 PASS |
| Banco adversarial | 83/83 escenarios, 0 fugas |
| I14 | **NOT PROVEN** — evidencia sin identidad temporal |

Quedaron abiertas: temporalidad, descubrimiento progresivo, identidad
relacional, el nombre canonico de un adaptador, y la posibilidad de que una
integracion futura reintrodujera un canal de salida libre.

---

## B. CAMBIOS REALIZADOS

### B.1 Cambios de produccion (4 archivos, minimos, cada uno con prueba)

| Archivo | Cambio | Motivo | Efecto |
| ------- | ------ | ------ | ------ |
| `dfchron/contrato_ia.py` | `evidencia()` acepta `state_version`; nuevos `SIN_VERSION`, `version_de_evidencia()`, `evidencia_es_actual()` | La evidencia no declaraba de que mundo salia (I14) | La evidencia se invalida por cambio de mundo. Backwards-compatible: sin el campo, `UNKNOWN` |
| `dfchron/ia_conocimiento.py` | `evidencia_de()` inyecta el `DATASET_ID` real | Anclar toda la evidencia en un solo sitio, no en cada constructor | Toda evidencia del puente queda versionada de forma automatica |
| `dfchron/ia_contrato.py` | `_claim_de_entrada()` conserva `state_version` | Sin el, la version se perdia al construir el contexto | La auditoria puede seguir la evidencia dentro del contexto |
| `dfchron/ia_estructura.py` | `verificar_afirmacion()` acepta `version_actual` | Cerrar I14 en el camino REAL de verificacion | Evidencia obsoleta -> `NO_VERIFICADA`. Backwards-compatible |

**Sin cambios:** `nucleo.py` (hash identico), `ia_frontera.py`,
`ia_verificacion.py`, `ia_contexto.py`, `estado_conocimiento.py`, `ia_mock.py`,
`ia_inferencia.py`.

### B.2 Cambios de pruebas

| Archivo | Cambio |
| ------- | ------ |
| `dfchron/pruebas/probar_cierre_pre_ia.py` | **NUEVO.** 54 pruebas, 8 familias |
| `dfchron/pruebas/probar_gate_pre_ia.py` | **NUEVO.** 15 pruebas, el gate |
| `dfchron/pruebas/probar_auditoria_final.py` | `test_H1`/`test_H2` **actualizados, no eliminados** (46 -> 49) |

Sobre `test_H1`/`test_H2`: eran guardas negativas que afirmaban «no hay
temporalidad». Ahora hay temporalidad real, asi que se han **invertido**: ya no
comprueban la ausencia, sino que la version sea la real, que no se disfraze de
reloj, que lo desconocido se declare desconocido, y que el alcance siga sin
prometer caducidad. **No se eliminaron.**

### B.3 Cambios documentales

| Archivo | Cambio |
| ------- | ------ |
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | **NUEVO.** 13 secciones. Contrato congelado |

### B.4 Cambios NO realizados (confirmado)

NO se implemento: LLM, API externa, RAG, embeddings, memoria conversacional,
agentes, NPC IA, generacion libre de texto, conocimiento externo operativo,
sistema temporal artificial, ni `df_id` artificial.

Verificado mecanicamente: cero SDK de IA en el proyecto; los archivos nuevos solo
importan `copy`, `json`, `os`, `sys`, `unittest` y modulos del propio proyecto.
Sin `requirements.txt` nuevo. Sin repositorio Git.

---

## C. TESTS

| Suite | Resultado |
| ----- | --------- |
| Regresion (15 suites originales) | **15/15 PASS, 0 FAIL** |
| Adversarial (banco) | **83/83, 0 fugas, determinista en 3 ejecuciones** |
| Verificacion estructurada | **18/18 PASS** (+3 de version) |
| Persistencia | **PASS** (estado, esquema, dataset distinto, solo lectura) |
| Reconstruccion | **PASS** (determinista, sin texto previo) |
| Temporalidad | **PASS** (54 pruebas; I14 por el camino real) |
| Descubrimiento | **PASS** (ciclo completo; el modelo no descubre) |
| Adaptador hostil | **PASS** (16 campos de privilegio + texto libre) |
| Gate PRE-LLM | **15/15 PASS** |
| Nueva suite de cierre | **54/54 PASS** |
| Auditoria final (actualizada) | **49/49 PASS** |

**Total: 17 suites. 0 FAIL en todo el proyecto.**

### C.1 Las pruebas tienen dientes: mutation test

Para no entregar pruebas que pasan siempre, se rompio el nucleo a proposito:
`evidencia_es_actual()` se sustituyo por `return True`.

| Suite | Resultado con el nucleo roto |
| ----- | ---------------------------- |
| `probar_gate_pre_ia.py` | **FAILED** (1 fallo) — el gate lo detecta |
| `probar_cierre_pre_ia.py` | **FAILED** (6 fallos) |

Nucleo restaurado y verificado. Las pruebas comprueban propiedades reales.

---

## D. INVARIANTES

| Invariante | Inicial | Final | Nota |
| ---------- | ------- | ----- | ---- |
| I01 | PASS | **PASS** | |
| I02 | PASS | **PASS** | |
| I03 | PASS | **PASS** | |
| I04 | PASS | **PASS** | |
| I05 | PASS | **PASS** | |
| I06 | PASS | **PASS** | |
| I07 | PASS | **PASS** | |
| I08 | PASS | **PASS** | |
| I09 | PASS | **PASS** | |
| I10 | PASS | **PASS** | |
| I11 | PASS | **PASS** | |
| I12 | PASS | **PASS** | |
| I13 | PASS | **PASS** | |
| **I14** | **NOT PROVEN** | **PASS** | Cerrada con la version real del dataset. No inventada |
| I15 | PASS | **PASS** | |
| I16 | PASS | **PASS** | |
| I17 | PASS | **PASS** | 15 suites intactas |
| I18 | PASS | **PASS** | `nucleo.py` con hash identico |

**18 PASS, 0 NOT PROVEN, 0 FAIL.**

Sobre I14, sin adornos: el nucleo **no tiene reloj de juego**, asi que no se
invento ninguno. Si tiene algo real: `dataset_id`, derivado del SHA-256 del
contenido por `actualizar_datos.calcular_dataset_id()`. Es determinista, cambia
exactamente cuando cambia el mundo, y ya se leia en `ia_conocimiento` para la
procedencia. Se integro ahi en lugar de crear un sistema temporal nuevo.

> **Corrección P1.1 (2026-10-04).** «Cambia exactamente cuando cambia el mundo»
> es **falso**, y está demostrado con datos reales
> (`P1_VERSIONADO_MUNDO_VIVO.md` §20.1): dos mundos con contenido idéntico
> reciben el mismo `dataset_id`, y el mundo puede cambiar sin que el contenido
> extraído cambie. `state_version` identifica **contenido**, no **estado**.
> El resto del párrafo —no hay reloj, se usó lo real, fail-closed— sigue vigente,
> y el propio párrafo ya decía lo esencial: I14 **no demuestra** que la
> afirmación siga siendo verdadera.

**Lo que NO se ha ganado:** I14 demuestra que una evidencia de otro mundo **no es
actual**. NO demuestra que la afirmacion siga siendo verdadera.

---

## E. RIESGOS RESIDUALES

### E.1 Reales (y mitigados)

| Riesgo | Estado |
| ------ | ------ |
| Campo de entrada concede privilegios | Mitigado: `_claim_de_entrada()` es copia minima declarada; un campo desconocido ni existe en el contexto |
| Texto libre como autoridad | Mitigado: el compositor usa claims del contexto, nunca `answer` |
| Evidencia de otro mundo | Mitigado: `state_version` + `evidencia_es_actual()` fail-closed |
| Cargar estado mas permisivo que producirlo | Mitigado: `_validar_esquema()` revalida cada entrada con el mismo `_validar()` |

### E.2 Aceptados

| Riesgo | Por que se acepta |
| ------ | ----------------- |
| `deteccion_fuga()` es un esqueleto | Se documenta como tal. Una parafrasis sin cifras («esta al norte») exige comprension del lenguaje |
| Trazabilidad lexica no es barrera de seguridad | Es una medida de descripcion, declarada como tal |
| El filtrado se apoya en reglas | Correcto: son reglas deterministas, no un juez. Quien las escribe puede equivocarse |

### E.3 NO demostrados (y declarados como tales)

| Capacidad | Por que sigue abierta |
| --------- | ---------------------- |
| **Verificacion semantica** | No existe. Parafrasis, negacion y afirmacion compuesta no se comprueban. Sigue en `NO_APLICABLE`. **No se usara otro LLM como juez.** |
| **Relaciones complejas** | El nucleo no da identidad estable para un grafo. Fuera de alcance: `NO_APLICABLE`, nunca `VERIFICADA` |
| **Caducidad temporal** | No hay reloj de juego. Solo «pertenece a este mundo o no» |
| **Estado de partida en vivo** | El dataset es una foto. Un mundo que cambia en memoria no tiene `dataset_id` todavia |
| **Descubrimiento en partida viva** | Demostrado sobre dataset estatico; no sobre DF-Hack |
| **Memoria conversacional** | No existe. Si se anade, debe revalidarse y recomponerse en cada turno |

Ninguno se ha convertido en PASS. Cada uno esta escrito donde se leera.

### E.4 Dependientes del futuro adaptador

* Que toda salida pase por `ia_contrato.validar_salida()`.
* Que el texto al jugador lo produzca `ia_frontera.componer_seguro()`.
* Que el adaptador DF aporte `df_id`, procedencia, descubrimiento, visibilidad,
  politica y **version temporal**.
* Que `test_H1b` siga pasando: la version no puede convertirse en reloj.

---

## F. HASHES

### F.1 Produccion

| Archivo | SHA-256 (16) | Cambio |
| ------- | ------------ | ------ |
| `00_SOURCE/tools/nucleo.py` | `CCC48EA67849701A` | **sin cambios** |
| `dfchron/contrato_ia.py` | `EB4A4156CBFAF764` | modificado |
| `dfchron/ia_contrato.py` | `A562FE031A3A259B` | modificado |
| `dfchron/ia_estructura.py` | `BE9FC091EFF534E9` | modificado |
| `dfchron/ia_conocimiento.py` | `7EBCBBC2C2B4F044` | modificado |
| `dfchron/ia_frontera.py` | `4EEE0519902E6AD3` | sin cambios |
| `dfchron/ia_verificacion.py` | `B8BFD2CC39D3F302` | sin cambios |
| `dfchron/ia_contexto.py` | `8AE65D381970147E` | sin cambios |
| `dfchron/estado_conocimiento.py` | `E30CBF271DB3EC0A` | sin cambios |
| `dfchron/ia_mock.py` | `269E2A22FE47E318` | sin cambios |
| `dfchron/ia_inferencia.py` | `CC616482F2536CFB` | sin cambios |

### F.2 Dataset (intacto)

| Entrada | SHA-256 (16) |
| ------- | ------------ |
| `dataset_id` | `v1-04170363943d4ba1` |
| `legends.xml` | `77db4739c4064911` |
| `legends_plus.xml` | `fb6be93dac3e878b` |

### F.3 Nota sobre trazabilidad

**No hay repositorio Git.** `git diff` no es posible. La trazabilidad depende de
las dos instantaneas registradas en esta sesion (inicio y cierre), no de un VCS.

---

## G. ESTADO FINAL

### Lo que queda demostrado

* **I14 cerrado** con la version real del dataset, no con un tick inventado.
* Descubrimiento progresivo demostrado en el dataset estatico.
* Identidad delimitada: `(entidad, df_id)` sirve; las relaciones complejas, no.
* Frontera del adaptador formalizada en documento congelado.
* Adaptador hostil sin LLM: 16 campos de privilegio, ninguno concede nada.
* Texto libre sin ruta a la verdad ni a la salida.
* No contaminacion entre los siete ejes.
* Reconstruccion determinista sin memoria conversacional.
* Persistencia que no puede ser mas permisiva que la produccion.
* Gate automatico de 15 invariantes.
* 17 suites, 0 FAIL, banco adversarial 83/83.

### Conclusion

```
PRE-LLM CERRADO CON RESERVAS
```

Se elige **con reservas**, y no sin ellas, por una razon concreta: hay
capacidades que el nucleo **no tiene** y no puede tener sin inventar semantica
inexistente: verificacion semantica, relaciones complejas, caducidad temporal, y
cualquier cosa que exija un reloj de juego o un estado en vivo. Convertirlas en
PASS habria exigido fabricar exactamente lo que la mision prohibe fabricar.

Lo que si se cierra, se cierra de verdad: los contratos que dependian de datos
inexistentes se han resuelto con los datos que el nucleo ya tenia, y los que no,
se han escrito como reservas explicitas.

### La frase que queda

> El nucleo sigue siendo la autoridad.
> El modelo, cuando llegue, solo va a proponer.

---

## H. COMO VERIFICAR

```powershell
# Gate (15 invariantes)
python dfchron\pruebas\probar_gate_pre_ia.py

# Cierre (54 pruebas)
python dfchron\pruebas\probar_cierre_pre_ia.py

# Banco adversarial (83 escenarios)
python dfchron\pruebas\evaluar_banco_ia.py

# Regresion completa
python dfchron\pruebas\probar_auditoria_final.py
```