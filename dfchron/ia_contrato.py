#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: CONTRATO DE ENTRADA Y SALIDA de la IA
=======================================================

Este modulo fija COMO habla la futura IA con el sistema, en las dos
direcciones. No la implementa: no hay cliente, ni SDK, ni endpoint, ni prompt,
ni llamada a la red. Es un contrato, y se cumple o se viola de forma detectable.

LA REGLA
--------
    La futura IA es una CONSUMIDORA de esta arquitectura, nunca su autoridad.

El sistema decide que es verdad, que es visible y que se puede revelar, ANTES
de que el modelo vea nada. El modelo redacta. La salida se vuelve a validar. Si
algo no cuadra, no llega al jugador.

    SABER   != UTILIZAR   != REVELAR
    RAZONAR != AFIRMAR    != REVELAR

EL MODELO NO ES LA AUTORIDAD SOBRE
---------------------------------
    verdad | visibilidad | divulgacion | procedencia | permisos

Y hay una consecuencia que se decide aqui y que es la mas importante del
modulo: **el modelo NUNCA recibe un dato FORBIDDEN.** No "no debe usarlo":
no lo recibe. Mandarle un secreto a un proveedor externo ya es divulgarlo. Por
eso FORBIDDEN no aparece en ningun contexto de salida al modelo, ni en modo
razonamiento ni en modo respuesta.

Que queda entonces para razonar con lo oculto? Lo determinista:
`ia_conocimiento.py` razona sobre el estado completo y produce afirmaciones ya
etiquetadas. El modelo recibe el resultado etiquetado, no el secreto.

QUE HAY AQUI
------------
    * `ContextoIA`    - el objeto de ENTRADA. Que puede leer el modelo.
    * `RespuestaIA`   - el objeto de SALIDA. Que devuelve el modelo.
    * `validar_salida()` - la puerta. FAIL CLOSED.
    * `deteccion_fuga()`  - el esqueleto del ataque por canal indirecto.

DETERMINISMO
------------
Sin relojes, sin azar, sin UUID. Misma entrada, mismo contexto, mismo
veredicto, byte a byte.

