"""Canonical master schema shared by normalization and workbook output."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Field:
    key: str
    spanish: str
    unit: str
    dtype: str                     # float|int|str|date|time
    valid: Optional[tuple] = None  # (min,max) numeric sanity range -> auto review flag


CANONICAL_SCHEMA = [
    Field("plant",                   "Planta",                      "",     "str"),
    Field("record_date",             "Fecha",                       "",     "date"),
    Field("record_time",             "Hora (as written)",           "",     "str"),
    Field("record_time_24h",         "Hora (24h normalized)",       "",     "time"),
    Field("operator",                "Nombre",                      "",     "str"),
    Field("flow_lps",                "Caudal",                      "L/s",  "float", (0, 1000)),
    Field("turbidity_raw_ntu",       "Agua Cruda",                  "NTU",  "float", (0, 5000)),
    Field("turbidity_clarified_ntu", "Clarificada",                 "NTU",  "float", (0, 1000)),
    Field("turbidity_filtered_ntu",  "Filtrada",                    "NTU",  "float", (0, 100)),
    Field("coag_slider_pct",         "Coagulante % del deslizador", "%",    "float", (0, 100)),
    Field("coag_dose_pct_mgl",       "Coagulante Dosis segun %",    "mg/L", "float", (0, 200)),
    Field("coag_dose_probeta_mgl",   "Coagulante Dosis probeta",    "mg/L", "float", (0, 200)),
]

PROVENANCE_FIELDS = ["source_image", "extracted_at", "model", "needs_review", "review_notes"]
CANONICAL_KEYS = [f.key for f in CANONICAL_SCHEMA]
FIELD_BY_KEY = {f.key: f for f in CANONICAL_SCHEMA}
ALL_COLS = CANONICAL_KEYS + PROVENANCE_FIELDS
