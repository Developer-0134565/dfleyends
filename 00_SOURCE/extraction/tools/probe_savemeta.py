#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 6 -- confirm save metadata (fortress name / world name).
Reads ONLY the decompressed .bin produced outside region1.
The candidate block sits at ~208,335,000 .. 208,342,000 of the payload.
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")


def main():
    d = open(BLOB, "rb").read()
    print("=" * 78)
    print("SAVE METADATA BLOCK  208,335,000 .. 208,342,000")
    print("=" * 78)
    off = 208_335_000
    end = 208_342_000
    for r in range(0, end - off, 16):
        c = d[off + r:off + r + 16]
        if not c:
            break
        print(f"{off+r:>12,}  " + " ".join(f"{x:02x}" for x in c).ljust(47)
              + "  " + "".join(chr(x) if 32 <= x < 127 else "." for x in c))

    print("\n" + "=" * 78)
    print("DECODED CANDIDATE FIELDS (read as: skip N, u16 len, ascii)")
    print("=" * 78)
    # show u32s immediately preceding each candidate string
    for target in (208_335_658, 208_341_392, 208_341_557):
        (ln,) = struct.unpack_from("<H", d, target)
        s = d[target + 2: target + 2 + ln].decode("latin-1")
        print(f"\n-- string @{target:,}: {s!r} (len={ln})")
        back = d[target - 48: target]
        u = [struct.unpack_from("<i", back, i)[0] for i in range(0, 48, 4)]
        print("   preceding 12 x i32:", u)


if __name__ == "__main__":
    main()