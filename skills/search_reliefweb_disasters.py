"""
Search ReliefWeb disasters by country, type, and date.
Supplemental to Montandon — provides disaster metadata, GLIDE codes, and status.
"""
from reliefweb_core import _rw_paginate, _rw_filter, _trim_rw_disaster


def search_reliefweb_disasters(
    country_code: str | None = None,
    country_codes: list[str] | None = None,
    disaster_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict:
    """
    Search ReliefWeb disasters to supplement Montandon event records.

    Args:
        country_code:   ISO 3166-1 alpha-3, e.g. "BGD"
        country_codes:  List of ISO alpha-3 codes, e.g. ["AFG","PAK"].
                        Supersedes country_code if both provided.
        disaster_type:  Plain-language type: "Flood", "Earthquake", "Cyclone", etc.
        date_from:      Start date "YYYY-MM-DD"
        date_to:        End date   "YYYY-MM-DD"
        status:         "current", "alert", or "past"
        query:          Free-text search across disaster fields
        limit:          Max results (default 20)

    Returns:
        Dict with keys:
          items:       list of disaster dicts (id, name, glide, status, types,
                       countries, country_iso3, dates, description, url)
          total_count: server-side total matching count
          count:       items returned in this response
    """
    cc = country_codes or ([country_code] if country_code else None)

    filter_obj = _rw_filter(
        country_iso3=cc,
        disaster_type=disaster_type,
        status=status,
        date_field="date.event",
        date_from=date_from,
        date_to=date_to,
    )

    body: dict = {
        "limit": min(limit, 100),
        "sort": ["date.event:desc"],
        "fields": {
            "include": [
                "name", "glide", "status", "description",
                "primary_type", "type", "country", "date", "url",
            ]
        },
    }

    if filter_obj:
        body["filter"] = filter_obj
    if query:
        body["query"] = {"value": query, "operator": "AND"}

    try:
        items, total_count = _rw_paginate("/disasters", body, limit)
        return {
            "items": [_trim_rw_disaster(it) for it in items],
            "total_count": total_count,
            "count": len(items),
        }
    except Exception as e:
        return {"error": str(e), "items": [], "total_count": 0, "count": 0}
