# AGENTS.md

Aplicación local que convierte los exports Legends de Dwarf Fortress (`legends.xml`,
`legends_plus.xml`) en un sistema consultable sobre personajes, entidades,
acontecimientos, sitios, artefactos y relaciones. Stack: **Python 3.11+ de
biblioteca estándar** (sin `pip install`) + una web **Astro** de una sola
dependencia.

> **Lee `AI_CONSUMER_BOUNDARY.md` antes de tocar el perímetro de IA** y
> `08_DATABASE/data_limitations.md` antes de concluir nada sobre los datos.

## Comandos

Todo se ejecuta **desde la raíz de `DF-Chronicles/`**, con la API primero
(`python run.py`) cuando la prueba toque HTTP.

| Objetivo | Comando |
|---|---|
| Arrancar la aplicación | `python run.py` → <http://127.0.0.1:877/> |
| Comprobar sin servir | `python run.py --comprobar` |
| Recargar datos desde los XML | `python 00_SOURCE/tools/integrar_legends.py` |
| **Regresión completa** | `python dfchron/pruebas/correr_todas.py` |
| Suite concreta | `python dfchron/pruebas/probar_api.py` |
| Web (tras `npm install`) | `cd dfchron/site` → `npm run dev` \| `build` \| `deploy` |
| Web con API | `$env:PUBLIC_API_BASE_URL="http://127.0.0.1:877"; npm run dev` |

Opciones de arranque: `python run.py 9000`, `--sin-navegador`, `--actualizar`,
`--estado`.

## Estructura

- `run.py` — punto de entrada único; solo orquesta.
- `dfchron/` — **APLICACIÓN**: `servicio.py` (única capa que construye envelopes),
  `servicio_consulta.py` (perímetro de IA), `api.py` (rutas HTTP, CORS), `web/`
  (UI clásica), `site/` (Astro), `pruebas/` (suites y su runner).
- `00_SOURCE/` — `original_data/` (**solo lectura**, SHA-256 verificado),
  `processed/merged/*.jsonl` (dataset normalizado), `exportes/` (**única** zona
  escribible), `tools/` (`rutas.py` = rutas centrales, `nucleo.py` = **toda** la
  lógica de dominio).
- `08_DATABASE/` — contrato de datos, límites y contexto para IA.
- `API_WEB/`, `P1*/`, `P1_FINAL/` — auditorías, contratos y mutation testing.

## Arquitectura: cinco reglas que no se rompen

1. **La UI nunca lee XML ni JSONL.** Habla solo con `/api/...` vía `fetch()`
   (`src/lib/api.ts` es el **único** sitio con la URL de la API).
2. **La API nunca implementa lógica de Dwarf Fortress**: traduce rutas a llamadas
   a `servicio.py`. No sabe qué es una figura.
3. **El servicio es el único que conoce la forma de la respuesta**
   (`envolver_lista()` / `envolver_ficha()`).
4. **El núcleo no sabe rutas absolutas**: todo se resuelve en `00_SOURCE/tools/rutas.py`.
5. **Ningún recorte es silencioso**: toda lista declara `total_encontrados`,
   `devueltos` y `truncado`.

## Reglas del dominio

- Los datos son **FACT**, **DERIVED** o **UNKNOWN**. `UNKNOWN` **nunca** se
  convierte en suposición: la ausencia de `death_year` no significa que la
  figura siga viva.
- `DERIVED` viaja siempre con su `metodo` o `regla`, para que sea auditable.
- **Rechazo ≠ ausencia**: `OPERACION_NO_PERMITIDA` ≠ `NOT_FOUND` ≠
  `DATA_UNAVAILABLE`. Ninguno se reduce a booleano.
- No se genera crónica, lore ni ranking. No se resuelve ningún conflicto en
  silencio: se conservan ambos valores.
- `original_data/` y `processed/` son de **solo lectura**; la API no tiene verbos
  de escritura (`POST`/`PUT`/`DELETE` → **405**) y el export solo escribe en
  `EXPORT_ROOT`.
- Los IDs de Dwarf Fortress se conservan **tal cual**, como cadenas. `-1` es
  centinela de «sin dato», nunca un ID.

## Código

- Python **solo biblioteca estándar**. No añadas dependencias ni propongas
  Flask/FastAPI/pytest: la ausencia de `pip install` es una decisión
  documentada, no una carencia.
- Los tests son **`unittest`**, no pytest. Suites por convención: `probar_*.py`,
  descubiertas automáticamente por `correr_todas.py` (no las hardcodees).
- Docstrings y comentarios en **castellano**; cabecera de módulo
  `# -*- coding: utf-8 -*-` + docstring `DF-Chronicles :: <Módulo>`.
  Los encabezados de docstring van **sin tildes** (`Nucleo`, `validacion`).
- Imports de stdlib ordenados; `config` se importa **antes** que `nucleo`
  (añade `00_SOURCE/tools/` al `sys.path`). Los scripts admiten ejecución suelta
  con el `try/except ImportError` del paquete.
- Mantén las líneas cerca de 89 columnas. **No hay linter ni formateador
  configurado**: no ejecutes `ruff`/`black` como si existieran.

## Antes de dar algo por terminado

- Toda respuesta y toda vista nueva declara su `certainty` y su truncamiento.
- Los tests que necesitan el servidor lo dicen en su docstring; `probar_web.py`
  y `aceptacion_mision.py` requieren `python run.py --sin-navegador` en otra
  terminal.
- Si amplías el contrato de IA, el cambio exige prueba + actualizar
  `AI_CONSUMER_BOUNDARY.md` **en el mismo commit**.

## PR y commits

- Rama base: **`master`**. Rama siempre; nunca push directo a `master`.
- Mensajes en castellano, en imperativo y con alcance explícito.
- No hay CI configurado: `correr_todas.py` en verde **antes** de abrir la PR.
- No subas `*.err` / `*.out` / `__pycache__` / `dist_publico` (ya ignorados).

## Seguridad

- Nada de secretos ni de credenciales; `.env` está ignorado.
- La API **no tiene autenticación** y está pensada para `127.0.0.1`.
  Exponerla con `--host 0.0.0.0` publica el archivo histórico completo: avisa de
  ello y recomienda añadir autenticación antes.
- CORS es una **lista explícita** de orígenes locales (`4321`, `4400`,
  ampliable con `DFCHRON_CORS_PUERTOS`). No lo cambies a `*`.