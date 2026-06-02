# 前端优化提示词

把下面这段发给另一个会话，它可以直接开始工作。

---

## 项目背景

这是一个 AI 狼人杀观战项目。6 个 AI 玩家（接不同大模型）自动玩一局狼人杀，人类用户通过 Web 界面实时观看它们的发言、思考过程和博弈。

**技术栈**：
- 后端：Python FastAPI + WebSocket（已优化完毕，不用动）
- 前端：React 19 + TypeScript + Vite，纯手写组件，无 UI 框架
- 通信：WebSocket 实时推送游戏状态

**项目路径**：`d:\求职之路\八股\进阶\ai-practice\sand-box\frontend`

**后端 API**（已稳定，前端只需对接）：
- `POST /game/start` → 创建并开始游戏，返回 `{game_id, players}`
- `POST /game/{id}/continue` → 推进游戏到下一步
- `GET /game/config` → 获取玩家配置（不含 key）
- `WS /game/{id}/ws` → 实时推送 `PublicGameState`

**WebSocket 推送数据结构**（见 `frontend/src/types/game.ts`）：
```typescript
interface PublicGameState {
  phase: 'game_init' | 'night' | 'day' | 'vote' | 'revote' | 'game_over';
  day: number;
  players: Player[];  // seat_id, player_name, model_name, role, is_alive
  speech_history: Speech[];  // 当天发言
  full_history: Speech[];    // 全部历史发言
  votes: Record<string, number | null>;  // 投票记录
  killed_last_night: number[];
  winner: string | null;
  current_speaker: number | null;
  current_thinking: string | null;   // AI 内心思考（核心卖点）
  current_speech?: string;           // AI 对外发言
  night_info?: string;               // 夜间行动信息
  phase_info?: string;               // 阶段描述
  vote_progress?: string;            // 投票进度
  waiting?: boolean;                 // true=等待用户点"继续"
}
```

## 当前前端状态

6 个文件：`App.tsx`, `GameSetup.tsx`, `GameBoard.tsx`, `PlayerCard.tsx`, `SpeechPanel.tsx`, `NightActionPanel.tsx`, `HistoryPanel.tsx`, `useGameSocket.ts`。

基本可用但体验粗糙：
- 全 inline style，无 CSS 框架
- 纯文本列表展示发言和历史
- 需要反复手动点"继续"按钮才能推进游戏
- 投票结果没有可视化
- 游戏结束后没有复盘
- 无自动播放模式

## 需要做的前端优化（按优先级）

### P0（核心体验，必须做）

1. **自动推进模式**
   - 加一个开关"自动播放 / 手动步进"
   - 自动模式下：每步推进后自动调 `/game/{id}/continue`，间隔 2-3 秒（可调）
   - 手动模式保持原样（点按钮推进）
   - 用户核心场景是"泡杯咖啡看 AI 打一局"，不应该要一直点

2. **投票结果可视化**
   - 投票阶段结束后，展示一个投票表格/图示：谁投了谁、得票数、谁被放逐
   - 数据来自 `gameState.votes`（key=投票者seat，value=目标seat）
   - 可以用简单的列表或箭头图

3. **游戏结束复盘页**
   - 游戏结束时（`phase === 'game_over'`）展示结构化复盘：
     - 角色揭示（所有人的真实身份+模型名）
     - 关键事件时间线（每天谁死了、投票结果）
     - 胜负原因简述
   - 数据都已在 `gameState` 中（`players` 有 role、`full_history` 有所有发言、`votes` 有投票）

### P1（体验提升）

4. **对话气泡形式展示发言**
   - 把 HistoryPanel 的纯列表改成聊天室风格（气泡+头像/座位号）
   - thinking 部分折叠，点击展开
   - 当前正在发言的人有打字机效果或高亮

5. **发言历史按天折叠**
   - `full_history` 用 day 分组，每天一个折叠块
   - 默认展开当天，之前的天数折叠

6. **夜晚/白天视觉区分**
   - 夜晚：深色背景/紫色调
   - 白天：正常亮色/暖色调
   - phase 切换时有简单过渡动画

7. **当前发言者高亮**
   - PlayerCard 正在发言时有呼吸灯或边框动画
   - 其他玩家卡片略微暗淡

### P2（锦上添花）

8. **样式改用 Tailwind CSS**（已安装 vite，加 tailwind 很方便）
9. **移动端适配**（响应式布局）
10. **死亡玩家的视觉效果**（淡出+灰度+删除线）

## 参考项目

可以参考 `d:\求职之路\八股\tool-projects\reference-projects\wolfcha` 的前端实现思路（Next.js + Tailwind），特别是：
- `src/components/game/DialogArea.tsx` — 对话区域
- `src/components/game/TalkingAvatar.tsx` — 说话动画
- `src/components/game/NightActionOverlay.tsx` — 夜间覆盖层
- `src/components/analysis/PostGameAnalysisPage.tsx` — 赛后复盘
- `src/components/game/BottomActionPanel.tsx` — 底部操作面板

注意 wolfcha 是产品级项目（有登录/付费/多语言），你不需要那些功能，只学它的观战体验设计。

## 约束

- 不要动后端代码（已在另一个会话优化完毕）
- 不要改 WebSocket 协议和 API 接口
- 保持 React + TypeScript + Vite 技术栈
- 可以引入 Tailwind CSS 或其他 CSS 方案
- 不需要登录/付费/多语言功能
- 核心目标是"看 AI 玩"的观战体验

## 开始

先读一遍 `frontend/src` 目录下的现有代码了解当前实现，然后从 P0 的三个任务开始做。每做完一个提交一次。
