#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: harness PERMANENTE de mutation testing de la frontera
=======================================================================

QUE DEMUESTRA
-------------
Que las pruebas de API y Web dependen REALMENTE de `servicio_consulta.py`, y no
de una coincidencia de valores.

Una prueba que compara «el JSON de la API» con «el JSON del servicio» pasa
igual aunque la API se salte el servicio, si el resultado coincide. Estas
mutaciones atacan la **semantica**, no el texto:

| Mutacion                | Que rompe                                         |
|-------------------------|--------------------------------------------------|
| A · `dataset_id` falso  | La API anuncia un mundo que no es                |
| B · evidencia eliminada | La API pierde la procedencia                       |
| C · estado contractual | `NOT_VERIFIED` pasa a `FOUND`                      |
| D · resultado alterado  | `buscar_relaciones` deja de delegar              |
| E · bypass de la frontera| El adaptador llama a `servicio.py` directamente  |
| F · `dataset_id` eliminado | El sobre deja de decir de que mundo es        |
| G · `state_version` falseado | La evidencia declara otra version             |
| H · bypass del nucleo   | El adaptador lee `nucleo.Archivo` sin el servicio |
| I · respuesta fabricada | La API devuelve datos sin preguntar al servicio   |

MUTACION E es la importante entre las de bypass: simula justo lo que la regla 9
prohibe («API -> indice» en vez de «API -> servicio_consulta -> indice»).
MUTACION H es su forma mas agresiva: saltar las DOS capas de una vez.
MUTACION I es la mas silenciosa: si el envelope fabricado coincide con el
correcto, ninguna prueba de igualdad de valores la detectaria.

GARANTIAS DEL HARNESS
---------------------
1. Guarda los BYTES originales, no una re-serializacion.
2. Restaura en un `finally`, pase lo que pase.
3. Verifica por HASH que la restauracion es exacta.
4. **Preserva CRLF/LF**: escribir en binario evita el cambio de finales de
   linea que en una auditoria anterior rompio el hash de produccion.

Uso:
    python dfchron\\pruebas\\probar_mutation_frontera.py
