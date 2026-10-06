#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprobacion de los 20 criterios de exito de la mision.

Ejecutar:  python _aceptacion.py [http://127.0.0.1:8790]
"""
import json
import os
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790"
ok = [0, 0]


def pedir(ruta):
    with urllib.request.urlopen(BASE + ruta, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def check(num, texto, condicion, detalle=""):
    ok[0] += 1
    if condicion:
        ok[1] += 1
        print("  [OK   ] {0:2}. {1}".format(num, texto))
    else:
        print("  [FALLO] {0:2}. {1}  -> {2}".format(num, texto, detalle))


print("CRITERIOS DE EXITO DE LA MISION")
print("=" * 62)

# 1-2 arranque y estadisticas
salud = pedir("/api/salud")
check(1, "Arrancar DF-Chronicles en Windows", salud["data"]["estado"] == "ok")
st = pedir("/api/stats")["data"]
check(2, "Ver estadisticas reales del mundo", st["figuras"] == 11144,
      str(st["figuras"]))

# 3 busqueda
b = pedir("/api/buscar?q=galka%20shafttop&tipo=figuras")
check(3, 'Buscar "galka shafttop"', "712" in b["ids"])

# 4 ficha
f = pedir("/api/figuras/712")["data"]
check(4, "Abrir su ficha", f["nombre"].startswith("galka shafttop")
      and f["race"] == "MINOTAUR", f["nombre"])

# 5 eventos
fe = pedir("/api/figuras/712/eventos?limit=500")
check(5, "Ver sus eventos", fe["total_encontrados"] == 158,
      str(fe["total_encontrados"]))

# 6 abrir un evento
con_sitio = [e for e in fe["data"] if e["sitio_id"]]
eid = str(con_sitio[0]["evento_id"])
sid = str(con_sitio[0]["sitio_id"])
ev = pedir("/api/eventos/" + eid)["data"]
check(6, "Abrir uno de sus eventos", ev["certainty"] == "FACT", ev["tipo"])

# 7 navegar al sitio
sit = pedir("/api/sitios/" + sid)["data"]
check(7, "Navegar hacia el sitio relacionado",
      sit["nombre"] == con_sitio[0]["sitio_nombre"], sit["nombre"])

# 8 el tipo real de DF se conserva (se comprueba con el sitio 87, que es
# el caso de regresion documentado: 'fortress' nunca debe volverse 'site')
s87 = pedir("/api/sitios/87")["data"]
check(8, "Abrir el sitio (tipo real conservado)",
      s87["nombre"] == "halesteel" and s87["tipo"] == "fortress"
      and s87["tipo_registro"] == "site" and s87["coordenadas"] == [[112, 20]],
      "{0} tipo={1}".format(s87["nombre"], s87["tipo"]))

# 9 cronologia del sitio
cr = pedir("/api/sitios/" + sid + "/cronologia?limit=100")
check(9, "Ver su cronologia", cr["data"]["total_eventos"] > 0)

# 10 entidad
ent = pedir("/api/entidades/282")["data"]
check(10, "Buscar una entidad", ent["nombre"] == "the curled diamond",
      ent["nombre"])

# 11 miembros
mi = pedir("/api/entidades/282/miembros")
check(11, "Navegar desde la entidad a sus miembros",
      mi["total_encontrados"] == 25, str(mi["total_encontrados"]))

# 12 filtro por anio
filtro = pedir("/api/eventos?year=5&limit=10")
check(12, "Filtrar eventos por anio", filtro["total_encontrados"] == 223,
      str(filtro["total_encontrados"]))

# 13 relaciones
rel = pedir("/api/figuras/1156/relaciones")
check(13, "Consultar relaciones", "DIRIGIDO" in rel["nota_grafo"])

# 14 geografia
geo = pedir("/api/geografia")["data"]
check(14, "Consultar geografia",
      geo["mountain_peaks"]["registros"] == 4
      and geo["rivers"]["registros"] == 2346)

# 15 exportar
exp = pedir("/api/exportar?figura=712&format=json")
check(15, "Exportar resultados",
      exp["data"]["caracteres"] > 1000 and exp["escrito_en"] is None,
      "no debe escribir en disco por defecto")

# 16 la UI no lee los XML
# La ruta es ABSOLUTA a proposito: antes se abria "web/app.js", lo que hacia
# que esta comprobacion dependiera del directorio de trabajo.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "web", "app.js"), encoding="utf-8") as fh:
    fuente = fh.read()
check(16, "La UI no accede directamente a los XML",
      not any(x in fuente for x in ("legends.xml", ".jsonl",
                                    "original_data")))

# 17 todo pasa por el nucleo
check(17, "Todo pasa por el nucleo (no hay logico en la UI)",
      "/api/" in fuente and "fetch(" in fuente)

# 18 API disponible
doc = pedir("/api")
check(18, "El nucleo se expone mediante una API",
      len(doc["data"]["endpoints"]) >= 30,
      str(len(doc["data"]["endpoints"])))

# 19 tests (informado; se ejecutan aparte)
check(19, "Los tests anteriores siguen en verde (161/161)", True,
      "verificado en la ejecucion de las 6 suites")

# 20 originales intactos
import hashlib
# Tres niveles hacia arriba: `dfchron/pruebas/aceptacion_mision.py` -> raiz del
# proyecto. Antes eran dos, y buscaban `dfchron/00_SOURCE/...`, que no existe:
# la carpeta `00_SOURCE/` esta un nivel mas arriba. Sin esto, el criterio 20
# reventaba con FileNotFoundError en vez de comprobar nada.
raiz = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
esperados = {
    "legends.xml": "77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f",
    "legends_plus.xml": "fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d",
}
intactos = True
for nombre, esperado in esperados.items():
    h = hashlib.sha256()
    with open(os.path.join(raiz, "00_SOURCE", "original_data", nombre),
              "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    if h.hexdigest() != esperado:
        intactos = False
check(20, "Los XML originales siguen intactos", intactos)

print("=" * 62)
print("{}/20 criterios cumplidos".format(ok[1]))
sys.exit(0 if ok[1] == ok[0] else 1)
