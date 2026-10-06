# Reproducibilidad del dataset

Cómo reconstruir DF-Chronicles desde cero, y comprobación de que el resultado
coincide con el dataset actual.

---

## 1. Archivos necesarios

**Insuficientes (solo con esto no se reconstruye):**

```
00_SOURCE/tools/cargar_legends.py
00_SOURCE/tools/integrar_legends.py
00_SOURCE/tools/validar_semantica.py
00_SOURCE/tools/nucleo.py
```

**Necesarios y suficientes:**

| # | Archivo | Bytes | SHA-256 |
|---|---|---:|---|
| 1 | `00_SOURCE/original_data/legends.xml` | 49.223.702 | `77db4739c4064911cdd6a94fd68d5b3cefcbfdbc5a4459d7495ca63985a4681f` |
| 2 | `00_SOURCE/original_data/legends_plus.xml` | 17.664.819 | `fb6be93dac3e878b36eb5bdd47bfe288b66d682fda30023ba9538e81194abc2d` |

Con esos dos ficheros y las cuatro herramientas, el pipeline se reconstruye
íntegramente. Nada más es necesario.

**No intervienen:**
- `world.sav` (pertenece al camino `extraction/`, no al núcleo).
- `processed/validation/` (fixtures de Fase 2, solo para pruebas).
- Los `.md` y `.json` de informe.

---

## 2. Las seis etapas

| # | Etapa | Comando | Entrada | Salida |
|---|---|---|---|---|
| 1 | **Extracción** | (ya hecha por DF) | juego en marcha | los dos XML |
| 2 | **Carga** | `cargar_legends.py` | los 2 XML | árbol ElementTree |
| 3 | **Normalización + merge** | `integrar_legends.py` | los 2 XML | `processed/` |
| 4 | **Validación semántica** | `validar_semantica.py` | `processed/` | estadísticas + fixtures |
| 5 | **Índice** | (automático) | `processed/merged/` | índice en memoria |
| 6 | **Pruebas** | `probar_nucleo.py` etc. | todo | 68 pruebas |

### Detalle

**Etapa 2 — carga.** Detecta la codificación sin valores hardcodeados:
BOM → UTF-8 estricto → declaración XML → cascada → CP437. Elimina los bytes de
control (`0x00-0x08`, `0x0b`, `0x0c`, `0x0e-0x1f`) **en memoria**.

**Etapa 3 — normalización.** Vuelca cada sección a JSONL con `certainty`,
`source` y `source_section` por campo. Aplica las reglas de merge (primaria
gana, vacío de plus no pisa, divergencias se conservan ambas). **Copia los XML
a `original_data/` de forma idempotente**: si ya existen, compara hashes y no
sobrescribe.

**Etapa 4 — validación.** Construye el índice de referencias cruzadas y verifica
que no haya enlaces rotos. **No escribe en `merged/`**: solo en
`processed/validation/`.

**Etapa 5 — índice.** Ocurre al instanciar `Archivo()`. Los índices se
normalizan a **texto** porque `df_id` es cadena en los JSONL.

**Etapa 6 — pruebas.** 20 de integración + 48 del núcleo + determinismo.

---

## 3. Verificación ejecutada

`verificar_reproducibilidad.py` reconstruye el pipeline **en un directorio
temporal**, importando `integrar_legends.py` y sobrescribiendo sus constantes
de ruta (sin editar el fichero).

Resultado obtenido:

```
1) Fingerprint del dataset ACTUAL
   historical_figures                    11,144 líneas  da400a37a7dd0b11
   entities                               1,067 líneas  b28665231259c1f3
   sites                                    734 líneas  53e5ec2da985fedb
   historical_events                     57,215 líneas  07204f1b3cfaf227
   artifacts                                427 líneas  8741133d84746ea4
   historical_event_relationships        13,192 líneas  43274e917ef9689e
   historical_event_relationship_supplements  21 líneas  c60a93188e1c1bf8
   historical_event_collections            6,544 líneas  1b9a8593e2548b08
   historical_eras                            1 línea   f4673c02c255424b

4) Comparación dataset actual vs reconstruido
   9/9 secciones byte-identicas

5) Los XML originales siguen intactos
   [OK] legends.xml          77db4739c4064911cdd6
   [OK] legends_plus.xml     fb6be93dac3e878b36eb

RESULTADO: REPRODUCIBLE desde los XML originales
```

El directorio temporal se elimina al terminar. **El dataset funcional no se
borra ni se toca.**

Para repetirlo:

```bash
cd "DF-Chronicles\00_SOURCE\tools"
python verificar_reproducibilidad.py
```

---

## 4. Garantías de la reconstrucción

| Garantía | Cómo se consigue |
|---|---|
| Determinista | Ordenación explícita por clave; sin dependencia de `set`/`dict` no ordenados |
| No toca los originales | `registrar_original()` compara hashes y nunca sobrescribe |
| Reproducible | Verificado: 9/9 secciones byte-idénticas |
| Sin dependencias | Solo biblioteca estándar de Python 3 |

**Qué NO afecta al resultado:** `PYTHONHASHSEED`, la hora, el orden del
filesystem y las ejecuciones anteriores. Verificado en `test_determinismo.py`
con 4 procesos y semillas distintas.

---

## 5. Reconstruir desde cero

```python
# 1. Copiar los dos XML a original_data/  (el script lo hace solo)
# 2. Ejecutar la integración
import sys
sys.path.insert(0, r"...\00_SOURCE\tools")
import integrar_legends as IL
IL.integrar()          # lee los XML, escribe processed/

# 3. Usar el núcleo
from nucleo import Archivo
a = Archivo()          # construye el índice
a.ficha_figura("712")
```

Tiempo aproximado: **~2 min** para la integración de 47 MB, **~2,1 s** para
cargar el índice.

---

## 6. Si los XML cambian

1. Se copian a `original_data/` **solo si no existen**; si existen con distinto
   hash, el script lo avisa y conserva la copia.
2. `integrar_legends.py` vuelve a procesarlos.
3. `validar_semantica.py` regenera estadísticas y fixtures.
4. Las pruebas verifican si los conteos esperados siguen valiendo.

**Los conteos esperados de las pruebas están fijos** (11.144 figuras, 57.215
eventos…). Con otro mundo, fallarían: es intencional, obliga a reauditar.