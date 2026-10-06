# Referencia de consultas · DF-Chronicles

API del módulo `00_SOURCE/tools/nucleo.py`. Solo biblioteca estándar.

```python
import sys
sys.path.insert(0, r"C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE\tools")
from nucleo import Archivo
a = Archivo()
```

Todos los métodos devuelven `dict` con la clave `certainty`
(`FACT`, `DERIVED` o `UNKNOWN`). Los IDs de Dwarf Fortress son **cadenas**.

---

## Fichas

### `ficha_figura(df_id, breve=False)`
Figura histórica completa: nombre, raza, casta, sexo, fechas, entidad, sitio,
identidad, acontecimientos, cronología, artefactos, relaciones sociales,
conflictos registrados y fuentes.

```python
a.ficha_figura("712")
# {'df_id': '712', 'nombre': 'galka shafttop the blades of knighting',
#  'race': 'MINOTAUR', 'caste': 'FEMALE',
#  'entidad': {'df_id': 312, 'nombre': 'the infamous disloyalty',
#              'tipo': 'civilization'},
#  'acontecimientos': [... 158 ...], 'certainty': 'FACT', ...}
```

`breve=True` omite acontecimientos, cronología y relaciones (más rápido, útil
para listados de búsqueda).

### `ficha_entidad(df_id, breve=False)`
Nombre, tipo, race, figuras, sitios, acontecimientos, artefactos, cronología.

### `ficha_sitio(df_id, breve=False)`
Nombre, **tipo real del XML** (`fortress`, `town`…), coordenadas, civilización,
propietario, figuras, eventos, artefactos y construcciones en su coordenada.

> `tipo` conserva el tipo de Dwarf Fortress. `tipo_registro` indica la clase de
> registro (`site`).

### `ficha_artefacto(df_id, breve=False)`
Nombre, tipo, material, propietario, creador, sitios, acontecimientos.

---

## Consultas por ID

| Método | Devuelve |
|---|---|
| `eventos_de_figura(df_id, limite=None, con_total=False)` | Acontecimientos de una figura, ordenados. `con_total=True` añade `items`/`total`/`devueltos`/`truncado` |
| `miembros_entidad(df_id)` | Figuras que pertenecen a la entidad |
| `sitios_de_entidad(df_id)` | Sitios de la entidad |
| `eventos_de_sitio(df_id, limite=None, con_total=False)` | Acontecimientos del sitio (igual que `eventos_de_figura`) |
| `artefactos_de_figura(df_id)` | Artefactos con esa persona como `holder_hfid` |
| `artefactos_de_entidad(df_id)` | Artefactos en sitios de la entidad (**DERIVED**) |
| `propietarios_artefacto(df_id)` | Propietario declarado + nº de eventos que lo mencionan |
| `identidad_de_figura(df_id)` | Identidad de `legends_plus` o `UNKNOWN` |
| `nombre_de(tipo, did)` | Resuelve el nombre de un `df_id` en un tipo (`"historical_figures"`, `"entities"`, `"sites"`, `"artifacts"`). Devuelve `UNKNOWN` si no existe. Es la función que usan las fichas para poner nombres legibles a los identificadores. |

---

## Cronología

| Método | Devuelve |
|---|---|
| `eventos_del_anio(anio)` | Eventos de un año. Fuera de 1–100 → `UNKNOWN`. Índice por año: O(año) |
| `eventos_entre_anios(anio_a, anio_b, limite=None)` | Eventos en el rango, ordenados por (año, segundos72) |
| `cronologia_figura(df_id, limite=None)` | Línea temporal de una figura |
| `cronologia_entidad(df_id, limite=None)` | Línea temporal de una entidad |
| `cronologia_sitio(df_id, limite=None)` | Línea temporal de un sitio |

Ordenación: `año` y, dentro de él, `seconds72`. El rango de los datos es
**1–100**; fuera de él se devuelve `UNKNOWN`, nunca una fecha inventada.

