# backend/game/strategy.py
"""
策略注入层：根据角色和当前局面，动态生成策略建议。
参考 wolfcha 的 buildSituationalStrategy 思路，精简版。

策略建议只出现在发言 prompt 中（不影响夜间行动和投票的结构化决策）。
"""
from typing import Any, Dict, List


def build_strategy_hint(role: str, view: Dict[str, Any]) -> str:
    """根据角色和视角信息生成策略建议。返回空串表示无特殊建议。"""
    day = view.get("day", 1)
    pd = view.get("private_data", {})
    players = view.get("players", [])
    speech_history = view.get("speech_history", [])
    killed = view.get("killed_last_night", [])
    my_seat = view.get("my_seat_id")

    if role == "prophet":
        return _prophet_strategy(day, pd, speech_history)
    elif role == "werewolf":
        return _werewolf_strategy(day, pd, players, speech_history, my_seat)
    elif role == "witch":
        return _witch_strategy(day, pd, killed)
    elif role == "villager":
        return _villager_strategy(day, speech_history)
    return ""


def _prophet_strategy(day: int, pd: Dict, speeches: List) -> str:
    """预言家策略：根据查验结果和局面给出行动建议。"""
    checks = pd.get("check_results", {})
    lines = []

    if not checks:
        return ""

    has_wolf_check = any(v == "狼人" for v in checks.values())
    has_good_check = any(v == "好人" for v in checks.values())
    wolf_seats = [int(s) for s, v in checks.items() if v == "狼人"]

    lines.append("【策略建议】")

    if has_wolf_check and day == 1:
        lines.append("你首验查杀！这是强信息。建议：")
        lines.append("- 直接跳身份报出查杀目标，带领好人归票")
        lines.append(f"- 明确说出：'我是预言家，查了{wolf_seats[0]}号是狼人'")
        lines.append("- 给出归票建议，呼吁大家集中投票")
        lines.append("- 准备好应对狼人可能的对跳")
    elif has_wolf_check and day >= 2:
        lines.append(f"你有查杀记录（{', '.join(f'{s}号' for s in wolf_seats)}）。建议：")
        lines.append("- 继续推进查杀目标出局")
        lines.append("- 结合新的查验结果巩固你的可信度")
        lines.append("- 如果被质疑，用逻辑和票型证明自己")
    elif has_good_check and not has_wolf_check:
        good_seats = [int(s) for s, v in checks.items() if v == "好人"]
        if day == 1:
            lines.append("你只有金水（好人验），信息量有限。建议：")
            lines.append("- 可以选择跳身份报金水，争取话语权")
            lines.append("- 或者潜水观察一天，等有查杀再跳")
            lines.append(f"- 如果跳，说：'我是预言家，验了{good_seats[0]}号是好人'")
        else:
            lines.append("你目前没有查杀，但有金水。建议：")
            lines.append("- 结合场上信息和发言分析谁最可疑")
            lines.append("- 你的金水玩家是可信的队友")

    return "\n".join(lines)


