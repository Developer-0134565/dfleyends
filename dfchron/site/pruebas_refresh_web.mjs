/**
 * DF Legends :: ciclo de refresco en NAVEGADOR REAL.
 * ====================================================
 *
 * Comprueba, con Chrome real, lo que la Web dice del dataset:
 *   1. El dashboard muestra el identificador y la fecha REALES;
 *   2. Si el dataset cambia mientras la pestaña esta abierta, avisa;
 *   3. El aviso NO recarga solo: la navegacion se conserva;
 *   4. Al recargar a mano, el mundo nuevo es el que se ve;
 *   5. Nunca se filtra una ruta interna ni un traceback.
 *
 * Para el punto 2 se cambia el `dataset_version.json` REAL con un
 * `dataset_id` distinto y luego se vuelve a poner. Se restaura SIEMPRE,
 * incluso si la prueba falla: no se puede dejar el dataset corrupto.
 *
 * Uso:  node pruebas_refresh_web.mjs [--url=http://127.0.0.1:4400]
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const RAIZ = 'C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles';
const REGISTRO = join(RAIZ, '00_SOURCE', 'dataset_version.json');
const ARG = process.argv.find((a) => a.startsWith('--url='));
const BASE = ARG ? ARG.slice(6) : 'http://127.0.0.1:4400';

const hallazgos = [];
function anotar(ok, donde, detalle) {
  hallazgos.push({ ok, donde, detalle });
  console.log(`${ok ? '  OK  ' : ' FALLO'}  ${donde}  - ${detalle}`);
}

/** Se ejecuta siempre, salga como salga la prueba: el registro nunca se pierde. */
function restaurarRegistro(original) {
  try {
    writeFileSync(REGISTRO, original, 'utf-8');
    console.log('\n[refresh] dataset_version.json restaurado a su estado original');
  } catch (e) {
    console.error('[refresh] NO SE PUDO RESTAURAR el registro:', e.message);
  }
}

const ORIGINAL = readFileSync(REGISTRO, 'utf-8');

const navegador = await chromium.launch({ channel: 'chrome' });
const contexto = await navegador.newContext({ viewport: { width: 1280, height: 900 } });
const pagina = await contexto.newPage();

/** Peticiones que la web hace de más: debe ser solo a la API. */
const peticiones = [];
pagina.on('request', (r) => peticiones.push(r.url()));

try {
  // ---------------------------------------------------- 1. el panel existe --
  await pagina.goto(`${BASE}/app/world`, { waitUntil: 'networkidle' });
  const panel = pagina.locator('.panel--dataset');
  await panel.waitFor({ state: 'visible', timeout: 15000 });
  anotar(true, 'dashboard', 'el panel "World dataset" se muestra');

  const idMostrado = (await panel.locator('code').first().textContent())?.trim() ?? '';
  const regex = /^v1-[0-9a-f]{16}$/;
  anotar(regex.test(idMostrado), 'dataset_id',
    `formato del id mostrado: ${idMostrado || '(vacio)'}`);

  const generado = (await panel.textContent()) ?? '';
  // La fecha debe ser la REAL del registro, no una inventada.
  const original = JSON.parse(ORIGINAL);
  anotar(generado.includes(String(original.actualizada).slice(0, 10)),
    'generated', 'la fecha viene del dataset_version.json real');

  // Nada de rutas internas en la pagina.
  const texto = (await pagina.textContent('body')) ?? '';
  anotar(!/C:\\Users|Traceback|MISSIN~1/.test(texto),
    'sin fugas', 'la pagina no expone rutas internas ni tracebacks');

  // ------------------------------- 2. cambia el dataset con la pagina abierta --
  const antes = idMostrado;
  const cambiado = { ...original, dataset_id: 'v1-0000000000000001' };
  writeFileSync(REGISTRO, JSON.stringify(cambiado, null, 1), 'utf-8');
  console.log(`\n[refresh] dataset cambiado en disco: ${antes} -> ${camel(cambiado)}`);

  // Se vuelve a la pestaña: es el momento en que se comprueba (§12).
  await pagina.evaluate(() => {
    Object.defineProperty(document, 'visibilityState',
      { value: 'visible', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  const aviso = pagina.locator('[data-aviso-dataset]');
  await aviso.waitFor({ state: 'visible', timeout: 15000 });
  anotar(true, 'aviso', 'la web avisa de que hay un mundo nuevo');

  const textoAviso = (await aviso.textContent()) ?? '';
  anotar(textoAviso.includes(antes) && textoAviso.includes('v1-0000000000000001'),
    'aviso', 'el aviso nombra el dataset anterior y el nuevo');

  // ------------------------------------------ 3. NO recarga sola la pagina --
  // Si la pagina se recargara sola, un valor puesto en `window` se perderia.
  // El nombre debe coincidir EXACTAMENTE con el que se lee despues: por eso
  // se usa una constante en vez de escribirlo dos veces a mano.
  const MARCA = '__refreshNoSeRecargo';
  await pagina.evaluate((k) => { window[k] = true; }, MARCA);
  await pagina.waitForTimeout(1200);
  const sigueVivo = await pagina.evaluate((k) => window[k] === true, MARCA);
  anotar(sigueVivo, 'sin recarga automatica',
    'la pagina NO se recarga sola al detectar el cambio');

  // El enlace de recarga existe y es un enlace de verdad.
  const enlace = aviso.locator('[data-recargar-pagina]');
  anotar(await enlace.count() === 1, 'aviso',
    'el aviso ofrece recargar, a peticion del usuario');

  // ------------------------------------- 4. recargar a mano muestra el nuevo --
  await pagina.reload({ waitUntil: 'networkidle' });
  const idFinal = (await pagina.locator('.panel--dataset code').first()
    .textContent())?.trim() ?? '';
  anotar(idFinal === 'v1-0000000000000001', 'recarga manual',
    `tras recargar, el dashboard muestra ${idFinal}`);
  anotar(await pagina.locator('[data-aviso-dataset]').count() === 0,
    'aviso', 'ya no hay aviso: el mundo nuevo es el que se ve');

  // 5. Solo se habla con la API.
  const ajenas = peticiones.filter((u) => !u.startsWith(BASE) &&
    !u.includes('127.0.0.1:877'));
  anotar(ajenas.length === 0, 'red',
    ajenas.length ? `peticiones inesperadas: ${ajenas.slice(0, 3)}`
                  : 'la web solo habla con la API configurada');
} catch (e) {
  anotar(false, 'ejecucion', e.message);
} finally {
  restaurarRegistro(ORIGINAL);
  await navegador.close();
}

const fallos = hallazgos.filter((h) => !h.ok);
console.log(`\n${hallazgos.length - fallos.length}/${hallazgos.length} comprobaciones`);
process.exit(fallos.length ? 1 : 0);

function camel(d) { return d.dataset_id; }