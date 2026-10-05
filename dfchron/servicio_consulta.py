#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAPA DE CONSULTA DETERMINISTA.

QUE ES
------
Una frontera estable para consultar el conocimiento estructurado del nucleo sin
tocar sus internals: sin `Archivo`, sin `Indice`, sin JSONL.

    consumidor -> QueryService -> nucleo

QUE NO ES
---------
No es un indice nuevo, ni una busqueda nueva, ni un verificador nuevo. **Delega**
en lo que ya existe y solo anade lo que faltaba.

LO QUE YA EXISTIA Y POR QUE NO SE DUPLICA
-----------------------------------------
| Necesidad                     | Donde vive YA                    |
|-------------------------------|----------------------------------|
| Busqueda y fichas             | `nucleo.Archivo`                 |
| Envelope de respuesta         | `servicio.envolver_lista/ficha`  |
| Errores estructurados         | `servicio.error()`               |
| Paginacion                    | `servicio.envolver_lista`        |
| Evidencia y procedencia       | `ia_conocimiento.evidencia_de`   |
| Verificacion de afirmaciones  | `verificacion_semantica`         |
| `dataset_id` / `state_version`| `ia_conocimiento.DATASET_ID`     |

La lista de codigos de error (`NO_ENCONTRADO`, `TIPO_DESCONOCICO`,
`CONSULTA_VACIA`...) tambien es prestada. **No se crea una taxonomia nueva.**

LO QUE SI ANADE, Y POR QUE
-------------------------
Los envelopes existentes NO transportan de que mundo viene lo que se lee. Un
consumidor recibe `{"ok": true, "data": {...}}` y no puede saber si es de este
dataset o de otro. Esta capa anade `identity` y `evidence` a cada resultado,
usando `ia_conocimiento`, que ya sabe emitirlos.

