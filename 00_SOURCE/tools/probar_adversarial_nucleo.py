#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADVERSARIAL DEL NUCLEO: campos adicionales y datos parcialmente incompletos.

POR QUE ESTA SUITE EXISTE
-------------------------
La auditoría de Fase 8 comparó las adversidades que pide la misión con lo que
cubrían las suites existentes. Trece de las catorce ya estaban cubiertas
(`probar_adversarial.py`, más `probar_estado_conocimiento.py` y
`probar_cierre_pre_ia.py` para dataset incompatible y evidencia de otro mundo).

Faltaban dos, y estas son:

  * **campos adicionales**: un JSONL con claves que el nucleo no conoce.
  * **datos parcialmente incompletos**: registros a los que les falta parte.

Ninguna de las dos es exótica, pero las dos pueden producir el fallo más
peligoso de un nucleo de datos: que un campo desconocido se interprete como si
fuera real, o que un registro incompleto se presente como completo.

LA REGLA QUE SE COMPRUEBA
-------------------------
El nucleo debe **ignorar** lo que no entiende y **declarar** lo que no tiene. No
debe inventar, no debe adivinar, y no debe convertir un dato parcial en un hecho
completo.

Ejecutar:  python 00_SOURCE/tools/probar_adversarial_nucleo.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nucleo import Archivo                        # noqa: E402


def _leer_jsonl(ruta):
    filas = []
    with io.open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                filas.append(json.loads(linea))
    return filas


