"""Tolerant JSON parsing for raw model output."""

import json
from typing import Dict


def parse_json(text: str) -> Dict:
    """Parse model output, dropping reasoning traces / markdown fences."""
    text = (text or "").strip()
    # some reasoning models prepend a  thinking... response trace — drop it
    if " response" in text:
        text = text.split(" response")[-1].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            return json.loads(text[s:e + 1])
        raise
