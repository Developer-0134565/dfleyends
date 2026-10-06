-- ============================================================================
-- P1.4 :: OBSERVADOR EXPERIMENTAL (prototipo AISLADO)
-- ----------------------------------------------------------------------------
-- SOLO LECTURA del juego. No escribe en la partida. No altera el estado.
-- Escribe UNICAMENTE en DFCHRON_OUT, que debe estar en la carpeta aislada.
--
-- Uso (PowerShell, con el juego ya arrancado):
--   dfhack-run lua "DFCHRON_OUT='C:/.../observaciones.jsonl'; \
--                   dofile('C:/.../observador.lua')"
--
-- QUE ES Y QUE NO ES `observation_id`
-- ------------------------------------
-- Contador MONOTONICO de lineas dentro de ESTE fichero de salida.
-- NO es identidad de mundo. NO es version del estado. NO es un reloj.
-- Cada linea trae su propio `observed_at` real.
--
-- PERIMETRO DE CONOCIMIENTO
-- -------------------------
-- Cada hecho lleva su clasificacion de visibilidad. Solo VISIBLE y
-- VISIBLE_CONDITIONAL pueden entrar en el perimetro. No se inventa ningun
-- valor: si una API falla, el valor es null y la observacion lo declara.
-- ============================================================================

local SALIDA = DFCHRON_OUT
if type(SALIDA) ~= 'string' or SALIDA == '' then
    print('OBSERVADOR ABORTADO: falta DFCHRON_OUT (carpeta de salida).')
    return
end

local json = require('json')
local tr = dfhack.translation.translateName
-- ---------------------------------------------------------------------------
-- CODIFICACION: un hallazgo real de esta mision
-- ---------------------------------------------------------------------------
-- `dfhack.translation.translateName()` devuelve texto CP437, NO UTF-8.
-- Comprobado: un ciudadano se escribe como `S\x86kzul`, y 0x86 es la 'e'
-- acentuada en CP437. Tal cual, ese texto ROMPE la exigencia de "codificacion
-- UTF-8" del JSONL. Y un nombre de enano fantasy esta lleno de tildes, asi que
-- no es un caso teorico.
--
-- DECISION DEL PROTOTIPO: no escribir bytes que no son UTF-8, y no fingir que
-- si lo son. Si un valor trae bytes >= 0x80, se marca de forma EXPLICITA como
-- __NO_UTF8_PENDIENTE con su valor hexadecimal, que si es valido y reversible.
-- No se descarta la informacion ni se inventa una conversion a medias: una
-- tabla parcial de CP437 corromperia en silencio otros caracteres.
--
-- QUE FALTA (ver P1.4/09_LIMITACIONES_Y_DEUDAS.md): la tabla completa
-- CP437->UTF-8, para poder incluir nombres individuales con tildes.
local function solo_ascii(s)
    for i = 1, #s do
        if string.byte(s, i) >= 0x80 then return false end
    end
    return true
end

local function a_hex(s)
    local h = ''
    for i = 1, #s do h = h .. string.format('%02X', string.byte(s, i)) end
    return h
end

local function sanitizar(v)
    if type(v) ~= 'string' then return v end
    if solo_ascii(v) then return v end
    return '__NO_UTF8_PENDIENTE(cp437):' .. a_hex(v)
end

local function segura(fn, por_defecto)
    local ok, v = pcall(fn)
    if ok and v ~= nil then return v end
    return por_defecto          -- nil explicito: NUNCA un valor inventado
end

local function fact(nombre, valor, visibilidad, mecanismo, nota)
    return { name = nombre,
             value = (valor == nil) and json.null or sanitizar(valor),
             visibility = visibilidad,
             mechanism = mecanismo,
             read_only = true,
             note = nota }
end

-- ------------------------------------------- contador monotono por fichero
-- BINARIO: en Windows, el modo texto traduciria LF a CRLF y romperia el
-- requisito de una observacion por linea. Se lee en 'rb' por lo mismo.
local function siguiente_id(ruta)
    local n = 0
    local f = io.open(ruta, 'rb')
    if f then
        for linea in f:lines() do
            if #(linea) > 0 then n = n + 1 end
        end
        f:close()
    end
    return n + 1
end

local base = siguiente_id(SALIDA)
local ahora = os.date('!%Y-%m-%dT%H:%M:%SZ')
local mundo_cargado = segura(function() return dfhack.isWorldLoaded() end, false)
local mapa_cargado  = segura(function() return dfhack.isMapLoaded() end, false)

local comun = {
    schema_version = 1, source = 'dfhack',
    dfhack_version = tostring(dfhack.getDFHackVersion()),
    df_version = tostring(dfhack.getDFVersion()),
    observed_at = ahora,        -- reloj REAL de captura, UTC
    world_loaded = mundo_cargado,
    map_loaded = mapa_cargado,
}

local hechos = {}

-- Sin mundo cargado NO se inventa nada: se registra la ausencia y se sale.
if not mundo_cargado then
    hechos[#hechos + 1] = fact('world_loaded', false, 'VISIBLE',
        'dfhack.isWorldLoaded()',
        'No hay mundo cargado: no se emite ningun dato de contenido.')
    local fh = assert(io.open(SALIDA, 'ab'))
    fh:write(json.encode({ schema_version = 1, source = 'dfhack',
        observed_at = ahora, status = 'NO_WORLD_LOADED', facts = hechos },
        { pretty = false }) .. '\n')
    fh:close()
    print('OBSERVADOR: sin mundo cargado. Ausencia registrada.')
    return
