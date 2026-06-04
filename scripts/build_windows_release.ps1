$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$releaseRoot = Join-Path $repo "release"
$releaseDir = Join-Path $releaseRoot "lycan-game-windows"
$backendDir = Join-Path $repo "backend"
$frontendDir = Join-Path $repo "frontend"

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
if (Test-Path $releaseDir) {
    Remove-Item -Recurse -Force $releaseDir
}
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Push-Location $frontendDir
npm install
npm run build
Pop-Location

Push-Location $backendDir
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
& .\.venv\Scripts\pyinstaller.exe --clean --onefile --name lycan-game `
    --add-data "$frontendDir\dist;frontend\dist" `
    main.py
Pop-Location

Copy-Item (Join-Path $backendDir "dist\lycan-game.exe") (Join-Path $releaseDir "lycan-game.exe")
New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir "config") | Out-Null
Copy-Item (Join-Path $backendDir "config\players.example.json") (Join-Path $releaseDir "config\players.example.json")
if (-not (Test-Path (Join-Path $releaseDir "config\players.json"))) {
    Copy-Item (Join-Path $backendDir "config\players.example.json") (Join-Path $releaseDir "config\players.json")
}

@'
@echo off
cd /d %~dp0
echo Starting AI Werewolf...
lycan-game.exe --configure
echo Open http://localhost:8000 in your browser.
start "" http://localhost:8000
lycan-game.exe
pause
'@ | Set-Content -Encoding ASCII (Join-Path $releaseDir "start.bat")

@'
@echo off
cd /d %~dp0
lycan-game.exe --configure --force
pause
'@ | Set-Content -Encoding ASCII (Join-Path $releaseDir "configure.bat")

@'
# lycan-game Windows Release

1. Double-click `start.bat`.
2. Paste your API Key when asked.
3. The browser opens `http://localhost:8000`.

To change API Key later, double-click `configure.bat`.

No Python or Node.js installation is needed for players who use this release package.
'@ | Set-Content -Encoding UTF8 (Join-Path $releaseDir "README.txt")

Compress-Archive -Force -Path (Join-Path $releaseDir "*") -DestinationPath (Join-Path $releaseRoot "lycan-game-windows.zip")
Write-Host "Built release package: $releaseRoot\lycan-game-windows.zip"
