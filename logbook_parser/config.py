"""Runtime settings. Environment is read here, not at import time."""

import os
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_OPENROUTER_MODEL = "google/gemma-4-31b-it:free"


def default_model() -> str:
    return os.environ.get("OPENROUTER_VISION_MODEL", DEFAULT_OPENROUTER_MODEL)


@dataclass(frozen=True)
class Settings:
    plant: str
    out: str = "plant.xlsx"
    provider: str = "openrouter"
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_retries: int = 5
    reprocess: bool = False
    photos: Optional[str] = None
    from_json: Optional[list] = field(default=None)
