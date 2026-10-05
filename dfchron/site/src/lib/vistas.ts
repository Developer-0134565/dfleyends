/**
 * Vistas de FICHA, renderizadas en el cliente.
 *
 * POR QUE EN EL CLIENTE Y NO EN EL SERVIDOR
 * ------------------------------------------
 * Una ficha se pide por id bajo demanda (`/figures/712`). Hay 11.144 figuras y
 * 57.215 eventos: pre-renderizar eso en build es insostenible, y Astro solo
 * permite render en servidor si se instala un adaptador, que supondria un
 * runtime en la capa publica.
 *
 * Este proyecto NO quiere todavia eso (la capa publica sigue siendo estatica).
 * Asi que las fichas se pintan en el navegador: la pagina es un shell estatico
 * y el contenido llega desde la API por `api.ts`.
 *
 * REGLAS QUE SE RESPETAN AQUI (estan en `api.ts`, no se duplican):
 *   - la direccion de la API se lee de un solo sitio;
 *   - UNKNOWN se muestra como UNKNOWN, nunca como una afirmacion;
 *   - un resultado truncado declara cuanto falta;
 *   - el grafo de relaciones es dirigido: no se invierte.
 */
import {
  consultar, hayApi, dato, noDisponible, avisoTruncamiento, type Envelope,
  lineaEstado, panelEvidencia,
} from './api';
import { esc, badge, Vacio, trunc, tablaEventos, contar } from './escapes';
import { listado, vistaEventos, vistaBusqueda, vistaGeografia } from './listados';
import {
  estadoDataset, avisoDataset, panelDataset, type EstadoDataset,
} from './dataset';

/** Badge de certidumbre. La implementación vive en `escapes.ts`; aquí se
 *  reexporta para no romper a quien ya la importaba desde este módulo. */
export { badge } from './escapes';


/** Bloque de pares etiqueta/valor. */
export function defs(pares: Array<[string, string]>, nota?: string): string {
  const cuerpo = pares.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join('');
  const n = nota ? `<p class="nota">${esc(nota)}</p>` : '';
  return `<dl class="definiciones">${cuerpo}</dl>${n}`;
}

export function noEncontrado(que: string, id: string, volverA: string): string {
  return `
    <h1>${esc(que)} not found</h1>
    <p class="aviso-api" role="status">No ${esc(que.toLowerCase())} exists with id
    <code>${esc(id)}</code> in this world.</p>
    <p><a href="${esc(volverA)}">Back to the list</a></p>`;
}

export function sinApi(): string {
  return `
    <h1>Data unavailable</h1>
    <p class="aviso-api" role="status">This build has no API configured, so
    details cannot be shown. Set <code>PUBLIC_API_BASE_URL</code> to connect
    to the local API.</p>`;
}

/** Enlace a otra ficha si el campo trae id; si no, dice Unknown. */
export function vinculo(campo: any, tipo: string): string {
  return campo?.df_id
    ? `<a href="/${tipo}/${encodeURIComponent(String(campo.df_id))}">${esc(dato(campo.nombre))}</a>`
    : 'Unknown';
}

const Vacio = `<p class="vacio">Data unavailable</p>`;

