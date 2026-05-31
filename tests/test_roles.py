# tests/test_roles.py
import pytest
from game.roles.base import get_role_handler
from game.roles.werewolf import WerewolfHandler
from game.roles.prophet import ProphetHandler
from game.roles.witch import WitchHandler
from game.roles.villager import VillagerHandler


def test_get_role_handler_werewolf():
    handler = get_role_handler("werewolf")
    assert isinstance(handler, WerewolfHandler)


def test_get_role_handler_prophet():
    handler = get_role_handler("prophet")
    assert isinstance(handler, ProphetHandler)


def test_get_role_handler_witch():
    handler = get_role_handler("witch")
    assert isinstance(handler, WitchHandler)


def test_get_role_handler_villager():
    handler = get_role_handler("villager")
    assert isinstance(handler, VillagerHandler)


def test_get_role_handler_invalid():
    with pytest.raises(ValueError, match="Unknown role"):
        get_role_handler("guard")


def test_werewolf_night_prompt_includes_teammates():
    handler = WerewolfHandler()
    prompt = handler.get_night_prompt(
        player_name="玩家1",
        view={"my_seat_id": 1, "private_data": {"teammates": [3]}, "players": []},
    )
    assert "狼人" in prompt or "队友" in prompt
    assert "玩家1" in prompt
    assert "刀" in prompt or "杀" in prompt


def test_prophet_night_prompt():
    handler = ProphetHandler()
    prompt = handler.get_night_prompt(
        player_name="玩家5",
        view={"private_data": {"check_results": {}}, "players": []},
    )
    assert "预言家" in prompt
    assert "查验" in prompt


def test_witch_night_prompt():
    handler = WitchHandler()
    prompt = handler.get_night_prompt(
        player_name="玩家3",
        view={
            "my_seat_id": 3,
            "private_data": {
                "antidote_remaining": 1,
                "poison_remaining": 1,
                "night_kill_target": 2,
            },
            "players": [
                {"seat_id": 1, "player_name": "玩家1", "is_alive": True},
                {"seat_id": 2, "player_name": "玩家2", "is_alive": True},
                {"seat_id": 3, "player_name": "玩家3", "is_alive": True},
            ],
        },
    )
    assert "女巫" in prompt
    assert "2号" in prompt


def test_villager_day_prompt():
    handler = VillagerHandler()
    prompt = handler.get_day_speech_prompt(
        player_name="玩家6",
        view={"day": 1, "speech_history": [], "full_history": []},
    )
    assert "村民" in prompt or "平民" in prompt
