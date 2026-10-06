-- ============================================================================
-- P1.7 :: prototipo de extraccion cartografica (SOLO LECTURA)
-- ----------------------------------------------------------------------------
-- REGLAS QUE RESPETA
--   1. NO despausa la partida. NO usa dfhack.timeout.
--   2. NO invoca ninguna accion de escritura: de `actions` solo usa `callback`.
--      Las acciones `set_tiletype`, `designation`, `occupancy`, `construct` y
--      `resetTileAssignment` EXISTEN y NO se usan.
--   3. Solo escribe en DFCHRON_OUT, que debe estar en la carpeta aislada P1.7.
--   4. Un tile NO VISIBLE no se emite como conocimiento del jugador: va a un
--      canal diagnostico separado, marcado como tal.
--
-- FIRMA RESUELTA (P1.7)
--   dfhack.maps.forEachTile(bounds[, filter[, actions]])
--     bounds  = {x1,y1,z1,x2,y2,z2}  (tabla Lua simple; NO hace falta df.coord)
--     filter  = fn(x,y,z,block,localx,localy,tiletype)
--     actions = { callback = fn(...) }   <-- UNICA forma usada aqui
--     devuelve { scanned, matched, changed, constructed, aborted }
--
-- `changed` y `constructed` se comprueban al final: deben ser 0. Si no lo son,
-- el prototipo ha modificado el mundo y eso hay que verlo.
-- ============================================================================

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.json = require('json')

-- Origen de la muestra: la fortaleza. En P1.5 un ciudadano estaba en (105,82,172).
-- El area se recorta al mapa cargado por propia cuenta (documentado).
_G.BX = 104
_G.BY = 81
_G.BZ = 171
_G.EX = 108
_G.EY = 85
_G.EZ = 175

_G.f = assert(io.open(_G.SALIDA, 'ab'))
_G.seq = 0
_G.T0 = dfhack.getTickCount()

_G.w = function(m)
    _G.f:write(_G.json.encode(m, { pretty = false }) .. '\n')
end

_G.nombre_tipo = function(tt)
    if tt == nil then return nil end
    local ok, v = pcall(function() return df.tiletype[tt] end)
    return (ok and v) or nil
end

-- GUARDIAN DE TIPOS. `json.encode` ABORTA si recibe un `userdata`: se vio con
-- `getRegionBiome`, que devuelve un objeto `df.region`, no un numero. Sin este
-- filtro el prototipo entero fallaba al escribir la PRIMERA linea.
-- Solo se admiten primitivos. Un objeto nunca se emite: se declara `null`.
local function prim(v)
    local t = type(v)
    if v == nil then return nil end
    if t == 'number' or t == 'string' or t == 'boolean' then return v end
    return nil
end

-- Canal de conocimiento del JUGADOR.
_G.emite_conocimiento = function(x, y, z, block, lx, ly, tt)
    _G.seq = _G.seq + 1
    local vis = dfhack.maps.isTileVisible(x, y, z)
    local bioma, region, ok_b = pcall(dfhack.maps.getBiomeType, x, y, z)
    local reg = pcall(dfhack.maps.getRegionBiome, x, y, z)
    _G.w({
        observation_id = string.format('MAP-%06d', _G.seq),
        domain = 'tile',
        x = x, y = y, z = z,
        -- `block` llega como PUNTERO df.map_block (userdata). No es un numero
        -- y `json.encode` ABORTA con userdata. Se guardan solo primitivos.
        block_presente = (type(block) ~= 'nil' and type(block) ~= 'userdata'),
        block = prim(block),
        localx = prim(lx), localy = prim(ly),
        tiletype_num = prim(tt),
        tiletype_nombre = _G.nombre_tipo(tt),
        -- VISIBILIDAD: solo se emite si el juego dice que el jugador la ve.
        visible_para_jugador = vis,
        visibilidad = (vis == true) and 'VISIBLE' or 'NOT_VISIBLE',
        bioma_num = prim(bioma),
        -- `getRegionBiome` devuelve un OBJETEO df.region, no un numero. Se
        -- intenta extraer un identificador primitivo; si no, queda `null`.
        region_num = (reg and prim(select(2, pcall(function()
            return dfhack.maps.getRegionBiome(x, y, z).id end)))) or nil,
        observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
        host_ms = dfhack.getTickCount() - _G.T0,
        paused = dfhack.world.ReadPauseState(),
        provenance = {
            metodo = 'dfhack.maps.forEachTile(callback) + isTileVisible',
            api = 'dfhack.maps.isTileVisible / getBiomeType / getRegionBiome',
            df_version = tostring(dfhack.getDFVersion()),
            dfhack_version = tostring(dfhack.getDFHackVersion()),
            read_only = true,
        },
        validacion = 'OK',
    })
