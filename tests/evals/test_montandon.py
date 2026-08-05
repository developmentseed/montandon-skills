import asyncio
from importlib import import_module
from pathlib import Path

import pytest

from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase

from metrics import make_content_metric
from scoring import tool_call_failures

app = import_module("app")

dataset = EvaluationDataset()
dataset.add_goldens_from_json_file(file_path=str(Path(__file__).parent / ".dataset.json"))

# Cases sharing hazard_codes()'s resolved code across turns need real, unsimulated
# turn text (e.g. asserting the SECOND turn reuses turn one's hazard_code) -- these
# are kept out of the single-turn parametrization and driven manually below.
SINGLE_TURN_GOLDENS = [g for g in dataset.goldens if "turns" not in (g.additional_metadata or {})]
MULTI_TURN_GOLDENS = [g for g in dataset.goldens if "turns" in (g.additional_metadata or {})]


def _check_tool_calls(tool_calls: list[dict], checks: list[dict]):
    failures = tool_call_failures(tool_calls, checks)
    assert not failures, "\n".join(failures)


def _run(messages: list[dict]) -> dict:
    return asyncio.run(app.run_agent(messages))


@pytest.mark.parametrize("golden", SINGLE_TURN_GOLDENS, ids=[g.name for g in SINGLE_TURN_GOLDENS])
def test_single_turn(golden: Golden):
    meta = golden.additional_metadata or {}
    messages = [
        {"role": "system", "content": app.SYSTEM_PROMPT},
        {"role": "user", "content": golden.input},
    ]
    result = _run(messages)

    _check_tool_calls(result["tool_calls"], meta.get("tool_checks", []))

    content_checks = meta.get("content_checks")
    if content_checks:
        test_case = LLMTestCase(input=golden.input, actual_output=result["content"])
        assert_test(test_case=test_case, metrics=[make_content_metric(content_checks)])


@pytest.mark.parametrize("golden", MULTI_TURN_GOLDENS, ids=[g.name for g in MULTI_TURN_GOLDENS])
def test_multi_turn_fixed(golden: Golden):
    meta = golden.additional_metadata
    turns = meta["turns"]
    turn_checks = meta["turn_tool_checks"]

    messages = [{"role": "system", "content": app.SYSTEM_PROMPT}]
    for turn_prompt, checks in zip(turns, turn_checks):
        messages.append({"role": "user", "content": turn_prompt})
        result = _run(messages)
        _check_tool_calls(result["tool_calls"], checks)
        messages = result["messages"]
