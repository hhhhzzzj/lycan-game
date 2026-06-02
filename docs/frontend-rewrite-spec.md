# AI 狼人杀前端重写设计文档

## 1. 项目概述

### 1.1 定位
AI 狼人杀观战平台前端。6 个 AI 玩家（接不同大模型）自动对战，人类用户通过 Web 界面实时观看 AI 的发言、内心思考和博弈过程。

### 1.2 核心卖点
- 观看 AI 的真实思考过程（内心独白 vs 对外发言的反差）
- 不同大模型之间的策略博弈
- 沉浸式的暗黑哥特观战体验

### 1.3 技术栈
- React 19 + TypeScript + Vite
- Tailwind CSS + 自定义 CSS（动画/主题）
- framer-motion（阶段过渡、卡片入场、气泡动画）
- WebSocket 实时通信

### 1.4 后端接口（已稳定，不改动）
- `POST /game/start` → `{ game_id, players }`
- `POST /game/{id}/continue` → 推进游戏一步（每次只前进一步）
- `GET /game/config` → 玩家配置
- `WS /game/{id}/ws` → 实时推送 `PublicGameState`

### 1.5 WebSocket 数据结构
完整类型定义见 `frontend/src/types/game.ts`，核心结构：
```typescript
interface PublicGameState {
  phase: 'game_init' | 'night' | 'day' | 'vote' | 'revote' | 'game_over';
  day: number;
  players: Player[];          // seat_id, player_name, model_name, role, is_alive
  speaker_order: number[];
  speech_history: Speech[];   // 当天发言
  full_history: Speech[];     // 全部历史发言
  votes: Record<string, number | null>;  // key=投票者seat, value=目标seat
  killed_last_night: number[];
  winner: string | null;      // 'villager' | 'werewolf' | null
  current_speaker: number | null;
  current_thinking: string | null;
  current_speech?: string;
  night_info?: string;
  phase_info?: string;
  vote_progress?: string;
  waiting?: boolean;          // true = 等待前端点"继续"
}

interface Player {
  seat_id: number;
  player_name: string;
  model_name: string;
  role: string;               // 'werewolf' | 'prophet' | 'witch' | 'villager'
  is_alive: boolean;
}

interface Speech {
  seat_id: number;
  player_name: string;
  content: string;
  thinking: string;
  timestamp: number;
}
```

---

## 2. 视觉风格

### 2.1 设计语言
**中世纪哥特暗黑 · 诅咒之夜**

关键词：猎巫之夜、被诅咒的村庄、月光下的阴谋、羊皮纸上的血书

区别于 wolfcha 的"东方古卷/旧报纸"风格，本项目走**欧洲中世纪黑暗奇幻**路线。

### 2.2 配色方案
```
深渊黑    #0d0a08  — 主背景
血色      #6b1a1a  — 强调/危险/狼人
血光      #a83232  — 血色高亮
暗金      #c9a84c  — 标题/边框/活跃态
暗金暗    #6e5520  — 次要金色
羊皮纸    #2a2218  — 面板背景
焦纸      #3d3226  — 卡片背景
旧字      #e8dcc8  — 主文字
灰字      #8a7b68  — 次要文字
```

### 2.3 字体
- 标题：`Cinzel`（哥特/中世纪感西文衬线体）
- 正文：`Noto Serif SC`（中文宋体）

### 2.4 昼夜双主题
| | 夜晚 | 白天 |
|---|---|---|
| 背景 | 纯暗黑 + 雾气飘动 + 月光光晕 | 深棕暖色 + 柔光效果 |
| 强调色 | 血色 #a83232 | 暗金 #c9a84c |
| 氛围 | 阴冷、紧张 | 略微明亮、争论感 |
| 切换 | 0.8s 渐变过渡 | |

---

## 3. 布局架构

### 3.1 全屏固定视框
整个应用占满视口（100vh），不产生页面级滚动。所有内容在一个屏幕内呈现。

### 3.2 三栏结构
```
┌─────────────────────────────────────────────────────────────┐
│ 顶栏：Logo · 阶段标识 · 当前状态 · 连接指示 · 自动播放开关  │
├──────────┬────────────────────────────────────┬──────────────┤
│          │                                    │              │
│  左栏     │          中间主区域                 │    右栏      │
│  300px   │          flex: 1                   │    300px     │
│          │                                    │              │
│  玩家列表 │  ┌─────────────────────────────┐   │  事件日志    │
│  (紧凑卡片)│  │ 当前行动区（思考+发言展示）  │   │  (按时间)   │
│          │  ├─────────────────────────────┤   │              │
│  · 座位号 │  │                             │   │  投票记录    │
│  · 名字   │  │ 对话流（可滚动）             │   │  (条形图)   │
│  · 模型   │  │                             │   │              │
│  · 角色   │  ├─────────────────────────────┤   │              │
│  · 存活态 │  │ 底部操作栏（继续/快进按钮）  │   │              │
│          │  └─────────────────────────────┘   │              │
└──────────┴────────────────────────────────────┴──────────────┘
```

