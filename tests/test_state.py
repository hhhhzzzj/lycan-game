# tests/test_state.py
import pytest
from game.state import (
    Player, GameState, Speech, NightAction, create_game_state,
    get_player_view, get_public_state
)


def test_create_game_state():
    state = create_game_state([
        {"seat_id": 1, "player_name": "玩家1", "model_name": "gpt-4o"},
        {"seat_id": 2, "player_name": "玩家2", "model_name": "gpt-4o"},
        {"seat_id": 3, "player_name": "玩家3", "model_name": "gpt-4o"},
        {"seat_id": 4, "player_name": "玩家4", "model_name": "gpt-4o"},
        {"seat_id": 5, "player_name": "玩家5", "model_name": "gpt-4o"},
        {"seat_id": 6, "player_name": "玩家6", "model_name": "gpt-4o"},
    ])
    assert len(state.players) == 6
    assert state.phase == "game_init"
    assert state.day == 0
    assert len(state.speaker_order) == 6
    assert state.winner is None

    roles = [p.role for p in state.players]
    assert roles.count("werewolf") == 2
    assert roles.count("villager") == 2
    assert roles.count("prophet") == 1
    assert roles.count("witch") == 1

    assert [p.seat_id for p in state.players] == [1, 2, 3, 4, 5, 6]


def test_get_player_view_werewolf():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    wolf_seats = [p.seat_id for p in state.players if p.role == "werewolf"]
    wolf_view = get_player_view(state, wolf_seats[0])
    teammates = wolf_view["private_data"]["teammates"]
    assert wolf_seats[1] in teammates
    assert wolf_seats[0] not in teammates


def test_get_player_view_villager():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    villager_seats = [p.seat_id for p in state.players if p.role == "villager"]
    view = get_player_view(state, villager_seats[0])
    assert "teammates" not in view["private_data"]
    assert "check_result" not in view["private_data"]


def test_get_player_view_prophet():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
    view = get_player_view(state, prophet_seat)
    assert "check_results" in view["private_data"]


def test_get_player_view_witch():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    view = get_player_view(state, witch_seat)
    assert "antidote_remaining" in view["private_data"]
    assert "poison_remaining" in view["private_data"]
    assert view["private_data"]["antidote_remaining"] == 1
    assert view["private_data"]["poison_remaining"] == 1
    assert "night_kill_target" in view["private_data"]


def test_public_state_excludes_private():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    public = get_public_state(state)
    for player_dict in public["players"]:
        assert "private_data" not in player_dict
    assert "private_data" not in public


def test_player_seat_ids_are_immutable():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    for i, p in enumerate(state.players, 1):
        assert p.seat_id == i