/* ----------------------------------------------------------------- FIGURA -- */
export async function fichaFigura(id: string): Promise<string> {
  const f = await consultar<Record<string, any>>(['api', 'figuras', id]);
  if (!f.ok) return noEncontrado('Figure', id, '/figures');
  const d = f.data;

  const evs = await consultar<any[]>(['api', 'figuras', id, 'eventos'], { limit: 50 });
  const rel = await consultar<any[]>(['api', 'figuras', id, 'relaciones'], { limit: 50 });
  const art = await consultar<any[]>(['api', 'figuras', id, 'artefactos']);

  const anio = (x: any) => (typeof x?.['aÃ±o'] === 'number' ? String(x['aÃ±o']) : 'Unknown');

  // Relaciones: se muestra SOLO la direccion que devuelve la API. El grafo es
  // dirigido: que A tenga relacion con B NO implica la inversa.
  const relaciones = (rel.ok && Array.isArray(rel.data) ? rel.data : [])
    .map(
      (r) =>
        `<li><a href="/figures/${encodeURIComponent(String(r.figura_id))}">${esc(dato(r.nombre))}</a>` +
        ` <span class="tag">${esc(dato(r.tipo))}</span> ${badge(r.certainty ?? 'FACT')}</li>`,
    )
    .join('');

  const artefactos = (art.ok && Array.isArray(art.data) ? art.data : [])
    .map((a) => `<li><a href="/artifacts/${encodeURIComponent(String(a.df_id))}">${esc(dato(a.nombre))}</a></li>`)
    .join('');

  const eventos = (evs.ok && Array.isArray(evs.data) ? evs.data : []) as any[];

  return `
    ${lineaEstado(f)}
    <h1>${esc(dato(d.nombre))}</h1>
    <p class="ficha-sub"><code>${esc(d.df_id)}</code> ${badge(d.certainty ?? 'FACT')}</p>

    ${panelEvidencia(f)}

    <section class="panel"><h2>Identity</h2>
      ${defs([
        ['Name', esc(dato(d.nombre))],
        ['ID', `<code>${esc(d.df_id)}</code>`],
        ['Race', esc(dato(d.race))],
        ['Caste', esc(dato(d.caste))],
        ['Sex', esc(dato(d.sexo))],
        ['Born', esc(anio(d.nacimiento))],
        ['Died', esc(anio(d.muerte))],
      ], '`Unknown` means the XML does not record it. It does NOT mean the figure is alive, nor that the event never happened.')}
    </section>

    <section class="panel"><h2>Entity &amp; site</h2>
      ${defs([
        ['Entity', vinculo(d.entidad, 'entities')],
        ['Site', vinculo(d.sitio, 'sites')],
      ])}
    </section>

    <section class="panel"><h2>Relationships</h2>
      <p class="nota">Directed graph: only the documented direction is shown; the reverse is never inferred.</p>
      ${trunc(rel)}
      ${relaciones ? `<ul class="lista-rel">${relaciones}</ul>` : Vacio}
    </section>

    <section class="panel"><h2>Artifacts</h2>
      ${artefactos ? `<ul class="lista-rel">${artefactos}</ul>` : Vacio}
    </section>

    <section class="panel"><h2>Events &amp; chronology</h2>
      ${trunc(evs)}
      ${tablaEventos(eventos)}
    </section>`;
}