end

-- ---- B1 Mundo y calendario (APIs de LECTURA de dfhack.world) ----
hechos[#hechos + 1] = fact('world_name',
    segura(function() return tr(df.global.world.world_data.name) end),
    'VISIBLE', 'dfhack.translation.translateName(world_data.name)',
    'El jugador ve el nombre de su mundo al cargar la partida.')

hechos[#hechos + 1] = fact('game_year',
    segura(function() return dfhack.world.ReadCurrentYear() end),
    'VISIBLE', 'dfhack.world.ReadCurrentYear()',
    'La interfaz muestra el anio en curso.')

hechos[#hechos + 1] = fact('game_month',
    segura(function() return dfhack.world.ReadCurrentMonth() end),
    'VISIBLE', 'dfhack.world.ReadCurrentMonth()',
    'La interfaz muestra el mes en curso.')

hechos[#hechos + 1] = fact('game_day',
    segura(function() return dfhack.world.ReadCurrentDay() end),
    'VISIBLE', 'dfhack.world.ReadCurrentDay()',
    'La interfaz muestra el dia del mes.')

hechos[#hechos + 1] = fact('game_season',
    segura(function() return df.global.cur_season end),
    'VISIBLE', 'df.global.cur_season',
    'La estacion se ve al seleccionar una casilla o en la ficha de fortaleza.')

hechos[#hechos + 1] = fact('game_tick',
    segura(function() return dfhack.world.ReadCurrentTick() end),
    'NO_VISIBLE', 'dfhack.world.ReadCurrentTick()',
    'Contador interno del ano. El jugador ve FECHA (anio/mes/dia), nunca un '
    .. 'tick crudo. Se registra por trazabilidad tecnica, no como '
    .. 'conocimiento del jugador.')

hechos[#hechos + 1] = fact('weather',
    segura(function() return dfhack.world.ReadCurrentWeather() end),
    'VISIBLE', 'dfhack.world.ReadCurrentWeather()',
    'El clima se muestra en la interfaz de la fortaleza.')

hechos[#hechos + 1] = fact('pause_state',
    segura(function() return dfhack.world.ReadPauseState() end),
    'VISIBLE', 'dfhack.world.ReadPauseState()',
    'El jugador controla la pausa y sabe si esta en pausa.')

hechos[#hechos + 1] = fact('fortress_mode',
    segura(function() return dfhack.world.isFortressMode() end),
    'VISIBLE_CONDITIONAL', 'dfhack.world.isFortressMode()',
    'Depende del modo de juego en el que este la partida.')
-- ---- Identidad tecnica (NO es conocimiento del jugador) ----
hechos[#hechos + 1] = fact('world_folder',
    segura(function() return dfhack.world.ReadWorldFolder() end),
    'VISIBLE_CONDITIONAL', 'dfhack.world.ReadWorldFolder()',
    'Nombre de carpeta del save. El jugador lo ve si abre sus carpetas de '
    .. 'partida, pero no es conocimiento del mundo: se usa como identidad '
    .. 'tecnica para NO mezclar mundos.')

-- ---- B2/B3 Fortaleza y unidades ----
local ciudadanos = segura(function()
    return dfhack.units.getCitizens()
end, {})

hechos[#hechos + 1] = fact('citizens_count', #ciudadanos,
    'VISIBLE', '#dfhack.units.getCitizens()',
    'La fortaleza muestra su poblacion.')

-- Muestra AGREGADA de la poblacion: nada de identificadores individuales.
local profesiones, razas = {}, {}
for _, u in ipairs(ciudadanos) do
    local pr = segura(function() return dfhack.units.getProfessionName(u) end, '?')
    local ra = segura(function() return dfhack.units.getRaceName(u) end, '?')
    profesiones[pr] = (profesiones[pr] or 0) + 1
    razas[ra] = (razas[ra] or 0) + 1
end
hechos[#hechos + 1] = fact('citizen_professions', profesiones,
    'VISIBLE', 'dfhack.units.getProfessionName(getCitizens())',
    'Lista de trabajos de la fortaleza; la interfaz los muestra.')
hechos[#hechos + 1] = fact('citizen_races', razas,
    'VISIBLE', 'dfhack.units.getRaceName(getCitizens())',
    'Especie de la poblacion; visible en la interfaz.')

-- --------------------------------------------------------- ESCRITURA (a disco)
-- Un FALLO DEBE SER EXPLICITO: si no se puede escribir, el observador falla
-- en voz alta en vez de fingir que la observacion existe.
-- MODO BINARIO + `pretty=false`: `json.encode` pone tabuladores y saltos de
-- linea por defecto, lo que produce un fichero que NO es JSONL. Sin esto, cada
-- observacion ocupaba 22 lineas. Consta en evidencias/DEFECTO_jsonl_no_valido.txt
local fh, err = io.open(SALIDA, 'ab')
if not fh then
    print('OBSERVADOR ABORTADO: no se pudo abrir ' .. SALIDA
          .. ' -> ' .. tostring(err))
    return
end

local n = 0
for _, h in ipairs(hechos) do
    local env = {}
    for k, v in pairs(comun) do env[k] = v end
    env.observation_id = string.format('%06d', base + n)
    env.subject = { type = 'world', id = comun.world_folder }
    env.fact = h
    fh:write(json.encode(env, { pretty = false }) .. '\n')
    n = n + 1
end
fh:close()

print(string.format('OBSERVADOR: %d observaciones escritas en %s (base %06d, %s)',
      n, SALIDA, base, ahora))