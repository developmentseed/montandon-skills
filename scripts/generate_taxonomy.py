#!/usr/bin/env python3
"""
Regenerate skills/taxonomy.json's hazard_codes section from the authoritative
pystac-monty HazardProfiles.csv (UNDRR-ISC 2025 hazard taxonomy):
https://github.com/IFRCGo/pystac-monty

Takes the full upstream table as-is — no filtering by presumed relevance. Which
hazard codes actually appear in Montandon search results is determined by the
underlying sources, not by this script; hazard_codes()'s job is just to let the
LLM map plain language to the correct code for any code that could appear.

Re-run this whenever IFRCGo/pystac-monty publishes an update to HazardProfiles.csv:
    uv run python scripts/generate_taxonomy.py
"""
import csv
import io
import json
from pathlib import Path

import requests

CSV_URL = "https://raw.githubusercontent.com/IFRCGo/pystac-monty/main/pystac_monty/HazardProfiles.csv"
TAXONOMY_PATH = Path(__file__).parent.parent / "skills" / "taxonomy.json"


def load_rows() -> list[dict]:
    resp = requests.get(CSV_URL, timeout=30)
    resp.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8-sig"))))
    # The upstream CSV contains some literal duplicate rows; drop exact dupes only.
    seen = set()
    deduped = []
    for r in rows:
        key = tuple(r.items())
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def build_entries(rows: list[dict]) -> list[dict]:
    by_code: dict[str, dict] = {}
    for r in rows:
        code = r["undrr_2025_key"]
        entry = by_code.setdefault(code, {
            "undrr": code,
            "glide": r["glide_code"],
            "name": r["label"],
            "cluster": r["cluster_label"],
            "family": r["family_label"],
            "emdat": [],
        })
        if r["emdat_key"] and r["emdat_key"] not in entry["emdat"]:
            entry["emdat"].append(r["emdat_key"])
    return [by_code[k] for k in sorted(by_code)]


def main() -> None:
    rows = load_rows()
    entries = build_entries(rows)
    print(f"Built {len(entries)} hazard_codes entries from {len(rows)} deduped CSV rows")

    taxonomy = json.loads(TAXONOMY_PATH.read_text())
    taxonomy["_source"] = (
        "hazard_codes: https://github.com/IFRCGo/pystac-monty "
        "(pystac_monty/HazardProfiles.csv, UNDRR-ISC 2025 — full upstream table, unfiltered); "
        "impact_types: https://ifrcgo.org/monty-stac-extension/model/taxonomy/#2025-update"
    )
    taxonomy["hazard_codes"] = entries
    TAXONOMY_PATH.write_text(json.dumps(taxonomy, indent=2) + "\n")
    print(f"Wrote {TAXONOMY_PATH}")


if __name__ == "__main__":
    main()
