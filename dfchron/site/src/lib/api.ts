/**
 * DF Legends :: configuracion de la API.
 * =======================================
 *
 * ESTE ES EL UNICO SITIO DEL FRONTEND DONDE SE ESCRIBE UNA URL DE API.
 *
 * Toda vista y todo componente consumen la API a traves de las funciones de
 * este modulo. No se escribe `fetch('http://...')` en ningun otro fichero: la
 * suite `probar_web.py` lo verifica con un grep sobre `src/` y falla si
 * aparece una URL de API fuera de aqui.
 *
 * DONDE SE CAMBIA EL ORIGEN
 * ------------------------
 * Ahora mismo, local:
 *
 *     PUBLIC_API_BASE_URL=http://127.0.0.1:877
 *
 * En el futuro, una API remota:
 *
 *     PUBLIC_API_BASE_URL=https://api.algundominio.example
 *
 * No hay que tocar ninguna vista, ni ningun componente, ni ninguna logica de
 * presentacion. Solo esta variable.
 *
 * BUILD PUBLICO SIN API
 * ---------------------
 * Si `PUBLIC_API_BASE_URL` NO esta definida, `API_BASE_URL` queda vacia y
 * `hayApi()` devuelve false. Las vistas que necesitan datos muestran
 * "Data unavailable" en vez de intentar una peticion.
 *
 * Esto es lo que mantiene separadas las dos capas del proyecto:
 *
 *   - build publico (Cloudflare): sin API, contenido estatico.
 *   - build local (Astro dev): con API, aplicacion real.
 *
 * El build publico NUNCA queda conectado a la API local: sin la variable no
 * hay ninguna URL de la que depender.
 */

/**
 * Origen de la API. Vacio significa "esta build no habla con ninguna API".
 *
 * Se lee de `PUBLIC_` porque Astro solo expone al navegador las variables con
 * ese prefijo. No contiene ningun secreto: es la direccion publica del servicio.
 */
export const API_BASE_URL: string = (import.meta.env.PUBLIC_API_BASE_URL ?? '').trim();

/** Hay una API configurada en esta build. */
export function hayApi(): boolean {
  return API_BASE_URL.length > 0;
}

/** Fila de error mostrada cuando no hay API configurada. */
export const SIN_API = {
  ok: false as const,
  motivo: 'Data unavailable',
  detalle:
    'Esta build no tiene una API configurada. Define PUBLIC_API_BASE_URL ' +
    'para conectar con la API local (http://127.0.0.1:877).',
};

/** Certidumbres posibles. La API no distingue mas de estas tres. */
export type Certainty = 'FACT' | 'DERIVED' | 'UNKNOWN';

/**
 * Estados del contrato de consulta determinista.
 *
 * Los cinco se conservan. En particular `NOT_VERIFIED` NO es `NOT_FOUND`:
 * «no pude determinarlo» y «no existe» son afirmaciones distintas, y la
 * segunda es mas fuerte. Colapsarlas seria el fallo que el servicio evita.
 */
export type Estado =
  | 'FOUND'
  | 'NOT_FOUND'
  | 'NOT_VERIFIED'
  | 'INVALID_QUERY'
  | 'DATA_UNAVAILABLE';

/** Identidad, solo si el tipo la tiene demostrada. Nunca se inventa. */
export interface Identity {
  tipo: string;
  df_id: string;
}

/** Procedencia de un dato, tal y como la devuelve el servicio. */
export interface Evidence {
  entidad?: string;
  df_id?: string;
  datos_utilizados?: string[];
  funcion?: string;
  fuente?: string[];
  state_version?: string;
}

/** Envelope de listado devuelto por la API. */
export interface Envelope<T> {
  ok: boolean;
  data: T;
  /** Estado del contrato. Lo copia el servicio; la Web no lo deduce. */
  estado?: Estado;
  identity?: Identity | null;
  evidence?: Evidence | null;
  dataset_id?: string | null;
  meta?: {
    total?: number;
    returned?: number;
    truncated?: boolean;
    limit?: number;
    offset?: number;
    certainty?: Certainty;
  };
  // Campos heredados del contrato previo. Se conservan porque el proyecto los
  // usa para el truncamiento; el frontend nuevo lee `meta`.
  total_encontrados?: number;
  devueltos?: number;
  truncado?: boolean;
  limit?: number;
  offset?: number;
  certainty?: Certainty;
  error?: { codigo?: string; code?: string; mensaje?: string; message?: string };
  http_status?: number;
}

/** Error normalizado de la capa de presentacion. */
export class ApiError extends Error {
  readonly codigo: string;
  readonly http: number;
  constructor(codigo: string, mensaje: string, http = 0) {
    super(mensaje);
    this.name = 'ApiError';
    this.codigo = codigo;
    this.http = http;
  }
}

