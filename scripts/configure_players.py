"""Run the interactive players.json setup wizard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from config_wizard import configure_players_json


if __name__ == "__main__":
    configure_players_json(force=False)
