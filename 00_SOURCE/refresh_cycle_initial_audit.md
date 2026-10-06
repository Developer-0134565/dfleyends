# DF Legends · Auditoría del ciclo de refresco

Auditoría **ejecutada antes de modificar nada**. Todas las cifras proceden de
lectura de código y de una medición real con un servidor HTTP en marcha.

---

## 1. Cómo funcionan hoy las cosas

```
Dwarf Fortress
      ↓  (export manual)
00_SOURCE/original_data/legends*.xml
      ↓
actualizar_datos.py  → staging → validación → activación (backup + rename)
      ↓
00_SOURCE/processed/merged/*.jsonl   ← el "dataset activo"
      ↓
nucleo.Archivo()   lee TODOS los JSONL al construirse  (~2,6 s)
      ↓
servicio._ARCHIVO  ← caché de UN SOLO proceso, para siempre
      ↓
api.crear_servidor()  sirve HTTP
```

| Fichero | Qué decide |
|---|---|
| `00_SOURCE/tools/actualizar_datos.py` | Cómo se genera, valida y activa un dataset |
| `dfchron/servicio.py` | **Cuándo se lee el disco**: `obtener_archivo()` con `_ARCHIVO` global |
| `dfchron/api.py` | Cómo se sirve; no toca el ciclo de vida del dataset |
| `00_SOURCE/tools/nucleo.py` | Cómo se leen los JSONL (en `Archivo.__init__`) |

## 2. Cuándo se cargan los JSONL

**Una sola vez**, en `nucleo.Archivo.__init__`, que lee de golpe figuras,
entidades, sitios, eventos, artefactos, relaciones y las cuatro capas
geográficas. Después construye sus índices en memoria.

Ese objeto mide ~2,6 s de carga y ocupa cientos de MiB. Es exactamente por eso
que existe la caché: reconstruirlo en cada petición sería inasumible.

## 3. La caché y su sincronización

`dfchron/servicio.py`:

```python
_ARCHIVO = None
_CANDADO = threading.Lock()

def obtener_archivo():
    global _ARCHIVO
    if _ARCHIVO is None:
        with _CANDADO:
            if _ARCHIVO is None:
                _ARCHIVO = Archivo()
    return _ARCHIVO
```

Doble cerrojo con comprobación: seguro para varios hilos a la vez. Correcto
para lo que hace — y **sin ninguna vía de invalidación**. No hay `mtime`, ni
hash, ni nada que vuelva a mirar el disco.

## 4. Medición real: ¿detecta la API un cambio?

Medido con un servidor HTTP real y dos datasets sintéticos (A: 5 figuras /
3 sitios; B: 9 figuras / 7 sitios), cambiando la ruta de lectura **con el
servidor en marcha**:

| Momento | Resultado |
|---|---|
| 1. API arrancada con A | `figuras=5 sitios=3`, nombres `figura-A-*` |
| 2. El disco pasa a B | — |
| 3. Petición **sin reiniciar** | **`figuras=5 sitios=3`, nombres `figura-A-*`** |
| 4. Se reconstruye `Archivo` | `figuras=9 sitios=7`, nombres `figura-B-*` |

**La API NO detecta el cambio.** Sigue sirviendo A indefinidamente mientras el
proceso viva. Solo al construir un `Archivo` nuevo se ve B.

> Detalle técnico encontrado durante la medición: `cargar_jsonl()` tiene
> `carpeta=MERGED` como valor por defecto, ligado al **definir** la función.
> Redirigir la constante del módulo NO cambia el comportamiento. Es una nota
> sobre el acoplamiento, no un defecto.

## 5. Qué ocurre al reiniciar

Correcto y sin sorpresas: `run.py` llama a `svc.obtener_archivo()` al arrancar,
cargando el dataset que haya en ese momento. **Reiniciar = ver lo nuevo.**

## 6. Mecanismo actual para saber qué dataset está activo

Existe `00_SOURCE/dataset_version.json`, escrito por `actualizar_datos.py`, y se
consulta con `python run.py --estado`.

**Lo que le falta:** ningún identificador estable. Tiene `actualizada` (fecha),
SHA-256 de las salidas, conteos y la ruta del backup anterior, pero **no hay
ningún campo `dataset_id`**.

Consecuencia: comparar "qué dataset sirve la API" exige hoy comparar hashes a
mano. La Web **no tiene ninguna forma** de saberlo.