/**
 * Construye la URL de un endpoint a partir de sus segmentos.
 *
 * Los segmentos se codifican aqui: un id con `/` o un texto de busqueda con
 * espacios NUNCA se concatena en crudo.
 */
export function ruta(...segmentos: Array<string | number>): string {
  const limpio = segmentos
    .map((s) => encodeURIComponent(String(s)))
    .join('/');
  return `${API_BASE_URL}/${limpio}`;
}
/**
 * Pide un endpoint y devuelve su envelope.
 *
 * Nunca lanza por un error HTTP: devuelve el envelope de error que la propia
 * API ha construido, de modo que la vista pueda distinguir "no hay resultados"
 * de "no se pudo consultar" sin analisar excepciones.
 */
export async function pedir<T>(...segmentos: Array<string | number>): Promise<Envelope<T>> {
  if (!hayApi()) {
    return {
      ok: false,
      data: [] as unknown as T,
      error: { code: 'SIN_API', mensaje: SIN_API.detalle },
    };
  }

  const url = ruta(...segmentos);
  try {
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    const cuerpo = await res.json().catch(() => null);

    if (cuerpo === null || typeof cuerpo !== 'object') {
      return {
        ok: false,
        data: [] as unknown as T,
        error: { code: 'RESPUESTA_INVALIDA', mensaje: 'la API no devolvio JSON' },
        http_status: res.status,
      };
    }
    // La API ya devuelve `ok: false` con su envelope en los errores: se respeta
    // tal cual en vez de reescribirlo aqui.
    return cuerpo as Envelope<T>;
  } catch {
    // Fallo de red: la API local esta apagada. No se inventa un resultado.
    return {
      ok: false,
      data: [] as unknown as T,
      error: {
        code: 'API_INALCANZABLE',
        mensaje:
          `no se pudo contactar con la API local en ${API_BASE_URL}. ` +
          'Comprueba que DF-Chronicles esta arrancado (python run.py).',
      },
      http_status: 0,
    };
  }
}

/**
 * Pide un endpoint con parametros de consulta.
 *
 * Los valores se codifican con `encodeURIComponent`. Esto evita depender de
 * concatenar cadenas a mano, que es donde aparecerian los espacios rotos y los
 * caracteres especiales sin escapar.
 *
 * IMPORTANTE: los parametros separan con `?` o `&` ANTES de codificarlos como
 * segmento. Si se codificaran como un segmento mas, la URL seria
 * `/api/eventos/from%3D1%26to%3D3` y la API recibiria una ruta inexistente.
 */
export async function consultar<T>(
  segmentos: Array<string | number>,
  params: Record<string, string | number | undefined> = {},
): Promise<Envelope<T>> {
  const pares = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  if (pares.length === 0) return pedir<T>(...segmentos);

  const base = segmentos.map((s) => encodeURIComponent(String(s))).join('/');
  // `ruta()` antepondria el origen y antepondria otro `/`; aqui se construye
  // la URL completa con la query ya montada.
  const url = `${API_BASE_URL}/${base}?${pares.join('&')}`;

  if (!hayApi()) {
    return {
      ok: false,
      data: [] as unknown as T,
      error: { code: 'SIN_API', mensaje: SIN_API.detalle },
    };
  }

  try {
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    const cuerpo = await res.json().catch(() => null);
    if (cuerpo === null || typeof cuerpo !== 'object') {
      return {
        ok: false,
        data: [] as unknown as T,
        error: { code: 'RESPUESTA_INVALIDA', mensaje: 'la API no devolvio JSON' },
        http_status: res.status,
      };
    }
    return cuerpo as Envelope<T>;
  } catch {
    return {
      ok: false,
      data: [] as unknown as T,
      error: {
        code: 'API_INALCANZABLE',
        mensaje:
          `no se pudo contactar con la API local en ${API_BASE_URL}. ` +
          'Comprueba que DF-Chronicles esta arrancado (python run.py).',
      },
      http_status: 0,
    };
  }
}

/**
 * Total real de un envelope, venga del campo nuevo o del heredado.
 *
 * La API declara los dos. Se leen los dos para que un recorte NUNCA se
 * presente como resultado completo.
 */
export function total(env: Envelope<unknown>): number {
  return env.meta?.total ?? env.total_encontrados ?? 0;
}

/** Numero de filas devueltas. */
export function devueltos(env: Envelope<unknown>): number {
  return env.meta?.returned ?? env.devueltos ?? 0;
}

/** True si la consulta esta truncada. La interfaz DEBE mostrarlo. */
export function truncado(env: Envelope<unknown>): boolean {
  return env.meta?.truncated ?? env.truncado ?? false;
}

