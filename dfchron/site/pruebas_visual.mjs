/**
 * DF Legends :: auditoria visual y end-to-end en navegador REAL.
 *
 * Usa Playwright con el Chrome YA INSTALADO en el sistema (`channel: 'chrome'`).
 * No descarga ningun navegador: `npm install -D playwright` son 2 paquetes.
 *
 * QUE COMPRUEBA
 *   - capturas en los 5 tamanos exigidos;
 *   - desbordes horizontales, solapamientos y texto cortado;
 *   - recorrido de navegacion con CLICS reales;
 *   - acceso directo y recarga de rutas internas;
 *   - peticiones de red: solo a la API configurada;
 *   - estados de carga, vacios y de error.
 *
 * NO sobrescribe: cada captura lleva fecha y hora.
 *
 * Uso:  node pruebas_visual.mjs [--url=http://127.0.0.1:4400]
 */
import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const RAIZ = 'C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles';
const ARG = process.argv.find((a) => a.startsWith('--url='));
const BASE = ARG ? ARG.slice(6) : 'http://127.0.0.1:4400';
const SALIDA = join(RAIZ, '00_SOURCE', 'informes', 'fase3');
if (!existsSync(SALIDA)) mkdirSync(SALIDA, { recursive: true });

/** Marca temporal: evita sobrescribir capturas anteriores. */
const SELLO = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
let contador = 0;

function rutaCaptura(nombre) {
  const completa = join(
    SALIDA,
    `${String(++contador).padStart(2, '0')}_${nombre}_${SELLO}.png`,
  );
  return completa;
}

const hallazgos = [];
function anotar(ok, donde, detalle) {
  hallazgos.push({ ok, donde, detalle });
  console.log(`${ok ? '  OK  ' : ' FALLO'}  ${donde}  - ${detalle}`);
}

const TAMANOS = [
  { id: 'escritorio', w: 1440, h: 900 },
  { id: 'portatil', w: 1280, h: 800 },
  { id: 'tablet', w: 768, h: 1024 },
  { id: 'movil', w: 390, h: 844 },
  { id: 'movil-pequeno', w: 320, h: 700 },
];

const RUTAS = [
  { id: 'portada', ruta: '/' },
  { id: 'dashboard', ruta: '/app/world' },
  { id: 'figuras', ruta: '/app/figures' },
  { id: 'entidades', ruta: '/app/entities' },
  { id: 'sitios', ruta: '/app/sites' },
  { id: 'artefactos', ruta: '/app/artifacts' },
  { id: 'eventos', ruta: '/app/events' },
  { id: 'timeline', ruta: '/app/timeline' },
  { id: 'geografia', ruta: '/app/geography' },
  { id: 'busqueda', ruta: '/app/search?q=halesteel' },
  { id: 'ficha-figura', ruta: '/figures/712' },
  { id: 'ficha-sitio', ruta: '/sites/87' },
  { id: 'ficha-entidad', ruta: '/entities/282' },
];

const navegador = await chromium.launch({ channel: 'chrome', headless: true });

/** Peticiones de red observadas: solo debe haber la API configurada. */
const destinos = new Set();
function vigilar(ctx) {
  ctx.on('request', (r) => {
    const u = r.url();
    if (u.startsWith('data:') || u.startsWith('blob:')) return;
    destinos.add(new URL(u).origin);
  });
}

