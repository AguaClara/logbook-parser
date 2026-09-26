"""OpenRouter provider preset."""

import os

from .openai_compat import OpenAICompatibleProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def make_provider(settings) -> OpenAICompatibleProvider:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Get a key at openrouter.ai -> Keys, then:\n"
            '  export OPENROUTER_API_KEY="sk-or-..."'
        )
    return OpenAICompatibleProvider(
        name="openrouter",
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
        # turn off Nemotron's reasoning trace -> cleaner JSON, faster/cheaper
        extra_body={"reasoning": {"enabled": False}},
        max_retries=settings.max_retries,
    )
