# 地基修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 AI 狼人杀基础局能稳定打完——通过结构化输出消除解析错位、合法性校验防止杀队友/投自己、结构化记忆消除前后矛盾。

**Architecture:** 在现有手写适配层内做三处增强：(1) `LLMResponse` 增加 `target_seat` 结构化字段，正则降级为 fallback；(2) engine 新增集中的 `_call_ai_with_target` 做合法性校验+重试1次+降级；(3) `private_data` 维护客观事实记忆，渲染成人话注入各角色 prompt。不引入框架，保持轻量。

**Tech Stack:** Python 3.11, FastAPI, pytest, openai/anthropic/google-generativeai SDK。

**对应 spec:** `docs/superpowers/specs/2026-05-31-foundation-fixes-design.md`

---

## 文件结构

| 文件 | 职责 | 改动 |
|------|------|------|
| `backend/game/llm/base.py` | LLM 响应解析 | `LLMResponse` 加 `target_seat`；`from_text` 解析该字段 |
| `backend/game/engine.py` | 流程编排 | 新增 `_call_ai_with_target`；升级 system prompt；替换各环节调用；写入记忆 |
| `backend/game/state.py` | 状态与视角 | `create_game_state` 初始化记忆字段（透传已支持） |
| `backend/game/roles/werewolf.py` | 狼人 prompt | 渲染 `kill_history` / `my_votes` 人话 |
| `backend/game/roles/prophet.py` | 预言家 prompt | 渲染 `my_votes`（查验记录已有） |
| `backend/game/roles/witch.py` | 女巫 prompt | 渲染 `potion_history` / `my_votes` |
| `backend/game/roles/villager.py` | 村民 prompt | 渲染 `my_votes` |
| `tests/test_llm.py` | 解析测试 | 新增 `target_seat` 解析用例 |
| `tests/test_engine.py` | 引擎测试 | 新增校验+重试、记忆写入用例 |
| `tests/test_state.py` | 状态测试 | 新增记忆字段初始化用例 |
| `tests/test_roles.py` | 角色测试 | 新增记忆渲染用例 |

**任务顺序**：Task 1（结构化输出，最底层、无依赖）→ Task 2（记忆字段，state 层）→ Task 3（校验+重试，依赖 Task 1）→ Task 4（记忆写入，依赖 Task 2+3）→ Task 5（记忆渲染，依赖 Task 2）→ Task 6（回归验证）。

---

## Task 1: 结构化输出 — `LLMResponse.target_seat`

**Files:**
- Modify: `backend/game/llm/base.py`（`LLMResponse` dataclass + `from_text`）
- Test: `tests/test_llm.py`

**背景**：`from_text` 当前只解析 `thinking`/`action`。增加 `target_seat` 字段，从同一段 JSON 里读取座位号；非 JSON 或缺失时保持 `None`，由 engine 走正则 fallback。

- [ ] **Step 1: 写失败测试**

在 `tests/test_llm.py` 末尾追加：

```python
def test_llm_response_parses_target_seat():
    resp = LLMResponse.from_text('{"thinking": "刀5号", "action": "我刀5号", "target_seat": 5}')
    assert resp.target_seat == 5


def test_llm_response_target_seat_absent_is_none():
    resp = LLMResponse.from_text('{"thinking": "分析", "action": "投票给3号"}')
    assert resp.target_seat is None


def test_llm_response_target_seat_in_code_fence():
    resp = LLMResponse.from_text(
        '```json\n{"thinking": "t", "action": "a", "target_seat": 2}\n```'
    )
    assert resp.target_seat == 2


def test_llm_response_target_seat_out_of_range_is_none():
    resp = LLMResponse.from_text('{"thinking": "t", "action": "a", "target_seat": 99}')
    assert resp.target_seat is None


def test_llm_response_target_seat_string_coerced():
    resp = LLMResponse.from_text('{"thinking": "t", "action": "a", "target_seat": "4"}')
    assert resp.target_seat == 4
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_llm.py -k target_seat -v`
Expected: FAIL（`LLMResponse` 无 `target_seat` 属性 / TypeError）

