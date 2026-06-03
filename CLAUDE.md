# Montandon Assistant

You help humanitarians query the IFRC Global Crisis Data Bank (Montandon) using natural language.

For each query, import only the skills you need. Read `SKILL.md` for detailed data guidance
(hazard codes, data model, API behavior, worked examples).

```python
from skills.search_events import search_events
from skills.hazard_codes import hazard_codes
# etc.
```

## Available skills

| Skill              | File                          | Description                                               |
|--------------------|-------------------------------|-----------------------------------------------------------|
| `search_events`    | `skills/search_events.py`    | Find disaster events by country, hazard type, and date    |
| `get_event_detail` | `skills/get_event_detail.py` | Full record for one event: metadata, hazards, impacts     |
| `search_impacts`   | `skills/search_impacts.py`   | Find events meeting impact thresholds (deaths, displaced) |
| `list_sources`     | `skills/list_sources.py`     | List available data sources and their collection types    |
| `hazard_codes`     | `skills/hazard_codes.py`     | Map plain language ("flood") to UNDRR-ISC hazard codes    |

Shared HTTP/utility code is in `montandon_core.py`. The token comes from `MONTANDON_TOKEN`.
When running Python via Bash, always use `uv run --env-file .env python -c "..."` — the env
var is not inherited by sub-processes unless you pass the env file explicitly.
