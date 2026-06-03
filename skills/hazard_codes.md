# hazard_codes

Map plain language to UNDRR-ISC codes. No API call — pure in-memory lookup.

## Workflow

1. Call `hazard_codes("flood")` to get candidate codes
2. If multiple plausible codes return, ask the user to clarify before querying
3. Pass `undrr_code` to search functions — never raw EM-DAT codes
4. Tell the user which code you used

## Three taxonomies

`monty:hazard_codes` on each item contains codes from all three systems:
- **UNDRR-ISC** (`MH0309`) — primary; always use this
- **GLIDE** (`TC`) — auto-expanded by search functions
- **EM-DAT** (`nat-met-sto-tro`) — auto-expanded by search functions

You only need to pass the UNDRR code — expansion to GLIDE and EM-DAT is automatic.

## Quick reference

| Plain language | UNDRR | GLIDE |
|----------------|-------|-------|
| Flood (riverine) | MH0600 | FL |
| Flash flood | MH0603 | FF |
| Coastal flood | MH0601 | FL |
| Tropical cyclone | MH0309 | TC |
| Earthquake | GH0001 | EQ |
| Volcanic eruption | GH0101 | VO |
| Landslide | GH0200 | LS |
| Drought | MH0400 | DR |
| Wildfire | MH0800 | WF |
| Extreme temperature | MH0500 | EP |
| Tsunami | GH0300 | TS |

Full taxonomy with EM-DAT mappings: `skills/taxonomy.json`
