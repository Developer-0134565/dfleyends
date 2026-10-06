# DF Legends :: Sistema de actualización manual de datos

Procedimiento manual, controlado y reversible para regenerar los datos que
consume la API a partir de los XML de Legends.

**Estado: COMPLETADA CON LIMITACIONES** (ver §9).

---

## 1. Arquitectura encontrada

### 1.1 Lo que ya existía

```
original_data/legends.xml  (49 MB, cp437)
original_data/legends_plus.xml (18 MB, UTF-8)      SOLO LECTURA
        │
        │  cargar_legends.py  ─ autodetecta codificación, sanea en memoria
        ▼                    ─ nunca escribe en disco
integrar_legends.integrar() ─ fusión con procedencia por campo
        │
        ▼
processed/from_legends_xml/*.jsonl
processed/from_legends_plus/*.jsonl
processed/merged/*.jsonl  +  _manifiesto.json
        │
        │  nucleo.py → validar_semantica.Indice().cargar()
        ▼
dfchron/servicio.py: _ARCHIVO  (singleton por proceso)
        ▼
API HTTP en 127.0.0.1:877  +  web de DF Legends
```

### 1.2 Qué faltaba

No existía ninguna capa que coordinara las etapas. Concretamente faltaba:

1. **Comprobación de entradas**: nadie verificaba que los XML existen, se leen
   o no están vacíos antes de empezar.
2. **Generación aislada**: `integrar_legends.py` escribe **sobre** `processed/`
   mientras trabaja. Si falla a mitad, la versión válida queda destruida.
3. **Registro de versión**: no había fecha de generación ni hashes de entrada
   asociados a un dataset concreto.
4. **Respaldo y recuperación**: no existía forma de volver atrás.
5. **Verificación posterior**: nada comprobaba que lo activado fuera lo mismo
   que lo generado.

### 1.3 Piezas reutilizadas (no duplicadas)

| Pieza | Uso |
|---|---|
| `cargar_legends.py` | Lectura y detección de codificación |
| `integrar_legends.integrar()` | Fusión completa, sin modificar |
| `rutas.py` | Resolución de rutas por `DFCHRON_ROOT` |
| `nucleo.py` | Carga y consultas (para validar el staging) |
| **`verificar_reproducibilidad.py`** | **El patrón clave**: generar en un árbol temporal reasignando rutas de módulo |

El patrón de `verificar_reproducibilidad.py` se reutiliza tal cual: al copiar
`tools/` junto a `original_data/` en un directorio nuevo, `rutas.py` resuelve ese
directorio como raíz y **todo** el pipeline escribe dentro, sin tocar el dataset
real. Es *seguro por construcción*.

### 1.4 Reinicio de la API

`dfchron/servicio.py` guarda el `Archivo` en un singleton (`_ARCHIVO`) creado
en el primer uso. **La API no relee los JSONL en cada petición**, así que tras
activar datos nuevos hay que reiniciar `python run.py`.

Esto no es un defecto: leer 57.215 eventos cuesta ~2,5 s y hacerlo por petición
no es viable. Está documentado en la salida del comando.

---
## 2. Flujo implementado

`actualizar_datos.actualizar()` ejecuta **8 etapas**. Las etapas 1–5 **no tocan
la versión activa** en ningún momento.

| # | Etapa | Qué hace | Falla si… |
|---|---|---|---|
| 1 | **Entradas** | Comprueba que los 2 XML existen, se leen y no están vacíos. Calcula su **SHA-256** | falta alguno, está vacío o no se lee |
| 2 | **Staging** | Crea un árbol completo aislado en `work/staging-<sello>/`: `original_data/` (copias), `tools/` (copia) | no se puede escribir |
| 3 | **Extracción + integración** | Ejecuta `integrar_legends.integrar()` en **subproceso** dentro del staging | el XML no parsea, la raíz no es `df_world`, o la integración revienta |
| 4 | **Validación** | (a) Cada JSONL es JSON válido y no vacío. (b) El **núcleo real** carga el staging y responde | falta una sección mínima, hay JSON corrupto, o el núcleo no carga |
| 5 | **Manifiesto** | SHA-256 y nº de líneas de cada JSONL → `merged/_hashes.json`, y se verifica al momento | los hashes no cuadran |
| 6 | **Activación** | Mueve la versión actual a `backups/` y pone la nueva en su sitio | el movimiento falla (se revierte) |
| 7 | **Comprobación posterior** | Vuelve a hashear la versión **ya activa** y la compara con el manifiesto | no cuadra → **se revierte automáticamente** |
| 8 | **Registro** | Escribe `dataset_version.json`: fecha, hashes de entrada y de salida, conteos, resumen del merge, copia de seguridad | — |

