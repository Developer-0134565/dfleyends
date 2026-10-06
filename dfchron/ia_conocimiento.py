#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Puente de conocimiento para la futura IA
===========================================================

Este modulo es la FRONTERA entre el nucleo y el contrato de IA:

    NUCLEO (nucleo.Archivo)  ->  ESTE MODULO  ->  contrato_ia  ->  futura IA

LA REGLA
--------
    Un dato puede ser VERDADERO y aun asi NO PODER decirse.

Aqui eso deja de ser una idea del documento y pasa a ser codigo: cada dato que
sale del nucleo se envuelve en una `afirmacion` con su verdad, su visibilidad,
su permiso de divulgacion y su procedencia, y de ahi no se sale sin pasar por
`contrato_ia.puede_revelarse()`.

LO QUE ESTE MODULO **NO** ES
-----------------------------
No es una IA. No llama a ningun modelo, ni a la red, ni lee ficheros de la
partida. No inventa claims: cada afirmacion repite un valor que el nucleo ya
devolvio, con el `df_id` y el campo de donde salio. Si el nucleo dice
UNKNOWN, aqui tambien.

NO MODIFICA EL NUCLEO
---------------------
Usa unicamente la API publica de `nucleo.Archivo`. No se toca `nucleo.py`, ni
los XML, ni los JSONL, ni `procesado/`. Este modulo solo lee, a traves del
nucleo, y anade metadatos.

LA LIMITACION DE PLAYER_KNOWLEDGE (importante)
----------------------------------------------
El dataset **no registra que discovering el jugador**. `legends.xml` no sabe
quien vio que. Por eso este modulo NO puede marcar nada como `PLAYER_VISIBLE`
por el hecho de conocerlo: no hay prueba de que el jugador lo supiera.

Consecuencia, y es deliberada: **todo lo que viene de `WORLD_KNOWLEDGE` sale
como `PLAYER_HIDDEN` + `FORBIDDEN`**. No es una limitacion provisional, es la
unica respuesta honesta a "no lo puedo demostrar". El mecanismo para abrirlo
existe y es `convertir('revelar', ...)`, que exige un motivo y deja constancia
de quien lo decided. Cuando exista un registro real de descubrimientos, se
enchufa ahi y no hay que reescribir nada.

