# lycan-game

AI 驱动的 6 人狼人杀实验场。每个座位由一个大语言模型扮演，后端负责规则、状态推进和模型调用，前端实时展示发言、投票、夜晚行动和推理过程。

这个项目的目标不是做一个复杂难装的技术 Demo，而是让普通用户拿到仓库链接后，可以在 AI 助手帮助下完成下载、填 API Key、启动并开局。

## 亮点

- **6 人标准局**：2 狼人、1 预言家、1 女巫、2 平民。
- **多模型同局**：支持 DeepSeek、MiniMax、小米 Mimo、火山方舟等 OpenAI-compatible 接口。
- **实时观战**：WebSocket 推送游戏状态，前端同步展示角色、发言、投票和事件流。
- **信息隔离**：每个 AI 只拿到自己视角的信息，狼人、预言家、女巫各有不同上下文。
- **小白友好**：Release 包可做到不安装 Python、不安装 Node.js，只填 API Key。
- **低成本连通性检查**：默认按厂商/base_url 去重，每家只 ping 一次，不跑完整游戏、不做深度自检。

## 最快开始

### 给不会编程的玩家

优先使用 Windows Release 包：

1. 打开仓库的 GitHub Releases 页面。
2. 下载 `lycan-game-windows.zip`。
3. 解压后双击 `start.bat`。
4. 按终端提示粘贴 API Key。
5. 浏览器打开 `http://localhost:8000` 开局。

Release 包内置后端可执行文件和前端构建产物，玩家机器不需要安装 Python 或 Node.js。

重新配置 API Key：双击 `configure.bat`。

快速测试模型能不能连通：双击 `ping_model.bat`。

### 让 AI 助手代跑

把仓库链接和下面这段话发给 AI 助手：

```text
请按仓库里的 AI_QUICKSTART.md 帮我启动 lycan-game。优先下载 Release 包；如果没有 Release，再走源码模式。需要 API Key 时在本机终端提示我输入，不要让我把 Key 发到聊天里。
```

给 AI 助手的完整操作说明在 [AI_QUICKSTART.md](AI_QUICKSTART.md)。

### 开发者源码运行

后端：

```powershell
git clone <repo-url>
cd lycan-game
python -m venv backend/.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
python scripts\configure_players.py
python scripts\ping_model.py --timeout 20
cd backend
.\.venv\Scripts\python.exe main.py
```

前端开发服务器：

```powershell
cd frontend
npm install
npm run dev
```

源码模式下：

- 后端默认地址：`http://localhost:8000`
- 前端开发地址：`http://localhost:5173`
- 如果已经构建过前端，也可以直接访问后端地址打开页面。

## 模型配置

真实配置文件是：

```text
backend/config/players.json
```

这个文件包含 API Key，已经被 `.gitignore` 忽略，不应该提交到仓库。

可以从示例文件复制：

```powershell
Copy-Item backend\config\players.example.json backend\config\players.json
```

也可以运行交互式配置向导：

```powershell
python scripts\configure_players.py
```

配置格式示例：

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

目前推荐使用 `provider: "openai"` 接入 OpenAI-compatible 服务。只要厂商兼容 Chat Completions 格式，通常只需要改 `model_name`、`api_key` 和 `base_url`。

常用模板：

- [backend/config/players.example.json](backend/config/players.example.json)
- [backend/config/players.deepseek-minimax-mimo.example.json](backend/config/players.deepseek-minimax-mimo.example.json)
- [backend/config/players.volcengine.example.json](backend/config/players.volcengine.example.json)
- [backend/config/players.volcengine-coding-plan.example.json](backend/config/players.volcengine-coding-plan.example.json)

## 连通性测试

接入新厂商或新 base_url 后，先运行：

```powershell
python scripts\ping_model.py --timeout 20
```

默认逻辑：

