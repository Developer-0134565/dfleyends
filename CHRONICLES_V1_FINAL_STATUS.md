# CHRONICLES v1 — ESTADO FINAL

```
CHRONICLES_V1_STATUS: PARTIAL
```

**No emito `COMPLETE`.** El inventario de eventos está hecho y el motor opera
sobre el dataset real, pero las capas `servicio_consulta → adaptador → API → Web`
**no existen**.

---

## Lo que SÍ está verificado

| | |
|---|---|
| **Motor Chronicles** | **25/25 OK** |
| **Ingestor sobre dataset real** | **9.311 registros**, 0 corruptas, determinista |
| **Inventario completo de eventos** | **57.215 leídos · 90 tipos · 78 utilizables** |
| **Procedencia por campo** | Respetada con `valor_de()` / `procedencia_de()` |
| **Producción** | **INTACTA** — 4 hashes sin cambios |
| **PRE-IA** | `COMPLETE`, intacto |
| **IA** | **0** |
| **Partida** | No tocada |

---

## El hallazgo de esta fase

Mi primera heurística buscaba el sujeto en campos `hf` y `figure`.
**Esos campos no existen.** El campo real se llama **`hfid`**.

Con los nombres correctos, los tipos utilizables pasan de **11 a 78 de 90**.

> Una lista de campos **supuesta** habría descartado el **88 %** de los
> eventos por un nombre inventado. Es el mismo error que el proyecto lleva
> evitando desde el principio: *no asumir, ejecutar*.

Segundo hallazgo: `year` y `seconds72` están en **los 57.215 registros**. El
tiempo es sólido y uniforme.

---

## Un defecto que la integración reveló

`cargar()` devolvía `_cache["datos"]` en la ruta cacheada y el `_cache`
completo en la primera: **mismo nombre, dos tipos de retorno**. Detectado
ejecutando, no leyendo. Corregido.

---

## Lo que NO está hecho

| Capa | Estado |
|---|---|
| Conversión dataset → eventos Chronicles | **NO** |
| `servicio_consulta` | **NO** |
| `adaptador_consulta` | **NO** |
| Endpoints API | **NO** |
| Vistas Web | **NO** |
| Fixture end-to-end | **NO** |
| Mutation testing del motor | **NO** |

---

## Dos decisiones que conviene conocer

**1. No he convertido `year`/`seconds72` a ticks de DF.** Exige conocer la
constante exacta de conversión, que **no está demostrada**. Convertirla sería
inventar precisión temporal. Queda usar `(year, seconds72)` como clave
compuesta: determinista sin constante inventada.

**2. `change hf job` NO es `PROFESSION_CHANGED`.** Es un cambio de *estado
vital*, no de profesión. Emitirlo como cambio de profesión sería una traducción
semántica sin evidencia.

---

## Lo que sabemos, y lo que no

### Sabemos
- 57.215 eventos con tiempo uniforme (`year` + `seconds72`).
- 78 tipos con sujeto identificable.
- `hf died` (4.484) tiene identidad, tiempo, causa y procedencia.
- El dataset merged declara **procedencia por campo**.

### No sabemos todavía
- Si `add hf entity link` significa realmente una llegada o una vinculación
  administrativa.
- La equivalencia exacta entre `seconds72` y ticks de DF.
- Si `hf wounded` aporta algo usable en v1.

### No está disponible
- Estado por tick de una figura: no hay serie temporal en el dataset.
- `PROFESSION_CHANGED` derivado: `NOT_AVAILABLE`.

---

## Por qué PARTIAL

```
DATASET → CHRONICLES → SERVICIO → ADAPTADOR → API → WEB → USUARIO
```

Hoy llega hasta `DATASET → CHRONICLES`, y ahora además sabe **qué** eventos
hay. Las tres capas siguientes no existen y la Web no muestra nada.

**Motivo: presupuesto de ejecución agotado.** No es un bloqueo de diseño: el
inventario que hacía falta ya está, y lo que sigue es trabajo mecánico.

---

## Siguiente paso, en orden

1. **Implementar la conversión** de los tipos verificados → eventos Chronicles,
   empezando por `hf died` → `DEATH`, que tiene evidencia completa.
2. **Conectar a `servicio_consulta`** reutilizando envelopes, paginación y
   certeza existentes.
3. **Adaptador + endpoints API**, con la prueba `mutación del servicio → test
   API falla` que ya sostiene el resto del sistema.
4. **Vistas Web**: fortaleza, personajes, eventos, línea temporal.
5. **Mutation testing del motor**.

Ninguno requiere IA. El inventario es precisamente lo que faltaba para no
construir sobre suposiciones.
