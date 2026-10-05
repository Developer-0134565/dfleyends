/**
 * DF Legends :: auditoria del EXPLORADOR GEOGRAFICO en navegador REAL.
 *
 * Mismaapproach que `pruebas_visual.mjs` (Playwright sobre el Chrome ya
 * instalado), pero centrada en la geografia: mapa, coordenadas, navegacion y
 * responsive en las 9 resoluciones exigidas por la Fase 5.
 *
 * Todo lo que se comprueba sale de la API real. Si un punto no aparece, es un
 * fallo: no se maquilla ni se rellena.
 *
 * Uso:  node pruebas_geografia.mjs [--url=http://127.0.0.1:4400]
 */
import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const RAIZ = 'C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles';
const ARG = process.argv.find((a) => a.startsWith('--url='));
const BASE = ARG ? ARG.slice(6) : 'http://127.0.0.1:4400';
const API = 'http://127.0.0.1:877';
const SALIDA = join(RAIZ, '00_SOURCE', 'informes', 'fase5');
if (!existsSync(SALIDA)) mkdirSync(SALIDA, { recursive: true });

const SELLO = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
let contador = 0;
const captura = (n) =>
  join(SALIDA, `${String(++contador).padStart(2, '0')}_${n}_${SELLO}.png`);

const hallazgos = [];
const anotar = (ok, donde, detalle) => {
  hallazgos.push({ ok, donde, detalle });
  console.log(`${ok ? '  OK  ' : ' FALLO'}  ${donde}  - ${detalle}`);
};

/** Las 9 resoluciones que pide la Fase 5, de la mas estrecha a la mas ancha. */
const TAMANOS = [
  { id: '320', w: 320, h: 700 },
  { id: '360', w: 360, h: 780 },
  { id: '390', w: 390, h: 844 },
  { id: '414', w: 414, h: 896 },
  { id: '600', w: 600, h: 900 },
  { id: '768', w: 768, h: 1024 },
  { id: '1024', w: 1024, h: 800 },
  { id: '1280', w: 1280, h: 800 },
  { id: '1440', w: 1440, h: 900 },
];

const navegador = await chromium.launch({ channel: 'chrome', headless: true });

/**
 * Ejecuta un bloque de comprobaciones sin tumbar la auditoria entera.
 *
 * Antes, un timeout en el paso 2 abortaba el proceso y los pasos 3-7 nunca se
 * ejecutaban: un fallo hacia que no hubiera resultados. Aqui cada bloque es
 * independiente y su error se registra como un hallazgo mas.
 */
async function bloque(nombre, fn) {
  try {
    await fn();
  } catch (e) {
    anotar(false, nombre, `excepcion: ${String(e.message).split('\n')[0]}`);
  }
}

/** Peticiones de red observadas: solo debe aparecer la API configurada. */
const destinos = new Set();
function vigilar(ctx) {
  ctx.on('request', (r) => {
    const u = r.url();
    if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')) {
      destinos.add(new globalThis.URL(u).origin);
    }
  });
}

async function nuevaPagina(ctx) {
  const p = await ctx.newPage();
  p.on('pageerror', (e) => anotar(false, 'consola', `error JS: ${e.message}`));
  return p;
}
// ==================================================================== 1 ===
// La vista de Geografia carga y trae datos REALES del mapa.
console.log('\n--- 1. La vista carga ---');
await bloque('paso 1 · carga', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  vigilar(ctx);
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('#app h1', { timeout: 20000 });

  const h1 = (await pag.textContent('#app h1'))?.trim();
  anotar(h1 === 'Geography', 'titulo', `h1 = ${JSON.stringify(h1)}`);

  const puntos = await pag.locator('svg.mapa a.mapa-punto').count();
  anotar(puntos > 0, 'mapa', `${puntos} puntos navegables dibujados`);

  const hayForm = await pag.locator('form[data-form-coords]').count();
  anotar(hayForm === 1, 'formulario', 'el formulario X/Y esta presente');

  const hayZ = (await pag.textContent('#app'))?.includes('no Z');
  anotar(!!hayZ, 'contrato Z', 'la UI declara que no hay Z');

  await pag.screenshot({ path: captura('geography_mundo_completo'), fullPage: true });
  await ctx.close();
});

