# AI 狼人杀第一版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 6 人全员 AI 狼人杀游戏，后端 Python + FastAPI + WebSocket，前端 React，支持多模型可配置、信息隔离、观战界面。

**Architecture:** 后端采用同步顺序游戏引擎，FastAPI 管理 HTTP/WebSocket 通信，前端通过 WebSocket 订阅游戏状态更新。每个 AI 玩家在轮到行动时调用 LLM（支持多模型适配器），前端展示思考过程和发言。

**Tech Stack:** Python 3.10+, FastAPI, asyncio, React 18+, TypeScript, Vite

---

## 补充说明（Spec Reviewer 反馈）

### 死亡结算顺序

```
夜晚结算顺序：狼人刀人 → 女巫解药救/毒药杀 → 结算死亡
  1. 狼人执行刀人 —— 记录被刀目标
  2. 女巫用药（仅在有人被刀时自动通知）：
     - 若用解药：被刀目标存活
     - 若用毒药：毒药目标死亡（独立于刀人结果）
  3. 合并死亡名单：[被刀且未被救的玩家] ∪ [被毒的玩家]
  4. 白天宣布死亡名单
```

### GameState 详细字段

```python
@dataclass
class Speech:
    seat_id: int
    player_name: str
    content: str
    thinking: str          # AI 思考过程（观战者可见）
    timestamp: float

@dataclass
class Player:
    seat_id: int           # 1-6
    player_name: str       # 显示名称
    model_name: str        # 使用的模型
    role: str              # werewolf / prophet / witch / villager
    is_alive: bool
    can_speak: bool        # 是否还能发表遗言

@dataclass
class NightAction:
    action_type: str       # kill / check / save / poison
    actor_seat: int
    target_seat: int
    resolved: bool         # 是否已结算

@dataclass
class GameState:
    phase: str             # game_init / night / day / vote / revote / game_over
    day: int               # 当前天数 (0 = 尚未白天)
    players: List[Player]  # 6 个玩家
    speaker_order: List[int]  # 发言顺序（按 seat_id）
    speech_history: List[Speech]  # 当天发言（每天清空）
    full_history: List[Speech]    # 跨天累积的全部发言和遗言
    votes: Dict[int, Optional[int]]  # voter_seat -> target_seat (None = 弃票)
    night_actions: List[NightAction]  # 当前夜晚行动记录
    killed_last_night: List[int]  # 昨晚死亡玩家 seat_id
    winner: Optional[str]  # werewolf / villager / None
    witch_antidote: int    # 解药剩余 (0 或 1)
    witch_poison: int      # 毒药剩余 (0 或 1)
    private_data: Dict[int, Dict[str, Any]]  # 按 seat_id 存储的私有信息
```

---

## Task 1: 项目初始化与 Git Setup

**Files:**
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `frontend/` (via Vite)

- [ ] **Step 1: 初始化 git 仓库并创建 .gitignore**

```bash
cd "D:/求职之路/八股/进阶/ai-practice/sand-box"
git init
```

```gitignore
# .gitignore
__pycache__/
*.pyc
.env
.venv/
node_modules/
dist/
.env.local
*.log
.vscode/
.idea/
```

- [ ] **Step 2: 创建后端目录结构和 requirements.txt**

```bash
mkdir -p backend/game/roles backend/game/llm backend/api backend/config
```

```
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
websockets==13.0
openai==1.51.0
anthropic==0.39.0
google-generativeai==0.8.3
python-dotenv==1.0.1
pydantic==2.9.2
```

- [ ] **Step 3: 安装后端依赖**

```bash
cd backend
pip install -r requirements.txt
cd ..
```

Expected: 所有包安装成功，无错误。

- [ ] **Step 4: 创建后端入口 main.py（占位）**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Werewolf Game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 5: 验证后端启动**

```bash
cd backend
python main.py
# 访问 http://localhost:8000/health 应返回 {"status":"ok"}
# Ctrl+C 停止
```

- [ ] **Step 6: 创建前端项目**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

- [ ] **Step 7: 验证前端启动**

```bash
cd frontend
npm run dev
# 访问 http://localhost:5173 应看到 Vite + React 页面
# Ctrl+C 停止
```

- [ ] **Step 8: 创建后端必要的 init 文件**

```bash
touch backend/game/__init__.py
touch backend/game/roles/__init__.py
touch backend/game/llm/__init__.py
touch backend/api/__init__.py
```

- [ ] **Step 9: Commit**

```bash
git add .gitignore backend/requirements.txt backend/main.py backend/game/__init__.py backend/game/roles/__init__.py backend/game/llm/__init__.py backend/api/__init__.py
git commit -m "feat: init project structure with FastAPI backend and Vite React frontend"
```

---

## Task 2: GameState 数据结构

**Files:**
- Create: `backend/config/__init__.py`
- Create: `backend/config/game_config.py`
- Create: `backend/game/state.py`
- Create: `tests/__init__.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: 创建测试文件**

```bash
mkdir -p tests
touch tests/__init__.py
```

```ini
# pytest.ini (项目根目录)
[pytest]
pythonpath = backend
testpaths = tests
```

```python
# tests/test_state.py
import pytest
from game.state import (
    Player, GameState, Speech, NightAction, create_game_state,
    get_player_view, get_public_state
)


def test_create_game_state():
    state = create_game_state()
    assert len(state.players) == 6
    assert state.phase == "game_init"
    assert state.day == 0
    assert len(state.speaker_order) == 6
    assert state.winner is None

    # 验证角色分配正确（2狼 2民 1预言 1女巫）
    roles = [p.role for p in state.players]
    assert roles.count("werewolf") == 2
    assert roles.count("villager") == 2
    assert roles.count("prophet") == 1
    assert roles.count("witch") == 1

    # 验证座次 1-6
    assert [p.seat_id for p in state.players] == [1, 2, 3, 4, 5, 6]


def test_get_player_view_werewolf():
    """狼人能看到队友"""
    state = create_game_state()
    wolf_seats = [p.seat_id for p in state.players if p.role == "werewolf"]
    wolf_view = get_player_view(state, wolf_seats[0])
    # 狼人应能看到队友
    teammates = wolf_view["private_data"]["teammates"]
    assert wolf_seats[1] in teammates
    assert wolf_seats[0] not in teammates  # 不包含自己


def test_get_player_view_villager():
    """村民看不到任何私有信息"""
    state = create_game_state()
    villager_seats = [p.seat_id for p in state.players if p.role == "villager"]
    view = get_player_view(state, villager_seats[0])
    assert "teammates" not in view["private_data"]
    assert "check_result" not in view["private_data"]


def test_get_player_view_prophet():
    """预言家能看到验人结果"""
    state = create_game_state()
    prophet_seat = [p.seat_id for p in state.players if p.role == "prophet"][0]
    view = get_player_view(state, prophet_seat)
    assert "check_results" in view["private_data"]


def test_get_player_view_witch():
    """女巫能看到用药状态"""
    state = create_game_state()
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    view = get_player_view(state, witch_seat)
    assert "antidote_remaining" in view["private_data"]
    assert "poison_remaining" in view["private_data"]
    assert view["private_data"]["antidote_remaining"] == 1
    assert view["private_data"]["poison_remaining"] == 1
    assert "night_kill_target" in view["private_data"]


