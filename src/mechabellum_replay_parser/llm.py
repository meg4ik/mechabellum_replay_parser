import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

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
    return f"""You are an expert Mechabellum coach analyzing a game replay.

Mechabellum is a strategy auto-battler where two teams of two players compete.
Each round, players spend supply to buy, upgrade, and position units. Rounds alternate
between the preparation phase (buying/moving units) and the fight phase (automatic battle).
Players start with reactor cores (HP) and lose them when enemy units deal damage.

Your task:
- Analyze the full game history provided in JSON format.
- Identify patterns: what units each team built, what techs they researched, how they
  positioned their units, what synergies or counters were used.
- Focus especially on the last recorded round to understand the current board state.
- Advise the player named "{player_name}" on the optimal strategy for the NEXT round
  (the round after the last one in the replay).

Be specific: name concrete units to buy, upgrades to prioritize, positioning advice
(based on x/y coordinates where relevant), and counter-strategies against the opponent.
"""


def analyze(parsed: dict) -> None:
    player_name = os.getenv("PLAYER_NAME", "")
    if not player_name:
        raise ValueError("PLAYER_NAME not set in .env")

    game_json = json.dumps(parsed, ensure_ascii=False)

    last_round = parsed.get("last_round", "?")
    teams = parsed.get("teams", [])
    print(f"\n[AI] Анализ игры (раундов: {last_round}, команды: {teams})")
    print(f"[AI] Советую игроку: {player_name}")
    print("[AI] Ожидаем ответ от OpenAI...\n")
    print("-" * 60)

    user_message = (
        f"Here is the full Mechabellum game replay data in JSON format:\n\n"
        f"```json\n{game_json}\n```\n\n"
        f"Please analyze the entire game history and advise {player_name} "
        f"on what to do in round {last_round + 1 if isinstance(last_round, int) else 'next'}."
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
