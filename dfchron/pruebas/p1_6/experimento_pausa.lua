-- ============================================================================
-- P1.6 :: EXPERIMENTO AUTORIZADO DE PAUSA / DESPAUSA
-- ----------------------------------------------------------------------------
-- Autorizacion del usuario: despausar ~10 s, observar, volver a pausar.
-- NO permite: guardar, cambiar velocidad, modificar unidades/edificios/objetos,
-- ni escribir en la partida.
--
-- DISENO DE SEGURIDAD
-- -------------------
-- 1. TODO ocurre en UNA sola invocacion de dfhack-run: asi no queda una
--    ventana entre procesos en la que el juego quede despausado.
-- 2. Los muestreos intermedios se hacen con `dfhack.timeout`, NO con dormir:
--    dormir bloquearia el juego y no avanzaria, que es justo lo que se quiere
--    observar. El mecanismo quedo demostrado antes de ejecutar esto.
-- 3. LA PAUSA SE APLICA SIEMPRE, incluso si algo falla: el cuerpo va dentro de
--    `pcall` y el `SetPauseState(true)` esta FUERA, en la ruta que se ejecuta
--    pase lo que pase. No se usa try/finally porque no existe en Lua.
-- 4. El script escribe un testigo `FIN_EXPERIMENTO` al terminar. Si falta,
--    significa que la pausa final no llego a ejecutarse y hay que pausar a mano.
--
-- `observation_id` es un contador LOCAL de esta ejecucion. NO es una version
-- del mundo y NO se llama state_version.
-- ============================================================================

local SALIDA = _G.DFCHRON_OUT_SALIDA
local MUESTRAS = 5          -- T1a..T1e durante la carrera
local PASO_S = 2            -- segundos entre muestras
local json = require('json')
local cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')
local tr = dfhack.translation.translateName

local T0_HOST = dfhack.getTickCount()
local id = 0
local t0_tick = dfhack.world.ReadCurrentTick()

-- NOTA DE AMBITO (P1.6): estas funciones se declaran como GLOBALS a proposito.
-- Con `local function`, la version anterior de este script falló con
-- "attempt to call a nil value (global 'muestrar')" pese a estar balanceada y
-- con los locales declarados antes del uso. Un caso minimo con dos locales
-- SI funciona, asi que no es una limitacion general de DFHack: es un detalle
-- de este patron. Convertirlas en globales lo evita y no afecta al resultado.
function ahora_host()
    return os.date('!%Y-%m-%dT%H:%M:%SZ')
end

function muestrear(etiqueta)
    local seguro = function(fn, def) local ok, v = pcall(fn)
        if ok and v ~= nil then return v end return def end

    local races, profs = {}, {}
    for _, u in ipairs(seguro(function() return dfhack.units.getCitizens() end, {})) do
        local r = seguro(function() return dfhack.units.getRaceName(u) end, '?')
        local p = seguro(function() return dfhack.units.getProfessionName(u) end, '?')
        races[r] = (races[r] or 0) + 1
        profs[p] = (profs[p] or 0) + 1
    end

    id = id + 1
    return {
        observation_id = string.format('%06d', id),
        etiqueta = etiqueta,
        observed_at_host = ahora_host(),
        host_ms_desde_inicio = dfhack.getTickCount() - T0_HOST,
        paused = seguro(function() return dfhack.world.ReadPauseState() end, nil),
        world_name = seguro(function()
            return cp.decode(tr(df.global.world.world_data.name)) end, nil),
        world_folder = seguro(function() return dfhack.world.ReadWorldFolder() end, nil),
        game_year = seguro(function() return dfhack.world.ReadCurrentYear() end, nil),
        game_month = seguro(function() return dfhack.world.ReadCurrentMonth() end, nil),
        game_day = seguro(function() return dfhack.world.ReadCurrentDay() end, nil),
        game_season = seguro(function() return df.global.cur_season end, nil),
        weather = seguro(function() return dfhack.world.ReadCurrentWeather() end, nil),
        fortress_mode = seguro(function() return dfhack.world.isFortressMode() end, nil),
        citizens = seguro(function() return #dfhack.units.getCitizens() end, nil),
        races = races,
        professions = profs,
        -- CANAL ESTRICTAMENTE DIAGNOSTICO. NO es conocimiento del jugador.
        -- Solo sirve para saber si el mundo avanzo.
        _diagnostico_tick = seguro(function()
            return dfhack.world.ReadCurrentTick() end, nil),
    }
end

function escribir(m)
    local fh = assert(io.open(SALIDA, 'ab'))
    fh:write(json.encode(m, { pretty = false }) .. '\n')
    fh:close()
end

-- --------------------------------------------------------------------------
-- T0 -- partida pausada, muestra de referencia
-- --------------------------------------------------------------------------
escribir(muestrar('T0'))
print('T0 capturada')

-- --------------------------------------------------------------------------
-- El experimento. Todo aqui dentro; la pausa final queda FUERA.
-- --------------------------------------------------------------------------
local error_experimento = nil

local function cuerpo()
    dfhack.world.SetPauseState(false)          -- despausa
    local n = 0
    local function paso(i)
        if i > MUESTRAS then
            return
        end
        n = i
        escribir(muestrar('T1_' .. i))
        dfhack.timeout(PASO_S, 'seconds', function() paso(i + 1) end)
    end
    dfhack.timeout(1, 'seconds', function() paso(1) end)
end

local ok, err = pcall(cuerpo)
if not ok then error_experimento = tostring(err) end

-- --------------------------------------------------------------------------
-- PAUSA GARANTIZADA: se ejecuta aunque el experimento haya fallado.
-- Ademas, una segunda red a los 3 s, por si el primer callback murio.
-- --------------------------------------------------------------------------
local function pausar_y_cerrar()
    dfhack.world.SetPauseState(true)
    escribir(muestrar('T2'))
    escribir({ evento = 'FIN_EXPERIMENTO',
               error_experimento = error_experimento,
               paused_final = dfhack.world.ReadPauseState(),
               tick_inicial = t0_tick,
               tick_final = dfhack.world.ReadCurrentTick(),
               observed_at_host = ahora_host() })
end

dfhack.timeout(PASO_S * (MUESTRAS + 1), 'seconds', pausar_y_cerrar)
dfhack.timeout((PASO_S * (MUESTRAS + 1)) + 3, 'seconds', function()
    dfhack.world.SetPauseState(true)          -- red de seguridad
end)