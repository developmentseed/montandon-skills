# search_reliefweb_disasters

Search ReliefWeb disasters to supplement Montandon event records.

## Parameters

- `country_code`: single ISO alpha-3 (`"BGD"`)
- `country_codes`: list of ISO alpha-3 for regional queries
- `disaster_type`: plain-language type — `"Flood"`, `"Earthquake"`, `"Cyclone"`, `"Drought"`, etc.
- `date_from` / `date_to`: `"YYYY-MM-DD"`
- `status`: `"current"`, `"alert"`, or `"past"`
- `query`: free-text search
- `limit`: default 20

## Returns

```python
{
  "items": [
    {
      "id": 12345,
      "name": "Bangladesh: Floods - Jun 2024",
      "glide": "FL-2024-000123-BGD",
      "status": "current",
      "primary_type": "Flood",
      "types": ["Flood", "Flash Flood"],
      "countries": ["Bangladesh"],
      "country_iso3": ["BGD"],
      "date_event": "2024-06-15T00:00:00+00:00",
      "description": "...",
      "url": "https://reliefweb.int/disaster/fl-2024-000123-bgd",
      "href": "https://api.reliefweb.int/v2/disasters/12345"
    }
  ],
  "total_count": 42,
  "count": 20
}
```

## When to use

- After a Montandon search, to get recent situation status (current/alert/past)
- To find GLIDE codes for cross-referencing with Montandon events
- To find IFRC Emergency Appeal and response info
- When the user asks about a disaster's current status

## Notes

- ReliefWeb uses plain-language disaster types, not UNDRR-ISC hazard codes
- GLIDE codes overlap with Montandon's `glide` source — use them to cross-reference
- ReliefWeb disaster IDs do NOT match Montandon `corr_id` values
- Use a disaster's `id` to search for related reports via `search_reliefweb_reports`