- [ ] **Step 3: 修改 `LLMResponse`**

在 `backend/game/llm/base.py` 中：

dataclass 增加字段：

```python
@dataclass
class LLMResponse:
    """AI 玩家的响应"""
    thinking: str
    action: str
    target_seat: Optional[int] = None
```

增加一个模块级辅助函数（放在 `from_text` 之前或类外）：

```python
def _coerce_seat(value) -> Optional[int]:
    """把任意值转成合法座位号(1-6)，非法返回 None。"""
    if value is None:
        return None
    try:
        seat = int(value)
    except (ValueError, TypeError):
        return None
    return seat if 1 <= seat <= 6 else None
```

- [ ] **Step 4: 在 `from_text` 的两处 JSON 解析分支读取 `target_seat`**

`from_text` 里现有两处 `return cls(...)` 是从 `data`（解析出的 dict）构造的（代码块 JSON 分支和直接 JSON 分支）。两处都改为：

```python
            return cls(
                thinking=think_content or data.get("thinking", ""),
                action=data.get("action", ""),
                target_seat=_coerce_seat(data.get("target_seat")),
            )
```

最后的降级分支（纯文本，无 JSON）保持不变（`target_seat` 默认 `None`）。

- [ ] **Step 5: 运行新测试确认通过**

Run: `pytest tests/test_llm.py -k target_seat -v`
Expected: PASS（5 个用例）

- [ ] **Step 6: 运行全部 llm 测试确认无回归**

Run: `pytest tests/test_llm.py -v`
Expected: PASS（原有用例 + 新增用例全绿）

- [ ] **Step 7: Commit**

```bash
git add backend/game/llm/base.py tests/test_llm.py
git commit -m "feat(llm): add structured target_seat field to LLMResponse"
```

---

## Task 2: 结构化记忆字段初始化 — `state.py`

**Files:**
- Modify: `backend/game/state.py`（`create_game_state` 中 `private_data` 初始化）
- Test: `tests/test_state.py`

**背景**：`create_game_state` 当前按角色初始化 `private_data`：狼人有 `teammates`、预言家有 `check_results`、女巫有药量+`night_kill_target`。本任务为所有玩家加通用记忆 `my_votes`，并给狼人加 `kill_history`、女巫加 `potion_history`。`get_player_view` 已整体透传 `private_data`，无需改动。

- [ ] **Step 1: 写失败测试**

在 `tests/test_state.py` 末尾追加：

```python
def test_all_players_have_my_votes_memory():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    for p in state.players:
        view = get_player_view(state, p.seat_id)
        assert view["private_data"]["my_votes"] == {}


def test_werewolf_has_kill_history_memory():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    wolf_seat = [p.seat_id for p in state.players if p.role == "werewolf"][0]
    view = get_player_view(state, wolf_seat)
    assert view["private_data"]["kill_history"] == {}


def test_witch_has_potion_history_memory():
    state = create_game_state([
        {"seat_id": i, "player_name": f"玩家{i}", "model_name": "gpt-4o"}
        for i in range(1, 7)
    ])
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    view = get_player_view(state, witch_seat)
    assert view["private_data"]["potion_history"] == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_state.py -k "my_votes or kill_history or potion_history" -v`
Expected: FAIL（KeyError）

- [ ] **Step 3: 修改 `create_game_state`**

在 `backend/game/state.py` 的 `create_game_state` 里，循环构造 `pd` 的部分改为（保留现有字段，新增记忆字段）：

```python
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
```

- [ ] **Step 4: 运行新测试确认通过**

Run: `pytest tests/test_state.py -k "my_votes or kill_history or potion_history" -v`
Expected: PASS（3 个用例）

- [ ] **Step 5: 运行全部 state 测试确认无回归**

Run: `pytest tests/test_state.py -v`
Expected: PASS（原有 + 新增全绿；注意 `test_get_player_view_villager` 断言 villager 无 `teammates`，仍成立）

- [ ] **Step 6: Commit**

