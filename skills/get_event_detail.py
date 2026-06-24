"""
Fetch full detail for a single disaster event: metadata, hazards, and impacts.
"""
from montandon_core import (
    _eq, _post_search, _trim_event, _trim_hazard, _trim_impact,
    _colls_by_type, _EVENT_FIELDS, _HAZARD_FIELDS, _IMPACT_FIELDS,
)


def get_event_detail(corr_id: str, collection: str | None = None) -> dict:
    """
    Get full detail for one event: its source record plus all cross-source hazards and impacts.

    Args:
        corr_id:    The monty:corr_id from a search_events result, e.g.
                    "20260530-BEL-1262724-MH0600-1-GCDB"
        collection: Optional — the specific events collection the event came from,
                    e.g. "gdacs-events". Speeds up lookup; inferred if omitted.

    Returns:
        Dict with keys:
          event:    trimmed event dict (from the specified or first-found source)
          hazards:  list of trimmed hazard dicts across all sources (may be empty)
          impacts:  list of trimmed impact dicts across all sources (each is one typed estimate row)

    Note:
        monty:corr_id pairs all items for the same real-world event across sources.
        Hazards and impacts are returned from ALL sources, not just the event's source —
        use the 'collection' field on each row to identify its origin.
        Group impacts by impact_type to summarise; EM-DAT 'cost' rows are thousands of USD.
    """
    event_colls = (
        [collection] if collection
        else _colls_by_type("-events", exclude_prefixes=("reference-",))
    )

    feats = _post_search({
        "collections": event_colls,
        "filter-lang": "cql2-json",
        "filter": _eq("monty:corr_id", corr_id),
        "limit": 1,
        "fields": _EVENT_FIELDS,
    }).get("features", [])

    if not feats:
        searched = collection or "all source collections"
        return {"error": f"Event with corr_id {corr_id!r} not found in {searched}"}

    hazard_colls = _colls_by_type("-hazards")
    impact_colls = _colls_by_type("-impacts")

    hazards = []
    if hazard_colls:
        try:
            hazards = [
                _trim_hazard(it)
                for it in _post_search({
                    "collections": hazard_colls,
                    "filter-lang": "cql2-json",
                    "filter": _eq("monty:corr_id", corr_id),
                    "limit": 50,
                    "fields": _HAZARD_FIELDS,
                }).get("features", [])
            ]
        except Exception:
            pass

    impacts = []
    if impact_colls:
        try:
            impacts = [
                _trim_impact(it)
                for it in _post_search({
                    "collections": impact_colls,
                    "filter-lang": "cql2-json",
                    "filter": _eq("monty:corr_id", corr_id),
                    "limit": 100,
                    "fields": _IMPACT_FIELDS,
                }).get("features", [])
            ]
        except Exception:
            pass

    return {
        "event": _trim_event(feats[0]),
        "hazards": hazards,
        "impacts": impacts,
    }
