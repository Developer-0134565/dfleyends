-- Sonda de entorno: SOLO LECTURA. No escribe nada en el juego.
-- Uso: dfhack-run lua "dofile('C:/.../sonda_entorno.lua')"
-- API descubierta por INTROSPECCION en DFHack 53.16-r2rc2, no asumida.

local out = {}
local function p(fmt, ...)
    out[#out + 1] = string.format(fmt, ...)
end
local function t(name, fn)
    local ok, v = pcall(fn)
    p("%-22s = %s", name, ok and tostring(v) or ("ERR:" .. tostring(v)))
end

p("DF_VERSION      = %s", tostring(dfhack.getDFVersion()))
p("DFHACK_VERSION  = %s", tostring(dfhack.getDFHackVersion()))
p("DFHACK_BUILD    = %s", tostring(dfhack.getDFHackBuildID()))

-- ---- Estado de carga (funciones de primer nivel en 53.16) ----
t("isWorldLoaded", function() return dfhack.isWorldLoaded() end)
t("isMapLoaded", function() return dfhack.isMapLoaded() end)
t("isSiteLoaded", function() return dfhack.isSiteLoaded() end)
t("isFortressMode", function() return dfhack.world.isFortressMode() end)
t("isAdventureMode", function() return dfhack.world.isAdventureMode() end)
t("isLegends", function() return dfhack.world.isLegends() end)

-- ---- Calendario y reloj: APIs LECTURA de dfhack.world ----
t("ReadCurrentYear", function() return dfhack.world.ReadCurrentYear() end)
t("ReadCurrentMonth", function() return dfhack.world.ReadCurrentMonth() end)
t("ReadCurrentDay", function() return dfhack.world.ReadCurrentDay() end)
t("ReadCurrentTick", function() return dfhack.world.ReadCurrentTick() end)
t("ReadCurrentWeather", function() return dfhack.world.ReadCurrentWeather() end)
t("ReadPauseState", function() return dfhack.world.ReadPauseState() end)
t("ReadWorldFolder", function() return dfhack.world.ReadWorldFolder() end)

-- ---- Estructuras: blindadas, porque el layout cambia entre versiones ----
local function campo(nombre, fn)
    local ok, v = pcall(fn)
    p("%-22s = %s", nombre, ok and tostring(v) or ("ERR"))
end

campo("cur_season", function() return df.global.cur_season end)
campo("cur_year_total_ticks", function() return df.global.cur_year_total_ticks end)
campo("gview_mode", function() return df.global.gview_mode end)
campo("world.cur_year", function() return df.global.world.cur_year end)
campo("world.cur_year_tick", function() return df.global.world.cur_year_tick end)
campo("world_data.name", function() return df.global.world.world_data.name end)
campo("world_data_presente", function()
    return df.global.world.world_data and "si" or "no"
end)

-- ---- Unidades ----
t("citizens_count", function() return #dfhack.units.getCitizens() end)
t("active_count", function() return #dfhack.units.getActive() end)

print(table.concat(out, "\n"))