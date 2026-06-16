from __future__ import annotations

from .coordinates import CoordinateFrame
from .schemas import (
    ConstructionRole,
    ConstructionStatus,
    ConstructionType,
    ConstructionView,
    Position,
)

# ── Mapping tables ────────────────────────────────────────────────────────────

_ID_TO_TYPE: dict[int, ConstructionType] = {
    1: ConstructionType.SUPPLY_TOWER,
    2: ConstructionType.COMMAND_TOWER,
    3: ConstructionType.RESEARCH_TOWER,
}

_NAME_TO_TYPE: dict[str, ConstructionType] = {
    "supply tower": ConstructionType.SUPPLY_TOWER,
    "command tower": ConstructionType.COMMAND_TOWER,
    "research tower": ConstructionType.RESEARCH_TOWER,
}

_TYPE_TO_ROLE: dict[ConstructionType, ConstructionRole] = {
    ConstructionType.SUPPLY_TOWER: ConstructionRole.ECONOMY,
    ConstructionType.COMMAND_TOWER: ConstructionRole.COMMAND,
    ConstructionType.RESEARCH_TOWER: ConstructionRole.RESEARCH,
    ConstructionType.UNKNOWN: ConstructionRole.UNKNOWN,
}


def _resolve_type(raw: dict) -> ConstructionType:
    cid = raw.get("construction_id")
    if cid is not None and cid in _ID_TO_TYPE:
        return _ID_TO_TYPE[cid]
    raw_str = str(raw.get("type", "")).strip().lower()
    return _NAME_TO_TYPE.get(raw_str, ConstructionType.UNKNOWN)


def normalize_construction(
    raw: dict,
    frame: CoordinateFrame | None = None,
) -> ConstructionView:
    ctype = _resolve_type(raw)
    role = _TYPE_TO_ROLE[ctype]

    raw_status = str(raw.get("status", "")).lower()
    if raw_status == "destroyed":
        status = ConstructionStatus.DESTROYED
    else:
        # Constructions present in a round snapshot are alive by default.
        status = ConstructionStatus.ALIVE

    pos_raw = raw.get("position")
    position: Position | None = None
    if pos_raw:
        position = Position(x=pos_raw["x"], y=pos_raw["y"])

    position_label: str | None = None
    if frame is not None and position is not None:
        position_label = frame.position_to_label(position)

    return ConstructionView(
        type=ctype,
        role=role,
        status=status,
        raw_type=raw.get("type"),
        construction_id=raw.get("construction_id"),
        index=raw.get("index"),
        position=position,
        position_label=position_label,
    )