```bash
git add backend/game/state.py tests/test_state.py
git commit -m "feat(state): add structured memory fields (my_votes/kill_history/potion_history)"
```

---

## Task 3: 合法性校验 + 重试辅助方法（隔离实现）

**Files:**
- Modify: `backend/game/engine.py`（`_call_ai` 增加 `target_seat` 透传；新增 `_extract_valid_target`、`_call_ai_with_target`）
- Test: `tests/test_engine.py`

**背景**：先把校验+重试逻辑做成可单独测试的辅助方法，**本任务不接入各环节调用点**（接入在 Task 4）。

**关键回归约束**：现有 `test_game_e2e.py` 的 mock 写法是 `engine._call_ai = mock_call`，返回的 dict **没有 `target_seat`**。因此辅助方法在 `target_seat` 缺失时必须 fallback 到 `_parse_target`，否则 e2e 失效。

- [ ] **Step 1: 写失败测试**

在 `tests/test_engine.py` 末尾追加：

```python
import asyncio
from unittest.mock import AsyncMock


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_engine.py -k "extract_valid or call_ai_with_target" -v`
Expected: FAIL（方法不存在）

- [ ] **Step 3: `_call_ai` 增加 `target_seat` 透传**

`backend/game/engine.py` 的 `_call_ai` 成功分支 return 改为：

```python
            return {
                "thinking": response.thinking,
                "action": response.action,
                "target_seat": response.target_seat,
            }
```

异常分支 return 改为：

```python
            return {"thinking": f"调用失败: {e}", "action": "（无法响应）", "target_seat": None}
```

- [ ] **Step 4: 新增两个辅助方法**

在 `GameEngine` 类中（建议放在 `_parse_target` 附近）新增：

```python
    def _extract_valid_target(self, result: Dict[str, Any], valid_targets) -> Optional[int]:
        """优先取结构化 target_seat，缺失则正则 fallback；校验是否在合法集合内。"""
        target = result.get("target_seat")
        if target is None:
            target = self._parse_target(result.get("action", "") or "", [])
        if target in valid_targets:
            return target
        return None

    async def _call_ai_with_target(self, seat_id: int, prompt: str, valid_targets, action_name: str):
        """调用 AI 并校验目标合法性；非法则带原因重试 1 次，仍失败则降级(target=None)。
        返回 (target, thinking, action)。"""
        result = await self._call_ai(seat_id, prompt)
        target = self._extract_valid_target(result, valid_targets)
        if target is not None:
            return target, result["thinking"], result["action"]

        # 重试 1 次，反馈具体非法选择
        chosen = result.get("target_seat")
        if chosen is None:
            chosen = self._parse_target(result.get("action", "") or "", [])
        valid_list = "、".join(f"{s}号" for s in sorted(valid_targets))
        retry_prompt = (
            prompt
            + f"\n\n【系统提示】你刚才选择的 {chosen}号 不是合法的{action_name}目标。"
            + f"请只从以下合法目标中选择：{valid_list}。"
            + "并把座位号填入 target_seat 字段。"
        )
        logger.info(f"[校验] {seat_id}号 {action_name} 选择非法({chosen})，重试 1 次")
        result = await self._call_ai(seat_id, retry_prompt)
        target = self._extract_valid_target(result, valid_targets)
        if target is None:
            logger.info(f"[校验] {seat_id}号 {action_name} 重试仍非法，降级处理")
        return target, result["thinking"], result["action"]
```

- [ ] **Step 5: 运行新测试确认通过**

Run: `pytest tests/test_engine.py -k "extract_valid or call_ai_with_target" -v`
Expected: PASS（6 个用例）

- [ ] **Step 6: 运行全部 engine 测试确认无回归**

Run: `pytest tests/test_engine.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/game/engine.py tests/test_engine.py
git commit -m "feat(engine): add target validation + single-retry helper"
```

---

## Task 4: 接入调用点 + 写入记忆

