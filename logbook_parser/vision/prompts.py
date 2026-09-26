"""Prompt construction for the vision transcription task."""

from ..plants import PlantConfig
from ..schema import FIELD_BY_KEY


def build_prompt(plant: PlantConfig) -> str:
    lines = []
    for raw_header, key in plant.columns:
        if key is None:
            continue
        f = FIELD_BY_KEY[key]
        rng = f", expected range {f.valid}" if f.valid else ""
        lines.append(f'  - "{key}" ({f.dtype}, unit: {f.unit or "none"}{rng}) '
                     f'— Spanish column on sheet: "{raw_header}"')
    cols = "\n".join(lines)
    return f"""You transcribe a handwritten Spanish water-treatment plant log book into JSON.

PLANT: {plant.name}

Sheet notes:
{plant.extraction_hints}

For EVERY data row in the table, output one object with these fields
(use null when a cell is blank or unreadable):
{cols}

Also include per row:
  - "uncertain_fields": list of the field names above you are NOT confident about
  - "row_note": short note if the row is unusual, else ""

RULES
- Transcribe ONLY rows inside this table. Ignore bleed-through / partial rows at edges.
- Keep numbers exactly as written (e.g. 41.06, 0.68). Never round or invent.
- Dates: transcribe exactly as written (e.g. 27/5/24). Never reformat or reorder day/month.
- If the date cell is blank, output null; never copy a date from another row.
- Ambiguous digit: give your best read AND list that field in "uncertain_fields".
- Do NOT include any explanation or reasoning. Output ONLY a JSON object:
  {{"rows": [ {{...}} ], "page_note": "..."}}
"""
