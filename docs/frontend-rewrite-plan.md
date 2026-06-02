# AI 狼人杀前端重写 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task should result in a working state that can be verified in the browser.

**Goal:** 重写前端为全屏固定视框的中世纪哥特暗黑风格观战界面

**Architecture:** React SPA，单页三栏布局（左玩家/中主舞台/右事件），通过 WebSocket hook 接收后端 PublicGameState 驱动全部 UI 渲染。所有组件是纯展示组件，状态统一由 App 层分发。

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS 4, framer-motion, 自定义 CSS 动画

**Spec:** `docs/frontend-rewrite-spec.md`
**Mockup:** `docs/mockups/full-demo.html`

---

## File Structure

```
frontend/src/
├── main.tsx                     # 入口
├── App.tsx                      # 顶层状态管理 + 路由切换
├── styles/
│   ├── index.css                # Tailwind 导入 + CSS 变量 + 全局样式
│   └── animations.css           # 自定义 keyframes
├── hooks/
│   ├── useGameSocket.ts         # WebSocket 连接（保留逻辑，类型更新）
│   ├── useAutoPlay.ts           # 自动播放 + 快进逻辑
│   └── useEventLog.ts           # 从 gameState 变化提取事件
├── types/
│   └── game.ts                  # 类型定义（保持不变）
├── components/
│   ├── WelcomePage.tsx           # 欢迎页/仪式开场
│   ├── GameLayout.tsx            # 三栏布局容器 + 背景
│   ├── TopBar.tsx                # 顶栏
│   ├── PlayerPanel.tsx           # 左栏
│   ├── PlayerCard.tsx            # 玩家卡片
│   ├── MainStage.tsx             # 中间主区域容器
│   ├── CurrentAction.tsx         # 当前行动区（思考+发言）
│   ├── DialogStream.tsx          # 对话流
│   ├── MessageBubble.tsx         # 单条消息
│   ├── ActionBar.tsx             # 底部操作栏
│   ├── InfoPanel.tsx             # 右栏容器
│   ├── EventLog.tsx              # 事件日志
│   ├── VoteChart.tsx             # 投票条形图
│   ├── PostGameOverlay.tsx       # 复盘覆盖层
│   └── GameBackground.tsx        # 昼夜背景层
└── index.html                    # 更新字体引入
```

---

## Task 1: 安装依赖 + Tailwind 配置

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/styles/index.css`
- Create: `frontend/src/styles/animations.css`
- Modify: `frontend/index.html`（字体）
- Modify: `frontend/vite.config.ts`（如需）

- [ ] **Step 1: 安装 Tailwind CSS 4 和 framer-motion**

```bash
cd frontend
npm install tailwindcss @tailwindcss/vite framer-motion
```

- [ ] **Step 2: 配置 Vite 插件**

`vite.config.ts` 添加 tailwind 插件：
```typescript
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

- [ ] **Step 3: 创建全局样式**

`src/styles/index.css`：包含 Tailwind 导入、CSS 变量（配色/字体）、昼夜主题 class。

- [ ] **Step 4: 创建动画文件**

`src/styles/animations.css`：呼吸灯、fadeInUp、雾气漂移等 keyframes。

- [ ] **Step 5: 更新 index.html**

添加 Google Fonts 引入（Cinzel + Noto Serif SC）。

- [ ] **Step 6: 更新 main.tsx 导入样式**

替换原有 `App.css` 和 `index.css` 导入为新样式文件。

- [ ] **Step 7: 验证**

运行 `npm run dev`，确认页面能正常加载，Tailwind class 生效。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "chore: setup tailwind 4 + framer-motion + theme variables"
```

---

## Task 2: 背景层 + 昼夜切换

**Files:**
- Create: `frontend/src/components/GameBackground.tsx`

- [ ] **Step 1: 实现 GameBackground 组件**

接收 `isNight: boolean` prop，渲染固定定位背景层：
- 噪点纹理（CSS SVG filter）
- 夜晚层：月光、血红雾气、暗角
- 白天层：暖光、金色辉光
- 用 framer-motion 的 `animate` 做 opacity 过渡（0.8s）

- [ ] **Step 2: 验证**

临时在 App.tsx 中渲染 GameBackground，加一个按钮切换 isNight，确认昼夜过渡效果明显。

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: add GameBackground with day/night transition"
```

---

## Task 3: 全屏三栏布局

**Files:**
- Create: `frontend/src/components/GameLayout.tsx`
- Create: `frontend/src/components/TopBar.tsx`
- Create: `frontend/src/components/PlayerPanel.tsx`
- Create: `frontend/src/components/MainStage.tsx`
- Create: `frontend/src/components/InfoPanel.tsx`

