#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 2 -- full container decode (STRICTLY READ-ONLY)

Container layout (empirically confirmed):
    u32 version       (observed 3602)
    u32 flag          (observed 1)
    repeat:
        u32 comp_len
        byte[comp_len] zlib stream -> inflates to exactly 20000 bytes

Outputs go ONLY into 00_SOURCE/extraction/raw/.
"""
import os
import re
import struct
import zlib
import json
import datetime

SRC = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw")


def main():
    with open(SRC, "rb") as f:
        raw = f.read()

    version, flag = struct.unpack_from("<II", raw, 0)
    pos = 8
    blocks = []
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
            blocks.append({"index": len(blocks), "offset": pos - clen, "error": str(e)})
            continue
        blocks.append({"index": len(blocks), "compressed": clen,
                       "decompressed": len(dec), "_data": dec})
    trailing = len(raw) - pos

    total = sum(b.get("decompressed", 0) for b in blocks)
    print(f"version field      : {version}")
    print(f"flag field         : {flag}")
    print(f"blocks decoded     : {len(blocks)}")
    print(f"bytes consumed     : {pos} / {len(raw)}  (trailing {trailing})")
    print(f"total decompressed : {total} bytes")

    # ---- classify each block: printable ratio ----
    print("\n== BLOCK PROFILE ==")
    print(f"{'idx':>5} {'off':>10} {'comp':>9} {'decomp':>9} {'text%':>7}  preview")
    for b in blocks:
        d = b.get("_data", b"")
        pr = sum(1 for x in d if 32 <= x < 127 or x in (9, 10, 13)) / max(1, len(d))
        txt = "".join(chr(x) if 32 <= x < 127 else "." for x in d[:48])
        print(f"{b['index']:>5} {b['offset']:>10} {b.get('compressed', 0):>9} "
              f"{b.get('decompressed', 0):>9} {pr*100:>6.1f}%  {txt}")

    # ---- find text <-> binary transitions ----
    print("\n== TEXT/BINARY TRANSITIONS ==")
    prev = None
    for b in blocks:
        d = b.get("_data", b"")
        pr = sum(1 for x in d if 32 <= x < 127 or x in (9, 10, 13)) / max(1, len(d))
        cur = "TEXT" if pr > 0.85 else ("MIX" if pr > 0.3 else "BIN")
        if cur != prev:
            print(f"  block {b['index']:>5} (off {b['offset']:>9}): {prev} -> {cur}")
            prev = cur

    # ---- write full decompressed stream ----
    blob = b"".join(b.get("_data", b"") for b in blocks)
    blobpath = os.path.join(OUT, "world_decompressed.bin")
    with open(blobpath, "wb") as g:
        g.write(blob)
    print("\nwrote", blobpath, len(blob), "bytes")

    # ---- string extraction (len >= 6), first 4000 + ascii-looking clusters ----
    strs = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{6,}", blob)]
    print("total ascii strings (>=6 chars):", len(strs))
    with open(os.path.join(OUT, "strings_all.txt"), "w", encoding="utf-8") as g:
        for s in strs:
            g.write(s + "\n")

    # strings that look like dwarf names / labels
    labels = [s for s in strs if re.match(r"^[A-Z][A-Z_0-9]{3,}$", s)]
    print("SCREAMING_CASE tokens:", len(labels))
    with open(os.path.join(OUT, "labels_all.txt"), "w", encoding="utf-8") as g:
        for s in sorted(set(labels)):
            g.write(s + "\n")

    meta = {
        "source": SRC,
        "source_size": len(raw),
        "source_mtime": datetime.datetime.fromtimestamp(os.stat(SRC).st_mtime).isoformat(),
        "version_field": version,
        "flag_field": flag,
        "block_count": len(blocks),
        "total_decompressed": total,
        "trailing_bytes": trailing,
        "string_count": len(strs),
        "label_token_count": len(set(labels)),
    }
    with open(os.path.join(OUT, "_decode_meta.json"), "w", encoding="utf-8") as g:
        json.dump(meta, g, indent=2)
    for b in blocks:
        b.pop("_data", None)
    with open(os.path.join(OUT, "_block_table.json"), "w", encoding="utf-8") as g:
        json.dump(blocks, g, indent=2)


if __name__ == "__main__":
    main()