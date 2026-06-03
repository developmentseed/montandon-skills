"""
Search for disaster events across Montandon sources.
"""
from montandon_core import _ov, _and, _datetime_range, _paginate_search, _trim_event
from skills.hazard_codes import EMDAT_CODES, GLIDE_CODES


def search_events(
    country_code: str | None = None,
    country_codes: list[str] | None = None,
    hazard_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sources: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search for disaster events across sources.

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
        limit:         Max results to return (default 10, max ~100)

    Returns:
        List of trimmed event dicts with keys: id, collection, corr_id, title, date,
        country_codes, hazard_codes, description, related_links.

    Note:
        Each result is a single-source event record. There is no cross-source deduplication
        in v1 — the same disaster may appear once per source that recorded it.
    """
    all_event_colls = [
        "desinventar-events", "emdat-events", "gdacs-events", "gfd-events",
        "glide-events", "ibtracs-events", "idmc-gidd-events", "idmc-idu-events",
        "ifrcevent-events", "pdc-events", "usgs-events",
    ]
    if sources:
        colls = [f"{s}-events" for s in sources if f"{s}-events" in all_event_colls]
    else:
        colls = all_event_colls

    clauses = []
    cc = country_codes or ([country_code] if country_code else None)
    if cc:
        clauses.append(_ov("monty:country_codes", cc))
    if hazard_code:
        hazard_values = [hazard_code] + GLIDE_CODES.get(hazard_code, []) + EMDAT_CODES.get(hazard_code, [])
        clauses.append(_ov("monty:hazard_codes", hazard_values))

    dt = _datetime_range(date_from, date_to)

    items: list[dict] = []
    for coll in colls:
        if len(items) >= limit:
            break
        body: dict = {"collections": [coll], "limit": min(limit, 100)}
        if clauses:
            body["filter-lang"] = "cql2-json"
            body["filter"] = _and(*clauses)
        if dt:
            body["datetime"] = dt
        try:
            items.extend(_paginate_search(body, limit - len(items)))
        except Exception:
            continue

    return [_trim_event(it) for it in items[:limit]]
