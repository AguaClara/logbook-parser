"""Tests for provider orchestration and JSON-failure diagnostics."""

import json

import pytest

from logbook_parser.vision import extract_photo


class StubProvider:
    name = "stub"

    def __init__(self, text):
        self.text = text

    def complete(self, image, prompt, model):
        return self.text


MALFORMED = '{"rows": [{"operator": "Victor" "record_time": "7pm"}]}'


def test_raw_output_saved_on_parse_failure(tmp_path):
    provider = StubProvider(MALFORMED)
    with pytest.raises(json.JSONDecodeError):
        extract_photo("page1.jpg", provider, "prompt", "model", debug_dir=str(tmp_path))
    saved = tmp_path / "page1.jpg.raw.txt"
    assert saved.read_text(encoding="utf-8") == MALFORMED


def test_debug_dir_is_created_if_missing(tmp_path):
    debug_dir = tmp_path / "nested" / "debug"
    with pytest.raises(json.JSONDecodeError):
        extract_photo("page1.jpg", StubProvider(MALFORMED), "prompt", "model",
                      debug_dir=str(debug_dir))
    assert (debug_dir / "page1.jpg.raw.txt").exists()


def test_no_debug_dir_writes_nothing(tmp_path):
    with pytest.raises(json.JSONDecodeError):
        extract_photo("page1.jpg", StubProvider(MALFORMED), "prompt", "model")
    assert list(tmp_path.iterdir()) == []


def test_valid_json_saves_nothing(tmp_path):
    provider = StubProvider('{"rows": [], "_model": "ignored"}')
    data = extract_photo("page1.jpg", provider, "prompt", "my-model", debug_dir=str(tmp_path))
    assert data["_model"] == "stub:my-model"
    assert list(tmp_path.iterdir()) == []
