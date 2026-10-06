# P1.4 — LIMITACIONES Y DEUDAS

> Lo que **no** se ha hecho, lo que **no** se ha medido, y lo que **no** se ha
> demostrado. Nada de esto se disimula.

---

## 1. Deuda técnica

| # | Deuda | Impacto | Por qué no se corrigió |
|---|---|---|---|
| D-1 | **Falta la tabla CP437→UTF-8** | **La mitad** de los nombres de la partida (7 de 14) no son utilizables | Deliberado: una tabla parcial corromperia en silencio. Se marca `__NO_UTF8_PENDIENTE` en su lugar |
| D-2 | El observador devuelve `exit=0` al abortar | Un llamador que se fie del código de salida **no detectaría un fallo** | `dfhack-run` no propaga el estado del script. Workaround: hoy solo se lee el mensaje |
| D-3 | El contador `observation_id` cuenta líneas del fichero | Si alguien trunca el fichero, la numeración **se reinicia** y puede repetirse | Aceptable en el prototipo. En producción: contador persistente o UUID |
| D-4 | Sin `dataset_id` de la partida | No se puede ligar una observación al contenido extraído | Fuera del alcance. P1.2 ya.Full |

## 2. Lo que NO se ha medido

| Cosa | Por qué |
|---|---|
| Comportamiento con la partida **en marcha** | Requiere pausar/despausar → **necesita tu autorización** |
| CPU atribuible al script | Exigiría instrumentación invasiva del proceso |
| Coste de la conversión CP437 pendiente | No existe todavía la conversión |
| Frecuencia sostenible con carga | No se ha medido bajo condiciones de carga |

## 3. Lo que NO se ha investigated

| Categoría | Estado | Nota |
|---|---|---|
| Notificaciones, muertes, nacimientos, llegadas, combates (B5) | `UNKNOWN` | `eventful` es el mecanismo candidato y **está presente** |
| Salud, heridas, pensamientos, relaciones, inventario individuales (B6) | `UNKNOWN` | No explorado |
| Animales, visitantes, migrantes | `UNKNOWN` | `isVisitor()` / `isPet()` existen y son solo lectura |

> **`UNKNOWN` no es `NO_VISIBLE`.** No explorarlo **no** autoriza a incluirlo,
> pero tampoco demuestra que sea invisible. Queda pendiente, no descartado.

## 4. Lo que NO se ha validado

| Prueba | Estado |
|---|---|
| **Correspondencia visual con la interfaz** | **Pendiente de verificación humana.** Los valores salen de APIs cuya semántica es conocida, pero **no he visto la pantalla**: no puedo afirmar que el «5 de mes» sea el que tú ves. Puedes comprobarlo en un segundo |
| Guardado y carga de la partida (E4) | **No realizado.** Requeriría guardar/cargar la partida del usuario |
| Despausar y volver a pausar (E3) | **No realizado.** Requiere tu autorización |
| Comportamiento ante cierre del juego | Parcial: probado el fallo de escritura y DFHack inalcanzable; no probado el cierre real |

## 5. Riesgo residual

| Riesgo | Estado |
|---|---|
| El observador altera la partida | **Descartado por medición**: 4 ejecuciones, tick constante |
| Escritura en la instalación de DF | **Ninguna**: `dofile` lo evita por completo |
| Mezcla de mundos | **Prevenida** por diseño (`world_folder`), pero **no probada** con dos mundos reales |
| Datos inventados | **Imposible** por construcción: `segura()` devuelve `nil` explícito, nunca un valor inventado |

## 6. Lo que esta misión **no** autoriza

- No integrar el observador en la API ni en la Web.
- No modificar el contrato pre-LLM ni ningún fichero congelado.
- No conectar ningún modelo.
- No introducir identidad de estado por la puerta de atrás (P1.3 la cerró).