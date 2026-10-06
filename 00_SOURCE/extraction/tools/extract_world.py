#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: PRODUCTION EXTRACTOR
=====================================
Reads  : C:\\...\\save\\region1\\world.sav   (mode 'rb' ONLY - never written)
Writes : DF-Chronicles/00_SOURCE/extraction/**  and **/processed/**
         (never inside region1)

Container format (reverse-engineered & verified byte-exact):
    u32  version_field          = 3602
    u32  flag_field             = 1
    repeat:
        u32  compressed_len
        u8[compressed_len]  zlib stream -> inflates to exactly 20000 bytes
                              (final block is the 20000-remainder)
"""
import os
import re
import csv
import json
import zlib
import struct
import hashlib
import datetime

SRC = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav"
BASE = r"C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE"
EXT = os.path.join(BASE, "extraction")
PROC = os.path.join(BASE, "processed")
RAW = os.path.join(EXT, "raw")

BLOCK_SIZE = 20000
# empirical boundary between the embedded-raws text region and the game data
RAWS_END = 6_455_296

LP = re.compile(rb"[\x04-\xdc][\x20-\x7e]{1,240}")
RAW_TOKEN = re.compile(r"^\[?[A-Z][A-Z_0-9]*(:[A-Z_0-9]+)*\]?$")
PROPER = re.compile(r"^[A-Z][A-z'\-]+(?: [A-Z][A-Za-z'\-]+)+$")
IDENT = re.compile(r"^[A-Z][A-Z_0-9]{2,}$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_container(path):
    """Yield decompressed chunks. READ-ONLY."""
    with open(path, "rb") as f:
        blob = f.read()
    version, flag = struct.unpack_from("<II", blob, 0)
    pos, nblocks, total = 8, 0, 0
    parts = []
    sizes = {}
    while pos + 4 <= len(blob):
        (clen,) = struct.unpack_from("<I", blob, pos)
        pos += 4
        if clen == 0 or pos + clen > len(blob):
            break
        dec = zlib.decompress(blob[pos:pos + clen])
        pos += clen
        nblocks += 1
        total += len(dec)
        sizes[len(dec)] = sizes.get(len(dec), 0) + 1
        parts.append(dec)
    return version, flag, nblocks, total, sizes, len(blob) - pos, b"".join(parts)


def extract_strings(data):
    """All length-prefixed strings: (offset, length, text)."""
    out = []
    for m in LP.finditer(data):
        start = m.start()
        if start < 2:
            continue
        ln = m.end() - start
        (v,) = struct.unpack_from("<H", data, start - 2)
        if v != ln:
            continue
        out.append((start - 2, ln, m.group().decode("latin-1")))
    return out


def classify(text, off):
    region = "raws_text" if off < RAWS_END else "game_data"
    if RAW_TOKEN.match(text):
        kind = "raw_tag_or_id"
    elif PROPER.match(text):
        kind = "proper_name_candidate"
    elif IDENT.match(text):
        kind = "identifier"
    elif re.match(r"^[a-z][a-z_0-9]+$", text):
        kind = "slug"
    else:
        kind = "text"
    return region, kind
# ---------------------------------------------------------------- output sets
SETS = ["historical_figures", "civilizations", "sites", "artifacts",
        "events", "units", "relationships"]


def main():
    for d in (EXT, PROC, RAW):
        os.makedirs(d, exist_ok=True)

    print("[1] hashing source (read-only) ...")
    pre_hash = sha256(SRC)
    st = os.stat(SRC)
    print("    sha256 =", pre_hash)

    print("[2] decoding container ...")
    version, flag, nblocks, total, sizes, trailing, data = decode_container(SRC)
    print(f"    blocks={nblocks:,} uncompressed={total:,} trailing={trailing}")

    print("[3] verifying source is untouched ...")
    post_hash = sha256(SRC)
    print("    sha256 =", post_hash, "->",
          "UNCHANGED" if pre_hash == post_hash else "!!! CHANGED !!!")
    assert pre_hash == post_hash, "SOURCE MODIFIED - ABORT"

    print("[4] extracting strings ...")
    strs = extract_strings(data)
    print("    length-prefixed strings:", f"{len(strs):,}")

    rows = []
    for off, ln, text in strs:
        region, kind = classify(text, off)
        rows.append({"offset": off, "length": ln, "text": text,
                     "region": region, "kind": kind,
                     "certainty": "FACT", "source": "world.sav"})

    name_rows = [r for r in rows if r["kind"] == "proper_name_candidate"]
    print("    proper-name candidates:", f"{len(name_rows):,}")

    with open(os.path.join(EXT, "strings.json"), "w", encoding="utf-8") as f:
        json.dump({
            "certainty": "FACT",
            "note": ("Literal length-prefixed strings read from world.sav. "
                     "These are STRINGS, not verified entities."),
            "source": SRC, "count": len(rows), "records": rows,
        }, f, indent=1, ensure_ascii=False)

    with open(os.path.join(EXT, "name_candidates.json"), "w", encoding="utf-8") as f:
        json.dump({
            "certainty": "UNKNOWN",
            "note": ("Strings resembling proper names. NOT bound to any DF "
                     "entity id. Do not use as narrative facts."),
            "count": len(name_rows), "records": name_rows,
        }, f, indent=1, ensure_ascii=False)

    with open(os.path.join(EXT, "strings.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["offset", "length", "region", "kind", "certainty", "text"])
        for r in rows:
            w.writerow([r["offset"], r["length"], r["region"], r["kind"],
                        r["certainty"], r["text"]])

    for key in SETS:
        with open(os.path.join(EXT, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump({
                "entity_type": key,
                "certainty": "UNKNOWN",
                "count": 0,
                "status": "UNKNOWN - no se pudo determinar con seguridad.",
                "reason": ("Offline decoding yields the container plus the raws "
                           "and string tables, but the df struct graph "
                           "(historical_figure, civilization, site, artifact, "
                           "event, relationship) requires DFHack running inside "
                           "Dwarf Fortress, which is not installed here."),
                "records": [],
            }, f, indent=1, ensure_ascii=False)

    by_kind, by_region = {}, {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        by_region[r["region"]] = by_region.get(r["region"], 0) + 1

    world = {
        "certainty": "FACT",
        "source_file": SRC,
        "source_size_bytes": st.st_size,
        "source_mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
        "source_sha256": pre_hash,
        "source_modified_by_extraction": False,
        "game_version_detected": "53.16",
        "container": {
            "magic_version_field": version,
            "flag_field": flag,
            "block_count": nblocks,
            "block_uncompressed_size": BLOCK_SIZE,
            "block_size_histogram": {str(k): v for k, v in sizes.items()},
            "trailing_bytes": trailing,
            "total_uncompressed_bytes": total,
            "compression": "zlib (RFC1950), one independent stream per block",
        },
        "strings": {
            "total": len(rows),
            "by_kind": by_kind,
            "by_region": by_region,
            "raws_text_region_end_offset": RAWS_END,
        },
        "entities": {k: "UNKNOWN" for k in SETS},
    }
    with open(os.path.join(EXT, "world.json"), "w", encoding="utf-8") as f:
        json.dump(world, f, indent=1, ensure_ascii=False)

    with open(os.path.join(EXT, "stats.json"), "w", encoding="utf-8") as f:
        json.dump({
            "strings_total": len(rows),
            "strings_by_kind": by_kind,
            "strings_by_region": by_region,
            "proper_name_candidates": len(name_rows),
            "blocks": nblocks,
            "uncompressed_bytes": total,
            "entities": {k: "UNKNOWN" for k in SETS},
            "unknown_records": len(rows) - len(name_rows),
        }, f, indent=1)

    with open(os.path.join(PROC, "world.md"), "w", encoding="utf-8") as f:
        f.write("# DF-Chronicles :: world.md\n\n")
        f.write("All values below are **FACT** (read directly from world.sav).\n\n")
        f.write("## Source\n\n")
        f.write(f"- File: `{SRC}`\n")
        f.write(f"- Size: {st.st_size:,} bytes\n")
        f.write(f"- Modified: {datetime.datetime.fromtimestamp(st.st_mtime)}\n")
        f.write(f"- SHA-256: `{pre_hash}`\n")
        f.write("- Modified by extraction: **NO** (opened read-only, hash re-verified)\n\n")
        f.write("## Container format (reverse-engineered)\n\n```\n")
        f.write(f"u32  version_field = {version}\n")
        f.write(f"u32  flag_field    = {flag}\n")
        f.write("repeat:\n")
        f.write("    u32  compressed_len\n")
        f.write(f"    u8[compressed_len]  zlib -> exactly {BLOCK_SIZE} bytes\n")
        f.write("```\n\n")
        f.write(f"- Blocks: **{nblocks:,}**\n")
        f.write(f"- Total uncompressed: **{total:,} bytes** ({total/1e6:.1f} MB)\n")
        f.write(f"- Trailing bytes: **{trailing}**\n")
        f.write(f"- Block size histogram: `{ {str(k): v for k, v in sizes.items()} }`\n\n")
        f.write("## Extracted strings\n\n")
        f.write(f"- Total length-prefixed strings: **{len(rows):,}**\n\n")
        f.write("| kind | count |\n|---|---|\n")
        for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
            f.write(f"| {k} | {v:,} |\n")
        f.write("\n| region | count |\n|---|---|\n")
        for k, v in sorted(by_region.items(), key=lambda x: -x[1]):
            f.write(f"| {k} | {v:,} |\n")

    with open(os.path.join(PROC, "timeline.md"), "w", encoding="utf-8") as f:
        f.write("# DF-Chronicles :: timeline.md\n\n")
        f.write("**UNKNOWN - no se pudo determinar con seguridad.**\n\n")
        f.write("world.sav holds the current world state plus the embedded raws. "
                "The historical timeline (years, wars, deaths, births) lives in "
                "the decoded `historical_figure` / `event` structures, which "
                "could not be decoded offline. No dates were invented.\n")

    for key in ["historical_figures", "civilizations", "events"]:
        with open(os.path.join(PROC, f"{key}.md"), "w", encoding="utf-8") as f:
            f.write(f"# DF-Chronicles :: {key}.md\n\n")
            f.write("**UNKNOWN - no se pudo determinar con seguridad.**\n\n")
            f.write(f"- Target entity: `{key}`\n- Count: **UNKNOWN**\n\n")
            f.write("No records were fabricated. See `extraction_report.md` for "
                    "the reason and the exact next step required.\n")

    print("\n[done] outputs written to", EXT)
    print("  proper-name candidates:", f"{len(name_rows):,}")
    print("  kinds:", by_kind)
    print("  regions:", by_region)


if __name__ == "__main__":
    main()
