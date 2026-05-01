# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_game_valid():
    response = client.post("/game/create", json={
        "players": [
            {
                "seat_id": i,
                "player_name": f"玩家{i}",
                "model_name": "gpt-4o",
                "provider": "openai",
                "api_key": "sk-test",
            }
            for i in range(1, 7)
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert "players" in data
    assert len(data["players"]) == 6


def test_create_game_wrong_player_count():
    response = client.post("/game/create", json={
        "players": [
            {"seat_id": 1, "player_name": "玩家1", "model_name": "gpt-4o",
             "provider": "openai", "api_key": "sk-test"}
        ],
    })
    assert response.status_code == 422


def test_get_game_not_found():
    response = client.get("/game/nonexistent-id/status")
    assert response.status_code == 404


def test_list_models():
    response = client.get("/models/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) >= 3
