"""Provider/model readiness checks for configured players."""
import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_wizard import validate_players_config
from game.llm.adapters import create_adapter
from runtime_paths import config_dir


@dataclass
class CheckResult:
    ok: bool
    seat_id: int
    player_name: str
    model_name: str
    base_url: str
    stage: str
    message: str
    suggestion: str = ""


CHECKS = [
    (
        "basic_json",
        (
            "你是 API 连通性测试助手。必须只输出合法 JSON，"
            '格式为 {"thinking":"简短思考","action":"可见回复","target_seat":null}。'
        ),
        "请回复连接正常。action 必须是非空字符串。",
        False,
    ),
    (
        "werewolf_context",
        (
            "你正在玩一局 6 人狼人杀。必须只输出合法 JSON，不要拒答，"
            '格式为 {"thinking":"简短思考","action":"你的自然发言","target_seat":null}。'
        ),
        "你是 1 号玩家，请用一句自然发言说明你会听大家发言再判断。action 必须非空。",
        False,
    ),
    (
        "target_seat",
        (
            "你正在玩一局 6 人狼人杀。必须只输出合法 JSON，"
            '格式为 {"thinking":"简短思考","action":"我选择投票给X号","target_seat":2}。'
        ),
        '请从 2号、3号 中选择一个投票目标。action 必须说明选择，target_seat 必须填 2 或 3。',
        True,
    ),
]


def load_players() -> list[dict[str, Any]]:
    path = config_dir() / "players.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到配置文件：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_players_config(data)
    if errors:
        raise ValueError("players.json 配置未完成：" + "；".join(errors))
    return data["players"]


def _short_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\n", " ")
    return text[:240] if text else type(exc).__name__


def _suggestion(stage: str, message: str, base_url: str) -> str:
    lower = message.lower()
    if "401" in lower or "unauthorized" in lower or "invalid api key" in lower:
        return "检查 API Key 是否填错、过期，或是否属于这个厂商。"
    if "404" in lower or "model" in lower and "not" in lower:
        return "检查 model_name 是否是该厂商真实支持的模型名。"
    if "429" in lower or "too many requests" in lower or "limitation" in lower:
        return "触发限流，稍等后重试；如果频繁出现，需要加大限流间隔。"
    if "timeout" in lower or "超时" in lower:
        return "网络或模型响应过慢，可稍后重试，或换更快的模型。"
    if stage == "empty_action":
        if "xiaomimimo" in base_url or "mimo" in base_url:
            return "模型可能只输出了 reasoning 没有 content；建议换非 reasoning 模型或继续加大 max_tokens。"
        return "模型返回了空发言；建议换模型，或降低模型推理强度。"
    if stage == "invalid_target":
        return "模型不稳定遵守 target_seat；游戏可继续但投票/刀人可能需要兜底。"
    return "请把该厂商的 base_url、model_name 与 OpenAI-compatible 文档再核对一遍。"


def _print_progress(player: dict[str, Any], stage: str):
    print(
        f"正在检测: {player['seat_id']}号 {player['player_name']} | "
        f"{player['model_name']} | {stage}",
        flush=True,
    )


