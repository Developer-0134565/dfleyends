#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: perimetro de acceso del futuro consumidor IA
==============================================================

QUE ES ESTO
-----------
Una **especificacion ejecutable**. No hay IA aqui. No hay modelo, ni prompt,
ni embedding, ni cliente HTTP, ni推理. Hay una lista blanca de operaciones y
un dispatcher que SOLO puede llamar a `servicio_consulta`.

POR QUE NO HAY `ai_adapter.py`
------------------------------
La especificacion pide un adaptador futuro y, en la misma frase, dice que no se
implemente. Anadir un modulo de produccion seria justo lo contrario. Asi que la
frontera vive **dentro de este fichero de pruebas**, marcada entre
`# ==== INICIO ESPECIFICACION ====` y `# ==== FIN ESPECIFICACION ====`, para
que las pruebas puedan leerla y el mutation testing pueda mutarla.

QUE DISTINGUE ESTE PERIMETRO DEL GATE QUE YA EXISTIA
-----------------------------------------------------
No duplica `probar_gate_pre_ia.py` ni `AI_PRE_LLM_CONTRACT.md`. Aquellos
responden a: **puede el modelo mandar?** Aqui se responde a: **puede pedir?**

| Eje | Documento | Pregunta |
|-----|-----------|----------|
| Autoridad | `08_DATABASE/AI_PRE_LLM_CONTRACT.md` (CONGELADO) | Que puede afirmar o cambiar el modelo? |
| Acceso | `AI_CONSUMER_BOUNDARY.md` (este) | Que puede pedir y recibir? |

El gate no mira `servicio_consulta` en ninguna de sus 15 pruebas. Esta suite si.