/* --------------------------------------------------------------- ENTIDAD -- */
export async function fichaEntidad(id: string): Promise<string> {
  const f = await consultar<Record<string, any>>(['api', 'entidades', id]);
  if (!f.ok) return noEncontrado('Entity', id, '/entities');
  const d = f.data;

  const miem = await consultar<any[]>(['api', 'entidades', id, 'miembros'], { limit: 50 });
  const sit = await consultar<any[]>(['api', 'entidades', id, 'sitios'], { limit: 50 });
  const evs = await consultar<any[]>(['api', 'entidades', id, 'eventos'], { limit: 50 });

  const miembros = (miem.ok && Array.isArray(miem.data) ? miem.data : [])
    .map((m) => `<li><a href="/figures/${encodeURIComponent(String(m.df_id))}">${esc(dato(m.nombre))}</a> <span class="tag">${esc(dato(m.race))}</span></li>`)
    .join('');
  const sitios = (sit.ok && Array.isArray(sit.data) ? sit.data : [])
    .map((s) => `<li><a href="/sites/${encodeURIComponent(String(s.df_id))}">${esc(dato(s.nombre))}</a> <span class="tag">${esc(dato(s.tipo))}</span></li>`)
    .join('');
  const eventos = (evs.ok && Array.isArray(evs.data) ? evs.data : []) as any[];

  return `
    <h1>${esc(dato(d.nombre))}</h1>
    <p class="ficha-sub"><code>${esc(d.df_id)}</code></p>

    <section class="panel"><h2>Summary</h2>
      ${defs([
        ['Name', esc(dato(d.nombre))],
        ['ID', `<code>${esc(d.df_id)}</code>`],
        ['Race', esc(dato(d.race))],
        ['Members', contar(d.figuras)],
        ['Sites', contar(d.sitios)],
        ['Events', contar(d.eventos)],
      ])}
    </section>

    <section class="panel"><h2>Members</h2>
      ${trunc(miem)}${miembros ? `<ul class="lista-rel">${miembros}</ul>` : Vacio}
    </section>
    <section class="panel"><h2>Sites</h2>
      ${trunc(sit)}${sitios ? `<ul class="lista-rel">${sitios}</ul>` : Vacio}
    </section>
    <section class="panel"><h2>Events</h2>
      ${trunc(evs)}${tablaEventos(eventos)}
    </section>`;
}
/* ----------------------------------------------------------------- SITIO -- */
export async function fichaSitio(id: string): Promise<string> {
  const f = await consultar<Record<string, any>>(['api', 'sitios', id]);
  if (!f.ok) return noEncontrado('Site', id, '/sites');
  const d = f.data;

  const figs = await consultar<any[]>(['api', 'sitios', id, 'figuras'], { limit: 50 });
  const evs = await consultar<any[]>(['api', 'sitios', id, 'eventos'], { limit: 50 });
  const geo = await consultar<any[]>(['api', 'sitios', id, 'geografia']);

  // `tipo` es el tipo REAL del XML (fortress, cave, ...). No se sustituye por
  // la palabra generica "site": el tipo es parte del dato.
  const crds = d.coordenadas;
  const coords =
    Array.isArray(crds) && crds.length
      ? crds.map((p: any) => `(${esc(p?.[0])}, ${esc(p?.[1])})`).join(' ')
      : 'Data unavailable';

  const figuras = (figs.ok && Array.isArray(figs.data) ? figs.data : [])
    .map((x) => `<li><a href="/figures/${encodeURIComponent(String(x.df_id))}">${esc(dato(x.nombre))}</a> <span class="tag">${esc(dato(x.race))}</span></li>`)
    .join('');
  const eventos = (evs.ok && Array.isArray(evs.data) ? evs.data : []) as any[];

  const construcciones = (geo.ok && Array.isArray(geo.data) ? geo.data : [])
    .map((c) => `<li>${esc(dato(c.nombre))} <span class="tag">${esc(dato(c.tipo))}</span></li>`)
    .join('');
  const notaGeo = (geo as any)?.nota ? `<p class="nota">${esc((geo as any).nota)}</p>` : '';

  return `
    <h1>${esc(dato(d.nombre))}</h1>
    <p class="ficha-sub"><code>${esc(d.df_id)}</code> <span class="tag tag--tipo">${esc(dato(d.tipo))}</span></p>

    <section class="panel"><h2>Site</h2>
      ${defs([
        ['Name', esc(dato(d.nombre))],
        ['ID', `<code>${esc(d.df_id)}</code>`],
        ['Type', esc(dato(d.tipo))],
        ['Coordinates', coords],
        ['Associated figures', contar(d.figuras_asociadas)],
        ['Events', contar(d.eventos)],
        ['Artifacts', contar(d.artefactos)],
        ['Civilization', vinculo(d.civilizacion, 'entities')],
        ['Current owner', vinculo(d.propietario_actual, 'entities')],
      ])}
    </section>

    <section class="panel"><h2>Geography</h2>
      ${notaGeo}
      ${construcciones ? `<ul class="lista-rel">${construcciones}</ul>` : Vacio}
    </section>

    <section class="panel"><h2>Figures here</h2>
      ${trunc(figs)}${figuras ? `<ul class="lista-rel">${figuras}</ul>` : Vacio}
    </section>

    <section class="panel"><h2>Events</h2>
      ${trunc(evs)}${tablaEventos(eventos)}
    </section>`;
}

/* -------------------------------------------------------------- ARTEFACTO -- */
export async function fichaArtefacto(id: string): Promise<string> {
  const f = await consultar<Record<string, any>>(['api', 'artefactos', id]);
  if (!f.ok) return noEncontrado('Artifact', id, '/artifacts');
  const d = f.data;
  const evs = await consultar<any[]>(['api', 'artefactos', id, 'eventos'], { limit: 50 });
  const duenos = await consultar<any>(['api', 'artefactos', id, 'propietarios']);

  const nombre = dato(d.nombre !== 'UNKNOWN' ? d.nombre : d.nombre_item);
  // El propietario NO se deduce del sitio ni de la civilizacion: si no consta,
  // se dice Unknown.
  const dueno = d.propietario_hfid
    ? `<a href="/figures/${encodeURIComponent(String(d.propietario_hfid))}">${esc(dato(d.propietario_nombre))}</a>`
    : 'Unknown';
  const sitio = d.sitio_id
    ? `<a href="/sites/${encodeURIComponent(String(d.sitio_id))}">${esc(dato(d.sitio_nombre))}</a>`
    : 'Unknown';

  const eventos = (evs.ok && Array.isArray(evs.data) ? evs.data : []) as any[];
  const notaDuenos = duenos.ok && (duenos.data as any)?.propietarios
    ? `<p class="nota">${(duenos.data as any).propietarios.length} ownership record(s).</p>`
    : '';

  return `
    <h1>${esc(nombre)}</h1>
    <p class="ficha-sub"><code>${esc(d.df_id)}</code></p>

    <section class="panel"><h2>Artifact</h2>
      ${defs([
        ['Name', esc(nombre)],
        ['ID', `<code>${esc(d.df_id)}</code>`],
        ['Subtype', esc(dato(d.subtipo))],
        ['Material', esc(dato(d.material))],
        ['Written', d.es_escrito === true ? 'Yes' : 'No'],
        ['Owner', dueno],
        ['Site', sitio],
      ], '`Unknown` means the data does not record an owner. It is not a guess.')}
    </section>

    <section class="panel"><h2>Relationships</h2>${notaDuenos || Vacio}</section>

    <section class="panel"><h2>Events</h2>
      ${trunc(evs)}${tablaEventos(eventos)}
    </section>`;
}

