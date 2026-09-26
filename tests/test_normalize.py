"""Unit tests for logbook_parser.normalize."""

from datetime import date, datetime

import pytest

from logbook_parser.normalize import coerce, normalize_extraction, parse_date, to_24h
from logbook_parser.schema import ALL_COLS


def row(**overrides):
    base = {
        "record_date": "07/01/26",
        "record_time": "7pm",
        "operator": "Victor",
        "flow_lps": "12",
        "turbidity_raw_ntu": "41.06",
        "turbidity_clarified_ntu": "1.79",
        "turbidity_filtered_ntu": "0.5",
        "coag_slider_pct": "50",
        "coag_dose_pct_mgl": "10",
        "coag_dose_probeta_mgl": "12",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# coerce
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value,dtype,expected",
    [
        (None, "float", None),
        ("", "float", None),
        ("41.06", "float", 41.06),
        ("41,06", "float", 41.06),
        (" 12 ", "float", 12.0),
        (12, "float", 12.0),
        (0, "float", 0.0),
        ("abc", "float", "abc"),
        ("12.9", "int", 12),
        ("abc", "int", "abc"),
        (" Victor ", "str", "Victor"),
        (12, "str", "12"),
        ("1,234", "float", 1.234),
    ],
)
def test_coerce(value, dtype, expected):
    assert coerce(value, dtype) == expected


# --------------------------------------------------------------------------- #
# parse_date
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,fmt,expected",
    [
        (None, "%d/%m/%y", None),
        ("", "%d/%m/%y", None),
        ("07/01/26", "%d/%m/%y", date(2026, 1, 7)),
        ("07/01/2026", "%d/%m/%y", date(2026, 1, 7)),
        ("07-01-26", "%d/%m/%y", date(2026, 1, 7)),
        ("07-01-2026", "%d/%m/%y", date(2026, 1, 7)),
        ("7/1/26", "%d/%m/%y", date(2026, 1, 7)),
        ("31/02/26", "%d/%m/%y", None),
        (" 07/01/26 ", "%d/%m/%y", date(2026, 1, 7)),
        # ISO year-first is intentionally unsupported
        ("2026-01-07", "%d/%m/%y", None),
    ],
)
def test_parse_date(raw, fmt, expected):
    assert parse_date(raw, fmt) == expected


# --------------------------------------------------------------------------- #
# to_24h
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,rule,expected",
    [
        # explicit am/pm
        ("7pm", "daytime", ("19:00", True)),
        ("7PM", "daytime", ("19:00", True)),
        ("7:30pm", "daytime", ("19:30", True)),
        ("12am", "daytime", ("00:00", True)),
        ("12pm", "daytime", ("12:00", True)),
        ("5am", "daytime", ("05:00", True)),
        (" 7 pm ", "daytime", ("19:00", True)),
        ("7.pm", "daytime", ("19:00", True)),
        # bare numbers, daytime rule: 7-11 AM, 12 noon, 1-6 PM
        ("7", "daytime", ("07:00", True)),
        ("12", "daytime", ("12:00", True)),
        ("1", "daytime", ("13:00", True)),
        ("6", "daytime", ("18:00", True)),
        ("0", "daytime", ("00:00", True)),
        ("13", "daytime", ("13:00", True)),
        ("23", "daytime", ("23:00", True)),
        ("5:30", "daytime", ("17:30", True)),
        # alternate bare rules
        ("7", "all_pm", ("19:00", True)),
        ("12", "all_pm", ("12:00", True)),
        ("7", "all_am", ("07:00", True)),
        ("12", "all_am", ("00:00", True)),
        # unrecognized
        ("abc", "daytime", (None, False)),
        ("7pm5", "daytime", (None, False)),
        ("7:5", "daytime", (None, False)),
        # out-of-range clock values now rejected
        ("25:00", "daytime", (None, False)),
        ("7:60", "daytime", (None, False)),
        ("13pm", "daytime", (None, False)),
        ("24:00", "daytime", (None, False)),
        ("0am", "daytime", (None, False)),
        # blank is "nothing to parse", not an error
        ("", "daytime", (None, True)),
        (None, "daytime", (None, True)),
    ],
)
def test_to_24h(raw, rule, expected):
    assert to_24h(raw, rule) == expected


# --------------------------------------------------------------------------- #
# normalize_extraction
# --------------------------------------------------------------------------- #
def test_keys_and_provenance(plant, sample_raw):
    out = normalize_extraction(sample_raw([row()]), plant, "page1.jpg")
    assert len(out) == 1
    r = out[0]
    assert set(r) == set(ALL_COLS)
    assert r["plant"] == plant.name
    assert r["source_image"] == "page1.jpg"
    assert r["model"] == "test:model"
    assert r["needs_review"] is False
    assert r["review_notes"] == ""
    assert datetime.fromisoformat(r["extracted_at"])


def test_field_types(plant, sample_raw):
    r = normalize_extraction(sample_raw([row()]), plant, "p.jpg")[0]
    assert r["record_date"] == "07/01/26"
    assert r["record_date_parsed"] == date(2026, 1, 7)
    assert r["record_time"] == "7pm"
    assert r["record_time_24h"] == "19:00"
    assert isinstance(r["flow_lps"], float)
    assert isinstance(r["turbidity_raw_ntu"], float)
    assert r["operator"] == "Victor"


def test_unpadded_written_date_parses(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_date="27/5/24")]), plant, "p.jpg")[0]
    assert r["record_date"] == "27/5/24"
    assert r["record_date_parsed"] == date(2024, 5, 27)
    assert r["needs_review"] is False


