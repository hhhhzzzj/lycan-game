# backend/main.py
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router
from runtime_paths import logs_dir

# 文件日志
LOG_DIR = logs_dir()
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "game.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logging.getLogger("werewolf").setLevel(logging.DEBUG)

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


def _find_frontend_dist() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[1] / "frontend" / "dist",
        Path(sys.executable).resolve().parent / "frontend" / "dist",
    ]
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidates.append(Path(bundle_dir) / "frontend" / "dist")
    for path in candidates:
        if (path / "index.html").exists():
            return path
    return None


FRONTEND_DIST = _find_frontend_dist()
if FRONTEND_DIST:
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