/* ----------------------------------------------------------------- EVENTO -- */
export async function fichaEvento(id: string): Promise<string> {
  const f = await consultar<Record<string, any>>(['api', 'eventos', id]);
  if (!f.ok) return noEncontrado('Event', id, '/events');
  const d = f.data;

  const participantes = Array.isArray(d.participantes) ? d.participantes.length : 0;
  const relaciones = Array.isArray(d.relaciones) ? d.relaciones.length : 0;

  return `
    <h1>${esc(dato(d.tipo))}${d.subtipo ? ' Â· ' + esc(dato(d.subtipo)) : ''}</h1>
    <p class="ficha-sub"><code>${esc(d.df_id)}</code> ${badge(d.certainty ?? 'FACT')}</p>

    <section class="panel"><h2>Event</h2>
      ${defs([
        ['ID', `<code>${esc(d.df_id)}</code>`],
        ['Year', esc(String(d['aÃ±o'] ?? 'Unknown'))],
        ['Type', esc(dato(d.tipo))],
        ['Subtype', esc(dato(d.subtipo))],
        ['State', esc(dato(d.estado))],
        ['Figure', vinculo(d.figura, 'figures')],
        ['Entity', vinculo(d.entidad, 'entities')],
        ['Site', vinculo(d.sitio, 'sites')],
      ])}
    </section>

    <section class="panel"><h2>Participants</h2>
      ${participantes ? `<p class="nota">${participantes} recorded.</p>` : Vacio}
    </section>
    <section class="panel"><h2>Relationships</h2>
      ${relaciones ? `<p class="nota">${relaciones} recorded.</p>` : Vacio}
    </section>`;
}
/* --------------------------------------------------------------- DASHBOARD */

