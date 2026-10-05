# DF Legends :: sitio (Astro)

Capa de **presentacion** de DF Legends: la web que consume la API local.

---

## Arranque

### 1. La API (obligatoria primero)

Desde la raiz del proyecto:

```bash
python run.py
```

Arranca en `http://127.0.0.1:877`. Carga el indice (~2,5 s) y abre el navegador.

### 2. La web

```bash
cd dfchron/site
npm install          # solo la primera vez
npm run dev          # desarrollo, con recarga
```

Abre `http://localhost:4321`.

**Importante:** sin la API arrancada, las vistas muestran `Data unavailable`.
No es un fallo: es la honestidad de no inventar cifras.

---

## Configuracion: donde vive la direccion de la API

Hay **un solo sitio** donde se escribe la direccion de la API:

```
src/lib/api.ts
```

Se lee de la variable de entorno `PUBLIC_API_BASE_URL`.

### Aplicacion local

```bash
# Windows (cmd)
set PUBLIC_API_BASE_URL=http://127.0.0.1:877 && npm run dev

# PowerShell
$env:PUBLIC_API_BASE_URL="http://127.0.0.1:877"; npm run dev
```

### Build publico (sin API)

```bash
npm run build
```

Si `PUBLIC_API_BASE_URL` **no** esta definida, `API_BASE_URL` queda vacia,
`hayApi()` devuelve `false` y las vistas muestran `Data unavailable`. El build
publico, por tanto, **no queda conectado a la API local**.

### API remota (futuro)

```bash
PUBLIC_API_BASE_URL=https://api.algundominio.example npm run build
```

No hay que tocar ninguna vista, componente ni logica de presentacion. Solo esa
variable. Una prueba (`probar_web.py`) verifica que ninguna otra pieza del
frontend escribe una URL de API.

---

## Como funciona el render

El sitio es **estatico**: `npm run build` genera `dist/`, que se sirve en
Cloudflare Workers como assets (ver `wrangler.jsonc`).

Las vistas que dependen de datos se pintan **en el navegador**:

| Ruta | Donde se sirve |
|---|---|
| `/app/...` | `app/index.html` (shell) |
| `/figures/712`, `/sites/87`, ... | `404.html` (mismo shell) |

Ambas usan `src/lib/vistas.ts`, que lee la URL, pide los datos a la API y pinta
el resultado.

**Por que no se pre-renderiza cada vista:** una pagina pre-renderizada congela
el resultado del build. Si la API no estaba viva durante `npm run build`, la
pagina queda con `Data unavailable` para siempre. Se comprobo en la practica.
La alternativa (render en servidor) exige un adaptador y por tanto un runtime
en la capa publica, que esta fase no permite.

### Nota sobre `astro preview`

`astro preview` sirve ficheros literales y devuelve 404 para las rutas limpias
(`/figures/712`): no aplica los `rewrites` ni el fallback a `404.html`. Para
probarlas hay que usar un servidor estatico con fallback a `404.html` (como
hace Cloudflare con `not_found_handling: "404-page"`), o usar `npm run dev` con
las rutas bajo `/app/...`.

---

## Estructura

```
src/
├── lib/
│   ├── api.ts        <- UNICA fuente de la direccion de la API
│   ├── escapes.ts    <- helpers compartidos (rompe un ciclo de imports)
│   ├── listados.ts   <- listados, eventos, timeline, busqueda, geografia
│   └── vistas.ts     <- fichas + router
├── components/       <- cabecera, pie, badges de certeza
├── layouts/          <- BaseLayout (portada)
├── pages/
│   ├── index.astro   <- portada publica (identidad + entrada)
│   ├── app.astro     <- shell de la aplicacion
│   └── 404.astro     <- mismo shell, para rutas limpias
└── styles/
    ├── base.css      <- tokens (piedra, pergamino, laton)
    ├── components.css
    ├── layout.css
    └── app.css       <- maquetacion de la aplicacion
```

---

## Reglas que el codigo respeta

- **UNKNOWN no es una afirmacion.** Un dato que no consta se muestra como
  `Unknown` o `Data unavailable`.
- **Los recortes se declaran.** `Showing 50 of 11.144`.
- **El grafo de relaciones es dirigido.** No se invierte la relacion.
- **El tipo real del sitio se conserva.** `fortress` sigue siendo `fortress`.
- **La ambiguedad se declara.** Una busqueda con varios resultados no elige
  sola: los muestra todos.
- **El navegador no descarga el dataset.** Todas las listas piden `limit`.

---

## Despliegue (Cloudflare Workers)

`wrangler.jsonc` sirve `dist/` como assets estaticos. No hay Worker con codigo.

```bash
npm run build
npm run deploy      # astro build && wrangler deploy
```

`astro.config.mjs` no define `site`: no hay URL de produccion verificada, y
inventarla publicaria un canonical falso. Con `site` definido, Astro añade el
`<link rel="canonical">` automaticamente.

---

## Pruebas

```bash
python ../pruebas/probar_web.py
```

Comprueba el envelope, los alias, CORS, los datos conocidos (figura 712,
entidad 282, sitio 87), los filtros combinados, el truncamiento, los casos
adversariales y que la URL de la API solo existe en `src/lib/api.ts`.