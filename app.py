import asyncio
import json
import os
import time

import chainlit as cl
from deepeval.tracing import observe, update_current_span
from openai import AsyncOpenAI

from skills.get_event_detail import get_event_detail
from skills.hazard_codes import hazard_codes
from skills.list_sources import list_sources
from skills.search_events import search_events
from skills.search_impacts import search_impacts

MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.6-luna-pro")

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

When the user DOES name a source explicitly (e.g. "using only EM-DAT", "just GDACS \
alerts"), you MUST pass sources= with that source's key from the list below (e.g. \
sources=["emdat"]) — restricting is correct here, and skipping the sources= argument \
in this case silently ignores the user's instruction and queries everything instead.

Call hazard_codes() the first time the user mentions a hazard type, before calling \
search_events or search_impacts — it returns the full upstream code table (hundreds of \
entries), so only call it once per conversation and reuse the undrr_code you already \
resolved for hazard types you've already looked up (e.g. once you know "flood" is \
MH0600, don't call hazard_codes() again just because the user mentions flooding again \
later).

Some plain-language hazard terms are ambiguous — e.g. "storm" could mean lightning, \
thunderstorm, dust/sandstorm, snow storm, storm surge, or storm tides, none of which is \
the same as tropical cyclone. When a term maps to multiple plausible hazard codes, ASK \
the user which one they mean before calling search_events or search_impacts — do not \
silently guess one code, and do not call search multiple times to cover every guess.

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

For questions asking which sources have data on a specific event (or to confirm cross-source \
coverage), call get_event_detail on the matching corr_id(s) from search_events rather than \
inferring source coverage from search_events results alone — search_events results only show \
each source's own record, while get_event_detail's hazards/impacts arrays reveal which other \
sources actually have linked data.

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
- monty:corr_id is deterministic per source, NOT a cross-source join key — two sources describing \
the same real-world event can produce different corr_ids (country resolution, hazard \
normalization, block_id, or episode number can differ). get_event_detail queries hazards/impacts \
across all source collections by exact corr_id match, so don't assume one call surfaced every \
source's data on an event

## Limitations

- Absence of results does not mean the event didn't happen — data completeness varies by source
- The same event may appear once per source (cross-source deduplication is in progress)
- For IDMC displacement queries, omit the hazard_code argument entirely — do not pass it as an \
empty string or null, leave the key out of the tool call — IDMC tags records with a generic \
code that won't match specific hazards, silently excluding them
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
                "Return the full table of UNDRR-ISC hazard codes Montandon uses (no arguments). "
                "Read the returned `name` fields yourself and match them to whatever hazard term "
                "the user mentioned — always call this first when the user mentions a hazard type."
            ),
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
                "If the user DOES name a source explicitly, you MUST pass sources= with that source's key "
                "(e.g. sources=['emdat']) — leaving it out ignores their instruction. "
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
                        "description": "UNDRR-ISC hazard code copied from hazard_codes()'s result, e.g. 'MH0600' for flood",
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
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Restrict to specific source keys, e.g. ['emdat']. Only pass this when "
                            "the user explicitly names a source — otherwise omit it to query all sources."
                        ),
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
                        "description": (
                            "UNDRR-ISC hazard code. For IDMC displacement queries, do not include "
                            "this key at all — not even as an empty string."
                        ),
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
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Restrict to specific source keys, e.g. ['emdat']. Only pass this when "
                            "the user explicitly names a source — otherwise omit it to query all sources."
                        ),
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

@observe(type="tool")
async def call_tool(fn_name: str, fn_args: dict):
    update_current_span(name=fn_name, input=fn_args)
    try:
        result = await asyncio.to_thread(SKILL_MAP[fn_name], **fn_args)
    except Exception as e:
        result = {"error": str(e)}
    update_current_span(output=result)
    return result


@observe(type="agent", name="montandon_agent")
async def run_agent(messages: list[dict], model: str = MODEL, on_tool_call=None) -> dict:
    """Drive the tool-calling loop against `messages` and return the final state.

    Framework-agnostic (no Chainlit dependency) so it can be called from both the
    Chainlit UI and the eval suite. Returns the full message list (including tool
    calls/results) and a flat log of {name, arguments} for deterministic checks.
    `on_tool_call(name, arguments, result)` is awaited after each tool call, if given —
    Chainlit uses it to render a live cl.Step. Also returns `wall_time_s` (whole loop,
    including tool execution) and `usage` (summed OpenRouter cost/tokens across every LLM
    call in the loop) — used by the eval suite to compare models on speed and cost, not
    just correctness.
    """
    tool_call_log = []
    usage = {
        "cost_usd": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
    }
    start = time.perf_counter()

    while True:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            extra_body={"usage": {"include": True}},
        )
        if response.usage is not None:
            usage["cost_usd"] += getattr(response.usage, "cost", 0.0) or 0.0
            usage["prompt_tokens"] += response.usage.prompt_tokens or 0
            usage["completion_tokens"] += response.usage.completion_tokens or 0
            details = getattr(response.usage, "prompt_tokens_details", None)
            if details is not None:
                usage["cached_tokens"] += getattr(details, "cached_tokens", 0) or 0
                usage["cache_write_tokens"] += getattr(details, "cache_write_tokens", 0) or 0
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
            tool_call_log.append({"name": fn_name, "arguments": fn_args})

            result = await call_tool(fn_name, fn_args)
            if on_tool_call is not None:
                await on_tool_call(fn_name, fn_args, result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )

    update_current_span(output=assistant.content)
    return {
        "content": assistant.content or "",
        "messages": messages,
        "tool_calls": tool_call_log,
        "wall_time_s": time.perf_counter() - start,
        "usage": usage,
    }


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    if (username, password) == (os.getenv("CHAINLIT_USER"), os.getenv("CHAINLIT_PASSWORD")):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("messages", [{"role": "system", "content": SYSTEM_PROMPT}])


@cl.on_message
async def on_message(message: cl.Message):
    messages = cl.user_session.get("messages")
    messages.append({"role": "user", "content": message.content})

    async def render_step(fn_name, fn_args, result):
        async with cl.Step(name=fn_name, type="tool") as step:
            step.input = fn_args
            step.output = result

    result = await run_agent(messages, on_tool_call=render_step)

    cl.user_session.set("messages", result["messages"])
    await cl.Message(content=result["content"]).send()