async function vistaMundo(): Promise<string> {
  const env = await consultar<Record<string, any>>(['api', 'estadisticas']);
  const d: Record<string, any> = env.ok ? (env.data as any) : {};
  // El mundo que hay delante. Viene de /api/salud, que lo lee del disco: si
  // se activó otro dataset, esto lo refleja aunque esta vista no se repinte.
  const ds = await estadoDataset();
  const n = (v: unknown) => (typeof v === 'number' ? v.toLocaleString('es') : 'Data unavailable');

  const tarjetas: Array<[string, string, unknown]> = [
    ['Figures', '/app/figures', d.figuras],
    ['Entities', '/app/entities', d.entidades],
    ['Sites', '/app/sites', d.sitios],
    ['Events', '/app/events', d.eventos],
    ['Artifacts', '/app/artifacts', d.artefactos],
    ['Relationships', '/app/events', d.relaciones],
  ];

  const rango =
    typeof d.anio_min === 'number' && typeof d.anio_max === 'number'
      ? `${esc(String(d.anio_min))} – ${esc(String(d.anio_max))}`
      : 'Data unavailable';

  const extra: Array<[string, unknown]> = [
    ['Years with events', d.anos_con_eventos],
    ['Rivers', d.rios],
    ['Landmasses', d.masas_tierra],
    ['Peaks', d.picos],
    ['World constructions', d.construcciones_mundo],
    ['Identities', d.identidades],
    ['Event collections', d.colecciones_eventos],
    ['Eras', d.eras],
  ];

  const cuerpo = env.ok
    ? `${panelDataset(ds)}
       <p class="certainty-line">These counts are ${badge('DERIVED')} &mdash; computed
         from the loaded data, not written in the XML.</p>
       <ul class="stats" role="list">${tarjetas.map(([et, href, v]) =>
         `<li class="stat"><a href="${href}"><span class="stat-value">${n(v)}</span>
          <span class="stat-label">${esc(et)}</span></a></li>`).join('')}</ul>
       <section class="panel"><h2>Time range</h2>
         <p class="dato-grande">${rango}</p>
         <p><a href="/app/timeline">Open the timeline</a></p></section>
       <section class="panel"><h2>Also in this world</h2>
         <dl class="definiciones">${extra.map(([k, v]) =>
           `<div><dt>${esc(k)}</dt><dd>${n(v)}</dd></div>`).join('')}</dl>
         <p><a href="/app/geography">Explore geography</a></p></section>`
    : `<p class="aviso-api" role="status"><b>Data unavailable.</b> The API did not
         return world statistics${env.error?.mensaje ? `: ${esc(env.error.mensaje)}` : '.'}
         The figures are not shown because inventing them would be worse than showing nothing.</p>
       <ul class="stats" role="list">${tarjetas.map(([et]) =>
         `<li class="stat"><span class="stat-value stat-value--vacio">Data unavailable</span>
          <span class="stat-label">${esc(et)}</span></li>`).join('')}</ul>
       <section class="panel"><h2>Time range</h2><p class="dato-grande">Data unavailable</p></section>`;

  return `
    <p class="eyebrow">World Explorer</p>
    <h1>The loaded world</h1>
    ${cuerpo}
    <section class="panel"><h2>Search the world</h2>
      <form class="buscador" action="/app/search" method="get" role="search">
        <label class="visually-hidden" for="q">Search the world</label>
        <input id="q" name="q" type="search" placeholder="Search the world…" autocomplete="off">
        <button type="submit">Search</button></form>
      <p class="nota">Finds figures, entities, sites, artifacts and events. Ambiguous
      names are never resolved silently.</p></section>`;
}
/* --------------------------------------------------------------- ENRUTADOR */

type Vista =
  | { k: 'mundo' }
  | { k: 'listado'; tipo: 'figures' | 'entities' | 'sites' | 'artifacts' }
  | { k: 'eventos' }
  | { k: 'timeline' }
  | { k: 'busqueda' }
  | { k: 'geografia' }
  | { k: 'ficha'; tipo: 'figures' | 'entities' | 'sites' | 'artifacts' | 'events'; id: string }
  | { k: 'desconocido' };

const LISTAS = ['figures', 'entities', 'sites', 'artifacts'] as const;
const FICHAS = ['figures', 'entities', 'sites', 'artifacts', 'events'] as const;

/** Interpreta la URL y decide que vista se pinta. */
export function interpretar(pathname: string): Vista {
  const segs = pathname.replace(/^\/+|\/+$/g, '').split('/').filter(Boolean);
  if (segs.length === 0) return { k: 'mundo' };

  const esLista = (s: string) => (LISTAS as readonly string[]).includes(s);
  const esFicha = (s: string) => (FICHAS as readonly string[]).includes(s);

  const desambiguar = (r: string, f: string[]): Vista => {
    if (f.length === 1 && esFicha(r)) {
      try {
        return { k: 'ficha', tipo: r as any, id: decodeURIComponent(f[0]) };
      } catch {
        return { k: 'desconocido' };
      }
    }
    if (f.length === 0) {
      if (esLista(r)) return { k: 'listado', tipo: r as any };
      if (r === 'events') return { k: 'eventos' };
      if (r === 'timeline') return { k: 'timeline' };
      if (r === 'search') return { k: 'busqueda' };
      if (r === 'geography') return { k: 'geografia' };
      if (r === 'world') return { k: 'mundo' };
    }
    return { k: 'desconocido' };
  };

  // Ruta navegable bajo /app: /app/figures, /app/figures/712, ...
  if (segs[0] === 'app') {
    if (segs.length === 1) return { k: 'mundo' };
    return desambiguar(segs[1], segs.slice(2));
  }

  // URL limpia: /figures/712, /events, /world...
  return desambiguar(segs[0], segs.slice(1));
}