def test_public_state_excludes_private():
    """公开状态不包含任何私有数据"""
    state = create_game_state()
    public = get_public_state(state)
    # 不应包含 private_data
    for player in public["players"]:
        assert "private_data" not in player
    assert "private_data" not in public


def test_player_seat_ids_are_immutable():
    """座位号固定 1-6"""
    state = create_game_state()
    for i, p in enumerate(state.players, 1):
        assert p.seat_id == i
```

- [ ] **Step 2: 运行测试 — 预期 FAIL（模块不存在）**

```bash
pytest tests/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'game.state'`

- [ ] **Step 3: 创建游戏配置常量**

```python
# backend/config/__init__.py
# 空文件

# backend/config/game_config.py
"""游戏配置常量"""

ROLE_DISTRIBUTION = {
    "werewolf": 2,
    "prophet": 1,
    "witch": 1,
    "villager": 2,
}

TOTAL_PLAYERS = 6
SEAT_IDS = [1, 2, 3, 4, 5, 6]

# 首夜狼人刀人时女巫自动通知被刀目标
WITCH_AUTO_NOTIFY_FIRST_NIGHT = True
```

- [ ] **Step 4: 实现 GameState 数据结构**

```python
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
    phase: str = "game_init"          # game_init / night / day / vote / revote / game_over
    day: int = 0
    players: List[Player] = field(default_factory=list)
    speaker_order: List[int] = field(default_factory=list)
    speech_history: List[Speech] = field(default_factory=list)
    full_history: List[Speech] = field(default_factory=list)
    votes: Dict[int, Optional[int]] = field(default_factory=dict)
    night_actions: List[NightAction] = field(default_factory=list)
    killed_last_night: List[int] = field(default_factory=list)
    winner: Optional[str] = None
    witch_antidote: int = 1
    witch_poison: int = 1
    private_data: Dict[int, Dict[str, Any]] = field(default_factory=dict)


def create_game_state(player_configs: List[Dict[str, str]]) -> GameState:
    """
    创建新游戏状态。

    Args:
        player_configs: [{seat_id, player_name, model_name}, ...]
                        必须恰好 6 个玩家
    """
    roles = []
    for role, count in ROLE_DISTRIBUTION.items():
        roles.extend([role] * count)
    random.shuffle(roles)

    players = []
    for cfg in player_configs:
        seat_id = cfg["seat_id"]
        # 按座位号分配角色
        player = Player(
            seat_id=seat_id,
            player_name=cfg["player_name"],
            model_name=cfg["model_name"],
            role=roles[seat_id - 1],
        )
        players.append(player)

    players.sort(key=lambda p: p.seat_id)

    # 初始化私有数据
    private_data = {}
    wolf_seats = [p.seat_id for p in players if p.role == "werewolf"]
    for p in players:
        pd: Dict[str, Any] = {}
        if p.role == "werewolf":
            pd["teammates"] = [s for s in wolf_seats if s != p.seat_id]
        elif p.role == "prophet":
            pd["check_results"] = {}  # {seat_id: "good"/"wolf"}
        elif p.role == "witch":
            pd["antidote_remaining"] = 1
            pd["poison_remaining"] = 1
            pd["night_kill_target"] = None
        private_data[p.seat_id] = pd

    state = GameState(
        players=players,
        speaker_order=[p.seat_id for p in players],
        private_data=private_data,
    )
    return state


def get_player_view(state: GameState, seat_id: int) -> Dict[str, Any]:
    """
    返回指定玩家视角的游戏状态。
    用于调用 AI 时传入过滤后的信息。
    """
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
        "votes": {
            str(voter): target
            for voter, target in state.votes.items()
        },
        "killed_last_night": list(state.killed_last_night),
        "private_data": dict(state.private_data.get(seat_id, {})),
    }


def get_public_state(state: GameState) -> Dict[str, Any]:
    """返回公开游戏状态（供前端和观战者使用）。不包含任何私有数据。"""
    return {
        "phase": state.phase,
        "day": state.day,
        "players": [
            {
                "seat_id": p.seat_id,
                "player_name": p.player_name,
                "model_name": p.model_name,
                "is_alive": p.is_alive,
                # 不传 role — 观战者可看到角色（因为观战者是上帝视角）
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
        "current_speaker": None,  # 由 engine 设置
        "current_thinking": None,
    }


def get_player(state: GameState, seat_id: int) -> Player:
    """按座位号获取玩家"""
    for p in state.players:
        if p.seat_id == seat_id:
            return p
    raise ValueError(f"Player with seat_id {seat_id} not found")


def get_alive_players(state: GameState) -> List[Player]:
    """获取所有存活玩家"""
    return [p for p in state.players if p.is_alive]


def check_game_over(state: GameState) -> Optional[str]:
    """
    检查游戏是否结束。
    返回: "werewolf" 狼人赢, "villager" 好人赢, None 游戏继续
    """
    alive = get_alive_players(state)
    wolf_count = sum(1 for p in alive if p.role == "werewolf")
    villager_count = sum(1 for p in alive if p.role != "werewolf")

    if wolf_count == 0:
        return "villager"
    if wolf_count >= villager_count:
        return "werewolf"
    return None
```

- [ ] **Step 5: 运行测试 — 预期全部 PASS**

```bash
pytest tests/test_state.py -v
```

Expected: 所有 7 个测试通过。

- [ ] **Step 6: Commit**

```bash
git add backend/config/ backend/game/state.py tests/test_state.py
git commit -m "feat: add GameState data structure with information isolation"
```

---

## Task 3: 角色定义

**Files:**
- Create: `backend/game/roles/base.py`
- Create: `backend/game/roles/werewolf.py`
- Create: `backend/game/roles/prophet.py`
- Create: `backend/game/roles/witch.py`
- Create: `backend/game/roles/villager.py`
- Create: `tests/test_roles.py`

- [ ] **Step 1: 创建角色测试**

```python
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
        view={"private_data": {"teammates": [3]}, "players": []},
    )
    assert "狼人" in prompt
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
            "private_data": {
                "antidote_remaining": 1,
                "poison_remaining": 1,
                "night_kill_target": 2,
            },
            "players": [
                {"seat_id": 1, "player_name": "玩家1", "is_alive": True},
                {"seat_id": 2, "player_name": "玩家2", "is_alive": True},
            ],
        },
    )
    assert "女巫" in prompt
    assert "2号" in prompt  # 被刀目标


def test_villager_day_prompt():
    handler = VillagerHandler()
    prompt = handler.get_day_speech_prompt(
        player_name="玩家6",
        view={"speech_history": []},
    )
    assert "村民" in prompt or "平民" in prompt
