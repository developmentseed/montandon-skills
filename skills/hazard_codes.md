# hazard_codes

Full table of UNDRR-ISC 2025 hazard codes — the complete upstream taxonomy, unfiltered.
No API call — pure in-memory lookup. Not a search function: it returns everything, and
you do the matching yourself by reading the `name` field.

## Workflow

1. Call `hazard_codes()` — it takes no arguments, returns the full table
2. Read the `name` field of each entry and semantically match it to what the user asked
   for (e.g. "hurricane" → the entry named "Tropical Cyclone"). Never guess a code from
   memory — always copy `undrr_code` from the returned list.
3. If more than one entry is plausible (e.g. "storm"), ask the user to clarify before
   querying
4. Pass `undrr_code` to search functions — never raw EM-DAT or GLIDE codes
5. Tell the user which code you used

## Three taxonomies

`monty:hazard_codes` on each item contains codes from all three systems:
- **UNDRR-ISC** (`MH0309`) — primary; always use this
- **GLIDE** (`TC`) — auto-expanded by search functions
- **EM-DAT** (`nat-met-sto-tro`) — auto-expanded by search functions

You only need to pass the UNDRR code — expansion to GLIDE and EM-DAT is automatic.

## Coverage

295 hazard codes — the complete UNDRR-ISC 2025 taxonomy from pystac-monty's
HazardProfiles.csv, taken as-is with no relevance filtering. This intentionally
includes families with no current Montandon coverage (chemical contaminants, cyber
hazards, societal/conflict, extraterrestrial) — which hazard types actually appear in
search results is determined by Montandon's underlying sources, not by this table.
Pre-filtering it would risk silently making a real, newly-ingested hazard type
unsearchable, the same failure mode that caused earlier versions of this table to miss
codes.

Each entry includes `cluster` and `family` (the UNDRR-ISC grouping) as extra context —
useful for disambiguating between plausible matches or explaining a code to the user.

## Updating

Source data lives in `skills/taxonomy.json`. Regenerate it from the latest upstream CSV
with:
```
uv run python scripts/generate_taxonomy.py
```
Re-run this if IFRCGo/pystac-monty publishes an update to HazardProfiles.csv.
