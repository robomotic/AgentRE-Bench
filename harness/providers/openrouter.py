from __future__ import annotations

from .openai_provider import OpenAIProvider


DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key=api_key, model=model, base_url=DEFAULT_BASE_URL)

    def _request_headers(self) -> dict[str, str]:
        headers = super()._request_headers()
        headers["HTTP-Referer"] = "https://github.com/AgentRE-Bench"
        headers["X-Title"] = "AgentRE-Bench"
        return headers
