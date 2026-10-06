-- P1.4 :: prueba del guardIAN de codificacion (SOLO LECTURA del juego).
-- Demuestra que un valor CP437 con bytes >= 0x80 NUNCA llega al JSONL crudo.
-- Escribe en la ruta de DFCHRON_OUT_SALIDA.

local SALIDA = _G.DFCHRON_OUT_SALIDA

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

-- Se recorren varios ciudadanos: basta con que UNO tenga tilde para que el
-- caso sea real. Se prueban todos y se informa de cuantos lo tienen.
local ciudad = dfhack.units.getCitizens()
local filas, con_tilde, ascii = {}, 0, 0

for i, u in ipairs(ciudad) do
    local crudo = dfhack.translation.translateName(
        dfhack.units.getVisibleName(u))
    if type(crudo) == 'string' then
        if solo_ascii(crudo) then ascii = ascii + 1 else con_tilde = con_tilde + 1 end
        filas[#filas + 1] = {
            index = i,
            bytes_crudos = #crudo,
            ascii = solo_ascii(crudo),
            valor_sanitizado = sanitizar(crudo),
        }
    end
end

local mundo = dfhack.translation.translateName(
    df.global.world.world_data.name)

local fh = assert(io.open(SALIDA, 'ab'))
fh:write('MUNDO ' .. sanitizar(mundo) .. string.char(10))
for _, f in ipairs(filas) do
    fh:write(string.format('U%02d bytes=%d ascii=%s valor=%s%s', f.index,
        f.bytes_crudos, tostring(f.ascii), f.valor_sanitizado,
        string.char(10)))
end
fh:close()

print(string.format(
    'ciudadanos=%d  ascii=%d  con_no_ascii=%d  mundo_bytes=%d',
    #ciudad, ascii, con_tilde, #mundo))