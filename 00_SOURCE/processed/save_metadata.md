# DF-Chronicles :: save_metadata.md

Verbatim metadata recovered from `world.sav`.

| field | value | offset | certainty |
|---|---|---|---|
| `cur_savegame.version_tag` | 3602 | 208335654 | **FACT** |
| `cur_savegame.version_string` | 53.16 | 208335660 | **FACT** |
| `creature_race_id_labels` | DWARF, ELF, GOBLIN, HUMAN | 208335593 | **FACT** |
| `candidate_fortress_name` | Give Me the Fortress | 208341394 | **FACT** |
| `candidate_world_name` | A Record of the Forest | 208341556 | **FACT** |
| `fortress_name / world_name assignment` | _(see note)_ | - | **DERIVED** |
| `u32 values preceding the two name fields` | 57, 58 | 208341387 | **UNKNOWN** |

## Notes

- **cur_savegame.version_tag** — u32 LE = 3602. Same value as the file container header (bytes 0-3), i.e. the save format revision tag.
- **cur_savegame.version_string** — u16 length prefix (5) + ASCII. Matches the reported Dwarf Fortress version 53.16 exactly.
- **creature_race_id_labels** — Four u16-length-prefixed ASCII labels appearing in sequence, each followed by two u32 values. They are the standard DF creature_race id labels (DWARF=0). They are vocabulary, NOT a roster of this save's inhabitants.
- **candidate_fortress_name** — u16 length prefix (20) + ASCII.
- **candidate_world_name** — u16 length prefix (22) + ASCII.
- **fortress_name / world_name assignment** — basis: These two single-word df::language_name fields sit in the cur_savegame block at the tail of world.sav, whose only name-bearing fields are fortress_name and world_name. 'Give Me the Fortress' matches DF's fortress-name convention; 'A Record of the Forest' matches its world-name convention. Order was NOT verified against the df-structures layout.
- **u32 values preceding the two name fields** — Sequential small integers immediately preceding each name. Their semantic (index? year? id?) could not be determined with confidence. NOT interpreted as dates.

## Confirmed entities

```
historical_figures: UNKNOWN
civilizations: UNKNOWN
sites: UNKNOWN
events: UNKNOWN
artifacts: UNKNOWN
units: UNKNOWN
relationships: UNKNOWN
```
