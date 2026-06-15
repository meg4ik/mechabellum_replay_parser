"""Placement block parser — extracted from the legacy llm.py."""
from __future__ import annotations

import json
import re

_PLACEMENT_RE = re.compile(r"PLACEMENT:\s*```json\s*(\[.*?\])\s*```", re.DOTALL)

_ZONE_X_MIN, _ZONE_X_MAX = -285, 285
_ZONE_Y_MIN, _ZONE_Y_MAX = -295, -45


def parse_placement(text: str) -> list[dict] | None:
    """Extract and validate the PLACEMENT block from LLM text output."""
    m = _PLACEMENT_RE.search(text)
    if not m:
        return None
    try:
        items = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            entry = {
                "unit": str(item["unit"]),
                "x": int(item["x"]),
                "y": int(item["y"]),
                "action": str(item.get("action", "keep")),
            }
        except (KeyError, ValueError, TypeError):
            continue
        entry["x"] = max(_ZONE_X_MIN, min(_ZONE_X_MAX, entry["x"]))
        entry["y"] = max(_ZONE_Y_MIN, min(_ZONE_Y_MAX, entry["y"]))
        result.append(entry)
    return result or None
