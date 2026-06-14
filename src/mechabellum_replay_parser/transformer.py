import json
import xml.etree.ElementTree as ET
from pathlib import Path

from . import (
    extract_xml,
    CARD_LOOKUP,
    COMMAND_TOWER_SKILLS,
    CONTRAPTION_LOOKUP,
    ITEM_LOOKUP,
    OFFICER_LOOKUP,
    RESEARCH_TOWER_SKILLS,
    SKILL_LOOKUP,
    TECH_LOOKUP,
    UNIT_LOOKUP,
)

CONSTRUCTION_LOOKUP = {
    1: "Supply Tower",
    2: "Command Tower",
    3: "Research Tower",
}


def _xy(el) -> dict | None:
    if el is None:
        return None
    return {"x": int(el.find("x").text), "y": int(el.find("y").text)}


def _unit_name(uid: int) -> str:
    return UNIT_LOOKUP.get(uid, f"unknown({uid})")


def _parse_units(player_data_el) -> list[dict]:
    units = []
    for u in player_data_el.findall("units/NewUnitData"):
        uid = int(u.find("id").text)
        equip_id = int(u.find("EquipmentID").text)
        units.append({
            "name": _unit_name(uid),
            "unit_id": uid,
            "index": int(u.find("Index").text),
            "level": int(u.find("Level").text),
            "exp": int(u.find("Exp").text),
            "rounds_survived": int(u.find("RoundCount").text),
            "position": _xy(u.find("Position")),
            "equipment": ITEM_LOOKUP.get(equip_id) if equip_id != 0 else None,
            "sell_supply": int(u.find("SellSupply").text),
            "rotate": u.find("IsRotate").text == "true",
        })
    return units


def _parse_officers(player_data_el) -> list[str]:
    return [
        OFFICER_LOOKUP.get(int(o.text), f"unknown_officer({o.text})")
        for o in player_data_el.findall("officers/int")
    ]


def _parse_commander_skills(player_data_el) -> dict[int, dict]:
    """Returns {index: {name, is_active, cooling_round}} for all acquired skills."""
    skills = {}
    for s in player_data_el.findall("commanderSkills/CommanderSkillData"):
        idx = int(s.find("index").text)
        sid = int(s.find("id").text)
        cooling = s.find("coolingRound")
        skills[idx] = {
            "name": SKILL_LOOKUP.get(sid, f"unknown_skill({sid})"),
            "is_active": s.find("isActive").text == "true",
            "cooling_round": int(cooling.text) if cooling is not None else 0,
        }
    return skills


def _parse_active_techs(player_data_el) -> list[dict]:
    techs = []
    for unit_tech in player_data_el.findall("activeTechnologies/"):
        uid_el = unit_tech.find("id")
        if uid_el is None:
            continue
        uid = int(uid_el.text)
        for tech_el in unit_tech.findall("techs/tech"):
            tid = int(tech_el.get("data"))
            techs.append({
                "unit": _unit_name(uid),
                "tech": TECH_LOOKUP.get(tid, f"unknown_tech({tid})"),
                "tech_id": tid,
            })
    return techs


def _parse_contraptions(player_data_el) -> list[dict]:
    items = []
    for c in player_data_el.findall("contraptions/ContraptionData"):
        cid = int(c.find("id").text)
        items.append({
            "name": CONTRAPTION_LOOKUP.get(cid, f"unknown({cid})"),
            "contraption_id": cid,
            "index": int(c.find("index").text),
            "position": _xy(c.find("position")),
        })
    return items


def _parse_constructions(player_data_el) -> list[dict]:
    items = []
    for c in player_data_el.findall("constructionSnapshotDatas/ConstructionSnapshotData"):
        cid = int(c.find("ID").text)
        items.append({
            "type": CONSTRUCTION_LOOKUP.get(cid, f"unknown({cid})"),
            "construction_id": cid,
            "index": int(c.find("Index").text),
            "position": _xy(c.find("Position")),
        })
    return items


def _parse_shop(player_data_el) -> dict:
    shop = player_data_el.find("shop")
    if shop is None:
        return {}
    return {
        "unlocked": [_unit_name(int(u.text)) for u in shop.findall("unlockedUnits/int")],
        "locked": [_unit_name(int(u.text)) for u in shop.findall("lockedUnits/int")],
        "buys_remaining": int(shop.find("BuyCount").text) if shop.find("BuyCount") is not None else None,
        "unlocks_remaining": int(shop.find("UnlockCount").text) if shop.find("UnlockCount") is not None else None,
    }


