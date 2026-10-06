#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 2b -- structural analysis of the decompressed stream
(STRICTLY READ-ONLY on the source; writes only to 00_SOURCE/extraction/raw/)

Confirms block geometry and maps the TEXT<->BINARY layout of the payload.
"""
import os
import re
import struct
import zlib
import json
import datetime
import collections

SRC = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw")
LOG = os.path.join(HERE, "_analyze_log.txt")

_lines = []


def p(*a):
    s = " ".join(str(x) for x in a)
    _lines.append(s)


def read_blocks(path):
    with open(path, "rb") as f:
        raw = f.read()
    version, flag = struct.unpack_from("<II", raw, 0)
    pos = 8
    sizes = []
    chunks = []
    while pos + 4 <= len(raw):
        (clen,) = struct.unpack_from("<I", raw, pos)
        pos += 4
        if clen == 0:
            break
        data = raw[pos:pos + clen]
        pos += clen
        try:
            dec = zlib.decompress(data)
        except Exception as e:
            p(f"  !! block {len(chunks)} decompress error: {e}")
            chunks.append(b"")
            sizes.append(0)
            continue
        chunks.append(dec)
        sizes.append(len(dec))
    return raw, version, flag, sizes, chunks, pos


def main():
    os.makedirs(OUT, exist_ok=True)
    raw, version, flag, sizes, chunks, pos = read_blocks(SRC)

    p("=" * 78)
    p("DF-Chronicles  |  world.sav container analysis  (READ-ONLY)")
    p("=" * 78)
    p(f"source          : {SRC}")
    p(f"source size     : {len(raw):,} bytes")
    p(f"source mtime    : {datetime.datetime.fromtimestamp(os.stat(SRC).st_mtime)}")
    p(f"version field   : {version}   (u32 @0)")
    p(f"flag field      : {flag}   (u32 @4)")
    p(f"block count     : {len(chunks):,}")
    p(f"bytes consumed  : {pos:,} / {len(raw):,}   trailing = {len(raw)-pos}")
    p(f"uncompressed    : {sum(sizes):,} bytes")

    hist = collections.Counter(sizes)
    p("\n-- uncompressed block-size histogram --")
    for sz, n in hist.most_common(10):
        p(f"   size {sz:>10,}  x {n:>7,}")
    p(f"   distinct sizes: {len(hist)}")
    if len(hist) <= 5:
        p(f"   => FIXED-SIZE BLOCKS, last block is the remainder "
          f"({sizes[-1]:,} of {max(sizes):,})")

    # join
    blob = b"".join(chunks)
    with open(os.path.join(OUT, "world_decompressed.bin"), "wb") as g:
        g.write(blob)
    p(f"\nwrote world_decompressed.bin ({len(blob):,} bytes)")

    # ---- per-block text ratio ----
    def ratio(d):
        if not d:
            return 0.0
        return sum(1 for x in d if 32 <= x < 127 or x in (9, 10, 13)) / len(d)

    p("\n-- TEXT/BINARY RUN MAP (threshold: >85% printable = TEXT) --")
    runs = []
    prev = None
    start = 0
    for i, c in enumerate(chunks):
        cur = "TEXT" if ratio(c) > 0.85 else "BIN"
        if cur != prev:
            if prev is not None:
                runs.append((prev, start, i - 1, (i - start) * 20000))
            prev, start = cur, i
    runs.append((prev, start, len(chunks) - 1, 0))
    for kind, a, b, _b in runs:
        p(f"   blocks {a:>6,}..{b:<6,} [{b-a+1:>6,} blocks]  {kind}")

    # byte-level transitions (1KB granularity) for precision
    p("\n-- BYTE-LEVEL RUN MAP (4KB granularity) --")
    G = 4096
    runs2 = []
    prev = None
    start = 0
    n = len(blob) // G
    for i in range(n):
        seg = blob[i * G:(i + 1) * G]
        cur = "TEXT" if ratio(seg) > 0.9 else "BIN"
        if cur != prev:
            if prev is not None:
                runs2.append((prev, start, i - 1))
            prev, start = cur, i
    runs2.append((prev, start, n - 1))
    for kind, a, b in runs2[:40]:
        p(f"   {a*G:>12,} .. {(b+1)*G:>12,}  {kind}")
    if len(runs2) > 40:
        p(f"   ... {len(runs2)} runs total")

    # ---- ascii strings ----
    strs = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{5,}", blob)]
    p(f"\n-- ascii strings (>=5 chars): {len(strs):,}")
    with open(os.path.join(OUT, "strings_all.txt"), "w", encoding="utf-8") as g:
        g.write("\n".join(strs))

    labels = sorted({s for s in strs if re.fullmatch(r"[A-Z][A-Z_0-9]{3,}", s)})
    p(f"-- SCREAMING_CASE raw-style tokens: {len(labels):,}")
    with open(os.path.join(OUT, "raws_labels.txt"), "w", encoding="utf-8") as g:
        g.write("\n".join(labels))

    # sample 120 from the head and tail of the ASCII region
    p("\n-- SAMPLE: first 60 strings --")
    for s in strs[:60]:
        p("   |" + s[:110])

    # ---- byte value histogram head ----
    p("\n-- first 128 bytes of payload --")
    h = blob[:128]
    for r in range(0, 128, 16):
        p("   " + " ".join(f"{x:02x}" for x in h[r:r + 16]))
    p("   " + "".join(chr(x) if 32 <= x < 127 else "." for x in h))

    # ---- candidate u32 counts at payload start ----
    p("\n-- first 40 u32 values of payload --")
    for i in range(40):
        v = struct.unpack_from("<I", blob, i * 4)[0]
        p(f"   +{i*4:<4} {v:>12,}")

    meta = {
        "source": SRC,
        "source_size": len(raw),
        "source_mtime": datetime.datetime.fromtimestamp(os.stat(SRC).st_mtime).isoformat(),
        "version_field": version, "flag_field": flag,
        "block_count": len(chunks),
        "distinct_block_sizes": {str(k): v for k, v in hist.items()},
        "total_uncompressed": sum(sizes),
        "trailing_bytes": len(raw) - pos,
        "ascii_string_count": len(strs),
        "raws_label_token_count": len(labels),
    }
    with open(os.path.join(OUT, "_container_meta.json"), "w", encoding="utf-8") as g:
        json.dump(meta, g, indent=2)

    with open(LOG, "w", encoding="utf-8") as g:
        g.write("\n".join(_lines))
    print("\n".join(_lines[-90:]))
    print(f"\n[full log -> {LOG}]")


if __name__ == "__main__":
    main()