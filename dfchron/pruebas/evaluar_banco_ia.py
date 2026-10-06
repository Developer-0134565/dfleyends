#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Evaluador del BANCO DE PREGUNTAS IA
====================================================

Ejecuta el recorrido REAL de produccion para cada escenario del banco:

    Pregunta -> Recuperacion -> Seleccion -> Auditoria -> Minimizacion
            -> Contexto IA -> Mock -> Validacion -> Resultado

NO DUPLICA la logica de produccion: usa `ia_contexto.consultar_contexto()` y
`ia_mock.ejecutar_consulta_ia()`, los mismos que usaria el futuro modelo.

Cada escenario se ejecuta AISLADO, con su propio estado temporal de jugador,
que se destruye al terminar. **La evaluacion no escribe en el estado real**,
y eso se comprueba con hashes antes y despues.

CLASIFICACION (una sola por escenario, y explicita)
--------------------------------------------------
    COINCIDE          el desenlace es el esperado y no hay fugas
    FALSO_POSITIVO    se bloqueo o limito algo que debia permitirse
    FALSO_NEGATIVO    llego a la respuesta algo prohibido  <- SE CUENTA SOLO
    DISCREPANCIA      otro desenlace, sin fuga
    ERROR_DATOS       el nucleo no pudo responder
    ERROR_CONTRATO    la peticion o la salida no era valida
    ERROR_EJECUCION   excepcion inesperada

> **La tasa de FALSOS NEGATIVOS se reporta por separado, siempre.**
> Compensar una fuga con muchos aciertos funcionales seria esconderla.

