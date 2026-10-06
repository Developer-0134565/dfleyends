#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Aplicacion
==========================

Aplicacion local para explorar los datos historicos de Dwarf Fortress.

ARQUITECTURA
------------
    UI (navegador)  ─┐
                     ├─> dfchron.api  (HTTP, solo stdlib)
    otro cliente  ───┘        │
                              v
                       dfchron.servicio   <- envelopes, validacion, limites
                              │
                              v
                    00_SOURCE/tools/nucleo.py   <- LOGICA DE DOMINIO
                              │
                              v
                    00_SOURCE/processed/merged/*.jsonl

REGLAS INNEGOCIABLES
--------------------
1. La UI NUNCA lee los XML. Habla con la API.
2. La API NUNCA implementa logica de Dwarf Fortress. Delega en el nucleo.
3. El nucleo NUNCA escribe en processed/ ni en original_data/.
4. Ningun recorte es silencioso: toda respuesta dice cuanto hay y cuanto va.
"""
__all__ = ["config", "servicio", "api"]
__version__ = "1.0"
