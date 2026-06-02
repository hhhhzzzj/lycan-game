# AI 狼人杀（lycan-game）

一款 AI 驱动的 6 人狼人杀全栈游戏。每个玩家由不同的大语言模型（LLM）扮演，通过 WebSocket 实时推送游戏状态到前端，支持逐步观战和 AI 推理过程可视化。

## 技术栈

### 后端
- **Python 3.11+** + **FastAPI** — REST API 与 WebSocket 实时通信
- **OpenAI / Anthropic / Google Gemini** — 多模型 LLM 适配器（统一 OpenAI-compatible 接口）
- **Uvicorn** — ASGI 服务器
- **Pytest** — 单元测试与集成测试

### 前端
- **React 19** + **TypeScript** — 类型安全的 UI 框架
- **Vite 8** — 极速构建工具
- **Tailwind CSS 4** — 原子化样式
- **Framer Motion** — 流畅动画
- **Playwright** — E2E 测试

## 游戏规则

标准 6 人局：

| 阵营 | 角色 | 人数 |
|------|------|------|
| 狼人阵营 | 狼人 | 2 |
| 好人阵营 | 预言家 | 1 |
| 好人阵营 | 女巫 | 1 |
| 好人阵营 | 平民 | 2 |

**胜利条件：**
- 狼人方：好人全部出局
- 好人方：狼人全部出局

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd sand-box
```

### 2. 后端配置

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/macOS

pip install -r requirements.txt
```

复制玩家配置模板并填入 API Key：

```bash
cp config/players.example.json config/players.json
```

编辑 `config/players.json`，为每位玩家配置 LLM：

```json
{
  "players": [
    {
      "seat_id": 1,
      "player_name": "小明",
      "model_name": "deepseek-chat",
      "provider": "openai",
      "api_key": "sk-your-key",
      "base_url": "https://api.deepseek.com/v1"
    }
  ]
}
```

支持的 `provider`：
- `openai` — OpenAI GPT 系列，以及所有兼容 OpenAI API 格式的服务（DeepSeek、MiniMax 等）
- `anthropic` — Anthropic Claude 系列
- `google` — Google Gemini 系列

启动后端：

```bash
python main.py
```

后端默认运行在 `http://localhost:8000`。

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`。

## 项目结构

```
sand-box/
├── backend/
│   ├── api/
│   │   └── routes.py            # REST + WebSocket 路由
│   ├── config/
│   │   ├── game_config.py       # 游戏配置常量（角色分配、座位数）
│   │   ├── players.example.json # 玩家配置模板
│   │   └── players.json         # 玩家配置（含 API Key，已 gitignore）
│   ├── game/
│   │   ├── engine.py            # 游戏引擎（夜晚→白天→投票→结算）
│   │   ├── state.py             # 游戏状态管理
│   │   ├── prompt_context.py    # Prompt 上下文构建
│   │   ├── strategy.py          # 策略建议系统
│   │   ├── summary_logger.py    # 游戏复盘日志记录器
│   │   ├── llm/                 # LLM 适配器层
│   │   │   ├── adapters.py      # 统一适配器工厂
│   │   │   └── base.py          # 适配器基类
│   │   └── roles/               # 角色处理器（prompt 模板）
│   │       ├── base.py
│   │       ├── werewolf.py
│   │       ├── prophet.py
│   │       ├── witch.py
│   │       └── villager.py
│   └── main.py                  # FastAPI 应用入口
├── frontend/
│   └── src/
│       ├── App.tsx              # 应用入口
│       ├── components/          # UI 组件
│       │   ├── GameLayout.tsx   # 游戏布局
│       │   ├── MainStage.tsx    # 主舞台
│       │   ├── PlayerPanel.tsx  # 玩家面板
│       │   ├── DialogStream.tsx # 对话流
│       │   ├── ActionBar.tsx    # 操作栏
│       │   ├── WelcomePage.tsx  # 欢迎页
│       │   └── ...
│       ├── hooks/               # 自定义 hooks
│       │   ├── useAutoPlay.ts   # 自动播放逻辑
│       │   └── useEventLog.ts   # 事件日志
│       └── styles/              # 样式文件
├── scripts/
│   ├── run_auto_game.py         # 自动游戏脚本（无需前端）
│   └── run_multi_games.py       # 批量游戏脚本
├── tests/                       # 后端测试
└── docs/                        # 设计文档与原型
```

## 核心设计

### 游戏流程

```
夜晚（Night）→ 白天（Day）→ 循环直到游戏结束
```

每个夜晚按顺序执行：
1. **狼人刀人** — 狼人协商并选择击杀目标
2. **预言家验人** — 预言家查验一名玩家身份
3. **女巫用药** — 女巫决定是否使用解药/毒药

每个白天按顺序执行：
1. **宣布死亡** — 公布昨晚结果，死者发表遗言
2. **发言阶段** — 存活玩家依次发言（AI 推理 + 策略建议）
3. **投票阶段** — 存活玩家投票放逐（支持平票重投）

### 信息隔离

每位 AI 玩家只接收自己视角的信息（`get_player_view`），确保：
- 狼人只知道队友身份，不知道其他角色
- 预言家只知道自己的查验结果
- 女巫只知道当晚谁被刀了

### LLM 适配器

通过统一的适配器模式支持多家 LLM 提供商，所有模型使用 OpenAI-compatible 接口格式，降低接入成本。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/game/start` | 使用 players.json 配置创建并启动游戏 |
| POST | `/game/create` | 通过请求体自定义玩家配置创建游戏 |
| POST | `/game/{id}/start` | 启动已创建的游戏 |
| POST | `/game/{id}/continue` | 继续游戏（交互式模式下逐步推进） |
| GET | `/game/{id}/status` | 获取游戏状态 |
| GET | `/games` | 列出所有活跃游戏 |
| GET | `/game/config` | 获取玩家配置（隐藏 API Key） |
| GET | `/models/presets` | 获取预设模型列表 |
| GET | `/health` | 健康检查 |
| WS | `/game/{id}/ws` | WebSocket 实时推送游戏状态 |

## 测试

```bash
# 后端测试
cd backend
pytest

# 前端 E2E 测试
cd frontend
npx playwright test
```

## 开发环境要求

- Python 3.11+
- Node.js 18+
- 至少一个 LLM API Key（DeepSeek、OpenAI、Anthropic 或 Google）

## 致谢

参考了 [AIWolfGame](https://github.com/参考项目) 的多轮评测框架设计和 [Wolfcha](https://github.com/参考项目) 的 Web 交互方案。
