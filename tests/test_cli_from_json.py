"""End-to-end tests for the --from-json CLI path (data only, no styling)."""

import json
from datetime import date

import pandas as pd
import pytest

from logbook_parser.cli import main
from logbook_parser.plants import SAN_JUAN_PLANES
from logbook_parser.schema import ALL_COLS

PLANT_SHEET = SAN_JUAN_PLANES.name
REVIEW_SHEET = "REVIEW_QUEUE"
SCHEMA_SHEET = "SCHEMA_MAP"


def row(**overrides):
    base = {
        "raw_date": "07/01/26",
        "record_time": "7pm",
        "operator": "Victor",
        "flow_lps": "12",
        "turbidity_raw_ntu": "41.06",
    }
    base.update(overrides)
    return base


def payload(rows, source_image=None, model="test:model"):
    raw = {"_model": model, "rows": rows}
    if source_image is not None:
        raw["_source_image"] = source_image
    return raw


def run_from_json(tmp_path, out, pattern):
    return main(["--plant", "san_juan_planes", "--from-json", pattern, "--out", str(out)])


def test_happy_path(write_json, read_workbook, tmp_path):
    write_json(payload([row(), row(raw_date="08/01/26", record_time="5am")]),
               "extraction.json")
    out = tmp_path / "out.xlsx"
    assert run_from_json(tmp_path, out, str(tmp_path / "*.json")) == 0

    sheets = read_workbook(str(out))
    assert set(sheets) == {PLANT_SHEET, REVIEW_SHEET, SCHEMA_SHEET}
    df = sheets[PLANT_SHEET]
    assert list(df.columns) == ALL_COLS
    assert len(df) == 2
    assert df["source_image"].tolist() == ["extraction.json", "extraction.json"]


def test_source_image_from_json(write_json, read_workbook, tmp_path):
    write_json(payload([row()], source_image="page1.jpg"), "extraction.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "*.json"))
    df = read_workbook(str(out))[PLANT_SHEET]
    assert df.loc[0, "source_image"] == "page1.jpg"


def test_unparseable_numeric_lands_in_review_queue(write_json, read_workbook, tmp_path):
    write_json(payload([row(turbidity_raw_ntu="4l.06")]), "extraction.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "*.json"))

    sheets = read_workbook(str(out))
    assert len(sheets[REVIEW_SHEET]) == 1
    reviewed = sheets[REVIEW_SHEET].iloc[0]
    assert bool(reviewed["needs_review"]) is True
    assert "turbidity_raw_ntu(unparsed)" in reviewed["review_notes"]
    assert sheets[PLANT_SHEET].iloc[0]["turbidity_raw_ntu"] == "4l.06"


def test_schema_map(write_json, read_workbook, tmp_path):
    write_json(payload([row()]), "extraction.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "*.json"))
    schema = read_workbook(str(out))[SCHEMA_SHEET]
    assert len(schema) == len(SAN_JUAN_PLANES.columns)
    assert set(schema["canonical_field"]) == {k for _, k in SAN_JUAN_PLANES.columns}


def test_append_across_runs(write_json, read_workbook, tmp_path):
    write_json(payload([row()], source_image="a.jpg"), "a.json")
    write_json(payload([row()], source_image="b.jpg"), "b.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    run_from_json(tmp_path, out, str(tmp_path / "b.json"))
    df = read_workbook(str(out))[PLANT_SHEET]
    assert set(df["source_image"]) == {"a.jpg", "b.jpg"}


def test_skip_already_done_without_reprocess(write_json, read_workbook, tmp_path):
    write_json(payload([row()], source_image="a.jpg"), "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    assert len(read_workbook(str(out))[PLANT_SHEET]) == 1


def test_reprocess_replaces_rows(write_json, read_workbook, tmp_path):
    write_json(payload([row(flow_lps="12")], source_image="a.jpg"), "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    write_json(payload([row(flow_lps="42")], source_image="a.jpg"), "a.json")
    main(["--plant", "san_juan_planes", "--from-json", str(tmp_path / "a.json"),
          "--out", str(out), "--reprocess"])
    df = read_workbook(str(out))[PLANT_SHEET]
    assert len(df) == 1
    assert df.iloc[0]["flow_lps"] == 42.0


def test_dedup_keeps_last_within_run(write_json, read_workbook, tmp_path):
    write_json(payload([row(flow_lps="12"), row(flow_lps="99")], source_image="a.jpg"),
               "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    df = read_workbook(str(out))[PLANT_SHEET]
    assert len(df) == 1
    assert df.iloc[0]["flow_lps"] == 99.0


def test_sorted_by_date_and_time(write_json, read_workbook, tmp_path):
    write_json(payload([
        row(raw_date="08/01/26", record_time="7pm"),
        row(raw_date="07/01/26", record_time="5am"),
    ]), "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    df = read_workbook(str(out))[PLANT_SHEET]
    assert [pd.Timestamp(d).date() for d in df["record_date"]] == [date(2026, 1, 7), date(2026, 1, 8)]
    assert df["record_time_24h"].tolist() == ["05:00", "19:00"]


def test_multiple_globs(write_json, read_workbook, tmp_path):
    write_json(payload([row()], source_image="a.jpg"), "a.json")
    write_json(payload([row()], source_image="b.jpg"), "b.json")
    out = tmp_path / "out.xlsx"
    main(["--plant", "san_juan_planes",
          "--from-json", str(tmp_path / "a*.json"), str(tmp_path / "b*.json"),
          "--out", str(out)])
    df = read_workbook(str(out))[PLANT_SHEET]
    assert set(df["source_image"]) == {"a.jpg", "b.jpg"}


def test_date_carry_down_end_to_end(write_json, read_workbook, tmp_path):
    write_json(payload([row(), row(raw_date=None, record_time="5am")]), "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    df = read_workbook(str(out))[PLANT_SHEET]
    assert {pd.Timestamp(d).date() for d in df["record_date"]} == {date(2026, 1, 7)}


def test_empty_rows_writes_workbook(write_json, read_workbook, tmp_path):
    write_json(payload([]), "a.json")
    out = tmp_path / "out.xlsx"
    run_from_json(tmp_path, out, str(tmp_path / "a.json"))
    sheets = read_workbook(str(out))
    assert set(sheets) == {PLANT_SHEET, REVIEW_SHEET, SCHEMA_SHEET}
    assert len(sheets[PLANT_SHEET]) == 0


def test_malformed_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    out = tmp_path / "out.xlsx"
    with pytest.raises(json.JSONDecodeError):
        run_from_json(tmp_path, out, str(bad))
