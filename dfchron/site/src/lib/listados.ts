/**
 * Vistas de LISTADO y EXPLORADOR, renderizadas en el cliente.
 *
 * MOTIVACION (decision arquitectónica documentada)
 * -------------------------------------------------
 * Una pagina pre-renderizada CONGELA el resultado del build: si la API no
 * estaba viva durante `npm run build`, la pagina se guarda con "Data
 * unavailable" para siempre. Y renderizar en el servidor exigiria un adaptador,
 * que supondria un runtime en la capa publica (no permitido en esta fase).
 *
 * La solucion que respeta las reglas: TODAS las vistas de datos se pintan en
 * el navegador, en un unico shell estatico. Nada se congela en el build, no
 * hace falta adaptador y la capa publica sigue siendo estatica.
 *
 * Reglas heredadas (NO se duplican, viven en `api.ts` y `vistas.ts`):
 *   - UNKNOWN se muestra como UNKNOWN;
 *   - un recorte declara cuanto falta;
 *   - la API se llama siempre por el mismo modulo.
 */
import { consultar, dato, noDisponible, type Envelope } from './api';
import { esc, Vacio, trunc, tablaEventos } from './escapes';
// Explorador geográfico: datos y renderer van en modulos separados.
import { datosArea, datosPunto } from './geografia';
import { renderMapa, renderLeyenda, rotuloArea } from './mapa';

export const LIMITE = 50;

/** Lee los parametros de la URL de la vista actual. */
export function paginaActual(sp: URLSearchParams): { pagina: number; offset: number } {
  const pagina = Math.max(1, Number(sp.get('page') ?? '1') || 1);
  return { pagina, offset: (pagina - 1) * LIMITE };
}

/** Paginacion que CONSERVA los filtros actuales. */
export function paginacion(sp: URLSearchParams, pagina: number, total: number): string {
  const paginas = Math.max(1, Math.ceil(total / LIMITE));
  if (paginas <= 1) return '';
  const url = (n: number) => {
    const p = new URLSearchParams(sp);
    p.set('page', String(n));
    return `?${p.toString()}`;
  };
  return `<nav class="paginacion" aria-label="Pagination">
    ${pagina > 1 ? `<a href="${esc(url(pagina - 1))}">&larr; Previous</a>` : '<span></span>'}
    <span>Page ${pagina} of ${paginas}</span>
    ${pagina < paginas ? `<a href="${esc(url(pagina + 1))}">Next &rarr;</a>` : '<span></span>'}
  </nav>`;
}

export const num = (n: number) => n.toLocaleString('es');

export const enlace = (tipo: string, id: unknown, texto: string) =>
  `<a href="/${tipo}/${encodeURIComponent(String(id))}">${esc(texto)}</a>`;

export const totalDe = (env: Envelope<unknown>) => env.meta?.total ?? env.total_encontrados ?? 0;

export const cabecera = (titulo: string, cuerpo: string) => `
  <p class="eyebrow"><a href="/world">World Explorer</a></p>
  <h1>${esc(titulo)}</h1>
  ${cuerpo}`;

export const fallo = (titulo: string, env: Envelope<unknown>) =>
  cabecera(titulo, `<p class="aviso-api" role="status"><b>${esc(noDisponible())}.</b> ${esc(env.error?.mensaje ?? '')}</p>`);

/* --------------------------------------------------------------- LISTADOS -- */

/** Listado generico: figuras, entidades, sitios o artefactos. */
export async function listado(
  tipo: 'figures' | 'entities' | 'sites' | 'artifacts',
  registro: string,
  titulo: string,
  sp: URLSearchParams,
): Promise<string> {
  const { pagina, offset } = paginaActual(sp);
  const env = await consultar<any[]>(['api', 'listar', registro], { limit: LIMITE, offset });
  if (!env.ok) return fallo(titulo, env);

  const t = totalDe(env);
  const filas = (Array.isArray(env.data) ? env.data : []).map((r) => {
    const nombre = tipo === 'artifacts'
      ? dato(r.nombre !== 'UNKNOWN' ? r.nombre : r.nombre_item)
      : dato(r.nombre);
    const tipoTxt =
      tipo === 'sites' ? dato(r.tipo)
      : tipo === 'artifacts' ? dato(r.subtipo ?? r.material)
      : dato(r.race);
    const notas =
      tipo === 'entities' ? `${r.figuras ?? 0} figures / ${r.sitios ?? 0} sites` : '';
    return `<tr>
      <th scope="row">${enlace(tipo, r.df_id, nombre)}</th>
      <td>${esc(tipoTxt)}</td>
      <td><code>${esc(r.df_id)}</code></td>
      <td>${esc(notas)}</td>
    </tr>`;
  }).join('');

  return cabecera(titulo, `
    <p class="nota">${num(t)} ${esc(titulo.toLowerCase())} recorded in this world.</p>
    ${trunc(env)}
    <div class="tabla-scroll"><table class="tabla">
      <thead><tr>
        <th scope="col">Name</th><th scope="col">Type</th>
        <th scope="col">ID</th><th scope="col">Notes</th>
      </tr></thead>
      <tbody>${filas || `<tr><td colspan="4">${Vacio}</td></tr>`}</tbody>
    </table></div>
    ${paginacion(sp, pagina, t)}`);
}
/* ---------------------------------------------------------------- EVENTOS -- */

