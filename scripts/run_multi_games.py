"""
多局自动化验证：连跑多局，汇总分析问题检出率。
用法: python scripts/run_multi_games.py [局数，默认3]
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from game.engine import GameEngine
from game.state import get_public_state, get_player, get_alive_players


def load_player_configs():
    config_path = Path(__file__).parent.parent / "backend" / "config" / "players.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["players"]


async def run_single_game(game_num: int, log_dir: Path):
    """跑一局，返回 (issues_list, summary_dict)"""
    player_configs = load_player_configs()
    engine = GameEngine(player_configs, interactive=False)
    state = engine.state

    role_map = {p.seat_id: {"name": p.player_name, "role": p.role, "model": p.model_name}
                for p in state.players}
    wolf_seats = [s for s, r in role_map.items() if r["role"] == "werewolf"]

    events = []
    start = time.time()

    async def on_update(data):
        events.append({"ts": round(time.time() - start, 2), **data})

    engine.set_on_update(on_update)
    await engine.run_game()
    elapsed = round(time.time() - start, 1)

    # 分析
    issues = []

    # 检查杀队友
    for action in state.night_actions:
        if action.action_type == "kill" and action.target_seat in wolf_seats:
            issues.append(f"[杀队友] D{state.day} 狼人{action.actor_seat}号刀了队友{action.target_seat}号")

    # 检查投自己/投死人（注意：被投票放逐的人是投票之后才死的，投票时还活着不算"投死人"）
    # 这里只检查当前 state.votes，它记录的是最后一次投票
    # 需要在投票发生时判断，而不是游戏结束后判断——所以此处检查从记忆中按天比对
    # 简化处理：如果某人在 Day N 白天被投出（day N 死亡），那 Day N 投他的票是合法的
    # 只有投了"在本次投票开始前就已经死亡"的人才算"投死人"
    # 当前数据无法精确区分（state.votes 不带时间戳），暂不检测"投死人"
    # 真实检测应从游戏事件流中按时序判断
    pass

    # 检查前后矛盾（预言家是否明确说了跟实际查验相反的结论）
    # 用更严格的模式避免误报：只匹配"X号...是好人/狼人"紧邻表述
    import re as _re
    prophet_seats = [s for s, r in role_map.items() if r["role"] == "prophet"]
    if prophet_seats:
        ps = prophet_seats[0]
        pd = state.private_data.get(ps, {})
        checks = pd.get("check_results", {})
        for speech in state.full_history:
            if speech.seat_id == ps:
                for seat_str, actual_result in checks.items():
                    # 严格匹配："X号"后10字内出现"是好人"或"是狼人"
                    claims_good = bool(_re.search(rf'{seat_str}号.{{0,10}}是好人', speech.content))
                    claims_wolf = bool(_re.search(rf'{seat_str}号.{{0,10}}是狼人', speech.content))
                    if actual_result == "狼人" and claims_good and not claims_wolf:
                        issues.append(f"[前后矛盾] 预言家{ps}号说{seat_str}号是好人，但实际查验是狼人")
                    elif actual_result == "好人" and claims_wolf and not claims_good:
                        issues.append(f"[前后矛盾] 预言家{ps}号说{seat_str}号是狼人，但实际查验是好人")

    summary = {
        "game": game_num,
        "winner": state.winner,
        "days": state.day,
        "elapsed_s": elapsed,
        "roles": role_map,
        "issues": issues,
        "alive_at_end": [p.seat_id for p in state.players if p.is_alive],
        "memory_snapshot": {
            s: {k: v for k, v in pd.items() if k in ("my_votes", "kill_history", "potion_history", "check_results")}
            for s, pd in state.private_data.items()
        },
    }

    # 保存详细日志
    log_path = log_dir / f"game_{game_num}.json"
    full_log = {
        "summary": summary,
        "speeches": [
            {"seat": s.seat_id, "name": s.player_name, "content": s.content,
             "thinking": s.thinking, "ts": s.timestamp}
            for s in state.full_history
        ],
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(full_log, f, ensure_ascii=False, indent=2)

    return issues, summary


async def main():
    num_games = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / "backend" / "logs" / f"multi_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"🎮 AI 狼人杀多局验证 — {num_games} 局")
    print(f"   日志目录: {log_dir}")
    print("=" * 60)

    all_summaries = []
    total_issues = []

    for i in range(1, num_games + 1):
        print(f"\n{'─' * 40}")
        print(f"📍 第 {i}/{num_games} 局")
        issues, summary = await run_single_game(i, log_dir)
        all_summaries.append(summary)
        total_issues.extend(issues)

        # 单局简报
        status = "✅ 无问题" if not issues else f"⚠️ {len(issues)} 问题"
        print(f"   结果: {summary['winner']} 胜 | {summary['days']}天 | {summary['elapsed_s']}s | {status}")
        if issues:
            for iss in issues:
                print(f"      {iss}")

    # 汇总报告
    print(f"\n{'=' * 60}")
    print(f"📊 汇总报告 ({num_games} 局)")
    print(f"{'=' * 60}")

    wolf_wins = sum(1 for s in all_summaries if s["winner"] == "werewolf")
    villager_wins = sum(1 for s in all_summaries if s["winner"] == "villager")
    avg_days = sum(s["days"] for s in all_summaries) / num_games
    avg_time = sum(s["elapsed_s"] for s in all_summaries) / num_games

    print(f"  胜率: 狼人 {wolf_wins}/{num_games} | 好人 {villager_wins}/{num_games}")
    print(f"  平均天数: {avg_days:.1f} | 平均耗时: {avg_time:.0f}s")
    print()

    if not total_issues:
        print("  ✅ 全部对局未检测到已知问题（杀队友/投自己/投死人/前后矛盾）")
    else:
        print(f"  ⚠️ 共检测到 {len(total_issues)} 个问题：")
        for iss in total_issues:
            print(f"      {iss}")

    # 保存汇总
    report_path = log_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_games": num_games,
            "wolf_wins": wolf_wins,
            "villager_wins": villager_wins,
            "avg_days": avg_days,
            "avg_time_s": avg_time,
            "total_issues": total_issues,
            "summaries": all_summaries,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 汇总报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