Ejecutar:  python dfchron/pruebas/probar_servicio_consulta.py
"""
import copy
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Donde vive el verificador determinista (`verificacion_semantica.py`), que
#: esta capa USA pero no reimplementa.
TOOLS = os.path.join(RAIZ, "00_SOURCE", "tools")

for _ruta in (RAIZ, TOOLS):
    if _ruta not in sys.path:
        sys.path.append(_ruta)

from dfchron import servicio                              # noqa: E402
from dfchron import ia_conocimiento as ic                 # noqa: E402

try:
    import verificacion_semantica as vs
except ImportError:                                         # pragma: no cover
    vs = None

# ======================================================== ESTADOS ===========
# NO se inventan estados nuevos. Se usan los que el proyecto YA tiene:
#
#   - `servicio.error(codigo, ...)` con `ok: False` y su codigo estable.
#   - `certainty` de `contrato_ia`: FACT / DERIVED / UNKNOWN.
#
# La equivalencia con los nombres conceptuales de la mision:
#
#   FOUND             -> ok=True  + certainty del dato
#   NOT_FOUND         -> ok=False + code NO_ENCONTRADO   (ya existe)
#   NOT_VERIFIED      -> ok=False + code NO_VERIFICADO    (nuevo, deliberado)
#   INVALID_QUERY     -> ok=False + code de `servicio` ya existente
#   DATA_UNAVAILABLE  -> ok=False + code NO_DISPONIBLE     (nuevo, deliberado)
#
# Los dos codigos nuevos son los MINIMOS que no existian y que la distincion
# entre «no existe» y «no se puede determinar» exige. Sin ellos habria que
# reusar `NO_ENCONTRADO` para las dos cosas, que es justamente el colapso que
# la prohibe: convertir «no puedo determinarlo» en «no existe».
NOT_FOUND = "NOT_FOUND"
NOT_VERIFIED = "NOT_VERIFIED"
INVALID_QUERY = "INVALID_QUERY"
DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
FOUND = "FOUND"

ESTADOS = (FOUND, NOT_FOUND, NOT_VERIFIED, INVALID_QUERY, DATA_UNAVAILABLE)

#: Codigos que ya existen en `servicio.py` y se reusan tal cual.
#: Se declaran aqui para que quede constancia de que la capa NO inventa una
#: taxonomia paralela. `test_los_codigos_prestados_existen_en_servicio` comprueba
#: que cada uno existe de verdad en ese fichero.
CODIGOS_PRESTADOS = (
    "NO_ENCONTRADO",        # id inexistente
    "TIPO_DESCONOCIDO",     # tipo de entidad no soportado
    "CONSULTA_VACIA",       # falta el texto de busqueda
)

#: Codigos nuevos, minimos, justificados arriba.
CODIGOS_NUEVOS = ("NO_VERIFICADO", "NO_DISPONIBLE")

#: Tipos con identidad demostrada. Los tres NO aparecen: no tienen `df_id`.
TIPOS_CON_IDENTIDAD = ("figura", "entidad", "sitio", "evento", "artefacto")

#: Tipos SIN identidad demostrada. Se declaran para poder responder con
#: honestidad cuando se piden, en vez de inventarles un id.
TIPOS_SIN_IDENTIDAD = ("relacion", "era", "suplemento")

#: Limite por defecto y maximo, para que ninguna consulta devuelva el mundo.
LIMITE_DEFECTO = 200
LIMITE_MAXIMO = 1000

# ====================================================== RESULTADO =========
def _identidad(tipo, df_id):
    """La identidad de lo consultado, y solo si existe de verdad.

    Devuelve `None` si el tipo no tiene identidad demostrada. Nunca se
    construye un id artificial: un consumidor que reciba `identity: null`
    sabe que eso no es consultable como entidad, que es la verdad.
    """
    if tipo not in TIPOS_CON_IDENTIDAD:
        return None
    return {"tipo": tipo, "df_id": str(df_id)}


def _evidencia(tipo, df_id, campos):
    """La evidencia, DEL `ia_conocimiento`: no se reimplementa.

    `evidencia_de()` ya ancla el `state_version` real al `DATASET_ID` que leyo
    del disco. Aqui solo se llama.
    """
    if tipo not in TIPOS_CON_IDENTIDAD:
        return None
    try:
        ev = ic.evidencia_de(tipo, str(df_id), list(campos),
                             "nucleo.Archivo.ficha_%s" % tipo, ["legends.xml"])
    except Exception:
        # Fallar al construir evidencia NO es inventarla: es no tenerla.
        return None
    return copy.deepcopy(dict(ev))


def _resultado(estado, data=None, tipo=None, df_id=None, campos=None,
               env=None, **extra):
    """El sobre comun de toda consulta.

    Envuelve el envelope que `servicio` ya produce y le anade `identity` y
    `evidence`, que es lo que faltaba. El envelope original no se rompe: sus
    claves siguen intactas para que un cliente antiguo no se entere.
    """
    base = dict(env) if isinstance(env, dict) else {}
    if env is None:
        base = {"ok": estado == FOUND, "data": data, "status": estado,
                "certainty": "FACT" if estado == FOUND else "UNKNOWN",
                "meta": {"total": 1 if data is not None else 0,
                         "returned": 1 if data is not None else 0,
                         "truncated": False,
                         "certainty": "FACT" if estado == FOUND else "UNKNOWN"}}
        if estado != FOUND:
            base["error"] = {"codigo": estado, "code": estado,
                             "mensaje": extra.get("motivo", estado),
                             "message": extra.get("motivo", estado)}
    base["estado"] = estado
    base["identity"] = _identidad(tipo, df_id) if tipo else None
    base["evidence"] = _evidencia(tipo, df_id, campos) if tipo else None
    base["dataset_id"] = ic.DATASET_ID
    base["alcance"] = alcance()
    if extra:
        for k, v in extra.items():
            if k != "motivo":
                base[k] = v
    return base


def alcance():
    """Qué puede y qué no puede esta capa. Viaja con cada respuesta.

    Sin esto, un consumidor tendría que suponer que «consulta» significa
    «responde lo que sea». Y no.
    """
    return {
        "puede": [
            "consultar entidades que tienen df_id",
            "leer atributos declarados en el dataset",
            "recorrer relaciones explicitamente registradas",
            "contar y filtrar con operadores definidos",
            "verificar afirmaciones estructuradas",
            "decir de que dataset y con que state_version viene cada dato",
        ],
        "no_puede": [
            "responder en lenguaje natural",
            "inferir lo que el XML no dice",
            "predecir ni deducir mas alla del dato",
            "dar una identidad a las relaciones, la era o los suplementos",
            "afirmar orden temporal sin años",
            "inventar caducidad: dataset_id NO es un reloj",
            "convertir ausencia de evidencia en evidencia de ausencia",
        ],
    }


# ==================================================== OPERACIONES =========
def _validar_limite(limite):
    """Normaliza `limite`. Devuelve `(limite, error)` — nunca lanza."""
    if limite is None:
        return LIMITE_DEFECTO, None
    if isinstance(limite, bool) or not isinstance(limite, int):
        return None, "el limite debe ser un entero"
    if limite < 1:
        return None, "el limite debe ser mayor que cero"
    return min(limite, LIMITE_MAXIMO), None


def obtener_entidad(tipo, df_id):
    """Operación 1. La ficha de una entidad, con identidad y evidencia.

    Delega en `servicio.figura/entidad/sitio/…`, que ya envuelven la ficha del
    núcleo. Aquí no se lee el índice directamente.
    """
    if tipo in TIPOS_SIN_IDENTIDAD:
        # Se pasa `tipo` a proposito: `_identidad` y `_evidencia` deben
        # comprobarlo ellos mismos y devolver `None`. Si aqui seroscopicara
        # el tipo, esas guardas nunca se ejercitarian y un cambio futuro
        # podria inventar una identidad sin que nada se diera cuenta.
        return _resultado(
            NOT_VERIFIED, tipo=tipo,
            motivo="el tipo %r no tiene identidad demostrada en el dataset; "
                   "no se puede consultar como entidad" % tipo)
    if tipo not in TIPOS_CON_IDENTIDAD:
        return _resultado(INVALID_QUERY,
                          motivo="tipo %r no soportado; soportados: %s"
                          % (tipo, ", ".join(TIPOS_CON_IDENTIDAD)))
    if df_id is None or str(df_id).strip() == "":
        return _resultado(INVALID_QUERY, motivo="falta el df_id")

    fn = {"figura": servicio.figura, "entidad": servicio.entidad,
          "sitio": servicio.sitio, "evento": servicio.evento,
          "artefacto": servicio.artefacto}[tipo]
    env = fn(str(df_id))
    if not env.get("ok"):
        # El núcleo ya dijo que no existe. No se reinterpreta.
        return _resultado(NOT_FOUND, env=env, tipo=tipo, df_id=df_id,
                          campos=["nombre"],
                          motivo=env.get("error", {}).get("mensaje"))
    return _resultado(FOUND, env=env, tipo=tipo, df_id=df_id,
                      campos=list(env["data"].keys())[:8])


def obtener_atributo(tipo, df_id, atributo):
    """Operación 2. Un atributo concreto.

    Si el atributo no existe, **no se infiere**: se responde que no se pudo
    determinar, que es distinto de «no existe la entidad».
    """
    r = obtener_entidad(tipo, df_id)
    if r["estado"] != FOUND:
        return r
    datos = r["data"] if isinstance(r.get("data"), dict) else {}
    if atributo not in datos:
        return _resultado(
            NOT_VERIFIED, tipo=tipo, df_id=df_id,
            motivo="la entidad existe pero el dataset no declara el atributo "
                   "%r; no se infiere" % atributo,
            atributos_disponibles=sorted(datos.keys()))
    valor = datos[atributo]
    if valor in (None, "", "-1"):
        return _resultado(
            NOT_VERIFIED, tipo=tipo, df_id=df_id, valor=None,
            motivo="el atributo %r esta ausente en el dato" % atributo)
    out = _resultado(FOUND, tipo=tipo, df_id=df_id, campos=[atributo])
    out["data"] = {"atributo": atributo, "valor": valor}
    return out


def buscar_relaciones(origen, tipo_relacion=None, limite=None):
    """Operación 3. Relaciones **registradas**, nunca reconstruidas.

    Delega en `servicio.figura_relaciones`, que ya aplica el grafo dirigido y
    el filtro por tipo. Si no hay ninguna, se dice que no hay: no se infiere.
    """
    lim, err = _validar_limite(limite)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    r = obtener_entidad("figura", origen)
    if r["estado"] != FOUND:
        return r
    env = servicio.figura_relaciones(str(origen), tipo=tipo_relacion, limite=lim)
    env["estado"] = FOUND if env.get("ok") else NOT_FOUND
    env["identity"] = _identidad("figura", origen)
    env["evidence"] = _evidencia("figura", origen, ["relacion"])
    env["dataset_id"] = ic.DATASET_ID
    env["alcance"] = alcance()
    return env


def contar(tipo, filtro=None):
    """Operación 4. Cuántos hay, con filtro de igualdad exacta.

    El filtro es `{"campo": valor}` y solo admite `==`. Se rechaza explícitamente
    cualquier otra cosa: «los mejores mineros» no pertenece a esta capa, y
    «mejores» no es un campo del dataset.
    """
    if tipo in TIPOS_SIN_IDENTIDAD:
        return _resultado(
            NOT_VERIFIED,
            motivo="el tipo %r no tiene identidad, así que no se puede contar"
                   % tipo)
    if tipo not in TIPOS_CON_IDENTIDAD:
        return _resultado(INVALID_QUERY, motivo="tipo %r no soportado" % tipo)
    if filtro is not None and not isinstance(filtro, dict):
        return _resultado(INVALID_QUERY,
                          motivo="el filtro debe ser un objeto {campo: valor}")

    try:
        archivo = servicio.obtener_archivo()
    except Exception as exc:                       # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="el dataset no esta disponible: %s" % exc)

    indice = {"figura": archivo.indice.figuras,
              "entidad": archivo.indice.entidades,
              "sitio": archivo.indice.sitios,
              "evento": archivo.indice.eventos,
              "artefacto": archivo.indice.artefactos}[tipo]

    total = len(indice)
    for campo in (filtro or {}):
        if campo not in _campos_de(indice):
            return _resultado(
                NOT_VERIFIED,
                motivo="el campo %r no existe en el dataset; no se filtra por "
                       "suposicion" % campo,
                campos_disponibles=sorted(_campos_de(indice))[:20])

    coincidencias = sum(1 for r in indice.values() if _coincide(r, filtro or {}))

    out = _resultado(FOUND, tipo=tipo)
    out["data"] = {"tipo": tipo, "total": total,
                   "coincidencias": coincidencias,
                   "filtros_aplicados": dict(filtro or {})}
    return out


def _campos_de(indice):
    """Los nombres de campo que el dataset declara de verdad."""
    campos = set()
    for registro in list(indice.values())[:200]:
        campos |= set((registro.get("campos") or {}).keys())
    return campos


def _coincide(registro, filtros):
    """Igualdad EXACTA sobre el valor del campo. Sin normalizar."""
    campos = registro.get("campos") or {}
    for campo, valor in filtros.items():
        entrada = campos.get(campo)
        obtenido = (entrada or {}).get("valor") if isinstance(entrada, dict) \
            else None
        if str(obtenido) != str(valor):
            return False
    return True


def verificar(sujeto_tipo, sujeto_id, predicado, objeto=None):
    """Operación 5. Verificar una afirmación estructurada.

    **Delega** en `verificacion_semantica`, que ya existe y ya está probado.
    Esta capa no implementa un segundo verificador: sería exactamente lo que la
    misión prohíbe.

    `predicado` decide qué se comprueba:

        "existe"                 -> nivel 1
        "tiene:<atributo>"       -> nivel 2  (`objeto` es el valor esperado)
        "relacionado_con"        -> nivel 3  (`objeto` es el otro id)
        "es_de_tipo"             -> nivel 4
        "total"                  -> nivel 5  (`objeto` es la cuenta esperada)
    """
    if vs is None:                                   # pragma: no cover
        return _resultado(DATA_UNAVAILABLE,
                          motivo="el verificador determinista no esta disponible")
    if predicado == "existe":
        r = vs.existe(servicio.obtener_archivo(), sujeto_tipo, sujeto_id)
    elif predicado and predicado.startswith("tiene:"):
        campo = predicado.split(":", 1)[1]
        r = vs.atributo(servicio.obtener_archivo(), sujeto_tipo, sujeto_id,
                        campo, objeto)
    elif predicado == "relacionado_con":
        r = vs.relacion(servicio.obtener_archivo(), sujeto_id, objeto)
    elif predicado == "es_de_tipo":
        r = vs.estado(servicio.obtener_archivo(), sujeto_tipo, sujeto_id)
    elif predicado == "total":
        r = vs.cantidad(servicio.obtener_archivo(), sujeto_tipo, objeto)
    else:
        return _resultado(
            INVALID_QUERY,
            motivo="predicado %r no soportado; soportados: existe, "
                   "tiene:<atributo>, relacionado_con, es_de_tipo, total"
                   % predicado)

    verificado = (r["estado"] == vs.VERIFICADA)
    out = _resultado(FOUND if verificado else NOT_VERIFIED,
                     tipo=sujeto_tipo, df_id=sujeto_id)
    out["data"] = {"afirmacion": {"sujeto_tipo": sujeto_tipo,
                                  "sujeto_id": str(sujeto_id),
                                  "predicado": predicado,
                                  "objeto": objeto},
                   "verificacion": r}
    return out


def obtener_evidencia(tipo, df_id, campos=None):
    """Operación 6. Solo la evidencia, delegando en `ia_conocimiento`.

    No se reimplementa la procedencia: se pide. Y si el tipo no tiene identidad,
    se responde `NOT_VERIFIED` en vez de fabricar un rastro.
    """
    if tipo in TIPOS_SIN_IDENTIDAD:
        return _resultado(
            NOT_VERIFIED,
            motivo="el tipo %r no tiene identidad demostrada; no se puede "
                   "rastrear a una fuente" % tipo)
    if tipo not in TIPOS_CON_IDENTIDAD:
        return _resultado(INVALID_QUERY, motivo="tipo %r no soportado" % tipo)
    ev = _evidencia(tipo, df_id, campos or ["nombre"])
    if ev is None:
        return _resultado(DATA_UNAVAILABLE,
                          motivo="no se pudo construir la evidencia")
    out = _resultado(FOUND, tipo=tipo, df_id=df_id, campos=campos)
    out["data"] = ev
    return out


# ============================================ OPERACIONES CHRONICLES V1 ========
# Consultas sobre la CRONICA: eventos interpretados, figuras con estado,
# timeline ordenada y snapshot demostrable de la fortaleza.
#
# Reglas de convivencia con la frontera existente:
#
#   1. `contrato()["operaciones"]` NO cambia: sigue con EXACTAMENTE las 6
#      del nucleo de conocimiento. Esa lista es el whitelist del perimetro IA
#      (AI_CONSUMER_BOUNDARY.md: «Seis operaciones. Ni una mas»), fijado por
#      `probar_perimetro_ia` y por `probar_servicio_consulta`. Las operaciones
#      Chronicles se declaran en `contrato()["operaciones_chronicles"]`: nunca
#      en `"operaciones"`, porque Chronicle no entra en el perimetro IA.
#
#   2. Se reutiliza `_resultado()`: el MISMO sobre (ok, data, estado,
#      identity, evidence, dataset_id, alcance). El contrato Chronicles es una
#      extension de este modulo, no una segunda arquitectura paralela.
#
#   3. Este fichero NO lee datasets: no se abre aqui ningun fichero. La
#      lectura vive en `chronicles_datos.cronica()` (JSONL, cache por huella);
#      aqui solo se LLAMA (import perezoso), como exige la frontera.
CHRONICLES_OPS = ("consultar_fortaleza", "consultar_figuras",
                  "consultar_figura", "consultar_eventos",
                  "consultar_evento", "consultar_timeline",
                  "consultar_tipos_evento")


def _cronica():
    """La cronica completa, delegando en `chronicles_datos`.

    El `import` es perezoso a proposito: `chronicles_datos` toca disco al
    usarse, y este modulo debe IMPORTARSE sin tocarlo (la frontera lo exige).
    La lectura ocurre solo cuando se CONSULTA.
    """
    from dfchron import chronicles_datos as _cd
    return _cd.cronica()


def _validar_paginacion(limite, offset):
    """`(limite, offset, error)`: nunca lanza, nunca inventa valores."""
    if limite is None or limite == "":
        limite = LIMITE_DEFECTO
    if offset is None or offset == "":
        offset = 0
    try:
        lim = int(str(limite).strip())
    except (TypeError, ValueError):
        return None, None, "el limite debe ser un entero"
    try:
        off = int(str(offset).strip())
    except (TypeError, ValueError):
        return None, None, "el offset debe ser un entero"
    if lim < 1:
        return None, None, "el limite debe ser mayor que cero"
    if off < 0:
        return None, None, "el offset no puede ser negativo"
    return min(lim, LIMITE_MAXIMO), off, None


def _sobre_lista(data, total, limite, offset=0, estado=FOUND, **extra):
    """Sobre de LISTADO: `servicio.envolver_lista` + la capa de consulta.

    `envolver_lista` declara `(meta, total_encontrados, devueltos, truncado,
    limit, certainty)`: NO se crea una segunda convencion. Se ANADEN `estado`,
    `identity`, `evidence`, `dataset_id` y `alcance`, como hace `_resultado`.
    """
    env = servicio.envolver_lista(list(data), total, limite, offset=offset,
                                  **extra)
    env["estado"] = estado
    env["identity"] = None
    env["evidence"] = None
    try:
        from dfchron import ia_conocimiento as _ic
        env["dataset_id"] = _ic.DATASET_ID
    except Exception:                                 # noqa: BLE001
        env["dataset_id"] = None
    env["alcance"] = alcance()
    return env


def consultar_fortaleza():
    """Operacion C1. Snapshot de la fortaleza: solo lo demostrable.

    La identidad de LA fortaleza del jugador es `NOT_PROVEN` (el dataset
    declara 13 sitios `fortress` y legends.xml no dice cual es del jugador);
    la lista de sitios fortress, el periodo y los recuentos son `DERIVED`.
    """
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    return _resultado(FOUND, data=dict(cronica["snapshot"]),
                      certeza="DERIVED")


def consultar_figuras(limite=None, offset=0):
    """Operacion C2. Figuras paginadas. Orden determinista por `hfid`.

    `estado` es `DEATH` con la evidencia del evento, o `NOT_AVAILABLE`:
    una figura sin DEATH no se declara viva ni muerta.
    """
    lim, off, err = _validar_paginacion(limite, offset)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    figuras = list(cronica["figuras"])
    pagina = figuras[off:off + lim]
    env = _sobre_lista(pagina, len(figuras), lim, offset=off,
                       certeza="DERIVED")
    env["data"] = {"tipo": "figura", "figuras": pagina}
    return env


def consultar_figura(hfid):
    """Operacion C3. UNA figura por `hfid`. `None` si no existe: no se inventa.

    Devuelve la ficha Chronicles: identidad, estado (DEATH con evidencia o
    NOT_AVAILABLE con motivo), datos del registro y cobertura temporal.
    """
    if hfid is None or str(hfid).strip() == "":
        return _resultado(INVALID_QUERY, motivo="falta el hfid")
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    from dfchron import chronicles_motor as _cm
    figura = _cm.detalle_figura(cronica, str(hfid).strip())
    if figura is None:
        return _resultado(NOT_FOUND, tipo="figura", df_id=str(hfid),
                          motivo="no existe la figura %r" % str(hfid))
    out = _resultado(FOUND, tipo="figura", df_id=str(hfid),
                     campos=["nombre", "estado", "nacimiento",
                             "fallecimiento_registro", "cobertura_temporal"])
    out["data"] = dict(figura)
    return out


def _par_temporal(valor, nombre):
    """`(year, seconds72)` desde texto HTTP. Devuelve `(par, error)`."""
    if valor is None or valor == "":
        return None, None
    t = str(valor).strip()
    if "," in t:
        partes = t.split(",", 1)
    elif " " in t:
        partes = t.split(None, 1)
    else:
        partes = [t]
    if len(partes) == 1:
        try:
            return (int(partes[0].strip()), -1), None
        except (TypeError, ValueError):
            return None, "%s debe ser `year` o `year,seconds72`" % nombre
    try:
        return (int(partes[0].strip()), int(partes[1].strip())), None
    except (TypeError, ValueError):
        return None, "%s debe ser `year` o `year,seconds72`" % nombre


def _rango_desde_hasta(desde, hasta):
    """Valida y normaliza el rango temporal. Devuelve `(d, h, error)`."""
    d, err_d = _par_temporal(desde, "desde")
    h, err_h = _par_temporal(hasta, "hasta")
    if err_d:
        return None, None, err_d
    if err_h:
        return None, None, err_h
    if d is not None and h is not None and d > h:
        return None, None, "el rango esta invertido: desde > hasta"
    return d, h, None


def consultar_eventos(hfid=None, tipo=None, tipo_raw=None, year=None,
                      grado=None, desde=None, hasta=None,
                      limite=None, offset=0):
    """Operacion C4. Eventos y observaciones, con filtros y paginacion.

    NO oculta lo no interpretado: las observaciones NOT_PROVEN viajan con
    `grado` y `motivo`. Filtros de igualdad exacta (==), como en `contar`.
    `desde`/`hasta` aceptan `year` o `year,seconds72`, inclusivos.
    """
    lim, off, err = _validar_paginacion(limite, offset)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    ano = None
    if year is not None and str(year).strip() != "":
        try:
            ano = int(str(year).strip())
        except (TypeError, ValueError):
            return _resultado(INVALID_QUERY,
                              motivo="year debe ser un entero")
    d, h, err = _rango_desde_hasta(desde, hasta)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    from dfchron import chronicles_motor as _cm
    res = _cm.consultar(cronica, lim, offset=off,
                        hfid=(str(hfid).strip() if hfid not in (None, "")
                              else None),
                        tipo=(str(tipo).strip() if tipo not in (None, "")
                              else None),
                        tipo_raw=(str(tipo_raw).strip()
                                  if tipo_raw not in (None, "") else None),
                        year=ano,
                        grado=(str(grado).strip() if grado not in (None, "")
                               else None),
                        desde=d, hasta=h)
    env = _sobre_lista(res["filas"], res["total"], lim, offset=off,
                       estado=FOUND, certeza="DERIVED")
    env["data"] = {"filas": res["filas"],
                   "filtros": {"hfid": hfid, "tipo": tipo,
                               "tipo_raw": tipo_raw, "year": ano,
                               "grado": grado, "desde": desde,
                               "hasta": hasta}}
    return env


def consultar_evento(event_id):
    """Operacion C5. UN evento por su `event_id`.

    Si el id existe pero NO es un evento interpretado (observacion
    NOT_PROVEN/UNSUPPORTED), se responde `NOT_VERIFIED` con el motivo: no es
    un dato inexistente, es uno no interpretado, y debe seguir auditable.
    """
    if event_id is None or str(event_id).strip() == "":
        return _resultado(INVALID_QUERY, motivo="falta el event_id")
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    from dfchron import chronicles_motor as _cm
    evento = _cm.detalle_evento(cronica, str(event_id).strip())
    if evento is None:
        obs = _cm.detalle_observacion(cronica, str(event_id).strip())
        if obs is not None:
            return _resultado(
                NOT_VERIFIED, motivo="existe con grado %s: no es un evento "
                                     "interpretado, pero su registro sigue "
                                     "auditable" % obs.get("grado"),
                data=dict(obs))
        return _resultado(NOT_FOUND,
                          motivo="no existe el evento %r" % str(event_id))
    return _resultado(FOUND, data=dict(evento))


def consultar_timeline(hfid=None, tipo=None, tipo_raw=None,
                       desde=None, hasta=None, limite=None, offset=0):
    """Operacion C6. Timeline ordenada: `year`, `seconds72`, identificador.

    El orden lo decide el MOTOR: la consulta no reordena (como la Web, que NO
    reordena en JS). Sin filtro de `grado`: la timeline muestra la cronica,
    no la clasificacion."""
    lim, off, err = _validar_paginacion(limite, offset)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    d, h, err = _rango_desde_hasta(desde, hasta)
    if err:
        return _resultado(INVALID_QUERY, motivo=err)
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    from dfchron import chronicles_motor as _cm
    res = _cm.consultar(cronica, lim, offset=off,
                        hfid=(str(hfid).strip() if hfid not in (None, "")
                              else None),
                        tipo=(str(tipo).strip() if tipo not in (None, "")
                              else None),
                        tipo_raw=(str(tipo_raw).strip()
                                  if tipo_raw not in (None, "") else None),
                        desde=d, hasta=h)
    env = _sobre_lista(res["filas"], res["total"], lim, offset=off,
                       estado=FOUND, certeza="DERIVED",
                       orden=["year", "seconds72", "event_id"],
                       orden_nota="el orden lo decide el motor; la consulta "
                                  "y la Web lo representan, no lo calculan")
    env["data"] = {"filas": res["filas"],
                   "filtros": {"hfid": hfid, "tipo": tipo,
                               "tipo_raw": tipo_raw, "desde": desde,
                               "hasta": hasta}}
    return env


def consultar_tipos_evento():
    """Operacion C7. Inventario de tipos con su grado y su regla.

    La prueba de que nada se oculta: SUPPORTED, PARTIAL, NOT_PROVEN y
    UNSUPPORTED viajan todos, con sus recuentos y sus motivos.
    """
    try:
        cronica = _cronica()
    except Exception as exc:                          # noqa: BLE001
        return _resultado(DATA_UNAVAILABLE,
                          motivo="chronicles no disponible: %s" % exc)
    from dfchron import chronicles_vocab as _vv
    return _resultado(FOUND, data={
        "grados": list(_vv.GRADOS),
        "tipos_soportados": sorted(_vv.SEMANTICA),
        "tipos_no_demostrados": sorted(_vv.SEMANTICA_NO_DEMOSTRADA),
        "reglas": dict((k, dict(v)) for k, v in _vv.SEMANTICA.items()),
        "no_demostradas": dict(_vv.SEMANTICA_NO_DEMOSTRADA),
        "informe": dict(cronica["informe"]),
    }, certeza="FACT")


def contrato():
    """El contrato, legible desde el propio código.

    No es documentación externa: es lo que la capa garantiza sobre sí misma.

    `"operaciones"` (6, nucleo de conocimiento) es el whitelist del perimetro
    IA y NO cambia. `"operaciones_chronicles"` (7, cronica) es la extension
    Chronicles de ESTE modulo: mismo sobre, mismos estados, mismos codigos.
    """
    return {
        "version": 1,
        "operaciones": ["obtener_entidad", "obtener_atributo",
                        "buscar_relaciones", "contar", "verificar",
                        "obtener_evidencia"],
        "operaciones_chronicles": list(CHRONICLES_OPS),
        "estados": list(ESTADOS),
        "codigos_prestados": list(CODIGOS_PRESTADOS),
        "codigos_nuevos": list(CODIGOS_NUEVOS),
        "tipos_con_identidad": list(TIPOS_CON_IDENTIDAD),
        "tipos_sin_identidad": list(TIPOS_SIN_IDENTIDAD),
        "operadores_filtro": ["=="],
        "limite_defecto": LIMITE_DEFECTO,
        "limite_maximo": LIMITE_MAXIMO,
        "temporalidad": "dataset_id identifica contenido. NO es un reloj. "
                        "No hay caducidad.",
        "alcance": alcance(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(contrato(), ensure_ascii=False, indent=2))