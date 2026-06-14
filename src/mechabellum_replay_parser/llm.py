import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def _build_system_prompt(player_name: str) -> str:
    return f"""You are an expert Mechabellum coach. Your job is to give {player_name} one single optimal action plan for the current round — no alternatives, no "you could also", no hedging.

## Game context
Mechabellum is a 2v2 auto-battler. Each round has a preparation phase (buy, upgrade, position units) followed by an automatic battle. The board is a grid; unit positions are x/y coordinates. Players share a team area and coordinate their army composition.

## Replay data format
You will receive a JSON with:
- `teams`: two teams of player names
- `rounds`: full history — each round contains each player's HP, units (with positions), active techs, commander skills, contraptions, and every action they took (buys, upgrades, moves, techs, skill uses)
- `last_round`: the round number that was just saved

## Critical timing rule
The replay is saved at the VERY START of a round, BEFORE the player has done anything. So `last_round` is the round {player_name} is currently playing RIGHT NOW, not a completed round. The actions list for `last_round` will be empty or minimal — that is expected.

## Your output format
Give exactly one plan. Structure it as:

**Round [N] plan for {player_name}**

**Buy / Upgrade**
Numbered list. Each item: `1. [action] — [reason in 5 words max]`

**Positioning**
Numbered list. Each item: `1. [unit name] → (x, y)` Use the coordinate system from the replay data. Be precise.

**Tech / Skills**
Numbered list. Which tech to research or commander skill to activate, if any.

**Priority order**
Numbered list. If supply is limited, rank actions by importance: 1 = do first.

Do not explain the opponent's strategy. Do not list what the opponent might do. Do not offer alternatives. Give the plan and stop.
"""


def analyze(parsed: dict) -> None:
    player_name = os.getenv("PLAYER_NAME", "")
    if not player_name:
        raise ValueError("PLAYER_NAME not set in .env")

    game_json = json.dumps(parsed, ensure_ascii=False)

    last_round = parsed.get("last_round", "?")
    teams = parsed.get("teams", [])
    print(f"\n[AI] Анализ игры (текущий раунд: {last_round}, команды: {teams})")
    print(f"[AI] Советую игроку: {player_name}")
    print("[AI] Ожидаем ответ от OpenAI...\n")
    print("-" * 60)

    user_message = (
        f"Here is the Mechabellum replay data in JSON format:\n\n"
        f"```json\n{game_json}\n```\n\n"
        f"The replay was saved at the start of round {last_round} before {player_name} took any actions. "
        f"Give {player_name} the exact plan for round {last_round}."
    )

    client = _get_client()
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _build_system_prompt(player_name)},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)

    print("\n" + "-" * 60)
