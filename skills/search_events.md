# search_events

Find disaster events across sources.

## Parameters

- `country_code`: single ISO alpha-3 (`"BGD"`)
- `country_codes`: list of ISO alpha-3 for regional queries — server-side filter, more efficient than filtering results yourself
- `hazard_code`: UNDRR-ISC code from `hazard_codes()` — never raw EM-DAT codes
- `date_from` / `date_to`: `"YYYY-MM-DD"`
- `sources`: optional list e.g. `["emdat", "gdacs"]`
- `limit`: default 10

## Notes

- Returns one record per source — same real-world event appears once per source that recorded it
- Use `get_event_detail` to fetch hazards and impacts for a specific result
