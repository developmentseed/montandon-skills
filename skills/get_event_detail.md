# get_event_detail

Full record for one event: metadata, hazards, and impacts.

## Parameters

- `corr_id`: from a `search_events` result — always use exact value, never construct or guess
- `collection`: optional, e.g. `"gdacs-events"` — speeds lookup by skipping other collections

## corr_id formats

- Recent: `YYYYMMDD-ISO3-NUMBER-HAZARDCODE-EPISODE-GCDB`
- Historical EM-DAT: `YYYYMMDD-ISO3-NAT-CLASS-TYPE-SUBTYPE-EPISODE-GCDB`

## Returns

```
{"event": {...}, "hazards": [...], "impacts": [...]}
```

- Group `impacts` by `impact_type` to summarise per event
- EM-DAT `cost` rows are in **thousands of USD** — multiply × 1,000 when presenting
- Empty `hazards` or `impacts` is normal — not all sources populate all three collection types
