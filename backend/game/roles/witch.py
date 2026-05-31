# backend/game/roles/witch.py
"""
女巫角色处理。
解药+毒药各1瓶，同一晚不能同时使用。
"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class WitchHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "女巫"

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def _format_history(self, history):
        return "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        )

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        antidote = pd.get("antidote_remaining", 0)
        poison = pd.get("poison_remaining", 0)
        kill_target = pd.get("night_kill_target")
        alive = [
            p for p in view["players"]
            if p["is_alive"] and p["seat_id"] != view["my_seat_id"]
        ]
        prompt = f"""你是{player_name}，你的身份是女巫。

当前药水状态：
  - 解药：{antidote}瓶{'（可用）' if antidote > 0 else '（已用）'}
  - 毒药：{poison}瓶{'（可用）' if poison > 0 else '（已用）'}

"""
        if kill_target is not None:
            prompt += f"""今晚狼人刀了 {kill_target} 号玩家。
你可以选择是否使用解药救活 {kill_target} 号玩家。
"""
        if poison > 0:
            prompt += f"""
你也可以使用毒药毒杀一名存活玩家。

存活玩家：
{self._format_players(alive)}
"""
        prompt += """
重要规则：
- 同一晚不能同时使用解药和毒药
- 解药只能用一次
- 毒药只能用一次

请输出你的选择：
- "不使用任何药"
- "用解药救 X 号"
- "用毒药毒 X 号"
"""
        return prompt

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        day = view["day"]
        night_summary = view.get("night_summary", "")
        pd = view["private_data"]
        last_action = pd.get("last_night_action", "")
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else "（无人发言）"

        night_context = f"夜间事件：{night_summary}" if night_summary else ""
        action_context = f"你昨晚的行动：{last_action}" if last_action else ""

        return f"""你是{player_name}，你的身份是女巫。

你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
{night_context}
{action_context}
当前是第{day}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为女巫，你拥有强大的技能，但请谨慎使用。如果需要，可以暗示你的身份和你昨晚的行动。

请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("full_history", view.get("speech_history", []))
        history_text = self._format_history(history) if history else ""
        return f"""你是{player_name}，身份是女巫。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any], reason: str = "night_kill") -> str:
        day = view.get("day", 1)
        death_label = "夜晚被杀" if reason == "night_kill" else "被投票放逐"
        pd = view["private_data"]
        history = view.get("full_history") or view.get("speech_history") or []
        if day == 1 and not history:
            context = f"游戏刚刚开始，这是第{day}天，还没有人发过言或投过票。"
        elif history:
            context = f"已有发言：\n" + self._format_history(history)
        else:
            context = ""
        return f"""你是{player_name}，你的身份是女巫。你在第{day}天{death_label}。
{context}
你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
请发表遗言。
注意：只说你有依据的内容，不要编造没有发生过的事情。"""


_register_role("witch", WitchHandler())