/** Medidas de renderizado reales. */
async function medir(pag) {
  return pag.evaluate(() => {
    const de = document.documentElement;
    const desbordes = [];
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      // Las tablas con scroll horizontal lo hacen a proposito.
      if (el.closest('.tabla-scroll')) continue;
      // Un elemento COMPLETAMENTE a la izquierda del viewport no es un
      // desborde: es la tecnica estandar para ocultar algo hasta que reciba
      // foco (por ejemplo `.skip-link`, que vive en left:-9999px). No genera
      // barra horizontal ni es visible, asi que no se cuenta.
      if (r.right <= 0) continue;
      // Si se sale por la derecha, SI es un problema real.
      if (r.right > de.clientWidth + 1.5) {
        desbordes.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className || '').toString().slice(0, 50),
          left: Math.round(r.left),
          right: Math.round(r.right),
        });
      }
    }
    // Texto cortado de verdad: sin scroll declarado pero mas ancho que su caja.
    const cortados = [];
    for (const el of document.querySelectorAll(
      '.stat-label, h1, h2, .tag, .stat-value, .definiciones dt, .certified',
    )) {
      const e = getComputedStyle(el);
      if (e.overflowX === 'auto' || e.overflowX === 'scroll') continue;
      if (el.scrollWidth > el.clientWidth + 1) {
        cortados.push({
          cls: (el.className || '').toString().slice(0, 40),
          texto: (el.textContent || '').trim().slice(0, 40),
          scrollW: el.scrollWidth,
          clientW: el.clientWidth,
        });
      }
    }
    const pequenos = [];
    for (const el of document.querySelectorAll('a, button')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.height < 16) pequenos.push({ txt: (el.textContent || '').trim().slice(0, 30), h: Math.round(r.height) });
    }
    return {
      scrollHorizontal: de.scrollWidth > de.clientWidth + 1,
      anchoDoc: de.scrollWidth,
      anchoVentana: de.clientWidth,
      desbordes: desbordes.slice(0, 5),
      cortados: cortados.slice(0, 5),
      pequenos: pequenos.slice(0, 5),
      texto: (document.getElementById('app')?.innerText || '').slice(0, 120),
    };
  });
}

/** Espera a que el shell haya pintado contenido real. */
async function esperarContenido(pag, ms = 20000) {
  await pag
    .waitForFunction(
      () => {
        const a = document.getElementById('app');
        return a && a.innerHTML.length > 400 && !a.innerHTML.includes('Loading');
      },
      { timeout: ms },
    )
    .catch(() => {});
}
// ==========================================================================
console.log(`\n=== 1. CAPTURAS Y MEDIDAS POR TAMANO ===`);
const medidas = [];

// `--solo=recorrido` salta la parte 1 (las 65 capturas) y comprueba solo la
// navegacion. Util cuando se corrige un selector y no hay que rehacer todo.
const SOLO = (process.argv.find((a) => a.startsWith('--solo=')) || '').slice(7);

if (SOLO === 'recorrido') {
  console.log('  (modo --solo=recorrido: se omiten las capturas)');
}

for (const t of SOLO === 'recorrido' ? [] : TAMANOS) {
  console.log(`\n-- ${t.id} ${t.w}x${t.h} --`);
  const ctx = await navegador.newContext({
    viewport: { width: t.w, height: t.h },
    deviceScaleFactor: 1,
  });
  vigilar(ctx);
  const pag = await ctx.newPage();

  for (const r of RUTAS) {
    await pag.goto(BASE + r.ruta, { waitUntil: 'networkidle', timeout: 30000 });
    await esperarContenido(pag);
    await pag.waitForTimeout(250);

    const f = rutaCaptura(`${t.id}_${r.id}`);
    await pag.screenshot({ path: f, fullPage: false });

    const m = await medir(pag);
    const ok =
      !m.scrollHorizontal &&
      m.desbordes.length === 0 &&
      m.cortados.length === 0 &&
      !m.texto.includes('Data unavailable');

    medidas.push({ tamano: t.id, ruta: r.ruta, captura: f, ...m, ok });
    anotar(
      ok,
      `${t.id} / ${r.ruta}`,
      ok
        ? `sin scroll-h (${m.anchoDoc}<=${m.anchoVentana}), sin desbordes, sin texto cortado`
        : `scrollH=${m.scrollHorizontal} desbordes=${JSON.stringify(m.desbordes)} cortados=${JSON.stringify(m.cortados)}`,
    );
  }
  await ctx.close();
}

// ==========================================================================
console.log(`\n=== 2. RECORRIDO DE NAVEGACION CON CLICS REALES ===`);
const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
vigilar(ctx);
const pag = await ctx.newPage();

