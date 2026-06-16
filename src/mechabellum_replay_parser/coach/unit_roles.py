from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "data" / "unit_data.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def get_unit_data(name: str) -> dict:
    return _load().get(name.lower(), {})


def get_tags(name: str) -> list[str]:
    return get_unit_data(name).get("tags", [])


def has_tag(name: str, tag: str) -> bool:
    return tag in get_tags(name)
