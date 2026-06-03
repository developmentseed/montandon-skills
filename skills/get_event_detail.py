"""
Fetch full detail for a single disaster event: metadata, hazards, and impacts.
"""
from montandon_core import (
    _eq, _post_search, _trim_event, _trim_hazard, _trim_impact,
    _available_collections,
)


def get_event_detail(corr_id: str, collection: str | None = None) -> dict:
    """
    Get full detail for one event: its source record, hazards, and impacts.

    Args:
        corr_id:    The monty:corr_id from a search_events result, e.g.
                    "20260530-BEL-1262724-MH0600-1-GCDB"
        collection: Optional — the specific events collection the event came from,
                    e.g. "gdacs-events". Speeds up lookup; inferred if omitted.

    Returns:
        Dict with keys:
          event:    trimmed event dict
          hazards:  list of trimmed hazard dicts (may be empty if source has no hazards)
          impacts:  list of trimmed impact dicts (each is one typed estimate row)

    Note:
        corr_id links an event to its OWN source's hazards/impacts only.
        Cross-source comparison is not supported in v1.
    """
    # Find the event
    event_item = None
    if collection:
        src = collection.replace("-events", "")
        body = {
            "collections": [f"{src}-events"],
            "filter-lang": "cql2-json",
            "filter": _eq("monty:corr_id", corr_id),
            "limit": 1,
        }
        feats = _post_search(body).get("features", [])
        if not feats:
            return {"error": f"Event {corr_id!r} not found in {src}-events"}
        event_item = feats[0]
    else:
        src = None
        event_colls = [
            "emdat-events", "gdacs-events", "pdc-events", "usgs-events",
            "ibtracs-events", "ifrcevent-events", "gfd-events", "glide-events",
            "desinventar-events", "idmc-gidd-events", "idmc-idu-events",
        ]
        for coll in event_colls:
            try:
                body = {
                    "collections": [coll],
                    "filter-lang": "cql2-json",
                    "filter": _eq("monty:corr_id", corr_id),
                    "limit": 1,
                }
                feats = _post_search(body).get("features", [])
                if feats:
                    src = coll.replace("-events", "")
                    event_item = feats[0]
                    break
            except Exception:
                continue
        if src is None:
            return {"error": f"Event {corr_id!r} not found in any collection"}

    event = _trim_event(event_item)
    available = _available_collections()

    # Query hazards and impacts directly by corr_id — avoids related_links which
    # point to internal cluster URLs inaccessible from outside
    hazards = []
    if f"{src}-hazards" in available:
        body = {
            "collections": [f"{src}-hazards"],
            "filter-lang": "cql2-json",
            "filter": _eq("monty:corr_id", corr_id),
            "limit": 20,
        }
        try:
            for it in _post_search(body).get("features", []):
                hazards.append(_trim_hazard(it))
        except Exception:
            pass

    impacts = []
    if f"{src}-impacts" in available:
        body = {
            "collections": [f"{src}-impacts"],
            "filter-lang": "cql2-json",
            "filter": _eq("monty:corr_id", corr_id),
            "limit": 50,
        }
        try:
            for it in _post_search(body).get("features", []):
                impacts.append(_trim_impact(it))
        except Exception:
            pass

    return {"event": event, "hazards": hazards, "impacts": impacts}
