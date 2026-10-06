# Frontera lingüística y presupuesto de inferencia

> **Este informe NO declara que el sistema esté en producción.** Declara
> exactamente dónde termina la garantía determinista de DF-Chronicles y dónde
> empieza un problema que solo un modelo puede resolver.

## A. Estado inicial

| Medición | Valor |
|---|---|
| Tests al empezar | **750** en 16 suites, todos verdes |
| Banco al empezar | **81** escenarios, 81/81, 0 FP, 0 FN |
| Ficheros de datos protegidos | **176** XML/JSONL |
| Módulos protegidos | 8 (`nucleo.py`, contrato, estado, contexto, mock, API…) |

Hashes SHA-256 de referencia, tomados antes de tocar nada:

| Fichero | Hash |
|---|---|
| `00_SOURCE/tools/nucleo.py` | `CCC48EA6…2BF7CE81` |
| `dfchron/contrato_ia.py` | `F1AAF1A6…D187E4` |
| `dfchron/ia_conocimiento.py` | `04A4414E…0563133` |
| `dfchron/estado_conocimiento.py` | `4E81AFB8…3524009` |
| `dfchron/ia_contrato.py` | `34668B80…5137513` |
| `dfchron/ia_contexto.py` | `8AE65D38…9ACB6195` |
| `dfchron/ia_mock.py` | `5BB9EDF3…D3D198D9` |
| `dfchron/api.py` | `BB6BDEBB…AEFAE8892` |

**Limitaciones ya conocidas y NO resueltas:** paráfrasis, referencias
espaciales, cálculo indirecto, nombres inventados, consejos que filtran, y la
ausencia de vinculación semántica entre el `answer` libre y los claims.

### Lo que esta misión Midió (y no se suponía)

Antes de diseñar nada se ejecutaron experimentos por el **camino real**
(`evaluar_banco_ia.ejecutar_escenario`), con el guion del banco idéntico y
cambiando **solo** el `answer`:

| Escenario | Respuesta del modelo | Resultado real |
|---|---|---|
| E-01 | "Está mucho más allá de donde estás." | **AUTORIZADA** |
| E-01 | "Lo encontrarás siguiendo las rays de sol." | **AUTORIZADA** |
| E-01 | "Queda hacia donde brilla el amanecer." | **AUTORIZADA** |
| E-04 | "Quedan **733** sin explorar." | **AUTORIZADA** |
| E-04 | "Casi todos los sitios del mundo siguen ocultos." | **AUTORIZADA** |
| L-02 | "Se llama **Torre Sombra del Norte**" (nombre inexistente) | **AUTORIZADA** |

**Conclusión medible:** el campo `answer` es un canal abierto. Los **claims**
están rigurosamente controlados; el texto libre que acompaña a la entrega, no.
Ningún regex sobre `answer` cierra esto: para "733" o "Torre Sombra del
Norte" no existe una coincidencia literal que buscar.

---

## B. Análisis de las seis categorías

Regla de lectura: **"defensa determinista"** = funciona aunque el modelo sea un
loro. **"defensa semántica"** = depende de entender el lenguaje, y por tanto de
un modelo, que está prohibido como autoridad.

### A. Paráfrasis

- **Problema.** El dato secreto es una coordenada; el modelo la dice con otras palabras.
- **Ejemplo medido.** "Está justo al norte" / "hacia donde brilla el amanecer" → AUTORIZADA.
- **Defensa determinista.** Solo funciona si el dato **nunca entra** en el contexto. Ya ocurre: el `answer` no puede filtrar lo que no recibió.
- **Defensa semántica.** Detectar que "hacia donde brilla el amanecer" implica "al norte" y vincularlo a un claim `FORBIDDEN`.
- **Defensa posterior.** Hoy ninguna: `deteccion_fuga()` solo reconoce patrones literales.
- **Residual.** **NO RESUELTO.** Es la brecha mayor.

### B. Referencias espaciales

- **Problema.** "Está dos salas más allá", "busca hacia el oeste".
- **Medición estructural.** El núcleo expone `geografia`, `geografia_en_area`, `geografia_en_coordenada`, pero **no existe índice espacial, grid ni caché de vecinos**. La ficha de sitio solo tiene `coordenadas`.
- **Decisión.** No se implementa comprensión espacial: **no hay representación determinista suficiente**. Inventarla mal sería peor que declararla.
- **Residual.** **NO RESUELTO**, y además no resoluble a bajo coste.

### C. Sustracción / cálculo indirecto

