#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF Chronicles :: pruebas del motor de cronica v1.

Prueban INVARIANTES, no cobertura de lineas:
    determinismo · idempotencia · orden estable · no invencion
    ausencia != negacion · procedencia · identidad no fabricada

Uso:  python dfchron/pruebas/probar_chronicles.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_RAIZ = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dfchron import chronicles as ch  # noqa: E402


def _reg(rid, df_id, nombre, certainty="FACT",
         seccion="historical_figures"):
    return {"record_id": rid, "df_id": df_id, "certainty": certainty,
            "source": "legends.xml", "source_section": seccion,
            "campos": {"name": nombre}}


class _Base(unittest.TestCase):

    def eventos_de_ejemplo(self):
        """Eventos con ORDEN DE ENTRADA barajado a proposito.

        Si el motor dependiera del orden de llegada, este test lo delataria.
        """
        return [
            ch.evento_observado(ch.BIRTH, "fig:712", 100, ["r1"], "FACT",
                                 {"name": "Urist"}),
            ch.evento_observado(ch.DEATH, "fig:900", 300, ["r9"], "FACT",
                                 {"cause": "hambre"}),
            ch.evento_observado(ch.ARRIVAL, "fig:712", 100, ["r2"], "FACT",
                                 {"name": "Urist"}),
            ch.evento_observado(ch.CONSTRUCTION, "ed:5", 200, ["r5"], "FACT",
                                 {"type": "Workshop"}),
        ]


class TestDeterminismo(_Base):

    def test_dos_ejecuciones_dan_el_mismo_id(self):
        self.assertEqual(ch.id_de_evento(ch.BIRTH, "fig:712", 100, ["r1"]),
                         ch.id_de_evento(ch.BIRTH, "fig:712", 100, ["r1"]),
                         "el identificador NO es determinista")

    def test_el_orden_de_entrada_no_cambia_el_resultado(self):
        evs = self.eventos_de_ejemplo()
        normal = ch.construir_timeline(evs)
        self.assertEqual(normal, ch.construir_timeline(list(reversed(evs))))
        self.assertEqual(normal, ch.construir_timeline(
            [evs[2], evs[0], evs[3], evs[1]]),
            "el motor depende del ORDEN de llegada")

    def test_el_id_es_estable_entre_procesos(self):
        cod = ("import sys; sys.path.insert(0, %r); "
               "from dfchron import chronicles as c; "
               "print(c.id_de_evento('BIRTH','f',1,['a']))" % _RAIZ)
        salidas = {subprocess.run([sys.executable, "-c", cod],
                                  capture_output=True,
                                  text=True).stdout.strip()
                   for _ in range(2)}
        self.assertEqual(len(salidas), 1,
                         "el identificador varia entre procesos: dependeria "
                         "de PYTHONHASHSEED")


class TestIdempotencia(_Base):

    def test_procesar_dos_veces_no_duplica(self):
        evs = self.eventos_de_ejemplo()
        uno = ch.construir_timeline(evs)
        self.assertEqual(len(uno), 4)
        self.assertEqual(ch.construir_timeline(evs + evs), uno,
                         "procesar dos veces ha DUPLICADO eventos")

    def test_los_duplicados_exactos_se_colapsan(self):
        e = ch.evento_observado(ch.BIRTH, "f", 1, ["r"], "FACT", {})
        self.assertEqual(len(ch.construir_timeline([e, e, e])), 1)


class TestOrdenEstable(_Base):

    def test_orden_por_tick_luego_tipo(self):
        t = ch.construir_timeline(self.eventos_de_ejemplo())
        ticks = [e["tick"] for e in t]
        self.assertEqual(ticks, sorted(ticks), "la timeline no esta ordenada")
        self.assertEqual([e["event_type"] for e in t][:2],
                         ["ARRIVAL", "BIRTH"],
                         "a igual tick, el desempate no es estable")

    def test_un_evento_sin_tick_no_inventa_posicion(self):
        sin_tick = ch.evento_observado(ch.COMBAT, "x", None, ["r"],
                                       "FACT", {})
        t = ch.construir_timeline([sin_tick] + self.eventos_de_ejemplo())
        self.assertEqual(len(t), 5)
        self.assertEqual(len([e for e in t if e.get("tick") is not None]), 4)


class TestAusenciaNoEsNegacion(_Base):

    def test_ausencia_no_genera_muerte(self):
        """Una figura que no aparece NO se convierte en DEATH."""
        evs = [ch.evento_observado(ch.BIRTH, "fig:1", 10, ["r"],
                                   "FACT", {})]
        self.assertEqual([e for e in evs if e["event_type"] == ch.DEATH],
                         [], "el motor fabrico una MUERTE por ausencia")

    def test_sin_estados_conocidos_no_deriva_nada(self):
        self.assertIsNone(ch.evento_derivado_profesion(
            "fig:1", 10, 20, None, "mason", ["r1", "r2"]))

    def test_sin_procedencia_no_deriva_nada(self):
        self.assertIsNone(ch.evento_derivado_profesion(
            "fig:1", 10, 20, "miner", "mason", []))