```

- [ ] **Step 2: 运行测试 — 预期 FAIL**

```bash
pytest tests/test_roles.py -v
```

- [ ] **Step 3: 实现角色基类和具体角色**

```python
# backend/game/roles/base.py
"""角色处理基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class RoleHandler(ABC):
    """角色处理抽象基类"""

    @abstractmethod
    def get_role_name(self) -> str:
        ...

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        """夜晚行动 prompt（默认无行动）"""
        return ""

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        """白天发言 prompt"""
        return ""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        """投票 prompt"""
        return ""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        """遗言 prompt"""
        return ""


_ROLE_REGISTRY: Dict[str, RoleHandler] = {}


def _register_role(role_name: str, handler: RoleHandler):
    _ROLE_REGISTRY[role_name] = handler


def get_role_handler(role_name: str) -> RoleHandler:
    if role_name not in _ROLE_REGISTRY:
        raise ValueError(f"Unknown role: {role_name}")
    return _ROLE_REGISTRY[role_name]
```

```python
# backend/game/roles/werewolf.py
"""狼人角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class WerewolfHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "狼人"

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        teammates = pd.get("teammates", [])
        alive = [p for p in view["players"] if p["is_alive"] and p["seat_id"] not in teammates]

        prompt = f"""你是{player_name}，你的身份是狼人。

你的狼人队友：{', '.join(f'{t}号玩家' for t in teammates)}。

现在是夜晚，你需要和队友一起选择今晚要杀死的目标。

当前存活玩家（排除队友）：
{self._format_players(alive)}

请选择你要杀死的目标（输出座位号 1-6）。
注意：你只能杀死存活玩家。
"""
        return prompt

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return self._base_speech_prompt(player_name, view, "狼人")

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return self._base_vote_prompt(player_name, view, "狼人")

    def _base_speech_prompt(self, player_name, view, role_cn):
        history = view.get("speech_history", [])
        history_text = self._format_history(history) if history else "（无人发言）"

        return f"""你是{player_name}，你的身份是{role_cn}。

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。你可以：
- 分析场上局势
- 质疑其他人的发言
- 隐藏自己的身份（如果你需要）
- 如果想要悍跳预言家，可以说"我是预言家，昨晚查了X号是狼人"

请用自然的中文发言。"""

    def _base_vote_prompt(self, player_name, view, role_cn):
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("speech_history", [])
        history_text = self._format_history(history) if history else ""

        return f"""你是{player_name}，身份是{role_cn}。

现在是投票环节。请根据今天的发言记录决定投票给谁。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。你可以投票给任何存活玩家。"""

    def _format_history(self, history):
        return "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        )

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return f"""你是{player_name}，你的身份是狼人。你即将被放逐/杀死。
请发表你的遗言。你可以暴露身份、误导好人、或说出你的想法。"""


_register_role("werewolf", WerewolfHandler())
```

```python
# backend/game/roles/prophet.py
"""预言家角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class ProphetHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "预言家"

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"] and p["seat_id"] != view["my_seat_id"]]
        prev_checks = view["private_data"].get("check_results", {})

        prompt = f"""你是{player_name}，你的身份是预言家。

现在是夜晚，你可以查验一名玩家的身份。

已验证过的玩家：
{self._format_checks(prev_checks)}

存活玩家：
{self._format_players(alive)}

请选择你要查验的玩家（输出座位号 1-6）。
"""
        return prompt

    def _format_checks(self, checks):
        if not checks:
            return "  （尚未查验任何玩家）"
        return "\n".join(f"  {seat}号: {result}" for seat, result in checks.items())

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        checks = view["private_data"].get("check_results", {})
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else "（无人发言）"

        return f"""你是{player_name}，你的身份是预言家。

你的查验记录：
{self._format_checks(checks)}

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为预言家，你可以：
- 报出你的查验结果
- 分析场上局势
- 带领好人投票

但是如果你的查验结果对你不利，你可以选择暂时不暴露身份。
请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        checks = view["private_data"].get("check_results", {})
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else ""

        return f"""你是{player_name}，身份是预言家。

你的查验记录：
{self._format_checks(checks)}

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        checks = view["private_data"].get("check_results", {})
        return f"""你是{player_name}，你的身份是预言家。你即将死亡。

你的查验记录：
{self._format_checks(checks)}

请发表遗言。你可以报出所有查验结果，或给出最后的建议。"""


_register_role("prophet", ProphetHandler())
```

```python
# backend/game/roles/witch.py
"""
女巫角色处理。
解药+毒药各1瓶，同一晚不能同时使用。
"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class WitchHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "女巫"

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        antidote = pd.get("antidote_remaining", 0)
        poison = pd.get("poison_remaining", 0)
        kill_target = pd.get("night_kill_target")

        alive = [
            p for p in view["players"]
            if p["is_alive"] and p["seat_id"] != view["my_seat_id"]
        ]

        prompt = f"""你是{player_name}，你的身份是女巫。

当前药水状态：
  - 解药：{antidote}瓶{'（可用）' if antidote > 0 else '（已用）'}
  - 毒药：{poison}瓶{'（可用）' if poison > 0 else '（已用）'}

"""

        if kill_target is not None:
            prompt += f"""今晚狼人刀了 {kill_target} 号玩家。
你可以选择是否使用解药救活 {kill_target} 号玩家。
"""

        if poison > 0:
            prompt += f"""
你也可以使用毒药毒杀一名存活玩家。

存活玩家：
{self._format_players(alive)}
"""

        prompt += """
重要规则：
- 同一晚不能同时使用解药和毒药
- 解药只能用一次
- 毒药只能用一次

请输出你的选择：
- "不使用任何药"
- "用解药救 X 号"
- "用毒药毒 X 号"
"""
        return prompt

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else "（无人发言）"

        return f"""你是{player_name}，你的身份是女巫。

你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为女巫，你拥有强大的技能，但请谨慎使用。

请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else ""

        return f"""你是{player_name}，身份是女巫。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        pd = view["private_data"]
        return f"""你是{player_name}，你的身份是女巫。你即将死亡。
你的药水状态：解药{pd.get('antidote_remaining', 0)}瓶，毒药{pd.get('poison_remaining', 0)}瓶。
请发表遗言。"""


_register_role("witch", WitchHandler())
```

```python
# backend/game/roles/villager.py
"""村民角色处理"""
from .base import RoleHandler, _register_role
from typing import Any, Dict


class VillagerHandler(RoleHandler):
    def get_role_name(self) -> str:
        return "村民"

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else "（无人发言）"

        return f"""你是{player_name}，你的身份是村民。

你没有特殊能力，但你通过分析发言和投票帮助好人获胜。

当前是第{view['day']}天白天，轮到你发言。

之前的发言记录：
{history_text}

请发表你的看法。作为村民，你应该：
- 认真分析每个人的发言
- 找出矛盾或可疑之处
- 帮助预言家等神职队友

请用自然的中文发言。"""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        alive = [p for p in view["players"] if p["is_alive"]]
        history = view.get("speech_history", [])
        history_text = "\n".join(
            f"  [{h['seat_id']}号 {h['player_name']}]: {h['content']}"
            for h in history
        ) if history else ""

        return f"""你是{player_name}，身份是村民。

发言记录：
{history_text}

存活玩家：
{self._format_players(alive)}

请选择你要投票放逐的玩家（输出座位号）。"""

    def _format_players(self, players):
        return "\n".join(f"  - {p['seat_id']}号: {p['player_name']}" for p in players)

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return f"""你是{player_name}，你的身份是村民。你即将死亡。
请发表遗言。作为村民，你可以说出你的怀疑对象或最后的建议。"""