end

-- Canal DIAGNOSTICO: lo que el motor sabe y el jugador NO. Se marca de forma
-- inequivoca para que nunca pueda confundirse con conocimiento del jugador.
-- La mision P1.7 obliga: un NOT_VISIBLE no puede convertirse en conocimiento.
local n_diag = 0
_G.emite_diagnostico = function(x, y, z, block, lx, ly, tt)
    n_diag = n_diag + 1
    if n_diag <= 40 then        -- acotado: no quiero un JSONL gigante
        _G.w({
            observation_id = string.format('DIAG-%06d', n_diag),
            domain = 'tile_NO_VISIBLE',
            aviso = 'CANAL DIAGNOSTICO. NO es conocimiento del jugador. '
                .. 'Un valor NOT_VISIBLE no puede transformarse en '
                .. 'conocimiento del jugador ni en informacion negativa.',
            x = x, y = y, z = z,
            block_presente = (type(block) ~= 'nil' and type(block) ~= 'userdata'),
            block = prim(block),
            tiletype_num = prim(tt),
            tiletype_nombre = _G.nombre_tipo(tt),
            visible_para_jugador = false,
            visibilidad = 'NOT_VISIBLE',
            observed_at_host = os.date('!%Y-%m-%dT%H:%M:%SZ'),
            provenance = {
                metodo = 'dfhack.maps.isTileVisible',
                api = 'dfhack.maps.isTileVisible',
                df_version = tostring(dfhack.getDFVersion()),
                dfhack_version = tostring(dfhack.getDFHackVersion()),
                read_only = true,
            },
        })
    end
end

local n_tot = 0
local res = dfhack.maps.forEachTile(
    { _G.BX, _G.BY, _G.BZ, _G.EX, _G.EY, _G.EZ },
    nil,                                   -- sin filtro: todos los tiles
    { callback = function(x, y, z, block, lx, ly, tt)
        n_tot = n_tot + 1
        local vis = dfhack.maps.isTileVisible(x, y, z)
        if vis == true then
            _G.emite_conocimiento(x, y, z, block, lx, ly, tt)
        else
            _G.emite_diagnostico(x, y, z, block, lx, ly, tt)
        end
    end })

_G.w({
    evento = 'RESUMEN',
    bounds = { _G.BX, _G.BY, _G.BZ, _G.EX, _G.EY, _G.EZ },
    scanned = res.scanned, matched = res.matched,
    -- ESTOS DOS DEBEN SER 0. Si no lo son, el prototipo ha ESCRITO.
    changed = res.changed, constructed = res.constructed,
    aborted = res.aborted,
    tiles_visitados = n_tot,
    emitidos_como_conocimiento = _G.seq,
    emitidos_como_diagnostico = n_diag,
    paused_final = dfhack.world.ReadPauseState(),
    tick = dfhack.world.ReadCurrentTick(),
    solo_lectura_ok = (res.changed == 0 and res.constructed == 0),
})

_G.f:close()
print(string.format(
    'MAPA: scanned=%d conocimiento=%d diagnostico=%d changed=%d constructed=%d',
    res.scanned, _G.seq, n_diag, res.changed, res.constructed))