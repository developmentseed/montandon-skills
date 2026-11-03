# get_event_detail

Full record for one event: metadata plus all cross-source hazards, impacts, and responses.

## Parameters

- `corr_id`: from a `search_events` result — always use exact value, never construct or guess
- `collection`: optional, e.g. `"gdacs-events"` — speeds lookup by searching that collection first

## corr_id formats

- Recent: `YYYYMMDD-ISO3-NUMBER-HAZARDCODE-EPISODE-GCDB`
- Historical EM-DAT: `YYYYMMDD-ISO3-NAT-CLASS-TYPE-SUBTYPE-EPISODE-GCDB`

## Returns

```
{"event": {...}, "hazards": [...], "impacts": [...], "responses": [...]}
```

- `event` is the first matching source record (or from `collection` if specified)
- `hazards`, `impacts`, and `responses` come from **all sources** — each row includes a `collection` field showing its origin. This means you may see the same event's impacts from emdat, idmc, and pdc all in one response.
- Group `impacts` by `impact_type` to summarise per event
- EM-DAT `cost` rows are in **thousands of USD** — multiply × 1,000 when presenting
- Empty `hazards`, `impacts`, or `responses` is normal — not all sources populate all four collection types. `responses` will almost always be empty — only `cems` and `charter` currently publish response items.
- `responses` are actions taken or products produced (a CEMS grading map, a Charter VAP) — **not** impact estimates. Don't fold `response_type`/`status`/`producer` into an impact summary; report them separately (e.g. "a CEMS grading product was published for this event").

## Note on corr_id semantics

`monty:corr_id` is a cross-source identifier — it pairs all items (events, hazards, impacts,
responses) for the same real-world event across sources. This skill queries hazards, impacts,
and responses across all source collections, not just the collection the event was found in.
