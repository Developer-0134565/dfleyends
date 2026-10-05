#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: adaptador HTTP del contrato de consulta determinista
=====================================================================

QUE ES ESTE FICHERO
-------------------
Un **adaptador**, y nada mas. Traduce HTTP a `servicio_consulta` y de vuelta.

Este modulo NO sabe que es una figura, ni si un id existe, ni que significa
una relacion, ni si un atributo esta verificado. Esa es exactamente la
razon por la que existe: para que esas decisiones queden en UN sitio, el
servicio, y no repartidas entre handlers HTTP.

        HTTP request
            v
        validacion de entrada      <- aqui (tipos, ids, limites)
            v
        este adaptador             <- aqui (codigos HTTP, query params)
            v
        servicio_consulta          <- aqui (que existe, que esta verificado)
            v
        nucleo

POR QUE NO SE TOCA `api.py`
---------------------------
`api.py` es la frontera HTTP existente, con sus consumidores y sus 54
pruebas. Este adaptador se registra como rutas NUEVAS (`/api/consulta/...`)
y ademas ENRIQUECE las fichas existentes sin cambiar su envelope. Asi la
compatibilidad no depende de que alguien lea bien este documento.

TRES REGLAS QUE NO SE ROMPEN
---------------------------
1. Este fichero no decide nada del dominio. Si aparece un `if` sobre el
   significado de un dato, esta en el sitio equivocado.
2. No fabrica. `dataset_id`, `evidence` e `identity` se COPIAN del
   resultado del servicio. Si el servicio dice `None`, aqui va `None`.
3. No confunde. `NOT_FOUND`, `NO_VERIFICADO` y `NO_DISPONIBLE` reciben
   codigos HTTP distintos. Ver `HTTP_POR_ESTADO`.