_register_role("villager", VillagerHandler())
```

- [ ] **Step 4: 运行角色测试 — 预期 PASS**

```bash
pytest tests/test_roles.py -v
```

Expected: 所有 9 个测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/game/roles/ tests/test_roles.py
git commit -m "feat: add role handlers (werewolf, prophet, witch, villager)"
```

---

## Task 4: LLM 适配器

**Files:**
- Create: `backend/game/llm/base.py`
- Create: `backend/game/llm/adapters.py`
- Create: `tests/conftest.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: 创建 LLM 测试**

```python
# tests/conftest.py
# 空文件 — pytest fixture 配置文件

# tests/test_llm.py
import pytest
from game.llm.base import LLMResponse, BaseLLMAdapter
from game.llm.adapters import create_adapter, OpenAIAdapter, AnthropicAdapter


def test_llm_response_parses_json():
    resp = LLMResponse.from_text("""
    ```json
    {"thinking": "吃了吗", "action": "投票给3号"}
    ```
    """)
    assert resp.thinking == "吃了吗"
    assert resp.action == "投票给3号"


def test_llm_response_parses_plain():
    resp = LLMResponse.from_text("""
    思考：我觉得3号有问题
    行动：投票给3号
    """)
    assert "3号" in resp.action or "3号" in resp.thinking


def test_create_openai_adapter():
    adapter = create_adapter("openai", "gpt-4o", "sk-test")
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.model == "gpt-4o"


def test_create_anthropic_adapter():
    adapter = create_adapter("anthropic", "claude-sonnet-4-6", "sk-test")
    assert isinstance(adapter, AnthropicAdapter)


def test_create_unknown_adapter_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_adapter("unknown", "model", "key")


def test_openai_adapter_builds_messages():
    adapter = OpenAIAdapter("gpt-4o", "sk-test")
    messages = adapter._build_messages(
        system="You are a player.",
        user="What do you do?",
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_anthropic_adapter_builds_messages():
    adapter = AnthropicAdapter("claude-sonnet-4-6", "sk-test")
    messages = adapter._build_messages(
        system="You are a player.",
        user="What do you do?",
    )
    assert len(messages) == 2
```

- [ ] **Step 2: 运行测试 — 预期 FAIL**

```bash
pytest tests/test_llm.py -v
```

- [ ] **Step 3: 实现 LLM 基础类和适配器**

```python
# backend/game/llm/base.py
"""LLM 适配器基础类"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """AI 玩家的响应"""
    thinking: str
    action: str

    @classmethod
    def from_text(cls, text: str) -> "LLMResponse":
        """从 LLM 原始输出解析思考过程和行动"""
        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return cls(
                    thinking=data.get("thinking", ""),
                    action=data.get("action", ""),
                )
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 JSON
        try:
            data = json.loads(text)
            return cls(
                thinking=data.get("thinking", ""),
                action=data.get("action", ""),
            )
        except json.JSONDecodeError:
            pass

        # 降级：整个文本作为 action
        return cls(thinking="", action=text.strip())


class BaseLLMAdapter(ABC):
    """LLM 适配器抽象基类"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """调用 LLM 并返回解析后的响应"""
        ...

    @abstractmethod
    def _build_messages(self, system: str, user: str) -> list:
        """构建消息格式"""
        ...
```

```python
# backend/game/llm/adapters.py
"""LLM 适配器实现 — OpenAI / Anthropic / Google AI"""
import asyncio
from typing import Optional
from .base import LLMResponse, BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 兼容接口适配器（GPT、DeepSeek、Qwen 等）"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.model,
                    messages=self._build_messages(system_prompt, user_prompt),
                    temperature=0.9,
                    max_tokens=1024,
                ),
                timeout=60.0,
            )
            text = response.choices[0].message.content or ""
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

    def _build_messages(self, system: str, user: str) -> list:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude 适配器"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=self._build_messages(system_prompt, user_prompt),
                ),
                timeout=60.0,
            )
            text = response.content[0].text
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

    def _build_messages(self, system: str, user: str) -> list:
        return [{"role": "user", "content": user}]


class GoogleAIAdapter(BaseLLMAdapter):
    """Google Gemini 适配器"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        try:
            model = genai.GenerativeModel(self.model)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    full_prompt,
                ),
                timeout=60.0,
            )
            text = response.text
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

    def _build_messages(self, system: str, user: str) -> list:
        return [{"role": "user", "content": f"{system}\n\n{user}"}]


_PROVIDER_REGISTRY = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleAIAdapter,
}


def create_adapter(
    provider: str,
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> BaseLLMAdapter:
    """
    创建 LLM 适配器实例。

    Args:
        provider: "openai" | "anthropic" | "google"
        model: 模型名称
        api_key: API 密钥
        base_url: 自定义 API endpoint（可选）
    """
    adapter_cls = _PROVIDER_REGISTRY.get(provider)
    if adapter_cls is None:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(_PROVIDER_REGISTRY.keys())}")
    return adapter_cls(model=model, api_key=api_key, base_url=base_url)
```

- [ ] **Step 4: 运行 LLM 测试 — 预期 PASS**

```bash
pytest tests/test_llm.py -v
```

Expected: 所有 7 个测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/game/llm/ tests/test_llm.py tests/conftest.py
git commit -m "feat: add LLM adapters (OpenAI, Anthropic, Google AI)"
```

---

## Task 5: 游戏引擎

**Files:**
- Create: `backend/game/engine.py`
- Create: `tests/test_engine.py`

这是整个项目的核心——游戏流程控制。

- [ ] **Step 1: 创建引擎测试**