async def check_player(player: dict[str, Any], timeout: float) -> list[CheckResult]:
    adapter = create_adapter(
        provider=player.get("provider", "openai"),
        model=player["model_name"],
        api_key=player["api_key"],
        base_url=player.get("base_url"),
    )
    results: list[CheckResult] = []
    for stage, system_prompt, user_prompt, require_target in CHECKS:
        _print_progress(player, stage)
        try:
            resp = await asyncio.wait_for(adapter.call(system_prompt, user_prompt), timeout=timeout)
        except Exception as exc:
            message = _short_error(exc)
            results.append(CheckResult(
                ok=False,
                seat_id=player["seat_id"],
                player_name=player["player_name"],
                model_name=player["model_name"],
                base_url=player.get("base_url") or "",
                stage=stage,
                message=message,
                suggestion=_suggestion(stage, message, player.get("base_url") or ""),
            ))
            continue

        action = (resp.action or "").strip()
        thinking = (resp.thinking or "").strip()
        if action == "弃票" and ("API 错误" in thinking or "API 超时" in thinking):
            message = thinking
            results.append(CheckResult(
                ok=False,
                seat_id=player["seat_id"],
                player_name=player["player_name"],
                model_name=player["model_name"],
                base_url=player.get("base_url") or "",
                stage=stage,
                message=message,
                suggestion=_suggestion(stage, message, player.get("base_url") or ""),
            ))
            continue

        if not action:
            message = "HTTP 成功，但模型没有返回可见发言 action。"
            results.append(CheckResult(
                ok=False,
                seat_id=player["seat_id"],
                player_name=player["player_name"],
                model_name=player["model_name"],
                base_url=player.get("base_url") or "",
                stage="empty_action",
                message=message,
                suggestion=_suggestion("empty_action", message, player.get("base_url") or ""),
            ))
            continue

        if require_target and resp.target_seat not in {2, 3}:
            message = f"模型返回了 action，但 target_seat 不合法：{resp.target_seat}"
            results.append(CheckResult(
                ok=False,
                seat_id=player["seat_id"],
                player_name=player["player_name"],
                model_name=player["model_name"],
                base_url=player.get("base_url") or "",
                stage="invalid_target",
                message=message,
                suggestion=_suggestion("invalid_target", message, player.get("base_url") or ""),
            ))
            continue

        results.append(CheckResult(
            ok=True,
            seat_id=player["seat_id"],
            player_name=player["player_name"],
            model_name=player["model_name"],
            base_url=player.get("base_url") or "",
            stage=stage,
            message=action[:80],
        ))
    return results


def _filter_players(
    players: list[dict[str, Any]],
    seats: set[int],
    base_url_contains: str,
    model_contains: str,
) -> list[dict[str, Any]]:
    selected = []
    for player in players:
        if seats and player.get("seat_id") not in seats:
            continue
        if base_url_contains and base_url_contains.lower() not in (player.get("base_url") or "").lower():
            continue
        if model_contains and model_contains.lower() not in (player.get("model_name") or "").lower():
            continue
        selected.append(player)
    return selected


def _representative_players(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    selected = []
    for player in players:
        key = (player.get("provider"), player.get("base_url"), player.get("model_name"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(player)
    return selected


def print_results(results: list[CheckResult]) -> bool:
    ok = True
    for result in results:
        mark = "OK" if result.ok else "FAIL"
        print(f"[{mark}] {result.seat_id}号 {result.player_name} | {result.model_name} | {result.stage}")
        print(f"      {result.message}")
        if result.suggestion:
            print(f"      建议：{result.suggestion}")
        ok = ok and result.ok
    print("=" * 60)
    if ok:
        print("模型自检全部通过，可以开局。")
    else:
        print("模型自检未全部通过。帮忙运行的 AI 应先按上面的建议修正配置，再启动游戏。")
    return ok


async def run_checks(args: argparse.Namespace) -> bool:
    players = load_players()
    players = _filter_players(
        players,
        seats=set(args.seat or []),
        base_url_contains=args.base_url_contains or "",
        model_contains=args.model_contains or "",
    )
    if not players:
        raise ValueError("没有匹配到要检测的玩家配置，请检查 --seat/--base-url-contains/--model-contains")
    if not args.include_duplicates:
        players = _representative_players(players)
    print(f"将检测 {len(players)} 个不同模型/厂商配置。不会打印 API Key。")
    all_results: list[CheckResult] = []
    for player in players:
        all_results.extend(await check_player(player, timeout=args.timeout))
    return print_results(all_results)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 players.json 里的模型是否适合开局")
    parser.add_argument("--seat", type=int, action="append", help="只检测指定座位，可重复传入")
    parser.add_argument("--base-url-contains", default="", help="只检测 base_url 包含该文本的配置")
    parser.add_argument("--model-contains", default="", help="只检测 model_name 包含该文本的配置")
    parser.add_argument("--timeout", type=float, default=45.0, help="每个测试阶段的超时时间，默认 45 秒")
    parser.add_argument("--include-duplicates", action="store_true", help="检测重复模型配置；默认只检测代表项")
    parser.add_argument("--check-models", action="store_true", help=argparse.SUPPRESS)
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    try:
        ok = asyncio.run(run_checks(args))
    except Exception as exc:
        print(f"[FAIL] 无法开始模型自检：{_short_error(exc)}")
        print("建议：先运行配置向导，确认 players.json 已生成且没有占位符。")
        raise SystemExit(2)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
