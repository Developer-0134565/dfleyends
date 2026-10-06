# Auditoría inicial :: Puente entre núcleo y contrato de IA

> Fase previa a `ai_knowledge_bridge_report.md`. Este documento es lo que se
> encontró **antes** de escribir una línea de código, ejecutando el contrato
> real y no leyéndolo.

## 1. Qué se pidió y qué había

El encargo describe una frontera entre el núcleo y el contrato de IA que
"todavía no está conectada al núcleo". La auditoría confirma la mitad de esa
afirmación y desmiente la otra:

| Pieza | Estado encontrado |
|---|---|
| `dfchron/contrato_ia.py` | **Existe y está completo.** 4 fuentes, 3 dimensiones, política de divulgación, conversiones justificadas |
| `dfchron/pruebas/probar_contrato_ia.py` | **Existe.** 44 pruebas, todas verdes |
| `AI_PROJECT_CONTEXT.md` / `ai_data_contract.md` | Documentan el contrato; se declaran «implementado y probado» |
| Adaptador núcleo → conocimiento | **No existe.** `WORLD_KNOWLEDGE` estaba definido pero sin conectar |
| `puede_usarse_para_razonar` | **No existe** |
| `preparar_respuesta_jugador` | **No existe** |
| Inmutabilidad de `Afirmacion` | **No existe, y es un agujero real** (ver §3) |

Es decir: el contrato estaba escrito y probado; **la conexión con el núcleo
nunca se hizo**. Que es exactamente el objetivo del encargo.

## 2. Estado del dataset (comprobado, no supuesto)

| Dato | Valor | Origen |
|---|---|---|
| `dataset_id` | `v1-04170363943d4ba1` | `00_SOURCE/dataset_version.json` |
| Hash de `legends.xml` | `77db4739c4064911…` | snapshot antes de la misión |
| Hash de `legends_plus.xml` | `fb6be93dac3e878b…` | snapshot antes de la misión |
| Archivos protegidos | 58 (2 XML + 56 JSONL) | `_hashes_antes_bridge.txt` |
| Figuras / sitios / entidades | 11.144 / 734 / 1.067 | fixtures de `validar_semantica.py` |
| Eventos | 57.215 | idem |

## 3. Hallazgo grave: `Afirmacion` era un `dict` mutable

Comprobado **ejecutando**, no leyendo el código:

```
=== 1. FACT + PLAYER_HIDDEN + FORBIDDEN ===
puede_revelarse            : False
puede_afirmarse_como_hecho: False

=== 2. ¿Se puede mutar la afirmación en silencio? ===
a["visibility"] = c.PLAYER_VISIBLE
a["disclosure"] = c.ALLOWED
MUTACIÓN POSIBLE (FALLO DE SEGURIDAD)
  -> puede_revelarse ahora: True
  -> puede_afirmarse_como_hecho: True
```

Una veta de diamantes con sus coordenadas —verdadera, oculta y prohibida— se
convertía en divulgable con dos líneas, sin dejar rastro y sin que nada lo
decidiera. Esto es exactamente el fallo que el encargo prohíbe en §17, y ya
existía antes de esta misión.

**Causa**: `Afirmacion(dict)` con `__slots__ = ()`. Los `__slots__` no
impiden mutar un `dict`: solo impiden *añadir atributos*.

## 4. Discrepancias detectadas entre el encargo y el código existente

### 4.1 `CONDITIONAL` como valor de `truth_status` — **NO se aplica**

El encargo (§4) pide `truth_status ∈ {FACT, DERIVED, UNKNOWN, CONDITIONAL}`.
El contrato existente tiene:

```
TRUTH_STATUS = ('FACT', 'DERIVED', 'UNKNOWN', 'INTERPRETATION')
DISCLOSURES  = ('ALLOWED', 'FORBIDDEN', 'CONDITIONAL')
'CONDITIONAL' es estado:  False
'CONDITIONAL' es permiso: True
```

**Decisión: se conserva el diseño existente.** Una afirmación no es
"condicionalmente verdadera": o es verdad o no lo es. Lo que sí puede ser
condicional es el **permiso de decirla**. Invertirlo obligaría a revisar las 44
pruebas del contrato y su documentación, para peor.

La *intención* del encargo —que `CONDITIONAL` nunca se convierta solo en un
hecho— sí queda garantizada, y por dos vías:
`puede_afirmarse_como_hecho()` devuelve `False` con `CONDITIONAL`
aunque `puede_revelarse()` devuelva `True`.

### 4.2 `truth_status` no incluye `INFERENCE` en la lista del encargo

El encargo no la menciona en §4, pero el contrato sí la tiene (alias de
`INTERPRETATION` del núcleo). Se conserva: sin ella no se puede representar
una inferencia, que el propio encargo exige en §7.

## 5. Lo que el núcleo ya hace bien (y no hay que duplicar)

Descubierto leyendo `nucleo.py` y ejecutándolo:

* **Fallar de forma segura ante identificadores hostility.** `ficha_figura`
  devuelve `{"certainty": "UNKNOWN", "motivo": "no existe esa figura"}` para
  `'abc'`, `-1`, `999999999`. No lanza. El adaptador hereda esta propiedad.
* **Declarar su propia certeza** en cada ficha, con `certainty` y `motivo`.
* **Marcar las ausencias.** `nacimiento` y `muerte` vienen como
  `{"año": null, "certainty": "UNKNOWN", "motivo": "… AUSENTE NO ES VIVA"}`.

Conclusión: el adaptador **no debe validar IDs**. Ya hay una capa que lo hace.

## 6. Salida de la auditoría

| | |
|---|---|
| Pruebas existentes antes de tocar nada | **382, todas verdes** |
| Contrato con agujero de mutabilidad | sí |
| Contrato sin puerta de razonamiento | sí |
| Adaptador al núcleo | no existía |
| Rutas `/api/ai` en la API | no existen (verificado en fuente y en servidor vivo) |

Se puede implementar sin tocar el núcleo, sin tocar los XML y sin tocar los
JSONL.