const texto = () => pag.evaluate(() => document.getElementById('app')?.innerText || '');
const esperar = (frag) =>
  pag.waitForFunction(
    (f) => (document.getElementById('app')?.innerText || '').includes(f),
    frag,
    { timeout: 20000 },
  );

async function paso(titulo, accion, comprobacion) {
  try {
    await accion();
    const r = comprobacion ? await comprobacion() : true;
    anotar(!!r, titulo, r === true ? 'correcto' : String(r));
    return true;
  } catch (e) {
    anotar(false, titulo, `ERROR: ${String(e.message).split('\n')[0].slice(0, 130)}`);
    return false;
  }
}

await paso('1. Abrir el dashboard', async () => {
  await pag.goto(`${BASE}/app/world`, { waitUntil: 'networkidle' });
  await esperar('The loaded world');
}, async () => {
  const t = await texto();
  return t.includes('11.144') && t.includes('57.215') ? 'cifras reales del mundo' : 'SIN cifras';
});

// Búsqueda con ambigüedad: comprueba que NO elige sola. Es un caso aparte del
// recorrido principal, que va de la figura 712 hacia abajo.
await paso('2. Busqueda ambigua (halesteel)', async () => {
  await pag.fill('input[name="q"]', 'halesteel');
  await pag.click('form[role="search"] button[type="submit"]');
  await pag.waitForLoadState('networkidle');
  await esperar('Nothing was selected automatically');
}, async () => {
  const t = await texto();
  return t.includes('Figures') && t.includes('Sites') ? 'declara ambiguedad y lista figuras y sitios' : 'faltan grupos';
});

await paso('3. Buscar la figura 712 y abrir su ficha', async () => {
  await pag.goto(`${BASE}/app/search?q=galka%20shafttop`, { waitUntil: 'networkidle' });
  await esperar('galka shafttop');
  await pag.click('#app a[href="/figures/712"]');
  await pag.waitForLoadState('networkidle');
  await esperar('galka shafttop');
}, async () => {
  const h = await pag.evaluate(() => location.pathname);
  const t = await texto();
  return h === '/figures/712' && t.includes('MINOTAUR') ? `ficha real en ${h}` : `ruta ${h}`;
});

// La CADENA REAL verificada contra la API antes de escribir el recorrido:
//   figura 712 -> evento 826 -> sitio 111 ("faintflies", dark pits)
//              -> entidad 312 ("the infamous disloyalty")
// De los 158 eventos de la figura 712, 129 tienen sitio; se elige el primero
// que lo tiene. No se inventa ninguna relacion.
await paso('4. Desde la figura, abrir un evento CON sitio', async () => {
  await esperar('Events & chronology');
  const href = await pag.evaluate(() => {
    // Fila de la tabla de eventos que ademas tiene sitio.
    for (const tr of document.querySelectorAll('#app table tbody tr')) {
      const a = [...tr.querySelectorAll('a')].find((x) =>
        /^\/events\/\d+$/.test(x.getAttribute('href') || ''),
      );
      if (a && !/Unknown/.test(tr.children[2]?.innerText || '')) return a.getAttribute('href');
    }
    return null;
  });
  if (!href) throw new Error('ningun evento de la figura muestra un sitio');
  await pag.click(`#app a[href="${href}"]`);
  await pag.waitForLoadState('networkidle');
}, async () => {
  const h = await pag.evaluate(() => location.pathname);
  return /^\/events\/\d+$/.test(h) ? `evento en ${h}` : `ruta ${h}`;
});

await paso('5. Desde el evento, abrir el sitio relacionado', async () => {
  const href = await pag.evaluate(() => {
    const a = document.querySelector('#app a[href^="/sites/"]');
    return a ? a.getAttribute('href') : null;
  });
  if (!href) throw new Error('este evento no tiene sitio asociado');
  await pag.click(`#app a[href="${href}"]`);
  await pag.waitForLoadState('networkidle');
}, async () => {
  const h = await pag.evaluate(() => location.pathname);
  const t = await texto();
  return /^\/sites\/\d+$/.test(h) && t.includes('dark pits')
    ? `sitio real en ${h}, tipo "dark pits" preservado`
    : `ruta ${h}`;
});

