"""
Shared HTTP session, filter builders, and item trimming for the ReliefWeb API.
Separate from montandon_core.py — different API, auth, and filter syntax.
"""
import os
from typing import Optional

import requests

RW_BASE_URL = "https://api.reliefweb.int/v2"


def _get_appname() -> str:
    appname = os.environ.get("RELIEFWEB_APPNAME")
    if not appname:
        raise RuntimeError(
            "RELIEFWEB_APPNAME is not set.\n"
            "Add it to .env and run: uv run --env-file .env claude"
        )
    return appname


_rw_sess: Optional[requests.Session] = None


def _get_rw_session() -> requests.Session:
    global _rw_sess
    if _rw_sess is None:
        _rw_sess = requests.Session()
    return _rw_sess


def _rw_post(endpoint: str, body: dict) -> dict:
    url = f"{RW_BASE_URL}{endpoint}"
    r = _get_rw_session().post(
        url, json=body, params={"appname": _get_appname()}, timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _rw_paginate(endpoint: str, body: dict, max_items: int) -> tuple[list[dict], int]:
    """POST with offset/limit pagination. Returns (items, total_count)."""
    items: list[dict] = []
    total_count = 0
    offset = body.get("offset", 0)
    page_size = min(body.get("limit", 50), 100)

    while len(items) < max_items:
        req = {**body, "limit": min(page_size, max_items - len(items)), "offset": offset}
        resp = _rw_post(endpoint, req)
        total_count = resp.get("totalCount", 0)
        data = resp.get("data", [])
        if not data:
            break
        items.extend(data)
        offset += len(data)
        if len(data) < page_size:
            break

    return items[:max_items], total_count


# ---------------------------------------------------------------------------
# Filter builders
# ---------------------------------------------------------------------------

def _rw_filter(
    country_iso3: list[str] | None = None,
    disaster_type: str | None = None,
    disaster_id: int | None = None,
    disaster_name: str | None = None,
    status: str | None = None,
    date_field: str = "date.event",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict | None:
    conditions = []

    if country_iso3:
        if len(country_iso3) == 1:
            conditions.append({"field": "country.iso3", "value": country_iso3[0]})
        else:
            conditions.append({"field": "country.iso3", "value": country_iso3, "operator": "OR"})

    if disaster_type:
        conditions.append({"field": "type", "value": disaster_type})

    if disaster_id:
        conditions.append({"field": "disaster.id", "value": disaster_id})
    elif disaster_name:
        conditions.append({"field": "disaster.name", "value": disaster_name})

    if status:
        conditions.append({"field": "status", "value": status})

    if date_from or date_to:
        date_val: dict = {}
        if date_from:
            date_val["from"] = f"{date_from}T00:00:00+00:00"
        if date_to:
            date_val["to"] = f"{date_to}T23:59:59+00:00"
        conditions.append({"field": date_field, "value": date_val})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"operator": "AND", "conditions": conditions}


# ---------------------------------------------------------------------------
# Item trimming
# ---------------------------------------------------------------------------

def _trim_rw_disaster(item: dict) -> dict:
    f = item.get("fields", {})
    return {
        "id": item.get("id"),
        "name": f.get("name"),
        "glide": f.get("glide"),
        "status": f.get("status"),
        "description": (f.get("description") or "")[:400] or None,
        "primary_type": f.get("primary_type", {}).get("name") if isinstance(f.get("primary_type"), dict) else None,
        "types": [t.get("name") for t in f.get("type", [])],
        "countries": [c.get("name") for c in f.get("country", [])],
        "country_iso3": [c.get("iso3") for c in f.get("country", [])],
        "date_event": (f.get("date") or {}).get("event"),
        "date_created": (f.get("date") or {}).get("created"),
        "url": f.get("url"),
        "href": item.get("href"),
    }


def _trim_rw_report(item: dict) -> dict:
    f = item.get("fields", {})
    files = f.get("file", [])
    return {
        "id": item.get("id"),
        "title": f.get("title"),
        "body_snippet": (f.get("body-html") or "")[:500] or None,
        "date_original": (f.get("date") or {}).get("original"),
        "date_created": (f.get("date") or {}).get("created"),
        "countries": [c.get("name") for c in f.get("country", [])],
        "country_iso3": [c.get("iso3") for c in f.get("country", [])],
        "disasters": [
            {"id": d.get("id"), "name": d.get("name"), "glide": d.get("glide")}
            for d in f.get("disaster", [])
        ],
        "source": [s.get("name") for s in f.get("source", [])] if isinstance(f.get("source"), list) else f.get("source"),
        "format": [fmt.get("name") for fmt in f.get("format", [])] if isinstance(f.get("format"), list) else f.get("format"),
        "language": [lang.get("name") for lang in f.get("language", [])] if isinstance(f.get("language"), list) else f.get("language"),
        "url": f.get("url"),
        "href": item.get("href"),
        "files": [
            {
                "filename": fi.get("filename"),
                "mimetype": fi.get("mimetype"),
                "url": fi.get("url"),
                "description": fi.get("description"),
            }
            for fi in files
        ],
        "file_count": len(files),
    }
