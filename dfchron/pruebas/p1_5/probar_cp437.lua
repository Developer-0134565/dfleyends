-- P1.5 :: prueba de la conversion CP437 -> UTF-8 (no necesita partida).
-- Emite los 128 bytes altos y casos compuestos. La comparacion la hace
-- Python contra SU PROPIO codec cp437: dos implementaciones independientes
-- tienen que coincidir byte a byte.

local SALIDA = _G.DFCHRON_OUT_SALIDA
local cp = dofile('C:/Users/Missingn0/Documents/Dwarf Fortress/DF-Chronicles/dfchron/pruebas/p1_5/cp437.lua')

local f = assert(io.open(SALIDA, 'ab'))
local function w(s) f:write(s .. string.char(10)) end

w('TABLA_ENTRADAS ' .. tostring(cp.tamano_tabla()))

-- Barrido completo del rango alto: UNA LINEA por byte.
w('BARRIDO')
for b = 0x80, 0xFF do
    local d = cp.decode(string.char(b))
    w(string.format('  %02X %s', b, cp.hex(d)))
end

-- Casos compuestos: los bytes se escriben crudos y se comparan fuera.
w('CASOS')
local compuestos = {
    string.char(0x53,0x86,0x6B,0x7A,0x75,0x6C,0x20,0x54),   -- S?kzul T
    string.char(0x4E,0xF1),                                 -- N?
    string.char(0xFC,0xF6,0xE1,0xF1,0xE7),                  -- uo an?c
    'ASCII_puro_123',                                       -- sin cambios
    '',                                                     -- vacio
}
for i, c in ipairs(compuestos) do
    w(string.format('  C%d %s -> %s', i, cp.hex(c), cp.hex(cp.decode(c))))
end

-- Determinismo: dos llamadas seguidas, mismo resultado.
local a = cp.decode(compuestos[1])
local b = cp.decode(compuestos[1])
w('DETERMINISTA ' .. tostring(a == b))

-- ASCII debe ser identidad exacta.
w('ASCII_IDENTIDAD ' .. tostring(cp.decode('ABC xyz 123') == 'ABC xyz 123'))

f:close()
print('CP437: tabla=' .. cp.tamano_tabla() .. ' casos=' .. #compuestos)