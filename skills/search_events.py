"""
Search for disaster events across Montandon sources.
"""
from montandon_core import (
    _ov, _and, _datetime_range, _post_search, _trim_event,
    _colls_by_type, _EVENT_FIELDS,
)
from skills.hazard_codes import EMDAT_CODES, GLIDE_CODES


def search_events(
    country_code: str | None = None,
    country_codes: list[str] | None = None,
    hazard_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sources: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """
    Search for disaster events across sources in a single API request.

    Args:
        country_code:  ISO 3166-1 alpha-3 for a single country, e.g. "BGD"
        country_codes: List of ISO alpha-3 codes to match any of, e.g. ["AFG","PAK","IRN"].
                       Use this for regional queries. Supersedes country_code if both provided.
        hazard_code:   UNDRR-ISC code, e.g. "MH0600" (flood), "GH0001" (earthquake).
                       Use hazard_codes() to look up from plain language.
        date_from:     Start date "YYYY-MM-DD"
        date_to:       End date   "YYYY-MM-DD"
        sources:       Optional list of source names to restrict to, e.g. ["emdat", "gdacs"].
                       Default: all available sources.
        limit:         Max results to return (default 50, max 100)

    Returns:
        Dict with keys:
          items:                list of trimmed event dicts (id, collection, corr_id, title,
                                date, country_codes, hazard_codes, description)
          total_matched:        total matching records on the server (may exceed len(items))
          sources_queried:      all sources searched
          sources_with_results: sources represented in the returned items

    Note:
        Each result is a single-source event record. There is no cross-source deduplication
        in v1 — the same disaster may appear once per source that recorded it.
        sources_with_results reflects the returned page; use total_matched to gauge coverage.
    """
    available = _colls_by_type("-events", exclude_prefixes=("reference-",))
    if sources:
        colls = [f"{s}-events" for s in sources if f"{s}-events" in available]
    else:
        colls = available

    clauses = []
    cc = country_codes or ([country_code] if country_code else None)
    if cc:
        clauses.append(_ov("monty:country_codes", cc))
    if hazard_code:
        hazard_values = [hazard_code] + GLIDE_CODES.get(hazard_code, []) + EMDAT_CODES.get(hazard_code, [])
        clauses.append(_ov("monty:hazard_codes", hazard_values))

    body: dict = {
        "collections": colls,
        "limit": min(limit, 100),
        "fields": _EVENT_FIELDS,
    }
    if clauses:
        body["filter-lang"] = "cql2-json"
        body["filter"] = _and(*clauses)
    dt = _datetime_range(date_from, date_to)
    if dt:
        body["datetime"] = dt

    d = _post_search(body)
    items = d.get("features", [])
    total_matched = d.get("numberMatched")

    sources_with_results = sorted({
        it.get("collection", "").replace("-events", "")
        for it in items if it.get("collection")
    })

    return {
        "items": [_trim_event(it) for it in items[:limit]],
        "total_matched": total_matched,
        "sources_queried": [c.replace("-events", "") for c in colls],
        "sources_with_results": sources_with_results,
    }
