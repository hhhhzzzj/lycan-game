# backend/game/engine.py
"""
游戏引擎：控制狼人杀完整流程。

死亡结算顺序：
1. 狼人刀人 → 2. 女巫救/毒 → 3. 合并死亡名单：[被刀且未被救] + [被毒]
"""
import asyncio
import random
import re
import time
from typing import Any, Dict, List, Optional
from collections import Counter

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

    def __init__(self, player_configs: List[Dict[str, Any]]):
        self.state = create_game_state(player_configs)
        self.player_configs = {cfg["seat_id"]: cfg for cfg in player_configs}
        self.adapters: Dict[int, Any] = {}
        self._on_update = None
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

    async def _push_update(self, extra: Optional[Dict] = None):
        if self._on_update:
            public = get_public_state(self.state)
            if extra:
                public.update(extra)
            await self._on_update(public)

    async def _call_ai(self, seat_id: int, prompt: str) -> Dict[str, str]:
        adapter = self.adapters[seat_id]
        player = get_player(self.state, seat_id)
        system_prompt = f"""你正在玩一局6人狼人杀游戏。你是{player.player_name}，座位号{seat_id}号。
请根据游戏状态做出决策。输出格式为JSON:
{{"thinking": "你的思考过程", "action": "你的行动或发言内容"}}

思考过程用中文，行动/发言内容也要用中文。发言要自然，像真人说话一样。"""
        try:
            response = await adapter.call(system_prompt, prompt)
            return {"thinking": response.thinking, "action": response.action}
        except Exception as e:
            return {"thinking": f"调用失败: {e}", "action": "（无法响应）"}

    async def run_night(self):
        state = self.state
        state.phase = "night"
        state.night_actions = []

        # Reset witch's night_kill_target
        witch_players = [p for p in state.players if p.role == "witch"]
        if witch_players:
            state.private_data[witch_players[0].seat_id]["night_kill_target"] = None

        alive = get_alive_players(state)

        # === 狼人刀人 ===
        wolf_players = [p for p in alive if p.role == "werewolf"]
        wolf_decisions = []
        for wolf in wolf_players:
            handler = get_role_handler("werewolf")
            view = get_player_view(state, wolf.seat_id)
            prompt = handler.get_night_prompt(wolf.player_name, view)
            result = await self._call_ai(wolf.seat_id, prompt)
            wolf_decisions.append({"seat_id": wolf.seat_id, "thinking": result["thinking"], "action": result["action"]})
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号 思考中...",
                "current_thinking": result["thinking"],
            })

        if wolf_decisions:
            chosen = random.choice(wolf_decisions)
            target = self._parse_target(chosen["action"], alive)
            if target:
                state.night_actions.append(NightAction(
                    action_type="kill", actor_seat=chosen["seat_id"], target_seat=target,
                ))
                if witch_players:
                    state.private_data[witch_players[0].seat_id]["night_kill_target"] = target

        # === 预言家验人 ===
        prophet = [p for p in alive if p.role == "prophet"]
        if prophet:
            p = prophet[0]
            handler = get_role_handler("prophet")
            view = get_player_view(state, p.seat_id)
            prompt = handler.get_night_prompt(p.player_name, view)
            result = await self._call_ai(p.seat_id, prompt)
            target = self._parse_target(result["action"], alive)
            if target:
                target_player = get_player(state, target)
                result_text = "狼人" if target_player.role == "werewolf" else "好人"
                state.private_data[p.seat_id]["check_results"][str(target)] = result_text
            await self._push_update({
                "night_info": f"预言家 {p.seat_id}号 查验完毕",
                "current_thinking": result["thinking"],
            })

        # === 女巫用药 ===
        if witch_players:
            w = witch_players[0]
            pd = state.private_data[w.seat_id]
            kill_target = pd.get("night_kill_target")
            if kill_target is not None or state.witch_poison > 0:
                handler = get_role_handler("witch")
                view = get_player_view(state, w.seat_id)
                prompt = handler.get_night_prompt(w.player_name, view)
                result = await self._call_ai(w.seat_id, prompt)
                action_text = result["action"]
                # Check potion availability and parse action
                if "救" in action_text and state.witch_antidote > 0:
                    target = self._parse_target(action_text, state.players)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="save", actor_seat=w.seat_id, target_seat=target,
                        ))
                elif "毒" in action_text and state.witch_poison > 0:
                    target = self._parse_target(action_text, alive)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="poison", actor_seat=w.seat_id, target_seat=target,
                        ))
                await self._push_update({
                    "night_info": f"女巫 {w.seat_id}号 行动完毕",
                    "current_thinking": result["thinking"],
                })

    async def run_day(self):
        state = self.state
        state.phase = "day"

        # 结算夜晚死亡
        deaths = _resolve_night_deaths(state)
        for seat_id in deaths:
            player = get_player(state, seat_id)
            player.is_alive = False
        state.killed_last_night = deaths

        await self._push_update({"phase_info": f"第{state.day}天白天开始"})

        # 宣布死亡 — 先清空当天发言，再追加遗言
        state.speech_history = []
        for seat_id in deaths:
            await self._run_last_words(seat_id)

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
            })

        # === 投票阶段 ===
        await self._run_vote(alive)

        # 平票 → 重投
        vote_result = _count_votes(state.votes)
        if len(vote_result["top_candidates"]) > 1:
            await self._push_update({"phase_info": "平票！进入重投阶段"})
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
                result = await self._call_ai(seat_id, prompt)
                target = self._parse_target(result["action"], alive)
                state.votes[seat_id] = target
                await self._push_update({
                    "current_thinking": result["thinking"],
                    "vote_progress": f"{seat_id}号 已投票",
                })

        # 结算投票
        state.phase = "day"
        final_result = _count_votes(state.votes)
        if len(final_result["top_candidates"]) == 1:
            eliminated = final_result["top_candidates"][0]
            player = get_player(state, eliminated)
            player.is_alive = False
            await self._push_update({
                "phase_info": f"{player.player_name}({eliminated}号) 被放逐！",
            })
            await self._run_last_words(eliminated)
        elif len(final_result["top_candidates"]) > 1:
            await self._push_update({
                "phase_info": "再次平票！本轮流放，无人出局。",
            })

        # 再次检查游戏结束
        winner = check_game_over(state)
        if winner:
            state.winner = winner
            state.phase = "game_over"
            await self._push_update({"phase_info": f"游戏结束! {winner} 胜利!"})

    async def _run_last_words(self, seat_id: int):
        player = get_player(self.state, seat_id)
        handler = get_role_handler(player.role)
        view = get_player_view(self.state, seat_id)
        prompt = handler.get_last_words_prompt(player.player_name, view)
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
        })

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
            result = await self._call_ai(seat_id, prompt)
            target = self._parse_target(result["action"], alive)
            self.state.votes[seat_id] = target
            await self._push_update({
                "current_thinking": result["thinking"],
                "vote_progress": f"{seat_id}号 已投票",
            })

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
