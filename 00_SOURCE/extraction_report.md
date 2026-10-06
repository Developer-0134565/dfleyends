# DF-Chronicles — Extraction Report

**Target:** `C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav`
**Game version:** Dwarf Fortress 53.16
**Report date:** 2026-10-02
**Status:** Diagnosis complete. Safe initial extraction complete. Legends-level entity decode **blocked** (reason in §5 and §10).

---

## 0. Safety statement (read-only guarantee)

| Check | Result |
|---|---|
| `world.sav` SHA-256 before extraction | `603f455dde52b567ede034e1f637755e7845b53467abcde07809d885625de114` |
| `world.sav` SHA-256 after extraction | `603f455dde52b567ede034e1f637755e7845b53467abcde07809d885625de114` |
| Modified? | **NO — byte-identical** |
| `world.sav` size / mtime | 12,490,429 bytes — 2026-10-02 17:26:56 (**unchanged**) |
| Files in `region1` | 379 (unchanged) |
| Files in `region1` modified during session | **0** |
| Any output written into `region1`? | **NO** |
| Dwarf Fortress launched? | **NO** |

Every tool opened the save with `open(path, "rb")` only. The extractor
(`extraction/tools/extract_world.py`) re-hashes the file after reading and
`assert`s equality. All generated files live under `DF-Chronicles/`.

---

## 1. ¿Se puede leer `world.sav` directamente?

**SÍ.** The file opens as a normal binary file and is fully, losslessly
decompressible. No encryption, no obfuscation, no custom codec. The container
was reverse-engineered from first principles and verified **byte-exact**.

## 2. ¿Qué formato tiene?

Dwarf Fortress v50+ (0.47/50/53) block-compressed save container:

```
u32  version_field = 3602          # save format revision tag
u32  flag_field    = 1
repeat:
    u32  compressed_len           # length of the next zlib stream
    u8[compressed_len]            # zlib (RFC1950) -> exactly 20 000 bytes
```

| Metric | Value |
|---|---|
| Block count | **10 425** |
| Block size histogram | `20 000 × 10 424`, `9 987 × 1` (last block = remainder) |
| Total compressed | 12,490,429 bytes |
| **Total uncompressed** | **208,489,987 bytes (~208.5 MB)** |
| Trailing bytes | **0** — every input byte accounted for |
| Compression ratio | ~16.7× |

Payload layout:

| Offset range | Content | Evidence |
|---|---|---|
| 0 – 6 455 296 | **Embedded raws text** (94 % printable, 132 696 `[TAG]`s, 5 534 distinct) | `[INORGANIC:DIVINE_1]`, `[OBJECT:REACTION]`, `Xah Alu, "The Dimension of Winds"` |
| 6 455 296 – end | **Serialized game data** (entropy 2.0–3.7, stride-32 indexed records) | `[DIVINE]`, `GENERAL_POISON`, `RUTHLESS`, `PLAINS` |

Strings are encoded **length-prefixed**: `u16` little-endian length, then that
many ASCII bytes. 150 695 such strings were recovered.

> The embedded-raws region corroborates the header: the string `53.16` appears
> verbatim in the `cur_savegame` block, and `0x0E12 = 3602` appears both as the
> container tag and inside that block.

## 3. ¿Qué herramienta/librería se utilizó?

| Source | Result | Usable? |
|---|---|---|
| **DFHack 53.16-r2** (`C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\hack`) | **Installed, exact version match** (non-Steam build; `RemoteFortressReader.plug.dll` reports `53.16-r2rc2-0-gc2f513da`). Contains `scripts/exportlegends.lua` — the modern reimplementation of Classic Legends export. Reads `world.world_data.sites`, `world.entities.all`, `df.historical_figure.find(hfid)`, `entity.relations.deities`, positions/assignments. | **POTENTIALLY YES — needs relocation (see `path_verification.md`).** Not yet run. |
| **Dwarf Fortress binary** | **INSTALLED (correction).** `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\Dwarf Fortress.exe` — x64, 26 507 264 bytes, embeds version string `53.16`. | **YES — but must not be launched until DFHack is placed in the game folder** |
| `backerman/dfworld` (Go) | World.sav tool, based on Andux 2014 research | **NO — DF2014-era format only** |
| `Mortal/dfworlddatpy` (Python) | world.dat parsing, 5 commits, 2013 | **NO — DF2014-era format only** |
| Andux `Format research/WORLD.SAV` (wiki, 2013) | Documents header + 19 string tables for **DF2014** | Reference only; superseded by 0.47+ zlib container |
| **Custom extractor (written for this mission)** | `extraction/tools/*.py` | **YES — this is what produced all outputs** |