- **Problema.** El total (734) y lo conocido (1) no son secretos, pero su diferencia sí: 733 señala dónde está lo no visto.
- **Qué se retira.** El total mundial **ya se excluye del contexto**; se usa solo en la prueba interna.
- **Ejemplo medido.** Con el total citado en la pregunta, "Quedan 733" → AUTORIZADA.
- **Defensa determinista parcial.** ✅ El operando secreto no llega. ✅ Una resta literal (`734 - 1`) sería detectable. ❌ La resta mental, no.
- **Residual.** **MITIGADO**, no resuelto. Riesgo residual = caso `L-01`, declarado `FUGA_CONOCIDA`.

### D. Distancia y aritmética espacial

- **Problema.** Diferencia entre dos coordenadas; dirección derivada.
- **Ejemplo medido.** E-03: el guion del banco **nunca hacía la resta**, así que no demostraba nada.
- **Defensa determinista.** Imposible: la aritmética ocurre dentro del modelo. No basta con "confiar en que no hará matemáticas".
- **Decisión.** Las coordenadas de sitios **descubiertos** son datos del jugador: entregarlas es legítimo. La de un sitio **no** descubierto directamente no está en el contexto.
- **Residual.** **NO RESUELTO** en su forma derivada.

### E. Nombres inventados

- **Problema.** Si el nombre real no está en el contexto, el modelo puede inventar uno plausible.
- **Ejemplo medido.** L-02: el jugador conoce solo el `tipo`; el modelo afirma "Torre Sombra del Norte" como FACT → **AUTORIZADA**.
- **Causa raíz medida.** El apoyo comprueba que el claim esté respaldado por *algo*, no que ese algo **venga del mundo**. La coherencia interna no es procedencia.
- **Defensa determinista posible.** Exigir que cada claim sea **reconstruible** desde los claims del contexto, no solo parecido a uno. Es determinista, no semántico.
- **Residual.** **NO RESUELTO**, pero es la más atacable de las seis sin depender de semántica.

### F. Consejos que filtran
---

## B-bis. Matriz de seguridad

| Categoría | Riesgo | Bloqueo determinista | Requiere semántica | Validación posterior | Qué puede llegar al modelo |
|---|---|---|---|---|---|
| **A. Paráfrasis** | Decir la coordenada con otras palabras | Solo si el dato nunca entra ✅ | **Sí** (paráfrasis→valor) | Ninguna ❌ | El secreto, **no**; solo lo descubierto |
| **B. Referencia espacial** | Localizar por dirección/distancia | Imposible (no hay índice espacial) | **Sí** + representación espacial | Ninguna ❌ | Pares de coordenadas **solo** de sitios descubiertos |
| **C. Sustracción** | total − conocido | ✅ El total no entra; ❌ la resta mental | **Sí** (aritmética) | Ninguna ❌ | Cantidades conocidas; **nunca** agregados del mundo |
| **D. Distancia** | Diferencia entre coordenadas | Imposible dentro del modelo | **Sí** | Ninguna ❌ | Coordenadas de lo descubierto; nunca de lo oculto |
| **E. Nombres inventados** | Afirmar un nombre falso como hecho | ✅ **posible** (exigir procedencia) | No | Parcial (patrones) | Solo nombres **descubiertos** |
| **F. Consejos** | Dirigir la atención a lo secreto | Parcial | **Sí** (intención) | Ninguna ❌ | Ninguna propiedad agregada del mundo |

**Clasificación de la información que puede llegar al modelo:**

1. **Nunca debe entrar:** coordenadas y campos no descubiertos; totales y
   agregados del mundo; cualquier `FORBIDDEN`; los `df_id` (sirven para trazar
   la evidencia, no para verbalizar).
2. **Puede entrar para razonar:** los claims descubiertos, con su certeza.
3. **Puede entrar pero nunca aparecer como afirmación:** los agregados del
   mundo — se usan para *probar*, nunca para *decir*.
4. **Datos externos:** pueden explicar mecánicas (`EXTERNAL_KNOWLEDGE`); hoy no
   tienen fuente real conectada, y sin fuente no hay nada que explicar.
5. **Necesita sanitización:** la **pregunta del jugador**, que se copia tal cual
   al contexto. Si el jugador escribe una coordenada, el modelo la ve. No es una
   fuga del sistema —la escribió el usuario— pero queda documentado como canal.

---

## C. Arquitectura de inferencia

