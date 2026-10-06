-- ============================================================================
-- P1.6 :: EXPERIMENTO AUTORIZADO DE PAUSA / DESPAUSA  (v4)
-- ============================================================================
-- Autorizacion: despausar ~10 s, observar, volver a pausar. Nada mas.
--
-- QUE CAMBIA RESPECTO A v3 (y por que)
-- -------------------------------------
-- v3 uso `dfhack.timeout(n, 'seconds', cb)`. **'seconds' NO EXISTE.** Los modos
-- validos, segun la documentacion de ESTA version, son:
--     'frames' (FPS real) | 'ticks' (FPS despausado) | 'days' | 'months' | 'years'
-- Como el script fallo EN ESA LINEA, que se ejecuta DESPUES de haber
-- despausado, la partida se quedo CORRIENDO hasta que se paused a mano.
-- Incidente documentado en P1.6_EXPERIMENTO_PAUSA.md.
--
-- DISENO DE v4 (defensa en profundidad)
-- ------------------------------------
-- 1. Se USA SOLO 'frames', unico modo verificado en este entorno.
-- 2. LA RED DE SEGURIDAD SE ARMA ANTES DE DESPAUSAR. En v3 estaba despues.
-- 3. Antes de despausar se VERIFICA que el temporizador devuelve un id valido.
--    Si no lo hace, el script aborta SIN despausar.
-- 4. Todo en una sola invocacion de dfhack-run.
--
-- `observation_id` es un contador LOCAL. NO es una version del mundo.

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.FRAMES_PASO = 90        -- ~1-2 s segun FPS
_G.FRAMES_SEGURIDAD = 900  -- tope duro: ~10-15 s
_G.T0_HOST = dfhack.getTickCount()
_G.id = 0
_G.t0_tick = dfhack.world.ReadCurrentTick()
_G.t0_pause = dfhack.world.ReadPauseState()
_G.json = require('json')
_G.cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')
_G.tr = dfhack.translation.translateName
_G.muestras_intermedias = 0

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

_G.cerrar = function(motivo)
    dfhack.world.SetPauseState(true)
    _G.escribir(_G.muestrar('T2'))
    _G.escribir({
        evento = 'FIN_EXPERIMENTO',
        motivo_cierre = motivo,
        muestras_intermedias = _G.muestras_intermedias,
        paused_final = dfhack.world.ReadPauseState(),
        tick_inicial = _G.t0_tick,
        tick_final = dfhack.world.ReadCurrentTick(),
        pause_inicial = _G.t0_pause,
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
    })
end

-- --------------------------------------------------------------------------
-- T0: referencia con la partida pausada
-- --------------------------------------------------------------------------
_G.escribir(_G.muestrar('T0'))

-- --------------------------------------------------------------------------
-- RED DE SEGURIDAD, ARMADA ANTES DE DESPAUSAR
-- Si cualquier cosa falla despues, esto pausa igualmente.
-- --------------------------------------------------------------------------
local id_seguridad = dfhack.timeout(_G.FRAMES_SEGURIDAD, 'frames',
                                   function() _G.cerrar('seguridad_frames') end)

if type(id_seguridad) ~= 'number' then
    -- El temporizador no arranco: NO se despausa. Se aborta con seguridad.
    _G.escribir({ evento = 'ABORTO', motivo = 'el temporizador no arranco',
                  id_seguridad = tostring(id_seguridad),
                  paused = dfhack.world.ReadPauseState() })
else
    -- Cadena de muestreo. Solo 'frames'.
    _G.paso = function(i)
        if i > 6 then return end
        _G.muestras_intermedias = _G.muestras_intermedias + 1
        _G.escribir(_G.muestrar('T1_' .. i))
        dfhack.timeout(_G.FRAMES_PASO, 'frames', function() _G.paso(i + 1) end)
    end
    dfhack.world.SetPauseState(false)          -- despausar
    dfhack.timeout(_G.FRAMES_PASO, 'frames', function() _G.paso(1) end)
end