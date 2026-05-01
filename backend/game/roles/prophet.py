# backend/game/roles/prophet.py
"""预言家角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class ProphetHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "预言家"

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def _format_checks(self, checks):
        if not checks:
            return "  （尚未查验任何玩家）"
        return "\n".join(f"  {seat}号: {result}" for seat, result in checks.items())

    def _format_history(self, history):
        return "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        )

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"] and p["seat_id"] != view["my_seat_id"]]
        prev_checks = view["private_data"].get("check_results", {})
        return f"""你是{player_name}，你的身份是预言家。

现在是夜晚，你可以查验一名玩家的身份。

已验证过的玩家：
{self._format_checks(prev_checks)}

存活玩家：
{self._format_players(alive)}

请选择你要查验的玩家（输出座位号 1-6）。
"""

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        checks = view["private_data"].get("check_results", {})
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else "（无人发言）"
        return f"""你是{player_name}，你的身份是预言家。

你的查验记录：
{self._format_checks(checks)}

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为预言家，你可以：
- 报出你的查验结果
- 分析场上局势
- 带领好人投票

但是如果你的查验结果对你不利，你可以选择暂时不暴露身份。
请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        checks = view["private_data"].get("check_results", {})
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else ""
        return f"""你是{player_name}，身份是预言家。

你的查验记录：
{self._format_checks(checks)}

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        checks = view["private_data"].get("check_results", {})
        return f"""你是{player_name}，你的身份是预言家。你即将死亡。

你的查验记录：
{self._format_checks(checks)}

请发表遗言。你可以报出所有查验结果，或给出最后的建议。"""


_register_role("prophet", ProphetHandler())
