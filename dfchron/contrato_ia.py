#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Contrato para la futura IA
=============================================

LA REGLA DE ORO
---------------
    La verdad de un dato y el permiso para revelarlo son cosas diferentes.

Un dato puede ser VERDADERO y aun asi NO PODER decirse. Este modulo hace
ejecutable esa separacion: define las cuatro fuentes de conocimiento, las tres
dimensiones de cada afirmacion, y la politica que decide que se puede revelar.

LO QUE ESTE MODULO **NO** ES
----------------------------
No es una IA. No es un mock. No hay ninguna tabla de preguntas y respuestas
prefijadas. No llama a ningun modelo, ni a ninguna red, ni genera texto.

Lo que si hace es **impedir** que alguien confunda "es verdad" con "se puede
decir". Ese es el trabajo: una frontera, no un generador.

QUE NO SE TOCA
--------------
- `nucleo.py` ya declara su certeza (`FACT`/`DERIVED`/`UNKNOWN`). Este modulo
  vive POR ENCIMA y no lo modifica.
- La API y la Web siguen igual: este modulo no anade endpoints.
- No se instancia nada ni se conecta a nada: solo define y valida.

COMO SE USA
-----------
    from dfchron import contrato_ia as cia

    c = cia.afirmacion(
        claim="Existe una veta de diamantes en 112,20,45",
        truth_status=cia.FACT,
        knowledge_source=cia.WORLD_KNOWLEDGE,
        visibility=cia.PLAYER_HIDDEN,
        evidencia=[cia.evidencia("sitio", "112", ["type"])],
    )
    cia.puede_revelarse(c)        # False  <-- aqui esta toda la defensa
    cia.violacion(c)              # explica por que
