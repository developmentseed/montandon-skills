"""Run the eval suite across multiple models and report score, wall time, and cost
per case per model. Not a pytest file -- run directly:

    uv run --env-file .env python tests/evals/run_matrix.py \\
        --models openai/gpt-5.6-luna-pro,openai/gpt-5.6-terra

Results print as tables and are saved to tests/evals/results/matrix_<timestamp>.json.
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THIS_DIR = Path(__file__).resolve().parent
for p in (REPO_ROOT, THIS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rich.console import Console
from rich.table import Table

from deepeval.test_case import LLMTestCase

from metrics import make_content_metric
from scoring import tool_call_failures

app = import_module("app")

MODELS_FILE = THIS_DIR / "models.txt"
DATASET_PATH = THIS_DIR / ".dataset.json"
RESULTS_DIR = THIS_DIR / "results"


def load_models_file() -> list[str]:
    lines = MODELS_FILE.read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def load_cases() -> list[dict]:
    return json.loads(DATASET_PATH.read_text())


async def run_single_turn(case: dict, model: str, semaphore: asyncio.Semaphore) -> dict:
    meta = case["additional_metadata"]
    async with semaphore:
        messages = [
            {"role": "system", "content": app.SYSTEM_PROMPT},
            {"role": "user", "content": case["input"]},
        ]
        result = await app.run_agent(messages, model=model)

    failures = tool_call_failures(result["tool_calls"], meta.get("tool_checks", []))

    content_score = None
    content_success = None
    content_error = None
    content_checks = meta.get("content_checks")
    if content_checks:
        try:
            test_case = LLMTestCase(input=case["input"], actual_output=result["content"])
            metric = make_content_metric(content_checks)
            content_score = metric.measure(test_case)
            content_success = metric.is_successful()
        except Exception as e:
            content_error = str(e)

    return _row(case["name"], model, not failures, failures, content_score, content_success,
                content_error, result["wall_time_s"], result["usage"])


async def run_multi_turn(case: dict, model: str, semaphore: asyncio.Semaphore) -> dict:
    meta = case["additional_metadata"]
    turns = meta["turns"]
    turn_checks = meta["turn_tool_checks"]

    all_failures = []
    wall_time_s = 0.0
    usage = {
        "cost_usd": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
    }

    async with semaphore:
        messages = [{"role": "system", "content": app.SYSTEM_PROMPT}]
        for turn_prompt, checks in zip(turns, turn_checks):
            messages.append({"role": "user", "content": turn_prompt})
            result = await app.run_agent(messages, model=model)
            all_failures += tool_call_failures(result["tool_calls"], checks)
            wall_time_s += result["wall_time_s"]
            for k in usage:
                usage[k] += result["usage"][k]
            messages = result["messages"]

    return _row(case["name"], model, not all_failures, all_failures, None, None, None,
                wall_time_s, usage)


def _row(name, model, tool_pass, tool_failures, content_score, content_success,
         content_error, wall_time_s, usage) -> dict:
    return {
        "case": name,
        "model": model,
        "tool_pass": tool_pass,
        "tool_failures": tool_failures,
        "content_score": content_score,
        "content_success": content_success,
        "content_error": content_error,
        "overall_pass": tool_pass and (content_success is not False),
        "wall_time_s": round(wall_time_s, 2),
        "cost_usd": round(usage["cost_usd"], 6),
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "cached_tokens": usage["cached_tokens"],
        "cache_write_tokens": usage["cache_write_tokens"],
    }


async def run_all(models: list[str], concurrency: int) -> list[dict]:
    cases = load_cases()
    semaphore = asyncio.Semaphore(concurrency)
    tasks = []
    for model in models:
        for case in cases:
            is_multi_turn = "turns" in case["additional_metadata"]
            coro = run_multi_turn(case, model, semaphore) if is_multi_turn else run_single_turn(case, model, semaphore)
            tasks.append(coro)
    return await asyncio.gather(*tasks)


def print_detail_table(console: Console, rows: list[dict]):
    table = Table(title="Per-case results")
    table.add_column("Model")
    table.add_column("Case")
    table.add_column("Tools")
    table.add_column("Content")
    table.add_column("Wall time")
    table.add_column("Cost")
    table.add_column("Cache hit%")
    for row in sorted(rows, key=lambda r: (r["model"], r["case"])):
        tools_cell = "✓" if row["tool_pass"] else f"✗ {row['tool_failures'][0][:40]}…" if row["tool_failures"] else "✗"
        if row["content_score"] is not None:
            content_cell = f"{row['content_score']:.2f} {'✓' if row['content_success'] else '✗'}"
        elif row["content_error"]:
            content_cell = f"error: {row['content_error'][:30]}"
        else:
            content_cell = "—"
        cached = row.get("cached_tokens", 0)
        prompt = row["prompt_tokens"]
        cache_cell = f"{cached / prompt:.0%}" if prompt else "—"
        table.add_row(
            row["model"], row["case"], tools_cell, content_cell,
            f"{row['wall_time_s']:.1f}s", f"${row['cost_usd']:.4f}", cache_cell,
        )
    console.print(table)


def print_summary_table(console: Console, rows: list[dict]):
    table = Table(title="Per-model summary")
    table.add_column("Model")
    table.add_column("Pass rate")
    table.add_column("Avg content score")
    table.add_column("Total wall time")
    table.add_column("Total cost")
    table.add_column("Cache hit%")

    models = sorted({r["model"] for r in rows})
    for model in models:
        model_rows = [r for r in rows if r["model"] == model]
        pass_rate = sum(r["overall_pass"] for r in model_rows) / len(model_rows)
        content_scores = [r["content_score"] for r in model_rows if r["content_score"] is not None]
        avg_content = sum(content_scores) / len(content_scores) if content_scores else None
        total_wall = sum(r["wall_time_s"] for r in model_rows)
        total_cost = sum(r["cost_usd"] for r in model_rows)
        total_cached = sum(r.get("cached_tokens", 0) for r in model_rows)
        total_prompt = sum(r["prompt_tokens"] for r in model_rows)
        table.add_row(
            model,
            f"{pass_rate:.0%} ({sum(r['overall_pass'] for r in model_rows)}/{len(model_rows)})",
            f"{avg_content:.2f}" if avg_content is not None else "—",
            f"{total_wall:.1f}s",
            f"${total_cost:.4f}",
            f"{total_cached / total_prompt:.0%}" if total_prompt else "—",
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=str, default=None,
                         help=f"Comma-separated OpenRouter model IDs. Defaults to the list in {MODELS_FILE.name}.")
    parser.add_argument("--concurrency", type=int, default=4,
                         help="Max concurrent run_agent calls across the whole matrix")
    args = parser.parse_args()
    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models else load_models_file()
    )

    console = Console()
    console.print(f"Running {len(load_cases())} cases across {len(models)} model(s): {models}")

    started = time.perf_counter()
    rows = asyncio.run(run_all(models, args.concurrency))
    console.print(f"\nDone in {time.perf_counter() - started:.1f}s wall clock (script-level).\n")

    print_detail_table(console, rows)
    console.print()
    print_summary_table(console, rows)

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"matrix_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(rows, indent=2))
    console.print(f"\nSaved raw results to {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
