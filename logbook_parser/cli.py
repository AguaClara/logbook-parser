"""Command-line entry point."""

import argparse
import sys

from .config import Settings, default_model
from .pipeline import merge_rows, rows_from_json, rows_from_photos
from .plants import PLANTS
from .vision import get_provider
from .workbook import load_existing, write_workbook


def build_parser() -> argparse.ArgumentParser:
    model_default = default_model()
    ap = argparse.ArgumentParser(description="Water log-book photos -> Excel.")
    ap.add_argument("--plant", required=True, choices=list(PLANTS))
    ap.add_argument("--photos", help="folder of photos (live extraction)")
    ap.add_argument("--from-json", nargs="+", help="glob(s) of pre-extracted JSON (dry run)")
    ap.add_argument("--out", default="plant.xlsx")
    ap.add_argument("--provider", choices=["openrouter", "local"], default="openrouter",
                    help="vision backend (default: openrouter)")
    ap.add_argument("--model", default=model_default,
                    help=f"model slug (default: {model_default}). "
                         f"Try google/gemini-2.5-flash for tougher handwriting.")
    ap.add_argument("--base-url", default=None,
                    help="OpenAI-compatible base URL for --provider local "
                         "(e.g. http://localhost:11434/v1)")
    ap.add_argument("--api-key", default=None,
                    help="optional API key for --provider local")
    ap.add_argument("--reprocess", action="store_true", help="re-extract even if already in file")
    return ap


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    plant = PLANTS[args.plant]

    settings = Settings(
        plant=args.plant,
        out=args.out,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        reprocess=args.reprocess,
        photos=args.photos,
        from_json=args.from_json,
    )

    existing = load_existing(args.out, plant.name)
    done = set() if args.reprocess else set(existing["source_image"].dropna().unique())

    if args.from_json:
        new = [r for r in rows_from_json(plant, args.from_json)
               if args.reprocess or r["source_image"] not in done]
    elif args.photos:
        provider = get_provider(settings)
        new = rows_from_photos(plant, args.photos, done, settings, provider)
    else:
        parser.error("provide --photos (live) or --from-json (dry run)")

    combined = merge_rows(existing, new, args.reprocess)
    new_count = len(new)
    df, review = write_workbook(combined, args.out, plant.name)
    print(f"Appended {new_count} new rows. Total {len(df)} in '{args.out}' "
          f"({len(review)} flagged red for review).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