def _werewolf_strategy(day: int, pd: Dict, players: List, speeches: List, my_seat=None) -> str:
    """狼人策略：根据局面给伪装/反打/悍跳建议。"""
    teammates = pd.get("teammates", [])
    kill_history = pd.get("kill_history", {})
    claimed_role = pd.get("claimed_role")
    claimed_checks = pd.get("claimed_checks", {})
    lines = []

    # 检测场上是否有人跳预言家
    prophet_claims = []  # (seat_id, content)
    for s in speeches:
        content = s.get("content", "")
        seat = s.get("seat_id")
        if "预言家" in content and ("我是" in content or "查验" in content or "查了" in content):
            prophet_claims.append({"seat": seat, "content": content})

    # 检测是否有人查杀自己或队友
    accused_wolves = set()
    for s in speeches:
        content = s.get("content", "")
        if "狼人" in content and "查" in content:
            for t in teammates:
                if f"{t}号" in content:
                    accused_wolves.add(t)
            # 检测自己是否被查杀（通过 my_seat）
            if my_seat and f"{my_seat}号" in content and "狼人" in content:
                accused_wolves.add(my_seat)

    lines.append("【策略建议】")

    # === 悍跳决策 ===
    if claimed_role == "prophet":
        # 已经悍跳了，要维持谎言
        lines.append("⚠️ 你已经悍跳预言家！必须维持这个身份：")
        lines.append(f"  - 你编造的查验结果：{claimed_checks if claimed_checks else '尚未编造'}")
        lines.append("  - 发言中继续以预言家身份说话")
        lines.append("  - 如果真预言家跟你对跳，坚持你是真的，质疑对方")
        lines.append("  - 今晚要'报查验'（编一个合理的查验结果）")
    elif prophet_claims and accused_wolves:
        # 有人跳预言家查杀了你/队友 → 强烈建议对跳
        accuser_seats = [pc["seat"] for pc in prophet_claims]
        lines.append(f"⚠️ 紧急！{', '.join(f'{s}号' for s in accuser_seats)} 跳预言家查杀了你的阵营！")
        lines.append("你有两个选择（权衡风险）：")
        lines.append("  【选项A：悍跳对跳】（高风险高收益）")
        lines.append("  - 说'我才是预言家'，并编造一个查验结果来反打")
        lines.append("  - 编造时要合理：说你查了某个好人（非队友）是'狼人'")
        lines.append("  - 如果选择悍跳，在 action 中明确说'我是预言家，昨晚查了X号是狼人'")
        lines.append("  【选项B：质疑但不跳】（低风险）")
        lines.append("  - 质疑对方预言家身份的逻辑和时机")
        lines.append("  - 帮被查杀的队友辩护")
        lines.append("  请根据局势自行判断哪个选项更合适。")
    elif not prophet_claims and day == 1:
        # 没人跳预言家 → 可以考虑先手悍跳抢位
        lines.append("目前没有人跳预言家。你可以考虑：")
        lines.append("  【选项：先手悍跳预言家】（大胆策略）")
        lines.append("  - 抢先跳预言家，编造一个查验结果（查某个好人是'狼人'）")
        lines.append("  - 好处：抢到话语权，带偏好人归票方向")
        lines.append("  - 风险：真预言家后面会跳出来对跳，你需要圆谎")
        lines.append("  - 如果不想冒险，正常伪装发言即可")
    else:
        # 一般局面
        if day == 1:
            lines.append("首日发言，建立信任最关键。建议：")
            lines.append("- 像好人一样分析局势，不要划水也不要过于积极")
            lines.append("- 绝对不要暴露你知道谁是狼人/好人")
            lines.append("- 可以适当质疑某个好人，制造混乱")
        else:
            lines.append(f"第{day}天，局势逐渐明朗。建议：")
            lines.append("- 维持你之前建立的人设，不要突然转变")
            lines.append("- 投票方向要和你的发言一致")

    if accused_wolves and not claimed_role:
        accused_str = "、".join(f"{s}号" for s in accused_wolves)
        lines.append(f"- ⚠️ 你的阵营 {accused_str} 被点名查杀了！")

    return "\n".join(lines)


def _witch_strategy(day: int, pd: Dict, killed: List) -> str:
    """女巫策略：用药决策和发言建议。"""
    antidote = pd.get("antidote_remaining", 0)
    poison = pd.get("poison_remaining", 0)
    potion_history = pd.get("potion_history", [])
    lines = []

    if not antidote and not poison and not potion_history:
        return ""

    lines.append("【策略建议】")

    if potion_history:
        # 已用过药，可以在发言中利用这些信息
        for ph in potion_history:
            if ph["type"] == "save":
                lines.append(f"- 你第{ph['day']}晚救了{ph['target']}号。如果需要，可以跳身份证明{ph['target']}号被刀过（帮助好人确认信息）")
            elif ph["type"] == "poison":
                lines.append(f"- 你第{ph['day']}晚毒了{ph['target']}号。如果对方是狼人，你可以暗示这个信息")

    if killed and day == 1:
        lines.append("- 你知道昨晚谁被刀了。这个信息在好人中只有你知道")
        lines.append("- 可以选择性地透露'昨晚有人被刀/被救'来帮助好人判断")

    return "\n".join(lines)


def _villager_strategy(day: int, speeches: List) -> str:
    """村民策略：引导村民积极参与而非划水。"""
    lines = []

    # 检测是否有人跳预言家
    has_prophet_claim = any("预言家" in s.get("content", "") for s in speeches)

    lines.append("【策略建议】")

    if day == 1 and not has_prophet_claim:
        lines.append("第一天还没人跳身份，信息有限。建议：")
        lines.append("- 主动分析每个人的发言态度和逻辑")
        lines.append("- 提出你觉得可疑的点，引导讨论")
        lines.append("- 不要说'先观察'或'等等看'——这对好人没帮助")
    elif day == 1 and has_prophet_claim:
        lines.append("有人跳预言家了。建议：")
        lines.append("- 分析跳预言家的人的逻辑是否可信")
        lines.append("- 如果可信，站边预言家跟票")
        lines.append("- 如果有对跳（两人都说自己是预言家），仔细比较谁的逻辑更扎实")
    else:
        lines.append(f"第{day}天，信息越来越多。建议：")
        lines.append("- 结合前几天的票型和发言分析")
        lines.append("- 关注谁的发言前后矛盾")
        lines.append("- 跟随可信的信息源（预言家/女巫的信息）归票")

    return "\n".join(lines)
