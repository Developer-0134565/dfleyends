/**
 * DF Legends :: renderizador de mapa (SVG)
 * =======================================
 *
 * SEGREGA DE LOS DATOS A PROPOSITO
 * ---------------------------------
 * Este modulo NO hace peticiones ni conoce la API. Recibe sitios ya
 * normalizados y devuelve una cadena SVG. Esa separacion es la que permite
 * sustituirlo por Leaflet, Mapbox o un mapa interactivo sin tocar la API, el
 * nucleo, los contratos, las URLs ni las vistas: solo habria que reescribir
 * `renderMapa()` conservando la misma firma.
 *
 * Lo que dibuja y lo que NO dibuja
 * --------------------------------
 * Dibuja: un punto por cada sitio con coordenadas REALES.
 * NO dibuja: continentes, oceanos, montanas, fronteras, costas, ni nada que no
 * venga de los datos. No hay ningun "fondo" geografico porque no existe en el
 * archivo.
 *
 * Lo que llega aqui ya viene validado por la API (que es quien tiene los
 * datos). Aqui no se calcula nada geografico.
 */

/** Tipos de sitio reales. NO es una lista cerrada de "sitios": son los tipos
 *  que de verdad aparecen en `sites.jsonl`. Un tipo desconocido se dibuja
 *  igual, con el glifo generico, para no perder informacion. */
export const GLIFOS: Record<string, string> = {
  fortress: '◆', fort: '◆', castle: '◆',
  town: '●', village: '●', hamlet: '●',
  cave: '▲', lair: '▲', tunnel: '▲',
  camp: '▪', necropolis: '▪',
  shrine: '✝', temple: '✝', monastery: '✝',
  // Los tipos reales de DF llevan espacios: la clave va entre comillas.
  'dark pits': '○', 'dark fortress': '○',
  'forest retreat': '✦', hillocks: '✦', labyrinth: '▨',
  'mountain halls': '▨', 'mysterious dungeon': '◈',
  'mysterious lair': '◈', 'mysterious palace': '◈',
  tomb: '▣', tower: '⌂',
};

/** Radio del punto en unidades del viewBox. */
const R = 7;
/** Lado del viewBox: 1000 x 1000 y se escala con CSS. */
const LADO = 1000;

function glifoDe(tipo: string): string {
  if (!tipo || tipo === 'UNKNOWN') return '?';
  return GLIFOS[tipo] ?? '·';
}

export interface SitioMapa {
  df_id: string;
  nombre: string;
  tipo: string;
  x: number;
  y: number;
}

export interface AreaMapa {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

export interface OpcionesMapa {
  /** Sitio a destacar (el consultado). */
  destacado?: string | null;
  /** Pixel por parche. */
  escala?: number;
  /** Parche mostrado bajo el cursor al pasar por encima. */
  etiqueta?: string | null;
}

/**
 * Devuelve el SVG del mapa. Sin sitios, devuelve igualmente el marco: un
 * area vacia tambien es informacion ("aqui no hay nada").
 */
export function renderMapa(
  sitios: SitioMapa[],
  area: AreaMapa,
  opciones: OpcionesMapa = {},
): string {
  const { ancho, alto } = area;
  const px = opciones.escala ?? 14;
  const w = Math.max(1, ancho) * px;
  const h = Math.max(1, alto) * px;

  // Los datos ya vienen filtrados por la API; el recorte es solo una red de
  // seguridad visual ante un area cambiada entre la peticion y el pintado.
  const dentro = sitios.filter(
    (s) =>
      s.x >= area.x &&
      s.x <= area.x + ancho - 1 &&
      s.y >= area.y &&
      s.y <= area.y + alto - 1,
  );

  const puntos = dentro
    .map((s) => {
      const cx = (s.x - area.x + 0.5) * px;
      const cy = (s.y - area.y + 0.5) * px;
      const dest = opciones.destacado && String(s.df_id) === String(opciones.destacado);
      const clase = dest ? 'mapa-punto mapa-punto--destacado' : 'mapa-punto';
      const tipo = s.tipo || 'UNKNOWN';
      // Cada punto es un <a>: navega a la ficha real del sitio.
      return (
        `<a href="/sites/${encodeURIComponent(String(s.df_id))}" ` +
        `class="${clase}" aria-label="${escAttr(s.nombre)}, ${escAttr(tipo)}, ${s.x}, ${s.y}">` +
        `<title>${esc(s.nombre)} · ${esc(tipo)} · ${s.x}, ${s.y}</title>` +
        `<circle cx="${round(cx)}" cy="${round(cy)}" r="${dest ? R + 2 : R}" ` +
        `data-glifo="${escAttr(glifoDe(tipo))}"></circle>` +
        `<text x="${round(cx)}" y="${round(cy + R * 0.62)}" text-anchor="middle" ` +
        `aria-hidden="true">${esc(glifoDe(tipo))}</text>` +
        `</a>`
      );
    })
    .join('');

  return (
    `<svg class="mapa" viewBox="0 0 ${round(w)} ${round(h)}" ` +
    `role="img" aria-label="Sites in area ${area.x} to ${area.x + ancho - 1} ` +
    `horizontally, ${area.y} to ${area.y + alto - 1} vertically. ` +
    `${dentro.length} sites with real coordinates." ` +
    `preserveAspectRatio="xMidYMid meet">` +
    `<rect class="mapa-fondo" x="0" y="0" width="${round(w)}" height="${round(h)}"></rect>` +
    puntos +
    (opciones.etiqueta
      ? `<text class="mapa-nota" x="${round(w / 2)}" y="${round(h - 6)}" ` +
        `text-anchor="middle">${esc(opciones.etiqueta)}</text>`
      : '') +
    `</svg>`
  );
}

/** Leyenda de los tipos REALES presentes en los datos. */
export function renderLeyenda(tipos: string[]): string {
  if (!tipos.length) return '';
  const celdas = tipos
    .map(
      (t) =>
        `<li><span class="leyenda-glifo" aria-hidden="true">${esc(glifoDe(t))}</span>` +
        `<span>${esc(t)}</span></li>`,
    )
    .join('');
  return `<ul class="leyenda" aria-label="Site types in the data">${celdas}</ul>`;
}

/** Formatea el área para mostrar. */
export function rotuloArea(area: AreaMapa): string {
  return `x ${area.x}–${area.x + area.ancho - 1} · y ${area.y}–${area.y + area.alto - 1}`;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

/* Los dos escapados locales: este modulo no debe importar de `escapes.ts`
 * para seguir siendo un renderer independiente de la UI. */
function esc(s: string): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
function escAttr(s: string): string {
  return esc(s).replace(/"/g, '&quot;');
}