- 按 `(provider, base_url)` 去重。
- 同一家厂商只测一个代表座位。
- 不打印 API Key。
- 只发送一次短请求，不跑完整游戏。
- thinking 模型默认给 `128` 输出 token，避免因为 token 太低导致假性空回复。

只测试某个座位：

```powershell
python scripts\ping_model.py --seat 3 --timeout 20
```

## 打包 Release

在 Windows 上执行：

```powershell
.\scripts\build_windows_release.ps1
```

产物：

```text
release/lycan-game-windows.zip
```

压缩包内包含：

- `lycan-game.exe`：后端可执行文件，负责 API、WebSocket 和静态前端。
- `start.bat`：配置并启动游戏。
- `configure.bat`：重新填写 API Key。
- `ping_model.bat`：快速测试厂商连通性。
- `config/players.example.json`：配置模板。

## 游戏规则

标准 6 人局：

| 阵营 | 角色 | 人数 |
| --- | --- | --- |
| 狼人阵营 | 狼人 | 2 |
| 好人阵营 | 预言家 | 1 |
| 好人阵营 | 女巫 | 1 |
| 好人阵营 | 平民 | 2 |

胜利条件：

- 狼人方：所有好人出局。
- 好人方：所有狼人出局。

流程：

```text
夜晚 -> 白天 -> 投票 -> 结算 -> 下一轮
```

夜晚顺序：

1. 狼人选择击杀目标。
2. 预言家查验一名玩家身份。
3. 女巫决定是否使用解药或毒药。

白天顺序：

1. 公布死亡信息。
2. 存活玩家依次发言。
3. 存活玩家投票放逐。
4. 平票时按规则重投。

## 技术栈

后端：

- Python 3.11+
- FastAPI
- Uvicorn
- OpenAI-compatible Chat Completions
- Pytest

前端：

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Playwright

## 项目结构

```text
sand-box/
├── backend/
│   ├── api/                    # REST API 与 WebSocket 路由
│   ├── config/                 # 游戏配置与玩家模板
│   ├── game/                   # 游戏引擎、状态、角色、LLM 适配器
│   ├── main.py                 # FastAPI 入口
│   └── model_ping.py           # 轻量模型连通性测试
├── frontend/
│   └── src/                    # React 前端
├── scripts/
│   ├── configure_players.py    # 交互式配置向导
│   ├── ping_model.py           # 命令行 ping 包装
│   └── build_windows_release.ps1
├── tests/                      # 后端测试
├── docs/                       # 设计文档
└── AI_QUICKSTART.md            # 给 AI 助手的启动说明
```

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/game/start` | 使用本地 `players.json` 创建并启动游戏 |
| `POST` | `/game/create` | 通过请求体自定义玩家配置创建游戏 |
| `POST` | `/game/{id}/start` | 启动已创建的游戏 |
| `POST` | `/game/{id}/continue` | 推进交互式游戏 |
| `GET` | `/game/{id}/status` | 获取游戏状态 |
| `GET` | `/games` | 列出活跃游戏 |
| `GET` | `/game/config` | 获取玩家配置，API Key 会被隐藏 |
| `GET` | `/models/presets` | 获取预设模型列表 |
| `GET` | `/health` | 健康检查 |
| `WS` | `/game/{id}/ws` | 实时推送游戏状态 |

## 测试

后端：

```powershell
cd backend
pytest
```

前端：

```powershell
cd frontend
npx playwright test
```

基础语法检查：

```powershell
python -m compileall backend scripts
```

## 隐私与安全

- 不要提交 `backend/config/players.json`。
- 不要提交 `backend/config/players.json.bak`、`players.json.back` 等本地备份。
- 不要把 API Key 发到聊天窗口；让 AI 助手在本机终端里提示输入。
- `/game/config` 返回配置时会隐藏 API Key。
- 分享给朋友时优先发 Release 包，不要发自己填过 Key 的配置目录。

## 许可证

未指定。发布前请根据你的分发方式补充 License。
