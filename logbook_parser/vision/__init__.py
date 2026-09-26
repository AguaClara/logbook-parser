"""Vision backends: photo -> raw JSON. Provider-agnostic orchestration."""

from typing import Dict, Optional

from .base import EncodedImage, ExtractionError, VisionProvider
from .openai_compat import OpenAICompatibleProvider, extract_json
from .prompts import build_prompt
from . import openrouter, local

__all__ = [
    "EncodedImage",
    "ExtractionError",
    "VisionProvider",
    "OpenAICompatibleProvider",
    "build_prompt",
    "extract_photo",
    "get_provider",
]


def get_provider(settings) -> VisionProvider:
    if settings.provider == "openrouter":
        return openrouter.make_provider(settings)
    if settings.provider == "local":
        return local.make_provider(settings)
    raise ValueError(f"Unknown provider '{settings.provider}'. Use 'openrouter' or 'local'.")


def extract_photo(path: str, provider: VisionProvider, prompt: str, model: str,
                  debug_dir: Optional[str] = None) -> Dict:
    """Extract one photo into raw JSON via the given provider.

    The prompt is built once by the caller and reused across photos. If
    `debug_dir` is set, unparseable model output is saved there for inspection.
    """
    return extract_json(provider, EncodedImage(path=path), prompt, model, debug_dir)
