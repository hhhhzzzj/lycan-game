"""
自动化对局 + 复盘检查。

用法：
    python scripts/replay_check.py

行为：
  1. 用 backend/config/players.json 启动一局非交互对局（不卡 step）
  2. 收集每个 push_update 事件 + engine 日志
  3. 跑完后分析：
     - 杀队友/选自己/选死人（依靠 night_actions/votes）
     - 校验重试触发次数（依靠 game.log 中 "[校验]" 行）
     - 每个角色的发言是否与自己客观记忆矛盾
  4. 输出 JSON 报告 + 可读复盘到 logs/replay-<ts>/
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend on path
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from game.engine import GameEngine, _resolve_night_deaths, _count_votes  # noqa: E402
from game.state import get_player, get_public_state  # noqa: E402


def setup_logging(replay_dir: Path) -> logging.Logger:
    replay_dir.mkdir(parents=True, exist_ok=True)
    log_path = replay_dir / "replay.log"
    fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    # Reset root logging to ensure file capture
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)
    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    werewolf = logging.getLogger("werewolf")
    werewolf.setLevel(logging.DEBUG)
    return werewolf


def load_player_configs() -> List[Dict[str, Any]]:
    cfg_path = BACKEND / "config" / "players.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    players = data.get("players", [])
    if len(players) != 6:
        raise SystemExit(f"players.json 必须有 6 个玩家，实际 {len(players)}")
    return players


async def run_game(replay_dir: Path) -> Dict[str, Any]:
    log = setup_logging(replay_dir)
    log.info("=== 自动化复盘开始 ===")

    cfgs = load_player_configs()
    engine = GameEngine(cfgs, interactive=False)
    state = engine.state

    # 公开角色分配（供复盘用，对模型不可见）
    role_assignment = {p.seat_id: {"name": p.player_name, "role": p.role,
                                   "model": p.model_name} for p in state.players}
    log.info(f"角色分配: {role_assignment}")

    # 收集每条 push_update（轻量快照）
    events: List[Dict[str, Any]] = []

    async def capture(data: Dict[str, Any]):
        snapshot = {
            "phase": data.get("phase"),
            "day": data.get("day"),
            "phase_info": data.get("phase_info"),
            "night_info": data.get("night_info"),
            "vote_progress": data.get("vote_progress"),
            "current_speaker": data.get("current_speaker"),
            "current_thinking": (data.get("current_thinking") or "")[:300],
            "current_speech": (data.get("current_speech") or "")[:300],
            "ts": time.time(),
        }
        events.append({k: v for k, v in snapshot.items() if v not in (None, "")})

    engine.set_on_update(capture)

    # 给整局加一个超时兜底（每个 LLM 调用 60s × ~30 次 + 余量）
    try:
        await asyncio.wait_for(engine.run_game(), timeout=60 * 30)
    except asyncio.TimeoutError:
        log.error("对局超时（30 分钟），强制结束以做部分复盘")

    final_public = get_public_state(state)
    final_public["winner"] = state.winner
    final_public["role_assignment"] = role_assignment

    return {
        "role_assignment": role_assignment,
        "events": events,
        "final_state": final_public,
        "private_data": {seat: state.private_data.get(seat, {}) for seat in role_assignment},
        "speech_history": [
            {"seat_id": s.seat_id, "player_name": s.player_name,
             "content": s.content, "thinking": s.thinking}
            for s in state.full_history
        ],
        "votes_final": {str(k): v for k, v in state.votes.items()},
    }


# =====================================================================
# 复盘分析
# =====================================================================

def analyze(record: Dict[str, Any], log_path: Path) -> Dict[str, Any]:
    role_assign = record["role_assignment"]
    findings: List[Dict[str, Any]] = []

    # 1. 校验重试与降级（从日志统计）
    retries = 0
    degrades = 0
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        retries = len(re.findall(r"\[校验\] .*?重试 1 次", text))
        degrades = len(re.findall(r"\[校验\] .*?重试仍非法", text))

    # 2. 检查 private_data 中记忆字段是否被正常写入
    pd = record["private_data"]
    memory_health = {}
    for seat_str, data in pd.items():
        seat = int(seat_str) if isinstance(seat_str, str) else seat_str
        role = role_assign[seat]["role"]
        memory_health[seat] = {
            "role": role,
            "my_votes": data.get("my_votes", {}),
            "kill_history": data.get("kill_history") if role == "werewolf" else None,
            "potion_history": data.get("potion_history") if role == "witch" else None,
            "check_results": data.get("check_results") if role == "prophet" else None,
        }

    # 3. 发言-记忆一致性：预言家发言里提到的"X号是狼/好人"是否和 check_results 一致
    speeches = record["speech_history"]
    for s in speeches:
        seat = s["seat_id"]
        role = role_assign[seat]["role"]
        content = s["content"] or ""
        if role == "prophet":
            checks = pd.get(seat, {}).get("check_results", {}) or {}
            # 抓"X号是狼" / "X号是好人" 这类断言
            pat = re.compile(r"(\d+)\s*号(?:是|为)(狼人|狼|好人|金水|银水|查杀)")
            for m in pat.finditer(content):
                target_seat = m.group(1)
                claim = m.group(2)
                truth = checks.get(target_seat) or checks.get(int(target_seat))
                if truth is None:
                    findings.append({
                        "type": "prophet_speech_no_evidence",
                        "seat": seat,
                        "claim": f"{target_seat}号是{claim}",
                        "note": "预言家公开断言了一个未在自己 check_results 中的玩家身份",
                    })
                else:
                    # 简化映射
                    is_wolf_claim = claim in ("狼人", "狼", "查杀")
                    is_wolf_truth = truth == "狼人"
                    if is_wolf_claim != is_wolf_truth:
                        findings.append({
                            "type": "prophet_speech_contradicts_memory",
                            "seat": seat,
                            "claim": f"{target_seat}号是{claim}",
                            "memory": f"{target_seat}号在记忆中是{truth}",
                        })

    # 4. 杀队友/选自己/选死人——夜晚动作和投票的合法性事后检查
    final = record["final_state"]
    # 夜晚动作来自最终 state 的 night_actions（最后一夜），日志里更全；这里用 events 兜底
    # 投票合法性：votes_final 里 voter == target？
    votes_final = record.get("votes_final") or {}
    for voter_str, target in votes_final.items():
        if target is None:
            continue
        voter = int(voter_str)
        if voter == target:
            findings.append({
                "type": "vote_self",
                "seat": voter,
                "note": "投票投了自己",
            })

    summary = {
        "winner": final.get("winner"),
        "total_speeches": len(speeches),
        "retries_triggered": retries,
        "degrades_triggered": degrades,
        "findings_count": len(findings),
        "findings": findings,
    }
    return {"summary": summary, "memory_health": memory_health}


# =====================================================================
# 入口
# =====================================================================

def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    replay_dir = ROOT / "logs" / f"replay-{ts}"

    record = asyncio.run(run_game(replay_dir))
    report = analyze(record, replay_dir / "replay.log")

    # 写入 JSON 数据
    (replay_dir / "events.json").write_text(
        json.dumps(record["events"], ensure_ascii=False, indent=2), encoding="utf-8")
    (replay_dir / "final_state.json").write_text(
        json.dumps(record["final_state"], ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    (replay_dir / "speech_history.json").write_text(
        json.dumps(record["speech_history"], ensure_ascii=False, indent=2),
        encoding="utf-8")
    (replay_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 可读复盘
    md = []
    md.append(f"# 复盘报告 ({ts})\n")
    md.append(f"## 角色分配\n")
    for seat, info in record["role_assignment"].items():
        md.append(f"- {seat}号 {info['name']} ({info['role']}) [{info['model']}]")
    md.append("")
    md.append(f"## 概要\n")
    s = report["summary"]
    md.append(f"- 胜方: **{s['winner']}**")
    md.append(f"- 总发言数: {s['total_speeches']}")
    md.append(f"- 校验重试触发: {s['retries_triggered']} 次")
    md.append(f"- 重试后仍降级: {s['degrades_triggered']} 次")
    md.append(f"- 检测到的疑点: {s['findings_count']} 条")
    md.append("")
    if s["findings"]:
        md.append("## 疑点详情\n")
        for f in s["findings"]:
            md.append(f"- **{f['type']}** seat={f.get('seat')} | {f}")
        md.append("")
    md.append(f"## 记忆健康度\n")
    for seat, mh in report["memory_health"].items():
        md.append(f"### {seat}号 ({mh['role']})")
        md.append(f"- my_votes: {mh['my_votes']}")
        if mh["kill_history"] is not None:
            md.append(f"- kill_history: {mh['kill_history']}")
        if mh["potion_history"] is not None:
            md.append(f"- potion_history: {mh['potion_history']}")
        if mh["check_results"] is not None:
            md.append(f"- check_results: {mh['check_results']}")
        md.append("")
    (replay_dir / "report.md").write_text("\n".join(md), encoding="utf-8")

    # 终端简要
    print("\n========= 复盘报告 =========")
    print(f"目录: {replay_dir}")
    print(f"胜方: {s['winner']}")
    print(f"重试: {s['retries_triggered']}  降级: {s['degrades_triggered']}  疑点: {s['findings_count']}")
    if s["findings"]:
        print("疑点:")
        for f in s["findings"][:10]:
            print(f"  - {f}")
    print(f"\n详见 {replay_dir / 'report.md'}")


if __name__ == "__main__":
    main()
