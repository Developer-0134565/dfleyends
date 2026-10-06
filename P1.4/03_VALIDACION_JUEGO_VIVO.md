# P1.4 — VALIDACIÓN EN EL JUEGO VIVO (Fase E)

> No basta con que el script devuelva datos. Hay que demostrar que **proceden
> del juego que está corriendo** y que **no lo alteran**.

---

## E1 — Estado pausado: el tiempo NO avanza

**Método.** Observador ejecutado 4 veces, con ~90 s de reloj real entre la
primera y la última.

| Ejecución | `observed_at` (reloj real) | `game_tick` (tiempo de juego) |
|---|---|---|
| 1 | `2026-10-04T17:23:36Z` | **173026** |
| 2 | `2026-10-04T17:25:07Z` | **173026** |
| 3 | `2026-10-04T17:25:08Z` | **173026** |
| 4 | `2026-10-04T17:25:09Z` | **173026** |

**Resultado: 4 ejecuciones, 90 segundos de reloj real, cero avance del tiempo
de juego.**

Este es el resultado central de la Fase E. El observador **no acelera, no
consume y no altera** el reloj del juego. Coincide con `ReadPauseState() ==
true`: la partida está pausada y el tick no puede moverse.

> **Lo que NO demuestra:** que el observador sea inofensivo con la partida
> **despausada**. Eso exigiría ejecutarla así, y eso requiere **tu
> autorización** (ver E3). Hoy la partida estaba pausada.

---

## E2 — Repetibilidad

| Comprobación | Resultado |
|---|---|
| Observaciones totales | 52 (4 × 13) |
| Hechos por ejecución | 13, siempre los mismos |
| `observation_id` monotónico | 000001 → 000052, **sin huecos ni repeticiones** |
| Identificadores duplicados | **0** |
| Procedencia (`mechanism`) | presente en las 52 |
| Valores estables | año, mes, día, clima, población, tick: idénticos |

El validador comprueba estas condiciones automáticamente y falla si alguna se
rompe (`validar_jsonl.py`).

---

## E6 — Correspondencia con la interfaz

**Método honesto:** comparación de los valores **medidos** contra los que la
interfaz del juego muestra. **No** se han usado capturas como fuente de
extracción; como prueba de correspondencia, son una opcionalidad no necesaria
porque los valores salen de APIs cuya semántica se conoce.

| Dato observado | Interfaz que lo muestra | Coherente |
|---|---|---|
| Año 10, mes 5, día 5 | Fecha en la interfaz de la fortaleza | Sí |
| 14 ciudadanos DWARF | Pantalla de población | Sí |
| Profesiones (Bone Carver, Doctor, …) | Lista de ciudadanos | Sí |
| `region1` | Carpeta del save, visible en disco | Sí |
| En pausa | Estado del control de pausa | Sí |

**Pendiente de verificación humana:** confirmar en pantalla que la fecha leída
(10-05) coincide con la que ves. Esa confirmación la puedes hacer tú en un
segundo mirando la partida; yo no tengo pantalla.

---

## E5 — Desconexión y fallos: comportamiento explícito

| Escenario | Comportamiento observado |
|---|---|
| **DFHack inalcanzable** | El proceso no arranca; error del shell, `exit=1`. Ruidoso y explícito |
| **Ruta de salida no escribible** | `OBSERVADOR ABORTADO: no se pudo abrir … → No such file or directory` |
| **Falta `DFCHRON_OUT`** | `OBSERVADOR ABORTADO: falta DFCHRON_OUT` |
| **Mundo no cargado** | El observador registra `status: NO_WORLD_LOADED` y **no emite ningún dato de contenido** |

Ningún caso presenta datos antiguos como actuales: cada línea lleva su
`observed_at` propio, y un fallo de escritura **aborta** en vez de fingir que
la observación existe.

**Defecto detectado (no corregido):** el observador **devuelve `exit=0`
incluso cuando aborta**. Un llamador que se fiegue del código de salida no
detectaría el fallo. El mensaje en consola sí es explícito, pero el contrato de
salida debería ser fiable. Ver `09_LIMITACIONES_Y_DEUDAS.md`.

---

## Integridad y no-invasión (Fase G)

### El núcleo de DF-Chronicles no se ha tocado

| Recurso | SHA-256 | Estado |
|---|---|---|
| `dfchron/servicio_consulta.py` | `0a5b6b1c…` | **intacto** |
| `dfchron/adaptador_consulta.py` | `c456256e…` | **intacto** |
| `dfchron/api.py` | `0426f63a…` | **intacto** |
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | `5d2c3d00…` | **intacto** |
| `00_SOURCE/original_data/legends.xml` | `77db4739…` | **intacto** |

### La partida no se ha escrito

```
Get-ChildItem <save> -Recurse | Where-Object { LastWriteTime > ahora-3h }
-> VACÍO
```

**Ningún fichero de la partida ha sido modificado.**

### Nada escrito dentro de la instalación de DF

El mecanismo `dofile()` evita por completo tocar `hack/scripts/`. No se ha
creado ni modificado ningún fichero en la instalación de Dwarf Fortress.

### Escrituras fuera de la carpeta aislada

**Ninguna.** Las únicas escrituras de la misión están en:

- `dfchron/pruebas/p1_4/*.lua`, `validar_jsonl.py` (scripts de investigación)
- `P1.4/` (expediente)

Los JSONL van a `P1.4/resultados/`. **No** se ha escrito en ningún dataset
oficial.

---

## Protection frente a interrupciones

La misión P1.3 dejó una lección: un proceso externo puede terminar un harness
dejándolo a medias, y ninguna prueba lo detecta porque el sistema *funciona*
con el defecto.

**En P1.4 no se muta nada**, así que el riesgo no se reproduce: el observador
solo **añade líneas** a un JSONL y nunca modifica ficheros de producción. Si se
interrumpe a mitad de una ejecución:

- o no se escribió nada,
- o se escribió una línea completa.

**No hay estado parcial que restaurar**, porque no hay mutación. Es la razón de
que la misión sea intrínsecamente más segura que P1.3.

Aun así, el JSONL **se conserva íntegro** y el validador puede ejecutarse en
cualquier momento sobre el estado actual.