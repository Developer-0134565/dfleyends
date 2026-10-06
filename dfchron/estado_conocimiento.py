#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Estado del conocimiento del jugador
====================================================

LA LIMITACION QUE RESUELVE
--------------------------
`legends.xml` **no registra qué descubrió el jugador**. El juego escribe la
historia del mundo, no la memoria de quien la jugó. Por eso `WORLD_KNOWLEDGE`
está perfecto y `PLAYER_KNOWLEDGE` no tenía dónde apoyarse.

Este módulo le da estado. Es **estado de ejecución**, no parte de la historia:
vive fuera del dataset y se puede borrar sin tocar un solo byte histórico.

    dataset histórico  +  estado del jugador  =  contexto de conocimiento

LO QUE ESTE MÓDULO **NO** ES
-----------------------------
No es una IA. No redacta, no razona, no revela. **No cambia ni una sola
dimensión de una afirmación.** No existe aquí un `si conocido: revelar()`.

TRES REGLAS QUE NO SE NEGOCIAN
------------------------------
1. **Conocido no es verdad.** `conocido=True` dice que *el jugador conoce esto*.
   La verdad la sigue dictando el núcleo: `FACT`/`DERIVED`/`UNKNOWN`. Marcar
   como conocido no convierte un `UNKNOWN` en `FACT`.

2. **Conocido no es revelable.** Ser conocido no cambia `disclosure`. Un dato
   `FORBIDDEN` sigue prohibido aunque el jugador lo conozca. La única puerta para
   cambiar de categoría sigue siendo `contrato_ia.convertir()`, con su motivo.

3. **Nada se autodescubre.** Que el núcleo lo tenga, que la web lo muestre, que
   una consulta lo devuelva o que sea `FACT` **no** lo marca como conocido.
   `WORLD_KNOWLEDGE → PLAYER_KNOWLEDGE` es siempre una decisión explícita.

GRANULARIDAD: LA QUE EL NÚCLEO SOSTIENE REALMENTE
-------------------------------------------------
Se auditing el núcleo en vez de inventar. Identidad estable por `df_id`:

| Tipo      | Identidad | Soportado |
|---|---|---|
| `figura`  | `df_id` | sí |
| `sitio`   | `df_id` | sí |
| `entidad` | `df_id` | sí |
| `artefacto`| `df_id` | sí |
| `evento`  | `df_id` | sí |
| `relacion`| — | **NO** |

Las relaciones **no tienen identificador estable**: `relaciones_de_figura()`
devuelve objetos sin `id`. Inventar uno sería fabricar una granularidad que el
dataset no puede sostener, así que no se ha hecho. Si algún día el núcleo les da
identidad, se añade el tipo aquí y en ningún otro sitio.

Dos niveles, ambos derivados de datos reales:
* **entidad**: el jugador conoce el sitio 87.
* **campo**: el jugador conoce las *coordenadas* del sitio 87.

El segundo existe porque las afirmaciones del puente hablan de **campos**
(`evidence[0]["datos_utilidades"]`), no de entidades enteras.