### 3.3 区域职责

**顶栏（48px 高）**
- Logo + 游戏名
- 阶段标识（"第2夜" / "第1天·讨论"）
- 当前状态文字（"狼人正在行动..."）
- WebSocket 连接状态
- 自动播放开关 + 速度调节

**左栏（300px）**
- 6 个玩家的紧凑卡片（垂直排列）
- 每张卡片显示：座位号、名字、模型名、角色（观战可见）、存活状态
- 当前发言者高亮（金色边框 + 呼吸灯动画）
- 死亡玩家：灰度 + 透明度降低 + 十字标记

**中间主区域（flex: 1）**
- 上方：当前行动区（展示正在行动的 AI 的思考过程和发言内容）。无人行动时显示"AI 思考中..."等待状态
- 中间：对话流（使用 `speech_history` 展示当天发言，内部可滚动）
- 底部：操作栏（继续按钮 + 快进按钮 + 进度指示）

**右栏（300px）**
- 事件日志：前端从 `gameState` 变化中自行提取关键事件（phase 变化 → 阶段标记，`killed_last_night` → 死亡事件，投票完成 → 结果记录）。保存在本地状态数组中，随游戏进程累积
- 投票记录：最近一次投票的可视化条形图（数据来自 `votes` 字段）

---

## 4. 页面/状态

### 4.1 欢迎页（GameSetup）
全屏叙事开场，带仪式感：
- 暗黑背景 + 标题动画入场
- 叙事文字："黑暗降临，六位命运之人齐聚诅咒之村..."
- 展示 6 个玩家配置卡片（名字 + 模型）
- "开始游戏"按钮（带hover特效）

### 4.2 游戏主界面（GameBoard）
三栏固定布局，根据 `phase` 切换展示内容：

**night 阶段**：
- 夜晚氛围（深色+雾气+月光）
- 当前行动区显示行动中角色的思考
- 对话流为空或显示"夜深了，村庄陷入沉寂..."

**day 阶段**：
- 白天氛围（暖色调）
- 当前行动区显示发言者的思考+发言
- 对话流显示当天已有的发言

**vote / revote 阶段**：
- 投票进行中：右栏实时更新投票条形图
- 投票结束：中间显示投票结果汇总卡片

**game_over 阶段**：
- 触发全屏复盘覆盖层

### 4.3 复盘页（PostGame Overlay）
全屏覆盖层，"战报卷轴"风格：
- 半透明黑色遮罩
- 中间卷轴式面板（可内部滚动）
- 内容：
  - 胜负宣告（好人/狼人胜利）
  - 角色揭示表（所有人的真实身份+模型名）
  - 每天事件摘要（谁死了、投票结果）
- 底部按钮："重开一局" / "关闭"

---

## 5. 交互设计

### 5.1 步进控制
- **默认手动**：每点一次"继续"，推进一步（一个人的发言/一次行动）
- **快进按钮**：前端自动连续调 `/continue` 直到 `phase` 发生变化（如从 day→vote），期间对话流快速滚动展示，不逐条停留
- **自动播放**：可切换开启，开启后自动调 `/continue`，间隔可调（2-5秒）
- 后端返回 `waiting: true` 时显示"继续"按钮，`waiting: false` 时显示"AI思考中..."（禁用态）

### 5.2 思考展示
- 当前发言者的思考过程**展开显示**在中间主区域顶部的"当前行动区"
- 思考文字用斜体 + 灰色 + 左侧血色边线，与正式发言视觉区分
- 历史对话中的思考**折叠**（`<details>` 或点击展开）

### 5.3 发言展示
- 对话流中每条发言是一个气泡卡片
- 包含：座位号 badge + 玩家名 + 模型名 + 发言内容
- 当前正在发言的气泡有微妙的入场动画（framer-motion fadeInUp）

### 5.4 投票可视化
- 投票阶段结束时，右栏更新投票条形图
- 显示：每个被投者的得票数（血色条）+ 投了谁的明细
- 被放逐者标记"放逐" badge

### 5.5 玩家状态
- 存活：绿色圆点 + 正常显示
- 死亡：灰度 + 透明度降低 + 十字标记，卡片不可交互感
- 当前发言者：金色边框 + 呼吸灯 CSS 动画

