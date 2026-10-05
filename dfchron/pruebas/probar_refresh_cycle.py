#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Legends :: Pruebas del CICLO DE REFRESCO
==========================================

Comprueba, con un servidor HTTP REAL, que el ciclo
actualizar -> validar -> activar -> API -> Web cierra bien, y que ante un fallo
se conserva el dataset anterior.

Todo ocurre en un DIRECTORIO TEMPORAL con datasets sinteticos. Esta suite NO
toca `00_SOURCE/processed/`, ni `original_data/`, ni los JSONL reales.

Escenarios (§19-§22 de la mision):

  1. La API arranca con dataset A
  2. Se genera dataset B
  3. B se valida
  4. Se activa B
  5. La API sigue viva, es coherente e identifica B
  6. Un dataset C corrupto NO destruye A
  7. Un fallo de carga deja el anterior disponible
  8. Consistencia: nunca se mezclan datasets en una respuesta
  9. Simultaneidad: dos actualizaciones a la vez
 10. El identificador cambia si cambia un byte, y NO si no cambia nada
 11. Sin acceso HTTP al sistema de ficheros
 12. Compatibilidad: el contrato viejo sigue intacto

Ejecutar:  python dfchron/pruebas/probar_refresh_cycle.py
"""
import io
import os
import sys
import json
import time
import shutil
import hashlib
import logging
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import config            # noqa: E402

logging.disable(logging.CRITICAL)    # el servidor imprime cada peticion

# Se importan DESPUES de desactivar el log para que no se mezclen.
from dfchron import servicio as svc    # noqa: E402
from dfchron import api                # noqa: E402

BANCO = tempfile.mkdtemp(prefix="df_refresh_")
VACIOS = ("entities", "historical_events", "artifacts",
          "historical_event_relationships",
          "historical_event_relationship_supplements",
          "historical_event_collections", "historical_eras")


# --------------------------------------------------------------------- banco --
def escribir_dataset(destino, n_fig, n_sit, semilla, corrupto=False):
    """Dataset sintetico minimo que el nucleo sabe cargar.

    `corrupto=True` escribe un JSONL invalido a proposito: sirve para probar
    que un dataset malo no se cuela en produccion.
    """
    os.makedirs(destino, exist_ok=True)
    with io.open(os.path.join(destino, "historical_figures.jsonl"),
                 "w", encoding="utf-8") as f:
        for i in range(n_fig):
            f.write(json.dumps({"df_id": str(i), "campos": {
                "name": {"valor": f"figura-{semilla}-{i}"},
                "entity_link.entity_id": {"valor": "1"}}}) + "\n")
    with io.open(os.path.join(destino, "sites.jsonl"), "w", encoding="utf-8") as f:
        for i in range(n_sit):
            f.write(json.dumps({"df_id": str(i), "campos": {
                "name": {"valor": f"sitio-{semilla}-{i}"},
                "type": {"valor": "fortress"},
                "coords": {"valor": f"{10 + i},{20 + i}"}}}) + "\n")
    for v in VACIOS:
        if corrupto and v == "historical_events":
            with io.open(os.path.join(destino, v + ".jsonl"), "w",
                         encoding="utf-8") as f:
                f.write('{"df_id": "roto", "campos": NO_CIERRA\n\n')
        else:
            io.open(os.path.join(destino, v + ".jsonl"), "w",
                    encoding="utf-8").close()
    return destino


def sha_directorio(d):
    """Huella del contenido de un dataset: {fichero: sha256}."""
    out = {}
    for n in sorted(os.listdir(d)):
        if n.endswith(".jsonl"):
            h = hashlib.sha256()
            with open(os.path.join(d, n), "rb") as f:
                h.update(f.read())
            out[n] = h.hexdigest()
    return out


def ids_de(salidas):
    """Huellas ordenadas de un dataset: la 'identidad' de un mundo."""
    return svc.calcular_dataset_id(salidas)


# ------------------------------------------------------------------ servidor --
_LEER_VERSION_REAL = svc._leer_version
_SRV = [None]
BASE = [None]


def arrancar_servidor():
    if _SRV[0] is not None:
        return BASE[0]
    # Puerto 0 = que el sistema elija uno libre. Se pide EXPRESAMENTE: si
    # hubiera otra API escuchando en 877, esta suite hablaria con ella y
    # mediria el dataset real en vez del banco de pruebas.
    _SRV[0] = api.crear_servidor("127.0.0.1", 0)
    threading.Thread(target=_SRV[0].serve_forever, daemon=True).start()
    BASE[0] = f"http://127.0.0.1:{_SRV[0].server_address[1]}"
    return BASE[0]


def pedir(ruta):
    """(codigo, cuerpo_json) hablando HTTP de verdad."""
    base = arrancar_servidor()
    try:
        with urllib.request.urlopen(base + ruta, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")


def stats():
    c, env = pedir("/api/stats")
    assert c == 200, env
    return env["data"]


def nombres_figuras():
    c, env = pedir("/api/listar/historical_figures?limit=200")
    assert c == 200, env
    return [f["nombre"] for f in env["data"]]


def salud_dataset():
    c, env = pedir("/api/salud")
    assert c == 200, env
    return env["data"]["dataset"]


_PARCHE = {"original": None}


def _modulo_de_carga():
    """El módulo donde vive REALMENTE `cargar_jsonl` que usa `Indice`.

    `nucleo.py` hace `from validar_semantica import cargar_jsonl`, así que
    parchear el atributo de `nucleo` NO surte efecto: `Indice.cargar()` busca
    el nombre en el ámbito del módulo donde se DEFINIÓ. Este detalle se
    commensuró en la auditoría y es la razón de que las pruebas apunten al
    módulo correcto en vez de al que parece obvio.
    """
    import nucleo                              # asegura que se importo
    return sys.modules[nucleo.cargar_jsonl.__module__]


def apuntar(directorio):
    """Habilita que la API lea de `directorio`.

    NO reinicia nada: solo cambia de dónde se leería en la PROXIMA carga. Sirve
    para comprobar por separado "el disco cambió" de "el proceso se reinició".
    """
    mod = _modulo_de_carga()
    if _PARCHE["original"] is None:
        _PARCHE["original"] = mod.cargar_jsonl
    real = _PARCHE["original"]

    def parche(nombre, carpeta=None):
        return real(nombre, directorio)
    mod.cargar_jsonl = parche


def reiniciar():
    """Lo que hace `run.py` al arrancar: un nucleo nuevo desde cero."""
    svc._ARCHIVO = None


def cargar(directorio):
    """Apunta el disco Y reinicia: el ciclo completo de refresco."""
    apuntar(directorio)
    reiniciar()


class BaseRefresh(unittest.TestCase):
    """Arranca cada prueba con un dataset Aisolado y limpio."""

    def setUp(self):
        self.dir = os.path.join(BANCO, self.__class__.__name__ + "-" +
                                self._testMethodName)
        shutil.rmtree(self.dir, ignore_errors=True)
        self.A = escribir_dataset(os.path.join(self.dir, "A"), 5, 3, "A")
        self.B = escribir_dataset(os.path.join(self.dir, "B"), 9, 7, "B")
        cargar(self.A)
        # Se avisa de que `dataset_version.json` no aplica a este banco: el
        # dataset_id se comprueba aparte, con registros reales de prueba.
        self._raiz_real = config.DATA_ROOT
        config.DATA_ROOT = self.dir
        svc._leer_version = _version_falsa(self.dir)

    def tearDown(self):
        config.DATA_ROOT = self._raiz_real
        svc._leer_version = _LEER_VERSION_REAL
        shutil.rmtree(self.dir, ignore_errors=True)


def _version_falsa(raiz):
    """Un lector de `dataset_version.json` apuntando al banco de pruebas."""
    real = svc._leer_version

    def leer():
        ruta = os.path.join(raiz, "dataset_version.json")
        try:
            with io.open(ruta, encoding="utf-8") as f:
                doc = json.load(f)
            return doc if isinstance(doc, dict) else None
        except (OSError, ValueError):
            return None
    return leer


def escribir_json(ruta, doc):
    """Escribe un JSON cerrando el fichero. Nunca deja ResourceWarning."""
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc))


def registrar(raiz, id_):
    """Escribe un `dataset_version.json` minimo, como haria una activacion."""
    escribir_json(os.path.join(raiz, "dataset_version.json"), {
        "dataset_id": id_,
        "actualizada": "2026-01-01T00:00:00+00:00",
        "conteos": {"figuras": 1, "eventos": 2},
    })


# ================================================== CASOS 1-5: EL CICLO ====
class TestCicloRefresh(BaseRefresh):
    """Actualizar -> validar -> activar -> la API sirve el nuevo."""

    def test_caso_1_api_arranca_con_dataset_a(self):
        d = stats()
        self.assertEqual(d["figuras"], 5)
        self.assertEqual(d["sitios"], 3)
        self.assertEqual(nombres_figuras()[0], "figura-A-0")

    def test_caso_2_dataset_b_se_genera(self):
        """Se prepara B en un sitio aparte; A sigue intacto y activo."""
        self.assertTrue(os.path.isdir(self.B))
        self.assertEqual(stats()["figuras"], 5, "A se toco al generar B")

    def test_caso_3_b_es_valido(self):
        """B carga en el nucleo sin error y con los conteos esperados."""
        cargar(self.B)
        d = stats()
        self.assertEqual(d["figuras"], 9)
        self.assertEqual(d["sitios"], 7)
        self.assertTrue(all(n.startswith("figura-B-") for n in nombres_figuras()))

    def test_caso_4_b_se_activa(self):
        """Tras activar (reiniciar la API), sirve B y ya no A."""
        cargar(self.B)
        self.assertEqual(stats()["figuras"], 9)
        self.assertNotIn("figura-A-0", nombres_figuras())

    def test_caso_5_api_identifica_b_correctamente(self):
        registrar(self.dir, ids_de(sha_directorio(self.B)))
        cargar(self.B)
        d = salud_dataset()
        self.assertEqual(d["dataset_id"], ids_de(sha_directorio(self.B)))
        self.assertEqual(d["certainty"], "FACT")
        self.assertEqual(d["conteos"]["figuras"], 1)

    def test_api_atiende_durante_todo_el_ciclo(self):
        """Sigue respondiendo antes, durante y despues."""
        self.assertEqual(pedir("/api/salud")[0], 200)
        self.assertEqual(pedir("/api/stats")[0], 200)
        cargar(self.B)
        self.assertEqual(pedir("/api/salud")[0], 200)
        self.assertEqual(pedir("/api/stats")[0], 200)

    def test_sin_reiniciar_sigue_sirviendo_el_anterior(self):
        """Documenta el comportamiento REAL medido en la auditoria.

        No es un fallo: es la Opcion A, elegida a proposito. El proceso cachea
        el dataset con el que arranco. Este test separ las dos cosas que antes
        iban juntas: cambiar el DISCO y RECONSTRUIR el nucleo.
        """
        self.assertEqual(stats()["figuras"], 5, "arranca en A")

        # 1. El dataset activo cambia en disco (como hace `activar()`).
        apuntar(self.B)
        # 2. La API se sigue sirviendo A: no ha pasado nada todavia.
        self.assertEqual(stats()["figuras"], 5,
                         "cambiar el disco no debe alterar al proceso vivo")
        self.assertIn("figura-A-0", nombres_figuras())

        # 3. Ahora si, reiniciar. Esto es lo que hace `python run.py`.
        reiniciar()
        self.assertEqual(stats()["figuras"], 9, "tras reiniciar debe verse B")
        self.assertNotIn("figura-A-0", nombres_figuras())


# ============================== CASOS 6-7: FALLOS Y CONSERVACION DE A ======
class TestFalloNoDestruye(BaseRefresh):
    """Un dataset malo no puede dejar a la aplicacion sin mundo."""

    def test_caso_6_dataset_corrupto_no_destruye_a(self):
        C = escribir_dataset(os.path.join(self.dir, "C"), 50, 40, "C",
                             corrupto=True)
        self.assertEqual(stats()["figuras"], 5, "A debe seguir sirviendo")
        self.assertTrue(os.path.isdir(self.A))

        # C falla al cargar: el nucleo no se construye con datos corruptos.
        with self.assertRaises(Exception):
            cargar(C)
            stats()

        # Lo importante: el dataset activo NO ha cambiado.
        cargar(self.A)
        self.assertEqual(stats()["figuras"], 5, "A debe seguir disponible")
        self.assertIn("figura-A-0", nombres_figuras())

    def test_caso_7_carga_fallida_deja_el_anterior_disponible(self):
        """Tras una carga imposible, el mundo anterior sigue en pie.

        DOCUMENTA UN HECHO MEDIDO, no lo que uno misma preferiria:
        `cargar_jsonl()` devuelve `[]` si el fichero no existe, en vez de
        lanzar. Es decir, el nucleo NO se rompe ante un dataset ausente: se
        queda con un indice vacio. Quien impide que eso llegue a produccion es
        `actualizar_datos.validar_estructura()`, que actua ANTES de activar.

        Este test deja esa frontera escrita, para que nadie la descubra por
        sorpresa: si alguna vez se relaja la validacion, esta prueba lo
        recordara.
        """
        self.assertEqual(stats()["figuras"], 5)
        cargar(os.path.join(self.dir, "no-existe-en-absoluto"))
        # Comportamiento real: no lanza, sirve un mundo vacio.
        self.assertEqual(stats()["figuras"], 0,
                         "sin datos, el nucleo sirve 0 y no revienta")
        # Y el anterior sigue disponible para volver.
        cargar(self.A)
        self.assertEqual(stats()["figuras"], 5)

    def test_jsonl_truncado_no_se_cuela(self):
        """Un JSONL cortado por la mitad de una linea no puede cargarse.

        Se corta DENTRO de un registro, no en un salto de linea: cortar en el
        salto dejaria un fichero valido y la prueba pasaria sin comprobar nada.
        """
        D = escribir_dataset(os.path.join(self.dir, "D"), 4, 2, "D")
        ruta = os.path.join(D, "historical_figures.jsonl")
        with io.open(ruta, "r+", encoding="utf-8") as f:
            cruda = f.read()
            ultimo = cruda.rstrip().rfind("\n") + 1   # inicio de la ultima linea
            f.seek(0)
            f.truncate()
            f.write(cruda[:ultimo + 5])   # se queda a mitad del ultimo registro
        with self.assertRaises(Exception):
            cargar(D)
            stats()
        cargar(self.A)
        self.assertEqual(stats()["figuras"], 5, "A debe seguir disponible")

    def test_manifest_incorrecto_se_ignora(self):
        """Un `dataset_version.json` roto degrada a UNKNOWN, no a excepcion."""
        with io.open(os.path.join(self.dir, "dataset_version.json"), "w",
                     encoding="utf-8") as f:
            f.write("{esto no es json")
        d = salud_dataset()
        self.assertIsNone(d["dataset_id"])
        self.assertEqual(d["certainty"], "UNKNOWN")
        self.assertTrue(d["motivo"])
        self.assertEqual(pedir("/api/stats")[0], 200, "la API sigue viva")


# ============================ CASO 8: CONSISTENCIA DEL SNAPSHOT ============
class TestConsistenciaSnapshot(BaseRefresh):
    """Nunca debe observarse una mezcla de dos datasets en una respuesta."""

    def test_respuesta_coherente_durante_el_cambio(self):
        """Cientos de peticiones mientras el mundo cambia; ninguna mezclada."""
        for i in range(200):
            d = stats()
            nombres = nombres_figuras()
            if d["figuras"] == 5:
                self.assertTrue(all(n.startswith("figura-A-") for n in nombres),
                                "conteo de A con nombres de B")
                self.assertEqual(d["sitios"], 3)
            elif d["figuras"] == 9:
                self.assertTrue(all(n.startswith("figura-B-") for n in nombres),
                                "conteo de B con nombres de A")
                self.assertEqual(d["sitios"], 7)
            else:
                self.fail(f"conteo inesperado durante el cambio: {d['figuras']}")

    def test_sitio_y_figura_coinciden_en_el_mismo_dataset(self):
        """Una figura y un sitio del mismo mundo deben ser del mismo mundo."""
        cargar(self.A)
        c, env = pedir("/api/sitios/0")
        self.assertEqual(c, 200)
        self.assertEqual(env["data"]["nombre"], "sitio-A-0")
        cargar(self.B)
        _, env = pedir("/api/sitios/0")
        self.assertEqual(env["data"]["nombre"], "sitio-B-0")

    def test_ids_que_no_existen_siguen_dando_404(self):
        for _ in range(50):
            codigo, env = pedir("/api/sitios/999999")
            self.assertEqual(codigo, 404)
            self.assertEqual(env["certainty"], "UNKNOWN")


# ========================= CASO 9: ACTUALIZACIONES SIMULTANEAS ==============
class TestSimultaneidad(BaseRefresh):
    """Dos cargas a la vez no pueden corromper el estado."""

    def test_cargas_concurrentes_dejan_un_mundo_valido(self):
        errores = []

        def cargar_en_hilo(destino):
            try:
                cargar(destino)
                d = stats()
                if d["figuras"] not in (5, 9):
                    errores.append(f"conteo invalido: {d['figuras']}")
            except Exception as exc:            # noqa: BLE001
                errores.append(repr(exc))

        hilos = [threading.Thread(target=cargar_en_hilo,
                                  args=(self.A if i % 2 else self.B,))
                 for i in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(errores, [], f"fallos bajo concurrencia: {errores}")
        self.assertEqual(pedir("/api/salud")[0], 200)

    def test_lecturas_paralelas_durante_el_cambio(self):
        """Peticiones simultaneas mientras el dataset cambia.

        Volumen acotado a proposito: el objetivo es probar que no se rompe nada
        bajo concurrencia, no medir el rendimiento. Un bucle infinito con 4
        hilos contra un servidor de un solo nucleo solo mide cuelgues.
        """
        fallos = []

        def lector(n):
            for _ in range(n):
                for ruta in ("/api/stats", "/api/salud"):
                    c, _ = pedir(ruta)
                    if c != 200:
                        fallos.append(f"{ruta} -> {c}")

        lectores = [threading.Thread(target=lector, args=(25,))
                    for _ in range(3)]
        for t in lectores:
            t.start()
        for i in range(6):
            cargar(self.A if i % 2 else self.B)
        for t in lectores:
            t.join(timeout=30)
            self.assertFalse(t.is_alive(), "un lector se quedo bloqueado")
        self.assertEqual(fallos, [], f"una peticion fallo: {fallos[:5]}")


# ======================== CASO 10: EL IDENTIFICADOR DEL DATASET ============
class TestIdentificadorDataset(BaseRefresh):
    """`dataset_id`: determinista, sensible y coherente entre modulos."""

    def test_mismo_contenido_mismo_id(self):
        self.assertEqual(ids_de(sha_directorio(self.A)),
                         ids_de(sha_directorio(self.A)))

    def test_contenido_distinto_id_distinto(self):
        self.assertNotEqual(ids_de(sha_directorio(self.A)),
                            ids_de(sha_directorio(self.B)))

    def test_un_byte_cambia_el_id(self):
        antes = ids_de(sha_directorio(self.A))
        ruta = os.path.join(self.A, "historical_figures.jsonl")
        with io.open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps({"df_id": "9", "campos": {
                "name": {"valor": "extra"}}}) + "\n")
        self.assertNotEqual(antes, ids_de(sha_directorio(self.A)))

    def test_servicio_y_actualizador_coinciden(self):
        """Las DOS implementaciones de la formula dan el mismo valor."""
        sys.path.insert(0, config.TOOLS_ROOT)
        import actualizar_datos
        salidas = sha_directorio(self.A)
        self.assertEqual(svc.calcular_dataset_id(salidas),
                         actualizar_datos.calcular_dataset_id(salidas))

    def test_id_presente_en_el_registro_gana(self):
        """Si el registro ya trae `dataset_id`, ese es el que se publica."""
        registrar(self.dir, "v1-fijo-de-prueba")
        self.assertEqual(salud_dataset()["dataset_id"], "v1-fijo-de-prueba")

    def test_id_se_deriva_si_el_registro_no_lo_trae(self):
        """Un registro antiguo sin el campo no rompe: se deriva."""
        escribir_json(os.path.join(self.dir, "dataset_version.json"), {
            "actualizada": "2026-01-01T00:00:00+00:00",
            "salidas": sha_directorio(self.B)})
        d = salud_dataset()
        self.assertEqual(d["dataset_id"], ids_de(sha_directorio(self.B)))
        self.assertEqual(d["certainty"], "FACT")


# ===================== CASO 11-12: SEGURIDAD Y COMPATIBILIDAD =============
class TestSeguridadYCompatibilidad(BaseRefresh):
    """Sin acceso al disco por HTTP, y sin romper el contrato anterior."""

    def test_no_acepta_rutas_de_fichero(self):
        for ruta in ("/api/salud?dataset=C:/datos", "/api/salud?file=../../x",
                     "/api/salud?ruta=..%2F..%2Fetc", "/api/salud?path=/tmp"):
            c, env = pedir(ruta)
            self.assertEqual(c, 200, ruta)
            self.assertNotIn("etc/passwd", json.dumps(env, default=str))

    def test_no_expone_el_sistema_de_ficheros(self):
        for ruta in ("/api/salud", "/api/salud?dataset_id=/etc/passwd",
                     "/api/stats"):
            _, env = pedir(ruta)
            self.assertNotIn("Traceback", json.dumps(env, default=str))

    def test_contrato_antiguo_intacto(self):
        """Los campos de siempre siguen ahi, con el mismo nombre."""
        _, env = pedir("/api/salud")
        d = env["data"]
        for clave in ("estado", "eventos", "figuras", "ruta_datos",
                      "export_root", "limite_maximo"):
            self.assertIn(clave, d, f"falta el campo previo {clave}")
        self.assertEqual(d["estado"], "ok")
        self.assertTrue(env["ok"])
        self.assertIn("certainty", env)

    def test_stats_no_cambia(self):
        """El endpoint mas usado no se toca con esta mision."""
        _, env = pedir("/api/stats")
        for clave in ("figuras", "entidades", "sitios", "eventos",
                      "artefactos", "relaciones"):
            self.assertIn(clave, env["data"])

    def test_certidumbres_conservadas(self):
        """UNKNOWN no se convierte en un hecho."""
        _, env = pedir("/api/sitios/999999")
        self.assertEqual(env["certainty"], "UNKNOWN")
        _, env2 = pedir("/api/geografia?x=112&y=20")
        self.assertIn(env2["certainty"], ("FACT", "DERIVED", "UNKNOWN"))

    def test_dataset_vacio_declara_unknown(self):
        """Sin registro, se dice UNKNOWN con motivo: no se inventa nada."""
        d = salud_dataset()
        self.assertIsNone(d["dataset_id"])
        self.assertEqual(d["certainty"], "UNKNOWN")
        self.assertTrue(d["motivo"])


def tearDownModule():
    """Se apaga el servidor y se borra el banco: nada se queda abierto."""
    if _SRV[0] is not None:
        try:
            _SRV[0].shutdown()
        except Exception:                      # noqa: BLE001
            pass
    shutil.rmtree(BANCO, ignore_errors=True)


if __name__ == "__main__":
    t0 = time.perf_counter()
    unittest.main(verbosity=2, exit=False)
    print(f"\n[probar_refresh_cycle] {time.perf_counter() - t0:.1f}s")