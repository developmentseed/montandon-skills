from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from openrouter_model import OpenRouterModel

# Shared judge model for every LLM-as-judge metric in this suite. Routed through
# OpenRouter so it reuses the OPENROUTER_API_KEY already used by app.py itself.
JUDGE_MODEL = OpenRouterModel()


def make_content_metric(content_checks: list[str]) -> GEval:
    """Build a per-case GEval metric from a case's `content_checks` list.

    Each case in tests/evals/.dataset.json carries its own natural-language content
    checks (grounded in app.py's SYSTEM_PROMPT and CLAUDE.md response guidelines), so
    the metric criteria are assembled per-golden rather than shared across the suite.
    """
    criteria = (
        "Evaluate the assistant's final response against ALL of the following "
        "requirements. The response fails if it violates any one of them:\n"
        + "\n".join(f"- {check}" for check in content_checks)
    )
    return GEval(
        name="Content Correctness",
        criteria=criteria,
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model=JUDGE_MODEL,
        threshold=0.5,
    )
