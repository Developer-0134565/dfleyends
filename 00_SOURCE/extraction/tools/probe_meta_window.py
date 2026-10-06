#!/usr/bin/env python3
"""DF-Chronicles :: narrow metadata window 208,335,400..208,335,800."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")
d = open(BLOB, "rb").read()
off, end = 208_335_400, 208_335_800
for r in range(0, end - off, 16):
    c = d[off + r:off + r + 16]
    if not c:
        break
    print(f"{off+r:>12,}  " + " ".join(f"{x:02x}" for x in c).ljust(47)
          + "  " + "".join(chr(x) if 32 <= x < 127 else "." for x in c))
print()
off, end = 208_341_300, 208_341_600
for r in range(0, end - off, 16):
    c = d[off + r:off + r + 16]
    if not c:
        break
    print(f"{off+r:>12,}  " + " ".join(f"{x:02x}" for x in c).ljust(47)
          + "  " + "".join(chr(x) if 32 <= x < 127 else "." for x in c))