## 7. Estado del endpoint de salud

`/api/salud` existe: estado, eventos, figuras, `ruta_datos` y límite máximo.
**No dice nada del dataset**: ni su id, ni cuándo se generó.

---

## 8. Opción A (reinicio) frente a Opción B (recarga)

| Criterio | Opción A · reinicio | Opción B · recarga en caliente |
|---|---|---|
| Complejidad | **Ninguna**: ya funciona | Media: bloqueo, rollback, concurrencia |
| Riesgo de API a medias | **Nulo**: o hay proceso viejo o nuevo | **Real**: hay ventana en la que se sirve |
| Coste | Cerrar y abrir | Recargar (2,6 s) |
| ¿Sirve datos mezclados? | **Imposible**: procesos distintos | Posible sin bloqueo explícito |
| Recuperación ante fallo | **Automática**: el viejo sigue sirviendo | Hay que reimplementar "conservar el anterior" |
| Robustez | **Máxima** por construcción | Hay que construirlo y probarlo |

### Decisión: **Opción A, con identificador de dataset**

1. **La Opción B es un problema que aún no tenemos.** El ciclo es manual: el
   usuario está delante, reinicia y sigue. Aporta menos de lo que cuesta.
2. **La Opción A hace imposible mezclar datasets por construcción**: dos
   procesos nunca comparten memoria. La B necesita bloquear peticiones para
   lograr lo mismo, y entonces ya es un reinicio en memoria.
3. **Si mañana hace falta la recarga**, el diseño preparado (id de dataset +
   carga bajo cerrojo + conservar el anterior) la hace trivial de añadir.
## 9. Lo que hay que construir

| # | Hueco | Solución |
|---|---|---|
| 1 | `dataset_version.json` sin identificador estable | Derivar un `dataset_id` de las huellas del dataset |
| 2 | `/api/salud` no dice qué dataset sirve | Exponer `dataset_id` y fecha de generación |
| 3 | La Web no puede detectar cambio | Consultar el estado y avisar si cambia |
| 4 | El mensaje tras actualizar es ambiguo | `--actualizar` dice explícitamente qué hacer |

**No** se implementa: polling continuo, vigilancia de archivos, recarga en
caliente, autenticación, ni nada que convierta el snapshot en tiempo real.

## 10. Decisión de diseño: cómo se calcula el `dataset_id`

**No se escribe un id "a mano" ni se usa un reloj.** Se **deriva** de la
huella del contenido, que es lo único que realmente distingue un dataset de
otro:

```
dataset_id = "v1-" + sha256( JSON ordenado de {fichero: sha256} )  [:16]
```

| Propiedad | Por qué importa |
|---|---|
| Determinista | El mismo contenido da siempre el mismo id |
| Cambia si cambia un byte | Un dataset distinto tiene id distinto |
| No inventa datos | Sale de los SHA-256 **reales** de `dataset_version.json` |
| Comparable | `dataset A != dataset B` se decide con una comparación de cadenas |

Un campo de reloj no sirve: dos ejecuciones sobre el mismo contenido darían ids
distintos y el aviso de "hay un mundo nuevo" saltaría sin motivo.

El `dataset_id` se escribe en `dataset_version.json` al activar, y la API lo
lee **del disco en cada petición a `/api/salud`** — así que refleja el disco,
no lo que tiene en memoria. La Web lo usa para detectar el cambio.

## 11. La decisión de fondo: "snapshot", no "tiempo real"

DF Legends actualiza por **snapshot del mundo**, no por tick:

```
PARTIDA
   ↓  GUARDAR / EXPORTAR        ← lo hace Dwarf Fortress, manualmente
   ↓  EXTRACCIÓN MANUAL         ← una vez, no en cada tick
   ↓  VALIDACIÓN
   ↓  ACTIVACIÓN (backup + rename)
   ↓  REINICIO DE LA API        ← explícito, consciente
   ↓  WEB
```

Lo que **no** ocurre, por diseño:

| No | Motivo |
|---|---|
| Actualización por tick | Una partida genera cambios masivos; sería inútil |
| Vigilancia continua del XML | La API solo mira el disco cuando se le pregunta el estado |
| Recarga automática al vuelo | Riesgo de servir datos mezclados sin necesidad |
| Extracción automática | La decisión de exportar es del jugador |

La Web comprueba el `dataset_id` **al cargar la aplicación** y **al volver a la
pestaña**, no cada segundo.