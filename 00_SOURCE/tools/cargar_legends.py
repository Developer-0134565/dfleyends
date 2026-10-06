#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Cargador de exports de Legends
==============================================

Carga los XML de Legends detectando la codificación, sin valores hardcodeados.

Estrategia de detección (en orden, sin hardcodear CP437/UTF-8):
  1. BOM UTF-8/UTF-16 si está presente.
  2. UTF-8 estricto (test fiable: si pasa, el archivo es UTF-8 válido).
  3. La codificación declarada en `<?xml ... encoding="..."?>`.
  4. Cascada de candidatos y, como último recurso, CP437 (nunca falla).

Los bytes de control prohibidos en XML se eliminan SOLO EN MEMORIA, para poder
parsear. Los archivos originales se abren en modo lectura y nunca se escriben.

Identificadores: se usan los IDs propios de Dwarf Fortress. Para registros sin
`<id>` (p.ej. `rivers`) se deriva un ID determinista del contenido, marcado
como DERIVED; nunca se genera un ID aleatorio.
"""
import re
import hashlib
import collections
import xml.etree.ElementTree as ET

CTRL_PROHIBIDOS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
CANDIDATAS = ("utf-8", "cp437", "latin-1")

FACT = "FACT"
DERIVED = "DERIVED"


class ResultadoLectura:
    """Resultado de leer un XML de Legends. Nunca escribe en disco."""

    def __init__(self, path):
        self.path = str(path)
        with open(self.path, "rb") as f:
            self.bruto = f.read()
        self.bytes = len(self.bruto)
        self.sha256 = hashlib.sha256(self.bruto).hexdigest()
        self.bom = None
        self.codificacion_declarada = None
        self.codificacion = None
        self.metodo_deteccion = None
        self.bytes_control = {}
        self.requiere_saneo = False
        self.raiz = None
        self.error = None

    def _detectar(self):
        b = self.bruto
        if b.startswith(b"\xef\xbb\xbf"):
            self.bom = "UTF-8"
            self.codificacion, self.metodo_deteccion = "utf-8-sig", "BOM UTF-8"
            return
        if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
            self.bom = "UTF-16"
            self.codificacion, self.metodo_deteccion = "utf-16", "BOM UTF-16"
            return

        m = re.match(rb"""\s*<\?xml[^>]*?encoding\s*=\s*["']([\w.-]+)["']""", b[:200])
        if m:
            self.codificacion_declarada = m.group(1).decode("ascii", "replace")

        try:
            b.decode("utf-8")
            self.codificacion = "utf-8"
            self.metodo_deteccion = (
                f"declaración declara {self.codificacion_declarada}"
                if self.codificacion_declarada else "decodificación estricta UTF-8 satisfactoria")
            return
        except UnicodeDecodeError:
            pass

        for enc in filter(None, (self.codificacion_declarada, *CANDIDATAS)):
            try:
                b.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
            self.codificacion = enc
            igual = enc.lower() == (self.codificacion_declarada or "").lower()
            self.metodo_deteccion = f"UTF-8 falló; '{enc}' decodifica" + (" (= declaración XML)" if igual else "")
            return

        self.codificacion = "cp437"
        self.metodo_deteccion = "respaldo: cp437 (mapea los 256 valores de byte)"

    def cargar(self):
        """Detecta codificación, sanea en memoria y parsea. Devuelve self."""
        self._detectar()
        texto = self.bruto.decode(self.codificacion, errors="replace")
        ctrl = CTRL_PROHIBIDOS.findall(texto)
        if ctrl:
            self.bytes_control = {f"0x{ord(c):02X}": n
                                 for c, n in sorted(collections.Counter(ctrl).items())}
            self.requiere_saneo = True
            texto = CTRL_PROHIBIDOS.sub("", texto)
        try:
            self.raiz = ET.fromstring(texto)
        except ET.ParseError as e:
            self.error = f"XML mal formado: {e}"
        return self

    def secciones(self):
        """{tag: [entradas]} conservando el orden del documento."""
        if self.raiz is None:
            return {}
        out = {}
        for hijo in self.raiz:
            out.setdefault(hijo.tag, []).extend(list(hijo))
        return out

    def resumen(self):
        secs = self.secciones()
        return {
            "ruta": self.path,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "raiz": None if self.raiz is None else self.raiz.tag,
            "codificacion_detectada": self.codificacion,
            "metodo_deteccion": self.metodo_deteccion,
            "codificacion_declarada": self.codificacion_declarada,
            "bom": self.bom or "ninguno",
            "bytes_control_encontrados": self.bytes_control or {},
            "requiere_saneo_memoria": self.requiere_saneo,
            "error": self.error,
            "total_entradas": sum(len(v) for v in secs.values()),
            "entradas_por_seccion": {k: len(v) for k, v in secs.items()},
        }


def id_de_entrada(elemento, seccion=None):
    """Devuelve (record_id, df_id_o_None, certainty).

    Prioriza el `<id>` de Dwarf Fortress. Sin él, deriva un ID determinista
    del contenido (mismo contenido -> mismo ID, siempre).
    """
    el = elemento.find("id")
    if el is not None and el.text and el.text.strip():
        v = el.text.strip()
        return (f"{seccion}:{v}" if seccion else v), v, FACT
    crudo = ET.tostring(elemento, encoding="utf-8")
    h = hashlib.sha256(crudo).hexdigest()[:16]
    return f"{seccion or 'sec'}:derived:{h}", None, DERIVED


def cargar_legends(path):
    """Atajo: lee, detecta y parsea un export de Legends."""
    return ResultadoLectura(path).cargar()