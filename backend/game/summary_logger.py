# backend/game/summary_logger.py
"""
游戏摘要日志记录器 - 生成前端视角的可读游戏复盘文件。

输出示例格式（上帝视角，人类可读）：
  - 每局游戏存一个独立文件: backend/logs/summary/game_YYYYMMDD_HHMMSS.txt
  - 包含：角色配置、每夜行动细节（思考+目标）、白天发言、投票、死亡
  - 增量写入（line-buffered），游戏进行中即可 tail 查看
"""
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


ROLE_LABELS = {
    "werewolf": "🐺 狼人",
    "prophet":  "🔮 预言家",
    "witch":    "🧙 女巫",
    "villager": "👤 村民",
    "hunter":   "🏹 猎人",
    "idiot":    "🃏 白痴",
}


def _rl(role: str) -> str:
    return ROLE_LABELS.get(role, f"❓ {role}")


def _clip(text: str, max_len: int = 200) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


class GameSummaryLogger:
    """
    写入人类可读的游戏复盘文件（上帝视角）。

    用法：
        logger = GameSummaryLogger()
        logger.log_game_start(players)        # 开局
        logger.log_night_start(day)           # 每夜
        logger.log_wolf_action(...)           # 狼人决策
        logger.log_prophet_action(...)        # 预言家查验
        logger.log_witch_action(...)          # 女巫用药
        logger.log_night_result(...)          # 夜晚结算
        logger.log_day_start(...)             # 白天开始
        logger.log_speech(...)                # 白天发言
        logger.log_last_words(...)            # 遗言
        logger.log_vote_result(...)           # 投票
        logger.log_game_end(...)              # 游戏结束
    """

    W = 67  # separator width

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / "logs" / "summary"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = log_dir / f"game_{ts}.txt"
        # line-buffered so tail -f works during a live game
        self._f = open(self.path, "w", encoding="utf-8", buffering=1)
        self._players: Dict[int, Dict] = {}   # seat_id -> {seat_id, player_name, model_name, role}
        self._start_time = time.time()

    # ── internal helpers ────────────────────────────────────────────

    def _w(self, text: str = ""):
        self._f.write(text + "\n")

    def _sep(self, char: str = "─"):
        self._w(char * self.W)

    def _pname(self, seat_id: int) -> str:
        p = self._players.get(seat_id, {})
        return p.get("player_name", f"{seat_id}号玩家")

    def _thinking_lines(self, thinking: str, max_lines: int = 999):
        """写出完整思考内容，默认不限制行数。"""
        if not thinking or not thinking.strip():
            return
        lines = thinking.strip().split("\n")
        for line in lines[:max_lines]:
            self._w(f"  💭 {line}")

    # ── game start ──────────────────────────────────────────────────

    def log_game_start(self, players: List[Dict]):
        """
        players: [{seat_id, player_name, model_name, role}, ...]
        """
        self._players = {p["seat_id"]: p for p in players}
        self._w("═" * self.W)
        self._w(f"  🎮 AI 狼人杀 游戏复盘    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._w("═" * self.W)
        self._w()
        self._w("【玩家配置（上帝视角）】")
        for p in sorted(players, key=lambda x: x["seat_id"]):
            role_str = _rl(p.get("role", ""))
            model = p.get("model_name", "")
            name = p.get("player_name", "")
            self._w(f"  {p['seat_id']}号  {name:<10}  {model:<24}  {role_str}")
        self._w()

    # ── night phase ──────────────────────────────────────────────────

    def log_night_start(self, day: int):
        self._sep()
        self._w(f"🌙 第 {day} 天 · 夜晚")
        self._sep()
        self._w()

    def log_wolf_action(
        self,
        seat_id: int,
        thinking: str,
        action: str,
        target: Optional[int],
    ):
        """Log a single wolf's decision (call once per wolf)."""
        p = self._players.get(seat_id, {})
        name = p.get("player_name", f"{seat_id}号")
        model = p.get("model_name", "")
        self._w(f"〔狼人行动〕{seat_id}号 {name} ({model})")
        self._thinking_lines(thinking)
        if target:
            tp = self._players.get(target, {})
            tname = tp.get("player_name", "")
            self._w(f"  → 刀 {target}号 {tname}")
        else:
            self._w(f"  → 未选出有效目标")
        self._w()

    def log_wolf_final_target(self, target: Optional[int], actor: int):
        """Log the final resolved wolf kill target (after coordination)."""
        if target:
            tp = self._players.get(target, {})
            tname = tp.get("player_name", "")
            self._w(f"  ★ 最终刀人: {target}号 {tname}  （由{actor}号决定）")
        else:
            self._w(f"  ★ 狼人未能选出有效刀人目标")
        self._w()

    def log_prophet_action(
        self,
        seat_id: int,
        thinking: str,
        target: Optional[int],
        result: Optional[str],
    ):
        p = self._players.get(seat_id, {})
        name = p.get("player_name", f"{seat_id}号")
        model = p.get("model_name", "")
        self._w(f"〔预言家行动〕{seat_id}号 {name} ({model})")
        self._thinking_lines(thinking)
        if target:
            tp = self._players.get(target, {})
            tname = tp.get("player_name", "")
            result_str = "🐺 狼人！" if result == "狼人" else "✅ 好人"
            self._w(f"  → 查验 {target}号 {tname} → {result_str}")
        else:
            self._w(f"  → 未选出有效查验目标")
        self._w()

    def log_witch_action(
        self,
        seat_id: int,
        thinking: str,
        kill_target: Optional[int],
        action_desc: str,
    ):
        p = self._players.get(seat_id, {})
        name = p.get("player_name", f"{seat_id}号")
        model = p.get("model_name", "")
        self._w(f"〔女巫行动〕{seat_id}号 {name} ({model})")
        if kill_target is not None:
            kp = self._players.get(kill_target, {})
            kname = kp.get("player_name", "")
            self._w(f"  知情: {kill_target}号 {kname} 今晚被刀")
        self._thinking_lines(thinking)
        self._w(f"  → {action_desc}")
        self._w()

    def log_night_result(self, deaths: List[int], night_summary: str):
        if deaths:
            parts = []
            for sid in deaths:
                p = self._players.get(sid, {})
                parts.append(f"{sid}号 {p.get('player_name','')} （{_rl(p.get('role',''))}）")
            self._w(f"  ☠️  夜晚结算: {' / '.join(parts)} 死亡")
        else:
            self._w(f"  ✨ 夜晚结算: 平安夜，无人死亡")
        self._w()

    # ── day phase ────────────────────────────────────────────────────

    def log_day_start(self, day: int, alive_seats: List[int], announcement: str):
        alive_str = "  ".join(f"{s}号" for s in sorted(alive_seats))
        self._sep()
        self._w(f"☀️  第 {day} 天 · 白天    存活: {alive_str}")
        self._sep()
        self._w()
        self._w(f"[公告] {announcement}")
        self._w()

    def log_last_words(
        self,
        seat_id: int,
        role: str,
        thinking: str,
        content: str,
        reason: str,
    ):
        p = self._players.get(seat_id, {})
        name = p.get("player_name", f"{seat_id}号")
        reason_str = "（被投票放逐）" if reason == "vote_eliminated" else "（夜间死亡）"
        self._w(f"[遗言] {seat_id}号 {name} | {_rl(role)} {reason_str}")
        self._thinking_lines(thinking)
        clean = content.replace("[遗言] ", "")
        self._w(f"  💬 \"{clean}\"")
        self._w()

    def log_speech(self, seat_id: int, role: str, thinking: str, content: str):
        p = self._players.get(seat_id, {})
        name = p.get("player_name", f"{seat_id}号")
        self._w(f"[{seat_id}号 {name} | {_rl(role)}]")
        self._thinking_lines(thinking)
        self._w(f"  💬 \"{content}\"")
        self._w()

    def log_vote_result(
        self,
        votes: Dict[int, Optional[int]],
        eliminated: Optional[int],
        is_revote: bool = False,
    ):
        prefix = "重投" if is_revote else "投票"
        self._w(f"[{prefix}结果]")
        # Print each vote
        vote_parts = []
        for voter, target in sorted(votes.items()):
            target_str = f"{target}号" if target is not None else "弃票"
            vote_parts.append(f"{voter}号→{target_str}")
        self._w("  " + "   ".join(vote_parts))
        # Tally
        valid = [v for v in votes.values() if v is not None]
        if valid:
            counts = Counter(valid)
            tally = "  ".join(
                f"{s}号({c}票)" for s, c in sorted(counts.items(), key=lambda x: -x[1])
            )
            self._w(f"  票数: {tally}")
        if eliminated is not None:
            ep = self._players.get(eliminated, {})
            ename = ep.get("player_name", "")
            erole = _rl(ep.get("role", ""))
            self._w(f"  ⚡ 出局: {eliminated}号 {ename} （{erole}）")
        else:
            self._w(f"  ⚡ 平票 / 无人出局")
        self._w()

    # ── game end ─────────────────────────────────────────────────────

    def log_game_end(self, winner: str, day: int, players: List[Dict]):
        elapsed = time.time() - self._start_time
        self._w("═" * self.W)
        winner_str = "🐺 狼人阵营胜利！" if winner == "werewolf" else "🌟 村民阵营胜利！"
        self._w(f"🏆 游戏结束  第 {day} 天   {winner_str}   耗时 {elapsed:.0f}s")
        alive = sorted([p for p in players if p.get("is_alive")], key=lambda x: x["seat_id"])
        dead  = sorted([p for p in players if not p.get("is_alive")], key=lambda x: x["seat_id"])
        if alive:
            alive_str = "  ".join(f"{p['seat_id']}号{p['player_name']}（{_rl(p['role'])}）" for p in alive)
            self._w(f"  存活: {alive_str}")
        if dead:
            dead_str  = "  ".join(f"{p['seat_id']}号{p['player_name']}（{_rl(p['role'])}）" for p in dead)
            self._w(f"  死亡: {dead_str}")
        self._w("═" * self.W)
        self._f.flush()

    # ── misc ─────────────────────────────────────────────────────────

    def close(self):
        try:
            self._f.flush()
            self._f.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