```python
a.eventos_entre_anios(20, 30)['total']      # 2747
a.eventos_del_anio(500)['certainty']        # 'UNKNOWN'
```

---

## Relaciones sociales

| Método | Tipo XML |
|---|---|
| `relaciones_de_figura(df_id, tipo=None, limite=None)` | Cualquiera |
| `amigos(df_id)` | `childhood_friend` |
| `amantes(df_id)` | `lover` |
| `exparejas(df_id)` | `former_lover` |
| `companeros_de_guerra(df_id)` | `war_buddy` |
| `obsesiones(df_id)` | `jealous_obsession` |
---

## Eventos

| Método | Devuelve |
|---|---|
| `participantes_evento(df_id)` | Figura principal, objetivo, grupo 1 y 2, entidad, sitio |
| `relaciones_adicionales_evento(df_id)` | Relaciones de plus que citan el evento (vacío) |

---

## Búsqueda

Normaliza el texto (minúsculas, sin acentos ni signos) y busca por token
exacto o por prefijo.

| Método | Ámbito |
|---|---|
| `buscar(texto, tipo=None, limite=50)` | Todas las categorías |
| `buscar_figura(texto, limite=20)` | Figuras |
| `buscar_entidad(texto, limite=20)` | Entidades |
| `buscar_sitio(texto, limite=20)` | Sitios |
| `buscar_artefacto(texto, limite=20)` | Artefactos |
| `buscar_evento(texto, limite=20)` | Eventos (por `type`) |

Todos devuelven `consulta_ambigua: bool`. **Con varias coincidencias el sistema
no elige**: devuelve la lista completa y quien pregunta decide.

```python
r = a.buscar_figura("razor")
r['ids']                 # ['3154']
r['consulta_ambigua']    # False
r['total_encontrados']   # 1  <- cuántos hay en realidad
r['devueltos']           # 1
r['truncado']            # False

r = a.buscar_figura("the")
r['consulta_ambigua']    # True  (miles de coincidencias)
r['total_encontrados']   # 262
r['devueltos']           # 20  (límite por defecto)
r['truncado']            # True
```

> **Fase 4:** se añadieron `total_encontrados`, `devueltos`, `truncado` y
> `limite`. Antes, una búsqueda truncada no revelaba cuántos resultados había.

---

## Conflictos (DERIVED)

| Método | Devuelve |
|---|---|
| `conflictos(limite_eventos=6000, solo_documentados=True)` | Eventos `hf simple battle event` con grupos enfrentados. `solo_documentados` está previsto para un uso futuro y hoy no altera el resultado. |
| `muertes_por_conflicto()` | Eventos `hf died` con causa violenta |

**Regla explícita:** `type == 'hf simple battle event'` y
`subtype ∈ {attacked, ambushed, confront, surprised, scuffle, got into a brawl,
corner, happen upon}`. El resultado es `DERIVED` e incluye la advertencia
`"NO demuestra guerras"`. El sistema **no crea guerras**.

```python
c = a.conflictos()                      # sin truncar (5.478 < 6.000)
c['eventos_de_enfrentamiento']          # 5478  <- TOTAL real, no lo devuelto
c['eventos_devueltos']                  # 5478
c['truncado']                           # False
c['por_subtipo']                        # recuento de lo devuelto
c['por_subtipo_total']                  # recuento del conjunto completo
c['trazabilidad']                       # cada evento conserva id, año, sitio y grupos

c = a.conflictos(limite_eventos=100)
c['eventos_de_enfrentamiento']          # 5478  <- sigue siendo el total
c['eventos_devueltos']                  # 100
c['truncado']                           # True
```

> **Fase 4:** `eventos_de_enfrentamiento` antes devolvía `len(filas)`, es decir
> el número **recogido**, no el total. Con `limite_eventos=100` reportaba 100
> eventos de enfrentamiento cuando hay 5.478: un parcial presentado como
> total. Ahora `total_real` y `truncado` lo hacen explícito.

