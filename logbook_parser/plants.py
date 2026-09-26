"""Per-plant column mappings and extraction hints."""

from dataclasses import dataclass


@dataclass
class PlantConfig:
    name: str
    columns: list                       # [(raw_spanish_header, canonical_key_or_None), ...]
    extraction_hints: str = ""
    date_format: str = "%d/%m/%y"
    bare_time_rule: str = "daytime"


SAN_JUAN_PLANES = PlantConfig(
    name="San Juan Planes",
    columns=[
        ("Fecha",                           "record_date"),
        ("Hora",                            "record_time"),
        ("Nombre",                          "operator"),
        ("Caudal (L/s)",                    "flow_lps"),
        ("Agua Cruda UTN",                  "turbidity_raw_ntu"),
        ("Clarificada UTN",                 "turbidity_clarified_ntu"),
        ("Filtrada UTN",                    "turbidity_filtered_ntu"),
        ("% del deslizador (Coagulante)",   "coag_slider_pct"),
        ("Dosis segun % mg/L (Coagulante)", "coag_dose_pct_mgl"),
        ("Dosis segun probeta mg/L (Coag)", "coag_dose_probeta_mgl"),
    ],
    extraction_hints=(
        "Handwritten water-treatment operations log. Read ONLY these columns "
        "(left group): Fecha, Hora, Nombre, Caudal, Agua Cruda UTN, Clarificada UTN, "
        "Filtrada UTN, then the three 'Coagulante' sub-columns (% del deslizador, "
        "Dosis segun % mg/L, Dosis segun probeta mg/L). IGNORE the entire 'Cloro' "
        "section and the rightmost cut-off column. Caudal is almost always 12. "
        "Dates are DD/MM/YY and often only appear on the first row of a day; leave the date "
        "blank where it is not written. Times mix formats (7pm / 7:00 / 5am). Operators are "
        "usually Victor, Tulio, or Jose. Turbidity values are decimals (41.06, 1.79). "
        "Ignore any bleed-through / partial rows from another page at the edges."
    ),
    bare_time_rule="daytime",
)

PLANTS = {"san_juan_planes": SAN_JUAN_PLANES}
