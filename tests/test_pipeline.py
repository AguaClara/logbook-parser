"""Unit tests for logbook_parser.pipeline helpers."""

import json

import pandas as pd

from logbook_parser.config import Settings
from logbook_parser.pipeline import merge_rows, rows_from_json, rows_from_photos
from logbook_parser.schema import ALL_COLS


def raw_row(**overrides):
    base = {
        "record_date": "07/01/26",
        "record_time": "7pm",
        "operator": "Victor",
        "flow_lps": "12",
    }
    base.update(overrides)
    return base


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_source_image_from_json(plant, tmp_path):
    write(tmp_path, "extraction.json",
          {"_source_image": "page1.jpg", "rows": [raw_row()]})
    rows = rows_from_json(plant, [str(tmp_path / "*.json")])
    assert rows[0]["source_image"] == "page1.jpg"


def test_source_image_falls_back_to_filename(plant, tmp_path):
    write(tmp_path, "extraction.json", {"rows": [raw_row()]})
    rows = rows_from_json(plant, [str(tmp_path / "*.json")])
    assert rows[0]["source_image"] == "extraction.json"


def test_glob_and_file_order(plant, tmp_path):
    write(tmp_path, "b.json", {"_source_image": "b.jpg", "rows": [raw_row()]})
    write(tmp_path, "a.json", {"_source_image": "a.jpg", "rows": [raw_row()]})
    rows = rows_from_json(plant, [str(tmp_path / "*.json")])
    assert [r["source_image"] for r in rows] == ["a.jpg", "b.jpg"]


def test_multiple_globs_aggregate(plant, tmp_path):
    write(tmp_path, "a.json", {"_source_image": "a.jpg", "rows": [raw_row()]})
    write(tmp_path, "b.json", {"_source_image": "b.jpg", "rows": [raw_row()]})
    rows = rows_from_json(plant, [str(tmp_path / "a*.json"), str(tmp_path / "b*.json")])
    assert {r["source_image"] for r in rows} == {"a.jpg", "b.jpg"}


def make_df(rows):
    return pd.DataFrame(rows, columns=ALL_COLS)


class MalformedProvider:
    name = "stub"

    def complete(self, image, prompt, model):
        return '{"rows": [{"operator": "Victor" "record_time": "7pm"}]}'


def test_rows_from_photos_saves_debug_on_parse_failure(plant, tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "a.jpg").write_bytes(b"x")
    debug = tmp_path / "debug"
    settings = Settings(plant="san_juan_planes", model="stub-model", debug_dir=str(debug))

    rows = rows_from_photos(plant, str(photos), set(), settings, MalformedProvider())

    assert rows == []
    assert (debug / "a.jpg.raw.txt").read_text(encoding="utf-8").startswith('{"rows"')


def test_merge_dedup_keeps_last():
    existing = make_df([])
    new = [
        {"source_image": "p.jpg", "record_date_parsed": None, "record_time": "7pm",
         "operator": "Victor", "flow_lps": 12.0},
        {"source_image": "p.jpg", "record_date_parsed": None, "record_time": "7pm",
         "operator": "Victor", "flow_lps": 99.0},
    ]
    out = merge_rows(existing, new, reprocess=False)
    assert len(out) == 1
    assert out.iloc[0]["flow_lps"] == 99.0


def test_merge_retains_disjoint_rows():
    existing = make_df([{"source_image": "old.jpg", "record_date_parsed": None,
                         "record_time": "7pm", "operator": "Victor"}])
    new = [{"source_image": "new.jpg", "record_date_parsed": None,
            "record_time": "7pm", "operator": "Victor"}]
    out = merge_rows(existing, new, reprocess=False)
    assert set(out["source_image"]) == {"old.jpg", "new.jpg"}


def test_merge_reprocess_replaces_source():
    existing = make_df([{"source_image": "p.jpg", "record_date_parsed": None,
                         "record_time": "7pm", "operator": "Victor", "flow_lps": 12.0}])
    new = [{"source_image": "p.jpg", "record_date_parsed": None,
            "record_time": "7pm", "operator": "Victor", "flow_lps": 42.0}]
    out = merge_rows(existing, new, reprocess=True)
    assert len(out) == 1
    assert out.iloc[0]["flow_lps"] == 42.0
