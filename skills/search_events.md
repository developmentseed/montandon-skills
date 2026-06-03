# search_events

Find disaster events across sources.

## Parameters

- `country_code`: single ISO alpha-3 (`"BGD"`)
- `country_codes`: list of ISO alpha-3 for regional queries — server-side filter, more efficient than filtering results yourself
- `hazard_code`: UNDRR-ISC code from `hazard_codes()` — never raw EM-DAT codes
- `date_from` / `date_to`: `"YYYY-MM-DD"`
- `sources`: optional list e.g. `["emdat", "gdacs"]`
- `limit`: default 10

## Returns

```python
{
  "items": [...],               # list of event dicts
  "sources_queried": [...],     # all sources searched
  "sources_with_results": [...] # sources that returned data
}
```

Always report `sources_queried` and `sources_with_results` to the user — this surfaces coverage gaps.

## Notes

- Returns one record per source — same real-world event appears once per source that recorded it
- Use `get_event_detail` to fetch hazards and impacts for a specific result
