"""
Montandon STAC API tools for Claude Code.

Load via SKILL.md. Token must be set in MONTANDON_TOKEN env var.
Run: MONTANDON_TOKEN=... uv run claude  (or: op run --env-file ... -- uv run claude)
"""
import os
import sys
from collections import defaultdict
from typing import Optional

import requests

BASE_URL = "https://montandon-eoapi-stage.ifrc.org/stac"

# ---------------------------------------------------------------------------
# Hazard taxonomy (UNDRR-ISC 2025 primary codes + common synonyms)
# Full list: https://github.com/IFRCGo/monty-stac-extension/blob/main/hazard-codes.md
# ---------------------------------------------------------------------------
HAZARD_TABLE = [
    # (undrr_code, glide_code, name, synonyms...)
    ("MH0600", "FL",  "Flood (general/riverine)", ["flood", "flooding", "inundation", "riverine flood"]),
    ("MH0603", "FF",  "Flash flood",               ["flash flood", "flash flooding", "pluvial", "surface water flood"]),
    ("MH0601", "FL",  "Coastal flood",              ["coastal flood", "storm surge", "sea flood", "tidal flood"]),
    ("MH0602", "FL",  "Urban flood",                ["urban flood", "city flood"]),
    ("MH0309", "TC",  "Tropical cyclone",           ["cyclone", "typhoon", "hurricane", "tropical storm", "tc"]),
    ("MH0101", "ST",  "Severe storm / convective",  ["storm", "severe storm", "thunderstorm", "hailstorm", "lightning", "tornado", "downburst"]),
    ("MH0103", "ST",  "Extra-tropical storm",       ["extratropical storm", "winter storm", "blizzard", "nor'easter"]),
    ("GH0001", "EQ",  "Earthquake",                 ["earthquake", "quake", "seismic", "tremor", "eq"]),
    ("GH0101", "VO",  "Volcanic eruption",          ["volcano", "volcanic", "eruption", "lava", "ash cloud"]),
    ("GH0200", "LS",  "Landslide / mass movement",  ["landslide", "mudslide", "rockslide", "avalanche", "debris flow", "mass movement"]),
    ("MH0400", "DR",  "Drought",                    ["drought", "dry spell", "water scarcity", "desiccation"]),
    ("MH0800", "WF",  "Wildfire",                   ["wildfire", "forest fire", "bushfire", "brush fire"]),
    ("MH0500", "EP",  "Extreme temperature",        ["heatwave", "heat wave", "extreme heat", "cold wave", "freeze", "frost"]),
    ("MH0300", "HU",  "Hailstorm",                  ["hail", "hailstorm"]),
    ("GH0300", "TS",  "Tsunami",                    ["tsunami", "tidal wave"]),
    ("EN0205", "AC",  "Accident / technological",   ["accident", "industrial accident", "chemical spill", "oil spill", "explosion"]),
    ("TL0048", "AC",  "Road transport accident",    ["road accident", "traffic accident", "vehicle crash"]),
    ("TL0049", "AC",  "Water transport accident",   ["boat accident", "ship accident", "maritime accident"]),
    ("TL0051", "AC",  "Air transport accident",     ["plane crash", "air accident", "aviation accident"]),
    ("TL0052", "AC",  "Rail transport accident",    ["train accident", "rail accident"]),
    ("MH0603", "FF",  "Flash flood",                ["rapid onset flood"]),
    ("GH0311", "EQ",  "Earthquake (shallow)",       ["shallow earthquake"]),
]


def hazard_codes(query: str) -> list[dict]:
    """
    Look up UNDRR-ISC hazard codes by plain-language term.

    Args:
        query: natural language term, e.g. "flood", "earthquake", "cyclone"

    Returns:
        List of {undrr_code, glide_code, name} matches. May include multiple
        entries for ambiguous terms — Claude should surface all and ask the user
        to clarify if more than one is plausible.
    """
    q = query.lower().strip()
    seen = set()
    results = []
    for row in HAZARD_TABLE:
        undrr, glide, name, synonyms = row
        if any(q in s or s in q for s in synonyms + [name.lower()]):
            key = undrr
            if key not in seen:
                seen.add(key)
                results.append({"undrr_code": undrr, "glide_code": glide, "name": name})
    return results


# ---------------------------------------------------------------------------
# Shared HTTP session + internal helpers
# ---------------------------------------------------------------------------

