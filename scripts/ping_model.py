"""Fast one-shot connectivity check for a configured model."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from model_ping import main


if __name__ == "__main__":
    main(sys.argv[1:])