"""
import copy

try:
    from . import servicio_consulta as qc
except ImportError:              # pragma: no cover - ejecucion suelta
    import servicio_consulta as qc

try:
    from . import servicio as svc
except ImportError:              # pragma: no cover
    import servicio as svc

try:
    from . import config
except ImportError:              # pragma: no cover
    import config


# ================================================ ESTADO -> CODIGO HTTP =======
# El servicio ya distingue tres cosas que un 404-barato mezclaria:
#
#   NOT_FOUND        -> el dato NO existe. 404.
#   NOT_VERIFIED     -> el dato existe pero no se puede determinar. 200.
#   DATA_UNAVAILABLE -> no se puede saber por fallo tecnico. 503.
#
# `NOT_VERIFIED` NO es 404 a proposito. Si «no puedo demostrar que esta
# figura tiene ese atributo» devolviera 404, un cliente concluiria «la
# figura no existe», que es una afirmacion MAS fuerte y FALSA. Deixa claro
# que la distincion existe porque cada codigo significa algo distinto.
HTTP_POR_ESTADO = {
    qc.FOUND: 200,
    qc.NOT_FOUND: 404,
    # 200 con `ok: false`: la peticion se atendio, la respuesta es que no
    # consta. Es un 200 porque el servidor funciono y respondio con la
    # verdad que tenia.
    qc.NOT_VERIFIED: 200,
    qc.INVALID_QUERY: 400,
    qc.DATA_UNAVAILABLE: 503,
}

#: Codigos de error del SERVICIO que ya significan 404. Se respetan tal cual
#: para no reescribir un 404 que el nucleo ya habia decidido.
HTTP_POR_CODIGO = {
    "NO_ENCONTRADO": 404,
}


def _error(codigo, mensaje, http=400, **extra):
    """Error del adaptador. Mismo formato que `servicio.error`, mas `estado`."""
    env = svc.error(codigo, mensaje, http=http)
    env["estado"] = codigo
    for k, v in extra.items():
        env[k] = v
    return env


def _http_de(resultado):
    """El codigo HTTP que corresponde a un resultado del servicio.

    Se respeta el `http_status` que el nucleo ya puso (404 de un id
    inexistente) y, si no hay, se deriva del ESTADO. Nunca se decide aqui
    si el dato existe: eso ya esta dicho en `resultado["estado"]`.
    """
    if isinstance(resultado, dict):
        if isinstance(resultado.get("http_status"), int):
            return resultado["http_status"]
        estado = resultado.get("estado")
        if estado in HTTP_POR_ESTADO:
            return HTTP_POR_ESTADO[estado]
        codigo = (resultado.get("error") or {}).get("code")
        if codigo in HTTP_POR_CODIGO:
            return HTTP_POR_CODIGO[codigo]
    return 500


def _responder(resultado):
    """Anade `http_status` y devuelve. No muta el resultado del servicio."""
    out = copy.deepcopy(dict(resultado))
    out["http_status"] = _http_de(out)
    return out


# ==================================================== VALIDACION DE ENTRADA ===
# Todo lo que llega de HTTP es texto. Estas funciones son la FRONTERA donde
# un texto se convierte en algo que el servicio pueda usar, o en un 400.

def _uno(params, nombre):
    """Primer valor de un parametro. `parse_qs` entrega listas."""
    if not params:
        return None
    v = params.get(nombre)
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _texto(valor, nombre, maximo=256):
    """Un campo de texto no vacio, acotado. Devuelve `(valor, error)`."""
    if valor is None:
        return None, "falta %s" % nombre
    t = str(valor).strip()
    if not t:
        return None, "%s esta vacio" % nombre
    if len(t) > maximo:
        return None, "%s excede %d caracteres" % (nombre, maximo)
    return t, None


def _entero(valor, nombre, defecto=None, minimo=None, maximo=None):
    """Un entero de query. Devuelve `(valor, error)`. Nunca lanza."""
    if valor is None or valor == "":
        return defecto, None
    t = str(valor).strip()
    try:
        n = int(t)
    except (TypeError, ValueError):
        return None, "%s debe ser un entero, no %r" % (nombre, t[:32])
    if minimo is not None and n < minimo:
        return None, "%s debe ser >= %d" % (nombre, minimo)
    if maximo is not None and n > maximo:
        return None, "%s no puede superar %d" % (nombre, maximo)
    return n, None


def _tipo(tipo):
    """Un tipo de entidad. NO se corrige ni se amplia: o es uno del
    contrato, o no lo es. Aceptar alias aqui seria inventar vocabulario."""
    if tipo is None:
        return None, "falta el tipo"
    t = str(tipo).strip()
    if not t:
        return None, "el tipo esta vacio"
    return t, None


def _rechaza_desconocidos(params, permitidos):
    """Params que el endpoint no entiende -> 400.

    Ignorar un parametro mal escrito es peor que rechazarlo: el cliente
    cree que esta filtrando por algo y nadie lo filtra.

    `None` se trata como "no hay query params". Las rutas que no aceptan
    query params pueden omitir el segundo argumento.
    """
    if not params:
        return None
    sobrantes = sorted(set(params) - set(permitidos))
    if sobrantes:
        return _error("PARAMETRO_DESCONOCIDO",
                      "parametros no reconocidos: %s" % ", ".join(sobrantes),
                      http=400,
                      permitidos=sorted(permitidos))
# ====================================================== FICHAS ENRIQUECIDAS ===
# Estas rutas YA EXISTEN y tienen consumidores. No se les cambia el envelope:
# se les anade lo que el servicio ya sabe y antes no viajaba.
#
# El envelope anterior (`ok`, `data`, `status`, `certainty`, `meta`, y los
# heredados `total_encontrados`/`truncado`) se conserva INTACTO. Solo se
# anaden claves. Un cliente antiguo no se entera; uno nuevo lee mas.

def ficha_figura(df_id):
    """`GET /api/figuras/{id}` -> `obtener_entidad('figura', id)`."""
    return _responder(qc.obtener_entidad("figura", df_id))


def ficha_entidad(df_id):
    """`GET /api/entidades/{id}` -> `obtener_entidad('entidad', id)`."""
    return _responder(qc.obtener_entidad("entidad", df_id))


def ficha_sitio(df_id):
    """`GET /api/sitios/{id}` -> `obtener_entidad('sitio', id)`."""
    return _responder(qc.obtener_entidad("sitio", df_id))


def ficha_artefacto(df_id):
    """`GET /api/artefactos/{id}` -> `obtener_entidad('artefacto', id)`."""
    return _responder(qc.obtener_entidad("artefacto", df_id))


def ficha_evento(df_id):
    """`GET /api/eventos/{id}` -> `obtener_entidad('evento', id)`."""
    return _responder(qc.obtener_entidad("evento", df_id))


def relaciones_figura(df_id, params):
    """`GET /api/figuras/{id}/relaciones` -> `buscar_relaciones`.

    COMPATIBILIDAD (por que esta ruta NO es como `relaciones`).

    Esta ruta EXISTIA y tiene clientes. Antes:
      * ignoraba cualquier query param que no fuera `limit`/`tipo`;
      * un `limit` ilegible, negativo o enorme NO daba 400: `limite_seguro`
        lo recortaba al maximo (500) o caia al defecto (200).

    Aqui se reutiliza `config.limite_seguro`, que es la MISMA normalizacion de
    antes, y se entrega al servicio un entero ya dentro de rango. Asi la
    respuesta es la de siempre y el limite sigue decidiéndolo el servicio.
    No se inventa aqui una segunda politica de limites.

    PARECE REDUNDANTE Y NO LO ES. `servicio.figura_relaciones` vuelve a
    aplicar `limite_seguro`, asi que el recorte final ocurre ahi. Pero sin
    esta normalizacion previa, un `limit=-5` llegaria crudo al servicio, que
    responde INVALID_QUERY -> 400, donde antes habia un 200. Esta linea
    convierte una entrada hostil en una consulta valida ANTES de que el
    servicio la mire. Quitarla es una regresion de compatibilidad.
    """
    limite = config.limite_seguro(_uno(params, "limit"), defecto=200)
    return _responder(qc.buscar_relaciones(df_id,
                                            tipo_relacion=_uno(params, "tipo"),
                                            limite=limite))


# ===================================================== RUTAS CHRONICLES V1 ====
# Superficie NUEVA de Chronicle: cada funcion es una traduccion HTTP a una
# operacion `consultar_*` del servicio. Nada de logica de dominio aqui: ese
# es exactamente el fallo que este modulo prohibe.
#
# El adaptador NO lee el indice ni el dataset: eso lo verifica la frontera.
# Solo valida texto de entrada, llama al servicio y anade `http_status` con
# `_responder`, que no muta el resultado del servicio (lo comprueba
# `probar_contrato_certainty` con M07).
L_SC = "limit"
O_SC = "offset"


def _lim_off_sc(q):
    """`limit`/`offset` de query. Devuelve `(limite, offset, error_dict)`."""
    limite, err = _entero(_uno(q, L_SC), "limit", defecto=None,
                          minimo=None, maximo=None)
    if limite is not None and limite < 1:
        err = "limit debe ser >= 1"
    offset, err_o = _entero(_uno(q, O_SC), "offset", defecto=0,
                            minimo=0, maximo=None)
    if err:
        return None, None, _error("LIMITE_INVALIDO", err, http=400)
    if err_o:
        return None, None, _error("OFFSET_INVALIDO", err_o, http=400)
    return limite, offset, None


def fortaleza(params, q=None):
    """`GET /api/chronicles/fortaleza` -> `consultar_fortaleza`."""
    malo = _rechaza_desconocidos(q, set())
    if malo:
        return malo
    return _responder(qc.consultar_fortaleza())


def figuras(params, q=None):
    """`GET /api/chronicles/figuras?limit=&offset=` -> `consultar_figuras`."""
    malo = _rechaza_desconocidos(q, {L_SC, O_SC})
    if malo:
        return malo
    limite, offset, err = _lim_off_sc(q)
    if err:
        return err
    return _responder(qc.consultar_figuras(limite=limite, offset=offset))


def figura(params, q=None):
    """`GET /api/chronicles/figuras/{hfid}` -> `consultar_figura`."""
    malo = _rechaza_desconocidos(q, set())
    if malo:
        return malo
    hfid, err = _texto(params.get("hfid"), "el hfid")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    return _responder(qc.consultar_figura(hfid))


def eventos(params, q=None):
    """`GET /api/chronicles/eventos?...` -> `consultar_eventos`.

    Filtros: hfid, tipo, tipo_raw, year, grado, desde, hasta. Un parametro
    mal escrito se RECHAZA (400): ignorarlo seria filtrar sin filtrar.
    """
    malo = _rechaza_desconocidos(
        q, {L_SC, O_SC, "hfid", "tipo", "tipo_raw", "year", "grado",
            "desde", "hasta"})
    if malo:
        return malo
    limite, offset, err = _lim_off_sc(q)
    if err:
        return err
    return _responder(qc.consultar_eventos(
        hfid=_uno(q, "hfid"), tipo=_uno(q, "tipo"),
        tipo_raw=_uno(q, "tipo_raw"), year=_uno(q, "year"),
        grado=_uno(q, "grado"), desde=_uno(q, "desde"),
        hasta=_uno(q, "hasta"), limite=limite, offset=offset))


def evento(params, q=None):
    """`GET /api/chronicles/eventos/{id}` -> `consultar_evento`."""
    malo = _rechaza_desconocidos(q, set())
    if malo:
        return malo
    eid, err = _texto(params.get("id"), "el id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    return _responder(qc.consultar_evento(eid))


def cronologia(params, q=None):
    """`GET /api/chronicles/cronologia?...` -> `consultar_timeline`."""
    malo = _rechaza_desconocidos(q, {L_SC, O_SC, "hfid", "tipo", "tipo_raw",
                                     "desde", "hasta"})
    if malo:
        return malo
    limite, offset, err = _lim_off_sc(q)
    if err:
        return err
    return _responder(qc.consultar_timeline(
        hfid=_uno(q, "hfid"), tipo=_uno(q, "tipo"),
        tipo_raw=_uno(q, "tipo_raw"), desde=_uno(q, "desde"),
        hasta=_uno(q, "hasta"), limite=limite, offset=offset))


def tipos_evento(params, q=None):
    """`GET /api/chronicles/tipos` -> `consultar_tipos_evento`."""
    malo = _rechaza_desconocidos(q, set())
    if malo:
        return malo
    return _responder(qc.consultar_tipos_evento())
    return None
    out["http_status"] = _http_de(out)
    return out
# ========================================================= RUTAS DE CONSULTA ==
# Superficie nueva. Cada ruta es una traduccion, no una implementacion.

def contrato():
    """`GET /api/consulta/contrato` -> el contrato, legible por HTTP.

    Un consumidor (humano o programa) puede preguntar «que sabes hacer?»
    sin leer el codigo. Y la respuesta es la del servicio, no una copia
    escrita a mano que se quedaria vieja.
    """
    return svc.envolver_estado(qc.contrato(), status="OK", certainty="FACT")


def entidad(params, q=None):
    """`GET /api/consulta/entidad/{tipo}/{id}`.

    `params` son los SEGMENTOS de la ruta y `q` son los query params. No se
    mezclan: `_rechaza_desconocidos` mira solo `q`. Antes de arreglar esto,
    `{tipo}` de la ruta se rechazaba a si mismo como parametro desconocido.
    """
    malo = _rechaza_desconocidos(q, {})
    if malo:
        return malo
    tipo, err = _tipo(params.get("tipo"))
    if err:
        return _error("TIPO_INVALIDO", err, http=400)
    df_id, err = _texto(params.get("id"), "el id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    return _responder(qc.obtener_entidad(tipo, df_id))


def atributo(params, q=None):
    """`GET /api/consulta/atributo/{tipo}/{id}/{atributo}`."""
    malo = _rechaza_desconocidos(q, {})
    if malo:
        return malo
    tipo, err = _tipo(params.get("tipo"))
    if err:
        return _error("TIPO_INVALIDO", err, http=400)
    df_id, err = _texto(params.get("id"), "el id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    atributo, err = _texto(params.get("atributo"), "el atributo", maximo=64)
    if err:
        return _error("ATRIBUTO_INVALIDO", err, http=400)
    return _responder(qc.obtener_atributo(tipo, df_id, atributo))


def relaciones(params, q=None):
    """`GET /api/consulta/relaciones/{id}`."""
    malo = _rechaza_desconocidos(q, {"tipo", "limit"})
    if malo:
        return malo
    df_id, err = _texto(params.get("id"), "el id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    limite, err = _entero(_uno(q, "limit"), "limit",
                          minimo=1, maximo=qc.LIMITE_MAXIMO)
    if err:
        return _error("LIMITE_INVALIDO", err, http=400,
                      limite_maximo=qc.LIMITE_MAXIMO)
    return _responder(qc.buscar_relaciones(df_id,
                                            tipo_relacion=_uno(q, "tipo"),
                                            limite=limite))


def contar(params, q=None):
    """`GET /api/consulta/contar/{tipo}?campo=&valor=`.

    Solo igualdad exacta, porque es lo unico que el servicio sabe hacer.
    Un `campo` que el dataset no declara -> el servicio responde
    NO_VERIFICADO, y aqui no se convierte en 0.
    """
    malo = _rechaza_desconocidos(q, {"campo", "valor"})
    if malo:
        return malo
    tipo, err = _tipo(params.get("tipo"))
    if err:
        return _error("TIPO_INVALIDO", err, http=400)
    campo, valor = _uno(q, "campo"), _uno(q, "valor")
    filtro = None
    if campo is not None and campo != "":
        if valor is None or valor == "":
            return _error("FILTRO_INVALIDO",
                          "si se envia `campo` hay que enviar tambien `valor`",
                          http=400)
        filtro = {str(campo): str(valor)}
    elif valor is not None and valor != "":
        return _error("FILTRO_INVALIDO",
                      "se envio `valor` sin `campo`: no hay con que comparar",
                      http=400)
    return _responder(qc.contar(tipo, filtro))


def verificar(params, q=None):
    """`GET /api/consulta/verificar?...`.

    Delega en `servicio_consulta.verificar`, que a su vez delega en
    `verificacion_semantica`. Aqui no hay un solo `if` sobre el resultado:
    el verificador ya es el nucleo, y reimplementarlo seria el fallo que
    la arquitectura prohibe.
    """
    malo = _rechaza_desconocidos(q, {"tipo", "id", "predicado", "objeto"})
    if malo:
        return malo
    tipo, err = _texto(_uno(q, "tipo"), "tipo", maximo=32)
    if err:
        return _error("TIPO_INVALIDO", err, http=400)
    df_id, err = _texto(_uno(q, "id"), "id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    predicado, err = _texto(_uno(q, "predicado"), "predicado", maximo=64)
    if err:
        return _error("PREDICADO_INVALIDO", err, http=400)
    return _responder(qc.verificar(tipo, df_id, predicado,
                                   _uno(q, "objeto")))


def evidencia(params, q=None):
    """`GET /api/consulta/evidencia/{tipo}/{id}?campos=a,b`."""
    malo = _rechaza_desconocidos(q, {"campos"})
    if malo:
        return malo
    tipo, err = _tipo(params.get("tipo"))
    if err:
        return _error("TIPO_INVALIDO", err, http=400)
    df_id, err = _texto(params.get("id"), "el id")
    if err:
        return _error("ID_INVALIDO", err, http=400)
    crudos = _uno(q, "campos")
    campos = [c.strip() for c in crudos.split(",") if c.strip()] if crudos else None
    return _responder(qc.obtener_evidencia(tipo, df_id, campos))