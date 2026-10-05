#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas de PROPAGACION de identidad del mundo (P1.2)
======================================================================

Comprueba, EJECUTANDO de verdad, que la identidad del mundo capturada en P1.1
llega a los consumidores sin mezclarse con la del dataset ni con la del estado.

Grupos (mision P1.2, PARTE 5):

  1. Captura correcta            -> lo que se propaga es lo capturado
  2. Persistencia correcta      -> sobrevive a disco y a proceso nuevo
  3. Propagacion sin perdida     -> llega intacto al consumidor final
  4. Ausencia explicita         -> se declara, con motivo; nunca se inventa
  5. Separacion mundo/dataset   -> ejes distintos, no se confunden
  6. Compatibilidad             -> los consumidores anteriores siguen igual
  7. Sin duplicacion            -> una sola interpretacion de la ausencia
  8. Sin acceso directo a disco -> la Web no lee `dataset_version.json`

Nada de esto toca el dataset real: se usa un directorio temporal por prueba.
"""
import io
import os
import re
import sys
import json
import shutil
import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _r in (_RAIZ, os.path.join(_RAIZ, "00_SOURCE", "tools")):
    if _r not in sys.path:
        sys.path.insert(0, _r)

from dfchron import ia_conocimiento as ic          # noqa: E402
from dfchron import servicio as svc                # noqa: E402

_SERVIDOR = None


def _arrancar():
    global _SERVIDOR
    if _SERVIDOR is None:
        from dfchron.api import crear_servidor
        _SERVIDOR = crear_servidor(puerto=0)
        threading.Thread(target=_SERVIDOR.serve_forever, daemon=True).start()
    return _SERVIDOR


def pedir(ruta):
    """Peticion HTTP REAL. Devuelve (codigo, cuerpo_json)."""
    base = "http://127.0.0.1:%d" % _arrancar().server_address[1]
    req = urllib.request.Request(base + ruta, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8")
        try:
            return e.code, json.loads(crudo)
        except ValueError:
            return e.code, {}
    except Exception as exc:                        # noqa: BLE001
        return -1, {"<excepcion>": type(exc).__name__}


def setUpModule():
    _arrancar()


# =============================================================================
# UTILIDADES DE PRUEBA
# =============================================================================
class _Base(unittest.TestCase):
    """Cada prueba escribe un `dataset_version.json` de verdad, en temporal."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="dfchron_mundo12_")
        self.ruta = os.path.join(self.dir, "dataset_version.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def escribir(self, mundo=None, **extra):
        """Un registro real. Si `mundo` es None, el registro es pre-P1.1."""
        doc = {"actualizada": "2026-10-04T10:00:00+02:00",
               "dataset_id": "v1-04170363943d4ba1",
               "entradas": {}, "salidas": {"sites": {"sha256": "aa" * 32}},
               "conteos": {"eventos": 1}}
        doc.update(extra)
        if mundo is not None:
            doc["mundo"] = mundo
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
        return self.ruta

    @staticmethod
    def mundo_completo(nombre="Orid En", carpeta="region1"):
        return {"world_name": nombre, "world_folder": carpeta,
                "world_name_ausente_porque": None,
                "world_folder_ausente_porque": None}
# =============================================================================
# 1. CAPTURA CORRECTA
# =============================================================================
class PruebaCaptura(_Base):
    """1. Lo que se propaga es EXACTAMENTE lo que P1.1 capturó."""

    def test_los_dos_campos_llegan_intactos(self):
        self.escribir(self.mundo_completo("Orid En", "region1"))
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "Orid En")
        self.assertEqual(m["world_folder"], "region1")

    def test_el_motivo_de_ausencia_travela_con_el_campo(self):
        self.escribir({"world_name": "Orid En", "world_folder": "UNKNOWN",
                       "world_name_ausente_porque": None,
                       "world_folder_ausente_porque": "el fichero se renombro"})
        m = ic.mundo(self.ruta)
        self.assertIsNone(m["world_name_ausente_porque"])
        self.assertEqual(m["world_folder_ausente_porque"],
                         "el fichero se renombro")


