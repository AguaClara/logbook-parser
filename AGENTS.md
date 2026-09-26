# AGENTS.md — Water Treatment Log-Book Extractor

## What This Is

A Python CLI package (`logbook_parser/`) that **extracts handwritten water-treatment log-book data from photos into Excel** using vision models. Provider-agnostic: OpenRouter by default, with a local OpenAI-compatible backend.

## How It Works (End-to-End)

1. **Photo → JSON** (via a vision provider): sends a photo + a Spanish-language prompt to a vision model, gets back structured JSON with rows of data.
2. **JSON → Normalized rows**: typed coercion, date/time parsing, range validation, provenance metadata (`logbook_parser/normalize.py`).
3. **Rows → Excel workbook**: appended to `plant.xlsx` with three sheets: main data, `REVIEW_QUEUE` (flagged rows), and `SCHEMA_MAP` (column mapping reference). Flagged cells are highlighted red (`logbook_parser/workbook.py`).

## Essential Commands

```bash
# Live extraction from photos
export OPENROUTER_API_KEY="sk-or-..."
uv run logbook-parser --plant san_juan_planes --photos /path/to/photos --out plant.xlsx

# Dry-run from pre-extracted JSON (for debugging or re-running normalization)
uv run logbook-parser --plant san_juan_planes --from-json "extractions/*.json" --out plant.xlsx

# Force re-extraction even if photos already in the output file
uv run logbook-parser --plant san_juan_planes --photos /path/to/photos --out plant.xlsx --reprocess

# Use a different model (Gemini is better for tough handwriting)
uv run logbook-parser --plant san_juan_planes --photos /path/to/photos --model google/gemini-2.5-flash

# Local OpenAI-compatible server (llama.cpp / vLLM / Ollama)
uv run logbook-parser --plant san_juan_planes --photos /path/to/photos \
  --provider local --base-url http://localhost:11434/v1 --model llava

# Equivalent module invocation
uv run python -m logbook_parser --plant san_juan_planes --photos /path/to/photos
```

## Project Config

- **Package manager**: `uv` (the `uv.lock` file is present, no `requirements.txt`).
- **pyproject.toml** declares `requires-python = ">=3.14"`; dependencies: `openai>=3.8.0`, `openpyxl>=3.1`, `pandas>=2.0`, `pillow>=10.0`, `pillow-heif>=0.16`. Entry point: `logbook-parser = "logbook_parser.cli:main"`.
- **`ollama` is intentionally NOT a dependency** — the local backend uses the generic OpenAI-compatible HTTP path instead. A native Ollama provider could be added later under `vision/`.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required for `--provider openrouter`)* | OpenRouter API key |
| `OPENROUTER_VISION_MODEL` | `google/gemma-4-31b-it:free` | Default vision model slug |

Env is read by `logbook_parser/config.py` (`default_model()`) and in `vision/openrouter.py`, never at import time.

## Code Organization

```
logbook_parser/
  __init__.py         version
  __main__.py         `python -m logbook_parser`
  schema.py           Field, CANONICAL_SCHEMA, PROVENANCE_FIELDS, ALL_COLS, FIELD_BY_KEY
  plants.py           PlantConfig, SAN_JUAN_PLANES, PLANTS
  normalize.py        coerce, parse_date, to_24h, normalize_extraction
  json_utils.py       parse_json (think-trace / fence stripping)
  config.py           Settings dataclass + env-backed defaults
  vision/
    __init__.py       extract_photo(), get_provider()
    base.py           EncodedImage, VisionProvider protocol, ExtractionError
    images.py         image_data_url, MIME map, HEIC->JPEG
    prompts.py        build_prompt(plant)
    openai_compat.py  OpenAICompatibleProvider + retry/backoff, extract_json
    openrouter.py     OpenRouter preset
    local.py          local OpenAI-compatible preset
  workbook.py         load_existing, schema_map_df, write_workbook + red styling
  pipeline.py         process_photo, rows_from_json, rows_from_photos, merge_rows
  cli.py              build_parser(), main()
```

- **schema.py / plants.py** — pure data, no I/O, no project imports.
- **normalize.py / json_utils.py** — pure functions (the main unit-test surface).
- **config.py** — frozen `Settings`; env read inside functions so callers can inject settings.
- **vision/base.py** — `EncodedImage` (path + optional data_url) and the `VisionProvider` protocol. `extract_photo()` in `vision/__init__.py` handles image encoding, JSON parsing, and `_model` tagging, so all providers behave identically. The prompt is built once per run by `pipeline.rows_from_photos()` and passed in.
- **vision/openai_compat.py** — the shared transport/retry; OpenRouter and local are just presets.

