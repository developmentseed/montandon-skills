import asyncio
from importlib import import_module
from pathlib import Path

import pytest

from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase

from metrics import make_content_metric

app = import_module("app")

dataset = EvaluationDataset()
dataset.add_goldens_from_json_file(file_path=str(Path(__file__).parent / ".dataset.json"))

# Cases sharing hazard_codes()'s resolved code across turns need real, unsimulated
# turn text (e.g. asserting the SECOND turn reuses turn one's hazard_code) -- these
# are kept out of the single-turn parametrization and driven manually below.
SINGLE_TURN_GOLDENS = [g for g in dataset.goldens if "turns" not in (g.additional_metadata or {})]
MULTI_TURN_GOLDENS = [g for g in dataset.goldens if "turns" in (g.additional_metadata or {})]


def _check_tool_calls(tool_calls: list[dict], checks: list[dict]):
    """Deterministic, non-LLM assertions on the model's actual tool_calls."""
    for check in checks:
        name = check["name"]
        matches = [c for c in tool_calls if c["name"] == name]

        if "count" in check:
            assert len(matches) == check["count"], (
                f"{name}: expected exactly {check['count']} call(s), got {len(matches)}: {matches}"
            )
        if "count_at_least" in check:
            assert len(matches) >= check["count_at_least"], (
                f"{name}: expected at least {check['count_at_least']} call(s), got {len(matches)}"
            )
        if "args_present" in check:
            assert any(
                all(c["arguments"].get(k) == v for k, v in check["args_present"].items())
                for c in matches
            ), f"{name}: no call had args {check['args_present']} (actual calls: {matches})"
        if "args_present_keys" in check:
            assert any(
                all(k in c["arguments"] for k in check["args_present_keys"])
                for c in matches
            ), f"{name}: no call had keys {check['args_present_keys']} (actual calls: {matches})"
        if "args_absent" in check:
            for c in matches:
                for k in check["args_absent"]:
                    assert k not in c["arguments"], (
                        f"{name}: arg '{k}' should be absent, got {c['arguments']}"
                    )
        if "args_falsy" in check:
            # Key must be either absent or present-but-falsy (e.g. "", None, 0) -- for args
            # the skill functions gate with `if arg:`, a falsy value is functionally identical
            # to omitting the key, so don't fail on the literal JSON shape.
            for c in matches:
                for k in check["args_falsy"]:
                    assert not c["arguments"].get(k), (
                        f"{name}: arg '{k}' should be absent or falsy, got {c['arguments']}"
                    )
        if "limit_at_least" in check:
            assert any(
                c["arguments"].get("limit", 0) >= check["limit_at_least"] for c in matches
            ), f"{name}: no call had limit >= {check['limit_at_least']} (actual calls: {matches})"


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
