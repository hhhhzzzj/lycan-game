# AI Quickstart

This file is for AI assistants helping a non-technical user run lycan-game.

## Goal

Get the game running with the least user input. Ask the user only for their LLM API Key.

## Best Path For Non-Technical Users

1. Open the repository's GitHub Releases page.
2. Download `lycan-game-windows.zip`.
3. Extract it.
4. Run `start.bat`.
5. When the setup wizard asks, paste the user's API Key.
6. If this is a new provider/model, run `check_models.bat` before starting a real game.
7. Open `http://localhost:8000` if the browser did not open automatically.

The release package does not require Python or Node.js.

## Source Code Path

Use this path only when there is no release zip.

```powershell
git clone <repo-url>
cd lycan-game
python scripts/configure_players.py
python scripts/check_models.py
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

In another terminal:

```powershell
cd lycan-game\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## If Something Fails

- If `players.json 配置未完成` appears, run `python scripts/configure_players.py` again.
- If port `8000` is busy, close the other app using it and restart.
- If API calls fail, confirm the key belongs to the selected provider.
- Never ask the user to paste API keys into chat logs unless they explicitly choose to. Prefer local terminal prompts.
