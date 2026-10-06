-- P1.5 :: reconocimiento del territorio observable. SOLO LECTURA.
-- Para cada categoria: que API existe, que devuelve, y si el mundo responde.
-- No se inventa nada: lo que no existe se marca ERROR / no.

local SALIDA = _G.DFCHRON_OUT_SALIDA
local cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')
local tr = dfhack.translation.translateName

local f = assert(io.open(SALIDA, 'ab'))
local function w(s) f:write(s .. string.char(10)) end
local function sec(t) w('') w('## ' .. t) end
local function par(k, v) w(string.format('  %-30s %s', k, tostring(v))) end

-- Ejecuta fn y registra. Nunca lanza: un fallo es un DATO, no un error.
local function prueba(nombre, fn)
    local ok, v = pcall(fn)
    if ok then par(nombre, v)
    else par(nombre, 'ERROR: ' .. tostring(v):sub(1, 80)) end
end

local function miembros(t)
    local l = {} for k in pairs(t) do l[#l + 1] = k end
    table.sort(l) return table.concat(l, ', ')
end

sec('ENTORNO')
prueba('world_loaded', function() return dfhack.isWorldLoaded() end)
prueba('map_loaded', function() return dfhack.isMapLoaded() end)
prueba('fortress_mode', function() return dfhack.world.isFortressMode() end)
prueba('pause', function() return dfhack.world.ReadPauseState() end)

sec('MUNDO')
prueba('world_folder', function() return dfhack.world.ReadWorldFolder() end)
prueba('world_name', function() return cp.decode(tr(df.global.world.world_data.name)) end)
prueba('year', function() return dfhack.world.ReadCurrentYear() end)
prueba('month', function() return dfhack.world.ReadCurrentMonth() end)
prueba('day', function() return dfhack.world.ReadCurrentDay() end)
prueba('season', function() return df.global.cur_season end)
prueba('tick', function() return dfhack.world.ReadCurrentTick() end)
prueba('weather', function() return dfhack.world.ReadCurrentWeather() end)
prueba('civ_id_tipo', function() return type(df.global.civ.id) end)
prueba('num_etnias', function() return #df.global.world.race_creature end)
prueba('depth', function() return df.global.world.world_data.depth end)

sec('UNIDADES')
local u = dfhack.units.getCitizens()[1]
prueba('ciudadanos', function() return #dfhack.units.getCitizens() end)
prueba('nombre_u1', function() return cp.decode(tr(dfhack.units.getVisibleName(u))) end)
prueba('raza', function() return dfhack.units.getRaceName(u) end)
prueba('raza_legible', function() return dfhack.units.getRaceReadableName(u) end)
prueba('profesion', function() return dfhack.units.getProfessionName(u) end)
prueba('visible_por_jugador', function() return dfhack.units.isVisible(u) end)
prueba('sexo', function() return dfhack.units.isFemale(u) and 'F' or 'M' end)
prueba('posicion', function() return u.pos.x .. ',' .. u.pos.y .. ',' .. u.pos.z end)
prueba('edad', function() return math.floor(dfhack.units.getAge(u)) end)
prueba('es_ciudadano', function() return dfhack.units.isCitizen(u) end)
prueba('es_muerto', function() return dfhack.units.isDead(u) end)
prueba('estres', function() return dfhack.units.getStressCategory(u) end)
prueba('edad_api', function() return type(dfhack.units.getAge) end)

sec('FORTALEZA')
prueba('edificios', function() return #dfhack.buildings.listBuildings() end)
prueba('tipos_edificio', function() return #dfhack.buildings.getTypeList() end)
prueba('trabajos_activos', function() return #dfhack.job.listJobs() end)
prueba('designaciones', function() return #dfhack.designations.getCivilians() end)
prueba('burrows', function() return type(dfhack.burrows) end)
prueba('kitchen', function() return type(dfhack.kitchen) end)
prueba('miembros_buildings', function() return miembros(dfhack.buildings) end)
prueba('miembros_job', function() return miembros(dfhack.job) end)
sec('MAPA')
prueba('isValid_tiles', function()
    local n = 0
    for x = 0, 7 do for y = 0, 7 do for z = 0, 0 do
        if dfhack.maps.isValid(x, y, z) then n = n + 1 end
    end end end
    return n .. '/64 tiles validos' end)
prueba('getTileType', function() return tostring(dfhack.maps.getTileType(1, 1, 0)) end)
prueba('miembros_maps', function() return miembros(dfhack.maps) end)

sec('OBJETOS')
prueba('miembros_items', function() return miembros(dfhack.items) end)

sec('MILITAR')
prueba('miembros_military', function() return miembros(dfhack.military) end)

sec('HISTORIA / PERSISTENCIA')
prueba('miembros_persistent', function() return miembros(dfhack.persistent) end)
prueba('persistent_world', function() return tostring(dfhack.persistent.world) end)
prueba('miembros_event', function() return miembros(dfhack.event) end)

sec('PANTALLA / UI')
prueba('miembros_screen', function() return miembros(dfhack.screen) end)
prueba('miembros_gui', function() return miembros(dfhack.gui) end)
prueba('cur_view', function()
    local ok, v = pcall(function() return dfhack.screen.getCurViewID() end)
    return ok and v or 'ERROR' end)

f:close()
print('RECONOCIMIENTO completado')