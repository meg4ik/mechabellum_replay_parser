import argparse
from pathlib import Path

from prettytable import PrettyTable

from . import parse_battle_record
from . import battle_record_to_string
from .transformer import replay_to_dict
from .watcher import watch, REPLAY_DIR


def show_battle_record(args):
    battle_record = parse_battle_record(Path(args.file).absolute())
    table = battle_record_to_string(battle_record)
    print(table)


def show_tech(args):
    battle_record = parse_battle_record(Path(args.file).absolute())
    for player in battle_record.player_records:
        print(player.name)
        table = PrettyTable()
        table.align = "l"
        table.field_names = ["Unit", "Techs"]
        for unit, techs in player.tech_choices.items():
            table.add_row([unit, "\n".join(techs)])
            table.add_divider()
        print(table)
        print()


def show_units(args):
    from .native_ui.display import CoachWindow

    path = Path(args.file).absolute()
    data = replay_to_dict(path)

    last_round = data["last_round"]
    target_round = args.round if args.round is not None else last_round

    round_data = next((r for r in data["rounds"] if r["round"] == target_round), None)
    if round_data is None:
        available = [r["round"] for r in data["rounds"]]
        print(f"Round {target_round} not found. Available rounds: {available}")
        return

    players = round_data["players"]
    if not players:
        print(f"No player data for round {target_round}.")
        return

    # Pick player: explicit --player, else first non-Bot, else first
    player_name = args.player
    if player_name:
        if player_name not in players:
            print(f"Player '{player_name}' not found. Available: {list(players.keys())}")
            return
    else:
        player_name = next((n for n in players if "bot" not in n.lower()), list(players.keys())[0])

    pdata = players[player_name]
    units = pdata["units"]
    constructions = list(pdata["constructions"])

    # Detect which Y-side this player is on
    positioned_ys = [
        u["position"]["y"]
        for u in units
        if u.get("position") and u["position"].get("y") is not None
    ]
    y_sign = -1 if (not positioned_ys or sum(positioned_ys) / len(positioned_ys) < 0) else 1

    # Inject fixed utility towers (not stored in replay)
    constructions += [
        {"type": "Command Tower",  "position": {"x": -140, "y": y_sign * 170}},
        {"type": "Research Tower", "position": {"x":  140, "y": y_sign * 170}},
    ]

    # Gather opponent data
    opponent_name = next((n for n in players if n != player_name), None)
    opponent_units: list[dict] = []
    opponent_constructions: list[dict] = []
    if opponent_name:
        odata = players[opponent_name]
        opponent_units = odata["units"]
        opponent_constructions = list(odata["constructions"])
        opponent_constructions += [
            {"type": "Command Tower",  "position": {"x": -140, "y": -y_sign * 170}},
            {"type": "Research Tower", "position": {"x":  140, "y": -y_sign * 170}},
        ]

    # Console summary
    print(f"v{data['metadata']['version']} | {data['metadata']['match_mode']} | round {target_round} | player: {player_name}")
    print(f"units: {len(units)}  constructions: {len(constructions)}")
    if opponent_name:
        print(f"opponent: {opponent_name} | units: {len(opponent_units)}  constructions: {len(opponent_constructions)}")

    # Y-coordinate stats across ALL rounds for this player (helps calibrate boundaries)
    all_ys = []
    all_xs = []
    for r in data["rounds"]:
        for u in r["players"].get(player_name, {}).get("units", []):
            pos = u.get("position") or {}
            if pos.get("y") is not None:
                all_ys.append(pos["y"])
            if pos.get("x") is not None:
                all_xs.append(pos["x"])
    if all_ys:
        print(f"\nCoord range across all rounds:")
        print(f"  x: {min(all_xs)} … {max(all_xs)}")
        print(f"  y: {min(all_ys)} … {max(all_ys)}  (front=closer to 0, back=farther)")

    unknown = [u for u in units if u["name"].startswith("unknown(")]
    if unknown:
        print("\nUnknown unit IDs (add to UNIT_LOOKUP in __init__.py):")
        for u in unknown:
            pos = u.get("position") or {}
            print(f"  {u['unit_id']}: \"???\"  # x={pos.get('x','?')} y={pos.get('y','?')}")

    # Detailed position table for current round
    if units:
        sorted_units = sorted(units, key=lambda u: (u.get("name", ""), u.get("position", {}).get("x", 0)))
        print(f"\nUnits  (round {target_round}):")
        print(f"  {'name':<22} {'x':>6}  {'y':>6}")
        print(f"  {'-'*22} {'-'*6}  {'-'*6}")
        for u in sorted_units:
            pos = u.get("position") or {}
            x, y = pos.get("x", "?"), pos.get("y", "?")
            print(f"  {u.get('name', '?'):<22} {str(x):>6}  {str(y):>6}")

    if constructions:
        print(f"\nConstructions  (round {target_round}):")
        print(f"  {'type':<25} {'x':>6}  {'y':>6}")
        print(f"  {'-'*25} {'-'*6}  {'-'*6}")
        for c in constructions:
            pos = c.get("position") or {}
            x, y = pos.get("x", "?"), pos.get("y", "?")
            print(f"  {c.get('type', '?'):<25} {str(x):>6}  {str(y):>6}")

    if not units and not constructions:
        print("Nothing to display (no units or constructions in this round).")
        return

    print("\nOpening board visualization…")
    window = CoachWindow()
    window.show_result(
        round_num=target_round,
        player_name=player_name,
        summary=f"{path.name}  —  раунд {target_round}",
        coach_text="",
        current_units=units,
        placement=[],
        constructions=constructions,
        opponent_units=opponent_units,
        opponent_constructions=opponent_constructions,
    )
    window.mainloop()


