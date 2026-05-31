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

    def _format_memory(self, view):
        pd = view.get("private_data", {})
        lines = []
        kh = pd.get("kill_history", {})
        if kh:
            lines.append("你的刀杀记录：" + "、".join(f"第{d}晚刀{t}号" for d, t in kh.items()))
        mv = pd.get("my_votes", {})
        if mv:
            lines.append("你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items()))
        return ("\n" + "\n".join(lines)) if lines else ""

    def get_night_prompt(self, player_name: str, view: Dict[str, Any], teammate_decision: str = None) -> str:
        pd = view["private_data"]
        teammates = pd.get("teammates", [])
        my_seat = view["my_seat_id"]
        alive = [p for p in view["players"] if p["is_alive"]
                 and p["seat_id"] not in teammates
                 and p["seat_id"] != my_seat]
        coord_text = ""
        if teammate_decision:
            coord_text = f"\n你的队友已经决定刀: {teammate_decision}。你可以选择跟刀同一目标，或提出不同意见。\n"
        prompt = f"""你是{player_name}，你的身份是狼人。

你的狼人队友：{', '.join(f'{t}号玩家' for t in teammates)}。

现在是夜晚，你需要和队友一起选择今晚要杀死的目标。{coord_text}
当前存活玩家（排除队友及自己）：
{self._format_players(alive)}

请选择你要杀死的目标（输出座位号 1-6）。
注意：你只能杀死存活玩家，不能杀自己或队友。
请在 target_seat 字段填入你的选择。
"""
        return prompt

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_game_summary, build_today_transcript, build_speak_order_hint
        day = view["day"]
        pd = view.get("private_data", {})
        last_action = pd.get("last_night_action", "")

        game_summary = build_game_summary(view)
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day, exclude_seat=view.get("my_seat_id"))
        speak_hint = view.get("_speak_order_hint", "")

        action_context = f"你昨晚的行动：{last_action}" if last_action else ""

        return f"""你是{player_name}，你的身份是狼人。

【局势摘要】
{game_summary}
{action_context}{self._format_memory(view)}

【今日发言记录】
{today_speeches}

{speak_hint}

请发表你的看法。你可以：
- 像好人一样分析局势、质疑可疑发言
- 适当站边或踩人，引导投票方向
- 保护你的狼队友（不要让集火对准他们）

请用自然的中文发言。发言环节 target_seat 填 null。
【重要】你是狼人但要伪装成好人。不要透露你知道谁是队友、你昨晚刀了谁等狼人独有信息。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_today_transcript, build_alive_players_list
        day = view["day"]
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day)
        alive_list = build_alive_players_list(view["players"], exclude_seat=view.get("my_seat_id"))

        return f"""你是{player_name}，身份是狼人。现在是投票环节。

【今日发言记录】
{today_speeches}
{self._format_memory(view)}

【存活玩家（可投票目标）】{alive_list}

请根据今天的发言，选择一个玩家投票放逐（不能投自己）。
策略：优先投对狼人阵营威胁最大的好人（跳身份的预言家、逻辑强的玩家），同时注意不要让投票模式暴露你和队友的关联。
请在 target_seat 字段填入你的选择。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any], reason: str = "night_kill") -> str:
        day = view.get("day", 1)
        death_label = "夜晚被杀" if reason == "night_kill" else "被投票放逐"
        history = view.get("full_history") or view.get("speech_history") or []
        if day == 1 and not history:
            context = f"游戏刚刚开始，这是第{day}天，还没有人发过言、也没有进行过投票。"
        elif history:
            context = f"已有发言：\n" + self._format_history(history)
        else:
            context = ""
        return f"""你是{player_name}，你的身份是狼人。你在第{day}天{death_label}。
{context}
请发表你的遗言。你可以暴露身份、误导好人、或说出你的想法。
注意：只说你有依据的内容，不要编造没有发生过的事情。"""


_register_role("werewolf", WerewolfHandler())
