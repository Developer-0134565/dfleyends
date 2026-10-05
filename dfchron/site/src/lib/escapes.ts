/**
 * Helpers de presentacion compartidos por `vistas.ts` y `listados.ts`.
 *
 * Este modulo existe para ROMPER UN CICLO DE IMPORTS. `vistas.ts` importa
 * `listados.ts` (para el router) y `listados.ts` importaba de vuelta a
 * `vistas.ts` (para `trunc` y `tablaEventos`). Al importarse mutuamente, el
 * bundle fallaba en runtime con
 * `ReferenceError: avisoTruncamiento is not defined`, aunque el simbolo
 * estuviera exportado y existiera en el fuente.
 *
 * Aqui no hay reglas de negocio ni direccion de API: eso vive en `api.ts`.
 */
import { avisoTruncamiento, dato, type Envelope } from './api';

/** Escapa texto antes de inyectarlo en HTML. */
export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Fila de ausencia de datos. */
export const Vacio = `<p class="vacio">Data unavailable</p>`;

/** Aviso de truncamiento. Nunca se oculta que faltan filas. */
export function trunc(env: Envelope<unknown>): string {
  const a = avisoTruncamiento(env);
  return a ? `<p class="truncado">${esc(a)}</p>` : '';
}

/**
 * Contador tolerante.
 *
 * El nucleo no siempre devuelve un numero: `artefactos` de un sitio puede ser
 * un entero o la lista de objetos. Con `String()` sobre un array salia
 * `[object Object]`, que es justo el tipo de dato falso que no debe verse.
 * Aqui se cuenta lo que haya y, si no es countable, se dice `Unknown`.
 */
export function contar(v: unknown): string {
  if (typeof v === 'number') return String(v);
  if (Array.isArray(v)) return String(v.length);
  if (typeof v === 'string' && /^\d+$/.test(v)) return v;
  return 'Unknown';
}

/**
 * Tabla de eventos, compartida por las fichas de figura, sitio y entidad.
 * Un campo que no consta se muestra como `Unknown`, nunca se omite.
 */
export function tablaEventos(eventos: any[]): string {
  if (!eventos || !eventos.length) return Vacio;
  const filas = eventos
    .map(
      (e) =>
        `<tr><td>${esc(e['año'] ?? 'Unknown')}</td>` +
        `<th scope="row"><a href="/events/${encodeURIComponent(String(e.evento_id))}">` +
        `${esc(dato(e.tipo))}${e.subtipo ? ' · ' + esc(dato(e.subtipo)) : ''}</a></th>` +
        `<td>${e.sitio_nombre && e.sitio_nombre !== 'UNKNOWN' ? esc(dato(e.sitio_nombre)) : 'Unknown'}</td>` +
        `<td>${e.entidad_nombre && e.entidad_nombre !== 'UNKNOWN' ? esc(dato(e.entidad_nombre)) : 'Unknown'}</td></tr>`,
    )
    .join('');
  return `<div class="tabla-scroll"><table class="tabla"><thead><tr>
    <th scope="col">Year</th><th scope="col">Event</th>
    <th scope="col">Place</th><th scope="col">Participants</th>
  </tr></thead><tbody>${filas}</tbody></table></div>`;
}
/**
 * Badge de certidumbre: FACT, DERIVED o UNKNOWN.
 *
 * Vive aquí, y no en `vistas.ts`, porque lo necesitan varios modulos y
 * `vistas.ts` importa a los demás: definirlo en `vistas.ts` obligaría a esos
 * modulos a importarlo de allí y crearía un ciclo de importaciones.
 * `vistas.ts` lo reexporta, de modo que nada de lo existente se rompa.
 */
export function badge(c: string | undefined): string {
  const v = (c || 'UNKNOWN').toUpperCase();
  const clase = v === 'FACT' ? 'fact' : v === 'DERIVED' ? 'derived' : 'unknown';
  return `<span class="certeza certeza--${clase}">${esc(v)}</span>`;
}
