#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INTEGRIDAD DOCUMENTAL: la documentacion no puede mentir ni estar rota.

QUE COMPRUEBA
-------------
Que **las referencias existen** y que **las cifras dicen la verdad**:

  1. Los documentos esenciales están.
  2. Cada ruta citada en el índice y en los documentos clave apunta a algo real.
  3. Las cifras de pruebas que publica la documentación coinciden con las que
     el código ejecuta de verdad.
  4. Las limitaciones `NOT PROVEN` siguen documentadas.
  5. No se presenta como implementado lo que no lo está.

LO QUE NO COMPRUEBA
-------------------
Que un documento sea *correcto* en sus razonamientos. Eso no se puede hacer
mecánicamente. Lo que sí se puede —y es lo que importa para la trazabilidad— es
que no apunte a ficheros inexistentes y no anuncie cifras falsas.

POR QUE EXISTE
--------------
`probar_documentacion_ia.py` ya comprueba que la documentación *semántica* no
contradiga al código. Esta suite cubre el hueco que dejaba: **enlaces y
cifras**. En la auditoría que precedió a esta misión, dos documentos anunciaban
32 pruebas donde había 35, y la comprobación existente no lo detectó porque solo
miraba una cifra.

Ejecutar:  python dfchron/pruebas/probar_documentacion_indice.py
"""
import io
import os
import re
import subprocess
import sys
import unittest

try:
    from . import config                                       # noqa: F401
except ImportError:                                           # pragma: no cover
    _RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

RAIZ = _RAIZ

INDICE = os.path.join(RAIZ, "PROJECT_DOCUMENTATION_INDEX.md")

#: Documentos que, si faltan, dejan al proyecto sin explicación de sí mismo.
ESENCIALES = (
    "README.md",
    "PROJECT_DOCUMENTATION_INDEX.md",
    "ARCHITECTURE.md",
    "ARCHITECTURE_OVERVIEW.md",
    "ARCHITECTURE_DECISIONS.md",
    "TECHNICAL_ROADMAP.md",
    "INFORME_CIERRE_PRE_IA.md",
    "INFORME_CONSOLIDACION_ARQUITECTONICA.md",
    os.path.join("08_DATABASE", "architecture.md"),
    os.path.join("08_DATABASE", "ai_data_contract.md"),
    os.path.join("08_DATABASE", "AI_PRE_LLM_CONTRACT.md"),
    os.path.join("08_DATABASE", "AI_PROJECT_CONTEXT.md"),
    os.path.join("08_DATABASE", "data_limitations.md"),
)

#: Documentos donde se comprueban las referencias.
CON_ENLACES = ESENCIALES

#: Limitaciones que NO deben desaparecer de la documentación. Si alguien las
#: cerrara de verdad, esta lista cambia a propósito, no por descuido.
#:
#: Se buscan SIN tilde a propósito: en este proyecto los documentos antiguos
#: escriben deliberadamente `semantica`, `relacional`, `lexica`. Comparar con
#: tilde daría un falso negativo en documentos que sí hablan del problema.
LIMITACIONES = (
    "semantic",     # verificación semántica
    "relacional",   # afirmaciones relacionales
    "caducidad",    # caducidad temporal
    "en vivo",      # estado de partida en vivo
)


def leer(ruta_rel):
    with io.open(os.path.join(RAIZ, ruta_rel), encoding="utf-8") as f:
        return f.read()


def bajo(texto):
    return texto.lower()


def sin_tildes(texto):
    """Minúsculas y sin tildes, para comparar sin depender de la ortografía.

    Los documentos de este proyecto mezclan `semantica` y `semántica` según la
    época. Una comprobación de integridad no debe depender de cuál se usó.
    """
    txt = texto.lower()
    for con, sin in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                     ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        txt = txt.replace(con, sin).replace(sin.upper(), sin)
    return txt


class TestDocumentosEsenciales(unittest.TestCase):
    """Lo que tiene que existir para que el proyecto se explique solo."""

    def test_los_documentos_esenciales_existen(self):
        faltan = [r for r in ESENCIALES
                  if not os.path.exists(os.path.join(RAIZ, r))]
        self.assertEqual(faltan, [],
                         "faltan documentos esenciales: %s" % faltan)

    def test_el_indice_existe_y_no_esta_vacio(self):
        self.assertGreater(len(leer("PROJECT_DOCUMENTATION_INDEX.md")), 500)


class TestReferenciasNoRotas(unittest.TestCase):
    """Ninguna referencia apunta a algo que no exista.

    Se resuelve por ruta relativa, por ruta desde la raíz, y por nombre de
    fichero en cualquier parte del proyecto. Los tres intentos existen porque la
    documentación usa las tres formas: `README.md`, `08_DATABASE/x.md` y
    `x.py` para un módulo que vive en `dfchron/`.
    """

    def _todos_los_ficheros(self):
        nombres = set()
        for base, _dirs, ficheros in os.walk(RAIZ):
            # No se baja a los sitios pesados ni generados.
            if any(p in base for p in ("node_modules", "original_data",
                                       "backups", "__pycache__", ".wrangler",
                                       "dist", ".git")):
                continue
            nombres.update(ficheros)
        return nombres

    def test_ninguna_referencia_esta_rota(self):
        existentes = self._todos_los_ficheros()
        rotas = []
        patron = re.compile(r"`([\w][\w\\/\.\-]*\.(?:md|py|json|js|html|css))`")
        for doc in CON_ENLACES:
            texto = leer(doc)
            base = os.path.dirname(os.path.join(RAIZ, doc))
            for ref in patron.findall(texto):
                ref = ref.replace("\\", "/")
                if (os.path.exists(os.path.join(RAIZ, ref))
                        or os.path.exists(os.path.join(base, ref))
                        or os.path.basename(ref) in existentes):
                    continue
                rotas.append("%s -> %s" % (doc, ref))
        self.assertEqual(rotas, [], "referencias rotas: %s" % rotas)

    def test_el_indice_no_tiene_rutas_inexistentes(self):
        """Lo específico del índice: una entrada debe ser un fichero real."""
        texto = leer("PROJECT_DOCUMENTATION_INDEX.md")
        existentes = self._todos_los_ficheros()
        rotas = []
        # Rutas de tabla: `algo.md` o `algo/dir/algo.md`
        for ref in re.findall(r"\|\s*`([\w][\w\\/\.\-]*\.(?:md|py))`", texto):
            ref = ref.replace("\\", "/")
            if os.path.basename(ref) not in existentes:
                rotas.append(ref)
        self.assertEqual(rotas, [],
                         "el indice lista ficheros que no existen: %s" % rotas)


#: Documentos donde se comprueban las cifras de pruebas declaradas.
#: Cada fila de tabla tiene la forma  | `suite.py` | modulo | N |
CON_CIFRAS = (os.path.join("08_DATABASE", "AI_PROJECT_CONTEXT.md"),)

#: Dónde puede vivir cada suite. Se buscan en varios sitios a propósito: una
#: suite puede estar en `dfchron/pruebas/` o en `00_SOURCE/tools/`.
DIRS_SUITES = (os.path.join("dfchron", "pruebas"),
               os.path.join("00_SOURCE", "tools"), "")


def ejecutar(suite):
    """Ejecuta una suite y devuelve cuántas pruebas corrieron. -1 si no se pudo."""
    p = subprocess.run([sys.executable, suite], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"Ran (\d+) tests?", out)
    return int(m.group(1)) if m else -1


class TestCifrasDocumentadas(unittest.TestCase):
    """Lo que la documentación dice que hay, contado de verdad.

    Esta es la comprobación que faltaba. Dos documentos anunciaban 32 pruebas de
    `probar_ia_mock.py` cuando había 35, y nadie lo notó: la comprobación
    anterior solo miraba la cifra de `probar_contrato_ia.py`.
    """

    def _filas(self):
        """(documento, suite, cifra declarada) de cada fila con cifra."""
        pat = re.compile(r"\|\s*`([\w_]+\.py)`\s*\|[^|]*\|\s*(\d+)\s*\|")
        filas = []
        for doc in CON_CIFRAS:
            for suite, cifra in pat.findall(leer(doc)):
                filas.append((doc, suite, int(cifra)))
        return filas

    def test_se_ha_encontrado_al_menia_una_cifra(self):
        """Si el patrón dejara de encontrar filas, la prueba no comprobaría nada."""
        filas = self._filas()
        self.assertGreaterEqual(
            len(filas), 8,
            "solo se han encontrado %d filas de cifras; el patrón ha cambiado"
            % len(filas))

    def test_las_cifras_documentadas_coinciden_con_el_codigo(self):
        """Cada suite se ejecuta y se compara. Sin excepciones."""
        discrepancias, comprobadas = [], 0
        for doc, suite, declarada in self._filas():
            ruta = None
            for d in DIRS_SUITES:
                candidata = (os.path.join(RAIZ, d, suite) if d
                             else os.path.join(RAIZ, suite))
                if os.path.exists(candidata):
                    ruta = candidata
                    break
            if ruta is None:
                discrepancias.append("%s cita %s, que no existe" % (doc, suite))
                continue
            real = ejecutar(ruta)
            comprobadas += 1
            if real != declarada:
                discrepancias.append(
                    "%s dice %d pruebas de %s; el código ejecuta %d"
                    % (doc, declarada, suite, real))
        self.assertGreater(comprobadas, 0)
        self.assertEqual(discrepancias, [],
                         "cifras desactualizadas: %s" % discrepancias)


class TestLimitacionesVisibles(unittest.TestCase):
    """Lo que NO se demuestra tiene que seguir escrito como tal."""

    def test_las_limitaciones_siguen_documentadas(self):
        documentos = (os.path.join("08_DATABASE", "AI_PRE_LLM_CONTRACT.md"),
                      "INFORME_CIERRE_PRE_IA.md",
                      "ARCHITECTURE_OVERVIEW.md")
        for doc in documentos:
            texto = sin_tildes(leer(doc))
            with self.subTest(documento=doc):
                for limitacion in LIMITACIONES:
                    self.assertIn(limitacion, texto,
                                  "%s ya no menciona la limitación %r"
                                  % (doc, limitacion))

    def test_el_estado_pre_llm_esta_declarado(self):
        cierre = leer("INFORME_CIERRE_PRE_IA.md")
        self.assertIn("PRE-LLM CERRADO CON RESERVAS", cierre)
        # Y el índice dice lo mismo, para que no haya dos verdades.
        self.assertIn("PRE-LLM CERRADO CON RESERVAS",
                      leer("PROJECT_DOCUMENTATION_INDEX.md"))


class TestNoSeVendeLoInexistente(unittest.TestCase):
    """Lo que no está implementado no puede aparecer como implementado."""

    def test_no_se_declara_un_modelo_conectado(self):
        """La ausencia de IA debe estar declarada, no insinuada."""
        for doc in ("ARCHITECTURE_OVERVIEW.md",
                    os.path.join("08_DATABASE", "AI_PRE_LLM_CONTRACT.md")):
            texto = bajo(leer(doc))
            with self.subTest(documento=doc):
                for marca in ("no existe", "ninguna", "no hay"):
                    self.assertIn(
                        marca, texto,
                        "%s no declara la ausencia de IA (%r)" % (doc, marca))

    def test_la_integracion_con_df_no_se_da_por_decidida(self):
        """La vía de integración está sin decidir, y el roadmap lo dice."""
        self.assertIn("sin decidir", bajo(leer("TECHNICAL_ROADMAP.md")))
        self.assertIn("pendiente", bajo(leer("ARCHITECTURE_DECISIONS.md")))

    def test_no_hay_sdk_de_ia_en_el_codigo(self):
        """Comprobación de código, no de documento: es la garantía de fondo."""
        prohibido = ("openai", "anthropic", "google.generativeai",
                     "transformers", "langchain", "cohere", "mistralai")
        fallos = []
        for base, dirs, ficheros in os.walk(os.path.join(RAIZ, "dfchron")):
            dirs[:] = [d for d in dirs
                       if d not in ("__pycache__", "node_modules", "pruebas")]
            for nombre in ficheros:
                if not nombre.endswith(".py"):
                    continue
                ruta = os.path.join(base, nombre)
                with io.open(ruta, encoding="utf-8", errors="replace") as f:
                    texto = bajo(f.read())
                for sdk in prohibido:
                    if re.search(r"^\s*(import|from)\s+%s\b" % sdk, texto, re.M):
                        fallos.append("%s importa %s" % (ruta, sdk))
        self.assertEqual(fallos, [], "SDK de IA en produccion: %s" % fallos)


if __name__ == "__main__":
    unittest.main(verbosity=2)