```python
# tests/test_engine.py
import pytest
from game.state import create_game_state, GameState, Player, Speech, NightAction
from game.engine import GameEngine


def _make_config():
    return [
        {"seat_id": 1, "player_name": f"玩家{i}", "model_name": "claude-sonnet-4-6"}
        for i in range(1, 7)
    ]


def test_engine_initialization():
    engine = GameEngine(_make_config())
    assert engine.state is not None
    assert len(engine.state.players) == 6
    assert engine.state.phase == "game_init"


def test_engine_can_detect_game_over():
    """狼人全死 → 好人胜利"""
    state = create_game_state(_make_config())
    # 手动杀死所有狼人
    for p in state.players:
        if p.role == "werewolf":
            p.is_alive = False
    from game.state import check_game_over
    assert check_game_over(state) == "villager"


def test_engine_can_detect_wolf_win():
    """狼人数量 >= 好人数量"""
    state = create_game_state(_make_config())
    # 手动杀到只剩狼
    for p in state.players:
        if p.role in ("prophet", "witch", "villager"):
            p.is_alive = False
    from game.state import check_game_over
    assert check_game_over(state) == "werewolf"


def test_kill_resolution_order():
    """
    死亡结算顺序测试：
    1. 狼人刀人 → 2. 女巫救/毒 → 3. 结算
    若女巫用毒药，毒杀目标独立死亡。
    """
    state = create_game_state(_make_config())
    wolf_seat = [p.seat_id for p in state.players if p.role == "werewolf"][0]
    target_seat = 3

    # 模拟狼人刀3号
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=wolf_seat, target_seat=target_seat,
    ))

    # 模拟女巫不用药
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    # 不救 → 3号死亡
    from game.engine import _resolve_night_deaths
    deaths = _resolve_night_deaths(state)
    assert target_seat in deaths


def test_kill_with_antidote():
    """女巫用解药 → 目标存活"""
    state = create_game_state(_make_config())
    target_seat = 3
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=1, target_seat=target_seat,
    ))
    state.night_actions.append(NightAction(
        action_type="save", actor_seat=4, target_seat=target_seat,
    ))
    from game.engine import _resolve_night_deaths
    deaths = _resolve_night_deaths(state)
    assert target_seat not in deaths
    assert state.witch_antidote == 0


def test_kill_with_poison():
    """女巫用毒药 → 被毒目标死亡(独立于刀人)"""
    state = create_game_state(_make_config())
    state.night_actions.append(NightAction(
        action_type="kill", actor_seat=1, target_seat=3,
    ))
    state.night_actions.append(NightAction(
        action_type="poison", actor_seat=4, target_seat=5,
    ))
    from game.engine import _resolve_night_deaths
    deaths = _resolve_night_deaths(state)
    assert 3 in deaths  # 刀杀
    assert 5 in deaths  # 毒杀
    assert state.witch_poison == 0


def test_vote_count_resolves_correctly():
    """简单多数投票测试"""
    votes = {1: 3, 2: 3, 3: 1, 4: 5, 5: 3, 6: 5}
    from game.engine import _count_votes
    result = _count_votes(votes)
    assert result["max_count"] == 3
    assert len(result["top_candidates"]) == 1
    assert 3 in result["top_candidates"]


def test_vote_count_tie():
    """平票时返回多个候选人"""
    votes = {1: 2, 2: 2, 3: 5, 4: 5, 5: 3, 6: 2}
    from game.engine import _count_votes
    result = _count_votes(votes)
    assert len(result["top_candidates"]) > 1


def test_vote_count_empty():
    """全部弃票"""
    votes = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
    from game.engine import _count_votes
    result = _count_votes(votes)
    assert result["max_count"] == 0
    assert result["top_candidates"] == []
```

- [ ] **Step 2: 运行测试 — 预期 FAIL（无 engine 模块）**

```bash
pytest tests/test_engine.py -v
```

- [ ] **Step 3: 实现游戏引擎**

```python
# backend/game/engine.py
"""
游戏引擎：控制狼人杀完整流程。

死亡结算顺序：
1. 狼人刀人
2. 女巫解药救 / 毒药杀
3. 合并死亡名单：[被刀且未被救] + [被毒]
"""
import asyncio
import random
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
    """
    结算夜晚死亡。

    结算顺序：
    1. 找到狼人的 kill action
    2. 找到女巫的 save/poison action
    3. 被刀且未被救 → 死亡
    4. 被毒 → 死亡
    """
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

    # 结算刀人（女巫若用解药则救活）
    if kill_action is not None:
        if save_action is None or save_action.target_seat != kill_action.target_seat:
            deaths.add(kill_action.target_seat)

    # 结算毒药（独立于刀人）
    if poison_action is not None:
        deaths.add(poison_action.target_seat)

    return list(deaths)


def _count_votes(votes: Dict[int, Optional[int]]) -> Dict[str, Any]:
    """
    统计投票结果。
    返回: {"max_count": int, "top_candidates": List[int], "counts": Dict}
    """
    valid = [v for v in votes.values() if v is not None]
    if not valid:
        return {"max_count": 0, "top_candidates": [], "counts": {}}

    counts = Counter(valid)
    max_count = max(counts.values())
    top = [seat for seat, cnt in counts.items() if cnt == max_count]
    return {"max_count": max_count, "top_candidates": top, "counts": dict(counts)}


class GameEngine:
    """
    狼人杀游戏引擎。

    流程：
    game_init → 夜晚 → 白天(发言+投票) → 夜晚 → ... → game_over
    """

    def __init__(self, player_configs: List[Dict[str, Any]]):
        """
        Args:
            player_configs: [{seat_id, player_name, model_name, provider, api_key, ...}, ...]
        """
        self.state = create_game_state(player_configs)
        self.player_configs = {cfg["seat_id"]: cfg for cfg in player_configs}
        self.adapters: Dict[int, Any] = {}
        self._on_update = None  # callback for WebSocket push
        self._init_adapters()

    def _init_adapters(self):
        """为每个玩家创建 LLM 适配器"""
        for cfg in self.player_configs.values():
            self.adapters[cfg["seat_id"]] = create_adapter(
                provider=cfg.get("provider", "openai"),
                model=cfg["model_name"],
                api_key=cfg.get("api_key", ""),
                base_url=cfg.get("base_url"),
            )

    def set_on_update(self, callback):
        """设置状态更新回调（用于 WebSocket 推送）"""
        self._on_update = callback

    async def _push_update(self, extra: Optional[Dict] = None):
        """推送当前公开状态到前端"""
        if self._on_update:
            public = get_public_state(self.state)
            if extra:
                public.update(extra)
            await self._on_update(public)

    async def _call_ai(
        self, seat_id: int, prompt: str,
    ) -> Dict[str, str]:
        """调用指定玩家的 LLM"""
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
        """运行夜晚阶段"""
        state = self.state
        state.phase = "night"
        state.night_actions = []
        alive = get_alive_players(state)

        # === 狼人刀人 ===
        wolf_players = [p for p in alive if p.role == "werewolf"]
        wolf_decisions: List[NightAction] = []

        for wolf in wolf_players:
            handler = get_role_handler("werewolf")
            view = get_player_view(state, wolf.seat_id)
            prompt = handler.get_night_prompt(wolf.player_name, view)
            result = await self._call_ai(wolf.seat_id, prompt)
            wolf_decisions.append({
                "seat_id": wolf.seat_id,
                "thinking": result["thinking"],
                "action": result["action"],
            })
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号 思考中...",
                "current_thinking": result["thinking"],
            })

        # 选择刀人目标（随机选一狼的决定）
        if wolf_decisions:
            chosen = random.choice(wolf_decisions)
            target = self._parse_target(chosen["action"], alive)
            if target:
                state.night_actions.append(NightAction(
                    action_type="kill", actor_seat=chosen["seat_id"], target_seat=target,
                ))
                # 更新女巫私有信息
                witch = [p for p in state.players if p.role == "witch"][0]
                state.private_data[witch.seat_id]["night_kill_target"] = target

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
        witch = [p for p in alive if p.role == "witch"]
        if witch:
            w = witch[0]
            # 仅在首夜或有死人时通知女巫
            kill_target = state.private_data[w.seat_id].get("night_kill_target")
            if kill_target is not None or state.witch_poison > 0:
                handler = get_role_handler("witch")
                view = get_player_view(state, w.seat_id)
                prompt = handler.get_night_prompt(w.player_name, view)
                result = await self._call_ai(w.seat_id, prompt)
                # 解析女巫行动
                action_text = result["action"]
                if "救" in action_text:
                    target = self._parse_target(action_text, state.players)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="save", actor_seat=w.seat_id, target_seat=target,
                        ))
                elif "毒" in action_text:
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
        """运行白天阶段（发言 + 投票）"""
        state = self.state
        state.phase = "day"

        # 结算夜晚死亡
        deaths = _resolve_night_deaths(state)
        for seat_id in deaths:
            player = get_player(state, seat_id)
            player.is_alive = False
        state.killed_last_night = deaths

        await self._push_update({"phase_info": f"第{state.day}天白天开始"})

        alive = get_alive_players(state)

        # 宣布死亡 — 先清空当天发言，再追加遗言
        state.speech_history = []
        for seat_id in deaths:
            # 遗言（追加到 speech_history 和 full_history）
            await self._run_last_words(seat_id)

        # 检查游戏结束
        winner = check_game_over(state)
        if winner:
            state.winner = winner
            state.phase = "game_over"
            await self._push_update({"phase_info": f"游戏结束! {winner} 胜利!"})
            return

        # === 发言阶段 ===
        # speech_history 已在死亡宣布前清空，speech 追加到 speech_history + full_history
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
            state.votes = {}
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
                })

        # 结算投票
        final_result = _count_votes(state.votes)
        if len(final_result["top_candidates"]) == 1:
            eliminated = final_result["top_candidates"][0]
            player = get_player(state, eliminated)
            player.is_alive = False
            await self._push_update({
                "phase_info": f"{player.player_name}({eliminated}号) 被放逐！",
            })
            # 遗言
            await self._run_last_words(eliminated)
        elif len(final_result["top_candidates"]) > 1:
            # 再次平票 → 流放，无人出局
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
        """执行遗言"""
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
        """运行投票阶段"""
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

    async def run_game(self):
        """运行完整游戏"""
        state = self.state
        # 推送初始状态
        await self._push_update()

        while state.phase != "game_over":
            state.day += 1

            # 夜晚阶段
            await self.run_night()
            await self._push_update()

            if state.phase == "game_over":
                break

            # 白天阶段
            await self.run_day()
            await self._push_update()

        await self._push_update({"phase_info": f"游戏结束! 胜利方: {state.winner}"})

    def _parse_target(self, text: str, players: List[Player]) -> Optional[int]:
        """从文本中解析目标座位号（1-6）"""
        import re
        matches = re.findall(r'(\d+)号', text)
        if matches:
            seat = int(matches[0])
            if 1 <= seat <= 6:
                return seat
        # 尝试匹配纯数字
        matches = re.findall(r'\b([1-6])\b', text)
        if matches:
            return int(matches[0])
        return None
```

