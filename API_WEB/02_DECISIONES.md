# API/WEB — DECISIONES ARQUITECTÓNICAS

> Cada decisión: qué se decidió, por qué, y qué se descartó.
> Una decisión sin alternativa descartada no es una decisión: es un comentario.

---

## Contexto que cambió la misión

La misión se enuncia como si la frontera API/Web **hubiera que construirla**. Al
inventariar el repositorio antes de escribir una línea, se encontró que ya
existía, implementada y probada por una misión anterior
(`ARCHITECTURE_DECISIONS.md` D18, `INFORME_INTEGRACION_API_WEB_CONSULTA.md`).

Eso convierte la misión de *construcción* en **auditoría y cierre verificable**.

---

## D-001 · Auditar, no reconstruir

**Decisión.** No migrar endpoints ni rehacer el adaptador. Verificar lo que hay y
ampliar solo los huecos demostrables.

**Por qué.** La frontera ya existe: `adaptador_consulta.py`, 13 rutas que la usan,
`probar_integracion_consulta.py` con 55 pruebas, un harness de mutación
permanente y la decisión D18 documentada. Rehacerlo habría producido una segunda
implementación —justo lo que la arquitectura prohíbe— y habría destruido
evidencia de por qué la primera es como es.

**Descartado.** «Añadir más rutas a `/api/consulta/*` hasta que cubra todo». La
frontera existe para afirmar sobre entidades, no para servir la API entera.

---

## D-002 · El perímetro son 13 rutas, no 51

**Decisión.** Solo las 5 fichas de entidad, la ruta de relaciones y las 7 rutas
`/api/consulta/*` pasan por `servicio_consulta`.

**Por qué.** El criterio es semántico: *¿el endpoint afirma algo?* Una ficha
afirma «esta figura existe y estos son sus atributos» — y esa afirmación necesita
`identity`, `evidence` y `dataset_id`. Un listado no afirma: devuelve filas para
orientarse, y «no aparece en esta búsqueda» **no es un hecho**.

**Descartado.** Migrar también los listados. Habría obligado a fabricar una
evidencia por fila que no significa nada, o a declararla ausente, que es peor.
Habría costado un `dataset_id` por elemento para no ganar nada.

**La distinción que lo fija.** `/api/figuras/712/relaciones` está dentro;
`/api/figuras/712/eventos` está fuera. La primera es *la* relación de esa figura
— sujeto único, verificable. La segunda es *la lista* de eventos donde aparece.
Ahí es donde `verificar()` tiene algo que verificar, y ahí termina el perímetro.

---

## D-003 · La Web se queda como está

**Decisión.** Ningún cambio en `web/` ni en `site/`.

**Por qué.** La auditoría no encontró acceso directo: cero `readFileSync`, cero
`XMLHttpRequest`, cero `fs`. Las dos únicas coincidencias de «dataset» son un
texto estático en `index.html` y un comentario en `mapa.ts`. La Web ya es
`Web → API → adaptador → servicio_consulta`.

**Descartado.** «Añadir una capa de tipos o un cliente generado» para hacer la Web
más explícita. Sería reescribir código que ya cumple, con riesgo de introducir
un acceso nuevo.

---

## D-004 · No borrar el código muerto del adaptador

**Decisión.** `adaptador_consulta.py` líneas 253-255 se quedan como están.

```python
    return _responder(qc.buscar_relaciones(...))
    return None                          # inalcanzable
    out["http_status"] = _http_de(out)   # inalcanzable, y `out` no existe
    return out                           # inalcanzable
```

**Por qué no se toca.** No causa fallo. Cambiaría el hash de un fichero de
producción sin necesidad, y la misión prohíbe modificar el adaptador. El arreglo
es trivial (borrar tres líneas) pero **no es de esta misión**.

**Por qué no se esconde.** Es una trampa: si alguien reordena esas líneas por
error, el fallo sería un `NameError` en ejecución, no un error visible de lógica.
Queda como deuda en §Deuda.

---

## D-005 · El harness se ejecuta siempre en segundo plano

**Decisión.** Nunca a través de un comando con límite de tiempo.

**Por qué.** El harness escribe sobre ficheros de producción. El `finally`
protege de excepciones, **no de que maten el proceso**. Una ejecución cancelada
a los 30 s dejó `servicio_consulta.py` con `evidence = None`.

**Por qué no se rediseña el harness.** Un harness que muta una copia en un
directorio temporal sería más seguro, pero las rutas de los ficheros ya están
fijas en el código y las pruebas leen rutas absolutas del repositorio.
Rediseñarlo excede el alcance.

**Lo que sí se hace:** documentar el modo de fallo y dejar
`restaurar_servicio.py`, que aborta si el hash no cuadra al restaurar.

---

## D-006 · El harness de mutación es permanente y va a 9

**Decisión.** Ampliar `dfchron/pruebas/probar_mutation_frontera.py` de 5 a 9
mutaciones, sobre 4 ficheros de producción, y añadir la suite adversarial a las
suites que deben detectar.

**Por qué.** La misión exige 8 categorías; las 5 existentes cubrían 4. Faltaban
*eliminar* `dataset_id`, *alterar* `state_version` y *respuesta fabricada*. Y una
suite que solo se ejecuta en la regresión no demuestra nada sobre sí misma: si
está en la lista de suites del harness, es porque debe detectar algo.

**Descartado.** Un harness nuevo en `API_WEB/`. Habría dejado dos fuentes de
verdad sobre qué mutaciones existen.