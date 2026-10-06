#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RESTAURACION DE EMERGENCIA (no es parte del producto).

Restaura `servicio_consulta.py` al byte exacto tras una ejecucion del harness
de mutacion interrumpida a mitad.

Contexto: una ejecucion anterior fue cancelada por el limite de tiempo de la
shell MIENTRAS tenia aplicada una mutacion. El `finally` del harness nunca llego
a correr, y el fichero de produccion se quedo mutado. Esto se detecta porque el
hash deja de coincidir con el baseline conocido.

Uso:  python API_WEB/restaurar_servicio.py
"""
import hashlib
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.abspath(os.path.join(_AQUI, "..", "dfchron",
                                    "servicio_consulta.py"))

#: Hash conocido del fichero intacto. Si tras restaurar no coincide, NO se
#: continua: significa que hay otro cambio y hay que investigar antes.
ESPERADO = "0a5b6b1c3244e6192752f311b89d075e6b75de23d971a4972fdba54f3a73f834"

MAL = b'    base["evidence"] = None'
BIEN = b'    base["evidence"] = _evidencia(tipo, df_id, campos) if tipo else None'


def main():
    with open(RUTA, "rb") as fh:
        antes = fh.read()

    print("ruta              : %s" % RUTA)
    print("hash antes        : %s" % hashlib.sha256(antes).hexdigest())
    print("CRLF=%d  LF sueltos=%d"
          % (antes.count(b"\r\n"), antes.count(b"\n") - antes.count(b"\r\n")))

    if hashlib.sha256(antes).hexdigest() == ESPERADO:
        print("\nEl fichero ya esta intacto. No se toca nada.")
        return 0

    n_mal, n_bien = antes.count(MAL), antes.count(BIEN)
    print("ocurrencias mutadas : %d" % n_mal)
    print("ocurrencias sanas   : %d" % n_bien)
    if n_mal != 1:
        print("\nABORTO: se esperaba exactamente 1 ocurrencia mutada y hay %d."
              % n_mal)
        print("No se restaura a ciegas. Se investiga primero.")
        return 2

    # Escritura BINARIA: no toca finales de linea ni anade BOM.
    with open(RUTA, "wb") as fh:
        fh.write(antes.replace(MAL, BIEN, 1))

    with open(RUTA, "rb") as fh:
        despues = fh.read()
    h = hashlib.sha256(despues).hexdigest()
    print("hash despues      : %s" % h)
    print("hash esperado     : %s" % ESPERADO)

    if h != ESPERADO:
        print("\nABORTO: el hash NO coincide. Queda otro cambio sin explicar.")
        return 2
    print("\nRESTAURADO byte a byte. Sin BOM, finales de linea intactos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
