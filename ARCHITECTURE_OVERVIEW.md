# ARCHITECTURE OVERVIEW

Qué es **DF-Chronicles** hoy: qué módulo hace qué, cómo fluyen los datos, dónde
está la frontera y qué no existe.

> **Este documento describe el sistema real, no el deseado.** Cuando algo está
> previsto pero no implementado, se dice «no existe». Ninguna capacidad futura se
> presenta como disponible.

**Documentos hermanos, no duplicados:**

| Documento | Cubre |
|-----------|-------|
| `ARCHITECTURE.md` | La cadena completa y las cinco reglas de diseño |
| `08_DATABASE/architecture.md` | La capa de datos en detalle: merge, certeza, rendimiento |
| `ARCHITECTURE_DECISIONS.md` | Por qué se decidió así (17 fichas) |
| `DATA_QUERY_SERVICE_CONTRACT.md` | **La capa de consulta determinista**: operaciones, estados, identidad, evidencia, límites |
| `TECHNICAL_ROADMAP.md` | Qué falta y en qué orden |

---

## 1. Qué hace el proyecto

Lee los exports de Dwarf Fortress (`legends.xml` y `legends_plus.xml`), los
normaliza en un dataset consultable, y lo expone por API y por UI. Encima de ese
dataset hay una capa de IA **preparada pero no conectada**, que responde
preguntas sobre la partida sin revelar lo que el jugador no ha descubierto.

* **Sin red.** Sin `pip install`. Solo biblioteca estándar de Python 3.11+.
* **Sin IA.** No hay modelo, ni SDK, ni endpoint de IA. La capa existe y se
  prueba con un motor determinista.

---

## 2. Mapa de módulos

### 2.1 Pipeline de datos (`00_SOURCE/tools/`)

| Módulo | Responsabilidad | No sabe de |
|--------|-----------------|-----------|
| `rutas.py` | Dónde vive cada carpeta (`PROJECT_ROOT`, `DATA_ROOT`, …) | Dwarf Fortress |
| `cargar_legends.py` | Leer XML autodetectando codificación, sanear bytes en memoria | El mundo histórico |
| `integrar_legends.py` | Fusionar las dos fuentes con procedencia por campo | Consultas |
| `validar_semantica.py` | Índice de referencias cruzadas y su validación | HTTP, UI |
| `nucleo.py` | **Lógica de dominio**: búsqueda, fichas, cronología, relaciones | HTTP, formato de respuesta |
| `actualizar_datos.py` | Refresco versionado: calcula `dataset_id` por SHA-256 | — |

`nucleo.py` (60 KB) es el corazón. No importa nada de la capa de IA.

### 2.2 Servicio y presentación (`dfchron/`)

| Módulo | Responsabilidad | No sabe de |
|--------|-----------------|-----------|
| `servicio.py` | Envelopes, paginación, límites, errores. Único que conoce el formato de respuesta | Dwarf Fortress |
| `servicio_consulta.py` | **Capa de consulta determinista.** Delega en `servicio`, `ia_conocimiento` y `verificacion_semantica`; añade `identity`, `evidence` y `dataset_id` a cada respuesta. Ver `DATA_QUERY_SERVICE_CONTRACT.md` | HTTP, formato de respuesta |
| `adaptador_consulta.py` | **Adaptador HTTP.** Traduce URL, query y códigos HTTP a `servicio_consulta`. No decide nada del dominio | Qué es una figura, qué relación existe |
| `api.py` | Rutas HTTP. Las fichas y relaciones **delegan en el adaptador**; el resto sigue usando `servicio` | Qué es una figura |
| `web/`, `site/` | UI (HTML+JS, y Astro). Hablan **solo** con `/api/...`. Muestran el estado y la evidencia que llega, sin decidir | Qué significa un evento |
| `config.py` | Configuración y rutas | — |

**La ruta de consulta real** (verificada con `probar_integracion_consulta.py`):

```
WEB  ──fetch──▶  API HTTP  ──▶  adaptador_consulta  ──▶  servicio_consulta  ──▶  NÚCLEO
                    │                   │                        │                  │
              valida entrada      traduce HTTP          decide qué existe,     lee el XML
              y formatea         y código HTTP         qué está verificado
```