**Files:**
- Modify: `backend/game/engine.py`（狼人刀人 / 预言家验人 / 女巫毒人 / 投票 / 重投 五处接入；记忆写入）
- Test: `tests/test_engine.py`（端到端校验行为），`tests/test_game_e2e.py`（回归）

**背景**：把 Task 3 的 `_call_ai_with_target` 接入各环节，并在决策落地后写入记忆字段。狼人/预言家/投票直接用结构化目标；女巫按 spec 特殊处理（救=固定刀口不校验，毒=走校验）。

**记忆写入点**：
- 投票结算后（`_run_vote` 与重投循环）→ `private_data[seat]["my_votes"][state.day] = target`
- 狼人刀人确定后 → `private_data[wolf]["kill_history"][state.day] = target`（写入所有狼）
- 女巫用药后 → `private_data[witch]["potion_history"].append({"day": state.day, "type": "save"/"poison", "target": target})`
- 预言家验人 → `check_results` 已有逻辑，保留

- [ ] **Step 1: 写校验行为测试（端到端，mock 出非法选择）**

在 `tests/test_engine.py` 末尾追加：

```python
def test_wolf_cannot_kill_teammate_e2e():
    """狼人首选刀队友 → 被校验拦下并重试，最终不会把队友写进刀杀目标"""
    e = GameEngine(_make_config(), interactive=False)
    state = e.state
    wolf_seats = sorted([p.seat_id for p in state.players if p.role == "werewolf"])
    witch_seat = [p.seat_id for p in state.players if p.role == "witch"][0]
    good_non_witch = [p.seat_id for p in state.players
                      if p.role != "werewolf" and p.seat_id != witch_seat][0]

    async def mock_call(seat_id, prompt):
        # 狼人若被提示重试(prompt 含"系统提示")则改选合法目标，否则先选队友(非法)
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
    # 刀杀目标不能是任何狼人
    for a in kill_actions:
        assert a.target_seat not in wolf_seats


def test_my_votes_memory_written():
    """投票后 my_votes 应记录到投票者的 private_data"""
    e = GameEngine(_make_config(), interactive=False)
    state = e.state
    alive = get_alive_players_local(state)
    target = alive[0].seat_id if alive[0].seat_id != alive[1].seat_id else alive[1].seat_id
    voter = alive[1].seat_id
    fixed_target = alive[0].seat_id

    async def mock_call(seat_id, prompt):
        # 所有人投 fixed_target（若自己是 fixed_target 则投 voter 避免投自己）
        t = fixed_target if seat_id != fixed_target else voter
        return {"thinking": "投", "action": f"投{t}号", "target_seat": t}

    e._call_ai = mock_call
    asyncio.run(e._run_vote(alive))

    # 至少一个非 fixed_target 的存活玩家把票记进了 my_votes
    recorded = [p.seat_id for p in state.players
                if state.day in state.private_data[p.seat_id].get("my_votes", {})]
    assert len(recorded) >= 1
```

并在 `tests/test_engine.py` 顶部 import 区补一个本地辅助（避免与现有 import 冲突）：

```python
from game.state import get_alive_players as get_alive_players_local
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_engine.py -k "cannot_kill_teammate or my_votes_memory" -v`
Expected: FAIL（当前刀人/投票逻辑用 `_parse_target`，未接入校验与记忆）

- [ ] **Step 3: 接入狼人刀人**

`backend/game/engine.py` 狼人段，把每只狼的 `result = await self._call_ai(...)` 调用保留用于"协调展示"，但**最终目标解析**改为对每只狼计算合法目标并用 `_call_ai_with_target`。最简改法：将 `wolf_decisions` 收集阶段改为调用 `_call_ai_with_target`，合法目标集合为 `存活 且 非该狼队友 且 非自己`：