"""
import json

# ============================================================ CERTEZAS ======
# Se importan del nucleo para que no haya dos definiciones de lo mismo.
# `INTERPRETATION` ya existe ahi reservada y es el equivalente de INFERENCE.
try:
    from . import config                                     # noqa: F401
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from nucleo import FACT, DERIVED, UNKNOWN, INTERPRETATION

# ============================================== FUENTES DE CONOCIMIENTO =====
PLAYER_KNOWLEDGE = "PLAYER_KNOWLEDGE"
WORLD_KNOWLEDGE = "WORLD_KNOWLEDGE"
EXTERNAL_KNOWLEDGE = "EXTERNAL_KNOWLEDGE"

#: Cuarto estado epistemologico. El nucleo lo declara pero no lo genera
#: ("no se genera en esta fase"). Aqui es el estado natural de INFERENCE.
#: Comparte valor con la constante del nucleo a proposito: son la misma idea,
#: y dos constantes distintas serian dos verdades.
INFERENCE = INTERPRETATION

#: Las cuatro fuentes, con el nombre que usa el contrato. `INFERENCE` es a la
#: vez la cuarta fuente y su propio estado: una inferencia no viene de ningun
#: sitio, se produce.
KNOWLEDGE_SOURCES = (PLAYER_KNOWLEDGE, WORLD_KNOWLEDGE, EXTERNAL_KNOWLEDGE,
                     INFERENCE)

TRUTH_STATUS = (FACT, DERIVED, UNKNOWN, INFERENCE)

#: Que fuente tiene permiso para describir el estado de ESTA partida.
#: Las otras dos no pueden: una es del jugador, la otra no es de este mundo.
FUENTES_DE_ESTADO = (PLAYER_KNOWLEDGE, WORLD_KNOWLEDGE)

# ============================================================= VISIBILIDAD ==
PLAYER_VISIBLE = "PLAYER_VISIBLE"
PLAYER_HIDDEN = "PLAYER_HIDDEN"
EXTERNAL = "EXTERNAL"
VISIBILITIES = (PLAYER_VISIBLE, PLAYER_HIDDEN, EXTERNAL)

# ============================================================ DIVULGACION ===
ALLOWED = "ALLOWED"
FORBIDDEN = "FORBIDDEN"
CONDITIONAL = "CONDITIONAL"
DISCLOSURES = (ALLOWED, FORBIDDEN, CONDITIONAL)

MOTIVO_FALTA = "falta la evidencia que lo sostenga"


# ====================================================== CONSTRUCTORES ======
def evidencia(entidad, df_id, datos_utilizados, funcion=None, fuente=None,
              state_version=None):
    """Rastro de un dato hasta el punto del dataset del que salio.

    Sin esto, una afirmacion seria "plausible" pero no auditable. La regla del
    contrato es: sin evidencia no se afirma.

    `state_version` identifica **que dataset** produjo el dato. No es un tick
    inventado: es el `dataset_id` real, que `ia_conocimiento` ya leia de
    `dataset_version.json` y que se deriva del SHA-256 del contenido, no de un
    reloj. Por eso:

      * es determinista: el mismo contenido produce siempre el mismo id;
      * cambia cuando cambia el CONTENIDO extraido, que es lo que hace falta
        para poder invalidar una evidencia vieja;
      * no es una serie temporal: el dataset no tiene reloj de juego.

    LO QUE ESTE CAMPO **NO** ES (corregido en P1.1, 2026-10-04)

    Una version anterior de este texto decia que `state_version` "cambia
    exactamente cuando cambia el mundo". **Eso es falso y P1 lo demostro con
    datos reales** (`P1_VERSIONADO_MUNDO_VIVO.md`, §20.1):

      * dos mundos con contenido identico reciben el MISMO `dataset_id`;
      * el mundo puede cambiar y el contenido extraido no, con lo que el
        `dataset_id` tampoco cambia.

    Es decir, `dataset_id` identifica CONTENIDO, y el contenido es una sombra
    del mundo, no el mundo. Por tanto:

      * `state_version == dataset_id` SIEMPRE;
      * `state_version` NO es identidad demostrada del estado vivo;
      * comparar `state_version` solo permite afirmar "mismo contenido
        extraido", nunca "mismo estado del mundo" ni "este es el estado exacto
        en el momento X".

    Para invalidar evidencia por dataset el mecanismo sigue siendo correcto y
    no se toca. Lo que no se puede es prometer una garantia de estado vivo: esa
    identificacion sigue **sin resolver** y depende de lo que P1 §19 deja
    pendiente.

    Si se omite, se deja `UNKNOWN` y la evidencia queda **explicita y
    deliberadamente no versionada**. No se rellena con el id actual a posteriori:
    eso seria afirmar que se verifico contra un mundo que no se comprobo.
    """
    return {
        "entidad": entidad,
        "df_id": str(df_id),
        "datos_utilizados": _ListaSolaLectura(datos_utilizados or []),
        "funcion": funcion,
        "fuente": fuente,
        "state_version": state_version,
    }


#: Valor que significa «esta evidencia no declara de que estado del mundo sale».
SIN_VERSION = "UNKNOWN"


def version_de_evidencia(ev):
    """La `state_version` de una evidencia, o `SIN_VERSION` si no la declara.

    Centraliza la lectura para que ninguna capa tenga que suponer que el campo
    existe: una evidencia construida antes de este campo, o a mano, se trata
    igual que una que lo declara desconocido.
    """
    if not isinstance(ev, dict):
        return SIN_VERSION
    return ev.get("state_version") or SIN_VERSION


def evidencia_es_actual(ev, version_actual):
    """¿La evidencia pertenece al estado del mundo que se esta mirando?

    Regla deliberadamente ESTRICTA: **solo es actual la que lo declara y
    coincide**. Una evidencia sin `state_version` no es «de otro mundo»: es
    **desconocida**, y una evidencia desconocida no puede sostener una afirmacion
    que se presente como actual. Es fail-closed, y es la unica lectura segura
    mientras el adaptador DF no lo facilite de forma sistematica.
    """
    if version_actual is None:
        # Sin estado del mundo con el que comparar, no se puede afirmar nada.
        return False
    return version_de_evidencia(ev) == version_actual


class ContratoInvalido(ValueError):
    """Una combinacion de dimensiones que el contrato no admite."""

    def __init__(self, errores):
        self.errores = list(errores)
        super().__init__("; ".join(self.errores))


class _Candado:
    """Abre la afirmacion durante su construccion y la vuelve a cerrar.

    Es la unica ventana por la que se puede escribir. Vive aqui y no se exporta,
    porque si el consumidor pudiera abrirla dejaria de ser una frontera.
    """

    abierto = False

    def __enter__(self):
        self._anterior = _Candado.abierto
        _Candado.abierto = True
        return self

    def __exit__(self, *_):
        _Candado.abierto = self._anterior
        return False


def _bloquear(operacion):
    """El unico error que produce una estructura de solo lectura."""
    raise ContratoInvalido([
        f"estructura de solo lectura: no se puede {operacion}. "
        "La evidencia de una afirmacion no se altera despues de "
        "construirse: si se pudiera, su procedencia seria falsificable."])


class _SolaLectura(dict):
    """Un `dict` que no se puede modificar y que sigue siendo JSON.

    Sin esto, `afirmacion["evidence"][0]["df_id"] = "999"` funcionaba: la
    procedencia de un secreto era falsificable sin dejar rastro. Bloquear solo
    el nivel superior no llegaba: los dicts y listas interiors seguían abiertos.
    """

    __slots__ = ()

    def __setitem__(self, k, v):
        _bloquear(f"asignar {k!r}")

    def __delitem__(self, k):
        _bloquear(f"borrar {k!r}")

    def update(self, *a, **k):
        _bloquear("usar update()")

    def setdefault(self, *a, **k):
        _bloquear("usar setdefault()")

    def pop(self, *a, **k):
        _bloquear("usar pop()")

    def popitem(self, *a, **k):
        _bloquear("usar popitem()")

    def clear(self):
        _bloquear("usar clear()")

    def __ior__(self, otro):
        _bloquear("usar |= (union in situ) en un dict")

    # Copiar una afirmacion es util (comparar, guardar). Sin esto, `deepcopy`
    # reintentaria escribir por `__setitem__` y reventaria. La copia sigue
    # siendo de solo lectura.
    def __copy__(self):
        nuevo = self.__class__.__new__(self.__class__)
        dict.update(nuevo, dict(self))
        return nuevo

    def __deepcopy__(self, memo):
        import copy as _c
        nuevo = self.__class__.__new__(self.__class__)
        memo[id(self)] = nuevo
        dict.update(nuevo, {k: _c.deepcopy(v, memo) for k, v in self.items()})
        return nuevo


class _ListaSolaLectura(list):
    """Una `list` que no se puede modificar y que sigue siendo JSON."""

    __slots__ = ()

    def __setitem__(self, i, v):
        _bloquear("asignar por indice")

    def __delitem__(self, i):
        _bloquear("borrar por indice")

    def append(self, v):
        _bloquear("usar append()")

    def extend(self, v):
        _bloquear("usar extend()")

    def insert(self, i, v):
        _bloquear("usar insert()")

    def remove(self, v):
        _bloquear("usar remove()")

    def pop(self, *a):
        _bloquear("usar pop()")

    def clear(self):
        _bloquear("usar clear()")

    def sort(self, *a, **k):
        _bloquear("usar sort()")

    def reverse(self):
        _bloquear("usar reverse()")

    def __ior__(self, otro):
        _bloquear("usar |= (union in situ) en una lista")

    def __copy__(self):
        nuevo = self.__class__.__new__(self.__class__)
        list.extend(nuevo, list(self))
        return nuevo

    def __deepcopy__(self, memo):
        import copy as _c
        nuevo = self.__class__.__new__(self.__class__)
        memo[id(self)] = nuevo
        list.extend(nuevo, [_c.deepcopy(v, memo) for v in self])
        return nuevo


def _congelar_evidencia(ev):
    """Deep-freeze de la evidencia: dicts y listas de solo lectura.

    Es idempotente, asi que se puede aplicar a una affirmation ya construida.
    """
    salida = []
    for e in ev or []:
        if isinstance(e, dict):
            d = dict(e)
            d["datos_utilizados"] = _ListaSolaLectura(
                d.get("datos_utilizados") or [])
            salida.append(_SolaLectura(d))
        else:
            salida.append(e)
    return _ListaSolaLectura(salida)


class Afirmacion(dict):
    """Una afirmacion con su verdad, su origen y su permiso de divulgacion.

    Es un `dict` a proposito: sale tal cual en JSON, sin conversion, para que
    quien la use no tenga que aprender una clase nueva.

    Y es de **SOLO LECTURA**. No es un detalle: sin esto, un
    `FACT` + `PLAYER_HIDDEN` + `FORBIDDEN` (una veta de diamantes con sus
    coordenadas) se convierte en `PLAYER_VISIBLE` + `ALLOWED` con dos
    asignaciones, y `puede_revelarse()` pasa a devolver `True` sin que nada lo
    decida. Comprobado, no temido: la suite de esta mision lo intenta.

    Para cambiar de categoria esta `convertir()`, que exige un motivo y deja
    escrito quien decidio y por que.
    """

    __slots__ = ()

    # --- la unica puerta de entrada --------------------------------------
    @staticmethod
    def _cerrada(operacion):
        if _Candado.abierto:
            return False
        raise ContratoInvalido([
            f"la afirmacion es de solo lectura: no se puede {operacion}. "
            "Para cambiar de categoria usa convertir(), que exige un motivo y "
            "deja constancia."])

    def __setitem__(self, k, v):
        self._cerrada(f"asignar {k!r}")
        dict.__setitem__(self, k, v)

    def __delitem__(self, k):
        self._cerrada(f"borrar {k!r}")
        dict.__delitem__(self, k)

    def update(self, *args, **kwargs):
        self._cerrada("usar update()")
        return dict.update(self, *args, **kwargs)

    def setdefault(self, *args, **kwargs):
        self._cerrada("usar setdefault()")
        return dict.setdefault(self, *args, **kwargs)

    def pop(self, *args, **kwargs):
        self._cerrada("usar pop()")
        return dict.pop(self, *args, **kwargs)

    def popitem(self, *args, **kwargs):
        self._cerrada("usar popitem()")
        return dict.popitem(self, *args, **kwargs)

    def clear(self):
        self._cerrada("usar clear()")
        return dict.clear(self)

    def __ior__(self, otro):
        self._cerrada("usar |= (union in situ)")
        return dict.__ior__(self, otro)


def afirmacion(claim, truth_status, knowledge_source, visibility,
               disclosure=ALLOWED, evidences=None, inferencia=None,
               motivo=None, **extra):
    """Construye y **valida** una afirmacion.

    Devuelve un `Afirmacion` (dict). Si la combinacion es imposible, lanza
    `ContratoInvalido` con el motivo: es preferible que falle al construir la
    afirmacion, y no cuando ya se ha escrito al jugador.
    """
    ev = [evidences] if isinstance(evidences, dict) else list(evidences or [])

    # Se arma en un dict normal y SOLO al final se sella como Afirmacion. Si se
    # construyera con `Afirmacion({...})` y se rellenara despues, habria que
    # dejar abierto el candado durante toda la construccion.
    a = {
        "claim": claim,
        "truth_status": truth_status,
        "knowledge_source": knowledge_source,
        "visibility": visibility,
        "disclosure": disclosure,
        "evidence": _congelar_evidencia(ev),
        "inference": knowledge_source == INFERENCE if inferencia is None
                      else bool(inferencia),
    }
    if motivo:
        a["motivo"] = motivo
    a.update(extra)

    errores = validar(a)
    if errores:
        raise ContratoInvalido(errores)
    with _Candado():
        return Afirmacion(a)


# ============================================================ VALIDACION =====
def validar(a):
    """Devuelve la lista de problemas. Vacia = afirmacion valida.

    No lanza: quien quiera un `raise` que use `afirmacion()`.

    Se buscan los errores de PRINCIPIO, no los de estilo: combinaciones que
    no pueden existir aunque se afirmen con total confianza.

    No lanza nunca, ni siquiera si le pasan algo que no es una afirmacion: un
    `None` o una cadena tienen que devolver un problema, no un `AttributeError`.
    """
    e = []

    if not isinstance(a, dict):
        return [f"no es una afirmacion: {type(a).__name__}"]

    # --- valores fuera del conjunto cerrado ------------------------------
    if a.get("truth_status") not in TRUTH_STATUS:
        e.append(f"truth_status invalido: {a.get('truth_status')!r}")
    if a.get("knowledge_source") not in KNOWLEDGE_SOURCES:
        e.append(f"knowledge_source invalido: {a.get('knowledge_source')!r}")
    if a.get("visibility") not in VISIBILITIES:
        e.append(f"visibility invalida: {a.get('visibility')!r}")
    if a.get("disclosure") not in DISCLOSURES:
        e.append(f"disclosure invalida: {a.get('disclosure')!r}")

    # --- combinaciones imposiblemente contradictorias ---------------------
    ks, vis = a.get("knowledge_source"), a.get("visibility")
    ts, disc = a.get("truth_status"), a.get("disclosure")

    # 1. Lo externo no es un estado del mundo de esta partida.
    if ks == EXTERNAL_KNOWLEDGE and vis != EXTERNAL:
        e.append("EXTERNAL_KNOWLEDGE solo puede tener visibility EXTERNAL: "
                 "no describe esta partida")
    # 2. Lo externo no puede ser un HECHO de ESTE mundo. Es la confusion que
    #    mas dano haria: decir "tu fortaleza tiene 37 goblins" citando la wiki.
    if ks == EXTERNAL_KNOWLEDGE and ts == FACT:
        e.append("EXTERNAL_KNOWLEDGE no puede ser FACT sobre esta partida: "
                 "eso seria afirmar como verdad algo que no viene del mundo")
    # 3. Una inferencia es por definicion no-FACT.
    if ks == INFERENCE and ts == FACT:
        e.append("INFERENCE no puede ser FACT: una conclusion no es una fuente")
    # 3-bis. Y la regla 1 es BIDIRECCIONAL. `visibility=EXTERNAL` significa
    #       "esto no describe esta partida", asi que solo lo externo puede
    #       llevarla. Sin esta regla, `visibility=EXTERNAL` esquivaba la rama
    #       `PLAYER_HIDDEN` de `puede_revelarse()`: un secreto reconstruido
    #       como WORLD_KNOWLEDGE+FACT+EXTERNAL+ALLOWED pasaba de no-divulgable
    #       a AFIRMABLE. Cerrado por auditoria (§3 del contrato de I/O).
    if vis == EXTERNAL and ks != EXTERNAL_KNOWLEDGE:
        e.append("EXTERNAL_KNOWLEDGE y visibility EXTERNAL son la misma cosa: "
                 "solo lo externo puede declarar que no describe esta partida")
    # 4. Lo que el jugador no ha descubierto no puede ser visible para el.
    if vis == PLAYER_VISIBLE and ks == WORLD_KNOWLEDGE and a.get("no_descubierto"):
        e.append("WORLD_KNOWLEDGE no descubierto no puede ser PLAYER_VISIBLE")
    # 5. No se puede estar en ALLOWED y FORBIDDEN a la vez.
    if a.get("disclosure_alias") == ALLOWED and disc == FORBIDDEN:
        e.append("disclosure contradictoria: ALLOWED y FORBIDDEN a la vez")

    # --- evidencia obligatoria -------------------------------------------
    if not a.get("evidence"):
        # Sin evidencia solo se admite UNKNOWN, y solo si el propio dato lo dice.
        if ts != UNKNOWN:
            e.append("sin evidencia: una afirmacion debe poder rastrearse "
                     "hasta una fuente")
        elif a.get("motivo") is None:
            e.append("UNKNOWN sin evidencia necesita un motivo que lo explique")
    else:
        for ev in a["evidence"]:
            if not isinstance(ev, dict) or not ev.get("df_id"):
                e.append("evidencia incompleta: falta df_id")
                break
            # Un hecho de ESTA partida necesita un rastro de ESTA partida.
            if ks in FUENTES_DE_ESTADO and not ev.get("funcion"):
                e.append("evidencia incompleta: falta la funcion del nucleo "
                         "que produjo el dato")
                break

    return e


# ==================================================== POLITICA DE REVELADO ==
def puede_revelarse(a):
    """¿Esta afirmacion puede mostrarse al jugador tal cual?

    Devuelve True/False. Es la UNICA puerta de salida del sistema, y por eso
    es conservadora: ante cualquier duda, False.

    Este es el corazon del contrato. Si aqui se comprobara solo el
    `truth_status`, un `FACT` de `WORLD_KNOWLEDGE` pasaria: y eso es
    justamente el error que la mision quiere impedir.
    """
    if validar(a):
        return False                      # si el contrato no la valida, no sale

    if a["disclosure"] == FORBIDDEN:
        return False

    ts, vis, ks = a["truth_status"], a["visibility"], a["knowledge_source"]

    # El nucleo ya clasifico; no lo pasamos por alto ni lo degradamos.
    if ts == UNKNOWN:
        # UNKNOWN puede mostrarse COMO UNKNOWN ("no consta"), nunca como hecho.
        return False

    if ts == INFERENCE:
        # Una inferencia puede mostrarse, pero nunca como afirmacion de hecho.
        return a["disclosure"] == ALLOWED and vis == PLAYER_VISIBLE

    if ks == EXTERNAL_KNOWLEDGE:
        return a["disclosure"] == ALLOWED

    # WORLD_KNOWLEDGE y PLAYER_KNOWLEDGE con certidumbre dura (FACT/DERIVED):
    if vis == PLAYER_HIDDEN:
        # Aqui esta la regla central: verdadero y, aun asi, no revelable.
        # Solo se abre con CONDITIONAL y una pista que el propio sistema autorice.
        return (a["disclosure"] == CONDITIONAL
                and a.get("pista_permitida") is True)

    return a["disclosure"] == ALLOWED


def puede_usarse_para_razonar(a):
    """¿Puede una IA usar este dato para razonar por dentro, aunque no revelarlo?

    Es MAS permisivo que `puede_revelarse` y **no lo reemplaza**: son dos
    preguntas distintas y responderlas con la misma funcion seria el error.

      * Razonar con un secreto es legitimo. El modelo puede encadenar hechos
        ocultos para llegar a una conclusion que si se puede contar.
      * Contar ese secreto no lo es. De ahi las dos funciones.

    Lo que NO permite:
      - usar una afirmacion que el contrato no valida;
      - usar `EXTERNAL_KNOWLEDGE` para describir ESTA partida;
      - tratar `UNKNOWN` como si fuera un hecho. `UNKNOWN` si entra, porque el
        modelo tiene que ver los huecos; por eso `puede_revelarse()` lo
        bloquea. Entra como hueco, nunca como verdad.
    """
    if validar(a):
        return False
    if a["knowledge_source"] == EXTERNAL_KNOWLEDGE:
        return False
    return True


def puede_afirmarse_como_hecho(a):
    """¿Puede enunciarse sin el proviso 'probablemente', 'parece que'...?

    Es mas estricto que `puede_revelarse`, y hay tres motivos para que lo sea:

      1. Una inferencia puede mostrarse, pero no como hecho.
      2. Un `CONDITIONAL` sigue siendo condicional: autorizada a mostrarse, no
         a enunciarse. Es la diferencia entre "puedes contar que hay una pista"
         y "afirmas que hay una veta".
      3. Un dato que el jugador no ha descubierto no puede ser un hecho suyo.

    Sin el punto 2, `CONDITIONAL` + `pista_permitida` devolvia True por ser
    `FACT`, y una pista se convertia en una afirmacion tajante. Lo que se
    autoriza es la MENCION, no la AFIRMACION.
    """
    if not puede_revelarse(a):
        return False
    if a["truth_status"] != FACT:
        return False
    if a["disclosure"] == CONDITIONAL:
        return False
    return True


def violacion(a):
    """Explica por que una afirmacion NO puede revelarse, o None si puede.

    Devuelve texto pensado para diagnostico, no para mostrar al jugador: no
    contiene rutas, ni tracebacks, ni informacion del sistema de ficheros.
    """
    problemas = validar(a)
    if problemas:
        return "contrato invalido: " + "; ".join(problemas)
    if puede_revelarse(a):
        return None
    if a["disclosure"] == FORBIDDEN:
        return "disclosure FORBIDDEN"
    if a["truth_status"] == UNKNOWN:
        return "UNKNOWN no es afirmable"
    if a["truth_status"] == INFERENCE:
        return "INFERENCE no es un hecho: solo como posibilidad"
    if a["visibility"] == PLAYER_HIDDEN:
        return "PLAYER_HIDDEN: verdadero pero no descubierto por el jugador"
    return "no divulgable"


# ============================== CONVERSIONES PROHIBIDAS (§6 de la mision) ==
#: Operaciones permitidas y su justificacion. Cada una queda registrada en la
#: afirmacion resultante: si alguien revelo algo, se ve quien y por que.
OPERACIONES = {
    "revelar": ("visibility", PLAYER_VISIBLE,
                "el jugador ha descubierto el dato"),
    "ocultar": ("visibility", PLAYER_HIDDEN,
                "el jugador ya no lo conoce"),
    "derivar": ("truth_status", DERIVED,
                "el dato es un calculo, no una lectura"),
    "confirmar": ("truth_status", FACT,
                  "el derivado tiene respaldo directo en la fuente"),
}


def convertir(a, operacion, motivo=None):
    """UNICA puerta para cambiar de categoria. Cada operacion, justificada.

    Sin esto, un `WORLD_KNOWLEDGE` acaba siendo `PLAYER_KNOWLEDGE` con un
    `.replace()` en algun sitio, y nadie se entera. Con esto, queda escrito que
    alguien lo decidio, y por que.

    `revelar` y `ocultar` solo tienen sentido sobre informacion que describe el
    estado del mundo. Una afirmacion externa o una inferencia no "se revelan":
    no son cosas que el jugador pueda descubrir.
    """
    if operacion not in OPERACIONES:
        raise ContratoInvalido(
            [f"operacion no permitida: {operacion!r}. "
             f"Validas: {sorted(OPERACIONES)}"])
    campo, destino, porque = OPERACIONES[operacion]

    if campo == "visibility" and a["knowledge_source"] not in FUENTES_DE_ESTADO:
        raise ContratoInvalido([
            f"{a['knowledge_source']} no puede pasar por '{operacion}': "
            f"solo el estado del mundo se revela u oculta"])

    # Copia PLANA, no `Afirmacion(a)`: la nueva afirmacion no puede construirse
    # encima de la anterior como punto de partida, porque esa esta cerrada.
    nueva = dict(a)
    nueva["evidence"] = _congelar_evidencia(a.get("evidence"))
    nueva[campo] = destino
    nueva["conversion"] = {"operacion": operacion, "campo": campo,
                           "desde": a[campo], "hacia": destino,
                           "motivo": motivo or porque}
    # `no_descubierto` deja de tener sentido en cuanto el jugador lo descubre.
    if operacion == "revelar":
        nueva["no_descubierto"] = False
        if nueva["disclosure"] == FORBIDDEN:
            # Descubrir el dato es justamente lo que autoriza a decirlo. Si se
            # dejara en FORBIDDEN, `revelar` no revelaria nada y habria dos
            # verdades sobre el mismo dato: "lo sabe" y "no se lo puedes decir".
            nueva["disclosure"] = ALLOWED
            nueva["conversion"]["tambien"] = {
                "campo": "disclosure", "desde": FORBIDDEN, "hacia": ALLOWED,
                "motivo": "descubrirlo es lo que autoriza a decirlo"}

    problemas = validar(nueva)
    if problemas:
        raise ContratoInvalido(problemas)
    with _Candado():
        return Afirmacion(nueva)


# ============================================== PERSISTENCIA Y LECTURA =====
def a_json(a, sangria=1):
    """La afirmacion tal cual se entregaria al modelo. Sin campos anadidos."""
    return json.dumps(a, ensure_ascii=False, indent=sangria)


def desde_json(texto):
    """Lee una afirmacion serializada y la valida. Falla si no es valida."""
    a = json.loads(texto) if isinstance(texto, str) else texto
    if isinstance(a, dict):
        # Lo que viene de un JSON externo es mutable: se congela antes de
        # entregarlo, o la frontera se perderia justo al cruzar el proceso.
        a = dict(a)
        a["evidence"] = _congelar_evidencia(a.get("evidence"))
    problemas = validar(a)
    if problemas:
        raise ContratoInvalido(problemas)
    with _Candado():
        return Afirmacion(a)


# ================================== CONTEXTO FIJO PARA CUALQUIER CONSULTA ====
#: Limitaciones reales y medidas del dataset actual. Deben acompanar SIEMPRE a
#: cualquier consulta: sin ellas, un modelo rellena los huecos por inercia, que
#: es el fallo mas probable y el mas dificil de detectar porque suena plausible.
LIMITACIONES = (
    "Solo hay datos de los anos 1 a 100.",
    "17.881 de 57.215 eventos (31 %) no tienen participantes.",
    "6.734 de 11.144 figuras no tienen fecha de muerte: AUSENTE NO ES VIVA.",
    "9.930 eventos tienen coordenadas centinela -1,-1: no tienen lugar real.",
    "Las 13.192 relaciones no tienen evento asociado: no las atribuyas a uno.",
    "Hay 1.925 conflictos entre las dos fuentes, sin resolver.",
    "No existe tabla de guerras en los datos.",
    "UNKNOWN es una respuesta valida y preferible a suponer.",
    "Un dato FACT puede ser PLAYER_HIDDEN: verdad no es permiso para revelar.",
)

REGLA = ("La verdad de un dato y el permiso para revelarlo son cosas "
         "diferentes.")


def contexto_obligatorio():
    """Lo que SIEMPRE acompana a una consulta, sin excepcion.

    Se entrega como dato, no como recomendacion: quien use el contrato lo
    recibe ya montado y no puede olvidarse de pedirlo.
    """
    return {
        "regla": REGLA,
        "limitaciones": list(LIMITACIONES),
        "certezas": list(TRUTH_STATUS),
        "fuentes": list(KNOWLEDGE_SOURCES),
        "visibilidades": list(VISIBILITIES),
        "divulgaciones": list(DISCLOSURES),
        "exige_evidencia": True,
        "unknown_es_respuesta_valida": True,
    }


# ================================================= EJEMPLOS DOCUMENTADOS ====
#: Los cinco casos de la mision (§11), ejecutables. Sirven de documentacion
#: que no puede quedarse obsoleta: si el contrato cambia, estas pruebas cambian
#: con el, y fallan.
def ejemplo_visible():
    """Caso A: el jugador conoce a Galka Shafttop. Se puede decir."""
    return afirmacion(
        claim="El jugador conoce a Galka Shafttop.",
        truth_status=FACT,
        knowledge_source=PLAYER_KNOWLEDGE,
        visibility=PLAYER_VISIBLE,
        disclosure=ALLOWED,
        evidences=[evidencia("figura", "712", ["name", "race"],
                             "nucleo.Archivo.ficha_figura", "legends.xml")],
    )


def ejemplo_secreto():
    """Caso B: una veta de diamantes. Es verdad y NO se puede revelar."""
    return afirmacion(
        claim="Existe una veta de diamantes en 112,20,45.",
        truth_status=FACT,
        knowledge_source=WORLD_KNOWLEDGE,
        visibility=PLAYER_HIDDEN,
        disclosure=FORBIDDEN,
        evidences=[evidencia("sitio", "112", ["type"],
                             "nucleo.Archivo.ficha_sitio", "legends.xml")],
        no_descubierto=True,
    )


def ejemplo_externo():
    """Caso C: la wiki explica una mecanica. Vale, pero no es este mundo."""
    return afirmacion(
        claim="Las fortalezas goblin pueden contener determinados enemigos.",
        truth_status=DERIVED,
        knowledge_source=EXTERNAL_KNOWLEDGE,
        visibility=EXTERNAL,
        disclosure=ALLOWED,
        evidences=[evidencia("regla_juego", "wiki:goblin_fortress",
                             ["tipo", "contenido"], "documentacion", "wiki")],
    )


def ejemplo_inferencia():
    """Caso D: una conclusion. Se puede decir, pero como posibilidad."""
    return afirmacion(
        claim="Probablemente convenga prepararse para enemigos.",
        truth_status=INFERENCE,
        knowledge_source=INFERENCE,
        visibility=PLAYER_VISIBLE,
        disclosure=ALLOWED,
        evidences=[evidencia("razonamiento", "fortaleza-goblin-norte",
                             ["site.type"], "nucleo.Archivo.ficha_sitio")],
    )


def ejemplo_unknown():
    """UNKNOWN sigue siendo una respuesta valida. No se rellena."""
    return afirmacion(
        claim="No consta la fecha de muerte de la figura.",
        truth_status=UNKNOWN,
        knowledge_source=WORLD_KNOWLEDGE,
        visibility=PLAYER_VISIBLE,
        disclosure=ALLOWED,
        evidences=[],
        motivo="death_year ausente: AUSENTE NO ES VIVA",
    )
# CONTINUA_CONTRATO_IA */