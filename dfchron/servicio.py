#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Servicio
========================

Capa intermedia entre la API y el nucleo. Es la UNICA que conoce la forma de
las respuestas, de modo que la UI local y una futura UI web reciben exactamente
los mismos objetos.

FORMATO DE RESPUESTA
--------------------
Listados (siempre):

    {
      "data": [...],
      "total_encontrados": 100,
      "devueltos": 20,
      "truncado": true,
      "limit": 20,
      "offset": 0,
      "certainty": "FACT"
    }

Ficha individual:

    {
      "data": {...},
      "status": "FACT",
      "certainty": "FACT"
    }

Error (nunca lanza excepcion hacia el cliente):

    {
      "error": {"codigo": "NO_ENCONTRADO", "mensaje": "..."},
      "status": "UNKNOWN"
    }

POR QUE EXISTE
--------------
Para que el nucleo (`nucleo.py`) siga siendo AGNOSTICO de la forma de la
respuesta. Si la API construyera envelopes por su cuenta, la UI tendria dos
formatos distintos y no se podria reutilizar la capa para una web.
"""
import os
import json
import hashlib
import threading

# `config` debe importarse ANTES que `nucleo`: es el que anade
# 00_SOURCE/tools/ al sys.path para que el nucleo sea localizable.
try:
    from . import config                      # como paquete dfchron
except ImportError:                           # como script suelto
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import config

from nucleo import Archivo

limite_seguro = config.limite_seguro
offset_seguro = config.offset_seguro

UNKNOWN = "UNKNOWN"
FACT = "FACT"
DERIVED = "DERIVED"

# Un unico Archivo por proceso: cargar 57.215 eventos cuesta ~2,5 s.
_ARCHIVO = None
_CANDADO = threading.Lock()


def obtener_archivo():
    """Archivo compartido, creado de forma segura con varios hilos."""
    global _ARCHIVO
    if _ARCHIVO is None:
        with _CANDADO:
            if _ARCHIVO is None:
                _ARCHIVO = Archivo()
    return _ARCHIVO


def envolver_lista(items, total, limite, offset=0, certainty=FACT, **extra):
    """Envelope normalizado de listados. Nunca oculta que hay mas.

    `meta` es ADITIVO: se anade al contrato ya existente sin quitar ni renombrar
    ningun campo. Asi los clientes antiguos (`total_encontrados`, `devueltos`,
    `truncado`) siguen funcionando y los nuevos pueden leer `meta`.
    """
    items = list(items)
    truncado = (offset + len(items)) < total
    return {
        "ok": True,
        "data": items,
        "total_encontrados": total,
        "devueltos": len(items),
        "truncado": truncado,
        "limit": limite,
        "offset": offset,
        "certainty": certainty,
        "meta": {"total": total, "returned": len(items),
                 "truncated": truncado, "limit": limite, "offset": offset,
                 "certainty": certainty},
        **extra,
    }


def envolver_ficha(datos, **extra):
    """Envelope normalizado de una ficha individual."""
    cert = datos.get("certainty", UNKNOWN) if isinstance(datos, dict) else UNKNOWN
    return {"ok": True, "data": datos, "status": cert, "certainty": cert,
            "meta": {"total": 1, "returned": 1, "truncated": False,
                     "certainty": cert},
            **extra}


def envolver_estado(datos, status="OK", certainty=DERIVED, **extra):
    """Envelope de un dato unico que NO es ficha (salud, stats, geografia...).

    Se separa de `envolver_ficha` porque aqui `data` son CONTEOS o RESUMENES,
    no una ficha de figura/entidad/sitio. Envolverlos como ficha daria a
    entender que existe un registro con esos atributos.
    """
    return {"ok": True, "data": datos, "status": status,
            "certainty": certainty,
            "meta": {"total": 1, "returned": 1, "truncated": False,
                     "certainty": certainty},
            **extra}


def error(codigo, mensaje, http=400):
    """Error estructurado. El cliente nunca ve una excepcion de Python.

    `code`/`message` son los nombres en ingles del contrato generico; `codigo` y
    `mensaje` se conservan por compatibilidad. Un cliente nuevo puede leer
    `ok` + `error.code` sin conocer el idioma del proyecto.
    """
    return {"ok": False,
            "error": {"codigo": codigo, "code": codigo,
                      "mensaje": mensaje, "message": mensaje},
            "status": UNKNOWN, "certainty": UNKNOWN, "http_status": http}


# =============================================================================
# ESTADISTICAS Y LIMITACIONES
# =============================================================================
def stats():
    """Cifras reales del mundo. La UI las muestra; no las inventa."""
    return envolver_estado(obtener_archivo().estadisticas(),
                           status="OK", certainty=DERIVED)


def _sin(reg, campo):
    """Valor de un campo tratando el centinela -1 como ausente."""
    from validar_semantica import v, sin_dato
    return sin_dato(v(reg, campo))


def limitaciones():
    """Limitaciones REALES del dataset, con su cifra medida.

    No es texto de relleno: son los conteos que el validador calculo. La
    interfaz los muestra para que el usuario no los descubra tarde.
    """
    a = obtener_archivo()
    idx = a.indice
    est = a.estadisticas()
    ev_sin_part = sum(1 for e in idx.eventos.values()
                      if _sin(e, "hfid") is None and _sin(e, "civ_id") is None)
    return envolver_estado({
        "rango_temporal": [est["anio_min"], est["anio_max"]],
        "era": UNKNOWN,
        "era_motivo": ("La unica era del XML declara start_year = -1, el "
                       "centinela de Dwarf Fortress para 'sin dato'. La era "
                       "historica NO se puede determinar con estos datos."),
        "eventos_sin_participantes": ev_sin_part,
        "eventos_totales": len(idx.eventos),
        "figuras_sin_eventos": sum(1 for k in idx.figuras
                                   if not idx.ev_por_hf.get(k)),
        "figuras_sin_muerte_registrada": sum(
            1 for f in idx.figuras.values() if _sin(f, "death_year") is None),
        "figuras_totales": len(idx.figuras),
        "relaciones_sin_evento": len(idx.relaciones),
        "relaciones_motivo": ("Los 13.192 registros de "
                              "historical_event_relationships citan eventos que "
                              "NO existen en historical_events. Se conservan "
                              "como relaciones, sin evento asociado."),
        "grafo_dirigido": True,
        "grafo_motivo": ("Que A tenga relacion con B no implica la inversa. El "
                         "grafo es asimetrico y se consulta en esa direccion."),
        "sin_tabla_de_guerras": True,
        "guerras_motivo": ("El XML no contiene una tabla de guerras. La "
                           "agrupacion de conflictos es DERIVED, no una "
                           "entidad extraida del XML."),
        "conflictos_entre_fuentes_sin_resolver": 1925,
        "conflictos_motivo": ("legends.xml y legends_plus.xml discrepan en 1.925 "
                              "campos. Se conservan ambos valores, sin elegir."),
        "rios_sin_id_df": len(a._rivers),
        "rio_motivo": ("Los rios del XML no tienen id propio: su "
                       "identificador es DERIVED (hash del contenido)."),
        "certainty": FACT,
    }, status=FACT, certainty=FACT)


# =============================================================================
# BUSQUEDA
# =============================================================================
_TIPOS_BUSQUEDA = {
    "figuras": "buscar_figura", "historical_figures": "buscar_figura",
    "entidades": "buscar_entidad", "entities": "buscar_entidad",
    "sitios": "buscar_sitio", "sites": "buscar_sitio",
    "artefactos": "buscar_artefacto", "artifacts": "buscar_artefacto",
    "eventos": "buscar_evento", "historical_events": "buscar_evento",
}

# El enunciado de la web usa SINGULARES en el alias (`/api/buscar/figura`).
# Se aceptan apuntando al MISMO metodo: el alias cambia la URL, nunca el
# criterio de busqueda.
_ALIAS_SINGULAR = {
    "figura": "figuras", "entidad": "entidades", "sitio": "sitios",
    "artefacto": "artefactos", "evento": "eventos",
}


def buscar(texto, tipo=None, limite=None):
    """Busqueda global o por tipo. La ambiguedad se declara, no se resuelve."""
    a = obtener_archivo()
    lim = limite_seguro(limite)
    if not (texto or "").strip():
        return error("CONSULTA_VACIA", "el texto de busqueda esta vacio")
    if tipo:
        # Un singular se resuelve a su plural y sigue el MISMO camino.
        tipo = _ALIAS_SINGULAR.get(tipo, tipo)
        metodo = _TIPOS_BUSQUEDA.get(tipo)
        if metodo is None:
            return error("TIPO_DESCONOCIDO",
                         f"tipo de busqueda no soportado: {tipo!r}")
        r = getattr(a, metodo)(texto, limite=lim)
        items = r.get("fichas") or r.get("ids") or []
        return envolver_lista(items, r.get("total_encontrados", 0), lim,
                              certainty=r.get("certainty", FACT),
                              consulta=texto, tipo=tipo,
                              ids=r.get("ids", []),
                              consulta_ambigua=r.get("consulta_ambigua", False))
    r = a.buscar(texto, limite=lim)
    grupos = []
    total = 0
    for tp, ids in r.get("resultados", {}).items():
        t = r.get("total_encontrados", {}).get(tp, len(ids))
        total += t
        grupos.append({"tipo": tp, "ids": ids, "total_encontrados": t,
                       "devueltos": len(ids), "truncado": t > len(ids)})
    return envolver_lista(grupos, total, lim, certainty=FACT, consulta=texto,
                          consulta_ambigua=r.get("consulta_ambigua", False),
                          por_tipo=True)


# =============================================================================
# LISTADOS, EVENTOS Y GEOGRAFIA
# =============================================================================
def listar(tipo_registro, limite=None, offset=None):
    a = obtener_archivo()
    r = a.listar_registros(tipo_registro, limite=limite_seguro(limite),
                           offset=offset_seguro(offset))
    if r.get("certainty") == UNKNOWN:
        return error("TIPO_DESCONOCIDO", r.get("motivo", "tipo desconocido"))
    return envolver_lista(r["items"], r["total_encontrados"], r["limite"],
                          r["offset"], certainty=r["certainty"],
                          tipo_registro=tipo_registro)


def eventos(params):
    """Explorador de eventos: año, rango, tipo, figura, sitio o entidad."""
    a = obtener_archivo()
    r = a.eventos_filtrados(
        anio=params.get("anio"), desde=params.get("desde"),
        hasta=params.get("hasta"), tipo=params.get("tipo"),
        figura=params.get("figura"), sitio=params.get("sitio"),
        entidad=params.get("entidad"),
        limite=limite_seguro(params.get("limit")),
        offset=offset_seguro(params.get("offset")))
    if r.get("certainty") == UNKNOWN:
        return error("ANIO_INVALIDO", r.get("motivo", "año no válido"))
    return envolver_lista(r["eventos"], r["total_encontrados"], r["limite"],
                          r["offset"], certainty=FACT,
                          filtros=r.get("filtros"), nota=r.get("nota"))


def tipos_evento():
    a = obtener_archivo()
    r = a.tipos_evento()
    items = [{"tipo": k, "eventos": n} for k, n in r["tipos"].items()]
    return envolver_lista(items, r["total_tipos"], r["total_tipos"],
                          certainty=FACT, nota=r["nota"])


def geografia(capa=None, limite=None, offset=None):
    """Geografia: resumen de capas, listado de una capa, o punto exacto."""
    a = obtener_archivo()
    if capa is None:
        return envolver_estado(a.geografia(), status=FACT, certainty=FACT)
    r = a.listar_geografia(capa, limite=limite_seguro(limite, defecto=100),
                           offset=offset_seguro(offset))
    if r.get("certainty") == UNKNOWN:
        return error("CAPA_DESCONOCIDA", r.get("motivo", "capa desconocida"))
    return envolver_lista(r["items"], r["total_encontrados"], r["limite"],
                          r["offset"], certainty=FACT, capa=capa,
                          nota_derivada=r.get("nota_derivada"))


def construir_en_coordenada(x, y):
    a = obtener_archivo()
    try:
        xi, yi = int(x), int(y)
    except (TypeError, ValueError):
        return error("COORDENADA_INVALIDA",
                     "x e y deben ser numeros enteros")
    r = a.construir_en_coordenada(xi, yi)
    return envolver_lista(r["construcciones"], r["total"],
                          len(r["construcciones"]), certainty=DERIVED,
                          coordenada=[xi, yi],
                          metodo="coordenada exacta compartida")


# --- geografía por coordenada -------------------------------------------------
# Rango de coordenadas admitido. Los datos de este mundo usan 0..127, pero el
# formato de Dwarf Fortress reserva 16 bits por eje; se acepta ese rango y se
# rechaza el resto. NO es una suposición sobre el mapa: es el límite del tipo de
# dato, para que un valor absurdo no llegue al indice.
COORD_MIN, COORD_MAX = 0, 65535
AREA_MAX = 256          # lado máximo de un viewport, para acotar el trabajo


def _coordenada(x, y):
    """Valida (x, y). Devuelve (par, None) o (None, respuesta de error).

    Nunca lanza: un valor no numérico, un vacío o un entero gigante producen un
    400 explicativo, no un 500 ni una excepcion.
    """
    def uno(v, nombre):
        s = str(v).strip()
        if not s:
            return None, f"{nombre} falta"
        try:
            n = int(s)
        except (TypeError, ValueError):
            return None, f"{nombre} debe ser un numero entero (recibido: {s[:20]!r})"
        if not (COORD_MIN <= n <= COORD_MAX):
            return None, (f"{nombre} esta fuera del rango admitido "
                          f"({COORD_MIN}..{COORD_MAX}): {s[:20]}")
        return n, None

    xi, e = uno(x, "x")
    if e:
        return None, error("COORDENADA_INVALIDA", e, http=400)
    yi, e = uno(y, "y")
    if e:
        return None, error("COORDENADA_INVALIDA", e, http=400)
    return (xi, yi), None


def geografia_coordenada(x, y):
    """Todo lo que el XML sitúa exactamente en (x, y)."""
    par, fallo = _coordenada(x, y)
    if fallo:
        return fallo
    a = obtener_archivo()
    r = a.geografia_en_coordenada(*par)
    return envolver_estado(r, status=FACT, certainty=FACT)


def geografia_area(x, y, ancho=None, alto=None, incluir_capas=None):
    """Sitios dentro de un rectángulo: el viewport que necesita el mapa."""
    par, fallo = _coordenada(x, y)
    if fallo:
        return fallo
    def tam(v, defecto, nombre):
        if v is None or str(v).strip() == "":
            return defecto, None
        s = str(v).strip()
        try:
            n = int(s)
        except (TypeError, ValueError):
            return None, f"{nombre} debe ser un numero entero"
        if n < 1:
            return None, f"{nombre} debe ser al menos 1"
        if n > AREA_MAX:
            return None, f"{nombre} no puede superar {AREA_MAX}"
        return n, None
    an, e = tam(ancho, 32, "ancho")
    if e:
        return error("AREA_INVALIDA", e, http=400)
    al, e = tam(alto, 32, "alto")
    if e:
        return error("AREA_INVALIDA", e, http=400)

    capas = str(incluir_capas or "").lower() in ("1", "true", "si", "yes")
    a = obtener_archivo()
    r = a.geografia_en_area(*par, ancho=an, alto=al, incluir_capas=capas)
    if r.get("certainty") == UNKNOWN:
        return error("AREA_INVALIDA", r.get("motivo", "area invalida"), http=400)
    return envolver_estado(r, status=FACT, certainty=FACT)




# =============================================================================
# FICHAS INDIVIDUALES Y SUS COLECCIONES
# =============================================================================
def _no_existe(que, df_id):
    return error("NO_ENCONTRADO",
                 f"no existe {que} con df_id {df_id!r}", http=404)


def _con_total(items, total, limite, **extra):
    return envolver_lista(items, total, limite, certainty=FACT, **extra)


def figura(df_id):
    a = obtener_archivo()
    d = a.ficha_figura(str(df_id))
    if d.get("certainty") == UNKNOWN:
        return _no_existe("la figura", df_id)
    return envolver_ficha(d)


def figura_eventos(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.figuras:
        return _no_existe("la figura", df_id)
    lim = limite_seguro(limite, defecto=200)
    r = a.eventos_de_figura(str(df_id), limite=lim, con_total=True)
    return _con_total(r["items"], r["total"], lim)


def figura_cronologia(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.figuras:
        return _no_existe("la figura", df_id)
    return envolver_ficha(a.cronologia_figura(
        str(df_id), limite=limite_seguro(limite, defecto=200)))


def figura_relaciones(df_id, tipo=None, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.figuras:
        return _no_existe("la figura", df_id)
    r = a.relaciones_de_figura(str(df_id), tipo=tipo,
                               limite=limite_seguro(limite, defecto=200))
    env = _con_total(r["relaciones"], r["total"], r["devueltos"])
    env["nota_grafo"] = r["nota_grafo"]
    env["figura_id"] = r["figura_id"]
    env["nombre"] = r["nombre"]
    return env




def entidad(df_id):
    a = obtener_archivo()
    d = a.ficha_entidad(str(df_id))
    if d.get("certainty") == UNKNOWN:
        return _no_existe("la entidad", df_id)
    return envolver_ficha(d)


def entidad_miembros(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.entidades:
        return _no_existe("la entidad", df_id)
    r = a.miembros_entidad(str(df_id))
    lim = limite_seguro(limite, defecto=500)
    env = _con_total(r["miembros"][:lim], r["total"], lim)
    env["entidad_id"] = r["entidad_id"]
    env["nombre"] = r["nombre"]
    env["enlace"] = r["enlace"]
    return env


def entidad_sitios(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.entidades:
        return _no_existe("la entidad", df_id)
    r = a.sitios_de_entidad(str(df_id))
    lim = limite_seguro(limite, defecto=500)
    env = _con_total(r["sitios"][:lim], r["total"], lim)
    env["entidad_id"] = r["entidad_id"]
    env["nombre"] = a.nombre_de("entities", df_id)
    env["enlace"] = r["enlace"]
    return env


def entidad_cronologia(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.entidades:
        return _no_existe("la entidad", df_id)
    return envolver_ficha(a.cronologia_entidad(
        str(df_id), limite=limite_seguro(limite, defecto=200)))


def entidad_eventos(df_id, limite=None, offset=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.entidades:
        return _no_existe("la entidad", df_id)
    r = a.eventos_filtrados(entidad=str(df_id),
                            limite=limite_seguro(limite, defecto=200),
                            offset=offset_seguro(offset))
    return envolver_lista(r["eventos"], r["total_encontrados"], r["limite"],
                          r["offset"], certainty=FACT)


def sitio(df_id):
    """Ficha de sitio. `tipo` conserva el tipo REAL de Dwarf Fortress."""
    a = obtener_archivo()
    d = a.ficha_sitio(str(df_id))
    if d.get("certainty") == UNKNOWN:
        return _no_existe("el sitio", df_id)
    return envolver_ficha(d)


def sitio_eventos(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.sitios:
        return _no_existe("el sitio", df_id)
    lim = limite_seguro(limite, defecto=200)
    r = a.eventos_de_sitio(str(df_id), limite=lim, con_total=True)
    return _con_total(r["items"], r["total"], lim)




def artefacto(df_id):
    a = obtener_archivo()
    d = a.ficha_artefacto(str(df_id))
    if d.get("certainty") == UNKNOWN:
        return _no_existe("el artefacto", df_id)
    return envolver_ficha(d)


def artefacto_propietarios(df_id):
    a = obtener_archivo()
    if str(df_id) not in a.indice.artefactos:
        return _no_existe("el artefacto", df_id)
    return envolver_ficha(a.propietarios_artefacto(str(df_id)))


def artefacto_eventos(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.artefactos:
        return _no_existe("el artefacto", df_id)
    lim = limite_seguro(limite, defecto=200)
    r = a.eventos_de_artefacto(str(df_id), limite=lim, con_total=True)
    return _con_total(r["items"], r["total"], lim)


def evento(df_id):
    a = obtener_archivo()
    d = a.ficha_evento(str(df_id))
    if d.get("certainty") == UNKNOWN:
        return _no_existe("el evento", df_id)
    return envolver_ficha(d)


def evento_participantes(df_id):
    a = obtener_archivo()
    if str(df_id) not in a.indice.eventos:
        return _no_existe("el evento", df_id)
    return envolver_ficha(a.participantes_evento(str(df_id)))


def eventos_del_anio(anio):
    a = obtener_archivo()
    r = a.eventos_del_anio(anio)
    if r.get("certainty") == UNKNOWN:
        return error("ANIO_INVALIDO", r.get("motivo", "año no válido"))
    return envolver_lista(r["eventos"], r["total"], r["total"],
                          certainty=FACT, anio=r["anio"], nota=r.get("nota"))


# =============================================================================
# EXPORTACION
# =============================================================================
def exportar(formato, figura_id=None, entidad_id=None, sitio_id=None,
             nombre=None, escribir=False):
    """Exporta a JSON o Markdown.

    NUNCA sobrescribe los originales: el fichero solo se escribe si el cliente
    lo pide Y dentro de EXPORT_ROOT, que no puede ser processed/ ni
    original_data/. Por defecto devuelve el texto sin tocar el disco.
    """
    a = obtener_archivo()
    formato = (formato or "json").lower()
    if formato not in ("json", "markdown", "md"):
        return error("FORMATO_NO_SOPORTADO",
                     f"formato no soportado: {formato!r} (use json o markdown)")

    if figura_id is not None:
        if str(figura_id) not in a.indice.figuras:
            return _no_existe("la figura", figura_id)
        datos = a.ficha_figura(str(figura_id), breve=False)
        titulo = f"Historia de {datos.get('nombre', figura_id)} (df_id {figura_id})"
    elif entidad_id is not None:
        if str(entidad_id) not in a.indice.entidades:
            return _no_existe("la entidad", entidad_id)
        datos = a.ficha_entidad(str(entidad_id), breve=False)
        titulo = f"Entidad {datos.get('nombre', entidad_id)} (df_id {entidad_id})"
    elif sitio_id is not None:
        if str(sitio_id) not in a.indice.sitios:
            return _no_existe("el sitio", sitio_id)
        datos = a.ficha_sitio(str(sitio_id), breve=False)
        titulo = f"Sitio {datos.get('nombre', sitio_id)} (df_id {sitio_id})"
    else:
        return error("FALTA_OBJETIVO",
                     "indique figura, entidad o sitio para exportar")

    if formato == "json":
        texto = a.exportar_json(datos, titulo)
    else:
        texto = a.exportar_markdown(datos, titulo)

    env = {"data": {"titulo": titulo, "formato": formato,
                    "caracteres": len(texto), "contenido": texto},
           "status": FACT, "certainty": FACT,
           "escrito_en": None,
           "nota": ("El export NUNCA sobrescribe los XML originales ni el "
                    "dataset: solo puede escribir en EXPORT_ROOT.")}
    if not escribir:
        return env

    import rutas
    # Un nombre con separadores o '..' es un INTENTO de traversal. No se
    # reescribe en silencio: se rechaza, para que el cliente sepa que su
    # peticion fue rechazada y no se fina un fichero con otro nombre.
    if nombre and (os.sep in nombre or "/" in nombre or "\\" in nombre
                   or nombre.strip() in (".", "..")):
        return error("NOMBRE_EXPORTACION_INVALIDO",
                     "el nombre del fichero no puede contener rutas")
    try:
        destino = rutas.ruta_de_exportacion(nombre or f"dfchron_{titulo[:40]}.{formato}")
        rutas.asegurar_export_root()
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto)
    except (ValueError, OSError, RuntimeError) as exc:
        return error("EXPORTACION_BLOQUEADA", str(exc))
    env["escrito_en"] = destino
    return env


def leer_dataset_id(raiz_datos=None):
    """Identificador estable del dataset activo, o None si no hay registro.

    El id NO se escribe a mano ni se saca de un reloj: se DERIVA de las huellas
    SHA-256 reales de `dataset_version.json`. Propiedades:

      * determinista  -> el mismo contenido da siempre el mismo id;
      * sensible      -> si cambia un byte, cambia el id;
      * sin invenciones-> sale de datos medidos, no de un contador.

    Se lee del DISCO en cada llamada (el fichero son unos pocos KB), no de la
    memoria de la API: asi refleja lo que esta activado ahora mismo, que es lo
    que la Web necesita para detectar un cambio.
    """
    ruta = os.path.join(raiz_datos or config.DATA_ROOT, "dataset_version.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(doc, dict) and doc.get("dataset_id"):
        return str(doc["dataset_id"])
    # Dataset valido sin `dataset_id` (p.ej. generado antes de este campo):
    # se calcula igual y no se descarta. El campo ausente NO es un fallo.
    salidas = doc.get("salidas") if isinstance(doc, dict) else None
    if isinstance(salidas, dict) and salidas:
        return calcular_dataset_id(salidas)
    return None


def calcular_dataset_id(salidas):
    """Deriva el id a partir de {fichero: sha256}. Determinista y explicable."""
    try:
        texto = json.dumps(salidas, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":"))
        return "v1-" + hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
    except (TypeError, ValueError):
        return None


def salud():
    """Estado del servicio. Util para diagnostico y para pruebas.

    Añade `dataset_id` y `dataset_generado`: qué mundo está sirviendo HOY. Se
    leen del disco (no de la memoria del proceso) precisamente para que la Web
    pueda detectar que se ha activado otro dataset.

    Lo que sigue igual NO se toca: `estado`, `eventos`, `figuras`,
    `ruta_datos`, `export_root` y `limite_maximo` mantienen su nombre y su
    valor, para no romper a ningun cliente existente.
    """
    d = obtener_archivo().estadisticas()
    doc = _leer_version()
    return envolver_estado({
        "estado": "ok", "eventos": d["eventos"],
        "figuras": d["figuras"],
        "ruta_datos": config.DATA_ROOT,
        "export_root": config.EXPORT_ROOT,
        "limite_maximo": config.LIMITE_MAXIMO,
        # --- nuevo: identidad del mundo servido ---
        "dataset": _resumen_dataset(doc),
    }, status="OK", certainty="DERIVED")


def _leer_version():
    """`dataset_version.json` completo, o None. Tolera un fichero corrupto."""
    ruta = os.path.join(config.DATA_ROOT, "dataset_version.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else None
    except (OSError, ValueError):
        return None


def _resumen_dataset(doc):
    """Lo que la Web necesita saber del mundo, y nada mas.

    Si no hay registro, se declara UNKNOWN con el motivo. Nunca se inventa una
    fecha ni un identificador: si el fichero no está, no se rellena.

    P1.2: añade `mundo`, la identidad del MUNDO (`world_name`, `world_folder`).
    Es una clave NUEVA: las de antes —`dataset_id`, `dataset_generado`,
    `conteos`, `certainty`, `motivo`— no cambian ni de nombre ni de valor.

    Por qué aquí y no en otro sitio: este bloque ya viaja por `/api/salud`, que
    es la ruta que la Web consulta para saber qué está sirviendo, y su docstring
    ya decía literalmente «lo que la Web necesita saber del mundo». La pregunta
    por el mundo ya tenía sitio; faltaba el dato.

    La LECTURA e INTERPRETACIÓN no se reimplementan aquí: se piden a
    `ia_conocimiento`, que ya lee este mismo fichero para `dataset_id` y ya
    decide qué es una ausencia. Dos interpretaciones de la misma clave
    divergirían sin que nadie lo notase.
    """
    if not doc:
        return {
            "dataset_id": None,
            "dataset_generado": None,
            "certainty": UNKNOWN,
            "motivo": "no hay registro de dataset: la API sirve "
                      "00_SOURCE/processed/merged directamente",
            "mundo": _mundo_desde_documento(None),
        }
    salidas = doc.get("salidas") or {}
    id_ = doc.get("dataset_id") or calcular_dataset_id(salidas)
    return {
        "dataset_id": id_ or None,
        "dataset_generado": doc.get("actualizada") or None,
        "conteos": doc.get("conteos") or None,
        "certainty": FACT if id_ else UNKNOWN,
        "motivo": None if id_ else "el registro no tiene salidas que identificar",
        "mundo": _mundo_desde_documento(doc),
    }


def _mundo_desde_documento(doc):
    """Delega en `ia_conocimiento`. Import perezoso para no crear un ciclo.

    `ia_conocimiento` importa `nucleo`, y `servicio` tambien. El import se hace
    dentro de la funcion, que es donde se necesita, en vez de arriba del todo.
    """
    try:
        from . import ia_conocimiento as ic
    except ImportError:                        # pragma: no cover - script suelto
        import ia_conocimiento as ic
    return ic.mundo_de(doc)

def sitio_cronologia(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.sitios:
        return _no_existe("el sitio", df_id)
    return envolver_ficha(a.cronologia_sitio(
        str(df_id), limite=limite_seguro(limite, defecto=200)))


def sitio_figuras(df_id, limite=None):
    a = obtener_archivo()
    if str(df_id) not in a.indice.sitios:
        return _no_existe("el sitio", df_id)
    ids = a.indice.hf_por_sitio.get(str(df_id), [])
    lim = limite_seguro(limite, defecto=500)
    return _con_total([a.ficha_figura(h, breve=True) for h in ids[:lim]],
                      len(ids), lim)

def figura_artefactos(df_id):
    a = obtener_archivo()
    if str(df_id) not in a.indice.figuras:
        return _no_existe("la figura", df_id)
    items = a.artefactos_de_figura(str(df_id))
    return _con_total(items, len(items), len(items))


def figura_identidad(df_id):
    a = obtener_archivo()
    if str(df_id) not in a.indice.figuras:
        return _no_existe("la figura", df_id)
    return envolver_ficha(a.identidad_de_figura(str(df_id)))

def conflictos(limite=None):
    """Agrupacion DERIVED de eventos de enfrentamiento. NO son 'guerras'."""
    a = obtener_archivo()
    r = a.conflictos(limite_eventos=limite_seguro(limite, defecto=200))
    return envolver_lista(r["eventos"], r["total_real"],
                          r["eventos_devueltos"], certainty=DERIVED,
                          regla=r["regla"], advertencia=r["advertencia"],
                          trazabilidad=r["trazabilidad"],
                          por_subtipo=r["por_subtipo"],
                          por_subtipo_total=r["por_subtipo_total"])


def tipos_relacion():
    a = obtener_archivo()
    r = a.tipos_relacion_disponibles()
    items = [{"tipo": k, "relaciones": n} for k, n in r["tipos"].items()]
    return envolver_lista(items, len(items), len(items), certainty=FACT,
                          nota=r["nota"])
