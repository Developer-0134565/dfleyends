// DF Legends :: configuracion de Astro.
//
// decisions:
//  - `static` (por defecto en Astro 7). El sitio se construye como assets
//    estaticos y se sirve igual en Cloudflare Workers.
//  - La PORTADA y las VISTAS DE LISTADO se pre-renderizan en build.
//  - Las FICHAS por id (`/figures/712`) NO se pre-renderizan: hay 11.144
//    figuras y 57.215 eventos. Se sirven con el shell `ficha.astro`, que resuelve
//    la ruta en el navegador. Para que la URL siga siendo `/figures/712`, el
//    rewrites de abajo manda cualquier ruta de dos segmentos al shell.
//  - IMPORTANTE: la capa publica sigue siendo ESTATICA y NO se conecta a la
//    API local. Un build sin `PUBLIC_API_BASE_URL` no tiene ninguna URL de API.
//  - sin `site`: no hay URL de produccion verificada todavia, y Astro la usaria
//    para canonical/sitemap. Inventarla seria publicar una URL falsa.
//  - sin framework de UI: nada de esto necesita runtime de componentes.

import { defineConfig } from 'astro/config';

// Las URLs limpias siguen siendo navegables y compartibles. En DESARROLLO las
// resuelve el `rewrites`; en el build estatico las sirve `404.html`, que es el
// mismo shell (ver `src/pages/404.astro`). En ambos casos se pinta en el
// navegador: no hay runtime ni adaptador.
const FICHA = '/app'; // shell Ãºnico de la aplicaciÃ³n

export default defineConfig({
  output: 'static',
  build: {
    format: 'directory',
  },
  rewrites: {
    '/world': FICHA,
    '/figures': FICHA,
    '/entities': FICHA,
    '/sites': FICHA,
    '/artifacts': FICHA,
    '/events': FICHA,
    '/timeline': FICHA,
    '/geography': FICHA,
    '/search': FICHA,
    '/figures/([^/]+)': FICHA,
    '/entities/([^/]+)': FICHA,
    '/sites/([^/]+)': FICHA,
    '/artifacts/([^/]+)': FICHA,
    '/events/([^/]+)': FICHA,
  },
});