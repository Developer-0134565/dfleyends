#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: MOTOR DE CONTEXTO real
========================================

Este modulo convierte el contrato en algo que funciona con los datos de verdad
de DF-Chronicles. No inventa una segunda politica: **reutiliza** las que ya
existen y solo hace de puente entre el nucleo y el contrato de E/S.

    nucleo.Archivo  (48 metodos de solo lectura)
          │
          ▼
    ia_conocimiento.Puente        ← ya existe: envuelve en afirmaciones
          │
          ▼
    ESTE MODULO                  ← recuperación, seleccion, minimizacion
          │                        y auditoria de dependencias
          ▼
    ia_contrato.contexto()        ← ya existe: filtra y construye ContextoIA

QUE NO HACE
-----------
* No implementa la politica de divulgacion. La pide a `contrato_ia`.
* No implementa la validacion de salida. La pide a `ia_contrato`.
* No escribe en el dataset. **Ni un byte.**
* No escribe en el estado del jugador. Una consulta es de solo lectura.
* No inventa identificadores. Si el nucleo no da un id, no lo hay.
* No completa huecos. Si no encuentra, devuelve lo que encontró y lo dice.

DETERMINISMO
------------
Sin relojes, sin azar, sin UUID. El mismo dataset y el mismo estado producen el
mismo contexto, byte a byte. Verificado por `probar_ia_contexto.py`.

