# AI 狼人杀 - 地基修复设计文档

**日期**：2026-05-31
**状态**：草稿
**范围**：地基修复（结构化输出 + 合法性校验 + 结构化记忆），让基础局能稳定打完、不杀队友、不前后矛盾。

---

## 一、背景与问题

当前实现能跑流程，但基础局不稳定，主要有三类问题：

1. **杀队友 / 投错人**：`engine._parse_target` 用正则从模型的自由文本 `action` 里抠座位号（取第一个 `X号` 或第一个 `1-6` 数字）。当模型说"不刀队友3号，刀5号"时，正则抓到第一个"3号"=队友，导致决策被解析错位。模型本身没错，是解析层吞掉了决策。

2. **缺少合法性约束**：即便解析正确，执行层也不校验目标是否合法（狼人不能刀队友/自己、不能选已死玩家、投票不能投自己），非法目标照常执行。

3. **前后矛盾**：每轮把 `full_history` 整段原始发言喂给模型，让它每次重新"回忆"自己做过什么。模型没有一份结构化的、属于自己的事实记忆，导致第二天与第一天对不上。

**本次明确不做（YAGNI，留待后续）**：策略注入（悍跳/对跳等高级玩法）、推理模型接入、对局持久化、人数/角色可配置、README。

---

## 二、设计决策（已与用户确认）

| 决策点 | 选择 |
|--------|------|
| 范围 | 仅地基：结构化输出 + 结构化记忆 |
| 结构化输出方式 | 强约束 JSON + 校验重试（不引入原生 tool calling，三家统一） |
| 记忆内容 | 仅客观事实（不含"对外宣称"，宣称留给后续策略阶段） |
| 校验失败处理 | 带原因重试 1 次，仍失败则降级（夜晚=放弃行动 / 投票=弃票） |
| 投票投自己 | 禁止 |
| 重试反馈 | 告知上次的具体非法选择和原因 |
| 记忆注入形式 | 渲染成自然语言人话，而非裸 dict |
| 是否引入框架 | 否，保持手写轻量适配层 |

---

## 三、改动设计

### 3.1 结构化输出（`game/llm/base.py`）

**目标**：让模型把"选谁"的决策放进一个独立字段，而不是埋在自由文本里。

- `LLMResponse` 增加可选字段 `target_seat: Optional[int] = None`。
- system prompt 的输出格式从 `{thinking, action}` 升级为 `{thinking, action, target_seat}`，明确说明：凡是需要选人的步骤（刀/验/毒/投票），必须把座位号填入 `target_seat`，不要只写在 action 里。
- `LLMResponse.from_text` 解析时一并读取 `target_seat`：转 int、范围检查（1-6），非法或缺失则置 `None`。
- **`_parse_target` 不删除**，降级为 fallback：仅当 `target_seat` 缺失时，才退回用正则从 action 抠。兼顾结构化收益与模型偶发不听话的鲁棒性。

**回归保护**：现有 `test_llm.py` 中所有 `from_text` 测试在 `target_seat` 缺失时行为不变，必须继续通过。

### 3.2 合法性校验 + 重试（`game/engine.py`）

新增集中方法（暂名 `_call_ai_with_target`），所有"要选人"的环节（狼人刀人 / 预言家验人 / 女巫毒人 / 投票 / 重投）统一走它。

```
_call_ai_with_target(seat_id, prompt, valid_targets, action_name):
    1. 调 _call_ai 拿到 {thinking, action, target_seat}
    2. 取 target = target_seat（缺失则 fallback 到 _parse_target）
    3. 校验 target 是否 ∈ valid_targets：
       - 合法 → 返回 (target, thinking, action)
       - 非法 → 把"你刚才选了 X 号，但该选择不合法（原因），
                请从 [合法列表] 中重选"拼进 prompt，重试 1 次
    4. 重试后仍非法 → 降级：
       - 夜晚行动（刀/验/毒）→ 返回 target=None（放弃本次行动）
       - 投票 → target=None（弃票，复用现有弃票逻辑）
```

**`valid_targets` 按角色规则由调用方算好传入**：

| 环节 | 合法目标 |
|------|----------|
| 狼人刀人 | 存活 且 非狼队友 且 非自己 |
| 预言家验人 | 存活 且 非自己（重复验人合法但浪费，不硬性拒绝；由 prompt 中的查验记录提示避免重复） |
| 女巫毒人 | 存活 且 非自己 |
| 投票 / 重投 | 存活 且 非自己 |

**女巫的特殊性**：女巫的决策是二维的（用哪种药 + 对谁），不能套用纯粹的"选一个目标"模型。处理方式：
- 保留现有的"救/毒"关键词解析逻辑（先判断用哪种药）。
- "救"分支：目标固定为当晚刀口（`night_kill_target`），无需选人，不走目标校验。
- "毒"分支：毒杀目标走 `_call_ai_with_target` 校验（存活且非自己）。

