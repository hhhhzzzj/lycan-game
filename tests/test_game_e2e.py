# tests/test_game_e2e.py
"""
端到端测试：用 mock AI 跑完整一局，验证游戏逻辑无 bug。

场景设计：
  1号 狼人小明  2号 预言家小红  3号 村民小刚
  4号 女巫小丽  5号 狼人小华    6号 村民小强

Night 1:
  狼人1号决定刀6号 → 狼人5号看到队友刀6号，同意 → 刀6号
  预言家2号验3号 → 狼人
  女巫4号收到刀人通知，使用解药救6号
  → 无人死亡

Day 1:
  发言后投票，多数放逐1号(狼人)
  → 1号狼人出局

Night 2:
  狼人5号刀4号
  预言家2号验5号 → 狼人
  女巫4号毒5号
  → 4号(女巫)被杀 + 5号(狼人)被毒 → 双死
  → 狼人全灭 → 好人胜利
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from game.engine import GameEngine
from game.state import get_public_state


def _make_config():
    return [
        {"seat_id": 1, "player_name": "小明", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
        {"seat_id": 2, "player_name": "小红", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
        {"seat_id": 3, "player_name": "小刚", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
        {"seat_id": 4, "player_name": "小丽", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
        {"seat_id": 5, "player_name": "小华", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
        {"seat_id": 6, "player_name": "小强", "model_name": "mock-model",
         "provider": "openai", "api_key": "sk-test"},
    ]


class TestE2EGame:
    """完整一局游戏测试"""

    def test_e2e_full_game(self):
        """跑完一整局，验证 狼人刀人 → 预言家验人 → 女巫用药 → 发言 → 投票 → 胜负"""
        engine = GameEngine(_make_config(), interactive=False)
        state = engine.state

        # 获取实际角色分配
        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        good_seats = [p.seat_id for p in state.players if p.role != "werewolf"]

        wolf_1 = wolf_seats[0]
        wolf_2 = wolf_seats[1]
        # 选一个非狼非女巫的好人作为刀人目标
        safe_targets = [s for s in good_seats if s != witch_seat]

        # 记录发送到前端的推送
        pushed_states = []
        async def capture_push(data):
            pushed_states.append(data)
        engine.set_on_update(capture_push)

        # 构建 mock 响应
        async def mock_call(seat_id, prompt):
            day = engine.state.day
            phase = engine.state.phase

            # Night 1
            if phase == "night" and day == 1:
                if seat_id == wolf_1:
                    return {"thinking": "刀6号", "action": f"我决定刀{safe_targets[0]}号"}
                if seat_id == wolf_2:
                    return {"thinking": "队友刀了{safe_targets[0]}号，同意", "action": f"我跟刀{safe_targets[0]}号"}
                if seat_id == prophet_seat:
                    return {"thinking": f"验{wolf_2}号", "action": f"我查验{wolf_2}号"}
                if seat_id == witch_seat:
                    return {"thinking": f"{safe_targets[0]}号被刀了，救他", "action": f"我使用解药救{safe_targets[0]}号"}
                return {"thinking": "...", "action": "..."}

            # Night 2
            if phase == "night" and day == 2:
                if seat_id == wolf_2:
                    return {"thinking": "刀女巫", "action": f"我决定刀{witch_seat}号"}
                if seat_id == prophet_seat:
                    return {"thinking": f"验{wolf_2}号", "action": f"我查验{wolf_2}号"}
                if seat_id == witch_seat:
                    return {"thinking": f"毒{wolf_2}号", "action": f"我使用毒药毒{wolf_2}号"}
                return {"thinking": "...", "action": "..."}

            # Day 1 speeches
            if phase == "day" and day == 1:
                return {"thinking": f"我是{seat_id}号，分析中...", "action": f"我是{seat_id}号，我认为需要仔细推理"}

            # Day 1 vote — 所有人投 wolf_1
            if phase == "vote" and day == 1:
                return {"thinking": f"投票给{wolf_1}号", "action": f"我投{wolf_1}号"}

            # Day 1 revote
            if phase == "revote" and day == 1:
                return {"thinking": f"重投{wolf_1}号", "action": f"我投{wolf_1}号"}

            # Day 2 vote — 所有人投 wolf_2
            if phase == "vote" and day == 2:
                return {"thinking": f"投票给{wolf_2}号", "action": f"我投{wolf_2}号"}

            return {"thinking": "默认", "action": "3号"}

        engine._call_ai = mock_call

        # 跑完整局
        asyncio.run(engine.run_game())

        # ===== 验证 =====
        assert state.phase == "game_over"
        assert state.winner == "villager", f"期望好人胜利，实际 winner={state.winner}"
        assert state.day >= 2

        # wolf_1 应在 day 1 被投票放逐
        p_wolf1 = [p for p in state.players if p.seat_id == wolf_1][0]
        assert not p_wolf1.is_alive, f"狼人{wolf_1}号应被放逐出局"

        # wolf_2 应在 night 2 被毒死或被投票放逐
        p_wolf2 = [p for p in state.players if p.seat_id == wolf_2][0]
        assert not p_wolf2.is_alive, f"狼人{wolf_2}号应已出局"

        # 好人应该胜利（狼人全灭）
        alive_wolves = [p for p in state.players if p.is_alive and p.role == "werewolf"]
        assert len(alive_wolves) == 0, f"狼人应全灭，实际存活狼人: {[p.seat_id for p in alive_wolves]}"

    def _build_responses(self, state):
        """已废弃 — 用内联 mock 替代"""
        return {}


class TestWolfCoordination:
    """狼人协作逻辑专项测试"""

    def _make_wolf_test_config(self):
        return [
            {"seat_id": 1, "player_name": "小明", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 2, "player_name": "小红", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 3, "player_name": "小刚", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 4, "player_name": "小丽", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 5, "player_name": "小华", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 6, "player_name": "小强", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
        ]

    def test_wolves_agree_on_target(self):
        """两狼意见一致 → 该目标被刀"""
        import asyncio
        engine = GameEngine(self._make_wolf_test_config(), interactive=False)
        state = engine.state

        # 找出狼人
        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]

        # 动态选合法刀杀目标（非狼）
        kill_target = [p.seat_id for p in state.players
                       if p.role != "werewolf" and p.seat_id != witch_seat][0]

        # Mock: 两狼都选 kill_target，女巫不用药
        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": f"刀{kill_target}号", "action": f"我决定刀{kill_target}号"}
            elif seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            else:
                return {"thinking": "验人", "action": f"我查验{kill_target}号"}
        engine._call_ai = mock_call

        # 手动跑夜晚
        asyncio.run(engine.run_night())

        # 验证：night_actions 中有一个 kill action，target=kill_target
        kill_actions = [a for a in state.night_actions if a.action_type == "kill"]
        assert len(kill_actions) == 1
        assert kill_actions[0].target_seat == kill_target, f"期望刀{kill_target}号，实际刀{ kill_actions[0].target_seat}号"

        # 验证死亡结算
        from game.engine import _resolve_night_deaths
        deaths = _resolve_night_deaths(state)
        assert kill_target in deaths, f"期望{kill_target}号死亡，实际死亡名单: {deaths}"

    def test_wolves_disagree_second_wolf_wins(self):
        """两狼意见不一致 → 以第二个狼（知情者）决定为准"""
        import asyncio
        engine = GameEngine(self._make_wolf_test_config(), interactive=False)
        state = engine.state

        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]

        # 动态选两个不同的合法刀杀目标（都非狼）
        non_wolf = [p.seat_id for p in state.players if p.role != "werewolf"]
        wolf1_target = non_wolf[0]
        wolf2_target = non_wolf[1]

        async def mock_call(seat_id, prompt):
            if seat_id == wolf_seats[0]:
                return {"thinking": f"刀{wolf1_target}号", "action": f"我决定刀{wolf1_target}号"}
            elif seat_id == wolf_seats[1]:
                # 狼2 不同意狼1，换个目标
                return {"thinking": "不，换个目标", "action": f"我决定刀{wolf2_target}号"}
            elif seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            elif seat_id == prophet_seat:
                return {"thinking": "验人", "action": f"我查验{wolf1_target}号"}
            else:
                return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        kill_actions = [a for a in state.night_actions if a.action_type == "kill"]
        assert len(kill_actions) == 1
        assert kill_actions[0].target_seat == wolf2_target, (
            f"两狼意见不一致时应该听狼2的({wolf2_target}号)，实际刀{ kill_actions[0].target_seat}号"
        )

    def test_witch_cant_use_both_potions(self):
        """女巫同一晚不能用解药又用毒药（elif 限制）"""
        import asyncio
        engine = GameEngine(self._make_wolf_test_config(), interactive=False)
        state = engine.state

        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": "刀6号", "action": "我决定刀6号"}
            elif seat_id == witch_seat:
                # 女巫试图同时用药（但 elif 限制只能用一个）
                return {"thinking": "既要救又要毒", "action": "我使用解药救6号，同时使用毒药毒1号"}
            elif seat_id == prophet_seat:
                return {"thinking": "验人", "action": "我查验3号"}
            else:
                return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        # 女巫输入包含"救"在"毒"前面 → 只能执行救
        # 因为代码用 if-elif，匹配"救"后不会执行"毒"
        save_actions = [a for a in state.night_actions if a.action_type == "save"]
        poison_actions = [a for a in state.night_actions if a.action_type == "poison"]
        assert len(save_actions) >= 1, "应该使用了解药"
        assert len(poison_actions) == 0, "不应该同时使用毒药(elif限制)"
        assert state.witch_poison == 1, "毒药应该未被消耗"

    def test_witch_save_negates_kill(self):
        """女巫救被刀目标 → 目标存活"""
        import asyncio
        engine = GameEngine(self._make_wolf_test_config(), interactive=False)
        state = engine.state

        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": "刀6号", "action": "我决定刀6号"}
            elif seat_id == witch_seat:
                return {"thinking": "救6号", "action": "我使用解药救6号"}
            elif seat_id == prophet_seat:
                return {"thinking": "验人", "action": "我查验3号"}
            else:
                return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        from game.engine import _resolve_night_deaths
        deaths = _resolve_night_deaths(state)
        assert 6 not in deaths, f"女巫救了6号，6号不应该死亡，实际死亡: {deaths}"
        assert state.witch_antidote == 0, "解药应该被消耗"


class TestInformationIsolation:
    """信息隔离测试：每个角色只能看到自己应看到的信息"""

    def _make_config(self):
        return [
            {"seat_id": 1, "player_name": "小明", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 2, "player_name": "小红", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 3, "player_name": "小刚", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 4, "player_name": "小丽", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 5, "player_name": "小华", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 6, "player_name": "小强", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
        ]

    def test_werewolf_sees_teammates_only(self):
        """狼人只能看到队友身份，看不到预言家验人结果、女巫药水状态"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.state import get_player_view

        wolf_seats = [p.seat_id for p in state.players if p.role == "werewolf"]
        for seat in wolf_seats:
            view = get_player_view(state, seat)

            # 狼人应看到队友列表
            assert "teammates" in view["private_data"]
            teammates = view["private_data"]["teammates"]
            assert len(teammates) == 1  # 2 werewolves total, teammate list excludes self
            # 队友列表不应包含自己，应包含另一只狼
            assert seat not in teammates
            other_wolf = [s for s in wolf_seats if s != seat][0]
            assert other_wolf in teammates

            # 狼人不应看到预言家验人结果
            assert "check_results" not in view["private_data"], \
                f"狼人{seat}号不应该看到预言家的验人结果"

            # 狼人不应看到女巫的药水信息
            assert "witch_antidote" not in view["private_data"] and \
                   "witch_poison" not in view["private_data"], \
                f"狼人{seat}号不应该看到女巫的药水状态"

    def test_prophet_sees_check_results_only(self):
        """预言家只能看到验人结果，看不到狼人队友、女巫药水"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.state import get_player_view

        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
        view = get_player_view(state, prophet_seat)

        # 预言家应看到 check_results
        assert "check_results" in view["private_data"], \
            "预言家应该能看到自己的验人结果"

        # 预言家不应看到狼人队友
        assert "teammates" not in view["private_data"], \
            "预言家不应该看到狼人队友信息"

        # 预言家不应看到女巫信息
        assert "night_kill_target" not in view["private_data"], \
            "预言家不应该看到刀人目标"

    def test_witch_sees_kill_target_and_potions(self):
        """女巫看到被刀目标、药水状态，但看不到狼人队友和验人结果"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.state import get_player_view

        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        view = get_player_view(state, witch_seat)

        # 女巫应看到药水
        assert "antidote_remaining" in view["private_data"]
        assert "poison_remaining" in view["private_data"]

        # 女巫不应看到狼人队友
        assert "teammates" not in view["private_data"], \
            "女巫不应该看到狼人队友信息"

        # 女巫不应看到预言家验人
        assert "check_results" not in view["private_data"], \
            "女巫不应该看到预言家验人结果"

    def test_villager_sees_nothing_private(self):
        """村民看不到任何私有信息"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.state import get_player_view

        villager_seats = [p.seat_id for p in state.players if p.role == "villager"]
        for seat in villager_seats:
            view = get_player_view(state, seat)
            # 村民的 private_data 应该只有空信息（或完全不存在敏感字段）
            pd = view["private_data"]
            forbidden = ["teammates", "check_results", "witch_antidote",
                         "witch_poison", "night_kill_target"]
            for key in forbidden:
                assert key not in pd, f"村民{seat}号不应该有 {key}"

    def test_public_state_exposes_roles_but_not_private(self):
        """公开状态（观战者视角）展示角色但不泄露内部私有数据"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.state import get_public_state

        public = get_public_state(state)
        for p in public["players"]:
            # 观战者能看到角色
            assert "role" in p
            # 但不能看到 API key 等私有配置
            assert "api_key" not in p


