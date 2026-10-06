#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 3 -- forensic characterisation of the decompressed payload
READ-ONLY on world.sav. Reads only the .bin we already produced outside region1.

Goal: characterise the TEXT region (embedded raws?) and the BINARY region
(actual df serialized structures), and harvest only what is defensible.
"""
import os
import re
import math
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")
OUT = os.path.join(HERE, "raw")

L = []


def p(*a):
    L.append(" ".join(str(x) for x in a))


def hd(b, off, n=96):
    out = []
    for r in range(0, n, 16):
        chunk = b[off + r: off + r + 16]
        if not chunk:
            break
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        out.append(f"  {off+r:>10,}  {hexs:<47}  {asc}")
    return out


def main():
    if not os.path.exists(BLOB):
        p("MISSING", BLOB)
        return
    data = open(BLOB, "rb").read()
    p("=" * 78)
    p("PAYLOAD FORENSICS (read-only)")
    p("=" * 78)
    p("size:", f"{len(data):,}")

    # ---------- entropy profile in 1 MB windows ----------
    p("\n== ENTROPY PROFILE (1 MB windows) ==")
    p(f"{'offset':>13} {'entropy':>8}  {'ascii%':>7}  note")
    for off in range(0, len(data), 1 << 20):
        w = data[off:off + (1 << 20)]
        cnt = collections.Counter(w)
        tot = len(w)
        ent = -sum((c / tot) * math.log2(c / tot) for c in cnt.values())
        pr = sum(1 for x in w if 32 <= x < 127 or x in (9, 10, 13)) / tot
        note = ""
        if pr > 0.90:
            note = "RAWS-LIKE TEXT"
        elif pr < 0.10:
            note = "DENSE BINARY (structures / arrays)"
        p(f"{off:>13,} {ent:>8.4f}  {pr*100:>6.1f}%  {note}")

    # ---------- TEXT region boundary ----------
    p("\n== TEXT REGION BOUNDARY ==")
    G = 4096
    def is_text(seg):
        return sum(1 for x in seg if 32 <= x < 127 or x in (9, 10, 13)) / max(1, len(seg)) > 0.90
    runs = []
    prev = None
    start = 0
    n = len(data) // G
    for i in range(n):
        cur = is_text(data[i * G:(i + 1) * G])
        if cur != prev:
            if prev is not None:
                runs.append((prev, start * G, i * G))
            prev, start = cur, i
    runs.append((prev, start * G, n * G))
    for kind, a, b in runs[:12]:
        p(f"  {a:>12,} .. {b:>12,}  {'TEXT' if kind else 'BIN '}")
    p(f"  total runs: {len(runs)}")

    # ---------- very start of payload ----------
    p("\n== PAYLOAD START (binary header?) ==")
    for line in hd(data, 0, 256):
        p(line)

    # ---------- start of the text region ----------
    p("\n== TEXT REGION HEAD @ 4096 ==")
    for line in hd(data, 4096, 256):
        p(line)

    p("\n== FIRST 4000 CHARS OF TEXT REGION ==")
    txt = data[4096:4096 + 4000]
    printable = "".join(chr(x) if 32 <= x < 127 or x in (9, 10) else "\u00b7" for x in txt)
    for i in range(0, len(printable), 100):
        p("  " + printable[i:i + 100])

    # ---------- last text run boundary sample ----------
    p("\n== SAMPLE @ 6,440,000 (text->bin edge) ==")
    for line in hd(data, 6440000, 256):
        p(line)

    # ---------- raw-tag census in text region ----------
    text_zone = data[:6_455_000]
    tags = re.findall(rb"\[[A-Z][A-Z_0-9:]{2,}\]", text_zone)
    tc = collections.Counter(t.decode() for t in tags)
    p(f"\n== RAW TAGS in text region: {len(tags):,} occurrences, {len(tc):,} distinct ==")
    for t, n in tc.most_common(40):
        p(f"   {n:>6,}  {t}")
    with open(os.path.join(OUT, "raws_tags.txt"), "w", encoding="utf-8") as g:
        for t, n in tc.most_common():
            g.write(f"{n}\t{t}\n")

    # ---------- csv-ish lines (name, "word") ----------
    csvl = re.findall(rb"[A-Za-z][A-Za-z'\- ]{2,40}, \"[^\"\n]{2,40}\"", text_zone)
    p(f"\n== csv 'name, \"token\"' lines: {len(csvl):,} ==")
    for c in csvl[:40]:
        p("   " + c.decode("latin-1"))

    # ---------- BINARY region: hunt for structure-defining strings ----------
    bin_zone = data[6_455_000:]
    p(f"\n== BINARY REGION: {len(bin_zone):,} bytes (from offset 6,455,000) ==")
    strs = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{4,}", bin_zone)]
    p(f"   ascii runs (>=4): {len(strs):,}")
    with open(os.path.join(OUT, "binary_strings.txt"), "w", encoding="utf-8") as g:
        g.write("\n".join(strs))
    p("\n   -- first 80 --")
    for s in strs[:80]:
        p("   |" + s[:100])

    # frequency of repeated binary-region strings (reveals vocabularies)
    c2 = collections.Counter(strs)
    p("\n   -- 50 most frequent (likely raws keys / status names) --")
    for s, n in c2.most_common(50):
        p(f"   {n:>7,}  {s[:80]}")

    with open(os.path.join(HERE, "_forensics_log.txt"), "w", encoding="utf-8") as g:
        g.write("\n".join(L))
    print("\n".join(L))
    print(f"\n[full log -> {os.path.join(HERE,'_forensics_log.txt')}]")


if __name__ == "__main__":
    main()