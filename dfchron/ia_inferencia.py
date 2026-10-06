#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: FRONTERA DE INFERENCIA y PRESUPUESTO
======================================================

Define COMO entra un modelo en el sistema, sin estar atado a ningun proveedor.
No hay LLM aqui. No hay SDK. No hay red. Lo que hay es **la frontera**, escrita
para que el dia que se conecte uno, lo que se conecte sea un detalle.

    ContextoIA -> Presupuesto -> Adaptador -> Modelo -> RespuestaIA
                                                         |
                                                   validar_salida()
                                                         |
                                              ACEPTADA / RECHAZADA

EL MODELO NO ES LA FRONTERA
---------------------------
El LLM NO es la autoridad, NO decide que secretos conoce, NO decide que puede
revelar, NO puede elevar su propia confianza y NO puede convertir una ausencia
de evidencia en un FACT. Todo eso lo sigue decidiendo `contrato_ia`, antes y
despues.

> **La capacidad linguistica del modelo NO amplia el conjunto de informacion
> que el sistema permite revelar.** Un modelo mas potente recibe EXACTAMENTE el
> mismo contexto, porque el presupuesto es un **techo**, no un objetivo.

QUE HAY AQUI
------------
    * `Presupuesto`  - los cinco limites y que se hace al excederlos
    * `Perfil`       - la abstraccion de hardware/modelo (sin elegir ninguno)
    * `Adaptador`    - la interfaz, con fallo cerrado en cada error
    * `inferir()`    - la orquestacion de una inferencia completa