En cualquier fallo de las etapas 1–5, el staging se borra y se imprime
`La version activa NO se ha modificado.`

### Detalle de seguridad

La generación va en **subproceso** (`subprocess.run`). Si la integración lanza
una excepción, el proceso principal sobrevive, puede limpiar y puede informar.
No queda un proceso a medias.

---
## 3. Comando para ejecutar la actualización

### Forma recomendada

```powershell
python run.py --estado      # ver qué datos hay ahora mismo
python run.py --actualizar  # actualizar los datos
python run.py --comprobar   # comprobar que la API funciona
```

### Forma completa (todas las opciones)

```powershell
python 00_SOURCE\tools\actualizar_datos.py estado
python 00_SOURCE\tools\actualizar_datos.py actualizar
python 00_SOURCE\tools\actualizar_datos.py actualizar --sin-activar
python 00_SOURCE\tools\actualizar_datos.py actualizar --originales D:\mi_partida
python 00_SOURCE\tools\actualizar_datos.py actualizar --dejar-staging
python 00_SOURCE\tools\actualizar_datos.py recuperar
python 00_SOURCE\tools\actualizar_datos.py recuperar --indice 1
python 00_SOURCE\tools\actualizar_datos.py historial
```

### Opciones

| Opción | Efecto |
|---|---|
| `--originales RUTA` | Usa otra carpeta de entrada (por ejemplo los XML recién extraídos de la partida) |
| `--sin-activar` | Genera y valida, pero **no** cambia la versión activa |
| `--dejar-staging` | No borra el staging al fallar, para depurar |
| `--indice N` | En `recuperar`: 0 = la copia más reciente |

Salida: **código 0** si todo fue bien, **1** si se canceló. El mensaje final es
inequívoco (`ACTUALIZACION CORRECTA` o `ACTUALIZACION CANCELADA`).

---
## 4. Directorios y archivos afectados

### Nuevos

| Ruta | Función |
|---|---|
| `00_SOURCE/tools/actualizar_datos.py` | La herramienta (≈870 líneas, solo biblioteca estándar) |
| `dfchron/pruebas/probar_actualizacion.py` | 43 pruebas de los 10 escenarios |
| `00_SOURCE/dataset_version.json` | Registro de la versión activa (lo crea el comando) |
| `00_SOURCE/work/` | Área de staging. Se vacía sola tras cada ejecución |
| `00_SOURCE/backups/merged-<sello>/` | Versiones anteriores. **No se borran** |
| `00_SOURCE/processed/merged/_hashes.json` | Manifiesto de hashes de salida |

### Modificados

| Fichero | Cambio |
|---|---|
| `run.py` | Añadidos `--estado` y `--actualizar` (delegan en la herramienta) |

### NO modificados

`nucleo.py`, `integrar_legends.py`, `cargar_legends.py`, `validar_semantica.py`,
`rutas.py`, `servicio.py`, `api.py`, `config.py`, la web de Astro, los XML
originales y los JSONL de datos.

**Los 17 JSONL de datos salen byte a byte idénticos** tras una actualización
(verificado: mismos SHA-256). Solo cambian tres ficheros que llevan metadatos de
generación: `_hashes.json` (nuevo), `_manifiesto.json` e
`indice_evento_relaciones.json` (llevan marcas de tiempo y orden de generación).

### Hook de pruebas

`DFCHRON_FALLO_EN=<etapa>` aborta en una etapa concreta. **Solo lo usa la suite de
pruebas**; no afecta al uso normal y no existe en ningún otro módulo.

---

## 5. Estrategia de protección y recuperación

### 5.1 Garantía central

> La versión activa **no se toca** hasta que la nueva ha generado, validado y
> tiene sus hashes comprobados.

Esto se consigue porque todo el trabajo ocurre en
`00_SOURCE/work/staging-<sello>/`, un árbol temporal completo. El dataset real
solo se ve alterado en la etapa 6, y para entonces ya todo está verificado.

### 5.2 Reglas de protección

