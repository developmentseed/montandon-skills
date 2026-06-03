"""
Shared HTTP session, CQL2 filter helpers, and item trimming utilities.
Used by all skills in the skills/ directory.
Token must be set in MONTANDON_TOKEN env var.
"""
import os
import sys
from collections import defaultdict
from typing import Optional

import requests

BASE_URL = "https://montandon-eoapi-stage.ifrc.org/stac"


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------

def _session() -> requests.Session:
    token = os.environ.get("MONTANDON_TOKEN")
    if not token:
        sys.exit(
            "MONTANDON_TOKEN is not set.\n"
            "Run: uv run --env-file .env claude\n"
            "Or:  MONTANDON_TOKEN=<token> uv run claude"
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
    d = _post_search(body)
    while True:
        items.extend(d.get("features", []))
        if len(items) >= max_items:
            break
        nxt = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
        if not nxt:
            break
        r = _get_session().get(nxt, timeout=30)
        r.raise_for_status()
        d = r.json()
    return items[:max_items]


# ---------------------------------------------------------------------------
# CQL2-JSON filter builders
# ---------------------------------------------------------------------------

def _ov(prop: str, values: list) -> dict:
    """a_overlaps filter for array properties (monty:country_codes, monty:hazard_codes)."""
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


def _or(*clauses) -> dict:
    active = [c for c in clauses if c]
    if len(active) == 1:
        return active[0]
    return {"op": "or", "args": list(active)}


# ---------------------------------------------------------------------------
# Item trimming
# ---------------------------------------------------------------------------

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
# Collection discovery
# ---------------------------------------------------------------------------

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
