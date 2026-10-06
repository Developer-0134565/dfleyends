-- ============================================================================
-- P1.6 :: EXPERIMENTO AUTORIZADO DE PAUSA / DESPAUSA  (v3)
-- ============================================================================
-- Autorizacion: despausar ~10 s, observar, volver a pausar. Nada mas.
-- NO se guarda, NO se cambia velocidad, NO se tocan unidades ni el mundo.
--
-- POR QUE UNA v3
-- ---------------
-- v1 y v2 fallaron con "attempt to call a nil value (global 'muestrar')", con el
-- codigo balanceado y los locales declarados antes del uso. Una funcion
-- hermana (`escribir`) SI funcionaba en el MISMO chunk, asi que no era un
-- problema general del entorno.
-- Diagnostico acotado: `_G.X = function(...) ... end` funciona en las TRES
-- formas probadas (funcion simple, con locales multiple, con pcall sobre
-- getCitizens). Se adopta ese patron, que es el unico verificado.
-- v1 y v2 se conservan intactas como evidencia del fallo.
--
-- DISENO DE SEGURIDAD
-- -------------------
-- 1. TODO en UNA sola invocacion de dfhack-run: no queda ventana entre
--    procesos con el juego despausado.
-- 2. Los muestreos usan `dfhack.timeout`, NO dormir: dormir bloquearia el
--    juego y no avanzaria. Demostrado en probar_mecanismo_timeout.lua.
-- 3. LA PAUSA SE APLICA SIEMPRE: el cuerpo va dentro de `pcall` y el
--    `SetPauseState(true)` final esta FUERA de el.
-- 4. Red de seguridad adicional a los +3 s, por si el primer callback murio.
-- 5. Testigo FIN_EXPERIMENTO. Si falta, hay que pausar a mano.
--
-- `observation_id` es un contador LOCAL. NO es una version del mundo.

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.MUESTRAS = 5
_G.PASO_S = 2
_G.T0_HOST = dfhack.getTickCount()
_G.id = 0
_G.t0_tick = dfhack.world.ReadCurrentTick()
_G.json = require('json')
_G.cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')
_G.tr = dfhack.translation.translateName

_G.escribir = function(m)
    local fh = assert(io.open(_G.SALIDA, 'ab'))
    fh:write(_G.json.encode(m, { pretty = false }) .. '\n')
    fh:close()
end

_G.seguro = function(fn, ...)
    local ok, v = pcall(fn, ...)
    if ok and v ~= nil then return v end
    return nil
end

_G.muestrar = function(etiqueta)
    local races, profs = {}, {}
    local ok_l, lista = pcall(dfhack.units.getCitizens)
    if ok_l and lista then
        for i = 1, #lista do
            local u = lista[i]
            local r = _G.seguro(dfhack.units.getRaceName, u) or '?'
            local p = _G.seguro(dfhack.units.getProfessionName, u) or '?'
            races[r] = (races[r] or 0) + 1
            profs[p] = (profs[p] or 0) + 1
        end
    end
    _G.id = _G.id + 1
    return {
        observation_id = string.format('%06d', _G.id),
        etiqueta = etiqueta,
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
        host_ms = dfhack.getTickCount() - _G.T0_HOST,
        paused = _G.seguro(dfhack.world.ReadPauseState),
        world_name = _G.seguro(function()
            return _G.cp.decode(_G.tr(df.global.world.world_data.name)) end),
        world_folder = _G.seguro(dfhack.world.ReadWorldFolder),
        game_year = _G.seguro(dfhack.world.ReadCurrentYear),
        game_month = _G.seguro(dfhack.world.ReadCurrentMonth),
        game_day = _G.seguro(dfhack.world.ReadCurrentDay),
        game_season = _G.seguro(function() return df.global.cur_season end),
        weather = _G.seguro(dfhack.world.ReadCurrentWeather),
        fortress_mode = _G.seguro(dfhack.world.isFortressMode),
        citizens = (ok_l and lista) and #lista or nil,
        races = races,
        professions = profs,
        -- CANAL DIAGNOSTICO. NO es conocimiento del jugador.
        _diag_tick = _G.seguro(dfhack.world.ReadCurrentTick),
    }
end

-- T0: partida pausada, muestra de referencia
_G.escribir(_G.muestrar('T0'))

-- El experimento, dentro de pcall. La pausa final esta FUERA.
_G.cuerpo = function()
    dfhack.world.SetPauseState(false)
    _G.paso = function(i)
        if i > _G.MUESTRAS then return end
        _G.escribir(_G.muestrar('T1_' .. i))
        dfhack.timeout(_G.PASO_S, 'seconds', function() _G.paso(i + 1) end)
    end
    dfhack.timeout(1, 'seconds', function() _G.paso(1) end)
end

_G.error_experimento = nil
local _ok, _err = pcall(_G.cuerpo)
if not _ok then _G.error_experimento = tostring(_err) end

-- PAUSA GARANTIZADA + T2 + testigo
_G.pausar_y_cerrar = function()
    dfhack.world.SetPauseState(true)
    _G.escribir(_G.muestrar('T2'))
    _G.escribir({
        evento = 'FIN_EXPERIMENTO',
        error_experimento = _G.error_experimento,
        paused_final = dfhack.world.ReadPauseState(),
        tick_inicial = _G.t0_tick,
        tick_final = dfhack.world.ReadCurrentTick(),
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
    })
end

dfhack.timeout(_G.PASO_S * (_G.MUESTRAS + 1), 'seconds', _G.pausar_y_cerrar)
dfhack.timeout((_G.PASO_S * (_G.MUESTRAS + 1)) + 3, 'seconds', function()
    dfhack.world.SetPauseState(true)
end)