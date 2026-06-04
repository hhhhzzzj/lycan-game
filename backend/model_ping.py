"""Fast one-shot connectivity check for a configured model."""
import argparse
import asyncio
import json
import time
from typing import Any

from config_wizard import validate_players_config
from runtime_paths import config_dir


def load_players() -> list[dict[str, Any]]:
    path = config_dir() / "players.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到配置文件：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_players_config(data)
    if errors:
        raise ValueError("players.json 配置未完成：" + "；".join(errors))
    return data["players"]


def select_player(players: list[dict[str, Any]], seat: int | None) -> dict[str, Any]:
    if seat is not None:
        for player in players:
            if player.get("seat_id") == seat:
                return player
        raise ValueError(f"players.json 里没有 {seat}号 玩家")
    return players[0]


def short_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\n", " ")
    return text[:300] if text else type(exc).__name__


async def ping_player(player: dict[str, Any], timeout: float) -> bool:
    if player.get("provider", "openai") != "openai":
        raise ValueError("轻量 ping 当前只支持 provider=openai 的 OpenAI-compatible 接口")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=player["api_key"],
        base_url=player.get("base_url"),
        timeout=timeout,
        max_retries=0,
    )
    print(
        f"PING {player['seat_id']}号 {player['player_name']} | "
        f"model={player['model_name']} | base_url={player.get('base_url')}",
        flush=True,
    )
    started = time.monotonic()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=player["model_name"],
                messages=[{"role": "user", "content": "请只回复 OK"}],
                temperature=0,
                max_tokens=8,
            ),
            timeout=timeout + 2,
        )
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {short_error(exc)}")
        return False

    elapsed = time.monotonic() - started
    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    if not content:
        print(f"[FAIL] HTTP 成功，但 content 为空。finish_reason={choice.finish_reason} elapsed={elapsed:.1f}s")
        return False
    print(f"[OK] elapsed={elapsed:.1f}s finish_reason={choice.finish_reason} content={content[:80]}")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="快速测试指定座位模型是否能连通")
    parser.add_argument("--seat", type=int, default=None, help="指定座位；默认测试 1 号")
    parser.add_argument("--timeout", type=float, default=20.0, help="请求超时秒数，默认 20")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    try:
        player = select_player(load_players(), args.seat)
        ok = asyncio.run(ping_player(player, args.timeout))
    except Exception as exc:
        print(f"[FAIL] 无法开始 ping：{short_error(exc)}")
        raise SystemExit(2)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