// ==================================================================== 2 ===
// Coordenadas reales: (112, 20) contiene la fortaleza #87.
console.log('\n--- 2. Coordenadas reales (112, 20) ---');
await bloque('paso 2 · punto real', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography?x=112&y=20`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('#app section.panel', { timeout: 20000 });

  const cuerpo = (await pag.textContent('#app')) ?? '';
  anotar(cuerpo.includes('Location 112, 20'), 'punto', 'muestra "Location 112, 20"');
  anotar(cuerpo.includes('halesteel'), 'sitio', 'aparece la fortaleza real #87');

  // El tipo REAL debe verse, no un "site" generico.
  const fortress = await pag.locator('.tag--tipo', { hasText: 'fortress' }).count();
  anotar(fortress > 0, 'tipo real', `${fortress} etiqueta(s) "fortress"`);

  const zNull = await pag.locator('code', { hasText: 'null' }).count();
  anotar(zNull > 0, 'Z', 'Z se muestra como null');

  const constr = await pag.locator('h3', { hasText: 'World constructions' }).count();
  anotar(constr > 0, 'construcciones', 'lista las construcciones del punto');

  await pag.screenshot({ path: captura('geography_punto_112_20'), fullPage: true });
  await ctx.close();
});

// ==================================================================== 3 ===
// El formulario escribe en la URL y recarga: navegacion de verdad.
console.log('\n--- 3. El formulario funciona ---');
await bloque('paso 3 · formulario', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('form[data-form-coords] input[name="x"]', { timeout: 20000 });

  await pag.fill('input[name="x"]', '112');
  await pag.fill('input[name="y"]', '20');
  await pag.click('form[data-form-coords] button[type="submit"]');
  await pag.waitForURL(/x=112/, { timeout: 20000 });
  await pag.waitForLoadState('networkidle');
  await pag.waitForSelector('#app section.panel', { timeout: 20000 });

  anotar(pag.url().includes('x=112') && pag.url().includes('y=20'), 'URL',
    `la URL es compartible: ${pag.url().split('?')[1]}`);
  const cuerpo = (await pag.textContent('#app')) ?? '';
  anotar(cuerpo.includes('halesteel'), 'resultado', 'el formulario trae datos reales');

  // Recarga: la URL directa debe seguir funcionando.
  await pag.reload({ waitUntil: 'networkidle' });
  await pag.waitForSelector('#app section.panel', { timeout: 20000 });
  anotar(((await pag.textContent('#app')) ?? '').includes('halesteel'),
    'recarga', 'tras recargar sigue mostrando el mismo resultado');
  await ctx.close();
});
// ==================================================================== 4 ===
// Cadena de navegación exigida: mapa -> sitio -> evento -> otra localisation.
console.log('\n--- 4. Navegacion con clics reales ---');
await bloque('paso 4 · navegacion', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography?x=112&y=20`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('#app a[href^="/sites/"]', { timeout: 20000 });

  // Mapa -> sitio
  await pag.click('#app .lista-rel a[href^="/sites/"]');
  await pag.waitForURL(/\/sites\/\d+/, { timeout: 20000 });
  await pag.waitForLoadState('networkidle');
  await pag.waitForSelector('#app h1', { timeout: 20000 });
  const sitioH1 = (await pag.textContent('#app h1'))?.trim();
  anotar(sitioH1 === 'halesteel', 'mapa -> sitio', `abre "${sitioH1}"`);

  // Sitio -> figuras (pestana de la ficha)
  const hayFiguras = await pag.locator('a[href*="/figures/"]').count();
  anotar(hayFiguras > 0, 'sitio -> figuras',
    `${hayFiguras} enlace(s) a figuras desde la ficha`);

  // Sitio -> eventos
  const hayEventos = await pag.locator('a[href*="/events/"]').count();
  anotar(hayEventos > 0, 'sitio -> eventos',
    `${hayEventos} enlace(s) a eventos desde la ficha`);

  await pag.screenshot({ path: captura('ficha_sitio_desde_mapa'), fullPage: true });

  // Volver atras debe devolver al mapa.
  await pag.goBack();
  await pag.waitForLoadState('networkidle');
  await pag.waitForSelector('#app h1', { timeout: 20000 });
  const vuelve = (await pag.textContent('#app h1'))?.trim();
  anotar(vuelve === 'Geography', 'navegacion atras', `vuelve a "${vuelve}"`);
  await ctx.close();
});