| Regla | Cómo se cumple |
|---|---|
| Nunca modificar los XML | `registrar_original()` de `integrar_legends.py` nunca sobrescribe, y además opera sobre las **copias** del staging |
| No sobrescribir la versión válida mientras se genera | Se genera al revés: staging primero, `merged/` real al final |
| No dejar una actualización incompleta como activa | Las etapas 1–5 no escriben en `processed/`. Si fallan, no hay nada que limpiar |
| Si algo falla, conservar la anterior | Solo falla tras activar en la etapa 7, y ahí se **revierte** |
| No borrar copias anteriores | `backups/` solo crece. `recuperar()` aparta la versión sustituida en otro backup, así que **recuperar también es reversible** |
| Mantener los manifiestos | `_hashes.json` en `merged/` y `dataset_version.json` en la raíz |
| Registrar fecha y entradas | `dataset_version.json`: fecha con milisegundos + SHA-256 de cada XML de entrada |

### 5.3 Mecanismo de activación

```
1.  processed/merged        →  backups/merged-<sello>/     (rename)
2.  work/staging-*/merged   →  processed/merged            (rename)
3.  verificación de la versión activa
    si falla → se deshace el paso 2 y se restaura el backup
```

Los dos `rename` ocurren dentro del mismo volumen y son prácticamente
instantáneos. Aun así, si el proceso se matase **exactamente** entre ambos, la
versión anterior seguiría íntegra en `backups/` y bastaría con
`python run.py ... recuperar`.

No es preciso un sistema de versionado complejo: una copia de seguridad y una
sustitución controlada cumplen.

---
## 6. Resultado de cada escenario de prueba

**43/43 pruebas OK.** Todas usan XML diminutos en directorios temporales
(`tempfile.mkdtemp`). **Nunca tocan los datos reales**: además de trabajar en
temporales, cada prueba comprueba que el `processed/merged/` real conserva su
hash antes y después.

| # | Escenario | Pruebas | Resultado | Qué se demuestra |
|---|---|---|---|---|
| 1 | Actualización correcta | 8 | **OK** | Flujo completo, API carga lo nuevo, XML de entrada sin cambios, staging limpio |
| 2 | XML de entrada ausente | 3 | **OK** | Faltar cualquiera de los 2 XML aborta; no se activa nada |
| 3 | XML ilegible o inválido | 4 | **OK** | Mal formado, vacío, no-XML y raíz equivocada se rechazan |
| 4 | Fallo en la extracción | 3 | **OK** | Bytes de control y XML truncado no rompen la versión activa |
| 5 | Fallo en la integración | 3 | **OK** | Fallo de integración no activa nada; sin secciones mínimas se rechaza |
| 6 | Fallo en la validación | 4 | **OK** | Fallo al validar o hashear aborta antes de activar |
| 7 | Interrupción antes de activar | 4 | **OK** | Las 5 etapas previas son seguras; staging se limpia (o se conserva con `--dejar-staging`) |
| 8 | Manifiesto incorrecto | 6 | **OK** | Hash manipulado, fichero borrado, manifiesto ilegible/vacío y JSONL adulterado se detectan |
| 9 | Recuperación | 5 | **OK** | Vuelve a la anterior, no borra copias, y **recuperar es reversible** |
| 10 | Segunda actualización | 2 | **OK** | Dos y tres actualizaciones seguidas, cada una con su fecha y su respaldo |

### En los escenarios fallidos se demuestra

Cada prueba de fallo comprueba explícitamente **tres** cosas:

1. La huella de `merged/` es **idéntica** a la de antes (`assertEqual`).
2. El núcleo real **carga** la versión activa (`assertApiSirve`).
3. El dataset real **no ha cambiado** (`assertRealIntacto`).

### Dos defectos encontrados por las propias pruebas

Las pruebas fallaron al escribirlas y revelaron dos problemas reales:

**a) La comprobación posterior no revertía.** Si fallaba la etapa 7, la versión
nueva **ya estaba activa** y el sistema se quedaba con datos que no habían
pasado la verificación. **Corregido**: ahora la etapa 7 revierte al backup y lo
informa (`se ha revertido a la version anterior`). Prueba:
`test_fallo_en_la_comprobacion_posterior_revierte`.

**b) Dos actualizaciones en el mismo segundo tenían la misma fecha.** La marca
temporal usaba resolución de segundos. **Corregido** a milisegundos.

También se corrigió un error propio: el staging no se borraba tras una
actualización correcta (dejaba ~50 MB de basura). Ahora se limpia, y una prueba
lo fija.

---

## 7. Resultado de las pruebas de regresión

| Suite | Resultado |
|---|---|
| `probar_nucleo.py` | **48/48** OK |
| `probar_integracion.py` | **20/20** OK |
| `probar_adversarial.py` | **39/39** OK |
| `probar_api.py` | **54/54** OK |
| `probar_web.py` | **65/65** OK |
| `probar_actualizacion.py` (nueva) | **43/43** OK |
| **TOTAL** | **269/269** |