def start_watch(args):
    import asyncio

    replay_dir = Path(args.dir) if args.dir else REPLAY_DIR
    asyncio.run(watch(replay_dir))


def export_dataset(args):
    import asyncio

    from .db.service import create_persistence_service
    from .learning.dataset_export import export_dataset as _export

    svc = create_persistence_service()
    if not svc.enabled:
        print("Database not available. Set DATABASE_URL or unset DEBUG_NO_DB.")
        return

    from .db.session import get_session_factory

    output = Path(args.output)
    count = asyncio.run(_export(get_session_factory(), output, format=args.format))
    print(f"Exported {count} rows to {output}")


def ingest_knowledge(args):
    from .knowledge.parser import parse_knowledge_file

    path = Path(args.file).absolute()
    if not path.exists():
        print(f"File not found: {path}")
        return
    chunks = parse_knowledge_file(path)
    print(f"Parsed {len(chunks)} knowledge chunks from {path.name}")
    by_topic: dict[str, int] = {}
    for c in chunks:
        by_topic[c.topic] = by_topic.get(c.topic, 0) + 1
    for topic, count in sorted(by_topic.items()):
        print(f"  {topic}: {count} chunks")
    always = [
        c
        for c in chunks
        if c.topic in {"base_rules", "deployment_rules", "towers"} and c.priority >= 2
    ]
    print(
        f"Always-include chunks (base_rules/deployment_rules/towers, priority>=2): {len(always)}"
    )


def main():
    parser = argparse.ArgumentParser(description="Mechabellum replay file parser")
    subparsers = parser.add_subparsers(dest="command")

    battle_parser = subparsers.add_parser(
        "battle", help="Parse a Mechabellum replay file (.grbr)"
    )
    battle_parser.add_argument(
        "file", help="Path to the Mechabellum replay file (.grbr)"
    )
    battle_parser.set_defaults(func=show_battle_record)

    units_parser = subparsers.add_parser(
        "units", help="Visualize units and constructions from a replay in a Tkinter window."
    )
    units_parser.add_argument("file", help="Path to the Mechabellum replay file (.grbr)")
    units_parser.add_argument("--round", type=int, default=None, help="Round number to display (default: last round)")
    units_parser.add_argument("--player", default=None, help="Player name to display (default: first non-bot player)")
    units_parser.set_defaults(func=show_units)

    tech_parser = subparsers.add_parser(
        "tech", help="Show tech information of both players in a replay file."
    )
    tech_parser.add_argument("file", help="Path to the Mechabellum replay file (.grbr)")
    tech_parser.set_defaults(func=show_tech)

    watch_parser = subparsers.add_parser(
        "watch", help="Monitor replay folder and auto-process new replays."
    )
    watch_parser.add_argument(
        "--dir", help=f"Replay folder to monitor (default: {REPLAY_DIR})", default=None
    )
    watch_parser.set_defaults(func=start_watch)

    knowledge_parser = subparsers.add_parser(
        "knowledge", help="Knowledge base management commands."
    )
    k_subparsers = knowledge_parser.add_subparsers(dest="k_command")
    ingest_parser = k_subparsers.add_parser(
        "ingest", help="Parse a knowledge markdown file and report chunk statistics."
    )
    ingest_parser.add_argument("file", help="Path to the knowledge markdown file")
    ingest_parser.set_defaults(func=ingest_knowledge)
    knowledge_parser.set_defaults(func=lambda a: knowledge_parser.print_help())

    learning_parser = subparsers.add_parser(
        "learning", help="Dataset export and feedback learning commands."
    )
    l_subparsers = learning_parser.add_subparsers(dest="l_command")
    export_parser = l_subparsers.add_parser(
        "export", help="Export recommendation dataset as JSONL for training."
    )
    export_parser.add_argument(
        "--output",
        default="data/recommendation_dataset.jsonl",
        help="Output file path (default: data/recommendation_dataset.jsonl)",
    )
    export_parser.add_argument(
        "--format", default="jsonl", choices=["jsonl"], help="Export format"
    )
    export_parser.set_defaults(func=export_dataset)
    learning_parser.set_defaults(func=lambda a: learning_parser.print_help())

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