await paso('6. Desde el sitio, abrir la entidad relacionada', async () => {
  const href = await pag.evaluate(() => {
    const a = document.querySelector('#app a[href^="/entities/"]');
    return a ? a.getAttribute('href') : null;
  });
  if (!href) throw new Error('este sitio no tiene entidad asociada');
  await pag.click(`#app a[href="${href}"]`);
  await pag.waitForLoadState('networkidle');
}, async () => {
  const h = await pag.evaluate(() => location.pathname);
  const t = await texto();
  return /^\/entities\/\d+$/.test(h) && t.includes('infamous disloyalty')
    ? `entidad real en ${h}`
    : `ruta ${h}`;
});

await paso('7. Volver atras dos veces', async () => {
  await pag.goBack();
  await pag.waitForLoadState('networkidle');
  await pag.waitForTimeout(700);
  await pag.goBack();
  await pag.waitForLoadState('networkidle');
  await pag.waitForTimeout(700);
}, async () => {
  const h = await pag.evaluate(() => location.pathname);
  const t = await texto();
  return t.length > 100 ? `sigue pintando contenido en ${h} (${t.length} car.)` : 'quedó vacía';
});

await paso('8. Acceso directo a /figures/712', async () => {
  await pag.goto(`${BASE}/figures/712`, { waitUntil: 'networkidle' });
  await esperar('galka shafttop');
}, async () => ((await texto()).includes('MINOTAUR') ? 'datos reales de la figura 712' : 'faltan datos'));

await paso('9. Recargar /figures/712', async () => {
  await pag.reload({ waitUntil: 'networkidle' });
  await esperar('galka shafttop');
}, async () => ((await texto()).includes('Identity') ? 'ok tras recargar' : 'quedó vacía'));

const ctx2 = await navegador.newContext({ viewport: { width: 1280, height: 800 } });
vigilar(ctx2);
const pag2 = await ctx2.newPage();
await paso('10. Abrir /figures/712 en pestana nueva', async () => {
  await pag2.goto(`${BASE}/figures/712`, { waitUntil: 'networkidle' });
  await pag2.waitForFunction(
    () => (document.getElementById('app')?.innerText || '').includes('galka shafttop'),
    { timeout: 20000 },
  );
}, async () => {
  const t = await pag2.evaluate(() => document.getElementById('app')?.innerText || '');
  return t.includes('Identity') ? 'ok en pestana independiente' : 'quedó vacía';
});
await ctx2.close();
// ==========================================================================
console.log(`\n=== 3. API: CERTIDUMBRE, ERRORES Y ESTADOS ===`);

await paso('11. Etiquetas FACT y Unknown visibles', async () => {
  await pag.goto(`${BASE}/figures/712`, { waitUntil: 'networkidle' });
  await esperar('galka shafttop');
}, async () => {
  const h = await pag.evaluate(() => {
    const t = document.getElementById('app').innerText;
    return { FACT: t.includes('FACT'), UNKNOWN: t.includes('Unknown') };
  });
  return h.FACT && h.UNKNOWN ? 'FACT y Unknown presentes' : JSON.stringify(h);
});

await paso('12. UNKNOWN no se presenta como afirmacion', async () => {
  const t = await texto();
  // En la ficha 712 el nacimiento no consta: debe decir Unknown, no una fecha.
  const inventa = /Born\s+(?!Unknown)\S+/i.test(t) || /Died\s+(?!Unknown)\S+/i.test(t);
  return !inventa ? 'nacimiento y muerte: Unknown, sin fecha inventada' : 'INVENTA una fecha';
});

await paso('13. Truncamiento declarado en listados', async () => {
  await pag.goto(`${BASE}/app/figures`, { waitUntil: 'networkidle' });
  await esperar('figures recorded');
}, async () => {
  const t = await texto();
  return /Showing\s+50\s+of\s+11\.144/.test(t)
    ? 'muestra "Showing 50 of 11.144"'
    : `no declara recorte: ${t.slice(0, 90)}`;
});

