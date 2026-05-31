# backend/game/engine.py
"""
游戏引擎：控制狼人杀完整流程。

死亡结算顺序：
1. 狼人刀人 → 2. 女巫救/毒 → 3. 合并死亡名单：[被刀且未被救] + [被毒]
"""
import asyncio
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional
from collections import Counter

logger = logging.getLogger("werewolf.engine")

from .state import (
    GameState, Player, Speech, NightAction,
    create_game_state, get_player_view, get_public_state,
    get_player, get_alive_players, check_game_over,
)
from .roles.base import get_role_handler
from .llm.adapters import create_adapter


def _resolve_night_deaths(state: GameState) -> List[int]:
    """结算夜晚死亡"""
    deaths = set()
    kill_action = None
    save_action = None
    poison_action = None

    for action in state.night_actions:
        if action.action_type == "kill":
            kill_action = action
        elif action.action_type == "save":
            save_action = action
            state.witch_antidote = 0
        elif action.action_type == "poison":
            poison_action = action
            state.witch_poison = 0

    if kill_action is not None:
        if save_action is None or save_action.target_seat != kill_action.target_seat:
            deaths.add(kill_action.target_seat)

    if poison_action is not None:
        deaths.add(poison_action.target_seat)

    return list(deaths)


def _count_votes(votes: Dict[int, Optional[int]]) -> Dict[str, Any]:
    """统计投票结果"""
    valid = [v for v in votes.values() if v is not None]
    if not valid:
        return {"max_count": 0, "top_candidates": [], "counts": {}}
    counts = Counter(valid)
    max_count = max(counts.values())
    top = [seat for seat, cnt in counts.items() if cnt == max_count]
    return {"max_count": max_count, "top_candidates": top, "counts": dict(counts)}


