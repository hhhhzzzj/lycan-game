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
        day = view.get("day", 1)
        antidote = pd.get("antidote_remaining", 0)
        poison = pd.get("poison_remaining", 0)
        kill_target = pd.get("night_kill_target")
        potion_history = pd.get("potion_history", [])
        alive = [
            p for p in view["players"]
            if p["is_alive"] and p["seat_id"] != view["my_seat_id"]
        ]
        # 用药历史
        history_text = ""
        if potion_history:
            history_lines = []
            for r in potion_history:
                action_desc = "救" if r["type"] == "save" else "毒"
                history_lines.append(f"第{r['day']}晚{action_desc}{r['target']}号")
            history_text = f"\n你的用药记录：{'、'.join(history_lines)}\n"

        prompt = f"""你是{player_name}，你的身份是女巫。

当前是第{day}天夜晚。

当前药水状态：
  - 解药：{antidote}瓶{'（可用）' if antidote > 0 else '（已用完）'}
  - 毒药：{poison}瓶{'（可用）' if poison > 0 else '（已用完）'}
{history_text}
"""
        if kill_target is not None:
            prompt += f"""今晚狼人刀了 {kill_target} 号玩家。
你可以选择是否使用解药救活 {kill_target} 号玩家。
"""
            if kill_target == view["my_seat_id"] and day == 1 and antidote > 0:
                prompt += (
                    "【强策略提示】今晚被刀的是你自己。6人局女巫首夜被刀时，"
                    "强烈建议使用解药自救；否则你会立刻死亡，通常会让好人阵营大劣。\n"
                )
        if poison > 0:
            prompt += f"""
你也可以使用毒药毒杀一名存活玩家。

可毒杀目标（其他存活玩家，不包含你自己；你仍然是存活且可以行动的）：
{self._format_players(alive)}
"""
        prompt += """
重要规则：
- 同一晚不能同时使用解药和毒药
- 解药只能用一次
- 毒药只能用一次
- 【同刀同毒规则】即使你今晚被狼人刀中，你仍然有权利在当晚使用毒药（夜晚死亡结算在你用药决定之后，你有机会使用毒药带走一名玩家再死亡）

请输出你的选择：
- "不使用任何药"（target_seat 填 null）
- "用解药救 X 号"（target_seat 填被救的人的座位号）
- "用毒药毒 X 号"（target_seat 填要毒的人的座位号）

【重要】你的 action 字段必须与你在 thinking 中做出的最终决定完全一致。如果你决定不用药，action 就写"不使用任何药"；如果决定救人，action 就写"用解药救 X 号"。
"""
        return prompt

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        from game.prompt_context import build_game_summary, build_today_transcript
        day = view["day"]
        pd = view["private_data"]
        kill_target = pd.get("night_kill_target")

        game_summary = build_game_summary(view)
        today_speeches = build_today_transcript(
            view.get("speech_history", []), day, exclude_seat=view.get("my_seat_id"))
        speak_hint = view.get("_speak_order_hint", "")
        kill_context = (
            f"最近一晚狼人刀口：{kill_target}号。"
            if kill_target is not None
            else "最近一晚你没有收到明确刀口信息。"
        )

        return f"""你是{player_name}，你的身份是女巫。

【局势摘要】
{game_summary}
你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
{kill_context}
注意：最近一晚刀口只指刚刚过去的夜晚；你的用药记录是历史信息，不等于最近一晚刀口。
{self._format_my_votes(view)}

【今日发言记录】
{today_speeches}

{speak_hint}

{view.get("_strategy_hint", "")}

请发表你的看法。作为女巫，你知道最近一晚谁被刀了（如果你还活着），这是重要信息。
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
        vote_text = view.get("_last_vote_text", "")
        return f"""你是{player_name}，你的身份是女巫。你在第{day}天{death_label}。
{context}
{vote_text}
你的出局前药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
请发表遗言。你已经出局，不能再使用解药或毒药，也不能参与后续夜晚行动、发言或投票。
注意：只说你有依据的内容，不要编造没有发生过的事情。"""


_register_role("witch", WitchHandler())
