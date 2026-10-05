#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: FRONTERA LINGUISTICA (fundacion de seguridad)
=============================================================

LA FUGA QUE ESTE MODULO EXISTE PARA CERRAR
-------------------------------------------
El campo `answer` es texto libre escrito por el modelo y se entrega al jugador.
Medido por el camino real, TODO esto pasaba la validacion y llegaba al jugador:

    "Esta mucho mas alla de donde estas."      -> AUTORIZADA
    "Queda hacia donde brilla el amanecer."    -> AUTORIZADA
    "Quedan 733 sin explorar."                 -> AUTORIZADA
    "Se llama Torre Sombra del Norte"          -> AUTORIZADA
    "Mejor no acerques por ahi."                -> AUTORIZADA
    "No hay nada de valor al norte."            -> AUTORIZADA

Seis vectores, una sola causa: **el modelo redacta el texto**. Mientras el texto
lo escriba el modelo no hay frontera posible, porque filtrar seria una propiedad
del modelo y no del sistema. Y el modelo es un componente NO confiable.

LA DECISION
-----------
    El modelo **no** redacta el texto que ve el jugador.

Pasa a ser un **selector**: elige QUE afirmaciones autorizadas se dicen y con que
tipo. El texto lo compone el sistema, por composicion literal de lo que el
contexto ya autorizo.

Eso convierte seis problemas semanticos en UNO determinista:

    Cada palabra con carga informativa del texto tiene que existir en el claim
    que la respalda.

De ahi sale, sin modelo y sin embeddings:

  | fuga                  | por que la detiene                          |
  |-----------------------|--------------------------------------------|
  | A. parafrasis          | "brilla", "amanecer" no estan en el claim  |
  | B. referencia espacial | "norte" no esta en el claim                |
  | C. sustraccion         | "733" no esta en el claim                  |
  | D. distancia           | "dieciocho", "tiles" no estan              |
  | E. nombre inventado    | "Torre", "Sombra" no estan                  |
  | F. consejo filtrador   | "ahi" es deictico: no esta en el claim     |

NO es un filtro de palabras prohibidas, que es lo que hay hoy y lo que no
funciona: para "733" o "Torre Sombra del Norte" no existe coincidencia literal
que buscar. Es lo contrario: **una lista blanca de lo que SI puede aparecer**,
derivada de los claims autorizados.

POR QUE UNA LISTA BLANCA Y NO UNA NEGRA
--------------------------------------
Una lista negra es infinita: el modelo puede decir "al otro lado de donde estas".
Una lista blanca es **finita y auditada**: el modelo solo puede usar el
vocabulario que el sistema le entrego.

DEFENSA EN PROFUNDIDAD, NO SUSTITUCION
--------------------------------------
Este modulo **anade** una capa; no reemplaza ninguna:

  1. `contrato_ia`  decide verdad/visibilidad/divulgacion   (sigue siendo la ley)
  2. `ia_contrato`  valida procedencia y coherencia de claims (sigue igual)
  3. `ia_frontera`  comprueba que el TEXTO no exceda a los claims (nuevo)
  4. el validador numerico detecta reconstruccion indirecta  (nuevo)

Si se desactivara la capa 3 el sistema seguiria siendo seguro frente a lo que ya
sabia; lo que se pierde es la garantia de que el texto no exceda a los claims.
Por eso es profundidad, no el muro unico.

DETERMINISMO
------------
Sin relojes, sin azar, sin UUID, sin `set` sensible al orden. Mismas entradas,
mismo veredicto, byte a byte. `frozenset` se usa solo para pertenencia y toda
salida se ordena antes de serializarse.

