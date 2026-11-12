# get_event_detail

Full record for one event: metadata plus the hazards, impacts, and responses that share its `corr_id`, from every source collection.

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
- `hazards`, `impacts`, and `responses` are looked up in **all source collections** by `corr_id` — each row includes a `collection` field showing its origin. Another source's rows appear only when that source gave the event the same `corr_id`, which is the exception, so a one-source result does not mean other sources have nothing on the event.
- Group `impacts` by `impact_type` to summarise per event
- EM-DAT `cost` rows are in **thousands of USD** — multiply × 1,000 when presenting
- Empty `hazards`, `impacts`, or `responses` is normal — not all sources populate all four collection types. `responses` will almost always be empty — only `cems` and `charter` currently publish response items.
- `responses` are actions taken or products produced (a CEMS grading map, a Charter VAP) — **not** impact estimates. Don't fold `response_type`/`status`/`producer` into an impact summary; report them separately (e.g. "a CEMS grading product was published for this event").

## Note on corr_id semantics

`monty:corr_id` is generated per source from the item's own date, country, grid block, hazard
code and episode. It ties an event to its own hazards, impacts and responses within that source. It is
**not** a cross-source join key: two sources describing the same real-world event usually get different
corr_ids. This skill queries every source collection by the corr_id, but only rows that carry that exact
value come back. To find the same event in other sources, use `search_events` per source with country,
hazard code and a date window, and compare the records.
