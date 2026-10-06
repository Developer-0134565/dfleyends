#!/usr/bin/env python3
"""
DF-Chronicles :: Phase 5 -- feasibility probe for recovering named entities.
Vectorised (regex) so it can walk a 208 MB payload quickly.
"""
import os
import re
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
BLOB = os.path.join(HERE, "raw", "world_decompressed.bin")

SEP_CANDIDATES = [0x07, 0x01, 0x1E, 0x02, 0x0B]
WORD = rb"[A-Za-z][A-Za-z'\-]{2,20}"

# length-prefixed string: u16 length (4..220) then exactly that many printable bytes.
# We exploit the fact that the low byte of the u16 equals the high byte when len<256,
# so the prefix bytes repeat; a robust formulation:
LP = re.compile(rb"[\x04-\xdc][\x20-\x7e]{4,220}")
# then validate by re-reading the true u16 at pos-2
import struct


def lp_scan(data):
    out = []
    for m in LP.finditer(data):
        start = m.start()
        p = start - 2
        if p < 0:
            continue
        (ln,) = struct.unpack_from("<H", data, p)
        if ln != (m.end() - start):
            continue
        out.append((p, ln, m.group().decode("latin-1")))
    return out


def main():
    data = open(BLOB, "rb").read()
    print("blob:", f"{len(data):,}")

    print("\n" + "=" * 72)
    print("Q1  length-prefixed string scan (u16 LE length + ascii payload)")
    print("=" * 72)
    hits = lp_scan(data)
    print(f"length-prefixed strings found: {len(hits):,}")
    for off, ln, s in hits[:12]:
        print(f"  @{off:>12,} len={ln:>4}  {s[:88]}")
    print("   ...")
    for off, ln, s in hits[-12:]:
        print(f"  @{off:>12,} len={ln:>4}  {s[:88]}")
    cov = sum(2 + h[1] for h in hits)
    print(f"\n  covered: {cov:,} bytes = {cov*100/len(data):.1f}% of blob")
    if hits:
        print(f"  last string ends at offset {hits[-1][0]+2+hits[-1][1]:,}")

    print("\n" + "=" * 72)
    print("Q2  multi-word name patterns in BINARY region (>6.5 MB)")
    print("=" * 72)
    binz = data[6_500_000:]
    for sep in SEP_CANDIDATES:
        pat = re.compile(rb"(?<![A-Za-z'\-])" + WORD + rb"(?:" +
                         bytes([sep]) + WORD + rb")+")
        found = pat.findall(binz)
        cnt = collections.Counter(found)
        print(f"\n  sep 0x{sep:02x}: {len(found):,} matches, {len(cnt):,} distinct")
        for s, c in cnt.most_common(10):
            print(f"      {c:>6}  {s.decode('latin-1')}")

    print("\n" + "=" * 72)
    print("Q3  spaced ascii runs in binary region (name candidates)")
    print("=" * 72)
    runs = [m.group().decode("latin-1")
            for m in re.finditer(rb"[A-Za-z][A-Za-z'\-]{1,20}(?: [A-Za-z'\-]{1,20}){1,4}",
                                 binz)]
    cnt = collections.Counter(r.strip() for r in runs)
    print(f"multi-word runs: {len(runs):,}  distinct: {len(cnt):,}")
    for s, c in cnt.most_common(35):
        print(f"   {c:>6}  {s[:70]}")


if __name__ == "__main__":
    main()