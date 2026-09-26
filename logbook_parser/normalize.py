"""Normalize raw extraction JSON into typed, validated canonical rows."""

import re
from datetime import datetime
from typing import Dict

from .plants import PlantConfig
from .schema import CANONICAL_KEYS, FIELD_BY_KEY


def coerce(value, dtype):
    if value is None or value == "":
        return None
    try:
        if dtype == "float":
            return float(str(value).replace(",", ".").strip())
        if dtype == "int":
            return int(float(value))
        return str(value).strip()
    except (ValueError, TypeError):
        return value  # keep raw; will be flagged


def parse_date(raw, fmt):
    if not raw:
        return None
    raw = str(raw).strip()
    for f in (fmt, "%d/%m/%Y", "%d/%m/%y", "%d-%m-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, f).date()
        except ValueError:
            continue
    return None


def to_24h(raw, bare_rule="daytime"):
    """Normalize a written time to 'HH:MM'. Honors explicit am/pm; applies
    bare_rule to bare numbers. Returns (hhmm_or_None, ok_bool)."""
    if not raw:
        return None, True
    s = str(raw).strip().lower().replace(" ", "").replace(".", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)$", s)
    if m:
        h, mins, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ap == "am":
            h = 0 if h == 12 else h
        else:
            h = h if h == 12 else h + 12
        return f"{h:02d}:{mins:02d}", True
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?$", s)
    if m:
        h, mins = int(m.group(1)), int(m.group(2) or 0)
        if bare_rule == "all_am":
            h = 0 if h == 12 else h
        elif bare_rule == "all_pm":
            h = h if h == 12 else h + 12
        else:  # "daytime": 7-11 AM, 12 noon, 1-6 PM
            if 1 <= h <= 6:
                h += 12
        return f"{h:02d}:{mins:02d}", True
    return None, False  # unrecognized format -> flag for review


def normalize_extraction(raw: Dict, plant: PlantConfig, source_image: str) -> list:
    rows_out = []
    extracted_at = datetime.now().isoformat(timespec="seconds")
    model = raw.get("_model", "")
    last_date = None

    for r in raw.get("rows", []):
        out = {k: None for k in CANONICAL_KEYS}
        out["plant"] = plant.name
        review = list(r.get("uncertain_fields", []))

        for fld in FIELD_BY_KEY.values():
            if fld.key in ("plant", "record_time_24h"):
                continue
            val = r.get(fld.key)
            if fld.dtype == "date":
                parsed = parse_date(val if val else r.get("raw_date"), plant.date_format)
                if parsed is None and (val or r.get("raw_date")):
                    review.append("record_date(unparsed)")
                parsed = parsed or last_date          # carry down
                if parsed:
                    last_date = parsed
                out[fld.key] = parsed
            else:
                coerced = coerce(val, fld.dtype)
                out[fld.key] = coerced
                if fld.valid and isinstance(coerced, (int, float)):
                    lo, hi = fld.valid
                    if not (lo <= coerced <= hi):
                        review.append(f"{fld.key}(out_of_range)")

        t24, ok = to_24h(out.get("record_time"), plant.bare_time_rule)
        out["record_time_24h"] = t24
        if not ok:
            review.append("record_time_24h(unparsed)")

        note = r.get("row_note", "") or ""
        out.update({
            "source_image": source_image, "extracted_at": extracted_at, "model": model,
            "needs_review": bool(review),
            "review_notes": "; ".join(filter(None, [note, ", ".join(sorted(set(review)))])),
        })
        rows_out.append(out)
    return rows_out
