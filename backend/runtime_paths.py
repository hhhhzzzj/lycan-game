"""Runtime paths for source and packaged builds."""
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def config_dir() -> Path:
    if getattr(sys, "frozen", False):
        return app_root() / "config"
    return app_root() / "config"


def logs_dir() -> Path:
    if getattr(sys, "frozen", False):
        return app_root() / "logs"
    return app_root() / "logs"
