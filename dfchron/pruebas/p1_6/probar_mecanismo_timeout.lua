-- P1.6 :: PRUEBA DEL MECANISMO, sin tocar la pausa.
-- Si este script no demuestra que `dfhack.timeout` ejecuta el callback mas
-- adelante SIN bloquear el juego, la prueba de pausa NO debe realizarse.
--
-- Escribe un fichero testigo. NO modifica nada del juego.

local SALIDA = _G.DFCHRON_OUT_SALIDA
local inicio = dfhack.getTickCount()

local function escribir(msg)
    local f = assert(io.open(SALIDA, 'ab'))
    f:write(msg .. string.char(10))
    f:close()
end

escribir('T0 chunk ms=' .. tostring(dfhack.getTickCount() - inicio))
escribir('T0 pause=' .. tostring(dfhack.world.ReadPauseState()))
escribir('T0 tick='  .. tostring(dfhack.world.ReadCurrentTick()))

-- Callback a 1 segundo. Si se ejecuta, el mechanismo funciona.
dfhack.timeout(1, 'frames', function()
    local f = assert(io.open(SALIDA, 'ab'))
    f:write('T1 callback ms=' .. tostring(dfhack.getTickCount() - inicio) .. string.char(10))
    f:write('T1 pause=' .. tostring(dfhack.world.ReadPauseState()) .. string.char(10))
    f:write('T1 tick='  .. tostring(dfhack.world.ReadCurrentTick()) .. string.char(10))
    f:write('FIN_MECANISMO_OK' .. string.char(10))
    f:close()
end)

escribir('T0 chunk retorna (el juego sigue libre)')
