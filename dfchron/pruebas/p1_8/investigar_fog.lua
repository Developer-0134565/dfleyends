-- ============================================================================
-- P1.8 (continuacion) :: A1 -- investigacion ACOTADA de fog_of_war
-- ----------------------------------------------------------------------------
-- PREGUNTA: ¿existe alguna observacion que permita distinguir dos tiles con
-- el MISMO estado de visibilidad actual pero DISTINTO estado historico?
--
-- REGLAS: solo lectura. Sin dfhack.timeout. Sin despausar. Sin escribir.
-- Las acciones de forEachTile que modifican el mapa NO se usan: solo `callback`.
--
-- TOPE DURO: si el numero de tiles supera el limite, el script ABORTA. El
-- incidente anterior (16,7 M tiles) vino de un cubo abierto sin cota.
-- ============================================================================

_G.SALIDA = _G.DFCHRON_OUT_SALIDA
_G.json = require('json')
_G.LIMITE = 20000

_G.f = assert(io.open(_G.SALIDA, 'ab'))
_G.n = 0
_G.abortado = false

_G.w = function(m) _G.f:write(_G.json.encode(m, { pretty = false }) .. '\n') end

-- Cajas pequenas alrededor de la fortaleza. La fortaleza esta en
-- (104..108, 81..85, 171..175). Seis cajas de 5x5x5 = 750 tiles en total.
_G.CAJAS = {
    { 'fortaleza',      104, 81, 171, 108, 85, 175 },
    { 'arriba_z+2',     104, 81, 203, 108, 85, 207 },
    { 'abajo_z-2',      104, 81, 139, 108, 85, 143 },
    { 'este_x+2',       132, 81, 171, 136, 85, 175 },
    { 'oeste_x-2',       72, 81, 171,  76, 85, 175 },
    { 'norte_y+2',      104, 89, 171, 108, 93, 175 },
}

-- Registro por tile: TODO lo necesario para interpretar la semántica.
-- NO se interpreta aquí: se recogen datos y se concluye fuera.
_G.distintos = {}

for _, caja in ipairs(_G.CAJAS) do
    local etq, x1, y1, z1, x2, y2, z2 = caja[1], caja[2], caja[3], caja[4],
                                          caja[5], caja[6], caja[7]
    local resumen = { caja = etq, bounds = { x1, y1, z1, x2, y2, z2 },
                      vistos = 0, por_fog = {} }

    dfhack.maps.forEachTile({ x1, y1, z1, x2, y2, z2 }, nil, {
        callback = function(x, y, z, block, lx, ly, tt)
            if _G.abortado then return false end      -- aborta el barrido
            _G.n = _G.n + 1
            if _G.n > _G.LIMITE then
                _G.abortado = true
                return false
            end
            local fog = block.fog_of_war[lx][ly]
            local vis = dfhack.maps.isTileVisible(x, y, z)
            resumen.vistos = resumen.vistos + 1
            local k = tostring(fog)
            resumen.por_fog[k] = (resumen.por_fog[k] or 0) + 1
            _G.distintos[k] = (_G.distintos[k] or 0) + 1
            -- Solo se emiten los valores de fog MAS RAROS: si todo es 0, el
            -- detalle por tile no aporta nada y ahogaria el fichero.
            if fog ~= 0 then
                _G.w({
                    etiqueta = 'TILE_FOG_NO_CERO',
                    caja = etq, x = x, y = y, z = z,
                    localx = lx, localy = ly,
                    fog_of_war = fog,
                    isTileVisible = vis,
                    tiletype = tt,
                    paused = dfhack.world.ReadPauseState(),
                })
            end
        end })

    _G.w({ etiqueta = 'RESUMEN_CAJA', caja = etq,
           bounds = { x1, y1, z1, x2, y2, z2 },
           tiles = resumen.vistos, por_fog_of_war = resumen.por_fog })
end

-- PREGUNTA CENTRAL: ¿alguna combinacion (fog, visible) aparece?
_G.w({ etiqueta = 'DISTRIBUCION_GLOBAL',
       valores_fog_declarados = _G.distintos,
       total_tiles = _G.n,
       abortado_por_limite = _G.abortado })

_G.w({ etiqueta = 'FIN',
       paused = dfhack.world.ReadPauseState(),
       tick = dfhack.world.ReadCurrentTick(),
       total_tiles = _G.n,
       abortado = _G.abortado })

_G.f:close()
print(string.format('FOG: tiles=%d  abortado=%s', _G.n, tostring(_G.abortado)))