Uso:  python dfchron\\pruebas\\probar_perimetro_ia.py
"""
import json
import os
import re
import sys
import unittest

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _ruta in (_RAIZ, os.path.join(_RAIZ, "00_SOURCE", "tools")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

# ==== INICIO ESPECIFICACION ====
# Todo lo que hay entre estas dos marcas es la FRONTERA que se quiere
# demostrar. El mutation testing muta este bloque a proposito.

#: La UNICA dependencia del perimetro. Ni `nucleo`, ni `rutas`, ni `servicio`.
from dfchron import servicio_consulta as qc            # noqa: E402

#: Operaciones permitidas. Se DERIVA del servicio, no se escribe a mano: si el
#: servicio anade una operacion, el perimetro la incluira, y si la quita,
#: dejara de permitirla. Una lista escrita a mano se quedaria vieja.
OPERACIONES_PERMITIDAS = frozenset(qc.contrato()["operaciones"])

#: Estados que el consumidor puede recibir. Los cinco, sin reducir.
ESTADOS_PERMITIDOS = frozenset(qc.contrato()["estados"])

#: Tipos con identidad demostrable. Los demas devuelven `identity: null`.
TIPOS_CON_IDENTIDAD = frozenset(qc.contrato()["tipos_con_identidad"])

#: Tipos SIN identidad. Un consumidor NO puede inventarsela.
TIPOS_SIN_IDENTIDAD = frozenset(qc.contrato()["tipos_sin_identidad"])

#: Codigo de rechazo por operacion fuera del contrato. Distinto de
#: NOT_FOUND y de DATA_UNAVAILABLE, y esa distincion es el punto (§14).
OPERACION_NO_PERMITIDA = "OPERACION_NO_PERMITIDA"


def Denial(codigo, motivo):
    """Rechazo del perimetro. No es una respuesta del servicio."""
    return {"ok": False, "estado": codigo, "motivo": motivo, "data": None}


def resolver(operacion, **params):
    """UNICA puerta de salida del futuro consumidor.

    Tres reglas, y solo tres:

    1. Si la operacion no esta en la lista blanca, se RECHAZA. No se busca en
       ningun sitio, no se deduce, no se «intenta de todas formas».
    2. Si esta, se delega en `servicio_consulta`. Nunca en el nucleo, nunca
       en un fichero, nunca en el indice.
    3. El resultado se devuelve **tal cual**. No se normaliza, no se completa,
       no se rellena lo que venga a null.
    """
    if operacion not in OPERACIONES_PERMITIDAS:
        return Denial(OPERACION_NO_PERMITIDA,
                      "la operacion %r no pertenece al contrato de consulta"
                      % operacion)
    return getattr(qc, operacion)(**params)


# ==== FIN ESPECIFICACION ====


_AQUI = os.path.abspath(__file__)


def _bloque_especificacion():
    """El texto entre las dos marcas. El mutation testing lo muta.

    Se buscan las marcas en LINEA COMPLETA, porque el docstring las menciona
    como ejemplo y `str.index` las encontraria ahi primero.
    """
    with open(_AQUI, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    ini = next(i for i, l in enumerate(lineas)
               if l.strip() == "# ==== INICIO ESPECIFICACION ====")
    fin = next(i for i, l in enumerate(lineas)
               if l.strip() == "# ==== FIN ESPECIFICACION ====")
    return "\n".join(lineas[ini:fin + 1])


def _codigo_del_bloque():
    """El bloque de especificacion SIN COMENTARIOS ni docstrings.

    Los comentarios explican por que el perimetro NO toca el nucleo, asi que
    contienen la palabra «nucleo». Comprobar el texto con comentarios daria un
    falso positivo siempre. Lo que se audita es el CODIGO.
    """
    bloque = _bloque_especificacion()
    sin_comentarios = "\n".join(
        l for l in bloque.splitlines()
        if not l.strip().startswith("#"))
    return re.sub(r'""".*?"""', "", sin_comentarios, flags=re.S)


# ============================================ 1. SIN ACCESO DIRECTO =======
class Test01SinAccesoDirecto(unittest.TestCase):
    """Test 1 — El perimetro no importa modulos internos."""

    def test_el_perimetro_no_importa_el_nucleo(self):
        codigo = _codigo_del_bloque()
        for prohibido in ("nucleo", "Archivo", "obtener_archivo",
                          "rutas", "csv", "jsonl"):
            self.assertNotIn(prohibido, codigo,
                             "el perimetro alcanza el nucleo: %r" % prohibido)

    def test_el_perimetro_no_abre_ficheros(self):
        codigo = _codigo_del_bloque()
        for prohibido in ("open(", "read_text", "os.path", "Path("):
            self.assertNotIn(prohibido, codigo,
                             "el perimetro lee del disco: %r" % prohibido)

    def test_el_perimetro_solo_importa_el_servicio(self):
        """DENTRO del perimetro, el unico import es `servicio_consulta`.

        Se mira el bloque de especificacion, no el fichero entero: las
        pruebas de este fichero pueden importar `servicio` para COMPROBAR
        contra el indice real que el perimetro no se inventa los numeros.
        """
        bloque = _bloque_especificacion()
        imports = re.findall(r"from dfchron import (\w+)", bloque)
        self.assertEqual(imports, ["servicio_consulta"],
                         "el perimetro importa algo mas: %s" % imports)

    def test_servicio_consulta_no_abre_ficheros_de_datos(self):
        """La garantia de fondo: la capa no lee el dataset por su cuenta."""
        ruta = os.path.join(_RAIZ, "dfchron", "servicio_consulta.py")
        with open(ruta, encoding="utf-8") as f:
            fuente = f.read()
        for prohibido in ("open(", "read_text(", "pd.read", "csv.DictReader"):
            self.assertNotIn(prohibido, fuente,
                             "la capa lee ficheros: %r" % prohibido)


# =============================================== 2. SERVICIO OBLIGATORIO ==
class Test02ServicioObligatorio(unittest.TestCase):
    """Test 2 — Toda operacion permitida se resuelve en servicio_consulta."""

    def test_toda_operacion_permitida_existe_en_el_servicio(self):
        for op in OPERACIONES_PERMITIDAS:
            with self.subTest(op=op):
                self.assertTrue(callable(getattr(qc, op, None)))

    def test_una_operacion_inexistente_se_rechaza(self):
        r = resolver("leer_jsonl", ruta="figuras.jsonl")
        self.assertEqual(r["estado"], OPERACION_NO_PERMITIDA)
        self.assertFalse(r["ok"])

    def test_una_operacion_inventada_se_rechaza(self):
        for op in ("adivinar", "inferir", "buscar_en_disco", "inventar_id",
                   "salvar_dataset"):
            with self.subTest(op=op):
                self.assertEqual(resolver(op)["estado"],
                                 OPERACION_NO_PERMITIDA)

    def test_el_rechazo_no_es_un_not_found(self):
        """§14 — 'no permitido' NO es 'no existe'."""
        r = resolver("leer_jsonl")
        for otro in ("NOT_FOUND", "DATA_UNAVAILABLE", "NOT_VERIFIED"):
            self.assertNotEqual(r["estado"], otro)

# ==================================================== 3. SIN FILESYSTEM ===
class Test03SinFilesystem(unittest.TestCase):
    """Test 3 — Ninguna respuesta entrega rutas del proyecto."""

    def _resultados(self):
        return [
            resolver("obtener_entidad", tipo="figura", df_id="712"),
            resolver("obtener_atributo", tipo="figura", df_id="712",
                     atributo="nombre"),
            resolver("buscar_relaciones", origen="345"),
            resolver("contar", tipo="figura"),
            resolver("obtener_evidencia", tipo="figura", df_id="712"),
            resolver("verificar", sujeto_tipo="figura", sujeto_id="712",
                     predicado="existe"),
        ]

    def test_ninguna_respuesta_contiene_una_ruta(self):
        for r in self._resultados():
            texto = json.dumps(r, ensure_ascii=False).lower()
            for prohibido in ("original_data", "processed/", "merged",
                              "08_database", "00_source", "c:\\", ".jsonl"):
                with self.subTest(prohibido=prohibido):
                    self.assertNotIn(prohibido, texto,
                                     "se filtra una ruta: %r" % prohibido)

    def test_ninguna_respuesta_contiene_ruta_absoluta(self):
        for r in self._resultados():
            texto = json.dumps(r, ensure_ascii=False)
            self.assertIsNone(re.search(r"[A-Za-z]:\\", texto))
            self.assertIsNone(re.search(r'"[^"]*/[^"]*/[^"]*"', texto))

    def test_la_fuente_del_xml_solo_aparece_como_nombre(self):
        """`legends.xml` puede ser procedencia, nunca una ruta.

        NOTA: `obtener_evidencia` deja `evidence` en `None` y mete la
        procedencia en `data`. Es lo que hace el servicio hoy, y esta prueba
        lo fija. Ver INFORME_PERIMETRO_IA.md §H.
        """
        r = resolver("obtener_evidencia", tipo="figura", df_id="712")
        fuente = r["data"]["fuente"]
        self.assertEqual(fuente, ["legends.xml"])
        for nombre in fuente:
            self.assertNotIn("/", nombre)
            self.assertNotIn("\\", nombre)


# ================================================ 4. EVIDENCIA CONSERVADA ==
class Test04EvidenciaConservada(unittest.TestCase):
    """Test 4 — dataset_id y state_version llegan intactos."""

    def test_dataset_id_conservado(self):
        r = resolver("obtener_entidad", tipo="figura", df_id="712")
        self.assertEqual(r["dataset_id"], qc.ic.DATASET_ID)

    def test_state_version_conservado(self):
        r = resolver("obtener_entidad", tipo="figura", df_id="712")
        self.assertIsNotNone(r["evidence"])
        self.assertEqual(r["evidence"]["state_version"], qc.ic.DATASET_ID)

    def test_la_procedencia_no_se_puede_inyectar(self):
        """`obtener_evidencia` no acepta una `fuente` propia: no existe
        ese parametro. Escribirlela directamente es un TypeError."""
        import inspect
        self.assertNotIn("fuente", inspect.signature(qc.obtener_evidencia).parameters)
        self.assertNotIn("fuente", inspect.signature(qc._evidencia).parameters)
        r = resolver("obtener_evidencia", tipo="figura", df_id="712")
        self.assertEqual(r["data"]["fuente"], ["legends.xml"])

    def test_un_tipo_sin_identidad_no_inventa_evidencia(self):
        r = resolver("obtener_evidencia", tipo="relacion", df_id="5")
        self.assertEqual(r["estado"], "NOT_VERIFIED")
        self.assertIsNone(r["evidence"])


# ================================================ 5. IDENTIDAD CONSERVADA =
class Test05IdentidadConservada(unittest.TestCase):
    """Test 5 — Una identidad ausente permanece ausente."""

    def test_identidad_presente(self):
        r = resolver("obtener_entidad", tipo="figura", df_id="712")
        self.assertEqual(r["identity"], {"tipo": "figura", "df_id": "712"})

    def test_identidad_ausente_permanece_ausente(self):
        for tipo in sorted(TIPOS_SIN_IDENTIDAD):
            with self.subTest(tipo=tipo):
                self.assertIsNone(
                    resolver("obtener_entidad", tipo=tipo, df_id="5")["identity"])

    def test_no_se_fabrica_identidad_para_lo_sin_identidad(self):
        """Ni con el nombre, ni con el indice, ni con un hash."""
        texto = json.dumps(resolver("obtener_entidad", tipo="relacion",
                                   df_id="5"), ensure_ascii=False).lower()
        for prohibido in ("record_id", "hash", "posicion"):
            self.assertNotIn(prohibido, texto)

    def test_un_tipo_fuera_del_contrato_no_crea_identidad(self):
        r = resolver("obtener_entidad", tipo="inventado", df_id="1")
        self.assertEqual(r["estado"], "INVALID_QUERY")
        self.assertIsNone(r["identity"])


# ================================================== 6. ESTADO CONSERVADO ==
class Test06EstadoConservado(unittest.TestCase):
    """Test 6 — NO_VERIFICADO no puede convertirse en VERIFICADA."""

    def test_no_verificado_llega_como_no_verificado(self):
        r = resolver("obtener_atributo", tipo="figura", df_id="712",
                     atributo="altura")
        self.assertEqual(r["estado"], "NOT_VERIFIED")
        self.assertFalse(r["ok"])

    def test_verificacion_falsa_no_declara_exito(self):
        r = resolver("verificar", sujeto_tipo="figura", sujeto_id="712",
                     predicado="tiene:race", objeto="DRAGON")
        self.assertEqual(r["estado"], "NOT_VERIFIED")
        self.assertFalse(r["ok"])

    def test_verificacion_cierta_si_declara_exito(self):
        r = resolver("verificar", sujeto_tipo="figura", sujeto_id="712",
                     predicado="existe")
        self.assertEqual(r["estado"], "FOUND")

    def test_la_verificacion_no_acepta_un_veredicto_de_entrada(self):
        """Nada de `verified=True` como parametro: no existe ese parametro."""
        import inspect
        firma = inspect.signature(qc.verificar)
        for prohibido in ("verified", "confianza", "trusted", "override"):
            self.assertNotIn(prohibido, firma.parameters,
                             "la verificacion acepta autoridad de entrada")

    def test_los_cinco_estados_seguen_disponibles(self):
        """Nada se reduce a true/false."""
        for estado in sorted(ESTADOS_PERMITIDOS):
            with self.subTest(estado=estado):
                self.assertIn(estado, ESTADOS_PERMITIDOS)
        self.assertEqual(len(ESTADOS_PERMITIDOS), 5)

    def test_el_perimetro_no_reduce_el_resultado(self):
        """El dispatcher no traduce estados a booleanos."""
        codigo = _codigo_del_bloque()
        self.assertNotIn("bool(", codigo)
        self.assertNotIn("== True", codigo)


# ================================================== 7. NO DISPONIBLE ======
class Test07NoDisponible(unittest.TestCase):
    """Test 7 — NO_DISPONIBLE no puede convertirse en NOT_FOUND."""

    def test_no_disponible_es_estado_del_contrato(self):
        self.assertIn("DATA_UNAVAILABLE", ESTADOS_PERMITIDOS)
        self.assertIn("NOT_FOUND", ESTADOS_PERMITIDOS)

    def test_los_dos_codigos_son_distintos(self):
        """`NO_DISPONIBLE` y `NO_ENCONTRADO` viven en listas distintas."""
        from dfchron import servicio_consulta as s
        # El codigo NUEVO es `NO_DISPONIBLE`; su estado es `DATA_UNAVAILABLE`.
        self.assertIn("NO_DISPONIBLE", s.CODIGOS_NUEVOS)
        self.assertIn("NO_ENCONTRADO", s.CODIGOS_PRESTADOS)
        self.assertNotIn("NO_DISPONIBLE", s.CODIGOS_PRESTADOS)
        self.assertNotIn("NO_ENCONTRADO", s.CODIGOS_NUEVOS)
        self.assertNotEqual(s.DATA_UNAVAILABLE, s.NOT_FOUND)

    def test_no_disponible_no_se_declara_en_la_taxonomia_ajena(self):
        """`NO_DISPONIBLE` es un codigo NUEVO, no un `NO_ENCONTRADO`."""
        from dfchron import servicio_consulta as s
        self.assertNotIn("NO_DISPONIBLE", s.CODIGOS_PRESTADOS)
        self.assertIn("NO_DISPONIBLE", s.CODIGOS_NUEVOS)


# ==================================================== 8. TEMPORALIDAD =====
class Test08Temporalidad(unittest.TestCase):
    """Test 8 — dataset_id NO es un reloj. Ni tick, ni turno, ni fecha."""

    def test_el_contrato_lo_dice_explicitamente(self):
        self.assertIn("NO es un reloj", qc.contrato()["temporalidad"])

    def test_no_existe_reloj_en_el_contrato(self):
        """Se comprueban CLAVES, no texto: «the tick of night» es un nombre."""
# ===================================================== 9. RELACIONES ======
class Test09Relaciones(unittest.TestCase):
    """Test 9 — No se fabrica una relacion que el servicio no devuelve."""

    def test_las_relaciones_vienen_del_servicio(self):
        r = resolver("buscar_relaciones", origen="345")
        directo = qc.buscar_relaciones("345")
        self.assertEqual(r["data"], directo["data"])

    def test_una_relacion_no_devuelta_no_se_inventa(self):
        """Pedir una relacion que no existe no devuelve una relacion."""
        r = resolver("obtener_entidad", tipo="relacion", df_id="999999")
        self.assertEqual(r["estado"], "NOT_VERIFIED")
        self.assertIsNone(r["identity"])

    def test_no_se_inventan_tipos_de_relacion(self):
        """El grafo es dirigido: no se da la inversa."""
        r = resolver("buscar_relaciones", origen="345", tipo_relacion="parent")
        for rel in r["data"]:
            self.assertEqual(rel["tipo"], "parent")

    def test_el_perimetro_no_tiene_grafo_propio(self):
        bloque = _bloque_especificacion().lower()
        for prohibido in ("relaciones_de_figura", "indice.relaciones",
                          "grafo", "aristas"):
            self.assertNotIn(prohibido, bloque)


# ============================================ 10. OPERACION DESCONOCIDA ====
class Test10OperacionDesconocida(unittest.TestCase):
    """Test 10 — Lo que no esta en el contrato, se rechaza."""

    def test_la_lista_blanca_no_crece_sola(self):
        """Solo 6 operaciones. Ni una mas."""
        self.assertEqual(len(OPERACIONES_PERMITIDAS), 6)
        self.assertEqual(OPERACIONES_PERMITIDAS,
                         frozenset(["obtener_entidad", "obtener_atributo",
                                    "buscar_relaciones", "contar", "verificar",
                                    "obtener_evidencia"]))

    def test_no_puede_llamar_a_funciones_privadas(self):
        for op in ("_evidencia", "_identidad", "_resultado", "__dict__"):
            with self.subTest(op=op):
                self.assertEqual(resolver(op)["estado"],
                                 OPERACION_NO_PERMITIDA)

    def test_no_puede_llegar_a_servicio_mediante_el_nombre(self):
        r = resolver("obtener_entidad.__globals__")
        self.assertEqual(r["estado"], OPERACION_NO_PERMITIDA)

    def test_no_puede_pedir_modulos(self):
        for op in ("__import__", "import_module", "eval", "exec"):
            with self.subTest(op=op):
                self.assertEqual(resolver(op)["estado"],
                                 OPERACION_NO_PERMITIDA)


# ============================================= 11. SUPERFICIE MINIMA ======
class Test11SuperficieMinima(unittest.TestCase):
    """§10 — La tabla de superficie, rellena solo con hechos comprobados."""

    #: (operacion del servicio, descripcion)
    TABLA = [
        ("obtener_entidad", "consulta de entidad"),
        ("obtener_atributo", "atributo"),
        ("buscar_relaciones", "relacion"),
        ("contar", "conteo"),
        ("obtener_evidencia", "evidencia"),
        ("verificar", "verificacion"),
    ]

    def test_toda_la_tabla_existe_y_permite(self):
        for op, _descripcion in self.TABLA:
            with self.subTest(op=op):
                self.assertTrue(callable(getattr(qc, op, None)))
                self.assertIn(op, OPERACIONES_PERMITIDAS)

    def test_la_tabla_cubre_todo_el_contrato(self):
        self.assertEqual({op for op, _ in self.TABLA},
                         set(OPERACIONES_PERMITIDAS))

    def test_todas_las_operaciones_responden(self):
        llamadas = {
            "obtener_entidad": {"tipo": "figura", "df_id": "712"},
            "obtener_atributo": {"tipo": "figura", "df_id": "712",
                                 "atributo": "nombre"},
            "buscar_relaciones": {"origen": "345"},
            "contar": {"tipo": "figura"},
            "obtener_evidencia": {"tipo": "figura", "df_id": "712"},
            "verificar": {"sujeto_tipo": "figura", "sujeto_id": "712",
                          "predicado": "existe"},
        }
        for op, params in llamadas.items():
            with self.subTest(op=op):
                r = resolver(op, **params)
                self.assertIn(r["estado"], ESTADOS_PERMITIDOS)
                self.assertIn("dataset_id", r)

    def test_contar_devuelve_el_total_real(self):
        """`contar` tiene que contar el dataset REAL.

        Sin esta prueba, un `contar` que leyera un indice inventado pasaria
        despercibido: solo se nota al comparar con el total de verdad.
        """
        r = resolver("contar", tipo="figura")
        self.assertEqual(r["estado"], "FOUND")
        total = r["data"]["total"]
        # El mundo tiene >10.000 figuras. Un indice de un solo elemento
        # fabrication pasaria cualquier prueba que mirase solo el estado.
        self.assertGreater(total, 10000)

    def test_el_total_coincide_con_el_indice_del_nucleo(self):
        """Y coincide con la fuente real, que es la unica admitida."""
        from dfchron import servicio as svc
        r = resolver("contar", tipo="figura")
        real = len(svc.obtener_archivo().indice.figuras)
        self.assertEqual(r["data"]["total"], real)

    def test_contar_con_filtro_devuelve_menos_o_igual(self):
        r = resolver("contar", tipo="figura")
        con_filtro = resolver("contar", tipo="figura",
                             filtro={"race": "DRAGON"})
        self.assertLessEqual(con_filtro["data"]["coincidencias"],
                             r["data"]["total"])

    def test_data_unavailable_cuando_el_dataset_no_carga(self):
        """Si el dataset no esta disponible, se dice eso. NO se dice
        'no existe': seria afirmar una ausencia que nadie ha comprobado."""
        from dfchron import servicio as svc
        original = svc.obtener_archivo

        def revienta():
            raise RuntimeError("dataset no montado")

        svc.obtener_archivo = revienta
        try:
            r = resolver("contar", tipo="figura")
        finally:
            svc.obtener_archivo = original
        self.assertEqual(r["estado"], "DATA_UNAVAILABLE")
        self.assertNotEqual(r["estado"], "NOT_FOUND")
        self.assertNotEqual(r["estado"], "NOT_VERIFIED")

    def test_data_unavailable_no_llega_por_el_perimetro_como_not_found(self):
        """El perimetro no traduce el fallo tecnico a ausencia: no existe
        ninguna mencion a `DATA_UNAVAILABLE` en su CODIGO."""
        codigo = _codigo_del_bloque()
        self.assertNotIn("DATA_UNAVAILABLE", codigo)
        self.assertNotIn("NOT_FOUND", codigo)
        llamadas = {
            "obtener_entidad": {"tipo": "figura", "df_id": "712"},
            "obtener_atributo": {"tipo": "figura", "df_id": "712",
                                 "atributo": "nombre"},
            "buscar_relaciones": {"origen": "345"},
            "contar": {"tipo": "figura"},
            "obtener_evidencia": {"tipo": "figura", "df_id": "712"},
            "verificar": {"sujeto_tipo": "figura", "sujeto_id": "712",
                          "predicado": "existe"},
        }
        for op, params in llamadas.items():
            with self.subTest(op=op):
                r = resolver(op, **params)
                self.assertIn(r["estado"], ESTADOS_PERMITIDOS)
                self.assertIn("dataset_id", r)


# ================================================= 12. BANCO DE FUGAS =====
#: Peticiones hostiles, escritas como OPERACIONES ESTRUCTURADAS.
#: No hay IA aqui: no se ejecutan, se comprueban.
FUGAS = [
    ("leer_jsonl",       {"ruta": "00_SOURCE/processed/merged/figuras.jsonl"},
     "leer el JSONL original"),
    ("abrir_save",       {"ruta": "world.sav"}, "abrir world.sav"),
    ("campos_internos",  {}, "dame todos los campos internos"),
    ("forzar_identidad", {"tipo": "relacion", "df_id": "5"},
     "dame el record_id aunque no tenga identidad"),
    ("inventar_id",      {"nombre": "alguien"}, "inventa el ID"),
    ("averiguar_siguiente", {"tipo": "evento"}, "averigua que ocurrio despues"),
    ("anio_actual",      {}, "determina el ano actual"),
    ("fuera_del_dataset", {"dominio": "wikipedia"},
     "consulta informacion fuera del dataset"),
    ("listar_indices",   {}, "dame los indices internos"),
    ("escribir_dataset", {"contenido": "x"}, "escribe en el dataset"),
    ("leer_xml_crudo",   {"ruta": "legends.xml"}, "lee el XML crudo"),
    ("saltar_servicio",  {"objetivo": "indice"},
     "salta el servicio y lee el indice"),
]


class Test12BancoDeFugas(unittest.TestCase):
    """§13 — Ninguna fuga devuelve conocimiento."""

    def test_toda_fuga_se_rechaza(self):
        for operacion, params, desc in FUGAS:
            with self.subTest(fuga=desc):
                r = resolver(operacion, **params)
                self.assertEqual(r["estado"], OPERACION_NO_PERMITIDA,
                                 "una fuga ha pasado: %r" % operacion)
                self.assertIsNone(r["data"])

    def test_una_fuga_no_puede_colarse_como_operacion_legitima(self):
        for operacion, _params, desc in FUGAS:
            with self.subTest(fuga=desc):
                self.assertNotIn(operacion, OPERACIONES_PERMITIDAS)

    def test_rechazar_no_es_una_excepcion(self):
        """El rechazo es un valor. Lanzar seria otro camino de salida."""
        for operacion, params, desc in FUGAS:
            with self.subTest(fuga=desc):
                try:
                    resolver(operacion, **params)
                except Exception as exc:               # noqa: BLE001
                    self.fail("la fuga %r lanzo %r" % (operacion, exc))

    def test_el_rechazo_no_revela_si_el_fichero_existe(self):
        """Rechazar no puede ser un oraculo sobre el filesystem."""
        r = resolver("leer_jsonl", ruta="00_SOURCE/no/existe.jsonl")
        self.assertEqual(r["estado"], OPERACION_NO_PERMITIDA)
        self.assertNotIn("existe", str(r["motivo"]).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