| Comprobación adicional | Resultado |
|---|---|
| `test_determinismo.py` | **DETERMINISTA** (29 consultas, 4 procesos, 3 repeticiones) |
| `verificar_reproducibilidad.py` | **REPRODUCIBLE desde los XML originales** |
| `npm run build` (con API local) | Correcto |
| `npm run build` (sin API, público) | Correcto, `hayApi() === false` |
| Actualización real con los XML de 49 MB | **Correcta**, 8 etapas |

### API antes y después

Comprobado con la API **en marcha** durante el ciclo completo:

| Momento | Resultado |
|---|---|
| Antes de actualizar | `figuras 11144, eventos 57215` |
| Actualización **fallida** | `ACTUALIZACION CANCELADA` + API intacta: `11144 / 57215` |
| Actualización **correcta** | Nueva versión activa + copia guardada |
| Tras reiniciar | `figuras 11144, eventos 57215, relaciones 13192` |
| `dataset_version.json` | `actualizada: 2026-10-03T02:25:39.120+02:00` |

---
## 8. Hashes e integridad de los datos

### 8.1 XML originales

| XML | SHA-256 | Estado |
|---|---|---|
| `legends.xml` | `77DB4739C4064911CDD6A94FD68D5B3CEFCBFDBC5A4459D7495CA63985A4681F` | **INTACTO** |
| `legends_plus.xml` | `FB6BE93DAC3E878B36EB5BDD47BFE288B66D682FDA30023BA9538E81194ABC2D` | **INTACTO** |

Comprobado antes de empezar, después de las actualizaciones reales y al
terminar. Además hay una prueba que compara los hashes de las entradas antes y
después de cada actualización de fixture.

### 8.2 JSONL: sin modificaciones involuntarias

Los **17 JSONL de datos** tienen el **mismo SHA-256** antes y después de dos
actualizaciones reales completas:

```
artifacts.jsonl                    8741133D84746EA4   (igual)
entities.jsonl                     B28665231259C1F3   (igual)
historical_events.jsonl            07204F1B3CFAF227   (igual)
historical_figures.jsonl           DA400A37A7DD0B11   (igual)
historical_event_relationships.jsonl 43274E917EF9689E (igual)
sites.jsonl                        53E5EC2DA985FEDB   (igual)
… (los 17 idénticos)
```

Tres ficheros **sí cambian**, y es lo esperado:

| Fichero | Por qué |
|---|---|
| `_hashes.json` | Nuevo: es el manifiesto de la versión |
| `_manifiesto.json` | Lleva la marca temporal de generación |
| `indice_evento_relaciones.json` | Lleva orden de generación y marca temporal |

### 8.3 Código del pipeline sin tocar

| Fichero | SHA-256 (prefijo) |
|---|---|
| `nucleo.py` | `865048A2081E3FDC` — sin modificar |
| `integrar_legends.py` | `35649CDCAF75153B` — sin modificar |

No hizo falta tocar `nucleo.py` ni ningún otro módulo del pipeline: todo el
sistema se apoya en reasignar rutas de módulo, que es exactamente para lo que
`verificar_reproducibilidad.py` ya hacía.

---

## 9. Limitaciones conocidas

1. **Hay que reiniciar la API.** `servicio._ARCHIVO` es un singleton: la API
   mantiene en memoria la versión con la que arrancó. Documentado y anunciado al
   final de cada actualización. Solución alternativa (releer por petición)
   descartada por coste: ~2,5 s por petición.

2. **`probar_integracion.py` fija los conteos de ESTA partida** (11.144 figuras,
   57.215 eventos…). Si el jugador actualiza con **otra partida**, esas 20
   pruebas fallarán legítimamente, porque verifican un mundo concreto.
   `actualizar_datos.py` **no** las ejecuta precisamente por eso: valida
   estructura, coherencia y carga del núcleo, que son independientes de la
   partida. Si el jugador cambia de mundo, esas referencias a los conteos
   deberán actualizarse aparte.

3. **Ventana mínima durante la activación.** Entre los dos `rename` hay una
   fracción de segundo sin `merged/`. Si la API se reiniciara *en ese instante
   exacto*, arrancaría sin datos. El riesgo es despreciable (los `rename` en el
   mismo volumen son inmediatos) y la recuperación es una sola orden.

4. **Las copias antiguas se acumulan.** `backups/` nunca se limpia, por
   seguridad. Cada `merged/` ocupa ~65 MB. No hay comando de limpieza: es
   deliberado ("no borrar copias anteriores sin una razón justificada").

