# CONTRATO PRE-LLM CONGELADO

> **Estado del documento:** CONGELADO.
> **Alcance:** obligatorio ANTES de integrar cualquier modelo de lenguaje.
> **Naturaleza:** describe lo que el sistema YA hace. No autoriza ninguna
> capacidad nueva.
> **Si algo de aqui no se cumple, el sistema no esta listo para un LLM.**

Documento normativo del proyecto. Complementa, sin sustituir, a
`ai_data_contract.md` (contrato de datos) y a
`INFORME_AUDITORIA_FINAL_PRE_IA.md` (auditoria).

---

## 0. PRINCIPIO RECTOR

```
El modelo propone.
El nucleo verifica.
La politica autoriza.
El compositor expresa.
```

Cuatro frases, cuatro autoridades distintas. Ninguna se delega.

El objetivo no es que el sistema pueda hablar con una IA. Es que **el nucleo
siga siendo la autoridad cuando la IA se equivoque, invente, mienta,
contradiga al juego o intente modificar sus propios privilegios.**

La IA es una capa intercambiable. Si se sustituye, el nucleo no cambia.

---

## 1. AUTORIDAD

| Nivel | Dueño | Puede | NO puede |
| ----- | ----- | ----- | -------- |
| Verdad del mundo | `nucleo.py` | decir que un sitio es de tipo X | ser corregido por el modelo |
| Evidencia | `ia_conocimiento` / `contrato_ia.evidencia()` | anclar un dato al `dataset_id` y a sus campos | ser fabricada por texto libre |
| Verificacion | `ia_estructura` | decir `VERIFICADA` / `NO_VERIFICADA` / `NO_APLICABLE` | ser saltada por un campo de entrada |
| Visibilidad | `contrato_ia` + `ia_contrato.contexto()` | filtrar que entra al contexto | ser cambiada por el modelo |
| Politica de divulgacion | `contrato_ia` (`disclosure`) | decir si algo puede revelarse | ser relajada por el modelo |
| Descubrimiento | `estado_conocimiento` | registrar que el JUGADOR conoce un dato | ser fabricado por el modelo |
| Salida | `ia_frontera.componer_seguro()` | redactar el texto del jugador | recibir texto libre del modelo |

**Regla estructural:** cada nivel se resuelve ANTES de pasar al siguiente. La IA
no participa en ninguno de ellos.

---

## 2. FLUJO

```
DF STATE  (nucleo, dataset real)
   |
   v
EVIDENCE  (entidad, df_id, campos, state_version)
   |
   v
VERIFICATION  (ia_estructura)
   |
   v
POLICY  (visibility + disclosure)
   |
   v
AUTHORIZED CONTEXT  (ia_contrato.contexto -> claims con ref)
   |
   v
AI PROPOSAL  <-- UNICA participacion de la IA. Propone, no afirma.
   |
   v
VERIFICATION AGAIN  (ia_contrato.validar_salida)
   |
   v
COMPOSITOR  (ia_frontera.componer_seguro)
   |
   v
PLAYER
```

### El punto exacto del poder de la IA

La IA interviene en **un solo nodo**: `AI PROPOSAL`. Ese nodo:

* puede elegir **cuales** referencias del contexto citar;
* puede clasificar la intencion entre tipos declarados;
* puede pedir informacion disponible segun el contrato.

No puede crear, no puede ampliar y no puede saltarse el contrato. Si su
propuesta no pasa `validar_salida()`, no sale. `puede_entregarse = False` es
fail-closed: ante cualquier duda, el jugador no lo lee.

---

## 3. CAMPOS PROHIBIDOS COMO AUTORIDAD

Ninguno de estos concede nada, venga de donde venga:

| Campo | Por que no concede nada |
| ----- | ---------------------- |
| `verified` | La verificacion la calcula el nucleo comparando con la ficha real. |
| `trusted` | No existe un canal de confianza de entrada. |
| `confidence` | La confianza declarada no influye en la calculada. |
| `admin_override` | No existe override por datos. |
| `visibility` | La decide `contrato_ia` al construir el contexto. |
| `discovered` | Lo registra `estado_conocimiento`, no el modelo. |
| `disclosure` | La politica de divulgacion es del sistema. |
| `source` | La procedencia la emite el sistema, no se declara. |
| `state_version` | Solo la emite el nucleo, al construir la evidencia. |

**Y cualquier equivalente futuro.** El principio no es una lista: es que
**ningun dato de entrada es autoridad sobre nada**. Los campos de arriba son
ejemplos, no la definicion.

No es una aspiracion: `ia_contrato._claim_de_entrada()` construye el contexto
como una **copia minima declarada**, de modo que un campo desconocido ni
siquiera llega a existir dentro del contexto.

---

## 4. TEXTO LIBRE

> **El texto libre producido por un modelo nunca constituye evidencia ni verdad
> por si mismo.**