Ejecutar:  python dfchron/pruebas/probar_frontera_linguistica.py
"""
import os
import re
import sys
import unicodedata

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from dfchron import contrato_ia as c          # noqa: E402

SCHEMA_FRONTERA = "frontera-1"


# ==================================================== NORMALIZACION ========
#: Todo el analisis de texto pasa por aqui y por ningun otro sitio. Si dos
#: partes normalizaran distinto, compararian cosas distintas, y ese fallo es el
#: unico que no se puede reproducir cuando aparece.
def normalizar(texto):
    """Minusculas, sin acentos, sin depender del teclado de quien escribio.

    Se usa `unicodedata.normalize` y no una tabla de acentos a mano: una tabla se
    queda vieja en cuanto aparece un caracter nuevo, y el fallo seria que un
    token deja de detectarse. Aqui el criterio es el del estandar.
    """
    if not isinstance(texto, str):
        return ""
    t = unicodedata.normalize("NFC", texto).lower()
    # Las tildes y la enye se descomponen a la base, para que "norte" y la misma
    # palabra acentuada comparen igual sin depender del writer del dato.
    return "".join(ch for ch in unicodedata.normalize("NFD", t)
                   if unicodedata.category(ch) != "Mn")


#: Palabras que NO aportan informacion del mundo: gramatica pura.
#:
#: Esta lista es el unico punto del sistema donde se admite texto que NO venia de
#: un claim, y por eso es **finita, corta y publica**. Esa es la justificacion
#: tecnica de por que esto no es un canal de fuga:
#:
#:     Un conjunto FINITO y FIJO de palabras que no nombran nada del mundo no
#:     puede codificar un secreto. No hay inyeccion posible: no hay donde meterla.
#:
#: Lo que decide el significado es el `tipo` del claim, que ya esta validado.
#: Cambiar "es" por "vale" no cambia lo que se afirma.
#:
#: CRITERIO DE ADMISION, revisable y no arbitrario: entra una palabra si NO puede
#: nombrar ni describir entidad, lugar, cantidad, direccion, distancia ni propiedad
#: de ESTA partida. Por eso "norte" NO entra (es direccion) y "es" si.
_FUNCIONAL = frozenset("""
a al algo algun alguna alguno algunos ante antes aqui aun aunque bajo bien cada
casi como con contra cual cuales cuando cuanto de del desde donde dos e el ella
ellas ellos en entre era eran eres es esa esas ese eso esos esta estaban estan
estas este esto estos estoy fue fueron ha habia han hasta hay la las le les lo
los mas me mi mientras mio mis misma mismo mucho muy ni no nos nosotros nuestra
nuestro o os otra otro para pero poco por porque pues que quien quienes se sea
segun ser si sido siempre sin sobre solamente solo son soy su sus tambien tan
tanto te tener tengo ti tiene tienen toda todas todo todos tras tu tus un una
unas uno unos usted ustedes va vamos van ver vez y ya yo
""".split())

#: Palabras que NUNCA entran en la lista funcional, aunque lo pidan. Aqui esta la
#: decision dura, y se escribe para que se pueda discutir:
#:
#:   * deicticos ("ahi", "alli"): dependen del punto de vista del jugador y son la
#:     via por la que un consejo filtrador dice "no mires ahi".
#:   * direcciones: son la fuga B, con mayuscula o sin ella.
#:   * negaciones ("nada", "nadie"): "no hay nada de valor al norte" son dos fugas
#:     en una frase, la direccion y la negacion.
#:   * aproximaciones ("cerca", "lejos"): son la fuga D.
_FUNCIONAL_PROHIBIDO = frozenset("""
nada nadie ninguno ninguna norte sur este oeste arriba abajo cerca lejos
aproximadamente alrededor detras delante encima debajo
""".split())

#: Deicticos y direcciones, para el DIAGNOSTICO. No bloquean por si mismos: ya
#: estan bloqueados por no estar en el vocabulario autorizado. Se listan para que
#: el motivo del rechazo sea legible por una persona y no solo por una maquina.
_TERMINOS_SOSPECHOSOS = frozenset("""
norte sur este oeste arriba abajo cerca lejos alrededor detras delante
encima debajo donde cuando mientras
""".split())


def _es_funcional(palabra):
    """Â¿Es gramatica pura, admitible sin venir de un claim?"""
    return palabra in _FUNCIONAL and palabra not in _FUNCIONAL_PROHIBIDO


#: Corte de palabra: por caracteres no alfanumericos. Se descartan los tokens de
#: un solo caracter porque no sostienen informacion y multiplicarian los falsos
#: positivos ("a", "y", "o").
def _tokens(texto):
    limpio = normalizar(texto)
    return frozenset(p for p in re.split(r"[^a-z0-9]+", limpio) if len(p) > 1)


#: Cifras, incluidos los millares con separador ("1,234" -> 1234). Se tratan
#: aparte de las palabras porque una cifra NUNCA es gramatica: siempre es un dato,
#: y por eso se comprueba contra los claims siempre y sin excepcion.
_RE_CIFRA = re.compile(r"\d+(?:[.,]\d+)*")


def _cifras(texto):
    """Cifras explicitas del texto, normalizadas a su valor entero.

    "setecientos treinta y tres" escrito con palabras no se resuelve aqui: lo
    cubre el vocabulario, porque esas palabras no estan en los claims y por tanto
    no pueden aparecer. Aqui solo las cifras escritas con digitos.
    """
    salida = set()
    for m in _RE_CIFRA.finditer(normalizar(texto)):
        try:
            salida.add(int(m.group(0).replace(".", "").replace(",", "")))
        except ValueError:                                   # pragma: no cover
            continue
    return frozenset(salida)


#: Nombres propios citados, en forma normalizada. Se extraen aparte porque son el
#: objetivo preferente de la fuga E (entidades inventadas), y porque un nombre
#: propio es la clase de token donde un parecido "aproximado" es inaceptable: o
#: es el nombre que consta en el claim, o no lo es.
_RE_PROPIO = re.compile(
    r"\b[A-ZÃÃ‰ÃÃ“ÃšÃ‘Ãœ][\wÃÃ‰ÃÃ“ÃšÃ‘ÃœÃ¡Ã©Ã­Ã³ÃºÃ±Ã¼'-]*"
    r"(?:\s+[A-ZÃÃ‰ÃÃ“ÃšÃ‘Ãœ][\wÃÃ‰ÃÃ“ÃšÃ‘ÃœÃ¡Ã©Ã­Ã³ÃºÃ±Ã¼'-]*)*")


def nombres_propios(texto):
    """Nombres propios citados, normalizados.

    Solo se consideran los que empiezan por mayuscula en el texto ORIGINAL: en
    espanol es la convencion que sostiene el dataset, y aplicarla sobre el texto
    ya normalizado daria un falso positivo en cada frase.
    """
    if not isinstance(texto, str):
        return frozenset()
    salida = set()
    for m in _RE_PROPIO.finditer(unicodedata.normalize("NFC", texto)):
        partes = [p for p in m.group(0).strip().split() if len(p) > 1]
        if not partes:
            continue
        # Una palabra capitalizada suelta suele ser el inicio de frase, no un
        # nombre. Se descarta cuando es gramatica pura.
        if len(partes) == 1 and normalizar(partes[0]) in _FUNCIONAL:
            continue
        salida.add(" ".join(normalizar(p) for p in partes))
    return frozenset(salida)


def texto_del_claim(cl):
    """El texto legible de un claim, tanto de contexto como de salida."""
    if not isinstance(cl, dict):
        return ""
    return cl.get("claim") or cl.get("texto") or ""


# ============================================ 1. VOCABULARIO AUTORIZADO =====
def vocabulario_de(claims):
    """El unico vocabulario que la salida puede usar. Sale de los claims.

    Devuelve `(palabras, cifras)`: las palabras con carga informativa y las
    cifras que esos claims contienen. Es una lista blanca derivada de la
    autorizacion, no una constante escrita a mano, y por eso no puede
    desincronizarse del contrato.
    """
    palabras, cifras = set(), set()
    for cl in claims or []:
        texto = texto_del_claim(cl)
        palabras |= {p for p in _tokens(texto) if not _es_funcional(p)}
        cifras |= _cifras(texto)
    return frozenset(palabras), frozenset(cifras)


# ===================================== 2. TRAZABILIDAD DEL TEXTO (NUEVO) ===
class ResultadoFrontera(dict):
    """Veredicto de la frontera. Objeto, nunca un booleano suelto.

    | clave                     | que significa                            |
    |---------------------------|------------------------------------------|
    | `texto_permitido`         | el texto tal cual puede entregarse       |
    | `violaciones`             | por que no, si no puede                   |
    | `palabras_no_autorizadas` | palabras del texto sin respaldo en claim |
    | `cifras_no_autorizadas`   | numeros del texto sin respaldo            |
    | `entidades_no_autorizadas`| nombres que no constan                   |
    """

    __slots__ = ()

    @property
    def permitido(self):
        return bool(self.get("texto_permitido"))

    def __bool__(self):
        return bool(self.get("texto_permitido"))


def _fallo(violaciones, palabras=(), cifras=(), entidades=()):
    return ResultadoFrontera({
        "texto_permitido": False,
        "violaciones": list(violaciones),
        "palabras_no_autorizadas": sorted(palabras),
        "cifras_no_autorizadas": sorted(cifras),
        "entidades_no_autorizadas": sorted(entidades),
    })


def _permite():
    return ResultadoFrontera({
        "texto_permitido": True, "violaciones": [],
        "palabras_no_autorizadas": [], "cifras_no_autorizadas": [],
        "entidades_no_autorizadas": []})


def comprobar_texto(texto, claims_salida, ctx):
    """¿El TEXTO ENTREGADO dice algo que los claims no dicen?

    Es una comprobacion de **lista blanca** sobre lo que realmente va a ver el
    jugador:

        una palabra con carga informativa tiene que existir en el claim que la
        respalda, o ser vocabulario del propio SISTEMA.

    Lo que el sistema dice por su cuenta (el prefijo "No consta.", el motivo de un
    `NON_DISCLOSURE`) esta autorizado por definicion: lo escribio el sistema, no
    el modelo, y no nombra nada del mundo. Sin esa excepcion, la comprobacion
    marcaria al propio sistema, que es un falso positivo que hace inutil la capa.

    NO se comprueba aqui el `texto` de cada claim de salida: ese texto ya no se
    entrega (el sistema compone con el del contexto), asi que medirlo seria
    rechazar por palabras que el jugador nunca va a leer.

    Devuelve un `ResultadoFrontera`. No lanza: un fallo de seguridad tiene que ser
    visible como veredicto, no como excepcion que alguien se come.
    """
    if not isinstance(texto, str) or not texto.strip():
        # Sin texto no hay nada que filtrar. No es un fallo: es una respuesta
        # vacia, y el motor ya decidio antes si eso es legitimo.
        return _permite()

    recibido = {cl["ref"]: cl for cl in (ctx.get("claims") or [])
                if isinstance(cl, dict) and "ref" in cl}

    # El vocabulario REAL de esta salida es el de SUS PROPIOS apoyos, no el de
    # todo el contexto. Medir contra todo el contexto abriria una via lateral: un
    # claim podria usar una palabra que solo esta autorizada por OTRO claim que
    # no le apoya, y el filtro pasaria sin que nadie lo autorizara para esa
    # afirmacion concreta.
    apoyos, propios_autorizados = [], set()
    for cl in claims_salida or []:
        if not isinstance(cl, dict):
            continue
        for r in (cl.get("soporte") or []):
            base = recibido.get(r)
            if base is None:
                continue
            apoyos.append(base)
            propios_autorizados |= nombres_propios(texto_del_claim(base))
    vocab_salida, cifras_salida = vocabulario_de(apoyos)
    # El vocabulario del SISTEMA esta autorizado siempre: lo escribio el sistema.
    vocab_salida = vocab_salida | _vocabulario_del_sistema()

    palabras = {p for p in _tokens(texto) if not _es_funcional(p)}
    palabras_no = palabras - vocab_salida
    cifras_no = _cifras(texto) - cifras_salida
    entidades_no = nombres_propios(texto) - propios_autorizados

    if palabras_no or cifras_no or entidades_no:
        v = []
        if palabras_no:
            v.append("el texto usa palabras sin respaldo en los claims que lo "
                     "sostienen: %s" % ", ".join(sorted(palabras_no)))
        if cifras_no:
            v.append("el texto usa cifras sin respaldo en los claims que lo "
                     "sostienen: %s"
                     % ", ".join(str(x) for x in sorted(cifras_no)))
        if entidades_no:
            v.append("el texto cita entidades que no constan en los claims: %s"
                     % ", ".join(sorted(entidades_no)))
        return _fallo(v, palabras_no, cifras_no, entidades_no)
    return _permite()


# ============================= 3. COMPOSICION (el sistema redacta) =========
#: Prefijos por tipo. Son del SISTEMA y son FIJOS: describen COMO se dice un
#: claim, nunca QUE se dice. Todo lo que sigue al prefijo es texto del claim que
#: la propia plataforma produjo, citado literalmente.
#:
#: Aqui esta la decision que hace que la frontera no tenga falsos positivos:
#:
#:     **El modelo NO aporta ni una palabra al texto entregado.**
#:
#: La primera version de este modulo componia con el `texto` que escribia el
#: modelo y luego lo comparaba con una lista blanca de vocabulario. Medido, eso
#: rechazaba respuestas legitimas ("No consta en los datos." no usa palabras del
#: claim que lo sostiene) y ademas dejaba al modelo decidir la redaccion, que es
#: justo el problema que se queria cerrar.
#:
#: Ahora el modelo elige QUE claims se dicen y con que TIPO; el texto lo pone la
#: plataforma,quoting el claim. Asi no hay nada que comparar: la comparacion se
#: vuelve innecesaria porque la fuente del texto ya esta autorizada por
#: construccion. `comprobar_texto` se conserva como capa independiente, para el
#: caso de que alguien conecte un adaptador que traiga texto propio.


#: Prefijos del sistema, por tipo de claim de salida. Describen COMO se dice un
#: claim, nunca QUE se dice: el contenido viene del claim, ya autorizado.
#:
#: Se escribe en espanol escueto y sin adjetivos a proposito. Anadir adorno a un
#: prefijo seria abrir un canal nuevo con las manos, asi que aqui no cabe el
#: estilo: solo palabras que no nombran nada del mundo.
_PREFIJOS = {
    "FACT": "",
    "DERIVED": "",
    "INTERPRETATION": "",
    "ADVICE": "",
    "UNKNOWN": "No consta. ",
    "NON_DISCLOSURE": "No puedo decirte eso: ",
    "MECHANIC_EXPLANATION": "Sobre las reglas del juego: ",
}


def _vocabulario_del_sistema():
    """Palabras que el SISTEMA dice por su cuenta, y por eso estan autorizadas.

    Sin esta excepcion, `comprobar_texto` marcaria al propio sistema: el prefijo
    "No consta." no aparece en ningun claim, y el filtro lo leeria como una fuga
    que el propio sistema ha cometido. Eso no es defensa: es un falso positivo
    que hace la capa inutil y empuja a desactivarla.

    Se construye A PARTIR de los prefijos, no a mano, para que no se puedan
    desincronizar: si alguien edita un prefijo, la lista se actualiza sola.
    """
    palabras = set()
    for prefijo in _PREFIJOS.values():
        palabras |= {p for p in _tokens(prefijo) if not _es_funcional(p)}
    # Las razones legibles del sistema tambien son suyas, y se derivan de la
    # MISMA tabla que usa `motivo_legible()`. Si se escribieran a mano aqui, las
    # dos listas podrian separarse y el filtro marcaria al propio sistema.
    for motivo in _MOTIVOS_LEGIBLES.values():
        palabras |= {p for p in _tokens(motivo) if not _es_funcional(p)}
    # Y la redaccion de coordenadas, que tambien es texto del SISTEMA: sin esto,
    # `comprobar_texto` rechazaria su propia sustitucion.
    for frase in (_REDACCION, _SIN_COORDENADAS):
        palabras |= {p for p in _tokens(frase) if not _es_funcional(p)}
    return frozenset(palabras)


#: Traduccion de los motivos de `NON_DISCLOSURE` a lenguaje llano.
#:
#: Es una tabla **FIJA y exhaustiva** a proposito. El motivo crudo es un valor
#: interno del contrato (`PLAYER_HIDDEN`, `FORBIDDEN`, `WORLD_KNOWLEDGE`...) y
#: entregarlo tal cual seria una fuga NUEVA: el jugador no necesita conocer los
#: nombres internos de la plataforma, solo la razon.
#:
#: Lo que NO esta en la tabla no se enseña: se usa la razon generica. Asi, anadir
#: un estado interno nuevo no filtra por olvido, y el comportamiento es fail-closed
#: por construccion y no por revision.
_MOTIVOS_LEGIBLES = {
    "PLAYER_HIDDEN": "no lo has descubierto todavia",
    "FORBIDDEN": "no puedo contartelo",
    "WORLD_KNOWLEDGE": "aun no lo sabes",
    "EXTERNAL_KNOWLEDGE": "eso no es un dato de tu partida",
    "CONDITIONAL": "no puedo afirmarlo todavia",
    "UNKNOWN": "no consta en los datos",
    "no_descubierto": "no lo has descubierto todavia",
}
_MOTIVO_GENERICO = "no puedo contartelo"


def motivo_legible(motivo):
    """Traduce un motivo interno a lenguaje que puede leer el jugador.

    Fail-closed: un motivo desconocido NO se enseña tal cual, se sustituye por la
    razon generica. Asi, anadir un estado interno nuevo no filtra nada por
    olvido, y el jugador nunca ve un identificador del contrato.
    """
    if not isinstance(motivo, str):
        return _MOTIVO_GENERICO
    return _MOTIVOS_LEGIBLES.get(motivo.strip(), _MOTIVO_GENERICO)


#: El banco de pruebas declara prohibido el literal "112" en B-08 ("Tengo
#: coordenadas de halesteel. ¿Me confirmas el tipo?"). El sistema, en cambio,
#: autorizaba la afirmacion porque el estado del jugador marca `coordenadas` como
#: conocido, y componia el claim tal cual:
#:
#:     "El sitio esta en las coordenadas '(112, 20)'."
#:
#: Antes de este cambio eso NO se deliveraba, no porque el sistema lo protegiera,
#: sino porque el modelo por casualidad escribio otra frase. El banco pasaba de
#: suerte, no por diseno. Compuesto por el sistema, el literal aparece, y
#: `deteccion_fuga()` (que ya prohibia coordenadas en texto entregado) lo rechaza.
#:
#: Hay aqui dos politicas que se contradicen, y la contradccion es REAL, no un
#: fallo mio:
#:
#:     `puede_revelarse()`  ->  las coordenadas SON divulgables (el jugador las conoce)
#:     `deteccion_fuga()`   ->  las coordenadas NO se entregan en texto
#:
#: La que se aplica al salir es la SEGUNDA, desde antes de este cambio. La
#: resolucion que se toma aqui es la CONSERVADORA y la coherente con esa politica:
#:
#:     Se puede AFIRMAR que las coordenadas constan en el registro del jugador.
#:     No se entrega el TRIPLET literal.
#:
#: Se distingue porque son dos afirmaciones distintas, y solo una es un spoiler:
#: "tienes esto anotado" es un hecho sobre el jugador; "112, 20" es la posicion de
#: un sitio todavia sin explorar. Es la misma separacion que sostiene el contrato
#: entre `FACT` y `DISCLOSURE`: verdad y permiso no son lo mismo.
#:
#: Es MAS conservador que cada politica por separado, de modo que resolver el
#: conflicto no cuesta seguridad: lo que se acota es la REDACCION, nunca el
#: control.
_RE_TRIPLETE = re.compile(r"\(?\b\d{1,4}\s*,\s*-?\d{1,4}\s*,\s*-?\d{1,4}\b\)?")
_RE_PAR = re.compile(r"\(?\b\d{1,4}\s*,\s*-?\d{1,4}\b\)?")

#: `_REDACCION` se usa SOLO cuando no hay una formula mejor, y no dentro de una
#: frase que ya hablaba de coordenadas: sustituir dentro de la frase produce
#: "esta en las coordenadas 'unas coordenadas registradas'", que no es espanol y
#: delata que hubo un recorte. Para ese caso hay `_SIN_COORDENADAS` mas abajo.
_REDACCION = "unas coordenadas registradas"

#: Sustitucion para la afirmacion "las coordenadas constan en el registro". Es una
#: afirmacion sobre lo que el JUGADOR sabe, no sobre donde esta el sitio, y por eso
#: se puede decir sin decir la posicion. Es la distincion que hace B-08
#: razonable: el jugador sabe que las tiene anotadas; no tiene por que leer donde.
_SIN_COORDENADAS = "Las coordenadas constan en tu registro."


def redactar_coordenadas(texto):
    """Sustituye coordenadas estructuradas por una mencion sin posicion.

    Determinista y total: si no hay coordenadas, devuelve el texto intacto. Se
    aplica al texto COMPUESTO, nunca a un claim del contexto (que se conserva
    integro para auditoria: alli la coordenada es el dato, y quitarla seria
    perder procedencia).
    """
    if not isinstance(texto, str) or not texto:
        return texto
    # Una afirmacion que YA hablaba de coordenadas se sustituye entera: decir
    # "esta en las coordenadas 'unas coordenadas registradas'" no es espanol y
    # ademas delata que hubo un recorte. Aqui se dice lo unico que es cierto y no
    # posiciona: que el jugador las tiene anotadas.
    if _RE_TRIPLETE.search(texto) or _RE_PAR.search(texto):
        return _SIN_COORDENADAS
    return texto


def componer(claims_salida, ctx):
    """Compone el texto del jugador. Determinista y sin redaccion del modelo.

    **El texto sale de los claims del CONTEXTO**, que son los que la plataforma
    construyo con su procedencia, no de los que escribio el modelo. El modelo
    aporta la seleccion y el tipo; nunca las palabras.

    Por eso esto no necesita ser "fiel": no hay nada que el modelo pueda
    desviar, porque no hay texto suyo en el resultado.

    Determinista: mismos `claims_salida` y mismo `ctx`, mismo texto, byte a byte.
    """
    recibido = {cl["ref"]: cl for cl in (ctx.get("claims") or [])
                if isinstance(cl, dict) and "ref" in cl}
    partes, vistos = [], set()
    for cl in claims_salida or []:
        if not isinstance(cl, dict):
            continue
        tipo = cl.get("tipo")
        if tipo not in _PREFIJOS:
            # Un tipo desconocido no se renderiza: no se inventa una plantilla
            # para algo que el contrato no conoce. Falla cerrado.
            continue
        if tipo == "NON_DISCLOSURE":
            # El motivo lo pone el SISTEMA y es un valor interno del contrato
            # (`PLAYER_HIDDEN`, `FORBIDDEN`...). Entregarlo tal cual al jugador
            # seria una fuga NUEVA: el jugador no deberia conocer los estados
            # internos de la plataforma. Se traduce a lenguaje llano con
            # `motivo_legible()`, que es una tabla FIJA y exhaustiva: lo que no
            # este en la tabla no se enseña, se dice la razon generica. Es
            # fail-closed por construccion.
            partes.append(_PREFIJOS[tipo] + motivo_legible(cl.get("motivo")) + ".")
            continue
        # El texto citado es el del CLAIM DE CONTEXTO, nunca el del modelo.
        citas = [texto_del_claim(recibido[r]) for r in (cl.get("soporte") or [])
                 if r in recibido]
        # La redaccion de coordenadas se aplica AQUI, al texto que sale hacia el
        # jugador. El claim del contexto se conserva intacto para auditoria:
        # alli la coordenada es el dato, y borrarla seria perder procedencia.
        citas = [redactar_coordenadas(t).strip() for t in citas if t]
        # Se deduplican: dos claims que apoyan en el mismo dato no lo repiten.
        nuevas = [t for t in citas if t and t not in vistos]
        if not nuevas:
            continue
        vistos.update(nuevas)
        partes.append(_PREFIJOS[tipo] + " ".join(nuevas))
    return " ".join(p for p in partes if p)


def componer_seguro(claims_salida, ctx):
    """Compone y comprueba. Devuelve `(texto, ResultadoFrontera)`.

    Es el camino que debe usarse para entregar al jugador: compone con el
    sistema y verifica que el texto no exceda a los claims. El texto devuelto es
    `None` si algo no cuadra, porque un texto no comprobado no debe llegar al
    jugador aunque la composicion sea inocua.

    UNA SOLA SALIDA, UN SOLO CRITERIO
    ---------------------------------
    Aqui se aplican **las mismas** comprobaciones que se aplicaban al texto del
    modelo: la lista blanca de `comprobar_texto()` Y `deteccion_fuga()`.

    Eso no es Belt-and-suspenders, es una correccion medida. `deteccion_fuga()`
    ya prohibia entregar coordenadas estructuradas, pero como corria ANTES de la
    composicion solo vigilaba el texto del modelo: el texto compuesto se salia de
    esa regla sin querer. Medido, B-08 devolvia

        "El sitio esta en las coordenadas '(112, 20)'."

    cuando el mismo texto pasado por `deteccion_fuga` ya se rechazaba. Un criterio
    de salida unico evita que la seguridad dependa de QUIEN redacta.
    """
    texto = componer(claims_salida, ctx)
    veredicto = comprobar_texto(texto, claims_salida, ctx)
    if not veredicto.permitido:
        return None, veredicto

    # La deteccion de fugas vive en `ia_contrato`: no se duplica ni se reimplementa
    # aqui, se usa la que ya existe. Import perezoso para no crear un ciclo con el
    # modulo que ya la invoca.
    from dfchron import ia_contrato as ioc
    fugas = ioc.deteccion_fuga(texto, ctx)
    if fugas:
        return None, _fallo(["fuga indirecta: %s" % f for f in fugas])
    return texto, veredicto


# ==================== 4. RECONSTRUCCION INDIRECTA (el numero que no esta) ==
#: La categoria que un filtro de texto NO puede ver:
#:
#:     TOTAL = 734
#:     ENCONTRADOS = 1
#:
#:     RESTANTES = 733
#:
#: El 733 nunca aparece en ninguna respuesta. Y sin embargo se sabe. Por eso
#: "no contiene el secreto" y "no permite reconstruir el secreto" son DOS
#: propiedades distintas, y hay que probarlas por separado.
#:
#: Lo que hace este detector es aritmetica EXPLICITA sobre las cifras que el
#: sistema ha autorizado. No adivina: solo comprueba si el texto presenta una
#: cuenta cuyos operandos son todos autorizados y cuyo resultado es un dato
#: retenido. Si el resultado esta retenido, la cuenta ES la fuga.
#:
#: NO se resuelve aqui la reconstruccion puramente semantica ("queda hacia el
#: norte" reconstruye una direccion). Eso no es aritmetica y no se finge lo
#: contrario: `comprobar_texto` lo cubre por la via del vocabulario.
_RE_CUENTA = re.compile(
    r"(?P<a>\d[\d.,]*)\s*(?P<op>[-+*/])\s*(?P<b>\d[\d.,]*)")


def _a_entero(bruto):
    try:
        return int(str(bruto).replace(".", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def detectar_reconstruccion(texto, ctx, retenidas=()):
    """Comprueba si el texto reconstruye, por cuenta, un dato retenido.

    Args:
        texto:     el texto que veria el jugador.
        ctx:       el contexto; sus claims son las cifras autorizadas.
        retenidas: cifras que el sistema sabe y NO ha autorizado. Si el texto las
                   reconstruye por aritmetica, es una fuga aunque no las escriba.

    `retenidas` la pasa quien llama y por defecto esta vacia: con la lista vacia
    no se puede acusar a nadie de nada. Es explicita a proposito, para que la
    deteccion no dependa de que este modulo adivine que es un secreto.
    """
    if not isinstance(texto, str) or not texto.strip():
        return []
    _, cifras_ok = vocabulario_de((ctx.get("claims") or []))
    retenidas = set(int(x) for x in (retenidas or ()))
    fugas = []
    for m in _RE_CUENTA.finditer(normalizar(texto)):
        a, b, op = _a_entero(m.group("a")), _a_entero(m.group("b")), m.group("op")
        if a is None or b is None:
            continue
        # Se exige que los DOS operandos estuvieran autorizados. Una cuenta con
        # un operando desconocido no se puede atribuir a este detector, y
        # acusar sin pruebas seria inventar una fuga.
        if a not in cifras_ok or b not in cifras_ok:
            continue
        if op == "+":
            r = a + b
        elif op == "-":
            r = a - b
        elif op == "*":
            r = a * b
        else:
            if not b:
                continue
            r = a // b
        # Se marca cuando el RESULTADO es un dato retenido: eso es literalmente
        # la fuga, y no una conjetura sobre ella.
        if r in retenidas:
            fugas.append("el texto reconstruye por cuenta el dato retenido %d "
                         "(%d %s %d): el resultado no aparece escrito, pero es "
                         "deducible" % (r, a, op, b))
    return fugas


if __name__ == "__main__":                                   # pragma: no cover
    print(__doc__)
