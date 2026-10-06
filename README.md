# DF-Chronicles

Aplicación **local** para consultar los datos históricos que Dwarf Fortress
registra en sus exports de Legends.

```bash
python run.py
```

Abre <http://127.0.0.1:877/> y ya está. No hay que instalar nada: solo la
biblioteca estándar de Python 3.

---

## La web (DF Legends)

Existe una segunda capa: **DF Legends**, en `dfchron/site/`. Es la aplicación
web que explora el mundo a través de la misma API.

```bash
# 1. la API (obligatoria primero)
python run.py

# 2. la web
cd dfchron/site
npm install          # solo la primera vez
set PUBLIC_API_BASE_URL=http://127.0.0.1:877 && npm run dev
```

Abre <http://localhost:4321/>.

La dirección de la API se declara en **un solo sitio**, `src/lib/api.ts`, y se
lee de `PUBLIC_API_BASE_URL`. Cambiarla a una API remota futura es cambiar esa
variable: no hay que reescribir ninguna vista.

Detalle completo en [`dfchron/site/README.md`](dfchron/site/README.md).

### Arquitectura

```
legends.xml + legends_plus.xml
        ↓  integración
      JSONL
        ↓  validación
       NÚCLEO            00_SOURCE/tools/nucleo.py
        ↓
     SERVICIO           dfchron/servicio.py   (envelopes, límites, errores)
        ↓
       API              dfchron/api.py        (rutas HTTP, CORS)
        ↓
      ASTRO             dfchron/site/         (API_BASE_URL)
        ↓
     USUARIO
```

El frontend **nunca** lee XML ni JSONL, ni importa Python. La API **nunca**
reimplementa una consulta del núcleo.

---

## Qué es

DF-Chronicles convierte `legends.xml` (49.223.702 B, CP437) y
`legends_plus.xml` (17.664.819 B, UTF-8) en un sistema consultable sobre
personajes, entidades, acontecimientos, sitios, artefactos y relaciones.

Estado actual: **aplicación funcional**. Núcleo, API y UI verificados con
pruebas automáticas sobre los datos reales.

| Suite | Resultado |
|---|---|
| Integración | **20 / 20** |
| Núcleo | **48 / 48** |
| Adversarial | **39 / 39** |
| API y seguridad | **54 / 54** |
| Web ↔ API (nueva) | **62 / 62** |
| Determinismo | 29 consultas × 4 procesos, idénticas |
| Reproducibilidad | **9 / 9** secciones byte-idénticas, **4 / 4** salvaguardas |

## Principio rector

> Los datos son **FACT** o **DERIVED**. Lo que no consta se marca **UNKNOWN**.
> Nunca se inventa.

El sistema no genera crónicas, lore, rankings ni interpretaciones. Solo expone
lo que los XML de Dwarf Fortress contienen, con su procedencia declarada, y
**hace visibles sus límites**.

---

## Requisitos

* Windows (probado en Windows 11)
* Python **3.11 o superior** — nada más. Sin `pip install`, sin dependencias.

```bash
python --version     # debe ser 3.11+
```

## Arranque

```bash
cd DF-Chronicles
python run.py
```

Imprime las rutas activas y abre el navegador:

```
DF-Chronicles iniciado
  Datos   : ...\DF-Chronicles\00_SOURCE
  Indice  : ...\DF-Chronicles\00_SOURCE\processed\merged
  Exports : ...\DF-Chronicles\00_SOURCE\exports
  UI      : ...\DF-Chronicles\dfchron\web
  Nucleo cargado en 2.35s
```

Opciones:

```bash
python run.py 9000            # otro puerto
python run.py --sin-navegador # no abrir el navegador
python run.py --comprobar     # solo comprobar datos y salir (no sirve)
```

---

## Cómo usarlo

### 1. Buscar una figura

Escribe `galka shafttop` en el buscador y pulsa Enter. La UI muestra los
resultados **agrupados por tipo** y declara si la consulta es ambigua: no
elige por ti.

### 2. Abrir su ficha

```
galka shafttop the blades of knighting   [FACT]

ID de Dwarf Fortress   712
Raza                  MINOTAUR
Caste                 FEMALE
Nacimiento            UNKNOWN
Muerte                UNKNOWN   el XML no registra esta fecha. NO significa
                                que la figura siga viva ni que muriera fuera
                                del rango de los datos.
Entidad               the infamous disloyalty     -> enlace
Sitio                 searinggorged the large call -> enlace
```