- [ ] **Step 1: 实现 GameLayout**

全屏 flex 容器（h-screen overflow-hidden），包含：
- TopBar（48px 固定高度）
- 主体区域（flex: 1, flex row）：左 300px | 中 flex-1 | 右 300px

- [ ] **Step 2: 实现 TopBar**

Props: `phase, day, statusText, connected, autoPlay, onAutoPlayChange`
渲染：Logo、阶段 badge（昼夜颜色不同）、状态文字、连接指示、自动播放开关。

- [ ] **Step 3: 实现 PlayerPanel（占位）**

左栏框架，暂时渲染静态占位文字"玩家列表"。

- [ ] **Step 4: 实现 MainStage（占位）**

中间框架，flex column，暂时渲染占位。

- [ ] **Step 5: 实现 InfoPanel（占位）**

右栏框架，暂时渲染占位。

- [ ] **Step 6: 在 App.tsx 中组装**

替换原有 GameBoard，使用 GameLayout + GameBackground。传入 gameState 的 phase 判断昼夜。

- [ ] **Step 7: 验证**

`npm run dev`，确认三栏布局正确，全屏无滚动，顶栏信息显示。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "feat: implement full-screen three-column layout"
```

---

## Task 4: 玩家卡片 + 左栏

**Files:**
- Create: `frontend/src/components/PlayerCard.tsx`
- Modify: `frontend/src/components/PlayerPanel.tsx`

- [ ] **Step 1: 实现 PlayerCard**

Props: `player, isSpeaking, isSpectator`
渲染：座位号圆形 badge、名字、模型名、角色（彩色）、存活状态（绿点/十字）。
发言中状态：金色边框 + 呼吸灯动画（CSS animation）。
死亡状态：灰度 + 透明度降低。

- [ ] **Step 2: 更新 PlayerPanel**

接收 `players, currentSpeaker` props，渲染 6 个 PlayerCard。

- [ ] **Step 3: 验证**

确认玩家列表正确显示，发言者有动画高亮。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: implement PlayerCard with speaking/dead states"
```

---

## Task 5: 当前行动区 + 对话流

**Files:**
- Create: `frontend/src/components/CurrentAction.tsx`
- Create: `frontend/src/components/DialogStream.tsx`
- Create: `frontend/src/components/MessageBubble.tsx`
- Modify: `frontend/src/components/MainStage.tsx`

- [ ] **Step 1: 实现 CurrentAction**

Props: `phase, currentSpeaker, currentThinking, currentSpeech, players, nightInfo, phaseInfo`
渲染：
- 行动头部（图标 + 标题，根据 phase 和角色变化）
- 思考区域（斜体灰色，血色左边线）
- 发言区域（正常字色，金色左边线）
- 无行动时："AI 思考中..." loading 态

- [ ] **Step 2: 实现 MessageBubble**

Props: `speech: Speech, players`
渲染：座位号 badge + 名字 + 模型 + 发言内容 + 折叠思考。
入场动画：framer-motion fadeInUp。

- [ ] **Step 3: 实现 DialogStream**

Props: `messages: Speech[]`
渲染 MessageBubble 列表，自动滚动到底部。

- [ ] **Step 4: 组装到 MainStage**

上方 CurrentAction + 下方 DialogStream（flex-1 overflow-y-auto）。

- [ ] **Step 5: 验证**

连接后端或用 mock 数据，确认发言正确展示，滚动正常。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: implement CurrentAction + DialogStream"
```

---

## Task 6: 操作栏（继续/快进/自动）

**Files:**
- Create: `frontend/src/components/ActionBar.tsx`
- Create: `frontend/src/hooks/useAutoPlay.ts`
- Modify: `frontend/src/components/MainStage.tsx`

- [ ] **Step 1: 实现 ActionBar**

Props: `waiting, gameId, phase, onContinue, onSkip`
渲染：
- "继续 →" 主按钮（waiting=true 时可点，否则 disabled 显示"AI 思考中..."）
- "快进 ⏩" 按钮（投票/结束阶段隐藏）
- 步骤信息

- [ ] **Step 2: 实现 useAutoPlay hook**

输入：`gameId, waiting, enabled, interval`
逻辑：enabled 且 waiting 时，每隔 interval 自动调 `/game/{id}/continue`。

- [ ] **Step 3: 实现快进逻辑**

快进 = 连续调 `/continue` 直到收到的 gameState.phase 发生变化（通过 WebSocket 推送判断），期间按钮显示 loading。

- [ ] **Step 4: 组装到 MainStage 底部**

- [ ] **Step 5: 验证**

手动点继续能推进，自动播放开关有效，快进能跳到下一阶段。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: implement ActionBar with continue/skip/autoplay"
```