- [ ] **Step 4: 运行测试 — 预期 PASS（无需 AI 调用的测试）**

```bash
pytest tests/test_engine.py -v
```

Expected: 所有不含 AI 调用的测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/game/engine.py tests/test_engine.py
git commit -m "feat: add game engine with day/night cycle and death resolution"
```

---

## Task 6: REST API + WebSocket

**Files:**
- Create: `backend/api/routes.py`
- Modify: `backend/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: 创建 API 测试**

```python
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
    """创建游戏的请求格式正确"""
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
    """玩家数不是6时应报错"""
    response = client.post("/game/create", json={
        "players": [{"seat_id": 1, "player_name": "玩家1", "model_name": "gpt-4o", "provider": "openai", "api_key": "sk-test"}],
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
```

- [ ] **Step 2: 运行测试 — 预期 FAIL（路由不存在）**

```bash
pytest tests/test_api.py -v
```

- [ ] **Step 3: 实现 API 路由**

```python
# backend/api/routes.py
"""
REST API 和 WebSocket 路由。
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from game.engine import GameEngine
from game.state import get_public_state

router = APIRouter()

# 内存中保存活跃游戏
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

    # 在后台运行游戏
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

    # 发送初始状态
    await websocket.send_json(get_public_state(engine.state))

    try:
        # 保持连接
        while True:
            msg = await websocket.receive_text()
            # 前端可以发送简单指令
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: 更新 main.py**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(title="AI Werewolf Game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 5: 运行 API 测试 — 预期 PASS**

```bash
pytest tests/test_api.py -v
```

Expected: 所有 5 个测试通过。

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes.py backend/main.py tests/test_api.py
git commit -m "feat: add REST API and WebSocket routes"
```

---

## Task 7: 前端 TypeScript 类型定义

**Files:**
- Create: `frontend/src/types/game.ts`

- [ ] **Step 1: 创建类型定义**

```typescript
// frontend/src/types/game.ts

export interface Player {
  seat_id: number;
  player_name: string;
  model_name: string;
  role: string;
  is_alive: boolean;
}

export interface Speech {
  seat_id: number;
  player_name: string;
  content: string;
  thinking: string;
  timestamp: number;
}

export interface PublicGameState {
  phase: GamePhase;
  day: number;
  players: Player[];
  speaker_order: number[];
  speech_history: Speech[];
  full_history: Speech[];
  votes: Record<string, number | null>;
  killed_last_night: number[];
  winner: string | null;
  current_speaker: number | null;
  current_thinking: string | null;
  current_speech?: string;
  night_info?: string;
  phase_info?: string;
}

export type GamePhase =
  | 'game_init'
  | 'night'
  | 'day'
  | 'vote'
  | 'revote'
  | 'game_over';

export interface PlayerConfig {
  seat_id: number;
  player_name: string;
  model_name: string;
  provider: string;
  api_key: string;
  base_url?: string;
}

export interface ModelPreset {
  provider: string;
  name: string;
  model: string;
  description: string;
}

export interface CreateGameResponse {
  game_id: string;
  players: Player[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/game.ts
git commit -m "feat: add frontend TypeScript game types"
```

---

## Task 8: 前端 WebSocket Hook

**Files:**
- Create: `frontend/src/hooks/useGameSocket.ts`

- [ ] **Step 1: 创建 WebSocket Hook**

