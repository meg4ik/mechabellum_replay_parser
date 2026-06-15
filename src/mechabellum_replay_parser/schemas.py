from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Position(BaseModel):
    x: int
    y: int


class Unit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    unit_id: int
    index: int
    level: int
    exp: int
    rounds_survived: int
    position: Position | None
    equipment: str | None
    sell_supply: int
    rotate: bool


class ActiveTech(BaseModel):
    unit: str
    tech: str
    tech_id: int


class Contraption(BaseModel):
    name: str
    contraption_id: int
    index: int
    position: Position | None


class Construction(BaseModel):
    type: str
    construction_id: int
    index: int
    position: Position | None


class Shop(BaseModel):
    unlocked: list[str] = []
    locked: list[str] = []
    buys_remaining: int | None = None
    unlocks_remaining: int | None = None


class CommanderSkill(BaseModel):
    name: str
    is_active: bool
    cooling_round: int


class FightReport(BaseModel):
    crystals_destroyed: int
    units_survived: int
    score: int


class PlayerRoundState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hp: int
    supply: int | None
    army_value: int
    fight_outcome: str | None
    officers: list[str]
    commander_skills: list[CommanderSkill]
    units: list[Unit]
    active_techs: list[ActiveTech]
    contraptions: list[Contraption]
    constructions: list[Construction]
    shop: Shop
    actions: list[dict[str, Any]]


class Round(BaseModel):
    round: int
    fight_result: dict[str, FightReport] | None
    players: dict[str, PlayerRoundState]


class ReplayMetadata(BaseModel):
    version: str
    match_mode: str | None


class ParsedReplay(BaseModel):
    metadata: ReplayMetadata
    teams: list[list[str]]
    rounds: list[Round]
    last_round: int


class PlacementEntry(BaseModel):
    unit: str
    x: int
    y: int
    action: str
