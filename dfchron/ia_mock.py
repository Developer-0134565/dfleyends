#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Adaptador de prueba (mock) para la futura IA
============================================================

Un `mock` que **no simula inteligencia**: no razona, no redacta, no improvisa.
Solo devuelve respuestas estructuradas que alguien ha escrito antes, para poder
recorrer el flujo entero sin un modelo:

    CONSULTA → CONTEXTO → MOCK → RESPUESTA → VALIDACIÓN → VEREDICTO

LO QUE ESTE MOCK NO PUEDE HACER
--------------------------------
* No puede cambiar `disclosure` de nada. No toca el contexto.
* No puede escribir en el estado del jugador ni en el dataset.
* No puede aprobarse a si mismo. Lo que devuelve lo valida `ia_contrato`, que
  no sabe que el origen es un mock.
* No llama a la red. No importa nada. Solo la biblioteca estandar.

Que no pueda hacer esas tres cosas es lo que lo hace **util** como prueba: si
pudiera, el flujo estaria probandose a si mismo y no probaria nada.

DETERMINISMO
------------
Sin azar, sin reloj. La misma pregunta con el mismo guion da la misma
respuesta, byte a byte.

Ejecutar:  python dfchron/pruebas/probar_ia_mock.py
"""
import os
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from dfchron import contrato_ia as c           # noqa: E402
from dfchron import ia_contrato as ioc         # noqa: E402
from dfchron import ia_frontera as fr          # noqa: E402


class MockIA:
    """Devuelve respuestas predefinidas. No piensa.

    Se construye con un guion: un diccionario de `clave → respuesta`. La clave
    se elige explicitamente al ejecutar la consulta, y se comprueba que exista
    en el guion. **Si no existe, falla**: un mock que se inventa la respuesta
   aria una segunda politica de verdad, que es justo lo que no se quiere.
    """

    def __init__(self, guion=None):
        self._guion = dict(guion or {})
        self.llamadas = []

    def registrar(self, clave, respuesta):
        """Define una respuesta para una clave. Devuelve `self`, para encadenar."""
        self._guion[clave] = respuesta
        return self

    def claves(self):
        return sorted(self._guion)

    def tiene(self, clave):
        return clave in self._guion

    def invocar(self, contexto, clave=None):
        """Devuelve la respuesta del guion. Sin `clave`, la primera que haya.

        Registra la llamada para que las pruebas puedan comprobar que se uso el
        camino que creian. No recibe ni toca el contexto: solo lo cuenta.
        """
        self.llamadas.append({"clave": clave,
                              "claims_recibidos": len(contexto.get("claims")
                                                       or [])})
        elegida = clave if clave is not None else (
            sorted(self._guion)[0] if self._guion else None)
        if elegida is None:
            raise c.ContratoInvalido([
                "el mock no tiene guion: sin respuesta que devolver"])
        if elegida not in self._guion:
            raise c.ContratoInvalido([
                "el mock no tiene guion para %r. Disponibles: %s"
                % (elegida, sorted(self._guion))])
        respuesta = self._guion[elegida]
        # Se devuelve una COPIA superficial: el guion no se muta al validar,
        # y una prueba que lo cambiara contaminaria las siguientes.
        if isinstance(respuesta, dict):
            copia = dict(respuesta)
            copia["claims"] = [dict(cl) if isinstance(cl, dict) else cl
                               for cl in (respuesta.get("claims") or [])]
            return copia
        return respuesta

    # --- azucar syntactic -------------------------------------------------
    def __len__(self):
        return len(self._guion)

    def __repr__(self):
        return "MockIA(claves=%s)" % (self.claves(),)


#: Un guion minimo y honesto: un hecho visible y un rechazo educado. No hay
#: ningun secreto aqui, y no se anade ninguno a proposito: el mock no sabe
#: cuales hay.
GUION_BASICO = {
    "hecho": {
        "answer": "El sitio es de tipo fortress.",
        "claims": [{"texto": "El sitio es de tipo fortress.",
                    "tipo": "FACT", "soporte": ["c0"]}],
    },
    "rechazo": {
        "answer": "No puedo decirte eso.",
        "claims": [{"texto": "Hay informacion que no puedo compartir.",
                    "tipo": "NON_DISCLOSURE",
                    "soporte": [], "motivo": "PLAYER_HIDDEN"}],
    },
    "no_consta": {
        "answer": "No consta en los datos.",
        "claims": [{"texto": "No consta en los datos.",
                    "tipo": "UNKNOWN", "soporte": ["c0"]}],
    },
}


def mock_basico():
    """Un mock con el guion basico, listo para usar."""
    return MockIA(GUION_BASICO)


# ============================== 2. LA CONFIANZA (decidida, §10) ===========
#: QUE SIGNIFICA `confidence`, Y QUE NO.
#:
#: Se confundian cuatro cosas distintas, y se separan:
#:
#:   1. **Confianza del modelo**: «creo que es correcto». NO es una prueba de
#:      nada. Un modelo puede estar muy seguro y equivocado, y su seguridad no
#:      depende de la evidencia. **Se IGNORA para decidir.**
#:   2. **Calidad del soporte**: ¿la afirmacion se apoya en un FACT? Esto SI
#:      es verificable, y es lo que se mide.
#:   3. **Completitud del contexto**: ¿faltaba informacion? Se informa aparte.
#:   4. **Veracidad**: la resuelve el contrato. La confianza no la sustituye.
#:
#: DECISION: `confidence` significa **calidad del SOPORTE**, y la calcula el
#: SISTEMA a partir de los claims validados. Nunca la declara el modelo.
CONFIANZA_ALTA = "ALTA"
CONFIANZA_MEDIA = "MEDIA"
CONFIANZA_BAJA = "BAJA"
CONFIANZA_NINGUNA = "NINGUNA"

_NIVELES = (CONFIANZA_ALTA, CONFIANZA_MEDIA, CONFIANZA_BAJA,
            CONFIANZA_NINGUNA)


def evaluar_confianza(respuesta, verificacion=None):
    """La confianza, calculada por el sistema. No declarada.

    | que contiene la respuesta              | confianza |
    |-----------------------------------------|-----------|
    | `FACT` con apoyo real y texto respaldado | ALTA      |
    | algun `DERIVED`/`ADVICE`/`INTERPRETATION`| MEDIA    |
    | solo `UNKNOWN` o `NON_DISCLOSURE`       | BAJA      |
    | nada                                    | NINGUNA   |

    Regla que la sostiene: **la confianza sube con la calidad de la evidencia y
    baja con la ausencia de ella.** Nunca con la seguridad del modelo.

    CORRECCION DE ESTA MISION: el `tipo` declarado **no basta** para dar confianza
    alta. Medido: un claim con texto «Existe una veta de diamantes», tipo `FACT` y
    apoyo en un claim real que solo decia «El sitio es de tipo fortress», recibia
    `ALTA`: la maxima confianza para contenido que **nadie habia comprobado**. El
    tipo lo elige el modelo, asi que usarlo como unico criterio es usar la
    declaracion del modelo como si fuera evidencia.

    Por eso ahora, si se pasa `verificacion` (el bloque que emite
    `ia_contrato.validar_salida`), un `FACT` **sin trazabilidad** baja a `MEDIA`, y
    uno **sin ningun respaldo** baja a `BAJA`. Sin `verificacion` no se puede
    comprobar el respaldo, asi que no se afirma `ALTA`: se degrada. Fallar hacia
    abajo es lo unico coherente con "no puedo demostrarlo".

    Esto **no** es un validador semantico: no comprueba que el texto sea
    consecuencia del apoyo, solo que tiene palabras en comun con el. La
    verificacion semantica sigue sin existir, y se declara como tal en
    `ia_verificacion.alcance()`.
    """
    claims = (respuesta or {}).get("claims") or []
    if not claims:
        return CONFIANZA_NINGUNA
    tipos = {cl.get("tipo") for cl in claims if isinstance(cl, dict)}
    if tipos <= {ioc.FACT}:
        return _confianza_por_trazabilidad(claims, verificacion)
    if tipos & {ioc.DERIVED, ioc.ADVICE, ioc.INTERPRETATION,
                ioc.MECHANIC_EXPLANATION}:
        return CONFIANZA_MEDIA
    if tipos <= {ioc.UNKNOWN, ioc.NON_DISCLOSURE}:
        return CONFIANZA_BAJA
    return CONFIANZA_MEDIA


def _confianza_por_trazabilidad(claims, verificacion):
    """`ALTA` solo si ademas hay respaldo medible. Si no, se degrada."""
    if not verificacion:
        # Sin el bloque de verificacion no se puede afirmar el respaldo. No se
        # inventa: se degrada. La confianza alta es una afirmacion que exige
        # pruebas, y aqui no hay pruebas.
        return CONFIANZA_MEDIA
    traz = (verificacion or {}).get("trazabilidad") or {}
    sin_respaldo = (verificacion or {}).get("claims_sin_respaldo") or []
    fracciones = [traz[i].get("fraccion") for i in sorted(traz)
                  if isinstance(traz.get(i), dict)]
    if not fracciones:
        return CONFIANZA_MEDIA
    if any(f == 0.0 for f in fracciones if f is not None):
        return CONFIANZA_BAJA
    if any(f is not None and f < 1.0 for f in fracciones):
        return CONFIANZA_MEDIA
    return CONFIANZA_ALTA


def confianza_declarada(respuesta):
    """Lo que el modelo quiso decir. Se REGISTRA, pero no decide nada.

    Se separa a proposito del campo `confidence`: mezclarlos es
    precisamente el fallo que esta funcion existe para evitar.
    """
    return (respuesta or {}).get("confidence")


# ================================================= 3. VALIDACION ==========
#: Los desenlaces posibles de una consulta. Se nombran todos, y son distintos
#: entre si, porque significan cosas distintas para el jugador.
#:
#: | desenlace              | que paso                                  |
#: |------------------------|-------------------------------------------|
#: | `AUTORIZADA`           | hay respuesta y puede mostrarse            |
#: | `PARCIAL`              | hay respuesta, pero el contexto estaba recortado |
#: | `DESCONOCIMIENTO`      | el sistema no sabe; eso es una respuesta   |
#: | `BLOQUEO_SEGURIDAD`    | alguien ha intentado revelar algo prohibido |
#: | `ERROR_CONTRATO`       | la peticion o la salida no era valida      |
#: | `ERROR_DATOS`          | el nucleo no ha podido responder           |
AUTORIZADA = "AUTORIZADA"
PARCIAL = "PARCIAL"
DESCONOCIMIENTO = "DESCONOCIMIENTO"
BLOQUEO_SEGURIDAD = "BLOQUEO_SEGURIDAD"
ERROR_CONTRATO = "ERROR_CONTRATO"
ERROR_DATOS = "ERROR_DATOS"

DESENLACES = (AUTORIZADA, PARCIAL, DESCONOCIMIENTO, BLOQUEO_SEGURIDAD,
              ERROR_CONTRATO, ERROR_DATOS)


def _es_bloqueo_seguridad(veredicto):
    """¿El fallo es de seguridad, o de otra cosa?

    No se adivina: se mira por que fallo. Un claim con apoyo inexistente, un
    tipo desconocido o texto prohibido son bloqueos de seguridad. Una
    respuesta sin `claims` es un fallo de contrato, no un ataque.
    """
    # Un intento de colar texto sin estructura, o de rehusar sin motivo, ES
    # un ataque: no un fallo de redaccion. Se enumeran aparte para que el
    # desenlace diga "intento de filtracion" y no "contrato mal formado".
    marcadores = ("forbidden", "inexistente", "divulgable", "fuga",
                  "contradictoria", "soporte", "tipos desconocidos",
                  "tipo desconocido", "coordenada", "intensificador",
                  "sin claims", "auditable", "motivo", "sin apoyo")
    for e in veredicto.get("errores") or []:
        bajo = str(e).lower()
        if any(m in bajo for m in marcadores):
            return True
    return False


def validar_respuesta_ia(salida, contexto, rec=None):
    """Valida la salida del modelo y devuelve un veredicto enriquecido.

    **Delega en `ia_contrato.validar_salida()`, que ya existe.** Aqui no se
    reimplementa ninguna regla: se le anaden dos cosas que solo el motor puede
    saber — la confianza calculada, y el desenlace.

    Lo que se comprueba, en resumen:
    estructura · referencias · procedencia · soporte vs tipo · verdad ·
    divulgacion · consistencia · informacion prohibida · confianza.
    """
    base = ioc.validar_salida(salida, contexto, rec=rec)
    veredicto = dict(base)
    # La confianza se calcula DESPUES de validar, y con el bloque de
    # verificacion que emite el contrato. Sin el, la confianza solo podria mirar
    # el `tipo` declarado (que elige el modelo), y daria confianza alta a
    # contenido que nadie ha comprobado. Ver `evaluar_confianza`.
    veredicto["confianza"] = evaluar_confianza(salida,
                                               veredicto.get("verificacion"))
    veredicto["confianza_declarada"] = confianza_declarada(salida)

    if veredicto.get("puede_entregarse"):
        veredicto["desenlace"] = AUTORIZADA
        return VeredictoIA(veredicto)

    # El resultado bloqueado NUNCA se devuelve como si fuera una respuesta.
    # Se clasifica, y el desenlace lo dice explicitamente.
    veredicto["desenlace"] = (BLOQUEO_SEGURIDAD if _es_bloqueo_seguridad(base)
                              else ERROR_CONTRATO)
    return VeredictoIA(veredicto)


class VeredictoIA(ioc.Veredicto):
    """El veredicto del motor: el del contrato, mas confianza y desenlace."""


# ============================================== 4. EL FLUJO COMPLETO =======
class Resultado(dict):
    """Lo que devuelve una consulta completa. Incluye todo, no solo el texto.

    Un motor que devuelve «la respuesta» y esconde por que la acepto o la
    rechazo no es auditable. Este devuelve el texto, el veredicto, el contexto
    que se uso y el registro tecnico.

    | clave        | que es                                        |
    |--------------|-----------------------------------------------|
    | `desenlace`  | uno de los seis de arriba                      |
    | `texto`      | lo que veria el jugador, o `None`              |
    | `veredicto`  | el resultado de validar                        |
    | `confianza`  | calidad del SOPORTE, calculada por el sistema |
    | `informe`    | el registro tecnico de la consulta             |
    """

    @property
    def entregable(self):
        return bool(self.get("puede_entregarse"))

    def __bool__(self):
        return bool(self.get("puede_entregarse"))


def ejecutar_consulta_ia(pregunta, mock, clave=None, consulta=None, tipo=None,
                         agente=None, modo=ioc.MODO_RAZONAMIENTO,
                         limite=None, estado=None, dataset_esperado=None,
                         auditoria=True, recuperador=None):
    """El flujo entero, sin LLM.

    ```
    CONSULTA → CONTEXTO → MOCK → RESPUESTA → VALIDACIÓN → VEREDICTO
    ```

    Y nada de eso cambia la semántica: el motor usa `ia_contexto` para el
    contexto y `ia_contrato` para validar. El mock solo ocupa el hueco donde
    un dia estara el modelo, y no puede hacer nada mas.
    """
    import dfchron.ia_contexto as cx          # import perezoso: carga 2,5 s

    informe = cx.consultar_contexto(
        pregunta, consulta=consulta, tipo=tipo, agente=agente, modo=modo,
        limite=limite if limite is not None else cx.LIMITE_CLAIMS,
        estado=estado, dataset_esperado=dataset_esperado, auditoria=auditoria,
        recuperador=recuperador)

    resultado = Resultado({"pregunta": pregunta, "informe": informe,
                           "texto": None, "veredicto": None,
                           "confianza": None, "puede_entregarse": False})

    if informe.get("fatal") or informe.get("error"):
        resultado["desenlace"] = (ERROR_DATOS
                                  if str(informe.get("error")).startswith(
                                      "error_datos")
                                  else ERROR_CONTRATO)
        return resultado

    contexto = informe.get("contexto")
    if contexto is None:
        resultado["desenlace"] = ERROR_CONTRATO
        return resultado

    # --- el modelo (o su simulacro) -------------------------------------
    try:
        salida = mock.invocar(contexto, clave)
    except c.ContratoInvalido as e:
        resultado["desenlace"] = ERROR_CONTRATO
        resultado["veredicto"] = VeredictoIA(
            {"puede_entregarse": False, "errores": list(e.errores),
             "claims_ok": 0, "claims_rechazados": [],
             "confianza": None, "desenlace": ERROR_CONTRATO})
        return resultado

    # --- validacion ------------------------------------------------------
    veredicto = validar_respuesta_ia(salida, contexto, rec=recuperador)
    resultado["veredicto"] = veredicto
    resultado["confianza"] = veredicto.get("confianza")
    resultado["puede_entregarse"] = bool(veredicto.get("puede_entregarse"))

    if not veredicto.get("puede_entregarse"):
        resultado["desenlace"] = veredicto.get("desenlace")
        # **Nada de texto.** Un resultado bloqueado no lleva texto al jugador.
        return resultado

    # --- entrega -------------------------------------------------------------
    # **El texto lo compone el SISTEMA, no el modelo.**
    #
    # Antes aqui se entregaba `salida["answer"]`: texto libre del modelo, tal cual.
    # Medido, ese canal dejaba pasar parafrasis, referencias espaciales,
    # sustracciones, nombres inventados y consejos que filtran. El modelo elige
    # QUE claims autorizados se dicen (ya validados arriba) y el sistema redacta.
    # `answer` se conserva como diagnostico y NO se entrega.
    texto, frontera = fr.componer_seguro(salida.get("claims") or [], contexto)
    if texto is None:
        # La composicion no cuadra con los claims: no se entrega nada. Falla
        # cerrado y explica por que, para que no parezca un silencio.
        resultado["desenlace"] = BLOQUEO_SEGURIDAD
        resultado["violaciones_frontera"] = list(frontera.get("violaciones") or [])
        resultado["answer_del_modelo"] = salida.get("answer")
        return resultado
    resultado["texto"] = texto
    resultado["answer_del_modelo"] = salida.get("answer")
    if informe.get("vacio"):
        # Contexto vacio con respuesta entregable: el sistema no sabe. Eso es
        # una respuesta legitima, no un fallo.
        resultado["desenlace"] = DESCONOCIMIENTO
    elif (informe.get("reduccion") or {}).get("truncado"):
        resultado["desenlace"] = PARCIAL
    else:
        resultado["desenlace"] = AUTORIZADA
    return resultado