```typescript
// frontend/src/hooks/useGameSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import type { PublicGameState } from '../types/game';

const WS_BASE = 'ws://localhost:8000';

export function useGameSocket(gameId: string | null) {
  const [gameState, setGameState] = useState<PublicGameState | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;

    const ws = new WebSocket(`${WS_BASE}/game/${gameId}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PublicGameState;
        setGameState(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    // Keep-alive ping every 30s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [gameId]);

  return { gameState, connected };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useGameSocket.ts
git commit -m "feat: add WebSocket hook for real-time game state"
```

---

## Task 9: 前端组件

**Files:**
- Create: `frontend/src/components/GameSetup.tsx`
- Create: `frontend/src/components/PlayerCard.tsx`
- Create: `frontend/src/components/SpeechPanel.tsx`
- Create: `frontend/src/components/HistoryPanel.tsx`
- Create: `frontend/src/components/NightActionPanel.tsx`
- Create: `frontend/src/components/GameBoard.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 GameSetup 组件（游戏配置界面）**

```typescript
// frontend/src/components/GameSetup.tsx
import { useState } from 'react';
import type { PlayerConfig, ModelPreset } from '../types/game';

const API_BASE = 'http://localhost:8000';

interface Props {
  onGameCreated: (gameId: string) => void;
}

const DEFAULT_PLAYERS: PlayerConfig[] = Array.from({ length: 6 }, (_, i) => ({
  seat_id: i + 1,
  player_name: `玩家${i + 1}`,
  model_name: 'claude-sonnet-4-6-20250514',
  provider: 'anthropic',
  api_key: '',
}));

export default function GameSetup({ onGameCreated }: Props) {
  const [players, setPlayers] = useState<PlayerConfig[]>(DEFAULT_PLAYERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [modelPresets] = useState<ModelPreset[]>([
    { provider: 'anthropic', name: 'Claude Sonnet 4.6', model: 'claude-sonnet-4-6-20250514', description: 'Anthropic Claude' },
    { provider: 'openai', name: 'GPT-4o', model: 'gpt-4o', description: 'OpenAI GPT-4o' },
    { provider: 'openai', name: 'GPT-4.1', model: 'gpt-4.1', description: 'OpenAI GPT-4.1' },
    { provider: 'google', name: 'Gemini 2.5 Pro', model: 'gemini-2.5-pro-exp-03-25', description: 'Google Gemini' },
  ]);

  const updatePlayer = (seat: number, field: keyof PlayerConfig, value: string) => {
    setPlayers((prev) =>
      prev.map((p) => (p.seat_id === seat ? { ...p, [field]: value } : p))
    );
  };

  const handleCreateGame = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/game/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ players }),
      });
      if (!res.ok) throw new Error('Failed to create game');
      const data = await res.json();
      onGameCreated(data.game_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>AI 狼人杀 - 游戏配置</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {players.map((p) => (
          <div key={p.seat_id} style={{ border: '1px solid #ccc', padding: 12, borderRadius: 8 }}>
            <h3>{p.seat_id}号 - {p.player_name}</h3>
            <label>
              名称: <input value={p.player_name} onChange={(e) => updatePlayer(p.seat_id, 'player_name', e.target.value)} />
            </label>
            <br />
            <label>
              模型:
              <select value={p.model_name} onChange={(e) => {
                const preset = modelPresets.find((m) => m.model === e.target.value);
                if (preset) {
                  updatePlayer(p.seat_id, 'model_name', preset.model);
                  updatePlayer(p.seat_id, 'provider', preset.provider);
                }
              }}>
                {modelPresets.map((m) => (
                  <option key={m.model} value={m.model}>{m.name}</option>
                ))}
              </select>
            </label>
            <br />
            <label>
              API Key: <input type="password" value={p.api_key} onChange={(e) => updatePlayer(p.seat_id, 'api_key', e.target.value)} placeholder="sk-..." />
            </label>
          </div>
        ))}
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <button
        onClick={handleCreateGame}
        disabled={loading}
        style={{ marginTop: 24, padding: '12px 32px', fontSize: 16 }}
      >
        {loading ? '创建中...' : '创建游戏'}
      </button>

      <p style={{ marginTop: 8, color: '#666', fontSize: 14 }}>
        创建游戏后，角色将随机分配。游戏自动开始。
      </p>
    </div>
  );
}
```

- [ ] **Step 2: 创建 PlayerCard 组件**

```typescript
// frontend/src/components/PlayerCard.tsx
import type { Player } from '../types/game';

interface Props {
  player: Player;
  isCurrentPlayer: boolean;
  isSpectator: boolean;
}

export default function PlayerCard({ player, isCurrentPlayer, isSpectator }: Props) {
  const statusColor = player.is_alive ? '#4caf50' : '#f44336';

  return (
    <div
      style={{
        border: isCurrentPlayer ? '2px solid gold' : '1px solid #666',
        borderRadius: 8,
        padding: 12,
        background: player.is_alive ? '#1a1a2e' : '#2a1a1a',
        minWidth: 120,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 'bold' }}>
        {player.seat_id}号
      </div>
      <div style={{ fontSize: 14 }}>{player.player_name}</div>
      {isSpectator && (
        <div style={{
          marginTop: 4,
          padding: '2px 8px',
          borderRadius: 4,
          background: player.role === 'werewolf' ? '#d32f2f' :
                      player.role === 'prophet' ? '#1976d2' :
                      player.role === 'witch' ? '#7b1fa2' : '#388e3c',
          fontSize: 12,
          color: '#fff',
        }}>
          {player.role === 'werewolf' ? '狼人' :
           player.role === 'prophet' ? '预言家' :
           player.role === 'witch' ? '女巫' : '村民'}
        </div>
      )}
      <div style={{
        marginTop: 4,
        width: 12,
        height: 12,
        borderRadius: '50%',
        background: statusColor,
        display: 'inline-block',
      }} />
      <div style={{ fontSize: 11 }}>{player.model_name}</div>
    </div>
  );
}
```

- [ ] **Step 3: 创建 SpeechPanel 组件**

```typescript
// frontend/src/components/SpeechPanel.tsx
interface Props {
  currentSpeaker: number | null;
  currentThinking: string | null;
  currentSpeech: string | null;
}

export default function SpeechPanel({ currentSpeaker, currentThinking, currentSpeech }: Props) {
  if (currentSpeaker === null) {
    return (
      <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
        <p>等待游戏开始...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
      <h3>当前发言：{currentSpeaker}号玩家</h3>

      {currentThinking && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ color: '#888' }}>思考过程</h4>
          <div style={{
            padding: 12,
            background: '#111',
            borderRadius: 4,
            whiteSpace: 'pre-wrap',
            fontSize: 14,
            color: '#aaa',
            maxHeight: 200,
            overflowY: 'auto',
          }}>
            {currentThinking}
          </div>
        </div>
      )}

      {currentSpeech && (
        <div>
          <h4 style={{ color: '#888' }}>发言内容</h4>
          <div style={{
            padding: 12,
            background: '#1a1a2e',
            borderRadius: 4,
            fontSize: 16,
            color: '#fff',
            border: '1px solid gold',
          }}>
            {currentSpeech}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 创建 HistoryPanel 组件**

```typescript
// frontend/src/components/HistoryPanel.tsx
import { useEffect, useRef } from 'react';
import type { Speech } from '../types/game';

interface Props {
  speechHistory: Speech[];
}

export default function HistoryPanel({ speechHistory }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [speechHistory.length]);

  if (speechHistory.length === 0) {
    return (
      <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
        <h4>发言历史</h4>
        <p style={{ color: '#666' }}>暂无发言</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
      <h4>发言历史</h4>
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        {speechHistory.map((s, idx) => (
          <div key={idx} style={{
            marginBottom: 12,
            padding: 8,
            background: '#1a1a2e',
            borderRadius: 6,
          }}>
            <div style={{ fontSize: 13, color: '#888' }}>
              [{s.seat_id}号 {s.player_name}]
            </div>
            <div style={{ marginTop: 4, fontSize: 14, color: '#ddd' }}>
              {s.content}
            </div>
            <details style={{ marginTop: 6 }}>
              <summary style={{ fontSize: 12, color: '#666', cursor: 'pointer' }}>
                查看思考过程
              </summary>
              <div style={{
                marginTop: 4,
                padding: 8,
                background: '#111',
                borderRadius: 4,
                fontSize: 13,
                color: '#999',
                whiteSpace: 'pre-wrap',
              }}>
                {s.thinking}
              </div>
            </details>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 创建 NightActionPanel 组件**

```typescript
// frontend/src/components/NightActionPanel.tsx
interface Props {
  nightInfo: string | undefined;
  currentThinking: string | null;
}

export default function NightActionPanel({ nightInfo, currentThinking }: Props) {
  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8, background: '#0a0a1e' }}>
      <h4 style={{ color: '#7b1fa2' }}>夜晚阶段</h4>

      {nightInfo && (
        <div style={{ marginBottom: 12, fontSize: 14, color: '#ccc' }}>
          {nightInfo}
        </div>
      )}

      {currentThinking && (
        <div style={{
          padding: 12,
          background: '#111',
          borderRadius: 4,
          whiteSpace: 'pre-wrap',
          fontSize: 14,
          color: '#aaa',
        }}>
          {currentThinking}
        </div>
      )}

      {!nightInfo && !currentThinking && (
        <p style={{ color: '#666' }}>夜晚行动进行中...</p>
      )}
    </div>
  );
}
```

- [ ] **Step 6: 创建 GameBoard 主组件**

```typescript
// frontend/src/components/GameBoard.tsx
import PlayerCard from './PlayerCard';
import SpeechPanel from './SpeechPanel';
import HistoryPanel from './HistoryPanel';
import NightActionPanel from './NightActionPanel';
import type { PublicGameState } from '../types/game';

interface Props {
  gameState: PublicGameState;
  gameId: string;
  connected: boolean;
  onStartGame: () => void;
}

export default function GameBoard({ gameState, gameId, connected, onStartGame }: Props) {
  const { phase, day, players, speech_history, full_history, current_speaker, current_thinking, current_speech, night_info, phase_info, winner } = gameState;

  const isNight = phase === 'night';
  const isGameOver = phase === 'game_over';
  const isGameInit = phase === 'game_init';

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      {/* 顶部信息栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2>
          {isGameInit ? '等待游戏开始' : isGameOver ? '游戏结束' : `第 ${day} 天 - ${isNight ? '夜晚' : '白天'}`}
        </h2>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{
            padding: '4px 12px',
            borderRadius: 4,
            fontSize: 13,
            background: connected ? '#2e7d32' : '#c62828',
            color: '#fff',
          }}>
            {connected ? '已连接' : '断开'}
          </span>
          <span style={{ fontSize: 13, color: '#666' }}>ID: {gameId}</span>
        </div>
      </div>

      {/* 玩家卡片 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        marginBottom: 24,
      }}>
        {players.map((p) => (
          <PlayerCard
            key={p.seat_id}
            player={p}
            isCurrentPlayer={p.seat_id === current_speaker}
            isSpectator={true}
          />
        ))}
      </div>

      {/* 状态提示 */}
      {phase_info && (
        <div style={{
          padding: 12,
          marginBottom: 16,
          background: phase_info.includes('胜利') ? '#1b5e20' : '#37474f',
          borderRadius: 8,
          fontSize: 16,
          fontWeight: 'bold',
          textAlign: 'center',
          color: '#fff',
        }}>
          {phase_info}
        </div>
      )}

      {isGameInit && (
        <div style={{ textAlign: 'center' }}>
          <button onClick={onStartGame} style={{ padding: '12px 32px', fontSize: 16, cursor: 'pointer' }}>
            开始游戏
          </button>
        </div>
      )}

      {/* 夜晚 / 白天 */}
      {isNight ? (
        <NightActionPanel nightInfo={night_info} currentThinking={current_thinking} />
      ) : (
        !isGameInit && !isGameOver && (
          <SpeechPanel
            currentSpeaker={current_speaker}
            currentThinking={current_thinking}
            currentSpeech={current_speech}
          />
        )
      )}

      {/* 发言历史 */}
      <div style={{ marginTop: 24 }}>
        <HistoryPanel speechHistory={full_history} />
      </div>

      {/* 游戏结束 */}
      {isGameOver && winner && (
        <div style={{
          marginTop: 24,
          padding: 24,
          background: '#1b5e20',
          borderRadius: 12,
          textAlign: 'center',
          fontSize: 24,
          fontWeight: 'bold',
          color: '#fff',
        }}>
          {winner === 'villager' ? '好人阵营 胜利！' : '狼人阵营 胜利！'}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: 更新 App.tsx 整合所有组件**

```typescript
// frontend/src/App.tsx
import { useState } from 'react';
import GameSetup from './components/GameSetup';
import GameBoard from './components/GameBoard';
import { useGameSocket } from './hooks/useGameSocket';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const { gameState, connected } = useGameSocket(gameId);

  const handleGameCreated = (id: string) => {
    setGameId(id);
  };

  const handleStartGame = async () => {
    if (!gameId) return;
    try {
      await fetch(`${API_BASE}/game/${gameId}/start`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to start game', err);
    }
  };

  // 游戏配置阶段
  if (!gameId || !gameState) {
    return <GameSetup onGameCreated={handleGameCreated} />;
  }

  // 游戏进行中
  return (
    <GameBoard
      gameState={gameState}
      gameId={gameId}
      connected={connected}
      onStartGame={handleStartGame}
    />
  );
}
```

- [ ] **Step 8: 验证前端构建**

```bash
cd frontend
npm run build
```

Expected: Build 成功，无 TypeScript 错误。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/ frontend/src/App.tsx
git commit -m "feat: add frontend game components (GameSetup, GameBoard, SpeechPanel, HistoryPanel)"
```

---

## Task 10: 集成与验证

**Files:**
- 无新文件 — 验证全链路

- [ ] **Step 1: 启动后端**

```bash
cd backend
python main.py &
sleep 3
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 2: 创建游戏（API 测试）**

```bash
curl -X POST http://localhost:8000/game/create \
  -H "Content-Type: application/json" \
  -d '{
    "players": [
      {"seat_id":1,"player_name":"玩家1","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"},
      {"seat_id":2,"player_name":"玩家2","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"},
      {"seat_id":3,"player_name":"玩家3","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"},
      {"seat_id":4,"player_name":"玩家4","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"},
      {"seat_id":5,"player_name":"玩家5","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"},
      {"seat_id":6,"player_name":"玩家6","model_name":"gpt-4o","provider":"openai","api_key":"sk-test"}
    ]
  }'
```

Expected: 返回 game_id 和 6 个玩家的角色信息。

- [ ] **Step 3: 检查前端页面**

```bash
cd frontend
npm run dev
# 打开 http://localhost:5173
# 应看到游戏配置页面
# 配置玩家并创建游戏
```

- [ ] **Step 4: 运行全部后端测试**

```bash
pytest tests/ -v
```

Expected: 所有测试通过。

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat: integration verification - full pipeline working"
```

---

## 后续计划（不在第一版范围内）

- [ ] `.env` 文件管理 API Key（避免前端暴露）
- [ ] 游戏速度控制（快进按钮）
- [ ] 数据库持久化游戏记录
- [ ] 警长环节
- [ ] 猎人 + 更多神职
- [ ] 狼人配合策略（多轮协商）
- [ ] 真人玩家加入
- [ ] UI 美化（动画、音效）
- [ ] 多局统计
