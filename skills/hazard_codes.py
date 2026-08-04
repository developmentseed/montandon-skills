"""
Authoritative UNDRR-ISC 2025 hazard code table — the full upstream taxonomy,
unfiltered. Self-contained — no API calls, no montandon_core dependency.
Taxonomy source: skills/taxonomy.json, regenerated via
scripts/generate_taxonomy.py from pystac-monty's HazardProfiles.csv:
https://github.com/IFRCGo/pystac-monty
"""
import json
from pathlib import Path

_taxonomy = json.loads((Path(__file__).parent / "taxonomy.json").read_text())
_hazard_data = _taxonomy["hazard_codes"]

# UNDRR-ISC → EM-DAT codes (for hazard filter expansion in search functions)
EMDAT_CODES: dict[str, list[str]] = {
    h["undrr"]: h["emdat"] for h in _hazard_data if h.get("emdat")
}

# UNDRR-ISC → GLIDE codes (for hazard filter expansion in search functions)
GLIDE_CODES: dict[str, list[str]] = {h["undrr"]: [h["glide"]] for h in _hazard_data}


def hazard_codes() -> list[dict]:
    """
    Full UNDRR-ISC 2025 hazard code table — every code upstream defines, not just the
    ones seen in Montandon data so far (new sources or newly-ingested hazard types
    won't be silently unsearchable).

    Not a search function — it returns every entry unfiltered. Read the `name` field
    yourself and pick the code(s) that match the user's plain-language term; a term like
    "hurricane" or "typhoon" won't appear verbatim in the table but clearly means
    "Tropical Cyclone". If more than one entry is plausible (e.g. "storm" could mean
    several convective hazard types), ask the user to clarify before querying — never
    guess an undrr_code from memory, always copy it from this returned list.

    Returns:
        List of {undrr_code, glide_code, name, cluster, family, emdat_codes}, spanning
        all UNDRR-ISC 2025 families: meteorological/hydrological, geological,
        environmental, chemical, biological, technological, societal, extraterrestrial.
    """
    return [
        {
            "undrr_code": h["undrr"],
            "glide_code": h["glide"],
            "name": h["name"],
            "cluster": h["cluster"],
            "family": h["family"],
            "emdat_codes": h.get("emdat", []),
        }
        for h in _hazard_data
    ]
