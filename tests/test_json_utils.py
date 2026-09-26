"""Unit tests for logbook_parser.json_utils.parse_json."""

import json

import pytest

from logbook_parser.json_utils import parse_json


def test_plain_object():
    assert parse_json('{"rows": [], "page_note": "ok"}') == {"rows": [], "page_note": "ok"}


def test_trailing_think_trace():
    open_tag = "<" + "think" + ">"
    close_tag = "<" + "/" + "think" + ">"
    assert parse_json(open_tag + "reasoning here\n" + close_tag + '{"a": 1}') == {"a": 1}


def test_multiple_think_traces_uses_last():
    open_tag = "<" + "think" + ">"
    close_tag = "<" + "/" + "think" + ">"
    text = open_tag + "one" + close_tag + "junk" + open_tag + "two" + close_tag + '{"a": 1}'
    assert parse_json(text) == {"a": 1}


def test_fenced_json():
    assert parse_json('```json\n{"rows": [1, 2]}\n```') == {"rows": [1, 2]}


def test_fenced_without_language():
    assert parse_json('```\n{"b": 2}\n```') == {"b": 2}


def test_fence_uppercase_json():
    assert parse_json('```JSON\n{"c": 3}\n```') == {"c": 3}


def test_surrounding_prose():
    assert parse_json('sure! here you go {"d": 4} hope that helps') == {"d": 4}


def test_nested_braces():
    assert parse_json('prefix {"a": {"b": {"c": 1}}} suffix') == {"a": {"b": {"c": 1}}}


@pytest.mark.parametrize("text", ["", "   ", None, "no json at all", "```\n```"])
def test_malformed_raises(text):
    with pytest.raises(json.JSONDecodeError):
        parse_json(text)


def test_top_level_array_parses():
    # a bare array is valid JSON and is returned as-is
    assert parse_json("[1, 2, 3]") == [1, 2, 3]