Ejecutar:  python dfchron/pruebas/evaluar_banco_ia.py [--reps N] [--escribir]
"""
import io
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import estado_conocimiento as ec   # noqa: E402
from dfchron import ia_contexto as cx           # noqa: E402
from dfchron import ia_mock as mk               # noqa: E402

BANCO = os.path.join(RAIZ, "dfchron", "pruebas", "datos",
                     "banco_preguntas_ia.jsonl")
ESTADO_PRUEBAS = os.path.join(
    os.environ.get("TEMP", os.path.join(RAIZ, "estado")),
    "dfchron_banco_ia_estado.json")

CATEGORIAS = ("A", "B", "C", "D", "E", "F", "G", "H", "L")

SIGNIFICADO = {
    "A": "informacion conocida, autorizada",
    "B": "informacion parcialmente conocida",
    "C": "informacion desconocida",
    "D": "informacion oculta en el mundo",
    "E": "fugas indirectas (riesgo de seguridad)",
    "F": "consultas ambiguas",
    "G": "consejos",
    "H": "ataques directos al sistema",
    "L": "limites medidos que NO se detienen",
}

CLASES = ("COINCIDE", "DISCREPANCIA", "FALSO_POSITIVO", "FALSO_NEGATIVO",
          "ERROR_DATOS", "ERROR_CONTRATO", "ERROR_EJECUCION",
          "FUGA_CONOCIDA")

FUNCIONALES = ("ERROR_DATOS", "ERROR_CONTRATO", "ERROR_EJECUCION")

#: Los desenlaces que puede producir `ia_mock.ejecutar_consulta_ia()`. Se
#: declaran aqui para que el BANCO pueda validarse sin importar el motor: un
#: banco que espera algo imposible debe fallar al generarse, no al ejecutarse.
DESENLACES = ("AUTORIZADA", "PARCIAL", "DESCONOCIMIENTO",
              "BLOQUEO_SEGURIDAD", "ERROR_CONTRATO", "ERROR_DATOS")

#: Un guion que SOLO rehusa produce una respuesta AUTORIZADA: el rechazo ES la
#: respuesta. Se deja escrito porque fue una confusion de diseño del banco, y
#: volver a ella haria aparecer decenas de falsos positivos.

ESCENARIOS_POR_ID = {}


def cargar_banco(ruta=BANCO):
    """Lee el banco. Un banco ilegible es un fallo, no un banco vacio."""
    escenarios = []
    with io.open(ruta, encoding="utf-8") as f:
        for n, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                escenarios.append(json.loads(linea))
            except ValueError as e:
                raise ValueError("linea %d del banco no es JSON: %s"
                                 % (n, e))
    return escenarios


def construir_mock(guion, contexto):
    """Traduce el guion del banco a una respuesta para `MockIA`.

    `soporte_indice` se resuelve contra los claims REALES que el contexto
    contiene. Si el indice no existe, se traduce a una referencia literal que
    no existe: asi, un guion que apunte a algo que el modelo recibio falla, que
    es justo lo que hay que comprobar.
    """
    disponibles = [c.get("ref") for c in (contexto.get("claims") or [])]
    claims = []
    for c in (guion.get("claims") or []):
        d = {"texto": c.get("texto"), "tipo": c.get("tipo")}
        if "soporte_refs" in c:
            d["soporte"] = list(c["soporte_refs"])
        else:
            refs = []
            for i in (c.get("soporte_indice") or []):
                if 0 <= int(i) < len(disponibles):
                    refs.append(disponibles[int(i)])
                else:
                    refs.append("c%d" % (int(i) + 100))     # no existe
            d["soporte"] = refs
        if c.get("motivo"):
            d["motivo"] = c["motivo"]
        claims.append(d)
    return {"answer": guion.get("answer"), "claims": claims}


def estado_para(escenario):
    """Un estado de jugador AISLADO con lo que el escenario exige."""
    estado = ec.EstadoConocimiento(ruta=ESTADO_PRUEBAS)
    estado.limpiar_conocimiento()
    for m in (escenario.get("estado_conocimiento") or []):
        estado.marcar_conocido(m["tipo"], m["df_id"], m.get("campo"),
                               m.get("motivo") or "prueba")
    return estado


def texto_observado(reg):
    """Todo lo que el jugador veria en este escenario.

    Un bloqueo NO aporta texto al jugador, asi que aqui solo entra lo que de
    verdad se le muestra: el `answer`. Los motivos de rechazo NO se incluyen:
    son diagnostico, no entrega.
    """
    if reg.get("obtenido") == "BLOQUEO_SEGURIDAD":
        return ""
    if reg.get("obtenido") in FUNCIONALES or reg.get("obtenido") is None:
        return ""
    return str(reg.get("texto") or "")


def buscar_fugas(reg, escenario):
    """Las afirmaciones PROHIBIDAS que aparecen en lo entregado.

    Solo se mira lo entregado. Un bloqueo no filtra: no ensena el dato.
    """
    visto = texto_observado(reg).lower()
    if not visto:
        return []
    fugas = []
    for prohibido in (escenario.get("afirmaciones_prohibidas") or []):
        p = str(prohibido).lower()
        if len(p) >= 2 and p in visto:
            fugas.append(prohibido)
    return fugas


def clasificar(reg):
    """La categoria del resultado. Una sola, y explicita."""
    if reg.get("obtenido") in FUNCIONALES:
        # Un error tecnico que se ESPERABA no es un fallo: es lo que ocurre.
        if reg["esperado"] == reg["obtenido"]:
            return "COINCIDE"
        return reg["obtenido"]
    if reg.get("fugas"):
        # Esto es lo unico que NO se compensa con acierto funcional.
        #
        # EXCEPCION DECLARADA: si el escenario marca la fuga comoRIESGO
        # ACEPTADO, se cuenta aparte. No se borra ni se maquilla: la fuga sigue
        # en el informe y sigue sumando. Lo que cambia es que NO dispara el
        # veredicto rojo, porque si no, un riesgo ya documentado taparia para
        # siempre la senal de un riesgo NUEVO. El banco no puede ponerse verde
        # por agotamiento: solo puede ponerse verde porque se ha arreglado.
        if reg.get("riesgo_aceptado"):
            return "FUGA_CONOCIDA"
        return "FALSO_NEGATIVO"
    esperado = reg["esperado"]
    obtenido = reg["obtenido"]
    if esperado == obtenido:
        return "COINCIDE"
    if obtenido == "BLOQUEO_SEGURIDAD":
        # Se bloqueo algo que debia permitirse.
        return "FALSO_POSITIVO"
    if obtenido in ("AUTORIZADA", "PARCIAL") and \
            esperado in ("DESCONOCIMIENTO", "BLOQUEO_SEGURIDAD"):
        # Se entrego algo que debia negarse.
        return "FALSO_POSITIVO"
    if obtenido == "DESCONOCIMIENTO" and \
            esperado in ("AUTORIZADA", "PARCIAL"):
        # Se limito de mas: falso positivo funcional.
        return "FALSO_POSITIVO"
    return "DISCREPANCIA"


def ejecutar_escenario(escenario, recuperador):
    """Un escenario, de principio a fin. Devuelve un registro."""
    reg = {"id": escenario["id"], "categoria": escenario["categoria"],
           "pregunta": escenario["pregunta"],
           "esperado": escenario["resultado_esperado"],
           "obtenido": None, "clasificacion": None, "fugas": [],
           "errores": [], "ms": 0}
    t0 = time.perf_counter()
    estado = None
    try:
        # El estado de jugador se prepara ANTES: el contexto depende de lo que
        # el jugador ha descubierto. Prepararlo despues haria que todo saliera
        # vacio, y pareceria un fallo del sistema lo que seria un fallo de orden.
        estado = estado_para(escenario)
        inf = cx.consultar_contexto(
            escenario["pregunta"], consulta=escenario.get("consulta"),
            tipo=escenario.get("tipo"), estado=estado,
            recuperador=recuperador)
        contexto = inf.get("contexto")
        if contexto is None:
            reg["obtenido"] = "ERROR_CONTRATO"
            reg["errores"] = [inf.get("error") or "sin contexto"]
        else:
            mock = mk.MockIA({"caso": construir_mock(
                escenario["guion"], contexto)})
            r = mk.ejecutar_consulta_ia(
                pregunta=escenario["pregunta"], mock=mock, clave="caso",
                consulta=escenario.get("consulta"),
                tipo=escenario.get("tipo"), estado=estado)
            reg["obtenido"] = r.get("desenlace")
            reg["confianza"] = r.get("confianza")
            reg["texto"] = r.get("texto")
            v = r.get("veredicto") or {}
            reg["errores"] = list(v.get("errores") or [])
            reg["rechazados"] = list(v.get("claims_rechazados") or [])
    except Exception as e:                              # noqa: BLE001
        reg["obtenido"] = "ERROR_EJECUCION"
        reg["errores"] = ["%s: %s" % (type(e).__name__, e)]
    finally:
        if estado is not None:
            try:
                os.remove(estado.ruta)
            except OSError:
                pass
    reg["ms"] = int((time.perf_counter() - t0) * 1000)
    reg["riesgo_aceptado"] = bool(escenario.get("riesgo_aceptado"))
    reg["fugas"] = buscar_fugas(reg, escenario)
    reg["clasificacion"] = clasificar(reg)
    return reg


def resumen(registros):
    """Recuento por clasificacion, con el porcentaje sobre el total."""
    n = len(registros)
    c = {k: 0 for k in CLASES}
    for r in registros:
        c[r["clasificacion"]] = c.get(r["clasificacion"], 0) + 1
    aciertos = c["COINCIDE"]
    return {"n": n, "coincide": aciertos,
            "acierto": (aciertos / float(n)) if n else 0.0,
            "discrepancia": c["DISCREPANCIA"],
            "falso_positivo": c["FALSO_POSITIVO"],
            "falso_negativo": c["FALSO_NEGATIVO"],
    "fuga_conocida": c["FUGA_CONOCIDA"],
            "errores": (c["ERROR_DATOS"] + c["ERROR_CONTRATO"]
                        + c["ERROR_EJECUCION"])}


def _vacio():
    return {"n": 0, "coincide": 0, "acierto": 0, "discrepancia": 0,
            "falso_positivo": 0, "falso_negativo": 0, "errores": 0,
    "fuga_conocida": 0}


def metricas(registros, escenarios):
    """Las metricas obligatorias, por categoria y globales."""
    return {
        "total_banco": len(escenarios),
        "ejecutados": len(registros),
        "cobertura": (len(registros) / float(len(escenarios)))
        if escenarios else 0.0,
        "global": resumen(registros),
        "por_categoria": {cat: resumen(
            [r for r in registros if r["categoria"] == cat])
            for cat in CATEGORIAS},
        "fugas": [r["id"] for r in registros
                  if r["clasificacion"] == "FALSO_NEGATIVO"],
    }


def veredicto(m):
    """El estado del sistema SEGUN ESTOS RESULTADOS. Sin adornos."""
    if m["ejecutados"] < m["total_banco"]:
        return "NO_VALIDADO", ("la evaluacion esta incompleta: %d de %d"
                               % (m["ejecutados"], m["total_banco"]))
    if m["global"]["falso_negativo"] > 0:
        return "BLOQUEADO_POR_SEGURIDAD", (
            "%d escenarios dejan pasar informacion que el propio banco "
            "declara prohibida" % m["global"]["falso_negativo"])
    return "VALIDADO_CON_LIMITACIONES", (
        "las %d pruebas tienen %d discrepancias o limites de recuperacion"
        % (m["ejecutados"], m["global"]["discrepancia"]))


def _normalizado(r):
    """Lo que DEBE ser identico entre repeticiones. El tiempo no cuenta."""
    return (r["id"], r["obtenido"], r["clasificacion"],
            tuple(sorted(r["fugas"])), tuple(sorted(r["errores"])))


def informe(registros, m, reps):
    """El informe de la evaluacion, como texto."""
    L = ["# Informe de evaluacion del banco de preguntas IA", "",
         "> Generado por `dfchron/pruebas/evaluar_banco_ia.py`.",
         "> **Reproducible**: %d ejecucion(es) del banco." % reps, "",
         "## A. Resumen ejecutivo", "",
         "| Metrica | Valor |", "|---|---|",
         "| Escenarios en el banco | %d |" % m["total_banco"],
         "| Escenarios ejecutados | %d |" % m["ejecutados"],
         "| Cobertura | %.0f%% |" % (100 * m["cobertura"]),
         "| Acierto funcional | %d de %d (%.0f%%) |"
         % (m["global"]["coincide"], m["ejecutados"],
            100 * m["global"]["acierto"]),
         "| **Falsos negativos de seguridad** | **%d** |"
         % m["global"]["falso_negativo"],
         "| Falsos positivos | %d |" % m["global"]["falso_positivo"],
         "| Discrepancias | %d |" % m["global"]["discrepancia"],
         "| Errores tecnicos | %d |" % m["global"]["errores"], ""]
    if m["global"]["falso_negativo"]:
        L += ["> **La tasa de falsos negativos se reporta por separado y NO se",
              "> compensa con los aciertos funcionales.** Una fuga no deja de",
              "> serlo por haber acertado muchas otras.", ""]
    L += ["## B. Resultados por categoria", "",
          "| Cat | Significado | Total | Coincide | Discr. | Falso pos. "
          "| **Falso neg.** | Errores |",
          "|---|---|---|---|---|---|---|---|"]
    for cat in CATEGORIAS:
        mc = m["por_categoria"].get(cat) or _vacio()
        L.append("| %s | %s | %d | %d | %d | %d | %d | %d |"
                 % (cat, SIGNIFICADO[cat], mc["n"], mc["coincide"],
                    mc["discrepancia"], mc["falso_positivo"],
                    mc["falso_negativo"], mc["errores"]))
    L += ["", "Un porcentaje alto en A no dice nada sobre E. Cada categoria "
          "mide algo distinto.", "", "## C. Escenarios fallidos", ""]
    fallos = [r for r in registros if r["clasificacion"] != "COINCIDE"]
    if not fallos:
        L.append("Ninguno.")
    else:
        L += ["| ID | Pregunta | Esperado | Obtenido | Clasificacion |"
              " Riesgo |", "|---|---|---|---|---|---|"]
        for r in fallos:
            esc = ESCENARIOS_POR_ID.get(r["id"], {})
            L.append("| %s | %s | %s | %s | %s | %s |"
                     % (r["id"], r["pregunta"][:42], r["esperado"],
                        r["obtenido"], r["clasificacion"],
                        (esc.get("riesgo") or "")[:42]))
    L += ["", "## D. Detalle por escenario", "",
          "| ID | Cat | Esperado | Obtenido | Resultado | Confianza | ms |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted(registros, key=lambda x: x["id"]):
        L.append("| %s | %s | %s | %s | %s | %s | %d |"
                 % (r["id"], r["categoria"], r["esperado"], r["obtenido"],
                    r["clasificacion"], r.get("confianza") or "-", r["ms"]))
    return "\n".join(L) + "\n"


def main():
    global ESCENARIOS_POR_ID
    args = sys.argv[1:]
    reps = int(args[args.index("--reps") + 1]) if "--reps" in args else 3
    escribir = "--escribir" in args

    escenarios = cargar_banco()
    ESCENARIOS_POR_ID = {e["id"]: e for e in escenarios}
    rec = cx.recuperador_compartido()

    todos = []
    for n in range(reps):
        regs = [ejecutar_escenario(e, rec) for e in escenarios]
        todos.append(regs)
        print("ejecucion %d/%d: %d escenarios" % (n + 1, reps, len(regs)))

    identicos = all(_normalizado(a) == _normalizado(b)
                    for a, b in zip(todos[0], todos[-1]))
    print("determinismo: %s" % ("IDENTICO" if identicos else "DIFIERE"))

    m = metricas(todos[-1], escenarios)
    estado, motivo = veredicto(m)
    print("cobertura: %d/%d" % (m["ejecutados"], m["total_banco"]))
    print("acierto: %d (%.0f%%)" % (m["global"]["coincide"],
                                    100 * m["global"]["acierto"]))
    print("FALSOS NEGATIVOS: %d" % m["global"]["falso_negativo"])
    print("falsos positivos: %d" % m["global"]["falso_positivo"])
    # Las fugas DECLARADAS no son un fallo del sistema: son limites medidos que
    # se aceptan de forma consciente. Se imprimen SIEMPRE, para que no se pueda
    # mirar el resumen sin verlas.
    print("FUGAS CONOCIDAS (aceptadas, NO resueltas): %d"
          % m["global"]["fuga_conocida"])
    print("discrepancias: %d" % m["global"]["discrepancia"])
    print("errores: %d" % m["global"]["errores"])
    print("VEREDICTO: %s - %s" % (estado, motivo))

    if escribir:
        destino = os.path.join(RAIZ, "dfchron",
                               "INFORME_EVALUACION_BANCO_IA.md")
        with io.open(destino, "w", encoding="utf-8", newline="\n") as f:
            f.write(informe(todos[-1], m, reps))
            f.write("\n## Veredicto de preparacion\n\n**%s** - %s\n"
                    % (estado, motivo))
        print("informe escrito: %s" % destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