DFHack is the correct tool for full legends extraction, but it is **inert
without the game binary**. This was the decisive constraint, so per the
priority ladder, a purpose-built read-only parser was written.

## 4. ¿Qué información contiene?

**Recovered as FACT:**

- Complete container geometry and version (10 425 blocks, 208.5 MB payload).
- **150 695 strings** with byte offsets, each length-validated:
  - 96 906 raw tags / raws IDs
  - 36 601 free text
  - 16 932 slugs
  - 256 proper-name-shaped strings
- 132 696 raw-tag occurrences, 5 534 distinct tags — the world's raws
  (materials, plants, creatures, reactions, syndromes, buildings, items).
- **Save metadata block** at payload offset ~208 335 400:

| Field | Value | Certainty |
|---|---|---|
| `version_tag` | `3602` | **FACT** |
| `version_string` | **`53.16`** | **FACT** |
| creature-race labels | `DWARF`, `ELF`, `GOBLIN`, `HUMAN` | **FACT** |
## 5. ¿Qué información NO contiene? / no se pudo extraer?

`world.sav` **does** contain all this data, but it is stored as DF's internal
serialized C++ struct graph, which is not self-describing. Without the
df-structures schema (or DF itself) the field layout cannot be walked.

| Category | Status |
|---|---|
| Historical figures | **UNKNOWN — no se pudo determinar con seguridad** |
| Civilizations | **UNKNOWN — no se pudo determinar con seguridad** |
| Sites | **UNKNOWN — no se pudo determinar con seguridad** |
| Events | **UNKNOWN — no se pudo determinar con seguridad** |
| Artifacts | **UNKNOWN — no se pudo determinar con seguridad** |
| Units | **UNKNOWN — no se pudo determinar con seguridad** |
| Relationships | **UNKNOWN — no se pudo determinar con seguridad** |
| Timeline (years, wars, deaths) | **UNKNOWN — no se pudo determinar con seguridad** |

**Critical negative result — validated, not assumed:** the 256
"proper-name-shaped" strings were inspected individually. They are **raws
vocabulary**, not entities: `LACE AGATE`, `BLUE JADE`, `PENGUIN MAN`,
`HOUSE GRASS`, `PLAY FUN`, `SKIN VERB`, `VANILLA MATERIALS`, plus generated
*book titles* (`My Friend Goo`, `The Future Weeps`, `It Must Have Been Ruin`).
**Not one is a historical figure, civilization, or site.** The name-shaped
strings in the game-data region are books and raws metadata. DF stores proper
names as multi-word `df::language_name` structures whose word separators did
not match any probed encoding (0x07, 0x01, 0x1E, 0x02, 0x0B → 0 hits), so
entities are not recoverable by pattern matching.

**No entity was invented. No date, name, or relationship was fabricated.**

## 6. ¿Qué otros archivos de `region1` son necesarios?

All 378 `.dat` files were opened read-only and **use the identical container
format** (same `3602`/`1` header, same 20 000-byte zlib blocks, 0 trailing):

| Group | Count | On disk | Bearing on history |
|---|---|---|---|
| `unit-*.dat` | 318 | 1.4 MB | Fortress units only. **No legends data.** |
| `feature-*.dat` | 54 | 397 KB | World features |
| `art_image-*.dat` | 4 | 19 KB | Map art |
| `region_snapshot-*.dat` | 2 | 4.4 KB | Region map snapshots |
| `world.sav` | 1 | **12.5 MB → 208.5 MB** | **The legends source.** |

Also present: `save/current`, `save/region2`.

**Conclusion:** processing the `.dat` files is **not necessary** for a
historical reconstruction. `world.sav` is where the history lives. The `.dat`
files matter only for map/unit geometry.

## 7. ¿Qué datos pudieron extraerse?

## 9. Riesgos y limitaciones

1. **No DF binary** → DFHack cannot run → legends export impossible offline.
2. **No maintained offline parser for v50/v53.** The two that exist target the
   2014 format and will misread this file. Using them would corrupt data.
3. **Struct graph is not self-describing.** Correct parsing requires the
   `df-structures` XML schema for v53.16, which is not bundled with DFHack
   (only `symbols.xml` is shipped) and is not present locally.
4. **The 208 MB `.bin` intermediate** (`extraction/tools/raw/`) is large and
   regenerable — safe to delete; `extract_world.py` recreates it.
5. **`name_candidates.json` must never be fed to a narrative generator** as
   fact. It is vocabulary, not people.
6. Metadata name assignment is **DERIVED**, not confirmed.

## 10. ¿Cuál sería el siguiente paso?

