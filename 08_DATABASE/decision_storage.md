# ¿Necesitamos realmente una base de datos?

Evaluación técnica solicitada en la Fase 4 (punto 14). **No se ha implementado
ninguna migración.**

---

## 1. Mediciones reales

| Parámetro | Valor |
|---|---:|
| Registros totales indexados | 83.579 |
| Volumen en disco (JSONL) | ~173 MB |
| Tiempo de arranque | **2,1 s** |
| Memoria resident estimada | **~507 MiB** |
| Coste dominante | **parseo de JSONL**, no los índices |

### Rendimiento por tipo de consulta (100 iteraciones cada una)

| Consulta | Media |
|---|---:|
| Ficha de artefacto | 0,03 ms |
| Ficha de figura | 0,61 ms |
| Ficha de sitio | 0,75 ms |
| Cronología de figura | 0,04 ms |
| Miembros de entidad | <0,01 ms |
| Consulta geográfica | 0,23 ms |
| Búsqueda (pocas coincidencias) | 0,39 ms |
| **Búsqueda (262 coincidencias)** | **7,5 ms** |
| **Eventos de un año** | **30 ms** |
| **Eventos entre años** | **96 ms** |

---

## 2. Análisis

### A favor de seguir con JSONL + índice

1. **El arranque es aceptable.** 2,1 s para 83.579 registros. Si el modelo se
   carga una vez por sesión, es irrelevante.
2. **Las consultas habituales son sub-milisegundo.** Fichas, cronologías de
   figura, miembros y geografía responden en menos de 1 ms.
3. **El volumen no justifica una base de datos.** 83.579 filas caben de sobra
   en memoria. SQLite no sería «más rápido»: el coste está en leer y
   deserializar el JSON, que es lo mismo.
4. **Transparencia total.** El JSONL se puede inspeccionar con cualquier
   editor. Para auditar datos, el formato legible gana a un binario.
5. **Reproducibilidad ya demostrada.** 9/9 secciones byte-idénticas al
   reconstruir. Una base de datos añadiría un estado que no se puede diffear.
6. **Cero dependencias.** Solo biblioteca estándar.

### En contra (y son reales)

| Problema | Gravedad |
|---|---|
| **507 MiB de RAM** | Alta si hubiera que alojar varios mundos o un servicio multiusuario |
| **2,1 s de arranque** | Irrelevante en CLI; molesto si se recarga por petición |
| `eventos_del_anio` a 30 ms | Recorre los 57.215 eventos en cada llamada |
| `eventos_entre_anios` a 96 ms | Barre y reordena todo el índice |

Los dos últimos son **O(n) por llamada**: se pueden cachear en un diccionario
`año → [evento_id]` construido una vez (2.1 s de carga). Es una mejora local,
no una migración.

---

## 3. Las tres opciones

### Opción A — JSONL + índice en memoria **[RECOMENDADA]**

Seguir como está.

*Cons:* 507 MiB y dos consultas O(n).

*Pro:* cero mantenimiento, total transparencia, ya reproducible y auditada.

### Opción B — SQLite

Volvería útil **si** el conjunto creciera 10× (más de 800.000 registros) o si
hace falta consultar sin cargar todo en memoria. El `schema/schema.sql` de
Fase 1 (15 tablas, 4 vistas) ya está escrito: la migración sería mecánica.

Inconveniente: la base de datos pasa a ser **estado**, y habría que.versionar
o regenerar. Con el pipeline actual, regenerar desde los XML tarda 2 min.

### Opción C — PostgreSQL / Supabase

**Descartada por ahora.** Solo tiene sentido si el modelo debe vivir en un
servicio accesible desde fuera, con escritura concurrente y auditoría de
consultas. Nada de eso es un requisito actual, y añadir una dependencia de red
en un proyecto cuya premisa es «los datos son un archivo inmutable» rompería
la reproducibilidad demostrada.

---

## 4. Recomendación

**Opción A. No migrar.**

Motivo: el cuello de botella medido es el **arranque**, no las consultas, y
ninguna de las tres opciones lo arregla. Una base de datos cambiaría el coste de
arranque pero añadiría complejidad, un estado que versionar y una dependencia.

**Cuando reconsiderarlo:**

| Señal | Acción |
|---|---|
| Más de un mundo activo en memoria | Optimizar memoria, no migrar |
| Más de 800.000 registros | Evaluar Opción B |
| Consulta desde otro proceso o por red | Evaluar Opción C |
| Escrituras concurrentes | Evaluar Opción C |
| Consultas analíticas ad-hoc sobre millones de filas | Evaluar Opción B |

**Mejoras locales que sí valen la pena** (no son migraciones):

1. Precalcular `año → [evento_id]` al cargar: `eventos_del_anio` pasa de 30 ms
   a microsegundos.
2. Cachear el índice si el proceso atiende varias consultas: ahorra los 2,1 s
   de arranque.
3. Si la memoria resulta un problema, cargar perezosamente por sección.

Ninguna cambia el formato ni la reproducibilidad.

---

## 5. Sobre la carpeta `08_DATABASE`

El nombre de la carpeta **no implica** una base de datos. Actualmente contiene:

- `schema/schema.sql` — documentación de la estructura relacional, escrita en
  Fase 1 como especificación.
- `architecture.md`, `query_reference.md`, `relationship_semantics.md`,
  `data_limitations.md`, `ai_data_contract.md` — documentación.

**No hay ninguna base de datos operativa.** El esquema SQL sirve como
especificación y está listo por si en el futuro hace falta la Opción B.