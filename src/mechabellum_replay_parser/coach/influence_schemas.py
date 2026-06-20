from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class InfluenceChannel(str, Enum):
    MY_GROUND = "my_ground"
    ENEMY_GROUND = "enemy_ground"
    MY_AIR = "my_air"
    ENEMY_AIR = "enemy_air"
    MY_ANTI_CHAFF = "my_anti_chaff"
    ENEMY_ANTI_CHAFF = "enemy_anti_chaff"
    MY_ANTI_HEAVY = "my_anti_heavy"
    ENEMY_ANTI_HEAVY = "enemy_anti_heavy"
    MY_ARTILLERY = "my_artillery"
    ENEMY_ARTILLERY = "enemy_artillery"
    MY_DURABILITY = "my_durability"
    ENEMY_DURABILITY = "enemy_durability"


class MapZone(str, Enum):
    LEFT_FRONT = "left_front"
    CENTER_FRONT = "center_front"
    RIGHT_FRONT = "right_front"
    LEFT_MID = "left_mid"
    CENTER_MID = "center_mid"
    RIGHT_MID = "right_mid"
    LEFT_BACK = "left_back"
    CENTER_BACK = "center_back"
    RIGHT_BACK = "right_back"


class InfluenceGridSpec(BaseModel):
    x_min: float
    x_max: float
    y_front: float
    y_back: float
    width: int
    height: int
    player_side: str


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


class ZoneInfluenceSummary(BaseModel):
    zone: MapZone
    my_ground: float = Field(default=0.0, ge=0.0, le=1.0)
    enemy_ground: float = Field(default=0.0, ge=0.0, le=1.0)
    my_air: float = Field(default=0.0, ge=0.0, le=1.0)
    enemy_air: float = Field(default=0.0, ge=0.0, le=1.0)
    my_anti_chaff: float = Field(default=0.0, ge=0.0, le=1.0)
    enemy_anti_chaff: float = Field(default=0.0, ge=0.0, le=1.0)
    my_anti_heavy: float = Field(default=0.0, ge=0.0, le=1.0)
    enemy_anti_heavy: float = Field(default=0.0, ge=0.0, le=1.0)
    danger_for_my_ground: float = Field(default=0.0, ge=0.0, le=1.0)
    danger_for_my_air: float = Field(default=0.0, ge=0.0, le=1.0)
    opportunity_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @classmethod
    def clamped(cls, **kwargs) -> ZoneInfluenceSummary:
        for key in (
            "my_ground",
            "enemy_ground",
            "my_air",
            "enemy_air",
            "my_anti_chaff",
            "enemy_anti_chaff",
            "my_anti_heavy",
            "enemy_anti_heavy",
            "danger_for_my_ground",
            "danger_for_my_air",
            "opportunity_score",
        ):
            if key in kwargs:
                kwargs[key] = _clamp01(kwargs[key])
        return cls(**kwargs)


class TacticalInfluenceFinding(BaseModel):
    key: str
    severity: float = Field(ge=0.0, le=1.0)
    zone: MapZone | None = None
    evidence: str
    recommended_response_types: list[str] = Field(default_factory=list)
    forbidden_response_types: list[str] = Field(default_factory=list)


class InfluenceAnalysisSummary(BaseModel):
    version: str = "v1"
    grid: InfluenceGridSpec
    global_assessment: dict[str, str] = Field(default_factory=dict)
    zones: list[ZoneInfluenceSummary] = Field(default_factory=list)
    critical_zones: list[ZoneInfluenceSummary] = Field(default_factory=list)
    tactical_findings: list[TacticalInfluenceFinding] = Field(default_factory=list)
