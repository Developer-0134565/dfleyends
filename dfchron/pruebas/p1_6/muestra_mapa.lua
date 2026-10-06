-- P1.6 :: Fase B - muestra cartografica. SOLO LECTURA. No toca tiles.
-- NOTA DE ALCANCE: `addItemSpatter`, `setTileAquifer`, `removeTileAquifer` y
-- `spawnFlow` existen y SON DE ESCRITURA. No se invocan. Se listan para que
-- conste que se los conoce y se los descarta deliberadamente.

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.json = require('json')
_G.f = assert(io.open(_G.SALIDA, 'ab'))
_G.w = function(m)
    _G.f:write(_G.json.encode(m, { pretty = false }) .. '\n')
end

local M = dfhack.maps

_G.w({ evento = 'DIMENSIONES' })
-- `getSize()` NO devuelve una tabla en esta version (fallo real observado:
-- "attempt to index a number value"). Se registra tal cual y se intentan
-- variantes, sin inventar el formato.
local ok_sz, sz = pcall(M.getSize)
_G.w({ evento = 'getSize', ok = ok_sz, tipo = type(sz), valor = tostring(sz) })
for _, n2 in ipairs({ 'getBlockSize', 'getMapSize' }) do
    local o2, v2 = pcall(function() return M[n2]() end)
    _G.w({ probe = n2, ok = o2, tipo = type(v2), valor = tostring(v2) })
end
local okx, bx = pcall(function() return df.global.world.world_data.end_block[1] end)
local oky, by = pcall(function() return df.global.world.world_data.end_block[2] end)
local okz, bz = pcall(function() return df.global.world.world_data.end_block[3] end)
_G.w({ evento = 'end_block', ok = { bx, by, bz }, valor = { tostring(bx), tostring(by), tostring(bz) } })

_G.w({ evento = 'VALIDACION_POSICIONES' })
local pruebas = {
    { 0, 0, 0 }, { 1, 1, 1 }, { -1, 0, 0 }, { 0, -1, 0 }, { 0, 0, -1 },
    { 99999, 0, 0 }, { 0, 99999, 0 },
}
for _, p in ipairs(pruebas) do
    local okv, v = pcall(M.isValidTilePos, p[1], p[2], p[3])
    _G.w({ x = p[1], y = p[2], z = p[3], ok = okv, valido = v })
end

-- FIRMA REAL: `forEachTile(coord, callback)` necesita un puntero `coord` como
-- PRIMER argumento. Descubierto al ejecutar: pasándole solo el callback falla
-- con "bad argument #1 to 'forEachTile' (pointer to coord expected)".
_G.w({ evento = 'MUESTRA_TILES' })
local n = 0
local ok_iter, err_iter = pcall(M.forEachTile, df.coord.new(0, 0, 0),
    function(x, y, z)
    n = n + 1
    if n <= 8 then
        local ttype = M.getTileType(x, y, z)
        local biome = M.getBiomeType(x, y, z)
        local flags = M.getTileFlags(x, y, z)
        local visible = M.isTileVisible(x, y, z)
        local region = M.getRegionBiome(x, y, z)
        local lf = M.getLocalInitFeature(x, y, z)
        local gf = M.getGlobalInitFeature(x, y, z)
        _G.w({
            x = x, y = y, z = z,
            tile_type = ttype,
            tile_flags = flags,
            bioma = biome,
            region = region,
            visible_por_jugador = visible,
            local_feature = lf,
            global_feature = gf,
        })
    end
end)
_G.w({ evento = 'ITERACION', ok = ok_iter, error = tostring(err_iter) })
_G.w({ evento = 'CONTEO_TILES', total = n })

_G.w({ evento = 'APIS_ESCRITURA_DESCARTADAS',
       lista = { 'addItemSpatter', 'addMaterialSpatter', 'setTileAquifer',
                 'removeTileAquifer', 'setTileAssignment', 'spawnFlow',
                 'enableBlockUpdates', 'ensureTileBlock',
                 'resetTileAssignment' } })

_G.f:close()
print('MUESTRA_MAPA: ' .. tostring(n) .. ' tiles recorridos')