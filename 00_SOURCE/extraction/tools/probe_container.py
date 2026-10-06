#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 1/2 probe  (STRICTLY READ-ONLY)

Opens world.sav with mode 'rb' only. Never writes to the source path.
Goal: empirically determine the DF 0.47+ (v50/v53) save container layout.
"""
import os
import sys
import zlib
import json
import struct
import datetime

SRC = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")


def log(*a):
    print(*a, flush=True)


def hexdump(b, n=64):
    return " ".join(f"{x:02x}" for x in b[:n])


def main():
    log("== SOURCE ==")
    log("path :", SRC)
    st = os.stat(SRC)
    log("size :", st.st_size)
    log("mtime:", datetime.datetime.fromtimestamp(st.st_mtime).isoformat())

    if not os.path.isdir(OUT):
        os.makedirs(OUT, exist_ok=True)

    with open(SRC, "rb") as f:          # READ ONLY
        raw = f.read()
    log("read :", len(raw), "bytes (full read into memory, no write-back)")

    log("\n== FIRST 64 BYTES ==")
    log(hexdump(raw, 64))

    u32 = lambda o: struct.unpack_from("<I", raw, o)[0]
    i32 = lambda o: struct.unpack_from("<i", raw, o)[0]

    log("\n== CANDIDATE HEADER FIELDS (little-endian u32) ==")
    for off in range(0, 32, 4):
        log(f"  +{off:<3} u32={u32(off):<12} i32={i32(off):<12}")

    # Is byte 12 a zlib header?
    log("\n== ZLIB CHECK ==")
    for probe in (0, 4, 8, 12, 16):
        if raw[probe] == 0x78 and raw[probe + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            log(f"  zlib magic at offset {probe}: {raw[probe]:02x} {raw[probe+1]:02x}")

    # ---- Sequential walk: header fields then a stream of zlib blocks ----
    log("\n== BLOCK WALK (heuristic) ==")
    offset = 0
    blocks = []
    # try: 3 leading u32s, then concatenated zlib streams
    pre = [u32(0), u32(4), u32(8)]
    log("  leading u32s:", pre)
    offset = 12
    idx = 0
    while offset < len(raw) and idx < 12:
        if raw[offset] == 0x78 and raw[offset + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            d = zlib.decompressobj()
            try:
                out = d.decompress(raw[offset:])
            except Exception as e:
                log(f"  block {idx} at {offset}: DECOMPRESS FAIL {e}")
                break
            consumed = len(raw) - offset - len(d.unused_data)
            blocks.append((idx, offset, consumed, len(out), out))
            log(f"  block {idx:<3} off={offset:<10} comp={consumed:<10} decomp={len(out):<10} "
                f"preview={hexdump(out, 24)}")
            outpath = os.path.join(OUT, f"block_{idx:03d}_off{offset}.bin")
            with open(outpath, "wb") as g:
                g.write(out)
            offset += consumed + (4 if len(d.unused_data) >= 4 else 0)
            idx += 1
        else:
            log(f"  stop at offset {offset}: {hexdump(raw[offset:offset+16],16)}")
            break

    log("\n== TRAILING ANALYSIS ==")
    log("  final offset:", offset, "of", len(raw))

    with open(os.path.join(OUT, "_probe_summary.json"), "w", encoding="utf-8") as g:
        json.dump({
            "source": SRC,
            "size": st.st_size,
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
            "leading_u32": pre,
            "blocks": [
                {"index": i, "offset": o, "compressed": c, "decompressed": dl}
                for (i, o, c, dl, _b) in blocks
            ],
        }, g, indent=2)
    log("  wrote", os.path.join(OUT, "_probe_summary.json"))


if __name__ == "__main__":
    main()