```python
        wolf_players = [p for p in alive if p.role == "werewolf"]
        wolf_decisions = []
        for i, wolf in enumerate(wolf_players):
            handler = get_role_handler("werewolf")
            view = get_player_view(state, wolf.seat_id)
            teammates = view["private_data"].get("teammates", [])
            valid = {p.seat_id for p in alive
                     if p.seat_id != wolf.seat_id and p.seat_id not in teammates}
            teammate_decision = wolf_decisions[0]["action"] if i > 0 else None
            prompt = handler.get_night_prompt(wolf.player_name, view, teammate_decision=teammate_decision)
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号({wolf.player_name}) 思考中...",
                "current_speaker": wolf.seat_id,
            }, waiting=False)
            target, thinking, action = await self._call_ai_with_target(
                wolf.seat_id, prompt, valid, "刀人")
            wolf_decisions.append({"seat_id": wolf.seat_id, "thinking": thinking,
                                   "action": action, "target": target})
            await self._push_update({
                "night_info": f"狼人 {wolf.seat_id}号({wolf.player_name}) 决定刀: {action}",
                "current_thinking": thinking,
                "current_speaker": wolf.seat_id,
            })
            await self._wait_step()
```

随后的"协调"块改为直接用已解析的 `target`：

```python
        if wolf_decisions:
            if len(wolf_decisions) >= 2:
                target_1 = wolf_decisions[0]["target"]
                target_2 = wolf_decisions[1]["target"]
                if target_1 == target_2 and target_1 is not None:
                    target, actor = target_1, wolf_decisions[0]["seat_id"]
                else:
                    target = target_2 or target_1
                    actor = wolf_decisions[1]["seat_id"] if target_2 else wolf_decisions[0]["seat_id"]
            else:
                target = wolf_decisions[0]["target"]
                actor = wolf_decisions[0]["seat_id"]
            if target:
                state.night_actions.append(NightAction(
                    action_type="kill", actor_seat=actor, target_seat=target,
                ))
                logger.info(f"[狼人] 最终刀人目标: {target}号 (由{actor}号决定)")
                # 写入记忆：所有狼记录本晚刀杀目标
                for wp in wolf_players:
                    state.private_data[wp.seat_id].setdefault("kill_history", {})[state.day] = target
                if witch_players:
                    state.private_data[witch_players[0].seat_id]["night_kill_target"] = target
                    logger.info(f"[女巫] 通知刀人目标: {target}号")
```

- [ ] **Step 4: 接入预言家验人**

预言家段：把 `result = await self._call_ai(...)` + `target = self._parse_target(...)` 改为：

```python
            valid = {q.seat_id for q in alive if q.seat_id != p.seat_id}
            target, thinking, action = await self._call_ai_with_target(
                p.seat_id, prompt, valid, "查验")
            result = {"thinking": thinking, "action": action}
```

（后续用到 `result["thinking"]` 的推送保持不变；`target` 用法不变。check_results 写入逻辑保留。）

- [ ] **Step 5: 接入女巫毒药**

女巫"毒"分支：把 `target = self._parse_target(action_text, alive)` 改为对毒目标做校验。在该分支内：

```python
                if not witch_action_desc and "毒" in action_text and state.witch_poison > 0:
                    valid = {q.seat_id for q in alive if q.seat_id != w.seat_id}
                    target = self._extract_valid_target(result, valid)
                    if target:
                        state.night_actions.append(NightAction(
                            action_type="poison", actor_seat=w.seat_id, target_seat=target,
                        ))
                        state.witch_poison = 0
                        state.private_data[w.seat_id]["poison_remaining"] = 0
                        state.private_data[w.seat_id].setdefault("potion_history", []).append(
                            {"day": state.day, "type": "poison", "target": target})
                        logger.info(f"[女巫] 使用毒药毒{target}号 (解药剩余:{state.witch_antidote})")
                        witch_action_desc = f"使用毒药毒 {target}号"
```

注意：女巫的 `result` 来自该段已有的 `result = await self._call_ai(w.seat_id, prompt)`，保持不变；只改目标解析。救药分支也补 potion_history：在 `witch_action_desc = f"使用解药救 {target}号"` 之后追加：

```python
                        state.private_data[w.seat_id].setdefault("potion_history", []).append(
                            {"day": state.day, "type": "save", "target": target})
```

