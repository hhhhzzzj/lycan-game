# backend/api/routes.py
"""REST API 和 WebSocket 路由"""
import asyncio
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from game.engine import GameEngine
from game.state import get_public_state

router = APIRouter()

_active_games: Dict[str, GameEngine] = {}


class PlayerConfig(BaseModel):
    seat_id: int = Field(..., ge=1, le=6)
    player_name: str
    model_name: str
    provider: str = "openai"
    api_key: str = ""
    base_url: str | None = None


class CreateGameRequest(BaseModel):
    players: List[PlayerConfig] = Field(..., min_length=6, max_length=6)


class CreateGameResponse(BaseModel):
    game_id: str
    players: List[Dict[str, Any]]


@router.post("/game/create", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest):
    game_id = str(uuid.uuid4())[:8]
    player_configs = [p.model_dump() for p in req.players]
    engine = GameEngine(player_configs)
    _active_games[game_id] = engine
    return CreateGameResponse(
        game_id=game_id,
        players=[
            {
                "seat_id": p.seat_id,
                "player_name": p.player_name,
                "role": p.role,
                "model_name": p.model_name,
                "is_alive": p.is_alive,
            }
            for p in engine.state.players
        ],
    )


@router.post("/game/{game_id}/start")
async def start_game(game_id: str):
    engine = _active_games.get(game_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Game not found")
    asyncio.create_task(engine.run_game())
    return {"status": "started", "game_id": game_id}


@router.get("/game/{game_id}/status")
async def get_game_status(game_id: str):
    engine = _active_games.get(game_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Game not found")
    return get_public_state(engine.state)


@router.get("/games")
async def list_games():
    return {
        "games": [
            {
                "game_id": gid,
                "phase": engine.state.phase,
                "day": engine.state.day,
            }
            for gid, engine in _active_games.items()
        ]
    }


@router.get("/models/presets")
async def get_model_presets():
    return {
        "presets": [
            {
                "provider": "anthropic",
                "name": "Claude Sonnet 4.6",
                "model": "claude-sonnet-4-6-20250514",
                "description": "Anthropic Claude (推荐)",
            },
            {
                "provider": "openai",
                "name": "GPT-4o",
                "model": "gpt-4o",
                "description": "OpenAI GPT-4o",
            },
            {
                "provider": "openai",
                "name": "GPT-4.1",
                "model": "gpt-4.1",
                "description": "OpenAI GPT-4.1",
            },
            {
                "provider": "google",
                "name": "Gemini 2.5 Pro",
                "model": "gemini-2.5-pro-exp-03-25",
                "description": "Google Gemini",
            },
        ],
    }


@router.websocket("/game/{game_id}/ws")
async def game_websocket(websocket: WebSocket, game_id: str):
    engine = _active_games.get(game_id)
    if not engine:
        await websocket.close(code=4004, reason="Game not found")
        return

    await websocket.accept()

    async def push_update(data: Dict[str, Any]):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    engine.set_on_update(push_update)
    await websocket.send_json(get_public_state(engine.state))

    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
