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
