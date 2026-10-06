# API/WEB — MUTACIONES INTRODUCIDAS Y DETECTADAS

> Harness **permanente**: `dfchron/pruebas/probar_mutation_frontera.py`
> No es un script temporal. Vive en el repositorio y se ejecuta en la regresión.
>
> ```
> python dfchron\pruebas\probar_mutation_frontera.py
> ```
>
> Cada mutación corre las 4 suites en **procesos separados**. Si corrieran en el
> mismo proceso, el módulo ya importado seguiría con el código viejo y la
> mutación no probaría nada.

---

## Resumen

| Métrica | Valor |
|---|---:|
| Mutaciones introducidas | **9** |
| Mutaciones detectadas | **9** |
| **Mutaciones supervivientes** | **0** |
| Suites que deben detectar | 4 |
| Ficheros de producción mutados | 4 |

**Categorías exigidas por la misión: 8. Cubiertas: 8.**

---

## Las nueve mutaciones

| ID | Qué cambia | Por qué debería romper | Resultado | Test que la detecta |
|---|---|---|---|---|
| **A** | `dataset_id` anuncia otro mundo | La API miente sobre de qué dataset viene el dato | **detectada** | integración |
| **B** | La evidencia se borra | La procedencia desaparece sin avisar | **detectada** | integración |
| **C** | `NOT_VERIFIED` pasa a `FOUND` | Se convierte «no se puede determinar» en «es cierto» | **detectada** | integración |
| **D** | `buscar_relaciones` deja de delegar | La operación autorizada se sustituye por un literal | **detectada** | integración, api |
| **E** | El adaptador salta a `servicio.py` | `API → servicio → núcleo` en vez de `API → servicio_consulta → núcleo` | **detectada** | integración, api, web |
| **F** | `dataset_id` desaparece del sobre | El sobre deja de poder atribuir su contenido | **detectada** | integración |
| **G** | `state_version` declara otra versión | Toda la evidencia miente sobre su dataset de origen | **detectada** | integración |
| **H** | El adaptador lee el núcleo sin servicio | Se saltan **las dos** capas de golpe | **detectada** | integración, api, web |
| **I** | La API fabrica la respuesta | Datos correctos… sin haber preguntado a nadie | **detectada** | integración, api, web |

---

## Las tres que había que añadir (F, G, I)

El harness ya existía con 5. La misión exige 8 categorías y faltaban tres.

### F — `dataset_id` desaparece del sobre

```
base["dataset_id"] = ic.DATASET_ID      →      base["dataset_id"] = None
```

**A** falseaba el `dataset_id`; **F** lo elimina. Son cosas distintas: *mentir* y
*callar*. Una frontera que declara «no sé de qué dataset vengo» es distinta de
una que declara un dataset equivocado, y ambas deben romper algo. El envelope
sin `dataset_id` rompe la trazabilidad, pero la paginación seguiría
funcionando — por eso hace falta una prueba que lo exija.

### G — `state_version` declara otra versión

```
list(fuentes_xml) or None, state_version=DATASET_ID
                    ↓
list(fuentes_xml) or None, state_version="v1-otro-mundo"
```

La más importante de las tres. `state_version` **no** vive en
`servicio_consulta.py`: se inyecta en `ia_conocimiento.evidencia_de()`, que es
donde nace la procedencia. Una mutación en el servicio no la alcanzaría.

Ataca justo la propiedad que P1 demostró: la evidencia solo es actual si
**declara** versión **y** coincide. Con `state_version` falseado, una evidencia
de otro mundo pasaría por válida.

### I — la API fabrica la respuesta

```python
lambda p, q: ac.ficha_figura(p["id"])              # antes
lambda p, q: {"ok": True, "data": {"nombre": "Fabricado"},   # después
              "estado": "FOUND", "dataset_id": "v1-inventado"}
```

**La más silenciosa de todas.** Una prueba que compara «el JSON de la API» con
«el JSON del servicio» pasaría igual: aquí el dato se inventa pero la ruta sigue
respondiendo. Solo la detecta que la ruta **deje de llamar al adaptador**.

Es el motivo por el que el harness existe: **probar la ejecución real, no la
igualdad de valores**.

---

## E y H: dos bypass distintos

**E** hace que el adaptador llame a `servicio.figura()`. **H** hace que lea
`servicio.obtener_archivo().ficha_figura()` directamente.

Se probaron las dos porque «llamar al servicio en vez de a la capa de consulta»
y «leer el índice» no son el mismo fallo, aunque los dos salten la frontera. Las
dos se detectan.
---

## Modo de fallo conocido: interrupción del harness

> **El harness escribe sobre ficheros de producción. Si el proceso muere a
> mitad, el `finally` no se ejecuta y el fichero se queda mutado.**

Ocurrió durante esta misión (ver `00_DIARIO.md` E4). Una ejecución se canceló
por el límite de tiempo de la shell con una mutación aplicada, y
`servicio_consulta.py` quedó con `evidence = None`.

**Cómo se detectó.** Comparando el hash contra el baseline conocido. Ninguna
prueba falló: el sistema *funcionaba* con la evidencia rota.

**Cómo se restauró.** `API_WEB/restaurar_servicio.py`, que verifica que haya
exactamente una ocurrencia mutada, escribe en binario y **aborta si el hash
final no coincide**.

**Cómo se evita.** Ejecutar el harness **siempre en segundo plano**, nunca a
través de un comando con límite de tiempo. El harness verifica por hash que
restaura bien, pero no puede protegerse de que le maten.

> No es una crítica al diseño — el `finally` y la verificación por hash son lo
> correcto — sino una limitación real que conviene conocer antes de ejecutarlo
> en un entorno con límites de ejecución.

---

## Garantías del harness

| Garantía | Cómo |
|---|---|
| Guarda **bytes** originales, no una reserialización | `_bytes_originales` abre en `"rb"` |
| Restaura pase lo que pase | `finally:` |
| Verifica por **hash** que la restauración fue exacta | `assertEqual(sha256…)` |
| **Preserva CRLF/LF** | escritura binaria; una auditoría anterior rompió el hash al cambiar finales de línea |
| No deja **BOM** | comprobado explícitamente |
| No deja **temporales** | prueba que busca copias `.orig`/`.bak`/`_` |
| No prueba sobre ficheros inexistentes | comprobación explícita de existencia |
| Escribe en un **proceso limpio** por suite | `subprocess.run` por suite |

Verificadas tras la última ejecución:

```
servicio_consulta.py   0A5B6B1C3244E6192752F311B89D075E  (idéntico al baseline)
adaptador_consulta.py  C456256EC1C1D731D5DEE461F8035CC1  (idéntico al baseline)
api.py                 0426F63A632FD243CE0675DB6C857389  (idéntico al baseline)
ia_conocimiento.py     639548169FD86D42163BAC4FDBD208A1  (idéntico al baseline)
```