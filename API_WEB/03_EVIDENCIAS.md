# API/WEB — EVIDENCIAS REPRODUCIBLES

> Todo lo de aquí se reproduce con los comandos indicados. Sin excepciones.

---

## EVID-001 · Baseline de hashes (antes de la misión)

Medido al inicio, antes de tocar nada:

| Recurso | SHA-256 |
|---|---|
| `dfchron/servicio_consulta.py` | `0a5b6b1c3244e6192752f311b89d075e6b75de23d971a4972fdba54f3a73f834` |
| `dfchron/adaptador_consulta.py` | `c456256ec1c1d731d5dee461f8035cc1df92b19725bb6de832997ad820e22212` |
| `dfchron/api.py` | `0426f63a632fd243ce0675db6c857389a3f3218ae44d1b950d176c67d0472e9e` |
| `dfchron/ia_conocimiento.py` | `639548169fd86d42163bac4fdbd208a1…` |
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | `5d2c3d001c542e774d8ff56951901f6d41b4701924b4a8971a6864cfb0b35e3a` |
| `00_SOURCE/original_data/legends.xml` | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` |
| `00_SOURCE/original_data/legends_plus.xml` | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` |

`servicio_consulta.py` y `adaptador_consulta.py` coinciden con los baselines
registrados en `P1_VERSIONADO_MUNDO_VIVO.md` §20 — ninguno de los dos cambió
desde la misión anterior.

```
Get-FileHash <fichero> -Algorithm SHA256
```

---

## EVID-002 · Mapa de la frontera: 13 de 51

```
python API_WEB\auditar_frontera.py
```

```
Rutas registradas            : 51
Delegan en el adaptador      : 13
Deberian pasar por frontera  : 13
```

**Discrepancia cero.** Es el resultado arquitectónico: ninguna ruta que necesite
la frontera la salta, y ninguna que no la necesite la usa.

Artefactos: `mapa_frontera.json`, `mapa_frontera.txt`.

---

## EVID-003 · La Web no accede al dataset

Búsqueda en `dfchron/web/*` y `dfchron/site/src/**` de: `legends.xml`,
`legends_plus`, `.jsonl`, `readFileSync`, `XMLHttpRequest`, `node:fs`,
`require(`, `readFile`, `.xml`, `dataset_id`, `indice`, `glob`.

**Resultado: cero accesos a disco.**

| Fichero | `fetch` a | Acceso a disco |
|---|---|---|
| `web/app.js` | `fetch(ruta)` genérico + `fetch('/api/salud')` | ninguno |
| `site/src/lib/api.ts` | `fetch(url)` — punto único de red | ninguno |
| `site/src/lib/dataset.ts` | lee `dataset_id` **del envelope** | ninguno |

Dos coincidencias aparentes, revisadas:
- `web/index.html:38` — `legends.xml` en un **texto descriptivo**.
- `site/src/lib/mapa.ts:25` — `sites.jsonl` dentro de un **comentario**.

Ninguna de las dos lee nada.

---

## EVID-004 · Ejecución real: la llamada atraviesa el servicio

`probar_frontera_adversarial.py`, clase `TestD_Bypass`. Se envuelven las seis
operaciones de `servicio_consulta`, se pide la ruta **por HTTP**, y se exige que
el registro contenga la operación esperada:

| Ruta | Operación que debe ejecutarse |
|---|---|
| `/api/figuras/712` | `obtener_entidad` |
| `/api/entidades/4` | `obtener_entidad` |
| `/api/sitios/4` | `obtener_entidad` |
| `/api/artefactos/1` | `obtener_entidad` |
| `/api/eventos/1` | `obtener_entidad` |
| `/api/figuras/712/relaciones` | `buscar_relaciones` |
| `/api/consulta/entidad/figura/712` | `obtener_entidad` |
| `/api/consulta/contar/figura` | `contar` |
| `/api/consulta/evidencia/figura/712` | `obtener_evidencia` |
| `/api/consulta/relaciones/712` | `buscar_relaciones` |

**Y lo contrario**, en `test_la_navegacion_no_usa_la_frontera_por_accidente`:
`/api/buscar`, `/api/listar/artifacts`, `/api/geografia`, `/api/stats`,
`/api/salud` y `/api/figuras/712/eventos` **no ejecutan ninguna** operación de
la capa de consulta. La frontera no se usa de más.

---

## EVID-005 · Estados semánticos, medidos contra el servidor real

Tomados ejecutando, no de la documentación:

| Petición | HTTP | `estado` | `certainty` |
|---|---:|---|---|
| `/api/consulta/entidad/figura/712` | 200 | `FOUND` | `FACT` |
| `/api/consulta/entidad/figura/999999999` | **404** | `NOT_FOUND` | `UNKNOWN` |
| `/api/consulta/atributo/figura/712/atributo_que_no_existe` | 200 | `NOT_VERIFIED` | `UNKNOWN` |
| `/api/consulta/entidad/relacion/1` | 200 | `NOT_VERIFIED` | `UNKNOWN` |
| `/api/consulta/verificar?...&predicado=tiene:raza&objeto=DRAGON` | 200 | `NOT_VERIFIED` | `UNKNOWN` |

**El caso que más importa** es el tercero. La figura 712 **existe**, pero el
dataset **no declara** ese atributo. El sistema responde:

```
"la entidad existe pero el dataset no declara el atributo
 'atributo_que_no_existe'; no se infiere"
```

y además publica `atributos_disponibles`. Eso es la diferencia entre
`NOT_VERIFIED` y `NOT_FOUND` funcionando de verdad: no es «no existe», es
«existe y el dataset no dice nada».