---

## Task 7: 右栏 — 事件日志 + 投票图表

**Files:**
- Create: `frontend/src/components/EventLog.tsx`
- Create: `frontend/src/components/VoteChart.tsx`
- Create: `frontend/src/hooks/useEventLog.ts`
- Modify: `frontend/src/components/InfoPanel.tsx`

- [ ] **Step 1: 实现 useEventLog hook**

监听 gameState 变化，提取关键事件存入本地数组：
- phase 变为 night → "第X夜"
- phase 变为 day → "第X天"
- killed_last_night 有值 → "X号被杀害"
- phase 变为 vote 后再变化 → 投票结果
- winner 有值 → 胜负

- [ ] **Step 2: 实现 EventLog**

Props: `events`
渲染事件列表，按类型不同左边线颜色（夜=红，日=金，投票=灰）。

- [ ] **Step 3: 实现 VoteChart**

Props: `votes, players`
渲染投票条形图：每个被投者一行（名字 + 条 + 票数 + 放逐标记）。
条形图带动画（width transition）。

- [ ] **Step 4: 组装到 InfoPanel**

上方事件日志，下方投票图表。

- [ ] **Step 5: 验证**

游戏推进时右栏正确更新，投票阶段条形图显示。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: implement EventLog + VoteChart in right panel"
```

---

## Task 8: 欢迎页

**Files:**
- Create: `frontend/src/components/WelcomePage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 实现 WelcomePage**

Props: `onGameStarted`
渲染：
- 全屏暗黑背景 + 居中内容
- 标题动画入场（Cinzel 字体，金色）
- 叙事文字："黑暗降临，六位命运之人齐聚诅咒之村..."（framer-motion 淡入）
- 从 `/game/config` 获取玩家配置展示（6 张小卡片）
- "开始游戏" 按钮（调 `/game/start`，成功后回调 onGameStarted）

- [ ] **Step 2: 更新 App.tsx 路由逻辑**

无 gameId 时显示 WelcomePage，有 gameId 时显示 GameLayout。

- [ ] **Step 3: 验证**

首次打开看到欢迎页，点开始后进入游戏界面。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: implement WelcomePage with narrative intro"
```

---

## Task 9: 复盘覆盖层

**Files:**
- Create: `frontend/src/components/PostGameOverlay.tsx`
- Modify: `frontend/src/components/GameLayout.tsx`

- [ ] **Step 1: 实现 PostGameOverlay**

Props: `gameState, visible, onClose, onRestart`
全屏覆盖层（fixed inset-0 z-50）：
- 半透明黑色遮罩 + backdrop-blur
- 中间卷轴面板（max-w-xl, 可内部滚动）
- 内容：胜负宣告 → 角色揭示表 → 每天事件摘要
- 底部按钮："重开一局"（刷新页面）/ "关闭"
- 入场动画：scale + opacity

- [ ] **Step 2: 在 GameLayout 中集成**

当 phase === 'game_over' 时自动显示 PostGameOverlay。

- [ ] **Step 3: 验证**

游戏结束后弹出复盘层，内容正确，可关闭可重开。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: implement PostGameOverlay"
```

---

## Task 10: 清理 + 动画润色 + 最终验证

**Files:**
- Delete: 原有 `src/App.css`, `src/index.css`
- Delete: 原有组件（如果还有残留）
- Modify: 多个组件添加 framer-motion 动画

- [ ] **Step 1: 删除旧文件**

清除不再使用的旧组件和样式文件。

- [ ] **Step 2: 添加 framer-motion 动画润色**

- MessageBubble 入场动画（stagger）
- PlayerCard 死亡时灰度过渡
- VoteChart 条形图数值动画
- 阶段切换时 CurrentAction 区域切换动画
- PostGameOverlay 入场动画

- [ ] **Step 3: 全流程验证**

启动后端 + 前端，完整跑一局游戏：
- 欢迎页 → 开始 → 第1夜 → 第1天 → 投票 → ... → 游戏结束 → 复盘
- 确认：昼夜切换明显、玩家状态正确、发言展示正确、投票可视化、复盘内容完整

- [ ] **Step 4: Build 验证**

```bash
npm run build
```
确认无 TypeScript 错误。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: frontend rewrite complete - gothic dark theme"
```

---

## 执行方式

建议**逐 Task 执行**，每个 Task 完成后确认浏览器效果正确再进入下一个。Task 1-3 搭完骨架后就能在浏览器看到基本布局，后续 Task 逐步填充内容。
