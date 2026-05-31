# backend/game/state.py
"""
GameState: 游戏状态数据结构，支持信息隔离。
"""
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from config.game_config import ROLE_DISTRIBUTION, SEAT_IDS


@dataclass
class Player:
    seat_id: int
    player_name: str
    model_name: str
    role: str        # werewolf / prophet / witch / villager
    is_alive: bool = True
    can_speak: bool = True


@dataclass
class Speech:
    seat_id: int
    player_name: str
    content: str
    thinking: str
    timestamp: float


@dataclass
class NightAction:
    action_type: str    # kill / check / save / poison
    actor_seat: int
    target_seat: int
    resolved: bool = False


@dataclass
class GameState:
    phase: str = "game_init"
    day: int = 0
    players: List[Player] = field(default_factory=list)
    speaker_order: List[int] = field(default_factory=list)
    speech_history: List[Speech] = field(default_factory=list)
    full_history: List[Speech] = field(default_factory=list)
    votes: Dict[int, Optional[int]] = field(default_factory=dict)
    night_actions: List[NightAction] = field(default_factory=list)
    killed_last_night: List[int] = field(default_factory=list)
    night_summary: str = ""  # 夜晚结果公告，如"平安夜"或"X号玩家死亡"
    winner: Optional[str] = None
    witch_antidote: int = 1
    witch_poison: int = 1
    private_data: Dict[int, Dict[str, Any]] = field(default_factory=dict)


def create_game_state(player_configs: List[Dict[str, str]]) -> GameState:
    roles = []
    for role, count in ROLE_DISTRIBUTION.items():
        roles.extend([role] * count)
    random.shuffle(roles)

    players = []
    for cfg in player_configs:
        seat_id = cfg["seat_id"]
        player = Player(
            seat_id=seat_id,
            player_name=cfg["player_name"],
            model_name=cfg["model_name"],
            role=roles[seat_id - 1],
        )
        players.append(player)

    players.sort(key=lambda p: p.seat_id)

    private_data = {}
    wolf_seats = [p.seat_id for p in players if p.role == "werewolf"]
    for p in players:
        pd: Dict[str, Any] = {"my_votes": {}}   # 通用记忆：所有角色
        if p.role == "werewolf":
            pd["teammates"] = [s for s in wolf_seats if s != p.seat_id]
            pd["kill_history"] = {}
        elif p.role == "prophet":
            pd["check_results"] = {}
        elif p.role == "witch":
            pd["antidote_remaining"] = 1
            pd["poison_remaining"] = 1
            pd["night_kill_target"] = None
            pd["potion_history"] = []
        private_data[p.seat_id] = pd

    state = GameState(
        players=players,
        speaker_order=[p.seat_id for p in players],
        private_data=private_data,
    )
    return state


def get_player_view(state: GameState, seat_id: int) -> Dict[str, Any]:
    """返回指定玩家视角的游戏状态（信息隔离）"""
    return {
        "my_seat_id": seat_id,
        "my_role": get_player(state, seat_id).role,
        "phase": state.phase,
        "day": state.day,
        "players": [
            {
                "seat_id": p.seat_id,
                "player_name": p.player_name,
                "is_alive": p.is_alive,
            }
            for p in state.players
        ],
        "speech_history": [
            {"seat_id": s.seat_id, "player_name": s.player_name, "content": s.content}
            for s in state.speech_history
        ],
        "full_history": [
            {"seat_id": s.seat_id, "player_name": s.player_name, "content": s.content}
            for s in state.full_history
        ],
        "votes": {
            str(voter): target
            for voter, target in state.votes.items()
        },
        "killed_last_night": list(state.killed_last_night),
        "night_summary": state.night_summary,
        "private_data": dict(state.private_data.get(seat_id, {})),
    }


def get_public_state(state: GameState) -> Dict[str, Any]:
    """返回公开游戏状态（供前端）。包含角色身份（上帝视角）"""
    return {
        "phase": state.phase,
        "day": state.day,
        "players": [
            {
                "seat_id": p.seat_id,
                "player_name": p.player_name,
                "model_name": p.model_name,
                "is_alive": p.is_alive,
                "role": p.role,
            }
            for p in state.players
        ],
        "speaker_order": list(state.speaker_order),
        "speech_history": [
            {
                "seat_id": s.seat_id,
                "player_name": s.player_name,
                "content": s.content,
                "thinking": s.thinking,
                "timestamp": s.timestamp,
            }
            for s in state.speech_history
        ],
        "full_history": [
            {
                "seat_id": s.seat_id,
                "player_name": s.player_name,
                "content": s.content,
                "thinking": s.thinking,
                "timestamp": s.timestamp,
            }
            for s in state.full_history
        ],
        "votes": {
            str(voter): target for voter, target in state.votes.items()
        },
        "killed_last_night": list(state.killed_last_night),
        "winner": state.winner,
        "current_speaker": None,
        "current_thinking": None,
    }


def get_player(state: GameState, seat_id: int) -> Player:
    for p in state.players:
        if p.seat_id == seat_id:
            return p
    raise ValueError(f"Player with seat_id {seat_id} not found")


def get_alive_players(state: GameState) -> List[Player]:
    return [p for p in state.players if p.is_alive]


def check_game_over(state: GameState) -> Optional[str]:
    """返回 'werewolf' / 'villager' / None"""
    alive = get_alive_players(state)
    wolf_count = sum(1 for p in alive if p.role == "werewolf")
    villager_count = sum(1 for p in alive if p.role != "werewolf")
    if wolf_count == 0:
        return "villager"
    if wolf_count >= villager_count:
        return "werewolf"
    return None
