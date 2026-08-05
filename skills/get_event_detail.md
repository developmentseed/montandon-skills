# get_event_detail

Full record for one event: metadata plus all cross-source hazards and impacts.

## Parameters

- `corr_id`: from a `search_events` result — always use exact value, never construct or guess
- `collection`: optional, e.g. `"gdacs-events"` — speeds lookup by searching that collection first

## corr_id formats

- Recent: `YYYYMMDD-ISO3-NUMBER-HAZARDCODE-EPISODE-GCDB`
- Historical EM-DAT: `YYYYMMDD-ISO3-NAT-CLASS-TYPE-SUBTYPE-EPISODE-GCDB`

## Returns

```
{"event": {...}, "hazards": [...], "impacts": [...]}
```

- `event` is the first matching source record (or from `collection` if specified)
- `hazards` and `impacts` come from **all sources** — each row includes a `collection` field showing its origin. This means you may see the same event's impacts from emdat, idmc, and pdc all in one response.
- Group `impacts` by `impact_type` to summarise per event
- EM-DAT `cost` rows are in **thousands of USD** — multiply × 1,000 when presenting
- Empty `hazards` or `impacts` is normal — not all sources populate all three collection types

## Note on corr_id semantics

`monty:corr_id` is deterministic **per source**, not a cross-source join key. Two sources
describing the same real-world event can produce **different** corr_ids — country resolution,
hazard normalization, block_id, or episode number can differ between sources. This skill queries
hazards and impacts across all source collections, but by **exact corr_id match** — so it
reliably returns everything chained to that corr_id, but may miss another source's record of the
same event if that source generated a different corr_id. To find all sources covering one
real-world event, call `search_events` with the same hazard code, country, and date range rather
than assuming one corr_id is exhaustive.
