"""Provider/model readiness checks for configured players."""
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
        "你是 API 连通性测试助手。必须输出合法 JSON。",
        '{"thinking":"简短思考","action":"你好，连接正常","target_seat":null}',
        False,
    ),
    (
        "werewolf_context",
        "你正在玩一局 6 人狼人杀。必须输出合法 JSON，不要拒答。",
        "你是 1 号玩家，请用一句自然发言说明你会听大家发言再判断。",
        False,
    ),
    (
        "target_seat",
        "你正在玩一局 6 人狼人杀。必须输出合法 JSON。",
        '请从 2号、3号 中选择一个投票目标，并把座位号填入 target_seat。',
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


async def check_player(player: dict[str, Any]) -> list[CheckResult]:
    adapter = create_adapter(
        provider=player.get("provider", "openai"),
        model=player["model_name"],
        api_key=player["api_key"],
        base_url=player.get("base_url"),
    )
    results: list[CheckResult] = []
    for stage, system_prompt, user_prompt, require_target in CHECKS:
        try:
            resp = await asyncio.wait_for(adapter.call(system_prompt, user_prompt), timeout=150.0)
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


async def run_checks() -> bool:
    players = _representative_players(load_players())
    print(f"将检测 {len(players)} 个不同模型/厂商配置。不会打印 API Key。")
    all_results: list[CheckResult] = []
    for player in players:
        all_results.extend(await check_player(player))
    return print_results(all_results)


def main():
    try:
        ok = asyncio.run(run_checks())
    except Exception as exc:
        print(f"[FAIL] 无法开始模型自检：{_short_error(exc)}")
        print("建议：先运行配置向导，确认 players.json 已生成且没有占位符。")
        raise SystemExit(2)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
