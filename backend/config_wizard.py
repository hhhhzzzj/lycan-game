"""Interactive players.json setup for non-technical users."""
import json
from pathlib import Path
from typing import Any

from runtime_paths import config_dir


DEEPSEEK_PRESET = {
    "label": "DeepSeek (recommended, one key for all players)",
    "api_key_placeholder": "sk-your-deepseek-key",
    "base_url": "https://api.deepseek.com/v1",
    "models": [
        "deepseek-chat",
        "deepseek-chat",
        "deepseek-chat",
        "deepseek-chat",
        "deepseek-chat",
        "deepseek-chat",
    ],
}

MINIMAX_PRESET = {
    "label": "MiniMax (one key for all players)",
    "api_key_placeholder": "sk-your-minimax-key",
    "base_url": "https://api.minimaxi.com/v1",
    "models": [
        "MiniMax-M3",
        "MiniMax-M3",
        "MiniMax-M3",
        "MiniMax-M3",
        "MiniMax-M3",
        "MiniMax-M3",
    ],
}

PLAYER_NAMES = ["小明", "小红", "小刚", "小丽", "小华", "小强"]
PLACEHOLDER_PARTS = ("xxx", "your-key", "your_", "placeholder", "填入", "replace-me")


def is_placeholder_key(value: str | None) -> bool:
    if not value:
        return True
    text = value.strip().lower()
    return not text or any(part in text for part in PLACEHOLDER_PARTS)


def validate_players_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    players = data.get("players")
    if not isinstance(players, list):
        return ["players.json 缺少 players 列表"]
    if len(players) != 6:
        errors.append(f"players 必须正好 6 个，当前是 {len(players)} 个")

    seen_seats = set()
    for idx, player in enumerate(players, start=1):
        prefix = f"第 {idx} 个玩家"
        seat = player.get("seat_id")
        if not isinstance(seat, int) or not 1 <= seat <= 6:
            errors.append(f"{prefix}: seat_id 必须是 1-6")
        elif seat in seen_seats:
            errors.append(f"{prefix}: seat_id {seat} 重复")
        else:
            seen_seats.add(seat)
        for field in ("player_name", "model_name", "provider", "base_url"):
            if not str(player.get(field, "")).strip():
                errors.append(f"{prefix}: 缺少 {field}")
        if is_placeholder_key(player.get("api_key")):
            errors.append(f"{prefix}: api_key 还没有填写")
    return errors


def build_config(preset: dict[str, Any], api_key: str) -> dict[str, Any]:
    return {
        "players": [
            {
                "seat_id": idx,
                "player_name": PLAYER_NAMES[idx - 1],
                "model_name": preset["models"][idx - 1],
                "provider": "openai",
                "api_key": api_key,
                "base_url": preset["base_url"],
            }
            for idx in range(1, 7)
        ]
    }


def _choose_preset() -> dict[str, Any]:
    print("选择模型供应商：")
    print("  1. DeepSeek（推荐：一个 Key 就能先玩起来）")
    print("  2. MiniMax")
    choice = input("请输入 1 或 2，直接回车默认 1：").strip()
    return MINIMAX_PRESET if choice == "2" else DEEPSEEK_PRESET


def configure_players_json(force: bool = False) -> Path:
    cfg_dir = config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    target = cfg_dir / "players.json"

    if target.exists() and not force:
        try:
            current = json.loads(target.read_text(encoding="utf-8"))
            errors = validate_players_config(current)
            if not errors:
                print(f"已检测到可用配置：{target}")
                return target
            print("检测到 players.json 还不能直接开局：")
            for error in errors:
                print(f"  - {error}")
        except Exception as exc:
            print(f"players.json 读取失败，将重新生成：{exc}")

    preset = _choose_preset()
    print(f"当前选择：{preset['label']}")
    api_key = input("请粘贴你的 API Key，然后回车：").strip()
    while is_placeholder_key(api_key):
        api_key = input("这个 Key 看起来还是空的或占位符，请重新粘贴 API Key：").strip()

    data = build_config(preset, api_key)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"配置已写入：{target}")
    return target


def main():
    configure_players_json(force=False)


if __name__ == "__main__":
    main()
