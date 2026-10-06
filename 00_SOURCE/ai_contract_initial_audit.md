# DF Legends · Auditoría inicial del contrato de IA

Inspección hecha **antes de escribir una línea** de código. Toda afirmación de
aquí procede de leer el fichero o de ejecutarlo.

---

## 1. Dónde están realmente los contratos

La misión los sitúa en la raíz. **No están ahí.** Busqué por nombre y por
contenido en todo el repositorio:

| Fichero | Ruta real | Tamaño |
|---|---|---|
| `AI_PROJECT_CONTEXT.md` | `08_DATABASE/AI_PROJECT_CONTEXT.md` | 192 líneas |
| `ai_data_contract.md` | `08_DATABASE/ai_data_contract.md` | 197 líneas |

No se han creado de cero: **ya existían** y ya definían casi todo lo que pide
la misión. Eso cambia el enfoque: el trabajo es **completar y reparar**, no
diseñar desde el principio.

## 2. Qué define ya el contrato anterior

### `AI_PROJECT_CONTEXT.md`

| Ya definido | Contenido |
|---|---|
| Las 4 fuentes | `PLAYER_KNOWLEDGE`, `WORLD_KNOWLEDGE`, `EXTERNAL_KNOWLEDGE`, `INFERENCE` |
| Las 3 dimensiones | `truth_status`, `visibility`, `disclosure` |
| La regla dura | «**`FACT` no es permiso para revelar**» |
| Ejemplo canónico | `{"truth_status": "FACT", "visibility": "PLAYER_HIDDEN", "disclosure": "FORBIDDEN"}` |
| 10 prohibiciones | De generar crónicas a rellenar `UNKNOWN` |
| 11 condiciones de aceptación | Para que una IA futura sea admisible |
| 6 riesgos con su mitigación | Tabla de riesgos |

### `ai_data_contract.md`

| Ya definido | Contenido |
|---|---|
| Flujo de acceso | XML → normalizar → validar → núcleo → **capa de contexto** → modelo |
| Qué NO puede ver la IA | 6 recursos excluidos, con motivo |
| Formato de evidencia | 6 campos obligatorios + 3 ejemplos reales |
| 10 reglas de redacción | Incluida «`UNKNOWN` es una respuesta válida» |
| Contexto fijo | 7 limitaciones que el modelo siempre recibe |
| Separación datos/narrativa | Qué capa es responsable de qué |

**Conclusión:** el diseño conceptual de la misión ya existía como
documentación. Lo que **no** existía era:

1. **Nada ejecutable.** Ninguna de las cuatro fuentes, ni `visibility`, ni
   `disclosure` está en el código. Solo están escritas.
2. **Pruebas.** Ninguna comprobaba que un `PLAYER_HIDDEN` no se revele.
3. **Reparar los documentos**, que están dañados (§4).

## 3. Estado real del código

### Lo que sí está implementado

`validar_semantica.py` declara cuatro constantes (líneas 44–47):

```python
FACT = "FACT"
DERIVED = "DERIVED"
INTERPRETATION = "INTERPRETATION"
UNKNOWN = "UNKNOWN"
```

`INTERPRETATION` existe pero **no se usa**: solo aparece en comentarios y en
`integrar_legends.py:401` con el texto *"no se genera en esta fase"*. Es una
constante reservada, y encaja con `INFERENCE` de la misión.

El envelope de `servicio.py` lleva la certeza en **tres sitios** a la vez
(`envolver_ficha`):

```python
return {"ok": True, "data": datos, "status": cert, "certainty": cert,
        "meta": {..., "certainty": cert}, **extra}
```

Es redundante a propósito: permite leerla desde donde toque.

### Lo que NO existe en el código

Búsqueda de `visibility`, `disclosure`, `PLAYER_HIDDEN`, `WORLD_KNOWLEDGE`
en `dfchron/*.py` y `00_SOURCE/tools/*.py`:

```
NINGUN RESULTADO
```

Es decir: **la política de divulgación está escrita pero no implementada**.
Una IA futura que se apoyara solo en el código actual podría leer un `FACT`
de `WORLD_KNOWLEDGE` y llamarlo verdad revelable, porque no hay nada que se
lo impida. Ese es exactamente el riesgo que la misión quiere cerrar.

### Lo que hay que mantener intacto