/** Explorador de eventos con filtros combinados, y vista de timeline. */
export async function vistaEventos(sp: URLSearchParams, timeline: boolean): Promise<string> {
  const titulo = timeline ? 'Timeline' : 'Events';
  const { pagina, offset } = paginaActual(sp);

  // Todos los filtros van juntos a la API, que es quien los combina. El rango
  // de anios NO se ignora cuando hay figura o sitio.
  const env = await consultar<any[]>(['api', 'eventos'], {
    from: sp.get('from') ?? '', to: sp.get('to') ?? '',
    figure: sp.get('figure') ?? '', entity: sp.get('entity') ?? '',
    site: sp.get('site') ?? '', type: sp.get('type') ?? '',
    limit: LIMITE, offset,
  });
  if (!env.ok) return fallo(titulo, env);

  let tipos: any[] = [];
  if (!timeline) {
    const te = await consultar<any[]>(['api', 'eventos', 'tipos']);
    if (te.ok && Array.isArray(te.data)) tipos = te.data;
  }

  const t = totalDe(env);
  const filas = Array.isArray(env.data) ? env.data : [];
  const v = (k: string) => esc(sp.get(k) ?? '');
  const action = timeline ? '/timeline' : '/events';

  const filtros = `<form class="filtros" method="get" action="${action}">
      <label>From <input type="number" name="from" value="${v('from')}" min="1"></label>
      <label>To <input type="number" name="to" value="${v('to')}" min="1"></label>
      ${timeline ? '' : `<label>Figure <input type="number" name="figure" value="${v('figure')}"></label>`}
      ${timeline ? '' : `<label>Entity <input type="number" name="entity" value="${v('entity')}"></label>`}
      ${timeline ? '' : `<label>Site <input type="number" name="site" value="${v('site')}"></label>`}
      ${timeline ? '' : `<label>Type<select name="type"><option value="">All</option>
        ${tipos.map((x) => `<option value="${esc(x.tipo)}"${sp.get('type') === x.tipo ? ' selected' : ''}>${esc(x.tipo)} (${x.eventos})</option>`).join('')}
      </select></label>`}
      <button type="submit">Apply</button>
      <a class="limpiar" href="${action}">Clear</a>
    </form>`;

  const cuerpo = timeline
    ? (filas.length
        ? `<ol class="linea-temporal">${filas.map((e) => `<li class="hito">
             <span class="hito-anio">${esc(e['año'] ?? 'Unknown')}</span>
             <div class="hito-cuerpo">
               ${enlace('events', e.evento_id, dato(e.tipo) + (e.subtipo ? ` · ${dato(e.subtipo)}` : ''))}
               <p class="hito-meta">${e.figura_id ? enlace('figures', e.figura_id, dato(e.figura_nombre)) : 'Unknown figure'}
                 · ${e.sitio_id ? enlace('sites', e.sitio_id, dato(e.sitio_nombre)) : 'Unknown site'}</p>
             </div></li>`).join('')}</ol>`
        : Vacio)
    : tablaEventos(filas);

  return cabecera(titulo, `
    <p class="nota">${num(t)} events ${timeline ? 'in this range, in chronological order' : 'match the current filters'}.</p>
    ${filtros}
    ${trunc(env)}
    ${cuerpo}
    ${paginacion(sp, pagina, t)}`);
}
/* -------------------------------------------------------------- BUSQUEDA -- */

const RUTA_BUSQUEDA: Record<string, { ruta: string; etiqueta: string }> = {
  historical_figures: { ruta: 'figures', etiqueta: 'Figures' },
  entities: { ruta: 'entities', etiqueta: 'Entities' },
  sites: { ruta: 'sites', etiqueta: 'Sites' },
  artifacts: { ruta: 'artifacts', etiqueta: 'Artifacts' },
  historical_events: { ruta: 'events', etiqueta: 'Events' },
};

