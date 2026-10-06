# API_WEB_MAPA_FRONTERA

> **Matriz de clasificación de endpoints.** Documento permanente.
> Expediente completo: [`API_WEB/`](API_WEB/) · Generado por
> [`API_WEB/auditar_frontera.py`](API_WEB/auditar_frontera.py)

---

## Arquitectura verificada

```text
                        ┌── Web
                        │
DF → dataset → núcleo → servicio_consulta
                        │
                        ├── API
                        │
                        ├── CLI
                        │
                        └── futuro consumidor IA
```

**Verificada por ejecución, no por lectura:** 13 de 51 rutas pasan por el
adaptador, y son exactamente las 13 que deben. **Discrepancia: 0.**

---

## Matriz de endpoints

### En el perímetro (13) — sí pasan por `servicio_consulta`

| Endpoint | Tipo | Pasa por consulta | Motivo |
|---|---|:---:|---|
| `/api/figuras/{id}` | consulta | **Sí** | Afirma sobre una entidad; aporta identidad y evidencia |
| `/api/entidades/{id}` | consulta | **Sí** | Ídem |
| `/api/sitios/{id}` | consulta | **Sí** | Ídem |
| `/api/artefactos/{id}` | consulta | **Sí** | Ídem |
| `/api/eventos/{id}` | consulta | **Sí** | Ídem |
| `/api/figuras/{id}/relaciones` | consulta | **Sí** | Sujeto único y verificable: *la* relación de esa figura |
| `/api/consulta/contrato` | consulta | **Sí** | El contrato, expuesto por HTTP |
| `/api/consulta/entidad/{tipo}/{id}` | consulta | **Sí** | Operación 1 del servicio |
| `/api/consulta/atributo/{tipo}/{id}/{a}` | consulta | **Sí** | Operación 2 |
| `/api/consulta/relaciones/{id}` | consulta | **Sí** | Operación 3 |
| `/api/consulta/contar/{tipo}` | consulta | **Sí** | Operación 4 |
| `/api/consulta/verificar` | consulta | **Sí** | Operación 5 |
| `/api/consulta/evidencia/{tipo}/{id}` | consulta | **Sí** | Operación 6 |

### Fuera del perímetro (38) — y por qué

| Endpoint | Tipo | Pasa por consulta | Motivo |
|---|---|:---:|---|
| `/api/buscar`, `/api/buscar/{tipo}` | navegación | No | Un «no aparece» no es un hecho |
| `/api/figuras`, `/api/entidades`, `/api/sitios` | navegación | No | Búsqueda por texto: orientación |
| `/api/artefactos` | navegación | No | Búsqueda/listado |
| `/api/listar/{tipo}` | navegación | No | Listado paginado |
| `/api/conflictos` | navegación | No | Explora fuentes, no afirma |
| `/api/eventos` | navegación | No | Listado filtrado del histórico |
| `/api/geografia` y sus 4 subrutas | navegación | No | Capas y puntos, no afirmaciones |
| `/api/sitios/{id}/geografia` | navegación | No | Construcciones por coordenada |
| `/api/figuras/{id}/eventos`, `/cronologia`, `/artefactos`, `/identidad` | navegación | No | Listado, no afirmación |
| `/api/entidades/{id}/miembros`, `/sitios`, `/eventos`, `/cronologia` | navegación | No | Listado, no afirmación |
| `/api/sitios/{id}/eventos`, `/cronologia`, `/figuras` | navegación | No | Listado, no afirmación |
| `/api/artefactos/{id}/propietarios`, `/eventos` | navegación | No | Listado, no afirmación |
| `/api/eventos/{id}/participantes` | navegación | No | Listado, no afirmación |
| `/api/stats`, `/api/estadisticas` | estadísticas | No | Cuenta agregada |
| `/api/relaciones/tipos`, `/api/eventos/tipos` | metadatos | No | Vocabulario: declara, no afirma |
| `/api/limitaciones` | metadatos | No | Declara lo que el dataset **no** sabe |
| `/api` | metadatos | No | Documento de la API |
| `/api/salud` | salud | No | Estado del **servicio**, no del conocimiento |
| `/api/exportar` | exportación | No | Consumidor de salida, no consulta |

---

## La distinción que fija el perímetro

| Ruta | ¿Afirma? | Por qué |
|---|:---:|---|
| `/api/figuras/712/relaciones` → **dentro** | **Sí** | Es *la* relación de esa figura. Sujeto único, verificable. |
| `/api/figuras/712/eventos` → **fuera** | No | Es *la lista* de eventos donde aparece. Un listado no se verifica elemento a elemento. |

El perímetro termina donde `verificar()` tiene algo que verificar.

---

## Web

| Criterio | Resultado |
|---|---|
| Accesos a disco (`readFileSync`, `XMLHttpRequest`, `fs`) | **0** |
| Lectura de `.jsonl` / `legends.xml` | **0** |
| Reconstrucción de búsquedas | **0** |
| Interpretación de índices | **0** |
| Comunicación | `fetch` a `/api/...` únicamente |

**La Web no tiene conocimiento de cómo está almacenado el dataset.**

---

## Resumen

| Métrica | Valor |
|---|---:|
| Rutas registradas | 51 |
| En el perímetro | 13 |
| Fuera del perímetro | 38 |
| Discrepancia entre lo declarado y lo real | **0** |
| Accesos directos de la Web al dataset | **0** |
| Dependencias de IA | **0** |