import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_GAME_KNOWLEDGE_PATH = Path(__file__).parent.parent.parent / "game_knowledge.md"
_game_knowledge: str | None = None


def _get_game_knowledge() -> str:
    global _game_knowledge
    if _game_knowledge is None:
        if _GAME_KNOWLEDGE_PATH.exists():
            _game_knowledge = _GAME_KNOWLEDGE_PATH.read_text(encoding="utf-8")
        else:
            _game_knowledge = ""
    return _game_knowledge


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def _build_system_prompt(player_name: str, last_round: int | str) -> str:
    knowledge = _get_game_knowledge()
    knowledge_block = f"\n\n## Mechabellum game knowledge\n{knowledge}" if knowledge else ""
    return f"""You are an expert Mechabellum coach. Your job is to give {player_name} one single optimal action plan for the current round — no alternatives, no "you could also", no hedging.{knowledge_block}

## Game context
Mechabellum is a 2v2 auto-battler. Each round has a preparation phase (buy, upgrade, position units) followed by an automatic battle. The board is a grid; unit positions are x/y coordinates. Players share a team area and coordinate their army composition.

## Replay data format
You will receive a JSON with:
- `teams`: two teams of player names
- `rounds`: full history — each round contains each player's HP, units (with positions), active techs, commander skills, contraptions, constructions, and every action they took (buys, upgrades, moves, techs, skill uses)
- `last_round`: the round number that was just saved

## HP, crystals, and tower destruction
- `players[name].hp` = **reactor crystals remaining**. A player starts with several crystals (typically 3–6 depending on mode). When all crystals reach 0, that team loses the game. This is the primary win/loss condition.
- `fight_result[name].crystals_destroyed` = how many crystals were destroyed in the previous battle. Losing crystals is urgent — the team is closer to elimination.
- `players[name].constructions` = the player's buildings on the field: Supply Tower, Command Tower, Research Tower. Each has a position (x, y).
- **Tower destruction consequence**: when a building (Supply Tower / Command Tower / Research Tower) is destroyed during battle, the entire owning team's army suffers a temporary stat debuff (reduced ATK and HP) for that round. Losing multiple towers in one round stacks debuffs and can cause a cascade loss.
- **Strategic implications**: enemy flanks or fast units that reach buildings force tower debuffs even if the main battle is winning. Protecting your own towers while threatening the opponent's is a key strategic lever — especially in early rounds when armies are small and the debuff is proportionally more impactful.

## Critical timing rule
The replay is saved at the VERY START of a round, BEFORE the player has done anything. So `last_round` is the round {player_name} is currently playing RIGHT NOW, not a completed round. The actions list for `last_round` will be empty or minimal — that is expected.

## Coordinate system
{player_name}'s deployment zone: x from -285 to +285, y from -295 to -45.
- x = 0 is the horizontal center of the zone.
- y = -45 is the front line (closest to the enemy), y = -295 is the back.
- Left flank: x around -285. Right flank: x around +285. Center: x near 0.

## Unit movement rules
{"## ROUND 1 — FREE PLACEMENT" if last_round == 1 else "## Movement constraint"}
{"This is round 1. Before the first battle, ALL starting units can be placed freely anywhere in the deployment zone. There are no fixed units. Every single unit in the replay data for this round MUST be given an explicit (x, y) coordinate in your plan. Use action `move` for all of them in the PLACEMENT block — none should be `keep`." if last_round == 1 else f"Deployed units are normally fixed after placement. Only newly bought units (action `new`) or units with a valid reposition mechanic (mobile beacon, redeployment card, etc.) can be moved. Do NOT use action `move` for existing units unless {player_name} has an explicit mechanic that allows it. Use `keep` with the current coordinates for all other existing units."}

## Your output format
Give exactly one plan. Structure it as:

**Round [N] plan for {player_name}**

**Buy / Upgrade**
Numbered list. Each item: `1. [action] — [reason in 5 words max]`

**Positioning**
Numbered list. Each item must include explicit coordinates:
`1. [unit name] → (x, y)  — [what it does there]`
Every unit that needs placing or moving MUST have a coordinate. No exceptions.

**Tech / Skills**
Numbered list. Which tech to research or commander skill to activate, if any.

**Priority order**
Numbered list. If supply is limited, rank actions by importance: 1 = do first.

Do not explain the opponent's strategy. Do not list what the opponent might do. Do not offer alternatives. Give the plan and stop.

## REQUIRED: placement block
After the plan, output this exact block with ALL units {player_name} should have on the board after this round (both existing and newly placed). No exceptions — every recommended unit must appear here.

PLACEMENT:
```json
[
  {{"unit": "<unit_name>", "x": <int>, "y": <int>, "action": "<keep|move|new>"}},
  ...
]
```

- `keep` — unit already on the board, staying at its EXACT current position from replay data (copy x/y verbatim)
- `move` — unit already on the board, repositioned to a new (x, y)
- `new` — unit you recommended buying in **Buy / Upgrade**; MUST use `"new"`, NEVER `"keep"` or `"move"`
- RULE: every unit listed in Buy / Upgrade MUST appear in PLACEMENT with `"action": "new"`. If it is absent or marked `"keep"`, the plan is invalid.
- x and y must be integers within the zone bounds (-285..285 for x, -295..-45 for y)
"""


_PLACEMENT_RE = re.compile(r"PLACEMENT:\s*```json\s*(\[.*?\])\s*```", re.DOTALL)


def parse_placement(text: str) -> list[dict] | None:
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
        # clamp to zone bounds
        entry["x"] = max(-285, min(285, entry["x"]))
        entry["y"] = max(-295, min(-45, entry["y"]))
        result.append(entry)
    return result or None


def analyze(parsed: dict, supply: int | None = None) -> list[dict] | None:
    player_name = os.getenv("PLAYER_NAME", "")
    if not player_name:
        raise ValueError("PLAYER_NAME not set in .env")

    def _strip_actions(rounds: list[dict]) -> list[dict]:
        result = []
        for rnd in rounds:
            stripped_players = {
                name: {k: v for k, v in pdata.items() if k != "actions"}
                for name, pdata in rnd.get("players", {}).items()
            }
            result.append({**rnd, "players": stripped_players})
        return result

    trimmed = {**parsed, "rounds": _strip_actions(parsed["rounds"][-3:])}
    game_json = json.dumps(trimmed, ensure_ascii=False)

    last_round = parsed.get("last_round", "?")
    teams = parsed.get("teams", [])
    print(f"\n[AI] Анализ игры (текущий раунд: {last_round}, команды: {teams})")
    print(f"[AI] Советую игроку: {player_name}")
    print("[AI] Ожидаем ответ от OpenAI...\n")
    print("-" * 60)

    supply_line = (
        f"\n\n{player_name}'s current supply this round: **{supply}**. "
        f"Your plan MUST NOT exceed this budget."
        if supply is not None
        else ""
    )
    user_message = (
        f"Here is the Mechabellum replay data in JSON format:\n\n"
        f"```json\n{game_json}\n```\n\n"
        f"The replay was saved at the start of round {last_round} before {player_name} took any actions. "
        f"Give {player_name} the exact plan for round {last_round}.{supply_line}"
    )

    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    client = _get_client()
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _build_system_prompt(player_name, last_round)},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    chunks: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            chunks.append(delta.content)

    print("\n" + "-" * 60)

    placement = parse_placement("".join(chunks))
    if placement is None:
        print("[!] PLACEMENT блок не найден или невалиден")
    else:
        print(f"[✓] Размещение распарсено: {len(placement)} юнитов")
    return placement
