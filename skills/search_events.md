# search_events

Find disaster events across sources in a single API request.

## Parameters

- `country_code`: single ISO alpha-3 (`"BGD"`)
- `country_codes`: list of ISO alpha-3 for regional queries — server-side filter, more efficient than filtering results yourself
- `hazard_code`: UNDRR-ISC code from `hazard_codes()` — never raw EM-DAT codes
- `date_from` / `date_to`: `"YYYY-MM-DD"`
- `sources`: optional list e.g. `["emdat", "gdacs"]`
- `limit`: default 50, max 100

## Returns

```python
{
  "items": [...],               # list of event dicts
  "total_matched": 1234,        # total server-side matches (may exceed len(items))
  "sources_queried": [...],     # all sources searched
  "sources_with_results": [...] # sources represented in the returned items
}
```

Always report `sources_queried`, `sources_with_results`, and `total_matched` to the user — this surfaces coverage gaps and lets them know if results were truncated.

## Notes

- Returns one record per source — same real-world event appears once per source that recorded it
- `sources_with_results` reflects the returned page only; `total_matched` tells you if items were truncated
- Use `get_event_detail` to fetch hazards and impacts for a specific result
