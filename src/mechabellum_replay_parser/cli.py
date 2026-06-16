import argparse
from pathlib import Path

from prettytable import PrettyTable

from . import parse_battle_record
from . import battle_record_to_string
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
