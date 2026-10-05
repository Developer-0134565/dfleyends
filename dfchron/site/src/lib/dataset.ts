/**
 * Identidad del MUNDO y del DATASET activos, y aviso cuando cambia.
 *
 * `dataset_id` identifica el CONTENIDO extraido. `world_name` y `world_folder`
 * identifican el MUNDO del que salio ese contenido: son ejes distintos, y P1
 * demostro que el hash no los distingue. **Ninguno de los dos es el estado del
 * mundo en un instante**: esa identificacion sigue sin existir.
 *
 * POR QUE NO HAY POLLING
 * ---------------------
 * Dwarf Fortress genera cambios masivos durante una partida, pero DF Legends
 * actualiza por SNAPSHOT, no por tick (ver `00_SOURCE/refresh_cycle_report.md`).
 * Por eso NO se consulta la API cada segundo: se comprueba al cargar la
 * aplicacion y al volver a la pestaña, que es cuando una persona puede notar la
 * diferencia. Un `setInterval` aqui solo gastaria recursos.
 *
 * POR QUE NO HAY RECARGA AUTOMATICA
 * ---------------------------------
 * Un `location.reload()` en silencio perderia la posicion del scroll, el texto
 * buscado y la ficha abierta. Se AVISA y deja que decida la persona.
 */
import { consultar } from './api';
import { esc, badge } from './escapes';

/** Lo que sabemos del dataset activo. */
export interface EstadoDataset {
  dataset_id: string | null;
  dataset_generado: string | null;
  /** 'FACT' si viene de la API, 'UNKNOWN' si no se pudo saber. */
  certainty: 'FACT' | 'UNKNOWN';
  motivo?: string | null;
  /** Id que tenía esta sesión al abrirla; si difiere, el mundo es otro. */
  idAlAbrir: string | null;
  cambiado: boolean;
  /**
   * Identidad del MUNDO. Se declara aunque no haya `dataset_id`: son preguntas
   * distintas, y que el dataset no se identifique no dice nada del mundo.
   * `dataset_id` es el CONTENIDO; esto es de que MUNDO salio ese contenido.
   * Ninguno de los dos es el estado del mundo en un instante.
   */
  mundo: IdentidadMundo | null;
}

/** Identidad del mundo, tal y como la declara la extraccion. */
export interface IdentidadMundo {
  /** Nombre descriptivo. NO es unico global: dos mundos pueden llamarse igual. */
  world_name: string;
  /** Carpeta del save. NO es unica fuera del entorno donde se exporto. */
  world_folder: string;
  /** Por que falta cada campo, o null si esta. Nunca se rellena el hueco. */
  world_name_ausente_porque?: string | null;
  world_folder_ausente_porque?: string | null;
}

let ultimo: EstadoDataset | null = null;

/** Lo que se declara cuando no hay dato. No se rellena con nada. */
function desconocido(motivo: string): IdentidadMundo {
  return {
    world_name: 'UNKNOWN',
    world_folder: 'UNKNOWN',
    world_name_ausente_porque: motivo,
    world_folder_ausente_porque: motivo,
  };
}

/** Lee la identidad que ya viene en la respuesta. Sin reglas propias. */
function leerMundo(ds: any, motivo: string): IdentidadMundo {
  const m = ds?.mundo;
  if (!m || typeof m !== 'object') return desconocido(motivo);
  return {
    world_name: typeof m.world_name === 'string' ? m.world_name : 'UNKNOWN',
    world_folder: typeof m.world_folder === 'string' ? m.world_folder : 'UNKNOWN',
    world_name_ausente_porque: m.world_name_ausente_porque ?? null,
    world_folder_ausente_porque: m.world_folder_ausente_porque ?? null,
  };
}

/**
 * Lee el dataset activo de la API. Devuelve `certainty: UNKNOWN` con el motivo
 * si no se puede saber: nunca inventa un id ni una fecha.
 */