即：`_call_ai_with_target` 只用于"毒"目标这一维，其余女巫逻辑不变。

**不改动的纯函数**：`_resolve_night_deaths`、`_count_votes` 保持原样（其测试继续通过）。`run_night` / `run_day` / `_run_vote` / 重投环节里散落的 `_call_ai` + `_parse_target` 调用，统一替换为 `_call_ai_with_target`（女巫除外，按上述特殊处理）。

**降级语义一致性**：降级到弃票/放弃，与 adapter 现有的"超时→弃票"行为一致，前端 `waiting` / WebSocket 推送逻辑不受影响。

### 3.3 结构化记忆（`game/state.py` + 少量 `game/engine.py`）

在 `private_data` 中为每个玩家维护一份**客观事实记忆**，每轮通过 `get_player_view` 透传进视角（已有机制），并在各角色 prompt 中渲染成人话。

**记忆字段**：

- 通用（所有角色）：`my_votes: {day: target_seat}` —— 我每天投了谁
- 狼人额外：`teammates`（已有）、`kill_history: {day: target_seat}` —— 每晚队伍刀了谁
- 预言家额外：`check_results: {seat: "狼人"/"好人"}`（已有，保留）
- 女巫额外：`antidote_remaining`/`poison_remaining`（已有）、`night_kill_target`（已有）、`potion_history: [{day, type, target}]` —— 用药记录
- 村民：仅通用的 `my_votes`

**写入时机（engine）**：

- 投票结算后 → 写 `my_votes`
- 狼人刀人确定后 → 写 `kill_history`
- 女巫用药后 → 写 `potion_history`
- 预言家验人后 → 写 `check_results`（保留现有逻辑）

**读取 / 渲染**：`get_player_view` 已整体透传 `private_data`，记忆字段天然进入视角。各角色 prompt 中将记忆渲染为自然语言，例如：

- 预言家发言/投票 prompt："你已查验：3号是狼人、5号是好人"
- 投票 prompt："你前几天投过：D1→3号，D2→5号"
- 女巫 prompt："你的用药记录：D1 用毒药毒了 5 号"

**为什么能修前后矛盾**：模型不再从长篇发言中"推导"自己做过什么，而是直接读到一份明确、属于自己的事实清单，发言与投票有了一致的事实锚点。

---

## 四、测试与验证策略

由于 LLM 输出不确定，验证以**可确定性测试**为主：mock 掉 `_call_ai`，把校验/记忆等纯逻辑变成可断言项。

**新增 / 修改测试**：

1. 结构化输出解析（`test_llm.py` 增量）
   - `target_seat` 字段正确解析
   - 字段缺失时 fallback 到正则；范围非法时置 None
   - 现有 `from_text` 测试全部保持通过（回归）

2. 合法性校验 + 重试（`test_engine.py` 增量，mock `_call_ai`）
   - 狼人选队友 → 判非法 → 触发重试
   - 重试后给出合法目标 → 采纳
   - 重试后仍非法 → 降级（夜晚=放弃 / 投票=弃票）
   - 投票投自己 → 非法
   - 选已死玩家 → 非法

3. 结构化记忆写入（`test_engine.py` / `test_state.py` 增量）
   - 投票后 `my_votes` 写入
   - 狼人刀人后 `kill_history` 写入
   - 女巫用药后 `potion_history` 写入
   - `get_player_view` 透传记忆字段

4. 记忆渲染（`test_roles.py` 增量）
   - 给定带记忆的 view，prompt 中出现对应人话

5. 回归
   - 现有 21 个测试（engine/llm/roles/state）继续全绿
   - `test_game_e2e.py`（514 行）在接口变更后仍能跑通

**验证流程**（遵循 TDD + verification-before-completion）：

- 每个改动按 TDD：先写失败测试 → 实现 → 跑绿
- 全部完成后跑完整 `pytest`，确认无回归
- 如有可用 API key，跑一局真实对局观察是否仍杀队友/前后矛盾；无 key 则以测试全绿为准，并明确标注"未经真实对局验证"

---

## 五、受影响文件清单

| 文件 | 改动 |
|------|------|
| `backend/game/llm/base.py` | `LLMResponse` 加 `target_seat`，`from_text` 解析，prompt 格式说明 |
| `backend/game/engine.py` | 新增 `_call_ai_with_target`；替换各环节调用；写入记忆字段 |
| `backend/game/state.py` | `create_game_state` 初始化记忆字段；`get_player_view` 透传（已支持） |
| `backend/game/roles/*.py` | 各角色 prompt 渲染记忆人话 |
| `tests/*.py` | 新增/更新测试，保护回归 |

---

## 六、非目标（本次不做）

- 策略注入（悍跳、对跳、倒钩等高级玩法提示）
- 推理模型接入与 thinking 展示增强
- 对局持久化 / 复盘存档
- 人数与角色配置化（仍固定 6 人 4 角色）
- README / 文档完善