Consecuencias, todas comprobadas por el gate:

* No se convierte en `evidence`.
* No marca nada como `VERIFICADA`.
* No entra automaticamente en el contexto.
* No aparece en la salida final por si mismo.

**Por que:** `ia_frontera.componer()` redacta la respuesta a partir de los
claims **del contexto**, no de los del modelo. El modelo aporta la seleccion;
nunca las palabras. Por eso no necesita ser «fiel»: no hay texto suyo en el
resultado que pueda desviar.

### Canales de salida que NO existen

Errores, logs, `repr()`, JSON de depuracion y excepciones **no** son canales de
salida al jugador. Si un texto no pasa por `componer_seguro()`, no se entrega.

---

## 5. CONOCIMIENTO EXTERNO

Una futura wiki, documentacion o base externa puede servir como:

* orientacion;
* explicacion;
* contexto;
* hipotesis.

**No puede** sobrescribir la verdad del estado actual del juego.

El estado del juego es la unica fuente de verdad. Un documento externo puede
ayudar a explicar un hecho que el nucleo ya confirmo, pero no puede
establecerlo. Si lo contradice, **el nucleo gana**, y la discrepancia se
reporta en vez de resolverse a favor del documento.

---

## 6. TEMPORALIDAD

### Lo que el nucleo tiene de verdad

El nucleo **no tiene reloj de juego**: no hay ticks, ni turnos, ni contador
monotonico. Pero si tiene una **identidad del estado del mundo**:

```
00_SOURCE/dataset_version.json  ->  dataset_id = "v1-04170363943d4ba1"
```

Ese identificador:

* **existe de verdad**: lo produce `calcular_dataset_id()` en cada actualizacion;
* **se deriva del contenido** (SHA-256 de las secciones), **no de un reloj**;
* **es determinista**: el mismo contenido produce siempre el mismo id;
* **cambia exactamente cuando cambia el mundo**, que es lo que hace falta para
  poder invalidar.

Por eso **no se ha inventado un sistema temporal**: se ha usado el que ya
existia.

### El contrato

```text
evidencia.state_version = dataset_id real del mundo que produjo el dato
evidencia_es_actual(ev, version_actual) -> bool
```

Regla estricta, **fail-closed**: solo es actual la evidencia que **declara**
version **y** coincide. Una evidencia sin `state_version` no es «de otro
mundo»: es **desconocida**, y lo desconocido no sostiene una afirmacion que se
presente como actual.

### Lo que sigue SIN existir, y se declara

* **Caducidad temporal.** No hay «la evidencia expira en N horas»: no hay reloj
  de juego al que pedirle una unidad de tiempo. Solo «pertenece a este mundo o
  no».
* **Estado de partida en vivo.** El dataset es una foto. Si se integra DF-Hack,
  su estado en memoria **no** tendra `dataset_id` hasta que se defina como se
  versiona un mundo que cambia en vivo. Problema **sin resolver y declarado**.

### Adaptador DF: requisitos para el futuro

Si se integra DF-Hack, solo se admiten datos estructurados con:

1. `df_id` (identidad estable);
2. procedencia;
3. estado de descubrimiento;
4. visibilidad;
5. politica de divulgacion;
6. **version temporal**.

---

## 7. IDENTIDAD

### Identificadores seguros

| Identificador | Uso |
| ------------- | --- |
| `df_id` + `entidad` | identidad de una afirmacion; solo significa junto a su tipo |
| `dataset_id` | identidad del estado del mundo, derivado del contenido |

`(entidad, df_id)` es la identidad real: `112` de sitio y `112` de figura **no**
son la misma entidad.

### Identificadores NO seguros

| Identificador | Por que no vale |
| ------------- | --------------- |
| Nombre de la entidad | No es unico, ni estable. |
| Posicion / coordenadas | Pueden cambiar; y ademas son secreto. |
| Indice o contador de iteracion | Depende del recorrido. |
| Texto de la afirmacion | No es identidad, es descripcion. |

### Relaciones: alcance limitado

El nucleo **no ofrece identidad estable para relaciones compuestas**
(`A esta relacionado con B` en un grafo arbitrario).

Por eso las afirmaciones relacionales complejas **quedan fuera del conjunto de
afirmaciones verificables**: salen `NO_APLICABLE`, nunca `VERIFICADA`.

No se usan comparacion de palabras ni similitud lexica para fingir una
verificacion relacional. **La trazabilidad lexica no es una barrera de
seguridad**: es una medida de descripcion, y asi se declara.

---

## 8. DESCUBRIMIENTO

### Los dos ejes, que no deben mezclarse

```
MUNDO    (truth_status, visibility, disclosure)  ->  del NUCLEO
JUGADOR  (knowledge: lo que el jugador ha visto)  ->  del ESTADO DEL JUGADOR
```