5. **`registrar_original()` nunca sobrescribe.** Si se cambia de partida, hay que
   reemplazar los XML a mano en `original_data/` (o usar `--originales`). La
   herramienta no borra los XML antiguos por sí sola, para no destruir el
   material original.

6. **El tamaño de los fixtures es mínimo.** Las pruebas usan XML diminutos: no
   verifican el rendimiento con 49 MB, solo la **corrección**. El rendimiento con
   datos reales se comprobó aparte (actualización completa en ~20 s).

7. **No se probó en Windows con otro antivirus** que bloquee `rename` sobre
   directorios con ficheros abiertos.

---

## 10. Instrucciones de uso para el jugador

### Quiero ver qué datos hay ahora

```powershell
python run.py --estado
```

Te dirá la fecha de la última actualización, los hashes de tus XML, cuántos
registros hay y si los datos son coherentes.

### Quiero actualizar mis datos

**Paso 1.** En Dwarf Fortress, exporta Legends y guarda los dos XML
(`legends.xml` y `legends_plus.xml`).

**Paso 2.** Copia los dos sobre
`00_SOURCE\original_data\legends.xml` y `...\legends_plus.xml`
(el juego puede seguir abierto).

**Paso 3.** Detén la API si está corriendo (Ctrl+C en su ventana) y ejecuta:

```powershell
python run.py --actualizar
```

Verás las 8 etapas en pantalla. Si todo va bien:

```
==========================================================================
ACTUALIZACION CORRECTA
==========================================================================
   OK  la nueva version esta activa
```

**Paso 4.** Arranca de nuevo la API:

```powershell
python run.py
```

> El reinicio es necesario: la API guarda los datos en memoria.

### Dubio antes de tocar nada

```powershell
python 00_SOURCE\tools\actualizar_datos.py actualizar --sin-activar
```

Genera y valida todo, pero **no cambia** los datos que usa la aplicación. Solo
una vez que todo esté verificado, ejecuta sin esa opción.

### Algo salió mal

Si la actualización falla, tus datos anteriores **siguen ahí**. No hace falta
hacer nada: la aplicación funciona igual. Cuando quieras, vuelve a intentarlo.

### Quiero volver atrás

```powershell
python 00_SOURCE\tools\actualizar_datos.py historial   # ver las copias
python 00_SOURCE\tools\actualizar_datos.py recuperar   # volver a la última
python run.py                                          # reiniciar
```

### Situaciones especiales

| Situación | Qué hacer |
|---|---|
| Los XML no están en `original_data/` | `... actualizar --originales RUTA` |
| Un fallo y quiero depurar | `... actualizar --dejar-staging` deja el staging intacto |
| Ver todas las versiones | `python 00_SOURCE\tools\actualizar_datos.py historial` |
| Cambiar de partida | Sustituye los dos XML en `original_data/` y actualiza |

---
## 11. Estado final

# COMPLETADA CON LIMITACIONES

### Criterio de finalización

> *«El usuario debe poder actualizar manualmente los datos de su mundo mediante
> un procedimiento sencillo y seguro. Si una actualización falla por cualquier
> motivo, DF Legends debe conservar y seguir utilizando la última versión válida
> de los datos.»*

**Cumplido**, y demostrado con pruebas:

- **Procedimiento sencillo**: un comando, `python run.py --actualizar`, con las
  etapas visibles y un resultado inequívoco.
- **Seguro**: se genera en un staging aislado y la versión activa no se toca
  hasta que todo ha pasado. Los XML originales son de solo lectura.
- **Si falla, la versión válida sobrevive**: comprobado en **23 pruebas** de los
  escenarios 2 a 8, y además con la API en marcha.
- **Recuperable**: una orden devuelve a la anterior, y esa recuperación también
  es reversible.

### Lo que se hizo

| | |
|---|---|
| Ficheros nuevos | 2 (`actualizar_datos.py`, `probar_actualizacion.py`) |
| Ficheros modificados | 1 (`run.py`, dos opciones) |
| Módulos del pipeline tocados | **0** |
| Dependencias añadidas | **0** (solo biblioteca estándar) |
| Pruebas | **43** nuevas, **269/269** en total |
| XML modificados | **0** |

### Por qué no es un COMPLETADA sin más

Las limitaciones de §9 quedan documentadas y son conocidas. La más relevante
es que `probar_integracion.py` está atada a los conteos de este mundo, de modo
que cambiar de partida exigiría revisar esas referencias. No afecta a la
corrección del sistema de actualización.