"""Settings loader. Reads settings.json from the project root."""

import json
from pathlib import Path

DEFAULTS = {
    "max_title_length": 80,
    "slug_separator": "-",
}


def load_settings(path: str | Path = "settings.json") -> dict:
    """Load settings from a JSON file, layering the file over DEFAULTS.

    A missing file yields the defaults. Unknown keys are kept as-is so
    callers can carry their own settings alongside ours.
    """
    settings = dict(DEFAULTS)
    settings_path = Path(path)
    if settings_path.exists():
        with settings_path.open(encoding="utf-8") as handle:
            settings.update(json.load(handle))
    return settings
