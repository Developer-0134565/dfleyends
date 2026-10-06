#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 5b -- targeted structural reads.

 (a) TAIL of world.sav payload  -> almost certainly df::cur_savegame metadata
     (save version, game mode, fortress name, world name, ...)
 (b) TRANSITION raws-text -> game-data
Reads only the .bin produced outside region1. Source file never opened for write.
"""
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")


def hexdump(data, off, n, width=16):
    rows = []
    for r in range(0, n, width):
        c = data[off + r: off + r + width]
        if not c:
            break
        rows.append(f"  {off+r:>12,}  " +
                    " ".join(f"{x:02x}" for x in c).ljust(width*3) + "  " +
                    "".join(chr(x) if 32 <= x < 127 else "." for x in c))
    return rows


def main():
    data = open(BLOB, "rb").read()
    n = len(data)
    print(f"blob {n:,}")

    print("\n" + "=" * 74)
    print("(a) TAIL REGION  (last 40 KB)")
    print("=" * 74)
    tail = n - 40000
    print("\n".join(hexdump(data, tail, 1600)))

    print("\n" + "=" * 74)
    print("(b) EVERY length-prefixed string in the last 64 KB")
    print("=" * 74)
    seg = data[-65536:]
    base = n - 65536
    for m in re.finditer(rb"[\x20-\x7e]{3,200}", seg):
        s = m.group().decode("latin-1")
        off = base + m.start()
        p = off - 2
        ln = None
        if p >= 0:
            (v,) = struct.unpack_from("<H", data, p)
            if v == len(s):
                ln = v
        print(f"  @{off:>12,}  {'LP len=%d' % ln if ln is not None else 'raw   '}  {s[:70]}")

    print("\n" + "=" * 74)
    print("(c) TRANSITION raws-text -> game data (around 6,440,000)")
    print("=" * 74)
    print("\n".join(hexdump(data, 6440000, 1200)))

    print("\n" + "=" * 74)
    print("(d) last 3000 length-prefixed strings BEFORE the binary region")
    print("=" * 74)
    pat = re.compile(rb"[\x04-\xdc][\x20-\x7e]{4,220}")
    lst = []
    for m in pat.finditer(data, 0, 6_600_000):
        ln = m.end() - m.start()
        if m.start() >= 2:
            (v,) = struct.unpack_from("<H", data, m.start() - 2)
            if v == ln:
                lst.append((m.start() - 2, ln, m.group().decode("latin-1")))
    for off, ln, s in lst[-120:]:
        print(f"  @{off:>10,} len={ln:>4}  {s[:80]}")


if __name__ == "__main__":
    main()