# =============================================================================
# 2. PERSISTENCIA CORRECTA
# =============================================================================
class PruebaPersistencia(_Base):
    """2. Sobrevive al disco y a un proceso nuevo."""

    def test_lectura_repetida_es_identica(self):
        self.escribir(self.mundo_completo())
        self.assertEqual(ic.mundo(self.ruta), ic.mundo(self.ruta))

    def test_sobrevive_a_otro_proceso(self):
        """Se relee desde un interprete NUEVO, no desde memoria del import."""
        self.escribir(self.mundo_completo("Reino Antiguo", "region7"))
        codigo = (
            "import json,sys;sys.path.insert(0,%r);sys.path.insert(0,%r);"
            "from dfchron import ia_conocimiento as ic;"
            "print(json.dumps(ic.mundo(%r)))"
            % (_RAIZ, os.path.join(_RAIZ, "00_SOURCE", "tools"), self.ruta))
        import subprocess
        p = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        self.assertEqual(json.loads(p.stdout)["world_name"], "Reino Antiguo")
        self.assertEqual(json.loads(p.stdout)["world_folder"], "region7")

    def test_cambiar_el_resto_no_altera_la_identidad(self):
        """Un cambio que no toca `mundo` no cambia la identidad del mundo."""
        self.escribir(self.mundo_completo())
        antes = ic.mundo(self.ruta)
        self.escribir(self.mundo_completo(), actualizado="2026-10-05")
        self.assertEqual(ic.mundo(self.ruta), antes)


# =============================================================================
# 3. PROPAGACION SIN PERDIDA (ejecucion REAL, de Python a HTTP)
# =============================================================================
class PruebaPropagacionReal(unittest.TestCase):
    """3. De la persistencia al consumidor final, pasando por HTTP de verdad."""

    def test_llego_a_la_api_real(self):
        codigo, env = pedir("/api/salud")
        self.assertEqual(codigo, 200)
        mundo = env["data"]["dataset"]["mundo"]
        for clave in ("world_name", "world_folder",
                      "world_name_ausente_porque",
                      "world_folder_ausente_porque"):
            self.assertIn(clave, mundo)

    def test_lo_que_llega_es_identico_a_lo_que_hay_en_disco(self):
        """Compara VALORES: lee el disco de verdad y lo confronta."""
        codigo, env = pedir("/api/salud")
        self.assertEqual(codigo, 200)
        por_http = env["data"]["dataset"]["mundo"]
        del_disco = ic.mundo()
        self.assertEqual(por_http, del_disco)

