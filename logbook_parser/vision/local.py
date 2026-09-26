"""Local inference provider preset.

Targets any server exposing the OpenAI chat-completions API with vision support
(llama.cpp's server, vLLM, or Ollama's OpenAI-compatible endpoint). Point it at
the server with `--base-url`. No OpenRouter API key is required.
"""

from .openai_compat import OpenAICompatibleProvider


def make_provider(settings) -> OpenAICompatibleProvider:
    if not settings.base_url:
        raise RuntimeError(
            "Local inference requires --base-url (e.g. http://localhost:11434/v1)."
        )
    return OpenAICompatibleProvider(
        name="local",
        base_url=settings.base_url,
        api_key=settings.api_key,
        extra_body=None,
        max_retries=settings.max_retries,
    )
