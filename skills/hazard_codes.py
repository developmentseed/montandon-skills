"""
Map plain-language hazard terms to UNDRR-ISC 2025 codes.
Self-contained — no API calls, no montandon_core dependency.
Taxonomy source: skills/taxonomy.json
"""
import json
from pathlib import Path

_taxonomy = json.loads((Path(__file__).parent / "taxonomy.json").read_text())
_hazard_data = _taxonomy["hazard_codes"]

# UNDRR-ISC → EM-DAT codes (for hazard filter expansion in search functions)
EMDAT_CODES: dict[str, list[str]] = {
    h["undrr"]: h["emdat"] for h in _hazard_data if h.get("emdat")
}

# UNDRR-ISC → GLIDE codes (auto-derived from taxonomy)
GLIDE_CODES: dict[str, list[str]] = {}
for _h in _hazard_data:
    _undrr, _glide = _h["undrr"], _h["glide"]
    if _undrr not in GLIDE_CODES:
        GLIDE_CODES[_undrr] = []
    if _glide not in GLIDE_CODES[_undrr]:
        GLIDE_CODES[_undrr].append(_glide)


def hazard_codes(query: str) -> list[dict]:
    """
    Look up UNDRR-ISC hazard codes by plain-language term.

    Args:
        query: natural language term, e.g. "flood", "earthquake", "cyclone"

    Returns:
        List of {undrr_code, glide_code, name, emdat_codes} matches. May include multiple
        entries for ambiguous terms — Claude should surface all and ask the user
        to clarify if more than one is plausible.
    """
    q = query.lower().strip()
    seen: set[str] = set()
    results = []
    for h in _hazard_data:
        undrr = h["undrr"]
        synonyms = h.get("synonyms", [])
        name = h["name"]
        if any(q in s or s in q for s in synonyms + [name.lower()]):
            if undrr not in seen:
                seen.add(undrr)
                results.append({
                    "undrr_code": undrr,
                    "glide_code": h["glide"],
                    "name": name,
                    "emdat_codes": h.get("emdat", []),
                })
    return results
