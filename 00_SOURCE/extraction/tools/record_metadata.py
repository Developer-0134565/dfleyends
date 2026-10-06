#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DF-Chronicles :: Phase 6 -- record verified save metadata.
Appends the metadata findings to the extraction outputs.

CERTAINTY POLICY
  FACT        : literal bytes read from world.sav
  DERIVED     : calculated/structured inference, stated with its basis
  UNKNOWN     : not determinable with confidence
"""
import os
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.abspath(os.path.join(HERE, ".."))
SRC = r"C:\Users\Missingn0\AppData\Roaming\Bay 12 Games\Dwarf Fortress\save\region1\world.sav"

META = {
    "source": SRC,
    "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat().replace("+00:00", "Z"),
    "records": [
        {
            "field": "cur_savegame.version_tag",
            "offset_in_payload": 208335654,
            "value": 3602,
            "certainty": "FACT",
            "note": "u32 LE = 3602. Same value as the file container header "
                    "(bytes 0-3), i.e. the save format revision tag.",
        },
        {
            "field": "cur_savegame.version_string",
            "offset_in_payload": 208335660,
            "value": "53.16",
            "certainty": "FACT",
            "note": "u16 length prefix (5) + ASCII. Matches the reported "
                    "Dwarf Fortress version 53.16 exactly.",
        },
        {
            "field": "creature_race_id_labels",
            "offset_in_payload": 208335593,
            "value": ["DWARF", "ELF", "GOBLIN", "HUMAN"],
            "certainty": "FACT",
            "note": "Four u16-length-prefixed ASCII labels appearing in "
                    "sequence, each followed by two u32 values. They are the "
                    "standard DF creature_race id labels (DWARF=0). They are "
                    "vocabulary, NOT a roster of this save's inhabitants.",
        },
        {
            "field": "candidate_fortress_name",
            "offset_in_payload": 208341394,
            "value": "Give Me the Fortress",
            "certainty": "FACT",
            "note": "u16 length prefix (20) + ASCII.",
        },
        {
            "field": "candidate_world_name",
            "offset_in_payload": 208341556,
            "value": "A Record of the Forest",
            "certainty": "FACT",
            "note": "u16 length prefix (22) + ASCII.",
        },
        {
            "field": "fortress_name / world_name assignment",
            "value": None,
            "certainty": "DERIVED",
            "confidence": "high but NOT confirmed",
            "basis": ("These two single-word df::language_name fields sit in the "
                      "cur_savegame block at the tail of world.sav, whose only "
                      "name-bearing fields are fortress_name and world_name. "
                      "'Give Me the Fortress' matches DF's fortress-name "
                      "convention; 'A Record of the Forest' matches its "
                      "world-name convention. Order was NOT verified against the "
                      "df-structures layout."),
            "do_not": "Do not treat as narrative fact until confirmed in-game.",
        },
        {
            "field": "u32 values preceding the two name fields",
            "offset_in_payload": 208341387,
            "value": [57, 58],
            "certainty": "UNKNOWN",
            "note": "Sequential small integers immediately preceding each name. "
                    "Their semantic (index? year? id?) could not be "
                    "determined with confidence. NOT interpreted as dates.",
        },
    ],
    "confirmed_entities": {
        "historical_figures": "UNKNOWN",
        "civilizations": "UNKNOWN",
        "sites": "UNKNOWN",
        "events": "UNKNOWN",
        "artifacts": "UNKNOWN",
        "units": "UNKNOWN",
        "relationships": "UNKNOWN",
    },
}


def main():
    p = os.path.join(EXT, "save_metadata.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(META, f, indent=1, ensure_ascii=False)
    print("wrote", p)

    proc = os.path.abspath(os.path.join(HERE, "..", "..", "processed"))
    os.makedirs(proc, exist_ok=True)
    with open(os.path.join(proc, "save_metadata.md"),
              "w", encoding="utf-8") as f:
        f.write("# DF-Chronicles :: save_metadata.md\n\n")
        f.write("Verbatim metadata recovered from `world.sav`.\n\n")
        f.write("| field | value | offset | certainty |\n|---|---|---|---|\n")
        for r in META["records"]:
            v = r["value"]
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            if v is None:
                v = "_(see note)_"
            f.write(f"| `{r['field']}` | {v} | {r.get('offset_in_payload','-')} "
                    f"| **{r['certainty']}** |\n")
        f.write("\n## Notes\n\n")
        for r in META["records"]:
            if r.get("note"):
                f.write(f"- **{r['field']}** — {r['note']}\n")
            if r.get("basis"):
                f.write(f"- **{r['field']}** — basis: {r['basis']}\n")
        f.write("\n## Confirmed entities\n\n")
        f.write("```\n")
        for k, v in META["confirmed_entities"].items():
            f.write(f"{k}: {v}\n")
        f.write("```\n")
    print("wrote processed/save_metadata.md")


if __name__ == "__main__":
    main()