DETERMINISMO
------------
Sin relojes, sin `random`, sin UUID, sin orden de `set`. El JSON se serializa
con claves ordenadas: las mismas entradas producen el mismo fichero, byte a byte.
"""
import json
import os
import sys

# `config` mete `00_SOURCE/tools` en `sys.path` para poder importar `rutas`.
# Se hace como en `contrato_ia.py`: igual funciona como modulo del paquete que
# como script suelto (`python dfchron/estado_conocimiento.py`).
try:
    from . import config                                   # noqa: F401
except ImportError:                                       # pragma: no cover
    _RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _RAIZ)
    sys.path.insert(0, os.path.join(_RAIZ, "00_SOURCE", "tools"))
    import config                                          # noqa: F401

import rutas                                            # noqa: E402

# ================================================================ RUTAS ======
#: Estado de EJECUCION, fuera del dataset. Igual que `exports/` está fuera de
#: `processed/` porque "un export nunca puede contaminar el dataset", aquí el
#: estado nunca puede contaminarlo tampoco.
RAIZ_ESTADO = os.environ.get(
    "DFCHRON_ESTADO_ROOT", "").strip() or os.path.join(
        rutas.PROJECT_ROOT, "estado")

ARCHIVO_ESTADO = os.path.join(RAIZ_ESTADO, "estado_conocimiento.json")

#: Si alguien apunta el estado dentro del dataset, se ABORTA. Se reutiliza la
#: protección que ya tenía el proyecto, en vez de escribir una segunda.
if rutas.es_ruta_protegida(ARCHIVO_ESTADO):
    raise RuntimeError(
        f"el estado del jugador no puede vivir dentro del dataset: "
        f"{ARCHIVO_ESTADO}")

SCHEMA_VERSION = 1

#: Tipos con identidad estable en el núcleo. `relacion` NO está, a propósito.
TIPOS_SOPORTADOS = ("figura", "sitio", "entidad", "artefacto", "evento")

#: Y esto se documenta, no se deduce leyendo el código.
TIPOS_NO_SOPORTADOS = {
    "relacion": "el nucleo no da identificador estable a las relaciones",
}

# ============================================================== ERRORES ======
class EstadoInvalido(ValueError):
    """El estado del jugador es ilegible o no se sabe interpretarlo."""


class DatasetDistinto(Exception):
    """El estado guardado pertenece a otro dataset. No se continua en silencio.

    No se borra nada al detectar esto. El sistema se queda quieto y espera a que
    alguien decida: por eso es una excepcion y no un aviso.
    """


# =========================================================== IDENTIFICADORES ==
def clave_entidad(tipo, df_id):
    return f"entidad|{tipo}:{df_id}"


def clave_campo(tipo, df_id, campo):
    return f"campo|{tipo}:{df_id}:{campo}"


def _validar(tipo, df_id, campo=None):
    """Normaliza y comprueba una referencia. Falla pronto y con motivo."""
    if not isinstance(tipo, str) or tipo not in TIPOS_SOPORTADOS:
        raise EstadoInvalido(
            f"tipo de conocimiento no soportado: {tipo!r}. "
            f"Soportados: {list(TIPOS_SOPORTADOS)}")
    if isinstance(df_id, bool) or df_id is None:
        raise EstadoInvalido(f"identificador invalido: {df_id!r}")
    if df_id.__class__ not in (str, int):
        raise EstadoInvalido(f"identificador invalido: {df_id!r}")
    if str(df_id).strip() == "":
        raise EstadoInvalido("identificador vacio")
    if campo is not None:
        if not isinstance(campo, str) or not campo.strip():
            raise EstadoInvalido(f"campo invalido: {campo!r}")
        campo = campo.strip()
    return str(df_id).strip(), campo


def _normalizar_motivo(motivo):
    """Un motivo es texto libre del que llama. NO se le pone fecha."""
    if motivo is None:
        return None
    if not isinstance(motivo, str):
        raise EstadoInvalido(f"motivo debe ser texto: {motivo!r}")
    return motivo.strip()[:500] or None
# ================================================================ ESTADO =====
class EstadoConocimiento:
    """El estado de descubrimiento del jugador. Local, explícito y auditable.

    No depende del orden en que se use, ni de la memoria del proceso. Todo lo
    que devuelve al exterior sale **congelado**: quien lo recibe no puede
    mutarlo y alterar el estado por la puerta de atrás (§14).
    """

    def __init__(self, ruta=None, dataset_id=None):
        self.ruta = os.path.abspath(ruta or ARCHIVO_ESTADO)
        if rutas.es_ruta_protegida(self.ruta):
            raise RuntimeError(
                f"el estado del jugador no puede escribirse en el dataset: "
                f"{self.ruta}")
        self.dataset_id = dataset_id or dataset_actual()
        self._datos = None          # cache perezosa; None = no leido

    # --- lectura / escritura del fichero ------------------------------
    def _leer(self):
        """Carga el estado. Determinado, sin migraciones y sin borrados."""
        if self._datos is not None:
            return self._datos
        if not os.path.exists(self.ruta):
            self._datos = _vacio(self.dataset_id)
            return self._datos
        try:
            with open(self.ruta, encoding="utf-8") as f:
                crudo = json.load(f)
        except (OSError, ValueError) as e:
            raise EstadoInvalido(
                f"estado del jugador ilegible ({os.path.basename(self.ruta)}): {e}")
        self._datos = _validar_esquema(crudo)
        return self._datos

    def _escribir(self):
        """Guarda con formato canónico: claves ordenadas, sin timestamps.

        Se escribe a un temporal y se renombra: un fallo a mitad no debe dejar
        un estado corrupto.
        """
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        temporal = self.ruta + ".tmp"
        texto = json.dumps(self._leer(), ensure_ascii=False,
                          indent=1, sort_keys=True)
        with open(temporal, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto + "\n")
        os.replace(temporal, self.ruta)

    # --- el estado del dataset, que decide si esto sirve de algo ------
    def compatibilidad(self):
        """¿El estado guardado corresponde al dataset de ahora?

        Devuelve un texto, nunca un booleano mudo: quien pregunte tiene que
        poder decir en voz alta en qué situación está.
        """
        d = self._leer()
        if not os.path.exists(self.ruta):
            return "SIN_ESTADO"
        if d.get("dataset_id") == self.dataset_id:
            return "COINCIDE"
        return "DISTINTO"

    def exigir_compatible(self):
        """Falla si el estado es de otro dataset. No borra: solo se niega."""
        estado = self.compatibilidad()
        if estado in ("SIN_ESTADO", "COINCIDE"):
            return estado
        raise DatasetDistinto(
            f"el estado del jugador pertenece al dataset "
            f"{self._leer().get('dataset_id')!r} y ahora se sirve "
            f"{self.dataset_id!r}. No se continua en silencio y el estado NO se "
            f"ha borrado: usa limpiar_conocimiento() para empezar de cero.")
# --- operaciones -------------------------------------------------
    def marcar_conocido(self, tipo, df_id, campo=None, motivo=None):
        """Registra que el jugador conoce esto. No toca el mundo.

        No cambia `truth_status`, ni `visibility`, ni `disclosure` de nada: solo
        anota un hecho sobre el jugador. Por eso se puede marcar un `UNKNOWN`
        como conocido: que el jugador sepa que no consta también es saber.
        """
        self.exigir_compatible()
        df_id, campo = _validar(tipo, df_id, campo)
        motivo = _normalizar_motivo(motivo)
        clave = clave_campo(tipo, df_id, campo) if campo \
            else clave_entidad(tipo, df_id)
        entrada = {"tipo": tipo, "df_id": df_id}
        if campo:
            entrada["campo"] = campo
        if motivo:
            entrada["motivo"] = motivo
        self._leer()["knowledge"][clave] = entrada
        self._escribir()
        return clave

    def marcar_desconocido(self, tipo, df_id, campo=None):
        """Revoca la marca. No toca el mundo histórico en absoluto."""
        self.exigir_compatible()
        df_id, campo = _validar(tipo, df_id, campo)
        clave = clave_campo(tipo, df_id, campo) if campo \
            else clave_entidad(tipo, df_id)
        self._leer()["knowledge"].pop(clave, None)
        self._escribir()
        return clave

    def esta_conocido(self, tipo, df_id, campo=None):
        """¿Está registrado como conocido?

        Si el estado es de otro dataset devuelve `False`: no se puede afirmar
        que el jugador conoce algo de un mundo que ya no es el que se sirve.
        Falla cerrado.
        """
        if self.compatibilidad() == "DISTINTO":
            return False
        df_id, campo = _validar(tipo, df_id, campo)
        clave = clave_campo(tipo, df_id, campo) if campo \
            else clave_entidad(tipo, df_id)
        return clave in self._leer()["knowledge"]

    def obtener_conocimiento(self):
        """Copia **congelada** del estado. No es mutable ni por dentro.

        Devuelve un snapshot: si quien lo recibe lo altera, altera su copia,
        nunca el estado guardado. Y leer no escribe nada en disco.
        """
        if self.compatibilidad() == "DISTINTO":
            raise DatasetDistinto(
                "el estado es de otro dataset; no se entrega como si valiera")
        return _congelar(self._leer())

    def limpiar_conocimiento(self, tipo=None, df_id=None, campo=None):
        """Reset explícito y controlado. Dos formas, y son distintas:

        * **Sin argumentos** → borra **TODO** el estado del jugador y lo **vuelve
          a ligar al dataset actual**. Es la única vía de recuperación cuando el
          dataset ha cambiado, y por eso está disponible incluso con el estado
          desfasado: si no, un cambio de dataset dejaría el estado inservible
          para siempre.

        * **Con `tipo` y `df_id`** → borra solo esa entrada y exige que el
          estado sea compatible. Es limpieza quirúrgica, no un reset.

        Ninguna de las dos toca el dataset, el XML ni el JSONL.
        """
        if (tipo is None) != (df_id is None):
            raise EstadoInvalido(
                "limpiar exige tipo y df_id juntos, o ninguno de los dos")
        datos = self._leer()
        conocimiento = datos["knowledge"]
        if tipo is None:
            borrados = len(conocimiento)
            conocimiento.clear()
            # El reset SI liga el estado al dataset que se esta sirviendo.
            datos["dataset_id"] = self.dataset_id
        else:
            self.exigir_compatible()
            df_id, campo = _validar(tipo, df_id, campo)
            clave = clave_campo(tipo, df_id, campo) if campo \
                else clave_entidad(tipo, df_id)
            borrados = 1 if conocimiento.pop(clave, None) is not None else 0
        self._escribir()
        return borrados
# ============================================================= ESQUEMA =======
def _vacio(dataset_id):
    return {"schema_version": SCHEMA_VERSION, "dataset_id": dataset_id,
            "knowledge": {}}


def _validar_esquema(crudo):
    """Valida el fichero de estado. Si no encaja, se dice: no se adivina."""
    if not isinstance(crudo, dict):
        raise EstadoInvalido("el estado debe ser un objeto JSON")
    faltan = [k for k in ("schema_version", "dataset_id", "knowledge")
              if k not in crudo]
    if faltan:
        raise EstadoInvalido(f"estado incompleto, faltan: {faltan}")
    if crudo["schema_version"] != SCHEMA_VERSION:
        # No hay migraciones silenciosas, y no se inventa ninguna.
        raise EstadoInvalido(
            f"schema_version {crudo['schema_version']!r} no es la de esta "
            f"version ({SCHEMA_VERSION}). No se migra solo: se dice.")
    if not isinstance(crudo["knowledge"], dict):
        raise EstadoInvalido("'knowledge' debe ser un objeto")

    # CONTENIDO DE LAS ENTRADAS, no solo la forma.
    #
    # Antes solo se comprobaba que el fichero tuviera las claves obligatorias y que
    # `knowledge` fuera un dict. Una entrada malformada se aceptaba en LECTURA:
    # bastaba editar el fichero a mano para meter una clave arbitraria bien
    # formada, y el sistema la creeria. Ahora cada entrada se revalida con el
    # MISMO `_validar()` que se usa al escribir, de modo que leer no es mas
    # permisivo que escribir. Es la defensa obvia que faltaba, y no cuesta nada:
    # la funcion ya existia y ya sabia decir que es una referencia invalida.
    conocimiento = {}
    for clave, entrada in crudo["knowledge"].items():
        if not isinstance(entrada, dict):
            raise EstadoInvalido(
                f"entrada de conocimiento malformada ({clave!r}): "
                f"se esperaba un objeto y hay {type(entrada).__name__}")
        tipo = entrada.get("tipo")
        df_id = entrada.get("df_id")
        campo = entrada.get("campo")
        if campo is not None and not (isinstance(campo, str) and campo.strip()):
            raise EstadoInvalido(
                f"entrada de conocimiento malformada ({clave!r}): "
                f"campo invalido: {campo!r}")
        try:
            _validar(tipo, df_id, campo)
        except EstadoInvalido as e:
            raise EstadoInvalido(
                f"entrada de conocimiento invalida ({clave!r}): {e}")
        conocimiento[clave] = dict(entrada)

    return {
        "schema_version": crudo["schema_version"],
        "dataset_id": crudo["dataset_id"],
        "knowledge": conocimiento,
    }


class _DictSello(dict):
    """dict que no se puede modificar (salida del snapshot)."""

    __slots__ = ()

    def _no(self, op):
        raise EstadoInvalido(f"el estado es de solo lectura: no se puede {op}")

    def __setitem__(self, k, v):
        self._no(f"asignar {k!r}")

    def __delitem__(self, k):
        self._no(f"borrar {k!r}")

    def update(self, *a, **k):
        self._no("usar update()")

    def pop(self, *a, **k):
        self._no("usar pop()")

    def clear(self):
        self._no("usar clear()")

    def setdefault(self, *a, **k):
        self._no("usar setdefault()")

    def __ior__(self, otro):
        self._no("usar |=")

    # Las estructuras selladas se pueden copiar (una copia es util para
    # comparar), pero la copia sigue sellada. Sin esto, `copy.deepcopy`
    # reintentaria escribir por `__setitem__` y reventaria.
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


class _ListaSello(list):
    """list que no se puede modificar (salida del snapshot)."""

    __slots__ = ()

    def _no(self, op):
        raise EstadoInvalido(f"el estado es de solo lectura: no se puede {op}")

    def __setitem__(self, i, v):
        self._no("asignar por indice")

    def __delitem__(self, i):
        self._no("borrar por indice")

    def append(self, v):
        self._no("usar append()")

    def extend(self, v):
        self._no("usar extend()")

    def pop(self, *a):
        self._no("usar pop()")

    def clear(self):
        self._no("usar clear()")

    def sort(self, *a, **k):
        self._no("usar sort()")

    def reverse(self):
        self._no("usar reverse()")

    def __ior__(self, otro):
        self._no("usar |=")

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


def _congelar(valor):
    """Deep-freeze. Idempotente, así que se puede aplicar a un dict plano."""
    if isinstance(valor, dict):
        return _DictSello({k: _congelar(v) for k, v in valor.items()})
    if isinstance(valor, (list, tuple)):
        return _ListaSello([_congelar(v) for v in valor])
    return valor


def dataset_actual():
    """El `dataset_id` del mecanismo real. Nunca se escribe a mano.

    Se lee del mismo `dataset_version.json` que usa la API y el refresco. No se
    depende de `ia_conocimiento` a proposito: asi este modulo funciona igual
    como parte del paquete y como script, y ambos leen la misma fuente.
    """
    ruta = os.path.join(rutas.DATA_ROOT, "dataset_version.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f).get("dataset_id") or "UNKNOWN"
    except (OSError, ValueError):
        # Sin dataset no hay estado que valga: se declara, no se inventa.
        return "UNKNOWN"
# ============================================ PUENTE CON LAS AFIRMACIONES =====
#: Tipos de evidencia que el puente produce, y su equivalencia aqui.
_TIPO_EVIDENCIA = {
    "figura": "figura",
    "sitio": "sitio",
    "entidad": "entidad",
    "artefacto": "artefacto",
    "evento": "evento",
}


def referencia_de(afirmacion):
    """Qué referencia tiene una afirmación, según su propia evidencia.

    NO inventa identidad: lee `evidence[0]`, que es el rastro real que el núcleo
    dejó. Si no hay evidencia utilizable, no hay referencia y se dice.

    Devuelve `(tipo, df_id, campo)` o `None`.
    """
    if not isinstance(afirmacion, dict):
        return None
    evidencia = afirmacion.get("evidence") or []
    if not evidencia:
        return None
    ev = evidencia[0]
    if not isinstance(ev, dict):
        return None
    tipo = _TIPO_EVIDENCIA.get(str(ev.get("entidad") or "").lower())
    if tipo is None:
        return None
    df_id = ev.get("df_id")
    if df_id is None or str(df_id).strip() == "":
        return None
    campos = ev.get("datos_utilizados") or []
    campo = str(campos[0]) if len(campos) == 1 else None
    return tipo, str(df_id).strip(), campo


def es_conocida(afirmacion, estado=None):
    """¿Está marcada como conocida la referencia de esta afirmación?

    **No devuelve si se puede revelar.** Eso lo decide el contrato de
    divulgación y nada más. Aquí no hay ningún `if conocido: revelar()`, y no
    debe añadirse: sería el atajo que abre la frontera.
    """
    ref = referencia_de(afirmacion)
    if ref is None:
        return False
    tipo, df_id, campo = ref
    return _estado(estado).esta_conocido(tipo, df_id, campo)


def marcar_conocida(afirmacion, estado=None, motivo=None):
    """Marca como conocida la referencia de una afirmación, y la devuelve igual.

    Devuelve la **misma** afirmación, sin tocar. Que el jugador la conozca no la
    vuelve visible, ni divulgable, ni verdadera: eso lo decide el contrato.
    """
    ref = referencia_de(afirmacion)
    if ref is None:
        raise EstadoInvalido(
            "esta afirmación no tiene evidencia con identidad utilizable: "
            "no se puede marcar sin inventar una referencia")
    tipo, df_id, campo = ref
    _estado(estado).marcar_conocido(tipo, df_id, campo, motivo)
    return afirmacion


# ================================================================ API ========
_ESTADO = None


def _estado(estado=None):
    """Un estado por proceso. Se puede pasar otro en las pruebas."""
    global _ESTADO
    if estado is not None:
        return estado
    if _ESTADO is None:
        _ESTADO = EstadoConocimiento()
    return _ESTADO


def obtener_estado():
    return _estado()


def marcar_conocido(tipo, df_id, campo=None, motivo=None):
    return _estado().marcar_conocido(tipo, df_id, campo, motivo)


def marcar_desconocido(tipo, df_id, campo=None):
    return _estado().marcar_desconocido(tipo, df_id, campo)


def esta_conocido(tipo, df_id, campo=None):
    return _estado().esta_conocido(tipo, df_id, campo)


def obtener_conocimiento():
    return _estado().obtener_conocimiento()


def limpiar_conocimiento(tipo=None, df_id=None, campo=None):
    return _estado().limpiar_conocimiento(tipo, df_id, campo)


def compatibilidad():
    return _estado().compatibilidad()


if __name__ == "__main__":
    print(json.dumps({"ruta": ARCHIVO_ESTADO,
                      "schema_version": SCHEMA_VERSION,
                      "dataset_id": dataset_actual(),
                      "compatibilidad": compatibilidad()},
                     ensure_ascii=False, indent=2))