class GameEngine:
    """狼人杀游戏引擎"""

    def __init__(self, player_configs: List[Dict[str, Any]], interactive: bool = True):
        self.state = create_game_state(player_configs)
        self.player_configs = {cfg["seat_id"]: cfg for cfg in player_configs}
        self.adapters: Dict[int, Any] = {}
        self._on_update = None
        self._interactive = interactive
        self._step_event: Optional[asyncio.Event] = None
        if interactive:
            self._step_event = asyncio.Event()
        self._init_adapters()

    def _init_adapters(self):
        for cfg in self.player_configs.values():
            self.adapters[cfg["seat_id"]] = create_adapter(
                provider=cfg.get("provider", "openai"),
                model=cfg["model_name"],
                api_key=cfg.get("api_key", ""),
                base_url=cfg.get("base_url"),
            )

    def set_on_update(self, callback):
        self._on_update = callback

    def signal_continue(self):
        if self._step_event:
            self._step_event.set()

    async def _wait_step(self):
        if self._step_event:
            await self._step_event.wait()
            self._step_event.clear()

    async def _push_update(self, extra: Optional[Dict] = None, *, waiting: Optional[bool] = None):
        if self._on_update:
            public = get_public_state(self.state)
            if extra:
                public.update(extra)
            public["waiting"] = waiting if waiting is not None else self._interactive
            await self._on_update(public)

    async def _call_ai(self, seat_id: int, prompt: str) -> Dict[str, str]:
        adapter = self.adapters[seat_id]
        player = get_player(self.state, seat_id)
        system_prompt = f"""你正在玩一局6人狼人杀游戏。你是{player.player_name}，座位号{seat_id}号。
请根据游戏状态做出决策。输出格式为JSON:
{{"thinking": "你的思考过程", "action": "你的行动或发言内容"}}

思考过程用中文，行动/发言内容也要用中文。发言要自然，像真人说话一样。"""
        logger.debug(f"[AI输入] {seat_id}号({player.player_name}, {player.role}) 收到的prompt:\n{prompt[:2000]}")
        try:
            response = await adapter.call(system_prompt, prompt)
            logger.debug(f"[AI输出] {seat_id}号 thinking: {response.thinking[:500]}")
            logger.debug(f"[AI输出] {seat_id}号 action: {response.action[:500]}")
            return {
                "thinking": response.thinking,
                "action": response.action,
                "target_seat": response.target_seat,
            }
        except Exception as e:
            logger.error(f"[AI错误] {seat_id}号调用失败: {e}")
            return {"thinking": f"调用失败: {e}", "action": "（无法响应）", "target_seat": None}

    async def run_night(self):
        state = self.state
        state.phase = "night"
        state.night_actions = []
        logger.info("=" * 40)
        logger.info(f"第{state.day}天夜晚降临")
        await self._push_update({"phase_info": f"第{state.day}天夜晚降临"})
        await self._wait_step()

        # Reset witch's night_kill_target
        witch_players = [p for p in state.players if p.role == "witch"]
        if witch_players:
            state.private_data[witch_players[0].seat_id]["night_kill_target"] = None

        alive = get_alive_players(state)

        # === 狼人刀人 ===
        wolf_players = [p for p in alive if p.role == "werewolf"]
        wolf_decisions = []
        for i, wolf in enumerate(wolf_players):
            handler = get_role_handler("werewolf")
            view = get_player_view(state, wolf.seat_id)
            teammates = view["private_data"].get("teammates", [])
            valid = {p.seat_id for p in alive
                     if p.seat_id != wolf.seat_id and p.seat_id not in teammates}
            # Show teammate's earlier decision for coordination (only for 2nd+ wolf)
            teammate_decision = wolf_decisions[0]["action"] if i > 0 else None
            prompt = handler.get_night_prompt(wolf.player_name, view, teammate_decision=teammate_decision)
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号({wolf.player_name}) 思考中...",
                "current_speaker": wolf.seat_id,
            }, waiting=False)
            target, thinking, action = await self._call_ai_with_target(
                wolf.seat_id, prompt, valid, "刀人")
            wolf_decisions.append({"seat_id": wolf.seat_id, "thinking": thinking,
                                   "action": action, "target": target})
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号({wolf.player_name}) 决定刀: {action}",
                "current_thinking": thinking,
                "current_speaker": wolf.seat_id,
            })
            await self._wait_step()

        if wolf_decisions:
            if len(wolf_decisions) >= 2:
                # Wolves coordinate: if both agree on target, use it; otherwise prefer wolf 2's (informed) decision
                target_1 = wolf_decisions[0]["target"]
                target_2 = wolf_decisions[1]["target"]
                if target_1 == target_2 and target_1 is not None:
                    target = target_1
                    actor = wolf_decisions[0]["seat_id"]
                else:
                    target = target_2 or target_1
                    actor = wolf_decisions[1]["seat_id"] if target_2 else wolf_decisions[0]["seat_id"]
            else:
                target = wolf_decisions[0]["target"]
                actor = wolf_decisions[0]["seat_id"]
            if target:
                state.night_actions.append(NightAction(
                    action_type="kill", actor_seat=actor, target_seat=target,
                ))
                logger.info(f"[狼人] 最终刀人目标: {target}号 (由{actor}号决定)")
                # 写入记忆：所有狼记录本晚刀杀目标
                for wp in wolf_players:
                    state.private_data[wp.seat_id].setdefault("kill_history", {})[state.day] = target
                if witch_players:
                    state.private_data[witch_players[0].seat_id]["night_kill_target"] = target
                    logger.info(f"[女巫] 通知刀人目标: {target}号")

        # === 预言家验人 ===
        prophet = [p for p in alive if p.role == "prophet"]
        if prophet:
            p = prophet[0]
            handler = get_role_handler("prophet")
            view = get_player_view(state, p.seat_id)
            prompt = handler.get_night_prompt(p.player_name, view)
            await self._push_update({
                "night_info": f"预言家 {p.seat_id}号({p.player_name}) 思考中...",
                "current_speaker": p.seat_id,
            }, waiting=False)
            valid = {q.seat_id for q in alive if q.seat_id != p.seat_id}
            target, thinking, action = await self._call_ai_with_target(
                p.seat_id, prompt, valid, "查验")
            result = {"thinking": thinking, "action": action}
            check_detail = ""
            if target:
                target_player = get_player(state, target)
                result_text = "狼人" if target_player.role == "werewolf" else "好人"
                state.private_data[p.seat_id]["check_results"][str(target)] = result_text
                logger.info(f"[预言家] 查验{target}号 → {result_text}")
                check_detail = f" → 查验{target}号({target_player.player_name})是{result_text}"
            else:
                logger.info(f"[预言家] 未解析到有效查验目标，原始输出: {result['action'][:100]}")
                check_detail = " → 未选择有效目标"
            await self._push_update({
                "night_info": f"预言家 {p.seat_id}号({p.player_name}) 查验{check_detail}",
                "current_thinking": result["thinking"],
                "current_speaker": p.seat_id,
            })
            await self._wait_step()

        # === 女巫用药 ===
        if witch_players:
            w = witch_players[0]
            pd = state.private_data[w.seat_id]
            kill_target = pd.get("night_kill_target")
            if kill_target is not None or state.witch_poison > 0:
                handler = get_role_handler("witch")
                view = get_player_view(state, w.seat_id)
                prompt = handler.get_night_prompt(w.player_name, view)
                await self._push_update({
                    "night_info": f"女巫 {w.seat_id}号({w.player_name}) 思考中...",
                    "current_speaker": w.seat_id,
                }, waiting=False)
                result = await self._call_ai(w.seat_id, prompt)
                action_text = result["action"]
                witch_action_desc = ""
                if "救" in action_text and state.witch_antidote > 0:
                    target = self._parse_target(action_text, state.players)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="save", actor_seat=w.seat_id, target_seat=target,
                        ))
                        state.witch_antidote = 0
                        state.private_data[w.seat_id]["antidote_remaining"] = 0
                        state.private_data[w.seat_id].setdefault("potion_history", []).append(
                            {"day": state.day, "type": "save", "target": target})
                        logger.info(f"[女巫] 使用解药救{target}号 (毒药剩余:{state.witch_poison})")
                        witch_action_desc = f"使用解药救 {target}号"
                if not witch_action_desc and "毒" in action_text and state.witch_poison > 0:
                    valid = {q.seat_id for q in alive if q.seat_id != w.seat_id}
                    target = self._extract_valid_target(result, valid)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="poison", actor_seat=w.seat_id, target_seat=target,
                        ))
                        state.witch_poison = 0
                        state.private_data[w.seat_id]["poison_remaining"] = 0
                        state.private_data[w.seat_id].setdefault("potion_history", []).append(
                            {"day": state.day, "type": "poison", "target": target})
                        logger.info(f"[女巫] 使用毒药毒{target}号 (解药剩余:{state.witch_antidote})")
                        witch_action_desc = f"使用毒药毒 {target}号"
                if not witch_action_desc:
                    logger.info(f"[女巫] 不使用任何药 (解药剩余:{state.witch_antidote}, 毒药剩余:{state.witch_poison})")
                    witch_action_desc = "不使用任何药"
                logger.info(f"[女巫] 原始决策文本: {action_text[:120]}")
                await self._push_update({
                    "night_info": f"女巫 {w.seat_id}号({w.player_name}): {witch_action_desc}",
                    "current_thinking": result["thinking"],
                    "current_speaker": w.seat_id,
                })
                await self._wait_step()

    async def run_day(self):
        state = self.state
        state.phase = "day"

        # 结算夜晚死亡
        deaths = _resolve_night_deaths(state)
        logger.info(f"[死亡结算] 夜晚死亡名单: {deaths}")
        for seat_id in deaths:
            player = get_player(state, seat_id)
            logger.info(f"[死亡结算] {seat_id}号 {player.player_name} ({player.role}) 死亡")
            player.is_alive = False
        state.killed_last_night = deaths

        # 生成夜晚公告
        if not deaths:
            state.night_summary = f"昨晚是平安夜，无人死亡。"
        else:
            dead_names = "、".join(f"{sid}号({get_player(state, sid).player_name})" for sid in deaths)
            state.night_summary = f"昨晚{dead_names}死亡。"

        # 记录每个角色的夜间行动（用于白天 prompt）
        for action in state.night_actions:
            pd = state.private_data.get(action.actor_seat, {})
            if action.action_type == "save":
                state.night_summary = f"昨晚狼人刀了{action.target_seat}号，但被女巫救活，无人死亡。"
                pd["last_night_action"] = f"使用解药救了 {action.target_seat}号"
            elif action.action_type == "poison":
                pd["last_night_action"] = f"使用毒药毒杀了 {action.target_seat}号"
            elif action.action_type == "kill":
                pd["last_night_action"] = f"和队友一起刀了 {action.target_seat}号"
        # 为预言家记录查验结果
        prophet = [p for p in state.players if p.role == "prophet"]
        if prophet:
            pd = state.private_data.get(prophet[0].seat_id, {})
            checks = pd.get("check_results", {})
            if checks:
                last_check = list(checks.items())[-1]
                pd["last_night_action"] = f"查验{last_check[0]}号，结果是{last_check[1]}"
        # 为女巫记录不使用药
        if not deaths and not any(a.action_type in ("save", "poison") for a in state.night_actions):
            for p in state.players:
                if p.role == "witch":
                    pd = state.private_data.get(p.seat_id, {})
                    if not pd.get("last_night_action"):
                        pd["last_night_action"] = "未使用任何药"

        logger.info(f"[夜晚公告] {state.night_summary}")

        await self._push_update({"phase_info": f"第{state.day}天白天开始 - {state.night_summary}"})
        await self._wait_step()

        # 宣布死亡 — 先清空当天发言，再追加遗言
        state.speech_history = []
        for seat_id in deaths:
            await self._run_last_words(seat_id, "night_kill")

        # 检查游戏结束
        winner = check_game_over(state)
        if winner:
            state.winner = winner
            state.phase = "game_over"
            await self._push_update({"phase_info": f"游戏结束! {winner} 胜利!"})
            return

        alive = get_alive_players(state)

        # === 发言阶段 ===
        for seat_id in state.speaker_order:
            player = get_player(state, seat_id)
            if not player.is_alive:
                continue
            handler = get_role_handler(player.role)
            view = get_player_view(state, seat_id)
            prompt = handler.get_day_speech_prompt(player.player_name, view)
            await self._push_update({
                "current_speaker": seat_id,
                "phase_info": f"第{state.day}天 - {player.player_name}({seat_id}号) 思考发言中...",
            }, waiting=False)
            result = await self._call_ai(seat_id, prompt)
            speech = Speech(
                seat_id=seat_id,
                player_name=player.player_name,
                content=result["action"],
                thinking=result["thinking"],
                timestamp=time.time(),
            )
            state.speech_history.append(speech)
            state.full_history.append(speech)
            await self._push_update({
                "current_speaker": seat_id,
                "current_thinking": result["thinking"],
                "current_speech": result["action"],
                "phase_info": f"第{state.day}天 - {player.player_name}({seat_id}号) 发言",
            })
            await self._wait_step()

        # === 投票阶段 ===
        await self._run_vote(alive)

        # 平票 → 重投
        vote_result = _count_votes(state.votes)
        await self._push_update({"phase_info": f"投票结果: {vote_result['counts']}"})
        await self._wait_step()
        if len(vote_result["top_candidates"]) > 1:
            await self._push_update({"phase_info": "平票！进入重投阶段"})
            await self._wait_step()
            state.phase = "revote"
            state.votes = {}
            alive = get_alive_players(state)
            for seat_id in state.speaker_order:
                player = get_player(state, seat_id)
                if not player.is_alive:
                    continue
                handler = get_role_handler(player.role)
                view = get_player_view(state, seat_id)
                prompt = handler.get_vote_prompt(player.player_name, view)
                await self._push_update({
                    "vote_progress": f"{seat_id}号({player.player_name}) 思考重投中...",
                    "current_speaker": seat_id,
                }, waiting=False)
                valid = {q.seat_id for q in state.players
                         if q.is_alive and q.seat_id != seat_id}
                target, thinking, action = await self._call_ai_with_target(
                    seat_id, prompt, valid, "投票")
                state.votes[seat_id] = target
                if target is not None:
                    state.private_data[seat_id].setdefault("my_votes", {})[state.day] = target
                await self._push_update({
                    "current_thinking": thinking,
                    "vote_progress": f"{seat_id}号({player.player_name}) 已投票",
                    "current_speaker": seat_id,
                })
                await self._wait_step()

        # 结算投票
        state.phase = "day"
        final_result = _count_votes(state.votes)
        await self._push_update({"phase_info": f"重投结果: {final_result['counts']}"})
        await self._wait_step()
        if len(final_result["top_candidates"]) == 1:
            eliminated = final_result["top_candidates"][0]
            player = get_player(state, eliminated)
            player.is_alive = False
            await self._push_update({
                "phase_info": f"{player.player_name}({eliminated}号) 被放逐！",
            })
            await self._wait_step()
            await self._run_last_words(eliminated, "vote_eliminated")
        elif len(final_result["top_candidates"]) > 1:
            await self._push_update({
                "phase_info": "再次平票！本轮流放，无人出局。",
            })
            await self._wait_step()

        # 再次检查游戏结束
        winner = check_game_over(state)
        if winner:
            state.winner = winner
            state.phase = "game_over"
            await self._push_update({"phase_info": f"游戏结束! {winner} 胜利!"})

    async def _run_last_words(self, seat_id: int, reason: str = "night_kill"):
        player = get_player(self.state, seat_id)
        handler = get_role_handler(player.role)
        view = get_player_view(self.state, seat_id)
        prompt = handler.get_last_words_prompt(player.player_name, view, reason)
        await self._push_update({
            "current_speaker": seat_id,
            "phase_info": f"{player.player_name}({seat_id}号) 思考遗言中...",
        }, waiting=False)
        result = await self._call_ai(seat_id, prompt)
        speech = Speech(
            seat_id=seat_id,
            player_name=player.player_name,
            content=f"[遗言] {result['action']}",
            thinking=result["thinking"],
            timestamp=time.time(),
        )
        self.state.speech_history.append(speech)
        self.state.full_history.append(speech)
        await self._push_update({
            "current_speaker": seat_id,
            "current_thinking": result["thinking"],
            "current_speech": f"[遗言] {result['action']}",
            "phase_info": f"{player.player_name}({seat_id}号) 发表遗言",
        })
        await self._wait_step()

    async def _run_vote(self, alive: List[Player]):
        self.state.phase = "vote"
        self.state.votes = {}
        for seat_id in self.state.speaker_order:
            player = get_player(self.state, seat_id)
            if not player.is_alive:
                continue
            handler = get_role_handler(player.role)
            view = get_player_view(self.state, seat_id)
            prompt = handler.get_vote_prompt(player.player_name, view)
            await self._push_update({
                "vote_progress": f"{seat_id}号({player.player_name}) 思考投票中...",
                "current_speaker": seat_id,
            }, waiting=False)
            valid = {q.seat_id for q in self.state.players
                     if q.is_alive and q.seat_id != seat_id}
            target, thinking, action = await self._call_ai_with_target(
                seat_id, prompt, valid, "投票")
            self.state.votes[seat_id] = target
            if target is not None:
                self.state.private_data[seat_id].setdefault("my_votes", {})[self.state.day] = target
            await self._push_update({
                "current_thinking": thinking,
                "vote_progress": f"{seat_id}号({player.player_name}) 已投票",
                "current_speaker": seat_id,
            })
            await self._wait_step()

    async def run_game(self):
        state = self.state
        await self._push_update()
        # Standard werewolf flow: Night 1 → Day 1 → Night 2 → Day 2 → ...
        while state.phase != "game_over":
            state.day += 1
            # Night phase
            await self.run_night()
            await self._push_update()
            if state.phase == "game_over":
                break
            # Day phase
            await self.run_day()
            await self._push_update()
        await self._push_update({"phase_info": f"游戏结束! 胜利方: {state.winner}"})

    def _parse_target(self, text: str, players: List[Player]) -> Optional[int]:
        """从文本中解析目标座位号"""
        # Try "X号" pattern first
        matches = re.findall(r'(\d+)\s*号', text)
        if matches:
            seat = int(matches[0])
            if 1 <= seat <= 6:
                return seat
        # Try standalone digit 1-6
        matches = re.findall(r'\b([1-6])\b', text)
        if matches:
            return int(matches[0])
        return None

    def _extract_valid_target(self, result: Dict[str, Any], valid_targets) -> Optional[int]:
        """优先取结构化 target_seat，缺失则正则 fallback；校验是否在合法集合内。"""
        target = result.get("target_seat")
        if target is None:
            target = self._parse_target(result.get("action", "") or "", [])
        if target in valid_targets:
            return target
        return None

    async def _call_ai_with_target(self, seat_id: int, prompt: str, valid_targets, action_name: str):
        """调用 AI 并校验目标合法性；非法则带原因重试 1 次，仍失败则降级(target=None)。
        返回 (target, thinking, action)。"""
        result = await self._call_ai(seat_id, prompt)
        target = self._extract_valid_target(result, valid_targets)
        if target is not None:
            return target, result["thinking"], result["action"]

        # 重试 1 次，反馈具体非法选择
        chosen = result.get("target_seat")
        if chosen is None:
            chosen = self._parse_target(result.get("action", "") or "", [])
        valid_list = "、".join(f"{s}号" for s in sorted(valid_targets))
        retry_prompt = (
            prompt
            + f"\n\n【系统提示】你刚才选择的 {chosen}号 不是合法的{action_name}目标。"
            + f"请只从以下合法目标中选择：{valid_list}。"
            + "并把座位号填入 target_seat 字段。"
        )
        logger.info(f"[校验] {seat_id}号 {action_name} 选择非法({chosen})，重试 1 次")
        result = await self._call_ai(seat_id, retry_prompt)
        target = self._extract_valid_target(result, valid_targets)
        if target is None:
            logger.info(f"[校验] {seat_id}号 {action_name} 重试仍非法，降级处理")
        return target, result["thinking"], result["action"]
