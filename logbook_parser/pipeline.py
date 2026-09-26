"""Orchestration: photos/JSON -> normalized rows, with dedup and merging."""

import glob
import json
import os
import sys
import time

import pandas as pd

from .normalize import normalize_extraction
from .schema import ALL_COLS
from .vision import build_prompt, extract_photo

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")


def rows_from_json(plant, json_globs):
    rows = []
    for pattern in json_globs:
        for jf in sorted(glob.glob(pattern)):
            with open(jf, encoding="utf-8") as f:
                raw = json.load(f)
            rows.extend(normalize_extraction(raw, plant, raw.get("_source_image", os.path.basename(jf))))
    return rows


def process_photo(path, plant, provider, prompt, model):
    """Extract + normalize one photo. Raises on provider failure."""
    extracted = extract_photo(path, provider, prompt, model)
    return normalize_extraction(extracted, plant, os.path.basename(path))


def rows_from_photos(plant, photos_dir, done, settings, provider):
    all_imgs = [p for p in sorted(glob.glob(os.path.join(photos_dir, "*")))
                if p.lower().endswith(IMAGE_EXTS)]
    todo = [p for p in all_imgs if os.path.basename(p) not in done]
    skipped = len(all_imgs) - len(todo)
    total = len(todo)

    if skipped:
        print(f"[skip] {skipped} photo(s) already in the file", file=sys.stderr)
    if total == 0:
        print("Nothing new to process.", file=sys.stderr)
        return []

    prompt = build_prompt(plant)   # identical for every photo -> build once
    print(f"Processing {total} photo(s) via {settings.model} ...", file=sys.stderr)

    rows, ok_count, fail_count = [], 0, 0
    for i, img in enumerate(todo, start=1):
        name = os.path.basename(img)
        t0 = time.time()
        try:
            new_rows = process_photo(img, plant, provider, prompt, settings.model)
        except Exception as e:  # noqa: BLE001 — keep going on a bad photo
            fail_count += 1
            print(f"[{i}/{total}] {name} FAILED after {time.time() - t0:0.0f}s -> {e}",
                  file=sys.stderr)
            continue
        rows.extend(new_rows)
        ok_count += 1
        flagged = sum(1 for r in new_rows if r["needs_review"])
        print(f"[{i}/{total}] {name} done in {time.time() - t0:0.0f}s -> "
              f"{len(new_rows)} rows ({flagged} flagged)", file=sys.stderr)

    print(f"Done: {ok_count} succeeded, {fail_count} failed, "
          f"{len(rows)} total rows extracted.", file=sys.stderr)
    return rows


def merge_rows(existing, new, reprocess):
    new_df = pd.DataFrame(new, columns=ALL_COLS)
    if reprocess and not new_df.empty:
        existing = existing[~existing["source_image"].isin(new_df["source_image"].unique())]
    return pd.concat([existing, new_df], ignore_index=True).drop_duplicates(
        subset=["source_image", "record_date", "record_time", "operator"], keep="last")
