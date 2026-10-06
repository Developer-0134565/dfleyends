-- ============================================================================
-- P1.5 :: cp437.lua -- Conversion CP437 -> UTF-8 determinista y verificable
-- ============================================================================
-- GENERADO AUTOMATICAMENTE por generar_cp437.py desde el CODEC CP437 de
-- Python. NO editar a mano: se regenera y se vuelve a probar.
--
-- Determinista : misma entrada -> misma salida, siempre.
-- Invertible   : cada byte 0x00-0xFF produce un caracter, nunca ninguno.
-- No inventa   : si un byte no tuviera tabla, decode() lo DECLARA con U+FFFD.
-- Conserva     : M.hex() siempre devuelve el crudo, para poder auditar.
--
-- P1.4         : translateName() devuelve CP437, no UTF-8. El ciudadano
--                S\x86kzul Tulonroder es "Sakzul" con 'a' con anillo:
--                en CP437, 0x86 = U+00E5. La 'e' acentuada es 0x82.
-- ============================================================================

local M = {}

local function utf8_char(cp)
    if cp < 0x80 then
        return string.char(cp)
    elseif cp < 0x800 then
        return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + (cp % 0x40))
    elseif cp < 0x10000 then
        return string.char(0xE0 + math.floor(cp / 0x1000),
                           0x80 + (math.floor(cp / 0x40) % 0x40),
                           0x80 + (cp % 0x40))
    end
    return nil
end

-- Tabla alta: indice i (1..128) -> byte 0x80 + (i - 1).
local CP437_ALTO = {
    0x00C7, 0x00FC, 0x00E9, 0x00E2, 0x00E4, 0x00E0, 0x00E5, 0x00E7,
    0x00EA, 0x00EB, 0x00E8, 0x00EF, 0x00EE, 0x00EC, 0x00C4, 0x00C5,
    0x00C9, 0x00E6, 0x00C6, 0x00F4, 0x00F6, 0x00F2, 0x00FB, 0x00F9,
    0x00FF, 0x00D6, 0x00DC, 0x00A2, 0x00A3, 0x00A5, 0x20A7, 0x0192,
    0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1, 0x00D1, 0x00AA, 0x00BA,
    0x00BF, 0x2310, 0x00AC, 0x00BD, 0x00BC, 0x00A1, 0x00AB, 0x00BB,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255D, 0x255C, 0x255B, 0x2510,
    0x2514, 0x2534, 0x252C, 0x251C, 0x2500, 0x253C, 0x255E, 0x255F,
    0x255A, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256C, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256B,
    0x256A, 0x2518, 0x250C, 0x2588, 0x2584, 0x258C, 0x2590, 0x2580,
    0x03B1, 0x00DF, 0x0393, 0x03C0, 0x03A3, 0x03C3, 0x00B5, 0x03C4,
    0x03A6, 0x0398, 0x03A9, 0x03B4, 0x221E, 0x03C6, 0x03B5, 0x2229,
    0x2261, 0x00B1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00F7, 0x2248,
    0x00B0, 0x2219, 0x00B7, 0x221A, 0x207F, 0x00B2, 0x25A0, 0x00A0,
}

local ALTO = {}
for i, cp in ipairs(CP437_ALTO) do ALTO[i] = utf8_char(cp) end

function M.es_ascii(s)
    if type(s) ~= 'string' then return false end
    for i = 1, #s do
        if string.byte(s, i) >= 0x80 then return false end
    end
    return true
end

function M.hex(s)
    local h = {}
    for i = 1, #s do
        h[#h + 1] = string.format('%02X', string.byte(s, i))
    end
    return table.concat(h)
end

function M.decode(s)
    if type(s) ~= 'string' then return nil end
    local out = {}
    for i = 1, #s do
        local b = string.byte(s, i)
        if b < 0x80 then
            out[#out + 1] = string.char(b)      -- ASCII: identidad
        else
            local c = ALTO[b - 0x7F]            -- 0x80 -> ALTO[1]
            if c == nil then
                out[#out + 1] = string.char(0xEF, 0xBF, 0xBD)  -- U+FFFD
            else
                out[#out + 1] = c
            end
        end
    end
    return table.concat(out)
end

function M.describir(s)
    if type(s) ~= 'string' then return nil end
    return { valor = M.decode(s), ascii = M.es_ascii(s),
             bytes_crudos = #s, hex_crudo = M.hex(s) }
end

function M.tamano_tabla()
    return #CP437_ALTO
end

return M