- [ ] **Step 6: 接入投票（`_run_vote`）与重投**

`_run_vote` 循环里把 `result = await self._call_ai(...)` + `target = self._parse_target(...)` 改为：

```python
            valid = {q.seat_id for q in self.state.players
                     if q.is_alive and q.seat_id != seat_id}
            target, thinking, action = await self._call_ai_with_target(
                seat_id, prompt, valid, "投票")
            self.state.votes[seat_id] = target
            if target is not None:
                self.state.private_data[seat_id].setdefault("my_votes", {})[self.state.day] = target
            result = {"thinking": thinking}
```

重投循环（`run_day` 内 `state.phase == "revote"` 段）做同样替换（注意该处用 `state` 而非 `self.state`，且合法目标排除自己）：

```python
                valid = {q.seat_id for q in state.players
                         if q.is_alive and q.seat_id != seat_id}
                target, thinking, action = await self._call_ai_with_target(
                    seat_id, prompt, valid, "投票")
                state.votes[seat_id] = target
                if target is not None:
                    state.private_data[seat_id].setdefault("my_votes", {})[state.day] = target
                result = {"thinking": thinking}
```

- [ ] **Step 7: 运行新测试确认通过**

Run: `pytest tests/test_engine.py -k "cannot_kill_teammate or my_votes_memory" -v`
Expected: PASS

- [ ] **Step 8: 运行 e2e 回归（关键）**

Run: `pytest tests/test_game_e2e.py -v`
Expected: PASS（e2e 的 mock 无 target_seat，依赖 `_extract_valid_target` 的正则 fallback；若失败，检查 fallback 是否生效）

- [ ] **Step 9: Commit**

```bash
git add backend/game/engine.py tests/test_engine.py
git commit -m "feat(engine): wire target validation into all phases + write memory"
```

---

## Task 5: 记忆渲染成人话（角色 prompt）

**Files:**
- Modify: `backend/game/roles/werewolf.py`、`prophet.py`、`witch.py`、`villager.py`
- Test: `tests/test_roles.py`

**背景**：记忆字段已在 view 的 `private_data` 中。本任务在各角色的发言/投票 prompt 里把记忆渲染成自然语言，给模型一致的事实锚点。为避免重复代码，在每个 handler 内加一个小的 `_format_my_votes` 辅助。

- [ ] **Step 1: 写失败测试**

在 `tests/test_roles.py` 末尾追加：

```python
def test_werewolf_speech_renders_kill_history():
    handler = WerewolfHandler()
    prompt = handler.get_day_speech_prompt(
        player_name="玩家1",
        view={
            "day": 2,
            "private_data": {"teammates": [5], "kill_history": {1: 6}, "my_votes": {1: 3}},
            "full_history": [],
            "speech_history": [],
        },
    )
    assert "6号" in prompt   # 刀杀记录被渲染


def test_villager_vote_renders_my_votes():
    handler = VillagerHandler()
    prompt = handler.get_vote_prompt(
        player_name="玩家6",
        view={
            "day": 2,
            "private_data": {"my_votes": {1: 3}},
            "players": [{"seat_id": 1, "player_name": "玩家1", "is_alive": True}],
            "full_history": [],
            "speech_history": [],
        },
    )
    assert "3号" in prompt   # 历史投票被渲染
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_roles.py -k "renders_kill_history or renders_my_votes" -v`
Expected: FAIL（prompt 不含对应内容）

- [ ] **Step 3: 在 werewolf.py 渲染**

`WerewolfHandler` 加辅助方法：

```python
    def _format_memory(self, view):
        pd = view.get("private_data", {})
        lines = []
        kh = pd.get("kill_history", {})
        if kh:
            lines.append("你的刀杀记录：" + "、".join(f"第{d}晚刀{t}号" for d, t in kh.items()))
        mv = pd.get("my_votes", {})
        if mv:
            lines.append("你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items()))
        return ("\n" + "\n".join(lines)) if lines else ""
```