`marcar_conocido()` esta documentado, por escrito, como una funcion que **no
toca `truth_status`, ni `visibility`, ni `disclosure`**. Solo anota un hecho
sobre el jugador. Eso es lo que permite cerrar esta fase sin inventar nada.

### Reglas

| Situacion | Resultado |
| --------- | --------- |
| El dato existe pero no se ha descubierto | No entra en el contexto por eso solo. |
| El estado del juego lo hace visible legitimamente | Pasa a formar parte del contexto permitido. |
| La IA propone `discovered=true` | Se descarta. Sin efecto. |
| La IA propone `visibility=...` | Se descarta. La decide el sistema. |

Se puede marcar como conocido un `UNKNOWN`: **saber que no consta tambien es
saber**. Decision del nucleo, no del modelo.

**Reserva declarada:** la progresion *dentro de una partida en vivo* (DF-Hack)
no esta demostrada, porque el nucleo actual trabaja sobre un dataset estatico.

---

## 9. EL FUTURO ADAPTADOR: CONTRATO MINIMO

### PUEDE

* recibir contexto ya autorizado;
* recibir datos explicitamente permitidos;
* **proponer** una afirmacion;
* **proponer** una intencion;
* seleccionar entre opciones estructuradas;
* solicitar informacion disponible segun el contrato.

### NO PUEDE

* escribir directamente en el nucleo;
* modificar la verdad del mundo;
* modificar visibilidad;
* modificar descubrimiento;
* modificar confianza;
* modificar procedencia;
* modificar evidencia;
* modificar politica;
* modificar permisos;
* emitir directamente la respuesta final;
* introducir texto libre como autoridad;
* marcar una afirmacion como `VERIFICADA`;
* marcar una afirmacion como `TRUSTED`;
* elevar privilegios mediante campos de entrada.

### Forma de la salida

Toda salida pasa por `ia_contrato.validar_salida(salida, ctx)`. No hay otra
ruta. Y el texto que ve el jugador lo produce `ia_frontera.componer_seguro()`,
no el modelo.

### Verificacion semantica: `NO_APLICABLE`

No existe verificador semantico. No se implementara uno, y **no se usara otro
LLM como juez**: eso seria el modelo como autoridad sobre lo que puede
revelarse.

Mientras no exista, se mantiene en `NO_APLICABLE` y **no se disimula**. Un
sistema que dice «no puedo comprobar esto» es mas seguro que uno que finge.

---

## 10. GATE

Antes de integrar cualquier modelo debe pasar:

```
python dfchron/pruebas/probar_gate_pre_ia.py
```

Los quince invariantes, numerados como en la mision:

| # | Invariante |
| - | ---------- |
| 01 | El modelo no controla la verdad. |
| 02 | El modelo no controla la verificacion. |
| 03 | El modelo no controla la visibilidad. |
| 04 | El modelo no controla la politica. |
| 05 | El texto libre no constituye evidencia. |
| 06 | Una evidencia invalida no verifica. |
| 07 | Una evidencia incorrecta no verifica. |
| 08 | La persistencia no eleva privilegios. |
| 09 | La reconstruccion no depende de texto libre. |
| 10 | El orden de llegada no cambia la verdad. |
| 11 | Los campos de privilegio no conceden privilegios. |
| 12 | El compositor no recibe autoridad del modelo. |
| 13 | Lo prohibido no entra en contexto. |
| 14 | Si hay versionado, la evidencia obsoleta falla. |
| 15 | Si no hay versionado, se marca `NOT PROVEN` y no se oculta. |

`FAIL` no es un fallo de test: es un fallo de seguridad.

El gate cubre ademas el comportamiento hostil: existe un adaptador de prueba
**sin ningun LLM** que envia a la vez `verified`, `trusted`, `confidence`,
`admin_override`, `visibility`, `discovered`, `source` y `state_version`, mas
texto libre inventado. Ninguno de esos campos cambia el veredicto, y el texto
no llega a la salida.

---

## 11. LO QUE ESTE CONTRATO NO CUBRE

* **Integracion con DF-Hack** (estado en vivo). Necesita su propio contrato
  temporal.
* **Verificacion semantica.** No existe y no se finge.
* **Relaciones complejas.** Fuera del alcance verificable.
* **Memoria conversacional.** No existe. Si se anade, **debe revalidarse y
  recomponerse en cada turno**.
* **Trazabilidad lexica.** No es una barrera de seguridad.

Cada uno de estos sigue siendo un `NOT PROVEN` honesto. No son fallos: son
capacidades que el nucleo no tiene, y que estan escritas para que no se
confundan con garantias.

---

## 12. REGLA DE CAMBIO

Cualquier modificacion que amplie lo que un modelo puede hacer requiere:

1. una razon escrita de por que el nucleo no basta;
2. una prueba que demuestre la propiedad nueva;
3. actualizar este documento **en el mismo commit**;
4. volver a pasar el gate y la regresion completa.

Un `FAIL` en el gate no se corrige debilitando el gate.


