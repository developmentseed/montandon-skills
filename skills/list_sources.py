"""
List all live Montandon data sources and their collection types.
"""
from collections import defaultdict
from montandon_core import _available_collections


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