"""
import hashlib
import io
import os
import subprocess
import sys
import unittest

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))

_SVC = os.path.join(_RAIZ, "dfchron", "servicio_consulta.py")
_ADA = os.path.join(_RAIZ, "dfchron", "adaptador_consulta.py")
_API = os.path.join(_RAIZ, "dfchron", "api.py")
_IAC = os.path.join(_RAIZ, "dfchron", "ia_conocimiento.py")

#: Ficheros de produccion que el harness puede tocar (y restaura).
MUTADOS = (_SVC, _ADA, _API, _IAC)

#: Suites que deben detectar una mutacion. Cada una corre en un PROCESO
#: aparte: si no, el modulo ya importado seguiria con el codigo viejo.
#: Las rutas pueden ser relativas a `dfchron/pruebas/` o absolutas.
SUITES = ("probar_integracion_consulta.py", "probar_api.py", "probar_web.py",
          os.path.join(_RAIZ, "API_WEB", "probar_frontera_adversarial.py"))

#: (nombre, fichero, buscar, reemplazar)
MUTACIONES = [
    ("A · dataset_id anuncia otro mundo",
     _SVC, 'base["dataset_id"] = ic.DATASET_ID',
     'base["dataset_id"] = "v1-inventado"'),
    ("B · evidencia se borra",
     _SVC, 'base["evidence"] = _evidencia(tipo, df_id, campos) if tipo else None',
     'base["evidence"] = None'),
    ("C · NOT_VERIFIED pasa a FOUND",
     _SVC, "            NOT_VERIFIED, tipo=tipo, df_id=df_id,",
     "            FOUND, tipo=tipo, df_id=df_id,"),
    ("D · relaciones deja de delegar en el servicio",
     _SVC, "    env = servicio.figura_relaciones(str(origen), tipo=tipo_relacion, limite=lim)",
     "    env = {'ok': True, 'data': [], 'total_encontrados': 0,"
     " 'devueltos': 0, 'truncado': False}"),
    ("E · el adaptador se salta la frontera",
     _ADA, '    return _responder(qc.obtener_entidad("figura", df_id))',
     "    import dfchron.servicio as _s\n"
     "    return _responder(_s.figura(str(df_id)))"),
    ("F · dataset_id desaparece del sobre",
     _SVC, 'base["dataset_id"] = ic.DATASET_ID',
     'base["dataset_id"] = None'),
    ("G · state_version declara otra version",
     _IAC, "list(fuentes_xml) or None, state_version=DATASET_ID)",
     'list(fuentes_xml) or None, state_version="v1-otro-mundo")'),
    ("H · el adaptador lee el nucleo sin servicio",
     _ADA, '    return _responder(qc.obtener_entidad("figura", df_id))',
     "    import dfchron.servicio as _s\n"
     "    _a = _s.obtener_archivo()\n"
     "    return _responder({'estado': 'FOUND', 'ok': True,\n"
     "                       'data': _a.ficha_figura(str(df_id)),\n"
     "                       'dataset_id': 'v1-inventado'})"),
    ("I · la API fabrica la respuesta sin preguntar",
     _API, '    lambda p, q: ac.ficha_figura(p["id"])), "figura")',
     '    lambda p, q: {"ok": True, "data": {"df_id": p["id"],\n'
     '                                     "nombre": "Fabricado"},\n'
     '                "estado": "FOUND", "dataset_id": "v1-inventado"}),\n'
     '    "figura")'),
]


def _bytes_originales(ruta):
    with io.open(ruta, "rb") as f:
        return f.read()


def _escribir_exacto(ruta, datos):
    """Escribe BYTES: no toca finales de linea ni anade BOM."""
    with io.open(ruta, "wb") as f:
        f.write(datos)


def _ejecutar(suite):
    """Ejecuta una suite en un proceso limpio. Acepta ruta absoluta o relativa."""
    ruta = suite if os.path.isabs(suite) else os.path.join(
        _RAIZ, "dfchron", "pruebas", suite)
    if not os.path.isfile(ruta):
        raise AssertionError("la suite %s no existe: el harness probaria "
                             "nada" % suite)
    return subprocess.run([sys.executable, ruta], cwd=_RAIZ,
                          capture_output=True, text=True, timeout=900)


class TestMutationFrontera(unittest.TestCase):
    """Cada mutacion debe ser detectada por AL MENOS una suite."""

    def test_cada_mutacion_es_detectada(self):
        informe = []
        for nombre, ruta, buscar, poner in MUTACIONES:
            with self.subTest(mutacion=nombre):
                original = _bytes_originales(ruta)
                fuente = original.decode("utf-8")
                self.assertIn(buscar, fuente,
                              "el patron de %s ya no existe: la mutacion "
                              "dejaria de probar nada" % nombre)
                mutado = fuente.replace(buscar, poner, 1)
                try:
                    _escribir_exacto(ruta, mutado.encode("utf-8"))
                    detectados = []
                    for suite in SUITES:
                        if _ejecutar(suite).returncode != 0:
                            detectados.append(suite)
                finally:
                    _escribir_exacto(ruta, original)
                # La restauracion debe ser EXACTA, no solo equivalente.
                self.assertEqual(
                    hashlib.sha256(_bytes_originales(ruta)).hexdigest(),
                    hashlib.sha256(original).hexdigest(),
                    "%s no se restauro exactamente" % nombre)
                self.assertTrue(
                    detectados,
                    "MUTACION %s SOBREVIVE: ninguna suite la detecta. Las "
                    "pruebas no dependen de la frontera." % nombre)
                informe.append("%-44s detectada por %s"
                               % (nombre, ", ".join(detectados)))
        print("\n".join(informe))

    def test_el_harness_no_deja_el_repo_sucio(self):
        """Los ficheros de produccion conservan bytes y finales de linea."""
        for ruta in MUTADOS:
            with self.subTest(fichero=os.path.basename(ruta)):
                datos = _bytes_originales(ruta)
                self.assertFalse(datos.startswith(b"\xef\xbb\xbf"),
                                 "BOM en %s" % os.path.basename(ruta))
                crlf = datos.count(b"\r\n")
                lf = datos.count(b"\n") - crlf
                self.assertTrue(crlf == 0 or lf == 0,
                                "finales de linea mezclados en %s"
                                % os.path.basename(ruta))

    def test_todos_los_ficheros_mutados_existen(self):
        """Un patron de mutacion sobre un fichero inexistente no probaria nada."""
        for ruta in MUTADOS:
            with self.subTest(fichero=os.path.basename(ruta)):
                self.assertTrue(os.path.isfile(ruta),
                                "el harness mutaria un fichero inexistente")

    def test_no_hay_temporales_del_harness(self):
        """Ni una copia de seguridad olvidada junto al codigo."""
        for nombre in ("servicio_consulta_orig.py", "adaptador_consulta_orig.py",
                       "servicio_consulta.bak", "adaptador_consulta.bak",
                       "_servicio_consulta.py", "_adaptador_consulta.py"):
            with self.subTest(temporal=nombre):
                self.assertFalse(
                    os.path.exists(os.path.join(_RAIZ, "dfchron", nombre)),
                    "quedo un temporal del harness: %s" % nombre)


if __name__ == "__main__":
    unittest.main(verbosity=2)