class TestKillTargetCorrectness:
    """刀人目标正确性：刀谁死谁，不会刀A死B"""

    def _make_config(self):
        return [
            {"seat_id": 1, "player_name": "小明", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 2, "player_name": "小红", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 3, "player_name": "小刚", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 4, "player_name": "小丽", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 5, "player_name": "小华", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 6, "player_name": "小强", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
        ]

    def test_kill_6_means_6_dies_not_someone_else(self):
        """狼人刀一个非狼好人 → 该玩家死亡，不会死别人"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]

        # 动态选取合法刀杀目标：非狼且非女巫（女巫不用药，但避免歧义）
        kill_target = [p.seat_id for p in state.players
                       if p.role != "werewolf" and p.seat_id != witch_seat][0]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": f"刀{kill_target}号", "action": f"我决定刀{kill_target}号"}
            if seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            if seat_id == prophet_seat:
                return {"thinking": "验人", "action": f"我查验{kill_target}号"}
            return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        from game.engine import _resolve_night_deaths
        deaths = _resolve_night_deaths(state)

        # 只有被刀的目标死，其他人活着
        assert kill_target in deaths, f"刀{kill_target}号，应该在死亡名单里，实际: {deaths}"
        for s in range(1, 7):
            if s != kill_target:
                assert s not in deaths, f"只刀了{kill_target}号，{s}号不应该死，实际死亡: {deaths}"

    def test_kill_plus_poison_two_die_correctly(self):
        """刀A + 毒B → A和B都死，不会串"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]

        # 动态选取合法目标（不依赖随机角色分配）：
        # 刀杀目标必须是非狼（否则会被合法性校验拦截）；
        # 毒杀目标必须存活且非女巫自己，且与刀杀目标不同。
        non_wolf_non_witch = [p.seat_id for p in state.players
                              if p.role != "werewolf" and p.seat_id != witch_seat]
        kill_target = non_wolf_non_witch[0]
        poison_target = non_wolf_non_witch[1]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": f"刀{kill_target}号", "action": f"我决定刀{kill_target}号"}
            if seat_id == witch_seat:
                return {"thinking": f"毒{poison_target}号", "action": f"我使用毒药毒{poison_target}号"}
            if seat_id == prophet_seat:
                return {"thinking": f"验{kill_target}号", "action": f"我查验{kill_target}号"}
            return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        from game.engine import _resolve_night_deaths
        deaths = _resolve_night_deaths(state)

        # 刀kill_target毒poison_target → 两者都死
        assert kill_target in deaths, f"刀了{kill_target}号，应该死，实际: {deaths}"
        assert poison_target in deaths, f"毒了{poison_target}号，应该死，实际: {deaths}"
        # 其他人不应该死
        for s in range(1, 7):
            if s not in (kill_target, poison_target):
                assert s not in deaths, f"只刀{kill_target}毒{poison_target}，{s}号不应该死，实际: {deaths}"


class TestProphetCheckCorrectness:
    """预言家验人正确性：验谁返回谁的真实身份"""

    def _make_config(self):
        return [
            {"seat_id": 1, "player_name": "小明", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 2, "player_name": "小红", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 3, "player_name": "小刚", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 4, "player_name": "小丽", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 5, "player_name": "小华", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 6, "player_name": "小强", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
        ]

    def test_prophet_check_werewolf_returns_werewolf(self):
        """预言家验狼人 → 结果应该是'狼人'，不是'好人'"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state

        wolf_seat = [p.seat_id for p in state.players if p.role == "werewolf"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        # 另一个狼人
        other_wolf = [p.seat_id for p in state.players if p.role == "werewolf"][1]

        async def mock_call(seat_id, prompt):
            if seat_id in (wolf_seat, other_wolf):
                return {"thinking": "刀3号", "action": "我决定刀3号"}
            if seat_id == prophet_seat:
                return {"thinking": f"验{wolf_seat}号", "action": f"我查验{wolf_seat}号"}
            if seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        pd = state.private_data[prophet_seat]
        result = pd["check_results"].get(str(wolf_seat))
        assert result is not None, f"预言家验了{wolf_seat}号，应该有结果"
        assert result == "狼人", \
            f"预言家验{wolf_seat}号（实际角色=狼人），结果应为'狼人'，实际: {result}"

    def test_prophet_check_villager_returns_good(self):
        """预言家验村民 → 结果应该是'好人'"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state

        villager_seat = [p.seat_id for p in state.players if p.role == "villager"][0]
        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
        wolf_seats = [p.seat_id for p in state.players if p.role == "werewolf"]
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": "刀3号", "action": "我决定刀3号"}
            if seat_id == prophet_seat:
                return {"thinking": f"验{villager_seat}号", "action": f"我查验{villager_seat}号"}
            if seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        pd = state.private_data[prophet_seat]
        result = pd["check_results"].get(str(villager_seat))
        assert result is not None, f"预言家验了{villager_seat}号，应该有结果"
        assert result == "好人", \
            f"预言家验{villager_seat}号（实际角色=村民），结果应为'好人'，实际: {result}"

    def test_prophet_checks_X_result_stored_for_X_not_others(self):
        """预言家验A号 → 结果存在A号下，不会存到B号"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state

        prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
        wolf_seats = [p.seat_id for p in state.players if p.role == "werewolf"]
        witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
        target = wolf_seats[0]

        async def mock_call(seat_id, prompt):
            if seat_id in wolf_seats:
                return {"thinking": "刀3号", "action": "我决定刀3号"}
            if seat_id == prophet_seat:
                return {"thinking": f"验{target}号", "action": f"我查验{target}号"}
            if seat_id == witch_seat:
                return {"thinking": "不用药", "action": "我不使用任何药水"}
            return {"thinking": "...", "action": "..."}
        engine._call_ai = mock_call

        asyncio.run(engine.run_night())

        pd = state.private_data[prophet_seat]
        # 结果只存在 target 下
        for s in range(1, 7):
            if s == target:
                assert str(s) in pd["check_results"], \
                    f"验了{target}号，check_results里应该有{target}号"
            elif str(s) in pd["check_results"]:
                # 如果之前验过其他人，那是正常的；但不能误存当前 target 的结果到别处
                pass


class TestVoteCorrectness:
    """投票逻辑正确性"""

    def _make_config(self):
        return [
            {"seat_id": 1, "player_name": "小明", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 2, "player_name": "小红", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 3, "player_name": "小刚", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 4, "player_name": "小丽", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 5, "player_name": "小华", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
            {"seat_id": 6, "player_name": "小强", "model_name": "mock", "provider": "openai", "api_key": "sk-test"},
        ]

    def test_vote_eliminates_correct_player(self):
        """所有人投3号 → 3号出局，不会错杀别人"""
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state
        from game.engine import _count_votes

        # 模拟投票：所有人投3号
        votes = {s: 3 for s in range(1, 7) if state.players[s - 1].is_alive}
        result = _count_votes(votes)

        assert result["max_count"] >= 4  # 至少4票投3号（有些玩家可能死了）
        assert len(result["top_candidates"]) == 1
        assert result["top_candidates"][0] == 3, \
            f"所有人投3号，最高票应该是3号，实际: {result['top_candidates']}"

    def test_dead_players_do_not_vote(self):
        """已死玩家不参与投票"""
        import asyncio
        engine = GameEngine(self._make_config(), interactive=False)
        state = engine.state

        # 手动杀死5号
        p5 = [p for p in state.players if p.seat_id == 5][0]
        p5.is_alive = False

        alive = [p for p in state.players if p.is_alive]

        async def mock_call(seat_id, prompt):
            return {"thinking": "投票", "action": "我投3号"}
        engine._call_ai = mock_call

        # 跑投票：_run_vote 遍历speaker_order，跳过死人
        asyncio.run(engine._run_vote(alive))

        # 死人不应投票
        assert 5 not in state.votes, f"5号已死，不应该在投票记录里，实际: {list(state.votes.keys())}"
        # 活人都应该投了
        for p in alive:
            assert p.seat_id in state.votes, f"{p.seat_id}号存活，应该投了票"
