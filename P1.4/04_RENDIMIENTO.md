# P1.4 — RENDIMIENTO (Fase F)

> Métricas **medidas**, no estimadas. Lo que no se ha medido se dice como no
> medido, nunca se rellena.

---

## 1. Coste de una observación

Medido con 5 ejecuciones completas desde PowerShell:

| Medición | Valor |
|---|---:|
| Ida y vuelta **sin** observar (`print('hola')`) | **53 ms** |
| Ida y vuelta **con** observador completo (13 hechos) | **60 ms** (media de 5) |
| **Coste real atribuible al observador** | **≈ 7 ms** |
| Tamaño del JSONL | 7144 B por 13 observaciones |
| Tamaño medio por observación | ≈ 550 B |

**Lectura:** de esos 60 ms, 53 son el coste de arrancar el proceso y hablar por
el socket. El trabajo real de leer 13 hechos del juego y escribirlos es de
**~7 ms**. El observador no es el cuello de botella: el launching lo es.

---

## 2. Frecuencia sostenible

| Escenario | Frecuencia viable | Coste |
|---|---:|---|
| Bajo demanda (pulsar «Actualizar») | 1 cada pocos segundos | ~7 ms de trabajo |
| Periódica | 1/seg | ~0,7 % de un núcleo |
| Periódica | 1/5 s | ~0,14 % de un núcleo |
| Basada en eventos (`eventful`) | por evento | despreciable |

**Conclusión: la frecuencia NO es el problema.** Un sondeo de 1 Hz costaría
menos del 1 % de un núcleo. Cualquier architectura periódica es viable.

---

## 3. Comportamiento con el juego en marcha

| Condición | Medido |
|---|---|
| Partida **pausada** | Sí — 4 ejecuciones, tick constante, ~60 ms |
| Partida **en marcha** | **NO MEDIDO** — requiere tu autorización para pausar/despausar |
| CPU atribuible al script | **NO MEDIDO** con precisión (requeriría instrumentación invasiva) |

> El proceso de DF consumía CPU de forma apreciable durante la sesión
> (2207 s → 2919 s acumulados), pero **eso es el juego, no el observador**. No se
> puede atribuir sin instrumentación, y no se afirma nada que no se haya medido.

---

## 4. Qué condiciona el diseño futuro

Como el coste marginal es de ~7 ms, la decisión de arquitectura **no debe
tomarse por rendimiento**. Las razones reales para preferir una opción u otra
son de otro tipo:

| Opción | Cuándo tiene sentido |
|---|---|
| **Bajo demanda** | La Web lo pide al abrir o al pulsar «Actualizar». Coste cero en reposo |
| **Periódica** | Quien quiera ver el ticked actualizar sin pedirlo |
| **Basada en eventos** | Want *solo* cuando algo cambia de verdad (una muerte, una llegada). Menos ruido |
| **Híbrida** | Lo más razonable: eventos para el estado, bajo demanda para el resto |

**Recomendación: híbrida**, empezada por **bajo demanda**, que es la más simple
y ya está demostrada. La periodicidad no aporta nada hasta que haya UI en vivo.

---

## 5. Coste de la conversión pendiente

La tabla CP437→UTF-8 pendiente (ver `01_INVENTARIO_VISIBILIDAD.md`) se calcula
**una vez** al inicio, no por observación. Su coste es despreciable y no cambia
ninguna de estas conclusiones.