# =============================================================================
# 4. AUSENCIA EXPLICITA  (PARTE 4: los seis escenarios)
# =============================================================================
class PruebaAusencia(_Base):
    """4. Ninguna ausencia se convierte en una identidad inventada."""

    def test_a_ambos_disponibles(self):
        self.escribir(self.mundo_completo("Orid En", "region1"))
        m = ic.mundo(self.ruta)
        self.assertEqual((m["world_name"], m["world_folder"]),
                         ("Orid En", "region1"))
        self.assertIsNone(m["world_name_ausente_porque"])
        self.assertIsNone(m["world_folder_ausente_porque"])

    def test_b_solo_world_name(self):
        self.escribir({"world_name": "Orid En", "world_folder": "UNKNOWN",
                       "world_name_ausente_porque": None,
                       "world_folder_ausente_porque": "sin prefijo save_dir"})
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "Orid En")
        self.assertEqual(m["world_folder"], "UNKNOWN")
        self.assertEqual(m["world_folder_ausente_porque"], "sin prefijo save_dir")

    def test_c_solo_world_folder(self):
        self.escribir({"world_name": "UNKNOWN", "world_folder": "region1",
                       "world_name_ausente_porque": "sin etiqueta en el export",
                       "world_folder_ausente_porque": None})
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "region1")
        self.assertEqual(m["world_name_ausente_porque"],
                         "sin etiqueta en el export")

    def test_d_ambos_desconocidos(self):
        self.escribir({"world_name": "UNKNOWN", "world_folder": "UNKNOWN",
                       "world_name_ausente_porque": "no consta",
                       "world_folder_ausente_porque": "no consta"})
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")
        self.assertEqual(m["world_name_ausente_porque"], "no consta")

    def test_registro_anterior_a_p1_1(self):
        """El caso REAL: el dataset activo se genero antes de P1.1."""
        self.escribir()                       # sin clave `mundo`
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")
        self.assertEqual(m["world_name_ausente_porque"], ic.SIN_MUNDO)

    def test_fichero_inexistente(self):
        m = ic.mundo(os.path.join(self.dir, "no_existe.json"))
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_name_ausente_porque"],
                         ic.SIN_VERSION_DATASET)

    def test_no_leer_no_es_lo_mismo_que_no_tener_mundo(self):
        """«No hay registro» y «el registro es anterior a P1.1» se distinguen.

        Si compartieran motivo, un fallo de lectura pareciera una decision, y
        nadie podria decir despues si faltaba el fichero o faltaba el dato.
        """
        ausente = ic.mundo(os.path.join(self.dir, "no_existe.json"))
        self.escribir()                       # registro real, sin clave `mundo`
        previo = ic.mundo(self.ruta)
        self.assertNotEqual(ausente["world_name_ausente_porque"],
                            previo["world_name_ausente_porque"])
        self.assertEqual(ausente["world_name_ausente_porque"],
                         ic.SIN_VERSION_DATASET)
        self.assertEqual(previo["world_name_ausente_porque"], ic.SIN_MUNDO)

    def test_registro_ilegible_no_rompe_el_dataset_id(self):
        """Un registro que no se puede leer no inventa un `dataset_id`."""
        self.escribir()
        ruta = os.path.join(self.dir, "roto.json")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("[[[no es json")
        self.assertEqual(ic._leer_registro(ruta), None)
        self.assertEqual(ic.dataset_id(), ic.DATASET_ID)

    def test_json_corrupto(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write("{esto no es json")
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")

    def test_valores_no_texto_son_ausencias(self):
        """Un numero no es un nombre de mundo: se declara, no se convierte."""
        self.escribir({"world_name": 42, "world_folder": ["region1"],
                       "world_name_ausente_porque": "no era texto",
                       "world_folder_ausente_porque": "no era texto"})
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")

    def test_cadena_vacia_es_ausencia(self):
        self.escribir({"world_name": "   ", "world_folder": "",
                       "world_name_ausente_porque": "vacia",
                       "world_folder_ausente_porque": "vacia"})
        m = ic.mundo(self.ruta)
        self.assertEqual(m["world_name"], "UNKNOWN")
        self.assertEqual(m["world_folder"], "UNKNOWN")

    def test_la_ausencia_no_se_rellena_con_reloj(self):
        """Nada de fechas, nada de sellos, nada de rutas."""
        self.escribir()
# =============================================================================
# 5. SEPARACION MUNDO / DATASET
# =============================================================================
class PruebaSeparacion(_Base):
    """5. `dataset_id` y `world_name` son ejes distintos, y no se confunden."""

    def test_e_dos_mundos_con_el_mismo_nombre_no_se_confunden(self):
        """Mismo nombre, carpetas distintas: la carpeta las separa."""
        a = self.escribir(self.mundo_completo("Orid En", "region1"))
        ma = ic.mundo(a)
        b = self.escribir(self.mundo_completo("Orid En", "region2"))
        mb = ic.mundo(b)
        self.assertEqual(ma["world_name"], mb["world_name"])
        self.assertNotEqual(ma["world_folder"], mb["world_folder"])

    def test_f_dos_datasets_identicos_de_carpetas_distintas(self):
        """Mismo contenido, distinta carpeta: el dataset_id no las distingue."""
        secciones = {"sites": {"lineas": 7, "sha256": "dd" * 32, "bytes": 3}}
        # Dos ficheros DISTINTOS: si compartieran la misma ruta, compararian
        # consigo mismos y la prueba no probaria nada.
        a = os.path.join(self.dir, "a.json")
        b = os.path.join(self.dir, "b.json")
        for ruta, carpeta in ((a, "region1"), (b, "region2")):
            doc = {"actualizada": "2026-10-04T10:00:00+02:00",
                   "dataset_id": "v1-04170363943d4ba1",
                   "salidas": dict(secciones),
                   "mundo": self.mundo_completo("Orid En", carpeta)}
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False)
        # El hash es el mismo: no ve el mundo.
        self.assertEqual(json.loads(_leer(a))["dataset_id"],
                         json.loads(_leer(b))["dataset_id"])
        # La identidad de mundo si los distingue. Ese es su motivo de existir.
        self.assertEqual(ic.mundo(a)["world_folder"], "region1")
        self.assertEqual(ic.mundo(b)["world_folder"], "region2")
        self.assertNotEqual(ic.mundo(a)["world_folder"],
                            ic.mundo(b)["world_folder"])

    def test_mundo_nunca_es_el_dataset_id(self):
        self.escribir(self.mundo_completo())
        m = ic.mundo(self.ruta)
        self.assertNotEqual(m["world_name"], ic.DATASET_ID)
        self.assertNotEqual(m["world_folder"], ic.DATASET_ID)

    def test_el_estado_no_se_inventa_a_partir_del_mundo(self):
        """Ningun campo de estado aparece en la identidad propagada."""
        self.escribir(self.mundo_completo())
        serializado = json.dumps(ic.mundo(self.ruta)).lower()
        for prohibido in ("state_id", "snapshot_id", "tick_id", "branch_id",
                          "lineage", "estado_id", "revision", "tick"):
            self.assertNotIn(prohibido, serializado)

    def test_la_identidad_no_lleva_reloj(self):
        """`world_name` no es una version: no tiene fecha ni contador."""