Cinco pestañas: **Eventos (158)**, **Cronología**, **Relaciones**,
**Artefactos** e **Identidad**.

### 3. Ver sus eventos y navegar

La pestaña **Eventos** lista los 158 acontecimientos. Cada fila enlaza a la
figura, al sitio y a la entidad implicada: se navega en cualquier dirección.

### 4. Abrir el sitio relacionado

La ficha del sitio conserva el **tipo real de Dwarf Fortress**:

```
halesteel   [FACT]

ID                                    87
Tipo (tal cual en Dwarf Fortress)     fortress   <- no se convierte en "site"
Coordenadas                           112, 20
Eventos                               1.546
```

### 5. Consultar una entidad y sus miembros

Menu **Entidades** -> `the curled diamond` (id 282): 25 miembros, sus sitios,
sus 769 eventos y su cronología. Cada miembro enlaza a su ficha.

### 6. Filtrar eventos

Menu **Eventos**. Filtros combinables por año, rango, tipo, figura y sitio:

```
Anio [ ]  Desde [1]  Hasta [20]  Tipo [todos]  Figura [ ]  Sitio [ ]  [Buscar]

---

## Estructura

```
DF-Chronicles/
├── run.py                       <- punto de entrada unico
├── API.md  ARCHITECTURE.md  WINDOWS.md
├── dfchron/                     <- APLICACION
│   ├── config.py                <- rutas y limites
│   ├── servicio.py              <- envelopes, validacion, errores
│   ├── api.py                   <- servidor HTTP (solo stdlib)
│   ├── web/                     <- UI: index.html, app.js, estilo.css
│   └── pruebas/probar_api.py    <- 54 pruebas de API, UI y seguridad
├── 00_SOURCE/
│   ├── original_data/           <- XML archivados (SOLO LECTURA)
│   ├── processed/
│   │   ├── from_legends_xml/  from_legends_plus/
│   │   ├── merged/             <- JSONL normalizado + manifiesto
│   │   └── validation/         <- fixtures
│   ├── exports/                <- unico sitio donde la app escribe
│   └── tools/
│       ├── rutas.py            <- CONFIGURACION CENTRAL de rutas
│       ├── cargar_legends.py   <- lectura con autodeteccion de codificacion
│       ├── integrar_legends.py <- normalizacion / fusion
│       ├── validar_semantica.py<- indice y validacion
│       ├── nucleo.py           <- LOGICA DE DOMINIO (API de consulta)
│       └── probar_*.py         <- suites
└── 08_DATABASE/                 <- documentacion del dataset
```

---

## Comandos

| Objetivo | Comando |
|---|---|
| **Arrancar la aplicación** | `python run.py` |
| Comprobar sin arrancar | `python run.py --comprobar` |
| Recargar datos desde los XML | `python 00_SOURCE/tools/integrar_legends.py` |
| Pruebas de integración (20) | `python 00_SOURCE/tools/probar_integracion.py` |
| Pruebas del núcleo (48) | `python 00_SOURCE/tools/probar_nucleo.py` |
| Pruebas adversariales (39) | `python 00_SOURCE/tools/probar_adversarial.py` |
| **Pruebas de API y UI (54)** | `python dfchron/pruebas/probar_api.py` |
| **Pruebas de Web ↔ API (62)** | `python dfchron/pruebas/probar_web.py` |
| Determinismo | `python 00_SOURCE/tools/test_determinismo.py` |
| Reproducibilidad desde los XML | `python 00_SOURCE/tools/verificar_reproducibilidad.py` |
| Criterios de éxito de la misión | `python dfchron/pruebas/aceptacion_mision.py` |

Todos usan **solo la biblioteca estándar de Python 3**.

> `aceptacion_mision.py` requiere el servidor en marcha
> (`python run.py --sin-navegador` en otra terminal) y comprueba los 20
> criterios de aceptación de un vistazo.

---

## Composición de los datos

| | |
|---|---|
| Figuras históricas | 11.144 |
| Entidades | 1.067 |
| Sitios | 734 |
| Eventos | 57.215 (años **1–100**) |
| Artefactos | 427 |
| Relaciones sociales (`legends_plus`) | 13.192 |
| Ríos / masas de tierra / picos / construcciones | 2.346 / 40 / 4 / 122 |

---

## Limitaciones

Estas limitaciones **se muestran dentro de la aplicación**, no solo aquí: una
banda de aviso aparece en todas las pantallas y hay una página completa.

* Los eventos cubren **solo los años 1–100**. La única era declarada tiene
  `start_year = -1` (centinela de DF): **UNKNOWN**.
* `-1` significa *sin dato*. Se trata como ausente, nunca como ID válido.
* **17.881** de 57.215 eventos no tienen participantes; **1.947** figuras no
  tienen eventos.
* **6.734** figuras no tienen `death_year`. Esto **no** significa que sigan
  vivas: el dato no consta.
* Los **13.192** `historical_event_relationships` apuntan a eventos que **no
  existen** en `historical_events`. Se conservan como relaciones, sin evento.
* **1.925** conflictos entre las dos fuentes siguen **sin resolver**: ambos
  valores se conservan y se pueden consultar.
* **No existe una tabla de guerras.** Los conflictos son eventos discretos
  (`hf simple battle event` con subtipo). Agruparlos es **DERIVED**.
* Los **ríos no tienen id propio** en el XML: su identificador es DERIVED.
* Algunas coordenadas son desconocidas (`-1,-1`).

Detalle completo: `08_DATABASE/data_limitations.md`.

---

## Garantías

* Los XML de `original_data/` se abren **solo en lectura** y nunca se
  escriben. Su SHA-256 se comprueba en cada suite.
* `processed/` y `validation/` son de solo lectura para la aplicación. La API
  no tiene verbos de escritura: `POST`/`PUT`/`DELETE` responden **405**.
* Los IDs originales de Dwarf Fortress se conservan tal cual (son cadenas).
* Cada resultado declara su `certainty` (`FACT`, `DERIVED`, `UNKNOWN`).
* **Ningún truncamiento es silencioso**: toda respuesta dice
  `total_encontrados`, `devueltos` y `truncado`.
* Cada exportación incluye sus fuentes y solo puede escribir en
  `00_SOURCE/exportes/`.
* No se resuelve ningún conflicto de forma silenciosa.

---

## Documentación

| Documento | Contenido |
|---|---|
| `API.md` | Referencia completa de endpoints y formato de respuesta |
| `ARCHITECTURE.md` | XML -> JSONL -> nucleo -> servicio -> API -> UI |
| `WINDOWS.md` | Instalación, arranque, empaquetado y problemas |
| `08_DATABASE/data_limitations.md` | **Lo que los datos NO permiten saber** |
| `08_DATABASE/ai_data_contract.md` | Contrato para la futura IA |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Contexto operativo de la futura IA |
| `00_SOURCE/dataset_manifest.json` | Hashes, conteos y estado del dataset |
| `00_SOURCE/final_extraction_phase_report.md` | Informe de esta fase |

> **Para la futura IA:** empieza por `data_limitations.md` y
> `AI_PROJECT_CONTEXT.md`. Un modelo **necesita** conocer las limitaciones para
> no rellenarlas por inercia.

---

## Ejecución en red

La API escucha solo en `127.0.0.1:877` — no es accesible desde la red local.
Para exponerla en otro sitio (ver `ARCHITECTURE.md`):

```bash
python run.py --host 0.0.0.0 8777
```

> **Aviso:** al exponerla en una red, cualquiera que alcance el puerto puede
> leer el archivo histórico completo. `original_data/` y `processed/` siguen
> protegidos, pero los datos son consultables. Añade autenticación antes de
> exponerla fuera de tu máquina.

```

`1-3` + figura `712` devuelve 6 eventos, no los 158 totales.

### 7. Consultar la cronología

Menu **Cronología**: agrupa por año en el orden validado `(año, seconds72)`.
No inventa fechas ni rellena años vacíos.

### 8. Consultar relaciones

Pestaña **Relaciones**. Muestra tipo, año, la otra figura y si el evento citado
consta.

> **El grafo es dirigido.** Que A tenga relación con B **no** implica la
> inversa. La ausencia del inverso significa solo que no está registrado.

### 9. Consultar geografía

Menu **Geografía**: ríos (2.346), masas de tierra (40), picos (4) y
construcciones del mundo (122), con coordenadas. También permite buscar
construcciones en un punto exacto (`112, 20`), enlace marcado **DERIVED**.

### 10. Exportar

**Exportar JSON** / **Exportar Markdown** abren el contenido en el navegador
**sin escribir en disco**. *Guardar en disco* escribe solo en
`00_SOURCE/exportes/`, nunca sobre los XML.