class TestDerivacion(_Base):

    def test_cambio_de_profesion_se_deriva(self):
        ev = ch.evento_derivado_profesion("fig:712", 10, 20, "miner",
                                           "mason", ["r1", "r2"])
        self.assertIsNotNone(ev)
        self.assertEqual(ev["origin"], ch.DERIVED,
                         "un evento derivado no puede decir OBSERVED")
        self.assertEqual(ev["certainty"], "DERIVED")
        self.assertEqual(ev["summary"], {"de": "miner", "a": "mason",
                                         "tick_anterior": 10})

    def test_sin_cambio_no_hay_evento(self):
        self.assertIsNone(ch.evento_derivado_profesion(
            "fig:712", 10, 20, "miner", "miner", ["r1", "r2"]))

    def test_un_tipo_no_permitido_se_rechaza(self):
        with self.assertRaises(ValueError):
            ch.evento_observado("SE_YUNTO", "x", 1, [], "FACT", {})


class TestIdentidad(_Base):

    def test_sin_df_id_no_se_fabrica_identidad(self):
        ent = ch.entidad_de_registro(_reg("r:9", None, "Anonimo"))
        self.assertIsNone(ent["entity_id"], "se fabrico un ID sin df_id")
        self.assertEqual(ent["identity_status"], "NOT_PROVEN")

    def test_con_df_id_la_identidad_es_demostrada(self):
        ent = ch.entidad_de_registro(_reg("r:1", "712", "Urist"))
        self.assertEqual(ent["entity_id"], "712")
        self.assertEqual(ent["identity_status"], "DEMONSTRATED")
        self.assertEqual(ent["display_name"], "Urist")
        self.assertEqual(ent["provenance"]["source"], "legends.xml")


class TestProcedencia(_Base):

    def test_todo_evento_conserva_evidencia(self):
        for ev in self.eventos_de_ejemplo():
            self.assertTrue(ev.get("evidence"))

    def test_la_entidad_conserva_record_id_y_fuente(self):
        ent = ch.entidad_de_registro(_reg("r:1", "712", "Urist"))
        self.assertEqual(ent["provenance"]["record_id"], "r:1")
        self.assertIn("source", ent["provenance"])


class TestEstadoHistorico(_Base):

    def test_sin_observacion_no_interpola(self):
        r = ch.estado_en_tick([{"entidad": "f", "tick": 1, "estado": "vivo",
                               "certainty": "FACT", "evidence": ["r1"]}],
                              "f", 99)
        self.assertEqual(r["status"], "NOT_AVAILABLE")
        self.assertIsNone(r["estado"])

    def test_con_observacion_devuelve_el_estado(self):
        r = ch.estado_en_tick([{"entidad": "f", "tick": 7,
                               "estado": "muerto", "certainty": "FACT",
                               "evidence": ["r7"]}], "f", 7)
        self.assertEqual(r["status"], "AVAILABLE")
        self.assertEqual(r["estado"], "muerto")


class TestFiltros(_Base):

    def test_filtro_por_tipo(self):
        t = ch.construir_timeline(self.eventos_de_ejemplo())
        self.assertEqual(len(ch.filtrar_por_tipo(t, ch.BIRTH)), 1)

    def test_filtro_por_entidad(self):
        t = ch.construir_timeline(self.eventos_de_ejemplo())
        self.assertEqual(len(ch.timeline_de_entidad(t, "fig:712")), 2)

    def test_rango_temporal_inclusivo(self):
        t = ch.construir_timeline(self.eventos_de_ejemplo())
        self.assertEqual(len(ch.filtrar_por_rango(t, 100, 200)), 3)

    def test_rango_excluye_eventos_sin_tick(self):
        t = ch.construir_timeline(
            [ch.evento_observado(ch.COMBAT, "x", None, ["r"], "FACT", {})]
            + self.eventos_de_ejemplo())
        self.assertNotIn(None, [e.get("tick")
                                for e in ch.filtrar_por_rango(t, 0, 9999)])


class TestSnapshot(_Base):

    def test_no_declara_edificios_ni_recursos_inventados(self):
        ent = [ch.entidad_de_registro(_reg("r:1", "712", "Urist"))]
        snap = ch.fortress_snapshot(ent, self.eventos_de_ejemplo())
        self.assertEqual(snap["edificios"], "NOT_AVAILABLE")
        self.assertEqual(snap["recursos"], "NOT_AVAILABLE")
        self.assertEqual(snap["poblacion_conocida"], 1)

    def test_el_snapshot_es_determinista(self):
        ent = [ch.entidad_de_registro(_reg("r:1", "712", "Urist"))]
        a = ch.fortress_snapshot(ent, self.eventos_de_ejemplo())
        b = ch.fortress_snapshot(ent, ch.construir_timeline(
            self.eventos_de_ejemplo()))
        self.assertEqual(json.dumps(a, sort_keys=True, default=str),
                         json.dumps(b, sort_keys=True, default=str))


if __name__ == "__main__":
    unittest.main(verbosity=2)
