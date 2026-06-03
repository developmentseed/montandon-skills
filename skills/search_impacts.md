# search_impacts

Find events by impact threshold. Filters on `*-impacts` collections server-side.

## Parameters

Same as `search_events` plus:
- `min_deaths`: minimum deaths (filters `type='death'`)
- `min_displaced`: minimum displaced — matches all `displacement` group types in `taxonomy.json`

Provide `min_deaths` **or** `min_displaced`, not both — they filter different impact rows.

## Impact type coverage by source

| Source | Types available |
|--------|----------------|
| EM-DAT / GDACS / PDC | `death`, `injured`, `affected_total`, `displaced_total`, `cost` |
| IDMC | `displaced_internal`, `evacuated` (not `displaced_total`) |
| DesInventar | `affected_direct`, `affected_indirect`, `destroyed`, `damaged`, `missing` |

`min_displaced` covers all displacement-group types. DesInventar displacement is not covered —
use `search_events` + `get_event_detail` for DesInventar displacement data.

## Notes

- Each result row is one impact-type estimate; rows for the same event share a `corr_id`
- EM-DAT `cost` values are in **thousands of USD** — multiply × 1,000 when presenting
