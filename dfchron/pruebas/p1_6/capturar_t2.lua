-- P1.6 :: captura T2 aislada. SOLO LECTURA. No toca la pausa.
-- Se ejecuta con la partida YA pausada, tras el incidente documentado.

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.json = require('json')

_G.escribir_t2 = function()
    local races, profs = {}, {}
    local ok_l, lista = pcall(dfhack.units.getCitizens)
    if ok_l and lista then
        for i = 1, #lista do
            local u = lista[i]
            local ok1, r = pcall(dfhack.units.getRaceName, u)
            local ok2, p = pcall(dfhack.units.getProfessionName, u)
            r = (ok1 and r) or '?'
            p = (ok2 and p) or '?'
            races[r] = (races[r] or 0) + 1
            profs[p] = (profs[p] or 0) + 1
        end
    end
    local m = {
        etiqueta = 'T2_capturado_manual',
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
        paused = dfhack.world.ReadPauseState(),
        world_folder = dfhack.world.ReadWorldFolder(),
        game_year = dfhack.world.ReadCurrentYear(),
        game_month = dfhack.world.ReadCurrentMonth(),
        game_day = dfhack.world.ReadCurrentDay(),
        game_season = df.global.cur_season,
        weather = dfhack.world.ReadCurrentWeather(),
        fortress_mode = dfhack.world.isFortressMode(),
        citizens = (ok_l and lista) and #lista or nil,
        races = races,
        professions = profs,
        _diag_tick = dfhack.world.ReadCurrentTick(),
        nota = 'capturado tras pausar a mano; el temporizador de seguridad '
            .. 'estaba armado pero se supero su ventana de 45 s',
    }
    local fh = assert(io.open(_G.SALIDA, 'ab'))
    fh:write(_G.json.encode(m, { pretty = false }) .. '\n')
    fh:close()
end

_G.escribir_t2()