Determinismo: no hay relojes, ni numeros aleatorios, ni UUID. Las mismas
entradas producen siempre el mismo conocimiento, byte a byte.
"""
import os
import sys

# El nucleo vive en 00_SOURCE/tools y se importa por su nombre plano, igual
# que hace `dfchron/contrato_ia.py`. Se anade la ruta solo si falta.
# Dos niveles: `dfchron/` -> `DF-Chronicles/`.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERRAMIENTAS = os.path.join(_RAIZ, "00_SOURCE", "tools")
if _HERRAMIENTAS not in sys.path:
    sys.path.insert(0, _HERRAMIENTAS)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from . import contrato_ia as c                       # noqa: E402
from nucleo import Archivo                            # noqa: E402

# ============================================================ IDENTIDAD ======
#: Se lee `dataset_version.json`, que ya existe. NO se genera un id con reloj:
#: el identificador tiene que ser el del dataset realmente cargado, para que
#: una afirmacion pueda auditarse contra los mismos bytes que lo produjeron.
VERSION_DATASET = os.path.join(_RAIZ, "00_SOURCE", "dataset_version.json")

#: Si el fichero no existe, el puente NO inventa un id: lo declara desconocido.
#: Un `dataset_id` inventado haria auditable una afirmacion que no lo es.
DESCONOCIDO = "UNKNOWN"


def _leer_registro(ruta=None):
    """`dataset_version.json` desde el disco. La UNICA apertura de este modulo.

    Una sola, y a proposito. El invariante de este modulo es que el puente de
    conocimiento no abre ficheros de DATOS del mundo (XML, JSONL): solo consulta
    el registro que declara de que dataset se trata. Abrirlo dos veces no
    debilitaria ese invariante, pero tampoco aportaria nada y haria que la
    lectura y su congelacion pudieran divergir sin que nadie lo notase.

    Devuelve `None` si el fichero no se pudo leer, y el diccionario si se pudo.
    La distincion importa: «no hay registro» y «hay registro pero es anterior a
    P1.1» son dos ausencias DISTINTAS, con motivos distintos, y confundirlas
    haria que un fallo de lectura pareciera una decision.
    """
    try:
        import json
        with open(ruta or VERSION_DATASET, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


#: Se lee UNA vez y se congela, igual que `DATASET_ID`: durante toda la vida del
#: proceso el dataset servido es el mismo, y el determinismo lo exige.
_REGISTRO = _leer_registro()


def dataset_id():
    """El identificador del dataset activo, leido del disco. Sin reloj."""
    return (_REGISTRO or {}).get("dataset_id") or DESCONOCIDO


#: Se resuelve una vez y se congela: durante toda la vida del proceso el
#: dataset es el mismo, y el determinismo lo exige.
DATASET_ID = dataset_id()


# ------------------------------------------------- IDENTIDAD DEL MUNDO (P1.1) --
# El `dataset_id` identifica el CONTENIDO extraido. P1 demostro con datos
# reales que eso NO distingue un mundo de otro, y que el mundo puede cambiar sin
# que el contenido cambie.
#
# La identidad del mundo (`world_name`, `world_folder`) la captura
# `00_SOURCE/tools/identidad_mundo.py` durante la extraccion y se persiste en la
# MISMA clave que este modulo ya lee: `dataset_version.json["mundo"]`. Por eso
# vive aqui y no en otro sitio: mismo fichero, misma lectura, mismo criterio de
# «ausente se declara, no se supone», misma congelacion por proceso.
#
# NO es identidad del ESTADO. No hay `state_id`, `lineage_id`, `snapshot_id` ni
# `tick_id` aqui, y no debe anadirse sin la evidencia que P1 declara ausente.
#
# Por que NO viaja en el sobre de cada respuesta: ese sobre lo construye
# `servicio_consulta._resultado()` (lineas 166-167) y `buscar_relaciones()`
# (lineas 291-292), y ese modulo esta CONGELADO. El adaptador no puede
# anadirlo porque su propia regla es no fabricar nada que no venga del servicio.
# Ver `P1.2_PROPAGACION_IDENTIDAD_MUNDO.md`.

#: Motivos de ausencia. El primero es el caso real de este repositorio: un
#: `dataset_version.json` generado antes de P1.1 no tiene la clave `mundo`.
SIN_MUNDO = ("el dataset activo se genero antes de P1.1 y su "
             "dataset_version.json no tiene la clave 'mundo'")
SIN_VERSION_DATASET = "dataset_version.json no existe o no es legible"


def mundo_de(doc):
    """La identidad del mundo a partir de un `dataset_version.json` YA LEIDO.

    Se separa de `mundo()` para que un consumidor que ya tiene el documento en
    la mano — `servicio._resumen_dataset()` lo tiene, por `_leer_version()` — no
    vuelva a leer el fichero, y para que la INTERPRETACION de la ausencia vivan
    en un solo sitio. La regla de este proyecto es no duplicar la decision: si
    dos sitios interpretaran `mundo`, divergeirían sin que nadie lo notase.

    Misma salida que `mundo()`, y el mismo criterio: ausente se DECLARA.
    """
    vacio = {"world_name": DESCONOCIDO, "world_folder": DESCONOCIDO,
             "world_name_ausente_porque": SIN_VERSION_DATASET,
             "world_folder_ausente_porque": SIN_VERSION_DATASET}
    if not isinstance(doc, dict):
        return vacio

    bloque = doc.get("mundo")
    if not isinstance(bloque, dict):
        # Dataset anterior a P1.1: ausencia CONOCIDA, con motivo. No es un fallo
        # de lectura y no se rellena con nada.
        sin_mundo = dict(vacio)
        sin_mundo["world_name_ausente_porque"] = SIN_MUNDO
        sin_mundo["world_folder_ausente_porque"] = SIN_MUNDO
        return sin_mundo

    salida = {}
    for clave in ("world_name", "world_folder"):
        valor = bloque.get(clave)
        # Solo texto no vacio. Un numero, un `None` o "" son ausencias, no
        # identidades: declararlos seria inventar un valor.
        texto = valor.strip() if isinstance(valor, str) else None
        # Y el centinela `UNKNOWN` ES una ausencia, no un nombre de mundo. asi
        # lo escribe P1.1 en `desde_export()`, asi que si aqui se tomara por un
        # valor, el motivo de la ausencia se perderia por el camino.
        ausente = (not texto) or texto == DESCONOCIDO
        salida[clave] = DESCONOCIDO if ausente else texto
        salida["%s_ausente_porque" % clave] = (
            bloque.get("%s_ausente_porque" % clave) if ausente else None)
    return salida


def mundo(ruta=None):
    """La identidad del MUNDO del dataset activo, leida del disco. Sin reloj.

    `dataset_id` dice «qué contenido tengo». Esto dice «de qué mundo salió», que
    es una pregunta distinta y no la responde el hash.

    Devuelve SIEMPRE las mismas claves, para que un consumidor pueda leerlas sin
    comprobar antes si existen:

        world_name   -> nombre descriptivo. NO es unico global.
        world_folder -> carpeta del save. NO es unica fuera de este entorno.
        ..._ausente_porque -> por que falta, o None si no falta.

    Nunca inventa. Si el dato no esta, sale `UNKNOWN` con su motivo: un
    identificador falso es peor que ningun identificador, porque permite
    afirmar algo que nadie comprobo.

    `ruta` existe para que las pruebas puedan ejercitar esto de verdad contra
    ficheros reales, en vez de contra un doble. Sin `ruta`, se usa el registro ya
    leido y congelado, que es el camino normal.
    """
    if not ruta:
        return mundo_de(_REGISTRO)
    return mundo_de(_leer_registro(ruta))


#: Se congela igual que `DATASET_ID`, y por el mismo motivo: durante toda la vida
#: del proceso el dataset servido es el mismo.
MUNDO = mundo()

# ============================================================== ERRORES ======
class ConocimientoNoDisponible(Exception):
    """No se puede construir conocimiento. Falla aqui y no en el consumidor."""


# ============================================================ VISIBILIDAD ====
#: Lo que el nucleo ya declaro y este modulo no puede re-declarar.
_CERTEZA_NUCLEO = (c.FACT, c.DERIVED, c.UNKNOWN, c.INFERENCE)

#: Politica de visibilidad. Es UNA constante, no una decision por afirmacion:
#: que la cambiase dependeria de quien escribiese la afirmacion.
#:
#: - `WORLD_KNOWLEDGE`: nada se marca visible, porque no hay registro de
#:   descubrimientos. Se aplica a TODO lo que venga del nucleo.
#: - `EXTERNAL_KNOWLEDGE`: nunca describe esta partida; el contrato ya lo
#:   prohibe y aqui no se intenta esquivarlo.
VISIBILIDAD_MUNDO = c.PLAYER_HIDDEN
PERMISO_MUNDO = c.FORBIDDEN

#: Lo que SI se puede contar sin demostracion previa: que un dato NO consta.
#: No es un secreto: es la ausencia de informacion, que el jugador necesita.
VISIBILIDAD_HUECO = c.PLAYER_VISIBLE
PERMISO_HUECO = c.ALLOWED
# ========================================================== PROVENIENCIA =====
#: Lo que el nucleo declara como origen de sus fichas. Si el nucleo no lo dice,
#: se registra como desconocido en vez de suponer `legends.xml`.
FUENTES_DESCONOCIDAS = ()


def _fuentes(ficha):
    f = ficha.get("sources") if isinstance(ficha, dict) else None
    if isinstance(f, (list, tuple)) and f:
        return [str(x) for x in f]
    return list(FUENTES_DESCONOCIDAS)


def _texto(valor):
    """Un valor solo si es de verdad un valor. Ausente no se imprime."""
    if valor is None:
        return None
    if isinstance(valor, str):
        v = valor.strip()
        if not v or v == c.UNKNOWN or v == "null":
            return None
        return v
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, (list, tuple)):
        partes = [str(x) for x in valor if x is not None]
        return ", ".join(partes) if partes else None
    return None


def _certeza(ficha):
    """La certeza que declaro el nucleo. Si no la declara, no se inventa."""
    v = ficha.get("certainty") if isinstance(ficha, dict) else None
    return v if v in _CERTEZA_NUCLEO else c.UNKNOWN


def procedencia(entity_type, entity_id, funciones, fuentes_xml):
    """De que dato real salio esto. Sin esto, una afirmacion no es auditable.

    No lleva reloj, ni contador, ni nada que cambie entre dos ejecuciones: la
    misma afirmacion tiene que dar la misma procedencia siempre.

    Deliberadamente NO lleva la ruta del dataset en disco. El `dataset_id` ya
    lo identifica, y una ruta interna no le hace falta a un modelo: solo le da
    informacion del sistema de ficheros.
    """
    return {
        "dataset_id": DATASET_ID,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "funciones": list(funciones),
        "fuentes_xml": list(fuentes_xml),
    }


def evidencia_de(tipo, df_id, campos, funcion, fuentes_xml):
    """Rastro de un dato concreto hasta el campo del que salio.

    Se inyecta aqui el `state_version` real (`DATASET_ID`) para que **toda** la
    evidencia construida por este modulo quede anclada al DATASET que la produjo.
    Se hace en un unico sitio a proposito: si cada constructor se acordara de
    anadirlo por su cuenta, bastaria uno que se olvidara para que reapareciera
    el hueco que esta evidencia acaba de cerrar.

    OJO CON LA SEMANTICA (P1.1). Como `DATASET_ID` es el `dataset_id` derived
    del contenido, `state_version` identifica el **contenido extraido**, no el
    estado vivo del mundo: dos mundos con el mismo contenido son
    indistinguibles para este campo. Anclar la evidencia sigue siendo correcto;
    afirmar que prueba un estado del mundo, no. Ver `contrato_ia.evidencia()`.
    """
    return c.evidencia(tipo, df_id, list(campos), funcion,
                       list(fuentes_xml) or None, state_version=DATASET_ID)


# ========================================================= CONSTRUCCION ======
def afirmacion_del_mundo(claim, certeza, tipo, df_id, campos, funcion,
                         fuentes_xml, motivo=None, **extra):
    """Envuelve un dato del nucleo en una afirmacion con su permiso.

    Decide la visibilidad con la politica de este modulo, no con lo que le
    pase al llamante. Que el permiso dependa del consumidor es exactamente el
    fallo que hay que impedir.

    Hay dos caminos, y solo dos:

    * **Consta.** Se marca `no_descubierto=True`. El dataset no registra que
      descubrio el jugador, asi que su estado es el de "verdadero y no
      demostrado como suyo". Nace asi; no hace falta registre una conversion.
    * **No consta.** Se declara `UNKNOWN` con su motivo. Nunca se rellena.
    """
    if certeza == c.UNKNOWN:
        return c.afirmacion(
            claim=claim,
            truth_status=c.UNKNOWN,
            knowledge_source=c.WORLD_KNOWLEDGE,
            visibility=VISIBILIDAD_HUECO,
            disclosure=PERMISO_HUECO,
            evidences=[],
            motivo=motivo or "el nucleo no registro este dato",
            **extra
        )

    return c.afirmacion(
        claim=claim,
        truth_status=certeza,
        knowledge_source=c.WORLD_KNOWLEDGE,
        visibility=VISIBILIDAD_MUNDO,
        disclosure=PERMISO_MUNDO,
        evidences=[evidencia_de(tipo, df_id, campos, funcion, fuentes_xml)],
        no_descubierto=True,
        **extra
    )
# ================================================================= PUENTE ====
class Puente:
    """Une el nucleo con el contrato. Es lo unico que la futura IA debe importar.

    No hereda de nada y no guarda estado propio salvo el `Archivo` compartido:
    cargar 57.215 eventos cuesta ~2,5 s y no se va a repetir por cada consulta.

    Uso:

        from dfchron import ia_conocimiento
        k = ia_conocimiento.Puente().obtener_conocimiento_figura("712")
        respuesta = ia_conocimiento.preparar_respuesta_jugador(k)
    """

    def __init__(self, archivo=None):
        # `None` a proposito: se construye LAZILY. Importar este modulo no debe
        # costar dos segundos y medio de RAM solo por existir.
        self._archivo = archivo

    @property
    def archivo(self):
        if self._archivo is None:
            self._archivo = Archivo()
        return self._archivo

    # --- consultas -----------------------------------------------------
    def obtener_conocimiento_figura(self, df_id):
        return self._envolver(
            "figura", df_id, "nucleo.Archivo.ficha_figura",
            lambda i: self.archivo.ficha_figura(_como_id(i)),
            self._campos_figura,
        )

    def obtener_conocimiento_entidad(self, df_id):
        return self._envolver(
            "entidad", df_id, "nucleo.Archivo.ficha_entidad",
            lambda i: self.archivo.ficha_entidad(_como_id_entidad(i)),
            self._campos_entidad,
        )

    def obtener_conocimiento_sitio(self, df_id):
        return self._envolver(
            "sitio", df_id, "nucleo.Archivo.ficha_sitio",
            lambda i: self.archivo.ficha_sitio(_como_id(i)),
            self._campos_sitio,
        )

    def obtener_conocimiento_evento(self, df_id):
        return self._envolver(
            "evento", df_id, "nucleo.Archivo.ficha_evento",
            lambda i: self.archivo.ficha_evento(_como_id_entidad(i)),
            self._campos_evento,
        )

    def obtener_conocimiento_artefacto(self, df_id):
        return self._envolver(
            "artefacto", df_id, "nucleo.Archivo.ficha_artefacto",
            lambda i: self.archivo.ficha_artefacto(_como_id_entidad(i)),
            self._campos_artefacto,
        )

    # --- el motor comun ------------------------------------------------
    def _envolver(self, tipo, df_id, funcion, pedir, campos):
        """Llama al nucleo y convierte su respuesta, sin dejar que se escape."""
        try:
            ficha = pedir(df_id)
        except Exception:          # noqa: BLE001 - el nucleo no debe romper la IA
            # No se filtra el traceback al consumidor: un fallo aqui es una
            # afirmacion que no se pudo construir, no una excepcion interna.
            ficha = {"certainty": c.UNKNOWN,
                     "motivo": "el nucleo no pudo responder a esta consulta"}
        return self._construir(tipo, df_id, ficha, funcion, campos)

    def _construir(self, tipo, df_id, ficha, funcion, campos):
        """Devuelve el sobre de conocimiento. Nunca lanza por datos malos."""
        df_id_txt = str(df_id)
        fuentes = _fuentes(ficha)
        certeza = _certeza(ficha)

        # El nucleo no encontro el registro: UNKNOWN con su motivo y nada mas.
        if certeza == c.UNKNOWN:
            claims = [afirmacion_del_mundo(
                claim=f"El nucleo no tiene datos para {tipo} {df_id_txt}.",
                certeza=c.UNKNOWN, tipo=tipo, df_id=df_id_txt,
                campos=[], funcion=funcion, fuentes_xml=fuentes,
                motivo=ficha.get("motivo") or "el nucleo no registro este dato",
            )]
        else:
            claims = []
            # Una entrada es (clave, plantilla, valor) y, opcionalmente,
            # (certeza, motivo) cuando el campo trae su propia certeza anidada:
            # las fechas del nucleo pueden ser UNKNOWN dentro de una ficha FACT.
            for entrada in campos(ficha):
                clave, plantilla, valor = entrada[0], entrada[1], entrada[2]
                cc = entrada[3] if len(entrada) > 3 else certeza
                motivo = entrada[4] if len(entrada) > 4 else None
                if valor is None:
                    continue
                claims.append(afirmacion_del_mundo(
                    claim=plantilla.format(valor=valor),
                    certeza=cc,
                    tipo=tipo,
                    df_id=str(ficha.get("df_id", df_id_txt)),
                    campos=[clave], funcion=funcion, fuentes_xml=fuentes,
                    motivo=motivo,
                ))

        # Orden estable y sin dependencias del diccionario: el mismo dataset
        # produce siempre la misma lista, en el mismo orden.
        claims.sort(key=lambda a: (a["truth_status"] == c.UNKNOWN,
                                   str(a["claim"])))

        return {
            "asunto": {
                "tipo": tipo,
                "df_id": df_id_txt,
                "certeza": certeza,
                "nombre": _texto(ficha.get("nombre")) if isinstance(ficha, dict)
                          else None,
            },
            "claims": claims,
            "provenance": procedencia(tipo, df_id_txt, [funcion], fuentes),
            "contexto": c.contexto_obligatorio(),
        }

    # --- que campos se extraen de cada tipo --------------------------
    # Son tablas explicitas, no reflexes: se lee que dato sale de donde, y
    # anadir un campo nuevo es una decision visible, no un efecto secundario.
    def _campos_figura(self, f):
        campos = _extraer(f, (
            ("nombre", "La figura se llama '{valor}'."),
            ("race", "La raza de la figura es '{valor}'."),
            ("caste", "El caste de la figura es '{valor}'."),
            ("sexo", "La figura esta registrada con sexo '{valor}'."),
            ("tipo", "El registro es de tipo '{valor}'."),
        ))
        return campos + _fechas(f, (
            ("nacimiento", "fecha de nacimiento"),
            ("muerte", "fecha de muerte"),
        ))

    def _campos_entidad(self, f):
        return _extraer(f, (
            ("nombre", "La entidad se llama '{valor}'."),
            ("race", "La raza de la entidad es '{valor}'."),
            ("tipo", "El registro es de tipo '{valor}'."),
        ))

    def _campos_sitio(self, f):
        campos = _extraer(f, (
            ("nombre", "El sitio se llama '{valor}'."),
            ("tipo", "El sitio es de tipo '{valor}'."),
            ("eventos", "El sitio tiene '{valor}' eventos registrados."),
        ))
        # Las coordenadas son el caso critico: pueden ser un asentamiento real
        # o el centinela -1,-1. El nucleo ya lo decided; aqui se respeta.
        coords = f.get("coordenadas")
        if isinstance(coords, (list, tuple)) and coords:
            txt = _texto(coords)
            if txt:
                campos.append(("coordenadas",
                               "El sitio esta en las coordenadas '{valor}'.",
                               txt))
        return campos

    def _campos_evento(self, f):
        campos = _extraer(f, (
            ("tipo", "El evento es de tipo '{valor}'."),
            ("estado", "El estado registrado del evento es '{valor}'."),
            ("subtipo", "El subtipo del evento es '{valor}'."),
        ))
        # El ano viene con enye y llega como numero. Solo se copia si esta.
        anio = f.get("año", f.get("anio")) if isinstance(f, dict) else None
        txt = _texto(anio)
        if txt is not None:
            campos.append(("año", "El evento ocurrio en el ano {valor}.", txt))
        return campos

    def _campos_artefacto(self, f):
        return _extraer(f, (
            ("nombre_item", "El objeto es '{valor}'."),
            ("tipo", "El registro es de tipo '{valor}'."),
            ("subtipo", "El subtipo del objeto es '{valor}'."),
            ("material", "El material del objeto es '{valor}'."),
        ))


# ============================================================ EXTRACTORES =====
def _extraer(ficha, tabla):
    """Convierte una tabla (clave, plantilla) en entradas con su valor."""
    if not isinstance(ficha, dict):
        return []
    salida = []
    for clave, plantilla in tabla:
        valor = _texto(ficha.get(clave))
        if valor is not None:
            salida.append((clave, plantilla, valor))
    return salida


def _fechas(ficha, pares):
    """Fechas del nucleo: si no constan, se declara el hueco. No se inventa.

    El nucleo pone `año` con enye. Se acepta tambien `anio` por si el volcado
    perdiera el acento, pero no se hace nada mas con el valor.
    """
    if not isinstance(ficha, dict):
        return []
    salida = []
    for clave, etiqueta in pares:
        dato = ficha.get(clave)
        if not isinstance(dato, dict):
            continue
        anio = dato.get("año", dato.get("anio"))
        texto = _texto(anio)
        certeza = dato.get("certainty")
        certeza = certeza if certeza in _CERTEZA_NUCLEO else c.UNKNOWN
        if texto is None:
            # Ausente NO es vivo ni es una fecha inventada: es un hueco, y el
            # nucleo ya explica por que. Se copia su motivo tal cual.
            salida.append((clave, f"La {etiqueta} no consta en los datos.",
                           "no consta", c.UNKNOWN,
                           dato.get("motivo") or
                           "el XML no registra esta fecha"))
        else:
            salida.append((clave, f"La {etiqueta} es el ano {texto}.",
                           texto, certeza, None))
    return salida


# =============================================================== IDENTIFICADORES
def _como_id(valor):
    """El nucleo indexa figuras y sitios por identificador de texto."""
    return str(valor)


def _como_id_entidad(valor):
    """Entidades, eventos y artefactos se indexan por entero.

    Un identificador que no sea un entero se devuelve tal cual: el nucleo ya
    responde con `UNKNOWN` y su motivo en vez de romperse, y repetir aqui esa
    validacion seria duplicar una proteccion que ya existe.
    """
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return valor


# ================================================== PUERTA DE DIVULGACION ===
def claims_divulgables(conocimiento):
    """Filtra lo que el jugador puede ver. Es un filtro, no un juez.

    Todo lo que sale de aqui ha pasado por `contrato_ia.puede_revelarse()`,
    que es la UNICA puerta de salida del sistema. Este filtro no decide: solo
    separa lo que ya ha sido declarado divulgable de lo que no.
    """
    if not isinstance(conocimiento, dict):
        return []
    salida = []
    for a in conocimiento.get("claims") or []:
        try:
            if c.puede_revelarse(a):
                salida.append(a)
        except Exception:          # noqa: BLE001 - un claim roto no se imprime
            continue
    return salida


def claims_para_razonar(conocimiento):
    """Lo que una IA puede usar para razonar, aunque no pueda contarlo.

    Aqui entra tambien lo prohibido: razonar con un secreto es legitimo,
    contarlo no. Por eso son dos funciones y no una.
    """
    if not isinstance(conocimiento, dict):
        return []
    salida = []
    for a in conocimiento.get("claims") or []:
        try:
            if c.puede_usarse_para_razonar(a):
                salida.append(a)
        except Exception:          # noqa: BLE001
            continue
    return salida


def preparar_respuesta_jugador(conocimiento):
    """Prepara lo que un sistema de IA puede responder al jugador.

    Es la contraparte de `claims_divulgables`, y aqui importa una cosa mas:
    **no se devuelve el dato prohibido**, ni siquiera envuelto, ni "acordate de
    que habia una veta en 112,20". Lo que no se puede revelar, no aparece.

    Lo omitido se cuenta, para que la omision sea visible y auditable, pero
    **sin el valor**: se dice cuantos y por que, nunca que.
    """
    if not isinstance(conocimiento, dict):
        return {
            "divulgable": [], "omitidos": 0, "motivos": {},
            "provenance": {}, "contexto": c.contexto_obligatorio(),
            "nota": "entrada invalida: no es un sobre de conocimiento",
        }

    permitidos = claims_divulgables(conocimiento)
    motivos = {}
    for a in conocimiento.get("claims") or []:
        if a in permitidos:
            continue
        motivo = c.violacion(a) or "no divulgable"
        motivos[motivo] = motivos.get(motivo, 0) + 1

    return {
        "asunto": conocimiento.get("asunto"),
        "divulgable": permitidos,
        "omitidos": len(conocimiento.get("claims") or []) - len(permitidos),
        "motivos": dict(sorted(motivos.items())),
        "provenance": conocimiento.get("provenance") or {},
        "contexto": conocimiento.get("contexto") or c.contexto_obligatorio(),
    }


# =============================================================== INFERENCIA ===
def registrar_inferencia(claim, evidencias, visibilidad=c.PLAYER_VISIBLE,
                         disclosure=c.ALLOWED, **extra):
    """Prepara una INFERENCIA. NO genera inferencias: solo las declara.

    Esto es una representacion, no un motor. No calcula, no razona y no decide
    nada: exige que quien la llama aporte las evidencias, porque una conclusion
    sin evidencia es justo lo que `contrato_ia` prohibe.

    Se separa de un `FACT` en `truth_status`, no en el permiso: nace `INFERENCE`,
    que es lo que impide enunciarla como hecho. `puede_revelarse()` puede
    devolver True, y aun asi `puede_afirmarse_como_hecho()` devuelve False,
    porque su verdad no es `FACT`. Se puede mencionar; no se puede afirmar.
    """
    if not isinstance(claim, str) or not claim.strip():
        raise ConocimientoNoDisponible(
            "una inferencia necesita un enunciado")
    if not isinstance(evidencias, (list, tuple)) or not evidencias:
        raise ConocimientoNoDisponible(
            "una inferencia necesita al menos una evidencia: sin ella no hay "
            "de donde salio la conclusion")
    return c.afirmacion(
        claim=claim.strip(),
        truth_status=c.INFERENCE,
        knowledge_source=c.INFERENCE,
        visibility=visibilidad,
        disclosure=disclosure,
        evidences=list(evidencias),
        **extra
    )


# ==================================================== EXTERNAL_KNOWLEDGE ====
#: Se declara el hueco, no se lo disfraza. Sin fuentes externas conectadas, la
#: unica afirmacion externa legitima es que no las hay.
EXTERNAL_PENDIENTE = ("wiki", "raws", "manuales", "documentacion")

EXTERNAL_NO_CONECTADO = (
    "EXTERNAL_KNOWLEDGE esta preparado pero desconectado: no hay ninguna fuente "
    "externa cargada. Puede explicar mecanicas, reglas y significado de "
    "objetos, pero NO puede afirmar nada sobre ESTA partida sin evidencia de "
    "WORLD_KNOWLEDGE que lo permita.",
)


def externo_pendiente(tipo, identificador, contenido, **extra):
    """Construye una afirmacion EXTERNAL. Hoy no hay ninguna fuente conectada.

    Se deja la pieza montada a proposito: cuando exista una wiki o unos raws, se
    rellena el contenido y la frontera ya esta puesta. El contrato ya prohibe
    que esto sea `FACT` sobre esta partida, y `validar()` lo rechaza.
    """
    return c.afirmacion(
        claim=contenido,
        truth_status=c.DERIVED,
        knowledge_source=c.EXTERNAL_KNOWLEDGE,
        visibility=c.EXTERNAL,
        disclosure=c.ALLOWED,
        evidences=[c.evidencia(tipo, identificador, ["contenido"],
                               "ia_conocimiento.externo_pendiente",
                               "sin_conectar")],
        **extra
    )


# ================================================================ API SIMPLE =
#: Atajos de modulo. La futura IA puede importar esto y no saber mas del nucleo:
#: ni sus rutas, ni su formato en disco, ni el nombre de sus ficheros.
_PUENTE = None


def puente():
    """Un unico Puente por proceso: cargar el indice cuesta ~2,5 s."""
    global _PUENTE
    if _PUENTE is None:
        _PUENTE = Puente()
    return _PUENTE


def obtener_conocimiento_figura(df_id):
    return puente().obtener_conocimiento_figura(df_id)


def obtener_conocimiento_entidad(df_id):
    return puente().obtener_conocimiento_entidad(df_id)


def obtener_conocimiento_sitio(df_id):
    return puente().obtener_conocimiento_sitio(df_id)


def obtener_conocimiento_evento(df_id):
    return puente().obtener_conocimiento_evento(df_id)


def obtener_conocimiento_artefacto(df_id):
    return puente().obtener_conocimiento_artefacto(df_id)