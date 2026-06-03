# backend/game/prompt_context.py
"""
Prompt 上下文构建器：为各角色 prompt 提供结构化的游戏信息。
把"一锅粥"的历史记录拆成：公开摘要 + 今日发言 + 发言位置感知。
"""
from typing import Any, Dict, List, Optional


def build_game_summary(state_view: Dict[str, Any]) -> str:
    """构建跨天的公开游戏摘要（不含今日发言原文，只含结构化事件）。
    
    输入是 get_player_view 返回的 view dict。
    """
    day = state_view.get("day", 1)
    night_summary = state_view.get("night_summary", "")
    killed = state_view.get("killed_last_night", [])
    votes = state_view.get("votes", {})
    players = state_view.get("players", [])
    death_log = state_view.get("death_log", [])

    lines = []
    lines.append(f"当前是第{day}天。")

    if night_summary:
        lines.append(f"昨晚事件：{night_summary}")

    # 已知的公开投票结果（上一轮的）
    if votes:
        vote_summary = "、".join(f"{v}号→{t}号" for v, t in votes.items() if t is not None)
        if vote_summary:
            lines.append(f"上轮投票记录：{vote_summary}")

    # 显式死亡历史（按时间顺序列出所有已死亡玩家及原因）
    if death_log:
        death_lines = []
        for d in death_log:
            seat = d["seat_id"]
            dday = d["day"]
            reason = "夜间被杀" if d["reason"] == "night_kill" else "被投票放逐"
            p_info = next((p for p in players if p["seat_id"] == seat), None)
            name = p_info["player_name"] if p_info else f"{seat}号"
            death_lines.append(f"  第{dday}天 {seat}号({name}) {reason}")
        lines.append("【死亡记录】\n" + "\n".join(death_lines))

    # 显式存活/死亡状态（最关键的信息）
    alive = [p for p in players if p.get("is_alive")]
    dead = [p for p in players if not p.get("is_alive")]
    alive_str = "、".join(f"{p['seat_id']}号({p['player_name']})" for p in alive)
    lines.append(f"【当前存活】{alive_str}")
    if dead:
        dead_str = "、".join(f"{p['seat_id']}号({p['player_name']})" for p in dead)
        lines.append(f"【已死亡】{dead_str}")

    return "\n".join(lines)


def build_today_transcript(full_history: List[Dict[str, Any]], day: int,
                           exclude_seat: Optional[int] = None) -> str:
    """构建今日已有的发言记录（不含自己之前的发言，除非需要）。
    
    只取当天的发言，不传全部历史——减少 token 消耗、突出重点。
    """
    # full_history 里每条 speech 没有 day 标记，但我们可以用 speech_history（当天）
    # 在 get_player_view 中，speech_history 是当天的，full_history 是全部的
    # 这里我们用传入的 full_history 做渲染（调用方决定传哪个）
    if not full_history:
        return "（尚无人发言）"

    lines = []
    for h in full_history:
        seat = h.get("seat_id", "?")
        name = h.get("player_name", "?")
        content = h.get("content", "")
        if exclude_seat and seat == exclude_seat:
            continue
        # 截断过长的发言，避免塞太多 token
        if len(content) > 200:
            content = content[:200] + "..."
        lines.append(f"  {seat}号({name}): {content}")

    return "\n".join(lines) if lines else "（尚无人发言）"


def build_speak_order_hint(speaker_order: List[int], current_seat: int,
                           spoken_seats: List[int]) -> str:
    """构建发言位置感知信息。
    
    告诉模型：你是第几个发言的、前面谁已经说了、后面还有谁。
    """
    # 过滤出存活的发言顺序（调用方应只传存活的）
    if current_seat not in speaker_order:
        return ""

    idx = speaker_order.index(current_seat)
    total = len(speaker_order)
    position = len(spoken_seats) + 1  # 当前是第几个

    if position == 1:
        return f"你是第1个发言（共{total}人），没有人可以参考，大胆表达你的观点。"
    elif position == total:
        return f"你是最后一个发言（第{total}/{total}个），你已经听完了所有人的发言，可以指出矛盾和总结。"
    else:
        spoken_str = "、".join(f"{s}号" for s in spoken_seats)
        remaining = [s for s in speaker_order[idx+1:]]
        remaining_str = "、".join(f"{s}号" for s in remaining)
        return f"你是第{position}/{total}个发言。已发言：{spoken_str}。还未发言：{remaining_str}。"


def build_alive_players_list(players: List[Dict[str, Any]], exclude_seat: Optional[int] = None) -> str:
    """构建存活玩家列表（用于合法目标展示）。"""
    alive = [p for p in players if p.get("is_alive") and p.get("seat_id") != exclude_seat]
    return "、".join(f"{p['seat_id']}号({p['player_name']})" for p in alive)
