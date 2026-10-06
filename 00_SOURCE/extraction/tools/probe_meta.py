#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 5c -- identify the save metadata block.
Near the end of the payload we saw: "53.16", "DWARF", "GOBLIN", "HUMAN",
"Give Me the Fortress", "A Record of the Forest".
This probe dumps that neighbourhood in full so it can be interpreted.
"""
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")


def hd(data, off, n, width=16):
    rows = []
    for r in range(0, n, width):
        c = data[off + r:off + r + width]
        if not c:
            break
        rows.append(f"{off+r:>12,}  " +
                    " ".join(f"{x:02x}" for x in c).ljust(width * 3) + "  " +
                    "".join(chr(x) if 32 <= x < 127 else "." for x in c))
    return rows


def main():
    data = open(BLOB, "rb").read()
    n = len(data)

    print("=" * 76)
    print("SAVE METADATA REGION  (~208,333,000 - end)")
    print("=" * 76)
    print("\n".join(hd(data, 208_333_000, 700)))

    print("\n" + "=" * 76)
    print("ALL length-prefixed strings in the last 2 MB")
    print("=" * 76)
    seg = data[-2_000_000:]
    base = n - 2_000_000
    pat = re.compile(rb"[\x20-\x7e]{2,300}")
    for m in pat.finditer(seg):
        s = m.group().decode("latin-1")
        off = base + m.start()
        p = off - 2
        tag = "     "
        if p >= 0:
            (v,) = struct.unpack_from("<H", data, p)
            if v == len(s):
                tag = f"LP{v:<4}"
        print(f"  {off:>12,} {tag}  {s[:90]}")

    print("\n" + "=" * 76)
    print("STRICT length-prefixed scan over WHOLE blob, grouped by neighbourhood")
    print("=" * 76)
    lp = re.compile(rb"[\x04-\xdc][\x20-\x7e]{3,220}")
    cnt = 0
    buckets = {}
    for m in lp.finditer(data):
        ln = m.end() - m.start()
        if m.start() < 2:
            continue
        (v,) = struct.unpack_from("<H", data, m.start() - 2)
        if v != ln:
            continue
        cnt += 1
        b = m.start() // (10 << 20)
        buckets[b] = buckets.get(b, 0) + 1
    print(f"  total strict LP strings: {cnt:,}")
    for b in sorted(buckets):
        print(f"    {b*10:>5}-{b*10+10:<5} MB : {buckets[b]:>8,}")


if __name__ == "__main__":
    main()