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

    def _format_my_votes(self, view):
        mv = view.get("private_data", {}).get("my_votes", {})
        if not mv:
            return ""
        return "\n你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items())

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_game_summary, build_today_transcript
        day = view["day"]
        game_summary = build_game_summary(view)
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day, exclude_seat=view.get("my_seat_id"))
        speak_hint = view.get("_speak_order_hint", "")

        return f"""你是{player_name}，你的身份是村民。你没有特殊能力，但你通过分析发言和投票帮助好人获胜。

【局势摘要】
{game_summary}
{self._format_my_votes(view)}

【今日发言记录】
{today_speeches}

{speak_hint}

请发表你的看法。作为村民，你应该：
- 认真分析每个人的发言，找出逻辑矛盾
- 跟随可信的预言家站边
- 明确表达你的怀疑和支持

请用自然的中文发言。发言环节 target_seat 填 null。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_today_transcript, build_alive_players_list
        day = view["day"]
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day)
        alive_list = build_alive_players_list(view["players"], exclude_seat=view.get("my_seat_id"))

        return f"""你是{player_name}，身份是村民。现在是投票环节。

【今日发言记录】
{today_speeches}
{self._format_my_votes(view)}

【存活玩家（可投票目标）】{alive_list}

请根据今天的发言和分析，选择一个最可疑的玩家投票放逐（不能投自己）。
请在 target_seat 字段填入你的选择。"""

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
