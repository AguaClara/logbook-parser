"""Shared fixtures for the logbook_parser test suite."""

import json

import pandas as pd
import pytest

from logbook_parser.plants import SAN_JUAN_PLANES

PLANT_SHEET = SAN_JUAN_PLANES.name
REVIEW_SHEET = "REVIEW_QUEUE"
SCHEMA_SHEET = "SCHEMA_MAP"


@pytest.fixture
def plant():
    return SAN_JUAN_PLANES


@pytest.fixture
def sample_raw():
    def _make(rows, model="test:model"):
        return {"_model": model, "rows": rows}

    return _make


@pytest.fixture
def write_json(tmp_path):
    def _write(payload, name="extraction.json"):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    return _write


@pytest.fixture
def read_workbook():
    def _read(path):
        return pd.read_excel(path, sheet_name=None)

    return _read
