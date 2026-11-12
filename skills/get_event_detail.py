"""
Fetch full detail for a single disaster event: metadata, hazards, and impacts.
"""
from montandon_core import (
    _eq, _post_search, _trim_event_detail, _trim_hazard, _trim_impact, _trim_response,
    _colls_by_type, _EVENT_DETAIL_FIELDS, _HAZARD_FIELDS, _IMPACT_FIELDS, _RESPONSE_FIELDS,
)


def get_event_detail(corr_id: str, collection: str | None = None) -> dict:
    """
    Get full detail for one event: its source record plus the hazards and impacts that share its
    corr_id, looked up in every source collection.

    Args:
        corr_id:    The monty:corr_id from a search_events result, e.g.
                    "20260530-BEL-1262724-MH0600-1-GCDB"
        collection: Optional — the specific events collection the event came from,
                    e.g. "gdacs-events". Speeds up lookup; inferred if omitted.

    Returns:
        Dict with keys:
          event:     trimmed event dict (from the specified or first-found source), including
                     the full, untruncated source description
          hazards:   list of trimmed hazard dicts across all sources (may be empty)
          impacts:   list of trimmed impact dicts across all sources (each is one typed estimate row)
          responses: list of trimmed response dicts across all sources (may be empty — only
                     'cems' and 'charter' currently publish response items). A response is an
                     action taken or product produced (a CEMS grading map, a Charter VAP) —
                     NOT an impact estimate; don't fold these into an impact summary.

    Note:
        monty:corr_id is generated per source and is NOT a cross-source join key: two sources
        describing the same real-world event usually get different corr_ids. Hazards, impacts,
        and responses are looked up in ALL source collections, but only rows carrying this exact
        corr_id come back, so another source's rows appear only when it shares the value — use the
        'collection' field on each row to identify its origin. To find the same event in other
        sources, search each by country, hazard code and date window.
        Group impacts by impact_type to summarise; EM-DAT 'cost' rows are thousands of USD.
    """
    event_colls = (
        [collection] if collection
        else _colls_by_type("-events")
    )

    feats = _post_search({
        "collections": event_colls,
        "filter-lang": "cql2-json",
        "filter": _eq("monty:corr_id", corr_id),
        "limit": 1,
        "fields": _EVENT_DETAIL_FIELDS,
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

    response_colls = _colls_by_type("-response")
    responses = []
    if response_colls:
        try:
            responses = [
                _trim_response(it)
                for it in _post_search({
                    "collections": response_colls,
                    "filter-lang": "cql2-json",
                    "filter": _eq("monty:corr_id", corr_id),
                    "limit": 50,
                    "fields": _RESPONSE_FIELDS,
                }).get("features", [])
            ]
        except Exception:
            pass

    return {
        "event": _trim_event_detail(feats[0]),
        "hazards": hazards,
        "impacts": impacts,
        "responses": responses,
    }
