"""Orchestration: photos/JSON -> normalized rows, with dedup and merging."""

import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from .normalize import normalize_extraction
from .schema import ALL_COLS
from .vision import extract_photo, get_provider

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")


def rows_from_json(plant, json_globs):
    rows = []
    for pattern in json_globs:
        for jf in sorted(glob.glob(pattern)):
            with open(jf, encoding="utf-8") as f:
                raw = json.load(f)
            rows.extend(normalize_extraction(raw, plant, raw.get("_source_image", os.path.basename(jf))))
    return rows


def rows_from_photos(plant, photos_dir, done, settings):
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

    provider = get_provider(settings)   # built once, shared across worker threads
    workers = max(1, min(settings.workers, total))
    print(f"Processing {total} photo(s) with {workers} worker(s) via {settings.model} ...",
          file=sys.stderr)

    def work(img):
        name = os.path.basename(img)
        t0 = time.time()
        try:
            extracted = extract_photo(img, plant, provider, settings.model)
            new_rows = normalize_extraction(extracted, plant, name)
            return name, new_rows, time.time() - t0, None
        except Exception as e:  # noqa: BLE001
            return name, None, time.time() - t0, e

    rows, ok_count, fail_count = [], 0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, img) for img in todo]
        for i, fut in enumerate(as_completed(futures), start=1):
            name, new_rows, dt, err = fut.result()
            if err is None:
                rows.extend(new_rows)
                ok_count += 1
                flagged = sum(1 for r in new_rows if r["needs_review"])
                print(f"[{i}/{total}] {name} done in {dt:0.0f}s -> "
                      f"{len(new_rows)} rows ({flagged} flagged)", file=sys.stderr)
            else:
                fail_count += 1
                print(f"[{i}/{total}] {name} FAILED after {dt:0.0f}s -> {err}", file=sys.stderr)

    print(f"Done: {ok_count} succeeded, {fail_count} failed, "
          f"{len(rows)} total rows extracted.", file=sys.stderr)
    return rows


def merge_rows(existing, new, reprocess):
    new_df = pd.DataFrame(new, columns=ALL_COLS)
    if reprocess and not new_df.empty:
        existing = existing[~existing["source_image"].isin(new_df["source_image"].unique())]
    return pd.concat([existing, new_df], ignore_index=True).drop_duplicates(
        subset=["source_image", "record_date", "record_time", "operator"], keep="last")
