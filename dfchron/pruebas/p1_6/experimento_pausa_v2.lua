-- ============================================================================
-- P1.6 :: EXPERIMENTO AUTORIZADO DE PAUSA / DESPAUSA  (version 2)
-- ============================================================================
-- Autorizacion: despausar ~10 s, observar, volver a pausar. Nada mas.
-- NO se guarda, NO se cambia velocidad, NO se tocan unidades ni el mundo.
--
-- POR QUE EXISTE UNA VERSION 2
-- ----------------------------
-- La v1 fallo con "attempt to call a nil value (global 'muestrar')" en DOS
-- intentos, incluso declaring las funciones como globales. El codigo estaba
-- balanceado y un caso minimo con dos locales SI funciona, asi que no es una
-- limitacion general de DFHack: la causa exacta NO se ha aislado. Se evita el
-- patron escribiendo el muestreo en forma PLANA. La v1 se conserva intacta en
-- `experimento_pausa.lua` como evidencia: un fallo que no se entiende y se
-- esquiva debe quedar escrito, no borrado.
--
-- DISENO DE SEGURIDAD (demostrado, no supuesto)
-- ---------------------------------------------
-- 1. TODO ocurre en UNA sola invocacion de dfhack-run: no queda ventana entre
--    procesos con el juego despausado.
-- 2. Los muestreos usan `dfhack.timeout`, NO dormir: dormir bloquearia el
--    juego y no avanzaria. Demostrado en probar_mecanismo_timeout.lua: el
--    callback se ejecuto solo, a los 63 ms, sin bloquear.
-- 3. LA PAUSA SE APLICA SIEMPRE: el cuerpo va dentro de `pcall` y el
--    `SetPauseState(true)` final esta FUERA. Lua no tiene try/finally, asi que
--    la garantia se consigue por estructura, no por?.
-- 4. Red de seguridad adicional a los +3 s, por si el primer callback murio.
-- 5. Se escribe un testigo FIN_EXPERIMENTO. Si falta, hay que pausar a mano.
--
-- `observation_id` es un contador LOCAL. NO es una version del mundo.

local SALIDA = _G.DFCHRON_OUT_SALIDA
local MUESTRAS = 5
local PASO_S = 2
local T0_HOST = dfhack.getTickCount()
local id = 0
local t0_tick = dfhack.world.ReadCurrentTick()
local json = require('json')
local cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')
local tr = dfhack.translation.translateName

local function escribir(m)
    local fh = assert(io.open(SALIDA, 'ab'))
    fh:write(json.encode(m, { pretty = false }) .. '\n')
    fh:close()
end

local function seguro(fn, ...)
    local ok, v = pcall(fn, ...)
    if ok and v ~= nil then return v end
    return nil
end

local function muestrear(etiqueta)
    local races, profs = {}, {}
    local ok_l, lista = pcall(dfhack.units.getCitizens)
    if ok_l and lista then
        for i = 1, #lista do
            local u = lista[i]
            local r = seguro(dfhack.units.getRaceName, u) or '?'
            local p = seguro(dfhack.units.getProfessionName, u) or '?'
            races[r] = (races[r] or 0) + 1
            profs[p] = (profs[p] or 0) + 1
        end
    end
    id = id + 1
    return {
        observation_id = string.format('%06d', id),
        etiqueta = etiqueta,
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
        host_ms = dfhack.getTickCount() - T0_HOST,
        paused = seguro(dfhack.world.ReadPauseState),
        world_name = seguro(function()
            return cp.decode(tr(df.global.world.world_data.name)) end),
        world_folder = seguro(dfhack.world.ReadWorldFolder),
        game_year = seguro(dfhack.world.ReadCurrentYear),
        game_month = seguro(dfhack.world.ReadCurrentMonth),
        game_day = seguro(dfhack.world.ReadCurrentDay),
        game_season = seguro(function() return df.global.cur_season end),
        weather = seguro(dfhack.world.ReadCurrentWeather),
        fortress_mode = seguro(dfhack.world.isFortressMode),
        citizens = (ok_l and lista) and #lista or nil,
        races = races,
        professions = profs,
        -- CANAL DIAGNOSTICO. NO es conocimiento del jugador.
        _diag_tick = seguro(dfhack.world.ReadCurrentTick),
    }
end
-- --------------------------------------------------------------------------
-- T0 -- partida pausada, muestra de referencia
-- --------------------------------------------------------------------------
escribir(muestrar('T0'))

local error_experimento = nil

-- El experimento: despausar y muestrear. Todo aqui dentro.
-- La pausa final esta FUERA, para que se ejecute aunque esto falle.
local function cuerpo()
    dfhack.world.SetPauseState(false)
    local paso
    paso = function(i)
        if i > MUESTRAS then return end
        escribir(muestrar('T1_' .. i))
        dfhack.timeout(PASO_S, 'seconds', function() paso(i + 1) end)
    end
    dfhack.timeout(1, 'seconds', function() paso(1) end)
end

local ok, err = pcall(cuerpo)
if not ok then error_experimento = tostring(err) end

-- --------------------------------------------------------------------------
-- PAUSA GARANTIZADA + T2 + testigo
-- --------------------------------------------------------------------------
local function pausar_y_cerrar()
    dfhack.world.SetPauseState(true)
    escribir(muestrar('T2'))
    escribir({
        evento = 'FIN_EXPERIMENTO',
        error_experimento = error_experimento,
        paused_final = dfhack.world.ReadPauseState(),
        tick_inicial = t0_tick,
        tick_final = dfhack.world.ReadCurrentTick(),
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
    })
end

dfhack.timeout(PASO_S * (MUESTRAS + 1), 'seconds', pausar_y_cerrar)
dfhack.timeout((PASO_S * (MUESTRAS + 1)) + 3, 'seconds', function()
    dfhack.world.SetPauseState(true)
end)