No existe ruta paralela: ni la API ni la Web consultan el dataset ni el índice
para resolver conocimiento que el servicio ya sabe resolver.

### 2.4 El perímetro del futuro consumidor IA — **especificado, no implementado**

Existe ya un contrato **congelado** de *autoridad*:
`08_DATABASE/AI_PRE_LLM_CONTRACT.md`, que gobierna lo que el modelo puede
afirmar o cambiar, con su gate de 15 invariantes
(`probar_gate_pre_ia.py`).

Falta el otro eje, y es lo que añade `AI_CONSUMER_BOUNDARY.md`: **qué puede
pedir y recibir**. Son preguntas distintas:

| Eje | Documento | Pregunta |
|-----|-----------|----------|
| Autoridad | `AI_PRE_LLM_CONTRACT.md` (CONGELADO) | ¿Qué puede afirmar o cambiar? |
| Acceso | `AI_CONSUMER_BOUNDARY.md` | ¿Qué puede pedir y recibir? |

La ruta especificada, y **no existe ninguna otra**:

```
FUTURO MODELO IA ──▶ PERÍMETMO RESTRINGIDO ──▶ servicio_consulta ──▶ núcleo
```

Nunca: `IA → dataset`, `IA → JSONL`, `IA → índice`, `IA → filesystem`.

El perímetro es ejecutable: vive como bloque marcado en
`dfchron/pruebas/probar_perimetro_ia.py` (50 pruebas, 11/11 mutaciones).
**No existe un módulo de adaptador de IA en producción**: la misión pide
especificar, no implementar, y un módulo de producción con ese nombre sería
ambiguo. Ver D19.

### 2.3 Capa de IA (`dfchron/`) — **sin modelo conectado**

| Módulo | Responsabilidad |
|--------|-----------------|
| `contrato_ia.py` | **Contrato de afirmaciones**: `evidencia()`, `afirmacion()`, dimensiones y sus valores válidos |
| `ia_conocimiento.py` | Puente núcleo → afirmaciones, con procedencia y versión |
| `estado_conocimiento.py` | Estado de ejecución del jugador: qué conoce. Fuera del dataset |
| `ia_contexto.py` | Recuperación desde el dataset real, selección y reducción |
| `ia_contrato.py` | `contexto()` (filtra por política) y `validar_salida()` (fail-closed) |
| `ia_estructura.py` | Verificación determinista contra la ficha del núcleo |
| `ia_verificacion.py` | Trazabilidad léxica y **declaración de alcance** |
| `ia_frontera.py` | Composición del texto y lista blanca de salida |
| `ia_inferencia.py` | Frontera del modelo: interfaz `invocar` |
| `ia_mock.py` | Motor **sin LLM** para probar el flujo completo |

---

## 3. Flujo de datos

```
legends.xml (CP437) + legends_plus.xml (UTF-8)     NUNCA se modifican
   -> cargar_legends        decodifica, sanea, parsea
   -> integrar_legends      merge con procedencia -> JSONL (20 secciones)
   -> validar_semantica     índice + referencias cruzadas
   -> nucleo.py             fichas, búsqueda, cronología, relaciones
   -> servicio.py           envelopes, límites, errores
   -> api.py                HTTP (stdlib)
   -> web/ | site/          UI
```

---

## 4. Flujo de la capa de IA

Este es el camino que un futuro modelo tendría que recorrer. **El modelo solo
aparece en UN nodo.**

```
nucleo.py
   -> ia_conocimiento       afirmacion() con evidencia + dataset_id + state_version
   -> ioc.contexto()        FILTRA por politica. FORBIDDEN no entra, ni en razonamiento
   -> [ ADAPTADOR / modelo ] UNA propuesta: elige claims y tipo de intencion
   -> ioc.validar_salida()  valida referencias y permisos. FAIL CLOSED
   -> ia_estructura         verifica contra la ficha. NO_VERIFICADA si no cuadra
   -> ia_frontera.componer  redacta DESDE EL CONTEXTO, no desde el modelo
   -> jugador
```

