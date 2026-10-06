# P1.4 — ARQUITECTURA FUTURA PROPUESTA (Fase H)

> **Propuesta, NO implementada.** La misión termina en JSONL. No se conecta
> nada a la API ni a la Web.

---

## 1. Los cinco conceptos que NO deben confundirse

P1.3 cerró sin poder demostrar una identidad de estado. Esta arquitectura **no
la recupera por la puerta de atrás**:

| Concepto | Qué es | Qué NO es |
|---|---|---|
| **Identidad del mundo** | `world_folder` (`region1`) + nombre. Qué partida se observa | Un reloj, un estado, una versión |
| **Sesión del observador** | El proceso que observa. Nace y muere | La partida |
| **Secuencia de observaciones** | `observation_id`: contador monotónico de líneas | Identidad del mundo |
| **Tiempo de captura** | `observed_at`: reloj real de mi máquina (UTC) | Tiempo interno del juego |
| **Tiempo interno del juego** | `game_tick`, año/mes/día | Tiempo real |
| **Frescura** | Cuánto lleva sin actualizarse | Una versión |

> **La regla que lo impide:** no existe ningún campo que afirme «esto es el
> estado del mundo». El observador registra **lo que ha visto y cuándo lo ha
> visto**, y nada más. Si mañana el juego cambiara dos veces entre dos
> observaciones, el JSONL no lo detectaría — y **no debe detectarlo**, porque no
> se ha demostrado que pueda.

---

## 2. Arquitectura propuesta

```text
          Dwarf Fortress (pausado o en marcha)
                      │
              DFHack  ──► script observador (Lua, solo lectura)
                      │
                      ▼
            JSONL  (una línea = una observación)
                      │
                      ▼
         ⛔ ESTE ES EL FIN DE LA MISIÓN
```

**Comunicación:** `dfhack-run lua "dofile(observador.lua)"`, invocado desde
cualquier proceso externo. Se demostró que funciona y que **no exige escribir
nada** en la instalación del juego.

**Dónde escribe:** una carpeta aislada, **una línea por mundo observado**:

```
observados/<world_folder>/observaciones-YYYYMMDD.jsonl
```

El directorio por `world_folder` es la **respuesta directa** al requisito de no
mezclar mundos: dos mundos distintos nunca comparten fichero.

---

## 3. Las diez preguntas

| # | Pregunta | Respuesta |
|---:|---|---|
| 1 | ¿Cómo se ejecuta automáticamente? | `dfhack-run lua dofile(...)` desde un planificador externo. **No** un timer dentro del juego: menos superficie, más aislamiento |
| 2 | ¿Cómo se comunica con DF-Chronicles? | **Todavía no.** Dejar los ficheros. El observador no conoce DF-Chronicles |
| 3 | ¿Dónde escribe los JSONL? | Carpeta aislada por `world_folder` |
| 4 | ¿Cómo identifica el mundo? | `ReadWorldFolder()` + `world_data.name`. Lo que **ya existe**, no un identificador inventado |
| 5 | ¿Cómo evita mezclar observaciones? | Un directorio por mundo + `subject.id = world_folder` en cada línea |
| 6 | ¿Cómo detecta obsolescencia? | Por **tiempo transcurrido**: `ahora - observed_at`. **No** por comparación de estado, porque no existe identidad de estado |
| 7 | ¿Cómo maneja un cierre inesperado? | El JSONL se añade línea a línea: o no se escribe, o se escribe una línea completa. No hay estado parcial que reparar |
| 8 | ¿Cómo amplía el catálogo? | Añadir bloques a `hechos[]` en el observador. Cada hecho nuevo debe declarar su `visibility` **o no entra** |
| 9 | ¿Cómo garantiza el perímetro? | Cada hecho lleva su clasificación **obligatoria**. `validar_jsonl.py` rechaza cualquier hecho sin visibilidad válida y separa los `NO_VISIBLE` |
| 10 | ¿Cómo se conecta a la frontera API/Web? | **No se conecta.** Cuando se haga, será un consumidor más del mismo patrón: el JSONL entra como `source` nuevo, y la frontera decide. **La IA futura no tendrá ninguna vía especial** |

---

## 4. Ampliación del catálogo — el filtro que protege el perímetro

Añadir un dato nuevo **no** es añadir una línea. Es añadir:

1. La llamada de solo lectura.
2. Una **clasificación de visibilidad justificada**.
3. Una prueba de que la extracción no altera nada.

Si un dato no puede clasificarse con honestidad, se registra como `UNKNOWN` y
queda fuera. La ausencia de pruebas no autoriza a incluirlo.

---

## 5. Orden sugerido de avance

| Paso | Qué | Por qué primero |
|---:|---|---|
| 1 | Tabla CP437→UTF-8 completa | Sin ella, **la mitad** de los nombres de la partida no son utilizables |
| 2 | `exit_code` fiable en el observador | Hoy aborta con `exit=0`: un fallo silencioso en producción |
| 3 | Script de comparación con la interfaz | Cerrar la últimaLaguna de validación manual |
| 4 | Segundo fichero de salida por mundo | Materializar la separación de mundos |
| 5 | Sondeo periódico + medir con el juego en marcha | Requiere autorización |

Los pasos 1–4 **no necesitan** autorización: no tocan la partida.