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

    def _format_my_votes(self, view):
        pd = view.get("private_data", {})
        lines = []
        ph = pd.get("potion_history", [])
        if ph:
            lines.append("你的用药记录：" + "、".join(
                f"第{r['day']}晚{'救' if r['type']=='save' else '毒'}{r['target']}号" for r in ph))
        mv = pd.get("my_votes", {})
        if mv:
            lines.append("你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items()))
        return ("\n" + "\n".join(lines)) if lines else ""

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
- "不使用任何药"（target_seat 填 null）
- "用解药救 X 号"（target_seat 填被救的人的座位号）
- "用毒药毒 X 号"（target_seat 填要毒的人的座位号）
"""
        return prompt

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_game_summary, build_today_transcript
        day = view["day"]
        pd = view["private_data"]
        last_action = pd.get("last_night_action", "")

        game_summary = build_game_summary(view)
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day, exclude_seat=view.get("my_seat_id"))
        speak_hint = view.get("_speak_order_hint", "")
        action_context = f"你昨晚的行动：{last_action}" if last_action else ""

        return f"""你是{player_name}，你的身份是女巫。

【局势摘要】
{game_summary}
你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
{action_context}{self._format_my_votes(view)}

【今日发言记录】
{today_speeches}

{speak_hint}

请发表你的看法。作为女巫，你知道昨晚谁被刀了（如果你还活着），这是重要信息。
你可以选择性地透露信息来帮助好人阵营。

请用自然的中文发言。发言环节 target_seat 填 null。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_today_transcript, build_alive_players_list
        day = view["day"]
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day)
        alive_list = build_alive_players_list(view["players"], exclude_seat=view.get("my_seat_id"))

        return f"""你是{player_name}，身份是女巫。现在是投票环节。

【今日发言记录】
{today_speeches}
{self._format_my_votes(view)}

【存活玩家（可投票目标）】{alive_list}

请根据今天的发言和你掌握的信息，选择投票目标（不能投自己）。
请在 target_seat 字段填入你的选择。"""

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