def _session() -> requests.Session:
    token = os.environ.get("MONTANDON_TOKEN")
    if not token:
        sys.exit(
            "MONTANDON_TOKEN is not set.\n"
            "Run: MONTANDON_TOKEN=<token> uv run claude\n"
            "Or:  op run --env-file .env -- uv run claude"
        )
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


_sess: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _sess
    if _sess is None:
        _sess = _session()
    return _sess


def _get(path: str, params: dict | None = None) -> dict:
    r = _get_session().get(BASE_URL + path, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def _post_search(body: dict) -> dict:
    r = _get_session().post(BASE_URL + "/search", json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def _paginate_search(body: dict, max_items: int) -> list[dict]:
    """POST /search with automatic next-page following up to max_items."""
    items = []
    while True:
        d = _post_search(body)
        items.extend(d.get("features", []))
        if len(items) >= max_items:
            break
        nxt = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
        if not nxt:
            break
        # next href includes full params; re-POST with token=token (session handles auth)
        r = _get_session().get(nxt, timeout=30)
        r.raise_for_status()
        d = r.json()
        items.extend(d.get("features", []))
        if len(items) >= max_items:
            break
        nxt = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
        if not nxt:
            break
        body = {**body, "token": nxt}  # eoapi uses cursor; fall out if unclear
        break  # single next-page follow is enough for typical limits
    return items[:max_items]


def _ov(prop: str, values: list) -> dict:
    """CQL2-JSON a_overlaps filter for array properties."""
    return {"op": "a_overlaps", "args": [{"property": prop}, values]}


def _eq(prop: str, value) -> dict:
    return {"op": "=", "args": [{"property": prop}, value]}


def _gt(prop: str, value) -> dict:
    return {"op": ">", "args": [{"property": prop}, value]}


def _and(*clauses) -> dict:
    active = [c for c in clauses if c]
    if len(active) == 1:
        return active[0]
    return {"op": "and", "args": list(active)}


def _trim_event(item: dict) -> dict:
    p = item.get("properties", {})
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "corr_id": p.get("monty:corr_id"),
        "title": p.get("title"),
        "date": p.get("datetime") or p.get("start_datetime"),
        "country_codes": p.get("monty:country_codes", []),
        "hazard_codes": p.get("monty:hazard_codes", []),
        "description": (p.get("description") or "")[:200] or None,
        "related_links": [
            l["href"] for l in item.get("links", []) if l.get("rel") == "related"
        ],
    }


def _trim_impact(item: dict) -> dict:
    p = item.get("properties", {})
    detail = p.get("monty:impact_detail", {})
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "corr_id": p.get("monty:corr_id"),
        "date": p.get("datetime") or p.get("start_datetime"),
        "country_codes": p.get("monty:country_codes", []),
        "hazard_codes": p.get("monty:hazard_codes", []),
        "impact_type": detail.get("type"),
        "impact_value": detail.get("value"),
        "impact_unit": detail.get("unit"),
        "impact_category": detail.get("category"),
        "estimate_type": detail.get("estimate_type"),
    }


def _trim_hazard(item: dict) -> dict:
    p = item.get("properties", {})
    detail = p.get("monty:hazard_detail", {})
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "corr_id": p.get("monty:corr_id"),
        "date": p.get("datetime") or p.get("start_datetime"),
        "hazard_codes": p.get("monty:hazard_codes", []),
        "severity_value": detail.get("severity_value"),
        "severity_unit": detail.get("severity_unit"),
        "estimate_type": detail.get("estimate_type"),
    }


def _datetime_range(date_from: str | None, date_to: str | None) -> str | None:
    if date_from and date_to:
        return f"{date_from}T00:00:00Z/{date_to}T23:59:59Z"
    if date_from:
        return f"{date_from}T00:00:00Z/.."
    if date_to:
        return f"../{date_to}T23:59:59Z"
    return None


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

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
        clauses.append(_ov("monty:hazard_codes", [hazard_code]))

    dt = _datetime_range(date_from, date_to)

    # Query per-collection and merge to avoid multi-collection CQL2 server errors
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