## Extraction Loop

- **Sequential**: `rows_from_photos()` (`pipeline.py`) iterates photos in a simple `for` loop, one at a time. There is no thread pool and no `--workers` flag.
- **Single shared provider**: the CLI builds the provider once via `get_provider(settings)` and injects it into `rows_from_photos(plant, photos_dir, done, settings, provider)`. Injecting the provider is the test seam (pass a stub to run offline).
- **`process_photo(path, plant, provider, prompt, model)`** — extracts and normalizes one photo and raises on failure.
- **Continue-on-error**: the loop catches per-photo exceptions, prints `FAILED ... -> <provider error>`, increments the failure count, and moves on.
- **Retry backoff**: `min(2 ** attempt, 30)` — no jitter. Retryable errors are matched by substring against `RETRYABLE` in `vision/openai_compat.py`.

## Key Patterns & Conventions

- **`@dataclass`** for `Field`, `PlantConfig`, `Settings`, `EncodedImage`; no type annotations on `__init__`.
- **Lazy `openai` import** — inside `OpenAICompatibleProvider._client_instance()` so dry-run mode (`--from-json`) doesn't need it installed.
- **Date carry-down**: if a row has no written date, the last-seen parsed date is carried forward in `normalize` (not the prompt); `record_date` stays blank so the as-written column is preserved.
- **As-written dates**: `record_date` is the verbatim date the model transcribes (the prompt tells it never to reformat); `record_date_parsed` is the derived `date`, mirroring the as-written `record_time` / derived `record_time_24h` pair. A failed parse flags `record_date_parsed(unparsed)` and `record_date` still preserves the text.
- **Time normalization**: `to_24h()` handles bare numbers (e.g., `7` → `19:00`), `am`/`pm` suffixes, and HH:MM. `bare_time_rule` configures bare-number behavior ("daytime" assumes 7-11 AM, 12 PM, 1-6 PM).
- **Excel**: uses `openpyxl` for cell-level formatting (red fill on review cells).
- **Dedup**: `drop_duplicates(subset=["source_image", "record_date_parsed", "record_time", "operator"], keep="last")` in `pipeline.merge_rows()`.

## Gotchas & Non-Obvious Details

- **The prompt is Spanish** — built for a Honduran water utility. All column names are in Spanish.
- **HEIC photos** are auto-converted to JPEG in-memory via `pillow-heif`; missing library raises an install-instructions error.
- **Nemotron's reasoning trace** is disabled via `extra_body={"reasoning": {"enabled": False}}` in the OpenRouter preset only — model-specific.
- **The `RETRYABLE` tuple** is a loose substring match on the lowercased error string, intentional for flaky free-tier models.
- **`max_retries`** lives on `Settings` (default 5) and is passed to the provider; there is no `--retries` CLI flag yet.
- **Only one plant defined** (`san_juan_planes`). Adding one means creating a `PlantConfig` in `plants.py` and registering it in `PLANTS`.
- **The output file** defaults to `plant.xlsx`, overridable with `--out`; the tool **appends** (reads, merges, dedups, rewrites).
- **`write_workbook` sorts** by `record_date_parsed` then `record_time_24h` before writing.
- **`--from-json` expects** JSON files with a `rows` key. `_source_image` is read from the JSON, not the filename.
- **`--provider local` requires `--base-url`** and needs no API key.
- **Tests**: `pytest` suite under `tests/` (run `uv run pytest`); no CI or linting config yet.

## Dependencies

```bash
uv add openai openpyxl pandas pillow pillow-heif
```

## Adding a Local Backend

Implement the `VisionProvider` protocol (`vision/base.py`) — return raw model text from `complete()` — then wire it into `get_provider()` in `vision/__init__.py` and add a `--provider` choice. For OpenAI-compatible servers, just point the `local` preset at a different `--base-url`.

## Git Commits

- **Only commit when explicitly asked.** Never commit on your own initiative.
- **Subject line**: short, imperative, matching existing repo style (e.g. `Refactor single-file script into modular package`).
- **Body**: use bullet points to explain what changed and why, one change per bullet. Group related edits into a single bullet; mention removed files and renamed/moved modules.
- **AI attribution trailer**: end every AI-assisted commit message with a trailer naming the model that did the work:
  ```
  AI-Assisted-By: <provider>/<model-id>
  ```
  Example: `AI-Assisted-By: hyper/deepseek-v4.1-flash`.
- **Before staging**: run `git status`, `git diff`, and `git diff --cached`; stage only intended files.
- **Never commit secrets**: `.env` is excluded via `.git/info/exclude`; do not add it. Leave stray build/output artifacts (e.g. `test.xlsx`) out of commits.