# =============================================================================
# 6. COMPATIBILIDAD
# =============================================================================
class PruebaCompatibilidad(unittest.TestCase):
    """6. Los consumidores anteriores siguen viendo exactamente lo mismo."""

    #: Claves que `dataset` ya tenia ANTES de P1.2. No se tocan.
    CLAVES_PREVIAS = ("dataset_id", "dataset_generado", "conteos",
                      "certainty", "motivo")

    def test_las_claves_previas_no_cambian(self):
        codigo, env = pedir("/api/salud")
        self.assertEqual(codigo, 200)
        d = env["data"]["dataset"]
        for clave in self.CLAVES_PREVIAS:
            self.assertIn(clave, d)
        self.assertEqual(d["dataset_id"], "v1-04170363943d4ba1")

    def test_mundo_es_la_unica_clave_nueva(self):
        codigo, env = pedir("/api/salud")
        d = env["data"]["dataset"]
        self.assertEqual(set(d) - set(self.CLAVES_PREVIAS), {"mundo"})

    def test_el_sobre_de_consulta_no_cambio(self):
        """Las rutas de `servicio_consulta` siguen con las mismas claves."""
        codigo, env = pedir("/api/consulta/entidad/figura/712")
        self.assertEqual(codigo, 200)
        self.assertEqual(sorted(env["identity"]), ["df_id", "tipo"])
        self.assertEqual(env["dataset_id"], "v1-04170363943d4ba1")
        # Y NO lleva `mundo`: ese sobre lo construye el modulo CONGELADO.
        self.assertNotIn("mundo", env)

    def test_salud_sigue_teniendo_sus_claves_originales(self):
        codigo, env = pedir("/api/salud")
        d = env["data"]
        for clave in ("estado", "eventos", "figuras", "ruta_datos",
                      "export_root", "limite_maximo", "dataset"):
            self.assertIn(clave, d)
# =============================================================================
# 7. AUSENCIA DE DUPLICACION
# =============================================================================
def _sin_comentarios(texto):
    """Quita `//` y `/* */` para mirar solo el codigo ejecutable.

    Importa porque un comentario puede CITAR un informe sin que el programa lea
    nada. Comprobar el texto entero haria fallar esta suite por un docstring.
    """
    limpio = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    return re.sub(r"//[^\n]*", "", limpio)


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