**La ruta `MODELO → TEXTO → JUGADOR` no existe.** Es lo que hace que el sistema
sea auditable: la salida se puede reconstruir sin el texto del modelo.

---

## 5. Puntos de entrada

| Fichero | Arranca |
|---------|---------|
| `run.py` | Orquestación: solo coordina |
| `dfchron/api.py` | Servidor HTTP |
| `dfchron/__init__.py` | Declara el paquete |
| `00_SOURCE/tools/*.py` | Cada herramienta de pipeline, ejecutable suelto |

---

## 6. Dependencias

| Capa | Dependencia |
|------|-------------|
| Todo el proyecto | **Solo biblioteca estándar de Python 3.11+** |
| `dfchron/site/` | Node (build de Astro). No afecta al núcleo |
| Redes | Ninguna |

No hay `requirements.txt`. No hay SDK de IA. `probar_contrato_ia.py` y
`probar_semantica_ia.py` **fallan si alguien añade uno**.

---

## 7. Pruebas

| Suite | Qué cubre |
|-------|-----------|
| `probar_gate_pre_ia.py` | **Gate**: 15 invariantes previos al LLM |
| `probar_cierre_pre_ia.py` | Temporalidad, descubrimiento, aislamiento, persistencia |
| `probar_auditoria_final.py` | 18 invariantes, 44 ataques |
| `probar_documentacion_ia.py` | La documentación no puede mentir sobre el código |
| `probar_documentacion_indice.py` | Enlaces y cifras del índice |
| `probar_banco_ia.py` / `evaluar_banco_ia.py` | 83 escenarios adversariales |
| `probar_integracion.py`, `probar_nucleo.py`, `probar_adversarial.py` | Pipeline y núcleo |
| `probar_api.py`, `probar_web.py` | API y UI reales por HTTP |
| `test_determinismo.py`, `verificar_reproducibilidad.py` | Determinismo y reproducibilidad |

Índice completo en `PROJECT_DOCUMENTATION_INDEX.md` §7.

---

## 8. Límites conocidos

Lo que **no** hace el sistema, escrito para que nadie lo dé por hecho.

### 8.1 Sobre los datos

| Limitación | Consecuencia |
|------------|--------------|
| Solo años 1–100 | No hay cronología completa. `event.year` va de 1 a 100 |
| 31 % de eventos sin participantes | 22.084 de 57.215 con `hfid` vacío: no se puede atribuir |
| 6.734 figuras sin fecha de muerte | `death_year == -1`. Ausente **no** es «viva» |
| 120 figuras sin fecha de nacimiento | `birth_year == -1` |
| 9.930 eventos con coordenadas `-1,-1` | No tienen lugar real |
| 13.192 relaciones sin evento asociado | `relation.event` no resuelve en **ninguno** de los eventos |
| 1.925 conflictos entre fuentes, sin resolver | Se conservan ambos valores, no se elige |
| Sin tabla de guerras | Los conflictos son eventos discretos |

Detalle en `08_DATABASE/data_limitations.md`.

### 8.1 bis Lo que sí está íntegro

Medido sobre el dataset activo, no estimado:

| Propiedad | Resultado |
|-----------|-----------|
| Referencias cruzadas con destino | **0 rotas.** Las 12.982 (`entity_id`, `site_id`, `civ_id`, `cur_owner_id`, artefactos, `source_hf`, `target_hf`) resuelven el 100 % |
| `subregion_id` de eventos | **5.611 de 5.611** resuelven en `regions`. Cero rotas |
| Unicidad de `df_id` | 16 secciones con id único; `record_id == sección:df_id` al 100 % |
| Hashes de sección | Las 17 coinciden con `dataset_version.json` |

> **Precisión que evita un error:** `subregion_id` resuelve en `regions`, **no**
> en `underground_regions`. Ambos usan ids solapados (0–404), así que medirlo
> contra la sección equivocada parece encontrar 1.732 referencias rotas que no
> existen.

### 8.2 Sobre la verificación