async function render(): Promise<string> {
  const v = interpretar(window.location.pathname);
  const sp = new URLSearchParams(window.location.search);

  switch (v.k) {
    case 'mundo':
      return vistaMundo();
    case 'listado': {
      const reg = {
        figures: 'historical_figures', entities: 'entities',
        sites: 'sites', artifacts: 'artifacts',
      }[v.tipo];
      const titulo =
        v.tipo === 'figures' ? 'Figures'
        : v.tipo[0].toUpperCase() + v.tipo.slice(1);
      return listado(v.tipo, reg, titulo, sp);
    }
    case 'eventos':
      return vistaEventos(sp, false);
    case 'timeline':
      return vistaEventos(sp, true);
    case 'busqueda':
      return vistaBusqueda(sp);
    case 'geografia':
      return vistaGeografia(sp);
    case 'ficha': {
      const fn = {
        figures: fichaFigura, entities: fichaEntidad, sites: fichaSitio,
        artifacts: fichaArtefacto, events: fichaEvento,
      }[v.tipo];
      return fn(v.id);
    }
    default:
      return `<h1>Page not found</h1><p class="aviso-api" role="status">This address does
        not match any view.</p><p><a href="/app/world">Back to the world</a></p>`;
  }
}

async function pintar(): Promise<void> {
  const raiz = document.getElementById('app');
  if (!raiz) return;
  if (!hayApi()) {
    raiz.innerHTML = sinApi();
    return;
  }
  raiz.innerHTML = '<p class="nota">Loading…</p>';
  try {
    raiz.innerHTML = await render();
  } catch {
    // Nunca se muestra un traceback: se dice que no se pudo cargar.
    raiz.innerHTML = `<h1>Data unavailable</h1><p class="aviso-api" role="status">
      The view could not be loaded. Check that the local API is running.</p>`;
  }
}

/**
 * Avisa si el mundo que hay en pantalla ya no es el que hay activo.
 *
 * Se llama al terminar cada pintado y al volver a la pestaña. NO hay polling:
 * comprobarlo cada segundo sería gastar peticiones para avisar de algo que
 * cambia una vez cada actualización manual, que además tarda minutos.
 */
async function comprobarCambioDataset(): Promise<void> {
  if (!hayApi()) return;
  if (document.querySelector('[data-aviso-dataset]')) return;  // ya avisado
  try {
    const ds = await estadoDataset();
    const aviso = avisoDataset(ds);
    if (!aviso) return;
    const raiz = document.getElementById('app');
    if (!raiz) return;
    // Se inserta al principio: es un aviso de contexto, no contenido.
    raiz.insertAdjacentHTML('afterbegin', aviso);
  } catch {
    // Si no se puede comprobar, no se molesta al usuario con un error.
  }
}

document.addEventListener('DOMContentLoaded', () => {
  void pintar().then(() => comprobarCambioDataset());
});

/** Al volver a la pestaña: ahí es cuando alguien puede notar el cambio. */
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') void comprobarCambioDataset();
});

/** El enlace "Reload" del aviso recarga de verdad, a petición del usuario. */
document.addEventListener('click', (ev) => {
  const t = ev.target as HTMLElement | null;
  if (t?.hasAttribute?.('data-recargar-pagina')) {
    ev.preventDefault();
    window.location.reload();
  }
});

/**
 * Formulario de coordenadas del explorador geográfico.
 *
 * Va por DELEGACION en `document`, no sobre el formulario: la vista se repinta
 * en cada navegacion, asi que un listenerDirecto dejaria de funcionar al
 * cambiar de pagina. Ademas se submit por GET, de modo que la URL resultant
 * (`/geography?x=112&y=20`) es compartible y sobrevive a una recarga.
 */
document.addEventListener('submit', (ev: Event) => {
  const objetivo = ev.target as HTMLElement | null;
  if (!objetivo || !objetivo.hasAttribute?.('data-form-coords')) return;
  ev.preventDefault();
  const f = objetivo as HTMLFormElement;
  const x = (f.querySelector('[name="x"]') as HTMLInputElement)?.value.trim();
  const y = (f.querySelector('[name="y"]') as HTMLInputElement)?.value.trim();
  if (x === undefined || y === undefined || x === '' || y === '') return;
  // Se avisa al backend, no al navegador: la API vuelve a validar.
  window.location.href = `/geography?x=${encodeURIComponent(x)}&y=${encodeURIComponent(y)}`;
});
