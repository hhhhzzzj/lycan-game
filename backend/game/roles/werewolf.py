# backend/game/roles/werewolf.py
"""狼人角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class WerewolfHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "狼人"

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def _format_history(self, history):
        return "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        )

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        teammates = pd.get("teammates", [])
        alive = [p for p in view["players"] if p["is_alive"] and p["seat_id"] not in teammates]
        prompt = f"""你是{player_name}，你的身份是狼人。

你的狼人队友：{', '.join(f'{t}号玩家' for t in teammates)}。

现在是夜晚，你需要和队友一起选择今晚要杀死的目标。

当前存活玩家（排除队友）：
{self._format_players(alive)}

请选择你要杀死的目标（输出座位号 1-6）。
注意：你只能杀死存活玩家。
"""
        return prompt

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else "（无人发言）"
        return f"""你是{player_name}，你的身份是狼人。

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。你可以：
- 分析场上局势
- 质疑其他人的发言
- 隐藏自己的身份（如果你需要）
- 如果想要悍跳预言家，可以说"我是预言家，昨晚查了X号是狼人"

请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else ""
        return f"""你是{player_name}，身份是狼人。

现在是投票环节。请根据今天的发言记录决定投票给谁。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。你可以投票给任何存活玩家。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return f"""你是{player_name}，你的身份是狼人。你即将被放逐/杀死。
请发表你的遗言。你可以暴露身份、误导好人、或说出你的想法。"""


_register_role("werewolf", WerewolfHandler())
