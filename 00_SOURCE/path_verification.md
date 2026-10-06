# Path Verification — DF-Chronicles

Generated: 2026-10-02
Scope: route correction + installation validation. **Read-only analysis of the
save. No game launch, no `exportlegends`, no save modification.**

---

## 1. Status summary

```
Project:
[OK] C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles

Dwarf Fortress:
[OK] C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\Dwarf Fortress.exe

DFHack:
[OK] C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\hack

Save:
[OK] C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav

Bay 12 data:
[OK] C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress
```

### Detected versions

| Component | Detected version | Evidence |
|---|---|---|
| Dwarf Fortress | **53.16** | `53.16` string embedded once in `Dwarf Fortress.exe`; matches `world.sav` container tag `0x0E12 = 3602` |
| DFHack | **53.16-r2** (RC build) | `plugins\RemoteFortressReader.plug.dll` reports `53.16-r2rc2-0-gc2f513da`; changelog entries `DFHack 53.16-r1` / `53.16-r1.1` in `docs\docs\changelogs\news.txt` |
| Architecture | **x64 / AMD64** (both) | PE header machine type `0x8664` on `Dwarf Fortress.exe`, `dfhack.dll`, `dfhack-run.exe`, `launchdf.exe`, `binpatch.exe` |
| Save format | **53.16** | matches game and DFHack exactly |

**Version match confirmed — all three are 53.16 / 53.16-r2.**

---

## 2. Dwarf Fortress executable

```
Path      : C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\Dwarf Fortress.exe
Size      : 26 507 264 bytes (25.3 MiB)
Modified  : 2026-08-06T09:29:17.2219148+02:00
Created   : 2026-10-01T07:30:59.2119544+02:00
Arch      : x64 (AMD64, PE machine 0x8664)
File ver. : (none — resource carries no FileVersion/ProductVersion strings)
SHA-256   : 205770918FD54C96CBBCF89223EBD449E2E113C7C873ED81177C4511A3450DB7
```

> **Correction to previous report.** The earlier mission concluded
> "`dwarfort.exe` does not exist anywhere on this system" and that the game
> binary was **NOT INSTALLED**. That was wrong. `dwarfort.exe` is the *old*
> (pre-50.x) executable name; since v50 the binary is `Dwarf Fortress.exe`.
> The game **is** installed and is version 53.16.
>
> Also corrected: the previous report located DFHack under
> `...\Steam\steamapps\common\DFHack`. It is **not** a Steam install; it came
> from the official DFHack site and lives at
> `C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\hack`.

Distribution is a non-Steam (AnkerGames) build — the folder contains
`steam_api.dll` / `steam_emu.ini`, and `data\credits.txt` confirms Bay 12
copyright with Kitfox Games as publisher.

---

## 3. DFHack installation

```
Root : C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\
        ├── dfhooks.dll
        ├── dfhooks_dfhack.ini      -> "hack/dfhooks_dfhack.dll"
        └── hack\                   <- the DFHack payload (35 entries, 84 plugins)
```

| Item | Status | Path |
|---|---|---|
| Version | **53.16-r2** | see §1 |
| `dfhack-run` | **Present** | `hack\dfhack-run.exe` (114 688 bytes) |
| `exportlegends.lua` | **Present** | `hack\scripts\exportlegends.lua` (64 418 bytes) |
| exportlegends docs | Present | `hack\docs\docs\tools\exportlegends.txt` |
| `RemoteFortressReader` plugin | Present | `hack\plugins\RemoteFortressReader.plug.dll` — the protobuf RPC engine `exportlegends` drives |
| Support scripts | Present | `open-legends.lua`, `make-legendary.lua` |
| Config files | Present | `hack\init\dfhack.default.init`, `dfhack.tools.init`, `dfhack.keybindings.init`, `onMapLoad.default.init`, `onMapUnload.default.init`, `onLoad.default.init`, `onUnload.default.init` |
| Launchers / executables | Present | `launchdf.exe` (launches DF with DFHack), `dfhack-run.exe`, `binpatch.exe` |
| `dfhack-config/` | **Absent** | will be auto-created on first run |
| Arch lock | `hack\dfhack_setarch.txt` = `x86_64` | matches the x64 DF build |