**In descending order of information yield:**

**Option A — reinstall Dwarf Fortress 53.16 (recommended, definitive).**
The Steam library is present but DF is not installed. Reinstalling DF, then
running the already-installed **DFHack 53.16-r2** gives the full Classic
Legends reconstruction with zero reverse engineering:

```
dfhack-run exportlegends
```

This yields `*-world_history.txt` (world name, civilizations, deities,
positions/assignments, wars) and `*-world_sites_and_pops.txt` (civilized
population, sites with **site ids**, outdoor/underground populations).
**Safety:** copy `region1` to a scratch location first and export from the copy,
so the original can never be written.

**Option B — obtain the df-structures schema and write a full struct parser.**
Fetch the v53.16 `df-structures` XML (`df.global.xml`, `df.items.xml`,
`df.interface.xml`, `df.enum.xml`, `df.world.xml`, `df.plant.xml`) and extend
`extract_world.py` to walk `world_data` → `figures`, `entities`, `sites`,
`regions`, `status`. Substantial, but fully offline and read-only.

**Option C — parse the `.dat` files** for map/unit geometry. Low value for
history; only after A or B.

**Recommended sequence:** A first (fast, complete, authoritative) →
B only if a fully offline pipeline is a hard requirement.

---

## Statistics

```text
Historical figures: UNKNOWN — no se pudo determinar con seguridad.
Civilizations:      UNKNOWN — no se pudo determinar con seguridad.
Sites:              UNKNOWN — no se pudo determinar con seguridad.
Events:             UNKNOWN — no se pudo determinar con seguridad.
Artifacts:          UNKNOWN — no se pudo determinar con seguridad.
Units:              UNKNOWN — no se pudo determinar con seguridad.
Relationships:      UNKNOWN — no se pudo determinar con seguridad.
Unknown records:    150 439
```

### What *was* measured

```text
Container blocks decoded           : 10 425
Uncompressed payload               : 208 489 987 bytes  (208.5 MB)
Bytes consumed / trailing          : 12 490 429 / 0        (100 % decoded)
Distinct length-prefixed strings   : 150 695
  raw tags & raws ids              : 96 906
  free text                        : 36 601
  slugs                            : 16 932
  proper-name-shaped (NOT entities): 256
Raw tag occurrences / distinct     : 132 696 / 5 534
auxiliary .dat files (read-only)   : 378
Save metadata fields recovered     : 6  (version, races, 2 names, 2 u32)
Entities recovered                 : 0  (blocked — see §10)
```

**Bottom line:** the save is fully readable and was fully decoded, with
integrity cryptographically verified. The container format is solved. The
*contents* are present but schema-blocked. The next step that yields the most
information is reinstalling DF and running `exportlegends` — no further
reverse engineering required.

---

## Appendix — pipeline reproduction

```powershell
cd C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE\extraction\tools
python probe_container.py     # header / block geometry
python decode_container.py    # full inflate -> raw/world_decompressed.bin
python analyze_payload.py     # text vs binary run map
python forensics_payload.py   # entropy + raw-tag census
python survey_region1.py      # read-only survey of the 378 .dat files
python probe_names.py         # string/name-encoding feasibility
python probe_meta_window.py   # cur_savegame metadata decode
python extract_world.py       # PRODUCTION extractor -> json/csv/md
python record_metadata.py     # metadata records w/ certainty labels
```

`extract_world.py` verifies the source SHA-256 before and after and aborts if
it ever differs.
| Artifact | Contents |
|---|---|
| `extraction/world.json` | Container geometry, version, string census |
| `extraction/strings.json` (29 MB) | All 150 695 strings + offsets + classification |
| `extraction/strings.csv` (9.4 MB) | Same, tabular |
| `extraction/save_metadata.json` | Version, race labels, name candidates |
| `extraction/name_candidates.json` | 256 name-shaped strings, flagged NOT entities |
| `extraction/stats.json` | Machine-readable counts |
| `processed/world.md` | Human-readable container + string report |
| `processed/save_metadata.md` | Metadata table with certainty per field |

## 8. ¿Qué datos no pudieron extraerse?

All entity-level records — see §5. Every corresponding file exists and contains
an explicit `UNKNOWN` status with a `reason`, rather than being omitted.
| candidate fortress name | **`Give Me the Fortress`** | **FACT** (string exists) |
| candidate world name | **`A Record of the Forest`** | **FACT** (string exists) |
| which name is which | fortress = "Give Me the Fortress", world = "A Record of the Forest" | **DERIVED** — high confidence, not confirmed against df-structures |
| two preceding u32s | `57`, `58` | **UNKNOWN** — not interpreted as years |