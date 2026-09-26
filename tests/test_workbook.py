"""Unit tests for logbook_parser.workbook.flagged_fields (matching logic only)."""

from logbook_parser.workbook import flagged_fields


def test_record_time_does_not_match_record_time_24h():
    assert flagged_fields("record_time_24h(unparsed)") == {"record_time_24h"}


def test_record_date_does_not_match_record_date_parsed():
    assert flagged_fields("record_date_parsed(unparsed)") == {"record_date_parsed"}


def test_multiple_reasons():
    notes = "turbidity_raw_ntu(out_of_range), record_time_24h(unparsed)"
    assert flagged_fields(notes) == {"turbidity_raw_ntu", "record_time_24h"}


def test_exact_key_token():
    assert flagged_fields("flow_lps") == {"flow_lps"}


def test_non_string_notes():
    assert flagged_fields(None) == set()