/** Frase de truncamiento, o null si la consulta esta completa. */
export function avisoTruncamiento(env: Envelope<unknown>): string | null {
  if (!truncado(env)) return null;
  const t = total(env).toLocaleString('es');
  const d = devueltos(env).toLocaleString('es');
  return `Showing ${d} of ${t}`;
}

/** Certidumbre de un envelope; por defecto UNKNOWN (no se presume nada). */
export function certeza(env: Envelope<unknown>): Certainty {
  return env.meta?.certainty ?? env.certainty ?? 'UNKNOWN';
}

/** Texto de un campo que puede faltar. NUNCA se inventa un valor. */
export function dato(valor: unknown, texto = 'Unknown'): string {
  if (valor === null || valor === undefined) return texto;
  if (typeof valor === 'string') {
    const t = valor.trim();
    if (t === '' || t === 'UNKNOWN' || t === 'None') return texto;
    return t;
  }
  return String(valor);
}

/** Si un campo no existe, devuelve su texto de ausencia. */
export function noDisponible(): string {
  return 'Data unavailable';
}

/**
 * EL ESTADO REAL DE UN ENVELOPE.
 *
 * Se LEE del envelope; no se deduce. Si `estado` no viene (endpoints que no
 * pasan por la capa de consulta), se cae a `ok`, que es lo que hacia esta Web
 * antes de que existiera el contrato.
 *
 * La caida de `error.code` a `NOT_FOUND` solo se aplica a `NO_ENCONTRADO`,
 * que es el unico codigo que significa de verdad «no existe». Cualquier otro
 * error NO se traduce a `NOT_FOUND`: seria afirmar una ausencia que nadie ha
 * comprobado.
 */
export function estado(env: Envelope<unknown>): Estado {
  if (env.estado) return env.estado;
  if (env.error?.code === 'NO_ENCONTRADO') return 'NOT_FOUND';
  if (env.ok) return 'FOUND';
  return 'DATA_UNAVAILABLE';
}

/** Etiqueta legible de cada estado, sin aumentar la certeza. */
const ETIQUETA: Record<Estado, string> = {
  FOUND: 'Found in this dataset',
  NOT_FOUND: 'Not present in this dataset',
  // Proposito: NO dice "does not exist". Dice que no se pudo determinar.
  NOT_VERIFIED: 'Cannot be determined from these data',
  INVALID_QUERY: 'Query is not valid',
  DATA_UNAVAILABLE: 'Data unavailable right now',
};

/** Una linea de estado. Distingue visualmente los cinco casos. */
export function lineaEstado(env: Envelope<unknown>): string {
  const e = estado(env);
  return (
    `<p class="estado estado--${e.toLowerCase()}" data-estado="${e}">` +
    `<span class="estado__texto">${ETIQUETA[e]}</span>` +
    `<code class="estado__codigo">${e}</code></p>`
  );
}

/**
 * Panel de procedencia. Pinta lo que LLEGA y nada mas.
 *
 * Si `identity` llega en null, se dice que no hay identidad: no se rellena
 * con el indice, la posicion ni un hash. `dataset_id` identifica contenido y
 * se presenta como eso, nunca como fecha ni como reloj.
 */
export function panelEvidencia(env: Envelope<unknown>): string {
  const ev = env.evidence;
  const ident = env.identity;
  const ds = env.dataset_id;
  if (!ev && !ident && !ds) return '';
  const fila = (k: string, v: string) => `<dt>${k}</dt><dd>${v}</dd>`;
  let h = '<section class="panel panel--evidencia"><h2>Provenance</h2><dl>';
  h += ident
    ? fila('Identity', `<code>${ident.tipo} #${ident.df_id}</code>`)
    : fila(
        'Identity',
        '<span class="certeza certeza--unknown">UNKNOWN</span>' +
          ' <small>this type has no demonstrable identity</small>',
      );
  h += fila('Dataset', ds ? `<code>${ds}</code>` : '<span class="vacio">none</span>');
  if (ev?.state_version) h += fila('state_version', `<code>${ev.state_version}</code>`);
  if (ev?.funcion) h += fila('Core function', `<code>${ev.funcion}</code>`);
  if (ev?.fuente?.length) h += fila('Source', `<code>${ev.fuente.join(', ')}</code>`);
  return h + '</dl></section>';
}

/** Enlace interno a una ficha, por tipo. */
export function enlaceFicha(
  tipo: 'figures' | 'entities' | 'sites' | 'artifacts' | 'events',
  id: unknown,
): string {
  return `/${tipo}/${encodeURIComponent(String(id))}`;
}