await paso('14. Filtro combinado de eventos', async () => {
  await pag.goto(`${BASE}/app/events?from=1&to=3&figure=712`, { waitUntil: 'networkidle' });
}, async () => {
  const t = await texto();
  const m = t.match(/(\d+) events match/);
  return m && m[1] === '6' ? '6 eventos: el rango manda (no los 158)' : `total: ${m ? m[1] : '?'}`;
});

await paso('15. Paginacion navegable', async () => {
  await pag.goto(`${BASE}/app/figures`, { waitUntil: 'networkidle' });
  await esperar('figures recorded');
  const antes = await texto();
  await pag.click('.paginacion a:has-text("Next")');
  await pag.waitForLoadState('networkidle');
  await pag.waitForTimeout(700);
  const despues = await texto();
  return antes !== despues && despues.includes('Page 2') ? 'la pagina 2 carga datos distintos' : 'la pagina 2 no cambió';
});

await paso('16. Error de API se muestra comprensible', async () => {
  const c = await navegador.newContext({ viewport: { width: 1280, height: 800 } });
  const p = await c.newPage();
  await p.route('**/api/**', (r) => r.abort());
  await p.goto(`${BASE}/app/world`, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(1800);
  const t = await p.evaluate(() => document.getElementById('app')?.innerText || '');
  await c.close();
  return !t.includes('undefined') && (t.includes('Data unavailable') || t.includes('could not'))
    ? 'mensaje claro, sin "undefined"'
    : `inesperado: ${t.slice(0, 100)}`;
});

await paso('17. Busqueda sin resultados', async () => {
  await pag.goto(`${BASE}/app/search?q=zzzqqqnoexiste`, { waitUntil: 'networkidle' });
}, async () => ((await texto()).includes('No results') ? 'mensaje de vacío correcto' : 'no lo muestra'));

await paso('18. Ficha inexistente', async () => {
  await pag.goto(`${BASE}/figures/99999999`, { waitUntil: 'networkidle' });
}, async () => ((await texto()).includes('not found') ? 'avisa de que no existe' : 'mensaje raro'));

// ==========================================================================
console.log(`\n=== 4. RED: DESTINOS REALES ===`);
const permitidos = new Set([BASE, 'http://127.0.0.1:877', 'http://127.0.0.1:4400', 'http://localhost:4321']);
const outsiders = [...destinos].filter((d) => !permitidos.has(d));
anotar(
  outsiders.length === 0,
  'Sin peticiones a servidores externos',
  outsiders.length
    ? `INESPERADOS: ${outsiders.join(', ')}`
    : `solo ${[...destinos].join(', ')}`,
);

// ==========================================================================
console.log(`\n=== 5. FALLBACK 404 ===`);
await paso('19. Ruta inexistente: el shell responde y avisa', async () => {
  await pag.goto(`${BASE}/no/existe/esta/ruta`, { waitUntil: 'networkidle' });
}, async () => {
  const t = await texto();
  return t.includes('not found') ? 'shell servido y mensaje correcto' : `inesperado: ${t.slice(0, 70)}`;
});

await ctx.close();
await navegador.close();

// ==========================================================================
const fallos = hallazgos.filter((h) => !h.ok);
writeFileSync(
  join(SALIDA, `medidas_${SELLO}.json`),
  JSON.stringify({ sello: SELLO, base: BASE, total: hallazgos.length, fallos: fallos.length, destinos: [...destinos], outsiders, medidas }, null, 2),
  'utf8',
);

console.log(`\n=== RESUMEN ===`);
console.log(`Comprobaciones: ${hallazgos.length}  |  fallos: ${fallos.length}`);
console.log(`Capturas: ${contador}  |  medidas: medidas_${SELLO}.json`);
if (fallos.length) {
  console.log('\nFALLOS:');
  for (const f of fallos) console.log(`  - ${f.donde}: ${f.detalle}`);
}
process.exit(fallos.length ? 1 : 0);