| Limitación | Estado |
|------------|--------|
| **Verificación semántica** (paráfrasis, negación, composición) | **NO DISPONIBLE.** `NO_APLICABLE` |
| **Verificación semántica determinista** (7 niveles) | **DEMOSTRADO.** `00_SOURCE/tools/verificacion_semantica.py` |
| **Afirmaciones relacionales complejas** | **PARCIALMENTE DEMOSTRADO.** La *relación* entre figuras se verifica (`relacion()`); la *fila de relación* no tiene identidad (`NOT PROVEN`) |
| **Identidad de la fila de relación** | **NO DISPONIBLE.** Filas sin `df_id` ni identidad recuperable |
| **Caducidad temporal** | No hay reloj de juego |
| **Estado en vivo** | El dataset es una foto; no hay `dataset_id` para mundo mutable |
| **Memoria conversacional** | No existe |
| **Trazabilidad léxica** | Es una medida de descripción, **no** una barrera de seguridad |
| **`deteccion_fuga()`** | Esqueleto heurístico: detecta coordenadas, no paráfrasis |

### 8.2 bis Verificación semántica determinista: qué cubre de verdad

Distinción importante, porque «semántica» sugiere una cosa y aquí son dos:

| Qué | Estado | Dónde |
|-----|--------|-------|
| Afirmación **estructurada** con sujeto y predicado | **DEMOSTRADO** | `verificacion_semantica.py` |
| Afirmación en **lengua natural** (paráfrasis, negación) | **NO DISPONIBLE** | — |

Los siete niveles del verificador determinista:

| Nivel | Ejemplo | Estado |
|-------|---------|--------|
| 1 Existencia | «la figura 712 existe» | **Completo** |
| 2 Atributo | «la figura 712 tiene raza MINOTAUR» | **Completo**, comparación exacta |
| 3 Relación | «500 tiene un war_buddy con 502» | **Completo**, grafo dirigido |
| 4 Estado | «la figura 712 es FACT» | **Completo** |
| 5 Cantidad | «hay 11.144 figuras» | **Completo**, recuento real |
| 6 Estructura | «500 → 502 → …» | **Completo**, cadena entera o nada |
| 7 Histórico | «A se relacionó con B antes que al revés» | **Parcial**: requiere años en ambos lados |

Que el nivel 2 sea **exacto** es la frontera: `minotaur` no es `MINOTAUR`. No
se normaliza, porque en cuanto se normaliza deja de ser determinista.

**Lo que este módulo NO hace**, y declara en `alcance()`: no reconoce
paráfrasis, no verifica negaciones, no usa similitud léxica.

### 8.3 Sobre la IA

**No existe** ningún modelo, SDK, endpoint ni RAG. La frontera existe y está
probada con `ia_mock.py`, que simula el motor sin LLM.

---

## 9. Puntos que no están claros

Se declara lo que no se pudo determinar por inspección:

* **Cómo se integrará con Dwarf Fortress en vivo** no está decidido. `P5` en
  `ARCHITECTURE_DECISIONS.md`. El proyecto hoy consume exports, no el juego.
* **La granularidad del estado del jugador para `relacion`** no existe: las
  relaciones no tienen identificador estable, y no se ha inventado uno.
* **`dfchron/site/` (Astro)** tiene `node_modules/` y builds; no se auditó su
  contenido porque no participa del camino de datos ni de la capa de IA.

---

## 10. Documentos de referencia

| Ruta | Para qué |
|------|----------|
| `PROJECT_DOCUMENTATION_INDEX.md` | Índice de toda la documentación |
| `README.md` | Qué es y cómo se arranca |
| `ARCHITECTURE.md` | Cadena completa y reglas de diseño |
| `08_DATABASE/architecture.md` | Capa de datos en detalle |
| `ARCHITECTURE_DECISIONS.md` | Las 17 decisiones y sus motivos |
| `TECHNICAL_ROADMAP.md` | Qué falta, en qué orden y qué bloquea qué |
| `08_DATABASE/AI_PRE_LLM_CONTRACT.md` | **Contrato congelado** previo al LLM |
| `08_DATABASE/AI_PROJECT_CONTEXT.md` | Contexto operativo para programar la capa de IA |
| `08_DATABASE/ai_data_contract.md` | Formato y semántica de las afirmaciones |
| `INFORME_CIERRE_PRE_IA.md` | Qué se demostró y qué sigue abierto |