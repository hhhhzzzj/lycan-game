"""Print a sanitized raw response for one configured player.

Usage:
  python scripts/debug_llm_response.py 3
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def main():
    from openai import AsyncOpenAI

    seat_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    cfg_path = Path(__file__).parent.parent / "backend" / "config" / "players.json"
    players = json.load(open(cfg_path, "r", encoding="utf-8"))["players"]
    player = next(p for p in players if p["seat_id"] == seat_id)

    client = AsyncOpenAI(api_key=player["api_key"], base_url=player["base_url"])
    resp = await client.chat.completions.create(
        model=player["model_name"],
        messages=[
            {"role": "system", "content": "你必须输出合法 JSON。"},
            {
                "role": "user",
                "content": (
                    '请只回答：{"thinking":"简短思考","action":"你好，我会正常发言","target_seat":null}'
                ),
            },
        ],
        temperature=0.3,
        max_tokens=512,
    )
    data = resp.model_dump(mode="json")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
