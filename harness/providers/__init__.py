from .base import AgentProvider, ProviderResponse, ToolCall
from .anthropic import AnthropicProvider
from .openai_provider import OpenAIProvider
from .openrouter import OpenRouterProvider
from .gemini import GeminiProvider
from .deepseek import DeepSeekProvider

PROVIDER_MAP = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
}


def create_provider(
    provider_name: str,
    model: str,
    api_key: str,
    base_url: str | None = None,
    is_bedrock_anthropic: bool = False,
    custom_headers: dict[str, str] | None = None,
) -> AgentProvider:
    cls = PROVIDER_MAP.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown provider {provider_name!r}. "
            f"Choose from: {', '.join(PROVIDER_MAP)}"
        )
    # Pass additional config to OpenAI provider
    if provider_name == "openai":
        kwargs = {"api_key": api_key, "model": model}
        if base_url:
            kwargs["base_url"] = base_url
        if is_bedrock_anthropic:
            kwargs["is_bedrock_anthropic"] = is_bedrock_anthropic
        if custom_headers:
            kwargs["custom_headers"] = custom_headers
        return cls(**kwargs)
    return cls(api_key=api_key, model=model)
