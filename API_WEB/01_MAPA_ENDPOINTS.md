# API/WEB — MAPA DE ENDPOINTS Y CLASIFICACIÓN DE LA FRONTERA

> **Cómo se produjo este mapa.** No está escrito a mano: lo genera
> `API_WEB/auditar_frontera.py`, que recorre `api.R.rutas` en ejecución, lee el
> **código** del manejador de cada ruta (desenvuelto del closure de `_peticion`)
> y determina a quién llama de verdad.
>
> Esto importa: comparar *resultados* no probaría nada, porque un bypass puede
> devolver exactamente lo mismo. Leer a quién llama el manejador sí.
>
> ```
> python API_WEB/auditar_frontera.py --json API_WEB/mapa_frontera.json
> ```
>
> Artefactos: `mapa_frontera.json` (datos), `mapa_frontera.txt` (salida).

---

## 1. El criterio

El criterio es **semántico**, no «devuelve JSON»:

> ¿El endpoint está proporcionandom **hechos** derivados del conocimiento del
> dataset?

| Tipo | Significado | ¿Gana algo con la frontera? |
|---|---|---|
| **consulta** | Afirma algo sobre una entidad o un conjunto concreto. La afirmación necesita `identity`, `evidence` y `dataset_id`. | **Sí** |
| **navegación** | Devuelve un subconjunto para orientarse. «No aparece en esta búsqueda» **no es un hecho**. | No |
| **estadísticas** | Cuenta agregada. No afirma nada sobre una entidad concreta. | No |
| **metadatos** | Describe el dataset, el contrato o el vocabulario. Declara; no afirma. | No |
| **salud** | Estado del **servicio** (carga, disponibilidad). No es conocimiento. | No |
| **exportación** | Vuelca a disco. Es un consumidor de salida, no una consulta. | No |

**Por qué la navegación se queda fuera, y no es pereza.** Un endpoint de
listado devuelve filas sin evidencia individual: no puede decir «esta figura
consta en el dataset» porque solo sabe que está en un índice. Meterlo en la
frontera obligaría a fabricar una evidencia por fila que no significa nada, o a
declararla ausente, que es peor. Migrarlo no aportaría nada y costaría un
`dataset_id` por elemento.

---

## 2. El perímetro: 13 de 51

| Métrica | Valor |
|---|---:|
| Rutas registradas | **51** |
| Deben pasar por la frontera determinista | **13** |
| **Pasan efectivamente por el adaptador** | **13** |
| Discrepancia | **0** |

> La ausencia de discrepancia es el resultado arquitectónico: *ninguna* ruta que
> necesite la frontera la salta, y *ninguna* ruta que no la necesite la usa.
> Ambas mitades importan igual; una frontera usada de más también es un defecto.

### 2.1 Las 13 rutas del perímetro

| Endpoint | Delega en | Operación del servicio |
|---|---|---|
| `/api/figuras/{id}` | `ac.ficha_figura` | `obtener_entidad('figura', id)` |
| `/api/entidades/{id}` | `ac.ficha_entidad` | `obtener_entidad('entidad', id)` |
| `/api/sitios/{id}` | `ac.ficha_sitio` | `obtener_entidad('sitio', id)` |
| `/api/artefactos/{id}` | `ac.ficha_artefacto` | `obtener_entidad('artefacto', id)` |
| `/api/eventos/{id}` | `ac.ficha_evento` | `obtener_entidad('evento', id)` |
| `/api/figuras/{id}/relaciones` | `ac.relaciones_figura` | `buscar_relaciones(id)` |
| `/api/consulta/contrato` | `ac.contrato` | `contrato()` |
| `/api/consulta/entidad/{tipo}/{id}` | `ac.entidad` | `obtener_entidad(tipo, id)` |
| `/api/consulta/atributo/{tipo}/{id}/{atributo}` | `ac.atributo` | `obtener_atributo(...)` |
| `/api/consulta/relaciones/{id}` | `ac.relaciones` | `buscar_relaciones(id)` |
| `/api/consulta/contar/{tipo}` | `ac.contar` | `contar(tipo, filtro)` |
| `/api/consulta/verificar` | `ac.verificar` | `verificar(...)` |
| `/api/consulta/evidencia/{tipo}/{id}` | `ac.evidencia` | `obtener_evidencia(...)` |

**Las 6 fichas** ya existían con clientes. No se les cambió el envelope: se les
**añadieron** `estado`, `identity`, `evidence`, `dataset_id` y `alcance`. Un
cliente antiguo sigue funcionando; uno nuevo lee más.

**Las 7 rutas `/api/consulta/*`** son nuevas. Antes `/api/consulta/...` daba 404.

### 2.2 Compatibilidad: dos vías de una migración

La unificación se hizo **de dos formas a la vez** (`ARCHITECTURE_DECISIONS.md`
D18), porque una sola habría roto consumidores:

1. **Enriquecimiento** — las fichas viejas se enriquecen sin cambiar su envelope.
2. **Superficie nueva** — `/api/consulta/*` expone el contrato explícito.

Así la compatibilidad no depende de que alguien lea bien un documento.