export async function estadoDataset(): Promise<EstadoDataset> {
  const env = await consultar<Record<string, any>>(['api', 'salud']);
  const ds = env.ok ? (env.data as any)?.dataset : null;
  if (!ds || !ds.dataset_id) {
    const motivo = ds?.motivo ?? 'la API no ha informado del dataset';
    return {
      dataset_id: null,
      dataset_generado: null,
      certainty: 'UNKNOWN',
      motivo,
      idAlAbrir: ultimo?.idAlAbrir ?? null,
      cambiado: false,
      mundo: leerMundo(ds, motivo),
    };
  }
  const base: EstadoDataset = {
    dataset_id: String(ds.dataset_id),
    dataset_generado: ds.dataset_generado ? String(ds.dataset_generado) : null,
    certainty: 'FACT',
    motivo: null,
    idAlAbrir: ultimo?.idAlAbrir ?? null,
    cambiado: false,
    mundo: leerMundo(ds, 'la API no ha informado del mundo'),
  };
  // La primera lectura fija la referencia; las siguientes comparan con ella.
  if (!ultimo) base.idAlAbrir = base.dataset_id;
  base.cambiado = base.idAlAbrir !== base.dataset_id;
  ultimo = base;
  return base;
}

/** Id con el que se abrió la sesión, o null si aún no se ha comprobado. */
export function idDeReferencia(): string | null {
  return ultimo?.idAlAbrir ?? null;
}

/**
 * Una identidad ausente se DICE, con su motivo. No se sustituye por el nombre
 * del fichero, ni por una fecha, ni por el hash del dataset: eso seria fabricar
 * una identidad y presentarla como observada.
 */
function filaMundo(m: IdentidadMundo): string {
  const celda = (valor: string, motivo?: string | null) =>
    valor === 'UNKNOWN'
      ? `<span class="vacio">UNKNOWN</span>`
        + (motivo ? ` <small class="nota">${esc(motivo)}</small>` : '')
      : `<code>${esc(valor)}</code>`;
  return `<div><dt>World name</dt><dd>${celda(
    m.world_name, m.world_name_ausente_porque)}</dd></div>
    <div><dt>Save folder</dt><dd>${celda(
    m.world_folder, m.world_folder_ausente_porque)}</dd></div>`;
}

/** Panel discreto del dashboard. Sin datos, lo dice; no rellena nada. */
export function panelDataset(ds: EstadoDataset): string {
  const mundo = ds.mundo ? filaMundo(ds.mundo) : '';
  if (ds.certainty === 'UNKNOWN' || !ds.dataset_id) {
    return `<section class="panel panel--dataset"><h2>World dataset</h2>
      <p class="nota">Dataset identity is unavailable: ${esc(ds.motivo ?? 'unknown')}.</p>
      ${mundo ? `<dl class="definiciones">${mundo}</dl>` : ''}</section>`;
  }
  return `<section class="panel panel--dataset">
    <h2>World dataset</h2>
    <dl class="definiciones">
      <div><dt>Dataset</dt><dd><code>${esc(ds.dataset_id)}</code> ${badge('FACT')}</dd></div>
      <div><dt>Generated</dt><dd>${ds.dataset_generado
        ? esc(ds.dataset_generado) : '<span class="vacio">Unknown</span>'}</dd></div>
      ${mundo}
    </dl>
    <p class="nota">The world is a snapshot, updated manually. DF Legends does not
    follow the game in real time.</p>
  </section>`;
}

/**
 * Aviso de dataset nuevo. Solo aparece si el id cambió de verdad.
 * Se inserta una vez; si no hay cambio, devuelve null y no toca el DOM.
 */
export function avisoDataset(ds: EstadoDataset): string | null {
  if (!ds.cambiado || !ds.dataset_id || !ds.idAlAbrir) return null;
  return `<div class="aviso-dataset" role="status" data-aviso-dataset>
    <p><strong>A new world snapshot is available.</strong> The dataset changed from
      <code>${esc(ds.idAlAbrir)}</code> to <code>${esc(ds.dataset_id)}</code>.</p>
    <p><a href="#" data-recargar-pagina>Reload to explore the updated world</a>,
      or keep reading the one already loaded.</p>
  </div>`;
}

/* CONTINUA_ESTADO_DATASET */