import os

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from deepeval.models import DeepEvalBaseLLM

DEFAULT_JUDGE_MODEL = "openai/gpt-4o-mini"


class OpenRouterModel(DeepEvalBaseLLM):
    """DeepEval judge model routed through OpenRouter (OpenAI-compatible API).

    Reuses OPENROUTER_API_KEY, the same credential app.py uses for the agent itself,
    so no separate provider account is needed for LLM-as-judge metrics.
    """

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        self.model_name = model or os.getenv("OPENROUTER_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        base_url = base_url or "https://openrouter.ai/api/v1"
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        super().__init__(self.model_name)

    def load_model(self):
        return self._client

    def generate(self, prompt: str, schema: BaseModel | None = None):
        if schema is not None:
            completion = self._client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=schema,
            )
            return completion.choices[0].message.parsed
        completion = self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content

    async def a_generate(self, prompt: str, schema: BaseModel | None = None):
        if schema is not None:
            completion = await self._async_client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=schema,
            )
            return completion.choices[0].message.parsed
        completion = await self._async_client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content

    def get_model_name(self):
        return f"openrouter:{self.model_name}"