def _parse_actions(round_el, round_number: int, reinforce_rounds: list[int], skills: dict[int, dict]) -> list[dict]:
    # Work on a copy so acquired skills accumulate within this round
    skills = dict(skills)
    next_skill_index = max(skills.keys()) + 1 if skills else 0

    actions = []
    for action_el in round_el.findall("actionRecords/MatchActionData"):
        xsi_type = action_el.get("{http://www.w3.org/2001/XMLSchema-instance}type")
        time_el = action_el.find("Time")
        timestamp = int(time_el.text) if time_el is not None else None

        parsed = _parse_single_action(action_el, xsi_type, round_number, reinforce_rounds, skills)
        if parsed is None:
            continue

        # Track skills acquired via card selection so later use_skill can resolve them
        if parsed["type"] == "card_select":
            card_id = parsed.get("card_id")
            if card_id in SKILL_LOOKUP:
                skills[next_skill_index] = {
                    "name": SKILL_LOOKUP[card_id],
                    "is_active": True,
                    "cooling_round": 0,
                }
                next_skill_index += 1

        # flatten move batches into individual actions with same timestamp
        if parsed["type"] == "_move_batch":
            for move in parsed["moves"]:
                move["time"] = timestamp
                actions.append(move)
        else:
            parsed["time"] = timestamp
            actions.append(parsed)

    return actions


def _parse_single_action(
    el, xsi_type: str, round_number: int, reinforce_rounds: list[int], skills: dict[int, dict]
) -> dict | None:
    if xsi_type == "PAD_MoveUnit":
        moves = []
        for move in el.findall("moveUnitDatas/MoveUnitData"):
            uid = int(move.find("unitID").text)
            moves.append({
                "type": "move",
                "unit": _unit_name(uid),
                "unit_id": uid,
                "unit_index": int(move.find("unitIndex").text),
                "from": _xy(move.find("positionRecord")),
                "to": _xy(move.find("position")),
                "rotate": move.find("isRotate").text == "true",
            })
        return {"type": "_move_batch", "moves": moves} if moves else None

    if xsi_type == "PAD_BuyUnit":
        uid = int(el.find("UID").text)
        return {
            "type": "buy",
            "unit": _unit_name(uid),
            "unit_id": uid,
            "position": _xy(el.find("position")),
        }

    if xsi_type == "PAD_UnlockUnit":
        uid = int(el.find("UID").text)
        return {
            "type": "unlock",
            "unit": _unit_name(uid),
            "unit_id": uid,
        }

    if xsi_type == "PAD_UpgradeUnit":
        uidx = int(el.find("UIDX").text)
        return {
            "type": "upgrade",
            "unit_index": uidx,
        }

    if xsi_type == "PAD_UpgradeTechnology":
        uid = int(el.find("UID").text)
        tech_id = int(el.find("TechID").text)
        return {
            "type": "tech",
            "unit": _unit_name(uid),
            "tech": TECH_LOOKUP.get(tech_id, f"unknown_tech({tech_id})"),
            "tech_id": tech_id,
        }

    if xsi_type == "PAD_ReleaseContraption":
        cid = int(el.find("ContraptionID").text)
        return {
            "type": "place_contraption",
            "name": CONTRAPTION_LOOKUP.get(cid, f"unknown({cid})"),
            "contraption_id": cid,
            "position": _xy(el.find("Position")),
        }

    if xsi_type == "PAD_ActiveEnergyTowerSkill":
        sid_el = el.find("SkillID")
        sid = int(sid_el.text) if sid_el is not None else None
        return {
            "type": "command_tower",
            "skill": COMMAND_TOWER_SKILLS.get(sid, f"unknown({sid})") if sid is not None else None,
        }

    if xsi_type == "PAD_ActiveBlueprint":
        sid = int(el.find("ID").text)
        return {
            "type": "research_tower",
            "skill": RESEARCH_TOWER_SKILLS.get(sid, f"unknown({sid})"),
        }

    if xsi_type == "PAD_ReleaseCommanderSkill":
        skill_idx = int(el.find("SkillIndex").text)
        skill_info = skills.get(skill_idx, {})
        positions_el = el.findall("Positions/MapVector")
        unit_index_el = el.find("UnitIndex")
        return {
            "type": "use_skill",
            "skill": skill_info.get("name", f"unknown_skill(index={skill_idx})"),
            "skill_index": skill_idx,
            "positions": [_xy(p) for p in positions_el],
            "unit_index": int(unit_index_el.text) if unit_index_el is not None else None,
        }

    if xsi_type == "PAD_ChooseReinforceItem":
        ident = int(el.find("ID").text)
        if round_number in reinforce_rounds:
            return {
                "type": "unit_drop_select",
                "drop_id": ident,
            }
        return {
            "type": "card_select",
            "card": CARD_LOOKUP.get(ident, f"unknown_card({ident})"),
            "card_id": ident,
        }

    return None