Ejecutar:  python dfchron/pruebas/probar_contrato_io.py
"""
import json
import os
import re
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from dfchron import contrato_ia as c           # noqa: E402
from dfchron import ia_verificacion as iv     # noqa: E402
from dfchron import ia_estructura as ie       # noqa: E402

# ================================================== 1. IDENTIDAD ===========
#: El agente que pregunta. Hoy solo existe uno, pero el contrato no esta
#: cerrado a mas: `agente` viaja en la consulta y la validacion comprueba que
#: sea conocido. Anadir DWARF o GOBLIN es anadir una constante y su estado.
AGENTE_JUGADOR = "PLAYER"
AGENTES = (AGENTE_JUGADOR,)

#: Un agente no tiene por que tener el mismo permiso que otro para el mismo
#: dato. Eso NO se resuelve aqui: se deja la puerta, no se responde. El supuesto
#: actual se escribe explicitamente, y por eso es cambiable:
#:
#:     SUPUESTO ACTUAL: el permiso de una afirmacion no depende del agente.
#:
#: Es una decision heredada, no de esta mision. Abrirla exigiria una dimension
#: nueva (`knowledge_owner`), que el mandato de esta prohibe inventar.

# ==================================================== 2. MODOS ============
#: Que se entrega al modelo y para que. No es una preferencia de estilo: es lo
#: que decide cuanto puede filtrar el sistema.
#:
#:   RAZONAMIENTO -> lo que puede leer para FORMULAR la respuesta. No implica
#:                   permiso de decirlo: el modelo puede "saber" algo que al
#:                   jugador no se le dice, y aun asi no debe decirlo.
#:   RESPUESTA    -> lo que puede DECIRSE. Subconjunto estricto del anterior.
MODOS = ("razonamiento", "respuesta")

MODO_RAZONAMIENTO = MODOS[0]
MODO_RESPUESTA = MODOS[1]

SCHEMA_VERSION = "io-1"


class _Candado:
    """Replica el candado del contrato para sellar el contexto de solo lectura."""

    def __init__(self):
        self._c = c._Candado()

    def __enter__(self):
        return self._c.__enter__()

    def __exit__(self, *a):
        return self._c.__exit__(*a)


# ============================== 3. EL OBJETO DE ENTRADA ===================
class ContextoIA(dict):
    """Lo que el modelo recibe. Estructurado, no un prompt.

    Es un `dict` por la misma razon que `Afirmacion`: sale tal cual en JSON.

    **Y es de SOLO LECTURA**, por el mismo motivo: si el contexto se pudiera
    reescribir despues, bastaria cambiar un `disclosure` para convertir un
    secreto en contexto, y la politica de divulgacion seria decorativa.

    Lo que lleva, y por que:

    | clave       | por que esta                              |
    |-------------|-------------------------------------------|
    | `schema`    | version del contrato, para no ambiguedad  |
    | `agente`    | quien pregunta                            |
    | `modo`      | razonamiento o respuesta                  |
    | `pregunta`  | la consulta en lenguaje natural            |
    | `claims`    | unidades semanticas con su procedencia    |
    | `contexto`  | limitaciones fijas: nunca se olvidan      |

    Lo que **NO** lleva, y es lo mas importante:

    * Ningun dato FORBIDDEN. Ni en modo razonamiento.
    * Ningun campo duplicado por derivacion: no hay `divulgable`, ni
      `es_secreto`. Se deducen de `disclosure` + `visibility`, que son la
      fuente unica de verdad. Un campo mas seria una segunda verdad, capaz de
      contradecir a la primera.
    * Ninguna tabla interna, ningun JSONL, ninguna ruta de fichero.
    """

    __slots__ = ()

    def __setitem__(self, k, v):
        c.Afirmacion._cerrada("modificar el contexto de entrada")
        dict.__setitem__(self, k, v)

    def __delitem__(self, k):
        c.Afirmacion._cerrada("borrar del contexto de entrada")
        dict.__delitem__(self, k)

    def update(self, *a, **k):
        c.Afirmacion._cerrada("modificar el contexto de entrada")
        return dict.update(self, *a, **k)

    def pop(self, *a, **k):
        c.Afirmacion._cerrada("modificar el contexto de entrada")
        return dict.pop(self, *a, **k)

    def clear(self):
        c.Afirmacion._cerrada("modificar el contexto de entrada")
        return dict.clear(self)

    def setdefault(self, *a, **k):
        c.Afirmacion._cerrada("modificar el contexto de entrada")
        return dict.setdefault(self, *a, **k)


# ================================== 4. LA PUERTA DE ENTRADA ================
def entra_en_contexto(a, modo):
    """¿Esta afirmación puede viajar al modelo en este modo?

    Es la UNICA puerta hacia el modelo. No es `puede_revelarse()`: esa
    responde a "al jugador", y aqui la pregunta es "al proveedor externo", que
    es un destinatario distinto y mas hostil. No es la misma pregunta.
    """
    if a.get("disclosure") == c.FORBIDDEN:
        # Ni para razonar. Mandarle un secreto a un proveedor externo ya es
        # divulgarlo. El razonamiento sobre lo oculto lo hace el sistema, que
        # es determinista; no el modelo, que no lo es.
        return False
    if a.get("knowledge_source") == c.EXTERNAL_KNOWLEDGE:
        return True          # mecanicas y reglas: se pueden explicar
    if modo == MODO_RESPUESTA:
        return c.puede_revelarse(a)
    # MODO_RAZONAMIENTO: puede leer mas, pero no secretos.
    if a.get("truth_status") == c.UNKNOWN:
        # "No consta" es informacion, y es lo que el jugador necesita.
        return True
    if a.get("visibility") == c.PLAYER_HIDDEN:
        # Solo una pista que el propio sistema autorizo a mencionar.
        return (a.get("disclosure") == c.CONDITIONAL
                and a.get("pista_permitida") is True)
    return a.get("disclosure") == c.ALLOWED


def _claim_de_entrada(a, indice):
    """La forma que ve el modelo. Copia minima, sin duplicar informacion.

    Se omiten los campos internos de politica (`no_descubierto`,
    `pista_permitida`, `conversion`): son de la casa, no del modelo, y no puede
    actuar sobre ellos. Se conservan los cuatro campos normativos y la
    evidencia, que es lo que da trazabilidad.
    """
    ev = []
    for e in (a.get("evidence") or []):
        copia = {"entidad": e.get("entidad"),
                 "df_id": e.get("df_id"),
                 "datos_utilizados": list(e.get("datos_utilizados") or []),
                 "funcion": e.get("funcion"),
                 "fuente": e.get("fuente")}
        # El estado del mundo viaja con la evidencia a proposito: sin el, quien
        # lee el contexto no puede distinguir «esto se comprobo aqui» de «esto
        # se comprobo en otra version». No concede ninguna capacidad al modelo,
        # que no puede escribirlo, pero si deja la afirmacion auditable.
        if e.get("state_version") is not None:
            copia["state_version"] = e["state_version"]
        ev.append(copia)
    claim = {
        "ref": "c%d" % indice,
        "claim": a.get("claim"),
        "truth_status": a.get("truth_status"),
        "knowledge_source": a.get("knowledge_source"),
        "visibility": a.get("visibility"),
        "disclosure": a.get("disclosure"),
        "evidence": ev,
    }
    if a.get("motivo"):
        claim["motivo"] = a["motivo"]
    return claim


def contexto(pregunta, afirmaciones, modo=MODO_RAZONAMIENTO,
              agente=AGENTE_JUGADOR, **extra):
    """Construye el contexto de entrada, YA FILTRADO por la politica.

    El filtrado ocurre aqui, no despues: quien llama no puede saltarselo. No
    hay forma de construir un contexto con secretos dentro.

    Que entra, por `modo`:

    | afirmacion                                  | razonamiento | respuesta |
    |---------------------------------------------|--------------|-----------|
    | `disclosure=FORBIDDEN`                      | **NO**       | **NO**    |
    | `EXTERNAL_KNOWLEDGE`                        | si           | si        |
    | `UNKNOWN`                                   | si           | **NO**    |
    | `PLAYER_HIDDEN` sin `pista_permitida`       | **NO**       | **NO**    |
    | `PLAYER_HIDDEN` + `CONDITIONAL` + pista     | si           | si        |
    | visible + `ALLOWED`                         | si           | si        |
    | `INFERENCE` visible + `ALLOWED`             | si           | si        |

    Minimizacion: el sistema no incluye `WORLD_KNOWLEDGE` por sistema. Si el
    jugador ya conoce el dato, basta el claim de `PLAYER_KNOWLEDGE`. Cada
    afirmacion que sobra es una via de mas por la que colarse un secreto.
    """
    if agente not in AGENTES:
        raise c.ContratoInvalido([
            f"agente desconocido: {agente!r}. Conocidos: {list(AGENTES)}"])
    if modo not in MODOS:
        raise c.ContratoInvalido([
            f"modo desconocido: {modo!r}. Conocidos: {list(MODOS)}"])
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise c.ContratoInvalido(["la pregunta es obligatoria"])

    admitidas = [a for a in (afirmaciones or []) if entra_en_contexto(a, modo)]
    ctx = {
        "schema": SCHEMA_VERSION,
        "agente": agente,
        "modo": modo,
        "pregunta": pregunta.strip(),
        "claims": [_claim_de_entrada(a, i) for i, a in enumerate(admitidas)],
        "contexto": c.contexto_obligatorio(),
    }
    ctx.update(extra)
    with _Candado():
        return ContextoIA(ctx)


def claims_de_contexto(ctx):
    """Los claims del contexto, reconstruidos como afirmaciones reales.

    Se usa para validar la salida: el modelo solo puede apoyarse en lo que
    recibio, y eso se comprueba contra estas afirmaciones de verdad, no contra
    lo que el modelo afirma haber tenido.
    """
    return [c.desde_json(c.a_json(cl)) for cl in ctx.get("claims") or []]


# ================================ 5. TIPOS DE SALIDA ======================
#: Que puede producir la IA. Son TIPOS DE CLAIM DE SALIDA, no otra dimension:
#: no sustituyen a `truth_status`, lo RESPETAN. Un claim de salida declara que
#: es, y la validacion comprueba que sea compatible con el `truth_status` de la
#: afirmacion en la que se apoya. Si no encaja, no pasa.
#:
#: Decidido explicitamente: NO hay "tipos de respuesta" aparte. La respuesta al
#: jugador es una cosa; lo que la sustenta son claims tipados.
FACT = "FACT"
DERIVED = "DERIVED"
INTERPRETATION = "INTERPRETATION"
ADVICE = "ADVICE"
UNKNOWN = "UNKNOWN"
NON_DISCLOSURE = "NON_DISCLOSURE"
MECHANIC_EXPLANATION = "MECHANIC_EXPLANATION"

TIPOS_SALIDA = (FACT, DERIVED, INTERPRETATION, ADVICE, UNKNOWN,
                NON_DISCLOSURE, MECHANIC_EXPLANATION)

#: `NON_DISCLOSURE` no necesita apoyo: su propio motivo ES el contenido.
#: Decir "esto lo se pero no te lo digo" no afirma nada del mundo.
TIPOS_SIN_APOYO = (NON_DISCLOSURE,)

#: Un consejo no puede colarse apoyandose solo en un hecho: si solo hay
#: hechos, hay una respuesta, no un consejo.
TIPOS_QUE_EXIGEN_INFERENCIA = (ADVICE, INTERPRETATION)


class RespuestaIA(dict):
    """Lo que el modelo devuelve. Estructurado, nunca texto suelto.

    Que el modelo devuelva texto libre es lo que hace imposible auditarlo.
    Aqui cada afirmacion lleva su tipo y sus apoyos, y ambos se comprueban.

    **Y el `answer` NO es la entrega.** Antes lo era, y al medir se vio que era
    una via de fuga abierta: seis vectores (paramfrasis, referencia espacial,
    sustraccion, distancia, nombre inventado y consejo filtrador) llegaban al
    jugador por aqui. Ahora `answer` es lo que el modelo PROPONE, y el texto que
    el jugador lee lo compone el sistema con `ia_frontera.componer()`. El campo
    sobrevive por auditoria (`answer_del_modelo`), no por confianza.

    | clave      | que obliga al modelo                         |
    |------------|----------------------------------------------|
    | `answer`   | su propuesta de redaccion; no se entrega      |
    | `claims`   | la estructura real; de aqui sale el texto    |

    El modelo elige QUE afirmaciones autorizadas se dicen y con que TIPO. Las
    palabras las pone el sistema. Por eso el sistema no necesita ser "fiel" al
    `answer`: no hay nada que el modelo pueda desviar.
    """

    __slots__ = ()

    def __setitem__(self, k, v):
        c.Afirmacion._cerrada("modificar la respuesta de salida")
        dict.__setitem__(self, k, v)

    def __delitem__(self, k):
        c.Afirmacion._cerrada("borrar de la respuesta de salida")
        dict.__delitem__(self, k)

    def update(self, *a, **k):
        c.Afirmacion._cerrada("modificar la respuesta de salida")
        return dict.update(self, *a, **k)


def claim_de_salida(texto, tipo, soporte=None, motivo=None):
    """Un claim de salida. Falla fuerte si le falta lo obligatorio."""
    if tipo not in TIPOS_SALIDA:
        raise c.ContratoInvalido([
            f"tipo de salida desconocido: {tipo!r}. "
            f"Conocidos: {list(TIPOS_SALIDA)}"])
    if not isinstance(texto, str) or not texto.strip():
        raise c.ContratoInvalido(["todo claim necesita texto"])
    if tipo not in TIPOS_SIN_APOYO and not soporte:
        raise c.ContratoInvalido([
            f"un claim de tipo {tipo} necesita al menos un apoyo: sin soporte "
            f"seria una afirmacion sin procedencia"])
    if tipo == NON_DISCLOSURE and not motivo:
        raise c.ContratoInvalido([
            "NON_DISCLOSURE necesita un motivo: 'no te lo digo' sin razon no "
            "es una respuesta, es un fallo"])
    d = {"texto": texto.strip(), "tipo": tipo,
         "soporte": sorted(set(soporte or []))}
    if motivo:
        d["motivo"] = motivo
    return d


def respuesta(answer, claims, confident=None):
    """Construye la respuesta de salida. No valida: validar es otro paso.

    Se construye aparte de la validacion a proposito. Si construir validara, no
    se podria probar el caso "el modelo devuelve algo invalido", que es justo
    el que importa.
    """
    if claims is None:
        claims = []
    if not isinstance(claims, (list, tuple)):
        raise c.ContratoInvalido(["claims debe ser una lista"])
    if not isinstance(claims, list):
        claims = list(claims)
    d = {"answer": answer, "claims": claims}
    if confident is not None:
        d["confidence"] = confident
    return RespuestaIA(d)


# ================================ 6. LA VALIDACION =======================
class Veredicto(dict):
    """El resultado de validar. Nunca un booleano suelto.

    | clave              | que significa                          |
    |--------------------|----------------------------------------|
    | `puede_entregarse` | si, el jugador puede leerlo            |
    | `errores`          | por que no, si no puede                |
    | `claims_ok`        | cuantos claims han pasado              |
    | `claims_rechazados`| los que no, con su motivo              |

    `puede_entregarse = False` es FAIL CLOSED: ante cualquier duda, no se
    entrega. No hay modo de exceptuar un error de seguridad.
    """

    __slots__ = ()

    @property
    def entregable(self):
        return bool(self.get("puede_entregarse"))

    def __bool__(self):
        return bool(self.get("puede_entregarse"))


def _fallo(errores, rechazados=None, n_ok=0):
    return Veredicto({"puede_entregarse": False, "errores": list(errores),
                      "claims_ok": n_ok,
                      "claims_rechazados": list(rechazados or [])})


def validar_salida(salida, ctx, rec=None):
    """La puerta. Comprueba la salida del modelo contra el contexto.

    Que comprueba, en este orden:

    1. **Estructura**: hay `claims`, y cada uno tiene tipo valido y texto.
    2. **Procedencia**: todo apoyo apunta a un `ref` que el modelo recibio de
       verdad. Un apoyo inventado es una afirmacion sin origen.
    3. **Verdad**: el `tipo` declarado es compatible con el `truth_status` de
       lo que apoya. Un `FACT` necesita un `FACT`.
    4. **Divulgacion**: lo que apoya puede revelarse. Un claim de salida nunca
       es mas permisivo que su apoyo.
    5. **Secretos indirectos**: `deteccion_fuga()` sobre el texto.

    NOTA HONESTA: la version anterior de este docstring listaba un paso 6,
    "Consistencia: el `answer` no afirma mas que los `claims`", que **no estaba
    implementado**. Documentar una comprobacion inexistente da una garantia falsa,
    que es peor que no documentarla, asi que se quito. Su lugar lo ocupa ahora
    `ia_frontera.comprobar_texto()`, que existe, se ejecuta y se prueba, y que
    trabaja sobre el texto que el jugador va a LEER (que ya no es el `answer` del
    modelo, sino el que compone el sistema).

    `rec` es el recuperador del nucleo, y es OPCIONAL a proposito: sin el, la
    funcion se comporta exactamente igual que antes, solo que sin la capa
    informativa de verificacion estructurada. Con el, el veredicto incluye
    `verificacion["estructurada"]`, que dice que afirmaciones concretas confirma
    el nucleo y cuales no puede comprobar.

    Ese bloque **no cambia `puede_entregarse`** ni toca la politica: verificar no
    autoriza a divulgar. Es informacion, no puerta.

    Devuelve un `Veredicto`. **No lanza**: una excepcion seria facil de
    ignorar, y el fallo debe ser visible, no una traza.
    """
    if not isinstance(salida, dict):
        return _fallo(["la salida del modelo no es un objeto"])

    claims = salida.get("claims")
    if not isinstance(claims, list):
        return _fallo(["la salida del modelo no lleva 'claims' como lista"])
    if not claims:
        return _fallo(["una respuesta sin claims no es auditable"])

    recibido = {cl["ref"]: cl for cl in (ctx.get("claims") or [])}
    reales = claims_de_contexto(ctx)
    por_ref = {}
    for i, cl in enumerate(ctx.get("claims") or []):
        por_ref[cl["ref"]] = reales[i] if i < len(reales) else None

    errores = []
    rechazados = []
    n_ok = 0

    for i, cl in enumerate(claims):
        problemas = _validar_claim(cl, recibido, por_ref)
        if problemas:
            rechazados.append({"indice": i, "motivos": problemas})
            errores.extend("claim %d: %s" % (i, p) for p in problemas)
        else:
            n_ok += 1

    # --- 5. secretos indirectos, sobre el texto que se mostraria ----------
    texto = salida.get("answer") or " ".join(
        str(cl.get("texto") or "") for cl in claims if isinstance(cl, dict))
    fugas = deteccion_fuga(texto, ctx)
    errores.extend("fuga indirecta: %s" % f for f in fugas)

    if not n_ok and not rechazados:
        errores.append("ningun claim pudo validarse")

    # --- ALCANCE DE LA VALIDACION -------------------------------------------
    # `claims_ok` dice que los claims pasaron los cuatro filtros ESTRUCTURALES:
    # la referencia existe, el tipo no es mas fuerte que el apoyo, el apoyo es
    # divulgable y la combinacion de dimensiones es coherente.
    #
    # NO dice que el sistema haya comprobado que el texto sea una consecuencia
    # del apoyo, ni que la afirmacion sea verdadera. Eso no se puede comprobar de
    # forma determinista, y antes de esta declaracion el veredicto no lo decia,
    # con lo que `claims_ok` se podia leer como una garantia de verdad que el
    # sistema nunca dio. Se adjunta aqui el alcance explicito para que no quepa
    # esa lectura. Ver `ia_verificacion.alcance()`.
    verificacion = iv.resumen_verificacion(claims, ctx)

    # --- VERIFICACION ESTRUCTURADA (determinista) ---------------------------
    # Se anade como capa INFORMATIVA dentro del mismo bloque `verificacion`. No
    # cambia `puede_entregarse`, ni toca la politica de divulgacion: verificar no
    # autoriza. No se calcula dentro de `_validar_claim()` porque esa funcion no
    # tiene acceso al recuperador, y porque una verificacion que consulta el
    # nucleo no debe poder alterar la validacion.
    if rec is not None:
        try:
            verificacion["estructurada"] = ie.resumen(claims, ctx, rec)
        except Exception:                                     # noqa: BLE001
            # Si la verificacion falla, se DICE. Callarse dejaria un veredicto
            # que parece completo y no lo esta.
            verificacion["estructurada"] = {
                "error": "no se pudo ejecutar la verificacion estructurada",
                "verificadas": [], "no_verificadas": [], "no_aplicables": [],
            }

    if errores:
        v = _fallo(errores, rechazados, n_ok)
        v["verificacion"] = verificacion
        return v
    v = Veredicto({"puede_entregarse": True, "errores": [],
                   "claims_ok": n_ok, "claims_rechazados": []})
    v["verificacion"] = verificacion
    return v


def _validar_claim(cl, recibido, por_ref):
    """Los cuatro filtros de un claim de salida. Devuelve los problemas."""
    if not isinstance(cl, dict):
        return ["no es un objeto"]
    p = []

    tipo = cl.get("tipo")
    if tipo not in TIPOS_SALIDA:
        return ["tipo desconocido: %r" % (tipo,)]

    texto = cl.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        p.append("sin texto")

    soporte = cl.get("soporte") or []
    if tipo not in TIPOS_SIN_APOYO and not soporte:
        p.append("un claim de tipo %s sin apoyo es una afirmacion sin "
                 "procedencia" % tipo)

    # --- 2. PROCEDENCIA: los apoyos tienen que existir --------------------
    apoyos = []
    for ref in soporte:
        if ref not in recibido:
            p.append("apoyo %r inexistente: el modelo no recibio ese dato, y "
                     "no puede apoyarse en lo que no tiene" % (ref,))
            continue
        real = por_ref.get(ref)
        if real is None:
            p.append("apoyo %r no reconstruible" % (ref,))
            continue
        apoyos.append(real)

    if p:
        return p

    # --- NON_DISCLOSURE: su motivo es el contenido -----------------------
    if tipo == NON_DISCLOSURE:
        if not cl.get("motivo"):
            p.append("NON_DISCLOSURE sin motivo")
        return p

    # --- 3. VERDAD: el tipo no puede ser mas fuerte que su apoyo ---------
    truths = {a.get("truth_status") for a in apoyos}
    fuentes = {a.get("knowledge_source") for a in apoyos}

    if tipo == FACT and c.FACT not in truths:
        p.append("un FACT necesita apoyo en un FACT; sus apoyos son %s. El "
                 "modelo no puede convertir una generacion en evidencia"
                 % sorted(truths))
    if tipo == MECHANIC_EXPLANATION and c.EXTERNAL_KNOWLEDGE not in fuentes:
        p.append("explicar una mecanica requiere apoyo EXTERNAL_KNOWLEDGE")

    if tipo in TIPOS_QUE_EXIGEN_INFERENCIA:
        # Un consejo o una interpretacion no puede colarse apoyandose solo en
        # un hecho: si solo hay hechos, no hay todavia un juicio.
        if not (truths & {c.INFERENCE, c.DERIVED}) and \
                c.EXTERNAL_KNOWLEDGE not in fuentes:
            p.append("un claim de tipo %s sin apoyo derivado o externo no es "
                     "mas que un hecho repetido: no aporta nada" % tipo)

    # --- 4. DIVULGACION: nunca mas permisivo que su apoyo -----------------
    for a in apoyos:
        if a.get("disclosure") == c.FORBIDDEN:
            p.append("se apoya en un dato FORBIDDEN (%r)" % a.get("claim"))
        elif not c.puede_revelarse(a):
            p.append("se apoya en algo no divulgable (%s/%s): el modelo no "
                     "puede decir lo que el sistema no dice"
                     % (a.get("visibility"), a.get("disclosure")))

    # Una pista (CONDITIONAL) autoriza a MENCIONAR, no a afirmar.
    if tipo == FACT and any(a.get("disclosure") == c.CONDITIONAL
                            for a in apoyos):
        p.append("un CONDITIONAL autoriza a mencionar, no a afirmar")

    return p


# ==================== 7. CANAL INDIRECTO Y POLITICA (§17, §19, §36) ======
#: Lo que se sabe del problema, sin fingir que se ha resuelto:
#:
#: El modelo NO recibe datos FORBIDDEN, y eso cierra el canal DIRECTO. Pero el
#: filtrado por parafrasis es un problema DISTINTO, y sigue abierto:
#:
#:     secreto: "diamantes en X=183, Y=72, Z=-14"
#:     respuesta: "Explora aproximadamente X=183."
#:
#: Aqui no hay coincidencia exacta ni dato prohibido literal, y sin embargo se
#: ha filtrado la coordenada. Un filtro de palabras prohibidas NO lo detecta.
#:
#: QUE SE ENTREGA EN ESTA MISION:
#:   * La ARQUITECTURA que hace imposible el caso facil: no hay secretos en el
#:     contexto, asi que no hay nada que filtrar por accidente.
#:   * Una deteccion determinista y conservadora, que marca lo que un detector
#:     serio marcaria, y falla cerrado.
#:   * La declaracion de que el problema de parafrasis esta ABIERTO.
#:
#: QUE NO SE ENTREGA:
#:   * Un detector semantico. No existe, y no se inventa.
#:
#: La regla que si se congela: ante duda, no se entrega.

#: Una coordenada es una ESTRUCTURA, no un parametro suelto. Hay dos formatos
#: con los que se filtra una posicion, y ambos se buscan:
#:
#:     X=183            una asignacion de coordenada (el caso de la mision)
#:     183, 72, -14     una tripleta de coordenadas, como las de DF
#:
#: Se incluye el par `183, 72`, que tambien es una posicion. Es deliberado: el
#: sistema falla cerrado, y preferimos bloquear una frase inutil a dejar pasar
#: una coordenada. El coste es que puede marcar texto inocente, y eso queda
#: declarado como limitacion conocida, no escondido.
_PATRON_COORDENADA = re.compile(
    r"(?:\bx\s*=\s*[-−]?\d+)"
    r"|(?:\d+\s*,\s*\d+\s*,\s*\d+)"
    r"|(?:\d+\s*,\s*\d+)", re.IGNORECASE)

#: Palabras que convierten un valor cualquiera en una pista sobre un secreto.
#: No es un detector semantico: es una lista de intensificadores de secreto.
_INTENSIFICADORES = (
    "exactamente", "concretamente", "precisamente", "justo ahi",
    "justo ahí", "en esa ubicacion", "en esa ubicación", "sin falta",
    "te diria donde", "te diría dónde",
)


def deteccion_fuga(texto, ctx=None):
    """Heuristica DETERMINISTA de fuga indirecta. Fail closed.

    Que marca hoy:
      * una coordenada estructurada (`X=183`, `183, 72, -14`), que es el
        formato con el que los secretos se explican al jugador;
      * un intensificador de secreto pegado a un numero.

    Que NO marca, y hay que decirlo sin rodeos: una parafrasis sin cifras
    ("esta justo al norte", "busca donde estan los diamantes"). Eso exige
    comprension del lenguaje, y aqui no la hay. Por esto es un ESQUELETO con
    nombre propio, no "la solucion": `deteccion_fuga()` es una primera barrera,
    y la definitiva sigue pendiente.
    """
    if not isinstance(texto, str) or not texto.strip():
        return []
    bajo = texto.lower()
    fugas = []

    for m in _PATRON_COORDENADA.finditer(bajo):
        fugas.append("coordenada estructurada en la respuesta: %r"
                     % m.group(0))
        break

    if any(w in bajo for w in _INTENSIFICADORES):
        # Solo es sospechoso si ademas hay un numero: un intensificador solo
        # es retorica, no una fuga.
        if re.search(r"\d", bajo):
            fugas.append("intensificador de secreto junto a un dato numerico")

    return fugas


def cerrar_contexto(ctx):
    """La regla del §17, en una frase ejecutable.

    El modelo NO decide la divulgacion. El sistema la decidio al construir el
    contexto, y la vuelve a comprobar al validar la salida. Entre medias no hay
    nadie: ni el prompt, ni la buena voluntad, ni el propio sistema.

    Si esto devuelve `False`, no se llama a nadie.
    """
    if not isinstance(ctx, dict):
        return False
    for cl in ctx.get("claims") or []:
        if not isinstance(cl, dict):
            return False
        if cl.get("disclosure") == c.FORBIDDEN:
            return False
        if cl.get("visibility") not in c.VISIBILITIES:
            return False
    return True


# ============================== 8. CANONICOS Y EJEMPLOS ===================
#: Los cinco casos obligatorios, ejecutables. Sirven de documentacion que no
#: puede quedarse obsoleta: si el contrato cambia, cambia con ellos.

def canonico_hecho_visible():
    """A. Lo que el jugador ya sabe. Se dice como hecho."""
    return c.afirmacion(
        claim="El jugador conoce a Galka Shafttop.",
        truth_status=c.FACT, knowledge_source=c.PLAYER_KNOWLEDGE,
        visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
        evidences=[c.evidencia("figura", "712", ["name"],
                               "nucleo.Archivo.ficha_figura", "legends.xml")])


def canonico_secreto():
    """B. El diamante. Es verdad y no sale. NUNCA llega al modelo."""
    return c.afirmacion(
        claim="Existe una veta de diamantes en 183,72,-14.",
        truth_status=c.FACT, knowledge_source=c.WORLD_KNOWLEDGE,
        visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
        evidences=[c.evidencia("sitio", "183", ["coordenadas"],
                               "nucleo.Archivo.ficha_sitio", "legends.xml")],
        no_descubierto=True)


def canonico_mecanica():
    """D. La wiki explica una regla. No es un hecho de esta partida."""
    return c.afirmacion(
        claim="Los enanos pueden extraer piedra de una veta.",
        truth_status=c.DERIVED, knowledge_source=c.EXTERNAL_KNOWLEDGE,
        visibility=c.EXTERNAL, disclosure=c.ALLOWED,
        evidences=[c.evidencia("regla_juego", "wiki:excavacion",
                               ["tipo", "contenido"],
                               "documentacion", "wiki")])


def canonico_desconocido():
    """E. No consta. Es una respuesta valida y preferible a suponer."""
    return c.afirmacion(
        claim="No consta la fecha de muerte de la figura.",
        truth_status=c.UNKNOWN, knowledge_source=c.WORLD_KNOWLEDGE,
        visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
        evidences=[], motivo="death_year ausente: AUSENTE NO ES VIVA")


def canonico_consejo(hecho=None, mecanica=None):
    """C. Consejo: un hecho + una mecanica externa + una inferencia.

    El consejo se apoya en lo que el jugador sabe y en lo que la wiki explica,
    y se marca como `INTERPRETATION`. Nunca se convierte en un dato del mundo.
    """
    hecho = hecho or canonico_hecho_visible()
    mecanica = mecanica or canonico_mecanica()
    return c.afirmacion(
        claim="Podria ser util explorar la zona norte.",
        truth_status=c.INFERENCE, knowledge_source=c.INFERENCE,
        visibility=c.PLAYER_VISIBLE, disclosure=c.ALLOWED,
        evidences=list(hecho["evidence"]) + list(mecanica["evidence"]))


#: Los cinco casos, indexados por nombre. Es la documentacion ejecutable.
CANONICOS = {
    "A_hecho_visible": canonico_hecho_visible,
    "B_secreto": canonico_secreto,
    "C_consejo": canonico_consejo,
    "D_mecanica": canonico_mecanica,
    "E_desconocido": canonico_desconocido,
}


def a_json(objeto):
    """El contexto o la respuesta, tal cual sale hacia el proveedor."""
    return json.dumps(objeto, ensure_ascii=False, sort_keys=True, indent=2)


def desde_json(texto):
    """La salida cruda del modelo, revalidada por `validar_salida()`.

    **No se valida aqui, a proposito.** Parsear y validar son dos pasos
    separados: si el parseo validara, no se podria probar el caso "el modelo
    devuelve JSON invalido", que es precisamente el que hay que detectar.
    """
    try:
        return json.loads(texto)
    except (ValueError, TypeError) as e:
        raise c.ContratoInvalido([
            "la salida del modelo no es JSON valido: %s" % (e,)])