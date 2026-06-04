"""Scan a summary log for known failure patterns.

Usage:
  python scripts/check_latest_summary.py
  python scripts/check_latest_summary.py backend/logs/summary/game_YYYYMMDD_HHMMSS.txt
"""
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        log_dir = Path(__file__).parent.parent / "backend" / "logs" / "summary"
        logs = sorted(log_dir.glob("game_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not logs:
            raise SystemExit("No summary logs found")
        path = logs[0]
    text = path.read_text(encoding="utf-8")
    patterns = {
        "empty_speech": r'💬\s*""',
        "json_leak": r'💬\s*"\s*\{["\']thinking["\']',
        "rate_limit": r"429|Too many requests|limitation",
        "invalid_target": r"未选出有效",
        "api_error": r"API 错误|API 超时",
    }
    print(f"扫描日志: {path}")
    found_any = False
    for name, pattern in patterns.items():
        hits = re.findall(pattern, text)
        print(f"{name}: {len(hits)}")
        found_any = found_any or bool(hits)
    raise SystemExit(1 if found_any else 0)


if __name__ == "__main__":
    main()
