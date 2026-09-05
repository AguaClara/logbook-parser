# Logbook Parser

Extract handwritten water-treatment log-book data from photos into Excel using AI vision models.

## How It Works

1. Take photos of handwritten log-book pages
2. The tool sends each photo to OpenRouter's vision API with a prompt asking for structured JSON
3. Raw JSON is normalized into typed, validated rows (date/time parsing, range checks, provenance tracking)
4. Results are appended to an Excel workbook with three sheets: main data, `REVIEW_QUEUE` (flagged rows), and `SCHEMA_MAP` (column mapping reference)

## Quick Start

```bash
# Set your API key
export OPENROUTER_API_KEY="sk-or-..."

# Extract from a folder of photos
python Onlinetrial.py --plant san_juan_planes --photos ./photos --out plant.xlsx
```

## Usage

```bash
# Set workers to 2-3 on the free tier to avoid rate limits
python Onlinetrial.py --plant san_juan_planes --photos ./photos --workers 2

# Use a stronger model for tough handwriting
python Onlinetrial.py --plant san_juan_planes --photos ./photos --model google/gemini-2.5-flash

# Re-extract photos already in the output file
python Onlinetrial.py --plant san_juan_planes --photos ./photos --reprocess

# Dry-run from previously extracted JSON (no API calls)
python Onlinetrial.py --plant san_juan_planes --from-json "extractions/*.json"
```

## Plants

Only one plant is currently defined: `san_juan_planes`. Adding a new plant means creating a `PlantConfig` with column mappings and registering it in the `PLANTS` dict.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | required | OpenRouter API key |
| `OPENROUTER_VISION_MODEL` | `nvidia/nemotron-nano-12b-v2-vl:free` | Vision model |
| `LOGBOOK_WORKERS` | `3` | Parallel requests |

## Dependencies

```bash
uv add openai openpyxl pandas
# Optional: for HEIC photo support
uv add pillow pillow-heif
```