Also present: 84 `.plug.dll` plugins, `lua53.dll`, allegro/SDL/protobuf runtime,
`symbols.xml`, offline docs (`hack\docs`), `stonesense\`.

---

## 4. Save data

```
world.sav   : 12 490 429 bytes, modified 2026-10-02T17:26:56
SHA-256     : 603F455DDE52B567EDE034E1F637755E7845B53467ABCDE07809D885625DE114
region1     : 379 files (378 *.dat + world.sav)
save/       : current\ (empty), region1\, region2\ (626 files)
```

**The save was not modified.** `world.sav` SHA-256 is identical to the value
recorded during the previous mission, and `region1` still holds exactly 379
files. `save\current\` is empty, so no fortress was open at inspection time.

Bay 12 data directory contents (read-only inspection):

| Path | Contents |
|---|---|
| `data\installed_mods` | present, empty — **no mods installed**, so the world is vanilla raws |
| `prefs\d_init.txt` (1 565 B) | Dwarf Fortress init — save path, autosave settings |
| `prefs\init.txt` (842 B) | audio/display prefs; `[COMPRESSED_SAVES:YES]` confirms the zlib container |
| `prefs\interface.txt` (39 347 B) | UI settings |
| `prefs\world_gen.txt` (28 129 B) | world generation params |
| `prefs\announcements.txt` (10 515 B) | Bay 12 announcements |
| `mods\mod_upload` | empty |
| Legends / exports / XML | **none present** — no `legends.xml`, no `legends_plus.xml` anywhere |

The absence of any XML export confirms `exportlegends` has never been run on
this world. The Bay 12 directory contains **nothing that would let us skip the
game**: no cached legends data. It holds only preferences and the save itself.
`world.sav` remains the sole source of world data.

---

## 5. The four spaces (kept separate, never mixed)

| Role | Path | Contents |
|---|---|---|
| **Game** | `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\` | `Dwarf Fortress.exe` + raws/libs |
| **DFHack** | `C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\hack\` | DFHack payload (53.16-r2) |
| **Save** | `C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\` | `world.sav` + 378 `.dat` |
| **Project** | `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\` | this project's deliverables |

---

## 6. Project relocation

**Moved from:** `C:\Users\Missingn0\LaGranImplosi-n\DF-Chronicles`
**Moved to:** `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles`

Method: `Move-Item` / `[Directory]::Move` both failed with *Access denied*
(a process holds a handle on the directory), so the transfer was performed as
**robocopy /E → SHA-256 verification of all 55 files → delete of source**.
Same-drive operation; the source path no longer exists.

```
Files before : 55
Files after  : 55
Missing      : 0
Extra        : 0
Hash mismatch: 0
Bytes        : 256 366 954
```

53 of 55 files are byte-identical to the pre-move manifest. The 2 that differ
are the ones deliberately corrected (see §7).

### Structure preserved

```
DF-Chronicles\
└── 00_SOURCE\
    ├── extraction_report.md
    ├── path_verification.md          <- this file
    ├── extraction\
    │   ├── artifacts.json  civilizations.json  events.json
    │   ├── historical_figures.json  relationships.json  sites.json  units.json
    │   ├── name_candidates.json  save_metadata.json  stats.json  world.json
    │   ├── strings.csv (9.4 MB)   strings.json (29 MB)
    │   ├── raw\
    │   └── tools\
    │       ├── analyze_payload.py  decode_container.py  extract_world.py
    │       ├── forensics_payload.py  probe_container.py  probe_meta.py
    │       ├── probe_meta_window.py  probe_names.py  record_metadata.py
    │       ├── survey_region1.py
    │       ├── _analyze_log.txt  _forensics_log.txt  _meta_out.txt  _tail_out.txt
    │       └── raw\  (binary_strings.txt, 12 block_*.bin probes,
    │                  raws_labels.txt, raws_tags.txt, strings_all.txt,
    │                  world_decompressed.bin 208 MB, _container_meta.json,
    │                  _probe_summary.json)
    └── processed\
        ├── civilizations.md  events.md  historical_figures.md
        ├── save_metadata.md  timeline.md  world.md