/**
 * Busqueda global.
 *
 * REGLA: una consulta ambigua NUNCA se resuelve sola. Se declara y se muestra
 * la lista; elige la persona. Casos cubiertos: cero, uno, varios y ambiguo.
 */
export async function vistaBusqueda(sp: URLSearchParams): Promise<string> {
  const q = (sp.get('q') ?? '').trim();
  const form = `<form class="buscador" method="get" action="/search" role="search">
    <label class="visually-hidden" for="q">Search the world</label>
    <input id="q" name="q" type="search" value="${esc(q)}" placeholder="Search the world…" autocomplete="off">
    <button type="submit">Search</button></form>`;

  if (!q) {
    return cabecera('Search', `${form}<p class="nota">Type a name to search figures, entities, sites, artifacts and events.</p>`);
  }

  const env = await consultar<any>(['api', 'buscar'], { q });
  if (!env.ok) {
    return cabecera('Search', `${form}<p class="aviso-api" role="status"><b>${esc(noDisponible())}.</b> ${esc(env.error?.mensaje ?? '')}</p>`);
  }

  const grupos = (Array.isArray(env.data) ? env.data : []) as any[];
  const conDatos = grupos.filter((g) => (g.ids ?? []).length > 0);
  const cuantos = conDatos.reduce((n, g) => n + g.ids.length, 0);
  const ambigua = (env as any).consulta_ambigua === true;

  let aviso = '';
  if (cuantos === 0) {
    aviso = `<p class="vacio">No results for <q>${esc(q)}</q>.</p>`;
  } else if (ambigua) {
    aviso = `<p class="aviso-ambigua" role="status">Several records match <q>${esc(q)}</q>.
      Nothing was selected automatically &mdash; choose the one you meant.</p>
      <p class="nota">${cuantos} results for <q>${esc(q)}</q>.</p>`;
  } else {
    aviso = `<p class="nota">${cuantos} result${cuantos === 1 ? '' : 's'} for <q>${esc(q)}</q>.</p>`;
  }

  const secciones = conDatos.map((g) => {
    const meta = RUTA_BUSQUEDA[g.tipo] ?? { ruta: 'figures', etiqueta: g.tipo };
    const items = g.ids
      .map((id: string) => `<li>${enlace(meta.ruta, id, `#${id}`)} <span class="tag">${esc(meta.etiqueta)}</span></li>`)
      .join('');
    const recorta = g.truncado
      ? `<p class="truncado">Showing ${g.ids.length} of ${g.total_encontrados}</p>` : '';
    return `<section class="panel"><h2>${esc(meta.etiqueta)}
      <span class="contador">(${esc(String(g.total_encontrados))})</span></h2>
      ${recorta}<ul class="lista-rel">${items}</ul></section>`;
  }).join('');

  return cabecera('Search', `${form}${aviso}${secciones}`);
}

/* ------------------------------------------------------------ GEOGRAFIA --- */

/**
 * Explorador geográfico: mapa + consulta por coordenadas.
 *
 * Se apoya en DOS modulos separados a propósito:
 *   - `geografia.ts` (datos) pide las coordenadas a la API;
 *   - `mapa.ts`     (renderer) dibuja los sitios que le llegan.
 *
 * Sustituir el SVG por un mapa interactivo real sería reescribir `renderMapa()`
 * y nada más: ni la API, ni el núcleo, ni los contratos, ni estas URLs.
 */
export async function vistaGeografia(sp: URLSearchParams): Promise<string> {
  const capas = [
    { id: 'rivers', etiqueta: 'Rivers' },
    { id: 'landmasses', etiqueta: 'Landmasses' },
    { id: 'mountain_peaks', etiqueta: 'Mountain peaks' },
    { id: 'world_constructions', etiqueta: 'World constructions' },
  ];
  const capa = sp.get('capa') ?? 'rivers';
  const { pagina, offset } = paginaActual(sp);

  // `?x=&y=` consulta un punto; `?mx=&my=&ancho=` mueve el mapa. Sin nada, se
  // muestra el mundo entero, que son solo 734 sitios: cabe de sobra.
  const xPedida = enteroDe(sp.get('x'));
  const yPedida = enteroDe(sp.get('y'));
  const hayPunto = xPedida !== null && yPedida !== null;

  const mx = enteroDe(sp.get('mx')) ?? (hayPunto ? xPedida : 0);
  const my = enteroDe(sp.get('my')) ?? (hayPunto ? yPedida : 0);
  const ancho = Math.min(128, Math.max(8, enteroDe(sp.get('ancho')) ?? 64));
  const alto = Math.min(128, Math.max(8, enteroDe(sp.get('alto')) ?? 64));

  const [resumen, vista, punto] = await Promise.all([
    consultar<any>(['api', 'geografia']),
    datosArea(mx, my, ancho, alto),
    hayPunto ? datosPunto(xPedida, yPedida) : Promise.resolve(null),
  ]);

  const env = await consultar<any[]>(['api', 'geografia', capa], { limit: LIMITE, offset });
  if (!env.ok) return fallo('Geography', env);

  const t = totalDe(env);
  const items = Array.isArray(env.data) ? env.data : [];
  const filas = items.map((i) => `<li>
      ${i.df_id ? enlace('artifacts', i.df_id, dato(i.nombre)) : `<span>${esc(dato(i.nombre))}</span>`}
      <span class="tag">${esc(dato(i.coordenadas ?? 'no coordinates'))}</span>
    </li>`).join('');

  const capasNav = `<nav class="capas" aria-label="Geography layers">${capas.map((c) =>
    `<a href="/geography?capa=${c.id}"${capa === c.id ? ' aria-current="page"' : ''}>${esc(c.etiqueta)}</a>`).join('')}</nav>`;

  const resumenHtml = resumen.ok && resumen.data
    ? `<section class="panel"><h2>Layers</h2><dl class="definiciones">${capas.map((c) =>
        `<div><dt>${esc(c.etiqueta)}</dt><dd>${esc(String((resumen.data as any)[c.id]?.registros ?? 'Unknown'))}</dd></div>`).join('')}</dl>
       ${(resumen.data as any).nota_rivers ? `<p class="nota">${esc((resumen.data as any).nota_rivers)}</p>` : ''}</section>`
    : '';

  return cabecera('Geography', `
    <p class="nota">Every position below is read from the data. A shared coordinate is a
    <em>position</em>, not a relationship: two sites on the same patch are not shown as
    related to each other.</p>
    ${formCoordenadas(hayPunto, xPedida, yPedida)}
    ${hayPunto ? panelPunto(punto, xPedida, yPedida) : ''}
    ${panelMapa(vista, mx, my, ancho, alto)}
    ${resumenHtml}
    ${capasNav}
    ${trunc(env)}
    ${filas ? `<ul class="lista-rel">${filas}</ul>` : Vacio}
    ${paginacion(sp, pagina, t)}
    <p class="nota">Sites with coordinates are reachable from <a href="/sites">Sites</a>.</p>`);
}
/* --- Explorador geográfico: piezas --------------------------------------- */

/** Formulario X / Y. Z no se ofrece: no existe en los datos. */
function formCoordenadas(hayPunto: boolean, x: number | null, y: number | null): string {
  return `<section class="panel">
      <h2>Explore a coordinate</h2>
      <form class="form-coords" role="search" data-form-coords>
        <div class="campo"><label for="coord-x">X</label>
          <input id="coord-x" name="x" type="number" inputmode="numeric" step="1"
                 value="${hayPunto ? esc(String(x)) : ''}" placeholder="112" required></div>
        <div class="campo"><label for="coord-y">Y</label>
          <input id="coord-y" name="y" type="number" inputmode="numeric" step="1"
                 value="${hayPunto ? esc(String(y)) : ''}" placeholder="20" required></div>
        <div class="campo"><button type="submit">Explore</button></div>
      </form>
      <p class="nota">X and Y are Dwarf Fortress <em>world coordinates</em>: a patch of the
      global map, read from the file. There is <strong>no Z</strong> in the data, so it is
      reported as <code>null</code> and never guessed.</p>
    </section>`;
}

/** Panel del mapa. En móvil va debajo del resultado; el CSS lo coloca. */
function panelMapa(v: any, mx: number, my: number, ancho: number, alto: number): string {
  if (!v) {
    return `<section class="panel"><h2>World map</h2>${Vacio}</section>`;
  }
  return `<section class="panel">
      <h2>World map <span class="contador">(${v.sitios.length} sites)</span></h2>
      <p class="nota">Real recorded area ${esc(rotuloArea(v.area))}. Nothing is drawn here
      that is not in the data: no coasts, no borders, no mountains.</p>
      ${renderMapa(v.sitios, v.area, { destacado: null })}
      ${renderLeyenda(v.tipos)}
      <nav class="mapa-nav" aria-label="Move the map">
        ${botonArea('←', mx - ancho, my, ancho, alto)}
        ${botonArea('↑', mx, my - alto, ancho, alto)}
        ${botonArea('↓', mx, my + alto, ancho, alto)}
        ${botonArea('→', mx + ancho, my, ancho, alto)}
        ${botonArea('larger', mx, my, Math.min(128, ancho * 2), Math.min(128, alto * 2))}
        ${botonArea('whole world', 0, 0, 128, 128)}
      </nav>
    </section>`;
}

/** Enlace que mueve el mapa. Solo cambia la vista, nunca los datos. */
function botonArea(etiqueta: string, mx: number, my: number, ancho: number, alto: number): string {
  return `<a class="boton-mapa" href="/geography?mx=${mx}&my=${my}&ancho=${ancho}&alto=${alto}">${esc(etiqueta)}</a>`;
}

/** Resultado del punto consultado. No rellena lo que no existe. */
function panelPunto(p: any, x: number, y: number): string {
  if (!p) {
    return `<section class="panel"><h2>Location ${x}, ${y}</h2>${Vacio}</section>`;
  }
  const c = p.coordenada ?? { x, y, z: null };

  const filasSitios = (p.sitios ?? []).map((s: any) => `<li>
      <a href="/sites/${encodeURIComponent(String(s.df_id))}">${esc(dato(s.nombre))}</a>
      <span class="tag tag--tipo">${esc(dato(s.tipo))}</span>
    </li>`).join('');

  const capas = Object.entries(p.capas ?? {}).map(([nombre, items]: [string, any]) => {
    if (!Array.isArray(items) || !items.length) return '';
    const li = items.slice(0, 25).map((i: any) => `<li>
        <span>${esc(dato(i.nombre))}</span>
        ${i.tipo ? `<span class="tag">${esc(dato(i.tipo))}</span>` : ''}
        <span class="tag">${i.coordenadas?.length ?? 0} pt</span>
      </li>`).join('');
    const mas = items.length > 25
      ? `<p class="truncado">Showing 25 of ${items.length}</p>` : '';
    return `<section class="subpanel">
        <h3>${esc(capaEtiqueta(nombre))} <span class="contador">(${items.length})</span></h3>
        <ul class="lista-rel">${li}</ul>${mas}</section>`;
  }).join('');

  const vacio = (p.total_sitios ?? 0) === 0 && (p.total_registros_capas ?? 0) === 0
    ? `<p class="vacio">Nothing is recorded at this coordinate. That does not mean nothing
       existed there: it means the file does not say.</p>` : '';

  return `<section class="panel">
      <h2>Location ${esc(String(c.x))}, ${esc(String(c.y))}</h2>
      <dl class="definiciones">
        <div><dt>X</dt><dd>${esc(String(c.x))} <span class="cert">FACT</span></dd></div>
        <div><dt>Y</dt><dd>${esc(String(c.y))} <span class="cert">FACT</span></dd></div>
        <div><dt>Z</dt><dd><code>${c.z === null ? 'null' : esc(String(c.z))}</code>
          <span class="cert">UNKNOWN</span></dd></div>
        <div><dt>Method</dt><dd>${esc(metodoEn(p.coordenadas?.metodo))}</dd></div>
      </dl>
      ${vacio}
      ${filasSitios ? `<section class="subpanel">
          <h3>Sites <span class="contador">(${p.sitios.length})</span></h3>
          <ul class="lista-rel">${filasSitios}</ul></section>` : ''}
      ${capas}
      <p class="nota">Positions are FACT. The link between records that share a coordinate
      is DERIVED: sharing a patch is a position, not a relationship.</p>
    </section>`;
}

/** Etiqueta de capa legible. */
function capaEtiqueta(id: string): string {
  return ({
    rivers: 'Rivers',
    landmasses: 'Landmasses',
    mountain_peaks: 'Mountain peaks',
    world_constructions: 'World constructions',
  } as Record<string, string>)[id] ?? id;
}

/**
 * Traduce al ingles la descripcion del metodo que emite el nucleo.
 *
 * El núcleo esta en español y su salida es la fuente de verdad; lo que se
 * traduce es solo el texto para la vista, nunca el dato.
 */
function metodoEn(m: string | undefined): string {
  if (!m) return 'exact coordinate';
  if (m.includes('exakta')) return 'exact shared coordinate (x, y)';
  return m;
}

/** Lee un entero de la URL. `null` si no es un número utilizable. */
function enteroDe(v: string | null): number | null {
  if (v === null || v.trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}