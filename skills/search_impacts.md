# search_impacts

Find events by impact threshold. Filters on `*-impacts` collections server-side.

## Parameters

- `country_code`: single ISO alpha-3 (`"ETH"`)
- `country_codes`: list of ISO alpha-3 for regional queries — supersedes `country_code`
- `date_from` / `date_to`: `"YYYY-MM-DD"`
- `hazard_code`: UNDRR-ISC code from `hazard_codes()` — never raw EM-DAT codes

Plus impact-specific filters:
- `min_deaths`: minimum deaths (filters `type='death'`; results sorted highest-first)
- `min_displaced`: minimum displaced — matches all `displacement` group types in `taxonomy.json` (results sorted highest-first)

Provide `min_deaths` **or** `min_displaced`, not both — they filter different impact rows.

## Impact type coverage by source

| Source | Types available |
|--------|----------------|
| EM-DAT / GDACS / PDC | `death`, `injured`, `affected_total`, `displaced_total`, `cost` |
| IDMC | `displaced_internal`, `evacuated` (not `displaced_total`) |
| DesInventar | `affected_direct`, `affected_indirect`, `destroyed`, `damaged`, `missing` |

`min_displaced` covers all displacement-group types. DesInventar displacement is not covered —
use `search_events` + `get_event_detail` for DesInventar displacement data.

## Returns

```python
{
  "items": [...],               # list of impact rows, sorted by value desc if threshold set
  "total_matched": 1234,        # total server-side matches (may exceed len(items))
  "sources_queried": [...],     # all sources searched
  "sources_with_results": [...] # sources represented in the returned items
}
```

Always report `sources_queried`, `sources_with_results`, and `total_matched` to the user — this surfaces coverage gaps and lets them know if results were truncated.

## Notes

- When `min_deaths` or `min_displaced` is set, results are sorted by impact magnitude (highest first). Use `total_matched` to see how many events met the threshold vs. how many were returned.
- Without an impact filter, results are in default API order (typically reverse-chronological).
- Each result row is one impact-type estimate; rows for the same event share a `corr_id`
- EM-DAT `cost` values are in **thousands of USD** — multiply × 1,000 when presenting
- **IDMC hazard codes:** IDMC-GIDD and IDMC-IDU tag records as `mix-mix-mix-mix` rather than
  specific UNDRR codes. Passing `hazard_code=` will silently exclude all IDMC rows. For
  displacement queries, omit `hazard_code` and filter by country + date only, then sum
  `impact_value` within each `corr_id` group to get per-event totals.
