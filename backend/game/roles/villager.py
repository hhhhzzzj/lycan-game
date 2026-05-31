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
        day = view["day"]
        night_summary = view.get("night_summary", "")
        last_action = view.get("private_data", {}).get("last_night_action", "")
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else "（无人发言）"

        night_context = f"夜间事件：{night_summary}" if night_summary else ""
        action_context = f"你昨晚的行动：{last_action}" if last_action else ""

        return f"""你是{player_name}，你的身份是村民。你没有特殊能力，但你通过分析发言和投票帮助好人获胜。

当前是第{day}天白天，轮到你发言。
{night_context}
{action_context}
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

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any], reason: str = "night_kill") -> str:
        day = view.get("day", 1)
        death_label = "夜晚被杀" if reason == "night_kill" else "被投票放逐"
        history = view.get("full_history") or view.get("speech_history") or []
        history_text = self._format_history(history) if history else ""
        if day == 1 and not history:
            context = f"游戏刚刚开始，这是第{day}天，还没有人发过言、也没有进行过投票。你对场上局势了解甚少。"
        elif day == 1:
            context = f"这是第{day}天，还没有进行过投票。已有的发言：\n{history_text}"
        else:
            context = f"之前已进行过{day - 1}轮游戏。发言记录：\n{history_text}" if history_text else ""
        return f"""你是{player_name}，你的身份是村民。你在第{day}天{death_label}。
{context}
请发表遗言。作为村民，你可以说出你的怀疑对象或最后的建议。
注意：只说你有依据的内容，不要编造没有发生过的事情。"""


_register_role("villager", VillagerHandler())
