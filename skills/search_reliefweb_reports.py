"""
Search ReliefWeb reports (situation updates, assessments, PDF documents).
Supplemental to Montandon — provides situational context and downloadable resources.
"""
from reliefweb_core import _rw_paginate, _rw_filter, _trim_rw_report


def search_reliefweb_reports(
    country_code: str | None = None,
    country_codes: list[str] | None = None,
    disaster_id: int | None = None,
    disaster_name: str | None = None,
    query: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict:
    """
    Search ReliefWeb reports to supplement Montandon data with documents.

    Args:
        country_code:    ISO 3166-1 alpha-3, e.g. "PHL"
        country_codes:   List of ISO alpha-3 codes for regional queries.
                         Supersedes country_code if both provided.
        disaster_id:     ReliefWeb disaster ID (from search_reliefweb_disasters)
        disaster_name:   Disaster name to filter by
        query:           Free-text search across report fields
        date_from:       Start date "YYYY-MM-DD" (filters by publication date)
        date_to:         End date   "YYYY-MM-DD"
        limit:           Max results (default 20)

    Returns:
        Dict with keys:
          items:       list of report dicts (id, title, body_snippet, countries,
                       disasters with glide, source, format, files with download
                       URLs, dates, url)
          total_count: server-side total matching count
          count:       items returned in this response

    Note:
        Each item includes a "files" array with direct download URLs and MIME types.
        One report may have multiple files (e.g. PDF + Excel).
    """
    cc = country_codes or ([country_code] if country_code else None)

    filter_obj = _rw_filter(
        country_iso3=cc,
        disaster_id=disaster_id,
        disaster_name=disaster_name,
        date_field="date.original",
        date_from=date_from,
        date_to=date_to,
    )

    body: dict = {
        "limit": min(limit, 100),
        "sort": ["date.original:desc"],
        "fields": {
            "include": [
                "title", "body-html", "country", "disaster", "disaster_type",
                "date", "source", "format", "language", "file", "url",
            ]
        },
    }

    if filter_obj:
        body["filter"] = filter_obj
    if query:
        body["query"] = {"value": query, "operator": "AND"}

    try:
        items, total_count = _rw_paginate("/reports", body, limit)
        return {
            "items": [_trim_rw_report(it) for it in items],
            "total_count": total_count,
            "count": len(items),
        }
    except Exception as e:
        return {"error": str(e), "items": [], "total_count": 0, "count": 0}