| No tocar | Motivo |
|---|---|
| `nucleo.py` | Ya declara su certeza; la capa nueva va **encima** |
| Los XML | Datos originales protegidos |
| Los JSONL | Datos originales protegidos |
| La API | 54 pruebas dependen de su contrato |
| La Web | Sin cambios de comportamiento (§13, §24) |

## 4. Un defecto encontrado en los contratos existentes

Al leerlos completos encontré que **ambos documentos tienen texto desplazado**.
No es un problema de formato: hay frases partidas y bloques fuera de sitio.

### `AI_PROJECT_CONTEXT.md`

La frase que cierra la regla dura aparece partida en dos puntos:

- **Línea 76**, empieza y se corta: `**Antes de que el modelo escriba una frase, el sistema debe decidir si esa`
- **Línea 191**, en el final del archivo: `frase puede decirse.** La verdad no basta.`

Las líneas 77–190 (ocho secciones enteras) están intercaladas dentro de esa
frase.

### `ai_data_contract.md`

- El bloque `### Caso DERIVED` (línea 106) **se corta** en `"funcion": "nucleo.Archivo.conflictos",` y **no se cierra**.
- Las secciones 5 a 8 enteras van en medio.
- El JSON continúa en las **líneas 179–183**, ya dentro de la lista de
  verificación, y allí sí se cierra.
- `### Caso UNKNOWN` (líneas 185–197) queda fuera, y el archivo **termina con
  una valla ``` sin cerrar** de más.

Comprobado con un script: el número de vallas ``` es par en ambos ficheros, y
las 8 secciones están en orden. El daño está **dentro** de los bloques de texto,
no en la estructura de títulos.

**Consecuencia práctica:** quien lea estos documentos tal como están recibe un
contrato mal formado. La regla más importante —«`FACT` no es permiso para
revelar»— es precisamente una de las frases partidas.

**Se reparan** en esta misión, dejando constancia en el informe.

## 5. Puntos de integración posibles

La capa nueva debe ir **por encima** del núcleo, sin tocarlo:

```
nucleo.py / servicio.py        ← NO se modifica
        ↓  certeza ya calculada (FACT/DERIVED/UNKNOWN)
+------------------------------------------------+
|  dfchron/contrato_ia.py       ← NUEVO           |
|  · las 4 fuentes de conocimiento               |
|  · las 3 dimensiones                           |
|  · la politica de divulgacion                   |
|  · validacion de combinaciones                  |
+------------------------------------------------+
        ↓
   futura IA  (NO existe)
```

Por qué aquí y no en otro sitio:

| Opción | Por qué no |
|---|---|
| Dentro de `nucleo.py` | Prohibido por §17; además el núcleo no conoce al jugador |
| En la API | Expondría la política a los clientes; §14 lo prohíbe |
| En la Web | La Web no debe decidir qué se revela (§13) |
| **`dfchron/contrato_ia.py`** | **Encima del servicio, sin dependencias, importable por quien haga falta** |

El contrato no se instancia ni se conecta a nada: solo define y valida.

## 6. Riesgos

| Riesgo | Mitigación prevista |
|---|---|
| Que `FACT` se lea como permiso de revelar | Implementar la comprobación, no solo escribirla |
| Que `UNKNOWN` se rellene | Prohibición explícita y prueba que lo compruebe |
| Que `INFERENCE` suba a `FACT` | `truth_status` y `knowledge_source` son campos separados e independientes |
| Que `EXTERNAL` se presente como estado del mundo | `EXTERNAL` no acepta `df_id` ni coordenadas de esta partida |
| Que el contrato crezca sin control | Valores cerrados y validación de combinaciones |
| Que «preparar la IA» acabe siendo una IA | No se instancia nada; la suite lo comprueba |

El punto que más riesgo lleva es el primero: **la distinción está escrita desde
hace tiempo y sigue sin código**. Por eso el valor de esta misión es
implementarla, no describirla otra vez.

## 7. Hashes (antes)

| Recurso | SHA-256 |
|---|---|
| `legends.xml` | `77DB4739C4064911CDD6A94FD68D5B3CEFCBFDBC5A4459D7495CA63985A4681F` |
| `legends_plus.xml` | `FB6BE93DAC3E878B36EB5BDD47BFE288B66D682FDA30023BA9538E81194ABC2D` |
| JSONL de `processed/` | 56 ficheros, manifiesto en `_hashes_antes_ia.txt` |