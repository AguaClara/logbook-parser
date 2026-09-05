# AGENTS.md — Water Treatment Log-Book Extractor

## What This Is

A single-file Python CLI tool (`Onlinetrial.py`) that **extracts handwritten water-treatment log-book data from photos into Excel** using OpenRouter's vision models. Entirely self-contained — no framework, no build system.

## How It Works (End-to-End)

1. **Photo → JSON** (via OpenRouter vision API): sends a photo + a Spanish-language prompt to a vision model, gets back structured JSON with rows of data.
2. **JSON → Normalized rows**: typed coercion, date/time parsing, range validation, provenance metadata.
3. **Rows → Excel workbook**: appended to `plant.xlsx` with three sheets: main data, `REVIEW_QUEUE` (flagged rows), and `SCHEMA_MAP` (column mapping reference). Flagged cells are highlighted red.

## Essential Commands

```bash
# Live extraction from photos
export OPENROUTER_API_KEY="sk-or-..."
python Onlinetrial.py --plant san_juan_planes --photos /path/to/photos --out plant.xlsx

# Dry-run from pre-extracted JSON (for debugging or re-running normalization)
python Onlinetrial.py --plant san_juan_planes --from-json "extractions/*.json" --out plant.xlsx

# Force re-extraction even if photos already in the output file
python Onlinetrial.py --plant san_juan_planes --photos /path/to/photos --out plant.xlsx --reprocess

# Use a different model (Gemini is better for tough handwriting)
python Onlinetrial.py --plant san_juan_planes --photos /path/to/photos --model google/gemini-2.5-flash

# Control parallelism (free tier: keep workers low, e.g. 2)
python Onlinetrial.py --plant san_juan_planes --photos /path/to/photos --workers 2
```

## Project Config

- **Package manager**: `uv` (the `uv.lock` file is present, no `requirements.txt`).
- **pyproject.toml** declares `requires-python = ">=3.14"`, dependencies: `ollama>=0.4`, `openai>=3.8.0`, `openpyxl>=3.1`, `pandas>=2.0`.
- **Known dep gap**: `ollama` is listed but never imported in the code. `pillow` (PIL) is used at runtime for HEIC→JPEG conversion but is NOT listed in `pyproject.toml` — it's only mentioned in the `RuntimeError` error message. If you extend the tool, decide whether to add it or remove `ollama`.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | OpenRouter API key (stored in `.env`) |
| `OPENROUTER_VISION_MODEL` | `nvidia/nemotron-nano-12b-v2-vl:free` | Vision model slug |
| `LOGBOOK_WORKERS` | `3` | Parallel photo threads |

## Code Organization (Single File, 483 Lines)

- **Section 1** (lines 14-84): Canonical schema, `Field` dataclass, `PlantConfig`, per-plant column mappings. Only one plant (`san_juan_planes`) is defined.
- **Section 2** (lines 86-185): `normalize_extraction()` — raw JSON → typed canonical rows with validation, date carry-down, time normalization.
- **Section 3** (lines 188-324): `extract_photo()` — OpenRouter API call with retry/backoff, image encoding (HEIC → JPEG auto-conversion), prompt building.
- **Section 4** (lines 327-382): `write_workbook()` — Excel output with red highlighting for flagged cells.
- **Section 5** (lines 385-483): CLI `main()` — argparse, dispatch, dedup, concat.

## Threading

- **Single shared client**: `_make_client()` (line 198) creates one `OpenAI` instance. That single client is built in `_rows_from_photos()` (line 411) and passed as `client=` to every `extract_photo()` call — no thread-local storage, no per-thread clients.
- **`ThreadPoolExecutor`** with `as_completed` for progress reporting. All result aggregation happens in the main thread (no races on the `rows` list).
- **No rate limiting**: There is no semaphore or lock throttling concurrent API calls. Workers run at full configured parallelism, which can trigger 429s on the free tier.
- **Retry backoff**: `min(2 ** attempt, 30)` — exponential backoff (1, 2, 4, 8, 16, 30s...) with no jitter. Retryable errors are matched by substring against `_RETRYABLE` (line 290).

## Key Patterns & Conventions

- **No type annotations on `__init__`** — uses `@dataclass` for `Field` and `PlantConfig`.
- **One lazy import** — `openai` is imported inside `_make_client()` so dry-run mode (`--from-json`) doesn't need it installed.
- **Error handling**: retry loop for transient HTTP errors (429, 502, 503, timeouts). Non-retryable errors propagate immediately.
- **Date carry-down**: if a row has no date, the tool carries the last-seen date forward — a common pattern in handwritten log transcription.
- **Time normalization**: `_to_24h()` handles bare numbers (e.g., `7` → `19:00`), `am`/`pm` suffixes, and HH:MM formats. The `bare_time_rule` configures behavior for ambiguous bare numbers ("daytime" assumes 7-11 AM, 12 PM, 1-6 PM).
- **JSON parsing**: strips `  ...  ` reasoning traces and markdown code fences before parsing.
- **Excel**: uses `openpyxl` (not xlsxwriter) — needed for cell-level formatting (red fill on review cells).
- **Dedup**: `drop_duplicates(subset=["source_image", "record_date", "record_time", "operator"], keep="last")` — prevents duplicate rows from repeated extraction of the same photo.

## Gotchas & Non-Obvious Details

- **The prompt is Spanish** — the tool was built for a Honduran water utility. All column names are in Spanish.
- **HEIC photos** are auto-converted to JPEG in-memory via `pillow-heif`. If that library is not installed, HEIC files raise an error with installation instructions.
- **Nemotron's reasoning trace** is explicitly disabled via `extra_body={"reasoning": {"enabled": False}}` — this is model-specific and may not work on other models.
- **The `_RETRYABLE` tuple** is a substring match on the lowercased error string — very loose matching. This is intentional for the flaky free-tier OpenRouter models.
- **`max_retries`** defaults to 5 but there is no `--retries` CLI flag — it's hardcoded in `extract_photo()`.
- **Only one plant defined** (`san_juan_planes`). Adding a new plant means creating a `PlantConfig` with a column mapping and adding it to the `PLANTS` dict.
- **The output filename** defaults to `plant.xlsx` but can be overridden with `--out`. The tool **appends** to existing files (reads existing rows, merges, deduplicates, re-writes the whole workbook).
- **`write_workbook` sorts** by `record_date` then `record_time_24h` before writing.
- **`--from-json` expects** JSON files with a `rows` key (OpenRouter response format). The `_source_image` key is read from the JSON, not from the filename.
- **No test suite**, no CI, no linting config — this is a production script, not a library project.

## Dependencies

```bash
uv add openai openpyxl pandas
# Optional: for HEIC photo support
uv add pillow pillow-heif
```

`ollama` is in `pyproject.toml` but unused in the code — consider removing it if you clean up.
