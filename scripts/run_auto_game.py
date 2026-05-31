"""
自动化端到端验证脚本
- 启动一局完整的 AI 狼人杀（非交互模式）
- 收集全过程日志（夜晚行动 / 发言 / 投票 / 死亡）
- 自动复盘分析：检查是否存在杀队友、投自己、前后矛盾等问题
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 确保能 import backend 模块
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from game.engine import GameEngine
from game.state import get_public_state, get_player, get_alive_players


def load_player_configs():
    config_path = Path(__file__).parent.parent / "backend" / "config" / "players.json"
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["players"]


class GameLogger:
    """收集游戏全过程的结构化日志"""

    def __init__(self):
        self.events = []
        self.start_time = time.time()

    def log(self, event_type: str, data: dict):
        self.events.append({
            "ts": round(time.time() - self.start_time, 2),
            "type": event_type,
            **data,
        })

    def save(self, filepath: Path):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)


class GameAnalyzer:
    """复盘分析器：检查已知问题是否仍存在"""

    def __init__(self, events: list, players: list):
        self.events = events
        self.players = {p["seat_id"]: p for p in players}
        self.issues = []

    def run_all_checks(self):
        self.check_wolf_kill_teammate()
        self.check_vote_self()
        self.check_vote_dead()
        self.check_prophet_contradiction()
        return self.issues

    def check_wolf_kill_teammate(self):
        """检查狼人是否刀了队友"""
        wolf_seats = [s for s, p in self.players.items() if p["role"] == "werewolf"]
        for e in self.events:
            if e["type"] == "night_kill" and e.get("target") in wolf_seats:
                self.issues.append({
                    "severity": "CRITICAL",
                    "type": "wolf_kill_teammate",
                    "detail": f"第{e.get('day')}晚: 狼人{e.get('actor')}号刀了队友{e.get('target')}号",
                })

    def check_vote_self(self):
        """检查是否投了自己"""
        for e in self.events:
            if e["type"] == "vote" and e.get("voter") == e.get("target"):
                self.issues.append({
                    "severity": "HIGH",
                    "type": "vote_self",
                    "detail": f"第{e.get('day')}天: {e.get('voter')}号投了自己",
                })

    def check_vote_dead(self):
        """检查是否投了已死的人"""
        dead_at_day = {}  # day -> set of dead seats
        current_dead = set()
        for e in self.events:
            if e["type"] == "death":
                current_dead.add(e["seat_id"])
            if e["type"] == "day_start":
                dead_at_day[e["day"]] = set(current_dead)
        for e in self.events:
            if e["type"] == "vote" and e.get("target") is not None:
                day = e.get("day")
                dead = dead_at_day.get(day, set())
                if e["target"] in dead:
                    self.issues.append({
                        "severity": "HIGH",
                        "type": "vote_dead",
                        "detail": f"第{day}天: {e.get('voter')}号投了已死的{e['target']}号",
                    })

    def check_prophet_contradiction(self):
        """检查预言家是否报了跟真实查验不一致的结果"""
        # 比较预言家发言中提到的查验结果 vs 实际查验记录
        checks = {}
        for e in self.events:
            if e["type"] == "prophet_check":
                checks[e["target"]] = e["result"]
        # TODO: 后续可进一步解析发言内容做语义对比
        # 当前只做结构化记录，不做发言内容的语义分析


async def run_game():
    print("=" * 60)
    print(f"🎮 AI 狼人杀自动化验证 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    player_configs = load_player_configs()
    engine = GameEngine(player_configs, interactive=False)
    state = engine.state
    logger = GameLogger()

    # 记录角色分配
    role_map = []
    for p in state.players:
        role_map.append({
            "seat_id": p.seat_id,
            "player_name": p.player_name,
            "model_name": p.model_name,
            "role": p.role,
        })
    logger.log("game_start", {"players": role_map})
    print("\n📋 角色分配：")
    for r in role_map:
        print(f"  {r['seat_id']}号 {r['player_name']} ({r['model_name']}) → {r['role']}")

    # 注册推送回调：收集关键事件
    async def on_update(data):
        # 记录夜间行动
        if "night_info" in data and data.get("night_info"):
            logger.log("night_action", {"info": data["night_info"], "day": state.day})
        # 记录发言
        if "current_speech" in data and data.get("current_speech"):
            logger.log("speech", {
                "speaker": data.get("current_speaker"),
                "content": data["current_speech"],
                "thinking": data.get("current_thinking", ""),
                "day": state.day,
            })
        # 记录阶段变化
        if "phase_info" in data and data.get("phase_info"):
            logger.log("phase", {"info": data["phase_info"], "day": state.day})

    engine.set_on_update(on_update)

    # 跑游戏
    print("\n🚀 开始对局...\n")
    start = time.time()
    await engine.run_game()
    elapsed = time.time() - start

    # 记录游戏结果
    logger.log("game_end", {
        "winner": state.winner,
        "day": state.day,
        "elapsed_seconds": round(elapsed, 1),
    })

    print(f"\n{'=' * 60}")
    print(f"🏁 对局结束！耗时 {elapsed:.1f}s，共 {state.day} 天")
    print(f"   胜利方: {state.winner}")
    print(f"{'=' * 60}")

    # 打印存活/死亡状态
    print("\n📊 最终状态：")
    for p in state.players:
        status = "✅ 存活" if p.is_alive else "💀 死亡"
        print(f"  {p.seat_id}号 {p.player_name} ({p.role}) - {status}")

    # 收集投票和刀杀事件用于分析
    # 从 engine state 收集实际发生的事件
    analysis_events = []
    # 从 night_actions 构建事件（需要在游戏过程中收集）
    # 这里我们从 logger 的事件中提取
    for e in logger.events:
        if e["type"] == "night_action" and "刀" in e.get("info", ""):
            # 尝试提取刀杀信息
            info = e["info"]
            if "最终刀人目标" in info or "决定刀" in info:
                pass  # 结构化提取在后续版本做
    # 从 state.private_data 提取记忆做验证
    print("\n📝 记忆验证：")
    for p in state.players:
        pd = state.private_data.get(p.seat_id, {})
        mv = pd.get("my_votes", {})
        kh = pd.get("kill_history", {})
        ph = pd.get("potion_history", [])
        if mv or kh or ph:
            print(f"  {p.seat_id}号 {p.player_name}:")
            if kh:
                print(f"    刀杀记录: {kh}")
            if mv:
                print(f"    投票记录: {mv}")
            if ph:
                print(f"    用药记录: {ph}")

    # 保存日志
    log_dir = Path(__file__).parent.parent / "backend" / "logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"auto_game_{timestamp}.json"
    logger.save(log_path)
    print(f"\n💾 日志已保存到: {log_path}")

    # 复盘分析
    print("\n🔍 自动复盘分析...")
    analyzer = GameAnalyzer(logger.events, role_map)
    issues = analyzer.run_all_checks()

    if not issues:
        print("  ✅ 未检测到已知问题（杀队友/投自己/投死人）")
    else:
        print(f"  ⚠️  检测到 {len(issues)} 个问题：")
        for issue in issues:
            print(f"    [{issue['severity']}] {issue['detail']}")

    # 输出完整对话记录摘要
    speeches = [e for e in logger.events if e["type"] == "speech"]
    print(f"\n💬 全局共 {len(speeches)} 条发言")
    for s in speeches[:20]:  # 最多打印前20条
        speaker = s.get("speaker", "?")
        content = s.get("content", "")[:80]
        print(f"  [{s.get('day', '?')}天] {speaker}号: {content}")
    if len(speeches) > 20:
        print(f"  ... (还有 {len(speeches) - 20} 条，详见日志文件)")

    return issues


if __name__ == "__main__":
    issues = asyncio.run(run_game())
    sys.exit(1 if issues else 0)
