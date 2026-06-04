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


def select_players(players: list[dict[str, Any]], seat: int | None) -> list[dict[str, Any]]:
    if seat is not None:
        for player in players:
            if player.get("seat_id") == seat:
                return [player]
        raise ValueError(f"players.json 里没有 {seat}号 玩家")

    selected: list[dict[str, Any]] = []
    seen_vendors = set()
    for player in players:
        vendor_key = (player.get("provider", "openai"), player.get("base_url") or "")
        if vendor_key in seen_vendors:
            continue
        seen_vendors.add(vendor_key)
        selected.append(player)
    return selected


def short_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\n", " ")
    return text[:300] if text else type(exc).__name__


async def ping_player(player: dict[str, Any], timeout: float, max_tokens: int) -> bool:
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
                max_tokens=max_tokens,
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
        if choice.finish_reason == "length":
            print("       建议：这是 thinking 模型常见现象，增加 --max-tokens 后重试。")
        return False
    print(f"[OK] elapsed={elapsed:.1f}s finish_reason={choice.finish_reason} content={content[:80]}")
    return True


async def ping_players(players: list[dict[str, Any]], timeout: float, max_tokens: int) -> bool:
    print(f"将按厂商/base_url 去重测试 {len(players)} 个配置。不会打印 API Key。")
    ok = True
    for player in players:
        ok = await ping_player(player, timeout, max_tokens) and ok
    return ok


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="快速测试模型厂商是否能连通")
    parser.add_argument("--seat", type=int, default=None, help="只测试指定座位；默认按 provider/base_url 去重，每家测一次")
    parser.add_argument("--timeout", type=float, default=20.0, help="请求超时秒数，默认 20")
    parser.add_argument("--max-tokens", type=int, default=128, help="最大输出 token，默认 128；thinking 模型不要设太低")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    try:
        players = select_players(load_players(), args.seat)
        ok = asyncio.run(ping_players(players, args.timeout, args.max_tokens))
    except Exception as exc:
        print(f"[FAIL] 无法开始 ping：{short_error(exc)}")
        raise SystemExit(2)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
