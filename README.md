# Montandon Assistant

Skills & tools for natural language querying of the [IFRC Global Crisis Data Bank](https://montandondata.org/) via Claude Code.

Ask questions like:

- _"What major floods happened in Bangladesh between 2020 and 2023?"_
- _"Which earthquakes caused more than 500 deaths in 2023?"_
- _"Tell me about the GDACS cyclone events in the Philippines last year."_

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Set your token (get one from the Montandon team)
export MONTANDON_TOKEN=<your-token>

# 3. Start Claude Code
uv run claude
```

Or with a `.env` file:

```bash
echo "MONTANDON_TOKEN=<your-token>" > .env
uv run --env-file .env claude
```

## How it works

Claude (or, theoretically, another terminal-based agent) reads `CLAUDE.md` on startup, which points to `SKILLS.md` (the skill manifest) and
`SKILL.md` (the data guide). Each skill is an independent Python file in `skills/`; shared
HTTP/utility code lives in `montandon_core.py`.

## Tools

| Function                                                                      | What it does                                        |
| ----------------------------------------------------------------------------- | --------------------------------------------------- |
| `search_events(country_code, country_codes, hazard_code, date_from, date_to)` | Find disaster events by location, hazard type, date |
| `get_event_detail(corr_id)`                                                   | Get full record: event + hazards + impact estimates |
| `search_impacts(min_deaths, min_displaced, ...)`                              | Find events by impact threshold                     |
| `list_sources()`                                                              | Show available data sources and collection types    |
| `hazard_codes(query)`                                                         | Map plain language ("flood") to hazard codes.       |

## Further Information

More: [montandondata.org](https://montandondata.org) · [GitHub repos](https://montandondata.org/resources.html)