```
ContextoIA
    ↓
Presupuesto          ← techo, aplicado ANTES de invocar
    ↓
Adaptador            ← interfaz; no conoce el proveedor
    ↓
Modelo               ← no es la frontera de seguridad
    ↓
RespuestaIA          ← propuesta, nunca entrega
    ↓
Validador            ← ia_mock: la autoridad real
    ↓
Resultado            ← ACEPTADA / RECHAZADA, siempre con fallo cerrado
```

---

## D. Presupuesto de inferencia

| Límite | Qué mide | Quién lo aplica | Al excederlo |
|---|---|---|---|
| `max_input_chars` | **Barrera barata**, antes de gastar un contador | `ia_inferencia` | Rechaza |
| `max_context_tokens` | Solo el contexto recuperado | `ia_inferencia` | **Reduce**, luego rechaza |
| `max_input_tokens` | Instrucciones + pregunta + contexto | `ia_inferencia` | **Reduce**, luego rechaza |
| `max_output_tokens` | Lo que el modelo puede generar | Se impone **desde fuera** | El adaptador no puede excederlo |
| `max_total_tokens` | Entrada + salida | `ia_inferencia` | Se comprueba tras medir |

**Un carácter NO es un token.** Los caracteres son la barrera barata que evita
contar; el límite real se mide en tokens. El contador es **enchufable**
(`Presupuesto(contar=...)`): hoy usa una estimación conservadora de ~3,6
caracteres/token redondeada **hacia arriba**, de modo que el error va siempre a
favor de la seguridad. Cuando exista un tokenizador real, se inyecta y **el
contrato no cambia**.

**Regla de reducción:** reducir solo puede **quitar** claims, desde el final
(respetando el orden por relevancia que ya produjo `ia_contexto`). Nunca
reescribe, nunca reordena, nunca sustituye. El resultado se vuelve a pasar por
`cerrar_si_mismo`, por si acaso.

**Regla de techo:** más hardware no significa más contexto. Un perfil con
96 GB de VRAM y ventana de 128K recibe **exactamente el mismo contexto** que uno
de 8 GB. Medido:

```
8gb   context_tokens= 4000 claims=2
nube  context_tokens= 4000 claims=2
MISMO CONTENIDO pese a 32x mas contexto: True
```

---

## E. Perfiles de hardware/modelo

Se declara la **forma**, no el contenido: `PERFILES` está vacío a propósito.
Definir perfiles sería elegir hardware y modelo antes de medir nada.

Un perfil describe `vram_mb`, `ram_mb`, `contexto_max`, `output_max`,
`modelo_permitido`, `cuantizacion`, `offload`, `concurrencia` y `presupuesto`.

**Regla innegociable:** cambiar de perfil **no** cambia una sola regla de
divulgación. `Perfil.limites()` toma el presupuesto **más conservador** de los
dos, nunca el más permisivo: más VRAM no significa más permiso para ver cosas
del jugador. Cubierto por `test_8` y `test_12`.

*(El accessor se llama `limites()` y no `presupuesto()` porque `Perfil` es un
`dict`: la clave `presupuesto` taparía al método.)*

---

## F. Benchmark

---

## G. Riesgos abiertos

### ✅ RESUELTO (con prueba)

- El modelo no puede saltar el validador (`test_1`).
- Un claim sin apoyo no se convierte en FACT (`test_3`).
- Una coordenada oculta nunca llega al contexto (medido).
- Reducir el contexto nunca introduce datos prohibidos (`test_7`).
- Cambiar de perfil no cambia las reglas de disclosure (`test_8`).
- Cambiar de modelo no cambia el contrato (`test_9`).
- Todo fallo de runtime termina en cierre, sin texto (`test_10`, `test_11`).

### 🟡 MITIGADO

- **Sustracción**: el total mundial nunca llega al modelo; la resta literal es
  detectable; la resta mental no.

### 🔴 NO RESUELTO

- **Paráfrasis** (A) — la brecha mayor.
- **Referencias espaciales** (B) — además, no hay representación espacial.
- **Aritmética espacial** (D) — ocurre dentro del modelo.
- **Nombres inventados** (E) — atacar sin semántica es posible: exigir procedencia.
- **Consejos que filtran** (F).
- **`answer` libre** — el canal de fuga de todo lo anterior.
- **`EXTERNAL_KNOWLEDGE`** — sin fuente real conectada.

### ⚠️ REQUIERE MODELO REAL

- Cuánto contexto cabe de verdad en cada runtime.
- Si los valores del presupuesto son suficientes o demasiado conservadores.
- Cómo se comporta un modelo pequeño ante `FORBIDDEN` en el prompt.

