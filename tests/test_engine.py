# tests/test_engine.py
import pytest
from game.state import create_game_state, Player, Speech, NightAction
from game.engine import GameEngine, _resolve_night_deaths, _count_votes


def _make_config():
    return [
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o",
         "provider": "openai", "api_key": "sk-test"}
        for i in range(1, 7)
    ]


def test_engine_initialization():
    engine = GameEngine(_make_config())
    assert engine.state is not None
    assert len(engine.state.players) == 6
    assert engine.state.phase == "game_init"


def test_game_over_wolves_dead():
    state = create_game_state(_make_config())
    for p in state.players:
        if p.role == "werewolf":
            p.is_alive = False
    from game.state import check_game_over
    assert check_game_over(state) == "villager"


def test_game_over_wolves_win():
    state = create_game_state(_make_config())
    for p in state.players:
        if p.role in ("prophet", "witch", "villager"):
            p.is_alive = False
    from game.state import check_game_over
    assert check_game_over(state) == "werewolf"


def test_kill_resolution_no_save():
    """狼人刀3号，女巫不救 → 3号死亡"""
    state = create_game_state(_make_config())
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=1, target_seat=3,
    ))
    deaths = _resolve_night_deaths(state)
    assert 3 in deaths


def test_kill_with_antidote():
    """狼人刀3号，女巫救 → 3号存活"""
    state = create_game_state(_make_config())
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=1, target_seat=3,
    ))
    state.night_actions.append(NightAction(
        action_type="save", actor_seat=4, target_seat=3,
    ))
    deaths = _resolve_night_deaths(state)
    assert 3 not in deaths
    assert state.witch_antidote == 0


def test_kill_with_poison():
    """狼人刀3号，女巫毒5号 → 3号和5号都死亡"""
    state = create_game_state(_make_config())
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=1, target_seat=3,
    ))
    state.night_actions.append(NightAction(
        action_type="poison", actor_seat=4, target_seat=5,
    ))
    deaths = _resolve_night_deaths(state)
    assert 3 in deaths
    assert 5 in deaths
    assert state.witch_poison == 0


def test_vote_count_single_winner():
    """简单多数：3号得3票=唯一候选"""
    votes = {1: 3, 2: 3, 3: 1, 4: 5, 5: 3, 6: 5}
    result = _count_votes(votes)
    assert result["max_count"] == 3
    assert len(result["top_candidates"]) == 1
    assert 3 in result["top_candidates"]


def test_vote_count_tie():
    """平票返回多个候选人"""
    votes = {1: 2, 2: 2, 3: 5, 4: 5, 5: 3, 6: 3}
    result = _count_votes(votes)
    assert len(result["top_candidates"]) > 1


def test_vote_count_all_abstain():
    """全部弃票"""
    votes = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
    result = _count_votes(votes)
    assert result["max_count"] == 0
    assert result["top_candidates"] == []


import asyncio
from unittest.mock import AsyncMock
from game.state import get_alive_players as get_alive_players_local


def _engine():
    return GameEngine(_make_config(), interactive=False)


def test_extract_valid_target_prefers_target_seat():
    e = _engine()
    t = e._extract_valid_target({"thinking": "", "action": "随便说点", "target_seat": 5}, {3, 5})
    assert t == 5


def test_extract_valid_target_fallback_to_regex_when_absent():
    e = _engine()
    t = e._extract_valid_target({"thinking": "", "action": "我投3号"}, {3, 5})
    assert t == 3


def test_extract_valid_target_rejects_illegal():
    e = _engine()
    t = e._extract_valid_target({"thinking": "", "action": "我刀2号", "target_seat": 2}, {3, 5})
    assert t is None


def test_call_ai_with_target_accepts_legal_first_try():
    e = _engine()
    e._call_ai = AsyncMock(return_value={"thinking": "t", "action": "a", "target_seat": 5})
    target, thinking, action = asyncio.run(
        e._call_ai_with_target(1, "prompt", {3, 5}, "投票")
    )
    assert target == 5
    assert e._call_ai.call_count == 1


def test_call_ai_with_target_retries_on_illegal_then_succeeds():
    e = _engine()
    e._call_ai = AsyncMock(side_effect=[
        {"thinking": "t1", "action": "刀2号", "target_seat": 2},   # 非法
        {"thinking": "t2", "action": "刀5号", "target_seat": 5},   # 重试合法
    ])
    target, thinking, action = asyncio.run(
        e._call_ai_with_target(1, "prompt", {3, 5}, "刀人")
    )
    assert target == 5
    assert e._call_ai.call_count == 2


def test_call_ai_with_target_degrades_after_failed_retry():
    e = _engine()
    e._call_ai = AsyncMock(side_effect=[
        {"thinking": "t1", "action": "刀2号", "target_seat": 2},   # 非法
        {"thinking": "t2", "action": "刀2号", "target_seat": 2},   # 重试仍非法
    ])
    target, thinking, action = asyncio.run(
        e._call_ai_with_target(1, "prompt", {3, 5}, "刀人")
    )
    assert target is None        # 降级
    assert e._call_ai.call_count == 2


def test_wolf_cannot_kill_teammate_e2e():
    """狼人首选刀队友 → 被校验拦下并重试，最终不会把队友写进刀杀目标"""
    e = GameEngine(_make_config(), interactive=False)
    state = e.state
    wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    good_non_witch = [p.seat_id for p in state.players
                      if p.role != "werewolf" and p.seat_id != witch_seat][0]

    async def mock_call(seat_id, prompt):
        if seat_id in wolf_seats:
            if "系统提示" in prompt:
                return {"thinking": "改刀", "action": f"刀{good_non_witch}号",
                        "target_seat": good_non_witch}
            teammate = [s for s in wolf_seats if s != seat_id][0]
            return {"thinking": "刀队友", "action": f"刀{teammate}号", "target_seat": teammate}
        return {"thinking": "不动", "action": "不使用任何药", "target_seat": None}

    e._call_ai = mock_call
    asyncio.run(e.run_night())

    kill_actions = [a for a in state.night_actions if a.action_type == "kill"]
    for a in kill_actions:
        assert a.target_seat not in wolf_seats


def test_my_votes_memory_written():
    """投票后 my_votes 应记录到投票者的 private_data"""
    e = GameEngine(_make_config(), interactive=False)
    state = e.state
    alive = get_alive_players_local(state)
    fixed_target = alive[0].seat_id
    voter = alive[1].seat_id

    async def mock_call(seat_id, prompt):
        t = fixed_target if seat_id != fixed_target else voter
        return {"thinking": "投", "action": f"投{t}号", "target_seat": t}

    e._call_ai = mock_call
    asyncio.run(e._run_vote(alive))

    recorded = [p.seat_id for p in state.players
                if state.day in state.private_data[p.seat_id].get("my_votes", {})]
    assert len(recorded) >= 1
