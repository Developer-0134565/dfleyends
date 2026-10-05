/**
 * DF Legends :: datos geográficos
 * ===============================
 *
 * CAPA DE DATOS, SEPARADA DEL RENDERIZADOR.
 *
 * Este modulo es el ÚNICO que sabe qué endpoint devuelve qué. Si mañana la API
 * se mueve o cambia de forma, solo se toca aquí: `mapa.ts` (el que dibuja) y
 * las vistas no se enteran.
 *
 * No calcula geografía. Solo traduce la respuesta de la API a las estructuras
 * que el renderer y las vistas necesitan. Si un dato no viene, se propaga
 * como `UNKNOWN`; nunca se suple ni se estima.
 */
import { consultar } from './api';
import type { SitioMapa, AreaMapa } from './mapa';

export interface CoordXYZ {
  x: number;
  y: number;
  z: number | null;
}

export interface SitioGeo {
  df_id: string;
  nombre: string;
  tipo: string;
  coordenadas: number[][];
  certainty: string;
}

export interface CapaGeo {
  df_id: string | null;
  nombre: string;
  tipo?: string;
  coordenadas: number[][];
  certainty: string;
}

export interface PuntoGeo {
  coordenada: CoordXYZ;
  coordenadas: Record<string, string>;
  sitios: SitioGeo[];
  total_sitios: number;
  capas: Record<string, CapaGeo[]>;
  total_registros_capas: number;
  certainty: string;
  certainty_enlace: string;
  motivo: string | null;
}

export interface VistaMapa {
  area: AreaMapa;
  sitios: SitioMapa[];
  tipos: string[];
  certainty: string;
}

/** Traduce la respuesta de la API al modelo del renderer. */
function aSitiosMapa(bruto: unknown): SitioMapa[] {
  if (!Array.isArray(bruto)) return [];
  const out: SitioMapa[] = [];
  for (const s of bruto as SitioGeo[]) {
    const par = Array.isArray(s.coordenadas) ? s.coordenadas[0] : null;
    // Sin coordenada no hay punto que dibujar. No se inventa una posición.
    if (!Array.isArray(par) || par.length < 2) continue;
    const x = Number(par[0]);
    const y = Number(par[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    out.push({
      df_id: String(s.df_id),
      nombre: String(s.nombre ?? 'Unknown'),
      tipo: String(s.tipo ?? 'UNKNOWN'),
      x,
      y,
    });
  }
  return out;
}

/** Geometría de un punto exacto. */
export async function datosPunto(
  x: number,
  y: number,
): Promise<PuntoGeo | null> {
  const env = await consultar<any>(['api', 'geografia', 'punto', String(x), String(y)]);
  if (!env.ok) return null;
  return env.data as PuntoGeo;
}

/** Geometría de un área: lo que el mapa necesita para pintarse. */
export async function datosArea(
  x: number,
  y: number,
  ancho: number,
  alto: number,
): Promise<VistaMapa | null> {
  const env = await consultar<any>(['api', 'geografia', 'area', String(x), String(y)], {
    ancho,
    alto,
  });
  if (!env.ok) return null;
  const d = env.data;
  const sitios = aSitiosMapa(d.sitios);
  // Los tipos se listan en el orden en que aparecen, sin repetir.
  const tipos: string[] = [];
  for (const s of sitios) if (!tipos.includes(s.tipo)) tipos.push(s.tipo);
  return {
    area: d.area as AreaMapa,
    sitios,
    tipos,
    certainty: String(d.certainty ?? 'UNKNOWN'),
  };
}

/** Sitios cuya coordenada coincide exactamente con (x, y). */
export async function sitiosEnCoordenada(x: number, y: number): Promise<SitioGeo[]> {
  const env = await consultar<SitioGeo[]>(['api', 'sitios'], { x, y });
  if (!env.ok || !Array.isArray(env.data)) return [];
  return env.data;
}

/** Resumen de las 4 capas, para los contadores de la vista. */
export async function resumenCapas(): Promise<Record<string, { registros: number }>> {
  const env = await consultar<any>(['api', 'geografia']);
  return env.ok && env.data ? (env.data as any) : {};
}