```

**Nothing was deleted or pruned.** All `UNKNOWN`-status JSON files
(`artifacts`, `civilizations`, `events`, `historical_figures`,
`relationships`, `sites`, `units`) were kept as-is: they document which
schema fields could not be resolved offline and are the exact list that
`exportlegends` is expected to fill. Raw probe blocks, logs and the 208 MB
decompressed payload were also retained.

---

## 7. Internal references corrected

Searched the whole project for `LaGranImplosi-n`, `dwarfort`, and the old
DFHack path. Two files needed changes:

| File | Change |
|---|---|
| `00_SOURCE\extraction\tools\extract_world.py` (line 28) | `BASE` → `C:\Users\Missingn0\Documents\Dwarf Fortress\DF-Chronicles\00_SOURCE` |
| `00_SOURCE\extraction_report.md` (line 243) | `cd ...` path in the reproduction appendix |

The extractor still parses cleanly (`python -c "ast.parse(...)"` → SYNTAX OK)
and its `SRC` (the save path) was already correct and untouched.

Additionally, the report's now-disproven claims were corrected in place rather
than deleted (so the prior investigation stays auditable):

* Table row for DFHack — path changed to the real non-Steam location, version
  evidence added, verdict changed from "cannot run" to "potentially yes,
  needs relocation".
* Table row for the game binary — "NOT INSTALLED / `dwarfort.exe` does not
  exist" replaced with the real path, size and `53.16` evidence.

Post-edit scan: **0 remaining** references to `LaGranImplosi-n` or `dwarfort`.

---

## 8. Compatibility assessment

| Requirement | Status |
|---|---|
| DF version == DFHack version | OK — 53.16 == 53.16-r2 |
| Architecture match | OK — x64 == x64 (`dfhack_setarch.txt` = `x86_64`) |
| `exportlegends` present | OK — `scripts\exportlegends.lua`, 64 418 B |
| RPC engine present | OK — `RemoteFortressReader.plug.dll` = 53.16-r2rc2 |
| `dfhack-run` present | OK — 114 688 B |
| DFHack inside the DF folder | **BLOCKER** — `hack/` is in `Documents\...\DFHack\`, not in the game folder |

**Verdict: compatible, but not yet wired up.**

Per DFHack's own `Installing.txt`: *"copy all of the files from the DFHack
archive into the root DF folder... ensure that the `hack` folder ends up next
to the `data` folder."* Currently `hack\` sits in a completely different
folder from `Dwarf Fortress.exe`, and there is no `dfhooks.dll` /
`dfhack.dll` / `dfhack-run.exe` in the game directory, nor any
`dfhack-config\`. DFHack cannot attach to the process as installed.

Note the DFHack version string is `53.16-r2rc2` — a **release candidate**
build. `r2` is the DFHack release line for DF 53.16, so the pairing is right,
but "rc2" means it is a pre-release build rather than the final `r2`. The
underlying DF structures are the same `53.16`, so it should work.

### One important side effect on the save

`exportlegends.lua` writes its output **into the save directory**:

```lua
local filename = world.cur_savegame.save_dir .. "-" .. get_world_date_str()
                 .. "-legends_plus.xml"