Cada elemento de `eventos` incluye `evento_id`, `anio`, `sitio_id`,
`grupo_1_id`, `grupo_2_id` y `fuente`, de modo que **toda agrupación es
reconstruible evento a evento**.

---

## Geografía

| Método | Devuelve |
|---|---|
| `geografia()` | Recuentos de ríos, masas, picos y construcciones |
| `construir_en_coordenada(x, y)` | Construcciones cuya ruta pasa por esa coordenada (**DERIVED**) |

---

## Exportación

| Método | Formato |
|---|---|
| `exportar_json(datos, titulo, ruta=None)` | JSON con `fuentes` |
| `exportar_markdown(datos, titulo, ruta=None)` | Markdown estructurado |
| `exportar_historia_figura(df_id, formato, ruta)` | Atajo: `"json"` o `"markdown"` |

Toda exportación incluye `fuentes` y el aviso de que `UNKNOWN` significa que
el dato no consta.

---

## Casos sin datos

Ante un ID inexistente el sistema **no inventa**: devuelve
`{'certainty': 'UNKNOWN', 'motivo': 'no existe esa figura'}`.

```python
a.ficha_figura("99999999")['certainty']   # 'UNKNOWN'
a.buscar("")['certainty']                 # 'UNKNOWN'
a.eventos_del_anio(500)['certainty']      # 'UNKNOWN'
```

### Tipos inválidos (auditoría Extra)

Ningún tipo incorrecto lanza una excepción. La coerción es explícita:

| Entrada | Resultado |
|---|---|
| `eventos_del_anio('5')` | **FACT**, año 5 (cadena numérica válida) |
| `eventos_del_anio('abc')` | UNKNOWN, «el año no es un número entero válido» |
| `eventos_del_anio(None)` | UNKNOWN |
| `eventos_del_anio(3.5)` | UNKNOWN |
| `eventos_entre_anios('a', 5)` | UNKNOWN |
| `ficha_figura(712)` | FACT (int válido, se normaliza a `'712'`) |
| `ficha_figura(None)` | UNKNOWN |
| `eventos_entre_anios(30, 20)` | Se normaliza a 20–30 |

### Fechas de nacimiento y muerte (auditoría Extra)

`nacimiento` y `muerte` llevan `certainty` explícita:

```python
f = a.ficha_figura("0")     # figura sin death_year
f['muerte']
# {'año': None, 'segundos72': None, 'certainty': 'UNKNOWN',
#  'motivo': 'el XML no registra esta fecha. NO significa que la figura
#             siga viva ni que muriera fuera del rango de los datos.',
#  'interpretacion_prohibida': ['sigue viva',
#                               'murió después del año 100',
#                               'murió en una fecha desconocida pero anterior']}
```

**6.734 de 11.144 figuras no tienen `death_year` registrado.** Un campo ausente
**no significa** que la figura siga viva: significa que el dato no consta.

### Colecciones vacías (auditoría Extra)

`0` significa «no constan», no «ocurrieron cero»:

```python
s = a.ficha_sitio("482")   # sitio sin eventos registrados
s['eventos']                 # 0
s['certainty_eventos']       # 'UNKNOWN'
s['nota_eventos']            # '... NO significa que no ocurriera ninguno'
```

---

## Referencias cruzadas

```
FIGURA ──entity_link.entity_id──> ENTIDAD ──civ_id──> EVENTO ──site_id──> SITIO
   │                                                                    ▲
   └──────────────── hf_link / site_link ───────────────────────────────┘
ARTEFACTO ──holder_hfid──> FIGURA      ARTEFACTO ──site_id──> SITIO
FIGURA <──source_hf/target_hf──> FIGURA   (13.192 relaciones, sin evento)
```
| `tipos_relacion_disponibles()` | Los 12 tipos con su recuento |

Cada relación incluye `evento_id` y `evento_existe`. **Siempre es `False`**:
los eventos que citan no existen en `historical_events` y no se asocian.