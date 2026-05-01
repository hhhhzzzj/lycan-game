# backend/game/roles/villager.py
"""村民角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class VillagerHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "村民"

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def _format_history(self, history):
        return "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        )

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else "（无人发言）"
        return f"""你是{player_name}，你的身份是村民。

你没有特殊能力，但你通过分析发言和投票帮助好人获胜。

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为村民，你应该：
- 认真分析每个人的发言
- 找出矛盾或可疑之处
- 帮助预言家等神职队友

请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else ""
        return f"""你是{player_name}，身份是村民。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return f"""你是{player_name}，你的身份是村民。你即将死亡。
请发表遗言。作为村民，你可以说出你的怀疑对象或最后的建议。"""


_register_role("villager", VillagerHandler())