def _parse_fight_result(snap_el, player_names: list[str]) -> dict | None:
    fight_el = snap_el.find("lastFightResult")
    if fight_el is None:
        return None
    result = {}
    reports = fight_el.findall("Reports/FightReport")
    for report, name in zip(reports, player_names):
        result[name] = {
            "crystals_destroyed": int(report.find("DestroyedCrystalCount").text),
            "units_survived": int(report.find("AliveMechCount").text),
            "score": int(report.find("Score").text),
        }
    return result or None


def replay_to_dict(path: Path) -> dict:
    xml_str = extract_xml(path)
    root = ET.fromstring(xml_str)

    version = root.find("Version").text

    player_elements = root.findall("playerRecords/PlayerRecord")
    player_names = [pr.find("name").text for pr in player_elements]

    battle_info = root.find("BattleInfo")
    match_mode_el = battle_info.find("MatchMode") if battle_info is not None else None
    match_mode = match_mode_el.text if match_mode_el is not None else None

    # In VS_2_2 the `ad` field is always 0, so split by position in playerRecords.
    # In 1v1 (VS_1_1) there are only 2 players and each is a team of one.
    n = len(player_names)
    half = n // 2
    teams = [player_names[:half], player_names[half:]] if n > 1 else [player_names]

    reinforce_rounds = [int(el.text) for el in root.findall("reinforceItems/int")]

    snapshots = {
        int(s.find("round").text): s
        for s in root.findall("matchDatas/MatchSnapshotData")
    }

    all_rounds = sorted({
        int(rr.find("round").text)
        for pr in player_elements
        for rr in pr.findall("playerRoundRecords/PlayerRoundRecord")
    })

    rounds = []
    for rnd in all_rounds:
        snap = snapshots.get(rnd)
        fight_result = _parse_fight_result(snap, player_names) if snap else None

        players_data = {}
        for pr in player_elements:
            name = pr.find("name").text
            rr_el = next(
                (r for r in pr.findall("playerRoundRecords/PlayerRoundRecord")
                 if int(r.find("round").text) == rnd),
                None,
            )
            if rr_el is None:
                continue

            pd = rr_el.find("playerData")
            skills = _parse_commander_skills(pd)
            pre_result_el = pd.find("preRoundFightResult")
            supply_el = pd.find("supply") or pd.find("Supply") or pd.find("energy") or pd.find("Energy")
            units = _parse_units(pd)

            players_data[name] = {
                "hp": int(pd.find("reactorCore").text),
                "supply": int(supply_el.text) if supply_el is not None else None,
                "army_value": sum(u["sell_supply"] for u in units),
                "fight_outcome": pre_result_el.text if pre_result_el is not None else None,
                "officers": _parse_officers(pd),
                "commander_skills": list(skills.values()),
                "units": units,
                "active_techs": _parse_active_techs(pd),
                "contraptions": _parse_contraptions(pd),
                "constructions": _parse_constructions(pd),
                "shop": _parse_shop(pd),
                "actions": _parse_actions(rr_el, rnd, reinforce_rounds, skills),
            }

        rounds.append({
            "round": rnd,
            "fight_result": fight_result,
            "players": players_data,
        })

    return {
        "metadata": {
            "version": version,
            "match_mode": match_mode,
        },
        "teams": teams,
        "rounds": rounds,
        "last_round": max(all_rounds),
    }


def replay_to_json(path: Path, indent: int = 2) -> str:
    return json.dumps(replay_to_dict(path), ensure_ascii=False, indent=indent)


def dump_player_data_xml_fields(path: Path) -> None:
    """Debug helper: prints all XML child tags in playerData for the first round of each player."""
    xml_str = extract_xml(path)
    root = ET.fromstring(xml_str)
    for pr in root.findall("playerRecords/PlayerRecord"):
        name = pr.find("name").text
        rr = pr.findall("playerRoundRecords/PlayerRoundRecord")
        if not rr:
            continue
        pd = rr[0].find("playerData")
        print(f"\n=== playerData XML fields for '{name}' ===")
        for child in pd:
            val = child.text.strip() if child.text and child.text.strip() else f"[{len(list(child))} children]"
            print(f"  <{child.tag}> = {val[:80]}")
