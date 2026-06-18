import asyncio
import json
import os

import chainlit as cl
from openai import AsyncOpenAI

from skills.get_event_detail import get_event_detail
from skills.hazard_codes import hazard_codes
from skills.list_sources import list_sources
from skills.search_events import search_events
from skills.search_impacts import search_impacts

MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-pro")

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY") or "not-set",
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_PROMPT = """You are a humanitarian data assistant helping users explore the IFRC Global \
Crisis Data Bank — a unified repository of disaster events, hazards, and impacts from ~11 \
authoritative sources.

You have tools to search events, look up impacts, drill into specific events, map hazard names \
to codes, and list available sources. Use them proactively to answer questions.

## Query strategy

ALWAYS query ALL sources for every search — never restrict to a single source unless the \
user explicitly asks by name. NEVER pass sources= unless the user names one. Different \
sources have different coverage gaps and ingestion lags; a storm, flood, or earthquake \
that is absent from one source may be fully documented in another. Omitting sources \
silently understates impact and can cause you to miss events entirely.

Always call hazard_codes() first when the user mentions a hazard type (flood, earthquake, \
cyclone, etc.) before calling search_events or search_impacts.

After every search, report:
- Which sources were queried
- Which sources returned results
- The total server-side count (total_matched)

If total_matched exceeds the number of items returned, say so PROMINENTLY AT THE TOP of your \
response before listing any results — e.g. "Note: 238 events matched but only 50 were \
retrieved; this list may be incomplete." Never bury this in a footnote.

For ranking questions or requests for precise measurements (strongest, deadliest, largest, \
fastest, etc.), call get_event_detail on the top candidates to retrieve structured hazard \
severity fields — do not rely solely on freetext descriptions.

Sources are complementary, not interchangeable — each has unique coverage and lags:
- emdat — deaths, affected, economic loss (historical; comprehensive but slow to update)
- idmc-gidd / idmc-idu — displacement counts (often higher than emdat; separate methodology)
- ifrcevent — IFRC Emergency Appeal scale and response
- glide — cross-source linkage, useful for finding all records of the same event
- gdacs / pdc — near-real-time alerts; first to have recent/ongoing events
- desinventar — local/sub-national detail for Latin America, South Asia
- ibtracs — tropical cyclone best-track archive (may lag current season by months; \
  always pair with gdacs/pdc for recent storms)
- usgs — earthquakes

## Data model

- EM-DAT cost values are in thousands of USD — always multiply by 1,000 when presenting \
(e.g. a value of 500 = $500,000)
- Impact rows are typed (death, displaced_total, etc.) — multiple rows per event is normal; \
group them by type when summarising
- monty:corr_id links the same real-world event across sources — use it with get_event_detail \
to fetch full hazard and impact records

## Limitations

- Absence of results does not mean the event didn't happen — data completeness varies by source
- The same event may appear once per source (cross-source deduplication is in progress)
- For IDMC displacement queries, omit hazard_code — IDMC tags records with a generic code \
that won't match specific hazards, silently excluding them
- Always tell the user which source(s) and hazard code you used

## Response guidelines

- If results are empty or sparse, say so explicitly — do not speculate about real-world events
- Group impact rows by type (deaths, displaced, cost) as a summary per event
- Offer next steps after showing results (filter by country, drill into an event, try another \
source)
- Keep language clear for non-technical humanitarian users; explain source names and codes \
when you use them"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hazard_codes",
            "description": (
                "Map a plain-language hazard term to UNDRR-ISC hazard codes. "
                "Always call this first when the user mentions a hazard type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Plain-language hazard term, e.g. 'flood', 'earthquake', 'cyclone'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sources",
            "description": "List all available data sources and which collection types (events, hazards, impacts) each provides.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_events",
            "description": (
                "Search for disaster events across ALL sources by country, hazard type, and/or date range. "
                "NEVER pass sources= unless the user explicitly names one — different sources have "
                "different coverage gaps and ingestion lags, so restricting sources can silently miss events. "
                "For annual or multi-month queries, pass limit=500 to avoid missing events in the middle of the date range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "country_code": {
                        "type": "string",
                        "description": "ISO 3166-1 alpha-3 country code, e.g. 'BGD' for Bangladesh",
                    },
                    "hazard_code": {
                        "type": "string",
                        "description": "UNDRR-ISC hazard code from hazard_codes(), e.g. 'MH0600' for flood",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_impacts",
            "description": (
                "Search for disaster impacts (deaths, displacement, cost) across ALL sources. "
                "NEVER pass sources= unless the user explicitly names one — different sources report "
                "different impact types and figures for the same event; combining them gives a fuller picture. "
                "Use min_deaths or min_displaced to filter by severity. "
                "Omit hazard_code when querying IDMC displacement data. "
                "EM-DAT cost values are in thousands of USD."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "country_code": {
                        "type": "string",
                        "description": "ISO 3166-1 alpha-3 country code",
                    },
                    "hazard_code": {
                        "type": "string",
                        "description": "UNDRR-ISC hazard code. Omit for IDMC displacement queries.",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD",
                    },
                    "min_deaths": {
                        "type": "number",
                        "description": "Minimum reported deaths. Use either this or min_displaced, not both.",
                    },
                    "min_displaced": {
                        "type": "number",
                        "description": "Minimum displaced persons. Use either this or min_deaths, not both.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_detail",
            "description": "Get the full record for a specific event — metadata, hazards, and impacts — using a corr_id from search_events results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corr_id": {
                        "type": "string",
                        "description": "The monty:corr_id from a search_events result",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Optional collection name (e.g. 'gdacs-events') to speed up lookup",
                    },
                },
                "required": ["corr_id"],
            },
        },
    },
]

SKILL_MAP = {
    "hazard_codes": hazard_codes,
    "list_sources": list_sources,
    "search_events": search_events,
    "search_impacts": search_impacts,
    "get_event_detail": get_event_detail,
}


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("messages", [{"role": "system", "content": SYSTEM_PROMPT}])


@cl.on_message
async def on_message(message: cl.Message):
    messages = cl.user_session.get("messages")
    messages.append({"role": "user", "content": message.content})

    while True:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        assistant = response.choices[0].message

        assistant_dict = {"role": "assistant", "content": assistant.content}
        if assistant.tool_calls:
            assistant_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant.tool_calls
            ]
        messages.append(assistant_dict)

        if not assistant.tool_calls:
            break

        for tc in assistant.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            async with cl.Step(name=fn_name, type="tool") as step:
                step.input = fn_args
                try:
                    result = await asyncio.to_thread(SKILL_MAP[fn_name], **fn_args)
                except Exception as e:
                    result = {"error": str(e)}
                step.output = result

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )

    cl.user_session.set("messages", messages)
    await cl.Message(content=assistant.content or "").send()