在 `get_day_speech_prompt` 的返回 prompt 中，紧接 `action_context` 之后插入 `{self._format_memory(view)}`；在 `get_vote_prompt` 的 `history_text` 之后插入同样的 `{self._format_memory(view)}`。

- [ ] **Step 4: 在 prophet.py / witch.py / villager.py 渲染**

三个 handler 各加一个 `_format_my_votes`（村民只有投票记忆）：

```python
    def _format_my_votes(self, view):
        mv = view.get("private_data", {}).get("my_votes", {})
        if not mv:
            return ""
        return "\n你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items())
```

- prophet.py：在 `get_day_speech_prompt` 与 `get_vote_prompt` 的查验记录附近插入 `{self._format_my_votes(view)}`（查验记忆 `check_results` 已渲染，无需改）。
- witch.py：加 `_format_potion_and_votes`：

```python
    def _format_my_votes(self, view):
        pd = view.get("private_data", {})
        lines = []
        ph = pd.get("potion_history", [])
        if ph:
            lines.append("你的用药记录：" + "、".join(
                f"第{r['day']}晚{'救' if r['type']=='save' else '毒'}{r['target']}号" for r in ph))
        mv = pd.get("my_votes", {})
        if mv:
            lines.append("你的投票记录：" + "、".join(f"第{d}天投{t}号" for d, t in mv.items()))
        return ("\n" + "\n".join(lines)) if lines else ""
```

  在 witch `get_day_speech_prompt` 与 `get_vote_prompt` 中插入 `{self._format_my_votes(view)}`。
- villager.py：加上面通用的 `_format_my_votes`，在 `get_day_speech_prompt` 与 `get_vote_prompt` 中插入。

- [ ] **Step 5: 运行新测试确认通过**

Run: `pytest tests/test_roles.py -k "renders_kill_history or renders_my_votes" -v`
Expected: PASS

- [ ] **Step 6: 运行全部 roles 测试确认无回归**

Run: `pytest tests/test_roles.py -v`
Expected: PASS（注意现有测试传入的 view 多数无 `private_data` 或无记忆键，`_format_*` 用 `.get` 容错，返回空串，不影响断言）

- [ ] **Step 7: Commit**

```bash
git add backend/game/roles/ tests/test_roles.py
git commit -m "feat(roles): render structured memory into role prompts"
```

---

## Task 6: 全量回归与验证

**Files:** 无新增改动，仅验证。

- [ ] **Step 1: 运行完整测试套件**

Run: `pytest -v`
Expected: 全部 PASS（原有 21 个 + 本次新增用例）。若有失败，回到对应 Task 修复。

- [ ] **Step 2: 真实对局验证（可选，需 API key）**

若 `backend/config/players.json` 配好可用 key：
启动后端 `python backend/main.py`，前端发起一局，重点观察：
- 狼人是否仍刀队友（应消失）
- 投票是否投自己/投死人（应消失）
- 预言家/女巫发言是否与自己的客观记录一致（前后矛盾应明显减少）

若无可用 key，跳过此步，并在完成说明中标注"未经真实对局验证，以测试全绿为准"。

- [ ] **Step 3: 最终提交（如有验证产生的微调）**

```bash
git add -A
git commit -m "test: full regression for foundation fixes"
```

---

## Self-Review 记录

- **Spec 覆盖**：结构化输出→Task1；记忆字段→Task2；校验+重试→Task3；接入+记忆写入→Task4；记忆渲染→Task5；测试/回归→Task6。女巫二维特殊处理→Task4 Step5。预言家放宽"未验过"→Task4 Step4（valid 仅排除自己）。✅
- **类型一致性**：`_call_ai_with_target` 返回 `(target, thinking, action)` 三元组，Task3 定义、Task4 各处一致使用；`_extract_valid_target(result, valid_targets)` 签名一致；记忆键名 `my_votes`/`kill_history`/`potion_history` 在 Task2/4/5 一致。✅
- **回归约束**：e2e mock 无 `target_seat` → 依赖 `_extract_valid_target` 正则 fallback，已在 Task3 背景与 Task4 Step8 标注。✅
