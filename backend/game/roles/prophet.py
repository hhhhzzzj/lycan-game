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

    def _format_my_votes(self, view):
        mv = view.get("private_data", {}).get("my_votes", {})
        if not mv:
            return ""
        return "\n你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items())

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        day = view.get("day", 1)
        alive = [p for p in view["players"] if p["is_alive"] and p["seat_id"] != view["my_seat_id"]]
        prev_checks = view["private_data"].get("check_results", {})
        return f"""你是{player_name}，你的身份是预言家。

当前是第{day}天夜晚，你可以查验一名玩家的身份。

已验证过的玩家：
{self._format_checks(prev_checks)}

可查验目标（其他存活玩家，不包含你自己；你仍然是存活且可以行动的）：
{self._format_players(alive)}

请选择你要查验的玩家（输出座位号 1-6）。
注意：只能查验存活玩家，不能查验自己。
请在 target_seat 字段填入你的选择。
"""

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_game_summary, build_today_transcript
        day = view["day"]
        pd = view.get("private_data", {})
        last_action = pd.get("last_night_action", "")
        checks = pd.get("check_results", {})

        game_summary = build_game_summary(view)
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day, exclude_seat=view.get("my_seat_id"))
        speak_hint = view.get("_speak_order_hint", "")
        action_context = f"你昨晚的行动：{last_action}" if last_action else ""

        return f"""你是{player_name}，你的身份是预言家。

【局势摘要】
{game_summary}
{action_context}

你的查验记录（铁证，必须如实汇报）：
{self._format_checks(checks)}{self._format_my_votes(view)}

【今日发言记录】
{today_speeches}

{speak_hint}

{view.get("_strategy_hint", "")}

请发表你的看法。作为预言家，你可以：
- 跳身份报出查验结果（如果你有查杀，这是关键信息）
- 带领好人归票
- 如果首验是金水（好人验），可以选择暂时潜水

请用自然的中文发言。发言环节 target_seat 填 null。
【重要】你的查验记录是铁证，发言时必须与之一致，不能报错。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_today_transcript, build_alive_players_list
        day = view["day"]
        checks = view["private_data"].get("check_results", {})
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day)
        alive_list = build_alive_players_list(view["players"], exclude_seat=view.get("my_seat_id"))

        return f"""你是{player_name}，身份是预言家。现在是投票环节。

你的查验记录：
{self._format_checks(checks)}{self._format_my_votes(view)}

【今日发言记录】
{today_speeches}

【存活玩家（可投票目标）】{alive_list}

请根据你的查验结果和今天的发言，选择投票目标（不能投自己）。
如果你有查杀记录，优先投被查杀的玩家。
请在 target_seat 字段填入你的选择。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any], reason: str = "night_kill") -> str:
        day = view.get("day", 1)
        death_label = "夜晚被杀" if reason == "night_kill" else "被投票放逐"
        checks = view["private_data"].get("check_results", {})
        history = view.get("full_history") or view.get("speech_history") or []
        if day == 1 and not history:
            context = f"游戏刚刚开始，这是第{day}天，还没有人发过言或投过票。"
        elif history:
            context = f"已有发言：\n" + self._format_history(history)
        else:
            context = ""
        vote_text = view.get("_last_vote_text", "")
        return f"""你是{player_name}，你的身份是预言家。你在第{day}天{death_label}。
{context}
{vote_text}
你的查验记录：
{self._format_checks(checks)}

请发表遗言。你已经出局，不能再参与后续夜晚查验、发言或投票；只能报出已发生的查验结果，或给出最后的建议。
注意：只说你有依据的内容，不要编造没有发生过的事情。"""


_register_role("prophet", ProphetHandler())
