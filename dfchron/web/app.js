/* DF-Chronicles :: interfaz
   ========================
   UI de UNA SOLA PAGINA. Habla EXCLUSIVAMENTE con la API local por HTTP.

   Decisiones de arquitectura:
   * No lee los XML ni el JSONL. No tiene logica de Dwarf Fortress. Si esta
     UI calculase algo, ese calculo existiria en dos sitios.
   * No inventa cifras: todo lo que se ve viene de /api.
   * No oculta un truncamiento: truncado() siempre se pinta si viene true.
   * JavaScript plano, sin framework ni build: se puede copiar tal cual a
     un servidor web futuro, apuntando a la misma API.

   Texto en ASCII a proposito: los nombres de Dwarf Fortress son ASCII y el
   fichero viaja entre sistemas sin depender de una codificacion concreta.
*/

'use strict';

// ---------------------------------------------------------------- utilidades
const $ = (sel) => document.querySelector(sel);
const vista = () => $('#vista');

const nf = new Intl.NumberFormat('es-ES');
const fmt = (n) => (typeof n === 'number' ? nf.format(n)
  : (n === null || n === undefined ? '-' : n));

/** Escapa texto antes de meterlo con innerHTML. Los nombres vienen del XML. */
function esc(s) {
  if (s === null || s === undefined) return '-';
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

/** Etiqueta de certeza FACT / DERIVED / UNKNOWN. */
const cert = (c) => '<span class="cert ' + esc(c) + '">' + esc(c) + '</span>';

/** Enlace navegable a una ficha. */
const enlace = (ruta, texto) =>
  '<a class="enlace" href="#' + ruta + '">' + esc(texto) + '</a>';

/** Pide un endpoint. Nunca lanza: devuelve {error} si algo falla. */
async function api(ruta) {
  try {
    const r = await fetch(ruta, { headers: { Accept: 'application/json' } });
    const datos = await r.json();
    if (datos && datos.error) return { error: datos.error };
    return datos;
  } catch (e) {
    return { error: { codigo: 'SIN_CONEXION', mensaje: String(e) } };
  }
}

/** Pinta un error de la API sin inventar nada. */
function pintaError(d) {
  vista().innerHTML = '<div class="error"><strong>' + esc(d.error.codigo)
    + '</strong><br>' + esc(d.error.mensaje) + '</div>';
}

/**
 * COMO SE MUESTRA UN ESTADO DEL CONTRATO.
 *
 * El servicio distingue cinco estados y la Web NO puede colapsarlos. En
 * particular `NOT_VERIFIED` NO se pinta como «no existe»: significaria
 * afirmar algo mas fuerte que lo que el servicio dice, y exactamente falso.
 *
 * Se lee `env.estado`, que la API copia del servicio. Si no viene (envelopes
 * antiguos que no han pasado por la capa de consulta), se cae al `ok` de
 * siempre, que es lo que hacia esta UI antes de existir el contrato.
 */
const ESTADOS = {
  FOUND: { clase: 'estado--found', texto: 'Encontrado en el dataset' },
  NOT_FOUND: { clase: 'estado--notfound', texto: 'No existe en el dataset' },
  NOT_VERIFIED: {
    clase: 'estado--notverified',
    texto: 'No se puede determinar con estos datos',
  },
  INVALID_QUERY: { clase: 'estado--invalid', texto: 'Consulta no valida' },
  DATA_UNAVAILABLE: {
    clase: 'estado--unavailable',
    texto: 'Datos no disponibles ahora mismo',
  },
};

/** El estado real de un envelope, sin adivinar. */
function estadoDe(env) {
  if (env && env.estado && ESTADOS[env.estado]) return env.estado;
  if (env && env.error) return env.error.codigo === 'NO_ENCONTRADO'
    ? 'NOT_FOUND' : 'DATA_UNAVAILABLE';
  return env && env.ok ? 'FOUND' : 'DATA_UNAVAILABLE';
}

/**
 * Linea de estado. Distingue visualmente los cinco casos sin cambiar lo que
 * el dato significa: solo repite lo que el servicio dijo.
 */
function lineaEstado(env) {
  const e = estadoDe(env);
  const info = ESTADOS[e];
  return '<div class="estado ' + info.clase + '" data-estado="' + esc(e) + '">'
    + '<span class="estado__etiqueta">' + esc(info.texto) + '</span>'
    + '<code class="estado__codigo">' + esc(e) + '</code></div>';
}

/**
 * Evidencia y dataset. Se pinta lo que LLEGA de la API; si no llega, no se
 * inventa: se dice que no hay. `dataset_id` identifica contenido: no se
 * presenta como fecha ni como reloj.
 */
function panelEvidencia(env) {
  const ev = env && env.evidence;
  const dataset = env && env.dataset_id;
  const ident = env && env.identity;
  if (!ev && !dataset && !ident) return '';
  let h = '<div class="panel panel--evidencia"><h3>Procedencia</h3><dl class="datos">';
  if (ident) {
    h += '<dt>Identidad</dt><dd class="mono">' + esc(ident.tipo) + ' #'
      + esc(ident.df_id) + '</dd>';
  } else {
    // El servicio no dio identidad. No se fabrica una para rellenar.
    h += '<dt>Identidad</dt><dd><span class="cert UNKNOWN">UNKNOWN</span>'
      + '<small> este tipo no tiene identidad demostrable</small></dd>';
  }
  h += '<dt>Dataset</dt><dd class="mono">'
    + (dataset ? esc(dataset) : '<span class="vacio">sin dataset</span>') + '</dd>';
  if (ev && ev.state_version) {
    h += '<dt>state_version</dt><dd class="mono">' + esc(ev.state_version)
      + '</dd>';
  }
  if (ev && ev.fuente) {
    h += '<dt>Fuente</dt><dd class="mono">' + esc((ev.fuente || []).join(', '))
      + '</dd>';
  }
  if (ev && ev.funcion) {
    h += '<dt>Funcion del nucleo</dt><dd class="mono">' + esc(ev.funcion) + '</dd>';
  }
  return h + '</dl></div>';
}

/**
 * AVISO DE TRUNCAMIENTO. Se pinta SIEMPRE que haya mas datos.
   Es la regla que impide que la UI esconda informacion disponible. */
function truncado(env, etiqueta) {
  etiqueta = etiqueta || 'resultados';
  if (!env || !env.truncado) return '';
  return '<div class="truncado">Mostrando ' + fmt(env.devueltos) + ' de '
    + fmt(env.total_encontrados) + ' ' + etiqueta + ' (desde la posicion '
    + fmt(env.offset || 0) + '). Hay mas datos disponibles: usa paginacion o '
    + 'exporta a JSON para verlos todos.</div>';
}

// --------------------------------------------------------------- plantillas
function tabla(cabeceras, filas) {
  if (!filas || !filas.length) return '<p class="vacio">Sin resultados.</p>';
  return '<div class="tabla-scroll"><table><thead><tr>'
    + cabeceras.map((c) => '<th>' + esc(c) + '</th>').join('')
    + '</tr></thead><tbody>'
    + filas.map((f) => '<tr>' + f.map((c) => '<td>' + c + '</td>').join('')
      + '</tr>').join('')
    + '</tbody></table></div>';
}

const CAB_EVENTOS = ['Evento', 'Anio', 'Tipo', 'Figura', 'Sitio', 'Entidad'];

/** Fila de evento, navegable en todas sus columnas. */
function filaEvento(e) {
  const figura = (e.figura_id && !desconocido(e.figura_nombre))
    ? enlace('figura/' + encodeURIComponent(e.figura_id), e.figura_nombre)
    : celda(e.figura_nombre);
  const sitio = (e.sitio_id && !desconocido(e.sitio_nombre))
    ? enlace('sitio/' + encodeURIComponent(e.sitio_id), e.sitio_nombre)
    : celda(e.sitio_nombre);
  const entidad = (e.entidad_id && !desconocido(e.entidad_nombre))
    ? enlace('entidad/' + encodeURIComponent(e.entidad_id), e.entidad_nombre)
    : celda(e.entidad_nombre);
  return [
    enlace('evento/' + encodeURIComponent(e.evento_id), e.evento_id),
    esc(e['año'] === null || e['año'] === undefined ? '-' : e['año']),
    esc(e.tipo || '-') + (e.subtipo ? '<br><small>' + esc(e.subtipo) + '</small>' : ''),
    figura, sitio, entidad,
  ];
}

/** Agrupa una linea temporal por anio, en el orden validado del nucleo. */
function bloqueCronologia(eventos, rango) {
  if (!eventos || !eventos.length) return '<p class="vacio">Sin eventos.</p>';
  const porAnio = new Map();
  eventos.forEach((e) => {
    const y = e['año'];
    if (!porAnio.has(y)) porAnio.set(y, []);
    porAnio.get(y).push(e);
  });
  const cuerpo = Array.from(porAnio.entries()).map(([y, lista]) =>
    '<div class="anio"><div class="titulo">Anio '
    + (y === null || y === undefined ? 'UNKNOWN' : y) + '</div><ul>'
    + lista.map((e) => '<li>' + enlace('evento/' + e.evento_id, e.evento_id)
      + ' - ' + esc(e.tipo || '')
      + (e.subtipo ? ' <small>(' + esc(e.subtipo) + ')</small>' : '')
      + ((e.sitio_id && !desconocido(e.sitio_nombre))
        ? ' @ ' + enlace('sitio/' + e.sitio_id, e.sitio_nombre) : '')
      + '</li>').join('')
    + '</ul></div>').join('');
  const rangoTxt = (rango && !Array.isArray(rango))
    ? '<span class="cert UNKNOWN">rango UNKNOWN</span>'
    : 'Anios ' + fmt(rango[0]) + '-' + fmt(rango[1]);
  return '<div class="cronologia"><p class="vacio">' + rangoTxt + ' | '
    + fmt(eventos.length) + ' eventos en el orden temporal validado '
    + '(anio, segundos72). No se inventan fechas.</p>' + cuerpo + '</div>';
}

/** Monta los botones de seccion de una ficha y carga la primera. */
function panelEvents(carga, inicial, panelId, prefijo) {
  const panel = document.getElementById(panelId);
  const botones = document.querySelectorAll('[data-sec^="' + prefijo + '-"]');
  const abrir = async (clave) => {
    botones.forEach((b) => b.classList.toggle('activo',
      b.dataset.sec === clave));
    panel.innerHTML = '<p class="vacio">Cargando...</p>';
    try {
      panel.innerHTML = await carga[clave]();
    } catch (e) {
      panel.innerHTML = '<div class="error">' + esc(String(e)) + '</div>';
    }
  };
  botones.forEach((b) => b.addEventListener('click',
    () => abrir(b.dataset.sec)));
  abrir(inicial);
}
/** Mapea el nombre de la API al nombre de la ruta de la UI. */
const BASE_RUTA = {
  historical_figures: 'figura', entities: 'entidad', sites: 'sitio',
  artifacts: 'artefacto', historical_events: 'evento',
};

// Tabla de pantallas. Debe existir ANTES de que se evaluen las vistas,
// porque cada vista se registra asignando a este objeto.
const VISTAS = {};

// --- Portada: estadisticas REALES del nucleo -------------------------------
VISTAS.inicio = async () => {
  const env = await api('/api/stats');
  if (env.error) return pintaError(env);
  const d = env.data;
  const tarjetas = [
    ['Figuras', d.figuras], ['Entidades', d.entidades], ['Sitios', d.sitios],
    ['Eventos', d.eventos], ['Artefactos', d.artefactos],
    ['Relaciones', d.relaciones], ['Rios', d.rios],
    ['Construcciones', d.construcciones_mundo],
  ].map(([k, v]) => '<div class="tarjeta"><span class="cifra">' + fmt(v)
    + '</span><span class="etiqueta">' + k + '</span></div>').join('');
  vista().innerHTML = '<h2>Resumen del archivo historico</h2>'
    + '<p class="vacio">Cifras obtenidas del nucleo, no escritas a mano. '
    + 'Rango temporal: <strong>anos ' + fmt(d.anio_min) + '-' + fmt(d.anio_max)
    + '</strong>. <span class="cert UNKNOWN">Era: UNKNOWN</span></p>'
    + '<div class="rejilla">' + tarjetas + '</div>'
    + '<div class="panel" style="margin-top:16px"><h3>Como empezar</h3>'
    + '<p>Busca arriba una figura, entidad, sitio o artefacto. Cada resultado '
    + 'enlaza a su ficha, y cada ficha a sus eventos, sitios y entidades.</p>'
    + '<p class="vacio">El grafo de relaciones es <strong>dirigido</strong>: '
    + 'que A tenga relacion con B no implica la inversa.</p>'
    + '<p><button class="accion" onclick="exportar(\'figura\',\'712\',\'json\')">'
    + 'Exportar historia de ejemplo (JSON)</button></p></div>';
};

// --- Buscador global -------------------------------------------------------
VISTAS.buscar = async (q) => {
  const env = await api('/api/buscar?q=' + encodeURIComponent(q));
  if (env.error) return pintaError(env);

  if (env.por_tipo) {
    const cuerpo = env.data.map((g) => {
      const base = BASE_RUTA[g.tipo] || 'figura';
      const filas = g.ids.map((id) => [
        enlace(base + '/' + encodeURIComponent(id), id)]);
      return '<h3>' + esc(g.tipo) + ' ' + cert('FACT')
        + ' <span class="vacio">' + fmt(g.devueltos) + ' de '
        + fmt(g.total_encontrados) + '</span></h3>'
        + tabla(['ID'], filas)
        + (g.truncado ? '<div class="truncado">Se muestran '
          + fmt(g.devueltos) + ' de ' + fmt(g.total_encontrados)
          + ' coincidencias de este tipo.</div>' : '');
    }).join('');
    vista().innerHTML = '<h2>Resultados para "' + esc(q) + '"</h2>'
      + (env.consulta_ambigua ? '<div class="truncado">La consulta es '
        + '<strong>ambigua</strong>: hay varias coincidencias. DF-Chronicles '
        + 'no elige por su cuenta; selecciona la que quieras.</div>' : '')
      + (cuerpo || '<p class="vacio">Sin coincidencias.</p>')
      + totalLinea(env, 'coincidencias en total');
    return;
  }

  const base = BASE_RUTA[env.tipo] || 'figura';
  const filas = (env.data || []).map((f) => [
    enlace(base + '/' + encodeURIComponent(f.df_id), f.nombre || f.df_id),
    celda(f.df_id), celda(f.race || f.tipo), esc(f.eventos === undefined ? '-' : f.eventos)]);
  vista().innerHTML = '<h2>Resultados: "' + esc(q) + '"</h2>'
    + (env.consulta_ambigua ? '<div class="truncado">Varias coincidencias. '
      + 'Selecciona una; el sistema no decide por ti.</div>' : '')
    + tabla(['Nombre', 'ID', 'Raza / tipo', 'Eventos'], filas)
    + truncado(env, 'figuras');
};

// --- Listados simples (paginados) ------------------------------------------
async function listado(tipo, titulo, etiqueta) {
  const pagina = Number(sessionStorage.getItem('pag') || 0);
  const env = await api('/api/listar/' + tipo + '?limit=25&offset='
    + (pagina * 25));
  if (env.error) return pintaError(env);
  const base = BASE_RUTA[tipo];
  const filas = env.data.map((f) => [
    enlace(base + '/' + encodeURIComponent(f.df_id), f.nombre || f.df_id),
    celda(f.df_id), celda(f.race || f.tipo),
    esc(f.eventos === undefined ? '-' : f.eventos)]);
  vista().innerHTML = '<h2>' + esc(titulo) + '</h2>'
    + tabla(['Nombre', 'ID', 'Raza / tipo', 'Eventos'], filas)
    + truncado(env, etiqueta) + '<p>' + botonPagina(pagina, env) + '</p>';
}

VISTAS.figuras = () => listado('historical_figures', 'Figuras historicas', 'figuras');
VISTAS.entidades = () => listado('entities', 'Entidades', 'entidades');
VISTAS.sitios = () => listado('sites', 'Sitios', 'sitios');
VISTAS.artefactos = () => listado('artifacts', 'Artefactos', 'artefactos');

function botonPagina(pagina, env) {
  const total = env.total_encontrados || 0;
  const porPagina = env.limit || 25;
  const ultima = Math.max(0, Math.ceil(total / porPagina) - 1);
  if (ultima === 0) return '';
  return '<button class="secundario" onclick="irPagina(' + (pagina - 1) + ')"'
    + (pagina === 0 ? ' disabled' : '') + '>Anterior</button> '
    + '<button class="secundario" onclick="irPagina(' + (pagina + 1) + ')"'
    + (pagina >= ultima ? ' disabled' : '') + '>Siguiente</button> '
    + '<span class="vacio">pagina ' + (pagina + 1) + ' de ' + fmt(ultima + 1)
    + '</span>';
}
window.irPagina = (n) => {
  sessionStorage.setItem('pag', Math.max(0, n));
  window.location.reload();
};

const totalLinea = (env, etiqueta) =>
  '<p class="vacio">' + fmt(env.devueltos) + ' de '
  + fmt(env.total_encontrados) + ' ' + etiqueta + ' '
  + cert(env.cert || 'FACT') + '</p>';

const desconocido = (v) => v === 'UNKNOWN' || v === undefined || v === null;

/** Muestra UNKNOWN de forma explicita, nunca como celda vacia. */
const celda = (v) => (desconocido(v)
  ? '<span class="cert UNKNOWN">UNKNOWN</span>' : esc(v));

// --- Ficha de FIGURA -------------------------------------------------------
VISTAS.figura = async (id) => {
  const env = await api('/api/figuras/' + encodeURIComponent(id));
  if (env.error) return pintaError(env);
  const f = env.data;
  const nac = f.nacimiento || {};
  const mue = f.muerte || {};
  const encEnt = (f.entidad && f.entidad.df_id)
    ? enlace('entidad/' + f.entidad.df_id, f.entidad.nombre) : celda(null);
  const encSit = (f.sitio && f.sitio.df_id)
    ? enlace('sitio/' + f.sitio.df_id, f.sitio.nombre) : celda(null);
  vista().innerHTML = lineaEstado(env) + '<h2>' + esc(f.nombre) + ' '
    + cert(f.certainty) + '</h2>'
    + panelEvidencia(env)
    + '<div class="panel"><dl class="datos">'
    + '<dt>ID de Dwarf Fortress</dt><dd class="mono">' + esc(f.df_id) + '</dd>'
    + '<dt>Raza</dt><dd>' + celda(f.race) + '</dd>'
    + '<dt>Caste</dt><dd>' + celda(f.caste) + '</dd>'
    + '<dt>Sexo</dt><dd>' + celda(f.sexo) + '</dd>'
    + '<dt>Nacimiento</dt><dd>' + celda(nac['año']) + '</dd>'
    + '<dt>Muerte</dt><dd>' + celda(mue['año'])
    + ' <small>' + esc(mue.motivo || '') + '</small></dd>'
    + '<dt>Entidad</dt><dd>' + encEnt + '</dd>'
    + '<dt>Sitio</dt><dd>' + encSit + '</dd></dl>'
    + '<p>'
    + '<button class="accion" onclick="exportar(\'figura\',\'' + esc(f.df_id)
    + '\',\'json\')">Exportar JSON</button> '
    + '<button class="secundario" onclick="exportar(\'figura\',\'' + esc(f.df_id)
    + '\',\'markdown\')">Exportar Markdown</button> '
    + '<button class="secundario" onclick="exportar(\'figura\',\'' + esc(f.df_id)
    + '\',\'markdown\',true)">Guardar en disco</button>'
    + '</p></div>'
    + '<div class="secciones"><nav>'
    + '<button class="activo" data-sec="f-eventos">Eventos ('
    + fmt((f.acontecimientos || []).length) + ')</button>'
    + '<button data-sec="f-cronologia">Cronologia</button>'
    + '<button data-sec="f-relaciones">Relaciones ('
    + fmt((f.relaciones_sociales || {}).total || 0) + ')</button>'
    + '<button data-sec="f-artefactos">Artefactos</button>'
    + '<button data-sec="f-identidad">Identidad</button>'
    + '</nav><div class="contenido-seccion" id="f-panel"></div></div>';

  panelEvents({
    'f-eventos': async () => {
      const e = await api('/api/figuras/' + id + '/eventos?limit=200');
      if (e.error) return pintaError(e);
      return tabla(CAB_EVENTOS, e.data.map(filaEvento))
        + truncado(e, 'eventos');
    },
    'f-cronologia': async () => {
      const e = await api('/api/figuras/' + id + '/cronologia?limit=300');
      if (e.error) return pintaError(e);
      return bloqueCronologia(e.data.linea_temporal, e.data.rango_anios);
    },
    'f-relaciones': async () => {
      const e = await api('/api/figuras/' + id + '/relaciones?limit=300');
      if (e.error) return pintaError(e);
      const filas = e.data.map((r) => [
        celda(r.tipo), esc(r['año'] === null ? '-' : r['año']),
        (r.otra_figura_id && !desconocido(r.otra_figura_nombre))
          ? enlace('figura/' + r.otra_figura_id, r.otra_figura_nombre)
          : celda(r.otra_figura_nombre),
        r.evento_id ? enlace('evento/' + r.evento_id, r.evento_id) : '-',
        r.evento_existe ? 'registrado'
          : '<span class="cert UNKNOWN">no consta</span>']);
      return tabla(['Tipo', 'Anio', 'Con', 'Evento citado', 'Nota'], filas)
        + truncado(e, 'relaciones')
        + '<div class="truncado">' + esc(e.nota_grafo || '') + '</div>';
    },
    'f-artefactos': async () => {
      const e = await api('/api/figuras/' + id + '/artefactos');
      if (e.error) return pintaError(e);
      return tabla(['Artefacto', 'ID', 'Tipo'], e.data.map((a) => [
        enlace('artefacto/' + a.df_id, a.nombre), celda(a.df_id), celda(a.tipo)]));
    },
    'f-identidad': async () => {
      const e = await api('/api/figuras/' + id + '/identidad');
      if (e.error) return pintaError(e);
      const d = e.data;
      if (desconocido(d.nombre)) {
        return '<p class="vacio">' + esc(d.motivo || 'sin identidad asociada')
          + ' ' + cert('UNKNOWN') + '</p>';
      }
      return '<dl class="datos"><dt>Nombre asociado</dt><dd>'
        + celda(d.nombre) + '</dd><dt>Origen</dt><dd>'
        + celda(d.source) + '</dd></dl>';
    },
  }, 'f-eventos', 'f-panel', 'f');
};


// --- Ficha de ENTIDAD -------------------------------------------------------
VISTAS.entidad = async (id) => {
  const env = await api('/api/entidades/' + encodeURIComponent(id));
  if (env.error) return pintaError(env);
  const e = env.data;
  vista().innerHTML = lineaEstado(env) + '<h2>' + esc(e.nombre) + ' '
    + cert(e.certainty) + '</h2>'
    + panelEvidencia(env)
    + '<div class="panel"><dl class="datos">'
    + '<dt>ID</dt><dd class="mono">' + esc(e.df_id) + '</dd>'
    + '<dt>Tipo</dt><dd>' + celda(e.tipo) + '</dd>'
    + '<dt>Posicion</dt><dd>' + celda(e.posicion) + '</dd>'
    + '<dt>Figuras</dt><dd>' + fmt(e.figuras) + '</dd>'
    + '<dt>Sitios</dt><dd>' + fmt(e.sitios) + '</dd>'
    + '<dt>Eventos</dt><dd>' + fmt(e.eventos) + '</dd></dl></div>'
    + '<div class="secciones"><nav>'
    + '<button class="activo" data-sec="e-miembros">Miembros ('
    + fmt(e.figuras) + ')</button>'
    + '<button data-sec="e-sitios">Sitios (' + fmt(e.sitios) + ')</button>'
    + '<button data-sec="e-eventos">Eventos</button>'
    + '<button data-sec="e-cronologia">Cronologia</button>'
    + '</nav><div class="contenido-seccion" id="e-panel"></div></div>';

  panelEvents({
    'e-miembros': async () => {
      const r = await api('/api/entidades/' + id + '/miembros');
      if (r.error) return pintaError(r);
      return tabla(['Nombre', 'ID', 'Raza', 'Eventos'], r.data.map((m) => [
        enlace('figura/' + m.df_id, m.nombre), celda(m.df_id), celda(m.race),
        esc(m.eventos)])) + truncado(r, 'miembros');
    },
    'e-sitios': async () => {
      const r = await api('/api/entidades/' + id + '/sitios');
      if (r.error) return pintaError(r);
      return tabla(['Sitio', 'ID', 'Tipo', 'Coordenadas'], r.data.map((s) => [
        enlace('sitio/' + s.df_id, s.nombre), celda(s.df_id), celda(s.tipo),
        (Array.isArray(s.coordenadas) && s.coordenadas.length)
          ? esc(s.coordenadas.map((c) => c.join(',')).join(' | '))
          : celda(null)])) + truncado(r, 'sitios');
    },
    'e-eventos': async () => {
      const r = await api('/api/entidades/' + id + '/eventos?limit=200');
      if (r.error) return pintaError(r);
      return tabla(CAB_EVENTOS, r.data.map(filaEvento))
        + truncado(r, 'eventos');
    },
    'e-cronologia': async () => {
      const r = await api('/api/entidades/' + id + '/cronologia?limit=300');
      if (r.error) return pintaError(r);
      return bloqueCronologia(r.data.linea_temporal, r.data.rango_anios);
    },
  }, 'e-miembros', 'e-panel', 'e');
};


// --- Ficha de SITIO ---------------------------------------------------------
VISTAS.sitio = async (id) => {
  const env = await api('/api/sitios/' + encodeURIComponent(id));
  if (env.error) return pintaError(env);
  const s = env.data;
  const coords = (Array.isArray(s.coordenadas) && s.coordenadas.length)
    ? s.coordenadas.map((c) => c.join(',')).join(' | ') : null;
  const encCiv = (s.civilizacion && s.civilizacion.df_id)
    ? enlace('entidad/' + s.civilizacion.df_id, s.civilizacion.nombre)
    : celda(null);
  const encOwn = (s.propietario_actual && s.propietario_actual.df_id)
    ? enlace('entidad/' + s.propietario_actual.df_id,
      s.propietario_actual.nombre) : celda(null);
  vista().innerHTML = lineaEstado(env) + '<h2>' + esc(s.nombre) + ' '
    + cert(s.certainty) + '</h2>'
    + panelEvidencia(env)
    + '<div class="panel"><dl class="datos">'
    + '<dt>ID</dt><dd class="mono">' + esc(s.df_id) + '</dd>'
    + '<dt>Tipo (tal cual en Dwarf Fortress)</dt><dd><strong>'
    + celda(s.tipo) + '</strong></dd>'
    + '<dt>Coordenadas</dt><dd>' + celda(coords) + '</dd>'
    + '<dt>Civilizacion</dt><dd>' + encCiv + '</dd>'
    + '<dt>Propietario actual</dt><dd>' + encOwn + '</dd>'
    + '<dt>Figuras asociadas</dt><dd>' + fmt(s.figuras_asociadas) + '</dd>'
    + '<dt>Eventos</dt><dd>' + fmt(s.eventos) + ' '
    + (s.certainty_eventos ? cert(s.certainty_eventos) : '') + '</dd>'
    + '<dt>Artefactos</dt><dd>' + fmt(s.artefactos) + '</dd></dl>'
    + (s.nota_eventos ? '<div class="truncado">' + esc(s.nota_eventos)
      + '</div>' : '')
    + '<p><button class="accion" onclick="exportar(\'sitio\',\'' + esc(s.df_id)
    + '\',\'json\')">Exportar JSON</button> '
    + '<button class="secundario" onclick="exportar(\'sitio\',\'' + esc(s.df_id)
    + '\',\'markdown\')">Exportar Markdown</button></p></div>'
    + '<div class="secciones"><nav>'
    + '<button class="activo" data-sec="s-cronologia">Cronologia</button>'
    + '<button data-sec="s-eventos">Eventos (' + fmt(s.eventos) + ')</button>'
    + '<button data-sec="s-figuras">Figuras ('
    + fmt(s.figuras_asociadas) + ')</button>'
    + '<button data-sec="s-geo">Geografia y construcciones</button>'
    + '</nav><div class="contenido-seccion" id="s-panel"></div></div>';

  panelEvents({
    's-cronologia': async () => {
      const r = await api('/api/sitios/' + id + '/cronologia?limit=300');
      if (r.error) return pintaError(r);
      return bloqueCronologia(r.data.linea_temporal, r.data.rango_anios);
    },
    's-eventos': async () => {
      const r = await api('/api/sitios/' + id + '/eventos?limit=200');
      if (r.error) return pintaError(r);
      return tabla(CAB_EVENTOS, r.data.map(filaEvento))
        + truncado(r, 'eventos');
    },
    's-figuras': async () => {
      const r = await api('/api/sitios/' + id + '/figuras');
      if (r.error) return pintaError(r);
      return tabla(['Nombre', 'ID', 'Raza', 'Eventos'], r.data.map((f) => [
        enlace('figura/' + f.df_id, f.nombre), celda(f.df_id), celda(f.race),
        esc(f.eventos === undefined ? '-' : f.eventos)]))
        + truncado(r, 'figuras');
    },
    's-geo': async () => {
      const r = await api('/api/sitios/' + id);
      const cs = r.data.construcciones || [];
      if (!cs.length) {
        return '<p class="vacio">Sin construcciones registradas en este sitio. '
          + 'Esto NO significa que no hubiera ninguna.</p>';
      }
      return tabla(['Construccion', 'Tipo', 'Coordenadas', 'Enlace'],
        cs.map((c) => [celda(c.nombre), celda(c.tipo),
          esc((c.coordenadas || []).map((x) => x.join(',')).join(' | ')),
          cert(c.certainty) + ' ' + esc(c.metodo || '')]));
    },
  }, 's-cronologia', 's-panel', 's');
};


// --- Ficha de ARTEFACTO -----------------------------------------------------
VISTAS.artefacto = async (id) => {
  const env = await api('/api/artefactos/' + encodeURIComponent(id));
  if (env.error) return pintaError(env);
  const a = env.data;
  const encProp = a.propietario_hfid
    ? enlace('figura/' + a.propietario_hfid, a.propietario_nombre)
    : celda(null);
  const encSitio = a.sitio_id
    ? enlace('sitio/' + a.sitio_id, a.sitio_nombre) : celda(null);
  const cr = a.creador || {};
  const encCreador = cr.figura_id
    ? enlace('figura/' + cr.figura_id, cr.nombre) : celda(null);
  vista().innerHTML = lineaEstado(env) + '<h2>' + esc(a.nombre) + ' '
    + cert(a.certainty) + '</h2>'
    + panelEvidencia(env)
    + '<div class="panel"><dl class="datos">'
    + '<dt>ID</dt><dd class="mono">' + esc(a.df_id) + '</dd>'
    + '<dt>Tipo</dt><dd>' + celda(a.tipo) + '</dd>'
    + '<dt>Subtipo</dt><dd>' + celda(a.subtipo) + '</dd>'
    + '<dt>Material</dt><dd>' + celda(a.material) + '</dd>'
    + '<dt>Objeto escrito</dt><dd>' + (a.es_escrito ? 'si' : 'no consta')
    + '</dd>'
    + '<dt>Propietario</dt><dd>' + encProp + '</dd>'
    + '<dt>Sitio</dt><dd>' + encSitio + '</dd>'
    + '<dt>Creador</dt><dd>' + encCreador + ' <small>'
    + esc(cr.metodo || '') + '</small></dd></dl></div>'
    + '<div id="a-eventos"></div>';
  const r = await api('/api/artefactos/' + id + '/eventos?limit=200');
  const panel = document.getElementById('a-eventos');
  if (r.error) {
    panel.innerHTML = '<p class="vacio">Sin eventos.</p>';
    return;
  }
  panel.innerHTML = '<h3>Eventos que lo mencionan ('
    + fmt(r.total_encontrados) + ')</h3>'
    + tabla(CAB_EVENTOS, r.data.map(filaEvento)) + truncado(r, 'eventos');
};

// --- Ficha de EVENTO --------------------------------------------------------
VISTAS.evento = async (id) => {
  const env = await api('/api/eventos/' + encodeURIComponent(id));
  if (env.error) return pintaError(env);
  const e = env.data;
  const p = e.participantes || {};
  const encFig = (hf, nombre) => (hf
    ? enlace('figura/' + hf, nombre || hf) : celda(null));
  const nota = (e.relaciones_adicionales || {}).nota
    || 'Este evento no tiene relaciones adicionales registradas.';
  vista().innerHTML = lineaEstado(env) + '<h2>Evento ' + esc(e.df_id) + ' '
    + cert(e.certainty) + '</h2>'
    + panelEvidencia(env)
    + '<div class="panel"><dl class="datos">'
    + '<dt>Anio</dt><dd>' + celda(e['año'])
    + ' <small>' + esc(e.segundos72 === null ? '' : e.segundos72)
    + ' (segundos72)</small></dd>'
    + '<dt>Tipo</dt><dd><strong>' + celda(e.tipo) + '</strong></dd>'
    + '<dt>Subtipo</dt><dd>' + celda(e.subtipo) + '</dd>'
    + '<dt>Estado</dt><dd>' + celda(e.estado) + '</dd>'
    + '<dt>Causa registrada</dt><dd>' + celda(e.causa) + '</dd>'
    + '<dt>Figura principal</dt><dd>' + encFig(p.hfid, p.nombre) + '</dd>'
    + '<dt>Objetivo</dt><dd>' + encFig(p.objetivo_hfid, 'figura objetivo')
    + '</dd>'
    + '<dt>Grupo 1 / Grupo 2</dt><dd>' + encFig(p.grupo_1_hfid)
    + ' / ' + encFig(p.grupo_2_hfid) + '</dd>'
    + '<dt>Entidad</dt><dd>'
    + ((e.entidad && e.entidad.df_id)
      ? enlace('entidad/' + e.entidad.df_id, e.entidad.nombre) : celda(null))
    + '</dd>'
    + '<dt>Sitio</dt><dd>'
    + ((e.sitio && e.sitio.df_id)
      ? enlace('sitio/' + e.sitio.df_id, e.sitio.nombre) : celda(null))
    + '</dd></dl></div>'
    + '<p class="vacio">' + esc(nota) + '</p>';
};


// --- Explorador de EVENTOS -------------------------------------------------
VISTAS.eventos = async (q) => {
  const p = new URLSearchParams(q || '');
  const tipos = await api('/api/eventos/tipos');
  const opciones = ['<option value="">todos</option>'].concat(
    (tipos.data || []).map((t) => '<option value="' + esc(t.tipo) + '"'
      + (p.get('tipo') === t.tipo ? ' selected' : '') + '>'
      + esc(t.tipo) + ' (' + fmt(t.eventos) + ')</option>')).join('');

  const filtrar = async () => {
    const f = new URLSearchParams();
    ['year', 'from', 'to', 'type', 'figure', 'site', 'limit'].forEach((k) => {
      const campo = document.getElementById('ev-' + k);
      if (campo && campo.value.trim()) f.set(k, campo.value.trim());
    });
    const env = await api('/api/eventos?' + f.toString());
    const destino = document.getElementById('ev-resultado');
    if (env.error) {
      destino.innerHTML = '<div class="error"><strong>'
        + esc(env.error.codigo) + '</strong><br>' + esc(env.error.mensaje)
        + '</div>';
      return;
    }
    destino.innerHTML = '<h3>' + fmt(env.total_encontrados)
      + ' eventos encontrados</h3>'
      + tabla(CAB_EVENTOS, env.data.map(filaEvento))
      + truncado(env, 'eventos');
  };
  window.filtrarEventos = filtrar;

  vista().innerHTML = '<h2>Explorador de eventos</h2>'
    + '<div class="filtros">'
    + '<div class="campo"><label>Anio</label><input id="ev-year" value="'
    + esc(p.get('year') || '') + '"></div>'
    + '<div class="campo"><label>Desde</label><input id="ev-from" value="'
    + esc(p.get('from') || '') + '"></div>'
    + '<div class="campo"><label>Hasta</label><input id="ev-to" value="'
    + esc(p.get('to') || '') + '"></div>'
    + '<div class="campo"><label>Tipo</label><select id="ev-type">' + opciones
    + '</select></div>'
    + '<div class="campo"><label>Figura (ID)</label><input id="ev-figure" value="'
    + esc(p.get('figure') || '') + '"></div>'
    + '<div class="campo"><label>Sitio (ID)</label><input id="ev-site" value="'
    + esc(p.get('site') || '') + '"></div>'
    + '<div class="campo"><label>Max. filas</label><input id="ev-limit" value="'
    + esc(p.get('limit') || '100') + '"></div>'
    + '<button class="accion" onclick="filtrarEventos()">Buscar</button>'
    + '</div><div id="ev-resultado"></div>';
  filtrar();
};

// --- CRONOLOGIA GLOBAL -----------------------------------------------------
VISTAS.cronologia = async () => {
  const stats = await api('/api/stats');
  vista().innerHTML = '<h2>Cronologia</h2>'
    + '<div class="filtros">'
    + '<div class="campo"><label>Desde</label><input id="cr-desde" value="'
    + stats.data.anio_min + '"></div>'
    + '<div class="campo"><label>Hasta</label><input id="cr-hasta" value="'
    + stats.data.anio_max + '"></div>'
    + '<button class="accion" onclick="cargarCronologia()">Ver</button></div>'
    + '<p class="vacio">El orden es el que el nucleo valida (anio, seconds72). '
    + 'No se inventan fechas ni se completan anos vacios.</p>'
    + '<div id="cr-salida"></div>';
  window.cargarCronologia = async () => {
    const d = document.getElementById('cr-desde').value.trim();
    const h = document.getElementById('cr-hasta').value.trim();
    const env = await api('/api/eventos?from=' + encodeURIComponent(d)
      + '&to=' + encodeURIComponent(h) + '&limit=500');
    const salida = document.getElementById('cr-salida');
    if (env.error) {
      salida.innerHTML = '<div class="error">' + esc(env.error.mensaje)
        + '</div>';
      return;
    }
    salida.innerHTML = bloqueCronologia(env.data, [d, h]);
  };
  window.cargarCronologia();
};


// --- GEOGRAFIA -------------------------------------------------------------
VISTAS.geografia = async () => {
  const env = await api('/api/geografia');
  if (env.error) return pintaError(env);
  const g = env.data;
  const tarjeta = (x, etiqueta) => '<div class="tarjeta"><span class="cifra">'
    + fmt(x.registros) + '</span><span class="etiqueta">' + etiqueta + ' | '
    + fmt(x.con_nombre) + ' con nombre</span></div>';
  vista().innerHTML = '<h2>Geografia</h2>'
    + '<p class="vacio">' + esc(g.nota_rivers || '') + '</p>'
    + '<div class="rejilla">' + tarjeta(g.rivers, 'rios')
    + tarjeta(g.landmasses, 'masas de tierra')
    + tarjeta(g.mountain_peaks, 'picos')
    + tarjeta(g.world_constructions, 'construcciones') + '</div>'
    + '<div class="filtros" style="margin-top:14px">'
    + '<div class="campo"><label>Capa</label><select id="geo-capa">'
    + '<option value="mountain_peaks">picos</option>'
    + '<option value="landmasses">masas de tierra</option>'
    + '<option value="world_constructions">construcciones del mundo</option>'
    + '<option value="rivers">rios</option></select></div>'
    + '<div class="campo"><label>Coordenada (x, y)</label>'
    + '<input id="geo-xy" placeholder="112, 20"></div>'
    + '<button class="accion" onclick="cargarGeo()">Ver</button></div>'
    + '<div id="geo-salida"></div>';

  window.cargarGeo = async () => {
    const salida = document.getElementById('geo-salida');
    const xy = document.getElementById('geo-xy').value.trim();
    if (xy) {
      const partes = xy.split(',').map((s) => s.trim());
      if (partes.length !== 2) {
        salida.innerHTML = '<div class="error">Coordenada con formato '
          + 'incorrecto: usa "x, y".</div>';
        return;
      }
      const r = await api('/api/geografia/construcciones/'
        + encodeURIComponent(partes[0]) + '/' + encodeURIComponent(partes[1]));
      if (r.error) {
        salida.innerHTML = '<div class="error">' + esc(r.error.mensaje)
          + '</div>';
        return;
      }
      salida.innerHTML = '<h3>Construcciones en (' + esc(partes[0]) + ', '
        + esc(partes[1]) + ') ' + cert('DERIVED') + '</h3>'
        + '<p class="vacio">' + esc(r.metodo) + '</p>'
        + tabla(['Nombre', 'Tipo', 'ID'], r.data.map((c) => [
          celda(c.nombre), celda(c.tipo), celda(c.df_id)]));
      return;
    }
    // El desplegable puede no existir todavia (p.ej. si se llama al
    // arrancar): en ese caso se pide el resumen general, no una capa.
    const sel = document.getElementById('geo-capa');
    const c = sel && sel.value ? sel.value : 'mountain_peaks';
    const r = await api('/api/geografia/' + encodeURIComponent(c) + '?limit=200');
    if (r.error) {
      salida.innerHTML = '<div class="error">' + esc(r.error.mensaje)
        + '</div>';
      return;
    }
    const items = Array.isArray(r.data) ? r.data : [];
    salida.innerHTML = '<h3>' + esc(r.capa || c) + ' ' + cert('FACT') + '</h3>'
      + (r.nota_derivada ? '<div class="truncado">' + esc(r.nota_derivada)
        + '</div>' : '')
      + tabla(['Nombre', 'ID', 'Tipo', 'Coordenadas'], items.map((i) => [
        celda(i.nombre), celda(i.df_id), celda(i.tipo || '-'),
        (Array.isArray(i.coordenadas) && i.coordenadas.length)
          ? esc(i.coordenadas.map((c2) => c2.join(',')).join(' | '))
          : celda(null)])) + truncado(r, 'elementos');
  };
  window.cargarGeo();
};


// --- LIMITACIONES ----------------------------------------------------------
VISTAS.limitaciones = async () => {
  const env = await api('/api/limitaciones');
  if (env.error) return pintaError(env);
  const d = env.data;
  const fila = (k, v, extra) => '<dt>' + k + '</dt><dd>' + v
    + (extra ? ' <small>' + esc(extra) + '</small>' : '') + '</dd>';
  vista().innerHTML = '<h2>Que se puede y que no se puede saber</h2>'
    + '<p>Estas limitaciones no son notas al pie: condicionan cada pantalla.</p>'
    + '<div class="panel"><dl class="datos">'
    + fila('Rango temporal', 'anos ' + fmt(d.rango_temporal[0]) + '-'
      + fmt(d.rango_temporal[1]))
    + fila('Era historica', cert('UNKNOWN'), d.era_motivo)
    + fila('Eventos sin participantes', fmt(d.eventos_sin_participantes)
      + ' de ' + fmt(d.eventos_totales))
    + fila('Figuras sin eventos', fmt(d.figuras_sin_eventos) + ' de '
      + fmt(d.figuras_totales))
    + fila('Figuras sin muerte registrada',
      fmt(d.figuras_sin_muerte_registrada))
    + fila('Relaciones sin evento asociado', fmt(d.relaciones_sin_evento))
    + fila('Grafo de relaciones', 'dirigido y asimetrico')
    + fila('Tabla de guerras', 'no existe en el XML')
    + fila('Conflictos entre fuentes sin resolver',
      fmt(d.conflictos_entre_fuentes_sin_resolver))
    + '</dl><h3>Por que importa cada una</h3><ul>'
    + '<li>' + esc(d.relaciones_motivo) + '</li>'
    + '<li>' + esc(d.grafo_motivo) + '</li>'
    + '<li>' + esc(d.guerras_motivo) + '</li>'
    + '<li>' + esc(d.conflictos_motivo) + '</li>'
    + '<li>' + esc(d.rio_motivo) + '</li>'
    + '<li>Una muerte sin registrar es <strong>UNKNOWN</strong>: no significa '
    + 'que la figura siga viva, ni que muriera fuera del rango.</li>'
    + '</ul></div>';
};

// --- EXPORTACION -----------------------------------------------------------
async function exportar(tipo, id, formato, escribir) {
  const f = new URLSearchParams({ format: formato });
  f.set(tipo, id);
  if (escribir) f.set('escribir', '1');
  const env = await api('/api/exportar?' + f.toString());
  if (env.error) {
    window.alert('No se pudo exportar:\n' + env.error.codigo + ': '
      + env.error.mensaje);
    return;
  }
  if (env.escrito_en) {
    window.alert('Guardado en:\n' + env.escrito_en);
    return;
  }
  // Sin `escribir`: se abre el contenido en una pestaña, sin tocar el disco.
  const w = window.open('', '_blank');
  if (w) {
    w.document.write('<pre>' + esc(env.data.contenido) + '</pre>');
    w.document.close();
  }
}
window.exportar = exportar;


// =============================================================================
// ROUTER Y ARRANQUE
// =============================================================================
// Rutas con hash: no requieren reconfiguracion del servidor y funcionan igual
// si este mismo HTML se copia a un hosting estatico en el futuro.
window.addEventListener('hashchange', enrutar);

function enrutar() {
  const bruto = (window.location.hash || '#/inicio').slice(1);
  const partesRuta = bruto.split('?');
  const consulta = partesRuta[1];
  const partes = partesRuta[0].split('/').filter(Boolean);
  const nombre = partes[0] || 'inicio';

  document.querySelectorAll('#menu a').forEach((a) => {
    a.classList.toggle('activo', a.getAttribute('href') === '#/' + nombre);
  });

  const fn = VISTAS[nombre];
  if (!fn) {
    vista().innerHTML = '<div class="error">Pantalla desconocida: '
      + esc(nombre) + '<br>Usa el menu superior.</div>';
    return;
  }
  vista().innerHTML = '<p class="vacio">Cargando...</p>';
  Promise.resolve(fn(partes[1], consulta)).catch((e) => {
    vista().innerHTML = '<div class="error">' + esc(String(e)) + '</div>';
  });
}

/** Limites siempre visibles, tambien fuera de su propia pantalla. */
async function cargarAviso() {
  const env = await api('/api/limitaciones');
  if (env.error) return;
  const d = env.data;
  $('#aviso-limitaciones').hidden = false;
  $('#aviso-limitaciones').innerHTML =
    '<strong>Alcance de los datos:</strong> anos ' + fmt(d.rango_temporal[0])
    + '-' + fmt(d.rango_temporal[1]) + ' | Era '
    + cert('UNKNOWN') + ' | ' + fmt(d.eventos_sin_participantes) + ' de '
    + fmt(d.eventos_totales) + ' eventos sin participantes | algunas '
    + 'coordenadas son desconocidas | las relaciones adicionales no siempre '
    + 'se vinculan a un evento concreto. '
    + '<a class="enlace" href="#/limitaciones">Ver todas las limitaciones</a>';
}

$('#form-buscar').addEventListener('submit', (ev) => {
  ev.preventDefault();
  const q = $('#q').value.trim();
  if (q) window.location.hash = '#/buscar/' + encodeURIComponent(q);
});

// Arranque.
(async () => {
  try {
    const r = await fetch('/api/salud');
    const s = await r.json();
    $('#pie-ruta').textContent = 'Datos: ' + s.data.ruta_datos;
  } catch (e) { /* la pantalla principal mostrara el error */ }
  await cargarAviso();
  enrutar();
})();