class PruebaSinDuplicacion(unittest.TestCase):
    """7. Una sola lectura, una sola interpretacion de la ausencia."""

    @staticmethod
    def _fuente(*partes):
        return _leer(os.path.join(_RAIZ, "dfchron", *partes))

    def test_la_web_no_reimprime_el_criterio_de_ausencia(self):
        """La Web LEE lo que llega; no decide que es una ausencia."""
        fuente = self._fuente("site", "src", "lib", "dataset.ts")
        self.assertIn("world_name_ausente_porque", fuente)
        codigo = _sin_comentarios(fuente)
        # Y NO inventa motivos ni rutas propias. Se mira el CODIGO, no los
        # comentarios: un docstring puede citar un informe sin que eso sea leer
        # el dataset, y una prueba que confundiera ambos no valdria para nada.
        self.assertNotIn("dataset_version.json", codigo)
        self.assertNotIn("00_SOURCE", codigo)
        self.assertNotIn("processar_merged", codigo)

    def test_el_servicio_delega_y_no_reimplementa(self):
        """`_mundo_desde_documento` pide a `ia_conocimiento`, no decide."""
        fuente = self._fuente("servicio.py")
        i = fuente.index("def _mundo_desde_documento")
        cuerpo = fuente[i:i + 700]
        self.assertIn("ia_conocimiento", cuerpo)
        self.assertIn("mundo_de", cuerpo)

    def test_el_servicio_no_abre_el_fichero_una_segunda_vez(self):
        """Reutiliza el documento que `_leer_version()` ya leyo."""
        fuente = self._fuente("servicio.py")
        i = fuente.index("def _mundo_desde_documento")
        self.assertNotIn("open(", fuente[i:i + 700])
        self.assertNotIn("dataset_version.json", fuente[i:i + 700])

    def test_resumen_dataset_no_decide_ausencias(self):
        """La rama que absence es la de `mundo_de`, no una suya."""
        fuente = self._fuente("servicio.py")
        j = fuente.index("def _resumen_dataset")
# =============================================================================
# 8. AUSENCIA DE ACCESO DIRECTO AL DATASET DESDE LA WEB
# =============================================================================
class PruebaWebSinAccesoDirecto(unittest.TestCase):
    """8. La Web no lee el dataset: consume la API."""

    #: Ficheros de la Web que deben quedarse sin acceso a disco.
    WEB = (("site", "src", "lib", "dataset.ts"),
           ("site", "src", "lib", "api.ts"),
           ("site", "src", "lib", "vistas.ts"),
           ("web", "app.js"))

    def test_la_web_no_abre_el_dataset(self):
        for partes in self.WEB:
            ruta = os.path.join(_RAIZ, "dfchron", *partes)
            if not os.path.isfile(ruta):
                continue
            codigo = _sin_comentarios(_leer(ruta))
            for prohibido in ("dataset_version.json", "00_SOURCE",
                              "processed/merged", ".jsonl", "original_data"):
                self.assertNotIn(
                    prohibido, codigo,
                    "%s usa %s en codigo: la Web no lee el dataset"
                    % (partes[-1], prohibido))

    def test_la_web_no_hace_fetch_de_ficheros(self):
        """Solo pide `/api/...`: no pide ficheros."""
        for partes in self.WEB:
            ruta = os.path.join(_RAIZ, "dfchron", *partes)
            if not os.path.isfile(ruta):
                continue
            codigo = _sin_comentarios(_leer(ruta))
            for destino in re.findall(r"""fetch\(\s*[`'"]([^`'"]+)""", codigo):
                self.assertTrue(
                    destino.startswith("/api") or destino.startswith("api"),
                    "%s hace fetch de %r, que no es la API"
                    % (partes[-1], destino))

    def test_el_mundo_llega_por_la_api_y_no_por_un_fichero(self):
        """`mundo` viaja DENTRO de la respuesta de /api/salud."""
        codigo, env = pedir("/api/salud")
        self.assertEqual(codigo, 200)
        self.assertIn("mundo", env["data"]["dataset"])




if __name__ == "__main__":
    unittest.main(verbosity=2)