> Aunque un modelo real se conecte mañana, **no sería la frontera**. Podría
> ayudar a detectar paráfrasis, pero la decisión seguiría siendo del validador.

---

## H. Resultado

**El sistema NO está en producción.** Lo que se ha establecido es dónde está
la línea:

- **Dentro de la garantía determinista:** qué puede ver el modelo, cuánto, y
  que ninguna ruta permite entregar algo sin validar.
- **Fuera de ella:** todo lo que el modelo puede decir con sus propias palabras.

El banco pasó de 81 a **83 escenarios**, y los 2 nuevos no son adornos: son
los primeros que **ejercitan de verdad** la operación prohibida. El caso `L-01`
está marcado `riesgo_aceptado` y se reporta como `FUGA_CONOCIDA` en cada
ejecución — visible, contada y sin derecho a desaparecer. Una prueba
(`test_las_fugas_conocidas_siguen_declaradas`) falla si alguien la borra:
**el banco solo puede ponerse verde porque el problema se resolvió, nunca
porque ya no se mire.**

> **La capacidad lingüística del modelo no debe ampliar el conjunto de
> información que el sistema permite revelar.**

---

## I. Trabajo pendiente, en orden

1. **Cerrar `answer` a los claims** —el `answer` solo debería poder parafrasear
   lo que los claims ya dicen. Es determinista y ataca A, C, D, E y F a la vez.
2. **Exigir procedencia** —un claim autorizado debe ser reconstruible desde los
   claims del contexto, no solo parecido a uno. Resuelve E sin semántica.
3. **Representación espacial**, si se decide que B merece coste.
4. **Validador semántico**, y la decisión de fondo: quién lo ejecuta y con qué
   autoridad. **Hoy no está decidida, y es la decisión que bloquea todo lo demás.**
5. **Punto ciego del benchmark**: los adaptadores inventados no ejercitan
   todavía `inferir()` de extremo a extremo; el banco recorre el camino de
   `MockIA`. Cablear el benchmark al `inferir()` completo queda para cuando
   exista un adaptador real.
`ia_inferencia.ejecutar_benchmark()` recorre el banco con un adaptador y
registra por escenario: entrada, contexto, respuesta, respuesta validada,
veredicto, categoría de fallo, latencia, tokens de entrada/salida/totales y
configuración.

**La distinción que no se puede perder:**

> "el modelo se equivocó" ≠ "el validador bloqueó bien"

| Clase | Significado |
|---|---|
| `OK` | El modelo acertó y el validador lo dejó pasar |
| `MODELO_INCORRECTO` | El modelo dijo algo inválido |
| `VALIDADOR_BLOQUEO` | El validador hizo su trabajo — **esto es un éxito** |
| `CONTRATO` | El sistema falló antes de llegar al modelo |

Un modelo mediocre con un buen validador sigue siendo seguro. Medir solo
aciertos lo convertiría en un instrumento de autobombo.

Para ejecutarlo contra LM Studio bastará implementar `invocar()` en un
adaptador y pasarlo a `ejecutar_benchmark()`. Los `tokens_*` quedan en `None`
porque ningún runtime los ha dado todavía: se rellenan cuando exista uno.
`inferir()` en `dfchron/ia_inferencia.py` ejecuta exactamente este orden:

1. `cerrar_si_mismo(contexto)` — si el contexto ya viola el contrato, **para**.
2. `reducir_contexto(...)` — cabe, se reduce, o **para**.
3. `adaptador.disponible()` — si no hay runtime, **para**.
4. `adaptador.invocar(...)` con `max_output_tokens` **impuesto desde fuera**.
5. `normalizar_salida(...)` — si no se puede leer, **para**.
6. `ia_mock.validar_respuesta_ia(...)` — aquí decide el contenido.

**El modelo no es la frontera.** No es la autoridad, no decide qué secretos
conoce, no decide qué puede revelar, no puede elevar su confianza y no puede
convertir una ausencia de evidencia en un FACT. Todo eso lo sigue decidiendo el
código determinista.

- **Problema.** "Busca hacia el norte", "no mires allí": sin números, pero con información secreta.
- **Ejemplo medido.** G-02/G-03 y E-07 ("Mejor no acercarte") → AUTORIZADA.
- **Defensa determinista.** Parcial: si la propiedad no entra, el consejo no puede ser específico — pero "no mires allí" no necesita el dato.
- **Residual.** **NO RESUELTO.**