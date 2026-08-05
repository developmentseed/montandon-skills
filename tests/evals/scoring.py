"""Shared, non-raising tool-call scoring -- used by both the pytest suite (which wraps
these in `assert`) and the cross-model matrix runner (which just wants a pass/fail + why).
"""


def tool_call_failures(tool_calls: list[dict], checks: list[dict]) -> list[str]:
    """Return a list of human-readable failure reasons; empty list means all checks passed."""
    failures = []
    for check in checks:
        name = check["name"]
        matches = [c for c in tool_calls if c["name"] == name]

        if "count" in check and len(matches) != check["count"]:
            failures.append(
                f"{name}: expected exactly {check['count']} call(s), got {len(matches)}: {matches}"
            )
        if "count_at_least" in check and len(matches) < check["count_at_least"]:
            failures.append(
                f"{name}: expected at least {check['count_at_least']} call(s), got {len(matches)}"
            )
        if "args_present" in check and not any(
            all(c["arguments"].get(k) == v for k, v in check["args_present"].items())
            for c in matches
        ):
            failures.append(
                f"{name}: no call had args {check['args_present']} (actual calls: {matches})"
            )
        if "args_present_keys" in check and not any(
            all(k in c["arguments"] for k in check["args_present_keys"]) for c in matches
        ):
            failures.append(
                f"{name}: no call had keys {check['args_present_keys']} (actual calls: {matches})"
            )
        if "args_absent" in check:
            for c in matches:
                for k in check["args_absent"]:
                    if k in c["arguments"]:
                        failures.append(f"{name}: arg '{k}' should be absent, got {c['arguments']}")
        if "args_falsy" in check:
            # Key must be either absent or present-but-falsy (e.g. "", None, 0) -- the skill
            # functions gate with `if arg:`, so a falsy value is functionally identical to
            # omitting the key; don't fail on the literal JSON shape.
            for c in matches:
                for k in check["args_falsy"]:
                    if c["arguments"].get(k):
                        failures.append(
                            f"{name}: arg '{k}' should be absent or falsy, got {c['arguments']}"
                        )
        if "limit_at_least" in check and not any(
            c["arguments"].get("limit", 0) >= check["limit_at_least"] for c in matches
        ):
            failures.append(
                f"{name}: no call had limit >= {check['limit_at_least']} (actual calls: {matches})"
            )
    return failures