Ejecutar:  python dfchron/pruebas/probar_frontera_inferencia.py
"""
import json
import os
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from dfchron import contrato_ia as c           # noqa: E402
from dfchron import ia_contrato as ioc         # noqa: E402
from dfchron import ia_frontera as fr         # noqa: E402

SCHEMA_INFERENCIA = "inferencia-1"


class PresupuestoExcedido(c.ContratoInvalido):
    """El contexto no cabe. Se distingue del error de contrato normal."""


def estimar_tokens(texto):
    """Estimacion CONSERVADORA de tokens. No es un tokenizador.

    ~3,6 caracteres por token, redondeado a **arriba**: quedarse corto dejaria
    pasar un contexto mayor del permitido, y quedarse largo solo cuesta una
    reduccion de mas. El error va **siempre a favor de la seguridad**.

    Cuando exista un tokenizador real, se inyecta con `Presupuesto(contar=...)`
    y este valor deja de usarse. **El contrato no cambia.**
    """
    if not texto:
        return 0
    return max(1, int(len(str(texto)) / 3.6) + 1)


class Presupuesto(dict):
    """Los cinco limites, y QUE PASA cuando se exceden.

    | limite               | que mide                                   |
    |----------------------|--------------------------------------------|
    | `max_input_chars`     | **barrera barata**, antes de contar tokens |
    | `max_context_tokens`  | solo el contexto recuperado                |
    | `max_input_tokens`    | instruccion + pregunta + contexto          |
    | `max_output_tokens`   | lo que el modelo puede GENERAR             |
    | `max_total_tokens`    | entrada + salida                           |

    La separacion entre `chars` y `tokens` es deliberada: **un caracter NO es un
    token**. Los caracteres paran antes de gastar un contador; el limite real de
    inferencia se mide en tokens, aunque hoy se estime.

    Los valores por defecto son MUY conservadores y estan marcados como tales:
    no se han medido contra ningun runtime. Hacen el contrato ejecutable; no
    afirman que un modelo quepa.
    """

    def __init__(self, max_input_chars=24000, max_input_tokens=6000,
                 max_context_tokens=4000, max_output_tokens=800,
                 max_total_tokens=6800, contar=None):
        dict.__init__(self, {
            "max_input_chars": max_input_chars,
            "max_input_tokens": max_input_tokens,
            "max_context_tokens": max_context_tokens,
            "max_output_tokens": max_output_tokens,
            "max_total_tokens": max_total_tokens,
            "_contador": contar or estimar_tokens,
        })

    def medir(self, texto):
        """(caracteres, tokens) de un texto."""
        s = "" if texto is None else str(texto)
        return len(s), int(self["_contador"](s))

    def medir_contexto(self, contexto, instrucciones=""):
        """Las cuatro medidas, por separado.

        Se cuenta la pregunta aparte del contexto, y ambos aparte de las
        instrucciones. Sin esa separacion no se puede explicar un rechazo, y
        una reduccion parcial podria tocar la parte equivocada.
        """
        cx_json = json.dumps(contexto, ensure_ascii=False, sort_keys=True)
        i_c, i_t = self.medir(instrucciones)
        p_c, p_t = self.medir(contexto.get("pregunta")
                              if isinstance(contexto, dict) else "")
        c_c, c_t = self.medir(cx_json)
        return {"instrucciones_chars": i_c, "instrucciones_tokens": i_t,
                "pregunta_chars": p_c, "pregunta_tokens": p_t,
                "contexto_chars": c_c, "contexto_tokens": c_t,
                "input_chars": i_c + p_c + c_c,
                "input_tokens": i_t + p_t + c_t}
def cerrar_si_mismo(contexto):
    """La valla mas baja: ¿el contexto que sale es presentable?"""
    if not isinstance(contexto, dict):
        return False
    for cl in contexto.get("claims") or []:
        if not isinstance(cl, dict):
            return False
        if cl.get("disclosure") == c.FORBIDDEN:
            return False
        if cl.get("visibility") not in c.VISIBILITIES:
            return False
    return True


def _cabe(m, p):
    """¿Cabe? Todas las cotas, a la vez."""
    return (m["input_chars"] <= p["max_input_chars"]
            and m["input_tokens"] <= p["max_input_tokens"]
            and m["contexto_tokens"] <= p["max_context_tokens"])


def reducir_contexto(contexto, presupuesto, instrucciones="",
                     instrucciones_obligatorias=()):
    """Decide: cabe entero, se reduce, o se rechaza.

    **Reducir solo puede QUITAR claims.** Jamás los reescribe, jamás los
    reordena para favorecer la divulgacion, jamás los sustituye. Si al reducir
    quedara alguna afirmacion prohibida, se rechaza; aunque eso no puede ocurrir
    —las prohibidas ya no estan en el contexto— se comprueba igualmente.

    El recorte va **desde el final**: el orden del contexto es el que produjo
    `ia_contexto`, ya ordenado por relevancia. No se reordena nada.

    Devuelve `(contexto_final, decision)`.
    """
    if not cerrar_si_mismo(contexto):
        return None, {"accion": "RECHAZADO",
                      "motivo": "el contexto ya viola el contrato"}

    m = presupuesto.medir_contexto(contexto, instrucciones)
    if _cabe(m, presupuesto):
        return contexto, {"accion": "ACEPTADO", "motivo": "cabe",
                          "medidas": m}

    if instrucciones_obligatorias:
        return None, {"accion": "RECHAZADO",
                      "motivo": "las instrucciones del contrato ya exceden "
                                "el presupuesto y no son recortables",
                      "medidas": m}

    claims = list((contexto.get("claims") or []))
    total = len(claims)
    if total <= 1:
        return None, {"accion": "RECHAZADO",
                      "motivo": "no se puede reducir mas: el unico claim ya "
                                "excede el presupuesto",
                      "medidas": m}

    from dfchron.ia_contrato import _Candado
    while len(claims) > 1:
        claims = claims[:-1]
        prueba = dict(contexto)
        prueba["claims"] = claims
        m2 = presupuesto.medir_contexto(prueba, instrucciones)
        if _cabe(m2, presupuesto):
            with _Candado():
                final = ioc.ContextoIA(prueba)
            if not cerrar_si_mismo(final):
                return None, {"accion": "RECHAZADO",
                              "motivo": "la reduccion introdujo algo prohibido",
                              "medidas": m2}
            return final, {"accion": "REDUCIDO",
                           "motivo": "se recortaron claims para caber",
                           "medidas": m2,
                           "claims_quitados": total - len(claims)}

    return None, {"accion": "RECHAZADO",
                  "motivo": "no se ha podido reducir dentro del presupuesto",
                  "medidas": m}
# ============================================ 2. PERFILES =================
#: Un perfil describe UNA CONFIGURACION DE EJECUCION, no un modelo concreto.
#:
#: Aqui NO se define ningun perfil, a proposito. Definirlos seria elegir
#: hardware y modelo antes de haber medido nada, que es exactamente la decision
#: que esta mision no quiere tomar. Se declara la FORMA y queda vacia.
#:
#: | campo              | que es                                       |
#: |--------------------|----------------------------------------------|
#: | `nombre`           | etiqueta libre ("local-8gb")                   |
#: | `vram_mb`          | VRAM disponible                               |
#: | `ram_mb`           | RAM disponible                                |
#: | `contexto_max`     | ventana maxima que admite el runtime           |
#: | `output_max`       | generacion maxima                             |
#: | `modelo_permitido` | identificador del modelo, si procede           |
#: | `cuantizacion`     | q4, q5, q8...                                 |
#: | `offload`          | que parte va a CPU                            |
#: | `concurrencia`     | peticiones simultaneas                       |
#: | `presupuesto`      | el `Presupuesto` que se le aplica             |
#:
#: REGLA INNEGOCIABLE: cambiar de perfil **NO** cambia una sola regla de
#: divulgacion. El perfil decide cuanto cabe, nunca que puede revelarse.
CAMPOS_PERFIL = ("nombre", "vram_mb", "ram_mb", "contexto_max", "output_max",
                 "modelo_permitido", "cuantizacion", "offload",
                 "concurrencia", "presupuesto")

#: Ningun perfil definido. Ver arriba.
PERFILES = {}


class Perfil(dict):
    """Una configuracion de ejecucion. Sin modelo, sin ceramica."""

    def __init__(self, **campos):
        desconocidos = [k for k in campos if k not in CAMPOS_PERFIL]
        if desconocidos:
            raise c.ContratoInvalido([
                "campo de perfil desconocido: %r. Conocidos: %s"
                % (desconocidos, list(CAMPOS_PERFIL))])
        dict.__init__(self, campos)

    def limites(self):
        """El presupuesto que corresponde a este perfil.

        Si el perfil no declara uno, se usa el conservador por defecto. **Nunca
        se construye uno mas permisivo a partir del hardware**: mas VRAM no
        significa mas permiso para ver cosas del jugador.
        """
        p = self.get("presupuesto")
        if p is not None:
            return p
        return Presupuesto(
            max_context_tokens=min(4000, int(self.get("contexto_max") or 4000)),
            max_output_tokens=min(800, int(self.get("output_max") or 800)))


#: Fallos del runtime. TODOS terminan en fallo cerrado: ninguno devuelve una
#: respuesta al jugador. Se nombran para que un adaptador real mapee sus errores
#: a uno de estos, en vez de inventar categorias.
FALLO_TIMEOUT = "TIMEOUT"
FALLO_CONTEXTO_GRANDE = "CONTEXTO_DEMASIADO_GRANDE"
FALLO_SALIDA_GRANDE = "SALIDA_DEMASIADO_GRANDE"
FALLO_MALFORMADA = "RESPUESTA_MALFORMADA"
FALLO_NO_DISPONIBLE = "MODELO_NO_DISPONIBLE"
FALLO_RUNTIME = "ERROR_RUNTIME"

FALLOS = (FALLO_TIMEOUT, FALLO_CONTEXTO_GRANDE, FALLO_SALIDA_GRANDE,
          FALLO_MALFORMADA, FALLO_NO_DISPONIBLE, FALLO_RUNTIME)


class FalloInferencia(Exception):
    """El runtime no pudo responder. Se convierte SIEMPRE en cierre."""

    def __init__(self, tipo, detalle=""):
        if tipo not in FALLOS:
            raise ValueError("tipo de fallo desconocido: %r" % (tipo,))
        self.tipo = tipo
        self.detalle = detalle
        Exception.__init__(self, "%s: %s" % (tipo, detalle))


class Adaptador:
    """La interfaz con un modelo. SOLO la interfaz; no hay ninguna aqui.

    Un adaptador real (LM Studio, llama.cpp, Ollama, API) implementa `invocar`
    y nada mas. No toca el contrato, no toca la politica, y **no puede devolver
    nada al jugador**: su salida siempre pasa por `validar_salida()`.

    Lo que un adaptador **no** puede hacer, y por que se documenta:
      * devolver texto al jugador — su retorno no llega al jugador;
      * ampliar el contexto — recibe el contexto ya cerrado;
      * relajar el presupuesto — `max_output_tokens` se le impone desde fuera;
      * declarar su propia confianza — se registra y se ignora.
    """

    nombre = "abstracto"

    def disponible(self):
        """¿Hay runtime? Se comprueba ANTES de construir nada."""
        return False

    def invocar(self, contexto, presupuesto):
        """Genera una respuesta. Lanza `FalloInferencia` si no puede."""
        raise FalloInferencia(FALLO_NO_DISPONIBLE,
                              "adaptador sin implementar")


def normalizar_salida(bruto, presupuesto):
    """Convierte lo que devuelve un runtime en algo validable.

    Un runtime devuelve JSON, texto, o cualquier cosa. Aqui se exige JSON con
    `claims`. Si no se puede leer, **fallo cerrado**: no se intenta adivinar.
    """
    if bruto is None:
        raise FalloInferencia(FALLO_MALFORMADA, "salida vacia")
    if isinstance(bruto, (bytes, bytearray)):
        try:
            bruto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            raise FalloInferencia(FALLO_MALFORMADA, "salida no utf-8")
    if isinstance(bruto, str):
        if len(bruto) > presupuesto["max_output_tokens"] * 8:
            raise FalloInferencia(FALLO_SALIDA_GRANDE,
                                  "la salida cruda excede lo admisible")
        try:
            bruto = json.loads(bruto)
        except ValueError as e:
            raise FalloInferencia(FALLO_MALFORMADA,
                                  "la salida no es JSON: %s" % e)
    if not isinstance(bruto, dict):
        raise FalloInferencia(FALLO_MALFORMADA, "la salida no es un objeto")
    if "claims" not in bruto or not isinstance(bruto["claims"], list):
        raise FalloInferencia(FALLO_MALFORMADA,
                              "la salida no lleva claims como lista")
    return {"answer": bruto.get("answer"), "claims": bruto["claims"],
            "confidence": bruto.get("confidence")}


# ================================ 4. ORQUESTACION ========================
def inferir(contexto, adaptador, presupuesto=None, perfil=None,
            instrucciones="", instrucciones_obligatorias=()):
    """El recorrido COMPLETO de una inferencia. Sin atarse a un proveedor.

    ```
    ContextoIA -> Presupuesto -> Adaptador -> Modelo -> RespuestaIA
                                                         |
                                                   validar_salida()
                                                         |
                                              ACEPTADA / RECHAZADA
    ```

    En este orden, y en ningun otro:

    1. ¿El contexto es presentable? (`cerrar_si_mismo`). Si no, se PARA.
    2. ¿Cabe en el presupuesto? Si no, se REDUCE; si no cabe, se PARA.
    3. ¿El runtime está disponible? Si no, se PARA.
    4. Se invoca con `max_output_tokens` **impuesto desde fuera**.
    5. Se normaliza la salida. Si no se puede leer, se PARA.
    6. `validar_salida()`. Aquí es donde el contenido se acepta o se rechaza.
    7. La confianza la calcula `ia_mock`, no el adaptador.

    Devuelve un `dict` con `desenlace`, `veredicto`, `decisión` y, solo si
    procede, `texto`. **Nunca devuelve texto si no se ha validado.**
    """
    if presupuesto is None:
        presupuesto = (perfil.limites() if perfil is not None
                       else Presupuesto())

    base = {"desenlace": None, "veredicto": None, "texto": None,
            "decision": None, "fallo": None}

    # 1. valla de entrada
    if not cerrar_si_mismo(contexto):
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = FALLO_MALFORMADA
        base["decision"] = {"accion": "RECHAZADO",
                            "motivo": "el contexto viola el contrato"}
        return base

    # 2. presupuesto: cabe, se reduce, o se para
    usable, decision = reducir_contexto(
        contexto, presupuesto, instrucciones, instrucciones_obligatorias)
    base["decision"] = decision
    if usable is None:
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = FALLO_CONTEXTO_GRANDE
        return base

    # 3. runtime disponible
    try:
        if not adaptador.disponible():
            base["desenlace"] = "RECHAZADO"
            base["fallo"] = FALLO_NO_DISPONIBLE
            return base
    except Exception:                                       # noqa: BLE001
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = FALLO_RUNTIME
        return base

    # 4-5. invocar y normalizar
    try:
        crudo = adaptador.invocar(usable, presupuesto)
        salida = normalizar_salida(crudo, presupuesto)
    except FalloInferencia as e:
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = e.tipo
        return base
    except Exception:                                       # noqa: BLE001
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = FALLO_RUNTIME
        return base

    # 6. validar. Aqui decide el contenido, no la forma.
    from dfchron import ia_mock as mk
    veredicto = mk.validar_respuesta_ia(salida, usable)
    base["veredicto"] = veredicto

    if not veredicto.get("puede_entregarse"):
        base["desenlace"] = veredicto.get("desenlace")
        return base          # sin texto: un bloqueo no entrega nada

    # 7. entrega. **Aqui el texto lo compone el SISTEMA, no el modelo.**
    #
    # Antes se entregaba `salida["answer"]`: texto libre escrito por el modelo y
    # entregado tal cual. Medido, ese canal dejaba pasar parafrasis, referencias
    # espaciales, sustracciones, nombres inventados y consejos que filtran.
    #
    # Ahora el modelo elige QUE claims autorizados se dicen (eso ya esta
    # validado en el paso 6) y el sistema redacta con plantillas propias. El
    # `answer` del modelo se conserva como campo de diagnostico y **no se
    # entrega**: no es la autoridad y no puede serlo.
    base["desenlace"] = "AUTORIZADA"
    texto, frontera = fr.componer_seguro(salida.get("claims") or [], usable)
    if texto is None:
        # La composicion no cuadra con los claims: no se entrega nada. Falla
        # cerrado, y se dice por que, para que no parezca un silencio.
        base["desenlace"] = "RECHAZADO"
        base["fallo"] = FALLO_MALFORMADA
        base["violaciones_frontera"] = list(frontera.get("violaciones") or [])
        base["answer_del_modelo"] = salida.get("answer")
        return base
    base["texto"] = texto
    base["answer_del_modelo"] = salida.get("answer")
    base["confianza"] = veredicto.get("confianza")
    base["confianza_declarada"] = veredicto.get("confianza_declarada")
    return base


# ============================ 5. BENCHMARK PARA LM STUDIO ==================
#: El benchmark NO se conecta a nada. Solo sabe RECORRER el banco con un
#: adaptador que se le pase, y anotar lo que devuelve. Cuando exista un
#: adaptador real, se le pasa; mientras tanto se le pasa el mock, y sirve para
#: comprobar que el instrumento mide bien.
#:
#: LA DISTINCIÓN QUE NO SE PUEDE PERDER:
#:
#:     "el modelo se equivocó"          !=  "el validador bloqueó bien"
#:
#: Un modelo mediocre con un buen validador sigue siendo seguro. Confundir las
#: dos cosas convierte al benchmark en un instrumento de autobombo: mide la
#: capacidad del modelo y lo llama calidad del sistema.
CLASE_MODELO = "MODELO_INCORRECTO"      # el modelo dijo algo invalido
CLASE_VALIDADOR = "VALIDADOR_BLOQUEO"  # el validador hizo su trabajo
CLASE_CONTRATO = "CONTRATO"            # el sistema fallo antes del modelo
CLASE_OK = "OK"
CLASES_BENCHMARK = (CLASE_OK, CLASE_MODELO, CLASE_VALIDADOR, CLASE_CONTRATO)


def ejecutar_benchmark(adaptador=None, presupuesto=None, perfil=None,
                       banco=None, limite=None, con_frontera=True):
    """Recorre el banco con un adaptador y devuelve un registro por escenario.

    Cada registro lleva escenario, entrada, contexto, respuesta, respuesta
    validada, veredicto, clase de fallo, latencia, tokens de entrada y salida,
    y configuracion.

    `limite` es una proteccion: el benchmark no debe cerrar el proceso.

    POR QUE `con_frontera` EXISTE Y POR QUE NO SE PUEDE QUITAR
    ---------------------------------------------------------
    Antes, esta funcion recorria el banco por `evaluar_banco_ia.ejecutar_escenario`,
    que va por `MockIA`: el `adaptador` recibido se guardaba en `config` y **no se
    invocaba nunca**. Eso hacia que un benchmark "con modelo real" midiera, en
    realidad, el guion del mock. Un instrumento que no mide lo que dice medir.

    Ahora, con `con_frontera=True` (por defecto), cada escenario pasa por
    `inferir()` de extremo a extremo: presupuesto, adaptador, `normalizar_salida()`,
    validacion y composicion. Es el camino real, y el unico que permite distinguir
    lo que el benchmark existe para distinguir:

        modelo mediocre + seguridad correcta
        modelo bueno   + seguridad incorrecta
        modelo bueno   + seguridad correcta
        modelo hostil  + seguridad correcta

    Con `con_frontera=False` se conserva el recorrido por `MockIA`, que sirve
    para comprobar el instrumento sin depender de ningun runtime. No es el
    default a proposito: por defecto se mide la verdad.
    """
    import time
    from dfchron import ia_contexto as cx
    import evaluar_banco_ia as ev

    if adaptador is None:
        adaptador = Adaptador()          # abstracto: falla cerrado, siempre
    if banco is None:
        banco = ev.cargar_banco()
    if limite is not None:
        banco = banco[:limite]
    if presupuesto is None:
        presupuesto = (perfil.limites() if perfil is not None else Presupuesto())
    rec = cx.recuperador_compartido()

    registros = []
    for e in banco:
        t0 = time.perf_counter()
        entrada = {"pregunta": e["pregunta"], "consulta": e.get("consulta"),
                   "modo": "razonamiento",
                   "esperado": e["resultado_esperado"]}

        if con_frontera:
            registro = _benchmark_frontera(e, adaptador, presupuesto, rec)
        else:
            registro = _benchmark_mock(e, rec)
        ms = int((time.perf_counter() - t0) * 1000)
        registro.update({"escenario": e["id"], "categoria": e["categoria"],
                         "entrada": entrada, "latencia_ms": ms,
                         "tokens_entrada": None, "tokens_salida": None,
                         "tokens_totales": None,
                         "config": {"adaptador": getattr(adaptador, "nombre", "?"),
                                    "perfil": getattr(perfil, "nombre", None),
                                    "frontera": bool(con_frontera)}})
        registros.append(registro)

    metricas = {"total": len(registros)}
    for cl in CLASES_BENCHMARK:
        metricas[cl] = sum(1 for r in registros if r["clase_fallo"] == cl)
    return registros, metricas


def _clase_de(desenlace, clasificacion, funcionales):
    """La clase que NO se puede perder: modelo vs validador vs contrato.

    Se calcula en un sitio para que las dos rutas del benchmark no puedan
    discrepar en como etiquetan un mismo desenlace. Confundir "el modelo se
    equivoco" con "el validador bloqueo bien" es lo que convierte el benchmark
    en un instrumento de autobombo.
    """
    if desenlace in funcionales:
        return CLASE_CONTRATO
    if clasificacion == "COINCIDE":
        return CLASE_OK
    if desenlace == "BLOQUEO_SEGURIDAD":
        return CLASE_VALIDADOR
    return CLASE_MODELO


def _contexto_de(e, estado, rec):
    """El contexto de un escenario, por el mismo camino que usa el banco."""
    import dfchron.ia_contexto as cx
    return cx.consultar_contexto(e["pregunta"], consulta=e.get("consulta"),
                                 tipo=e.get("tipo"), estado=estado,
                                 recuperador=rec)


def _benchmark_frontera(e, adaptador, presupuesto, rec):
    """Un escenario por el camino REAL: `inferir()` de punta a punta.

    Devuelve el mismo esquema que `_benchmark_mock`, para que las dos rutas sean
    comparables fila a fila. Es lo que permite afirmar "modelo hostil + seguridad
    correcta" con datos y no con entusiasmo.
    """
    import evaluar_banco_ia as ev
    estado = ev.estado_para(e)
    try:
        inf = _contexto_de(e, estado, rec)
        contexto = inf.get("contexto")
        if contexto is None:
            return {"contexto": {"claims": 0}, "respuesta": None,
                    "respuesta_validada": False, "veredicto": "ERROR_CONTRATO",
                    "fugas": [], "clase_fallo": CLASE_CONTRATO}
        r = inferir(contexto, adaptador, presupuesto=presupuesto)
        desenlace = r.get("desenlace")
        fugas = ev.buscar_fugas({"obtenido": desenlace,
                                 "texto": r.get("texto")}, e)
        if fugas:
            # Una fuga en lo ENTREGADO pesa mas que cualquier acierto funcional.
            clase = CLASE_MODELO
        else:
            clase = _clase_de(desenlace, None, ev.FUNCIONALES)
        return {"contexto": {"claims": len(contexto.get("claims") or [])},
                "respuesta": r.get("answer_del_modelo"),
                "respuesta_validada": bool(desenlace == "AUTORIZADA"),
                "veredicto": desenlace,
                "fugas": fugas,
                "clase_fallo": clase}
    finally:
        try:
            os.remove(estado.ruta)
        except OSError:                                     # pragma: no cover
            pass


def _benchmark_mock(e, rec):
    """El recorrido antiguo, por `MockIA`. Sirve para probar el instrumento."""
    import evaluar_banco_ia as ev
    r = ev.ejecutar_escenario(e, rec)
    return {"contexto": {"claims": r.get("claims", 0)},
            "respuesta": r.get("respuesta"),
            "respuesta_validada": r["obtenido"] != "BLOQUEO_SEGURIDAD",
            "veredicto": r["obtenido"],
            "fugas": r.get("fugas") or [],
            "clase_fallo": _clase_de(r["obtenido"], r.get("clasificacion"),
                                     ev.FUNCIONALES)}





