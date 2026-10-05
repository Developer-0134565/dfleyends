#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Pruebas del ESTADO DE CONOCIMIENTO DEL JUGADOR
===============================================================

Comprueba, ejecutando de verdad, las tres reglas que este modulo promete:

    conocido  !=  verdad
    conocido  !=  revelable
    WORLD_KNOWLEDGE != PLAYER_KNOWLEDGE (nunca automatico)

Y que ninguna de las dos dimensiones se puede tocar por mutacion, ni
directamente ni a traves de un dict, una lista o un objeto anidado.

Todos los estados de prueba se escriben en una carpeta TEMPORAL. El estado real
del jugador no se toca nunca desde una prueba.

Ejecutar:  python dfchron/pruebas/probar_estado_conocimiento.py
"""
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dfchron import contrato_ia as c              # noqa: E402
from dfchron import estado_conocimiento as ec     # noqa: E402
from dfchron import ia_conocimiento as ia         # noqa: E402

PUENTE = ia.Puente()

FIGURA = "712"        # galka shafttop the blades of knighting
SITIO = "87"          # halesteel, fortaleza, con coordenadas reales

_COUNTER = [0]


def estado_temporal(dataset_id=None):
    """Un estado aislado, en una carpeta temporal que se puede tirar."""
    _COUNTER[0] += 1
    d = tempfile.mkdtemp(prefix="dfchron_estado_")
    e = ec.EstadoConocimiento(
        ruta=os.path.join(d, "estado_conocimiento.json"),
        dataset_id=dataset_id or ec.dataset_actual())
    return e, d


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


class BaseTemporal(unittest.TestCase):
    """Base que garantiza que el estado real no se toca durante las pruebas."""

    def setUp(self):
        self.estado, self.dir = estado_temporal()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def afirmar(self, **kw):
        base = dict(claim="dato de prueba", truth_status=c.FACT,
                    knowledge_source=c.WORLD_KNOWLEDGE,
                    visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN,
                    evidences=[c.evidencia("sitio", SITIO, ["coordenadas"],
                                           "nucleo.Archivo.ficha_sitio",
                                           "legends.xml")])
        base.update(kw)
        return c.afirmacion(**base)


# ============================================================ ESQUEMA =========
class TestEsquemaYVersionado(BaseTemporal):
    """4 y 5. El fichero tiene esquema explicito y `dataset_id` real."""

    def test_el_fichero_tiene_las_tres_claves(self):
        self.estado.marcar_conocido("sitio", SITIO)
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["schema_version"], ec.SCHEMA_VERSION)
        self.assertEqual(d["dataset_id"], ec.dataset_actual())
        self.assertIsInstance(d["knowledge"], dict)

    def test_el_dataset_id_no_esta_hardcodeado(self):
        """Viene del mecanismo real: se lee de `dataset_version.json`."""
        with open(os.path.join(RAIZ, "00_SOURCE", "dataset_version.json"),
                  encoding="utf-8") as f:
            self.assertEqual(ec.dataset_actual(), json.load(f)["dataset_id"])

    def test_el_estado_vive_fuera_del_dataset(self):
        import rutas
        self.assertFalse(rutas.es_ruta_protegida(self.estado.ruta))
        real = os.path.abspath(ec.ARCHIVO_ESTADO)
        self.assertFalse(rutas.es_ruta_protegida(real),
                         "la ruta por defecto esta dentro del dataset")

    def test_no_se_puede_apuntar_el_estado_al_dataset(self):
        import rutas
        for destino in (os.path.join(rutas.PROCESSED_ROOT, "e.json"),
                        os.path.join(rutas.ORIGINAL_DATA_ROOT, "e.json"),
                        os.path.join(rutas.VALIDATION_ROOT, "e.json")):
            with self.subTest(d=destino):
                with self.assertRaises(RuntimeError):
                    ec.EstadoConocimiento(ruta=destino)

    def test_un_estato_ilegible_se_declara_no_se_adivina(self):
        with open(self.estado.ruta, "w", encoding="utf-8") as f:
            f.write("{esto no es json")
        with self.assertRaises(ec.EstadoInvalido):
            self.estado.obtener_conocimiento()

    def test_schema_version_desconocida_no_se_migra_sola(self):
        self.estado.marcar_conocido("sitio", SITIO)
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        d["schema_version"] = 99
        with open(self.estado.ruta, "w", encoding="utf-8") as f:
            json.dump(d, f)
        with self.assertRaises(ec.EstadoInvalido):
            ec.EstadoConocimiento(ruta=self.estado.ruta).obtener_conocimiento()

    def test_claves_que_faltan_se_declaran(self):
        with open(self.estado.ruta, "w", encoding="utf-8") as f:
            json.dump({"knowledge": {}}, f)
        with self.assertRaises(ec.EstadoInvalido):
            self.estado.obtener_conocimiento()


# ========================================================== GRANULARIDAD ======
class TestGranularidad(BaseTemporal):
    """2. Solo la identidad que el nucleo sostiene de verdad."""

    def test_los_cinco_tipos_soportados(self):
        for tipo, id_ in (("figura", "712"), ("sitio", "87"),
                          ("entidad", 294), ("artefacto", 1), ("evento", 1)):
            with self.subTest(tipo=tipo):
                self.estado.marcar_conocido(tipo, id_)
                self.assertTrue(self.estado.esta_conocido(tipo, id_))

    def test_relaciones_no_se_soportan_y_se_dice_por_que(self):
        """No hay `relation_id` en el dataset, y no se inventa uno."""
        self.assertNotIn("relacion", ec.TIPOS_SOPORTADOS)
        self.assertIn("relacion", ec.TIPOS_NO_SOPORTADOS)
        self.assertIn("identificador estable", ec.TIPOS_NO_SOPORTADOS["relacion"])
        with self.assertRaises(ec.EstadoInvalido):
            self.estado.marcar_conocido("relacion", "1")
        with self.assertRaises(ec.EstadoInvalido):
            self.estado.marcar_conocido("inventado", "1")

    def test_dos_niveles_entidad_y_campo(self):
        self.estado.marcar_conocido("sitio", SITIO)
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO))
        self.assertFalse(self.estado.esta_conocido("sitio", SITIO, "coordenadas"),
                         "conocer la entidad no conoce sus campos")
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO, "coordenadas"))
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO))

    def test_revocar_el_campo_no_toca_la_entidad(self):
        self.estado.marcar_conocido("sitio", SITIO)
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.estado.marcar_desconocido("sitio", SITIO, "coordenadas")
        self.assertFalse(self.estado.esta_conocido("sitio", SITIO, "coordenadas"))
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO))

    def test_identificadores_hostiles_se_rechazan(self):
        for malo in (None, "", "   ", [], {}, 3.5, True, b"87"):
            with self.subTest(v=type(malo).__name__):
                with self.assertRaises(ec.EstadoInvalido):
                    self.estado.marcar_conocido("sitio", malo)

    def test_el_estado_persiste_entre_instancias(self):
        self.estado.marcar_conocido("figura", FIGURA, "nombre", "lo vio")
        otro = ec.EstadoConocimiento(ruta=self.estado.ruta)
        self.assertTrue(otro.esta_conocido("figura", FIGURA, "nombre"))
        self.assertEqual(otro.obtener_conocimiento()["knowledge"]
                         [ec.clave_campo("figura", FIGURA, "nombre")]["motivo"],
                         "lo vio")


# ================================================= CONOCIDO != REVELABLE =====
class TestConocidoNoEsRevelable(BaseTemporal):
    """6, y los casos 1-3 y el ataque A."""

    def test_caso_1_world_fact_hidden_forbidden(self):
        """WORLD / FACT / PLAYER_HIDDEN / FORBIDDEN."""
        a = self.afirmar()
        self.assertTrue(c.puede_usarse_para_razonar(a))
        self.assertFalse(c.puede_revelarse(a))
        self.assertFalse(c.puede_afirmarse_como_hecho(a))

    def test_ataque_A_conocer_un_forbidden_no_lo_revela(self):
        """Marcar como conocido y comprobar que sigue sin poder revelarse."""
        a = self.afirmar()
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO, "coordenadas"))
        self.assertFalse(c.puede_revelarse(a),
                         "ser conocido NO convierte FORBIDDEN en ALLOWED")

    def test_ataque_B_conocer_un_hidden_no_lo_revela(self):
        """PLAYER_HIDDEN + FORBIDDEN sigue prohibido aunque el jugador lo sepa."""
        a = self.afirmar(visibility=c.PLAYER_HIDDEN, disclosure=c.FORBIDDEN)
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertFalse(c.puede_revelarse(a))

    def test_caso_2_conocido_y_forbidden_no_se_revela(self):
        a = self.afirmar()
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertFalse(c.puede_revelarse(a))

    def test_caso_3_descubrir_y_convertir_si_revela(self):
        """El camino completo: descubrir -> `convertir` -> sí se puede decir.

        Se comprueba que la afirmacion sigue siendo de `WORLD_KNOWLEDGE`: el
        estado del jugador no reescribe de donde viene la verdad (§12).
        """
        a = self.afirmar()
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        revelada = c.convertir(a, "revelar", "el jugador lo ha descubierto")
        self.assertEqual(revelada["knowledge_source"], c.WORLD_KNOWLEDGE,
                         "descubrirlo no cambia de donde viene el dato")
        self.assertEqual(revelada["visibility"], c.PLAYER_VISIBLE)
        self.assertEqual(revelada["disclosure"], c.ALLOWED)
        self.assertTrue(c.puede_revelarse(revelada))
        self.assertTrue(c.puede_afirmarse_como_hecho(revelada))

    def test_el_estado_no_puede_tocar_la_disclosure(self):
        """Prueba ESTRUCTURAL: no existe ningún atajo conocer -> revelar.

        Se analiza el árbol sintáctico, no el texto: el nombre aparece en la
        prosa del módulo, pero lo que importa es si se *llama*.
        """
        import ast
        ruta = os.path.join(RAIZ, "dfchron", "estado_conocimiento.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())

        llamadas, atributos, importados = set(), set(), set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                f_ = nodo.func
                if isinstance(f_, ast.Name):
                    llamadas.add(f_.id)
                elif isinstance(f_, ast.Attribute):
                    atributos.add(f_.attr)
            elif isinstance(nodo, (ast.ImportFrom, ast.Import)):
                importados.update(a.name for a in nodo.names)

        # No llama a la puerta de divulgación ni a la conversión.
        self.assertNotIn("convertir", llamadas,
                         "el estado no convierte: la puerta es convertir()")
        self.assertNotIn("puede_revelarse", llamadas)
        self.assertNotIn("puede_afirmarse_como_hecho", llamadas)
        self.assertNotIn("afirmacion", llamadas,
                         "el estado no crea afirmaciones: solo las consulta")
        # Y ni siquiera depende del contrato: se acopla solo por `estado`.
        self.assertNotIn("contrato_ia", importados)


# ==================================================== CONOCIDO != VERDAD =====
class TestConocidoNoEsVerdad(BaseTemporal):
    """7, y los casos 4, 5 y 6: conocer no cambia la verdad."""

    def test_caso_4_unknown_conocido_nunca_es_hecho(self):
        a = self.afirmar(truth_status=c.UNKNOWN, visibility=c.PLAYER_VISIBLE,
                         disclosure=c.ALLOWED, evidences=[],
                         motivo="el nucleo no registro esta fecha")
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertEqual(a["truth_status"], c.UNKNOWN)
        self.assertFalse(c.puede_afirmarse_como_hecho(a),
                         "saber que no consta no lo convierte en verdad")

    def test_caso_5_derivado_nunca_sube_a_fact(self):
        a = self.afirmar(truth_status=c.DERIVED, visibility=c.PLAYER_HIDDEN,
                         disclosure=c.FORBIDDEN)
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas")
        self.assertEqual(a["truth_status"], c.DERIVED)
        revelada = c.convertir(a, "revelar", "el jugador lo ha descubierto")
        self.assertEqual(revelada["truth_status"], c.DERIVED,
                         "descubrirlo no lo convierte en FACT")
        self.assertFalse(c.puede_afirmarse_como_hecho(revelada),
                         "un DERIVED no se enuncia como hecho")

    def test_caso_6_inference_conserva_su_semantica(self):
        inf = ia.registrar_inferencia(
            "la fortaleza podria ser peligrosa",
            [c.evidencia("razonamiento", "sitio-87", ["tipo"],
                         "nucleo.Archivo.ficha_sitio")])
        self.estado.marcar_conocido("sitio", SITIO)
        self.assertEqual(inf["truth_status"], c.INFERENCE)
        self.assertTrue(c.puede_revelarse(inf), "se puede mencionar")
        self.assertFalse(c.puede_afirmarse_como_hecho(inf))
        with self.assertRaises(c.ContratoInvalido):
            c.afirmacion("conclusion", c.FACT, c.INFERENCE, c.PLAYER_VISIBLE,
                         evidences=[c.evidencia("r", "x", ["t"], "f")])

    def test_marcar_conocido_no_toca_la_afirmacion(self):
        a = self.afirmar()
        ec.marcar_conocida(a, estado=self.estado, motivo="lo vio")
        self.assertEqual(a["truth_status"], c.FACT)
        self.assertEqual(a["visibility"], c.PLAYER_HIDDEN)
        self.assertEqual(a["disclosure"], c.FORBIDDEN)
        self.assertFalse(c.puede_revelarse(a))
        self.assertTrue(ec.es_conocida(a, estado=self.estado),
                        "lo puede conocer aunque no se lo podamos decir")


# ============================================================ ATAQUE G ========
class TestSinAutodescubrimiento(BaseTemporal):
    """8 y el ataque G: nada se marca solo."""

    def test_ataque_G_no_existe_marcar_todo(self):
        """No hay ninguna API para marcar todo el mundo como conocido."""
        import ast
        with open(os.path.join(RAIZ, "dfchron", "estado_conocimiento.py"),
                  encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        publicas = [n.name for n in arbol.body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                    and not n.name.startswith("_")]
        for prohibido in ("marcar_todo", "marcar_todo_conocido",
                          "descubrir_todo", "marcar_world_knowledge",
                          "autodescubrir", "marcar_todo_el_mundo"):
            self.assertNotIn(prohibido, publicas)

    def test_consultar_el_nucleo_no_marca_nada(self):
        """Que el dato exista en WORLD_KNOWLEDGE no lo hace conocido."""
        k = PUENTE.obtener_conocimiento_sitio(SITIO)
        self.assertTrue(k["claims"], "el nucleo tiene datos de sobra")
        self.assertEqual(len(self.estado.obtener_conocimiento()["knowledge"]), 0,
                         "y el estado del jugador sigue vacio")
        for a in k["claims"]:
            self.assertFalse(ec.es_conocida(a, estado=self.estado))

    def test_esta_conocido_no_es_una_consulta_al_nucleo(self):
        self.assertFalse(self.estado.esta_conocido("sitio", SITIO))
        self.assertFalse(self.estado.esta_conocido("figura", FIGURA))


# ==================================================== CAMBIO DE DATASET ======
class TestDatasetDistinto(BaseTemporal):
    """5, 13 y el caso 7 y el ataque F: nunca se continua en silencio."""

    def test_caso_7_estado_de_otro_dataset_se_declara(self):
        self.estado.marcar_conocido("sitio", SITIO)
        otro = ec.EstadoConocimiento(ruta=self.estado.ruta,
                                     dataset_id="v1-0000000000000000")
        self.assertEqual(otro.compatibilidad(), "DISTINTO")
        self.assertFalse(otro.esta_conocido("sitio", SITIO),
                         "falla cerrado: no se afirma que conozca nada")
        with self.assertRaises(ec.DatasetDistinto):
            otro.marcar_conocido("sitio", SITIO)
        with self.assertRaises(ec.DatasetDistinto):
            otro.obtener_conocimiento()

    def test_el_estado_no_se_borra_al_detectar_el_cambio(self):
        self.estado.marcar_conocido("sitio", SITIO, motivo="importante")
        otro = ec.EstadoConocimiento(ruta=self.estado.ruta,
                                     dataset_id="v1-0000000000000000")
        with self.assertRaises(ec.DatasetDistinto):
            otro.exigir_compatible()
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        self.assertIn(ec.clave_entidad("sitio", SITIO), d["knowledge"],
                      "el estado sigue ahi, intacto")

    def test_ataque_F_editar_el_dataset_id_a_mano_se_detecta(self):
        self.estado.marcar_conocido("sitio", SITIO)
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        d["dataset_id"] = "v1-falsificado"
        with open(self.estado.ruta, "w", encoding="utf-8") as f:
            json.dump(d, f)
        recargado = ec.EstadoConocimiento(ruta=self.estado.ruta)
        self.assertEqual(recargado.compatibilidad(), "DISTINTO")
        self.assertFalse(recargado.esta_conocido("sitio", SITIO))
        with self.assertRaises(ec.DatasetDistinto):
            recargado.marcar_conocido("sitio", SITIO)

    def test_hay_que_resetear_explicitamente(self):
        """Con el dataset cambiado solo se sale con un reset explicito.

        Y el reset vuelve a ligar el estado al dataset actual: sin eso, un cambio
        de dataset dejaria el estado inservible para siempre.
        """
        self.estado.marcar_conocido("sitio", SITIO)
        otro = ec.EstadoConocimiento(ruta=self.estado.ruta,
                                     dataset_id="v1-0000000000000000")
        with self.assertRaises(ec.DatasetDistinto):
            otro.limpiar_conocimiento("sitio", SITIO)   # quirurgico: no
        self.assertEqual(otro.limpiar_conocimiento(), 1)  # reset: si
        self.assertEqual(otro.obtener_conocimiento()["knowledge"], {})
        self.assertEqual(otro.compatibilidad(), "COINCIDE")

    def test_el_reset_conserva_el_dataset_id_y_el_esquema(self):
        self.estado.marcar_conocido("sitio", SITIO)
        self.estado.limpiar_conocimiento()
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["dataset_id"], ec.dataset_actual())
        self.assertEqual(d["schema_version"], ec.SCHEMA_VERSION)


# =========================================================== MUTABILIDAD =====
class TestMutabilidad(BaseTemporal):
    """14, y los ataques C y D: ni directa, ni anidada, ni por alias."""

    def test_ataque_C_y_D_en_la_afirmacion(self):
        a = self.afirmar()
        for destino in (c.ALLOWED, c.FORBIDDEN, c.CONDITIONAL):
            with self.subTest(d="disclosure -> " + destino):
                with self.assertRaises(c.ContratoInvalido):
                    a["disclosure"] = destino
        for destino in (c.PLAYER_VISIBLE, c.PLAYER_HIDDEN):
            with self.subTest(v="visibility -> " + destino):
                with self.assertRaises(c.ContratoInvalido):
                    a["visibility"] = destino
        self.assertEqual(a["disclosure"], c.FORBIDDEN)
        self.assertEqual(a["visibility"], c.PLAYER_HIDDEN)

    def test_no_se_puede_tocar_truth_status(self):
        a = self.afirmar()
        for destino in (c.UNKNOWN, c.INFERENCE, c.DERIVED):
            with self.subTest(t=destino):
                with self.assertRaises(c.ContratoInvalido):
                    a["truth_status"] = destino

    def test_no_se_puede_tocar_la_provenance_por_mutacion_anidada(self):
        """El agujero que quedaba: dicts y listas dentro de `evidence`."""
        a = self.afirmar()
        ev = a["evidence"][0]
        intentos = (
            lambda: ev.__setitem__("df_id", "999"),
            lambda: ev.__setitem__("funcion", "falsa"),
            lambda: a["evidence"].__setitem__(0, {}),
            lambda: a["evidence"].append(c.evidencia("x", "1", ["y"], "z")),
            lambda: ev["datos_utilizados"].append("campo_inventado"),
            lambda: ev["datos_utilizados"].sort(),
        )
        for i, intento in enumerate(intentos, 1):
            with self.subTest(intento=i):
                with self.assertRaises(c.ContratoInvalido):
                    intento()
        self.assertEqual(a["evidence"][0]["df_id"], SITIO)
        self.assertEqual(a["evidence"][0]["funcion"],
                         "nucleo.Archivo.ficha_sitio")

    def test_el_snapshot_del_estado_es_de_solo_lectura(self):
        self.estado.marcar_conocido("sitio", SITIO, "nombre", "lo vio")
        snap = self.estado.obtener_conocimiento()
        intentos = (
            lambda: snap.__setitem__("dataset_id", "v1-falso"),
            lambda: snap["knowledge"].__setitem__("x", {}),
            lambda: snap["knowledge"].clear(),
            lambda: snap["knowledge"].pop(ec.clave_entidad("sitio", SITIO)),
        )
        for i, intento in enumerate(intentos, 1):
            with self.subTest(intento=i):
                with self.assertRaises(ec.EstadoInvalido):
                    intento()
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO, "nombre"),
                        "el estado real sigue intacto")

    def test_una_copia_superficial_no_toca_el_estado(self):
        """`copy.copy` da un snapshot independiente, y sigue sellado."""
        self.estado.marcar_conocido("sitio", SITIO)
        copia = copy.copy(self.estado.obtener_conocimiento())
        self.assertEqual(copia["knowledge"],
                         self.estado.obtener_conocimiento()["knowledge"])
        with self.assertRaises(ec.EstadoInvalido):
            copia["knowledge"] = {}
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO))

    def test_una_copia_profunda_no_toca_el_estado(self):
        """`copy.deepcopy` tampoco puede abrir un hueco en el estado real."""
        self.estado.marcar_conocido("sitio", SITIO, "nombre")
        copia = copy.deepcopy(self.estado.obtener_conocimiento())
        self.assertEqual(copia["knowledge"],
                         self.estado.obtener_conocimiento()["knowledge"])
        with self.assertRaises(ec.EstadoInvalido):
            copia["knowledge"].clear()
        self.assertTrue(self.estado.esta_conocido("sitio", SITIO, "nombre"),
                        "el estado real no se ha enterado de nada")

    def test_el_snapshot_no_es_el_estado_interno(self):
        """Alias: dos llamadas seguidas no comparten estructura."""
        a = self.estado.obtener_conocimiento()
        b = self.estado.obtener_conocimiento()
        self.assertIsNot(a["knowledge"], b["knowledge"])
        self.assertEqual(a["knowledge"], b["knowledge"])


# ========================================================== DETERMINISMO =====
class TestDeterminismo(BaseTemporal):
    """18. Mismas entradas, mismo fichero, byte a byte."""

    def _leer_texto(self):
        return _leer(self.estado.ruta)

    def test_el_orden_de_marcar_no_cambia_el_fichero(self):
        self.estado.marcar_conocido("sitio", SITIO, "nombre", "a")
        self.estado.marcar_conocido("figura", FIGURA, "raza", "b")
        self.estado.marcar_conocido("entidad", 294, None, "c")
        primero = self._leer_texto()
        otro = ec.EstadoConocimiento(ruta=self.estado.ruta)
        otro.limpiar_conocimiento()
        otro.marcar_conocido("entidad", 294, None, "c")
        otro.marcar_conocido("figura", FIGURA, "raza", "b")
        otro.marcar_conocido("sitio", SITIO, "nombre", "a")
        self.assertEqual(primero, _leer(otro.ruta),
                         "el orden de las marcas no debe notarse")

    def test_no_hay_relojes_ni_uuids(self):
        self.estado.marcar_conocido("sitio", SITIO)
        texto = self._leer_texto()
        self.assertNotRegex(texto, r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}",
                            "no debe haber marcas de tiempo")
        self.assertNotRegex(texto, r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-",
                            "no debe haber UUID")
        self.assertIsNone(re.search(r'"(creado|actualizado|fecha)"', texto))

    def test_el_json_es_canonico(self):
        self.estado.marcar_conocido("sitio", SITIO)
        self.estado.marcar_conocido("figura", FIGURA)
        texto = self._leer_texto()
        self.assertEqual(texto, json.dumps(json.loads(texto),
                                          ensure_ascii=False, indent=1,
                                          sort_keys=True) + "\n")

    def test_leer_no_escribe(self):
        self.estado.marcar_conocido("sitio", SITIO)
        antes = self._leer_texto()
        mtime = os.path.getmtime(self.estado.ruta)
        for _ in range(3):
            self.estado.obtener_conocimiento()
            self.estado.esta_conocido("sitio", SITIO)
        self.assertEqual(self._leer_texto(), antes)
        self.assertEqual(os.path.getmtime(self.estado.ruta), mtime,
                         "consultar no toca el fichero")


# =================================================== NO CONTAMINACION ========
class TestNoContaminaElDataset(BaseTemporal):
    """17 y el ataque E: tocar el estado no toca la historia."""

    PROTEGIDOS = ("00_SOURCE/original_data/legends.xml",
                  "00_SOURCE/original_data/legends_plus.xml")

    def test_ataque_E_marcar_desmarcar_y_resetear_no_toca_el_dataset(self):
        import hashlib

        def huella(ruta):
            with open(os.path.join(RAIZ, ruta.replace("/", os.sep)),
                      "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        antes = {r: huella(r) for r in self.PROTEGIDOS}
        self.estado.marcar_conocido("sitio", SITIO, "coordenadas", "lo vio")
        self.estado.marcar_desconocido("sitio", SITIO, "coordenadas")
        self.estado.marcar_conocido("figura", FIGURA)
        self.estado.limpiar_conocimiento()
        with open(self.estado.ruta, encoding="utf-8") as f:
            d = json.load(f)
        d["dataset_id"] = "v1-manipulado"
        with open(self.estado.ruta, "w", encoding="utf-8") as f:
            json.dump(d, f)
        # con el dataset manipulado, el estado se niega a ser entregado
        with self.assertRaises(ec.DatasetDistinto):
            ec.EstadoConocimiento(ruta=self.estado.ruta).obtener_conocimiento()
        despues = {r: huella(r) for r in self.PROTEGIDOS}
        self.assertEqual(antes, despues, "el dataset historico esta intacto")

    def test_el_estado_real_esta_fuera_del_dataset(self):
        import rutas
        self.assertFalse(rutas.es_ruta_protegida(ec.ARCHIVO_ESTADO))
        self.assertFalse(os.path.abspath(ec.ARCHIVO_ESTADO).startswith(
            os.path.abspath(os.path.join(rutas.PROCESSED_ROOT, "x"))))


# ============================================================ NO HAY IA ======
class TestNoHayIA(unittest.TestCase):
    """20. Se comprueba POR NEGACION que no se ha construido una IA."""

    RUTAS_PROHIBIDAS = ("/api/ai", "/api/chat", "/api/assistant",
                        "/api/ia", "/api/ask", "/api/preguntar")

    def test_la_api_no_tiene_rutas_de_ia(self):
        with open(os.path.join(RAIZ, "dfchron", "api.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for ruta in self.RUTAS_PROHIBIDAS:
            self.assertNotIn(f'"{ruta}"', fuente)

    def test_esta_mision_no_creo_rutas_de_ia(self):
        with open(os.path.join(RAIZ, "dfchron", "estado_conocimiento.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for ruta in self.RUTAS_PROHIBIDAS:
            self.assertNotIn(f'"{ruta}"', fuente)

    def test_no_hay_sdk_de_ia(self):
        with open(os.path.join(RAIZ, "dfchron", "estado_conocimiento.py"),
                  encoding="utf-8") as f:
            fuente = f.read()
        for sdk in ("openai", "anthropic", "ollama", "langchain",
                    "llama_index", "transformers", "torch", "requests",
                    "urllib", "httpx"):
            self.assertNotRegex(fuente, rf"^\s*(import|from)\s+{sdk}\b",
                                f"{sdk} no debe importarse")

    def test_no_hay_web_ni_endpoint_nuevo(self):
        """10: ni pantallas, ni botones, ni rutas de IA en la web."""
        web = os.path.join(RAIZ, "dfchron", "web")
        for nombre in os.listdir(web):
            with open(os.path.join(web, nombre), encoding="utf-8") as f:
                texto = f.read()
            for ruta in self.RUTAS_PROHIBIDAS:
                self.assertNotIn(ruta, texto,
                                 f"la web no debe hablar de {ruta}")


if __name__ == "__main__":
    unittest.main(verbosity=2)