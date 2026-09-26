# Logbook Parser

Extract handwritten water-treatment log-book data from photos into Excel using AI vision models.

## How It Works

1. Take photos of handwritten log-book pages
2. Each photo is sent to a vision model with a prompt asking for structured JSON
3. Raw JSON is normalized into typed, validated rows (date/time parsing, range checks, provenance tracking)
4. Results are appended to an Excel workbook with three sheets: main data, `REVIEW_QUEUE` (flagged rows), and `SCHEMA_MAP` (column mapping reference)

Live extraction currently goes through OpenRouter, but the vision layer is provider-agnostic and can target a local OpenAI-compatible server.

## Quick Start

```bash
# Set your API key
export OPENROUTER_API_KEY="sk-or-..."

# Install (uv)
uv sync

# Extract from a folder of photos
uv run logbook-parser --plant san_juan_planes --photos ./photos --out plant.xlsx
```

You can also run the package directly:

```bash
uv run python -m logbook_parser --plant san_juan_planes --photos ./photos --out plant.xlsx
```

## Usage

```bash
# Set workers to 2-3 on the free tier to avoid rate limits
logbook-parser --plant san_juan_planes --photos ./photos --workers 2

# Use a stronger model for tough handwriting
logbook-parser --plant san_juan_planes --photos ./photos --model google/gemini-2.5-flash

# Re-extract photos already in the output file
logbook-parser --plant san_juan_planes --photos ./photos --reprocess

# Dry-run from previously extracted JSON (no API calls)
logbook-parser --plant san_juan_planes --from-json "extractions/*.json"
```

### Local inference

`--provider local` targets any server exposing the OpenAI chat-completions API
with vision support (llama.cpp's server, vLLM, or Ollama's OpenAI-compatible
endpoint). Pass its URL with `--base-url`:

```bash
# Ollama's OpenAI-compatible endpoint, for example
logbook-parser --plant san_juan_planes --photos ./photos \
  --provider local --base-url http://localhost:11434/v1 --model llava

# Or llama.cpp's server
logbook-parser --plant san_juan_planes --photos ./photos \
  --provider local --base-url http://localhost:8080/v1 --model ./models/qwen2.5-vl.gguf
```

No OpenRouter API key is needed for local inference.

## Plants

Only one plant is currently defined: `san_juan_planes`. Adding a new plant means creating a `PlantConfig` in `logbook_parser/plants.py` with column mappings and registering it in the `PLANTS` dict.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | required for `--provider openrouter` | OpenRouter API key |
| `OPENROUTER_VISION_MODEL` | `google/gemma-4-31b-it:free` | Default vision model slug |
| `LOGBOOK_WORKERS` | `3` | Parallel requests |

## Package Layout

```
logbook_parser/
  schema.py          canonical fields and output columns
  plants.py          per-plant column mappings
  normalize.py       raw JSON -> typed, validated rows
  json_utils.py      tolerant model-output JSON parsing
  config.py          runtime Settings
  vision/            provider-agnostic photo -> JSON layer
    base.py          VisionProvider protocol
    images.py        image loading / HEIC conversion
    prompts.py       prompt construction
    openai_compat.py generic OpenAI-compatible provider + retry
    openrouter.py    OpenRouter preset
    local.py         local OpenAI-compatible preset
  workbook.py        Excel output and review highlighting
  pipeline.py        photo/JSON orchestration, dedup, merge
  cli.py             command-line entry point
```

## Dependencies

```bash
uv add openai openpyxl pandas pillow pillow-heif
```

## Adding a local provider

Any backend that implements the `VisionProvider` protocol in
`logbook_parser/vision/base.py` can be selected by extending
`get_provider()` in `logbook_parser/vision/__init__.py`. The shared
`extract_photo()` orchestration handles prompt building, JSON parsing, and
model tagging, so new providers only need to return raw model text.