Ejecutar:  python dfchron/pruebas/probar_ia_contexto.py
"""
import os
import re
import sys

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

from dfchron import contrato_ia as c            # noqa: E402
from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_conocimiento as ic        # noqa: E402
from dfchron import ia_contrato as ioc          # noqa: E402
#: Los conversores de identificador del puente. Se reutilizan los suyos en vez
#: de escribir otros: el nucleo indexa figuras y sitios por texto, y el resto
#: por entero. Reescribir esa regla seria una segunda verdad sobre los ids.
from dfchron.ia_conocimiento import (            # noqa: E402
    _como_id, _como_id_entidad)

# ================================================== 1. LIMITES =============
#: Límites EXPLICITOS, y no arbitrarios. Cada uno es un número pequeño y
#: justificado, y cuando salta se REGISTRA. Perder en silencio es peor que
#: devolver menos de lo que se podria.
LIMITE_CLAIMS = 24
LIMITE_EVIDENCIAS_POR_CLAIM = 6
LIMITE_FICHAS_POR_BUSQUEDA = 8

#: Tipos que el nucleo indexa de verdad. Se declara en vez de deducirse, para
#: que anadir uno sea una decision visible y no un efecto secundario.
TIPOS_RECUPERABLES = ("figura", "entidad", "sitio", "evento", "artefacto")

#: Las relaciones NO se recuperan. El nucleo no les da identificador estable
#: (`relaciones_de_figura()` devuelve objetos sin `id`), y esta mision tiene
#: prohibido inventarlo. Se declara aqui para que no parezca un olvido.
TIPOS_NO_RECUPERABLES = ("relacion",)


class ConsultaInvalida(c.ContratoInvalido):
    """La peticion no tiene sentido. Falla al entrar, no al responder."""


# ============================================ 2. LO QUE YA EXISTE ==========
#: El dataset activo. Se lee de `dataset_version.json`, que no se inventa.
def dataset_id():
    """El identificador del dataset realmente cargado. Sin reloj."""
    return ic.DATASET_ID


def comprobar_dataset(esperado=None):
    """¿Estamos sobre el dataset que el estado del jugador cree?

    Es una comprobacion real: si el dataset se ha regenerado y el estado del
    jugador es del anterior, sus marcas de «descubierto» ya no significan lo
    mismo. Detectar eso aqui es mas barato que descubrirlo en una respuesta.
    """
    activo = dataset_id()
    if esperado is not None and str(esperado) != activo:
        return False, ("el dataset activo (%s) no es el que se consultó (%s)"
                       % (activo, esperado))
    estado = ec.EstadoConocimiento()
    comp = estado.compatibilidad()
    if isinstance(comp, dict):
        declar = comp.get("dataset_id")
        if declar and str(declar) != activo:
            return False, ("el estado del jugador pertenece al dataset %s y "
                           "el activo es %s" % (declar, activo))
    return True, None
def estado_del_jugador(estado=None):
    """El estado persistente, o el de este proceso."""
    return ec._estado(estado)


# ================================================ 3. RECUPERACION ==========
#: De tipo del nucleo a la funcion de busqueda real. Se declara en vez de
#: deducirse: un `getattr` por nombre de metodo seria una dependencia invisible.
_BUSCADORES = {
    "figura": "buscar_figura",
    "entidad": "buscar_entidad",
    "sitio": "buscar_sitio",
    "evento": "buscar_evento",
    "artefacto": "buscar_artefacto",
}

#: De tipo a la funcion del puente que devuelve el conocimiento. Otra vez
#: declarado, no resuelto en runtime.
_CONOCIMIENTO = {
    "figura": "obtener_conocimiento_figura",
    "entidad": "obtener_conocimiento_entidad",
    "sitio": "obtener_conocimiento_sitio",
    "evento": "obtener_conocimiento_evento",
    "artefacto": "obtener_conocimiento_artefacto",
}


class Recuperador:
    """Busca en el dataset real. Solo lectura. Determinista.

    Existe como clase y no como funciones sueltas por una razon: el `Archivo`
    del nucleo cuesta ~2,5 s en cargarse, y una consulta por partida debe
    reutilizarlo. El `Puente` de `ia_conocimiento` ya resuelve ese caching; aqui
    se reutiliza su instancia en vez de crear una segunda.
    """

    def __init__(self, puente=None, estado=None):
        self._puente = puente or ic.Puente()
        self._estado = estado

    @property
    def puente(self):
        return self._puente

    def buscar(self, consulta, tipo=None, limite=LIMITE_FICHAS_POR_BUSQUEDA):
        """Busca por texto. Devuelve fichas del nucleo, sin interpretar.

        `tipo=None` busca en los cinco. El resultado viene ordenado como lo
        ordena el nucleo, y se acota a `limite`. Lo que se descarte se registra
        en `truncado`, nunca se pierde callado.
        """
        if not isinstance(consulta, str) or not consulta.strip():
            raise ConsultaInvalida(["la consulta de busqueda esta vacia"])
        texto = consulta.strip()
        tipos = [tipo] if tipo else list(TIPOS_RECUPERABLES)
        for t in tipos:
            if t not in TIPOS_RECUPERABLES:
                raise ConsultaInvalida([
                    "tipo no recuperable: %r. Recuperables: %s"
                    % (t, list(TIPOS_RECUPERABLES))])

        archivo = self._puente.archivo
        salida = []
        for t in tipos:
            metodo = getattr(archivo, _BUSCADORES[t])
            bruto = metodo(texto, limite=limite)
            if not isinstance(bruto, dict):
                continue
            # El nucleo omite `fichas` cuando no encuentra nada. No se inventa
            # una lista vacia: se lee lo que hay.
            for ficha in bruto.get("fichas") or []:
                if not isinstance(ficha, dict):
                    continue
                df_id = ficha.get("df_id")
                if df_id is None or str(df_id).strip() == "":
                    # Sin identificador NO hay procedencia posible. Se descarta
                    # y se cuenta: inventar uno seria fabricar una identidad.
                    continue
                salida.append({"tipo": t,
                                "df_id": str(df_id).strip(),
                                "ficha": ficha,
                                "certainty": ficha.get("certainty") or c.UNKNOWN})

        # Orden estable: primero por tipo, luego por identificador. Sin
        # dependencias del orden del diccionario, que no esta garantizado.
        salida.sort(key=lambda r: (r["tipo"], _orden_id(r["df_id"])))
        if len(salida) > limite:
            salida = salida[:limite]
        return salida

    def conocimiento_de(self, tipo, df_id):
        """El sobre de conocimiento del puente para UN registro real.

        Delega en `ia_conocimiento`, que ya sabe extraer campos y montar
        evidencias con su procedencia. Aqui no se reimplementa nada de eso.
        """
        metodo = getattr(self._puente, _CONOCIMIENTO[tipo])
        return metodo(df_id)

    def ficha_de(self, tipo, df_id):
        """La ficha cruda del nucleo, para el analisis de dependencias."""
        archivo = self._puente.archivo
        metodo = getattr(archivo, "ficha_%s" % tipo)
        conv = (_como_id if tipo in ("figura", "sitio")
                else _como_id_entidad)
        try:
            return metodo(conv(df_id))
        except Exception:                                   # noqa: BLE001
            return None
def _orden_id(df_id):
    """Ordena identificadores de forma estable: numerico si puede, texto si no."""
    try:
        return (0, int(str(df_id)), "")
    except (TypeError, ValueError):
        return (1, 0, str(df_id))


#: Un `Recuperador` por proceso. NO es una optimizacion: cargar el indice del
#: nucleo cuesta ~2,5 s, y sin esto cada consulta los pagaria. Se construye de
#: forma perezosa, al primer uso, no al importar el modulo.
_RECUR = {"instancia": None}


def recuperador_compartido():
    """El recuperador del proceso. Se crea una vez y se reutiliza."""
    if _RECUR["instancia"] is None:
        _RECUR["instancia"] = Recuperador()
    return _RECUR["instancia"]


# ================================================== 4. LA POLITICA =========
#: Aqui NO hay una politica nueva. La de divulgacion ya existe en
#: `contrato_ia`, y esta se limita a decidir **que datos merece la pena
#: preguntar**, que es otra cosa.
#:
#: El problema real: `ia_conocimiento` marca TODO lo del mundo como
#: `PLAYER_HIDDEN + FORBIDDEN`, porque el dataset no registra que descubrio el
#: jugador. Ese es el comportamiento correcto y NO se toca.
#:
#: Entonces, ¿como llega algo al jugador? Por la unica puerta que el contrato
#: ya tiene: `convertir(a, "revelar", motivo)`, y solo si el estado del
#: jugador dice que lo conoce. Este modulo NO inventa otra puerta.
MOTIVOS = {
    ic.VISIBILIDAD_HUECO: "no consta",
    c.PLAYER_VISIBLE: "el jugador conoce este dato",
}


#: Los campos que el puente extrae de cada tipo. Se declara en vez de
#: deducirse, y **debe coincidir con las tablas de `ia_conocimiento`**: si
#: aquel anade un campo, hay que anadirlo aqui tambien.
#:
#: Se necesita para la consulta de granularidad: preguntar «¿conoce el jugador
#: el TIPO de este sitio?» es distinto de «¿conoce sus COORDENADAS?». El
#: estado del jugador guarda el descubrimiento campo a campo, y este modulo
#: tiene que問 preguntar en la misma unidad.
CAMPOS_POR_TIPO = {
    "figura": ("nombre", "race", "caste", "sexo", "tipo",
               "nacimiento", "muerte"),
    "entidad": ("nombre", "race", "tipo"),
    "sitio": ("nombre", "tipo", "eventos", "coordenadas"),
    "evento": ("tipo", "estado", "subtipo", "año"),
    "artefacto": ("nombre_item", "tipo", "subtipo", "material"),
}

#: Lo que devuelve `campos_conocidos()` cuando el jugador conoce el registro
#: ENTERO. No es un campo: es un comodin explicito, para no confundirse con un
#: campo mas.
TODOS = "TODOS"


def _campos_permitidos(a, conocidos):
    """¿Este claim se apoya solo en campos que el jugador conoce?

    Regla, y es importante que sea exacta: **basta con que uno de sus campos
    se conozca.** Un claim con varios campos es una frase que los usa todos, y
    el jugador puede conocer uno y no otro («sé que halesteel es una fortaleza,
    pero no dónde está»). Exigir todos los campos descartaría el dato útil
    junto al perigoso.

    Un claim **sin** campos (un `UNKNOWN`, que no tiene evidencia) siempre pasa:
    no depende de nada que el jugador pueda no saber.
    """
    campos = set(campos_de_afirmacion(a))
    if not campos:
        return True
    if conocidos is TODOS:
        return True
    return bool(campos & set(conocidos))


def campos_conocidos(estado, tipo, df_id):
    """¿Qué campos de este registro conoce el jugador?

    Consulta `estado_conocimiento` en la MISMA unidad en que él guarda: el
    campo. Si el jugadoriautizó el registro entero, se devuelve `TODOS`.

    No decide qué se ha descubierto. Lo pregunta, y devuelve lo que hay.
    """
    if estado.esta_conocido(tipo, str(df_id)):
        return TODOS
    conocidos = set()
    for campo in CAMPOS_POR_TIPO.get(tipo, ()):
        if estado.esta_conocido(tipo, str(df_id), campo):
            conocidos.add(campo)
    return conocidos


class Selector:
    """Decide que afirmaciones del dataset entran en la consulta.

    **No decide si se pueden revelar.** Eso lo dice `contrato_ia`. Aqui solo se
    decide que datos se piden y cuales se ofrecen, que es una cuestion de
    cobertura, no de permiso.
    """

    def __init__(self, recuperador, estado=None):
        self.rec = recuperador
        self.estado = ec._estado(estado)

    def seleccionar(self, tipo, df_id, conocidos=None):
        """Devuelve `(afirmaciones, marcas)` para UN registro real.

        `afirmaciones` son las del puente, ya con su procedencia y su permiso
        vigente. `marcas` registra lo que se decidio, para que el consumidor
        sepa que se ha considerado algo y por que no entra.
        """
        if conocidos is None:
            conocidos = campos_conocidos(self.estado, tipo, df_id)
        sobre = self.rec.conocimiento_de(tipo, df_id)
        afirmaciones = list(sobre.get("claims") or [])
        marcas = {
            "tipo": tipo,
            "df_id": str(df_id),
            "certeza": (sobre.get("asunto") or {}).get("certeza"),
            "campos_conocidos": (sorted(conocidos) if conocidos is not TODOS
                                 else TODOS),
            "claims_totales": len(afirmaciones),
            "claims_admitidos": 0,
            "claims_rechazados": [],
            "truncado": False,
        }

        admitidas = []
        for a in afirmaciones:
            if not _campos_permitidos(a, conocidos):
                marcas["claims_rechazados"].append(
                    {"claim": a.get("claim"),
                     "motivo": "el campo de este dato no se ha descubierto"})
                continue
            # El puente marca TODO lo del mundo como FORBIDDEN, porque el
            # dataset no registra descubrimientos. Ese es su comportamiento
            # correcto y no se toca.
            #
            # La unica puerta que el contrato ofrece para pasar de «verdadero y
            # no demostrado como tuyo» a «tuyo» es `convertir()`. Este motor no
            # inventa otra, y no relaja el contrato: comprueba que el
            # estado del jugador diga que lo conoce, y entonces convierte.
            #
            # Si el claim ya no es FORBIDDEN (por ejemplo un UNKNOWN, que el
            # puente marca ALLOWED), se pasa tal cual.
            if a.get("disclosure") == c.FORBIDDEN:
                promovido = self._promover(a, tipo, df_id)
                if promovido is None:
                    marcas["claims_rechazados"].append(
                        {"claim": a.get("claim"),
                         "motivo": "no se pudo promover a conocimiento del "
                                   "jugador"})
                    continue
                a = promovido
            if not ioc.entra_en_contexto(a, ioc.MODO_RAZONAMIENTO):
                marcas["claims_rechazados"].append(
                    {"claim": a.get("claim"),
                     "motivo": "no entra en contexto por politica"})
                continue
            admitidas.append(a)

        marcas["claims_admitidos"] = len(admitidas)
        return admitidas, marcas

    def _promover(self, a, tipo, df_id):
        """Convierte un dato del mundo en conocimiento del jugador.

        Delega **enteramente** en `contrato_ia.convertir()`, que es la puerta
        que el contrato ya definio y que deja constancia de quien decidio y por
        que. Aqui no se reimplementa nada de eso: se le pasa un motivo.

        Si la conversion falla, se devuelve `None` en vez de propagar el
        error: un dato que no se puede promover se aparta, y la respuesta
        sigue siendo valida.
        """
        campos = campos_de_afirmacion(a)
        detalle = ", ".join(sorted(campos)) if campos else "el registro"
        try:
            return c.convertir(
                a, "revelar",
                "el estado del jugador registra como descubierto: %s de %s %s"
                % (detalle, tipo, df_id))
        except c.ContratoInvalido:
            return None

    def describir(self, marcas):
        """El registro legible que viaja con el resultado tecnico.

        Se leen las claves con `.get()` a proposito: las marcas las escriben dos
        sitios (el selector y el motor, para lo que queda oculto) y esta
        funcion tiene que describir las dos sin romperse con ninguna.
        """
        return {"tipo": marcas.get("tipo"), "df_id": marcas.get("df_id"),
                "certeza": marcas.get("certeza"),
                "campos_conocidos": marcas.get("campos_conocidos"),
                "admitidos": marcas.get("claims_admitidos", 0),
                "rechazados": len(marcas.get("claims_rechazados") or []),
                "truncado": bool(marcas.get("truncado")),
                "oculto": bool(marcas.get("oculto"))}


# ============================================== 5. MINIMIZACION ===========
#: No se manda «lo que hay», se manda «lo que se ha preguntado». Si la pregunta
#: es «¿qué civilizaciones conocemos?», el contexto son civilizaciones
#: conocidas. Ni los 57.215 eventos, ni los 11.144 figures.
#:
#: Sin un limite, el contexto crece con el dataset y el modelo recibe mas de lo
#: necesario: mas coste, mas superficie de fuga, y peor respuesta.

def campos_de_afirmacion(a):
    """Los campos que un claim usa, tal como los declaro la evidencia."""
    salida = []
    for e in (a.get("evidence") or []):
        for campo in (e.get("datos_utilizados") or []):
            salida.append(str(campo))
    return salida


def claim_relevante(a, consulta, campo_buscado=None, anclados=()):
    """¿Este claim responde a lo que se ha preguntado?

    Criterios, en orden de fuerza:

    1. Si el claim pertenece a una entidad que la búsqueda encontró por su
       nombre, **es relevante siempre**. La búsqueda ya resolvió la ambigüedad;
       volver a pasar el texto de la pregunta por un filtro de palabras solo
       puede descartarlo sin motivo. DEFECTO CORREGIDO: con la pregunta
       «dime halesteel», el filtro descartaba «El sitio es de tipo 'fortress'»
       porque la palabra «halesteel» no aparece en la frase del claim.
    2. Si se busca un campo concreto, el claim tiene que hablar de él.
    3. Si no, se exige que alguna palabra de la pregunta aparezca.

    `anclados` son los `df_id` que la recuperación devolvió. Releva del punto 1
    y por tanto tampoco puede saltarse el filtro de campo del punto 2: el filtro
    de campo se aplica antes de la relevance por anclaje.
    """
    if campo_buscado:
        return campo_buscado in campos_de_afirmacion(a)
    if anclados and _df_id_de(a) in anclados:
        return True
    texto = (a.get("claim") or "").lower()
    if not consulta:
        return True
    # Se compara por palabras, no por subcadena: una subcadena seria «la» y
    # no significaria nada. Y se exige que al menos una palabra de la consulta
    # aparezca, no todas: la pregunta natural no coincide con el dato.
    palabras = [p for p in _normalizar(consulta).split() if len(p) > 3]
    if not palabras:
        return True
    normalizado = _normalizar(texto)
    return any(p in normalizado for p in palabras)


def _normalizar(texto):
    """Minusculas, sin acentos ni signos: comparar texto, no literales."""
    t = str(texto or "").lower().strip()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                 ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def reducir(afirmaciones, limite=LIMITE_CLAIMS, campo_buscado=None,
            consulta="", anclados=()):
    """Aplica minimizacion. Devuelve `(claims, registro)`.

    **El registro del truncamiento es tan importante como los claims.** Si se
    recorta algo, el consumidor tiene que saberlo: perder en silencio es
    peor que devolver menos.
    """
    registro = {"total": len(afirmaciones), "quedan": 0, "truncado": False,
                "descartados_por_relevancia": 0}
    relevantes = [a for a in afirmaciones
                  if claim_relevante(a, consulta, campo_buscado, anclados)]
    registro["descartados_por_relevancia"] = \
        len(afirmaciones) - len(relevantes)
    if len(relevantes) > limite:
        registro["truncado"] = True
        relevantes = relevantes[:limite]
    registro["quedan"] = len(relevantes)
    return relevantes, registro


# ============================ 6. AUDITORIA DE DEPENDENCIAS (§7) ===========
#: LA PARAFRASE SIGUE ABIERTA. Lo que hay aqui NO la resuelve, y no se presenta
#: como si lo hiciera. Lo que hace es otra cosa, y es real:
#:
#: Detecta cuando un claim ADMITIDO lleva un campo que, al combinarse con lo
#: que el jugador ya sabe, reconstruye un secreto. Concretamente:
#:
#:   * un campo de ESPACIO (coordenadas) de algo que el jugador no ha
#:     descubierto: es la via clasica de localizar lo oculto;
#:   * un CONTEO que, junto al total del mundo, delata cuantos hay ocultos
#:     («de 734 sitios, el jugador conoce 3» ya es una pista de 731);
#:   * un NOMBRE propio de algo oculto, que permite preguntar por el.
#:
#: Lo que NO hace, y hay que decirlo sin rodeos: no entiende lenguaje. Si la
#: respuesta del modelo dice «esta justo al norte», este modulo no lo detecta.
#: Eso lo hace `ia_contrato.deteccion_fuga()`, y tambien solo a medias. Las dos
#: barreras son DISCRETAS y su union NO es una garantia.
CAMPOS_ESPACIALES = ("coordenadas", "coordenadas_comunes", "posicion")
CAMPOS_CONTEO = ("eventos", "artefactos", "figuras_asociadas", "construcciones")


def auditar_dependencias(afirmaciones, fichas_ocultas=(), total_mundo=None,
                        cifras=None):
    """Revisa si un conjunto de claims ADMITE filtrar algo prohibido.

    `fichas_ocultas` son las fichas crudas de registros que el jugador no ha
    descubierto. Se usan SOLO para comparar, nunca para devolverlas: su unico
    papel es detectar si un claim visible depende de ellas.

    `cifras` son los totales del mundo POR DIMENSION (ver `cifras_del_mundo`).
    Es un diccionario, no un numero: comparar un conteo de eventos contra el
    total de sitios es comparar dos cosas distintas, y da falsos positivos.

    `total_mundo` se conserva por compatibilidad con la firma anterior, pero ya
    no se usa para contar: si viene, se ignora.

    Devuelve `(informe, claims_sin_riesgo)`. Los claims con riesgo no se
    entregan: se retiran del contexto, no se marcan y se dejan pasar.
    """
    informe = {"riesgo_indirecto": [], "revisados": len(afirmaciones),
               "coordenadas_visibles": 0, "retirados": 0}
    if not isinstance(cifras, dict):
        cifras = {}
    occlusion = _ids_ocultos(fichas_ocultas)
    limpios = []

    for a in afirmaciones:
        campos = campos_de_afirmacion(a)
        texto = (a.get("claim") or "").lower()

        # 1. ESPACIO: coordenadas de algo oculto.
        espaciales = [c for c in campos if c in CAMPOS_ESPACIALES]
        if espaciales:
            informe["coordenadas_visibles"] += 1
            df_id = _df_id_de(a)
            if df_id in occlusion:
                informe["riesgo_indirecto"].append({
                    "claim": a.get("claim"), "tipo": "espacial",
                    "motivo": "las coordenadas de un registro no descubierto "
                              "localizan ese registro"})
                informe["retirados"] += 1
                continue

        # 2. CONTEO: junto al total del mundo, delata lo que falta.
        conteos = [c for c in campos if c in CAMPOS_CONTEO and c in cifras]
        if conteos:
            if not _coherente_con_el_mundo(a, conteos, cifras):
                informe["riesgo_indirecto"].append({
                    "claim": a.get("claim"), "tipo": "conteo",
                    "motivo": "un conteo imposible junto al total del mundo"})
                informe["retirados"] += 1
                continue

        # 3. NOMBRE: el nombre propio de algo oculto es buscable.
        df_id = _df_id_de(a)
        if df_id in _ids_ocultos_nombres(fichas_ocultas) and not campos:
            informe["riesgo_indirecto"].append({
                "claim": a.get("claim"), "tipo": "nombre",
                "motivo": "un nombre propio de algo no descubierto"})
            informe["retirados"] += 1
            continue

        limpios.append(a)

    return informe, limpios


def _ids_ocultos(fichas):
    """Los identificadores de lo que el jugador no ha visto."""
    salida = set()
    for f in fichas or ():
        if isinstance(f, dict) and f.get("df_id") is not None:
            salida.add(str(f.get("df_id")).strip())
    return salida


def _ids_ocultos_nombres(fichas):
    """Los nombres propios de lo oculto. Para comparar, nunca para devolver."""
    salida = set()
    for f in fichas or ():
        if isinstance(f, dict):
            nombre = _normalizar(f.get("nombre"))
            if nombre:
                salida.add(nombre)
    return salida


def _df_id_de(a):
    for e in (a.get("evidence") or []):
        if isinstance(e, dict) and e.get("df_id") is not None:
            return str(e.get("df_id")).strip()
    return None


def _coherente_con_el_mundo(a, conteos, cifras):
    """¿El conteo del claim cabe en SU PROPIA dimension del mundo?

    Se compara cada numero contra el total de lo que ese numero cuenta: los
    eventos contra los eventos, las figuras contra las figuras. Un numero mayor
    que ese total es imposible y se retira.

    LIMITACION DECLARADA: es una comprobacion de IMPOSIBILIDAD, no de
    inferencia. No modela lo que un lector podria deducir. Calcular «734
    sitios, el jugador conoce 3, luego hay 731 que no ve» es correcto y sigue
    sin detectarse: exigiria razonamiento sobre el modelo, que es
    precisamente lo que la frontera prohibe.
    """
    texto = str(a.get("claim") or "")
    numeros = re.findall(r"\d+", texto)
    if not numeros:
        return True
    for campo in conteos:
        tope = cifras.get(campo)
        if tope is None:
            continue
        for n in numeros:
            try:
                valor = int(n)
            except ValueError:
                continue
            if valor <= int(tope):
                return True
        # Todos los numeros de este campo superan su tope: es imposible.
        return False
    # Ninguna dimension conocida: no se comprueba nada.
    return True
# =========================================== 7. EL MOTOR DE CONSULTA =======
def consultar_contexto(pregunta, consulta=None, tipo=None, agente=None,
                       modo=ioc.MODO_RAZONAMIENTO, limite=LIMITE_CLAIMS,
                       estado=None, recuperador=None,
                       dataset_esperado=None, auditoria=True):
    """Construye un `ContextoIA` a partir de una pregunta, sobre datos reales.

    El orden importa y es el que fija §8:

    1. **Valida** la peticion. Mala, se para aqui.
    2. **Comprueba el dataset.** Si el estado del jugador es de otro, se dice.
    3. **Recupera** candidatos del nucleo. Solo lectura.
    4. **Evalua permisos**, delegando en `contrato_ia`.
    5. **Construye** las afirmaciones, vía el puente.
    6. **Incorpora** las evidencias que ya trae.
    7. **Aplica minimizacion** y registra el truncamiento.
    8. **Audita dependencias** (§7) y retira lo que filtraría.
    9. **Genera** el `ContextoIA`, que vuelve a filtrar por su cuenta.
    10. **Registra** el resultado tecnico.

    Devuelve un `Informe` con el contexto y todo lo que se decidio. **No escribe
    ni en el dataset ni en el estado**: una consulta no cambia el mundo.
    """
    # --- 1. validacion ---------------------------------------------------
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ConsultaInvalida(["la pregunta es obligatoria"])
    if tipo is not None and tipo not in TIPOS_RECUPERABLES:
        raise ConsultaInvalida([
            "tipo no recuperable: %r. Recuperables: %s"
            % (tipo, list(TIPOS_RECUPERABLES))])
    if agente is not None and agente not in ioc.AGENTES:
        raise ConsultaInvalida([
            "agente desconocido: %r. Conocidos: %s"
            % (agente, list(ioc.AGENTES))])

    informe = Informe(pregunta.strip(), modo, agente or ioc.AGENTE_JUGADOR)

    # --- 2. dataset ------------------------------------------------------
    ok, motivo = comprobar_dataset(dataset_esperado)
    informe["dataset_ok"] = ok
    if not ok:
        informe["error"] = "dataset_desalineado: %s" % motivo
        informe["fatal"] = True
        return informe

    # --- 3. recuperacion -------------------------------------------------
    rec = recuperador or recuperador_compartido()
    selector = Selector(rec, estado=estado)
    informe.recuperador = rec
    termino = consulta if (consulta or "").strip() else pregunta
    try:
        encontrados = rec.buscar(termino, tipo=tipo,
                                 limite=LIMITE_FICHAS_POR_BUSQUEDA)
    except Exception as e:                                  # noqa: BLE001
        informe["error"] = "error_datos: la busqueda fallo (%s)" % (
            type(e).__name__,)
        informe["fatal"] = True
        return informe

    informe["encontrados"] = len(encontrados)
    if not encontrados:
        informe["vacio"] = True
        # Contexto vacio es una respuesta VALIDA: «no consta» tambien lo es.
        informe["contexto"] = ioc.contexto(pregunta, [], modo=modo,
                                         agente=informe["agente"])
        return informe

    # --- 4-6. permisos y construccion -------------------------------------
    campo = _campo_buscado(tipo, pregunta)
    todas = []
    marcas = []
    ocultas = []
    estado_j = ec._estado(estado)

    for registro in encontrados:
        df_id = registro["df_id"]
        # DEFECTO CORREGIDO: se usa el tipo DEL REGISTRO, no el de la peticion.
        # Con `tipo=None` (buscar en los cinco), la peticion no tiene tipo, y
        # preguntar por el estado con `tipo=None` reventaba con
        # `EstadoInvalido: tipo no soportado: None`. Aqui la busqueda ya sabe
        # de que tipo es cada cosa: hay que usar ese.
        tipo_registro = registro.get("tipo") or tipo
        ficha = registro.get("ficha") or {}
        # Se pregunta al estado DEL JUGADOR, campo a campo. Si no conoce
        # ninguno, el registro entero se aparta y su ficha se guarda solo para
        # la auditoria de dependencias (§7): de ella no sale ni un dato.
        conocidos = campos_conocidos(estado_j, tipo_registro, df_id)
        if not conocidos:
            ocultas.append(ficha)
            marcas.append({"tipo": tipo_registro, "df_id": df_id,
                           "certeza": registro.get("certainty"),
                           "campos_conocidos": [],
                           "claims_admitidos": 0,
                           "claims_rechazados": [],
                           "truncado": False, "oculto": True})
            continue
        admitidas, marca = selector.seleccionar(tipo_registro, df_id,
                                                 conocidos)
        marca["oculto"] = False
        marcas.append(marca)
        todas.extend(admitidas)

    informe["marcas"] = [selector.describir(m) for m in marcas]
    informe["ocultos_excluidos"] = sum(1 for m in marcas if m.get("oculto"))

    # --- 7. minimizacion -------------------------------------------------
    cifras = cifras_del_mundo(rec)
    if auditoria:
        informe_aud, todas = auditar_dependencias(todas, ocultas, cifras=cifras)
        informe["auditoria"] = informe_aud
    anclados = {r["df_id"] for r in encontrados if r.get("df_id")}

    # DEFECTO CORREGIDO: el filtro de campo solo se aplica si el jugador
    # conoce ESE campo. Antes se aplicaba siempre, y una palabra suelta de la
    # pregunta («¿la cueva que está en el mapa?» contiene «mapa») descartaba
    # campos que el jugador sí conocía, devolviendo un contexto vacío y
    # hac believing que no había nada que contar.
    #
    # Regla: un filtro que descarta lo que el jugador SÍ sabe no es
    # minimización, es pérdida de información silenciosa.
    conocidos = set()
    todo = False
    for m in marcas:
        cc = m.get("campos_conocidos")
        if cc == TODOS:
            todo = True
        elif cc:
            conocidos.update(cc)
    if campo and not todo and campo not in conocidos:
        campo = None

    reducidas, informe_red = reducir(todas, limite=limite,
                                     campo_buscado=campo, consulta=pregunta,
                                     anclados=anclados)
    informe["reduccion"] = informe_red
    informe["claims_candidatos"] = len(todas)
    informe["claims_entregados"] = len(reducidas)

    # --- 8-9. contexto ---------------------------------------------------
    try:
        ctx = ioc.contexto(pregunta, reducidas, modo=modo,
                            agente=informe["agente"])
    except c.ContratoInvalido as e:
        informe["error"] = "error_contrato: %s" % ("; ".join(e.errores),)
        informe["fatal"] = True
        return informe
    informe["contexto"] = ctx
    informe["cerrable"] = ioc.cerrar_contexto(ctx)
    if not informe["cerrable"]:
        # No deberia pasar: `ioc.contexto` ya filtra. Si pasa, es un fallo de
        # la frontera y se dice, en vez de entregarlo como si nada.
        informe["error"] = "error_contrato: el contexto no supera cerrar_contexto"
        informe["fatal"] = True
    return informe
# ------------------------------------------------- AYUDAS DEL MOTOR -------
def _campo_buscado(tipo, pregunta=""):
    """El campo que la PREGUNTA pide, no el que el tipo sugiere.

    DEFECTO CORREGIDO: antes esto devolvia `"tipo"` para todo `sitio` y
    `"nombre"` para todo `figura`. Consecuencia real, reproducida: un jugador
    que hubiera descubierto las COORDENADAS de un sitio no las recibia
    nunca, porque la pregunta iba marcada como `tipo="sitio"` y el filtro
    las descartaba. El filtro era una suposicion sobre la pregunta, no una
    lectura de la pregunta.

    Ahora se deduce del texto. Y si el texto no precisa ningun campo, se
    devuelve `None`, que significa «no filtrar por campo»: la
    relevancia por palabras decide, y el limite de claims acota.
    """
    texto = cx_normalizar(pregunta)
    if not texto:
        return None
    # Un unico campo por pregunta, en orden de especificidad: si alguien pide
    # «donde», pide coordenadas aunque tambien mencione el tipo.
    if any(p in texto for p in ("donde", "ubicacion", "ubicaciones",
                                "coordenada", "coordenadas", "situado",
                                "situada", "lugar", "mapa")):
        return "coordenadas"
    if any(p in texto for p in ("quien", "nombre", "llama", "llamado")):
        return "nombre"
    if any(p in texto for p in ("tipo", "clase", "que es", "categoria")):
        return "tipo"
    return None


def cx_normalizar(texto):
    """Minusculas y sin acentos. Se reutiliza el del propio modulo."""
    return _normalizar(texto)


#: De tipo de registro a la cifra que el nucleo da en `estadisticas()`. Se
#: declara en vez de deducirse, como todo lo demas de este modulo.
_CIFRAS_MUNDO = {"sitio": "sitios", "figura": "figuras",
                 "entidad": "entidades", "evento": "eventos",
                 "artefacto": "artefactos"}


#: De campo de conteo a la cifra del mundo que le corresponde.
#:
#: ESTO ES IMPORTANTE y no es cosmetico: comparar un numero de EVENTOS con el
#: total de SITIOS es comparar dos cosas distintas, y marca como imposible
#: algo que es perfectamente real («este sitio tiene 1546 eventos» en un mundo
#: de 734 sitios es normal, si se cuentan los eventos de todos los sitios).
#: El primer fallo que dio fue exactamente ese.
#:
#: Cada conteo se compara contra SU PROPIA dimension, y si no se conoce esa
#: dimension, no se comprueba nada: ante la duda, no se retira nada.
_CIFRA_POR_CAMPO = {
    "eventos": "eventos",
    "artefactos": "artefactos",
    "figuras_asociadas": "figuras",
    "construcciones": "construcciones_mundo",
}


def cifras_del_mundo(rec):
    """El tamaño del mundo en cada dimension, para comparar conteos.

    **No se envia al modelo.** Se usa solo para comprobar si un numero es
    imposible. Que el sistema sepa cuantos sitios hay, y el modelo no, es
    justamente lo que evita el «734 menos 3 igual 731».
    """
    try:
        stats = rec.puente.archivo.estadisticas()
    except Exception:                                       # noqa: BLE001
        return {}
    if not isinstance(stats, dict):
        return {}
    return {campo: stats[clave]
            for campo, clave in _CIFRA_POR_CAMPO.items()
            if isinstance(stats.get(clave), int)}


def _total_mundo(rec, tipo=None):
    """Se conserva por compatibilidad. El total de un TIPO de registro.

    Ya no se usa para comparar conteos (eso es `cifras_del_mundo`): quedarse
    solo con el total del tipo era justamente el error de comparar peras con
    manzanas. Se mantiene porque es informacion util del informe.
    """
    if tipo is None:
        return None
    clave = _CIFRAS_MUNDO.get(tipo)
    if clave is None:
        return None
    try:
        stats = rec.puente.archivo.estadisticas()
    except Exception:                                       # noqa: BLE001
        return None
    if not isinstance(stats, dict):
        return None
    valor = stats.get(clave)
    return valor if isinstance(valor, int) else None


class Informe(dict):
    """Lo que devuelve una consulta: el contexto y TODO lo que se decidio.

    No devuelve solo el contexto. Un motor que devuelve un resultado sin
    explicar como llego a el es un motor que no se puede auditar, y esta
    mision exige lo contrario.

    | clave              | que es                                      |
    |--------------------|---------------------------------------------|
    | `pregunta`         | lo que se pregunto                          |
    | `dataset_ok`       | el dataset consultado es el que se esperaba   |
    | `encontrados`      | candidatos antes de filtrar                   |
    | `claims_entregados`| los que llegan al modelo                      |
    | `ocultos_excluidos`| los que se quedaron fuera por no descubiertos |
    | `auditoria`        | riesgos indirectos detectados (§7)            |
    | `reduccion`        | truncamiento y descarte por relevancia        |
    | `contexto`         | el `ContextoIA`                               |
    | `error`            | el fallo, si lo hay                           |
    | `fatal`            | si la consulta no puede continuar             |
    """

    def __init__(self, pregunta, modo, agente):
        dict.__init__(self, {
            "pregunta": pregunta, "modo": modo, "agente": agente,
            "dataset_id": dataset_id(), "dataset_ok": True,
            "encontrados": 0, "claims_candidatos": 0, "claims_entregados": 0,
            "ocultos_excluidos": 0, "marcas": [], "vacio": False,
            "cerrable": True, "auditoria": None, "reduccion": None,
            "contexto": None, "error": None, "fatal": False,
        })
        self.recuperador = None

    @property
    def ok(self):
        return self.get("error") is None

    def resumen(self):
        """El registro tecnico, sin el contexto entero. Para diagnostico."""
        return {k: v for k, v in self.items()
                if k not in ("contexto", "recuperador")}

