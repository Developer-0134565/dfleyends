#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 3b -- READ-ONLY survey of the other region1 files.
Opens every .dat strictly with mode 'rb'. Writes nothing into region1.
"""
import os
import glob
import zlib
import struct
import collections

REGION = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1"


def probe(path):
    with open(path, "rb") as f:
        head = f.read(64)
    with open(path, "rb") as f:
        blob = f.read()
    name = os.path.basename(path)
    z = (head[0] == 0x78 and len(head) > 1 and head[1] in (0x01, 0x5E, 0x9C, 0xDA))
    return name, len(blob), head, z, blob


def try_blocks(blob):
    """same container layout as world.sav: u32,u32 then {u32 len, zlib}"""
    if len(blob) < 8:
        return None
    try:
        v, fl = struct.unpack_from("<II", blob, 0)
    except struct.error:
        return None
    pos = 8
    total = 0
    n = 0
    sizes = collections.Counter()
    while pos + 4 <= len(blob) and n < 100000:
        (clen,) = struct.unpack_from("<I", blob, pos)
        pos += 4
        if clen == 0 or pos + clen > len(blob):
            break
        try:
            d = zlib.decompress(blob[pos:pos + clen])
        except Exception:
            return ("ERR", v, fl, n, total, pos, len(blob))
        pos += clen
        total += len(d)
        sizes[len(d)] += 1
        n += 1
    return ("OK", v, fl, n, total, pos, len(blob), sizes)


def main():
    print("=" * 78)
    print("REGION1 AUXILIARY FILE SURVEY  (read-only)")
    print("=" * 78)

    groups = collections.defaultdict(list)
    for p in glob.glob(os.path.join(REGION, "*.dat")):
        base = os.path.basename(p)
        kind = base.split("-")[0]
        groups[kind].append(p)

    for kind in sorted(groups):
        files = sorted(groups[kind])
        sizes = [os.path.getsize(p) for p in files]
        print(f"\n### {kind}  count={len(files)}  total={sum(sizes):,} bytes")
        print(f"    size range: {min(sizes):,} .. {max(sizes):,}")

        for p in files[:3]:
            name, ln, head, z, blob = probe(p)
            hexs = " ".join(f"{x:02x}" for x in head[:32])
            r = try_blocks(blob)
            print(f"    - {name}: {ln:,} bytes  zlib0={z}")
            print(f"        head: {hexs}")
            if r and r[0] == "OK":
                _, v, fl, n, total, pos, flen, sizes_c = r
                print(f"        u32={v} u32={fl} blocks={n} decomp_total={total:,} "
                      f"consumed={pos:,}/{flen:,} trailing={flen-pos:,} sizes={dict(list(sizes_c.items())[:3])}")
            elif r:
                print(f"        blockwalk: {r}")
            # raw ascii preview
            txt = "".join(chr(x) if 32 <= x < 127 else "." for x in blob[:80])
            print(f"        ascii: {txt}")

    print("\n### DONE")


if __name__ == "__main__":
    main()