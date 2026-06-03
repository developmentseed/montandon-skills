"""
Search for disaster events by impact thresholds (deaths, displaced, etc.).
"""
import json
from pathlib import Path as _Path

from montandon_core import _ov, _eq, _gt, _and, _or, _datetime_range, _paginate_search, _trim_impact
from skills.hazard_codes import EMDAT_CODES, GLIDE_CODES

_taxonomy = json.loads((_Path(__file__).parent / "taxonomy.json").read_text())
# All displacement-group impact types — drives the min_displaced filter
_DISPLACEMENT_TYPES: list[str] = [
    t["code"] for t in _taxonomy["impact_types"] if t["group"] == "displacement"
]


def search_impacts(
    hazard_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_deaths: float | None = None,
    min_displaced: float | None = None,
    country_code: str | None = None,
    country_codes: list[str] | None = None,
    sources: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """
    Search for events meeting impact thresholds (deaths, displaced, etc.).

    Args:
        hazard_code:    UNDRR-ISC code, e.g. "GH0001" (earthquake). Use hazard_codes() for lookup.
        date_from:      Start date "YYYY-MM-DD"
        date_to:        End date   "YYYY-MM-DD"
        min_deaths:     Minimum reported deaths (filters on impact_detail.type='death')
        min_displaced:  Minimum displaced — matches all displacement-group types in taxonomy.json
                        (displaced_total, displaced_internal, displaced_external, evacuated,
                        relocated, homeless)
        country_code:   ISO 3166-1 alpha-3, e.g. "PHL"
        country_codes:  List of ISO alpha-3 codes to match any of, e.g. ["ETH","KEN","SOM"].
                        Use for regional queries. Supersedes country_code if both provided.
        sources:        Optional list of source names, e.g. ["emdat"]. Default: all sources with impacts.
        limit:          Max results (default 10, max ~100). Each row is one impact-type estimate.

    Returns:
        Dict with keys:
          items:                list of trimmed impact dicts (each is one estimate row;
                                rows for the same event share a corr_id)
          sources_queried:      all sources searched
          sources_with_results: sources that returned at least one result

    Note:
        Impact figures are per-source estimates. Different sources may report different numbers
        for the same disaster. This is expected — compare corr_ids to spot duplicates.
        min_deaths and min_displaced cannot be combined in one query (they filter different rows);
        provide one at a time for clarity.
    """
    all_impact_colls = [
        "desinventar-impacts", "emdat-impacts", "gdacs-impacts", "gfd-impacts",
        "idmc-gidd-impacts", "idmc-idu-impacts", "pdc-impacts",
    ]
    if sources:
        colls = [f"{s}-impacts" for s in sources if f"{s}-impacts" in all_impact_colls]
    else:
        colls = all_impact_colls

    clauses = []
    cc = country_codes or ([country_code] if country_code else None)
    if cc:
        clauses.append(_ov("monty:country_codes", cc))
    if hazard_code:
        hazard_values = [hazard_code] + GLIDE_CODES.get(hazard_code, []) + EMDAT_CODES.get(hazard_code, [])
        clauses.append(_ov("monty:hazard_codes", hazard_values))
    if min_deaths is not None:
        clauses.append(_and(_eq("monty:impact_detail.type", "death"), _gt("monty:impact_detail.value", min_deaths)))
    elif min_displaced is not None:
        displacement_type = _or(*[_eq("monty:impact_detail.type", t) for t in _DISPLACEMENT_TYPES])
        clauses.append(_and(displacement_type, _gt("monty:impact_detail.value", min_displaced)))

    dt = _datetime_range(date_from, date_to)

    items: list[dict] = []
    sources_with_results: list[str] = []
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
            new_items = _paginate_search(body, limit - len(items))
            if new_items:
                sources_with_results.append(coll.replace("-impacts", ""))
            items.extend(new_items)
        except Exception:
            continue

    return {
        "items": [_trim_impact(it) for it in items[:limit]],
        "sources_queried": [c.replace("-impacts", "") for c in colls],
        "sources_with_results": sources_with_results,
    }