// ==================================================================== 5 ===
// Punto sin resultados: debe decirlo, sin inventar nada.
console.log('\n--- 5. Coordenada sin resultados ---');
await bloque('paso 5 · punto vacio', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography?x=1&y=1`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('#app section.panel', { timeout: 20000 });
  const cuerpo = (await pag.textContent('#app')) ?? '';
  anotar(cuerpo.includes('Nothing is recorded'),
    'punto vacio', 'lo dice explicitamente en vez de inventar');
  anotar(cuerpo.includes('does not mean'),
    'honestidad', 'advierte que no significa que no existiera');
  await pag.screenshot({ path: captura('geography_punto_vacio'), fullPage: true });
  await ctx.close();
});

// ==================================================================== 6 ===
// Responsivo: las 9 resoluciones, sin scroll horizontal ni texto cortado.
console.log('\n--- 6. Responsive ---');
const resumenResponsive = [];
for (const t of TAMANOS) {
  const ctx = await navegador.newContext({
    viewport: { width: t.w, height: t.h },
    isMobile: t.w < 768,
    hasTouch: t.w < 768,
  });
  const pag = await nuevaPagina(ctx);
  try {
    await pag.goto(`${BASE}/app/geography?x=112&y=20`, { waitUntil: 'networkidle' });
    await pag.waitForSelector('svg.mapa', { timeout: 20000 });

    const m = await pag.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      cuerpoW: document.body.scrollWidth,
    }));
    const desborde = Math.max(m.scrollW, m.cuerpoW) - m.clientW;
    anotar(desborde <= 1, `responsive ${t.id}`,
      desborde <= 1 ? 'sin scroll horizontal'
        : `DESBORDE de ${desborde}px (doc ${m.scrollW} vs ${m.clientW})`);

    // Los controles deben seguir siendo utilizables y visibles.
    const btn = await pag.locator('.boton-mapa').first();
    const caja = await btn.boundingBox();
    anotar(!!caja && caja.height >= 28 && caja.width >= 28 && caja.y >= 0,
      `responsive ${t.id} · boton mapa`,
      caja ? `${Math.round(caja.width)}x${Math.round(caja.height)}px utilizables`
           : 'no visible');

    const campo = await pag.locator('form[data-form-coords] input[name="x"]').boundingBox();
    anotar(!!campo && campo.width >= 60 && campo.height >= 36,
      `responsive ${t.id} · campo X`,
      campo ? `${Math.round(campo.width)}x${Math.round(campo.height)}px` : 'no visible');

    // El mapa debe caber sin salirse del ancho disponible.
    const mapa = await pag.locator('svg.mapa').boundingBox();
    anotar(!!mapa && mapa.width <= m.clientW + 1,
      `responsive ${t.id} · mapa`,
      mapa ? `${Math.round(mapa.width)}px <= ${m.clientW}px` : 'no visible');

    await pag.screenshot({ path: captura(`responsive_geo_${t.id}`), fullPage: true });
    resumenResponsive.push({ id: t.id, desborde, w: t.w });
  } catch (e) {
    anotar(false, `responsive ${t.id}`, `error: ${e.message}`);
  }
  await ctx.close();
}
// ==================================================================== 7 ===
// La UI no debe leer XML ni JSONL: solo habla con la API.
console.log('\n--- 7. Red y datos ---');
await bloque('paso 7 · red', async () => {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  vigilar(ctx);
  const pag = await nuevaPagina(ctx);
  await pag.goto(`${BASE}/app/geography?x=112&y=20`, { waitUntil: 'networkidle' });
  await pag.waitForSelector('svg.mapa', { timeout: 20000 });

  anotar(destinos.size === 1 && destinos.has(new globalThis.URL(API).origin),
    'red', `origenes externos: ${[...destinos].join(', ') || 'ninguno'}`);

  const html = (await pag.content()) ?? '';
  anotar(!/\.xml/i.test(html), 'sin XML', 'la pagina no referencia ningun XML');
  anotar(!/\.jsonl/i.test(html), 'sin JSONL', 'la pagina no referencia ningun JSONL');
  await ctx.close();
});

await navegador.close();

// ================================================================= RESUMEN ==
const fallos = hallazgos.filter((h) => !h.ok);
const resumen = {
  generado: new Date().toISOString(),
  total: hallazgos.length,
  ok: hallazgos.length - fallos.length,
  fallos: fallos.length,
  responsive: resumenResponsive,
  hallazgos,
};
writeFileSync(join(SALIDA, `resumen_${SELLO}.json`), JSON.stringify(resumen, null, 2));

console.log(`\n${'='.repeat(58)}`);
console.log(`  ${resumen.ok}/${resumen.total} comprobaciones OK`);
console.log(`  fallos: ${resumen.fallos}`);
if (fallos.length) {
  console.log('\n  DETALLE DE FALLOS:');
  for (const f of fallos) console.log(`   - [${f.donde}] ${f.detalle}`);
}
console.log(`  capturas: ${SALIDA}`);
console.log('='.repeat(58));
process.exit(fallos.length ? 1 : 0);