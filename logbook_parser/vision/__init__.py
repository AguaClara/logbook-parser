"""Vision backends: photo -> raw JSON. Provider-agnostic orchestration."""

from typing import Dict

from .base import EncodedImage, ExtractionError, VisionProvider
from .openai_compat import OpenAICompatibleProvider, extract_json
from .prompts import build_prompt
from . import openrouter, local

__all__ = [
    "EncodedImage",
    "ExtractionError",
    "VisionProvider",
    "OpenAICompatibleProvider",
    "extract_photo",
    "get_provider",
]


def get_provider(settings) -> VisionProvider:
    if settings.provider == "openrouter":
        return openrouter.make_provider(settings)
    if settings.provider == "local":
        return local.make_provider(settings)
    raise ValueError(f"Unknown provider '{settings.provider}'. Use 'openrouter' or 'local'.")


def extract_photo(path: str, plant, provider: VisionProvider, model: str) -> Dict:
    """Extract one photo into raw JSON via the given provider."""
    prompt = build_prompt(plant)
    return extract_json(provider, EncodedImage(path=path), prompt, model)