```

So `region1\` will gain a `region1-<date>-legends_plus.xml` file, and the
vanilla *Export XML* button will additionally drop `region1-<date>.xml`. This
is **additive** — it does not overwrite `world.sav` — but it does mean the run
is not strictly zero-touch on the save folder. Since the save has not been
opened since 2026-10-02 and `world.sav` is hash-verified, this is acceptable,
but the plan should account for it.

---

## 9. What is required for a full Legends extraction

Nothing has been run. To get the complete Legends dump:

1. **Back up the save first.** Copy `save\region1\` (and `region2\`) somewhere
   safe. Bay 12's own `release notes.txt` says: *"Copy the relevant region
   folder in `save` to a safe location."* Record the `world.sav` SHA-256
   (`603F455D...25DE114`) so we can prove afterwards it was not rewritten.
2. **Install DFHack into the game folder.** Copy everything from
   `C:\Users\Missingn0\Documents\Dwarf Fortress\DFHack\` into
   `C:\Users\Missingn0\Downloads\Dwarf-Fortress-AnkerGames\Dwarf Fortress\`
   so that `hack\`, `stonesense\`, `dfhooks.dll`, `dfhack.dll`,
   `dfhack-run.exe`, `launchdf.exe` and the allegro/SDL/protobuf DLLs all sit
   beside `data\`. This is the only blocking step.
3. **Unblock the copied files** (`Unblock-File` on the DLLs) so Windows
   Defender does not quarantine them — DFHack's docs call this out.
4. **Launch via `launchdf.exe`** (or run `Dwarf Fortress.exe` once so it loads
   `dfhooks.dll`). Verify the DFHack console opens and reports version 53.16-r2.
5. **Confirm DF attaches to `region1`.** The save was made by a 53.16 build so
   there should be no conversion prompt. If DF offers to upgrade the save,
   **abort** — that would rewrite `world.sav`.
6. **Enter Legends mode** without loading a fortress:
   *Main Menu -> "Load Game" -> select `region1` -> "Start a new game" ->
   Legends.* No fortress is loaded and nothing is saved; the world is only
   read. (Never press Save, and do not load an existing site.)
7. **Run `exportlegends`** either by clicking *Export XML* with the
   "Also export extended legends data" toggle on (the default), or by typing
   `exportlegends` in the DFHack console while Legends is open. The latter
   gives the extended data only and avoids the large vanilla XML.
8. **Collect the output.** Expected in `save\region1\`:
   * `region1-<date>-legends_plus.xml` — the extended export with
     historical figures, entities, sites, civs, artifacts, events,
     relationships, deities, positions and assignments.
   * `region1-<date>.xml` — vanilla XML (only if step 7 used the button).

   Copy them into `DF-Chronicles\00_SOURCE\extraction\legends\`.
9. **Re-verify integrity:** confirm `world.sav` SHA-256 is still
   `603F455D...25DE114` and that `region1` has 379 + (new XML) files.
10. **Parse into the existing project schema.** The seven `UNKNOWN`-status JSON
    files become real records. `exportlegends.lua` already reads
    `world.world_data.sites`, `world.entities.all`,
    `df.historical_figure.find(hfid)`, `entity.relations.deities`, positions
    and assignments — exactly the fields blocked offline.

Free disk space is a real constraint: only **~2.6 GB** free on C:. The vanilla
XML plus `legends_plus.xml` can reach several hundred MB, and the project
already holds a 208 MB decompressed payload. Clean up before step 8 if needed.

### Alternative worth considering

`RemoteFortressReader` also exposes a standalone gRPC/Protobuf interface, so a
headless client could pull the same data without ever entering the Legends
screen. It is more complex and still requires the same step 2 (DFHack inside
the game folder) plus a running DF process. It is only worth it if the GUI
route proves problematic.

---

## 10. Integrity statement

* `world.sav` — **unmodified**. SHA-256
  `603F455DDE52B567EDE034E1F637755E7845B53467ABCDE07809D885625DE114`,
  unchanged from the previous mission; mtime still `2026-10-02T17:26:56`.
* `region1` — **379 files**, unchanged.
* `Bay 12 Games\Dwarf Fortress` — inspected **read-only**; nothing created,
  modified or deleted.
* `Dwarf Fortress.exe` — **never executed**.
* `exportlegends` — **never executed**.
* Legends mode — **never opened**.
* Project relocation — 53/55 files byte-identical; 2 corrected by design.