def test_record_date_preserved_when_unparseable(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_date="not-a-date")]), plant, "p.jpg")[0]
    assert r["record_date"] == "not-a-date"
    assert r["record_date_parsed"] is None
    assert "record_date_parsed(unparsed)" in r["review_notes"]


def test_record_date_blank_is_none(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_date="")]), plant, "p.jpg")[0]
    assert r["record_date"] is None
    assert r["record_date_parsed"] is None


def test_missing_rows_key(plant):
    assert normalize_extraction({"_model": "m"}, plant, "p.jpg") == []


def test_rows_key_null(plant):
    assert normalize_extraction({"_model": "m", "rows": None}, plant, "p.jpg") == []


def test_empty_rows(plant, sample_raw):
    assert normalize_extraction(sample_raw([]), plant, "p.jpg") == []


def test_blank_values_are_none_and_not_flagged(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(operator="", flow_lps=None)]), plant, "p.jpg")[0]
    assert r["operator"] is None
    assert r["flow_lps"] is None
    assert r["needs_review"] is False


def test_date_carry_down(plant, sample_raw):
    rows = [row(), row(record_date=None, record_time="5am")]
    out = normalize_extraction(sample_raw(rows), plant, "p.jpg")
    assert out[0]["record_date_parsed"] == date(2026, 1, 7)
    assert out[1]["record_date_parsed"] == date(2026, 1, 7)
    assert out[1]["record_date"] is None


def test_blank_raw_date_stays_none_while_parsed_carries(plant, sample_raw):
    rows = [row(), row(record_date=None, record_time="5am")]
    out = normalize_extraction(sample_raw(rows), plant, "p.jpg")
    assert out[1]["record_date"] is None
    assert out[1]["record_date_parsed"] == date(2026, 1, 7)
    assert out[1]["needs_review"] is False


def test_date_carry_down_resets_on_new_date(plant, sample_raw):
    rows = [row(), row(record_date="08/01/26")]
    out = normalize_extraction(sample_raw(rows), plant, "p.jpg")
    assert out[1]["record_date_parsed"] == date(2026, 1, 8)


def test_unparsed_date_flagged_and_carried(plant, sample_raw):
    rows = [row(), row(record_date="not-a-date")]
    out = normalize_extraction(sample_raw(rows), plant, "p.jpg")
    assert out[1]["record_date"] == "not-a-date"
    assert out[1]["record_date_parsed"] == date(2026, 1, 7)
    assert "record_date_parsed(unparsed)" in out[1]["review_notes"]
    assert out[1]["needs_review"] is True


def test_unparsed_date_without_prior_date(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_date="not-a-date")]), plant, "p.jpg")[0]
    assert r["record_date_parsed"] is None
    assert "record_date_parsed(unparsed)" in r["review_notes"]


@pytest.mark.parametrize("value,flagged", [("100", False), ("100.1", True), ("0", False), ("-1", True)])
def test_out_of_range_flagging(plant, sample_raw, value, flagged):
    r = normalize_extraction(sample_raw([row(turbidity_filtered_ntu=value)]), plant, "p.jpg")[0]
    assert (f"turbidity_filtered_ntu(out_of_range)" in r["review_notes"]) is flagged


def test_unparseable_numeric_flagged_and_preserved(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(turbidity_raw_ntu="4l.06")]), plant, "p.jpg")[0]
    assert r["turbidity_raw_ntu"] == "4l.06"
    assert r["needs_review"] is True
    assert "turbidity_raw_ntu(unparsed)" in r["review_notes"]


def test_blank_numeric_not_flagged(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(flow_lps="")]), plant, "p.jpg")[0]
    assert r["flow_lps"] is None
    assert r["needs_review"] is False


def test_unparsed_time_flagged(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_time="nope")]), plant, "p.jpg")[0]
    assert r["record_time_24h"] is None
    assert "record_time_24h(unparsed)" in r["review_notes"]


def test_blank_time_not_flagged(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(record_time=None)]), plant, "p.jpg")[0]
    assert r["record_time_24h"] is None
    assert r["needs_review"] is False


def test_uncertain_fields_list(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(uncertain_fields=["turbidity_raw_ntu"])]), plant, "p.jpg")[0]
    assert r["needs_review"] is True
    assert r["review_notes"] == "turbidity_raw_ntu"


def test_uncertain_fields_null_does_not_crash(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(uncertain_fields=None)]), plant, "p.jpg")[0]
    assert r["needs_review"] is False


def test_uncertain_fields_string_not_exploded(plant, sample_raw):
    r = normalize_extraction(sample_raw([row(uncertain_fields="turbidity_raw_ntu")]), plant, "p.jpg")[0]
    assert r["review_notes"] == "turbidity_raw_ntu"


def test_review_notes_join_and_sort(plant, sample_raw):
    r = normalize_extraction(
        sample_raw([row(row_note="check this", uncertain_fields=["b", "a"])]), plant, "p.jpg"
    )[0]
    assert r["review_notes"] == "check this; a, b"


def test_review_notes_dedup(plant, sample_raw):
    r = normalize_extraction(
        sample_raw([row(flow_lps="5000", uncertain_fields=["flow_lps(out_of_range)"])]),
        plant, "p.jpg",
    )[0]
    assert r["review_notes"] == "flow_lps(out_of_range)"


def test_plant_and_time24_are_not_model_inputs(plant, sample_raw):
    r = normalize_extraction(
        sample_raw([row(plant="HACK", record_time_24h="99:99")]), plant, "p.jpg"
    )[0]
    assert r["plant"] == plant.name
    assert r["record_time_24h"] == "19:00"
