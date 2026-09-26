"""Generic provider for any OpenAI-compatible chat-completions endpoint."""

import time
from typing import Optional

from .base import EncodedImage, ExtractionError
from .images import image_data_url
from ..json_utils import parse_json

# transient conditions worth retrying with backoff (rate limits / provider hiccups)
RETRYABLE = ("429", "rate", "timeout", "timed out", "502", "503", "overloaded", "temporarily")


class OpenAICompatibleProvider:
    """Speaks the OpenAI chat-completions API. OpenRouter and local servers
    (llama.cpp, vLLM, Ollama's OpenAI endpoint) are just different presets."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None,
                 extra_body: Optional[dict] = None, max_retries: int = 5):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.extra_body = extra_body
        self.max_retries = max_retries
        self._client = None

    def _client_instance(self):
        if self._client is None:
            from openai import OpenAI  # lazy: dry-run path needs no openai installed
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key or "not-needed")
        return self._client

    def complete(self, image: EncodedImage, prompt: str, model: str) -> str:
        data_url = image.data_url or image_data_url(image.path)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }]
        kwargs = {"model": model, "messages": messages, "temperature": 0}
        if self.extra_body is not None:
            kwargs["extra_body"] = self.extra_body

        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self._client_instance().chat.completions.create(**kwargs)
                return resp.choices[0].message.content
            except Exception as e:  # noqa: BLE001 — we classify below
                last_err = e
                if any(tok in str(e).lower() for tok in RETRYABLE) and attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 30))  # 1,2,4,8,16,30s...
                    continue
                raise
        raise ExtractionError(f"failed after {self.max_retries} retries: {last_err}")


def extract_json(provider, image: EncodedImage, prompt: str, model: str) -> dict:
    """Run a provider and parse its output, tagging the model that produced it."""
    data = parse_json(provider.complete(image, prompt, model))
    data["_model"] = f"{provider.name}:{model}"
    return data