def _volcar_jsonl(ruta, filas):
    with io.open(ruta, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


class _DatasetTemporal(unittest.TestCase):
    """Copia de trabajo del dataset. El real NO se toca nunca.

    Se copia **una sola sección** a un directorio temporal y se le dice al
    código que lea de ahí. Al ser una copia, no hace falta restaurar nada: el
    dataset real no se abre ni se escribe.
    """

    #: Sección que cada prueba va a deformar.
    SECCION = "historical_figures"

    def setUp(self):
        import rutas
        self._dir = tempfile.mkdtemp(prefix="dfch-nucleo-")
        self.addCleanup(shutil.rmtree, self._dir, True)
        origen = os.path.join(rutas.MERGED_ROOT, self.SECCION + ".jsonl")
        self.ruta = os.path.join(self._dir, self.SECCION + ".jsonl")
        shutil.copyfile(origen, self.ruta)
        self.originales = _leer_jsonl(self.ruta)

    def _con(self, filas):
        """Escribe las filas y devuelve el nucleo leido de la copia."""
        _volcar_jsonl(self.ruta, filas)
        return _leer_desde(self._dir)

    def _truncar(self, cuantas):
        """Deja solo las primeras `cuantas` filas.

        Se hace con `del`, no con un rebajado: `_degradar()` usa el valor que
        devuelve el mutador, y eso es facil de equivocar en silencio. Aqui la
        lista se modifica en el sitio y no hay nada que devolver.
        """
        filas = [json.loads(json.dumps(f)) for f in self.originales]
        del filas[cuantas:]
        return self._con(filas)

    def _degradar(self, mutador):
        """Aplica `mutador` a una copia y devuelve el nucleo resultante.

        El mutador modifica la lista **en el sitio**. No se usa su valor de
        retorno: una versión anterior confiaba en él, y `filas[:5]` no mutaba
        nada, así que la prueba pasaba sin comprobar lo que creía.
        """
        filas = [json.loads(json.dumps(f)) for f in self.originales]
        mutador(filas)
        return self._con(filas)

    def _intacto(self):
        """El nucleo leyendo la copia sin tocar nada. Debe ser el estado bueno."""
        return self._con([json.loads(json.dumps(f)) for f in self.originales])


def _leer_desde(directorio):
    """Un `Archivo` que lee de `directorio` en vez del dataset real.

    Por qué el parche es en la FUNCIÓN y no en la constante:

        def cargar_jsonl(nombre, carpeta=MERGED):   # <- valor capturado AL DEFINIR

    El valor por defecto se evalúa una sola vez, cuando se define la función.
    Cambiar `validar_semantica.MERGED` después **no** cambia lo que lee
    `cargar_jsonl`. Por eso se sustituye la propia función: es el punto de
    entrada real, y hacerlo visible evita que esta parezca funcionar cuando no
    comprueba nada.

    Se restaura en el `finally`. El dataset real no se abre ni se escribe.
    """
    import nucleo
    from validar_semantica import Indice

    real_cargar = validar_semantica.cargar_jsonl

    def cargar_de_la_copia(nombre, carpeta=None):
        return real_cargar(nombre, directorio)

    validar_semantica.cargar_jsonl = cargar_de_la_copia
    nucleo.cargar_jsonl = cargar_de_la_copia
    try:
        indice = Indice()
        indice.cargar()
        archivo = nucleo.Archivo.__new__(nucleo.Archivo)
        archivo.indice = indice
        archivo.c = nucleo.Consultas(indice)
        archivo.tiempo_carga = 0.0
        archivo._rivers = cargar_de_la_copia("rivers")
        archivo._landmasses = cargar_de_la_copia("landmasses")
        archivo._peaks = cargar_de_la_copia("mountain_peaks")
        archivo._wcs = cargar_de_la_copia("world_constructions")
        archivo.creador_artefacto = {}
        archivo.ev_por_artefacto = {}
        return archivo
    finally:
        validar_semantica.cargar_jsonl = real_cargar
        nucleo.cargar_jsonl = real_cargar


import validar_semantica                               # noqa: E402


# ================================== CAMPOS ADICIONALES ====================
class TestCamposAdicionales(_DatasetTemporal):
    """Un JSONL con claves que el nucleo no conoce.

    El riesgo real no es que rompa: es que las ignore en silencio y el jugador
    crea que el dato existe. Aqui se comprueba que se ignoran **y** que no
    inventan nada.
    """

    #: Claves falsas que el juego NUNCA escribe.
    FANTASMAS = ("poder_magico", "nivel_de_threat", "secreto_del_jefe",
                 "inventario_oculto", "es_jefe_final")

    def test_las_claves_fantasma_no_se_interpretan(self):
        """Los campos reales no cambian por que haya campos inventados."""
        nucleo_ok = self._intacto()
        nucleo_malo = self._degradar(
            lambda filas: _inyectar_campos(filas, self.FANTASMAS))
        buena = nucleo_ok.ficha_figura(0, breve=True)
        mala = nucleo_malo.ficha_figura(0, breve=True)
        for campo in ("nombre", "race", "caste", "df_id", "certainty"):
            self.assertEqual(buena.get(campo), mala.get(campo),
                             "el campo fantasma alteró %r" % campo)

    def test_las_claves_fantasma_no_aparecen_en_la_ficha(self):
        """Lo que el juego no escribió no puede salir en la respuesta."""
        nucleo_malo = self._degradar(
            lambda filas: _inyectar_campos(filas, self.FANTASMAS))
        volcado = json.dumps(nucleo_malo.ficha_figura(0, breve=True),
                             ensure_ascii=False, default=str)
        for fantasma in self.FANTASMAS:
            self.assertNotIn(fantasma, volcado,
                             "el campo fantasma %r llegó a la ficha" % fantasma)
        self.assertNotIn("valor_inventado", volcado)

    def test_un_campo_adicional_no_cambia_el_conteo(self):
        nucleo_ok = self._intacto()
        nucleo_malo = self._degradar(
            lambda filas: _inyectar_campos(filas, self.FANTASMAS))
        self.assertEqual(len(nucleo_ok.indice.figuras),
                         len(nucleo_malo.indice.figuras),
                         "un campo adicional cambió el número de figuras")

    def test_una_clave_extra_en_el_registro_tambien_se_ignora(self):
        """La basura puede estar en `campos` o en la raíz del registro."""

        def mutar(filas):
            _inyectar_campos(filas, ("campo_nuevo",))
            for f in filas[:5]:
                f["clave_raiz_desconocida"] = "inventado"

        nucleo_ok = self._intacto()
        nucleo_malo = self._degradar(mutar)
        self.assertEqual(nucleo_ok.ficha_figura(0, breve=True).get("nombre"),
                         nucleo_malo.ficha_figura(0, breve=True).get("nombre"))


def _inyectar_campos(filas, nombres, valor="valor_inventado"):
    """Añade campos que el juego nunca escribe, en unas pocas filas."""
    for f in filas[:50]:
        campos = f.setdefault("campos", {})
        for n in nombres:
            campos[n] = {"valor": valor, "source": "legends.xml",
                         "source_section": "historical_figures"}


# ========================= DATOS PARCIALMENTE INCOMPLETOS ================
class TestDatosParcialmenteIncompletos(_DatasetTemporal):
    """Registros a los que les falta parte.

    El peligro no es que el nucleo falle: es que rellene. Un `birth_year` que no
    esta no puede convertirse en «nació el año 1», y un registro sin `campos` no
    puede convertirse en una ficha vacía que parezca una ficha real.
    """

    def test_sin_campos_la_figura_no_inventa_atributos(self):
        def mutar(filas):
            for f in filas[:10]:
                f["campos"] = {}
        nucleo = self._degradar(mutar)
        ficha = nucleo.ficha_figura(0, breve=True)
        # La figura sigue existiendo: el registro está, aunque vacío.
        self.assertEqual(ficha.get("df_id"), "0")
        # Pero sus atributos no se inventan.
        for campo in ("nombre", "race", "caste"):
            valor = ficha.get(campo)
            self.assertIn(valor, (None, "", "UNKNOWN"),
                          "el nucleo inventó %s = %r" % (campo, valor))

    def test_sin_el_campo_de_nacimiento_no_hay_fecha(self):
        """`birth_year` ausente no puede salir como año."""
        def mutar(filas):
            for f in filas[:10]:
                f.get("campos", {}).pop("birth_year", None)
        nucleo = self._degradar(mutar)
        nac = nucleo.ficha_figura(0, breve=True).get("nacimiento") or {}
        self.assertIsNone(nac.get("año"),
                          "el nucleo inventó un año de nacimiento")
        self.assertEqual(nac.get("certainty"), "UNKNOWN")

    def test_un_valor_vacio_no_es_un_valor(self):
        """`""` no es un nombre. Se declara ausente, no vacío."""
        def mutar(filas):
            for f in filas[:10]:
                campos = f.setdefault("campos", {})
                if "name" in campos:
                    campos["name"]["valor"] = ""
        nucleo = self._degradar(mutar)
        nombre = nucleo.ficha_figura(0, breve=True).get("nombre")
        self.assertIn(nombre, (None, "", "UNKNOWN"),
                      "el nucleo presentó una cadena vacía como nombre real")

    def test_sin_df_id_el_registro_falla_al_cargar(self):
        """LÍMITE REAL del núcleo, documentado como tal.

        `Indice.cargar()` hace `self.figuras[r["df_id"]] = r`: accede a la
        clave **sin** `.get()`. Un registro sin `df_id` no se ignora con
        elegancia: **rompe la carga entera** con `KeyError`.

        Esto NO se considera un defecto que haya que arreglar aqui. El dataset
        lo genera el propio proyecto y siempre trae `df_id`; añadir una regla de
        tolerancia cambiaría la semántica del índice sin que nadie lo pidiera, y
        la misión prohíbe relajar o inventar.

        Lo que sí hace esta prueba es **fijar el comportamiento real**, para que
        nadie lo descubra por sorpresa: un JSONL mal formado se rompe al cargar,
        y el error dice exactamente por qué.
        """
        def mutar(filas):
            for f in filas[:3]:
                f.pop("df_id", None)
        with self.assertRaises(KeyError) as ctx:
            self._degradar(mutar)
        self.assertIn("df_id", str(ctx.exception))

    def test_el_resto_del_dataset_no_se_corrompe(self):
        """Quitar la mayoria de las figuras no rompe la carga.

        Al leer desde un directorio que solo tiene `historical_figures`, las
        demas secciones quedan **vacias** — y eso es lo correcto: `cargar_jsonl`
        devuelve `[]` si el fichero no esta, y lo que no esta no se rellena.

        La propiedad que importa aquí no es «las demas siguen», sino «cargar un
        dataset incompleto no revienta ni inventa». Por eso se comprueba que las
        consultas vacias responden con honestidad en vez de con basura.
        """
        nucleo = self._truncar(5)
        self.assertEqual(len(nucleo.indice.figuras), 5,
                         "la copia truncada no se respeta: %d"
                         % len(nucleo.indice.figuras))
        # Las secciones ausentes quedan vacias, no rellenas de nada.
        self.assertEqual(nucleo.indice.entidades, {},
                         "una sección ausente se inventó")
        self.assertEqual(nucleo.indice.sitios, {},
                         "una sección ausente se inventó")
        # Y una figura que si esta, se sigue pudiendo consultar.
        self.assertEqual(nucleo.ficha_figura("0", breve=True).get("df_id"), "0")

    def test_una_seccion_ausente_no_deja_basura(self):
        """Si el fichero no está, `cargar_jsonl` devuelve vacío: índice vacío.

        La sección ausente no se rellena con nada. Es el comportamiento correcto
        y fail-safe: lo que no esta, no se inventa.
        """
        import os as _os
        _os.remove(self.ruta)
        nucleo = self._con([])
        self.assertEqual(nucleo.indice.figuras, {},
                         "una sección ausente dejó basura en el índice")


if __name__ == "__main__":
    unittest.main(verbosity=2)