### 5.6 阶段过渡动画
使用 framer-motion：
- 昼夜切换：背景色 + 氛围效果 0.8s 渐变
- 玩家死亡：卡片淡出到灰度
- 新发言入场：气泡 fadeInUp
- 投票结果：条形图从 0 长到目标宽度
- 复盘覆盖层：从 opacity 0 + scale 0.95 过渡到正常

---

## 6. 组件结构

```
src/
├── App.tsx                    # 路由/状态管理
├── components/
│   ├── WelcomePage.tsx        # 欢迎页/开始游戏
│   ├── GameLayout.tsx         # 三栏固定布局容器
│   ├── TopBar.tsx             # 顶栏
│   ├── PlayerPanel.tsx        # 左栏：玩家列表
│   ├── PlayerCard.tsx         # 单个玩家卡片
│   ├── MainStage.tsx          # 中间主区域
│   ├── CurrentAction.tsx      # 当前行动展示（思考+发言）
│   ├── DialogStream.tsx       # 对话流
│   ├── MessageBubble.tsx      # 单条发言气泡
│   ├── ActionBar.tsx          # 底部操作栏
│   ├── InfoPanel.tsx          # 右栏容器
│   ├── EventLog.tsx           # 事件日志
│   ├── VoteChart.tsx          # 投票条形图
│   ├── PostGameOverlay.tsx    # 复盘覆盖层
│   └── GameBackground.tsx     # 背景层（昼夜氛围）
├── hooks/
│   ├── useGameSocket.ts       # WebSocket 连接
│   └── useAutoPlay.ts         # 自动播放逻辑
├── types/
│   └── game.ts                # 类型定义（保持不变）
├── styles/
│   ├── theme.css              # CSS 变量/主题
│   └── animations.css         # 自定义 CSS 动画
└── main.tsx
```

---

## 7. 数据流

```
WebSocket 推送 PublicGameState
         │
         ▼
    useGameSocket hook (状态管理)
         │
         ▼
    App.tsx (gameState, connected)
         │
    ┌────┴─────────────────────────────┐
    ▼                                  ▼
  WelcomePage                     GameLayout
  (gameId == null)            (gameState != null)
                                   │
                    ┌──────────┬────┴────┬───────────┐
                    ▼          ▼         ▼           ▼
              PlayerPanel  MainStage  InfoPanel  TopBar
```

### 7.1 状态来源
所有 UI 数据来自 `PublicGameState`，前端不维护额外游戏状态：
- `phase` → 决定布局模式和氛围
- `players` → 左栏玩家列表
- `current_speaker` + `current_thinking` + `current_speech` → 中间行动区
- `speech_history` / `full_history` → 对话流
- `votes` → 投票图表
- `killed_last_night` / `winner` → 事件日志 / 复盘
- `waiting` → 操作按钮状态

---

## 8. 约束与排除

### 做
- 纯观战体验，核心是"看 AI 玩"
- 全屏固定视框，不滚动整页
- 中世纪哥特暗黑风格
- 昼夜氛围切换
- framer-motion 中等动效
- Tailwind + 自定义 CSS
- 手动步进 + 快进 + 自动播放三种模式

### 不做
- 后端代码修改
- WebSocket 协议修改
- 登录/注册/付费
- 多语言
- 移动端适配（桌面优先，后续再说）
- 音效/TTS
- 重度粒子特效

---

## 9. 参考

- **最终效果 mockup**：`docs/mockups/full-demo.html`（完整交互模拟，可本地打开）
- 布局概念：`docs/mockups/layout-concept.html`
- 风格概念：`docs/mockups/style-concept.html`
- wolfcha 参考（仅设计思路）：`d:\求职之路\八股\tool-projects\reference-projects\wolfcha`
  - 对话区域交互逻辑：`src/components/game/DialogArea.tsx`
  - 投票卡片：`src/components/game/VoteResultCard.tsx`
  - 背景切换：`src/components/game/GameBackground.tsx`
  - 底部操作面板：`src/components/game/BottomActionPanel.tsx`

---

## 10. 实现顺序建议

1. 搭建项目骨架：Tailwind 配置 + 主题变量 + 基础布局
2. 三栏布局 + 顶栏 + 背景层
3. WebSocket hook + 基础状态流转
4. 左栏玩家列表（含存活/发言状态）
5. 中间区域：当前行动 + 对话流 + 操作栏
6. 右栏：事件日志 + 投票图表
7. 昼夜切换效果
8. 欢迎页
9. 复盘覆盖层
10. 动画润色（framer-motion）