def get_event_detail(corr_id: str, collection: str | None = None) -> dict:
    """
    Get full detail for one event: its source record, hazards, and impacts.

    Args:
        corr_id:    The monty:corr_id from a search_events result, e.g.
                    "20260530-BEL-1262724-MH0600-1-GCDB"
        collection: Optional — the specific events collection the event came from,
                    e.g. "gdacs-events". Speeds up lookup; inferred from corr_id if omitted.

    Returns:
        Dict with keys:
          event:    trimmed event dict
          hazards:  list of trimmed hazard dicts (may be empty if source has no hazards)
          impacts:  list of trimmed impact dicts (each is one typed estimate row)

    Note:
        corr_id links an event to its OWN source's hazards/impacts only.
        Cross-source comparison is not supported in v1.
    """
    # Determine source from collection name or by scanning event collections
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

    # Follow related links to get hazards + impacts from same source
    hazards = []
    impacts = []
    seen_hrefs = set()
    for href in event["related_links"]:
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        try:
            r = _get_session().get(href, timeout=20)
            r.raise_for_status()
            it = r.json()
            coll = it.get("collection", "")
            if "hazard" in coll:
                hazards.append(_trim_hazard(it))
            elif "impact" in coll:
                impacts.append(_trim_impact(it))
        except Exception:
            continue

    # Fallback: if related links gave nothing, filter hazard/impact collections by corr_id
    if not hazards and f"{src}-hazards" in _available_collections():
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

    if not impacts and f"{src}-impacts" in _available_collections():
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


_cached_collections: list[str] | None = None


def _available_collections() -> list[str]:
    global _cached_collections
    if _cached_collections is not None:
        return _cached_collections
    colls = []
    path = "/collections"
    while path:
        d = _get(path)
        colls.extend(c["id"] for c in d.get("collections", []))
        nxt = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
        if nxt:
            r = _get_session().get(nxt, timeout=30)
            r.raise_for_status()
            d = r.json()
            colls.extend(c["id"] for c in d.get("collections", []))
        path = None
    _cached_collections = colls
    return colls


def list_sources() -> list[dict]:
    """
    List all live data sources and their collection types.

    Returns:
        List of dicts {source, types} where types is a list of available
        collection types for that source: "events", "hazards", "impacts".
        Use this to understand what's queryable before running other tools.

    Note:
        Not all sources have all three collection types.
        Data completeness varies by source — some may be partially loaded.
    """
    colls = _available_collections()
    by_source: dict[str, list[str]] = defaultdict(list)
    for c in colls:
        parts = c.rsplit("-", 1)
        if len(parts) == 2:
            src, typ = parts
            by_source[src].append(typ)
    return [
        {"source": src, "types": sorted(types)}
        for src, types in sorted(by_source.items())
    ]


def search_impacts(
    hazard_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_deaths: float | None = None,
    min_displaced: float | None = None,
    country_code: str | None = None,
    sources: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search for events meeting impact thresholds (deaths, displaced, etc.).

    Args:
        hazard_code:    UNDRR-ISC code, e.g. "GH0001" (earthquake). Use hazard_codes() for lookup.
        date_from:      Start date "YYYY-MM-DD"
        date_to:        End date   "YYYY-MM-DD"
        min_deaths:     Minimum reported deaths (filters on impact_detail.type='death')
        min_displaced:  Minimum reported displaced (filters on type='displaced_total')
        country_code:   ISO 3166-1 alpha-3, e.g. "PHL"
        sources:        Optional list of source names, e.g. ["emdat"]. Default: all sources with impacts.
        limit:          Max results (default 10, max ~100). Each row is one impact-type estimate.

    Returns:
        List of trimmed impact dicts, each representing one estimate row. Rows for the same
        event share a corr_id. Multiple rows per event is normal (deaths, affected, cost are separate).

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
    if country_code:
        clauses.append(_ov("monty:country_codes", [country_code]))
    if hazard_code:
        clauses.append(_ov("monty:hazard_codes", [hazard_code]))
    if min_deaths is not None:
        clauses.append(_and(_eq("monty:impact_detail.type", "death"), _gt("monty:impact_detail.value", min_deaths)))
    elif min_displaced is not None:
        clauses.append(_and(_eq("monty:impact_detail.type", "displaced_total"), _gt("monty:impact_detail.value", min_displaced)))

    dt = _datetime_range(date_from, date_to)

    # Query per-collection and merge to avoid multi-collection CQL2 server errors
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

    return [_trim_impact(it) for it in items[:limit]]
