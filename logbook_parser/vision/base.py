"""Vision-backend abstraction shared by all providers."""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class EncodedImage:
    """A photo to extract. `data_url` is filled lazily when a remote provider
    needs it; local providers may consume `path`/bytes directly."""

    path: str
    data_url: Optional[str] = None


class VisionProvider(Protocol):
    name: str

    def complete(self, image: EncodedImage, prompt: str, model: str) -> str:
        """Return the raw text completion for a single photo."""
        ...


class ExtractionError(RuntimeError):
    """Base class for provider failures."""
