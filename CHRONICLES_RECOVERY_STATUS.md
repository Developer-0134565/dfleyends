# CHRONICLES_RECOVERY_STATUS.md — punto de reanudación de la misión

Actualizado: 2026-10-05 (sesion de reanudacion tras INFERENCE_CAP_ERROR/429)

## 0. CONTEXTO

El proyecto DF-Chronicles NO tiene repo git (documentado en
`00_SOURCE/audit_inicial.md`): no existe `git status`/`git diff`. El mecanismo
de integridad son los HASHES SHA256 documentados en la mision anterior:

    servicio_consulta.py  0a5b6b1c3244e619  VERIFICADO INTACTO
    adaptador_consulta.py c456256ec1c1d731  VERIFICADO INTACTO
    servicio.py           48eb8354dca8728b  VERIFICADO INTACTO
    api.py                0426f63a632fd243  VERIFICADO INTACTO
    ia_conocimiento.py    639548169fd86d42  VERIFICADO INTACTO

`chronicles_datos.py` (267 lineas, sintaxis valida) fue reconstruido en esta
sesion con la NUEVA arquitectura V1 (delegacion a chronicles_motor; eliminado
el calculo `tick = anio * 1000000 + seg` por conversion no demostrada).
`probar_chronicles.py` sigue 25/25. Herramientas `clasificar_tipos.py` y
`diagnostico_v1.py` funcionan sobre el cd reconstruido.

## CHECKPOINT 0 — RECOVERY: PASS

- Archivos criticos: existen, sintaxis valida, 5 hashes de produccion intactos.
- chronicles.py: intacto, 25/25.
- Nuevos modulos: chronicles_vocab.py, chronicles_evento.py, chronicles_motor.py
  (compilan; motor validado sobre fixtures synthetic).
- chronicles_datos.py: reconstruido (loader + cronica + delegacion). PENDIENTE:
  ejecutar `cronica()` sobre dataset real (medir tiempo/memoria).
- ULTIMO CHECKPOINT VALIDO CONOCIDO: este (CHECKPOINT 0 = PASS).
- BLOQUEADORES: ninguno.
- SIGUIENTE FASE: CHECKPOINT 1 — CORE (verificar 25/25, ya hecho) y
  CHECKPOINT 2 — DATASET (cronica real + numeros 9311/57215/90/78 completos).

## ESTADO DE FASES

    CHECKPOINT 0 — RECOVERY:  PASS
    CHECKPOINT 1 — CORE:       PASS (probar_chronicles 25/25 verificado)
    CHECKPOINT 2 — DATASET:    EN CURSO (falta cronica real completa)
    CHECKPOINT 3 — SERVICE:    PENDIENTE
    CHECKPOINT 4 — ADAPTER/API: PENDIENTE
    CHECKPOINT 5 — WEB:        PENDIENTE
    CHECKPOINT 6 — E2E:        PENDIENTE
    CHECKPOINT 7 — REGRESSION: PENDIENTE

## NOTAS DE CONTINUIDAD

- Si esta sesion muere: leer este fichero y continuar desde CHECKPOINT 2.
- No matar procesos python mientras corra probar_mutation_frontera.py (muta
  _SVC/_ADA/_API/_IAC en sitio y restaura en `finally`; matarlo deja residuo).
- Herramienta prohibida aprendida: no usar open("w")+newline con doble escape
  desde con PowerShell; el editor es la via segura para edicion.
- AI = 0 en toda la mision. DF = READ ONLY.
